"""Company-first discovery: harvest employer career pages, not job boards.

Same shape as the curated-schemes harvester -- a config registry
(config/company_pages.yaml) turned into job rows. Entries with an `ats`
block are expanded to the employer's real open roles via the public ATS
JSON API (reusing discovery.direct_ats fetchers); entries with only a
`careers_url` become one pointer row for the enrichment/scoring stages.

Also seeds from the jobs.company column: any employer the pipeline has
already discovered that appears in the registry's `known_boards` map is
re-harvested from source, so a fresh run picks up its current openings
without going through a job board.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from scoutpilot import config
from scoutpilot.database import get_connection, init_db, store_jobs
from scoutpilot.discovery.direct_ats import (
    fetch_ashby_jobs,
    fetch_greenhouse_jobs,
    fetch_lever_jobs,
)

log = logging.getLogger(__name__)

_FETCHERS = {
    "greenhouse": fetch_greenhouse_jobs,
    "ashby": fetch_ashby_jobs,
    "lever": fetch_lever_jobs,
}

CHANNEL = "company_pages"


def _expand_ats(name: str, ats: dict) -> list[dict]:
    fetcher = _FETCHERS.get((ats or {}).get("type"))
    board = (ats or {}).get("board")
    if not fetcher or not board:
        return []
    try:
        jobs = fetcher(board, name)
    except Exception as e:  # network / API shape
        log.debug("company_pages ATS fetch failed for %s (%s): %s", name, board, e)
        return []
    for j in jobs:
        j["channel"] = CHANNEL
        j["site"] = f"Career Page ({name})"
    return jobs


def _pointer_row(name: str, careers_url: str, location: str | None) -> dict:
    return {
        "url": careers_url,
        "title": f"{name} — Careers",
        "company": name,
        "location": location or "UK",
        "description": f"Employer career page for {name}. Check for current openings.",
        "full_description": (
            f"{name} career page: {careers_url}\n"
            f"Location: {location or 'UK'}\n"
            "Company-first discovery pointer -- open roles are listed on the "
            "employer's own site rather than a job board."
        ),
        "application_url": careers_url,
        "site": f"Career Page ({name})",
        "channel": CHANNEL,
        "opportunity_type": "direct_job",
        "funding_status": "standard_salary",
    }


def _registry_entries(cfg: dict) -> list[dict]:
    """Flatten the NI/UK employer lists into a single list of entry dicts."""
    entries: list[dict] = []
    for key, val in cfg.items():
        if key == "known_boards":
            continue
        if isinstance(val, list):
            entries.extend(e for e in val if isinstance(e, dict) and e.get("name"))
    return entries


def _db_seed_entries(cfg: dict, conn) -> list[dict]:
    """jobs.company values that match the known_boards map -> ATS entries."""
    known = {k.lower(): v for k, v in (cfg.get("known_boards") or {}).items()}
    if not known:
        return []
    rows = conn.execute(
        "SELECT DISTINCT company FROM jobs WHERE company IS NOT NULL AND company != ''"
    ).fetchall()
    seen: set[str] = set()
    out: list[dict] = []
    for (company,) in rows:
        m = known.get(str(company).strip().lower())
        if m and company.lower() not in seen:
            seen.add(company.lower())
            out.append({"name": company, "ats": m})
    return out


def run_company_pages_discovery(workers: int = 4, include_db_seeds: bool = True) -> dict:
    """Harvest the company-first registry. Returns
    {total_found, new, existing, errors, employers}."""
    cfg = config.load_company_pages_config()
    if not cfg:
        log.info("No company_pages configuration found.")
        return {"total_found": 0, "new": 0, "existing": 0, "errors": 0, "employers": 0}

    conn = init_db()
    entries = _registry_entries(cfg)
    if include_db_seeds:
        existing_names = {e["name"].lower() for e in entries}
        for seed in _db_seed_entries(cfg, conn):
            if seed["name"].lower() not in existing_names:
                entries.append(seed)

    all_jobs: list[dict] = []
    errors = 0
    ats_entries = [e for e in entries if e.get("ats")]
    pointer_entries = [e for e in entries if not e.get("ats") and e.get("careers_url")]

    with ThreadPoolExecutor(max_workers=max(workers, 2)) as ex:
        futs = {ex.submit(_expand_ats, e["name"], e["ats"]): e for e in ats_entries}
        for fut in as_completed(futs):
            e = futs[fut]
            try:
                got = fut.result()
                all_jobs.extend(got)
                # an ATS board that returned nothing still gets a pointer if
                # it has a careers_url, so the employer isn't lost
                if not got and e.get("careers_url"):
                    all_jobs.append(_pointer_row(e["name"], e["careers_url"], e.get("location")))
            except Exception as ex_err:  # noqa: BLE001
                log.debug("company_pages entry %s failed: %s", e.get("name"), ex_err)
                errors += 1

    for e in pointer_entries:
        all_jobs.append(_pointer_row(e["name"], e["careers_url"], e.get("location")))

    total_found = len(all_jobs)
    new = existing = 0
    if all_jobs:
        new, existing = store_jobs(conn, all_jobs, site="Career Page", strategy=CHANNEL)

    log.info(
        "Company-pages discovery: %d employers -> %d found -> %d new, %d existing",
        len(entries), total_found, new, existing,
    )
    return {
        "total_found": total_found,
        "new": new,
        "existing": existing,
        "errors": errors,
        "employers": len(entries),
    }
