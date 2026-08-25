"""Cover letter generation: LLM-powered, profile-driven, with validation.

Generates concise, engineering-voice cover letters tailored to specific job
postings. All personal data (name, skills, achievements) comes from the user's
profile at runtime. No hardcoded personal information.

Fabrication control mirrors resume tailoring (see scoring/tailor.py): the
prompt instruction alone is not enforcement. NumericGuard and ToolLeakGuard
are deterministic, post-generation checks -- a violation feeds back into the
retry loop, and a letter that never passes never gets a cover_letter_path,
so it re-enters the queue on the next run instead of silently shipping.

The guards only work as a *pair* with the prompt, though, and that pairing
was broken until 2026-08-25: the prompt demanded numbers while the FactBank
that decides which numbers are legal was never shown to it (see
_build_cover_letter_prompt). Everything downstream behaved exactly as
designed and the result was still five unusable letters -- the model
guessed, the guard rejected, retries ran out, and the deterministic
strip-and-ship fallback removed sentences until what was left was a 41-word
fragment opening on a pronoun with no referent. Two lessons are now
encoded here:

  * a guard that rejects an input the prompt never gave the model a way to
    satisfy is a guaranteed failure, not a safety net; and
  * the last-resort fallback must re-validate what it produced, because
    "deterministic" and "correct" are different properties -- deleting a
    sentence is safe for the *claims* and destructive to the *prose*.

validate_cover_letter therefore checks structure (length, paragraph count,
dangling references) in every mode, including lenient.
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
from applypilot.facts import FactBank, NumericGuard, NumericGuardViolation, format_facts_block
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

def _build_cover_letter_prompt(profile: dict, job: dict, fact_bank: FactBank) -> str:
    """Build the cover letter system prompt from the user's profile.

    All personal data, skills, and sign-off name come from the profile.
    company_summary/company_hook (captured during scoring, see scorer.py --
    derived only from the job description, never the model's own training
    knowledge) drive PARAGRAPH 3 when present.

    The FactBank is injected for the same reason tailor.py injects it: this
    prompt asks for numbers, and NumericGuard rejects every number that
    isn't traceable to a verified fact. Until 2026-08-25 the two halves were
    never introduced -- the prompt said "Use numbers" while its only numeric
    input was `resume_facts.real_metrics`, which is empty in a normal
    profile, so the model was asked for numbers with no idea which ones were
    permitted. It guessed, NumericGuard rejected the letter, retries
    exhausted, and the deterministic fallback deleted the offending
    sentences -- which is how letters shipped opening on "This directly
    addresses..." with the sentence that "This" referred to already gone,
    and how one shipped "classifies hand gestures with % accuracy". Showing
    the model the allowed numbers up front is what stops that at the source;
    the guards below stay exactly as strict.
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

    preserved_projects = resume_facts.get("preserved_projects", [])

    # Build achievement examples for the prompt
    projects_hint = ""
    if preserved_projects:
        projects_hint = f"\nKnown projects to reference: {', '.join(preserved_projects)}"

    facts_block = format_facts_block(
        fact_bank.relevant_facts(job.get("full_description") or "")
    )

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
        # No scraped company fact for this job (true for well over half of
        # them -- see scorer.py, which only captures a hook when the posting
        # actually describes the company). This used to read "Do not make any
        # company-specific claim -- you don't have enough to go on. Close on
        # your own terms instead.", which took the one paragraph designed to
        # be specific and instructed it to be generic; every such letter
        # closed on an interchangeable "I'd welcome the opportunity to bring
        # that combination of...". The job description itself is always
        # present in the user message and is always specific to this job, so
        # point the paragraph at that instead of at nothing.
        hook_instruction = (
            "You have no company background for this one, so use the posting "
            "itself: name ONE concrete requirement, system, or problem from "
            "the job description above and say why that is work you want. "
            "Quote their own terminology. Do not praise the company in "
            "general terms and do not invent anything about them."
        )

    return f"""Write a cover letter for {sign_off_name}. The goal is to get an interview.

Use {style["spelling"]} English spelling and terminology throughout. If you refer to the attached document, call it a "{style["doc_name"]}", never the other term.

STRUCTURE: 3 short paragraphs. Under 250 words. Every sentence must earn its place.
Separate every paragraph -- including the salutation and the sign-off -- with
one full blank line (an actual empty line between them, not just a line
break). Do NOT run paragraphs together into a single block of text.

PARAGRAPH 1 (2-3 sentences): Open with a specific thing YOU built that solves THEIR problem. Not "I'm excited about this role." Not "This role aligns with my experience." Start with the work.
Choose it by RELEVANCE to this job, not by how impressive it is. Read the job description first and pick the piece of experience closest to what they actually need. If they want backend, open on backend. If they want data work, open on data work. Opening on your most technically striking project when the job is about something else tells them you did not read the posting, and it is the single fastest way to sound like a form letter.

PARAGRAPH 2 (3-4 sentences): Pick 2 achievements from the resume that are MOST relevant to THIS job -- different ones from paragraph 1. Frame as solving their problem, not listing your accomplishments.{projects_hint}
Write them as full sentences in your own voice, with a subject and a verb. Do NOT paste a line out of the {style["doc_name"]} or a reference wording from VERIFIED FACTS as-is. To borrow an unrelated trade for the shape of it: "Rebuilt the kiln control loop" is a {style["doc_name"]} bullet, whereas "I rebuilt the kiln's control loop after the third batch cracked, and we stopped losing firings" is a sentence in a letter. Same fact, different job of work.

PARAGRAPH 3 (1-2 sentences): {hook_instruction}
Then close on its own line: "Happy to walk through any of this in more detail." or "Let's discuss." Nothing else.
Then, on its own line after a blank line: "Sincerely,"

BANNED WORDS AND PHRASES (a sample -- an automated validator checks a much larger list, do not use even words like these):
{banned_sample}

ALSO BANNED (meta-commentary the validator catches):
{leak_sample}

BANNED PUNCTUATION: No em dashes (—) or en dashes (–). Use commas or periods.

VOICE:
- Write like a real engineer emailing someone they respect. Not formal, not casual. Just direct.
- NEVER narrate or explain what you're doing. Do not tell them what a fact demonstrates about you; state the fact and stop. The reader draws the conclusion.
- NEVER hedge. No "might", "could help with", "some of your". Say what the work did.
- Every paragraph needs at least one checkable detail: a named system, a named tool, or a verified number. A paragraph of pure characterisation is filler.
- Vary your sentence lengths. Three medium declaratives in a row is the sound of a template.
- Read it out loud. If it sounds like a robot wrote it, rewrite it.

FABRICATION = INSTANT REJECTION:
The candidate's real tools are ONLY: {skills_str}.
Do NOT mention ANY tool not in this list. If the job asks for tools not listed, talk about the work you did, not the tools.

NUMBERS (checked automatically after you respond -- a letter that fails this check is thrown away):
Every digit you write must come from the verified facts below, used with the fact it belongs to. No other number may appear anywhere in the letter: not a percentage, not a headcount, not a duration, not a rounded "over 100". You may write these claims in your own words -- reword them for this job, that is the point -- but you may not attach a number to a claim that does not license it, and you may not import a number from one fact into a sentence about another.
If no verified fact fits what you want to say, say it without a number. A sentence with no number is fine. An invented number destroys the letter.

VERIFIED FACTS (the only numbers you may write):
{facts_block}
The short/long wordings above are there to tell you what each fact means and which numbers it covers. They are reference text, not sentences to copy. Say the same thing in your own words, in the first person, angled at this job.

Then, on its own line, below "Sincerely,": "{sign_off_name}"

Output ONLY the letter text. No subject lines. No "Here is the cover letter:" preamble. No notes after the name.
Start DIRECTLY with "Dear Hiring Manager," and end with the name, each part on
its own line separated by a blank line, e.g.:

Dear Hiring Manager,

<paragraph 1>

<paragraph 2>

<paragraph 3>

Sincerely,

{sign_off_name}"""


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


def _normalize_greeting_spacing(text: str) -> str:
    """Guarantee exactly one blank line between the "Dear ...," greeting and
    the first paragraph, regardless of what the model actually wrote there.

    Confirmed live 2026-08-24: even after the prompt was made explicit about
    a blank line between every paragraph (fixing the paragraph-collapse bug
    everywhere else), the local model still reliably skips it at this one
    spot, gluing paragraph 1 directly onto the greeting line. Deterministic
    fix instead of chasing further prompt wording for one boundary.
    """
    match = _DEAR_LINE_START_RE.search(text)
    if not match:
        return text
    nl = text.find("\n", match.start())
    if nl == -1:
        return text
    greeting_line = text[:nl]
    rest = text[nl:].lstrip("\n")
    return f"{greeting_line}\n\n{rest}"


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

# Single source of truth for these two error-message prefixes: built into
# the error string in _full_validate() below, and matched against (prefix
# stripped, in the tool-leak case, to recover the actual tool names) in the
# retry-exhaustion fallback further down. Keeping both ends in one place
# means they can't drift apart the way a duplicated literal could.
_NUMERIC_ERROR_PREFIX = "Unverified number(s)"
_TOOL_LEAK_ERROR_PREFIX = "Tool(s) mentioned that aren't in the candidate's real skills:"


def _strip_tool_sentences(text: str, tools: list[str]) -> str:
    """Deterministic, code-only removal of any sentence naming one of the
    given leaked tool tokens -- mirrors strip_numbered_sentences's
    paragraph-preserving approach (validator.py), applied by tool-name
    match instead of digit presence. Used alongside it in the retry-
    exhaustion fallback when a letter fails on both a fabricated number and
    a leaked tool mention in the same pass.
    """
    if not text or not tools:
        return text
    tool_res = [re.compile(r"\b" + re.escape(t) + r"\b", re.IGNORECASE) for t in tools]

    def _strip_para(para: str) -> str:
        if not any(r.search(para) for r in tool_res):
            return para
        sentences = _SENTENCE_SPLIT_RE.split(para)
        kept = [s for s in sentences if not any(r.search(s) for r in tool_res)]
        return " ".join(kept).strip()

    sep = "\n\n" if "\n\n" in text else "\n"
    # Drop any paragraph that comes back empty (every sentence in it named a
    # leaked tool) instead of rejoining it as a blank gap in the letter.
    stripped_paras = [_strip_para(p) for p in text.split(sep)]
    return sep.join(p for p in stripped_paras if p.strip())


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

    Falls back to splitting on single newlines when the letter has no blank
    lines at all -- confirmed live 2026-08-24: a local model that ignores
    the "separate paragraphs with a blank line" instruction and uses single
    newlines instead used to make this function treat the ENTIRE letter as
    one paragraph (no "\\n\\n" to split on), so the per-sentence rejoin
    below flattened every paragraph break -- and the greeting-to-body break
    -- into one run-on line the moment any sentence anywhere had a digit
    (i.e. almost always, since paragraph 2 is required to use numbers).
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

    if "\n\n" in text:
        return "\n\n".join(_fix_paragraph(p) for p in text.split("\n\n"))
    return "\n".join(_fix_paragraph(p) for p in text.split("\n"))


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
                f"{_NUMERIC_ERROR_PREFIX} {e.numbers} in: " + "; ".join(e.bullets[:3])
            )
        try:
            tool_guard.check(job, candidate)
        except ToolLeakViolation as e:
            errors.append(
                f"{_TOOL_LEAK_ERROR_PREFIX} {', '.join(e.tools)}"
            )
        company_error = _check_company_mentioned(candidate, job)
        if company_error:
            errors.append(company_error)
        return {"passed": not errors, "errors": errors, "warnings": base["warnings"]}

    avoid_notes: list[str] = []
    letter = ""
    validation: dict = {"passed": False, "errors": [], "warnings": []}
    client = get_client()
    cl_prompt_base = _build_cover_letter_prompt(profile, job, fact_bank)

    for attempt in range(max_retries + 1):
        # Fresh conversation every attempt
        prompt = cl_prompt_base
        if avoid_notes:
            # Retry feedback used to be purely negative -- a list of things
            # not to do, with no statement of what to do instead. A local
            # model handed only prohibitions retreats to the blandest text
            # it can produce, which is how a retry reliably came back worse
            # than the attempt that triggered it. Pair the violations with
            # the positive instruction that resolves them.
            prompt += (
                "\n\n## YOUR LAST ATTEMPT WAS REJECTED FOR THESE:\n"
                + "\n".join(f"- {n}" for n in avoid_notes[-5:])
                + "\n\nFix those specifically. Do NOT fix them by writing a shorter or "
                "vaguer letter -- it must still be three full paragraphs with concrete "
                "detail in each. If a number was rejected, either use one from VERIFIED "
                "FACTS with the fact it belongs to, or make the same point with no "
                "number at all."
            )

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": (
                f"RESUME:\n{resume_text}\n\n---\n\n"
                f"TARGET JOB:\n{job_text}\n\n"
                "Write the cover letter:"
            )},
        ]

        # Held at 0.7 across retries. This used to drop to 0.3 after the
        # first attempt, which made every retry *less* able to find another
        # way to phrase whatever got rejected -- the model would re-emit
        # near-identical text and fail the same check again, burning the
        # attempt budget and landing in the deterministic strip fallback.
        # The guards, not a low temperature, are what keep output truthful.
        temperature = 0.7
        letter = client.chat(messages, max_tokens=1024, temperature=temperature)
        letter = sanitize_text(letter)  # auto-fix em dashes, smart quotes
        letter = _strip_preamble(letter)  # remove any "Here is the letter:" prefix
        letter = _normalize_greeting_spacing(letter)  # guarantee a blank line after "Dear ...,"
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

    # Retries exhausted. NumericGuard fabrication and a leaked tool mention
    # are the two failure modes a deterministic, code-only fix can safely
    # resolve without yet another (possibly equally unreliable) LLM call: if
    # every remaining error is one of those two kinds, strip the offending
    # sentences and re-validate. Any other remaining error (banned words,
    # missing company mention, wrong salutation) still blocks -- those
    # aren't safe to paper over mechanically.
    #
    # Handling both together, not just numeric-only, matters in practice:
    # confirmed live 2026-08-25 that a job posting explicitly asking for LLM
    # experience (which this candidate's real skills don't include) got the
    # local model fabricating BOTH an unverified stat AND an "LLM" skill
    # claim on every one of 3 attempts -- a mixed-error case the old
    # numeric-only check never even tried to rescue.
    fixable = validation["errors"] and all(
        e.startswith(_NUMERIC_ERROR_PREFIX) or e.startswith(_TOOL_LEAK_ERROR_PREFIX)
        for e in validation["errors"]
    )
    if fixable:
        # Protect the mandatory "Dear ...," opening before stripping.
        # strip_numbered_sentences splits on terminal punctuation (. ! ?)
        # only -- a salutation ending in a comma has none, so it glues to
        # whatever sentence follows it and gets dropped as one unit if that
        # sentence has a digit, losing the salutation entirely. Confirmed
        # live 2026-08-23: a fabrication-only failure that should have been
        # rescued by this fallback came back still failing, on "Must start
        # with 'Dear Hiring Manager,'" -- the fallback itself had eaten it.
        first_line, has_dear, rest = letter.partition("\n")
        if not (has_dear and first_line.strip().lower().startswith("dear")):
            first_line, rest = "", letter

        body = strip_numbered_sentences(rest)

        leaked_tools: list[str] = []
        for e in validation["errors"]:
            if e.startswith(_TOOL_LEAK_ERROR_PREFIX):
                tools_str = e[len(_TOOL_LEAK_ERROR_PREFIX):].strip()
                leaked_tools.extend(t.strip() for t in tools_str.split(",") if t.strip())
        if leaked_tools:
            body = _strip_tool_sentences(body, leaked_tools)

        stripped = f"{first_line}\n{body}" if first_line else body
        # partition() above only ever consumes the FIRST newline after the
        # greeting, so if the original letter had the (correct) blank line
        # there, rebuilding with a single "\n" silently drops it. Re-run the
        # same normalization the main per-attempt path already applies
        # rather than re-deriving the right amount of whitespace here.
        stripped = _normalize_greeting_spacing(stripped)
        stripped_validation = _full_validate(stripped)
        if stripped_validation["passed"]:
            fixed_notes = []
            if any(e.startswith(_NUMERIC_ERROR_PREFIX) for e in validation["errors"]):
                fixed_notes.append("Fabricated number(s) removed by deterministic fallback after exhausting retries")
            if leaked_tools:
                fixed_notes.append(
                    f"Leaked tool mention(s) removed by deterministic fallback: {', '.join(leaked_tools)}"
                )
            stripped_validation["warnings"] = list(stripped_validation["warnings"]) + fixed_notes
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


# ── Per-job worker (shared by the batch runner and the single-job entry
# point used by the dashboard's Tailor button) ───────────────────────────

def _generate_one_cover_letter(conn, job: dict, base_resume_text: str, profile: dict,
                               fact_bank: FactBank, validation_mode: str,
                               max_retries: int) -> dict:
    """Generate a cover letter for one job, write its file(s)/PDF, and
    commit the DB update for this job alone.

    Returns:
        {"url", "title", "site", "status": one of "generated"/"pdf_failed"/
        "failed_validation"/"error", "fallback_to_base": bool, "path",
        "pdf_path", "errors": list[str]}.
    """
    now = datetime.now(timezone.utc).isoformat()
    fallback_to_base = False

    try:
        # Use THIS job's tailored resume, not the base one -- the caller's
        # selection query already requires tailored_resume_path to exist.
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
            fallback_to_base = True

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
            status = "generated"
            log.info("[OK] %s | %s", job["title"][:40], job["site"])
        elif this_pdf_failed:
            # Infra failure, not a content/quality failure -- don't burn
            # the retry ceiling on something the letter itself didn't cause.
            conn.execute(
                "UPDATE jobs SET cover_letter_passed=0, cover_letter_errors=? WHERE url=?",
                (json.dumps(errors), job["url"]),
            )
            status = "pdf_failed"
            log.warning("[PDF FAILED, no retry charged] %s", job["title"][:40])
        else:
            conn.execute(
                "UPDATE jobs SET cover_letter_passed=0, cover_letter_errors=?, "
                "cover_attempts=COALESCE(cover_attempts,0)+1 WHERE url=?",
                (json.dumps(errors), job["url"]),
            )
            status = "failed_validation"
            log.info("[FAILED VALIDATION] %s -- %s", job["title"][:40], errors[:2])

        conn.commit()
        return {
            "url": job["url"], "title": job["title"], "site": job["site"],
            "status": status, "fallback_to_base": fallback_to_base,
            "path": str(cl_path), "pdf_path": pdf_path, "errors": errors,
        }

    except Exception as e:
        conn.execute(
            "UPDATE jobs SET cover_letter_passed=0, cover_letter_errors=?, "
            "cover_attempts=COALESCE(cover_attempts,0)+1 WHERE url=?",
            (json.dumps([str(e)]), job["url"]),
        )
        conn.commit()
        log.error("[ERROR] %s -- %s", job["title"][:40], e)
        return {
            "url": job["url"], "title": job["title"], "site": job["site"],
            "status": "error", "fallback_to_base": fallback_to_base,
            "path": None, "pdf_path": None, "errors": [str(e)],
        }


def cover_letter_one(url: str, validation_mode: str | None = None,
                     max_retries: int | None = None) -> dict:
    """Generate a cover letter for exactly one job, by URL, regardless of
    its current batch-selection eligibility (e.g. regenerating one that
    already has a cover letter). Used by the dashboard's Tailor button,
    right after tailor_one() for the same job.

    Requires the job to already have a tailored_resume_path (its own
    tailored resume text is what the letter is built from) -- returns
    status "no_tailored_resume" instead of falling back to the base resume,
    since this is an explicit on-demand call for one job, not a batch run
    where a rare missing file shouldn't halt everything else.

    Returns:
        Result dict (see _generate_one_cover_letter), or
        {"status": "not_found", ...} / {"status": "no_tailored_resume", ...}.
    """
    if max_retries is None:
        # 2, not 1, for a local model. A retry was previously near-worthless
        # here -- it dropped the temperature and handed the model nothing but
        # prohibitions, so it tended to re-emit the same rejected text. Now
        # that retries keep temperature and carry a positive instruction, the
        # second one is where a letter that tripped a guard usually recovers,
        # instead of falling through to the deterministic strip fallback.
        max_retries = 2 if is_local_provider() else 3
    if validation_mode is None:
        validation_mode = "lenient" if is_local_provider() else "normal"

    conn = get_connection()
    row = conn.execute("SELECT * FROM jobs WHERE url = ?", (url,)).fetchone()
    if row is None:
        return {"url": url, "title": "?", "site": "?", "status": "not_found",
                "fallback_to_base": False, "path": None, "pdf_path": None, "errors": []}
    job = dict(row)

    if not job.get("tailored_resume_path"):
        return {"url": url, "title": job.get("title", "?"), "site": job.get("site", "?"),
                "status": "no_tailored_resume", "fallback_to_base": False,
                "path": None, "pdf_path": None, "errors": []}

    profile = load_profile()
    base_resume_text = RESUME_PATH.read_text(encoding="utf-8")
    fact_bank = FactBank.load()
    COVER_LETTER_DIR.mkdir(parents=True, exist_ok=True)
    _preflight_pdf_converter()

    log.info("Generating 1 cover letter on demand: %s (validation=%s, max_retries=%d)",
             job["title"][:40], validation_mode, max_retries)
    return _generate_one_cover_letter(conn, job, base_resume_text, profile, fact_bank,
                                      validation_mode, max_retries)


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
        # 2, not 1, for a local model. A retry was previously near-worthless
        # here -- it dropped the temperature and handed the model nothing but
        # prohibitions, so it tended to re-emit the same rejected text. Now
        # that retries keep temperature and carry a positive instruction, the
        # second one is where a letter that tripped a guard usually recovers,
        # instead of falling through to the deterministic strip fallback.
        max_retries = 2 if is_local_provider() else 3
    if validation_mode is None:
        validation_mode = "lenient" if is_local_provider() else "normal"
    profile = load_profile()
    base_resume_text = RESUME_PATH.read_text(encoding="utf-8")
    # Loaded once per batch, not per job -- also means a bad facts.yaml
    # entry fails loudly here, before any LLM calls.
    fact_bank = FactBank.load()
    conn = get_connection()

    # Optional location_focus (config.load_location_focus): same
    # temporary/reversible narrowing as database.get_jobs_by_stage and
    # apply.launcher.acquire_job. No-op when focus is disabled.
    from applypilot.config import load_location_focus
    focus = load_location_focus()
    tier_count = len((focus or {}).get("priority", []))
    focus_clause = f"AND loc_priority(location) < {tier_count} " if tier_count else ""
    order_by = "loc_priority(location) ASC, fit_score DESC" if tier_count else "fit_score DESC"

    # Fetch jobs that have tailored resumes but no cover letter yet
    jobs = conn.execute(
        "SELECT * FROM jobs "
        "WHERE fit_score >= ? AND tailored_resume_path IS NOT NULL "
        "AND full_description IS NOT NULL "
        "AND (cover_letter_path IS NULL OR cover_letter_path = '') "
        "AND COALESCE(cover_attempts, 0) < ? "
        "AND COALESCE(hidden, 0) = 0 "
        f"{focus_clause}"
        f"ORDER BY {order_by} LIMIT ?",
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
        result = _generate_one_cover_letter(conn, job, base_resume_text, profile,
                                            fact_bank, validation_mode, max_retries)
        if result["fallback_to_base"]:
            fallback_to_base += 1
        status = result["status"]
        if status == "generated":
            generated += 1
        elif status == "pdf_failed":
            pdf_failed += 1
        elif status == "failed_validation":
            failed_validation += 1
        else:
            error_count += 1
        log.info(
            "%d/%d [%s] %s | %s",
            completed, len(jobs), status.upper(), result["title"][:40], result["site"],
        )

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
