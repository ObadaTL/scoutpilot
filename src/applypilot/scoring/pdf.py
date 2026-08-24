"""Text-to-PDF conversion for tailored resumes and cover letters.

Parses the structured text resume format, renders via an HTML/CSS template,
and exports to PDF using headless Chromium via Playwright.
"""

import base64
import logging
from functools import lru_cache
from pathlib import Path

from applypilot.config import TAILORED_DIR

log = logging.getLogger(__name__)

# ── Embedded Fonts ───────────────────────────────────────────────────────
# Extracted 2026-08-23 from the candidate's real baseline documents
# (baseline_cv.docx -> Palatino Linotype / Century Gothic,
# CoverLetter.DOCX -> Roboto Condensed) so generated PDFs render with the
# actual fonts those documents use, not a generic substitute -- Century
# Gothic/Palatino Linotype/Roboto Condensed aren't standard fonts a viewer's
# system or Chromium's default set would otherwise have, so without
# embedding them the browser would silently fall back to something else
# regardless of what font-family the CSS names.
_FONTS_DIR = Path(__file__).resolve().parent / "fonts"


@lru_cache(maxsize=None)
def _font_b64(filename: str) -> str:
    return base64.b64encode((_FONTS_DIR / filename).read_bytes()).decode("ascii")


def _font_face(family: str, filename: str, weight: str = "normal", style: str = "normal") -> str:
    return (
        f"@font-face {{ font-family: '{family}'; "
        f"src: url(data:font/ttf;base64,{_font_b64(filename)}) format('truetype'); "
        f"font-weight: {weight}; font-style: {style}; }}"
    )


def _cv_font_faces() -> str:
    return "\n".join([
        _font_face("Palatino Linotype", "PalatinoLinotype-regular.ttf"),
        _font_face("Palatino Linotype", "PalatinoLinotype-bold.ttf", weight="bold"),
        _font_face("Palatino Linotype", "PalatinoLinotype-italic.ttf", style="italic"),
        _font_face("Palatino Linotype", "PalatinoLinotype-boldItalic.ttf", weight="bold", style="italic"),
        _font_face("Century Gothic", "CenturyGothic-regular.ttf"),
        _font_face("Century Gothic", "CenturyGothic-bold.ttf", weight="bold"),
        _font_face("Century Gothic", "CenturyGothic-italic.ttf", style="italic"),
        _font_face("Century Gothic", "CenturyGothic-boldItalic.ttf", weight="bold", style="italic"),
    ])


def _cover_letter_font_faces() -> str:
    return "\n".join([
        _font_face("Roboto Condensed", "RobotoCondensed-regular.ttf"),
        _font_face("Roboto Condensed", "RobotoCondensed-bold.ttf", weight="bold"),
        _font_face("Roboto Condensed", "RobotoCondensed-italic.ttf", style="italic"),
        _font_face("Roboto Condensed", "RobotoCondensed-boldItalic.ttf", weight="bold", style="italic"),
    ])


# ── Resume Parser ────────────────────────────────────────────────────────

def parse_resume(text: str) -> dict:
    """Parse a structured text resume into sections.

    Expects a format with header lines (name, title, location, contact)
    followed by ALL-CAPS section headers (SUMMARY, TECHNICAL SKILLS, etc.).

    Args:
        text: Full resume text.

    Returns:
        {"name": str, "title": str, "location": str, "contact": str, "sections": dict}
    """
    lines = [line.rstrip() for line in text.strip().split("\n")]

    # Header: first few lines before SUMMARY
    header_lines: list[str] = []
    body_start = 0
    for i, line in enumerate(lines):
        if line.strip().upper() == "SUMMARY":
            body_start = i
            break
        if line.strip():
            header_lines.append(line.strip())

    name = header_lines[0] if len(header_lines) > 0 else ""
    title = header_lines[1] if len(header_lines) > 1 else ""
    # The header may have 3 or 4 lines depending on whether location is included
    location = ""
    contact = ""
    if len(header_lines) > 3:
        location = header_lines[2]
        contact = header_lines[3]
    elif len(header_lines) > 2:
        # Could be location or contact -- check for email/phone indicators
        if "@" in header_lines[2] or "|" in header_lines[2]:
            contact = header_lines[2]
        else:
            location = header_lines[2]

    # Split body into sections by ALL-CAPS headers
    sections: dict[str, str] = {}
    current_section: str | None = None
    current_lines: list[str] = []

    for line in lines[body_start:]:
        stripped = line.strip()
        # Detect section headers (all caps, no leading dash/bullet, longer than 3 chars)
        if (
            stripped
            and stripped == stripped.upper()
            and not stripped.startswith("-")
            and len(stripped) > 3
            and not stripped.startswith("\u2022")
        ):
            if current_section:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = stripped
            current_lines = []
        else:
            current_lines.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_lines).strip()

    return {
        "name": name,
        "title": title,
        "location": location,
        "contact": contact,
        "sections": sections,
    }


def split_sections(text: str) -> dict[str, str]:
    """Split arbitrary CV/resume text into sections keyed by ALL-CAPS headers.

    Unlike parse_resume(), this makes no assumption about a fixed header
    block before the first section -- it just walks the whole text and
    treats any all-caps, non-bullet line as a new section start. Used to
    pull sections (Languages, Certifications, Awards, ...) out of a base CV
    that doesn't follow the tailored-resume template exactly.

    Args:
        text: Raw CV/resume text.

    Returns:
        Dict of section header (as found) -> body text.
    """
    sections: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []
    for raw_line in text.split("\n"):
        line = raw_line.rstrip()
        stripped = line.strip()
        is_header = (
            bool(stripped)
            and stripped == stripped.upper()
            and any(c.isalpha() for c in stripped)
            and not stripped.startswith("-")
            and not stripped.startswith("•")
            and not stripped.startswith("●")
            and len(stripped) > 3
        )
        if is_header:
            if current:
                sections[current] = "\n".join(lines).strip()
            current = stripped
            lines = []
        elif current:
            lines.append(line)
    if current:
        sections[current] = "\n".join(lines).strip()
    return sections


def parse_skills(text: str) -> list[tuple[str, str]]:
    """Parse skills section into (category, value) pairs.

    Args:
        text: The TECHNICAL SKILLS section text.

    Returns:
        List of (category_name, skills_string) tuples.
    """
    skills: list[tuple[str, str]] = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if ":" in line:
            cat, val = line.split(":", 1)
            skills.append((cat.strip(), val.strip()))
    return skills


def parse_entries(text: str) -> list[dict]:
    """Parse experience/project entries from section text.

    Args:
        text: The EXPERIENCE or PROJECTS section text.

    Returns:
        List of {"title": str, "subtitle": str, "bullets": list[str]} dicts.
    """
    entries: list[dict] = []
    lines = text.strip().split("\n")
    current: dict | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- ") or stripped.startswith("\u2022 "):
            if current:
                current["bullets"].append(stripped[2:].strip())
        elif current is None or (
            not stripped.startswith("-")
            and not stripped.startswith("\u2022")
            and len(current.get("bullets", [])) > 0
        ):
            # New entry
            if current:
                entries.append(current)
            current = {"title": stripped, "subtitle": "", "bullets": []}
        elif current and not current["subtitle"]:
            current["subtitle"] = stripped
        else:
            if current:
                current["bullets"].append(stripped)

    if current:
        entries.append(current)

    return entries


# ── HTML Template ────────────────────────────────────────────────────────

KNOWN_SECTIONS: set[str] = {"SUMMARY", "TECHNICAL SKILLS", "EXPERIENCE", "PROJECTS", "EDUCATION"}

# Layouts tried in order by _fit_resume_html(). "spacious" is the default --
# font size, name size, and margins parsed exactly out of the candidate's
# real baseline CV's own DOCX XML (baseline_cv.docx: word/document.xml
# section properties + run properties), not estimated -- 11pt body/headers
# (w:sz 22, half-points), 34pt name (w:sz 68), 0.417in/0.556in margins
# (600/800 dxa, 1440 dxa/in). Font *family* (Palatino Linotype for the name
# and section headers, Century Gothic for body text) and colors (#0069a5
# headers, #231f20 body) are set directly in the CSS below, embedded via
# _cv_font_faces() -- Century Gothic/Palatino Linotype aren't fonts a
# viewer's system or Chromium's defaults would have, so without embedding
# them the font-family CSS would silently fall back to something else no
# matter what these numbers say. "normal"/"compact" are a step-down safety
# net, not the goal: they only kick in if a resume has enough content that
# "spacious" would spill past 2 pages, stepping down just far enough to land
# back at 2.
_DENSITY_PRESETS: tuple[dict, ...] = (
    {
        "name": "spacious", "margin_v": 600 / 1440, "margin_h": 800 / 1440, "font": 11.0,
        "line": 1.25, "name_size": 34, "section_mt": 15, "entry_mb": 12,
        "li_mb": 3, "li_line": 1.3,
    },
    {
        "name": "normal", "margin_v": 0.55, "margin_h": 0.65, "font": 10.0,
        "line": 1.15, "name_size": 28, "section_mt": 10, "entry_mb": 9,
        "li_mb": 2, "li_line": 1.2,
    },
    {
        "name": "compact", "margin_v": 0.45, "margin_h": 0.55, "font": 9.5,
        "line": 1.1, "name_size": 24, "section_mt": 6, "entry_mb": 6,
        "li_mb": 1, "li_line": 1.15,
    },
)

_PAGE_DIMS_IN: dict[str, tuple[float, float]] = {
    "Letter": (8.5, 11.0),
    "A4": (8.27, 11.69),
}

_TARGET_MAX_PAGES = 2

# _fit_resume_html only ever stepped DOWN from "spacious" to avoid overflow
# past _TARGET_MAX_PAGES -- there was no matching step UP for content that
# falls short of it. Confirmed live 2026-08-24 on a real tailored resume:
# "spacious" rendered at ~52% of the 2-page budget (~1.05 pages), which
# ships as a 2-page PDF with a couple of stray lines on an otherwise blank
# second page -- exactly the "1 page long, other page mostly empty" look.
# _TARGET_FILL_RATIO is how much of the budget a stretch pass aims to
# reach (not literally 100% -- a touch of bottom margin reads as
# intentional, a page filled to the pixel reads as suspiciously tight).
# _STRETCH_MAX_SCALE caps how far spacing/line-height are allowed to grow
# so a genuinely thin resume gets MORE breathing room, not obviously
# padded whitespace that would fail an "industry standard" look.
_TARGET_FILL_RATIO = 0.92
_STRETCH_MAX_SCALE = 1.45


def _stretch_density(base: dict, scale: float) -> dict:
    """Proportionally loosen a density preset's line-height and vertical
    spacing (not its margins -- those anchor the page layout the DOCX
    baseline defines) so short content spreads to better fill the page.
    Font size gets a much gentler bump than spacing does (0.35x the
    spacing scale, capped at 12.5pt) -- oversized body text reads as
    padding a lot faster than slightly looser line spacing does.
    """
    scale = min(scale, _STRETCH_MAX_SCALE)
    font_scale = 1 + (scale - 1) * 0.35
    return {
        **base,
        "name": f"{base['name']}-stretched",
        "font": round(min(base["font"] * font_scale, 12.5), 2),
        "line": round(base["line"] * scale, 3),
        "section_mt": round(base["section_mt"] * scale, 2),
        "entry_mb": round(base["entry_mb"] * scale, 2),
        "li_mb": round(base["li_mb"] * scale, 2),
        "li_line": round(base["li_line"] * scale, 3),
    }


def build_html(resume: dict, page_size: str = "Letter", density: dict | None = None) -> str:
    """Build professional resume/CV HTML from parsed data.

    Any section beyond the five standard ones (e.g. LANGUAGES,
    CERTIFICATIONS & AWARDS -- carried through verbatim from the base CV by
    the tailoring step) is rendered generically so real content isn't
    silently dropped just because it's outside the fixed schema.

    Args:
        resume: Parsed resume dict from parse_resume().
        page_size: "Letter" (US) or "A4" (most of the rest of the world).
        density: One of _DENSITY_PRESETS, or None for the default ("normal").

    Returns:
        Complete HTML string ready for PDF rendering.
    """
    d = density or _DENSITY_PRESETS[0]
    sections = resume["sections"]

    # Skills
    skills_html = ""
    if "TECHNICAL SKILLS" in sections:
        skills = parse_skills(sections["TECHNICAL SKILLS"])
        rows = ""
        for cat, val in skills:
            rows += f'<div class="skill-row"><span class="skill-cat">{cat}:</span> {val}</div>\n'
        skills_html = f'<div class="section"><div class="section-title">Technical Skills</div>{rows}</div>'

    # Experience
    exp_html = ""
    if "EXPERIENCE" in sections:
        entries = parse_entries(sections["EXPERIENCE"])
        items = ""
        for e in entries:
            bullets = "".join(f"<li>{b}</li>" for b in e["bullets"])
            subtitle = f'<div class="entry-subtitle">{e["subtitle"]}</div>' if e["subtitle"] else ""
            items += f'<div class="entry"><div class="entry-title">{e["title"]}</div>{subtitle}<ul>{bullets}</ul></div>'
        exp_html = f'<div class="section"><div class="section-title">Experience</div>{items}</div>'

    # Projects
    proj_html = ""
    if "PROJECTS" in sections:
        entries = parse_entries(sections["PROJECTS"])
        items = ""
        for e in entries:
            bullets = "".join(f"<li>{b}</li>" for b in e["bullets"])
            subtitle = f'<div class="entry-subtitle">{e["subtitle"]}</div>' if e["subtitle"] else ""
            items += f'<div class="entry"><div class="entry-title">{e["title"]}</div>{subtitle}<ul>{bullets}</ul></div>'
        proj_html = f'<div class="section"><div class="section-title">Projects</div>{items}</div>'

    # Education
    edu_html = ""
    if "EDUCATION" in sections:
        edu_text = sections["EDUCATION"].strip()
        edu_html = f'<div class="section"><div class="section-title">Education</div><div class="edu">{edu_text}</div></div>'

    # Any extra sections (Languages, Certifications & Awards, Publications, ...)
    # not covered by the five standard ones above -- render generically.
    extra_html = ""
    for name, body in sections.items():
        if name in KNOWN_SECTIONS or not body.strip():
            continue
        bullets = [ln.strip()[2:].strip() for ln in body.split("\n") if ln.strip().startswith("- ")]
        if bullets:
            items = "".join(f"<li>{b}</li>" for b in bullets)
            extra_html += f'<div class="section"><div class="section-title">{name.title()}</div><ul>{items}</ul></div>'
        else:
            extra_html += f'<div class="section"><div class="section-title">{name.title()}</div><div class="summary">{body}</div></div>'

    # Summary
    summary_html = ""
    if "SUMMARY" in sections:
        summary_html = f'<div class="section"><div class="section-title">Summary</div><div class="summary">{sections["SUMMARY"].strip()}</div></div>'

    # Contact line parsing
    contact = resume["contact"]
    contact_parts = [p.strip() for p in contact.split("|")] if contact else []
    contact_html = " &nbsp;|&nbsp; ".join(contact_parts)

    # Location line (may be empty)
    location_html = f'<div class="location">{resume["location"]}</div>' if resume["location"] else ""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{_cv_font_faces()}
@page {{
    size: {page_size};
    margin: {d['margin_v']}in {d['margin_h']}in;
}}
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}
body {{
    font-family: 'Century Gothic', 'Century Gothic Std', Verdana, sans-serif;
    font-size: {d['font']}pt;
    line-height: {d['line']};
    color: #231f20;
    background: #ffffff;
}}
.header {{
    text-align: center;
    margin-bottom: 6px;
    padding-bottom: 6px;
    border-bottom: 1.5px solid #0069a5;
}}
.name {{
    font-family: 'Palatino Linotype', Georgia, serif;
    font-size: {d['name_size']}pt;
    font-weight: 700;
    color: #0069a5;
    letter-spacing: 0.3px;
    margin-bottom: 3px;
}}
.title {{
    font-family: 'Century Gothic', Verdana, sans-serif;
    font-size: {d['font'] + 2}pt;
    font-weight: 700;
    color: #0069a5;
    margin-bottom: 3px;
}}
.location {{
    font-size: {d['font'] - 1}pt;
    color: #231f20;
}}
.contact {{
    font-size: {d['font'] - 1}pt;
    color: #231f20;
    margin-top: 2px;
}}
.contact a {{
    color: #0069a5;
    text-decoration: none;
}}
.section {{
    margin-top: {d['section_mt']}px;
}}
.section-title {{
    font-family: 'Palatino Linotype', Georgia, serif;
    font-size: {d['font']}pt;
    font-weight: 700;
    color: #0069a5;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1.5px solid #0069a5;
    padding-bottom: 2px;
    margin-bottom: 6px;
}}
.summary {{
    font-size: {d['font']}pt;
    color: #231f20;
    line-height: {d['line']};
    text-align: justify;
}}
.skill-row {{
    font-size: {d['font']}pt;
    margin-bottom: 3px;
    line-height: {d['line']};
}}
.skill-cat {{
    font-weight: 700;
    color: #0069a5;
}}
.entry {{
    margin-bottom: {d['entry_mb']}px;
    break-inside: avoid;
}}
.entry-title {{
    font-weight: 700;
    font-size: {d['font']}pt;
    color: #231f20;
}}
.entry-subtitle {{
    font-size: {d['font'] - 0.5}pt;
    color: #231f20;
    margin-bottom: 3px;
}}
ul {{
    margin-left: 16px;
    padding: 0;
}}
li {{
    font-size: {d['font']}pt;
    margin-bottom: {d['li_mb']}px;
    line-height: {d['li_line']};
    color: #231f20;
    text-align: justify;
}}
.edu {{
    font-size: {d['font']}pt;
    line-height: {d['line']};
    color: #231f20;
}}
</style>
</head>
<body>
<div class="header">
    <div class="name">{resume['name']}</div>
    <div class="title">{resume['title']}</div>
    {location_html}
    <div class="contact">{contact_html}</div>
</div>
{summary_html}
{skills_html}
{exp_html}
{proj_html}
{edu_html}
{extra_html}
</body>
</html>"""


def build_cover_letter_html(text: str, profile: dict | None = None, page_size: str = "A4") -> str:
    """Build a beautifully styled, professional 1-page cover letter HTML."""
    from datetime import datetime
    from html import escape

    personal = (profile or {}).get("personal", {}) if profile else {}
    name = personal.get("full_name") or "Applicant"
    # Plain-text parts get escaped individually; link parts are already-safe
    # HTML (the URL itself is escaped inside), so the final join must NOT
    # re-escape everything -- that was the bug: LinkedIn/GitHub were
    # appended as bare label text with no href at all, so there was never a
    # link to click regardless of how the join happened.
    contact_parts = []
    if personal.get("email"):
        contact_parts.append(escape(personal["email"]))
    if personal.get("phone"):
        contact_parts.append(escape(personal["phone"]))
    city = personal.get("city", "")
    country = personal.get("country", "")
    if city or country:
        contact_parts.append(escape(f"{city}, {country}".strip(", ")))
    if personal.get("linkedin_url"):
        contact_parts.append(f'<a href="{escape(personal["linkedin_url"])}">LinkedIn</a>')
    if personal.get("github_url"):
        contact_parts.append(f'<a href="{escape(personal["github_url"])}">GitHub</a>')

    contact_line = " &nbsp;|&nbsp; ".join(contact_parts)
    today = datetime.now().strftime("%d %B %Y")

    # Split text into paragraphs
    raw_paras = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    if not raw_paras:
        raw_paras = [p.strip() for p in text.strip().split("\n") if p.strip()]

    body_paras = []
    salutation = "Dear Hiring Team,"
    signoff_name = personal.get("preferred_name") or personal.get("full_name") or name
    _signoff_phrases = ("sincerely", "best regards", "kind regards", "warm regards", "regards")

    for i, p in enumerate(raw_paras):
        p_clean = p.replace("\r", "").strip()
        if i == 0 and p_clean.lower().startswith("dear "):
            salutation = p_clean
            continue
        # "Sincerely,\nName" with no blank line between them lands as ONE
        # paragraph chunk here rather than two -- strip the signoff phrase
        # off the front first, or it both fails the exact-match skip below
        # AND gets misread as the whole signoff name (rendering as
        # "Sincerely, / Sincerely, Name" -- the static template's own
        # "Sincerely," plus this chunk's, both showing).
        lines = [ln.strip() for ln in p_clean.split("\n") if ln.strip()]
        if lines and lines[0].lower().rstrip(",") in _signoff_phrases:
            if len(lines) > 1:
                signoff_name = " ".join(lines[1:])
            continue
        if i == len(raw_paras) - 1 and len(p_clean.split()) <= 4 and not p_clean.endswith("."):
            signoff_name = p_clean
        elif p_clean.lower().rstrip(",") in _signoff_phrases:
            continue
        else:
            body_paras.append(f"<p>{escape(p_clean)}</p>")

    body_html = "\n".join(body_paras)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{_cover_letter_font_faces()}
@page {{
    size: {page_size};
    margin: {300 / 1440}in {1280 / 1440}in;
}}
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}
body {{
    font-family: 'Roboto Condensed', 'Arial Narrow', Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #000000;
    background: #ffffff;
}}
.letterhead {{
    text-align: center;
    padding-bottom: 10px;
    margin-bottom: 16px;
    border-bottom: 1.5px solid #7f8183;
}}
.name {{
    font-size: 18pt;
    font-weight: 700;
    color: #000000;
    letter-spacing: 0.3px;
    margin-bottom: 4px;
}}
.contact {{
    font-size: 9.5pt;
    color: #7f8183;
}}
.contact a {{
    color: #7f8183;
    text-decoration: none;
}}
.date {{
    font-size: 11pt;
    color: #000000;
    margin-bottom: 16px;
}}
.salutation {{
    font-size: 11pt;
    font-weight: 700;
    color: #000000;
    margin-bottom: 14px;
}}
.content p {{
    margin-bottom: 12px;
    text-align: justify;
    color: #000000;
    line-height: 1.5;
}}
.signoff {{
    margin-top: 20px;
    font-size: 11pt;
    font-weight: 700;
    font-style: italic;
}}
.signoff-name {{
    margin-top: 12px;
    font-weight: 700;
    color: #000000;
    font-size: 11pt;
}}
</style>
</head>
<body>
<div class="letterhead">
    <div class="name">{escape(name)}</div>
    <div class="contact">{contact_line}</div>
</div>

<div class="date">{today}</div>

<div class="salutation">{escape(salutation)}</div>

<div class="content">
{body_html}
</div>

<div class="signoff">
    <div>Sincerely,</div>
    <div class="signoff-name">{escape(signoff_name)}</div>
</div>
</body>
</html>"""


def _fit_resume_html(resume: dict, page_size: str) -> str:
    """Render `resume` at the density that best fills `_TARGET_MAX_PAGES`
    pages (2, matching the candidate's real baseline CV) without overflowing
    it -- too much content shrinks down through the density presets, too
    little stretches the baseline ("spacious") preset looser instead of
    shipping as-is with a mostly-blank trailing page.

    Chromium's print layout has no built-in "shrink/grow to fit N pages" for
    @page-based pagination, so this does it manually in a single headless
    Chromium session: render the baseline density at the page's actual
    content width, measure the resulting content height, and:
      - if it overflows the page budget, step down through the tighter
        presets and stop at the first that fits (falls back to the most
        compact preset if even that overflows -- a genuinely long resume
        legitimately needs more room, but this keeps it as close to
        `_TARGET_MAX_PAGES` as the presets allow rather than sprawling
        further unchecked);
      - if it falls short of `_TARGET_FILL_RATIO` of the budget, stretch
        spacing/line-height by the ratio needed to reach that fill level
        (capped at `_STRETCH_MAX_SCALE`) and use that instead, so short
        content reads as a normally-spaced, well-filled CV rather than a
        cramped one-and-a-bit pages with an empty tail.
    """
    from playwright.sync_api import sync_playwright

    page_w_in, page_h_in = _PAGE_DIMS_IN.get(page_size, _PAGE_DIMS_IN["Letter"])

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            def _measure(density: dict) -> tuple[str, int, int]:
                html = build_html(resume, page_size=page_size, density=density)
                content_w_px = round((page_w_in - 2 * density["margin_h"]) * 96)
                budget_px = round((page_h_in - 2 * density["margin_v"]) * 96) * _TARGET_MAX_PAGES
                page = browser.new_page(viewport={"width": content_w_px, "height": 100})
                page.set_content(html, wait_until="networkidle")
                height = page.evaluate("document.body.scrollHeight")
                page.close()
                return html, height, budget_px

            baseline = _DENSITY_PRESETS[0]
            html, height, budget_px = _measure(baseline)

            if height <= budget_px:
                if height < budget_px * _TARGET_FILL_RATIO:
                    scale = (budget_px * _TARGET_FILL_RATIO) / height
                    stretched_html, stretched_height, _ = _measure(_stretch_density(baseline, scale))
                    if stretched_height <= budget_px:
                        return stretched_html
                    # Overshot the single-pass estimate -- the un-stretched
                    # baseline is still a safe, correctly-fitting result.
                return html

            for density in _DENSITY_PRESETS[1:]:
                html, height, budget_px = _measure(density)
                if height <= budget_px or density is _DENSITY_PRESETS[-1]:
                    return html
        finally:
            browser.close()
    return build_html(resume, page_size=page_size)  # unreachable, keeps type-checkers happy


# ── PDF Renderer ─────────────────────────────────────────────────────────

def render_pdf(html: str, output_path: str, page_size: str = "Letter") -> None:
    """Render HTML to PDF using Playwright's headless Chromium.

    Args:
        html: Complete HTML string.
        output_path: Path to write the PDF file.
        page_size: "Letter" or "A4" -- must match the @page size baked into html.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        page.pdf(
            path=output_path,
            format=page_size,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            print_background=True,
        )
        browser.close()


# ── Public API ───────────────────────────────────────────────────────────

def convert_to_pdf(
    text_path: Path, output_path: Path | None = None, html_only: bool = False
) -> Path:
    """Convert a text resume or cover letter to a formatted PDF.

    Args:
        text_path: Path to the .txt file to convert.
        output_path: Optional override for the output path. Defaults to same
            name with .pdf extension.
        html_only: If True, output HTML instead of PDF.

    Returns:
        Path to the generated PDF (or HTML) file.
    """
    text_path = Path(text_path)
    text = text_path.read_text(encoding="utf-8")

    profile = None
    page_size = "A4"
    try:
        from applypilot.config import get_locale_style, load_profile
        profile = load_profile()
        page_size = get_locale_style(profile)["page_size"]
    except Exception:
        log.debug("Could not load profile for locale detection, defaulting to A4", exc_info=True)

    # Detect whether this is a cover letter or a resume
    is_cover_letter = (
        text_path.name.endswith("_CL.txt")
        or "cover_letter" in text_path.name.lower()
        or text.strip().startswith("Dear ")
        or "\nDear " in text[:200]
    )

    if is_cover_letter:
        html = build_cover_letter_html(text, profile=profile, page_size=page_size)
    else:
        resume = parse_resume(text)
        html = _fit_resume_html(resume, page_size=page_size)

    if html_only:
        out = output_path or text_path.with_suffix(".html")
        out = Path(out)
        out.write_text(html, encoding="utf-8")
        log.info("HTML generated: %s", out)
        return out

    out = output_path or text_path.with_suffix(".pdf")
    out = Path(out)
    render_pdf(html, str(out), page_size=page_size)
    log.info("PDF generated: %s", out)
    return out


def batch_convert(limit: int = 50) -> int:
    """Convert .txt files in TAILORED_DIR that don't have corresponding PDFs.

    Scans for .txt files (excluding _JOB.txt and _REPORT.json), checks if a
    .pdf with the same stem already exists, and converts any that are missing.

    Args:
        limit: Maximum number of files to convert.

    Returns:
        Number of PDFs generated.
    """
    if not TAILORED_DIR.exists():
        log.warning("Tailored directory does not exist: %s", TAILORED_DIR)
        return 0

    txt_files = sorted(TAILORED_DIR.glob("*.txt"))
    # Exclude _JOB.txt and _CL.txt files from resume conversion
    # (they get their own conversion calls)
    candidates = [
        f for f in txt_files
        if not f.name.endswith("_JOB.txt")
    ]

    # Filter to those without a corresponding PDF
    to_convert: list[Path] = []
    for f in candidates:
        pdf_path = f.with_suffix(".pdf")
        if not pdf_path.exists():
            to_convert.append(f)
        if len(to_convert) >= limit:
            break

    if not to_convert:
        log.info("All text files already have PDFs.")
        return 0

    log.info("Converting %d files to PDF...", len(to_convert))
    converted = 0
    for f in to_convert:
        try:
            convert_to_pdf(f)
            converted += 1
        except Exception as e:
            log.error("Failed to convert %s: %s", f.name, e)

    log.info("Done: %d/%d PDFs generated in %s", converted, len(to_convert), TAILORED_DIR)
    return converted
