"""Graduate Schemes & Funded Training Programs Harvester.

Ingests curated early-career technology graduate schemes, government-funded Skills Bootcamps (UK DfE),
reskilling cohorts, apprenticeships, and live curated markdown repositories (SimplifyJobs, etc.).
"""

import logging
import re
import urllib.request
from datetime import datetime, timezone

from scoutpilot import config
from scoutpilot.database import get_connection, init_db, store_jobs

log = logging.getLogger(__name__)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


def _http_get_text(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        log.debug("HTTP GET text failed for %s: %s", url, e)
    return ""


def parse_github_jobs_markdown(markdown_content: str, source_name: str = "GitHub Curated") -> list[dict]:
    """Parse Markdown table format commonly used in job repos (SimplifyJobs, etc.).

    Table row structure:
    | Company | Role | Location | Application/Link | Age |
    """
    if not markdown_content:
        return []

    jobs = []
    lines = markdown_content.splitlines()

    for line in lines:
        if not line.strip().startswith("|") or "---" in line or "Company" in line:
            continue

        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 3:
            continue

        company_raw = cells[0]
        role_raw = cells[1]
        location_raw = cells[2]
        link_raw = cells[3] if len(cells) > 3 else ""

        # Extract markdown link: [Text](URL)
        link_match = re.search(r"\[([^\]]+)\]\((https?://[^\)]+)\)", link_raw or role_raw or company_raw)
        company_clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", company_raw).strip()
        role_clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", role_raw).strip()

        if link_match:
            job_url = link_match.group(2)
        elif "http" in link_raw:
            url_match = re.search(r"https?://[^\s\|]+", link_raw)
            job_url = url_match.group(0) if url_match else None
        else:
            continue

        if not job_url or len(role_clean) < 3:
            continue

        jobs.append({
            "url": job_url,
            "title": role_clean,
            "company": company_clean,
            "location": location_raw or "Remote / UK Wide",
            "description": f"{role_clean} at {company_clean}. Location: {location_raw}. Sourced from {source_name}.",
            "full_description": f"{role_clean} at {company_clean}.\nLocation: {location_raw}\nApply URL: {job_url}\nProgram: Graduate / Early Career Cohort",
            "application_url": job_url,
            "site": source_name,
            "opportunity_type": "graduate_scheme",
            "channel": "curated_schemes",
            "funding_status": "standard_salary",
        })
    return jobs


def run_schemes_discovery() -> dict:
    """Ingest curated graduate schemes, funded training programs, and community markdown feeds.

    Returns:
        Dict with total_found, new_stored, existing_stored, errors.
    """
    schemes_cfg = config.load_schemes_config()
    if not schemes_cfg:
        log.info("No schemes configuration found.")
        return {"total_found": 0, "new": 0, "existing": 0, "errors": 0}

    conn = init_db()
    all_jobs = []
    total_errors = 0

    # 1. Ingest Graduate Schemes
    for g in schemes_cfg.get("graduate_schemes", []):
        url = g.get("url")
        if not url:
            continue
        all_jobs.append({
            "url": url,
            "title": g.get("name", "Graduate Technology Scheme"),
            "company": g.get("company", "Graduate Employer"),
            "location": g.get("location", "Belfast / UK"),
            "description": g.get("description", ""),
            "full_description": f"{g.get('name')} - {g.get('company')}\nLocation: {g.get('location')}\n{g.get('description')}\nDirect Application: {url}",
            "application_url": url,
            "site": f"Graduate Scheme ({g.get('company')})",
            "opportunity_type": g.get("opportunity_type", "graduate_scheme"),
            "channel": "graduate_schemes",
            "deadline": g.get("deadline"),
            "funding_status": g.get("funding_status", "standard_salary"),
        })

    # 2. Ingest Funded Training Programs
    for t in schemes_cfg.get("funded_training", []):
        url = t.get("url")
        if not url:
            continue
        all_jobs.append({
            "url": url,
            "title": t.get("name", "Funded Tech Training Programme"),
            "company": t.get("company", "Training Provider"),
            "location": t.get("location", "UK / Remote"),
            "description": t.get("description", ""),
            "full_description": f"{t.get('name')} - {t.get('company')}\nLocation: {t.get('location')}\n{t.get('description')}\nDirect Application / Enrollment: {url}",
            "application_url": url,
            "site": f"Funded Training ({t.get('company')})",
            "opportunity_type": t.get("opportunity_type", "funded_training"),
            "channel": "funded_training",
            "deadline": t.get("deadline"),
            "funding_status": t.get("funding_status", "fully_funded"),
        })

    # 3. Ingest Curated Remote / GitHub Repos
    for feed in schemes_cfg.get("curated_feeds", []):
        feed_url = feed.get("url")
        feed_name = feed.get("name", "Curated Feed")
        if feed_url and feed.get("type") == "markdown_table":
            try:
                md_content = _http_get_text(feed_url, timeout=10)
                if md_content:
                    parsed_jobs = parse_github_jobs_markdown(md_content, source_name=feed_name)
                    all_jobs.extend(parsed_jobs)
            except Exception as e:
                log.debug("Failed fetching curated feed %s: %s", feed_name, e)
                total_errors += 1

    total_found = len(all_jobs)
    total_new = 0
    total_existing = 0

    if all_jobs:
        total_new, total_existing = store_jobs(conn, all_jobs, site="Schemes & Funded Training", strategy="curated_schemes")

    log.info(
        "Schemes & Funded Training discovery complete: %d found -> %d new, %d existing",
        total_found, total_new, total_existing,
    )

    return {
        "total_found": total_found,
        "new": total_new,
        "existing": total_existing,
        "errors": total_errors,
    }
