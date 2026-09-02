"""Search Operator ('Google Dorking') & Direct ATS Discovery Agent.

Executes targeted search queries (targeting Greenhouse, Lever, Ashby, Workable, and Skills Bootcamps)
to unearth brand-new, unadvertised opportunities and direct ATS links without aggregator distortion.
"""

import html
import logging
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from scoutpilot.database import get_connection, init_db, store_jobs
from scoutpilot.discovery.direct_ats import infer_opportunity_type, is_relevant_tech_role

log = logging.getLogger(__name__)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

# Core high-precision search operator templates
DEFAULT_DORK_QUERIES = [
    # 1. Northern Ireland & Belfast direct ATS tech roles
    'site:boards.greenhouse.io ("software" OR "developer" OR "engineer" OR "python") ("Belfast" OR "Northern Ireland")',
    'site:jobs.ashbyhq.com ("software" OR "backend" OR "engineer") ("Belfast" OR "UK" OR "Remote")',
    'site:jobs.lever.co ("software" OR "developer" OR "engineer") ("Belfast" OR "Northern Ireland")',

    # 2. Graduate Schemes & Early Career Tech
    'site:boards.greenhouse.io ("graduate" OR "new grad" OR "early career" OR "associate") ("software" OR "technology") ("UK" OR "Remote" OR "Belfast")',
    'site:jobs.ashbyhq.com ("graduate" OR "junior" OR "early career" OR "entry level") ("software" OR "engineer")',
    'site:jobs.lever.co ("graduate" OR "junior" OR "associate") ("developer" OR "engineer")',

    # 3. Remote Tech & Python/Backend Engineering
    'site:boards.greenhouse.io ("backend" OR "python" OR "full stack") ("Remote" OR "Worldwide" OR "EMEA")',
    'site:jobs.ashbyhq.com ("backend" OR "python" OR "AI" OR "engineer") ("Remote")',

    # 4. Government Funded Training & Tech Bootcamps
    'intitle:"Skills Bootcamp" ("software" OR "data" OR "cloud" OR "AI") ("funded" OR "apply")',
]


def _clean_ddg_url(raw_url: str) -> str:
    """Extract destination URL from DuckDuckGo redirect link."""
    if "/l/?uddg=" in raw_url:
        match = re.search(r"uddg=([^&]+)", raw_url)
        if match:
            return urllib.parse.unquote(match.group(1))
    return raw_url


def search_duckduckgo(query: str, max_results: int = 25, timeout: int = 12) -> list[dict]:
    """Execute search query against DuckDuckGo HTML interface."""
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        },
    )

    results = []
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8", errors="replace")

        # Parse result blocks: class="result__body" or class="result__url"
        blocks = re.findall(
            r'<a[^>]+class="result__snippet[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'<a[^>]+class="result__url[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            content,
            re.DOTALL,
        )
        if not blocks:
            # Alternate pattern matching standard DDG HTML result elements
            links = re.findall(r'<a class="result__url"[^>]*href="([^"]+)"', content)
            titles = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', content)
            for i, raw_link in enumerate(links[:max_results]):
                clean_url = _clean_ddg_url(raw_link)
                snippet = re.sub(r"<[^>]+>", "", titles[i]) if i < len(titles) else ""
                results.append({"url": clean_url, "title": snippet[:100], "snippet": snippet})
            return results

        for block in blocks[:max_results]:
            raw_url = block[0] or block[2]
            snippet_html = block[1] or block[3]
            clean_url = _clean_ddg_url(raw_url)
            clean_snippet = html.unescape(re.sub(r"<[^>]+>", "", snippet_html)).strip()

            if clean_url.startswith("http"):
                results.append({
                    "url": clean_url,
                    "title": clean_snippet[:80],
                    "snippet": clean_snippet,
                })
    except Exception as e:
        log.debug("Search query failed for '%s': %s", query, e)

    return results


def run_dorking_discovery(
    queries: list[str] | None = None,
    max_results_per_query: int = 20,
) -> dict:
    """Run search operator discovery against ATS domains and funded training opportunities.

    Args:
        queries: List of search operator strings. Defaults to DEFAULT_DORK_QUERIES.
        max_results_per_query: Maximum links to harvest per query.

    Returns:
        Dict with total_found, new_stored, existing_stored, errors.
    """
    search_list = queries or DEFAULT_DORK_QUERIES
    conn = init_db()
    total_found = 0
    total_new = 0
    total_existing = 0
    total_errors = 0

    all_jobs = []

    for q in search_list:
        try:
            hits = search_duckduckgo(q, max_results=max_results_per_query)
            for hit in hits:
                url = hit.get("url")
                if not url or "duckduckgo.com" in url:
                    continue

                snippet = hit.get("snippet", "")
                title = hit.get("title") or "Software Engineering / Tech Opportunity"
                if not is_relevant_tech_role(title, snippet):
                    continue

                # Infer company and ATS
                company = "Target Employer"
                if "greenhouse.io" in url:
                    match = re.search(r"greenhouse\.io/([^/]+)", url)
                    company = match.group(1).capitalize() if match else "Greenhouse Employer"
                elif "ashbyhq.com" in url:
                    match = re.search(r"ashbyhq\.com/([^/]+)", url)
                    company = match.group(1).capitalize() if match else "Ashby Employer"
                elif "lever.co" in url:
                    match = re.search(r"lever\.co/([^/]+)", url)
                    company = match.group(1).capitalize() if match else "Lever Employer"

                opp_type = infer_opportunity_type(title, snippet)

                all_jobs.append({
                    "url": url,
                    "title": title,
                    "company": company,
                    "location": "Belfast / UK / Remote",
                    "description": snippet or f"Discovered via search operator: {q}",
                    "full_description": f"{title} at {company}\nURL: {url}\n\nSearch Context:\n{snippet}",
                    "application_url": url,
                    "site": f"Search Operator ({company})",
                    "opportunity_type": opp_type,
                    "channel": "dorking",
                    "funding_status": "standard_salary" if opp_type != "funded_training" else "fully_funded",
                })
        except Exception as e:
            log.error("Dorking query failed [%s]: %s", q, e)
            total_errors += 1

    total_found = len(all_jobs)
    if all_jobs:
        total_new, total_existing = store_jobs(conn, all_jobs, site="Search Operator Discovery", strategy="search_operator")

    log.info(
        "Search operator discovery complete: %d found -> %d new, %d existing",
        total_found, total_new, total_existing,
    )

    return {
        "total_found": total_found,
        "new": total_new,
        "existing": total_existing,
        "errors": total_errors,
    }
