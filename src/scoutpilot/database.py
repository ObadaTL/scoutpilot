"""ScoutPilot database layer: schema, migrations, stats, and connection helpers.

Single source of truth for the jobs table schema. All columns from every
pipeline stage are created up front so any stage can run independently
without migration ordering issues.
"""

import hashlib
import json
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from scoutpilot.config import APP_DIR, DB_PATH, DEFAULTS, load_location_focus

# Thread-local connection storage — each thread gets its own connection
# (required for SQLite thread safety with parallel workers)
_local = threading.local()


# A bare "remote" term is ambiguous by itself -- global job boards routinely
# tag postings restricted to a single foreign country as e.g. "Colombia -
# Remote", "REMOTE/TELETRAVAIL, ON, CAN", "Remote Jersey City (NJ)". None of
# those are workable for a UK/NI candidate. A denylist of every country/state
# that might show up there doesn't scale (confirmed live 2026-08-24: even
# after adding all 50 US states plus half a dozen countries, fresh leaks
# kept surfacing -- Colombia, Thailand, Sweden, Spain, Singapore, "ON, CAN").
# So this instead only trusts a generic remote term when the location EITHER
# carries an explicit UK/NI signal, OR is genuinely bare once the remote
# wording itself is stripped out -- a positive check, not an ever-growing
# blacklist.
_UK_SIGNAL_TERMS = ("united kingdom", "uk", "gb", "great britain",
                    "england", "scotland", "wales", "northern ireland", "belfast")
_GENERIC_REMOTE_TERMS = ("remote", "anywhere", "work from home", "wfh", "distributed")
_REMOTE_WORDING_RE = re.compile(
    r"\b(remote|anywhere|work[\s-]?from[\s-]?home|wfh|distributed|fully|100%|"
    r"first|telework|teletravail)\b"
)
_PUNCT_RE = re.compile(r"[()\[\],/-]")


def _is_relevant_remote(loc_lower: str) -> bool:
    """True if a (lowercased) location's "remote" claim is UK/NI-relevant or
    unqualified, rather than restricted to some other specific country/region."""
    if any(t in loc_lower for t in _UK_SIGNAL_TERMS):
        return True
    stripped = _PUNCT_RE.sub(" ", loc_lower)
    stripped = _REMOTE_WORDING_RE.sub(" ", stripped)
    return not stripped.strip()


def _location_priority_tier(location: str | None, tiers: list[list[str]]) -> int:
    """0-indexed priority tier for a job's location (lower = higher priority).

    Checked in order; the first tier with a matching term wins. A tier term
    that's just a generic remote-work word (see _GENERIC_REMOTE_TERMS) only
    counts as a match when _is_relevant_remote() confirms it isn't actually
    restricted to some other country -- see that function's docstring. A
    location matching none of the tiers (or a NULL location, when tiers are
    active) gets `len(tiers)` -- one past the last real tier, so it always
    sorts last and can be filtered out with `< len(tiers)`.
    """
    if not tiers:
        return 0
    if not location:
        return len(tiers)
    loc = location.lower()
    for i, terms in enumerate(tiers):
        for t in terms:
            tl = t.lower()
            if tl not in loc:
                continue
            if tl in _GENERIC_REMOTE_TERMS and not _is_relevant_remote(loc):
                continue
            return i
    return len(tiers)


def classify_location(location: str | None) -> str:
    """Human-readable place label for a job's location, for the dashboard's
    place filter. Reuses the same location_focus config and tier logic as
    loc_priority() so the two always agree; each tier's label is just its
    first configured term (e.g. tier ["Northern Ireland", "Antrim", ...]
    displays as "Northern Ireland"). Falls back to a plain Remote / Other
    split when no location_focus is configured, so the filter still works
    for a setup without one.
    """
    focus = load_location_focus()
    tiers = (focus or {}).get("priority", [])
    if tiers:
        tier = _location_priority_tier(location, tiers)
        return tiers[tier][0] if tier < len(tiers) else "Other"
    if not location:
        return "Unknown"
    return "Remote" if any(k in location.lower() for k in _GENERIC_REMOTE_TERMS) else "Other"


# Boards that list many employers: their `site` is a job board, never a
# company. Anything else in `site` IS the employer (the Workday-style
# per-company scrapers store it that way).
_AGGREGATOR_SITES = {
    "linkedin", "indeed", "glassdoor", "ziprecruiter", "google", "remoteok",
    "welcometothejungle", "job bank canada", "careerjet canada", "hacker news",
}

# "Greenhouse (GitLab)", "Ashby (Supabase)", "Lever (Spotify)".
_BOARD_SITE_RE = re.compile(
    r"^(?:greenhouse|ashby|lever|workday|smartrecruiters)\s*\((.+)\)\s*$", re.I
)

# The scorer writes company_summary as prose that opens on the employer:
# "Riff Financial is a pre-launch UK fintech...", "Esri develops...",
# "Cisco's Webex Engineering Group is...". Up to four capitalised words
# before the verb, which covers "Motorola Solutions" and "M Group Energy"
# without swallowing half a sentence.
_COMPANY_NAME = r"[A-Z][\w&.\-]*(?:\s+[A-Z][\w&.\-]*){0,3}"
# Two shapes, possessive first: in "Cisco's Webex Engineering Group is
# building ..." the employer is Cisco, and the name ends at the apostrophe --
# without this branch the verb pattern below walks past it and matches
# nothing, because what follows "Cisco's" is another proper noun rather
# than a verb.
_SUMMARY_COMPANY_RES = (
    re.compile(rf"^\s*({_COMPANY_NAME})(?:'s|’s)\s"),
    re.compile(
        rf"^\s*({_COMPANY_NAME})\s+"
        r"(?:is|are|was|operates|builds|provides|develops|delivers|has|works|"
        r"specialis|specializ)"
    ),
)

UNKNOWN_COMPANY = "Unknown employer"


def derive_company(job: dict | sqlite3.Row) -> str:
    """Best available employer name for a job, for grouping in the dashboard.

    Derived at read time rather than backfilled into the `company` column,
    because only the first source below is authoritative -- the other two
    are recovery for rows that should have had a company and don't.

    Three sources, most trustworthy first:

    1. `company` itself. Set by the direct-ATS and schemes harvesters, and
       (from 2026-09-02) by the JobSpy path, which read it and then dropped
       it on the floor for the whole life of the database -- see
       discovery/jobspy.store_jobspy_results. That bug is why this function
       has to exist for the rows already stored: 1456 of 1842 dashboard
       jobs have no company, and re-discovering them is not possible for
       postings that have since closed.
    2. `site`, when it is not one of the aggregator boards. The
       per-employer scrapers put the employer there ("Thomson Reuters"),
       and the ATS ones use "Board (Employer)".
    3. The opening words of `company_summary`, which the scorer writes as
       prose starting on the employer's name.

    Returns UNKNOWN_COMPANY rather than None so callers can group on the
    result without a special case; measured 2026-09-02 this identifies 57%
    of dashboard rows, up from the 21% that had the column set.
    """
    def _get(key: str) -> str:
        try:
            value = job[key]
        except (KeyError, IndexError, TypeError):
            return ""
        return (value or "").strip() if isinstance(value, str) else ""

    explicit = _get("company")
    if explicit:
        return explicit

    site = _get("site")
    board = _BOARD_SITE_RE.match(site)
    if board:
        return board.group(1).strip()
    if site and site.lower() not in _AGGREGATOR_SITES:
        return site

    summary = _get("company_summary")
    for pattern in _SUMMARY_COMPANY_RES:
        match = pattern.match(summary)
        if match:
            return match.group(1).strip()

    return UNKNOWN_COMPANY


_SHINGLE_WORD_RE = re.compile(r"[a-z0-9]+")
_SHINGLE_K = 5
# Only the first N words are shingled. Descriptions average ~1000 words and
# this runs over every ad of every multi-ad employer on each dashboard
# render, so the tail is cut to bound that cost; two postings that agree
# across their first 600 words are not going to diverge into different jobs
# after it.
_SHINGLE_MAX_WORDS = 600

# Jaccard over those shingles at which two ads are worth pointing out to a
# human. Measured 2026-09-02 over 1188 randomly sampled same-employer pairs,
# scored against difflib.SequenceMatcher.ratio() -- the same measure
# find_duplicate_groups treats as authoritative at 0.85:
#
#   jaccard   pairs   share that are duplicates by ratio >= 0.85
#     <= 0.7    1093       0%
#        0.8      12      58%
#        0.9      11      81%
#        1.0      72      90%
#
# 0.8 is where findings start existing at all: below it the rate is a flat
# zero across more than a thousand pairs, so a lower bar would produce pure
# noise. Above it the minority that are not true duplicates are employers
# reusing one description across genuinely different roles, which is worth
# a human glance rather than a silent decision -- see NOT_A_DUPLICATE_MARK.
_NEAR_IDENTICAL_JACCARD = 0.8

# This drives a BADGE and nothing else. find_duplicate_groups stays the only
# thing that sets `duplicate_of`, because a job marked duplicate drops out of
# scoring, tailoring and apply entirely, and the 2026-09-02 audit found the
# cases this would get wrong: three Ciena postings differing only by which
# air force base, a Thomson Reuters Principal vs Staff pair, and an iOS and
# an Android graduate programme that scored 6 and 8. All are near-identical
# text. None are duplicates.
NOT_A_DUPLICATE_MARK = True


def description_shingles(text: str) -> frozenset:
    """Set of 5-word shingle hashes over a description's first 600 words.

    Order-independent and immune to a shared boilerplate header, unlike a
    prefix comparison: an employer's standard preamble contributes the same
    shingles to every one of its ads and so cancels out of the Jaccard.
    """
    words = _SHINGLE_WORD_RE.findall((text or "").lower())[:_SHINGLE_MAX_WORDS]
    if len(words) < _SHINGLE_K:
        return frozenset()
    return frozenset(
        hash(" ".join(words[i:i + _SHINGLE_K]))
        for i in range(len(words) - _SHINGLE_K + 1)
    )


def shingle_jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    return (len(a & b) / union) if union else 0.0


def group_near_identical(jobs: list, threshold: float = _NEAR_IDENTICAL_JACCARD) -> dict[str, int]:
    """Map url -> a group number, for ads that read as the same posting.

    Only urls sharing a number with at least one other appear in the result,
    so a url that is absent has nothing to flag.

    Compares pairwise within whatever list it is given. Callers pass ONE
    employer's ads at a time: that keeps the pair count small and means two
    unrelated companies' boilerplate is never compared, which was the flaw
    in the first version of this analysis.
    """
    scored = [(j, description_shingles(
        (j["full_description"] or j["description"]) if not isinstance(j, dict)
        else (j.get("full_description") or j.get("description") or "")
    )) for j in jobs]
    scored = [(j, sh) for j, sh in scored if sh]
    if len(scored) < 2:
        return {}

    parent = list(range(len(scored)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(scored)):
        for k in range(i + 1, len(scored)):
            if find(i) == find(k):
                continue
            if shingle_jaccard(scored[i][1], scored[k][1]) >= threshold:
                parent[find(i)] = find(k)

    clusters: dict[int, list] = {}
    for i, (job, _) in enumerate(scored):
        clusters.setdefault(find(i), []).append(job)

    out: dict[str, int] = {}
    number = 0
    for members in clusters.values():
        if len(members) < 2:
            continue
        number += 1
        for job in members:
            out[job["url"]] = number
    return out


def _register_loc_priority(conn: sqlite3.Connection) -> None:
    """Register the `loc_priority(location)` SQL function used to rank/filter
    jobs by the optional location_focus config (config.load_location_focus).

    With focus disabled/absent, tiers is empty and _location_priority_tier
    always returns 0 -- so `ORDER BY loc_priority(location)` is a harmless
    no-op and callers simply don't add the `< len(tiers)` filter clause.
    """
    focus = load_location_focus()
    tiers = (focus or {}).get("priority", [])

    def _priority(location):
        return _location_priority_tier(location, tiers)

    conn.create_function("loc_priority", 1, _priority)


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Get a thread-local cached SQLite connection with WAL mode enabled.

    Each thread gets its own connection (required for SQLite thread safety).
    Connections are cached and reused within the same thread.

    Args:
        db_path: Override the default DB_PATH. Useful for testing.

    Returns:
        sqlite3.Connection configured with WAL mode and row factory.
    """
    path = str(db_path or DB_PATH)

    if not hasattr(_local, 'connections'):
        _local.connections = {}

    conn = _local.connections.get(path)
    if conn is not None:
        try:
            conn.execute("SELECT 1")
            return conn
        except sqlite3.ProgrammingError:
            pass

    conn = sqlite3.connect(path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.row_factory = sqlite3.Row
    _register_loc_priority(conn)
    _local.connections[path] = conn
    return conn


def close_connection(db_path: Path | str | None = None) -> None:
    """Close the cached connection for the current thread."""
    path = str(db_path or DB_PATH)
    if hasattr(_local, 'connections'):
        conn = _local.connections.pop(path, None)
        if conn is not None:
            conn.close()


def init_db(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Create the full jobs table with all columns from every pipeline stage.

    This is idempotent -- safe to call on every startup. Uses CREATE TABLE IF NOT EXISTS
    so it won't destroy existing data.

    Schema columns by stage:
      - Discovery:  url, title, salary, description, location, site, strategy, discovered_at
      - Enrichment: full_description, application_url, detail_scraped_at, detail_error
      - Scoring:    fit_score, score_reasoning, scored_at
      - Tailoring:  tailored_resume_path, tailored_at, tailor_attempts
      - Cover:      cover_letter_path, cover_letter_at, cover_attempts
      - Apply:      applied_at, apply_status, apply_error, apply_attempts,
                   agent_id, last_attempted_at, apply_duration_ms, apply_task_id,
                   verification_confidence

    Args:
        db_path: Override the default DB_PATH.

    Returns:
        sqlite3.Connection with the schema initialized.
    """
    path = db_path or DB_PATH

    # Ensure parent directory exists
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    conn = get_connection(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            -- Discovery stage (smart_extract / job_search / harvesters)
            url                   TEXT PRIMARY KEY,
            title                 TEXT,
            company               TEXT,
            salary                TEXT,
            description           TEXT,
            location              TEXT,
            site                  TEXT,
            strategy              TEXT,
            opportunity_type      TEXT,
            deadline              TEXT,
            funding_status        TEXT,
            cohort_start          TEXT,
            channel               TEXT,
            discovered_at         TEXT,

            -- Enrichment stage (detail_scraper)
            full_description      TEXT,
            application_url       TEXT,
            detail_scraped_at     TEXT,
            detail_error          TEXT,

            -- Scoring stage (job_scorer)
            fit_score             INTEGER,
            score_reasoning       TEXT,
            scored_at             TEXT,
            company_summary       TEXT,
            company_hook          TEXT,
            gate_reason           TEXT,

            -- Ingest pre-filter (discovery/prefilter.py): a short reason
            -- string when a deterministic rule filtered this row out before
            -- any LLM saw it; NULL means it passed (or predates the filter).
            -- The scoring queue skips any row where this is set. Reversible:
            -- UPDATE jobs SET prefilter_reason = NULL WHERE ...
            prefilter_reason      TEXT,

            -- Discovery-cohort archive (database.archive_discovery_results):
            -- one ISO timestamp stamped on the whole discovery backlog when
            -- the search is restarted, so work-acquisition queries skip it
            -- while every row stays in the DB. Undo = clear this column for
            -- that timestamp; the exact command is written to
            -- ~/.applypilot/last_discovery_archive.txt.
            archived_at           TEXT,

            -- Tailoring stage (resume tailor)
            tailored_resume_path  TEXT,
            tailored_at           TEXT,
            tailor_attempts       INTEGER DEFAULT 0,

            -- Cover letter stage
            cover_letter_path     TEXT,
            cover_letter_at       TEXT,
            cover_attempts        INTEGER DEFAULT 0,
            cover_letter_passed   INTEGER,
            cover_letter_errors   TEXT,

            -- Critic pass (scoring/critic.py) -- a decimal COMPUTED from
            -- discrete extraction findings (bullet counts, header-restating
            -- bullets, JD relevance, duplicate content, unsupported cover
            -- letter claims), unlike fit_score which the scoring LLM
            -- assigns directly as an integer. Set after tailoring (CV-only)
            -- and updated to the CV/letter average once the cover letter's
            -- own critic pass also runs -- see critic.combined_critic_score.
            critic_score          REAL,

            -- Application stage
            applied_at            TEXT,
            apply_status          TEXT,
            apply_error           TEXT,
            apply_attempts        INTEGER DEFAULT 0,
            agent_id              TEXT,
            last_attempted_at     TEXT,
            apply_duration_ms     INTEGER,
            apply_task_id         TEXT,
            verification_confidence TEXT
        )
    """)
    conn.commit()

    # Run migrations for any columns added after initial schema
    ensure_columns(conn)

    # Runs: one row per invocation of a pipeline stage (discover, enrich,
    # score, tailor, apply). Attempts: one row per try at applying to a job,
    # tied to the run that made the attempt. jobs.apply_status stays a mirror
    # of the latest attempt so existing queries keep working.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            stage         TEXT NOT NULL,
            started_at    TEXT NOT NULL,
            ended_at      TEXT,
            status        TEXT NOT NULL DEFAULT 'running',
            config_json   TEXT,
            stats_json    TEXT,
            error         TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            id                       INTEGER PRIMARY KEY AUTOINCREMENT,
            job_url                  TEXT NOT NULL REFERENCES jobs(url),
            run_id                   INTEGER NOT NULL REFERENCES runs(id),
            worker_id                INTEGER,
            status                   TEXT NOT NULL DEFAULT 'in_progress',
            error                    TEXT,
            started_at               TEXT NOT NULL,
            ended_at                 TEXT,
            duration_ms              INTEGER,
            task_id                  TEXT,
            verification_confidence  TEXT,
            session_id               TEXT,
            cost_usd                 REAL
        )
    """)
    # Forward migration for the two columns added after attempts shipped
    # (mirrors the jobs table's ensure_columns pattern, scoped to this table).
    existing_attempt_cols = {row[1] for row in conn.execute("PRAGMA table_info(attempts)").fetchall()}
    for col, dtype in {"session_id": "TEXT", "cost_usd": "REAL"}.items():
        if col not in existing_attempt_cols:
            conn.execute(f"ALTER TABLE attempts ADD COLUMN {col} {dtype}")

    # Per-attempt event timeline: one row per Claude Code stream-json event
    # (tool_use paired with its tool_result, assistant text, the system/init
    # handshake, and the final result). This is what an "expand this attempt"
    # view in a dashboard reads -- attempts.status/error is just the summary.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attempt_events (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id           INTEGER NOT NULL REFERENCES attempts(id),
            seq                  INTEGER NOT NULL,
            ts                   TEXT NOT NULL,
            event_type           TEXT NOT NULL,
            tool_name            TEXT,
            tool_use_id          TEXT,
            parent_tool_use_id   TEXT,
            input_json           TEXT,
            result_json          TEXT,
            text                 TEXT,
            raw_json             TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_stage ON runs(stage)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_attempts_job_url ON attempts(job_url)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_attempts_run_id ON attempts(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_attempts_status ON attempts(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_attempt_events_attempt_seq ON attempt_events(attempt_id, seq)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_attempt_events_tool_use_id ON attempt_events(attempt_id, tool_use_id)")
    conn.commit()

    return conn


# Complete column registry: column_name -> SQL type with optional default.
# This is the single source of truth. Adding a column here is all that's needed
# for it to appear in both new databases and migrated ones.
_ALL_COLUMNS: dict[str, str] = {
    # Discovery
    "url": "TEXT PRIMARY KEY",
    "title": "TEXT",
    "company": "TEXT",
    "salary": "TEXT",
    "description": "TEXT",
    "location": "TEXT",
    "site": "TEXT",
    "strategy": "TEXT",
    "opportunity_type": "TEXT",
    "deadline": "TEXT",
    "funding_status": "TEXT",
    "cohort_start": "TEXT",
    "channel": "TEXT",
    "discovered_at": "TEXT",
    # Enrichment
    "full_description": "TEXT",
    "application_url": "TEXT",
    "detail_scraped_at": "TEXT",
    "detail_error": "TEXT",
    # Scoring
    "fit_score": "INTEGER",
    "score_reasoning": "TEXT",
    "scored_at": "TEXT",
    "company_summary": "TEXT",
    "company_hook": "TEXT",
    "gate_reason": "TEXT",
    # Ingest pre-filter reason (discovery/prefilter.py); NULL = passed / predates it
    "prefilter_reason": "TEXT",
    # Discovery-cohort archive timestamp (database.archive_discovery_results); NULL = live
    "archived_at": "TEXT",
    # Tailoring
    "tailored_resume_path": "TEXT",
    "tailored_at": "TEXT",
    "tailor_attempts": "INTEGER DEFAULT 0",
    # Cover letter
    "cover_letter_path": "TEXT",
    "cover_letter_at": "TEXT",
    "cover_attempts": "INTEGER DEFAULT 0",
    "cover_letter_passed": "INTEGER",
    "cover_letter_errors": "TEXT",
    "critic_score": "REAL",
    # Application
    "applied_at": "TEXT",
    "apply_status": "TEXT",
    "apply_error": "TEXT",
    "apply_attempts": "INTEGER DEFAULT 0",
    "agent_id": "TEXT",
    "last_attempted_at": "TEXT",
    "apply_duration_ms": "INTEGER",
    "apply_task_id": "TEXT",
    "verification_confidence": "TEXT",
    # Deduplication: the same real-world posting frequently gets discovered
    # more than once -- same job scraped from two sites (LinkedIn + Indeed),
    # or re-discovered on a later sweep under a new URL. Set to the
    # canonical job's url when this row is a detected duplicate of it; NULL
    # means either unique or not yet checked. Every stage-selection query
    # (scoring, tailoring, apply) should filter `duplicate_of IS NULL` so a
    # duplicate never gets its own separate tailor/apply cycle.
    "duplicate_of": "TEXT",
    "listing_checked_at": "TEXT",
    # Manual dashboard hide: a permanent "never apply to this" decision,
    # independent of apply_status. Every stage-selection query that acquires
    # work (score/tailor/apply) filters hidden = 0 so a hidden job is never
    # picked up again -- it stays in the DB, viewable via the dashboard's
    # Hidden filter, but the pipeline treats it as inert.
    "hidden": "INTEGER DEFAULT 0",
    "hidden_at": "TEXT",
}


def ensure_columns(conn: sqlite3.Connection | None = None) -> list[str]:
    """Add any missing columns to the jobs table (forward migration).

    Reads the current table schema via PRAGMA table_info and compares against
    the full column registry. Any missing columns are added with ALTER TABLE.

    This makes it safe to upgrade the database from any previous version --
    columns are only added, never removed or renamed.

    Args:
        conn: Database connection. Uses get_connection() if None.

    Returns:
        List of column names that were added (empty if schema was already current).
    """
    if conn is None:
        conn = get_connection()

    existing = {row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    added = []

    for col, dtype in _ALL_COLUMNS.items():
        if col not in existing:
            # PRIMARY KEY columns can't be added via ALTER TABLE, but url
            # is always created with the table itself so this is safe
            if "PRIMARY KEY" in dtype:
                continue
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} {dtype}")
            added.append(col)

    if added:
        conn.commit()

    return added


# ── Deduplication ────────────────────────────────────────────────────────
# The same real-world posting is frequently discovered more than once --
# scraped from two different sites (LinkedIn + Indeed), or re-discovered
# under a new URL on a later sweep. Confirmed live 2026-08-23: "Junior
# Application Software Engineer" at One Big Circle existed as both a
# LinkedIn row and an Indeed row; the Indeed copy was scored, tailored, and
# applied to, while the LinkedIn copy sat unscored -- if it had later
# scored >=8 on its own, the pipeline would have tailored and applied to
# the *same job* a second time with no way to know it already had.

_TITLE_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def _normalize_title(title: str) -> str:
    return _TITLE_NORMALIZE_RE.sub(" ", (title or "").lower()).strip()


def find_duplicate_groups(conn: sqlite3.Connection | None = None,
                          similarity_threshold: float = 0.85) -> list[list[dict]]:
    """Group jobs that are likely the same real-world posting.

    Groups by normalized title first (cheap, high-recall), then within each
    group compares full_description pairwise with difflib -- title alone is
    too weak a signal (many genuinely different postings share a generic
    title like "Software Engineer"), so two jobs only count as duplicates
    if their descriptions are also substantially similar.

    Uses SequenceMatcher.ratio(), NOT quick_ratio(). Confirmed live
    2026-08-23: quick_ratio() is a rough character-multiset upper bound, not
    an actual similarity measure -- it scored two completely unrelated
    "Machine Learning Engineer" postings at 0.634 (comfortably over a 0.6
    threshold) when their real ratio() was 0.009. Grouping by quick_ratio
    at any threshold under ~0.9 produced enormous false-positive clusters
    (18 unrelated "Software Engineer" postings from different companies
    lumped into one "duplicate" group). ratio() is slower (true alignment,
    not an approximation) but correct: the same false-positive pair scores
    0.009, while confirmed true positives score 0.94-1.0.

    Args:
        conn: Database connection. Uses get_connection() if None.
        similarity_threshold: Minimum difflib.SequenceMatcher.ratio() (0-1)
            between two full_description texts to treat them as the same
            posting. 0.85 sits well above the false-positive ceiling (~0.01
            observed) and below confirmed true positives (0.94-1.0), leaving
            room for each site's own HTML-stripping/formatting differences.

    Returns:
        List of duplicate groups, each a list of job dicts (2+ per group)
        sharing enough title + description similarity to be the same
        posting. Does not modify the database.
    """
    import difflib

    if conn is None:
        conn = get_connection()

    rows = conn.execute(
        "SELECT url, title, site, location, full_description, fit_score, "
        "tailored_resume_path, applied_at, discovered_at FROM jobs "
        "WHERE full_description IS NOT NULL"
    ).fetchall()
    jobs = [dict(r) for r in rows]

    by_title: dict[str, list[dict]] = {}
    for j in jobs:
        key = _normalize_title(j["title"])
        if not key:
            continue
        by_title.setdefault(key, []).append(j)

    groups: list[list[dict]] = []
    for title_key, candidates in by_title.items():
        if len(candidates) < 2:
            continue
        # Union-find over this title's candidates by description similarity.
        parent = list(range(len(candidates)))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for i in range(len(candidates)):
            for j in range(i + 1, len(candidates)):
                desc_i = (candidates[i]["full_description"] or "").strip().lower()
                desc_j = (candidates[j]["full_description"] or "").strip().lower()
                if not desc_i or not desc_j:
                    continue
                matcher = difflib.SequenceMatcher(None, desc_i, desc_j)
                # quick_ratio() is a valid *upper bound* on the real ratio()
                # (just not an accurate similarity score on its own -- see
                # the false-positive note above) -- cheap enough to skip the
                # expensive real ratio() computation for obviously-dissimilar
                # pairs without risking a false negative.
                if matcher.quick_ratio() < similarity_threshold:
                    continue
                if matcher.ratio() >= similarity_threshold:
                    ri, rj = find(i), find(j)
                    if ri != rj:
                        parent[ri] = rj

        clusters: dict[int, list[dict]] = {}
        for i, c in enumerate(candidates):
            clusters.setdefault(find(i), []).append(c)
        groups.extend(g for g in clusters.values() if len(g) > 1)

    return groups


def apply_duplicate_marks(conn: sqlite3.Connection | None = None,
                          groups: list[list[dict]] | None = None) -> int:
    """Mark all but one job in each duplicate group with duplicate_of.

    Picks the canonical (kept) job in each group by: already applied > has
    a tailored resume > higher fit_score > earliest discovered_at -- so
    real progress already made on a job is never the one thrown away.

    Args:
        conn: Database connection. Uses get_connection() if None.
        groups: Duplicate groups from find_duplicate_groups(). Computed
            fresh if not given.

    Returns:
        Number of jobs newly marked as duplicates.
    """
    if conn is None:
        conn = get_connection()
    if groups is None:
        groups = find_duplicate_groups(conn)

    def _rank(j: dict) -> tuple:
        return (
            0 if j.get("applied_at") else 1,
            0 if j.get("tailored_resume_path") else 1,
            -(j.get("fit_score") or -1),
            j.get("discovered_at") or "9999",
        )

    marked = 0
    for group in groups:
        ranked = sorted(group, key=_rank)
        canonical = ranked[0]
        for dup in ranked[1:]:
            conn.execute(
                "UPDATE jobs SET duplicate_of = ? WHERE url = ? AND duplicate_of IS NULL",
                (canonical["url"], dup["url"]),
            )
            marked += 1
    conn.commit()
    return marked


# ── Manual hide/unhide ───────────────────────────────────────────────────
# A dashboard-driven "never apply to this" decision, separate from
# apply_status: the job stays in the DB (viewable via the dashboard's
# Hidden filter) but every pipeline acquisition query above skips it.

def hide_job(conn: sqlite3.Connection, url: str) -> bool:
    """Mark a job hidden so it stops showing by default and stops being
    picked up for scoring/tailoring/apply.

    Returns:
        True if a matching job row was found and hidden.
    """
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "UPDATE jobs SET hidden = 1, hidden_at = ? WHERE url = ?", (now, url)
    )
    conn.commit()
    return cursor.rowcount > 0


def unhide_job(conn: sqlite3.Connection, url: str) -> bool:
    """Reverse hide_job() -- the job becomes visible and eligible for the
    pipeline again.

    Returns:
        True if a matching job row was found and unhidden.
    """
    cursor = conn.execute(
        "UPDATE jobs SET hidden = 0, hidden_at = NULL WHERE url = ?", (url,)
    )
    conn.commit()
    return cursor.rowcount > 0


def get_stats(conn: sqlite3.Connection | None = None) -> dict:
    """Return job counts by pipeline stage.

    Provides a snapshot of how many jobs are at each stage, useful for
    dashboard display and pipeline progress tracking.

    Args:
        conn: Database connection. Uses get_connection() if None.

    Returns:
        Dictionary with keys:
            total, by_site, pending_detail, with_description,
            scored, unscored, tailored, untailored_eligible,
            with_cover_letter, applied, score_distribution
    """
    if conn is None:
        conn = get_connection()

    stats: dict = {}

    # Total jobs
    stats["total"] = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    # By site breakdown
    rows = conn.execute(
        "SELECT site, COUNT(*) as cnt FROM jobs GROUP BY site ORDER BY cnt DESC"
    ).fetchall()
    stats["by_site"] = [(row[0], row[1]) for row in rows]

    # Enrichment stage
    stats["pending_detail"] = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE detail_scraped_at IS NULL"
    ).fetchone()[0]

    stats["with_description"] = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE full_description IS NOT NULL"
    ).fetchone()[0]

    stats["detail_errors"] = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE detail_error IS NOT NULL"
    ).fetchone()[0]

    # Scoring stage
    stats["scored"] = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE fit_score IS NOT NULL"
    ).fetchone()[0]

    # "unscored" == what the scorer would actually pick up: excludes rows
    # set aside by the discovery archive or the ingest pre-filter, so this
    # tracks the real scoring queue rather than the raw backlog.
    stats["unscored"] = conn.execute(
        "SELECT COUNT(*) FROM jobs "
        "WHERE full_description IS NOT NULL AND fit_score IS NULL "
        "AND archived_at IS NULL AND prefilter_reason IS NULL "
        "AND duplicate_of IS NULL AND COALESCE(hidden, 0) = 0"
    ).fetchone()[0]
    stats["unscored_raw"] = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE full_description IS NOT NULL AND fit_score IS NULL"
    ).fetchone()[0]

    # Score distribution
    dist_rows = conn.execute(
        "SELECT fit_score, COUNT(*) as cnt FROM jobs "
        "WHERE fit_score IS NOT NULL "
        "GROUP BY fit_score ORDER BY fit_score DESC"
    ).fetchall()
    stats["score_distribution"] = [(row[0], row[1]) for row in dist_rows]

    # Tailoring stage
    stats["tailored"] = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE tailored_resume_path IS NOT NULL"
    ).fetchone()[0]

    stats["untailored_eligible"] = conn.execute(
        "SELECT COUNT(*) FROM jobs "
        "WHERE fit_score >= 7 AND full_description IS NOT NULL "
        "AND tailored_resume_path IS NULL"
    ).fetchone()[0]

    stats["tailor_exhausted"] = conn.execute(
        "SELECT COUNT(*) FROM jobs "
        "WHERE COALESCE(tailor_attempts, 0) >= 5 "
        "AND tailored_resume_path IS NULL"
    ).fetchone()[0]

    # Cover letter stage
    stats["with_cover_letter"] = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE cover_letter_path IS NOT NULL"
    ).fetchone()[0]

    stats["cover_exhausted"] = conn.execute(
        "SELECT COUNT(*) FROM jobs "
        "WHERE COALESCE(cover_attempts, 0) >= 5 "
        "AND (cover_letter_path IS NULL OR cover_letter_path = '')"
    ).fetchone()[0]

    # Application stage
    stats["applied"] = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE applied_at IS NOT NULL"
    ).fetchone()[0]

    stats["apply_errors"] = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE apply_error IS NOT NULL"
    ).fetchone()[0]

    stats["ready_to_apply"] = conn.execute(
        "SELECT COUNT(*) FROM jobs "
        "WHERE tailored_resume_path IS NOT NULL "
        "AND applied_at IS NULL "
        "AND application_url IS NOT NULL"
    ).fetchone()[0]

    stats["hidden"] = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE hidden = 1"
    ).fetchone()[0]

    return stats


def store_jobs(conn: sqlite3.Connection, jobs: list[dict],
               site: str, strategy: str) -> tuple[int, int]:
    """Store discovered jobs, skipping duplicates by URL.

    Args:
        conn: Database connection.
        jobs: List of job dicts with keys: url, title, salary, description, location,
              and optional: company, full_description, application_url, opportunity_type,
              deadline, funding_status, cohort_start, channel.
        site: Source site name (e.g. "RemoteOK", "Dice", "Ashby", "Greenhouse").
        strategy: Extraction strategy used (e.g. "json_ld", "api_response", "direct_ats", "hn_api").

    Returns:
        Tuple of (new_count, duplicate_count).
    """
    now = datetime.now(timezone.utc).isoformat()
    new = 0
    existing = 0

    # Deterministic ingest pre-filter -- runs here, before any LLM call. A
    # tripped job is still stored; prefilter_reason just gets set and the
    # scoring queue skips it. Lazy import to keep database.py free of a
    # discovery-package dependency at module load.
    from scoutpilot.discovery.prefilter import evaluate_prefilter
    from scoutpilot.discovery.cohort import infer_cohort_start
    from scoutpilot.config import load_prefilter_config
    pf_cfg = load_prefilter_config()

    for job in jobs:
        url = job.get("url")
        if not url:
            continue

        full_desc = job.get("full_description")
        detail_scraped_at = now if (full_desc and len(full_desc) > 200) else None
        prefilter_reason = evaluate_prefilter(
            job, pf_cfg, channel=job.get("channel") or strategy
        )
        cohort_start = job.get("cohort_start") or infer_cohort_start(
            job.get("title"), full_desc or job.get("description"), job.get("opportunity_type")
        )

        try:
            conn.execute(
                "INSERT INTO jobs (url, title, company, salary, description, location, site, strategy, "
                "opportunity_type, deadline, funding_status, cohort_start, channel, discovered_at, "
                "full_description, application_url, detail_scraped_at, prefilter_reason) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    url,
                    job.get("title"),
                    job.get("company"),
                    job.get("salary"),
                    job.get("description"),
                    job.get("location"),
                    job.get("site", site),
                    strategy,
                    job.get("opportunity_type"),
                    job.get("deadline"),
                    job.get("funding_status"),
                    cohort_start,
                    job.get("channel", strategy),
                    now,
                    full_desc,
                    job.get("application_url"),
                    detail_scraped_at,
                    prefilter_reason,
                ),
            )
            new += 1
        except sqlite3.IntegrityError:
            existing += 1
            # Re-discovering a job that was archived (search restarted) brings
            # it back into the live set -- it's a current result again. Only
            # if nothing downstream has touched it.
            conn.execute(
                "UPDATE jobs SET archived_at = NULL WHERE url = ? AND archived_at IS NOT NULL "
                "AND tailored_resume_path IS NULL AND applied_at IS NULL",
                (url,),
            )

    conn.commit()
    return new, existing


def get_jobs_by_stage(conn: sqlite3.Connection | None = None,
                      stage: str = "discovered",
                      min_score: int | None = None,
                      limit: int = 100,
                      channel: str | None = None,
                      opp_type: str | None = None,
                      keywords: str | list[str] | None = None,
                      cohort: str | None = None) -> list[dict]:
    """Fetch jobs filtered by pipeline stage.

    Args:
        conn: Database connection. Uses get_connection() if None.
        stage: One of "discovered", "enriched", "scored", "tailored", "applied".
        min_score: Minimum fit_score filter (only relevant for scored+ stages).
        limit: Maximum number of rows to return.
        channel: Filter to a specific channel (e.g. 'direct_ats', 'hacker_news', 'graduate_schemes').
        opp_type: Filter to a specific opportunity type (e.g. 'graduate_scheme', 'funded_training').
        keywords: Optional keyword(s) to match against job title and description (e.g. 'AI, python, signal processing').

    Returns:
        List of job dicts.
    """
    if conn is None:
        conn = get_connection()

    conditions = {
        "discovered": "1=1",
        "pending_detail": "detail_scraped_at IS NULL",
        "enriched": "full_description IS NOT NULL",
        # duplicate_of IS NULL on pending_score/pending_tailor: a detected
        # duplicate of an already-handled posting shouldn't burn a second
        # round of scoring/tailoring LLM calls on the same real job.
        # COALESCE(hidden, 0) = 0 on every acquisition query: a job the user
        # hid from the dashboard is a "never apply to this" decision, so it
        # must never be picked up for scoring/tailoring/apply again.
        "pending_score": (
            "full_description IS NOT NULL AND fit_score IS NULL AND duplicate_of IS NULL "
            "AND COALESCE(hidden, 0) = 0 AND prefilter_reason IS NULL AND archived_at IS NULL"
        ),
        "scored": "fit_score IS NOT NULL",
        "pending_tailor": (
            "fit_score >= ? AND full_description IS NOT NULL "
            "AND tailored_resume_path IS NULL AND duplicate_of IS NULL "
            "AND COALESCE(apply_status, '') != 'listing_closed' AND COALESCE(hidden, 0) = 0 "
            "AND archived_at IS NULL "
            "AND COALESCE(tailor_attempts, 0) < "
            f"{DEFAULTS['max_tailor_attempts']}"
        ),
        "tailored": "tailored_resume_path IS NOT NULL",
        "pending_apply": (
            "tailored_resume_path IS NOT NULL AND applied_at IS NULL "
            "AND application_url IS NOT NULL AND duplicate_of IS NULL "
            "AND COALESCE(apply_status, '') != 'listing_closed' AND COALESCE(hidden, 0) = 0"
        ),
        "applied": "applied_at IS NOT NULL",
    }

    where = conditions.get(stage, "1=1")
    params: list = []

    if stage == "pending_tailor":
        params.append(min_score if min_score is not None else 7)

    if channel:
        where += " AND (channel = ? OR strategy = ? OR site LIKE ?)"
        params.extend([channel, channel, f"%{channel}%"])

    if opp_type:
        where += " AND opportunity_type = ?"
        params.append(opp_type)

    if cohort:
        # "immediate" -> the immediate-start marker; a 4-digit year -> that
        # year's intake (cohort_start "YYYY" or "YYYY-MM", or a deadline in
        # that year); "future" -> anything dated past next year.
        if cohort == "immediate":
            where += " AND cohort_start = 'immediate'"
        elif re.fullmatch(r"20\d\d", str(cohort)):
            where += " AND (cohort_start LIKE ? OR deadline LIKE ?)"
            params.extend([f"{cohort}%", f"%{cohort}%"])
        elif cohort == "future":
            fy = datetime.now(timezone.utc).year + 1
            where += " AND (substr(cohort_start,1,4) > ? OR substr(deadline,1,4) > ?)"
            params.extend([str(fy), str(fy)])

    if keywords:
        if isinstance(keywords, str):
            kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
        else:
            kw_list = list(keywords)
        if kw_list:
            kw_clauses = " OR ".join(["(title LIKE ? OR full_description LIKE ?)" for _ in kw_list])
            where += f" AND ({kw_clauses})"
            for kw in kw_list:
                params.extend([f"%{kw}%", f"%{kw}%"])

    if min_score is not None and "fit_score" not in where and stage in ("scored", "tailored", "applied"):
        where += " AND fit_score >= ?"
        params.append(min_score)

    # Optional location_focus (config.load_location_focus): when enabled,
    # the three "give me work to do next" stages are restricted to jobs
    # matching one of the configured location tiers (e.g. Belfast, then
    # rest of NI, then remote) instead of the full backlog -- a temporary,
    # reversible narrowing that touches no existing rows. loc_priority() is
    # a no-op (always 0) when focus is disabled, so ORDER BY including it
    # never changes behavior in that case.
    order_by = "fit_score DESC NULLS LAST, discovered_at DESC"
    if stage == "pending_score":
        # Prioritize candidate profile domain keywords (AI, Signal Processing, ML, Python, Graduate/Junior)
        order_by = """
            CASE
                WHEN title LIKE '%graduate%' OR title LIKE '%junior%' OR title LIKE '%early career%' OR title LIKE '%intern%' THEN 1
                WHEN title LIKE '%signal%' OR title LIKE '%dsp%' OR title LIKE '%audio%' OR title LIKE '%video%' OR title LIKE '%biosignal%' THEN 2
                WHEN title LIKE '%ai%' OR title LIKE '%machine learning%' OR title LIKE '%ml%' OR title LIKE '%deep learning%' THEN 3
                WHEN title LIKE '%python%' OR title LIKE '%fastapi%' OR title LIKE '%backend%' OR title LIKE '%back-end%' THEN 4
                WHEN title LIKE '%fullstack%' OR title LIKE '%full stack%' OR title LIKE '%full-stack%' OR title LIKE '%software%' OR title LIKE '%developer%' OR title LIKE '%engineer%' THEN 5
                ELSE 6
            END ASC, """ + order_by

    if stage in ("pending_score", "pending_tailor", "pending_apply"):
        focus = load_location_focus()
        tier_count = len((focus or {}).get("priority", []))
        if tier_count:
            where += f" AND loc_priority(location) < {tier_count}"
            order_by = "loc_priority(location) ASC, " + order_by

    query = f"SELECT * FROM jobs WHERE {where} ORDER BY {order_by}"
    if limit > 0:
        query += " LIMIT ?"
        params.append(limit)

    rows = conn.execute(query, params).fetchall()

    # Convert sqlite3.Row objects to dicts
    if rows:
        columns = rows[0].keys()
        return [dict(zip(columns, row)) for row in rows]
    return []


# ── Per-source hit rate & scoring-queue budget ───────────────────────────
# The scorer used to work the backlog in roughly arrival order, so a big
# unscored pile built up behind sources (global startup ATS boards) that
# almost never produce a fit-7 job for this candidate. These two functions
# reorder the queue by each source's *measured* yield instead.

_DOMAIN_RANK_CASES = (
    (("graduate", "junior", "early career", "intern"), 1),
    (("signal", "dsp", "audio", "video", "biosignal"), 2),
    (("ai", "machine learning", "ml", "deep learning"), 3),
    (("python", "fastapi", "backend", "back-end"), 4),
    (("fullstack", "full stack", "full-stack", "software", "developer", "engineer"), 5),
)


def _title_domain_rank(title: str | None) -> int:
    """Same profile-domain ordering get_jobs_by_stage applies in SQL, in
    Python, so scoring_queue can use it as a within-bucket tiebreak."""
    t = (title or "").lower()
    for needles, rank in _DOMAIN_RANK_CASES:
        if any(n in t for n in needles):
            return rank
    return 6


def _url_bucket(url: str, divisor: int) -> int:
    """Stable 0..divisor-1 bucket for a URL (deterministic sampling)."""
    if divisor <= 1:
        return 0
    return int(hashlib.md5(url.encode("utf-8")).hexdigest(), 16) % divisor


def source_hit_rates(conn: sqlite3.Connection | None = None,
                     hit_score: int = 7,
                     min_sample: int = 15) -> dict[str, dict]:
    """Live per-source hit rate: of a source's scored jobs, the share that
    reached ``fit_score >= hit_score``.

    Source is the ``site`` column -- the finest actionable grain (a specific
    board or employer portal), which is what the queue orders on.

    Returns ``{site: {scored, hits, rate, trusted}}`` where ``trusted`` is
    ``scored >= min_sample`` -- below that the rate is too noisy to act on
    and the queue treats the source as unknown rather than high or low.
    """
    if conn is None:
        conn = get_connection()
    rows = conn.execute(
        """
        SELECT COALESCE(site, '?') AS s,
               COUNT(*) AS scored,
               SUM(CASE WHEN fit_score >= ? THEN 1 ELSE 0 END) AS hits
        FROM jobs
        WHERE fit_score IS NOT NULL
        GROUP BY s
        """,
        (hit_score,),
    ).fetchall()
    out: dict[str, dict] = {}
    for r in rows:
        scored = r["scored"] or 0
        hits = r["hits"] or 0
        out[r["s"]] = {
            "scored": scored,
            "hits": hits,
            "rate": (hits / scored) if scored else 0.0,
            "trusted": scored >= min_sample,
        }
    return dict(sorted(out.items(), key=lambda kv: (-kv[1]["rate"], -kv[1]["scored"])))


def scoring_queue(conn: sqlite3.Connection | None = None,
                  limit: int = 0,
                  cfg: dict | None = None) -> list[str]:
    """Ordered list of job URLs to score next, highest-yield source first.

    Ordering: high-yield sources (trusted history, hit rate above ``floor``)
    first, ranked by rate; then unknown sources (too little history); then
    low-yield sources, which are *sampled* -- only ~1 in ``sample_divisor``
    of their pending rows are queued at all -- so the backlog isn't spent
    exhausting a source that doesn't produce, while still feeding it enough
    new data points to keep its rate honest. Within every bucket, the
    candidate's profile-domain title ordering breaks ties.

    Reads only ``url``/``site``/``title`` for the pending rows (never the
    descriptions) so it stays cheap on a large backlog.
    """
    if conn is None:
        conn = get_connection()
    if cfg is None:
        from scoutpilot.config import load_prefilter_config
        cfg = load_prefilter_config()
    q = cfg.get("scoring_queue", {}) or {}
    hit_score = int(q.get("hit_score", 7))
    floor = float(q.get("floor", 0.05))
    min_sample = int(q.get("min_sample", 15))
    divisor = int(q.get("sample_divisor", 6))
    enabled = q.get("enabled", True)

    where = (
        "full_description IS NOT NULL AND fit_score IS NULL AND duplicate_of IS NULL "
        "AND COALESCE(hidden, 0) = 0 AND prefilter_reason IS NULL AND archived_at IS NULL"
    )
    focus = load_location_focus()
    tier_count = len((focus or {}).get("priority", []))
    if tier_count:
        where += f" AND loc_priority(location) < {tier_count}"

    rows = conn.execute(
        f"SELECT url, COALESCE(site, '?') AS site, title, cohort_start, deadline, discovered_at "
        f"FROM jobs WHERE {where} ORDER BY discovered_at DESC"
    ).fetchall()
    if not rows:
        return []

    if not enabled:
        urls = [r["url"] for r in rows]
        return urls[:limit] if limit and limit > 0 else urls

    from scoutpilot.discovery.cohort import cohort_rank

    rates = source_hit_rates(conn, hit_score=hit_score, min_sample=min_sample)

    ranked: list[tuple] = []
    for i, r in enumerate(rows):
        info = rates.get(r["site"], {"rate": 0.0, "trusted": False})
        if info["trusted"] and info["rate"] > floor:
            bucket = 0  # high yield
        elif not info["trusted"]:
            bucket = 1  # unknown
        else:
            bucket = 2  # low yield -> sampled
            if _url_bucket(r["url"], divisor) != 0:
                continue
        c_rank = cohort_rank(r["cohort_start"], r["deadline"])
        ranked.append(
            ((bucket, c_rank, -info["rate"], _title_domain_rank(r["title"]), i), r["url"])
        )

    ranked.sort(key=lambda t: t[0])
    urls = [u for _, u in ranked]
    return urls[:limit] if limit and limit > 0 else urls


_ARCHIVE_NOTE_PATH = APP_DIR / "last_discovery_archive.txt"


def archive_discovery_results(conn: sqlite3.Connection | None = None,
                              note_path: Path | str | None = None) -> dict:
    """Set `archived_at` to one timestamp on the whole live discovery
    backlog, so a fresh search starts clean without those rows competing
    for scoring budget. Nothing is deleted.

    Scope: rows not already archived, not tailored, not applied -- pipeline
    work already in flight and all applied/tailored history are left
    exactly as they were. Work-acquisition queries (pending_score,
    pending_tailor, scoring_queue) filter `archived_at IS NULL`; the
    dashboard and stats still see the rows.

    Writes the one-line undo command to `note_path`
    (~/.applypilot/last_discovery_archive.txt by default).

    Returns {"archived": int, "timestamp": str, "note_path": str}.
    """
    if conn is None:
        conn = get_connection()
    ts = datetime.now(timezone.utc).isoformat()
    target = "archived_at IS NULL AND tailored_resume_path IS NULL AND applied_at IS NULL"
    cur = conn.execute(f"UPDATE jobs SET archived_at = ? WHERE {target}", (ts,))
    conn.commit()
    n = cur.rowcount

    path = Path(note_path) if note_path else _ARCHIVE_NOTE_PATH
    path.write_text(
        f"# Discovery backlog archived {ts}\n"
        f"# {n} rows marked (not tailored, not applied). Nothing was deleted.\n"
        f"# To restore them, run this against {DB_PATH}:\n"
        f"UPDATE jobs SET archived_at = NULL WHERE archived_at = '{ts}';\n",
        encoding="utf-8",
    )
    return {"archived": n, "timestamp": ts, "note_path": str(path)}


def unarchive_discovery_results(conn: sqlite3.Connection | None = None,
                                timestamp: str | None = None) -> int:
    """Reverse archive_discovery_results. With `timestamp`, restores just
    that batch; without, restores every archived row. Returns rows restored."""
    if conn is None:
        conn = get_connection()
    if timestamp:
        cur = conn.execute("UPDATE jobs SET archived_at = NULL WHERE archived_at = ?", (timestamp,))
    else:
        cur = conn.execute("UPDATE jobs SET archived_at = NULL WHERE archived_at IS NOT NULL")
    conn.commit()
    return cur.rowcount


def refresh_prefilter(conn: sqlite3.Connection | None = None) -> dict:
    """Re-run the ingest pre-filter over the live, unscored backlog and
    rewrite each row's prefilter_reason from the current config/rules.

    Only touches rows that are live (archived_at IS NULL), unscored, not
    tailored and not applied -- rewriting a computed marker, never real
    data. Use after changing config/prefilter.yaml or the rule code.

    Returns {"checked": int, "now_filtered": int, "now_cleared": int,
    "changed": int}.
    """
    if conn is None:
        conn = get_connection()
    from scoutpilot.discovery.prefilter import evaluate_prefilter
    from scoutpilot.config import load_prefilter_config
    cfg = load_prefilter_config()

    rows = conn.execute(
        "SELECT url, title, location, description, full_description, channel, strategy, "
        "prefilter_reason FROM jobs "
        "WHERE archived_at IS NULL AND fit_score IS NULL "
        "AND tailored_resume_path IS NULL AND applied_at IS NULL"
    ).fetchall()

    now_filtered = now_cleared = changed = 0
    for r in rows:
        job = {
            "title": r["title"], "location": r["location"],
            "description": r["description"], "full_description": r["full_description"],
            "channel": r["channel"], "strategy": r["strategy"],
        }
        new = evaluate_prefilter(job, cfg)
        old = r["prefilter_reason"]
        if new == old:
            continue
        changed += 1
        if new and not old:
            now_filtered += 1
        elif old and not new:
            now_cleared += 1
        conn.execute("UPDATE jobs SET prefilter_reason = ? WHERE url = ?", (new, r["url"]))
    conn.commit()
    return {
        "checked": len(rows), "now_filtered": now_filtered,
        "now_cleared": now_cleared, "changed": changed,
    }


def clean_non_tech_jobs(conn: sqlite3.Connection | None = None) -> int:
    """Mark irrelevant, non-engineering discovered jobs as hidden (hidden = 1) to clean scoring queues.

    Returns:
        Number of jobs marked as hidden.
    """
    from scoutpilot.discovery.direct_ats import is_relevant_tech_role
    if conn is None:
        conn = get_connection()

    unscored_jobs = conn.execute(
        "SELECT url, title, full_description FROM jobs WHERE fit_score IS NULL AND COALESCE(hidden, 0) = 0"
    ).fetchall()

    to_hide = []
    for job in unscored_jobs:
        url = job[0]
        title = job[1] or ""
        desc = job[2] or ""
        if not is_relevant_tech_role(title, desc):
            to_hide.append(url)

    if to_hide:
        conn.executemany("UPDATE jobs SET hidden = 1, hidden_at = datetime('now') WHERE url = ?", [(u,) for u in to_hide])
        conn.commit()

    return len(to_hide)


# ---------------------------------------------------------------------------
# Runs: one row per invocation of a pipeline stage
# ---------------------------------------------------------------------------

def start_run(conn: sqlite3.Connection, stage: str, config: dict | None = None) -> int:
    """Record the start of one pipeline stage invocation.

    Args:
        conn: Database connection.
        stage: One of "discover", "enrich", "score", "tailor", "apply".
        config: Snapshot of the config/kwargs this invocation ran with.

    Returns:
        The new run's id.
    """
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO runs (stage, started_at, status, config_json) VALUES (?, ?, 'running', ?)",
        (stage, now, json.dumps(config, default=str) if config is not None else None),
    )
    conn.commit()
    return cur.lastrowid


def end_run(conn: sqlite3.Connection, run_id: int, status: str = "completed",
           stats: dict | None = None, error: str | None = None) -> None:
    """Record the end of a pipeline stage invocation.

    Args:
        conn: Database connection.
        run_id: Id returned by start_run().
        status: "completed", "partial", "failed", or "interrupted".
        stats: Result stats dict for this run (json-encoded).
        error: Error message if the run failed.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE runs SET ended_at = ?, status = ?, stats_json = ?, error = ? WHERE id = ?",
        (now, status, json.dumps(stats, default=str) if stats is not None else None, error, run_id),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Attempts: one row per try at applying to a job, tied to a run
# ---------------------------------------------------------------------------

def create_attempt(conn: sqlite3.Connection, job_url: str, run_id: int,
                   worker_id: int | None = None) -> int:
    """Start a new apply attempt for a job, tied to a run.

    Also mirrors the in-progress state onto jobs.apply_status so downstream
    queries that only know about the jobs table keep working. Caller is
    responsible for the surrounding transaction/commit (acquire_job runs
    this inside a BEGIN IMMEDIATE to keep it atomic with job selection).

    Args:
        conn: Database connection.
        job_url: The job being attempted (jobs.url).
        run_id: The apply run this attempt belongs to.
        worker_id: Numeric worker claiming this attempt.

    Returns:
        The new attempt's id.
    """
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO attempts (job_url, run_id, worker_id, status, started_at) "
        "VALUES (?, ?, ?, 'in_progress', ?)",
        (job_url, run_id, worker_id, now),
    )
    conn.execute("""
        UPDATE jobs SET apply_status = 'in_progress',
                       agent_id = ?,
                       last_attempted_at = ?
        WHERE url = ?
    """, (f"worker-{worker_id}" if worker_id is not None else None, now, job_url))
    return cur.lastrowid


def finish_attempt(conn: sqlite3.Connection, attempt_id: int, status: str,
                   error: str | None = None, duration_ms: int | None = None,
                   task_id: str | None = None,
                   verification_confidence: str | None = None,
                   apply_attempts: int | None = None) -> None:
    """Record the outcome of an apply attempt and mirror it onto jobs.

    Args:
        conn: Database connection.
        attempt_id: Id returned by create_attempt().
        status: "applied", "failed", "needs_review", "skipped", "manual", etc.
        error: Failure reason, if any.
        duration_ms: Wall-clock duration of the attempt.
        task_id: Claude Code task id, if any.
        verification_confidence: Verification confidence label, if any.
        apply_attempts: New value for jobs.apply_attempts (caller computes
            this so permanent-failure semantics stay in one place).
    """
    row = conn.execute("SELECT job_url FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
    if row is None:
        return
    job_url = row["job_url"]
    now = datetime.now(timezone.utc).isoformat()

    conn.execute("""
        UPDATE attempts SET status = ?, error = ?, ended_at = ?, duration_ms = ?,
                            task_id = ?, verification_confidence = ?
        WHERE id = ?
    """, (status, error, now, duration_ms, task_id, verification_confidence, attempt_id))

    applied_at = now if status == "applied" else None
    conn.execute("""
        UPDATE jobs SET apply_status = ?,
                       apply_error = ?,
                       agent_id = NULL,
                       apply_duration_ms = ?,
                       apply_task_id = ?,
                       verification_confidence = ?,
                       applied_at = COALESCE(?, applied_at),
                       apply_attempts = COALESCE(?, apply_attempts)
        WHERE url = ?
    """, (status, error, duration_ms, task_id, verification_confidence,
         applied_at, apply_attempts, job_url))
    conn.commit()


def recover_orphaned_attempts(conn: sqlite3.Connection | None = None) -> list[str]:
    """Mark attempts left 'in_progress' by a crashed worker as needs_review.

    Call this once at launcher startup, before any new attempts are
    acquired. An attempt stuck in_progress means the worker that owned it
    died without reporting a result (process crash, killed, machine reset)
    -- there's no way to know what state the application was left in, so it
    needs a human to check rather than being silently retried or lost.

    Args:
        conn: Database connection. Uses get_connection() if None.

    Returns:
        List of job URLs that were recovered.
    """
    if conn is None:
        conn = get_connection()

    now = datetime.now(timezone.utc).isoformat()
    orphans = conn.execute(
        "SELECT id, job_url, run_id FROM attempts WHERE status = 'in_progress'"
    ).fetchall()

    for row in orphans:
        conn.execute("""
            UPDATE attempts SET status = 'needs_review', ended_at = ?,
                                error = COALESCE(error, 'orphaned: worker never reported back')
            WHERE id = ?
        """, (now, row["id"]))
        conn.execute(
            "UPDATE jobs SET apply_status = 'needs_review', agent_id = NULL WHERE url = ?",
            (row["job_url"],),
        )

    orphan_run_ids = {row["run_id"] for row in orphans if row["run_id"] is not None}
    for run_id in orphan_run_ids:
        run = conn.execute("SELECT ended_at FROM runs WHERE id = ?", (run_id,)).fetchone()
        if run and run["ended_at"] is None:
            conn.execute(
                "UPDATE runs SET ended_at = ?, status = 'interrupted' WHERE id = ?",
                (now, run_id),
            )

    conn.commit()
    return [row["job_url"] for row in orphans]


# ---------------------------------------------------------------------------
# Attempt event timeline: per-tool-call detail for an attempt, for the
# "expand this attempt" view. attempts.status/error is just the summary --
# this is where the actual command-by-command history lives.
# ---------------------------------------------------------------------------

def set_attempt_session(conn: sqlite3.Connection, attempt_id: int, session_id: str) -> None:
    """Record the Claude Code session id for an attempt (from the init event)."""
    conn.execute("UPDATE attempts SET session_id = ? WHERE id = ?", (session_id, attempt_id))
    conn.commit()


def set_attempt_cost(conn: sqlite3.Connection, attempt_id: int, cost_usd: float) -> None:
    """Record the total cost for an attempt (from the final result event)."""
    conn.execute("UPDATE attempts SET cost_usd = ? WHERE id = ?", (cost_usd, attempt_id))
    conn.commit()


def log_event(conn: sqlite3.Connection, attempt_id: int, seq: int, event_type: str, *,
              tool_name: str | None = None, tool_use_id: str | None = None,
              parent_tool_use_id: str | None = None, input_data=None,
              text: str | None = None, raw=None) -> int:
    """Persist one Claude Code stream-json event onto an attempt's timeline.

    Caller controls commits (the launcher batches one commit per stream-json
    line so a crash mid-attempt still leaves everything up to that point
    queryable, matching the orphan-recovery story).

    Args:
        conn: Database connection.
        attempt_id: The attempt this event belongs to.
        seq: Monotonically increasing sequence number within the attempt.
        event_type: "system_init", "text", "tool_use", "tool_result", or "result".
        tool_name: MCP/tool name, for tool_use events.
        tool_use_id: The tool_use block's id (used to pair with attach_tool_result).
        parent_tool_use_id: Non-null means this event came from inside a
            subagent (Task tool) invocation nested under that parent call --
            a dashboard should nest these under the parent tool_use.
        input_data: Full tool input, for tool_use events. Stored verbatim
            (e.g. the literal Bash command string), not paraphrased.
        text: Assistant text content, for text events.
        raw: The full raw event/block as received, for fidelity.

    Returns:
        The new event row's id.
    """
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute("""
        INSERT INTO attempt_events (
            attempt_id, seq, ts, event_type, tool_name, tool_use_id,
            parent_tool_use_id, input_json, text, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        attempt_id, seq, now, event_type, tool_name, tool_use_id, parent_tool_use_id,
        json.dumps(input_data, default=str) if input_data is not None else None,
        text,
        json.dumps(raw, default=str),
    ))
    return cur.lastrowid


def attach_tool_result(conn: sqlite3.Connection, attempt_id: int, tool_use_id: str | None,
                       result_data, raw) -> bool:
    """Pair a tool_result event onto its matching tool_use event row.

    Falls back to inserting a standalone tool_result event (with the next
    seq in the attempt) if no matching tool_use row is found, so nothing is
    silently dropped.

    Returns:
        True if an existing tool_use row was updated in place, False if a
        standalone tool_result event was inserted instead.
    """
    if tool_use_id:
        row = conn.execute("""
            SELECT id FROM attempt_events
            WHERE attempt_id = ? AND tool_use_id = ? AND event_type = 'tool_use'
            ORDER BY id DESC LIMIT 1
        """, (attempt_id, tool_use_id)).fetchone()
        if row:
            conn.execute(
                "UPDATE attempt_events SET result_json = ? WHERE id = ?",
                (json.dumps(result_data, default=str), row["id"]),
            )
            return True

    seq_row = conn.execute(
        "SELECT COALESCE(MAX(seq), 0) + 1 FROM attempt_events WHERE attempt_id = ?",
        (attempt_id,),
    ).fetchone()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO attempt_events (attempt_id, seq, ts, event_type, tool_use_id, result_json, raw_json)
        VALUES (?, ?, ?, 'tool_result', ?, ?, ?)
    """, (
        attempt_id, seq_row[0], now, tool_use_id,
        json.dumps(result_data, default=str), json.dumps(raw, default=str),
    ))
    return False
