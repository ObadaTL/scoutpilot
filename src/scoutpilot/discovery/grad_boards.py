"""NI / UK graduate & early-career job-board harvesters.

These boards have no usable JSON API, so each parser pulls job links off
search-result HTML into pointer rows (url + title + company + location);
the enrichment stage fills in the full description per URL later.

config/grad_boards.yaml holds the per-board settings and the enabled flag.
Start point: NIJobs (proven). Add a `_parse_*` for the next board and a
branch in `_PARSERS` to switch it on.
"""

import logging
import re
import urllib.request
from datetime import datetime, timezone

from scoutpilot import config
from scoutpilot.database import init_db, store_jobs
from scoutpilot.discovery.direct_ats import infer_opportunity_type, is_relevant_tech_role

log = logging.getLogger(__name__)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

CHANNEL = "grad_boards"


def _http_get(url: str, timeout: int = 20) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return resp.read().decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        log.debug("grad_boards GET failed %s: %s", url, e)
    return ""


def _titlecase(slug: str) -> str:
    return re.sub(r"\s+", " ", slug.replace("-", " ").replace("_", " ")).strip().title()


# ── NIJobs ──────────────────────────────────────────────────────────────
# Listing pages carry links of the form
#   /job/<title-slug>/<company-slug>-job<numeric-id>
_NIJOBS_LINK_RE = re.compile(r'href="(/job/([^"/]+)/([^"]+?)-job(\d+))"')


def _parse_nijobs(html: str, base_url: str, location: str) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for path, title_slug, company_slug, job_id in _NIJOBS_LINK_RE.findall(html):
        if job_id in seen:
            continue
        seen.add(job_id)
        title = _titlecase(title_slug)
        company = _titlecase(company_slug)
        if not is_relevant_tech_role(title):
            continue
        url = base_url.rstrip("/") + path
        out.append({
            "url": url,
            "title": title,
            "company": company,
            "location": location,
            "description": f"{title} at {company} ({location}). Via NIJobs.",
            "application_url": url,
            "site": "NIJobs",
            "channel": CHANNEL,
            "opportunity_type": infer_opportunity_type(title),
            "funding_status": "standard_salary",
        })
    return out


# ── GradIreland ─────────────────────────────────────────────────────────
# The server-rendered feed at /s/jobs/all lists links of the form
#   /jobs/<title-slug>-<numeric-id>
# with no employer in the URL -- company comes from enrichment.
_GRADIRELAND_LINK_RE = re.compile(r'href="(/jobs/([a-z0-9-]+?)-(\d{5,}))"', re.I)


def _parse_gradireland(html: str, base_url: str, location: str) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for path, title_slug, job_id in _GRADIRELAND_LINK_RE.findall(html):
        if job_id in seen:
            continue
        seen.add(job_id)
        title = _titlecase(title_slug)
        if not is_relevant_tech_role(title):
            continue
        url = base_url.rstrip("/") + path
        out.append({
            "url": url,
            "title": title,
            "company": None,
            "location": location,
            "description": f"{title} ({location}). Via gradIreland.",
            "application_url": url,
            "site": "gradIreland",
            "channel": CHANNEL,
            "opportunity_type": infer_opportunity_type(title),
            "funding_status": "standard_salary",
        })
    return out


_PARSERS = {
    "nijobs": _parse_nijobs,
    "gradireland": _parse_gradireland,
}


def run_grad_boards_discovery(only: str | None = None) -> dict:
    """Harvest every enabled grad board (or just `only`). Returns
    {total_found, new, existing, errors, boards}."""
    cfg = config.load_grad_boards_config()
    if not cfg:
        log.info("No grad_boards configuration found.")
        return {"total_found": 0, "new": 0, "existing": 0, "errors": 0, "boards": 0}

    conn = init_db()
    all_jobs: list[dict] = []
    errors = 0
    boards_run = 0

    for board, bcfg in cfg.items():
        if only and board != only:
            continue
        if not bcfg.get("enabled"):
            continue
        parser = _PARSERS.get(board)
        if not parser:
            log.debug("grad_boards: no parser for %s yet", board)
            continue
        boards_run += 1
        base_url = bcfg.get("base_url", "")
        location = bcfg.get("location", "United Kingdom")
        max_pages = int(bcfg.get("max_pages", 1))
        for path in bcfg.get("list_paths", []):
            for page in range(1, max_pages + 1):
                sep = "&" if "?" in path else "?"
                url = f"{base_url.rstrip('/')}{path}" + ("" if page == 1 else f"{sep}page={page}")
                html = _http_get(url)
                if not html:
                    errors += 1
                    continue
                all_jobs.extend(parser(html, base_url, location))

    # de-dup within this run by url
    uniq = {j["url"]: j for j in all_jobs}
    jobs = list(uniq.values())

    new = existing = 0
    if jobs:
        new, existing = store_jobs(conn, jobs, site="Grad Board", strategy=CHANNEL)

    log.info("grad_boards discovery: %d boards -> %d found -> %d new, %d existing",
             boards_run, len(jobs), new, existing)
    return {
        "total_found": len(jobs),
        "new": new,
        "existing": existing,
        "errors": errors,
        "boards": boards_run,
    }
