"""Built In Belfast (builtinbelfast.uk) harvester: Belfast tech jobs.

Plain server-rendered HTML, no bot wall. `/jobs?page=N` carries a JSON-LD
ItemList of ~10 postings per page (~13 pages in total, empty past the last);
each posting's own page carries a full schema.org JobPosting block (real
description, employer, location, datePosted, validThrough). So a row is
stored with `full_description` already attached and needs no enrichment.
"""

from __future__ import annotations

import html
import json
import logging
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from scoutpilot.database import init_db, store_jobs
from scoutpilot.discovery.direct_ats import infer_opportunity_type, is_relevant_tech_role

log = logging.getLogger(__name__)

BASE = "https://builtinbelfast.uk"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
CHANNEL = "builtinbelfast"

_LD_RE = re.compile(r'<script type="application/ld(?:\+|&#x2B;)json">\s*(\{.*?\})\s*</script>', re.S)
_TAG_RE = re.compile(r"<[^>]+>")


def _http_get(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return resp.read().decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        log.debug("builtinbelfast GET failed %s: %s", url, e)
    return ""


def _ld_blocks(page: str) -> list[dict]:
    out = []
    for raw in _LD_RE.findall(page):
        try:
            out.append(json.loads(raw))
        except ValueError:
            continue
    return out


def _clean_html(raw: str) -> str:
    text = html.unescape(raw or "")
    text = re.sub(r"</(p|div|li|h\d)>|<br\s*/?>", "\n", text)
    text = _TAG_RE.sub("", text).replace("\xa0", " ")
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def list_job_urls(max_pages: int = 30) -> list[tuple[str, str]]:
    """(url, title) for every posting on the listing, stopping at the first empty page."""
    found: dict[str, str] = {}
    for page in range(1, max_pages + 1):
        html_text = _http_get(f"{BASE}/jobs" + ("" if page == 1 else f"?page={page}"))
        items = []
        for block in _ld_blocks(html_text):
            for node in block.get("@graph", [block]):
                if node.get("@type") == "ItemList":
                    items = node.get("itemListElement", [])
        if not items:
            break
        for it in items:
            if it.get("url"):
                found[it["url"]] = it.get("name") or ""
    return list(found.items())


def _fetch_posting(url: str, list_title: str) -> dict | None:
    page = _http_get(url)
    jp = None
    for block in _ld_blocks(page):
        for node in block.get("@graph", [block]):
            if node.get("@type") == "JobPosting":
                jp = node
    if not jp:
        return None
    title = (jp.get("title") or list_title or "").strip()
    desc = _clean_html(jp.get("description", ""))
    if not title or not desc or not is_relevant_tech_role(title, desc):
        return None
    loc = jp.get("jobLocation") or {}
    if isinstance(loc, list):
        loc = loc[0] if loc and isinstance(loc[0], dict) else {}
    addr = (loc.get("address") or {}) if isinstance(loc, dict) else {}
    parts = [addr.get("addressLocality"), addr.get("addressRegion")]
    location = ", ".join(p for p in parts if p) or "Belfast, Northern Ireland"
    org = jp.get("hiringOrganization") or {}
    if isinstance(org, list):
        org = org[0] if org and isinstance(org[0], dict) else {}
    company = (org.get("name") or "").strip() or None
    return {
        "url": url,
        "title": title[:120],
        "company": company,
        "location": location[:100],
        "description": f"{title} at {company or 'unknown'} ({location}). Via Built In Belfast.",
        "full_description": desc,
        "application_url": url,
        "site": "Built In Belfast",
        "channel": CHANNEL,
        "opportunity_type": infer_opportunity_type(title, desc),
        "deadline": (jp.get("validThrough") or None),
        "funding_status": "standard_salary",
    }


def run_builtinbelfast_discovery(workers: int = 4) -> dict:
    """Harvest Built In Belfast. Returns {total_found, new, existing, listed, errors}."""
    conn = init_db()
    listed = list_job_urls()
    if not listed:
        return {"total_found": 0, "new": 0, "existing": 0, "listed": 0, "errors": 1}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        rows = list(pool.map(lambda t: _fetch_posting(*t), listed))
    jobs = [r for r in rows if r]
    new = existing = 0
    if jobs:
        new, existing = store_jobs(conn, jobs, site="Built In Belfast", strategy=CHANNEL)
    log.info("builtinbelfast: %d listed -> %d tech -> %d new, %d existing",
             len(listed), len(jobs), new, existing)
    return {"total_found": len(jobs), "new": new, "existing": existing,
            "listed": len(listed), "errors": 0}
