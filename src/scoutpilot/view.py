"""ScoutPilot HTML Dashboard Generator.

Generates an interactive, self-contained HTML dashboard with:
  - High-level pipeline metrics (discovered, scored, tailored, cover letters, applied)
  - Score distribution & source site breakdowns
  - Full multi-sentence LLM Fit Reasoning (no truncation) and ATS keyword chips
  - Company Context & Cover Letter Hook highlights
  - Direct local file links to tailored CVs (PDF/TXT) and cover letters (PDF/TXT)
  - Real-time application status tracking (applied, ready, in_progress, failed)
  - Multi-dimensional filtering (by score tier, by application status, by site, search text)
  - In-page CV/cover-letter preview modal

Served live via `serve_dashboard()` (a local HTTP server that regenerates
from the DB on every request) so the in-page Refresh button reflects the
DB's actual current state -- a plain file:// snapshot can't do that: reloading
a static file just re-displays the same stale content from whenever it was
last written, no matter how many times you click refresh or reload.
"""

from __future__ import annotations

import logging
import platform
import subprocess
import threading
import time
import webbrowser
from html import escape
from pathlib import Path

from rich.console import Console

from scoutpilot.config import APP_DIR, COVER_LETTER_DIR, DB_PATH, TAILORED_DIR
from scoutpilot.database import classify_location, get_connection

console = Console()
log = logging.getLogger(__name__)

# Directories serve_dashboard() is willing to stream files from via /files --
# CV/cover-letter assets only, not an arbitrary local-file read.
ASSET_SERVE_ROOTS: tuple[Path, ...] = (TAILORED_DIR, COVER_LETTER_DIR)


# ---------------------------------------------------------------------------
# On-demand single-job tailor + cover letter (dashboard "Tailor" button)
#
# Runs in a background thread per job so the POST that kicks it off returns
# immediately -- an LLM tailor+cover-letter round trip can take a minute or
# two, far past any reasonable HTTP timeout. The page polls /api/tailor-status
# for progress instead of holding the connection open.
# ---------------------------------------------------------------------------

_tailor_jobs: dict[str, dict] = {}
_tailor_jobs_lock = threading.Lock()


def _set_tailor_status(url: str, **fields) -> None:
    with _tailor_jobs_lock:
        state = _tailor_jobs.setdefault(url, {})
        state.update(fields)


def get_tailor_status(url: str) -> dict:
    """Current on-demand tailor-job status for a URL, or {"status": "idle"}
    if none has ever been started for it in this server process."""
    with _tailor_jobs_lock:
        state = _tailor_jobs.get(url)
        return dict(state) if state else {"status": "idle"}


def _on_demand_retries() -> int:
    """Retry budget for a single on-demand click.

    A batch run defaults to 1 retry on a local provider so hundreds of jobs
    don't each burn multiple LLM passes. Here it's one job and the user is
    actively waiting, so a couple more attempts (each ~30-60s locally) is
    worth it for a better chance of passing validation on the first click.
    """
    from scoutpilot.llm import is_local_provider
    return 2 if is_local_provider() else 3


def _error_summary(errors: list | None) -> str:
    if not errors:
        return ""
    return " -- " + "; ".join(str(e)[:160] for e in errors[:2])


_TAILOR_SUCCESS_STATUSES = {
    "approved", "approved_with_judge_warning", "approved_unquantified_fallback",
}


def _run_cover_letter(url: str) -> None:
    """Generate the cover letter for one job, reporting into the job's
    `cover` field only. Safe to call on its own -- this is what the page's
    cover-letter retry does when the CV is already on disk."""
    from scoutpilot.scoring.cover_letter import cover_letter_one

    _set_tailor_status(url, cover="running", stage="cover_letter", cover_error=None)
    try:
        result = cover_letter_one(url, max_retries=_on_demand_retries())
    except Exception as exc:  # noqa: BLE001 -- report to the page, don't crash the thread
        log.exception("On-demand cover letter failed for %s", url)
        _set_tailor_status(url, cover="error", stage=None, cover_error=str(exc))
        return

    if result["status"] != "generated":
        _set_tailor_status(
            url, cover="error", stage=None,
            cover_error=f"Cover letter failed ({result['status']})"
                        f"{_error_summary(result.get('errors'))}",
        )
        return
    _set_tailor_status(url, cover="done", stage=None, cover_error=None)


def _run_tailor_and_cover(url: str) -> None:
    """Background-thread target: tailor the CV, then generate the cover
    letter, reporting the two outcomes SEPARATELY.

    They used to share one status field, and a cover-letter failure set it
    to "error" for the whole job. The page only reloads on success, so a
    blocked cover letter meant the successfully tailored CV never appeared
    on the card at all -- it was on disk and in the database the whole time,
    with nothing on screen to say so. The two artefacts are independent
    (the CV is useful without a letter, and `cover_letter_one` can be run
    again on its own against the CV that already exists), so they now report
    independently: `cv` and `cover` each settle on their own, and the
    overall `status` is an error only when the CV itself failed.
    """
    from scoutpilot.scoring.tailor import tailor_one

    _set_tailor_status(
        url, status="running", stage="tailoring",
        cv="running", cover="pending", error=None, cv_error=None, cover_error=None,
    )
    try:
        tailor_result = tailor_one(url, max_retries=_on_demand_retries())
    except Exception as exc:  # noqa: BLE001 -- report to the page, don't crash the thread
        log.exception("On-demand tailoring failed for %s", url)
        _set_tailor_status(url, status="error", stage=None, cv="error",
                           cv_error=str(exc), error=str(exc), cover="skipped")
        return

    if tailor_result["status"] not in _TAILOR_SUCCESS_STATUSES:
        message = (f"Tailoring failed ({tailor_result['status']})"
                   f"{_error_summary(tailor_result.get('errors'))}")
        _set_tailor_status(url, status="error", stage="tailoring", cv="error",
                           cv_error=message, error=message, cover="skipped")
        return

    # The CV is done and on disk from here on. Nothing below may set the
    # overall status back to "error" -- the page needs to be able to show it.
    _set_tailor_status(url, cv="done", cv_error=None, status="running")
    _run_cover_letter(url)
    _set_tailor_status(url, status="done", stage=None)


def _reveal_in_file_manager(path: Path) -> None:
    """Open the OS file manager with `path` pre-selected.

    Lets the user grab a tailored CV or cover letter straight off disk to
    attach it to a manual application on a portal the AI couldn't submit
    through. No shell=True and no string interpolation into a shell command
    -- each arg is passed straight to the OS process, so this is safe even
    though `path` ultimately comes from a browser request (still validated
    against ASSET_SERVE_ROOTS by the caller before this runs).
    """
    system = platform.system()
    if system == "Windows":
        subprocess.run(["explorer", f"/select,{path}"])
    elif system == "Darwin":
        subprocess.run(["open", "-R", str(path)])
    else:
        subprocess.run(["xdg-open", str(path.parent)])


def generate_dashboard(output_path: str | None = None, serve_base_url: str | None = None) -> str:
    """Generate an HTML dashboard of all jobs with fit scores, tailored assets, and apply statuses.

    Args:
        output_path: Where to write the HTML file. Defaults to ~/.applypilot/dashboard.html.
        serve_base_url: When set (e.g. "http://127.0.0.1:8765" from
            serve_dashboard()), CV/cover-letter asset links point at
            `{serve_base_url}/files?path=...` instead of a `file://` URI.
            Needed because a page served over http:// linking or
            iframe-embedding a `file://` resource is a cross-scheme
            navigation browsers block outright -- harmless when the
            dashboard itself is also a `file://` page (the default, None),
            broken once it's served live.

    Returns:
        Absolute path to the generated HTML file.
    """
    out = Path(output_path) if output_path else APP_DIR / "dashboard.html"
    conn = get_connection()

    # --- Summary Metrics ---
    total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    with_desc = conn.execute("SELECT COUNT(*) FROM jobs WHERE full_description IS NOT NULL").fetchone()[0]
    scored = conn.execute("SELECT COUNT(*) FROM jobs WHERE fit_score IS NOT NULL").fetchone()[0]
    high_fit = conn.execute("SELECT COUNT(*) FROM jobs WHERE fit_score >= 7").fetchone()[0]
    tailored = conn.execute("SELECT COUNT(*) FROM jobs WHERE tailored_resume_path IS NOT NULL").fetchone()[0]
    with_cl = conn.execute("SELECT COUNT(*) FROM jobs WHERE cover_letter_path IS NOT NULL").fetchone()[0]
    applied = conn.execute("SELECT COUNT(*) FROM jobs WHERE applied_at IS NOT NULL OR apply_status = 'applied'").fetchone()[0]
    unavailable = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE apply_status IN ('listing_closed', 'manual')"
    ).fetchone()[0]
    ready_to_apply = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE tailored_resume_path IS NOT NULL AND applied_at IS NULL AND application_url IS NOT NULL"
    ).fetchone()[0]
    in_progress = conn.execute("SELECT COUNT(*) FROM jobs WHERE apply_status = 'in_progress'").fetchone()[0]
    failed_apply = conn.execute("SELECT COUNT(*) FROM jobs WHERE apply_status IN ('failed', 'needs_review')").fetchone()[0]
    hidden_count = conn.execute("SELECT COUNT(*) FROM jobs WHERE hidden = 1").fetchone()[0]

    # --- Score Distribution ---
    score_dist: dict[int, int] = {}
    if scored:
        rows = conn.execute(
            "SELECT fit_score, COUNT(*) FROM jobs "
            "WHERE fit_score IS NOT NULL "
            "GROUP BY fit_score ORDER BY fit_score DESC"
        ).fetchall()
        for r in rows:
            score_dist[r[0]] = r[1]

    # --- Site Stats ---
    site_stats = conn.execute("""
        SELECT site,
               COUNT(*) as total,
               SUM(CASE WHEN fit_score >= 7 THEN 1 ELSE 0 END) as high_fit,
               SUM(CASE WHEN fit_score BETWEEN 5 AND 6 THEN 1 ELSE 0 END) as mid_fit,
               SUM(CASE WHEN fit_score < 5 AND fit_score IS NOT NULL THEN 1 ELSE 0 END) as low_fit,
               SUM(CASE WHEN fit_score IS NULL THEN 1 ELSE 0 END) as unscored,
               ROUND(AVG(fit_score), 1) as avg_score
        FROM jobs GROUP BY site ORDER BY high_fit DESC, total DESC
    """).fetchall()

    # --- All Scored Jobs ---
    jobs = conn.execute("""
        SELECT url, title, salary, description, location, site, strategy,
               full_description, application_url, detail_error,
               fit_score, score_reasoning, company_summary, company_hook, gate_reason, critic_score,
               tailored_resume_path, tailored_at, tailor_attempts,
               cover_letter_path, cover_letter_at, cover_attempts,
               applied_at, apply_status, apply_error, apply_attempts,
               last_attempted_at, verification_confidence, hidden, discovered_at
        FROM jobs
        WHERE fit_score IS NOT NULL OR tailored_resume_path IS NOT NULL
        ORDER BY fit_score DESC, site, title
    """).fetchall()

    # Place filter: classify every job's location up front (Belfast/NI/Remote
    # tiers when location_focus is configured, else a plain Remote/Other
    # split) and tally counts for the filter buttons below.
    from collections import Counter
    from scoutpilot.config import load_location_focus

    # Employer for every job, and -- within each employer that has more than
    # one ad -- which of those ads read as the same posting.
    #
    # The `company` column is set on only 21% of these rows (see
    # database.derive_company for why), so grouping has to derive it. The
    # near-identical marks are advisory ONLY: they put a badge on the card
    # and change nothing about which jobs the pipeline will act on, because
    # employers demonstrably reuse one description across genuinely
    # different roles and demoting those would drop real postings.
    from scoutpilot.database import UNKNOWN_COMPANY, derive_company, group_near_identical

    # Emitted into the page so the JS knows whether /api/search exists.
    server_search_flag = "true" if serve_base_url else "false"

    company_labels = {j["url"]: derive_company(j) for j in jobs}
    company_counts = Counter(company_labels.values())

    jobs_by_company: dict[str, list] = {}
    for j in jobs:
        jobs_by_company.setdefault(company_labels[j["url"]], []).append(j)
    dup_marks: dict[str, int] = {}
    for name, group in jobs_by_company.items():
        # Never across the unknown bucket: it is not an employer, it is
        # every job whose employer could not be recovered, so comparing
        # inside it would be exactly the cross-company comparison this is
        # scoped to avoid.
        if name == UNKNOWN_COMPANY or len(group) < 2:
            continue
        for url, mark in group_near_identical(group).items():
            dup_marks[url] = mark

    dup_group_sizes = Counter(dup_marks.values())

    place_labels = {j["url"]: classify_location(j["location"]) for j in jobs}
    place_counts = Counter(place_labels.values())
    focus_cfg = load_location_focus()
    tier_labels = [t[0] for t in (focus_cfg or {}).get("priority", [])]
    ordered_place_labels = [l for l in tier_labels if l in place_counts] + sorted(
        (l for l in place_counts if l not in tier_labels),
        key=lambda l: -place_counts[l],
    )
    # Employers ordered by ad count: the ones with several ads are exactly
    # the ones worth grouping, so they sit at the top of the list.
    company_options = "".join(
        f'<option value="{escape(name)}">{escape(name)} ({count})</option>'
        for name, count in sorted(
            company_counts.items(),
            key=lambda kv: (kv[0] == UNKNOWN_COMPANY, -kv[1], kv[0].lower()),
        )
    )
    multi_ad_employers = sum(
        1 for name, count in company_counts.items()
        if count > 1 and name != UNKNOWN_COMPANY
    )

    place_filter_buttons = "".join(
        f'<button class="filter-btn" onclick="filterPlace(\'{escape(label)}\', this)">'
        f'{escape(label)} ({place_counts[label]})</button>'
        for label in ordered_place_labels
    )

    # Color map per site
    colors = {
        "RemoteOK": "#10b981", "WelcomeToTheJungle": "#f59e0b",
        "Job Bank Canada": "#3b82f6", "CareerJet Canada": "#8b5cf6",
        "Hacker News Jobs": "#ff6600", "BuiltIn Remote": "#ec4899",
        "TD Bank": "#00a651", "CIBC": "#c41f3e", "RBC": "#003168",
        "indeed": "#2164f3", "linkedin": "#0a66c2",
        "Dice": "#eb1c26", "Glassdoor": "#0caa41",
        "Thomson Reuters": "#ff8000", "Motorola Solutions": "#0080ff",
        "Moderna": "#e60000", "NVIDIA": "#76b900", "Salesforce": "#00a1e0",
    }

    # Score distribution bar chart
    score_bars = ""
    max_count = max(score_dist.values()) if score_dist else 1
    for s in range(10, 0, -1):
        count = score_dist.get(s, 0)
        pct = (count / max_count * 100) if max_count else 0
        score_color = "#10b981" if s >= 7 else ("#f59e0b" if s >= 5 else "#ef4444")
        score_bars += f"""
        <div class="score-row">
          <span class="score-label">{s}</span>
          <div class="score-bar-track">
            <div class="score-bar-fill" style="width:{pct}%;background:{score_color}"></div>
          </div>
          <span class="score-count">{count}</span>
        </div>"""

    # Site stats rows
    site_rows = ""
    for s in site_stats[:12]:
        site = s["site"] or "?"
        color = colors.get(site, "#6b7280")
        avg = s["avg_score"] or 0
        site_rows += f"""
        <div class="site-row">
          <div class="site-name" style="color:{color}">{escape(site)}</div>
          <div class="site-nums">{s['total']} jobs &middot; {s['high_fit']} strong fit &middot; avg score {avg}</div>
          <div class="bar-track">
            <div class="bar-fill" style="width:{s['high_fit']/max(s['total'],1)*100}%;background:{color}"></div>
            <div class="bar-fill" style="width:{s['mid_fit']/max(s['total'],1)*100}%;background:{color}66"></div>
          </div>
        </div>"""

    # Job cards grouped by score
    job_sections = ""
    current_score = None
    for card_order, j in enumerate(jobs):
        score = j["fit_score"] or 0
        if score != current_score:
            if current_score is not None:
                job_sections += "</div>"
            score_color = "#10b981" if score >= 7 else ("#f59e0b" if score >= 5 else "#ef4444")
            score_label = {
                10: "Perfect Match (10/10)", 9: "Excellent Fit (9/10)", 8: "Strong Fit (8/10)",
                7: "Good Fit (7/10)", 6: "Moderate+ (6/10)", 5: "Moderate (5/10)",
                4: "Weak Fit (4/10)", 3: "Seniority / Skill Mismatch (3/10)",
                2: "Poor Match (2/10)", 1: "Unrelated (1/10)", 0: "Error / Unscored (0/10)",
            }.get(score, f"Score {score}")
            count_at_score = score_dist.get(score, 0)
            job_sections += f"""
            <h2 class="score-header" style="border-color:{score_color}" data-score-header="{score}">
              <span class="score-badge" style="background:{score_color}">{score}</span>
              {score_label} ({count_at_score} jobs)
            </h2>
            <div class="job-grid" data-score-grid="{score}">"""
            current_score = score

        title = escape(j["title"] or "Untitled")
        url = escape(j["url"] or "")
        salary = escape(j["salary"] or "")
        location = escape(j["location"] or "")
        site = escape(j["site"] or "")
        site_color = colors.get(j["site"] or "", "#6b7280")
        apply_url = escape(j["application_url"] or "")

        # Application Status
        applied_at = j["applied_at"]
        apply_status = (j["apply_status"] or "").lower()
        if applied_at or apply_status == "applied":
            status_pill = f'<span class="status-pill status-applied">✓ APPLIED {escape(applied_at[:10]) if applied_at else ""}</span>'
            data_status = "applied"
        elif apply_status == "in_progress":
            status_pill = '<span class="status-pill status-progress">⏳ IN PROGRESS</span>'
            data_status = "in_progress"
        elif apply_status == "listing_closed":
            status_pill = '<span class="status-pill status-closed">🚫 LISTING CLOSED</span>'
            data_status = "closed"
        elif apply_status == "manual":
            err_msg = escape((j["apply_error"] or "Needs manual application")[:60])
            status_pill = f'<span class="status-pill status-manual" title="{err_msg}">✋ MANUAL ONLY</span>'
            data_status = "manual"
        elif apply_status in ("failed", "needs_review"):
            err_msg = escape((j["apply_error"] or "Review needed")[:60])
            status_pill = f'<span class="status-pill status-failed" title="{err_msg}">⚠ {apply_status.upper()}</span>'
            data_status = "failed"
        elif j["tailored_resume_path"] and apply_url:
            status_pill = '<span class="status-pill status-ready">🚀 READY TO APPLY</span>'
            data_status = "ready"
        elif j["tailored_resume_path"]:
            status_pill = '<span class="status-pill status-tailored">📄 CV TAILORED</span>'
            data_status = "tailored"
        else:
            status_pill = '<span class="status-pill status-none">PENDING TAILOR</span>'
            data_status = "unapplied"

        is_hidden = bool(j["hidden"])
        if is_hidden:
            status_pill += ' <span class="status-pill status-hidden">🙈 HIDDEN</span>'

        # Asset Links (CV & Cover Letter) -- each asset gets an "open in new
        # tab" link plus a "Preview" button that loads it into the in-page
        # modal (see #preview-modal / openPreview() JS) so the assets are
        # actually viewable without leaving the dashboard.
        def _asset_buttons(path_str: str | None, css_class: str, label: str, icon: str) -> str:
            if not path_str:
                return ""
            base_path = Path(path_str)
            pdf_path = base_path.with_suffix(".pdf")
            if pdf_path.exists():
                target, kind = pdf_path, "PDF"
            elif base_path.exists():
                target, kind = base_path, "TXT"
            else:
                return ""
            if serve_base_url:
                import urllib.parse
                uri = escape(f"{serve_base_url}/files?path={urllib.parse.quote(str(target))}")
            else:
                uri = escape(target.as_uri())
            preview_title = escape(f"{label} ({kind}) — {j['title'] or ''}")
            # The most common reason to click Open Folder turned out to be
            # "get the filename so I can paste it into an upload dialog" --
            # give that its own one-click button instead of routing through
            # the file manager every time. Works on a static file:// export
            # too, unlike Open Folder/Preview, since it's pure client-side
            # clipboard access with no server involved.
            copy_btn = (
                f'<button type="button" class="asset-btn copy-btn" '
                f'data-filename="{escape(target.name)}" onclick="copyFilename(this)">'
                f'\U0001f4cb Copy Filename</button>'
            )
            # Open Folder needs the local server to actually run a process on
            # this machine -- only wire it up when one is behind the page (a
            # static file:// snapshot has nothing listening to ask).
            folder_btn = ""
            if serve_base_url:
                folder_btn = (
                    f'<button type="button" class="asset-btn folder-btn" '
                    f'data-path="{escape(str(target))}" onclick="openFolder(this)">'
                    f'\U0001f4c2 Open Folder</button>'
                )
            return (
                f'<a href="{uri}" class="asset-btn {css_class}" target="_blank">{icon} {label} ({kind})</a>'
                f'{copy_btn}'
                f'<button type="button" class="asset-btn preview-btn" '
                f"onclick=\"openPreview('{uri}', '{preview_title}')\">"
                f"\U0001f441️ Preview</button>"
                f"{folder_btn}"
            )

        tailored_cv = j["tailored_resume_path"]
        cover_letter = j["cover_letter_path"]
        asset_links = [
            _asset_buttons(tailored_cv, "cv-btn", "Tailored CV", "\U0001f4c4"),
            _asset_buttons(cover_letter, "cl-btn", "Cover Letter", "✉️"),
        ]
        asset_links = [a for a in asset_links if a]

        assets_html = f'<div class="assets-row">{" ".join(asset_links)}</div>' if asset_links else ""

        # Manual status controls -- lets the user apply themselves (e.g. via
        # the asset's Open Folder button above, on a portal the AI couldn't
        # get through) and then tell the dashboard about it directly,
        # without touching the CLI. Same live-server requirement as Open
        # Folder above: these mutate the DB through a POST the page sends.
        manage_html = ""
        if serve_base_url:
            manage_buttons = []
            tailor_label = "🪄 Re-tailor CV + Cover Letter" if tailored_cv else "🪄 Tailor CV + Cover Letter"
            manage_buttons.append(
                f'<button type="button" class="manage-btn manage-tailor" '
                f'onclick="tailorJob(this)">{tailor_label}</button>'
            )
            # Cover letter on its own, once a CV exists. The letter is the
            # half that gets blocked; being able to retry just it means a
            # failed letter never costs the CV that was already generated.
            if tailored_cv:
                cover_label = "📄 Redo cover letter" if cover_letter else "📄 Cover letter"
                manage_buttons.append(
                    f'<button type="button" class="manage-btn manage-cover" '
                    f'onclick="coverLetterJob(this)">{cover_label}</button>'
                )
            if data_status != "applied":
                manage_buttons.append(
                    '<button type="button" class="manage-btn manage-applied" '
                    'onclick="markApplied(this)">✅ Mark Applied</button>'
                )
                manage_buttons.append(
                    '<button type="button" class="manage-btn manage-failed" '
                    'onclick="markFailed(this)">✖ Mark Failed</button>'
                )
            # Always offered, even on a job with no apply_status yet (ready/
            # tailored/unapplied) -- reset_job() is a harmless no-op with
            # nothing to clear there, and always hiding it made the control
            # inconsistently absent from card to card for no reason a user
            # could tell from looking at the card.
            manage_buttons.append(
                '<button type="button" class="manage-btn manage-reset" '
                'onclick="resetJobStatus(this)">↺ Reset to Pending</button>'
            )
            if is_hidden:
                manage_buttons.append(
                    '<button type="button" class="manage-btn manage-unhide" '
                    'onclick="unhideJob(this)">👁 Unhide</button>'
                )
            else:
                manage_buttons.append(
                    '<button type="button" class="manage-btn manage-hide" '
                    'onclick="hideJob(this)">🙈 Hide</button>'
                )
            if manage_buttons:
                manage_html = f'<div class="manage-row">{" ".join(manage_buttons)}</div>'

        # Parse keywords and full reasoning from score_reasoning. scorer.py
        # always writes this as f"{keywords}\n{reasoning}" -- exactly one
        # newline separating the two -- so split on the FIRST newline only.
        # The old approach (drop all blank lines, then guess whether line[0]
        # was keywords from a comma/line-count heuristic) broke whenever the
        # LLM returned an empty KEYWORDS field: the now-blank first "line"
        # got silently dropped by the blank-line filter, which shifted the
        # reasoning's own first sentence into the keywords slot -- showing
        # reasoning text as "ATS keyword" chips.
        reasoning_raw = j["score_reasoning"] or ""
        if "\n" in reasoning_raw:
            keywords_part, reasoning_part = reasoning_raw.split("\n", 1)
        else:
            keywords_part, reasoning_part = "", reasoning_raw
        keywords_part = keywords_part.strip()
        full_reasoning = reasoning_part.strip()
        keywords_chips = (
            [f'<span class="kw-chip">{escape(kw.strip())}</span>'
             for kw in keywords_part.split(",") if kw.strip()][:12]
            if keywords_part else []
        )

        full_reasoning_html = escape(full_reasoning).replace("\n", "<br>")

        full_desc_text = j["full_description"] or ""
        desc_preview = escape(full_desc_text[:280])
        desc_ellipsis = "..." if len(full_desc_text) > 280 else ""
        desc_len = len(full_desc_text)
        # Descriptions are ~11.7 MB of the page across 1842 jobs, all of it
        # inside collapsed <details> the browser must still parse. When the
        # dashboard is served they are fetched from /api/description on
        # first expand instead.
        #
        # This was tried once before, on 2026-09-02, and reverted within the
        # hour: the search box matched `card.textContent`, so removing the
        # descriptions silently shrank what a search could reach, and because
        # the search term persists in localStorage the effect outlived the
        # page and read as "all my jobs disappeared". It is safe now, and
        # only now, because the served page searches in SQL (/api/search,
        # see _handle_search) rather than over the DOM.
        #
        # The static snapshot keeps them inline: a file:// page has no server
        # to search or fetch from, so its search is still the textContent
        # one, and being self-contained is the point of that mode.
        full_desc_html = (
            "" if serve_base_url else escape(full_desc_text).replace("\n", "<br>")
        )

        company_summary = escape(j["company_summary"] or "")
        company_hook = escape(j["company_hook"] or "")
        gate_reason = escape(j["gate_reason"] or "")
        critic_score = j["critic_score"]

        company_name = company_labels[j["url"]]
        meta_parts = [
            f'<span class="meta-tag site-tag" style="background:{site_color}33;color:{site_color}">{site}</span>'
        ]
        if company_name != UNKNOWN_COMPANY:
            # Rendered into the card, not just a data attribute, so the
            # existing search box (which matches card.textContent) finds an
            # employer by name for free.
            meta_parts.append(
                f'<span class="meta-tag company-tag">🏢 {escape(company_name)}</span>'
            )
        if salary:
            meta_parts.append(f'<span class="meta-tag salary">{salary}</span>')
        if location:
            meta_parts.append(f'<span class="meta-tag location">{location[:35]}</span>')
        meta_html = " ".join(meta_parts)

        # Action Buttons
        action_buttons = []
        if apply_url:
            action_buttons.append(f'<a href="{apply_url}" class="action-btn apply-btn" target="_blank">Direct Apply ↗</a>')
        if url:
            action_buttons.append(f'<a href="{url}" class="action-btn job-btn" target="_blank">Job Posting ↗</a>')

        actions_html = f'<div class="card-actions">{" ".join(action_buttons)}</div>'

        # Advisory only -- see database.group_near_identical. This never
        # removes the job from anything, it just says "you have seen this".
        dup_mark = dup_marks.get(j["url"])
        dup_html = ""
        if dup_mark:
            others = dup_group_sizes[dup_mark] - 1
            dup_html = (
                f'<div class="dup-box">&#128203; Nearly identical to {others} other '
                f'ad{"s" if others != 1 else ""} from {escape(company_name)}. '
                f'Check they are not the same role before applying to each.</div>'
            )

        job_sections += f"""
        <div class="job-card" data-url="{url}" data-score="{score}" data-site="{escape(j['site'] or '')}" data-status="{data_status}" data-hidden="{1 if is_hidden else 0}" data-place="{escape(place_labels[j['url']])}" data-company="{escape(company_name)}" data-dup="{dup_mark or ''}" data-has-cv="{1 if tailored_cv else 0}" data-has-cl="{1 if cover_letter else 0}" data-order="{card_order}" data-discovered="{escape(j['discovered_at'] or '')}" data-tailored="{escape(j['tailored_at'] or '')}" data-applied="{escape(applied_at or '')}" data-gated="{1 if gate_reason else 0}">
          <div class="card-header">
            <div class="card-title-group">
              <span class="score-pill" style="background:{'#10b981' if score >= 7 else ('#f59e0b' if score >= 5 else '#ef4444')}">{score}</span>
              {f'<span class="critic-pill" title="Critic score: computed from discrete findings (bullet density, header restatement, JD relevance, duplicate content), not model-assigned like the fit score.">&#128269; {critic_score:.1f}</span>' if critic_score is not None else ''}
              <a href="{url}" class="job-title" target="_blank">{title}</a>
            </div>
            {status_pill}
          </div>

          {f'''<div class="gate-box">
            <strong>&#9940; Eligibility gate:</strong> {gate_reason}
          </div>''' if gate_reason else ''}

          <div class="meta-row">{meta_html}</div>
          <button type="button" class="card-compact-toggle" onclick="toggleCardExpand(this)">&#9662; Details</button>

          {f'''<div class="company-box">
            <div class="company-summary"><strong>🏢 Company Context:</strong> {company_summary}</div>
            {f'<div class="company-hook"><strong>🎯 Cover Letter Angle:</strong> <em>{company_hook}</em></div>' if company_hook else ''}
          </div>''' if company_summary or company_hook else ''}

          {f'''<div class="analysis-box">
            <div class="analysis-title">FIT & SENIORITY ANALYSIS</div>
            <div class="reasoning-text">{full_reasoning_html}</div>
          </div>''' if full_reasoning else ''}

          {f'''<div class="keywords-box">
            <span class="kw-label">ATS Match:</span>
            <div class="kw-container">{" ".join(keywords_chips)}</div>
          </div>''' if keywords_chips else ''}

          {dup_html}
          {assets_html}
          {manage_html}

          <p class="desc-preview">{desc_preview}{desc_ellipsis}</p>
          {("<details class='full-desc-details'" + (f''' data-desc-url="{url}" ontoggle="loadFullDesc(this)"''' if serve_base_url else "") + "><summary class='expand-btn'>View Full Job Description (" + f'{desc_len:,}' + " chars)</summary><div class='full-desc'>" + (full_desc_html or "Loading...") + "</div></details>") if j["full_description"] else ""}

          <div class="card-footer">{actions_html}</div>
        </div>"""

    if current_score is not None:
        job_sections += "</div>"

    scored_pct = (scored / total * 100) if total else 0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ScoutPilot Dashboard</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #0b0f19; color: #e2e8f0; padding: 2rem; line-height: 1.5; }}

  /* Top Bar */
  .top-bar {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 1rem; }}
  h1 {{ font-size: 1.9rem; font-weight: 800; color: #f8fafc; letter-spacing: -0.02em; }}
  .subtitle {{ color: #94a3b8; font-size: 0.95rem; margin-top: 0.2rem; }}

  /* Refresh Control */
  .refresh-box {{ display: flex; align-items: center; gap: 0.75rem; background: #1e293b; padding: 0.5rem 1rem; border-radius: 8px; border: 1px solid #334155; }}
  .refresh-btn {{ background: #3b82f6; color: #ffffff; border: none; padding: 0.35rem 0.8rem; border-radius: 6px; font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: 0.15s; }}
  .refresh-btn:hover {{ background: #2563eb; }}

  /* Summary Metrics Grid */
  .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
  .stat-card {{ background: #151d30; border: 1px solid #243049; border-radius: 12px; padding: 1.15rem; transition: transform 0.15s, border-color 0.15s; }}
  .stat-card:hover {{ border-color: #3b82f6; transform: translateY(-2px); }}
  .stat-num {{ font-size: 1.85rem; font-weight: 800; }}
  .stat-label {{ color: #94a3b8; font-size: 0.82rem; font-weight: 500; margin-top: 0.2rem; }}

  .stat-total .stat-num {{ color: #f8fafc; }}
  .stat-scored .stat-num {{ color: #60a5fa; }}
  .stat-high .stat-num {{ color: #34d399; }}
  .stat-tailored .stat-num {{ color: #a78bfa; }}
  .stat-cl .stat-num {{ color: #f472b6; }}
  .stat-applied .stat-num {{ color: #10b981; }}
  .stat-unavailable .stat-num {{ color: #64748b; }}
  .stat-hidden .stat-num {{ color: #a8a29e; }}

  /* Filter Controls */
  .filter-panel {{ background: #151d30; border: 1px solid #243049; border-radius: 12px; padding: 1.25rem; margin-bottom: 2rem; display: flex; flex-direction: column; gap: 1rem; }}
  .filter-row {{ display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }}
  .filter-label {{ color: #94a3b8; font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; min-width: 65px; }}

  .filter-btn {{ background: #1e293b; border: 1px solid #334155; color: #cbd5e1; padding: 0.35rem 0.85rem; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; transition: all 0.15s; }}
  .filter-btn:hover {{ background: #334155; color: #ffffff; }}
  .filter-btn.active {{ background: #3b82f6; border-color: #3b82f6; color: #ffffff; font-weight: 700; }}

  .search-input {{ background: #1e293b; border: 1px solid #334155; color: #f8fafc; padding: 0.45rem 1rem; border-radius: 6px; font-size: 0.85rem; flex: 1; min-width: 250px; outline: none; }}
  .search-input:focus {{ border-color: #3b82f6; }}

  .sort-select {{ background: #1e293b; border: 1px solid #334155; color: #f8fafc; padding: 0.35rem 0.7rem; border-radius: 6px; font-size: 0.8rem; cursor: pointer; outline: none; }}
  .sort-select:focus {{ border-color: #3b82f6; }}

  .hide-toggle {{ display: flex; align-items: center; gap: 0.5rem; color: #cbd5e1; font-size: 0.85rem; font-weight: 600; cursor: pointer; user-select: none; }}
  .hide-toggle input {{ width: 1rem; height: 1rem; cursor: pointer; accent-color: #3b82f6; }}

  /* Compact view -- collapses the heavier per-card detail blocks so more
     cards fit on screen at once; a card the user expands individually
     stays expanded (.expanded) even while compact mode is on. */
  .card-compact-toggle {{ display: none; align-self: flex-start; background: none; border: none; color: #60a5fa; font-size: 0.78rem; font-weight: 600; cursor: pointer; padding: 0 0 0.6rem; font-family: inherit; }}
  .card-compact-toggle:hover {{ color: #93c5fd; text-decoration: underline; }}
  body.compact-mode .card-compact-toggle {{ display: inline-flex; }}
  body.compact-mode .job-card:not(.expanded) .company-box,
  body.compact-mode .job-card:not(.expanded) .analysis-box,
  body.compact-mode .job-card:not(.expanded) .keywords-box,
  body.compact-mode .job-card:not(.expanded) .desc-preview,
  body.compact-mode .job-card:not(.expanded) .full-desc-details {{ display: none; }}

  /* Score & Site Visualizations */
  .analytics-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2.5rem; }}
  .analytics-card {{ background: #151d30; border: 1px solid #243049; border-radius: 12px; padding: 1.5rem; }}
  .analytics-card h3 {{ font-size: 1rem; font-weight: 700; margin-bottom: 1.2rem; color: #cbd5e1; }}

  .score-row {{ display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.45rem; }}
  .score-label {{ width: 1.5rem; text-align: right; font-size: 0.85rem; font-weight: 700; }}
  .score-bar-track {{ flex: 1; height: 14px; background: #1e293b; border-radius: 4px; overflow: hidden; }}
  .score-bar-fill {{ height: 100%; border-radius: 4px; transition: width 0.3s ease; }}
  .score-count {{ width: 3rem; font-size: 0.8rem; color: #94a3b8; font-weight: 600; }}

  .site-row {{ margin-bottom: 0.85rem; }}
  .site-name {{ font-weight: 700; font-size: 0.88rem; }}
  .site-nums {{ color: #94a3b8; font-size: 0.75rem; margin: 0.15rem 0 0.35rem 0; }}
  .bar-track {{ height: 8px; background: #1e293b; border-radius: 4px; display: flex; overflow: hidden; }}
  .bar-fill {{ height: 100%; transition: width 0.3s; }}

  /* Score Headers */
  .score-header {{ font-size: 1.25rem; font-weight: 700; margin: 2.5rem 0 1.2rem; padding-bottom: 0.6rem; border-bottom: 3px solid; display: flex; align-items: center; gap: 0.75rem; }}
  .score-badge {{ display: inline-flex; align-items: center; justify-content: center; width: 2.2rem; height: 2.2rem; border-radius: 8px; color: #0b0f19; font-weight: 800; font-size: 1.05rem; }}

  /* Job Cards Grid */
  .job-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(440px, 1fr)); gap: 1.35rem; }}

  .job-card {{ background: #151d30; border: 1px solid #243049; border-radius: 12px; padding: 1.35rem; border-left: 4px solid #334155; transition: transform 0.15s, box-shadow 0.15s; display: flex; flex-direction: column; }}
  .job-card:hover {{ transform: translateY(-2px); box-shadow: 0 8px 24px #00000066; border-color: #3b82f666; }}

  .job-card[data-score="10"], .job-card[data-score="9"] {{ border-left-color: #10b981; }}
  .job-card[data-score="8"] {{ border-left-color: #34d399; }}
  .job-card[data-score="7"] {{ border-left-color: #60a5fa; }}
  .job-card[data-score="6"] {{ border-left-color: #f59e0b; }}
  .job-card[data-score="5"] {{ border-left-color: #fbbf24; }}
  .job-card[data-score="4"], .job-card[data-score="3"], .job-card[data-score="2"], .job-card[data-score="1"], .job-card[data-score="0"] {{ border-left-color: #ef4444; }}

  .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 0.75rem; margin-bottom: 0.75rem; }}
  .card-title-group {{ display: flex; align-items: center; gap: 0.6rem; flex: 1; }}

  .score-pill {{ display: inline-flex; align-items: center; justify-content: center; min-width: 1.85rem; height: 1.85rem; border-radius: 6px; color: #0b0f19; font-weight: 800; font-size: 0.9rem; flex-shrink: 0; }}
  /* Dashed border, not a solid fill like score-pill -- visually marks this
     as a COMPUTED value (critic findings run through fixed weights), not
     an LLM-assigned score the way fit_score is. */
  .critic-pill {{ display: inline-flex; align-items: center; gap: 0.2rem; height: 1.6rem; padding: 0 0.5rem; border-radius: 6px; border: 1px dashed #7c8aa5; color: #c7d0e0; font-weight: 700; font-size: 0.78rem; flex-shrink: 0; cursor: help; }}
  .job-title {{ color: #f1f5f9; text-decoration: none; font-weight: 700; font-size: 1.05rem; line-height: 1.3; }}
  .job-title:hover {{ color: #60a5fa; text-decoration: underline; }}

  /* Status Badges */
  .status-pill {{ font-size: 0.72rem; font-weight: 700; padding: 0.25rem 0.65rem; border-radius: 9999px; letter-spacing: 0.03em; white-space: nowrap; }}
  .status-applied {{ background: #064e3b; color: #34d399; border: 1px solid #059669; }}
  .status-progress {{ background: #78350f; color: #fbbf24; border: 1px solid #d97706; }}
  .status-failed {{ background: #7f1d1d; color: #f87171; border: 1px solid #dc2626; }}
  .status-ready {{ background: #1e3a8a; color: #93c5fd; border: 1px solid #3b82f6; }}
  .status-tailored {{ background: #4c1d95; color: #c4b5fd; border: 1px solid #7c3aed; }}
  .status-none {{ background: #1e293b; color: #64748b; border: 1px solid #334155; }}
  .status-closed {{ background: #1e293b; color: #64748b; border: 1px solid #475569; }}
  .status-manual {{ background: #451a03; color: #fdba74; border: 1px solid #c2410c; }}
  .status-hidden {{ background: #1c1917; color: #a8a29e; border: 1px solid #57534e; }}

  .meta-row {{ display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.85rem; }}
  .meta-tag {{ font-size: 0.74rem; padding: 0.2rem 0.55rem; border-radius: 6px; background: #1e293b; color: #94a3b8; font-weight: 500; }}
  .meta-tag.salary {{ background: #064e3b44; color: #6ee7b7; border: 1px solid #064e3b; }}
  .meta-tag.location {{ background: #1e3a5f44; color: #93c5fd; border: 1px solid #1e3a5f; }}

  /* Company Box */
  .gate-box {{ background: #450a0a; color: #fca5a5; padding: 0.6rem 0.9rem; border-radius: 8px; margin-bottom: 0.85rem; border: 1px solid #b91c1c; font-size: 0.8rem; line-height: 1.4; }}
  .gate-box strong {{ color: #fecaca; }}

  .company-box {{ background: #0f1629; padding: 0.75rem 0.9rem; border-radius: 8px; margin-bottom: 0.85rem; border-left: 3px solid #3b82f6; font-size: 0.82rem; }}
  .company-summary {{ color: #cbd5e1; margin-bottom: 0.35rem; line-height: 1.45; }}
  .company-hook {{ color: #93c5fd; line-height: 1.4; }}

  /* Analysis Box */
  .analysis-box {{ background: #12192b; padding: 0.85rem 1rem; border-radius: 8px; margin-bottom: 0.85rem; border: 1px solid #202b40; }}
  .analysis-title {{ font-size: 0.7rem; font-weight: 800; color: #60a5fa; letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 0.4rem; }}
  .reasoning-text {{ font-size: 0.82rem; color: #e2e8f0; line-height: 1.5; font-style: normal; }}

  /* Keywords Chips */
  .keywords-box {{ display: flex; align-items: flex-start; gap: 0.5rem; margin-bottom: 0.85rem; font-size: 0.75rem; flex-wrap: wrap; }}
  .kw-label {{ color: #94a3b8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em; margin-top: 0.2rem; font-size: 0.7rem; }}
  .kw-container {{ display: flex; flex-wrap: wrap; gap: 0.35rem; flex: 1; }}
  .kw-chip {{ background: #064e3b44; color: #34d399; border: 1px solid #05966966; padding: 0.15rem 0.5rem; border-radius: 4px; font-weight: 500; font-size: 0.74rem; }}

  /* Asset Buttons */
  .assets-row {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.95rem; padding: 0.65rem; background: #0f1629; border-radius: 8px; border: 1px solid #1f293d; }}
  .asset-btn {{ font-size: 0.78rem; font-weight: 600; text-decoration: none; padding: 0.4rem 0.85rem; border-radius: 6px; transition: 0.15s; display: inline-flex; align-items: center; gap: 0.3rem; }}
  .cv-btn {{ background: #2e1065; color: #c4b5fd; border: 1px solid #7c3aed; }}
  .cv-btn:hover {{ background: #3b0764; color: #ffffff; border-color: #a855f7; }}
  .cl-btn {{ background: #831843; color: #fbcfe8; border: 1px solid #db2777; }}
  .cl-btn:hover {{ background: #700c35; color: #ffffff; border-color: #f472b6; }}
  .preview-btn {{ background: #0c4a6e; color: #7dd3fc; border: 1px solid #0284c7; cursor: pointer; font-family: inherit; }}
  .preview-btn:hover {{ background: #075985; color: #ffffff; border-color: #38bdf8; }}
  .folder-btn {{ background: #292524; color: #fcd34d; border: 1px solid #78716c; cursor: pointer; font-family: inherit; }}
  .folder-btn:hover {{ background: #44403c; color: #ffffff; border-color: #d6d3d1; }}
  .copy-btn {{ background: #0f2e1e; color: #86efac; border: 1px solid #16a34a; cursor: pointer; font-family: inherit; }}
  .copy-btn:hover {{ background: #14532d; color: #ffffff; border-color: #22c55e; }}

  /* Manual status controls */
  .manage-row {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.95rem; }}
  .manage-btn {{ font-size: 0.78rem; font-weight: 600; padding: 0.4rem 0.85rem; border-radius: 6px; cursor: pointer; font-family: inherit; transition: 0.15s; }}
  .manage-applied {{ background: #064e3b; color: #6ee7b7; border: 1px solid #059669; }}
  .manage-applied:hover {{ background: #065f46; color: #ffffff; }}
  .manage-failed {{ background: #450a0a; color: #fca5a5; border: 1px solid #b91c1c; }}
  .manage-failed:hover {{ background: #7f1d1d; color: #ffffff; }}
  .manage-reset {{ background: #1e293b; color: #94a3b8; border: 1px solid #334155; }}
  .manage-reset:hover {{ background: #334155; color: #ffffff; }}
  .manage-hide {{ background: #1c1917; color: #d6d3d1; border: 1px solid #57534e; }}
  .manage-hide:hover {{ background: #292524; color: #ffffff; }}
  .manage-unhide {{ background: #172554; color: #93c5fd; border: 1px solid #1d4ed8; }}
  .manage-unhide:hover {{ background: #1e3a8a; color: #ffffff; }}
  .manage-tailor {{ background: #3b0764; color: #e9d5ff; border: 1px solid #7c3aed; }}
  .manage-cover {{ background: #172554; color: #bfdbfe; border: 1px solid #3b82f6; }}
  .company-tag {{ background: #1e293b; color: #cbd5e1; }}
  .dup-box {{ margin-top: 0.6rem; padding: 0.5rem 0.75rem; border-radius: 6px; font-size: 0.78rem; background: #2a2015; color: #dfa463; border: 1px solid #7c5a2a; }}
  .manage-tailor:hover {{ background: #4c1d95; color: #ffffff; }}
  .manage-tailor:disabled {{ opacity: 0.6; cursor: default; }}

  /* Card highlight after a Tailor job finishes and the page auto-reloads --
     the job-card the user was just watching gets a brief pulsing border so
     they can find it again among however many other cards are on screen. */
  @keyframes focus-pulse {{
    0%, 100% {{ box-shadow: 0 0 0 3px #a855f799; }}
    50% {{ box-shadow: 0 0 0 3px #a855f722; }}
  }}
  .job-card.just-tailored {{ animation: focus-pulse 1.1s ease-in-out 3; border-color: #a855f7; }}

  /* Asset Preview Modal */
  .preview-overlay {{
    display: none; position: fixed; inset: 0; z-index: 1000;
    background: rgba(4, 7, 15, 0.82); backdrop-filter: blur(2px);
    align-items: center; justify-content: center; padding: 3vh 3vw;
  }}
  .preview-overlay.open {{ display: flex; }}
  .preview-panel {{
    background: #0f1629; border: 1px solid #2a3650; border-radius: 12px;
    width: min(900px, 100%); height: 94vh; display: flex; flex-direction: column;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5); overflow: hidden;
  }}
  .preview-header {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 0.7rem 1rem; border-bottom: 1px solid #202b40; background: #0c1220;
  }}
  .preview-title {{ font-size: 0.85rem; font-weight: 700; color: #e2e8f0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .preview-header-actions {{ display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0; margin-left: 1rem; }}
  .preview-open-link {{ font-size: 0.78rem; color: #7dd3fc; text-decoration: none; padding: 0.3rem 0.6rem; border-radius: 6px; border: 1px solid #0284c7; }}
  .preview-open-link:hover {{ background: #0c4a6e; }}
  .preview-close {{
    background: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 6px;
    width: 1.8rem; height: 1.8rem; font-size: 1rem; cursor: pointer; line-height: 1;
  }}
  .preview-close:hover {{ background: #7f1d1d; color: #fca5a5; border-color: #dc2626; }}
  .preview-frame {{ flex: 1; border: 0; background: #ffffff; width: 100%; }}

  .desc-preview {{ font-size: 0.8rem; color: #64748b; line-height: 1.5; margin-bottom: 0.85rem; max-height: 3.8em; overflow: hidden; }}

  /* Action Buttons */
  .card-footer {{ margin-top: auto; padding-top: 0.75rem; border-top: 1px solid #243049; display: flex; justify-content: flex-end; }}
  .card-actions {{ display: flex; gap: 0.5rem; }}
  .action-btn {{ font-size: 0.8rem; font-weight: 600; text-decoration: none; padding: 0.35rem 0.85rem; border-radius: 6px; transition: 0.15s; }}
  .apply-btn {{ background: #10b981; color: #0b0f19; }}
  .apply-btn:hover {{ background: #059669; color: #ffffff; }}
  .job-btn {{ background: #1e293b; color: #94a3b8; border: 1px solid #334155; }}
  .job-btn:hover {{ background: #334155; color: #ffffff; }}

  /* Expandable full description */
  .full-desc-details {{ margin-bottom: 0.85rem; }}
  .expand-btn {{ font-size: 0.8rem; color: #60a5fa; cursor: pointer; list-style: none; padding: 0.2rem 0; font-weight: 500; }}
  .expand-btn:hover {{ color: #93c5fd; text-decoration: underline; }}
  .full-desc {{ font-size: 0.82rem; color: #cbd5e1; line-height: 1.6; margin-top: 0.5rem; padding: 0.85rem; background: #0b0f19; border: 1px solid #243049; border-radius: 8px; max-height: 400px; overflow-y: auto; white-space: pre-wrap; word-break: break-word; }}

  .hidden {{ display: none !important; }}
  .job-count-banner {{ color: #94a3b8; font-size: 0.9rem; font-weight: 600; margin-bottom: 1rem; }}

  @media (max-width: 850px) {{
    .analytics-grid {{ grid-template-columns: 1fr; }}
    .job-grid {{ grid-template-columns: 1fr; }}
    body {{ padding: 1rem; }}
  }}
</style>
</head>
<body>

<div class="top-bar">
  <div>
    <h1>ScoutPilot Dashboard</h1>
    <p class="subtitle">{total} discovered &middot; {scored} scored ({scored_pct:.1f}%) &middot; {high_fit} high fit (&ge;7) &middot; {applied} applied</p>
  </div>
  <div class="refresh-box">
    <button class="refresh-btn" onclick="location.reload()">🔄 Refresh Now</button>
  </div>
</div>

<div class="summary">
  <div class="stat-card stat-total"><div class="stat-num">{total}</div><div class="stat-label">Total Jobs</div></div>
  <div class="stat-card stat-scored"><div class="stat-num">{scored}</div><div class="stat-label">Scored by LLM</div></div>
  <div class="stat-card stat-high"><div class="stat-num">{high_fit}</div><div class="stat-label">Strong Matches (7+)</div></div>
  <div class="stat-card stat-tailored"><div class="stat-num">{tailored}</div><div class="stat-label">Tailored CVs Ready</div></div>
  <div class="stat-card stat-cl"><div class="stat-num">{with_cl}</div><div class="stat-label">Cover Letters Ready</div></div>
  <div class="stat-card stat-applied"><div class="stat-num">{applied}</div><div class="stat-label">Submitted Applications</div></div>
  <div class="stat-card stat-unavailable"><div class="stat-num">{unavailable}</div><div class="stat-label">Unavailable (closed/manual)</div></div>
  <div class="stat-card stat-hidden"><div class="stat-num">{hidden_count}</div><div class="stat-label">Hidden by you</div></div>
</div>

<div class="filter-panel">
  <div class="filter-row">
    <span class="filter-label">Score:</span>
    <button class="filter-btn active" onclick="filterScore('all', this)">All Scored</button>
    <button class="filter-btn" onclick="filterScore('7', this)">7+ Strong</button>
    <button class="filter-btn" onclick="filterScore('8', this)">8+ Excellent</button>
    <button class="filter-btn" onclick="filterScore('9', this)">9+ Perfect</button>
    <button class="filter-btn" onclick="filterScore('5', this)">5+ Moderate</button>
    <button class="filter-btn" onclick="filterScore('low', this)">&lt; 5 Low Fit</button>
  </div>

  <div class="filter-row">
    <span class="filter-label">Status:</span>
    <button class="filter-btn active" onclick="filterStatus('all', this)">All Statuses</button>
    <button class="filter-btn" onclick="filterStatus('ready', this)">Ready to Apply</button>
    <button class="filter-btn" onclick="filterStatus('applied', this)">Applied</button>
    <button class="filter-btn" onclick="filterStatus('tailored', this)">Has Tailored CV</button>
    <button class="filter-btn" onclick="filterStatus('cl', this)">Has Cover Letter</button>
    <button class="filter-btn" onclick="filterStatus('failed', this)">Needs Review / Failed</button>
    <button class="filter-btn" onclick="filterStatus('unavailable', this)">Unavailable (Closed/Manual)</button>
    <button class="filter-btn" onclick="filterStatus('gated', this)">⛔ Eligibility gated</button>
    <button class="filter-btn" onclick="filterStatus('hidden', this)">🙈 Hidden by you</button>
  </div>

  <div class="filter-row">
    <span class="filter-label">Place:</span>
    <button class="filter-btn active" onclick="filterPlace('all', this)">All Places</button>
    {place_filter_buttons}
  </div>

  <div class="filter-row">
    <span class="filter-label">Search:</span>
    <input type="text" id="search-input" class="search-input" placeholder="Search by title, company, skills, location..." oninput="filterText(this.value)">
  </div>

  <div class="filter-row">
    <span class="filter-label">Employer:</span>
    <select id="company-select" class="sort-select" onchange="filterCompany(this.value)">
      <option value="all">All employers ({len(company_counts)}, {multi_ad_employers} with several ads)</option>
      {company_options}
    </select>
  </div>

  <div class="filter-row">
    <span class="filter-label">Sort:</span>
    <select id="sort-select" class="sort-select" onchange="applySort(this.value)">
      <option value="score">Fit Score (default)</option>
      <option value="company-asc">Employer (A-Z, groups ads together)</option>
      <option value="discovered-desc">Newest Discovered</option>
      <option value="discovered-asc">Oldest Discovered</option>
      <option value="tailored-desc">Recently Tailored</option>
      <option value="applied-desc">Recently Applied</option>
    </select>
  </div>

  <div class="filter-row">
    <label class="hide-toggle">
      <input type="checkbox" id="hide-toggle-input" checked onchange="toggleHideAppliedUnavailable(this.checked)">
      Hide Applied, Unavailable &amp; Hidden jobs by default (a Status filter above still shows them)
    </label>
    <label class="hide-toggle">
      <input type="checkbox" id="compact-toggle-input" onchange="toggleCompactMode(this.checked)">
      Compact view (collapse card details; expand one via its "Details" link)
    </label>
  </div>
</div>

<div class="analytics-grid">
  <div class="analytics-card">
    <h3>Score Distribution</h3>
    {score_bars}
  </div>
  <div class="analytics-card">
    <h3>Top Job Sources</h3>
    {site_rows}
  </div>
</div>

<div id="job-count-banner" class="job-count-banner"></div>

{job_sections}

<div id="preview-overlay" class="preview-overlay" onclick="if (event.target === this) closePreview()">
  <div class="preview-panel">
    <div class="preview-header">
      <span id="preview-title" class="preview-title"></span>
      <div class="preview-header-actions">
        <a id="preview-open-link" class="preview-open-link" href="#" target="_blank">Open in new tab ↗</a>
        <button type="button" class="preview-close" onclick="closePreview()" aria-label="Close preview">✕</button>
      </div>
    </div>
    <iframe id="preview-frame" class="preview-frame"></iframe>
  </div>
</div>

<script>
function openPreview(url, title) {{
  document.getElementById('preview-frame').src = url;
  document.getElementById('preview-title').textContent = title;
  document.getElementById('preview-open-link').href = url;
  document.getElementById('preview-overlay').classList.add('open');
}}

function closePreview() {{
  document.getElementById('preview-overlay').classList.remove('open');
  document.getElementById('preview-frame').src = '';
}}

document.addEventListener('keydown', (e) => {{
  if (e.key === 'Escape') closePreview();
}});

function apiPost(url, body) {{
  return fetch(url, {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify(body || {{}}),
  }}).then(r => r.json().catch(() => ({{}})).then(data => {{
    if (!r.ok || data.ok === false) throw new Error(data.error || ('HTTP ' + r.status));
    return data;
  }}));
}}

function cardUrl(btn) {{
  return btn.closest('.job-card').dataset.url;
}}

function markApplied(btn) {{
  if (!confirm('Mark this job as applied?')) return;
  apiPost('/api/status', {{url: cardUrl(btn), action: 'applied'}})
    .then(() => location.reload())
    .catch(err => alert('Failed to update status: ' + err.message));
}}

function markFailed(btn) {{
  const reason = prompt('Reason (optional):', '');
  if (reason === null) return;
  apiPost('/api/status', {{url: cardUrl(btn), action: 'failed', reason}})
    .then(() => location.reload())
    .catch(err => alert('Failed to update status: ' + err.message));
}}

function resetJobStatus(btn) {{
  if (!confirm('Reset this job back to pending (clears applied/failed status)?')) return;
  apiPost('/api/status', {{url: cardUrl(btn), action: 'reset'}})
    .then(() => location.reload())
    .catch(err => alert('Failed to reset status: ' + err.message));
}}

function openFolder(btn) {{
  apiPost('/api/open-folder', {{path: btn.dataset.path}})
    .catch(err => alert('Failed to open folder: ' + err.message));
}}

function _fallbackCopy(text) {{
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try {{ document.execCommand('copy'); }} catch (e) {{}}
  document.body.removeChild(ta);
}}

function copyFilename(btn) {{
  const name = btn.dataset.filename;
  const original = btn.textContent;
  const showCopied = () => {{
    btn.textContent = '✅ Copied!';
    setTimeout(() => {{ btn.textContent = original; }}, 1400);
  }};
  if (navigator.clipboard && navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(name).then(showCopied).catch(() => {{ _fallbackCopy(name); showCopied(); }});
  }} else {{
    _fallbackCopy(name);
    showCopied();
  }}
}}

function hideJob(btn) {{
  apiPost('/api/status', {{url: cardUrl(btn), action: 'hide'}})
    .then(() => location.reload())
    .catch(err => alert('Failed to hide job: ' + err.message));
}}

function unhideJob(btn) {{
  apiPost('/api/status', {{url: cardUrl(btn), action: 'unhide'}})
    .then(() => location.reload())
    .catch(err => alert('Failed to unhide job: ' + err.message));
}}

// Descriptions are not in the served page (see full_desc_html in
// generate_dashboard); the search reaches them through SQL instead. Fetch
// one the first time its <details> opens, once -- on failure the flag is
// cleared so closing and reopening retries.
function loadFullDesc(el) {{
  if (!el.open || el.dataset.loaded) return;
  const box = el.querySelector('.full-desc');
  if (!box) return;
  el.dataset.loaded = '1';
  box.textContent = 'Loading...';
  fetch('/api/description?url=' + encodeURIComponent(el.dataset.descUrl))
    .then(r => r.json())
    .then(d => {{ box.textContent = d.text || '(no description stored for this job)'; }})
    .catch(err => {{
      el.dataset.loaded = '';
      box.textContent = 'Could not load the description: ' + err.message;
    }});
}}

const FOCUS_STORAGE_KEY = 'scoutpilot_focus_url';

function tailorJob(btn) {{
  const url = cardUrl(btn);
  btn.disabled = true;
  btn.textContent = '⏳ Starting...';
  apiPost('/api/tailor-one', {{url}})
    .then(() => pollTailorStatus(url, btn))
    .catch(err => {{
      alert('Failed to start tailoring: ' + err.message);
      btn.disabled = false;
      btn.textContent = '🪄 Tailor CV + Cover Letter';
    }});
}}

// Reload as soon as the CV lands, not when the whole job finishes. A cover
// letter can take another minute or fail outright, and the CV is already on
// disk and worth showing -- waiting for both is what used to leave a
// perfectly good CV invisible whenever the letter was blocked. The reload
// drops this polling loop, so the URL is parked in localStorage and picked
// up again by resumeCoverPolling() on the way back.
const COVER_RESUME_KEY = 'scoutpilot_cover_pending_url';

function coverButtonFor(url) {{
  const card = document.querySelector('.job-card[data-url="' + CSS.escape(url) + '"]');
  return card ? card.querySelector('.manage-cover') : null;
}}

function pollTailorStatus(url, btn, opts) {{
  const coverOnly = !!(opts && opts.coverOnly);
  fetch('/api/tailor-status?url=' + encodeURIComponent(url))
    .then(r => r.json())
    .then(data => {{
      if (!coverOnly && data.cv === 'error') {{
        alert('Tailoring failed: ' + (data.cv_error || data.error || 'unknown error'));
        localStorage.removeItem(COVER_RESUME_KEY);
        if (btn) {{ btn.disabled = false; btn.textContent = '🪄 Tailor CV + Cover Letter'; }}
        return;
      }}
      // The CV is ready: show it now and let the letter finish in the
      // background. The server keeps this job's status either way.
      if (!coverOnly && data.cv === 'done') {{
        localStorage.setItem(FOCUS_STORAGE_KEY, url);
        if (data.cover === 'running' || data.cover === 'pending') {{
          localStorage.setItem(COVER_RESUME_KEY, url);
        }}
        location.reload();
        return;
      }}
      if (coverOnly && (data.cover === 'done' || data.cover === 'error')) {{
        localStorage.removeItem(COVER_RESUME_KEY);
        if (data.cover === 'error') {{
          if (btn) {{
            btn.disabled = false;
            btn.textContent = '📄 Retry cover letter';
            btn.title = data.cover_error || 'The cover letter failed; the CV above is fine.';
          }}
        }} else {{
          localStorage.setItem(FOCUS_STORAGE_KEY, url);
          location.reload();
        }}
        return;
      }}
      if (btn) {{
        btn.textContent = '⏳ ' + (data.stage === 'cover_letter'
          ? 'Writing cover letter...' : 'Tailoring CV...');
      }}
      setTimeout(() => pollTailorStatus(url, btn, opts), data.status === 'idle' ? 1500 : 3000);
    }})
    .catch(() => setTimeout(() => pollTailorStatus(url, btn, opts), 3000));
}}

// Picks the cover letter back up after the reload that showed the CV.
function resumeCoverPolling() {{
  let url;
  try {{ url = localStorage.getItem(COVER_RESUME_KEY); }} catch (e) {{ return; }}
  if (!url) return;
  const btn = coverButtonFor(url);
  if (btn) {{ btn.disabled = true; btn.textContent = '⏳ Writing cover letter...'; }}
  pollTailorStatus(url, btn, {{coverOnly: true}});
}}

function coverLetterJob(btn) {{
  const url = cardUrl(btn);
  btn.disabled = true;
  btn.textContent = '⏳ Writing cover letter...';
  apiPost('/api/cover-letter-one', {{url}})
    .then(() => pollTailorStatus(url, btn, {{coverOnly: true}}))
    .catch(err => {{
      alert('Failed to start the cover letter: ' + err.message);
      btn.disabled = false;
      btn.textContent = '📄 Cover letter';
    }});
}}

function focusStoredCard() {{
  let url;
  try {{
    url = localStorage.getItem(FOCUS_STORAGE_KEY);
    localStorage.removeItem(FOCUS_STORAGE_KEY);
  }} catch (e) {{
    return;
  }}
  if (!url) return;
  const card = document.querySelector(`.job-card[data-url="${{CSS.escape(url)}}"]`);
  if (!card) return;
  card.classList.remove('hidden');
  card.scrollIntoView({{behavior: 'smooth', block: 'center'}});
  card.classList.add('just-tailored');
  setTimeout(() => card.classList.remove('just-tailored'), 3600);
}}

let activeScoreFilter = 'all';
let activeStatusFilter = 'all';
let activePlaceFilter = 'all';
let searchText = '';
let hideAppliedUnavailable = true;
let compactMode = false;
let activeSort = 'score';

function toggleHideAppliedUnavailable(checked) {{
  hideAppliedUnavailable = checked;
  saveFilterState();
  applyFilters();
}}

function toggleCompactMode(checked) {{
  compactMode = checked;
  document.body.classList.toggle('compact-mode', compactMode);
  saveFilterState();
}}

function toggleCardExpand(btn) {{
  const card = btn.closest('.job-card');
  const expanded = card.classList.toggle('expanded');
  btn.innerHTML = expanded ? '&#9652; Hide Details' : '&#9662; Details';
}}

function applySort(val) {{
  activeSort = val;
  saveFilterState();
  document.querySelectorAll('.job-grid').forEach(grid => {{
    const cards = Array.from(grid.querySelectorAll('.job-card'));
    if (val === 'score') {{
      cards.sort((a, b) => (parseInt(a.dataset.order) || 0) - (parseInt(b.dataset.order) || 0));
    }} else {{
      const [key, dir] = val.split('-');
      cards.sort((a, b) => {{
        const av = a.dataset[key] || '';
        const bv = b.dataset[key] || '';
        if (!av && !bv) return 0;
        if (!av) return 1;
        if (!bv) return -1;
        return dir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      }});
    }}
    cards.forEach(c => grid.appendChild(c));
  }});
}}

let activeCompanyFilter = 'all';

function filterCompany(val) {{
  activeCompanyFilter = val;
  saveFilterState();
  applyFilters();
}}

function filterScore(val, btn) {{
  activeScoreFilter = val;
  btn.parentElement.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  saveFilterState();
  applyFilters();
}}

function filterStatus(val, btn) {{
  activeStatusFilter = val;
  btn.parentElement.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  saveFilterState();
  applyFilters();
}}

function filterPlace(val, btn) {{
  activePlaceFilter = val;
  btn.parentElement.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  saveFilterState();
  applyFilters();
}}

// When the dashboard is served, the search runs in SQL (/api/search) so it
// can reach the job descriptions without them having to be in the page.
// `serverMatches` is the set of matching urls, or null for "no answer yet".
//
// null deliberately means "do not filter by text", never "nothing matched".
// A search whose fetch is still in flight, or that failed outright, shows
// everything rather than hiding everything -- getting that backwards is
// what made the board look empty on 2026-09-02.
const SERVER_SEARCH = {server_search_flag};
let serverMatches = null;
let searchSeq = 0;
let searchTimer = null;

function fetchSearchMatches(term) {{
  const seq = ++searchSeq;
  return fetch('/api/search?q=' + encodeURIComponent(term))
    .then(r => r.json())
    .then(d => {{
      if (seq !== searchSeq) return;          // a later keystroke already won
      serverMatches = (d && d.urls) ? new Set(d.urls) : null;
      applyFilters();
    }})
    .catch(() => {{
      if (seq !== searchSeq) return;
      serverMatches = null;                    // fail open, never blank
      applyFilters();
    }});
}}

function filterText(text) {{
  searchText = text.toLowerCase();
  saveFilterState();
  if (!SERVER_SEARCH) {{
    applyFilters();
    return;
  }}
  searchSeq++;                                 // invalidate anything in flight
  serverMatches = null;
  applyFilters();                              // responsive immediately
  clearTimeout(searchTimer);
  if (searchText) {{
    searchTimer = setTimeout(() => fetchSearchMatches(searchText), 200);
  }}
}}

// Filters live only as in-memory JS state, so a plain location.reload()
// (the Refresh button, and the auto-reload after a tailor job finishes)
// used to snap back to the defaults. Persist the active selections here
// and re-apply them on load so a refresh keeps showing what you were
// looking at.
const FILTER_STORAGE_KEY = 'scoutpilot_filter_state';

function saveFilterState() {{
  try {{
    localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify({{
      score: activeScoreFilter,
      status: activeStatusFilter,
      place: activePlaceFilter,
      company: activeCompanyFilter,
      search: searchText,
      hideAppliedUnavailable: hideAppliedUnavailable,
      compactMode: compactMode,
      sort: activeSort,
    }}));
  }} catch (e) {{}}
}}

function _setActiveFilterButton(selector, val) {{
  document.querySelectorAll(selector).forEach(btn => {{
    const onclick = btn.getAttribute('onclick') || '';
    const start = onclick.indexOf("'") + 1;
    const end = onclick.indexOf("'", start);
    const arg = (start > 0 && end > start) ? onclick.slice(start, end) : '';
    btn.classList.toggle('active', arg === val);
  }});
}}

function restoreFilterState() {{
  let saved;
  try {{
    saved = JSON.parse(localStorage.getItem(FILTER_STORAGE_KEY));
  }} catch (e) {{
    return;
  }}
  if (!saved) return;

  activeScoreFilter = saved.score || 'all';
  activeStatusFilter = saved.status || 'all';
  activePlaceFilter = saved.place || 'all';
  activeCompanyFilter = saved.company || 'all';
  searchText = saved.search || '';
  hideAppliedUnavailable = saved.hideAppliedUnavailable !== false;
  compactMode = saved.compactMode === true;
  activeSort = saved.sort || 'score';

  const searchInput = document.getElementById('search-input');
  if (searchInput) searchInput.value = saved.search || '';
  const hideToggle = document.getElementById('hide-toggle-input');
  if (hideToggle) hideToggle.checked = hideAppliedUnavailable;
  const compactToggle = document.getElementById('compact-toggle-input');
  if (compactToggle) compactToggle.checked = compactMode;
  document.body.classList.toggle('compact-mode', compactMode);
  const companySelect = document.getElementById('company-select');
  // A stored employer that no longer has any ads on the page would filter
  // everything away with no obvious cause, so fall back to "all" instead.
  if (companySelect) {{
    const known = Array.from(companySelect.options).some(o => o.value === activeCompanyFilter);
    if (!known) activeCompanyFilter = 'all';
    companySelect.value = activeCompanyFilter;
  }}
  const sortSelect = document.getElementById('sort-select');
  if (sortSelect) sortSelect.value = activeSort;
  applySort(activeSort);

  if (SERVER_SEARCH && searchText) fetchSearchMatches(searchText);

  _setActiveFilterButton('.filter-btn[onclick^="filterScore("]', activeScoreFilter);
  _setActiveFilterButton('.filter-btn[onclick^="filterStatus("]', activeStatusFilter);
  _setActiveFilterButton('.filter-btn[onclick^="filterPlace("]', activePlaceFilter);
}}

function applyFilters() {{
  let shown = 0;
  let total = 0;

  document.querySelectorAll('.job-card').forEach(card => {{
    total++;
    const score = parseInt(card.dataset.score) || 0;
    const status = card.dataset.status;
    const isHidden = card.dataset.hidden === '1';
    const place = card.dataset.place;
    const hasCV = card.dataset.hasCv === '1';
    const hasCL = card.dataset.hasCl === '1';
    const isGated = card.dataset.gated === '1';
    const text = card.textContent.toLowerCase();

    // Score Filter
    let scoreMatch = true;
    if (activeScoreFilter === '9') scoreMatch = score >= 9;
    else if (activeScoreFilter === '8') scoreMatch = score >= 8;
    else if (activeScoreFilter === '7') scoreMatch = score >= 7;
    else if (activeScoreFilter === '5') scoreMatch = score >= 5;
    else if (activeScoreFilter === 'low') scoreMatch = score < 5;

    // Status Filter
    let statusMatch = true;
    if (activeStatusFilter === 'applied') statusMatch = status === 'applied';
    else if (activeStatusFilter === 'ready') statusMatch = status === 'ready';
    else if (activeStatusFilter === 'tailored') statusMatch = hasCV;
    else if (activeStatusFilter === 'cl') statusMatch = hasCL;
    else if (activeStatusFilter === 'failed') statusMatch = status === 'failed';
    else if (activeStatusFilter === 'unavailable') statusMatch = status === 'closed' || status === 'manual';
    else if (activeStatusFilter === 'gated') statusMatch = isGated;
    else if (activeStatusFilter === 'hidden') statusMatch = isHidden;

    // Place Filter
    const placeMatch = activePlaceFilter === 'all' || place === activePlaceFilter;

    // Employer Filter
    const companyMatch = activeCompanyFilter === 'all'
      || (card.dataset.company || '') === activeCompanyFilter;

    // Hide Applied/Unavailable/Hidden toggle (default on) combines with the
    // filters above, but a specific Status filter always wins -- picking
    // "Applied" or "Hidden by you" is an explicit request to see exactly
    // those, so the blanket hide shouldn't fight it.
    const hideMatch = activeStatusFilter !== 'all' || !hideAppliedUnavailable
      || (status !== 'applied' && status !== 'closed' && status !== 'manual' && !isHidden);

    // Search Text Match
    // Server-side when served (serverMatches null = answer not in yet, so
    // don't filter), client-side against the card's own text otherwise.
    const textMatch = !searchText
      || (SERVER_SEARCH ? (serverMatches === null || serverMatches.has(card.dataset.url))
                        : text.includes(searchText));

    if (scoreMatch && statusMatch && placeMatch && companyMatch && hideMatch && textMatch) {{
      card.classList.remove('hidden');
      shown++;
    }} else {{
      card.classList.add('hidden');
    }}
  }});

  document.getElementById('job-count-banner').textContent = `Showing ${{shown}} of ${{total}} scored jobs`;

  // Hide empty score section headers
  document.querySelectorAll('.score-header').forEach(header => {{
    const scoreVal = header.dataset.scoreHeader;
    const grid = document.querySelector(`.job-grid[data-score-grid="${{scoreVal}}"]`);
    if (grid) {{
      const visible = grid.querySelectorAll('.job-card:not(.hidden)').length;
      header.style.display = visible ? '' : 'none';
      grid.style.display = visible ? '' : 'none';
    }}
  }});
}}

restoreFilterState();
applyFilters();
focusStoredCard();
resumeCoverPolling();
</script>

</body>
</html>"""

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    abs_path = str(out.resolve())
    console.print(f"[green]Dashboard written to {abs_path}[/green]")
    return abs_path


def open_dashboard(output_path: str | None = None) -> None:
    """Generate a static dashboard snapshot and open it in the default
    browser -- a one-shot file:// view. The in-page Refresh button and any
    manual browser reload just re-display this same snapshot; the file only
    changes the next time this (or `serve_dashboard`) is called. Prefer
    `serve_dashboard()` for anything you intend to keep checking back on.

    Args:
        output_path: Where to write the HTML file. Defaults to ~/.applypilot/dashboard.html.
    """
    path = generate_dashboard(output_path)
    console.print("[dim]Opening in browser...[/dim]")
    webbrowser.open(Path(path).as_uri())


def serve_dashboard(output_path: str | None = None, port: int = 8765) -> None:
    """Serve the dashboard over a local HTTP server, regenerating fresh from
    the DB on every request, and block until interrupted.

    This is what makes the in-page "Refresh Now" button (a plain
    `location.reload()`) actually pull current data: reloading a
    `file://...dashboard.html` snapshot just re-displays whatever was on
    disk from the last `scoutpilot dashboard` run, since nothing regenerates
    it in between -- there's no live connection from a static file back to
    the database. Serving it means every GET (a page reload, or a fresh
    `scoutpilot dashboard` open) re-runs generate_dashboard() against the
    live DB, so "refresh" means what it says.

    Args:
        output_path: Where to also write the HTML snapshot on each request
            (same file `open_dashboard`/`generate_dashboard` use). Defaults
            to ~/.applypilot/dashboard.html.
        port: Local port to listen on. Tries a few ports upward if taken
            (most likely cause: a previous `scoutpilot dashboard` is still
            running in another terminal).
    """
    import json
    import urllib.parse
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    def _base_url() -> str:
        return f"http://127.0.0.1:{tried_port}"

    class _DashboardHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A002
            pass  # suppress the default per-request access log; Rich prints its own status

        def do_GET(self) -> None:
            parsed = urllib.parse.urlsplit(self.path)
            if parsed.path in ("/", ""):
                self._serve_dashboard()
            elif parsed.path == "/files":
                self._serve_asset(urllib.parse.parse_qs(parsed.query))
            elif parsed.path == "/api/tailor-status":
                self._handle_tailor_status(urllib.parse.parse_qs(parsed.query))
            elif parsed.path == "/api/search":
                self._handle_search(urllib.parse.parse_qs(parsed.query))
            elif parsed.path == "/api/description":
                self._handle_description(urllib.parse.parse_qs(parsed.query))
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self) -> None:
            parsed = urllib.parse.urlsplit(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            raw_body = self.rfile.read(length) if length else b""
            try:
                payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._respond_json(400, {"ok": False, "error": "invalid JSON body"})
                return

            if parsed.path == "/api/status":
                self._handle_status(payload)
            elif parsed.path == "/api/open-folder":
                self._handle_open_folder(payload)
            elif parsed.path == "/api/tailor-one":
                self._handle_tailor_one(payload)
            elif parsed.path == "/api/cover-letter-one":
                self._handle_cover_letter_one(payload)
            else:
                self.send_response(404)
                self.end_headers()

        def _handle_tailor_one(self, payload: dict) -> None:
            # Kicks off tailor_one() + cover_letter_one() for exactly one
            # job in a background thread and returns immediately -- an LLM
            # round trip is far too slow to hold this HTTP request open for.
            # The page polls /api/tailor-status for progress instead.
            url = str(payload.get("url") or "").strip()
            if not url:
                self._respond_json(400, {"ok": False, "error": "url is required"})
                return

            existing = get_tailor_status(url)
            if existing.get("status") == "running":
                self._respond_json(200, {"ok": True, "status": "already_running"})
                return

            thread = threading.Thread(target=_run_tailor_and_cover, args=(url,), daemon=True)
            thread.start()
            self._respond_json(200, {"ok": True, "status": "started"})

        def _handle_cover_letter_one(self, payload: dict) -> None:
            # Generates ONLY the cover letter, against the CV already on
            # disk. This is the other half of separating the two: when a
            # letter is blocked, the CV it belongs to is fine and re-running
            # the whole tailor pass to get another shot at the letter would
            # throw that CV away and cost another minute.
            url = str(payload.get("url") or "").strip()
            if not url:
                self._respond_json(400, {"ok": False, "error": "url is required"})
                return

            existing = get_tailor_status(url)
            if existing.get("cover") == "running" or existing.get("cv") == "running":
                self._respond_json(200, {"ok": True, "status": "already_running"})
                return

            row = get_connection().execute(
                "SELECT tailored_resume_path FROM jobs WHERE url = ?", (url,)
            ).fetchone()
            if row is None or not row["tailored_resume_path"]:
                self._respond_json(
                    400,
                    {"ok": False, "error": "this job has no tailored CV yet -- tailor it first"},
                )
                return

            thread = threading.Thread(target=_run_cover_letter, args=(url,), daemon=True)
            thread.start()
            self._respond_json(200, {"ok": True, "status": "started"})

        # Columns a search looks in. `full_description` is here so that
        # searching for something only the description mentions still works
        # -- that used to happen in the browser, against the description
        # text inlined into every card, and it is the reason the page could
        # not be made smaller. Doing it in SQL instead costs ~30ms over 6184
        # rows (measured 2026-09-02) and frees the page from having to carry
        # 11.7 MB of description text purely to be searchable.
        _SEARCH_COLUMNS = (
            "title", "company", "site", "location", "salary",
            "score_reasoning", "company_summary",
        )

        def _handle_description(self, query: dict[str, list[str]]) -> None:
            """One job's description, fetched when its <details> is expanded."""
            url = (query.get("url") or [""])[0]
            if not url:
                self._respond_json(400, {"ok": False, "error": "url is required"})
                return
            row = get_connection().execute(
                "SELECT COALESCE(NULLIF(full_description, ''), description) AS text "
                "FROM jobs WHERE url = ?",
                (url,),
            ).fetchone()
            if row is None:
                self._respond_json(404, {"ok": False, "error": "no such job"})
                return
            self._respond_json(200, {"ok": True, "text": row["text"] or ""})

        def _handle_search(self, query: dict[str, list[str]]) -> None:
            term = (query.get("q") or [""])[0].strip().lower()
            if not term:
                # An empty query means "no text filter", which is not the
                # same as "nothing matches" -- returning an empty list here
                # would blank the board.
                self._respond_json(200, {"ok": True, "q": "", "urls": None})
                return

            like = f"%{term}%"
            columns = " OR ".join(
                f"lower(COALESCE({c}, '')) LIKE ?" for c in self._SEARCH_COLUMNS
            )
            sql = (
                "SELECT url FROM jobs "
                "WHERE (fit_score IS NOT NULL OR tailored_resume_path IS NOT NULL) "
                f"AND ({columns} "
                "OR lower(COALESCE(full_description, description, '')) LIKE ?)"
            )
            params = (like,) * (len(self._SEARCH_COLUMNS) + 1)
            try:
                urls = [r["url"] for r in get_connection().execute(sql, params)]
            except Exception as exc:  # noqa: BLE001 -- a failed search must not blank the page
                log.exception("Dashboard search failed for %r", term)
                self._respond_json(500, {"ok": False, "error": str(exc)})
                return
            self._respond_json(200, {"ok": True, "q": term, "urls": urls})

        def _handle_tailor_status(self, query: dict[str, list[str]]) -> None:
            url = (query.get("url") or [""])[0]
            if not url:
                self._respond_json(400, {"status": "error", "error": "url is required"})
                return
            self._respond_json(200, get_tailor_status(url))

        def _handle_status(self, payload: dict) -> None:
            # Lets the dashboard mark a job applied/failed, reset it back to
            # pending, or hide/unhide it -- without the user touching the
            # CLI. Covers both the "I applied by hand, tell the dashboard"
            # workflow and the "never show me this posting again" one.
            from scoutpilot.apply.launcher import mark_job, reset_job
            from scoutpilot.database import hide_job, unhide_job

            url = str(payload.get("url") or "").strip()
            action = str(payload.get("action") or "").strip()
            reason = payload.get("reason")
            valid_actions = ("applied", "failed", "reset", "hide", "unhide")
            if not url or action not in valid_actions:
                self._respond_json(400, {"ok": False, "error": "url and a valid action are required"})
                return
            try:
                if action == "reset":
                    reset_job(url)
                elif action == "hide":
                    hide_job(get_connection(), url)
                elif action == "unhide":
                    unhide_job(get_connection(), url)
                else:
                    mark_job(url, action, reason=(reason or None) if action == "failed" else None)
                self._respond_json(200, {"ok": True})
            except Exception as exc:  # noqa: BLE001 -- report the failure to the page, don't crash the server
                log.exception("Manual status update failed")
                self._respond_json(500, {"ok": False, "error": str(exc)})

        def _handle_open_folder(self, payload: dict) -> None:
            # Same allow-listed-roots check as _serve_asset: only ever reveal
            # a file that already lives under the CV/cover-letter output
            # dirs, never an arbitrary path a request happens to name.
            raw = str(payload.get("path") or "").strip()
            if not raw:
                self._respond_json(400, {"ok": False, "error": "path is required"})
                return
            try:
                target = Path(raw).resolve()
            except (OSError, ValueError):
                self._respond_json(400, {"ok": False, "error": "invalid path"})
                return
            allowed = any(
                target == root.resolve() or root.resolve() in target.parents
                for root in ASSET_SERVE_ROOTS
            )
            if not allowed or not target.is_file():
                self._respond_json(403, {"ok": False, "error": "path not allowed"})
                return
            try:
                _reveal_in_file_manager(target)
                self._respond_json(200, {"ok": True})
            except Exception as exc:  # noqa: BLE001 -- report the failure to the page, don't crash the server
                log.exception("Failed to open file manager")
                self._respond_json(500, {"ok": False, "error": str(exc)})

        def _respond_json(self, status: int, obj: dict) -> None:
            self._respond(status, json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

        def _serve_dashboard(self) -> None:
            try:
                path = generate_dashboard(output_path, serve_base_url=_base_url())
                html = Path(path).read_text(encoding="utf-8")
            except Exception as exc:  # noqa: BLE001 -- must still respond, not crash the server
                log.exception("Dashboard generation failed")
                self._respond(500, f"Dashboard generation failed: {exc}".encode(), "text/plain; charset=utf-8")
                return
            self._respond(200, html.encode("utf-8"), "text/html; charset=utf-8")

        def _serve_asset(self, query: dict[str, list[str]]) -> None:
            # Same-origin file streaming for CV/cover-letter assets -- a
            # page served over http:// linking or iframe-embedding a
            # file:// resource is a cross-scheme navigation browsers block
            # outright, which is what silently broke "View"/"Preview" the
            # moment the dashboard stopped being a file:// page itself.
            raw = (query.get("path") or [""])[0]
            if not raw:
                self.send_response(400)
                self.end_headers()
                return
            try:
                target = Path(raw).resolve()
            except (OSError, ValueError):
                self.send_response(400)
                self.end_headers()
                return
            allowed = any(
                target == root.resolve() or root.resolve() in target.parents
                for root in ASSET_SERVE_ROOTS
            )
            if not allowed or not target.is_file():
                self.send_response(403)
                self.end_headers()
                return
            content_type = "application/pdf" if target.suffix.lower() == ".pdf" else "text/plain; charset=utf-8"
            self._respond(200, target.read_bytes(), content_type)

        def _respond(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            # Every response through here -- the dashboard HTML itself and
            # every /files asset -- must always be re-fetched, never served
            # from the browser's cache. Without this, a re-tailored CV/cover
            # letter writes to the SAME deterministic /files?path=... URL as
            # before (same job -> same filename), so the browser can (and,
            # confirmed live 2026-08-25, does) keep showing the old cached
            # file after a regenerate-and-reload even though the file on
            # disk changed.
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.end_headers()
            self.wfile.write(body)

    server = None
    tried_port = port
    for tried_port in range(port, port + 10):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", tried_port), _DashboardHandler)
            break
        except OSError:
            continue
    if server is None:
        console.print(
            f"[red]Could not bind any port in {port}-{port + 9} -- "
            "is a dashboard server already running in another terminal?[/red]"
        )
        return

    url = f"http://127.0.0.1:{tried_port}/"
    console.print(f"[green]Dashboard live at {url}[/green] [dim](regenerates from the DB on every load/refresh)[/dim]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        console.print("\n[dim]Dashboard server stopped.[/dim]")
    finally:
        server.server_close()
