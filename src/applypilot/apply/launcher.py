"""Apply orchestration: acquire jobs, spawn Claude Code sessions, track results.

This is the main entry point for the apply pipeline. It pulls jobs from
the database, launches Chrome + Claude Code for each one, parses the
result, and updates the database. Supports parallel workers via --workers.
"""

import atexit
import json
import logging
import os
import platform
import re
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.markup import escape

from applypilot import config
from applypilot.database import (
    get_connection, start_run, end_run, create_attempt, finish_attempt,
    recover_orphaned_attempts, log_event, attach_tool_result,
    set_attempt_session, set_attempt_cost,
)
from applypilot.apply import chrome, dashboard, prompt as prompt_mod
from applypilot.apply.chrome import (
    launch_chrome, cleanup_worker, kill_all_chrome,
    reset_worker_dir, cleanup_on_exit, _kill_process_tree,
    BASE_CDP_PORT,
)
from applypilot.apply.dashboard import (
    init_worker, update_state, add_event, get_state,
    render_full, get_totals,
)

logger = logging.getLogger(__name__)

# Blocked sites loaded from config/sites.yaml
def _load_blocked():
    from applypilot.config import load_blocked_sites
    return load_blocked_sites()

# How often to poll the DB when the queue is empty (seconds)
POLL_INTERVAL = config.DEFAULTS["poll_interval"]

# Thread-safe shutdown coordination
_stop_event = threading.Event()

# Track active Claude Code processes for skip (Ctrl+C) handling
_claude_procs: dict[int, subprocess.Popen] = {}
_claude_lock = threading.Lock()

# Register cleanup on exit
atexit.register(cleanup_on_exit)
if platform.system() != "Windows":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))


# ---------------------------------------------------------------------------
# MCP config
# ---------------------------------------------------------------------------

def _make_mcp_config(cdp_port: int) -> dict:
    """Build MCP config dict for a specific CDP port."""
    return {
        "mcpServers": {
            "playwright": {
                "command": "npx",
                "args": [
                    "@playwright/mcp@latest",
                    f"--cdp-endpoint=http://localhost:{cdp_port}",
                    f"--viewport-size={config.DEFAULTS['viewport']}",
                ],
            },
            "gmail": {
                "command": "npx",
                "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
            },
        }
    }


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

def acquire_job(target_url: str | None = None, min_score: int = 7,
                worker_id: int = 0, run_id: int | None = None) -> dict | None:
    """Atomically acquire the next job to apply to and open an attempt for it.

    Args:
        target_url: Apply to a specific URL instead of picking from queue.
        min_score: Minimum fit_score threshold.
        worker_id: Worker claiming this job (for tracking).
        run_id: The apply run this attempt belongs to.

    Returns:
        Job dict (with an 'attempt_id' key) or None if the queue is empty.
    """
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")

        if target_url:
            # Exact match first, always. Confirmed live 2026-08-24: the old
            # single query OR'd in a fuzzy LIKE fallback built from
            # target_url.split('?')[0] -- stripping the query string. For
            # Indeed URLs the query string (?jk=...) *is* the entire
            # identifier, so that pattern degraded to "%https://uk.indeed.com
            # /viewjob%", matched every tailored Indeed job in the DB, and
            # with no ORDER BY, SQLite handed back whichever one it felt
            # like -- --url targeting a specific "Academic Tutor" posting
            # instead submitted a real application to an unrelated
            # "Engineering Support Graduate Assessment Day" posting. Exact
            # match is tried alone first so this can't happen when the
            # caller passes the real jobs.url/application_url value (the
            # normal case for a DB-sourced URL); the fuzzy fallback below
            # only runs when that fails, and never discards the query
            # string, so a query-string-only identifier can't be erased.
            row = conn.execute("""
                SELECT url, title, site, application_url, tailored_resume_path,
                       fit_score, location, full_description, cover_letter_path
                FROM jobs
                WHERE (url = ? OR application_url = ?)
                  AND tailored_resume_path IS NOT NULL
                  AND (apply_status IS NULL OR apply_status != 'in_progress')
                LIMIT 1
            """, (target_url, target_url)).fetchone()

            if not row:
                like = f"%{target_url.rstrip('/')}%"
                row = conn.execute("""
                    SELECT url, title, site, application_url, tailored_resume_path,
                           fit_score, location, full_description, cover_letter_path
                    FROM jobs
                    WHERE (application_url LIKE ? OR url LIKE ?)
                      AND tailored_resume_path IS NOT NULL
                      AND (apply_status IS NULL OR apply_status != 'in_progress')
                    ORDER BY url
                    LIMIT 1
                """, (like, like)).fetchone()
        else:
            blocked_sites, blocked_patterns = _load_blocked()
            # Build parameterized filters to avoid SQL injection
            params: list = [min_score]
            site_clause = ""
            if blocked_sites:
                placeholders = ",".join("?" * len(blocked_sites))
                site_clause = f"AND site NOT IN ({placeholders})"
                params.extend(blocked_sites)
            url_clauses = ""
            if blocked_patterns:
                url_clauses = " ".join(f"AND url NOT LIKE ?" for _ in blocked_patterns)
                params.extend(blocked_patterns)

            # Optional location_focus (config.load_location_focus): same
            # temporary/reversible narrowing as database.get_jobs_by_stage
            # -- restrict the auto-apply queue to matching location tiers
            # and process them in tier order (e.g. Belfast before rest-of-NI
            # before remote) when enabled. No-op when focus is disabled.
            from applypilot.config import load_location_focus
            focus = load_location_focus()
            tier_count = len((focus or {}).get("priority", []))
            focus_clause = f"AND loc_priority(location) < {tier_count}" if tier_count else ""
            order_by = "loc_priority(location) ASC, fit_score DESC, url" if tier_count else "fit_score DESC, url"

            row = conn.execute(f"""
                SELECT url, title, site, application_url, tailored_resume_path,
                       fit_score, location, full_description, cover_letter_path
                FROM jobs
                WHERE tailored_resume_path IS NOT NULL
                  AND (apply_status IS NULL OR apply_status = 'failed' OR apply_status = 'skipped')
                  AND (apply_attempts IS NULL OR apply_attempts < ?)
                  AND fit_score >= ?
                  AND duplicate_of IS NULL
                  AND COALESCE(hidden, 0) = 0
                  {site_clause}
                  {url_clauses}
                  {focus_clause}
                ORDER BY {order_by}
                LIMIT 1
            """, [config.DEFAULTS["max_apply_attempts"]] + params).fetchone()

        if not row:
            conn.rollback()
            return None

        # Skip manual ATS sites (unsolvable CAPTCHAs)
        from applypilot.config import is_manual_ats
        apply_url = row["application_url"] or row["url"]
        if is_manual_ats(apply_url):
            conn.execute(
                "UPDATE jobs SET apply_status = 'manual', apply_error = 'manual ATS' WHERE url = ?",
                (row["url"],),
            )
            conn.commit()
            logger.info("Skipping manual ATS: %s", row["url"][:80])
            return None

        attempt_id = create_attempt(conn, row["url"], run_id, worker_id=worker_id)
        conn.commit()

        job = dict(row)
        job["attempt_id"] = attempt_id
        return job
    except Exception:
        conn.rollback()
        raise


def mark_result(attempt_id: int, url: str, status: str, error: str | None = None,
                permanent: bool = False, duration_ms: int | None = None,
                task_id: str | None = None) -> None:
    """Record an attempt's outcome and mirror it onto the job."""
    conn = get_connection()
    if status == "applied":
        new_attempts = None  # leave jobs.apply_attempts as-is on success
    elif permanent:
        new_attempts = 99
    else:
        current = conn.execute(
            "SELECT apply_attempts FROM jobs WHERE url = ?", (url,)
        ).fetchone()
        new_attempts = (current["apply_attempts"] or 0) + 1 if current else 1

    finish_attempt(
        conn, attempt_id, status,
        error=None if status == "applied" else (error or "unknown"),
        duration_ms=duration_ms, task_id=task_id, apply_attempts=new_attempts,
    )


def release_lock(attempt_id: int, url: str) -> None:
    """Release the in_progress lock without recording a terminal outcome.

    Used when a job was claimed but never really attempted (e.g. skipped
    via Ctrl+C before Chrome/Claude did anything). The job becomes eligible
    for re-acquisition again.
    """
    conn = get_connection()
    finish_attempt(conn, attempt_id, "skipped")


# ---------------------------------------------------------------------------
# Utility modes (--gen, --mark-applied, --mark-failed, --reset-failed)
# ---------------------------------------------------------------------------

def gen_prompt(target_url: str, min_score: int = 7,
               model: str = "sonnet", worker_id: int = 0) -> Path | None:
    """Generate a prompt file and print the Claude CLI command for manual debugging.

    Returns:
        Path to the generated prompt file, or None if no job found.
    """
    conn = get_connection()
    run_id = start_run(conn, "apply", {"gen_prompt": True, "target_url": target_url, "model": model})
    job = acquire_job(target_url=target_url, min_score=min_score, worker_id=worker_id, run_id=run_id)
    if not job:
        end_run(conn, run_id, status="completed", stats={"found": False})
        return None

    # Read resume text
    resume_path = job.get("tailored_resume_path")
    txt_path = Path(resume_path).with_suffix(".txt") if resume_path else None
    resume_text = ""
    if txt_path and txt_path.exists():
        resume_text = txt_path.read_text(encoding="utf-8")

    prompt = prompt_mod.build_prompt(job=job, tailored_resume=resume_text)

    # Release the lock so the job stays available
    release_lock(job["attempt_id"], job["url"])
    end_run(conn, run_id, status="completed", stats={"found": True, "url": job["url"]})

    # Write prompt file
    config.ensure_dirs()
    site_slug = (job.get("site") or "unknown")[:20].replace(" ", "_")
    prompt_file = config.LOG_DIR / f"prompt_{site_slug}_{job['title'][:30].replace(' ', '_')}.txt"
    prompt_file.write_text(prompt, encoding="utf-8")

    # Write MCP config for reference
    port = BASE_CDP_PORT + worker_id
    mcp_path = config.APP_DIR / f".mcp-apply-{worker_id}.json"
    mcp_path.write_text(json.dumps(_make_mcp_config(port)), encoding="utf-8")

    return prompt_file


def mark_job(url: str, status: str, reason: str | None = None) -> None:
    """Manually mark a job's apply status in the database.

    Records this as a completed attempt (tied to its own single-attempt run)
    so the manual override shows up in the same history as automated ones.

    Args:
        url: Job URL to mark.
        status: Either 'applied' or 'failed'.
        reason: Failure reason (only for status='failed').
    """
    conn = get_connection()
    run_id = start_run(conn, "apply", {"manual": True, "action": status})
    attempt_id = create_attempt(conn, url, run_id, worker_id=None)
    conn.commit()

    if status == "applied":
        finish_attempt(conn, attempt_id, "applied")
    else:
        finish_attempt(conn, attempt_id, "failed", error=reason or "manual", apply_attempts=99)

    end_run(conn, run_id, status="completed", stats={"url": url, "status": status})


def reset_failed() -> int:
    """Reset all failed jobs so they can be retried.

    Returns:
        Number of jobs reset.
    """
    conn = get_connection()
    cursor = conn.execute("""
        UPDATE jobs SET apply_status = NULL, apply_error = NULL,
                       apply_attempts = 0, agent_id = NULL
        WHERE apply_status = 'failed'
          OR (apply_status IS NOT NULL AND apply_status != 'applied'
              AND apply_status != 'in_progress')
    """)
    conn.commit()
    return cursor.rowcount


def reset_job(url: str) -> bool:
    """Clear one job's apply status back to pending, e.g. after a wrong manual
    mark or to let a stuck/failed job be picked up again (by auto-apply or a
    fresh manual attempt).

    Args:
        url: Job URL to reset.

    Returns:
        True if a matching job row was found and reset.
    """
    conn = get_connection()
    cursor = conn.execute("""
        UPDATE jobs SET apply_status = NULL, apply_error = NULL,
                       applied_at = NULL, apply_attempts = 0, agent_id = NULL
        WHERE url = ?
    """, (url,))
    conn.commit()
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Per-job execution
# ---------------------------------------------------------------------------

def _check_playwright_mcp(msg: dict) -> str | None:
    """Inspect a system/init stream-json event for playwright MCP health.

    Browser control depends entirely on this server. If it didn't come up,
    continuing would just burn a full attempt fumbling with no tools --
    better to abort immediately with a clear, retryable error.

    Returns:
        An error string if playwright failed to connect, else None.
    """
    servers = msg.get("mcp_servers") or []
    server_errors = msg.get("mcp_server_errors") or {}

    if isinstance(server_errors, dict) and server_errors.get("playwright"):
        return str(server_errors["playwright"])
    if isinstance(server_errors, list):
        for e in server_errors:
            if isinstance(e, dict) and e.get("name") == "playwright":
                return str(e.get("error") or e)

    entry = next((s for s in servers if isinstance(s, dict) and s.get("name") == "playwright"), None)
    if entry is None:
        return "playwright MCP server not reported in init event"
    status = entry.get("status")
    if status not in ("connected", "ready", "ok"):
        return f"playwright MCP server status: {status}"
    return None

def run_job(job: dict, port: int, worker_id: int = 0,
            model: str = "sonnet", dry_run: bool = False) -> tuple[str, int]:
    """Spawn a Claude Code session for one job application.

    Returns:
        Tuple of (status_string, duration_ms). Status is one of:
        'applied', 'expired', 'captcha', 'login_issue',
        'failed:reason', or 'skipped'.
    """
    # Read tailored resume text
    resume_path = job.get("tailored_resume_path")
    txt_path = Path(resume_path).with_suffix(".txt") if resume_path else None
    resume_text = ""
    if txt_path and txt_path.exists():
        resume_text = txt_path.read_text(encoding="utf-8")

    # Build the prompt
    agent_prompt = prompt_mod.build_prompt(
        job=job,
        tailored_resume=resume_text,
        dry_run=dry_run,
    )

    # Write per-worker MCP config
    mcp_config_path = config.APP_DIR / f".mcp-apply-{worker_id}.json"
    mcp_config_path.write_text(json.dumps(_make_mcp_config(port)), encoding="utf-8")

    # Build claude command
    cmd = [
        "claude",
        "--model", model,
        "-p",
        "--mcp-config", str(mcp_config_path),
        "--permission-mode", "bypassPermissions",
        "--no-session-persistence",
        "--disallowedTools", (
            "mcp__gmail__draft_email,mcp__gmail__modify_email,"
            "mcp__gmail__delete_email,mcp__gmail__download_attachment,"
            "mcp__gmail__batch_modify_emails,mcp__gmail__batch_delete_emails,"
            "mcp__gmail__create_label,mcp__gmail__update_label,"
            "mcp__gmail__delete_label,mcp__gmail__get_or_create_label,"
            "mcp__gmail__list_email_labels,mcp__gmail__create_filter,"
            "mcp__gmail__list_filters,mcp__gmail__get_filter,"
            "mcp__gmail__delete_filter"
        ),
        "--output-format", "stream-json",
        "--verbose", "-",
    ]

    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE_ENTRYPOINT", None)

    worker_dir = reset_worker_dir(worker_id)

    update_state(worker_id, status="applying", job_title=job["title"],
                 company=job.get("site", ""), score=job.get("fit_score", 0),
                 start_time=time.time(), actions=0, last_action="starting")
    add_event(f"[W{worker_id}] Starting: {job['title'][:40]} @ {job.get('site', '')}")

    worker_log = config.LOG_DIR / f"worker-{worker_id}.log"
    ts_header = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_header = (
        f"\n{'=' * 60}\n"
        f"[{ts_header}] {job['title']} @ {job.get('site', '')}\n"
        f"URL: {job.get('application_url') or job['url']}\n"
        f"Score: {job.get('fit_score', 'N/A')}/10\n"
        f"{'=' * 60}\n"
    )

    start = time.time()
    stats: dict = {}
    proc = None
    stderr_thread = None
    attempt_id = job["attempt_id"]
    conn = get_connection()

    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=str(worker_dir),
        )
        with _claude_lock:
            _claude_procs[worker_id] = proc

        proc.stdin.write(agent_prompt)
        proc.stdin.close()

        # stderr has its own OS pipe buffer, separate from stdout's. If we
        # only read stdout, a chatty child (MCP server startup noise, node
        # warnings) can fill that buffer and block on write -- which stalls
        # the child entirely, including its stdout. Drain it concurrently
        # so the two pipes can never deadlock each other.
        stderr_log_path = config.LOG_DIR / f"worker-{worker_id}-stderr.log"

        def _drain_stderr(p=proc, path=stderr_log_path):
            try:
                with open(path, "a", encoding="utf-8") as ef:
                    for eline in p.stderr:
                        ef.write(eline)
            except Exception:
                logger.debug("Worker %d stderr drain ended", worker_id, exc_info=True)

        stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
        stderr_thread.start()

        seq = 0

        def _next_seq():
            nonlocal seq
            seq += 1
            return seq

        text_parts: list[str] = []
        abort_reason: str | None = None

        with open(worker_log, "a", encoding="utf-8") as lf:
            lf.write(log_header)

            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    text_parts.append(line)
                    lf.write(line + "\n")
                    continue

                msg_type = msg.get("type")
                parent_tool_use_id = msg.get("parent_tool_use_id")

                if msg_type == "system" and msg.get("subtype") == "init":
                    session_id = msg.get("session_id")
                    if session_id:
                        set_attempt_session(conn, attempt_id, session_id)
                    mcp_error = _check_playwright_mcp(msg)
                    log_event(conn, attempt_id, _next_seq(), "system_init", raw=msg)
                    conn.commit()
                    if mcp_error:
                        abort_reason = f"mcp_playwright_unavailable:{mcp_error}"
                        lf.write(f"  !! ABORT: {abort_reason}\n")
                        break

                elif msg_type == "assistant":
                    for block in msg.get("message", {}).get("content", []):
                        bt = block.get("type")
                        if bt == "text":
                            text_parts.append(block["text"])
                            lf.write(block["text"] + "\n")
                            log_event(conn, attempt_id, _next_seq(), "text",
                                     text=block["text"],
                                     parent_tool_use_id=parent_tool_use_id, raw=block)
                        elif bt == "tool_use":
                            name = (
                                block.get("name", "")
                                .replace("mcp__playwright__", "")
                                .replace("mcp__gmail__", "gmail:")
                            )
                            inp = block.get("input", {})
                            if "url" in inp:
                                desc = f"{name} {inp['url'][:60]}"
                            elif "ref" in inp:
                                desc = f"{name} {inp.get('element', inp.get('text', ''))}"[:50]
                            elif "fields" in inp:
                                desc = f"{name} ({len(inp['fields'])} fields)"
                            elif "paths" in inp:
                                desc = f"{name} upload"
                            else:
                                desc = name

                            lf.write(f"  >> {desc}\n")
                            ws = get_state(worker_id)
                            cur_actions = ws.actions if ws else 0
                            update_state(worker_id,
                                         actions=cur_actions + 1,
                                         last_action=desc[:35])
                            add_event(f"[W{worker_id}] [cyan]>>[/cyan] {escape(desc[:45])}")
                            log_event(conn, attempt_id, _next_seq(), "tool_use",
                                     tool_name=block.get("name", ""),
                                     tool_use_id=block.get("id"),
                                     parent_tool_use_id=parent_tool_use_id,
                                     input_data=inp, raw=block)
                    conn.commit()

                elif msg_type == "user":
                    for block in msg.get("message", {}).get("content", []):
                        if block.get("type") == "tool_result":
                            attach_tool_result(conn, attempt_id, block.get("tool_use_id"),
                                               block.get("content"), raw=block)
                    conn.commit()

                elif msg_type == "result":
                    stats = {
                        "input_tokens": msg.get("usage", {}).get("input_tokens", 0),
                        "output_tokens": msg.get("usage", {}).get("output_tokens", 0),
                        "cache_read": msg.get("usage", {}).get("cache_read_input_tokens", 0),
                        "cache_create": msg.get("usage", {}).get("cache_creation_input_tokens", 0),
                        "cost_usd": msg.get("total_cost_usd", 0),
                        "turns": msg.get("num_turns", 0),
                    }
                    text_parts.append(msg.get("result", ""))
                    set_attempt_cost(conn, attempt_id, stats["cost_usd"])
                    log_event(conn, attempt_id, _next_seq(), "result", raw=msg)
                    conn.commit()

        if abort_reason:
            if proc.poll() is None:
                _kill_process_tree(proc.pid)
            proc.wait(timeout=10)
            proc = None
            duration_ms = int((time.time() - start) * 1000)
            add_event(f"[W{worker_id}] ABORTED: {abort_reason[:40]}")
            update_state(worker_id, status="failed", last_action="mcp server unavailable")
            return f"failed:{abort_reason}", duration_ms

        proc.wait(timeout=300)
        returncode = proc.returncode
        proc = None

        if returncode and returncode < 0:
            return "skipped", int((time.time() - start) * 1000)

        output = "\n".join(text_parts)
        elapsed = int(time.time() - start)
        duration_ms = int((time.time() - start) * 1000)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_log = config.LOG_DIR / f"claude_{ts}_w{worker_id}_{job.get('site', 'unknown')[:20]}.txt"
        job_log.write_text(output, encoding="utf-8")

        if stats:
            cost = stats.get("cost_usd", 0)
            ws = get_state(worker_id)
            prev_cost = ws.total_cost if ws else 0.0
            update_state(worker_id, total_cost=prev_cost + cost)

        def _clean_reason(s: str) -> str:
            return re.sub(r'[*`"]+$', '', s).strip()

        for result_status in ["APPLIED", "EXPIRED", "CAPTCHA", "LOGIN_ISSUE"]:
            if f"RESULT:{result_status}" in output:
                add_event(f"[W{worker_id}] {result_status} ({elapsed}s): {job['title'][:30]}")
                update_state(worker_id, status=result_status.lower(),
                             last_action=f"{result_status} ({elapsed}s)")
                return result_status.lower(), duration_ms

        if "RESULT:FAILED" in output:
            for out_line in output.split("\n"):
                if "RESULT:FAILED" in out_line:
                    reason = (
                        out_line.split("RESULT:FAILED:")[-1].strip()
                        if ":" in out_line[out_line.index("FAILED") + 6:]
                        else "unknown"
                    )
                    reason = _clean_reason(reason)
                    PROMOTE_TO_STATUS = {"captcha", "expired", "login_issue"}
                    if reason in PROMOTE_TO_STATUS:
                        add_event(f"[W{worker_id}] {reason.upper()} ({elapsed}s): {job['title'][:30]}")
                        update_state(worker_id, status=reason,
                                     last_action=f"{reason.upper()} ({elapsed}s)")
                        return reason, duration_ms
                    add_event(f"[W{worker_id}] FAILED ({elapsed}s): {reason[:30]}")
                    update_state(worker_id, status="failed",
                                 last_action=f"FAILED: {reason[:25]}")
                    return f"failed:{reason}", duration_ms
            return "failed:unknown", duration_ms

        # No RESULT: marker was ever emitted. RESULT: stays authoritative
        # whenever present (it carries far more meaning than a process exit
        # code ever could -- expired/captcha/login_issue/failed all exit 0).
        # The exit code only fills the gap for the cases where the agent
        # never got to report one.
        if returncode == 143:
            add_event(f"[W{worker_id}] SIGTERM, turn unfinished ({elapsed}s)")
            update_state(worker_id, status="needs_review",
                         last_action=f"SIGTERM mid-turn ({elapsed}s)")
            return "needs_review:sigterm_unfinished_turn", duration_ms

        if returncode != 0:
            add_event(f"[W{worker_id}] CRASHED exit={returncode} ({elapsed}s)")
            update_state(worker_id, status="failed",
                         last_action=f"crashed exit={returncode}")
            return f"failed:crashed_exit_{returncode}", duration_ms

        add_event(f"[W{worker_id}] NO RESULT ({elapsed}s)")
        update_state(worker_id, status="failed", last_action=f"no result ({elapsed}s)")
        return "failed:no_result_line", duration_ms

    except subprocess.TimeoutExpired:
        # Same ambiguity as a SIGTERM mid-turn: the agent may have already
        # interacted with the real application form before being killed
        # below, so this needs a human look rather than a blind retry.
        duration_ms = int((time.time() - start) * 1000)
        elapsed = int(time.time() - start)
        add_event(f"[W{worker_id}] TIMEOUT, turn unfinished ({elapsed}s)")
        update_state(worker_id, status="needs_review", last_action=f"TIMEOUT mid-turn ({elapsed}s)")
        return "needs_review:timeout_unfinished_turn", duration_ms
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        add_event(f"[W{worker_id}] ERROR: {str(e)[:40]}")
        update_state(worker_id, status="failed", last_action=f"ERROR: {str(e)[:25]}")
        return f"failed:{str(e)[:100]}", duration_ms
    finally:
        with _claude_lock:
            _claude_procs.pop(worker_id, None)
        if proc is not None and proc.poll() is None:
            _kill_process_tree(proc.pid)
        if stderr_thread is not None:
            stderr_thread.join(timeout=5)


# ---------------------------------------------------------------------------
# Permanent failure classification
# ---------------------------------------------------------------------------

PERMANENT_FAILURES: set[str] = {
    "expired", "captcha", "login_issue",
    "not_eligible_location", "not_eligible_salary",
    "already_applied", "account_required",
    "not_a_job_application", "unsafe_permissions",
    "unsafe_verification", "sso_required",
    "site_blocked", "cloudflare_blocked", "blocked_by_cloudflare",
}

PERMANENT_PREFIXES: tuple[str, ...] = ("site_blocked", "cloudflare", "blocked_by")


def _is_permanent_failure(result: str) -> bool:
    """Determine if a failure should never be retried."""
    reason = result.split(":", 1)[-1] if ":" in result else result
    return (
        result in PERMANENT_FAILURES
        or reason in PERMANENT_FAILURES
        or any(reason.startswith(p) for p in PERMANENT_PREFIXES)
    )


# ---------------------------------------------------------------------------
# Worker loop
# ---------------------------------------------------------------------------

def worker_loop(worker_id: int = 0, limit: int = 1,
                target_url: str | None = None,
                min_score: int = 7, headless: bool = False,
                model: str = "sonnet", dry_run: bool = False,
                run_id: int | None = None) -> tuple[int, int]:
    """Run jobs sequentially until limit is reached or queue is empty.

    Args:
        worker_id: Numeric worker identifier.
        limit: Max jobs to process (0 = continuous).
        target_url: Apply to a specific URL.
        min_score: Minimum fit_score threshold.
        headless: Run Chrome headless.
        model: Claude model name.
        dry_run: Don't click Submit.
        run_id: The apply run this worker's attempts belong to.

    Returns:
        Tuple of (applied_count, failed_count).
    """
    applied = 0
    failed = 0
    continuous = limit == 0
    jobs_done = 0
    empty_polls = 0
    port = BASE_CDP_PORT + worker_id

    while not _stop_event.is_set():
        if not continuous and jobs_done >= limit:
            break

        update_state(worker_id, status="idle", job_title="", company="",
                     last_action="waiting for job", actions=0)

        job = acquire_job(target_url=target_url, min_score=min_score,
                          worker_id=worker_id, run_id=run_id)
        if not job:
            if not continuous:
                add_event(f"[W{worker_id}] Queue empty")
                update_state(worker_id, status="done", last_action="queue empty")
                break
            empty_polls += 1
            update_state(worker_id, status="idle",
                         last_action=f"polling ({empty_polls})")
            if empty_polls == 1:
                add_event(f"[W{worker_id}] Queue empty, polling every {POLL_INTERVAL}s...")
            # Use Event.wait for interruptible sleep
            if _stop_event.wait(timeout=POLL_INTERVAL):
                break  # Stop was requested during wait
            continue

        empty_polls = 0

        chrome_proc = None
        try:
            add_event(f"[W{worker_id}] Launching Chrome...")
            chrome_proc = launch_chrome(worker_id, port=port, headless=headless)

            result, duration_ms = run_job(job, port=port, worker_id=worker_id,
                                            model=model, dry_run=dry_run)

            if result == "skipped":
                release_lock(job["attempt_id"], job["url"])
                add_event(f"[W{worker_id}] Skipped: {job['title'][:30]}")
                continue
            elif result == "applied":
                mark_result(job["attempt_id"], job["url"], "applied", duration_ms=duration_ms)
                applied += 1
                update_state(worker_id, jobs_applied=applied,
                             jobs_done=applied + failed)
            elif result.startswith("needs_review"):
                # Turn was cut off (SIGTERM/timeout) with no RESULT: marker --
                # we can't tell if the agent already touched the real form,
                # so this needs a human look rather than a blind retry.
                reason = result.split(":", 1)[-1] if ":" in result else result
                mark_result(job["attempt_id"], job["url"], "needs_review", reason,
                            permanent=False, duration_ms=duration_ms)
                failed += 1
                update_state(worker_id, jobs_failed=failed,
                             jobs_done=applied + failed)
            else:
                reason = result.split(":", 1)[-1] if ":" in result else result
                mark_result(job["attempt_id"], job["url"], "failed", reason,
                            permanent=_is_permanent_failure(result),
                            duration_ms=duration_ms)
                failed += 1
                update_state(worker_id, jobs_failed=failed,
                             jobs_done=applied + failed)

        except KeyboardInterrupt:
            release_lock(job["attempt_id"], job["url"])
            if _stop_event.is_set():
                break
            add_event(f"[W{worker_id}] Job skipped (Ctrl+C)")
            continue
        except Exception as e:
            logger.exception("Worker %d launcher error", worker_id)
            add_event(f"[W{worker_id}] Launcher error: {str(e)[:40]}")
            release_lock(job["attempt_id"], job["url"])
            failed += 1
            update_state(worker_id, jobs_failed=failed)
        finally:
            if chrome_proc:
                cleanup_worker(worker_id, chrome_proc)

        jobs_done += 1
        if target_url:
            break

    update_state(worker_id, status="done", last_action="finished")
    return applied, failed


# ---------------------------------------------------------------------------
# Main entry point (called from cli.py)
# ---------------------------------------------------------------------------

def main(limit: int = 1, target_url: str | None = None,
         min_score: int = 7, headless: bool = False, model: str = "sonnet",
         dry_run: bool = False, continuous: bool = False,
         poll_interval: int = 60, workers: int = 1) -> None:
    """Launch the apply pipeline.

    Args:
        limit: Max jobs to apply to (0 or with continuous=True means run forever).
        target_url: Apply to a specific URL.
        min_score: Minimum fit_score threshold.
        headless: Run Chrome in headless mode.
        model: Claude model name.
        dry_run: Don't click Submit.
        continuous: Run forever, polling for new jobs.
        poll_interval: Seconds between DB polls when queue is empty.
        workers: Number of parallel workers (default 1).
    """
    global POLL_INTERVAL
    POLL_INTERVAL = poll_interval
    _stop_event.clear()

    config.ensure_dirs()
    console = Console()

    conn = get_connection()

    # A worker that died mid-attempt in a previous run leaves its attempt
    # (and the job's apply_status mirror) stuck 'in_progress' forever unless
    # something notices. Do that here, once, before claiming any new work.
    recovered = recover_orphaned_attempts(conn)
    if recovered:
        console.print(
            f"[yellow]Recovered {len(recovered)} orphaned attempt(s) "
            f"from a previous run -> needs_review[/yellow]"
        )

    run_id = start_run(conn, "apply", {
        "limit": limit, "target_url": target_url, "min_score": min_score,
        "headless": headless, "model": model, "dry_run": dry_run,
        "continuous": continuous, "poll_interval": poll_interval, "workers": workers,
    })

    if continuous:
        effective_limit = 0
        mode_label = "continuous"
    else:
        effective_limit = limit
        mode_label = f"{limit} jobs"

    # Initialize dashboard for all workers
    for i in range(workers):
        init_worker(i)

    worker_label = f"{workers} worker{'s' if workers > 1 else ''}"
    console.print(f"Launching apply pipeline ({mode_label}, {worker_label}, poll every {POLL_INTERVAL}s)...")
    console.print("[dim]Ctrl+C = skip current job(s) | Ctrl+C x2 = stop[/dim]")

    # Double Ctrl+C handler
    _ctrl_c_count = 0

    def _sigint_handler(sig, frame):
        nonlocal _ctrl_c_count
        _ctrl_c_count += 1
        if _ctrl_c_count == 1:
            console.print("\n[yellow]Skipping current job(s)... (Ctrl+C again to STOP)[/yellow]")
            # Kill all active Claude processes to skip current jobs
            with _claude_lock:
                for wid, cproc in list(_claude_procs.items()):
                    if cproc.poll() is None:
                        _kill_process_tree(cproc.pid)
        else:
            console.print("\n[red bold]STOPPING[/red bold]")
            _stop_event.set()
            with _claude_lock:
                for wid, cproc in list(_claude_procs.items()):
                    if cproc.poll() is None:
                        _kill_process_tree(cproc.pid)
            kill_all_chrome()
            raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _sigint_handler)

    run_status = "interrupted"
    try:
        with Live(render_full(), console=console, refresh_per_second=2) as live:
            # Daemon thread for display refresh only (no business logic)
            _dashboard_running = True

            def _refresh():
                while _dashboard_running:
                    live.update(render_full())
                    time.sleep(0.5)

            refresh_thread = threading.Thread(target=_refresh, daemon=True)
            refresh_thread.start()

            if workers == 1:
                # Single worker — run directly in main thread
                total_applied, total_failed = worker_loop(
                    worker_id=0,
                    limit=effective_limit,
                    target_url=target_url,
                    min_score=min_score,
                    headless=headless,
                    model=model,
                    dry_run=dry_run,
                    run_id=run_id,
                )
            else:
                # Multi-worker — distribute limit across workers
                if effective_limit:
                    base = effective_limit // workers
                    extra = effective_limit % workers
                    limits = [base + (1 if i < extra else 0)
                              for i in range(workers)]
                else:
                    limits = [0] * workers  # continuous mode

                with ThreadPoolExecutor(max_workers=workers,
                                        thread_name_prefix="apply-worker") as executor:
                    futures = {
                        executor.submit(
                            worker_loop,
                            worker_id=i,
                            limit=limits[i],
                            target_url=target_url,
                            min_score=min_score,
                            headless=headless,
                            model=model,
                            dry_run=dry_run,
                            run_id=run_id,
                        ): i
                        for i in range(workers)
                    }

                    results: list[tuple[int, int]] = []
                    for future in as_completed(futures):
                        wid = futures[future]
                        try:
                            results.append(future.result())
                        except Exception:
                            logger.exception("Worker %d crashed", wid)
                            results.append((0, 0))

                total_applied = sum(r[0] for r in results)
                total_failed = sum(r[1] for r in results)

            _dashboard_running = False
            refresh_thread.join(timeout=2)
            live.update(render_full())

        totals = get_totals()
        console.print(
            f"\n[bold]Done: {total_applied} applied, {total_failed} failed "
            f"(${totals['cost']:.3f})[/bold]"
        )
        console.print(f"Logs: {config.LOG_DIR}")

        run_status = "completed"
    except KeyboardInterrupt:
        run_status = "interrupted"
    finally:
        _stop_event.set()
        kill_all_chrome()
        end_run(conn, run_id, status=run_status, stats=get_totals())
