"""targetjobs.co.uk graduate job board harvester.

targetjobs.co.uk's own search page (/search/jobs) is entirely client-
rendered -- no search API endpoint is findable anywhere in its Gatsby JS
bundles (checked live 2026-09-22: app/framework/page-specific chunks all
inspected, none reference an external API/GraphQL/search-as-a-service
host). But every live posting is listed in its sitemap
(https://targetjobs.co.uk/sitemap-index.xml -> sitemap-0.xml) at a stable
`/jobs/<slug>-<id>` URL -- 8120 postings confirmed live that day, no
pagination or search-widget guessing required.

Each posting page also server-renders a short (~450-char) meta description
(react-helmet), but not the full JD -- that only renders client-side, same
as the search page. Rows here are stored with `full_description` unset
(jobspy.py's shallow-row convention); the existing Playwright fallback
already in enrichment/detail.py (used for other JS-heavy sites) fills in
the real JD and corrects the title from the rendered page.

The title stored at discovery time is derived from the URL slug (cheap --
avoids one HTTP request per posting just to read react-helmet's title tag)
and used only to prefilter for tech relevance before storing; detail.py
overwrites it with the real title during enrichment.
"""

from __future__ import annotations

import logging
import re
import urllib.request
import xml.etree.ElementTree as ET

from scoutpilot.database import init_db, store_jobs
from scoutpilot.discovery.direct_ats import (
    _NON_TECH_TITLE_RE,
    infer_opportunity_type,
    is_relevant_tech_role,
)

log = logging.getLogger(__name__)

# is_relevant_tech_role()'s catch-all early-career terms ("graduate", "grad",
# "trainee", "scheme", ...) are safe on boards already scoped to tech
# employers (Greenhouse/Ashby/Lever), where any "Graduate X" role is a tech
# role by construction. targetjobs.co.uk spans every industry (law, retail,
# marketing, social work, finance...), so that catch-all alone matched 5571
# of 8120 postings when first measured live 2026-09-22 -- "Graduate Credit
# Analyst", "Graduate Trainee Social Worker", "Local Marketer Internship"
# all passed on "graduate"/"trainee"/"internship" alone.
#
# A second cut requiring is_relevant_tech_role()'s own (also fairly broad)
# technical-term list still matched 1493 -- direct_ats.py's bare
# "engineer"/"engineering" is safe there for the same reason ("Engineer" on
# an already-tech-scoped board), but on a general board it swept in
# mechanical/aerospace/defence/landscape-architecture engineering roles
# ("Fuel Systems Fluid Mechanical Engineering Placement", "Complex Warheads
# Lethality Engineer", "Graduate Landscape Architect"). Requires a
# software/data/ML-qualified term instead of a bare engineering discipline.
_TECH_TITLE_RE = re.compile(
    r"\b("
    r"software engineer|software developer|software engineering|"
    r"full[- ]?stack|front[- ]?end(?:\s+(?:developer|engineer))?|back[- ]?end(?:\s+(?:developer|engineer))?|"
    r"machine learning|deep learning|artificial intelligence|\bai\b|\bml\b|\bnlp\b|\bllm\b|"
    r"data engineer|data scientist|data science|data analy|"
    r"devops|site reliability|\bsre\b|cloud engineer|"
    r"python developer|java developer|\.net developer|"
    r"computer science|"
    r"cyber ?security|"
    r"embedded (?:systems? )?engineer|firmware engineer|robotics engineer|"
    r"solutions? architect|"
    r"it support|systems? admin"
    r")\b",
    re.IGNORECASE,
)


def _is_tech_role_strict(title: str) -> bool:
    """is_relevant_tech_role() plus an actual technical term -- see the
    module-level comment on _TECH_TITLE_RE for why the generic version's
    catch-all isn't enough on a general (non-tech-specific) board."""
    if not title or _NON_TECH_TITLE_RE.search(title.lower()):
        return False
    return bool(_TECH_TITLE_RE.search(title.lower())) and is_relevant_tech_role(title)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

SITEMAP_INDEX_URL = "https://targetjobs.co.uk/sitemap-index.xml"
_JOB_URL_RE = re.compile(r"^https://targetjobs\.co\.uk/jobs/([a-z0-9-]+)-(\d+)$", re.IGNORECASE)
# Acronyms that should stay upper-case rather than Title-Cased when
# reconstructing a display title from a hyphenated URL slug.
_ACRONYMS = {"ai", "ml", "hr", "it", "uk", "cad", "raf", "ceo", "cv", "phd", "stem"}


def _http_get_text(url: str, timeout: int = 15) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                return response.read().decode("utf-8", errors="replace")
    except Exception as e:
        log.debug("HTTP GET failed for %s: %s", url, e)
    return None


def _title_from_slug(slug: str) -> str:
    words = slug.split("-")
    return " ".join(w.upper() if w.lower() in _ACRONYMS else w.capitalize() for w in words)


def fetch_targetjobs_urls() -> list[str]:
    """Every live `/jobs/<slug>-<id>` URL from the sitemap."""
    index_xml = _http_get_text(SITEMAP_INDEX_URL)
    if not index_xml:
        return []
    try:
        index_root = ET.fromstring(index_xml)
    except ET.ParseError as e:
        log.debug("targetjobs sitemap index failed to parse: %s", e)
        return []

    sitemap_urls = [el.text for el in index_root.iter() if el.tag.endswith("loc") and el.text]

    job_urls: list[str] = []
    for sm_url in sitemap_urls:
        xml_text = _http_get_text(sm_url)
        if not xml_text:
            continue
        try:
            sm_root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            log.debug("targetjobs sitemap %s failed to parse: %s", sm_url, e)
            continue
        for el in sm_root.iter():
            if el.tag.endswith("loc") and el.text and _JOB_URL_RE.match(el.text):
                job_urls.append(el.text)
    return job_urls


def fetch_targetjobs_jobs() -> list[dict]:
    """Tech-relevant job rows from the sitemap. No full_description -- see
    module docstring; detail.py's Playwright fallback fills it in."""
    results = []
    for url in fetch_targetjobs_urls():
        m = _JOB_URL_RE.match(url)
        if not m:
            continue
        title = _title_from_slug(m.group(1))
        if not _is_tech_role_strict(title):
            continue

        opp_type = infer_opportunity_type(title)
        results.append({
            "url": url,
            "title": title,
            "location": "UK",
            "description": f"{title} -- listed on targetjobs.co.uk.",
            "application_url": url,
            "site": "targetjobs",
            "opportunity_type": opp_type,
            "channel": "targetjobs",
            "deadline": None,
            "funding_status": "standard_salary",
        })
    return results


def run_targetjobs_discovery() -> dict:
    """Harvest targetjobs.co.uk via its sitemap and store results into the DB."""
    conn = init_db()
    jobs = fetch_targetjobs_jobs()
    new = existing = 0
    if jobs:
        new, existing = store_jobs(conn, jobs, site="targetjobs", strategy="targetjobs")
    log.info(
        "targetjobs discovery complete: %d tech-relevant -> %d new, %d existing",
        len(jobs), new, existing,
    )
    return {"total_found": len(jobs), "new": new, "existing": existing, "errors": 0}
