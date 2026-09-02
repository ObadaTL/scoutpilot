"""Deterministic ingest pre-filter — runs in store_jobs, before any LLM call.

A job that trips a rule is still stored; store_jobs just records the reason in
`prefilter_reason`, and the scoring queue skips any row with that column set.
Nothing here calls an LLM, the network, or the database — it is a pure
function of the job dict and the config, so it is cheap enough to run on
every discovered row and fully unit-testable.

Rules (all config-driven, see config/prefilter.yaml):
  - location:         names a non-UK/Ireland place and nothing UK/IE, and
                      isn't a UK-relevant "remote"
  - seniority_title:  Senior / Staff / Principal / Lead / Director / ... in the
                      title, with no junior/graduate qualifier
  - experience_years: an explicit "N+ years experience" ask above the cap
"""

from __future__ import annotations

import re

from scoutpilot.config import load_prefilter_config
from scoutpilot.database import _is_relevant_remote

# Years outside this range in an "N years" match are almost always noise
# (a stray year like "2019", "10x", a version string) rather than a real
# experience requirement.
_MIN_PLAUSIBLE_YEARS = 1
_MAX_PLAUSIBLE_YEARS = 25


def _contains_term(text: str, term: str) -> bool:
    """Whole-word-ish containment: `\\bterm\\b`, so 'uk' doesn't match
    'ukraine' and 'lead' doesn't match 'leader'."""
    if not term:
        return False
    return re.search(rf"\b{re.escape(term.lower().strip())}\b", text) is not None


def _check_location(location: str | None, rule: dict) -> str | None:
    if not rule.get("enabled", True):
        return None
    loc = (location or "").strip().lower()
    if not loc:
        return None
    allow = rule.get("allow_terms", []) or []
    if any(_contains_term(loc, t) for t in allow):
        return None
    deny = rule.get("deny_terms", []) or []
    hit = next((t for t in deny if _contains_term(loc, t)), None)
    if hit is None:
        return None
    if _is_relevant_remote(loc):
        return None
    return f"location: {location.strip()[:60]!r} (matched {hit!r})"


def _check_seniority(title: str | None, rule: dict) -> str | None:
    if not rule.get("enabled", True):
        return None
    t = (title or "").strip().lower()
    if not t:
        return None
    if any(_contains_term(t, term) for term in (rule.get("allow_terms", []) or [])):
        return None
    hit = next((term for term in (rule.get("terms", []) or []) if _contains_term(t, term)), None)
    if hit is None:
        return None
    return f"seniority: {hit!r} in title"


def _check_experience(title: str, body: str, rule: dict) -> str | None:
    if not rule.get("enabled", True):
        return None
    # scan: "title" (default) or "title_and_body". Body scanning is off by
    # default because it double-does the scorer's MIN_YEARS_COMMERCIAL
    # extraction, worse: on the historical DB, matching JD boilerplate
    # ("equivalent to 3 years of study", a nice-to-have) is what produced
    # nearly every fit-7 job this filter would have wrongly dropped. The
    # LLM + eligibility gate handle in-body year requirements with context.
    scan = str(rule.get("scan", "title")).lower()
    text = title if scan == "title" else f"{title}\n{body}"
    max_years = int(rule.get("max_years", 2))
    for pat in rule.get("patterns", []) or []:
        for m in re.finditer(pat, text, re.IGNORECASE):
            try:
                n = int(m.group(1))
            except (ValueError, IndexError):
                continue
            if _MIN_PLAUSIBLE_YEARS <= n <= _MAX_PLAUSIBLE_YEARS and n > max_years:
                return f"experience: {n}+ years required (cap {max_years})"
    return None


def evaluate_prefilter(job: dict, cfg: dict | None = None) -> str | None:
    """Return a short reason string if `job` should be filtered at ingest,
    else None. `cfg` defaults to load_prefilter_config()."""
    cfg = cfg if cfg is not None else load_prefilter_config()
    pf = cfg.get("prefilter", {}) or {}
    if not pf.get("enabled", True):
        return None

    title = job.get("title") or ""
    location = job.get("location")
    body = job.get("full_description") or job.get("description") or ""

    return (
        _check_location(location, pf.get("location", {}) or {})
        or _check_seniority(title, pf.get("seniority_title", {}) or {})
        or _check_experience(title, body, pf.get("experience_years", {}) or {})
    )


def prefilter_breakdown(job: dict, cfg: dict | None = None) -> list[str]:
    """Every rule `job` trips, not just the first — for historical reporting."""
    cfg = cfg if cfg is not None else load_prefilter_config()
    pf = cfg.get("prefilter", {}) or {}
    if not pf.get("enabled", True):
        return []
    title = job.get("title") or ""
    body = job.get("full_description") or job.get("description") or ""
    reasons = [
        _check_location(job.get("location"), pf.get("location", {}) or {}),
        _check_seniority(title, pf.get("seniority_title", {}) or {}),
        _check_experience(title, body, pf.get("experience_years", {}) or {}),
    ]
    return [r for r in reasons if r]
