"""Terminal job-detail listing: fit score and company context for individual
jobs, via `scoutpilot jobs`. Separate from `status` (a pipeline health
check) -- this is a job browser.
"""

from __future__ import annotations

from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from scoutpilot.database import get_connection


def list_jobs(min_fit: int = 0, limit: int = 20, site: str | None = None,
              status: str | None = None, tailored_only: bool = False) -> list[dict]:
    """Fetch scored jobs for terminal display, filtered and sorted by fit.

    Args:
        min_fit: Minimum fit_score. Jobs with a NULL fit_score are only
            included when min_fit is 0 (COALESCE(fit_score, 0) >= min_fit).
        limit: Maximum number of jobs to return.
        site: Restrict to one source site, if given.
        status: Filter by apply_status (e.g. 'applied', 'in_progress', 'failed', 'needs_review').
        tailored_only: If True, only return jobs that have a tailored resume.

    Returns:
        List of job dicts.
    """
    conn = get_connection()

    where_clauses = ["COALESCE(fit_score, 0) >= ?"]
    params: list = [min_fit]

    if site:
        where_clauses.append("site = ?")
        params.append(site)

    if status:
        if status.lower() == "applied":
            where_clauses.append("applied_at IS NOT NULL")
        elif status.lower() == "ready":
            where_clauses.append("tailored_resume_path IS NOT NULL AND applied_at IS NULL")
        else:
            where_clauses.append("apply_status = ?")
            params.append(status)

    if tailored_only:
        where_clauses.append("tailored_resume_path IS NOT NULL")

    params.append(limit)

    query = f"""
        SELECT url, title, site, location, fit_score, company_summary, company_hook,
               gate_reason, critic_score, tailored_resume_path, cover_letter_path, apply_status,
               applied_at, apply_error, application_url
        FROM jobs
        WHERE {' AND '.join(where_clauses)}
        ORDER BY fit_score DESC NULLS LAST, title
        LIMIT ?
    """
    rows = conn.execute(query, params).fetchall()
    if not rows:
        return []
    columns = rows[0].keys()
    return [dict(zip(columns, row)) for row in rows]


def render_jobs(jobs: list[dict], console: Console | None = None) -> None:
    """Render one Rich panel per job with fit score, company context, tailored CV/Cover letter links, and apply status."""
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

        # Application & Pipeline Status
        apply_status = job.get("apply_status")
        applied_at = job.get("applied_at")
        if applied_at or apply_status == "applied":
            status_tag = f"[bold green]APPLIED[/bold green] ({applied_at[:10] if applied_at else ''})"
        elif apply_status == "in_progress":
            status_tag = "[bold yellow]IN PROGRESS[/bold yellow]"
        elif apply_status in ("failed", "needs_review"):
            err = job.get("apply_error") or "error"
            status_tag = f"[bold red]{apply_status.upper()}[/bold red] ({err[:30]})"
        elif job.get("tailored_resume_path"):
            status_tag = "[bold cyan]READY TO APPLY[/bold cyan]"
        else:
            status_tag = "[dim]NOT APPLIED[/dim]"

        critic = job.get("critic_score")
        # "Critic" label, not "fit"-style styling -- this is a computed
        # value from discrete findings, not an LLM-assigned score.
        critic_str = f"  |  Critic: [dim]{critic:.1f}/10 (computed)[/dim]" if critic is not None else ""

        lines = [f"Fit: {fit_str}  |  Status: {status_tag}{critic_str}"]

        if job.get("gate_reason"):
            lines.append("")
            lines.append(f"[bold red]⛔ Eligibility gate:[/bold red] {job['gate_reason']}")

        if job.get("company_summary"):
            lines.append("")
            lines.append(f"[bold]Company:[/bold] {job['company_summary']}")
        if job.get("company_hook"):
            lines.append(f"[bold]Hook:[/bold] [italic]{job['company_hook']}[/italic]")

        # Assets & Document Links
        assets: list[str] = []
        tailored_cv = job.get("tailored_resume_path")
        if tailored_cv:
            cv_p = Path(tailored_cv)
            pdf_p = cv_p.with_suffix(".pdf")
            if pdf_p.exists():
                assets.append(f"[cyan]CV (PDF):[/cyan] [link={pdf_p.as_uri()}]{pdf_p.name}[/link]")
            elif cv_p.exists():
                assets.append(f"[cyan]CV (TXT):[/cyan] [link={cv_p.as_uri()}]{cv_p.name}[/link]")

        cover_letter = job.get("cover_letter_path")
        if cover_letter:
            cl_p = Path(cover_letter)
            cl_pdf = cl_p.with_suffix(".pdf")
            if cl_pdf.exists():
                assets.append(f"[magenta]Cover Letter (PDF):[/magenta] [link={cl_pdf.as_uri()}]{cl_pdf.name}[/link]")
            elif cl_p.exists():
                assets.append(f"[magenta]Cover Letter (TXT):[/magenta] [link={cl_p.as_uri()}]{cl_p.name}[/link]")

        if assets:
            lines.append("")
            lines.extend(assets)

        # Links
        links: list[str] = []
        if job.get("url"):
            links.append(f"[blue]Posting:[/blue] {job['url']}")
        if job.get("application_url"):
            links.append(f"[green]Apply URL:[/green] {job['application_url']}")

        if links:
            lines.append("")
            lines.extend(links)

        title = f"{job.get('title') or 'Untitled'}  @ {job.get('site') or 'Unknown'}"
        console.print(Panel("\n".join(lines), title=title, border_style="blue"))
