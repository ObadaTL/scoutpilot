"""Direct ATS API harvester: scrapes Greenhouse, Ashby, and Lever career portals.

Queries official, unblocked JSON endpoints with zero browser overhead and zero CAPTCHAs.
Extracts complete job descriptions, location metadata, and application URLs directly.
"""

import json
import logging
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import urllib.request

from scoutpilot import config
from scoutpilot.database import get_connection, init_db, store_jobs

log = logging.getLogger(__name__)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

# Opportunity classification regexes
_GRAD_RE = re.compile(r"\b(graduate|new grad|grad scheme|early career|rotational|trainee|apprentice|cadet)\b", re.IGNORECASE)
_INTERN_RE = re.compile(r"\b(intern|internship|placement|co-op)\b", re.IGNORECASE)
_FUNDED_RE = re.compile(r"\b(bootcamp|funded training|skills bootcamp|reskilling|fellowship|residency)\b", re.IGNORECASE)

# Technical & target engineering keyword patterns (AI, ML, Signal Processing, Software, Python, etc.)
_TECH_ROLE_RE = re.compile(
    r"\b("
    r"ai|artificial intelligence|ml|machine learning|deep learning|nlp|llm|"
    r"signal processing|dsp|audio|video|speech|vision|computer vision|multimedia|"
    r"software|developer|engineer|engineering|programmer|coder|architect|"
    r"python|backend|back-end|frontend|front-end|fullstack|full-stack|full stack|"
    r"java|kotlin|c\+\+|golang|rust|typescript|javascript|react|node|fastapi|django|flask|"
    r"data|cloud|aws|azure|gcp|devops|sre|site reliability|infrastructure|platform|systems|"
    r"distributed|api|iot|firmware|embedded|robotics|automation|qa|test automation|"
    r"graduate|grad|new grad|early career|junior|entry level|trainee|apprentice|apprenticeship|intern|internship|placement|bootcamp|scheme"
    r")\b",
    re.IGNORECASE,
)

# Non-technical, presales, or non-engineering functions to exclude
_NON_TECH_TITLE_RE = re.compile(
    r"\b("
    r"sales|account executive|account manager|sdr|bdr|sales development|sales representative|"
    r"recruiter|recruiting|talent acquisition|people partner|human resources|hr |"
    r"brand designer|graphic designer|visual designer|creative director|"
    r"executive assistant|office manager|workplace manager|receptionist|"
    r"legal counsel|paralegal|compliance officer|compliance manager|"
    r"accounting|accountant|payroll|tax manager|controller|financial analyst|billing specialist|"
    r"content writer|copywriter|social media manager|event coordinator|event planner|"
    r"customer success manager|customer support specialist|outbound sdr|sales agent|"
    r"customer engineer|presales|pre-sales|sales engineer|solutions architect|solutions engineer|"
    r"professional services|tam leader|support engineer|customer solution architect|client support|"
    r"marketing|audit|treasury|finance|commercial|brand|strategist|communications|policy|"
    r"civil engineer|structural engineer|water engineer|process engineer|geotechnical|geoenvironmental|"
    r"environmental engineer|mechanical engineer|hvac|piping|chemical engineer|petroleum|surveyor|construction"
    r")\b",
    re.IGNORECASE,
)

# Foreign cities / states that indicate non-UK / non-remote when embedded in job titles
_FOREIGN_TITLE_LOCATIONS_RE = re.compile(
    r"\b("
    r"nyc|new york|san francisco|los angeles|seattle|austin|texas|calgary|toronto|canberra|"
    r"shenzhen|east china|beijing|shanghai|tokyo|singapore|sydney|melbourne|berlin|munich|paris|"
    r"raleigh|charlotte|cincinnati|detroit|minnesota|chicago|boston|atlanta|dallas|denver|florida|"
    r"amer|apac|latam|brazil|mexico|poland|india|bangalore"
    r")\b",
    re.IGNORECASE,
)


def is_relevant_tech_role(title: str, description: str = "") -> bool:
    """Filter to ensure we only harvest relevant tech/engineering/graduate roles."""
    if not title:
        return False
    title_lower = title.lower()

    # Reject if title explicitly targets a foreign city or region (e.g. NYC, Toronto, Shenzhen, AMER)
    # unless UK or Northern Ireland or Belfast is also in the title
    if _FOREIGN_TITLE_LOCATIONS_RE.search(title_lower):
        if not re.search(r"\b(uk|united kingdom|belfast|northern ireland|london)\b", title_lower):
            return False

    # Reject non-core / presales / non-tech functions
    if _NON_TECH_TITLE_RE.search(title_lower):
        return False

    return bool(_TECH_ROLE_RE.search(title_lower) or _TECH_ROLE_RE.search(description[:400]))


def infer_opportunity_type(title: str, description: str = "") -> str:
    """Infer the opportunity type from the title and description."""
    text = f"{title} {description[:300]}"
    if _FUNDED_RE.search(text):
        return "funded_training"
    if _GRAD_RE.search(text):
        return "graduate_scheme"
    if _INTERN_RE.search(text):
        return "internship"
    return "direct_job"


def _http_get_json(url: str, timeout: int = 15) -> dict | list | None:
    """Helper to fetch and parse JSON from a public endpoint."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = response.read().decode("utf-8", errors="replace")
                return json.loads(data)
    except Exception as e:
        log.debug("HTTP GET failed for %s: %s", url, e)
    return None


def _http_get_text(url: str, timeout: int = 15) -> str | None:
    """Helper to fetch raw text (XML feeds, etc.) from a public endpoint."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                return response.read().decode("utf-8", errors="replace")
    except Exception as e:
        log.debug("HTTP GET failed for %s: %s", url, e)
    return None


# ── Greenhouse API ─────────────────────────────────────────────────────────

def fetch_greenhouse_jobs(board_name: str, company_name: str | None = None) -> list[dict]:
    """Fetch jobs from a Greenhouse board via its public JSON API.

    Endpoint: https://boards-api.greenhouse.io/v1/boards/{board_name}/jobs?content=true
    """
    company = company_name or board_name.capitalize()
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_name}/jobs?content=true"
    data = _http_get_json(url)
    if not data or not isinstance(data, dict):
        return []

    raw_jobs = data.get("jobs", [])
    results = []
    for item in raw_jobs:
        job_url = item.get("absolute_url")
        if not job_url:
            continue

        title = item.get("title", "")
        content_html = item.get("content", "")
        if not is_relevant_tech_role(title, content_html):
            continue

        location_obj = item.get("location", {})
        location_name = location_obj.get("name", "") if isinstance(location_obj, dict) else str(location_obj)
        updated_at = item.get("updated_at", "")

        opp_type = infer_opportunity_type(title, content_html)

        results.append({
            "url": job_url,
            "title": title,
            "company": company,
            "location": location_name or "Remote / Unspecified",
            "description": f"{title} at {company}. Location: {location_name}",
            "full_description": content_html,
            "application_url": job_url,
            "site": f"Greenhouse ({company})",
            "opportunity_type": opp_type,
            "channel": "direct_ats",
            "deadline": None,
            "funding_status": "standard_salary",
        })
    return results


# ── Ashby API ──────────────────────────────────────────────────────────────

def fetch_ashby_jobs(board_name: str, company_name: str | None = None) -> list[dict]:
    """Fetch jobs from an Ashby board via its public JSON API.

    Endpoint: https://api.ashbyhq.com/posting-api/job-board/{board_name}
    """
    company = company_name or board_name.capitalize()
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board_name}"
    data = _http_get_json(url)
    if not data or not isinstance(data, dict):
        return []

    job_postings = data.get("jobPostings", []) or data.get("jobs", [])
    results = []
    for item in job_postings:
        job_url = item.get("jobUrl") or item.get("applyUrl") or item.get("url")
        if not job_url:
            continue

        title = item.get("title", "")
        content_desc = item.get("descriptionHtml") or item.get("descriptionPlain") or ""
        if not is_relevant_tech_role(title, content_desc):
            continue

        location_name = item.get("locationName") or item.get("location", "")
        if item.get("isRemote"):
            location_name = f"{location_name} (Remote)" if location_name else "Remote"

        opp_type = infer_opportunity_type(title, content_desc)

        results.append({
            "url": job_url,
            "title": title,
            "company": company,
            "location": location_name or "Remote / Unspecified",
            "description": f"{title} at {company}. Location: {location_name}",
            "full_description": content_desc,
            "application_url": item.get("applyUrl") or job_url,
            "site": f"Ashby ({company})",
            "opportunity_type": opp_type,
            "channel": "direct_ats",
            "deadline": None,
            "funding_status": "standard_salary",
        })
    return results


# ── Lever API ──────────────────────────────────────────────────────────────

def fetch_lever_jobs(board_name: str, company_name: str | None = None) -> list[dict]:
    """Fetch jobs from a Lever board via its public JSON API.

    Endpoint: https://api.lever.co/v0/postings/{board_name}?mode=json
    """
    company = company_name or board_name.capitalize()
    url = f"https://api.lever.co/v0/postings/{board_name}?mode=json"
    data = _http_get_json(url)
    if not data or not isinstance(data, list):
        return []

    results = []
    for item in data:
        job_url = item.get("hostedUrl") or item.get("applyUrl")
        if not job_url:
            continue

        title = item.get("text", "")
        content_desc = item.get("descriptionPlain") or item.get("description") or ""
        if not is_relevant_tech_role(title, content_desc):
            continue

        categories = item.get("categories", {})
        location_name = categories.get("location", "") if isinstance(categories, dict) else ""
        workplace_type = item.get("workplaceType", "")
        if workplace_type and workplace_type.lower() == "remote":
            location_name = f"{location_name} (Remote)" if location_name else "Remote"

        opp_type = infer_opportunity_type(title, content_desc)

        results.append({
            "url": job_url,
            "title": title,
            "company": company,
            "location": location_name or "Remote / Unspecified",
            "description": f"{title} at {company}. Location: {location_name}",
            "full_description": content_desc,
            "application_url": item.get("applyUrl") or job_url,
            "site": f"Lever ({company})",
            "opportunity_type": opp_type,
            "channel": "direct_ats",
            "deadline": None,
            "funding_status": "standard_salary",
        })
    return results


# ── SmartRecruiters API ─────────────────────────────────────────────────
# Endpoint: https://api.smartrecruiters.com/v1/companies/{companyIdentifier}/postings
# `companyIdentifier` is NOT the display name -- it's whatever slug the
# employer's career site actually uses (case-insensitive), and the API
# returns HTTP 200 + an empty result for a wrong slug just as readily as for
# a company with zero current openings, so a guessed identifier can't be
# trusted without checking the *company* endpoint too (404s on a truly
# invalid slug). Confirmed live 2026-09-21 against companyIdentifier
# "smartrecruiters" (SmartRecruiters' own board).

def fetch_smartrecruiters_jobs(company_id: str, company_name: str | None = None) -> list[dict]:
    company = company_name or company_id
    data = _http_get_json(f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings?limit=100")
    if not data or not isinstance(data, dict):
        return []

    results = []
    for item in data.get("content", []):
        posting_id = item.get("id")
        if not posting_id:
            continue
        job_url = f"https://jobs.smartrecruiters.com/{company_id}/{posting_id}"

        title = item.get("name", "")
        location_obj = item.get("location", {}) or {}
        location_name = ", ".join(filter(None, [location_obj.get("city"), location_obj.get("country")]))
        # The postings-list endpoint doesn't carry the full JD -- that lives
        # behind a second per-posting request this harvester doesn't make
        # (same shallow-row tradeoff as jobspy.py); left for enrichment.
        if not is_relevant_tech_role(title):
            continue

        opp_type = infer_opportunity_type(title)
        results.append({
            "url": job_url,
            "title": title,
            "company": company,
            "location": location_name or "Remote / Unspecified",
            "description": f"{title} at {company}. Location: {location_name}",
            "application_url": job_url,
            "site": f"SmartRecruiters ({company})",
            "opportunity_type": opp_type,
            "channel": "direct_ats",
            "deadline": None,
            "funding_status": "standard_salary",
        })
    return results


# ── Pinpoint API ───────────────────────────────────────────────────────────
# Endpoint: https://{board}.pinpointhq.com/postings.json -- unauthenticated,
# full JD + location + deadline in one response. Confirmed live 2026-09-21
# against board "cazoo".

def fetch_pinpoint_jobs(board_name: str, company_name: str | None = None) -> list[dict]:
    company = company_name or board_name.capitalize()
    data = _http_get_json(f"https://{board_name}.pinpointhq.com/postings.json")
    if not data or not isinstance(data, dict):
        return []

    results = []
    for item in data.get("data", []):
        job_url = item.get("url")
        if not job_url:
            continue

        title = item.get("title", "")
        description = item.get("description") or ""
        if not is_relevant_tech_role(title, description):
            continue

        location_obj = item.get("location") or {}
        location_name = location_obj.get("name") or location_obj.get("city") or ""
        workplace_type = item.get("workplace_type_text") or ""
        if workplace_type and "remote" in workplace_type.lower() and "remote" not in location_name.lower():
            location_name = f"{location_name} (Remote)" if location_name else "Remote"

        opp_type = infer_opportunity_type(title, description)

        results.append({
            "url": job_url,
            "title": title,
            "company": company,
            "location": location_name or "Remote / Unspecified",
            "description": f"{title} at {company}. Location: {location_name}",
            "full_description": description,
            "application_url": job_url,
            "site": f"Pinpoint ({company})",
            "opportunity_type": opp_type,
            "channel": "direct_ats",
            "deadline": item.get("deadline_at"),
            "funding_status": "standard_salary",
        })
    return results


# ── Personio XML feed ───────────────────────────────────────────────────
# Endpoint: https://{board}.jobs.personio.de/xml -- a syndication feed
# (Personio's own "workzag-jobs" schema), unauthenticated. Confirmed live
# 2026-09-21 against board "personio" (Personio's own board); an invalid
# board 307-redirects to the personio.com marketing site instead of
# returning XML, which _http_get_text's plain-text return can't tell apart
# from a real empty feed -- callers should treat zero results here with
# more suspicion than the JSON-API fetchers above.

def fetch_personio_jobs(board_name: str, company_name: str | None = None) -> list[dict]:
    company = company_name or board_name.capitalize()
    xml_text = _http_get_text(f"https://{board_name}.jobs.personio.de/xml")
    if not xml_text:
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        log.debug("Personio feed for %s failed to parse: %s", board_name, e)
        return []

    results = []
    for position in root.findall(".//position"):
        posting_id = position.findtext("id")
        if not posting_id:
            continue
        job_url = f"https://{board_name}.jobs.personio.de/job/{posting_id}"

        title = (position.findtext("name") or "").strip()
        office = (position.findtext("office") or "").strip()
        jd_parts = [
            (position.findtext(tag) or "")
            for tag in ("jobDescriptions", "yourProfile", "whatWeOffer")
        ]
        description = "\n\n".join(p for p in jd_parts if p).strip()
        if not is_relevant_tech_role(title, description):
            continue

        opp_type = infer_opportunity_type(title, description)
        results.append({
            "url": job_url,
            "title": title,
            "company": company,
            "location": office or "Remote / Unspecified",
            "description": f"{title} at {company}. Location: {office}",
            "full_description": description or None,
            "application_url": job_url,
            "site": f"Personio ({company})",
            "opportunity_type": opp_type,
            "channel": "direct_ats",
            "deadline": None,
            "funding_status": "standard_salary",
        })
    return results


# ── Teamtailor JSON Feed ─────────────────────────────────────────────────
# Endpoint: https://{board}.teamtailor.com/jobs.json -- a JSON Feed
# (jsonfeed.org: top-level `items`, not `jobs`/`data`), unauthenticated.
# Confirmed live 2026-09-21 against board "storytel".

def fetch_teamtailor_jobs(board_name: str, company_name: str | None = None) -> list[dict]:
    company = company_name or board_name.capitalize()
    data = _http_get_json(f"https://{board_name}.teamtailor.com/jobs.json")
    if not data or not isinstance(data, dict):
        return []

    results = []
    for item in data.get("items", []):
        job_url = item.get("url") or item.get("id")
        if not job_url:
            continue

        title = item.get("title", "")
        summary = item.get("summary") or item.get("content_text") or ""
        if not is_relevant_tech_role(title, summary):
            continue

        opp_type = infer_opportunity_type(title, summary)
        results.append({
            "url": job_url,
            "title": title,
            "company": company,
            "location": "Remote / Unspecified",
            "description": f"{title} at {company}.",
            "full_description": summary or None,
            "application_url": job_url,
            "site": f"Teamtailor ({company})",
            "opportunity_type": opp_type,
            "channel": "direct_ats",
            "deadline": None,
            "funding_status": "standard_salary",
        })
    return results


# ── Full Direct ATS Discovery Runner ──────────────────────────────────────

def run_direct_ats_discovery(
    employers: dict | None = None,
    workers: int = 4,
) -> dict:
    """Scrape configured Greenhouse, Ashby, and Lever employers and store results into the DB.

    Args:
        employers: Dict with keys 'greenhouse', 'ashby', 'lever' (defaults to config/ats_employers.yaml).
        workers: Thread pool concurrency.

    Returns:
        Dict with total_found, new_stored, existing_stored, errors.
    """
    if employers is None:
        employers = config.load_ats_employers()

    if not employers:
        log.info("No ATS employers configured.")
        return {"total_found": 0, "new": 0, "existing": 0, "errors": 0}

    conn = init_db()
    total_found = 0
    total_new = 0
    total_existing = 0
    total_errors = 0

    tasks = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for gh in employers.get("greenhouse", []):
            board = gh.get("board")
            name = gh.get("name")
            if board:
                tasks.append(executor.submit(fetch_greenhouse_jobs, board, name))

        for ash in employers.get("ashby", []):
            board = ash.get("board")
            name = ash.get("name")
            if board:
                tasks.append(executor.submit(fetch_ashby_jobs, board, name))

        for lev in employers.get("lever", []):
            board = lev.get("board")
            name = lev.get("name")
            if board:
                tasks.append(executor.submit(fetch_lever_jobs, board, name))

        for future in as_completed(tasks):
            try:
                jobs = future.result()
                if jobs:
                    total_found += len(jobs)
                    site_label = jobs[0].get("site", "Direct ATS")
                    new_cnt, ext_cnt = store_jobs(conn, jobs, site=site_label, strategy="direct_ats")
                    total_new += new_cnt
                    total_existing += ext_cnt
            except Exception as e:
                log.error("ATS fetch task failed: %s", e)
                total_errors += 1

    log.info(
        "Direct ATS discovery complete: %d found -> %d new, %d existing, %d errors",
        total_found, total_new, total_existing, total_errors,
    )
    return {
        "total_found": total_found,
        "new": total_new,
        "existing": total_existing,
        "errors": total_errors,
    }
