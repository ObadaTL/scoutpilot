"""Cover letter generation: LLM-powered, profile-driven, with validation.

Generates concise, engineering-voice cover letters tailored to specific job
postings. All personal data (name, skills, achievements) comes from the user's
profile at runtime. No hardcoded personal information.

Fabrication control mirrors resume tailoring (see scoring/tailor.py): the
prompt instruction alone is not enforcement. NumericGuard and ToolLeakGuard
are deterministic, post-generation checks -- a violation feeds back into the
retry loop as an explicit negative constraint, and a letter that never passes
never gets a cover_letter_path, so it re-enters the queue on the next run
instead of silently shipping.
"""

import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from applypilot.config import COVER_LETTER_DIR, DEFAULTS, RESUME_PATH, get_locale_style, load_profile
from applypilot.database import get_connection
from applypilot.facts import FactBank, NumericGuard, NumericGuardViolation
from applypilot.llm import get_client, is_local_provider
from applypilot.scoring.validator import (
    ToolLeakGuard,
    ToolLeakViolation,
    sanitize_text,
    strip_numbered_sentences,
    validate_cover_letter,
)

log = logging.getLogger(__name__)

MAX_ATTEMPTS = DEFAULTS["max_cover_attempts"]  # max cross-run retries before giving up

# Short, hand-picked steer for the base prompt -- NOT the enforcement list.
# validate_cover_letter (the full BANNED_WORDS/LLM_LEAK_PHRASES sets in
# validator.py) remains authoritative; dumping the complete ~50/~25-item
# lists into every prompt just primes a local model to notice and echo
# phrasing near them. The retry loop still injects the *actual* violations
# found on a failed attempt (see avoid_notes below).
_PROMPT_BANNED_SAMPLE = [
    "passionate", "spearheaded", "cutting-edge", "synergy",
    "utilize", "proven track record", "team player", "seamless",
]
_PROMPT_LEAK_SAMPLE = [
    "i am sorry", "here is the", "as requested", "note:", "i have rewritten",
]

# job['site'] is the *source* the posting was scraped from, not necessarily
# the hiring company -- true for jobs pulled straight from a company's own
# careers page (e.g. "Motorola Solutions", "NVIDIA"), but false for postings
# aggregated through a job board, where site is the board's own name and the
# real employer (if identifiable at all) is buried in free-text
# full_description. Checking for the board's name in the letter is not just
# unhelpful there, it's actively wrong -- and a hard-fails-every-retry check,
# since a job board name will never legitimately appear in a cover letter
# addressed to the actual employer. Skip the company-mention check for known
# aggregators/boards rather than block generation on an unwinnable check.
_AGGREGATOR_SITES = {
    "linkedin", "indeed", "glassdoor", "dice", "remoteok", "welcometothejungle",
    "job bank canada", "careerjet canada", "hacker news jobs", "builtin remote",
}


# ── Prompt Builder (profile-driven) ──────────────────────────────────────

def _build_cover_letter_prompt(profile: dict, job: dict) -> str:
    """Build the cover letter system prompt from the user's profile.

    All personal data, skills, and sign-off name come from the profile.
    company_summary/company_hook (captured during scoring, see scorer.py --
    derived only from the job description, never the model's own training
    knowledge) drive PARAGRAPH 3 when present.
    """
    personal = profile.get("personal", {})
    boundary = profile.get("skills_boundary", {})
    resume_facts = profile.get("resume_facts", {})

    # Preferred name for the sign-off (falls back to full name)
    sign_off_name = personal.get("preferred_name") or personal.get("full_name", "")

    # Flatten all allowed skills
    all_skills: list[str] = []
    for items in boundary.values():
        if isinstance(items, list):
            all_skills.extend(items)
    skills_str = ", ".join(all_skills) if all_skills else "the tools listed in the resume"

    # Real metrics from resume_facts
    real_metrics = resume_facts.get("real_metrics", [])
    preserved_projects = resume_facts.get("preserved_projects", [])

    # Build achievement examples for the prompt
    projects_hint = ""
    if preserved_projects:
        projects_hint = f"\nKnown projects to reference: {', '.join(preserved_projects)}"

    metrics_hint = ""
    if real_metrics:
        metrics_hint = f"\nReal metrics to use: {', '.join(real_metrics)}"

    # Short steer, not the full list -- see module docstring/_PROMPT_*_SAMPLE.
    # validate_cover_letter is what actually rejects a letter.
    banned_sample = ", ".join(f'"{w}"' for w in _PROMPT_BANNED_SAMPLE)
    leak_sample = ", ".join(f'"{p}"' for p in _PROMPT_LEAK_SAMPLE)
    style = get_locale_style(profile)

    company_hook = job.get("company_hook")
    if company_hook:
        hook_instruction = (
            f'State why the specific work described here -- {company_hook} -- '
            f'is somewhere you actually want to be. Not a compliment about the '
            f'company in general, this exact thing.'
        )
    else:
        hook_instruction = (
            "Do not make any company-specific claim -- you don't have enough "
            "to go on. Close on your own terms instead."
        )

    return f"""Write a cover letter for {sign_off_name}. The goal is to get an interview.

Use {style["spelling"]} English spelling and terminology throughout. If you refer to the attached document, call it a "{style["doc_name"]}", never the other term.

STRUCTURE: 3 short paragraphs. Under 250 words. Every sentence must earn its place.

PARAGRAPH 1 (2-3 sentences): Open with a specific thing YOU built that solves THEIR problem. Not "I'm excited about this role." Not "This role aligns with my experience." Start with the work.

PARAGRAPH 2 (3-4 sentences): Pick 2 achievements from the resume that are MOST relevant to THIS job. Use numbers. Frame as solving their problem, not listing your accomplishments.{projects_hint}{metrics_hint}

PARAGRAPH 3 (1-2 sentences): {hook_instruction}
Then close. "Happy to walk through any of this in more detail." or "Let's discuss." Nothing else.

BANNED WORDS AND PHRASES (a sample -- an automated validator checks a much larger list, do not use even words like these):
{banned_sample}

ALSO BANNED (meta-commentary the validator catches):
{leak_sample}

BANNED PUNCTUATION: No em dashes (—) or en dashes (–). Use commas or periods.

VOICE:
- Write like a real engineer emailing someone they respect. Not formal, not casual. Just direct.
- NEVER narrate or explain what you're doing. BAD: "This demonstrates my commitment to X." GOOD: Just state the fact and move on.
- NEVER hedge. BAD: "might address some of your challenges." GOOD: "solves the same problem your team is facing."
- Every sentence should contain either a number, a tool name, or a specific outcome. If it doesn't, cut it.
- Read it out loud. If it sounds like a robot wrote it, rewrite it.

FABRICATION = INSTANT REJECTION:
The candidate's real tools are ONLY: {skills_str}.
Do NOT mention ANY tool not in this list. If the job asks for tools not listed, talk about the work you did, not the tools.

Sign off: just "{sign_off_name}"

Output ONLY the letter text. No subject lines. No "Here is the cover letter:" preamble. No notes after the sign-off.
Start DIRECTLY with "Dear Hiring Manager," and end with the name."""


# ── Helpers ──────────────────────────────────────────────────────────────

_DEAR_LINE_START_RE = re.compile(r"^[ \t]*Dear\b", re.IGNORECASE | re.MULTILINE)


def _strip_preamble(text: str) -> str:
    """Remove LLM preamble before 'Dear Hiring Manager,' if present.

    Gemini and other models sometimes output "Here is the cover letter:" or
    similar meta-commentary before the actual letter text. Strip everything
    before the first line-starting "Dear" so the validator's start-check
    passes. Anchored to a line start (not a bare substring search) so a word
    like "endeared" or "dearest" sitting in the preamble can't be mistaken
    for the letter's real opening.
    """
    match = _DEAR_LINE_START_RE.search(text)
    if match and match.start() > 0:
        return text[match.start():]
    return text


def _strip_after_signoff(text: str, sign_off_name: str) -> str:
    """Truncate anything after the sign-off line.

    Models occasionally add notes/P.S. lines after the name despite being
    told not to. Finds the LAST line containing sign_off_name (not the
    first) so an incidental earlier mention of the name in the body can't
    cause a premature truncation, and drops everything after it.
    """
    if not sign_off_name:
        return text
    lines = text.split("\n")
    last_idx = None
    name_lower = sign_off_name.lower()
    for i, line in enumerate(lines):
        if name_lower in line.lower():
            last_idx = i
    if last_idx is None:
        return text
    return "\n".join(lines[:last_idx + 1]).rstrip()


_ANY_DIGIT_RE = re.compile(r"\d")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _recover_numeric_sentences(text: str, fact_bank: FactBank) -> str:
    """Proactively swap any sentence carrying a digit for the matching
    verified fact's own verbatim text, before validation ever runs.

    Mirrors tailor.py's per-bullet fact recovery (FactBank.match_similar) --
    same rationale, applied per-sentence here since a cover letter is prose,
    not a bullet list a violation can be dropped from cleanly. Without this,
    a sentence that happens to restate an already-verified fact in the
    model's own words (e.g. "...which I helped grow to 9 concurrent
    participants...") fails NumericGuard exactly like a fabricated one
    would, and the retry loop either burns an attempt or, once exhausted,
    deletes the whole sentence (strip_numbered_sentences) -- discarding
    true, verified content instead of shipping it under its safe wording.
    A sentence with no fact match is left untouched; NumericGuard still
    catches it downstream exactly as before.

    Splits on blank lines first and rejoins each paragraph independently --
    joining every sentence in the whole letter with a single space (as a
    naive split/rejoin would) collapses the required 3-short-paragraph
    structure into one wall of text the moment any paragraph needs a
    substitution.
    """
    if not _ANY_DIGIT_RE.search(text):
        return text

    def _fix_paragraph(para: str) -> str:
        if not _ANY_DIGIT_RE.search(para):
            return para
        fixed = []
        for sentence in _SENTENCE_SPLIT_RE.split(para):
            if _ANY_DIGIT_RE.search(sentence):
                recovered = fact_bank.match_similar(sentence)
                if recovered is not None:
                    fact_text = recovered[1]
                    if not fact_text.endswith((".", "!", "?")):
                        fact_text += "."
                    fixed.append(fact_text)
                    continue
            fixed.append(sentence)
        return " ".join(fixed)

    return "\n\n".join(_fix_paragraph(p) for p in text.split("\n\n"))


def _check_company_mentioned(letter: str, job: dict) -> str | None:
    """A cover letter that never names the company it's addressed to reads
    as generic/templated. Reuses the same job['site']-is-the-company-name
    convention already established for ToolLeakGuard's whitelist.

    Returns:
        An error string if the company name is missing, else None.
    """
    company = str(job.get("site") or "").strip()
    if not company or company.lower() in _AGGREGATOR_SITES or company.lower() in letter.lower():
        return None
    return f"Company name '{company}' is never mentioned in the letter"


# ── Core Generation ──────────────────────────────────────────────────────

def generate_cover_letter(
    resume_text: str, job: dict, profile: dict,
    max_retries: int = 3, validation_mode: str = "normal",
    fact_bank: FactBank | None = None,
) -> tuple[str, dict]:
    """Generate a cover letter with fresh context on each retry + auto-sanitize.

    Same design as tailor_resume: fresh conversation per attempt, issues noted
    in the prompt, no conversation history stacking. Also mirrors tailor_resume's
    fabrication control: NumericGuard and ToolLeakGuard are deterministic
    post-generation checks (not just prompt instructions), and their
    violations feed back as explicit negative constraints on retry.

    Args:
        resume_text:      The candidate's resume text (base or tailored).
        job:              Job dict with title, site, location, full_description.
        profile:          User profile dict.
        max_retries:      Maximum retry attempts.
        validation_mode:  "strict", "normal", or "lenient".
        fact_bank:        FactBank to check numbers against. Loads the
                          repo-root facts.yaml if not provided.

    Returns:
        (letter, validation) where validation = {"passed": bool, "errors":
        list[str], "warnings": list[str]} -- the caller decides whether to
        ship based on validation["passed"], never on "did this return".
    """
    fact_bank = fact_bank or FactBank.load()
    numeric_guard = NumericGuard(fact_bank, profile)
    tool_guard = ToolLeakGuard(profile)

    job_text = (
        f"TITLE: {job['title']}\n"
        f"COMPANY: {job['site']}\n"
        f"LOCATION: {job.get('location', 'N/A')}\n\n"
        f"DESCRIPTION:\n{(job.get('full_description') or '')[:6000]}"
    )

    personal = profile.get("personal", {})
    sign_off_name = personal.get("preferred_name") or personal.get("full_name", "")

    def _full_validate(candidate: str) -> dict:
        base = validate_cover_letter(candidate, mode=validation_mode)
        errors = list(base["errors"])
        try:
            numeric_guard.check(candidate)
        except NumericGuardViolation as e:
            errors.append(
                f"Unverified number(s) {e.numbers} in: " + "; ".join(e.bullets[:3])
            )
        try:
            tool_guard.check(job, candidate)
        except ToolLeakViolation as e:
            errors.append(
                f"Tool(s) mentioned that aren't in the candidate's real skills: {', '.join(e.tools)}"
            )
        company_error = _check_company_mentioned(candidate, job)
        if company_error:
            errors.append(company_error)
        return {"passed": not errors, "errors": errors, "warnings": base["warnings"]}

    avoid_notes: list[str] = []
    letter = ""
    validation: dict = {"passed": False, "errors": [], "warnings": []}
    client = get_client()
    cl_prompt_base = _build_cover_letter_prompt(profile, job)

    for attempt in range(max_retries + 1):
        # Fresh conversation every attempt
        prompt = cl_prompt_base
        if avoid_notes:
            prompt += "\n\n## AVOID THESE ISSUES:\n" + "\n".join(
                f"- {n}" for n in avoid_notes[-5:]
            )

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": (
                f"RESUME:\n{resume_text}\n\n---\n\n"
                f"TARGET JOB:\n{job_text}\n\n"
                "Write the cover letter:"
            )},
        ]

        temperature = 0.7 if attempt == 0 else 0.3
        letter = client.chat(messages, max_tokens=1024, temperature=temperature)
        letter = sanitize_text(letter)  # auto-fix em dashes, smart quotes
        letter = _strip_preamble(letter)  # remove any "Here is the letter:" prefix
        letter = _strip_after_signoff(letter, sign_off_name)  # drop any trailing notes
        letter = _recover_numeric_sentences(letter, fact_bank)  # swap in verified fact text before validating

        validation = _full_validate(letter)

        if validation["passed"]:
            return letter, validation

        avoid_notes.extend(validation["errors"])
        # Warnings never block — only hard errors trigger a retry
        log.debug(
            "Cover letter attempt %d/%d failed: %s",
            attempt + 1, max_retries + 1, validation["errors"],
        )

    # Retries exhausted. NumericGuard fabrication is the one failure mode a
    # deterministic, code-only fix can safely resolve without yet another
    # (possibly equally unreliable) LLM call: if every remaining error is a
    # fabricated-number violation, strip the offending sentences and
    # re-validate. Any other remaining error (banned words, missing company
    # mention, wrong salutation, tool leak) still blocks -- those aren't
    # safe to paper over mechanically.
    numeric_only = validation["errors"] and all(
        e.startswith("Unverified number(s)") for e in validation["errors"]
    )
    if numeric_only:
        # Protect the mandatory "Dear ...," opening before stripping.
        # strip_numbered_sentences splits on terminal punctuation (. ! ?)
        # only -- a salutation ending in a comma has none, so it glues to
        # whatever sentence follows it and gets dropped as one unit if that
        # sentence has a digit, losing the salutation entirely. Confirmed
        # live 2026-08-23: a fabrication-only failure that should have been
        # rescued by this fallback came back still failing, on "Must start
        # with 'Dear Hiring Manager,'" -- the fallback itself had eaten it.
        first_line, _, rest = letter.partition("\n")
        if first_line.strip().lower().startswith("dear"):
            stripped = first_line + "\n" + strip_numbered_sentences(rest)
        else:
            stripped = strip_numbered_sentences(letter)
        stripped_validation = _full_validate(stripped)
        if stripped_validation["passed"]:
            stripped_validation["warnings"] = list(stripped_validation["warnings"]) + [
                "Fabricated number(s) removed by deterministic fallback after exhausting retries"
            ]
            return stripped, stripped_validation

    return letter, validation  # last attempt, still failed -- caller must not ship this


# ── PDF Preflight ────────────────────────────────────────────────────────

def _preflight_pdf_converter() -> None:
    """Smoke-test the PDF pipeline once per batch, before any LLM calls.

    Exercises the real parse_resume -> build_html -> render_pdf (Playwright
    Chromium) path on a throwaway file. If the converter is systemically
    broken (e.g. Chromium not installed), every job would otherwise pass
    validation and only fail at the PDF step -- burning up to max_retries
    local-model generations per job for a reason that has nothing to do
    with letter content. Abort the whole batch loudly instead.

    Raises:
        RuntimeError: the PDF pipeline is broken; batch should not proceed.
    """
    from applypilot.scoring.pdf import convert_to_pdf

    probe_dir = COVER_LETTER_DIR / ".preflight"
    probe_dir.mkdir(parents=True, exist_ok=True)
    probe_txt = probe_dir / "probe.txt"
    probe_pdf = probe_txt.with_suffix(".pdf")
    try:
        probe_txt.write_text(
            "Dear Hiring Manager,\n\nPDF preflight probe letter.\n\nCandidate",
            encoding="utf-8",
        )
        convert_to_pdf(probe_txt)
    except Exception as e:
        raise RuntimeError(
            f"PDF generation is broken (preflight check failed): {e}. "
            "Aborting the cover-letter batch before spending LLM calls on "
            "jobs that would fail at the PDF step regardless of letter quality."
        ) from e
    finally:
        probe_txt.unlink(missing_ok=True)
        probe_pdf.unlink(missing_ok=True)


# ── Batch Entry Point ────────────────────────────────────────────────────

def run_cover_letters(min_score: int = 7, limit: int = 20,
                      validation_mode: str | None = None,
                      max_retries: int | None = None) -> dict:
    """Generate cover letters for high-scoring jobs that have tailored resumes.

    Args:
        min_score:       Minimum fit_score threshold.
        limit:           Maximum jobs to process.
        validation_mode: "strict", "normal", or "lenient". If not given,
                         auto-picks "lenient" for a local provider or
                         "normal" for cloud -- same as run_tailoring.
        max_retries:     Per-job retry budget passed to generate_cover_letter().
                         If not given, auto-picks 1 for a local provider vs.
                         3 for cloud -- same reasoning as run_tailoring: a
                         small local model rarely improves materially on a
                         3rd/4th "avoid these issues" retry.

    Returns:
        {"generated": int, "failed_validation": int, "pdf_failed": int,
         "errors": int, "fallback_to_base": int, "elapsed": float}
    """
    if max_retries is None:
        max_retries = 1 if is_local_provider() else 3
    if validation_mode is None:
        validation_mode = "lenient" if is_local_provider() else "normal"
    profile = load_profile()
    base_resume_text = RESUME_PATH.read_text(encoding="utf-8")
    # Loaded once per batch, not per job -- also means a bad facts.yaml
    # entry fails loudly here, before any LLM calls.
    fact_bank = FactBank.load()
    conn = get_connection()

    # Fetch jobs that have tailored resumes but no cover letter yet
    jobs = conn.execute(
        "SELECT * FROM jobs "
        "WHERE fit_score >= ? AND tailored_resume_path IS NOT NULL "
        "AND full_description IS NOT NULL "
        "AND (cover_letter_path IS NULL OR cover_letter_path = '') "
        "AND COALESCE(cover_attempts, 0) < ? "
        "ORDER BY fit_score DESC LIMIT ?",
        (min_score, MAX_ATTEMPTS, limit),
    ).fetchall()

    if not jobs:
        log.info("No jobs needing cover letters (score >= %d).", min_score)
        return {"generated": 0, "failed_validation": 0, "pdf_failed": 0,
               "errors": 0, "fallback_to_base": 0, "elapsed": 0.0}

    # Convert rows to dicts
    if jobs and not isinstance(jobs[0], dict):
        columns = jobs[0].keys()
        jobs = [dict(zip(columns, row)) for row in jobs]

    COVER_LETTER_DIR.mkdir(parents=True, exist_ok=True)
    _preflight_pdf_converter()

    log.info(
        "Generating cover letters for %d jobs (score >= %d)...",
        len(jobs), min_score,
    )
    t0 = time.time()
    completed = 0
    generated = 0
    failed_validation = 0
    pdf_failed = 0
    error_count = 0
    fallback_to_base = 0

    for job in jobs:
        completed += 1
        now = datetime.now(timezone.utc).isoformat()

        try:
            # Use THIS job's tailored resume, not the base one -- the batch
            # query already requires tailored_resume_path to exist.
            tailored_txt = None
            if job.get("tailored_resume_path"):
                candidate = Path(job["tailored_resume_path"]).with_suffix(".txt")
                if candidate.exists():
                    tailored_txt = candidate

            if tailored_txt:
                resume_text = tailored_txt.read_text(encoding="utf-8")
            else:
                expected = (
                    Path(job["tailored_resume_path"]).with_suffix(".txt")
                    if job.get("tailored_resume_path") else "N/A"
                )
                log.warning(
                    "Job %s (%s): tailored resume .txt not found at %s -- "
                    "falling back to the base resume for this cover letter",
                    job["url"], job["title"][:40], expected,
                )
                resume_text = base_resume_text
                fallback_to_base += 1

            letter, validation = generate_cover_letter(
                resume_text, job, profile,
                validation_mode=validation_mode, fact_bank=fact_bank,
                max_retries=max_retries,
            )

            # Build safe, collision-resistant filename prefix
            safe_title = re.sub(r"[^\w\s-]", "", job["title"])[:50].strip().replace(" ", "_")
            safe_site = re.sub(r"[^\w\s-]", "", job["site"])[:20].strip().replace(" ", "_")
            url_hash = hashlib.sha1(job["url"].encode("utf-8")).hexdigest()[:8]
            prefix = f"{safe_site}_{safe_title}_{url_hash}"

            # Always write the .txt for debugging, regardless of outcome --
            # same transparency precedent as tailor.py's _REPORT.json.
            cl_path = COVER_LETTER_DIR / f"{prefix}_CL.txt"
            cl_path.write_text(letter, encoding="utf-8")

            errors = list(validation["errors"])
            pdf_path = None
            this_pdf_failed = False

            if validation["passed"]:
                try:
                    from applypilot.scoring.pdf import convert_to_pdf
                    pdf_path = str(convert_to_pdf(cl_path))
                except Exception as e:
                    log.warning("PDF generation failed for %s: %s", cl_path, e)
                    errors.append(f"PDF generation failed: {e}")
                    this_pdf_failed = True

            success = validation["passed"] and pdf_path is not None

            if success:
                conn.execute(
                    "UPDATE jobs SET cover_letter_path=?, cover_letter_at=?, "
                    "cover_letter_passed=1, cover_letter_errors=NULL, "
                    "cover_attempts=COALESCE(cover_attempts,0)+1 WHERE url=?",
                    (str(cl_path), now, job["url"]),
                )
                generated += 1
                log.info(
                    "%d/%d [OK] %s | %s",
                    completed, len(jobs), job["title"][:40], job["site"],
                )
            elif this_pdf_failed:
                # Infra failure, not a content/quality failure -- don't burn
                # the retry ceiling on something the letter itself didn't cause.
                conn.execute(
                    "UPDATE jobs SET cover_letter_passed=0, cover_letter_errors=? WHERE url=?",
                    (json.dumps(errors), job["url"]),
                )
                pdf_failed += 1
                log.warning(
                    "%d/%d [PDF FAILED, no retry charged] %s",
                    completed, len(jobs), job["title"][:40],
                )
            else:
                conn.execute(
                    "UPDATE jobs SET cover_letter_passed=0, cover_letter_errors=?, "
                    "cover_attempts=COALESCE(cover_attempts,0)+1 WHERE url=?",
                    (json.dumps(errors), job["url"]),
                )
                failed_validation += 1
                log.info(
                    "%d/%d [FAILED VALIDATION] %s -- %s",
                    completed, len(jobs), job["title"][:40], errors[:2],
                )

            conn.commit()

        except Exception as e:
            conn.execute(
                "UPDATE jobs SET cover_letter_passed=0, cover_letter_errors=?, "
                "cover_attempts=COALESCE(cover_attempts,0)+1 WHERE url=?",
                (json.dumps([str(e)]), job["url"]),
            )
            conn.commit()
            error_count += 1
            log.error("%d/%d [ERROR] %s -- %s", completed, len(jobs), job["title"][:40], e)

    elapsed = time.time() - t0
    log.info(
        "Cover letters done in %.1fs: %d generated, %d failed validation, "
        "%d PDF failures, %d errors, %d fell back to base resume",
        elapsed, generated, failed_validation, pdf_failed, error_count, fallback_to_base,
    )

    return {
        "generated": generated,
        "failed_validation": failed_validation,
        "pdf_failed": pdf_failed,
        "errors": error_count,
        "fallback_to_base": fallback_to_base,
        "elapsed": elapsed,
    }
