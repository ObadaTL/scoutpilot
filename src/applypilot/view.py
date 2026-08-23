"""ApplyPilot HTML Dashboard Generator.

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
import webbrowser
from html import escape
from pathlib import Path

from rich.console import Console

from applypilot.config import APP_DIR, COVER_LETTER_DIR, DB_PATH, TAILORED_DIR
from applypilot.database import get_connection

console = Console()
log = logging.getLogger(__name__)

# Directories serve_dashboard() is willing to stream files from via /files --
# CV/cover-letter assets only, not an arbitrary local-file read.
ASSET_SERVE_ROOTS: tuple[Path, ...] = (TAILORED_DIR, COVER_LETTER_DIR)


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
    ready_to_apply = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE tailored_resume_path IS NOT NULL AND applied_at IS NULL AND application_url IS NOT NULL"
    ).fetchone()[0]
    in_progress = conn.execute("SELECT COUNT(*) FROM jobs WHERE apply_status = 'in_progress'").fetchone()[0]
    failed_apply = conn.execute("SELECT COUNT(*) FROM jobs WHERE apply_status IN ('failed', 'needs_review')").fetchone()[0]

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
               fit_score, score_reasoning, company_summary, company_hook,
               tailored_resume_path, tailored_at, tailor_attempts,
               cover_letter_path, cover_letter_at, cover_attempts,
               applied_at, apply_status, apply_error, apply_attempts,
               last_attempted_at, verification_confidence
        FROM jobs
        WHERE fit_score IS NOT NULL OR tailored_resume_path IS NOT NULL
        ORDER BY fit_score DESC, site, title
    """).fetchall()

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
    for j in jobs:
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
            return (
                f'<a href="{uri}" class="asset-btn {css_class}" target="_blank">{icon} {label} ({kind})</a>'
                f'<button type="button" class="asset-btn preview-btn" '
                f"onclick=\"openPreview('{uri}', '{preview_title}')\">"
                f"\U0001f441️ Preview</button>"
            )

        tailored_cv = j["tailored_resume_path"]
        cover_letter = j["cover_letter_path"]
        asset_links = [
            _asset_buttons(tailored_cv, "cv-btn", "Tailored CV", "\U0001f4c4"),
            _asset_buttons(cover_letter, "cl-btn", "Cover Letter", "✉️"),
        ]
        asset_links = [a for a in asset_links if a]

        assets_html = f'<div class="assets-row">{" ".join(asset_links)}</div>' if asset_links else ""

        # Parse keywords and full reasoning from score_reasoning
        reasoning_raw = j["score_reasoning"] or ""
        reasoning_lines = [ln.strip() for ln in reasoning_raw.split("\n") if ln.strip()]
        keywords_chips = []
        full_reasoning = ""
        if reasoning_lines:
            first_line = reasoning_lines[0]
            if "," in first_line or len(reasoning_lines) > 1:
                kws = [k.strip() for k in first_line.split(",") if k.strip()]
                keywords_chips = [f'<span class="kw-chip">{escape(kw)}</span>' for kw in kws[:12]]
                full_reasoning = "\n\n".join(reasoning_lines[1:])
            else:
                full_reasoning = "\n\n".join(reasoning_lines)

        full_reasoning_html = escape(full_reasoning).replace("\n", "<br>")

        full_desc_text = j["full_description"] or ""
        desc_preview = escape(full_desc_text[:280])
        desc_ellipsis = "..." if len(full_desc_text) > 280 else ""
        full_desc_html = escape(full_desc_text).replace("\n", "<br>")
        desc_len = len(full_desc_text)

        company_summary = escape(j["company_summary"] or "")
        company_hook = escape(j["company_hook"] or "")

        meta_parts = [
            f'<span class="meta-tag site-tag" style="background:{site_color}33;color:{site_color}">{site}</span>'
        ]
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

        job_sections += f"""
        <div class="job-card" data-score="{score}" data-site="{escape(j['site'] or '')}" data-status="{data_status}" data-has-cv="{1 if tailored_cv else 0}" data-has-cl="{1 if cover_letter else 0}">
          <div class="card-header">
            <div class="card-title-group">
              <span class="score-pill" style="background:{'#10b981' if score >= 7 else ('#f59e0b' if score >= 5 else '#ef4444')}">{score}</span>
              <a href="{url}" class="job-title" target="_blank">{title}</a>
            </div>
            {status_pill}
          </div>

          <div class="meta-row">{meta_html}</div>

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

          {assets_html}

          <p class="desc-preview">{desc_preview}{desc_ellipsis}</p>
          {"<details class='full-desc-details'><summary class='expand-btn'>View Full Job Description (" + f'{desc_len:,}' + " chars)</summary><div class='full-desc'>" + full_desc_html + "</div></details>" if j["full_description"] else ""}

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
<title>ApplyPilot Dashboard</title>
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

  /* Filter Controls */
  .filter-panel {{ background: #151d30; border: 1px solid #243049; border-radius: 12px; padding: 1.25rem; margin-bottom: 2rem; display: flex; flex-direction: column; gap: 1rem; }}
  .filter-row {{ display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }}
  .filter-label {{ color: #94a3b8; font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; min-width: 65px; }}

  .filter-btn {{ background: #1e293b; border: 1px solid #334155; color: #cbd5e1; padding: 0.35rem 0.85rem; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; transition: all 0.15s; }}
  .filter-btn:hover {{ background: #334155; color: #ffffff; }}
  .filter-btn.active {{ background: #3b82f6; border-color: #3b82f6; color: #ffffff; font-weight: 700; }}

  .search-input {{ background: #1e293b; border: 1px solid #334155; color: #f8fafc; padding: 0.45rem 1rem; border-radius: 6px; font-size: 0.85rem; flex: 1; min-width: 250px; outline: none; }}
  .search-input:focus {{ border-color: #3b82f6; }}

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

  .meta-row {{ display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.85rem; }}
  .meta-tag {{ font-size: 0.74rem; padding: 0.2rem 0.55rem; border-radius: 6px; background: #1e293b; color: #94a3b8; font-weight: 500; }}
  .meta-tag.salary {{ background: #064e3b44; color: #6ee7b7; border: 1px solid #064e3b; }}
  .meta-tag.location {{ background: #1e3a5f44; color: #93c5fd; border: 1px solid #1e3a5f; }}

  /* Company Box */
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
    <h1>ApplyPilot Dashboard</h1>
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
  </div>

  <div class="filter-row">
    <span class="filter-label">Search:</span>
    <input type="text" class="search-input" placeholder="Search by title, company, skills, location..." oninput="filterText(this.value)">
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
let activeScoreFilter = 'all';
let activeStatusFilter = 'all';
let searchText = '';

function filterScore(val, btn) {{
  activeScoreFilter = val;
  btn.parentElement.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}}

function filterStatus(val, btn) {{
  activeStatusFilter = val;
  btn.parentElement.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}}

function filterText(text) {{
  searchText = text.toLowerCase();
  applyFilters();
}}

function applyFilters() {{
  let shown = 0;
  let total = 0;

  document.querySelectorAll('.job-card').forEach(card => {{
    total++;
    const score = parseInt(card.dataset.score) || 0;
    const status = card.dataset.status;
    const hasCV = card.dataset.hasCv === '1';
    const hasCL = card.dataset.hasCl === '1';
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

    // Search Text Match
    const textMatch = !searchText || text.includes(searchText);

    if (scoreMatch && statusMatch && textMatch) {{
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

applyFilters();
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
    disk from the last `applypilot dashboard` run, since nothing regenerates
    it in between -- there's no live connection from a static file back to
    the database. Serving it means every GET (a page reload, or a fresh
    `applypilot dashboard` open) re-runs generate_dashboard() against the
    live DB, so "refresh" means what it says.

    Args:
        output_path: Where to also write the HTML snapshot on each request
            (same file `open_dashboard`/`generate_dashboard` use). Defaults
            to ~/.applypilot/dashboard.html.
        port: Local port to listen on. Tries a few ports upward if taken
            (most likely cause: a previous `applypilot dashboard` is still
            running in another terminal).
    """
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
            else:
                self.send_response(404)
                self.end_headers()

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
