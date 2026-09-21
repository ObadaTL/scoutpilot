"""Start-date / cohort inference for a discovered opportunity.

A role that starts next month and a "September 2027 intake" graduate cohort
are different opportunities and should be told apart at ingest. This reads a
normalised marker off the posting text:

  "immediate"   -- explicitly an immediate / ASAP start
  "YYYY-MM"     -- a specific month named as the start / intake
  "YYYY"        -- only a year named

`cohort_bucket()` collapses that (plus a raw deadline) into the coarse
class the scoring queue and the dashboard filter on.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

_NOW = None  # test seam; None -> real now


def _now() -> datetime:
    return _NOW or datetime.now(timezone.utc)


_MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9, "october": 10,
    "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}
_SEASONS = {"spring": 4, "summer": 6, "autumn": 9, "fall": 9, "winter": 1}

_IMMEDIATE_RE = re.compile(
    r"\b(immediate start|start immediately|starts? immediately|asap|as soon as possible|"
    r"immediate availability|start date[:\s]+immediate)\b",
    re.IGNORECASE,
)

_MONTH_ALT = "|".join(sorted(_MONTHS, key=len, reverse=True))
_SEASON_ALT = "|".join(_SEASONS)

# "September 2026", "Sept 2026", "Autumn 2026"
_MONTH_YEAR_RE = re.compile(rf"\b({_MONTH_ALT}|{_SEASON_ALT})\.?\s+(20\d\d)\b", re.IGNORECASE)
# "2026 intake", "2026 cohort", "2026 entry", "2026 graduate programme", "2026 start"
_YEAR_KEYWORD_RE = re.compile(
    r"\b(20\d\d)\s+(?:intake|cohort|entry|start|starters?|graduate|programme|program|scheme|class)\b",
    re.IGNORECASE,
)
# "intake: September 2026" / "starting in 2027" / "cohort begins 2026"
_KEYWORD_YEAR_RE = re.compile(
    r"\b(?:intake|cohort|start(?:ing|s)?|commencing|begins?|entry)\b[^.\n]{0,25}?\b(20\d\d)\b",
    re.IGNORECASE,
)


def infer_cohort_start(title: str | None,
                       description: str | None = None,
                       opportunity_type: str | None = None) -> str | None:
    """Normalised start marker, or None if the posting doesn't state one.

    Only years within [this year - 1, this year + 3] are trusted -- anything
    outside that window in an "N years" style string is noise, not a start
    date.
    """
    text = f"{title or ''}\n{description or ''}"
    if not text.strip():
        return None

    if _IMMEDIATE_RE.search(text):
        return "immediate"

    this_year = _now().year
    lo, hi = this_year - 1, this_year + 3

    def _ok(y: int) -> bool:
        return lo <= y <= hi

    m = _MONTH_YEAR_RE.search(text)
    if m:
        y = int(m.group(2))
        if _ok(y):
            token = m.group(1).lower()
            month = _MONTHS.get(token) or _SEASONS.get(token)
            return f"{y:04d}-{month:02d}"

    for rx in (_YEAR_KEYWORD_RE, _KEYWORD_YEAR_RE):
        m = rx.search(text)
        if m:
            y = int(m.group(1))
            if _ok(y):
                return f"{y:04d}"

    return None


def cohort_bucket(cohort_start: str | None, deadline: str | None = None) -> str:
    """Coarse class for filtering/ordering: 'immediate', 'this_year',
    'next_year', 'future', or 'unknown'."""
    if cohort_start == "immediate":
        return "immediate"
    this_year = _now().year
    year = None
    if cohort_start:
        m = re.match(r"(20\d\d)", cohort_start)
        if m:
            year = int(m.group(1))
    if year is None and deadline:
        m = re.search(r"(20\d\d)", deadline)
        if m:
            year = int(m.group(1))
    if year is None:
        return "unknown"
    if year <= this_year:
        return "this_year"
    if year == this_year + 1:
        return "next_year"
    return "future"


# Queue ordering: lower sorts first. Immediate and near-term opportunities
# are worth scoring ahead of a cohort two years out.
_BUCKET_RANK = {
    "immediate": 0,
    "this_year": 1,
    "unknown": 2,
    "next_year": 3,
    "future": 4,
}


def cohort_rank(cohort_start: str | None, deadline: str | None = None) -> int:
    return _BUCKET_RANK.get(cohort_bucket(cohort_start, deadline), 2)


def _cohort_effective_month(cohort_start: str | None) -> tuple[int, int] | None:
    """(year, month) a positively-inferred cohort_start resolves to, or None
    for 'immediate' / unknown (no start date was ever inferred -- those are
    never "later than" anything). A year-only value ("YYYY", no month
    stated) resolves to January of that year: the earliest date consistent
    with the text, so the horizon filter below only ever hides a year-only
    row once even that earliest reading is past the horizon.
    """
    if not cohort_start or cohort_start == "immediate":
        return None
    m = re.match(r"^(20\d\d)(?:-(\d\d))?$", cohort_start)
    if not m:
        return None
    year = int(m.group(1))
    month = int(m.group(2)) if m.group(2) else 1
    return (year, month)


def within_cohort_horizon(cohort_start: str | None, horizon_months: int = 3,
                          now: datetime | None = None) -> bool:
    """True unless `cohort_start` names a start later than `horizon_months`
    from now (calendar-month granularity, not exact days).

    'immediate' and unknown (None) are always True -- this only hides a
    *positively inferred* future date; it never treats "we don't know" as
    "later". Used to keep a graduate cohort a year out from dominating the
    active queue without deleting the row or touching cohort inference.
    """
    ym = _cohort_effective_month(cohort_start)
    if ym is None:
        return True
    year, month = ym
    now = now or _now()
    now_idx = now.year * 12 + (now.month - 1)
    target_idx = year * 12 + (month - 1)
    return target_idx <= now_idx + horizon_months
