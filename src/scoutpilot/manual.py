"""Manually add a single job posting by URL and run it through
enrichment + scoring, so it shows up on the dashboard like any other job.

Used by both `scoutpilot add <url>` and the dashboard's "Add job by URL"
box.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from scoutpilot.database import get_connection, init_db

log = logging.getLogger(__name__)

MANUAL_CHANNEL = "manual"


def _insert_stub(conn, url: str) -> str:
    """Insert a bare row for `url` if absent. Returns 'new' | 'existing' |
    'revived' (was archived, now live again)."""
    now = datetime.now(timezone.utc).isoformat()
    row = conn.execute(
        "SELECT archived_at, fit_score FROM jobs WHERE url = ?", (url,)
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO jobs (url, title, site, strategy, channel, discovered_at) "
            "VALUES (?, ?, 'Manual', ?, ?, ?)",
            (url, url, MANUAL_CHANNEL, MANUAL_CHANNEL, now),
        )
        conn.commit()
        return "new"
    if row["archived_at"] is not None:
        conn.execute(
            "UPDATE jobs SET archived_at = NULL, prefilter_reason = NULL WHERE url = ?", (url,)
        )
        conn.commit()
        return "revived"
    return "existing"


def add_and_process_job(url: str, rescore: bool = True) -> dict:
    """Add `url`, enrich it, score it. Returns a summary dict:
    {url, added, enrich_status, fit_score, gate_reason, reasoning}.

    Blocking -- enrichment is a fetch and scoring is one LLM call. The
    dashboard runs this in a background thread.
    """
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("url must start with http:// or https://")

    conn = init_db()
    added = _insert_stub(conn, url)

    # Clear any pre-filter mark -- a manually added job is an explicit
    # "score this" and should never be skipped as queue noise.
    conn.execute("UPDATE jobs SET prefilter_reason = NULL WHERE url = ?", (url,))
    conn.commit()

    # --- enrich (unless it already has a description) ---
    row = conn.execute(
        "SELECT full_description, title FROM jobs WHERE url = ?", (url,)
    ).fetchone()
    enrich_status = "already_enriched"
    if not row["full_description"]:
        from scoutpilot.enrichment.detail import scrape_site_batch
        stats = scrape_site_batch(conn, "Manual", [(url, row["title"])], delay=0.0)
        if stats.get("ok"):
            enrich_status = "ok"
        elif stats.get("partial"):
            enrich_status = "partial"
        else:
            enrich_status = "error"

    # --- score ---
    row = conn.execute(
        "SELECT * FROM jobs WHERE url = ?", (url,)
    ).fetchone()
    if not row["full_description"]:
        return {
            "url": url, "added": added, "enrich_status": enrich_status,
            "fit_score": None, "gate_reason": None,
            "reasoning": "Could not fetch a job description for this URL.",
        }

    if row["fit_score"] is not None and not rescore:
        return {
            "url": url, "added": added, "enrich_status": enrich_status,
            "fit_score": row["fit_score"], "gate_reason": row["gate_reason"],
            "reasoning": (row["score_reasoning"] or "").strip(),
        }

    from scoutpilot.config import RESUME_PATH, load_profile
    from scoutpilot.scoring.scorer import score_job

    resume_text = RESUME_PATH.read_text(encoding="utf-8")
    profile = load_profile()
    job = dict(zip(row.keys(), row))
    result = score_job(resume_text, job, profile)

    conn.execute(
        "UPDATE jobs SET fit_score = ?, score_reasoning = ?, scored_at = ?, "
        "company_summary = ?, company_hook = ?, gate_reason = ? WHERE url = ?",
        (
            result["score"],
            f"{result['keywords']}\n{result['reasoning']}",
            datetime.now(timezone.utc).isoformat(),
            result.get("company_summary"), result.get("company_hook"),
            result.get("gate_reason"), url,
        ),
    )
    conn.commit()

    return {
        "url": url, "added": added, "enrich_status": enrich_status,
        "fit_score": result["score"], "gate_reason": result.get("gate_reason"),
        "reasoning": result["reasoning"],
    }
