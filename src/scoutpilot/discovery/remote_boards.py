"""Remote-first job board harvesters: remote.com and We Work Remotely.

Both are general remote-work boards (not ATS APIs), so results go through
the same `is_relevant_tech_role` filter as Hacker News -- most postings on
either site are non-technical.

remote.com/jobs/all is server-rendered HTML: job title/company/salary sit
directly in the page markup, paginated via `?page=N`. No JD text is on the
listing page itself, so rows are stored with `full_description` unset (like
jobspy.py's shallow rows) and picked up by the normal enrichment pass
(detail.py) via their own URL.

We Work Remotely publishes a real per-category RSS feed at
`/categories/<slug>.rss` -- title ("Company: Role"), region/country
eligibility, and a full HTML job description, all in one request. Feeds it
into `store_jobs` with the description already attached.
"""

from __future__ import annotations

import html
import logging
import re
import urllib.request
import xml.etree.ElementTree as ET

from scoutpilot.database import get_connection, init_db, store_jobs
from scoutpilot.discovery.direct_ats import infer_opportunity_type, is_relevant_tech_role

log = logging.getLogger(__name__)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

_TAG_RE = re.compile(r"<[^>]+>")


def _http_get_text(url: str, timeout: int = 15) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                return response.read().decode("utf-8", errors="replace")
    except Exception as e:
        log.debug("HTTP GET failed for %s: %s", url, e)
    return None


def _clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = html.unescape(raw_html)
    text = text.replace("<p>", "\n\n").replace("<br>", "\n").replace("<br/>", "\n")
    text = _TAG_RE.sub("", text)
    return text.strip()


# ── remote.com ───────────────────────────────────────────────────────────
# Job cards are plain server-rendered HTML: a link to the posting followed
# by a title span, then a company-name span. Confirmed live 2026-09-21:
# https://remote.com/jobs/all?page=1 (20 postings/page, ~320 pages listed).
_REMOTE_COM_ROW_RE = re.compile(
    r'href="(/jobs/[a-zA-Z0-9/_-]+-c[a-z0-9]+/[a-zA-Z0-9/_-]+-j[a-z0-9]+)">'
    r'<span[^>]*>([^<]+)</span></a><span[^>]*>([^<]+)</span>'
)


def fetch_remote_com_jobs(pages: int = 5) -> list[dict]:
    """Scrape https://remote.com/jobs/all, `pages` pages deep.

    No JD text is available on the listing page -- `full_description` is
    left unset so the normal enrichment pass (detail.py) fills it in from
    the job's own URL, same as jobspy.py's shallow rows.
    """
    seen: set[str] = set()
    results: list[dict] = []
    for page in range(1, pages + 1):
        page_html = _http_get_text(f"https://remote.com/jobs/all?page={page}")
        if not page_html:
            break
        rows = _REMOTE_COM_ROW_RE.findall(page_html)
        if not rows:
            break
        for path, title_raw, company_raw in rows:
            job_url = f"https://remote.com{path}"
            if job_url in seen:
                continue
            seen.add(job_url)

            title = html.unescape(title_raw).strip()
            company = html.unescape(company_raw).strip()
            if not is_relevant_tech_role(title):
                continue

            opp_type = infer_opportunity_type(title)
            results.append({
                "url": job_url,
                "title": title[:120],
                "company": company[:80],
                "location": "Remote",
                "description": f"{title} at {company}. Listed on remote.com.",
                "application_url": job_url,
                "site": "Remote.com",
                "opportunity_type": opp_type,
                "channel": "remote_boards",
                "deadline": None,
                "funding_status": "standard_salary",
            })
    return results


# ── We Work Remotely ────────────────────────────────────────────────────
# Every category has a real RSS feed at /categories/<slug>.rss (confirmed
# live 2026-09-21 for each slug below). Title is "Company: Role"; <region>/
# <country> carry work-eligibility, folded into location; <description> is
# the full HTML job posting.
_WWR_CATEGORIES = [
    "remote-programming-jobs",
    "remote-back-end-programming-jobs",
    "remote-front-end-programming-jobs",
    "remote-full-stack-programming-jobs",
    "remote-devops-sysadmin-jobs",
]


def fetch_weworkremotely_jobs(categories: list[str] | None = None) -> list[dict]:
    """Fetch and parse We Work Remotely's per-category RSS feeds."""
    seen: set[str] = set()
    results: list[dict] = []
    for cat in categories or _WWR_CATEGORIES:
        xml_text = _http_get_text(f"https://weworkremotely.com/categories/{cat}.rss")
        if not xml_text:
            continue
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            log.debug("WWR feed %s failed to parse: %s", cat, e)
            continue

        for item in root.findall(".//item"):
            link = (item.findtext("link") or "").strip()
            title_full = (item.findtext("title") or "").strip()
            if not link or not title_full or link in seen:
                continue
            seen.add(link)

            company, sep, role = title_full.partition(": ")
            if not sep:
                company, role = "WeWorkRemotely Employer", title_full

            region = (item.findtext("region") or "").strip()
            location = f"{region} (Remote)" if region and "remote" not in region.lower() else (region or "Remote")

            clean_desc = _clean_html(item.findtext("description") or "")
            if not is_relevant_tech_role(role, clean_desc):
                continue

            opp_type = infer_opportunity_type(role, clean_desc)
            results.append({
                "url": link,
                "title": role[:120],
                "company": company[:80],
                "location": location[:100],
                "description": f"WeWorkRemotely: {company} - {role}.",
                "full_description": clean_desc,
                "application_url": link,
                "site": "WeWorkRemotely",
                "opportunity_type": opp_type,
                "channel": "remote_boards",
                "deadline": None,
                "funding_status": "standard_salary",
            })
    return results


def run_remote_boards_discovery(pages: int = 5) -> dict:
    """Run both remote.com and We Work Remotely harvesters and store results.

    Returns {total_found, new, existing, errors, by_source: {...}}.
    """
    conn = init_db()
    errors = 0
    by_source: dict[str, dict] = {}

    try:
        remote_com_jobs = fetch_remote_com_jobs(pages=pages)
    except Exception as e:
        log.error("remote.com harvest failed: %s", e)
        remote_com_jobs = []
        errors += 1
    new, existing = (0, 0)
    if remote_com_jobs:
        new, existing = store_jobs(conn, remote_com_jobs, site="Remote.com", strategy="remote_boards")
    by_source["remote_com"] = {"found": len(remote_com_jobs), "new": new, "existing": existing}

    try:
        wwr_jobs = fetch_weworkremotely_jobs()
    except Exception as e:
        log.error("WeWorkRemotely harvest failed: %s", e)
        wwr_jobs = []
        errors += 1
    new2, existing2 = (0, 0)
    if wwr_jobs:
        new2, existing2 = store_jobs(conn, wwr_jobs, site="WeWorkRemotely", strategy="remote_boards")
    by_source["weworkremotely"] = {"found": len(wwr_jobs), "new": new2, "existing": existing2}

    total_found = len(remote_com_jobs) + len(wwr_jobs)
    total_new = new + new2
    total_existing = existing + existing2

    log.info(
        "Remote-boards discovery complete: %d found -> %d new, %d existing, %d errors",
        total_found, total_new, total_existing, errors,
    )
    return {
        "total_found": total_found,
        "new": total_new,
        "existing": total_existing,
        "errors": errors,
        "by_source": by_source,
    }
