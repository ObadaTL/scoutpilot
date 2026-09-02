"""ScoutPilot CLI — the main entry point."""

from __future__ import annotations

import logging
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from scoutpilot import __version__

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)

app = typer.Typer(
    name="scoutpilot",
    help="Scout early-career jobs: discover, score, and tailor your CV per role. "
    "Auto-apply is available but optional — it runs only where applying is cheap.",
    no_args_is_help=True,
)
console = Console()
log = logging.getLogger(__name__)

# Valid pipeline stages (in execution order)
VALID_STAGES = ("discover", "enrich", "score", "tailor", "cover", "pdf")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bootstrap() -> None:
    """Common setup: load env, create dirs, init DB."""
    from scoutpilot.config import load_env, ensure_dirs
    from scoutpilot.database import init_db

    load_env()
    ensure_dirs()
    init_db()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold]scoutpilot[/bold] {__version__}")
        raise typer.Exit()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """ScoutPilot — scouts early-career jobs, scores fit, and tailors your CV per role.

    Auto-apply is an optional last stage, run only where applying is cheap.
    """


@app.command()
def init() -> None:
    """Run the first-time setup wizard (profile, resume, search config)."""
    from scoutpilot.wizard.init import run_wizard

    run_wizard()


@app.command()
def run(
    stages: Optional[list[str]] = typer.Argument(
        None,
        help=(
            "Pipeline stages to run. "
            f"Valid: {', '.join(VALID_STAGES)}, all. "
            "Defaults to 'all' if omitted."
        ),
    ),
    min_score: int = typer.Option(7, "--min-score", help="Minimum fit score for tailor/cover stages."),
    workers: int = typer.Option(1, "--workers", "-w", help="Parallel threads for discovery/enrichment stages."),
    stream: bool = typer.Option(False, "--stream", help="Run stages concurrently (streaming mode)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview stages without executing."),
    validation: Optional[str] = typer.Option(
        None,
        "--validation",
        help=(
            "Validation strictness for tailor/cover stages. "
            "strict: banned words = errors, judge must pass. "
            "normal: banned words = warnings only (recommended for a cloud provider). "
            "lenient: banned words ignored, LLM judge skipped (fastest, fewest calls). "
            "Default: auto-picks 'lenient' for a local LLM_URL provider (skips the "
            "judge -- a same-size local model judging its own output is slow and not "
            "much more trustworthy than the writer) or 'normal' for a cloud provider."
        ),
    ),
) -> None:
    """Run pipeline stages: discover, enrich, score, tailor, cover, pdf."""
    _bootstrap()

    if validation is None:
        from scoutpilot.llm import is_local_provider
        validation = "lenient" if is_local_provider() else "normal"
        console.print(
            f"[dim]--validation not set -- auto-selected '{validation}' "
            f"({'local model, skipping LLM judge' if validation == 'lenient' else 'cloud provider'})[/dim]"
        )

    from scoutpilot.pipeline import run_pipeline

    stage_list = stages if stages else ["all"]

    # Validate stage names
    for s in stage_list:
        if s != "all" and s not in VALID_STAGES:
            console.print(
                f"[red]Unknown stage:[/red] '{s}'. "
                f"Valid stages: {', '.join(VALID_STAGES)}, all"
            )
            raise typer.Exit(code=1)

    # Gate AI stages behind Tier 2
    llm_stages = {"score", "tailor", "cover"}
    if any(s in stage_list for s in llm_stages) or "all" in stage_list:
        from scoutpilot.config import check_tier
        check_tier(2, "AI scoring/tailoring")

    # Validate the --validation flag value
    valid_modes = ("strict", "normal", "lenient")
    if validation not in valid_modes:
        console.print(
            f"[red]Invalid --validation value:[/red] '{validation}'. "
            f"Choose from: {', '.join(valid_modes)}"
        )
        raise typer.Exit(code=1)

    result = run_pipeline(
        stages=stage_list,
        min_score=min_score,
        dry_run=dry_run,
        stream=stream,
        workers=workers,
        validation_mode=validation,
    )

    if result.get("errors"):
        raise typer.Exit(code=1)


@app.command()
def apply(
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Max applications to submit."),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of parallel browser workers."),
    min_score: int = typer.Option(7, "--min-score", help="Minimum fit score for job selection."),
    model: str = typer.Option("haiku", "--model", "-m", help="Claude model name."),
    continuous: bool = typer.Option(False, "--continuous", "-c", help="Run forever, polling for new jobs."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview actions without submitting."),
    headless: bool = typer.Option(False, "--headless", help="Run browsers in headless mode."),
    url: Optional[str] = typer.Option(None, "--url", help="Apply to a specific job URL."),
    gen: bool = typer.Option(False, "--gen", help="Generate prompt file for manual debugging instead of running."),
    mark_applied: Optional[str] = typer.Option(None, "--mark-applied", help="Manually mark a job URL as applied."),
    mark_failed: Optional[str] = typer.Option(None, "--mark-failed", help="Manually mark a job URL as failed (provide URL)."),
    fail_reason: Optional[str] = typer.Option(None, "--fail-reason", help="Reason for --mark-failed."),
    reset_failed: bool = typer.Option(False, "--reset-failed", help="Reset all failed jobs for retry."),
) -> None:
    """Launch auto-apply to submit job applications."""
    _bootstrap()

    from scoutpilot.config import check_tier, PROFILE_PATH as _profile_path
    from scoutpilot.database import get_connection

    # --- Utility modes (no Chrome/Claude needed) ---

    if mark_applied:
        from scoutpilot.apply.launcher import mark_job
        mark_job(mark_applied, "applied")
        console.print(f"[green]Marked as applied:[/green] {mark_applied}")
        return

    if mark_failed:
        from scoutpilot.apply.launcher import mark_job
        mark_job(mark_failed, "failed", reason=fail_reason)
        console.print(f"[yellow]Marked as failed:[/yellow] {mark_failed} ({fail_reason or 'manual'})")
        return

    if reset_failed:
        from scoutpilot.apply.launcher import reset_failed as do_reset
        count = do_reset()
        console.print(f"[green]Reset {count} failed job(s) for retry.[/green]")
        return

    # --- Full apply mode ---

    # Check 1: Tier 3 required (Claude Code CLI + Chrome)
    check_tier(3, "auto-apply")

    # Check 2: Profile exists
    if not _profile_path.exists():
        console.print(
            "[red]Profile not found.[/red]\n"
            "Run [bold]scoutpilot init[/bold] to create your profile first."
        )
        raise typer.Exit(code=1)

    # Check 3: Tailored resumes exist (skip for --gen with --url)
    if not (gen and url):
        conn = get_connection()
        ready = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE tailored_resume_path IS NOT NULL AND applied_at IS NULL"
        ).fetchone()[0]
        if ready == 0:
            console.print(
                "[red]No tailored resumes ready.[/red]\n"
                "Run [bold]scoutpilot run score tailor[/bold] first to prepare applications."
            )
            raise typer.Exit(code=1)

    if gen:
        from scoutpilot.apply.launcher import gen_prompt, BASE_CDP_PORT
        target = url or ""
        if not target:
            console.print("[red]--gen requires --url to specify which job.[/red]")
            raise typer.Exit(code=1)
        prompt_file = gen_prompt(target, min_score=min_score, model=model)
        if not prompt_file:
            console.print("[red]No matching job found for that URL.[/red]")
            raise typer.Exit(code=1)
        mcp_path = _profile_path.parent / ".mcp-apply-0.json"
        console.print(f"[green]Wrote prompt to:[/green] {prompt_file}")
        console.print(f"\n[bold]Run manually:[/bold]")
        console.print(
            f"  claude --model {model} -p "
            f"--mcp-config {mcp_path} "
            f"--permission-mode bypassPermissions < {prompt_file}"
        )
        return

    from scoutpilot.apply.launcher import main as apply_main

    effective_limit = limit if limit is not None else (0 if continuous else 1)

    console.print("\n[bold blue]Launching Auto-Apply[/bold blue]")
    console.print(f"  Limit:    {'unlimited' if continuous else effective_limit}")
    console.print(f"  Workers:  {workers}")
    console.print(f"  Model:    {model}")
    console.print(f"  Headless: {headless}")
    console.print(f"  Dry run:  {dry_run}")
    if url:
        console.print(f"  Target:   {url}")
    console.print()

    apply_main(
        limit=effective_limit,
        target_url=url,
        min_score=min_score,
        headless=headless,
        model=model,
        dry_run=dry_run,
        continuous=continuous,
        workers=workers,
    )


@app.command()
def discover(
    ats: bool = typer.Option(False, "--ats", help="Run Direct ATS harvester (Greenhouse, Ashby, Lever)."),
    hn: bool = typer.Option(False, "--hn", help="Run Hacker News 'Who is Hiring?' harvester."),
    schemes: bool = typer.Option(False, "--schemes", help="Run Graduate Schemes & Funded Training harvester."),
    companies: bool = typer.Option(False, "--companies", help="Run company-first (employer career page) harvester."),
    gradboards: bool = typer.Option(False, "--gradboards", help="Run NI/UK graduate job-board harvesters (NIJobs, ...)."),
    dorking: bool = typer.Option(False, "--dorking", help="Run Search Operator / Dorking discovery."),
    jobspy: bool = typer.Option(False, "--jobspy", help="Run JobSpy boards crawl."),
    workday: bool = typer.Option(False, "--workday", help="Run Workday corporate scraper."),
    all_channels: bool = typer.Option(False, "--all", "-a", help="Run all discovery channels."),
    workers: int = typer.Option(4, "--workers", "-w", help="Number of worker threads."),
) -> None:
    """Run specific or all discovery harvesters to find jobs, graduate schemes, and funded training."""
    _bootstrap()

    run_all = all_channels or not (ats or hn or schemes or companies or gradboards or dorking or jobspy or workday)

    console.print("\n[bold blue]Starting Opportunity Discovery[/bold blue]\n")

    if run_all or ats:
        console.print("[cyan]Running Direct ATS Harvester (Greenhouse, Ashby, Lever)...[/cyan]")
        from scoutpilot.discovery.direct_ats import run_direct_ats_discovery
        res = run_direct_ats_discovery(workers=workers)
        console.print(f"  [green]ATS Result:[/green] {res.get('new', 0)} new / {res.get('total_found', 0)} found")

    if run_all or schemes:
        console.print("[cyan]Running Graduate Schemes & Funded Training Harvester...[/cyan]")
        from scoutpilot.discovery.schemes_and_training import run_schemes_discovery
        res = run_schemes_discovery()
        console.print(f"  [green]Schemes Result:[/green] {res.get('new', 0)} new / {res.get('total_found', 0)} found")

    if run_all or companies:
        console.print("[cyan]Running Company-First Harvester (employer career pages)...[/cyan]")
        from scoutpilot.discovery.company_pages import run_company_pages_discovery
        res = run_company_pages_discovery(workers=workers)
        console.print(f"  [green]Company Pages Result:[/green] {res.get('new', 0)} new / {res.get('total_found', 0)} found "
                      f"across {res.get('employers', 0)} employers")

    if run_all or gradboards:
        console.print("[cyan]Running NI/UK Graduate Job-Board Harvesters...[/cyan]")
        from scoutpilot.discovery.grad_boards import run_grad_boards_discovery
        res = run_grad_boards_discovery()
        console.print(f"  [green]Grad Boards Result:[/green] {res.get('new', 0)} new / {res.get('total_found', 0)} found "
                      f"across {res.get('boards', 0)} boards")

    if run_all or hn:
        console.print("[cyan]Running Hacker News 'Who is Hiring?' Harvester...[/cyan]")
        from scoutpilot.discovery.hacker_news import run_hn_discovery
        res = run_hn_discovery(workers=workers)
        console.print(f"  [green]Hacker News Result:[/green] {res.get('new', 0)} new / {res.get('total_found', 0)} found")

    if run_all or dorking:
        console.print("[cyan]Running Search Operator / ATS Dorking Discovery...[/cyan]")
        from scoutpilot.discovery.dorking import run_dorking_discovery
        res = run_dorking_discovery()
        console.print(f"  [green]Dorking Result:[/green] {res.get('new', 0)} new / {res.get('total_found', 0)} found")

    if run_all or jobspy:
        console.print("[cyan]Running JobSpy Aggregate Crawl...[/cyan]")
        from scoutpilot.discovery.jobspy import run_discovery
        res = run_discovery()
        console.print(f"  [green]JobSpy Result:[/green] {res.get('new', 0)} new")

    if run_all or workday:
        console.print("[cyan]Running Workday Corporate Scraper...[/cyan]")
        from scoutpilot.discovery.workday import run_workday_discovery
        res = run_workday_discovery(workers=workers)
        console.print(f"  [green]Workday Result:[/green] {res.get('new', 0)} new")

    console.print("\n[bold green]Discovery complete. Check status with `scoutpilot status`.[/bold green]\n")


@app.command()
def score(
    limit: int = typer.Option(50, "--limit", "-l", help="Number of jobs to score in this batch (0 = all)."),
    channel: Optional[str] = typer.Option(None, "--channel", "-c", help="Filter scoring to one channel (schemes, hn, direct_ats, dorking, workday)."),
    opp_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by opportunity type (graduate_scheme, funded_training, direct_job)."),
    keywords: Optional[str] = typer.Option(None, "--keywords", "-k", help="Filter scoring to specific keywords (e.g. 'ai, python, signal processing, machine learning')."),
    cohort: Optional[str] = typer.Option(None, "--cohort", help="Filter by start date/cohort: 'immediate', a year like '2026', or 'future'."),
    rescore: bool = typer.Option(False, "--rescore", help="Re-score already scored jobs."),
) -> None:
    """Score unscored jobs with the LLM in prioritized, manageable batches."""
    _bootstrap()

    from scoutpilot.config import check_tier
    check_tier(2, "AI scoring")

    # Map shorthand channel names
    channel_map = {
        "schemes": "graduate_schemes",
        "hn": "hacker_news",
        "ats": "direct_ats",
        "dorking": "dorking",
        "workday": "workday",
    }
    actual_channel = channel_map.get(channel, channel) if channel else None

    console.print("\n[bold blue]Starting Batch LLM Scoring[/bold blue]")
    console.print(f"  Batch limit:   {'All available' if limit == 0 else limit}")
    if actual_channel:
        console.print(f"  Channel:       {actual_channel}")
    if opp_type:
        console.print(f"  Type:          {opp_type}")
    if keywords:
        console.print(f"  Keywords:      {keywords}")
    if cohort:
        console.print(f"  Cohort:        {cohort}")
    console.print()

    from scoutpilot.scoring.scorer import run_scoring
    result = run_scoring(
        limit=limit,
        rescore=rescore,
        channel=actual_channel,
        opp_type=opp_type,
        keywords=keywords,
        cohort=cohort,
    )

    console.print(f"\n[bold green]Scored {result.get('scored', 0)} jobs in {result.get('elapsed', 0.0):.1f}s ({result.get('errors', 0)} errors).[/bold green]\n")


@app.command()
def clean() -> None:
    """Clean the queue by hiding irrelevant non-engineering roles (Sales, Marketing, HR, etc.)."""
    _bootstrap()
    from scoutpilot.database import clean_non_tech_jobs
    console.print("\n[bold blue]Cleaning non-engineering jobs from scoring queue...[/bold blue]")
    count = clean_non_tech_jobs()
    console.print(f"[bold green]Hidden {count} irrelevant non-engineering jobs from the queue.[/bold green]\n")


@app.command(name="archive-discovery")
def archive_discovery(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
) -> None:
    """Set aside the current discovery backlog before a fresh search.

    Stamps one timestamp on every discovered row that hasn't been tailored
    or applied to. Nothing is deleted; applied/tailored history is
    untouched. Work-acquisition (score/tailor) skips archived rows. The
    exact undo command is written to ~/.applypilot/last_discovery_archive.txt.
    """
    _bootstrap()
    from scoutpilot.database import get_connection, archive_discovery_results

    conn = get_connection()
    pending = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE archived_at IS NULL "
        "AND tailored_resume_path IS NULL AND applied_at IS NULL"
    ).fetchone()[0]
    if not pending:
        console.print("[yellow]Nothing to archive.[/yellow]")
        raise typer.Exit()
    if not yes:
        import typer as _t
        if not _t.confirm(f"Archive {pending} discovery rows (reversible)?"):
            raise typer.Exit()

    res = archive_discovery_results(conn)
    console.print(
        f"[bold green]Archived {res['archived']} rows[/bold green] at {res['timestamp']}.\n"
        f"Undo instructions: {res['note_path']}"
    )


@app.command(name="restore-discovery")
def restore_discovery(
    timestamp: Optional[str] = typer.Option(None, "--timestamp", help="Restore only this archive batch (default: all)."),
) -> None:
    """Reverse `archive-discovery` — bring archived discovery rows back."""
    _bootstrap()
    from scoutpilot.database import get_connection, unarchive_discovery_results

    n = unarchive_discovery_results(get_connection(), timestamp)
    console.print(f"[bold green]Restored {n} archived rows.[/bold green]")


@app.command()
def status() -> None:
    """Show pipeline statistics from the database."""
    _bootstrap()

    from scoutpilot.database import get_connection, get_stats, source_hit_rates

    stats = get_stats()
    conn = get_connection()
    filtered_at_ingest = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE prefilter_reason IS NOT NULL"
    ).fetchone()[0]
    archived = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE archived_at IS NOT NULL"
    ).fetchone()[0]
    hit_rates = source_hit_rates(conn)

    console.print("\n[bold]ScoutPilot Pipeline Status[/bold]\n")

    # Summary table
    summary = Table(title="Pipeline Overview", show_header=True, header_style="bold cyan")
    summary.add_column("Metric", style="bold")
    summary.add_column("Count", justify="right")

    summary.add_row("Total jobs discovered", str(stats["total"]))
    if archived:
        summary.add_row("  archived (set aside)", str(archived))
    summary.add_row("With full description", str(stats["with_description"]))
    summary.add_row("Pending enrichment", str(stats["pending_detail"]))
    summary.add_row("Enrichment errors", str(stats["detail_errors"]))
    summary.add_row("Scored by LLM", str(stats["scored"]))
    summary.add_row("Pending scoring", str(stats["unscored"]))
    summary.add_row("Filtered at ingest", str(filtered_at_ingest))
    summary.add_row("Tailored resumes", str(stats["tailored"]))
    summary.add_row("Pending tailoring (7+)", str(stats["untailored_eligible"]))
    summary.add_row("Cover letters", str(stats["with_cover_letter"]))
    summary.add_row("Ready to apply", str(stats["ready_to_apply"]))
    summary.add_row("Applied", str(stats["applied"]))
    summary.add_row("Apply errors", str(stats["apply_errors"]))

    console.print(summary)

    # Score distribution
    if stats["score_distribution"]:
        dist_table = Table(title="\nScore Distribution", show_header=True, header_style="bold yellow")
        dist_table.add_column("Score", justify="center")
        dist_table.add_column("Count", justify="right")
        dist_table.add_column("Bar")

        max_count = max(count for _, count in stats["score_distribution"]) or 1
        for score, count in stats["score_distribution"]:
            bar_len = int(count / max_count * 30)
            if score >= 7:
                color = "green"
            elif score >= 5:
                color = "yellow"
            else:
                color = "red"
            bar = f"[{color}]{'=' * bar_len}[/{color}]"
            dist_table.add_row(str(score), str(count), bar)

        console.print(dist_table)

    # By site, with live hit rate (share of scored jobs reaching fit 7+).
    # This is the number that orders the scoring queue: high-yield sources
    # first, low-yield trusted sources sampled rather than scored in full.
    if stats["by_site"]:
        site_table = Table(title="\nJobs by Source (hit rate = fit 7+ / scored)",
                           show_header=True, header_style="bold magenta")
        site_table.add_column("Site")
        site_table.add_column("Total", justify="right")
        site_table.add_column("Scored", justify="right")
        site_table.add_column("Fit 7+", justify="right")
        site_table.add_column("Hit rate", justify="right")
        site_table.add_column("Queue", justify="left")

        for site, count in stats["by_site"]:
            key = site or "?"
            hr = hit_rates.get(key)
            if not hr or hr["scored"] == 0:
                site_table.add_row(site or "Unknown", str(count), "0", "0", "-", "unknown")
                continue
            if not hr["trusted"]:
                queue = "[yellow]unknown[/yellow]"
            elif hr["rate"] > 0.05:
                queue = "[green]priority[/green]"
            else:
                queue = "[red]sampled[/red]"
            site_table.add_row(
                site or "Unknown", str(count), str(hr["scored"]), str(hr["hits"]),
                f"{hr['rate'] * 100:.0f}%", queue,
            )

        console.print(site_table)

    console.print()


@app.command()
def jobs(
    min_fit: int = typer.Option(0, "--min-fit", help="Minimum fit score."),
    limit: int = typer.Option(20, "--limit", "-l", help="Max jobs to show."),
    site: Optional[str] = typer.Option(None, "--site", help="Filter to one source site."),
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status (applied, ready, failed, in_progress)."),
    tailored: bool = typer.Option(False, "--tailored", help="Show only jobs with a tailored resume."),
) -> None:
    """List individual jobs with fit score, company context, CV/cover letter links, and application status."""
    _bootstrap()

    from scoutpilot.terminal_view import list_jobs, render_jobs

    matched = list_jobs(min_fit=min_fit, limit=limit, site=site, status=status, tailored_only=tailored)
    render_jobs(matched, console)


@app.command()
def logs(
    worker: int = typer.Option(0, "--worker", "-w", help="Worker ID to show logs for."),
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show from the end."),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output in real-time."),
    stderr: bool = typer.Option(False, "--stderr", help="View stderr log instead of main worker log."),
) -> None:
    """View or stream worker logs in real time."""
    import time
    from scoutpilot.config import LOG_DIR

    log_filename = f"worker-{worker}-stderr.log" if stderr else f"worker-{worker}.log"
    log_path = LOG_DIR / log_filename

    if not log_path.exists():
        console.print(f"[yellow]No log file found at:[/yellow] {log_path}")
        return

    console.print(f"[bold cyan]ScoutPilot Log:[/bold cyan] {log_path}\n")

    import sys

    def _safe_print(text: str) -> None:
        try:
            console.print(text, highlight=False, markup=False, emoji=False)
        except Exception:
            sys.stdout.buffer.write(f"{text}\n".encode("utf-8", errors="replace"))
            sys.stdout.buffer.flush()

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            for line in all_lines[-lines:]:
                _safe_print(line.rstrip())

            if follow:
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if line:
                        _safe_print(line.rstrip())
                    else:
                        time.sleep(0.5)
    except KeyboardInterrupt:
        pass


@app.command()
def events(
    limit: int = typer.Option(30, "--limit", "-l", help="Number of recent events to display."),
    url: Optional[str] = typer.Option(None, "--url", help="Filter events to a specific job URL."),
) -> None:
    """Show structured event timeline from recent apply attempts."""
    import json
    _bootstrap()
    from scoutpilot.database import get_connection

    conn = get_connection()
    if url:
        query = """
            SELECT e.ts, e.event_type, e.tool_name, e.input_json, e.text, a.job_url, j.title
            FROM attempt_events e
            JOIN attempts a ON e.attempt_id = a.id
            JOIN jobs j ON a.job_url = j.url
            WHERE a.job_url = ?
            ORDER BY e.id DESC LIMIT ?
        """
        rows = conn.execute(query, (url, limit)).fetchall()
    else:
        query = """
            SELECT e.ts, e.event_type, e.tool_name, e.input_json, e.text, a.job_url, j.title
            FROM attempt_events e
            JOIN attempts a ON e.attempt_id = a.id
            JOIN jobs j ON a.job_url = j.url
            ORDER BY e.id DESC LIMIT ?
        """
        rows = conn.execute(query, (limit,)).fetchall()

    if not rows:
        console.print("[dim]No attempt events recorded in database yet.[/dim]")
        return

    events_table = Table(title="Recent Application Events", show_header=True, header_style="bold cyan")
    events_table.add_column("Time", width=10)
    events_table.add_column("Job", min_width=20, max_width=35, no_wrap=True)
    events_table.add_column("Type", width=12)
    events_table.add_column("Details", min_width=30)

    for row in reversed(rows):
        ts = row["ts"][11:19] if row["ts"] and len(row["ts"]) >= 19 else (row["ts"] or "")
        ev_type = row["event_type"]
        details = ""
        if ev_type == "tool_use":
            tool_name = (row["tool_name"] or "").replace("mcp__playwright__", "").replace("mcp__gmail__", "gmail:")
            inp = json.loads(row["input_json"]) if row["input_json"] else {}
            if "url" in inp:
                details = f"[cyan]{tool_name}[/cyan] {inp['url'][:50]}"
            elif "element" in inp or "text" in inp:
                details = f"[cyan]{tool_name}[/cyan] {inp.get('element', inp.get('text', ''))[:40]}"
            elif "fields" in inp:
                details = f"[cyan]{tool_name}[/cyan] ({len(inp['fields'])} fields)"
            else:
                details = f"[cyan]{tool_name}[/cyan]"
        elif ev_type == "text":
            details = (row["text"] or "").strip().replace("\n", " ")[:60]
        elif ev_type == "system_init":
            details = "[dim]Claude session initialized[/dim]"
        elif ev_type == "result":
            details = "[bold green]Application completed[/bold green]"
        else:
            details = ev_type

        events_table.add_row(ts, row["title"] or "Unknown", ev_type, details)

    console.print(events_table)


@app.command()
def dashboard(
    static: bool = typer.Option(
        False, "--static",
        help="Write a one-shot HTML snapshot and open it, instead of serving it live. "
             "The in-page Refresh button won't pull new data in this mode -- the file "
             "only updates the next time this command runs.",
    ),
) -> None:
    """Open the HTML dashboard in your browser.

    Serves it live by default (regenerates from the DB on every load, so
    the in-page Refresh button and browser reload both show current data)
    and keeps running until you press Ctrl+C.
    """
    _bootstrap()

    if static:
        from scoutpilot.view import open_dashboard
        open_dashboard()
        return

    from scoutpilot.view import serve_dashboard

    serve_dashboard()


@app.command()
def doctor() -> None:
    """Check your setup and diagnose missing requirements."""
    import shutil
    from scoutpilot.config import (
        load_env, PROFILE_PATH, RESUME_PATH, RESUME_PDF_PATH,
        SEARCH_CONFIG_PATH, ENV_PATH, get_chrome_path,
    )

    load_env()

    ok_mark = "[green]OK[/green]"
    fail_mark = "[red]MISSING[/red]"
    warn_mark = "[yellow]WARN[/yellow]"

    results: list[tuple[str, str, str]] = []  # (check, status, note)

    # --- Tier 1 checks ---
    # Profile
    if PROFILE_PATH.exists():
        results.append(("profile.json", ok_mark, str(PROFILE_PATH)))
    else:
        results.append(("profile.json", fail_mark, "Run 'scoutpilot init' to create"))

    # Resume
    if RESUME_PATH.exists():
        results.append(("resume.txt", ok_mark, str(RESUME_PATH)))
    elif RESUME_PDF_PATH.exists():
        results.append(("resume.txt", warn_mark, "Only PDF found — plain-text needed for AI stages"))
    else:
        results.append(("resume.txt", fail_mark, "Run 'scoutpilot init' to add your resume"))

    # Profile URLs -- a typo'd github/linkedin/portfolio link is invisible
    # until a recruiter actually clicks it, and nothing else in this
    # pipeline ever fetches these to notice. Only checked when profile.json
    # exists; each URL gets a real request, so this is the one doctor check
    # that needs network access and can take a few seconds.
    if PROFILE_PATH.exists():
        import urllib.error
        import urllib.request

        def _check_url_reachable(url: str, timeout: float = 5.0) -> tuple[bool, str]:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ScoutPilot doctor)"})
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return True, f"HTTP {resp.status}"
            except urllib.error.HTTPError as e:
                # A site blocking bots with 403 (LinkedIn does this reliably)
                # isn't evidence the URL is broken -- only a definite 404/410
                # is worth failing doctor over.
                if e.code in (404, 410):
                    return False, f"HTTP {e.code}"
                return True, f"HTTP {e.code} (server reachable, may just be blocking bots)"
            except Exception as e:  # noqa: BLE001 -- report any failure, don't crash doctor over one bad URL
                return False, str(e)

        try:
            from scoutpilot.config import load_profile
            personal = (load_profile() or {}).get("personal", {}) or {}
        except Exception:
            personal = {}

        for field, label in (
            ("github_url", "GitHub URL"), ("linkedin_url", "LinkedIn URL"),
            ("portfolio_url", "Portfolio URL"), ("website_url", "Website URL"),
        ):
            url = str(personal.get(field) or "").strip()
            if not url:
                continue
            ok, note = _check_url_reachable(url)
            results.append((label, ok_mark if ok else fail_mark, f"{url} -- {note}"))

    # Search config
    if SEARCH_CONFIG_PATH.exists():
        results.append(("searches.yaml", ok_mark, str(SEARCH_CONFIG_PATH)))
    else:
        results.append(("searches.yaml", warn_mark, "Will use example config — run 'scoutpilot init'"))

    # jobspy (discovery dep installed separately)
    try:
        import jobspy  # noqa: F401
        results.append(("python-jobspy", ok_mark, "Job board scraping available"))
    except ImportError:
        results.append(("python-jobspy", warn_mark,
                        "pip install --no-deps python-jobspy && pip install pydantic tls-client requests markdownify regex"))

    # --- Tier 2 checks ---
    import os
    has_gemini = bool(os.environ.get("GEMINI_API_KEY"))
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    has_local = bool(os.environ.get("LLM_URL"))
    if has_gemini:
        model = os.environ.get("LLM_MODEL", "gemini-2.0-flash")
        results.append(("LLM API key", ok_mark, f"Gemini ({model})"))
    elif has_openai:
        model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        results.append(("LLM API key", ok_mark, f"OpenAI ({model})"))
    elif has_local:
        results.append(("LLM API key", ok_mark, f"Local: {os.environ.get('LLM_URL')}"))
    else:
        results.append(("LLM API key", fail_mark,
                        "Set GEMINI_API_KEY in ~/.applypilot/.env (run 'scoutpilot init')"))

    # --- Tier 3 checks ---
    # Claude Code CLI
    claude_bin = shutil.which("claude")
    if claude_bin:
        results.append(("Claude Code CLI", ok_mark, claude_bin))
    else:
        results.append(("Claude Code CLI", fail_mark,
                        "Install from https://claude.ai/code (needed for auto-apply)"))

    # Chrome
    try:
        chrome_path = get_chrome_path()
        results.append(("Chrome/Chromium", ok_mark, chrome_path))
    except FileNotFoundError:
        results.append(("Chrome/Chromium", fail_mark,
                        "Install Chrome or set CHROME_PATH env var (needed for auto-apply)"))

    # Node.js / npx (for Playwright MCP)
    npx_bin = shutil.which("npx")
    if npx_bin:
        results.append(("Node.js (npx)", ok_mark, npx_bin))
    else:
        results.append(("Node.js (npx)", fail_mark,
                        "Install Node.js 18+ from nodejs.org (needed for auto-apply)"))

    # CapSolver (optional)
    capsolver = os.environ.get("CAPSOLVER_API_KEY")
    if capsolver:
        results.append(("CapSolver API key", ok_mark, "CAPTCHA solving enabled"))
    else:
        results.append(("CapSolver API key", "[dim]optional[/dim]",
                        "Set CAPSOLVER_API_KEY in .env for CAPTCHA solving"))

    # --- Render results ---
    console.print()
    console.print("[bold]ScoutPilot Doctor[/bold]\n")

    col_w = max(len(r[0]) for r in results) + 2
    for check, status, note in results:
        pad = " " * (col_w - len(check))
        console.print(f"  {check}{pad}{status}  [dim]{note}[/dim]")

    console.print()

    # Tier summary
    from scoutpilot.config import get_tier, TIER_LABELS
    tier = get_tier()
    console.print(f"[bold]Current tier: Tier {tier} — {TIER_LABELS[tier]}[/bold]")

    if tier == 1:
        console.print("[dim]  → Tier 2 unlocks: scoring, tailoring, cover letters (needs LLM API key)[/dim]")
        console.print("[dim]  → Tier 3 unlocks: auto-apply (needs Claude Code CLI + Chrome + Node.js)[/dim]")
    elif tier == 2:
        console.print("[dim]  → Tier 3 unlocks: auto-apply (needs Claude Code CLI + Chrome + Node.js)[/dim]")

    console.print()


if __name__ == "__main__":
    app()
