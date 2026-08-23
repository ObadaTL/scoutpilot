"""Terminal job-detail listing: fit score and company context for individual
jobs, via `applypilot jobs`. Separate from `status` (a pipeline health
check) -- this is a job browser.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from applypilot.database import get_connection


def list_jobs(min_fit: int = 0, limit: int = 20, site: str | None = None) -> list[dict]:
    """Fetch scored jobs for terminal display, filtered and sorted by fit.

    Args:
        min_fit: Minimum fit_score. Jobs with a NULL fit_score are only
            included when min_fit is 0 (COALESCE(fit_score, 0) >= min_fit).
        limit: Maximum number of jobs to return.
        site: Restrict to one source site, if given.

    Returns:
        List of job dicts (url, title, site, fit_score, company_summary).
    """
    conn = get_connection()

    site_clause = ""
    params: list = [min_fit]
    if site:
        site_clause = "AND site = ?"
        params.append(site)
    params.append(limit)

    query = f"""
        SELECT url, title, site, fit_score, company_summary
        FROM jobs
        WHERE COALESCE(fit_score, 0) >= ?
        {site_clause}
        ORDER BY fit_score DESC NULLS LAST, title
        LIMIT ?
    """
    rows = conn.execute(query, params).fetchall()
    if not rows:
        return []
    columns = rows[0].keys()
    return [dict(zip(columns, row)) for row in rows]


def render_jobs(jobs: list[dict], console: Console | None = None) -> None:
    """Render one Rich panel per job: title/site, fit score, company summary.

    Formatted consistently with how fit_score is already shown elsewhere
    (green >=7, yellow >=5, red below, matching the score coloring already
    used in view.py and cli.py's status distribution table).
    """
    console = console or Console()

    if not jobs:
        console.print("[yellow]No jobs match those filters.[/yellow]")
        return

    for job in jobs:
        fit = job.get("fit_score")
        if fit is None:
            fit_str = "[dim]unscored[/dim]"
        elif fit >= 7:
            fit_str = f"[green]{fit}/10[/green]"
        elif fit >= 5:
            fit_str = f"[yellow]{fit}/10[/yellow]"
        else:
            fit_str = f"[red]{fit}/10[/red]"

        lines = [f"Fit: {fit_str}"]
        if job.get("company_summary"):
            lines.append("")
            lines.append(job["company_summary"])

        title = f"{job.get('title') or 'Untitled'}  @ {job.get('site') or 'Unknown'}"
        console.print(Panel("\n".join(lines), title=title, border_style="blue"))
