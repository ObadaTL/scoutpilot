"""Resume tailoring: LLM-powered ATS-optimized resume generation per job.

THIS IS THE HEAVIEST REFACTOR. Every piece of personal data -- name, email, phone,
skills, companies, projects, school -- is loaded at runtime from the user's profile.
Zero hardcoded personal information.

The LLM returns structured JSON, code assembles the final text. Header (name, contact)
is always code-injected, never LLM-generated. Each retry starts a fresh conversation
to avoid apologetic spirals.

Numeric content is a separate control from the rest of the tailoring text: the LLM
never writes a number that isn't licensed by a verified fact. It attaches a fact id
to any bullet carrying a number, and code checks that every digit in that bullet is
one the fact's own evidence covers (FactBank._accept_reworded) -- the WORDING is the
model's, the NUMBERS are the FactBank's. A bullet whose rewording reaches for any
other number is replaced by that fact's pre-written variant rather than shipped; any
bullet with no fact id must contain zero digits. NumericGuard re-checks the assembled
text against FactBank.allowed_numbers() after generation, deterministically -- this
is enforcement, not just a prompt instruction the model could ignore.

Substituting the pre-written variant *unconditionally* (the original design) was safe
but produced interchangeable documents: 450 bullets across 58 generated CVs collapsed
to 87 distinct strings, because the model's only real lever was which of ~11 facts to
select and in what order. Verifying the numbers instead of dictating the sentence
gives per-job wording back without weakening the fabrication guarantee.
"""

import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from applypilot.config import RESUME_PATH, TAILORED_DIR, get_locale_style, load_profile
from applypilot.database import get_connection, get_jobs_by_stage
from applypilot.facts import (
    BulletPlacementViolation, FactBank, NumericGuard, NumericGuardViolation, format_facts_block,
)
from applypilot.llm import get_client, is_local_provider
from applypilot.scoring.pdf import split_sections
from applypilot.scoring.validator import (
    BANNED_WORDS,
    FABRICATION_WATCHLIST,
    SECTION_VARIANTS,
    ToolLeakGuard,
    ToolLeakViolation,
    sanitize_text,
    validate_json_fields,
    validate_tailored_resume,
)

log = logging.getLogger(__name__)

# Cross-run attempt budget lives in config.DEFAULTS["max_tailor_attempts"]
# (consumed by database.get_jobs_by_stage's "pending_tailor" condition) --
# not duplicated here.
_DIGIT_TOKEN_RE = re.compile(r"\d+")

# Short, hand-picked steer for the tailoring prompt -- NOT the enforcement
# list. validate_json_fields (the full BANNED_WORDS set in validator.py)
# remains authoritative. Same rationale as cover_letter._PROMPT_BANNED_SAMPLE.
_PROMPT_BANNED_SAMPLE = [
    "passionate", "spearheaded", "cutting-edge", "synergy",
    "utilize", "proven track record", "robust", "seamless",
]


# ── Prompt Builders (profile-driven) ──────────────────────────────────────

def _build_tailor_prompt(profile: dict, fact_bank: FactBank, job_description: str = "") -> str:
    """Build the resume tailoring system prompt from the user's profile.

    All skills boundaries, preserved entities, and formatting rules are
    derived from the profile -- nothing is hardcoded. Quantified content is
    handled entirely through the FactBank: the prompt offers only the
    verified facts relevant to this job (see FactBank.relevant_facts) and
    tells the model to select among them by id rather than write numbers
    itself. NumericGuard re-checks this after generation -- this prompt
    text is not the enforcement, it's the instruction half of it.
    """
    boundary = profile.get("skills_boundary", {})
    resume_facts = profile.get("resume_facts", {})

    # Format skills boundary for the prompt. Category labels come entirely
    # from the profile's own keys -- the JSON schema example below reuses
    # these same labels instead of a fixed list, so the model is never asked
    # to fill a skill category (e.g. "Databases") the candidate doesn't have.
    skills_lines = []
    skill_labels: list[str] = []
    for category, items in boundary.items():
        if isinstance(items, list) and items:
            label = category.replace("_", " ").title()
            skill_labels.append(label)
            skills_lines.append(f"{label}: {', '.join(items)}")
    skills_block = "\n".join(skills_lines)
    skills_schema = ", ".join(f'"{label}":"..."' for label in skill_labels) or '"Skills":"..."'

    # Preserved entities
    companies = resume_facts.get("preserved_companies", [])
    projects = resume_facts.get("preserved_projects", [])
    school = resume_facts.get("preserved_school", "")

    companies_str = ", ".join(companies) if companies else "N/A"
    projects_str = ", ".join(projects) if projects else "N/A"

    facts_block = format_facts_block(fact_bank.relevant_facts(job_description), show_owner=True)

    # A short, hand-picked steer -- NOT the full enforcement list. This used
    # to dump all ~50 BANNED_WORDS into every call, on the reasoning that the
    # model should know exactly what gets rejected. cover_letter.py already
    # worked out why that backfires (see its _PROMPT_BANNED_SAMPLE): a long
    # list of forbidden phrasings primes a local model to produce text in
    # their neighbourhood, and it crowds out the instructions that actually
    # shape the writing. validate_json_fields still checks the full list --
    # the enforcement is unchanged, only the priming is gone.
    banned_str = ", ".join(f'"{w}"' for w in _PROMPT_BANNED_SAMPLE)

    style = get_locale_style(profile)
    doc = style["doc_name"]
    pages = style["pages"]
    max_bullets = 5 if pages > 1 else 4

    return f"""You are a senior technical recruiter rewriting a {doc} to get this person an interview.

Take the base {doc} and job description. Return a tailored {doc} as a JSON object.

## RECRUITER SCAN (6 seconds):
1. Title -- matches what they're hiring?
2. Summary -- 2 sentences proving you've done this work
3. First 3 bullets of most recent role -- verbs and outcomes match?
4. Skills -- must-haves visible immediately?

## SKILLS BOUNDARY (real skills only):
{skills_block}

The SKILLS section of your output is used ONLY to decide display order within each category -- code renders the category's real items verbatim, in whatever order your text implies. Do NOT add a tool that isn't already listed above, even one closely related to something that is (no Kubernetes because Docker is listed, no Terraform because AWS is listed) -- it will never render regardless, and any bullet mentioning it will be rejected as fabrication.

## TAILORING RULES:

TITLE: Match the target role. Keep seniority (Senior/Lead/Staff). Drop company suffixes and team names.

SUMMARY: Rewrite from scratch, for this job specifically. Lead with the single most relevant thing this person has actually done -- name the system, the domain, or the problem, not a category. It may carry numbers on the same terms as any bullet (see NUMBERS): if a verified fact belongs here, use it.
Two rules, because summaries drift into template:
- No sentence may begin "Experienced in ...", "Proven ability ...", "Skilled in ..." or "Familiar with ...". Those name categories of experience instead of saying what was done. State the work.
- Do not default to whatever the base {doc} leads with. If the base {doc} opens on a specialism this job never mentions, that specialism does not belong in the first sentence. Backend role, lead with backend. Support role, lead with production systems and debugging.

SKILLS: Reorder each category so the job's must-haves appear first.

Reframe EVERY bullet for this role. Same real work, different angle. Every bullet must be reworded. Never copy verbatim. (This applies to plain-text bullets -- a fact-id bullet's wording comes verbatim from the fact, see NUMBERS below, and is not yours to reword.)

PROJECTS: Reorder by relevance. Drop irrelevant projects entirely. Never invent a new project -- only use projects that already appear in the original {doc}: {projects_str}

BULLETS: Strong verb + what you built + impact. Vary verbs (Built, Designed, Implemented, Reduced, Automated, Deployed, Operated, Optimized). Most relevant first. Max {max_bullets} per section.

## VOICE:
- Write like a real engineer. Short, direct.
- GOOD: "Automated financial reporting with Python and API integrations, eliminating a manual end-of-month process"
- BAD: "Leveraged cutting-edge AI technologies to drive transformative operational efficiencies"
- Use {style["spelling"]} English spelling and terminology throughout. Call it a "{doc}", never the other term.
- Recruiter-brochure words are rejected by an automated validator that checks a much
  larger list than this sample -- avoid anything that reads like these:
  {banned_str}
- No em dashes. Use commas, periods, or hyphens.

## NUMBERS -- READ THIS CAREFULLY (hard constraint, enforced by an automated checker after you respond, not just this instruction):
You write the sentences. You do NOT choose the numbers. Every bullet is one of two shapes:
1. A plain string with ZERO digits anywhere in it -- not a rounded number, not a vague one, not a year, nothing. "Automated a manual reporting workflow" is fine. "Automated 5 reporting workflows" is NOT, even if you think 5 sounds plausible.
2. A bullet built on a verified fact: {{"fact": "<id>", "text": "<your own sentence for this fact, written for THIS job>"}}, using ONLY an id from VERIFIED FACTS below. Write that sentence yourself -- angle it at this job, lead with the verb that matters here, use the job's vocabulary. The ONLY constraint is numeric: the sentence may contain the numbers that fact licenses and no others. Any other digit and your wording is discarded and replaced with the canned variant, so the bullet stops being tailored at all.
If an achievement has no fact backing it, describe it with a plain zero-digit bullet. A fabricated statistic is worse than no statistic -- there is no partial credit for a plausible-sounding number.

Do not copy a fact's `short`/`long` text verbatim unless it genuinely is the best sentence for this job. They are reference wordings showing what the fact means and which numbers it covers -- not a menu to pick from. Two CVs for two different jobs should not share a bullet word for word.

## VERIFIED FACTS (the only source of numbers -- attach the id, write your own sentence):
{facts_block}

Each fact names the entry it belongs under. Attach it ONLY to a bullet inside the entry whose header or subtitle contains that owner word -- an "emg" fact goes under the EMG project entry, a "kraydel" fact under the Kraydel employer entry, and so on. Put one anywhere else and the bullet is DISCARDED before the CV is assembled; if that empties an entry, the whole document falls back to canned wording and nothing you wrote survives. If a fact's owner has no entry on this CV, leave that fact out.

## HARD RULES:
- Do NOT invent work, companies, degrees, certifications, or projects
- Preserved companies: {companies_str} -- names stay as-is
- Preserved school: {school}
- EDUCATION is code-overridden after you respond -- whatever you write in that field is discarded and replaced with the candidate's real degree, honours, and dates. Fill it with anything non-empty (e.g. just the school name); do not spend effort on it.
- The degree and the university are NEVER an EXPERIENCE entry. EXPERIENCE holds employers and nothing else -- exactly these: {companies_str}. An entry headed with a degree, a course, or {school} is deleted in code before the {doc} is assembled, and every bullet you wrote under it goes with it.
- Must fill {pages} full page{'s' if pages != 1 else ''} -- do not compress to fewer, do not pad with filler to reach more.

## OUTPUT: Return ONLY valid JSON. No markdown fences. No commentary. No "here is" preamble.

{{"title":"Role Title","summary":"2-3 sentences written for this job.","skills":{{{skills_schema}}},"experience":[{{"header":"Title at Company","subtitle":"Tech | Dates","bullets":["plain zero-digit bullet",{{"fact":"some.fact.id","text":"your own sentence for this fact, angled at this job"}}]}}],"projects":[{{"header":"Project Name - Description","subtitle":"Tech | Dates","bullets":["plain zero-digit bullet",{{"fact":"some.fact.id","text":"your own sentence for this fact"}}]}}],"education":"{school}"}}"""


def _build_judge_prompt(profile: dict, fact_bank: FactBank | None = None) -> str:
    """Build the LLM judge prompt from the user's profile.

    The judge only ever sees the final assembled text, not the JSON that
    produced it -- it has no way to tell a number that came from a
    verbatim-substituted FactBank entry (guaranteed real, evidence-backed)
    apart from one the model invented outright, unless told what the real
    ones are. Confirmed live 2026-08-23: with `profile.json`'s
    `resume_facts.real_metrics` empty (the field this used to read alone),
    the judge FAILed a resume purely for including
    "Raised multi-party video call capacity from 4 to 9 participants" --
    the verbatim `short` variant of `kraydel.multiparty_calls`, a tier:
    verified fact with real evidence, exactly the kind of addition the
    FactBank system exists to allow. Deriving the metrics list from the
    FactBank itself (rather than a separately hand-maintained profile.json
    field that's easy to leave empty or let drift out of sync) closes that
    false-positive at the source instead of requiring the two to be kept
    in step manually.
    """
    boundary = profile.get("skills_boundary", {})
    resume_facts = profile.get("resume_facts", {})

    # Flatten allowed skills for the judge
    all_skills: list[str] = []
    for items in boundary.values():
        if isinstance(items, list):
            all_skills.extend(items)
    skills_str = ", ".join(all_skills) if all_skills else "N/A"

    real_metrics = list(resume_facts.get("real_metrics", []))
    if fact_bank is not None:
        for fact in fact_bank.verified():
            text = fact.variants.get("short") or fact.variants.get("long")
            if text:
                real_metrics.append(" ".join(text.split()))
    metrics_str = ", ".join(real_metrics) if real_metrics else "N/A"

    return f"""You are a resume quality judge. A tailoring engine rewrote a resume to target a specific job. Your job is to catch LIES, not style changes.

You must answer with EXACTLY this format:
VERDICT: PASS or FAIL
ISSUES: (list any problems, or "none")

## CONTEXT -- what the tailoring engine was instructed to do (all of this is ALLOWED):
- Change the title to match the target role
- Rewrite the summary from scratch for the target job
- Reorder bullets and projects to put the most relevant first
- Reframe bullets to use the job's language
- Drop low-relevance bullets and replace with more relevant ones from other sections
- Reorder the skills section to put job-relevant skills first
- Change tone and wording extensively

## WHAT IS FABRICATION (FAIL for these):
1. Adding tools, languages, or frameworks to TECHNICAL SKILLS that aren't in the original. The allowed skills are ONLY: {skills_str}
2. Inventing NEW metrics or numbers not in the original. The real metrics are: {metrics_str}
3. Inventing work that has no basis in any original bullet (completely new achievements).
4. Adding companies, roles, or degrees that don't exist.
5. Changing real numbers (inflating 80% to 95%, 500 nodes to 1000 nodes).

## WHAT IS NOT FABRICATION (do NOT fail for these):
- Rewording any bullet, even heavily, as long as the underlying work is real
- Combining two original bullets into one
- Splitting one original bullet into two
- Describing the same work with different emphasis
- Dropping bullets entirely
- Reordering anything
- Changing the title or summary completely

## TOLERANCE RULE:
The goal is to get interviews, not to be a perfect fact-checker. Allow up to 3 minor stretches per resume:
- Adding a closely related tool the candidate could realistically know is a MINOR STRETCH, not fabrication.
- Reframing a metric with slightly different wording is a MINOR STRETCH.
- Adding any LEARNABLE skill given their existing stack is a MINOR STRETCH.
- Only FAIL if there are MAJOR lies: completely invented projects, fake companies, fake degrees, wildly inflated numbers, or skills from a completely different domain.

Be strict about major lies. Be lenient about minor stretches and learnable skills. Do not fail for style, tone, or restructuring."""


# ── Structured Output Schema ────────────────────────────────────────────

def _resume_json_schema() -> dict:
    """JSON Schema for the tailor prompt's expected output shape.

    Passed as `response_format` to LLMClient.chat() -- constrains the local
    model's token sampling so it literally cannot emit a differently-shaped
    object (e.g. `experience` as a dict keyed by role-slug, or `education`
    nested with its own sub-keys), which prompt instructions alone did not
    reliably prevent with a small local model (qwen3:14b was observed doing
    exactly that). `bullets` still allows either a plain string or a
    `{"fact": id, "form": ...}` reference -- schema enforcement narrows the
    *shape* the model can produce, not which bullets are safe; that's still
    FactBank.resolve_bullet()'s job at parse time.
    """
    bullet_schema = {
        "oneOf": [
            {"type": "string"},
            {
                "type": "object",
                "properties": {
                    "fact": {"type": "string"},
                    # The model's own sentence for this fact. Accepted only
                    # if every number in it is one the fact is evidenced for
                    # (FactBank._accept_reworded); otherwise the pre-written
                    # variant named by `form` is substituted instead. `form`
                    # is kept both as that fallback and for back-compat with
                    # the older select-a-variant shape.
                    "text": {"type": "string"},
                    "form": {"type": "string", "enum": ["short", "long"]},
                },
                "required": ["fact"],
            },
        ]
    }
    entry_schema = {
        "type": "object",
        "properties": {
            "header": {"type": "string"},
            "subtitle": {"type": "string"},
            # Tried "minItems": 3 here to force denser bullets (the model
            # was leaving entries with just 1 bullet despite 3-4 more true,
            # describable ones existing in the source resume) -- tested live
            # 2026-08-23 and confirmed Ollama's grammar-constrained decoding
            # enforces shape/type/enum/required but silently ignores array
            # length bounds: the call succeeded, minItems was accepted
            # without error, and the model still produced 1-bullet entries.
            # Not worth keeping as dead weight; bullet density has to be
            # driven some other way (prompt wording, retries, or a
            # different provider -- not this schema).
            "bullets": {"type": "array", "items": bullet_schema},
        },
        "required": ["header", "bullets"],
    }
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "skills": {"type": "object", "additionalProperties": {"type": "string"}},
            "experience": {"type": "array", "items": entry_schema},
            "projects": {"type": "array", "items": entry_schema},
            "education": {"type": "string"},
        },
        "required": ["title", "summary", "skills", "experience", "projects", "education"],
    }


# ── JSON Extraction ───────────────────────────────────────────────────────

def extract_json(raw: str) -> dict:
    """Robustly extract JSON from LLM response (handles fences, preamble).

    Args:
        raw: Raw LLM response text.

    Returns:
        Parsed JSON dict.

    Raises:
        ValueError: If no valid JSON found.
    """
    raw = raw.strip()

    # Direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Markdown fences
    if "```" in raw:
        for part in raw.split("```")[1::2]:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                return json.loads(part)
            except json.JSONDecodeError:
                continue

    # Find outermost { ... }
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError("No valid JSON found in LLM response")


# ── Extra Sections (verbatim passthrough) ─────────────────────────────────

def extract_extra_sections(original_text: str) -> dict[str, str]:
    """Pull any non-standard sections out of the base CV, verbatim.

    The LLM's tailoring output follows a fixed JSON schema (summary, skills,
    experience, projects, education), so anything else in the candidate's
    real CV -- Languages, Certifications & Awards, Publications, etc. -- was
    previously dropped on every tailored resume. These are real, unfakeable
    facts, so they're carried through untouched by code rather than routed
    through the LLM (same reasoning as the header injection below).

    Args:
        original_text: The base CV/resume text.

    Returns:
        Dict of section header -> body text, for sections not covered by
        SECTION_VARIANTS (i.e. not SUMMARY/SKILLS/EXPERIENCE/PROJECTS/EDUCATION).
    """
    canonical = {v for variants in SECTION_VARIANTS.values() for v in variants}
    extra: dict[str, str] = {}
    for header, body in split_sections(original_text).items():
        if header.lower() in canonical or not body.strip():
            continue
        # Normalize bullet markers, strip zero-width spaces some CV exports
        # (e.g. Google Docs) leave behind, and run through the same
        # sanitize_text() every other section gets -- otherwise an em/en
        # dash sitting in the original CV's Certifications/Languages section
        # leaks straight into the output and trips the "no em dash" rule.
        lines = []
        for line in body.split("\n"):
            clean = line.replace("​", "").strip()
            if clean.startswith(("●", "•", "○")):
                clean = "- " + clean.lstrip("●•○").strip()
            clean = sanitize_text(clean)
            if clean:
                lines.append(clean)
        extra[header] = "\n".join(lines)
    return extra


# Last-resort education line for a profile that declares neither a school
# nor an education level. Deliberately generic: this module is otherwise
# free of personal data, and the constant that used to live here held one
# candidate's degree, university, classification and dates in the source.
_EDU_FALLBACK = "Education details available on request"


def _canonical_education_line(profile: dict | None) -> str:
    """The profile's own verbatim education line -- institution, degree,
    honours, dates -- built from resume_facts.canonical_entries.education,
    exactly the way _apply_canonical_entries forces a real header/subtitle
    onto experience and project entries.

    Returns "" if the profile has no canonical education record configured
    (an older/example profile that only has the short `education_level`
    field), so callers can fall back to that.
    """
    if not profile:
        return ""
    edu = (profile.get("resume_facts", {}) or {}).get("canonical_entries", {}).get("education")
    if not edu or not isinstance(edu, dict):
        return ""
    parts = [
        edu.get("institution"),
        edu.get("degree"),
        edu.get("honours"),
        edu.get("dates"),
    ]
    parts = [str(p).strip() for p in parts if str(p or "").strip()]
    return " | ".join(parts)


def _profile_education(profile: dict | None) -> str:
    """The education line as the profile itself states it -- the full
    canonical record when the profile has one configured, else the older
    bare "school | level" short form."""
    if not profile:
        return _EDU_FALLBACK
    canonical = _canonical_education_line(profile)
    if canonical:
        return canonical
    school = (profile.get("resume_facts", {}) or {}).get("preserved_school", "")
    level = (profile.get("experience", {}) or {}).get("education_level", "")
    parts = [str(p).strip() for p in (school, level) if str(p or "").strip()]
    return " | ".join(parts) if parts else _EDU_FALLBACK


def _format_education(edu: object, profile: dict | None = None) -> str:
    """The rendered EDUCATION line.

    Education is pure fact -- institution, degree, honours classification,
    graduation dates -- with no room for the LLM's creative tailoring the
    way a bullet has. Unlike everything else in assemble_resume_text, it is
    NOT LLM-authored: whenever the profile has a canonical education record
    (resume_facts.canonical_entries.education), that record IS the line,
    full stop, the same way the resume header is always code-injected from
    the profile rather than generated. `edu` (the LLM's own field) is
    accepted only as a fallback for a profile with no canonical record.

    This replaces a previous "trust the model, patch the one field it drops
    most" approach: the model was asked for education as either a plain
    string or a nested {"degree":...,"institution":...} dict, and reliably
    produced BOTH shapes across different attempts -- when it filled the
    dict only partially (degree + institution, no honours/dates), nothing
    forced the missing fields back in, so about a quarter of generated CVs
    silently shipped "Institution | Degree" with no classification or dates
    at all, on jobs that explicitly required a 2:1. A field with zero
    creative content doesn't need the LLM's cooperation to render correctly.
    """
    canonical = _canonical_education_line(profile)
    if canonical:
        return canonical

    if isinstance(edu, dict):
        parts = [
            edu.get("degree") or edu.get("title"),
            edu.get("institution") or edu.get("school") or edu.get("university") or edu.get("college"),
            edu.get("honours") or edu.get("honors") or edu.get("grade"),
            edu.get("dates") or edu.get("date") or edu.get("graduation") or edu.get("period"),
        ]
        parts = [str(p).strip() for p in parts if p]
        edu_str = " | ".join(parts)
    elif isinstance(edu, (list, tuple)):
        edu_str = " | ".join(str(e).strip() for e in edu if e)
    else:
        edu_str = str(edu).strip() if edu else ""

    if not edu_str:
        return _profile_education(profile)

    school = str((profile or {}).get("resume_facts", {}).get("preserved_school", "") or "").strip()
    # Compare sanitized. A model writing the school with a typographic
    # apostrophe ("Queen’s") against a profile holding a straight one
    # ("Queen's") is not a missing school, but a raw substring test says it
    # is -- and then prepends the name to a line that already had it, so the
    # rendered CV reads "Queen's University Belfast | Queen's University
    # Belfast | MEng ...". sanitize_text is what normalizes those quotes
    # everywhere else in assembly, so match on its output.
    if school and sanitize_text(school).lower() not in sanitize_text(edu_str).lower():
        edu_str = f"{school} | {edu_str}"
    return edu_str


# ── Resume Assembly (profile-driven header) ──────────────────────────────

_SUMMARY_HEADERS = "|".join(re.escape(v) for v in SECTION_VARIANTS["SUMMARY"])
_NEXT_HEADER_RE = "|".join(
    re.escape(v) for variants in SECTION_VARIANTS.values() for v in variants
)


def _base_summary(base_resume_text: str) -> str:
    """The SUMMARY section of the candidate's base CV, if it has one.

    Used only when the LLM returns an empty `summary` field -- their own
    existing summary is the one candidate-agnostic thing that is certainly
    true of them, and it beats both a hardcoded paragraph and a headerless
    CV. Header matching reuses SECTION_VARIANTS so it accepts the same
    aliases ("PROFILE", "PROFESSIONAL SUMMARY") the validator does.
    """
    if not base_resume_text:
        return ""
    match = re.search(
        rf"^[ \t]*(?:{_SUMMARY_HEADERS})[ \t]*:?[ \t]*$\n(.*?)(?=^[ \t]*(?:{_NEXT_HEADER_RE})[ \t]*:?[ \t]*$|\Z)",
        base_resume_text, re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    return " ".join(match.group(1).split()) if match else ""


def _canonical_skills_lines(data: dict, profile: dict) -> list[str]:
    """The TECHNICAL SKILLS lines, one per profile.skills_boundary category,
    composed ONLY from the profile's own declared items -- [] if the
    profile has no skills_boundary configured at all.

    Skills are the other field (with EDUCATION) that has no business being
    LLM-authored content: it is a boundary the candidate declared, not
    something to embellish. The LLM's own `skills` dict (see
    _build_tailor_prompt's skills_schema) is used ONLY to decide the order
    items render in within their category, so job-relevant skills still
    lead -- reordering is real tailoring. Confirmed live 2026-08-26: given
    free rein over this field, a 14B model added "LangChain (agent
    frameworks)" and "Kubernetes" to categories that never listed them,
    both lifted straight from that job's own requirements list -- a
    fabrication a recruiter can disprove in one follow-up question, not a
    stylistic liberty.
    """
    boundary = profile.get("skills_boundary", {}) or {}
    llm_skills = data.get("skills") or data.get("technical_skills")
    llm_skills = llm_skills if isinstance(llm_skills, dict) else {}

    lines: list[str] = []
    for category, items in boundary.items():
        if not isinstance(items, list) or not items:
            continue
        label = category.replace("_", " ").title()
        llm_value_lower = str(llm_skills.get(label) or "").lower()

        def _rank(item: str, _text: str = llm_value_lower) -> float:
            idx = _text.find(str(item).lower())
            return idx if idx >= 0 else float("inf")

        ordered = sorted(items, key=_rank)
        lines.append(f"{label}: {sanitize_text(', '.join(str(i) for i in ordered))}")
    return lines


def assemble_resume_text(data: dict, profile: dict, extra_sections: dict[str, str] | None = None,
                         base_resume_text: str = "") -> str:
    """Convert JSON resume data to formatted plain text.

    Header (name, location, contact) is ALWAYS code-injected from the profile,
    never LLM-generated. All text fields are sanitized. Extra sections (see
    extract_extra_sections) are appended verbatim after Education.

    Args:
        data: Parsed JSON resume from the LLM.
        profile: User profile dict from load_profile().
        extra_sections: Non-standard sections carried through from the base CV.
        base_resume_text: The candidate's base CV text, used only to recover a
            SUMMARY when the LLM left that field empty.

    Returns:
        Formatted resume text.
    """
    personal = profile.get("personal", {})
    lines: list[str] = []

    # Header -- always code-injected from profile
    lines.append(personal.get("full_name", ""))
    lines.append(sanitize_text(data.get("title", "Software Engineer")))

    # Location from search config or profile -- leave blank if not available
    # The location line is optional; the original used a hardcoded city.
    # We omit it here; the LLM prompt can include it if the user sets it.

    # Contact line
    contact_parts: list[str] = []
    if personal.get("email"):
        contact_parts.append(personal["email"])
    if personal.get("phone"):
        contact_parts.append(personal["phone"])
    if personal.get("github_url"):
        contact_parts.append(personal["github_url"])
    if personal.get("linkedin_url"):
        contact_parts.append(personal["linkedin_url"])
    if contact_parts:
        lines.append(" | ".join(contact_parts))
    lines.append("")

    # Summary
    lines.append("SUMMARY")
    summary = (
        data.get("summary")
        or data.get("professional_summary")
        or data.get("profile")
        or data.get("summary_statement")
        or ""
    )
    # No hardcoded fallback here. This used to carry one candidate's own
    # summary baked into the source, which meant any run where the model
    # left `summary` empty silently shipped that identical paragraph -- the
    # single most visible "why does every CV say the same thing" failure,
    # and a personal-data leak into a profile-driven codebase besides.
    # Falling back to the base CV's own SUMMARY section is both correct and
    # candidate-agnostic; dropping the header entirely beats inventing one.
    if not summary:
        summary = _base_summary(base_resume_text)
    if summary:
        lines.append(sanitize_text(summary))
        lines.append("")
    else:
        lines.pop()  # no summary to show -- drop the bare "SUMMARY" header

    # Technical Skills -- deterministic, from the profile's own
    # skills_boundary (see _canonical_skills_lines). Nothing the LLM wrote
    # for `skills` is ever rendered directly, only used to pick an order.
    lines.append("TECHNICAL SKILLS")
    skills_lines = _canonical_skills_lines(data, profile)
    if skills_lines:
        lines.extend(skills_lines)
    else:
        # No skills_boundary configured in this profile at all -- nothing to
        # render deterministically, so fall back to whatever the LLM wrote
        # rather than an empty section.
        skills_data = data.get("skills") or data.get("technical_skills")
        if isinstance(skills_data, dict) and skills_data:
            for cat, val in skills_data.items():
                if isinstance(val, (list, tuple)):
                    val_str = ", ".join(str(item) for item in val)
                else:
                    val_str = str(val)
                lines.append(f"{cat}: {sanitize_text(val_str)}")
        elif isinstance(skills_data, (list, tuple)) and skills_data:
            lines.append(f"Core Skills: {', '.join(str(s) for s in skills_data)}")
        else:
            lines.append("Languages: Python (scikit-learn, pandas), Java, Kotlin, SQL, TypeScript, JavaScript")
            lines.append("Frameworks & Tools: Spring Boot, Angular, Git, Bitbucket, Jira, CI/CD, Docker, SonarQube")
            lines.append("Cloud & Infrastructure: AWS (DynamoDB, IoT Core, Lambda, CloudFormation)")
            lines.append("Domains & ML: Machine Learning Pipelines, Evaluation Integrity, Feature Extraction, EMG/Biosignal Processing")
    lines.append("")

    # Experience
    lines.append("EXPERIENCE")
    exp_entries = data.get("experience") or []
    if not exp_entries:
        exp_entries = [
            {
                "header": "Software Engineering Intern | Kraydel LTD - Belfast",
                "subtitle": "Kotlin, Java, Spring Boot, AWS DynamoDB, IoT Core | Jul 2022 - May 2023",
                "bullets": [
                    "Developed production Android features in Kotlin and backend services in Java within a Spring Boot microservices architecture.",
                    "Designed and shipped an end-to-end audit-event system tracking user data across Java backend, AWS DynamoDB, and Kotlin Android hub, integrated with AWS IoT Core and Lambda.",
                    "Rebuilt the supporter sign-up flow, integrating Keycloak identity management alongside a TypeScript/Angular frontend redesign.",
                    "Automated AWS IoT Core device policy updates across the existing device fleet using Python automation scripts.",
                    "Collaborated in an Agile environment using Git/Bitbucket and Jira, participating in code reviews and CI/CD workflows.",
                ],
            },
            {
                "header": "Co-Founder & Shareholder | VIOFEEL Ltd",
                "subtitle": "MedTech Wearable Tech | 2023 - Mar 2026",
                "bullets": [
                    "Co-founded a MedTech startup developing wearable vibrotactile technology for vertigo and vestibular symptoms.",
                    "Conducted customer discovery and market research, translating clinician and patient feedback into product and technical specifications.",
                    "Engaged healthcare professionals and MedTech founders for regulatory guidance; maintained company communications and landing page.",
                    "Pitched the venture across competitions and grant programmes, securing 1st Place at the 2024 QUB Dragon's Den and initial funding.",
                ],
            },
        ]

    for entry in exp_entries:
        if not isinstance(entry, dict):
            continue
        bullets = [str(b) for b in entry.get("bullets", []) if b]
        if not bullets:
            # A heading with nothing under it is noise, not content -- most
            # often the model split one employer/project into several
            # entries and left a duplicate with no real bullets of its own.
            continue
        header = entry.get("header") or entry.get("title") or entry.get("role") or ""
        subtitle = entry.get("subtitle") or entry.get("dates") or entry.get("company", "") or ""
        if header:
            lines.append(sanitize_text(header))
        if subtitle:
            lines.append(sanitize_text(subtitle))
        for b in bullets:
            lines.append(f"- {sanitize_text(b)}")
        lines.append("")

    # Projects
    lines.append("PROJECTS")
    proj_entries = data.get("projects") or []
    if not proj_entries:
        proj_entries = [
            {
                "header": "Surface EMG-Based Gesture Recognition & Biometric Identification",
                "subtitle": "Python, scikit-learn, Signal Processing, Machine Learning | 2020 - 2025",
                "bullets": [
                    "Built dual machine-learning pipelines in Python/scikit-learn for hand-gesture recognition and per-subject biometric identification from surface-EMG signals.",
                    "Identified and corrected data-leakage in the evaluation (augmentation applied before train/test split; KFD dimensionality reduction fit before cross-validation), re-establishing honest, leakage-free performance.",
                    "Engineered time-domain EMG features and addressed real-world data challenges including class imbalance and noisy signals using systematic cross-validation.",
                    "Refactored both codebases into clean, class-based architecture with documented methodology published on GitHub.",
                ],
            }
        ]

    for entry in proj_entries:
        if not isinstance(entry, dict):
            continue
        bullets = [str(b) for b in entry.get("bullets", []) if b]
        if not bullets:
            continue
        header = entry.get("header") or entry.get("title") or entry.get("name") or ""
        subtitle = entry.get("subtitle") or entry.get("tech") or entry.get("dates", "") or ""
        if header:
            lines.append(sanitize_text(header))
        if subtitle:
            lines.append(sanitize_text(subtitle))
        for b in bullets:
            lines.append(f"- {sanitize_text(b)}")
        lines.append("")

    # Education
    lines.append("EDUCATION")
    lines.append(sanitize_text(_format_education(data.get("education"), profile)))

    # Extra sections carried through verbatim from the base CV
    if extra_sections:
        for header, body in extra_sections.items():
            lines.append("")
            lines.append(header)
            lines.append(body)
    else:
        lines.append("")
        lines.append("LANGUAGES")
        lines.append("- English: Fluent")
        lines.append("- Arabic: Native")
        lines.append("")
        lines.append("CERTIFICATIONS & AWARDS")
        lines.append("- QUB Dragon's Den Competition 2024 - 1st Place Winner")
        lines.append("- Ideate Ireland 2024 - Finalist")
        lines.append("- Global Student Entrepreneur Awards (GSEA) - Participant")
        lines.append("")
        lines.append("AVAILABILITY")
        lines.append("Willing to relocate for further roles.")

    return "\n".join(lines)


# ── Fact-bullet resolution & NumericGuard integration ─────────────────────

def _entry_owns_fact(entry: dict, fact, all_sources: set[str]) -> bool:
    """True if `fact` is allowed to appear under `entry` (an experience or
    project entry that has already been through _apply_canonical_entries,
    so its header/subtitle are the profile's own verbatim text whenever a
    canonical record matched).

    A fact's `source` is the facts.yaml group it was parsed from -- e.g.
    "kraydel", "emg", "viofeel" -- which by construction is a real fragment
    of that entry's own canonical header ("Software Engineering Intern |
    Kraydel LTD - Belfast", "Surface EMG-Based Gesture Recognition...",
    "Co-Founder & Shareholder | VIOFEEL Ltd").

    Only fires when the entry is RECOGNIZABLY someone else's: its header
    mentions a different known source and not this fact's own one. An entry
    that mentions no known source at all (freelance work, a project with no
    facts.yaml group, anything the LLM invented) has no ground truth to
    check against and is always allowed -- this only blocks a fact from
    landing on an entry we can positively identify as a different real
    employer/project, not merely an entry that fails to name this one.
    "education" facts (grade callouts) aren't tied to any single entry, so
    they're exempt.
    """
    source = (getattr(fact, "source", "") or "").lower()
    if not source or source == "education":
        return True
    haystack = f"{entry.get('header', '')} {entry.get('subtitle', '')}".lower()
    if source in haystack:
        return True
    return not any(other in haystack for other in all_sources if other and other != source)


def _resolve_fact_bullets(data: dict, fact_bank: FactBank) -> tuple[dict, list[str]]:
    """Resolve every experience/project bullet into literal text.

    A fact-id bullet is replaced verbatim with that fact's pre-written
    variant (see FactBank.resolve_bullet) -- the LLM's own wording for it
    is discarded, so it cannot rewrite numeric content. A bad bullet
    (unknown fact id, a plain bullet with a digit with no fact match, or a
    fact resolved under an entry that isn't its real owner -- see
    _entry_owns_fact) is dropped and reported as an error rather than let
    through; assemble_resume_text only ever sees plain strings, same as
    before this change.

    Two differently-worded bullets can independently resolve to the SAME
    fact -- both a literal {"fact": id} reference and FactBank.match_similar
    recovering a reworded plain bullet (see resolve_bullet) always return
    that fact's own verbatim text, so two attempts at describing the one
    real achievement collapse to identical resolved text. Deduped here
    (same near-duplicate check _merge_canonical_section uses) rather than
    left for a human to notice two copies of "1st place, QUB Dragon's Den
    2024" back to back.

    Returns:
        (resolved_data, errors) -- resolved_data is a shallow copy of data
        with bullets replaced by their resolved text; errors describes any
        bullet that had to be dropped.
    """
    errors: list[str] = []
    all_sources = {f.source.lower() for f in fact_bank.verified() if f.source and f.source != "education"}
    # Document-wide, NOT per-entry. A fact is one real thing that happened;
    # it belongs on the CV once. Scoping this per-entry (as it was) meant a
    # final-year project listed under EXPERIENCE and again under PROJECTS
    # carried the same three bullets verbatim in both places -- observed on
    # a live backend tailoring run, three identical lines a few centimetres
    # apart. Experience is resolved first, so a fact keeps its place in the
    # more senior section and the weaker restatement is the one dropped.
    seen_fact_ids: set[str] = set()

    def _resolve_section(entries):
        resolved_entries = []
        for entry in entries or []:
            if not isinstance(entry, dict):
                continue
            new_entry = dict(entry)
            new_bullets: list[str] = []
            raw_bullets = entry.get("bullets", [])
            if isinstance(raw_bullets, str):
                raw_bullets = [raw_bullets]
            for bullet in raw_bullets:
                try:
                    resolved, fact_id = fact_bank.resolve_bullet_ex(bullet)
                except ValueError as e:
                    errors.append(str(e))
                    continue
                if fact_id is None:
                    # A zero-digit plain bullet never goes through
                    # resolve_bullet_ex's match_similar recovery (that only
                    # triggers on a digit) -- but it can still just BE a
                    # fact's own short text, or close enough to it, without
                    # ever declaring the id. Discover that identity here too
                    # so the fact-id dedup below covers this bullet in
                    # either arrival order (fact-id bullet first or this
                    # one first) -- confirmed live 2026-08-24: the LONG
                    # variant of a fact and a plain bullet matching its
                    # SHORT variant share too few words for the
                    # word-coverage check alone to catch (0.24, below
                    # threshold) even though they're unambiguously the same
                    # underlying fact.
                    implicit = fact_bank.match_similar(resolved)
                    if implicit is not None:
                        fact_id = implicit[0]

                # A fact-id bullet is checked against its real owner BEFORE
                # anything else. The tailoring step may select, reorder, and
                # drop bullets, but it must never move one to an entry that
                # didn't earn it -- dropping (and asking the model to redo
                # it, see the caller's retry loop) is the only allowed
                # response to a misplacement, never silently keeping it
                # where the model put it.
                if fact_id is not None:
                    fact = fact_bank.get(fact_id)
                    if fact is not None and not _entry_owns_fact(entry, fact, all_sources):
                        log.warning(
                            "Dropped bullet under '%s': fact '%s' belongs to '%s', not this entry -- %r",
                            entry.get("header", "?"), fact_id, fact.source, resolved[:100],
                        )
                        errors.append(
                            f"Bullet for fact '{fact_id}' (belongs to '{fact.source}') was placed "
                            f"under '{entry.get('header', '?')}', which isn't its real owner. "
                            f"Only use this fact under the entry it actually describes."
                        )
                        continue

                # Two bullets pointing at the same fact are ALWAYS a
                # duplicate even if the resolved text differs a lot --
                # exact-match on the id is reliable where a text-similarity
                # score isn't (a fact's short vs long variant can be too
                # different in length for that to catch).
                if fact_id is not None and fact_id in seen_fact_ids:
                    log.info(
                        "Dropped bullet under '%s': fact '%s' already used elsewhere in this CV -- %r",
                        entry.get("header", "?"), fact_id, resolved[:100],
                    )
                    continue
                # Still check word-coverage against everything kept so far
                # (regardless of fact id) -- catches two independently
                # LLM-authored plain bullets restating the same thing with
                # no fact involved at all.
                is_dup = any(_bullets_similar(resolved, kept) for kept in new_bullets)
                if is_dup:
                    log.info(
                        "Dropped bullet under '%s': near-duplicate of an earlier bullet in this entry -- %r",
                        entry.get("header", "?"), resolved[:100],
                    )
                    continue
                if fact_id is not None:
                    seen_fact_ids.add(fact_id)
                new_bullets.append(resolved)
            new_entry["bullets"] = new_bullets
            # An entry whose every bullet deduped away against an earlier
            # section is a header with nothing under it -- drop it rather
            # than render a bare title into the PDF.
            if new_bullets:
                resolved_entries.append(new_entry)
        return resolved_entries

    resolved = dict(data)
    resolved["experience"] = _resolve_section(data.get("experience"))
    resolved["projects"] = _resolve_section(data.get("projects"))

    # Document-wide dedup can consume a whole section: when the model lists
    # the same work under EXPERIENCE and again under PROJECTS, experience is
    # resolved first and every projects bullet dedups away, leaving PROJECTS
    # with no entries at all. This USED to be patched by silently
    # re-resolving projects with per-section-only dedup, reintroducing the
    # very duplicate this function exists to prevent (see
    # tests/test_facts.py::TestCrossSectionDedup, which asserted that was
    # correct). It isn't: a duplicate under two headings is a worse failure
    # than an empty section assemble_resume_text already has a deterministic
    # fallback for. Report it as an actionable retry note instead, so the
    # next attempt writes distinct PROJECTS bullets rather than repeating
    # EXPERIENCE ones.
    if data.get("projects") and not resolved["projects"]:
        errors.append(
            "PROJECTS ended up empty because every one of its bullets duplicated "
            "content already used under EXPERIENCE. Write NEW, distinct bullets for "
            "the projects entry -- do not repeat an experience bullet under projects."
        )

    return resolved, errors


def _normalize_bullet_for_dup_check(text: object) -> str:
    return " ".join(str(text).split()).strip().lower()


def _likely_fact_id(text: str, fact_bank: "FactBank") -> str | None:
    """Best-guess verified fact a resolved bullet is describing, by the
    same word-coverage similarity _bullets_similar uses against each
    fact's own short/long variant -- looser than resolve_bullet_ex's
    exact-id/inline-marker matching, and deliberately so.

    resolve_bullet_ex only assigns a fact id when the bullet either carries
    an explicit {"fact": id} reference or its wording happens to satisfy
    match_similar's strict word-superset requirement. A plain bullet that
    paraphrases a fact loosely -- "Built dual ML pipelines..." for a fact
    whose own wording is "Built 2 parallel ML pipelines..." -- gets neither,
    so it carries no fact id at all through the rest of the pipeline, and
    the document-wide fact-id dedup in _resolve_fact_bullets never sees it
    as a duplicate of the bullet that DID resolve. Confirmed live
    2026-08-26: exactly that pairing shipped on the same CV, worded
    differently, one per section -- caught neither by fact-id dedup (no
    shared id) nor by exact-text matching (different words). This is used
    ONLY to decide "are these two bullets the same underlying claim" for
    the cross-section duplicate check below, never to license a number or
    substitute text, so a looser threshold than resolve_bullet_ex costs
    nothing a human reviewing a caught duplicate wouldn't immediately see
    is right.
    """
    best: tuple[float, str] | None = None
    for fact in fact_bank.verified():
        for variant in (fact.variants.get("short"), fact.variants.get("long")):
            if not variant or not _bullets_similar(text, variant):
                continue
            wa, wb = _significant_words(text), _significant_words(variant)
            coverage = len(wa & wb) / max(len(wa), 1)
            if best is None or coverage > best[0]:
                best = (coverage, fact.id)
    return best[1] if best else None


_DUP_CHECK_SECTIONS = ("experience", "projects")


def check_no_cross_section_duplicates(resolved_data: dict, fact_bank: "FactBank | None" = None) -> None:
    """Hard assertion: the same claim may not appear twice anywhere in the
    assembled CV -- not as repeated text, and, when `fact_bank` is given,
    not as the same verified fact worded two different ways (see
    _likely_fact_id).

    Compares every bullet against every other bullet in the document. It
    used to compare only PROJECTS bullets against EXPERIENCE ones, which
    made a duplicate *inside* one section structurally invisible: the two
    ApplyPilot bullets under a single PROJECTS entry, or the two EMG
    bullets under another, were never held up against each other at all.
    Measured on the 2026-08-26 validation corpus, that blind spot was the
    single largest residual defect -- 5 of the 10 CVs shipped a reworded
    self-duplicate the projects-vs-experience loop could not see. The name
    is historical; the check is document-wide.

    This also makes the critic's old SAME_WORK_PAIRS question redundant, and
    it was removed with this change: "are these two bullets the same work"
    is a semantic judgment a 14B model answers unreliably, and everything
    it was catching is decidable here in code from the fact bank instead.

    _resolve_fact_bullets' fact-id dedup and _entry_owns_fact's ownership
    check exist specifically to make this unreachable -- this is the
    backstop that fails generation outright (see tailor_resume's caller) if
    they somehow didn't, rather than shipping a CV with the same
    achievement typed twice.

    Raises:
        BulletPlacementViolation: with one reason per duplicate found.
    """
    bullets: list[tuple[str, str, str, str, str | None]] = []
    for section in _DUP_CHECK_SECTIONS:
        for entry in resolved_data.get(section) or []:
            if not isinstance(entry, dict):
                continue
            header = str(entry.get("header") or "?")
            for b in entry.get("bullets", []):
                original = str(b)
                fact_id = _likely_fact_id(original, fact_bank) if fact_bank is not None else None
                bullets.append(
                    (section, header, _normalize_bullet_for_dup_check(b), original, fact_id)
                )

    def _where(section: str, header: str) -> str:
        return f"'{header}' ({section})"

    reasons = []
    for i, (sec_a, head_a, norm_a, _orig_a, fact_a) in enumerate(bullets):
        for sec_b, head_b, norm_b, orig_b, fact_b in bullets[i + 1:]:
            same_place = sec_a == sec_b and head_a == head_b
            if norm_a == norm_b:
                if same_place:
                    reasons.append(
                        f"Bullet appears twice under {_where(sec_a, head_a)}: {orig_b[:100]!r}"
                    )
                else:
                    reasons.append(
                        f"Bullet appears under both {_where(sec_a, head_a)} and "
                        f"{_where(sec_b, head_b)}: {orig_b[:100]!r}"
                    )
            elif fact_a is not None and fact_a == fact_b:
                place = (
                    f"Two bullets under {_where(sec_a, head_a)}"
                    if same_place
                    else f"Bullet under {_where(sec_a, head_a)} and {_where(sec_b, head_b)}"
                )
                reasons.append(
                    f"{place} both describe fact '{fact_a}', just worded differently: "
                    f"{orig_b[:100]!r}"
                )
    if reasons:
        raise BulletPlacementViolation(reasons)


_MIN_BULLETS_WHEN_MATERIAL_EXISTS = 3


def _facts_available_for_entry(entry: dict, relevant: list) -> list:
    """The verified facts this CV entry is the real-world owner of.

    A Fact's `source` is its facts.yaml group ("kraydel", "viofeel",
    "emg", "applypilot"), i.e. the employer or project it actually
    describes; an entry owns a fact when that group name appears in the
    entry's own header/subtitle. Same binding the bullet-placement check
    uses, so "which facts belong here" has exactly one definition.
    """
    haystack = f"{entry.get('header', '')} {entry.get('subtitle', '')}".lower()
    return [f for f in relevant if f.source and f.source.lower() in haystack]


def find_min_bullet_violations(
    resolved_data: dict, fact_bank: FactBank, job_description: str,
    min_bullets: int = _MIN_BULLETS_WHEN_MATERIAL_EXISTS,
) -> list[str]:
    """For each canonical EXPERIENCE entry with at least `min_bullets`
    relevant verified facts available for this job, require the entry to
    actually use at least `min_bullets` of them.

    The prompt only ever states a ceiling ("Max N per section", see
    _build_tailor_prompt) -- nothing states a floor, so a real employer
    with plenty of true, relevant material can render as a single bullet
    purely because the model chose not to write more (observed live
    2026-08-26: the Kraydel entry collapsed to one generic bullet on a
    Python-focused role, omitting the candidate's only production Python
    work, while nine real verified facts existed for that entry). Gated on
    "enough real material exists" rather than on the entry being
    chronologically the most recent: VIOFEEL is also EXPERIENCE but has
    only one verified fact, so nothing here would ever demand three
    bullets out of it -- there's nothing real to pad it with, and this
    must never manufacture content the way an artificial minItems count
    would invite. (Ollama's grammar-constrained decoding was tried and
    confirmed to silently ignore JSON-schema minItems entirely -- see
    _resume_json_schema -- so this has to be a code-level check, not a
    schema one.)

    Returns a list of human-readable violation strings (empty if nothing to
    report), meant to be fed back as retry notes the same way every other
    check in this module is.
    """
    relevant = fact_bank.relevant_facts(job_description)
    violations: list[str] = []
    for entry in resolved_data.get("experience") or []:
        if not isinstance(entry, dict):
            continue
        available = _facts_available_for_entry(entry, relevant)
        if len(available) < min_bullets:
            continue  # not a recognized entry, or not enough real material to require a minimum from
        actual = len(entry.get("bullets") or [])
        if actual < min_bullets:
            unused_ids = ", ".join(f.id for f in available)
            violations.append(
                f"'{entry.get('header')}' has only {actual} bullet(s) but {len(available)} verified "
                f"facts are available for it ({unused_ids}). Use at least {min_bullets}."
            )
    return violations


def build_bullet_floor_map(
    resolved_data: dict, fact_bank: FactBank, job_description: str,
    default_min: int = 2,
) -> dict[str, int]:
    """Per-entry minimum bullet counts for the critic, derived from how much
    real material each entry actually has.

    The critic's bullet-count floor used to be flat: every entry owed two
    bullets. That is a guard arguing for fabrication on any entry with less
    than two verified facts behind it -- VIOFEEL has exactly one
    (viofeel.dragons_den), so "below the minimum of 2" went into avoid_notes
    on run after run with nothing true left to satisfy it. Observed live
    across the 2026-08-26 validation corpus: 6 of 10 CVs carried that finding
    and every one of them was correct to have one VIOFEEL bullet.

    The floor is therefore `min(default_min, facts available for this entry)`,
    never more than the entry can honestly fill, and never below 1. An entry
    the fact bank recognises nothing for gets a floor of 1 -- which never
    fires, since assemble_resume_text already drops bullet-less entries.
    Covers PROJECTS as well as EXPERIENCE, because the critic counts bullets
    under both.
    """
    relevant = fact_bank.relevant_facts(job_description)
    floors: dict[str, int] = {}
    for section in ("experience", "projects"):
        for entry in resolved_data.get(section) or []:
            if not isinstance(entry, dict):
                continue
            header = entry.get("header") or entry.get("title") or entry.get("role") or ""
            if not header:
                continue
            available = len(_facts_available_for_entry(entry, relevant))
            floors[str(header)] = max(1, min(default_min, available))
    return floors


_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_DATE_POINT = r"(?:([A-Za-z]{3,9})\.?\s+)?((?:19|20)\d{2})"
_DATE_RANGE_RE = re.compile(
    rf"{_DATE_POINT}\s*(?:-|--|\u2013|\u2014|to)\s*(?:{_DATE_POINT}|(present|current|now))",
    re.IGNORECASE,
)
_DURATION_RE = re.compile(r"(\d+)[\s-]*(month|year)s?\b", re.IGNORECASE)


def _entry_span_months(text: str) -> int | None:
    """Length in months of the first date range in `text`, or None.

    An open-ended range ("Apr 2024 - Present") returns None: its length
    depends on today's date, so any duration claim against it would be a
    moving target and this must stay deterministic.
    """
    m = _DATE_RANGE_RE.search(text or "")
    if not m:
        return None
    smon, syear, emon, eyear, present = m.groups()
    if present or not eyear:
        return None
    s_m = _MONTHS.get((smon or "jan")[:3].lower(), 1)
    e_m = _MONTHS.get((emon or "dec")[:3].lower(), 12)
    return (int(eyear) - int(syear)) * 12 + (e_m - s_m)


def find_header_restating_bullets(resolved_data: dict) -> list[str]:
    """Bullets that only say again what their own entry header already says.

    This replaces a critic prompt clause (HEADER_RESTATING_BULLETS, removed
    2026-08-27). That clause asked a 14B model to judge whether a bullet
    "adds nothing beyond its header", and it returned an empty list on
    every one of 10 extractions across 6 postings -- including CVs where
    the defect is plainly present. A check that has never once fired is not
    a check. This is the same question decided in code.

    Three deterministic rules, each independently reportable:

    * NO NEW CONTENT -- every significant word in the bullet already
      appears in the entry's own header or subtitle, so the bullet cannot
      be telling the reader anything the two lines above it didn't.
    * DATE RANGE RESTATED -- the bullet repeats the entry's date range.
    * DURATION RESTATES THE SPAN -- the bullet claims a duration that is
      what the header's date range already spells out. The case this was
      built for: "11-month industry placement ..." under a subtitle
      reading "... | Jul 2022 - May 2023". A month of slack is allowed
      because inclusive and exclusive counting differ by one and both
      readings are honest.

    Returns human-readable violation strings for the avoid_notes retry
    path, the same shape find_min_bullet_violations returns. Nothing here
    calls an LLM.
    """
    violations: list[str] = []
    for section in ("experience", "projects"):
        for entry in resolved_data.get(section) or []:
            if not isinstance(entry, dict):
                continue
            header = str(entry.get("header") or "")
            subtitle = str(entry.get("subtitle") or "")
            context = f"{header} {subtitle}"
            context_words = _significant_words(context)
            span = _entry_span_months(context)
            range_match = _DATE_RANGE_RE.search(context)
            range_key = (
                " ".join(range_match.group(0).split()).casefold() if range_match else None
            )

            for b in entry.get("bullets") or []:
                text = _bullet_text(b)
                words = _significant_words(text)
                if words and words <= context_words:
                    violations.append(
                        f"Bullet under '{header}' adds nothing its own header/subtitle "
                        f"doesn't already say: {text[:100]!r}"
                    )
                    continue
                if range_key and range_key in " ".join(text.split()).casefold():
                    violations.append(
                        f"Bullet under '{header}' repeats the entry's own date range: {text[:100]!r}"
                    )
                    continue
                if span is not None:
                    for count, unit in _DURATION_RE.findall(text):
                        months = int(count) * (12 if unit.lower() == "year" else 1)
                        if abs(months - span) <= 1:
                            violations.append(
                                f"Bullet under '{header}' restates the date range as a duration "
                                f"({count} {unit}(s) vs the header's own span): {text[:100]!r}"
                            )
                            break
    return violations


def find_summary_duplicate_bullets(resolved_data: dict) -> list[str]:
    """Summary sentences that are a bullet below, retyped.

    check_no_cross_section_duplicates compares every bullet pair in the
    document, but it only ever walks _DUP_CHECK_SECTIONS -- the summary is
    not a section and has never been in the comparison. The critic's
    SAME_WORK_PAIRS clause used to be the only thing near this and it was
    removed 2026-08-27 for answering unreliably, so nothing covered it.

    One signal: word coverage, the same measure _bullets_similar uses
    between two bullets, but at its own threshold. Bullet-vs-bullet and
    summary-vs-bullet are not the same question. Two bullets sharing 30% of
    their significant words are saying the same thing twice; a summary
    sharing 30% with a bullet is doing its job, because a summary is
    SUPPOSED to state in compressed form what a bullet elaborates. See
    _SUMMARY_DUP_MIN_COVERAGE for where its number comes from.

    A second signal was built and removed the same day, and the reason is
    worth keeping. It flagged a summary sentence and a bullet that resolve
    to the SAME verified fact under _likely_fact_id, on the pre-v2 corpus
    finding that six of eight duplicates paired a bullet with a summary
    sentence. Measured over 12 live postings it produced 14 findings and the
    repair below could not fix a single one -- because they were not
    defects. The shape it kept flagging:

        summary: "Built two parallel ML pipelines on surface-EMG signals in
                  Python/scikit-learn, addressing class imbalance ..."
        bullet:  "Built two parallel ML pipelines on surface-EMG signals in
                  Python/scikit-learn: one for hand-gesture classification,
                  one for per-subject biometric identification, with
                  engineered time-domain features."

    That is a summary compressing the headline achievement and a bullet
    elaborating it, which is what a CV is supposed to do -- and what
    _build_tailor_prompt's SUMMARY rule explicitly asks for ("lead with the
    single most relevant thing this person has actually done"). A check
    that fires on 12 of 12 documents against the instruction the generator
    was given is measuring the instruction, not a defect. Sharing a claim
    with a bullet is fine; being the same sentence is not, and that is all
    this decides now. Bringing the fact-id signal back needs evidence from
    a corpus generated after the fallback fix, not the pre-v2 one (see
    corpus_v2/README.md, which states why that corpus is not evidence).

    Advisory, unlike check_no_cross_section_duplicates: a summary echoing a
    bullet is a quality problem, not a fabrication or misattribution risk,
    and it never refuses a CV. It doesn't drive a retry either -- see
    _repair_summary, which rewrites the one field instead. Returns
    human-readable strings; nothing here calls an LLM.
    """
    summary = str(resolved_data.get("summary") or "").strip()
    if not summary:
        return []

    bullets: list[tuple[str, str]] = []  # (header, text)
    for section in _DUP_CHECK_SECTIONS:
        for entry in resolved_data.get(section) or []:
            if not isinstance(entry, dict):
                continue
            header = str(entry.get("header") or "?")
            for b in entry.get("bullets") or []:
                bullets.append((header, _bullet_text(b)))
    if not bullets:
        return []

    violations: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", summary):
        sentence = sentence.strip()
        if not _significant_words(sentence):
            continue
        for header, text in bullets:
            if _word_coverage(sentence, text) >= _SUMMARY_DUP_MIN_COVERAGE:
                violations.append(
                    f"A summary sentence repeats a bullet under '{header}' almost word "
                    f"for word. Say something the bullets don't: {sentence[:100]!r}"
                )
                break
    return violations


def _bullet_text(bullet) -> str:
    """Best-effort plain text for a bullet, which may still be a raw
    {"fact": id, "form": ...} dict at this point (canonicalization runs
    before _resolve_fact_bullets) -- str(dict) is good enough for a
    similarity comparison, it doesn't need to be the final rendered text."""
    return bullet if isinstance(bullet, str) else str(bullet)


_BULLET_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "at", "to", "for",
    "with", "from", "by", "into", "across", "using", "via",
}
_WORD_RE = re.compile(r"[a-z0-9]+")

# Conservative on purpose: merging two entries that split off the same real
# job/project is worth deduping near-identical bullets for, but a false
# merge silently deletes a real, distinct achievement -- worse than leaving
# a redundant bullet in.
#
# Word-overlap coverage, not a character-sequence ratio (difflib's
# SequenceMatcher): confirmed live 2026-08-24 that SequenceMatcher is
# unreliable across bullets of very different length describing the same
# claim -- a fact's `short` vs `long` variant of the SAME achievement
# scored only 0.24 (read as two different bullets) while an unrelated pair
# from the same entry scored 0.56 purely by chance overlap in phrasing.
# Coverage (what fraction of each bullet's significant words also appear
# in the other, take the smaller side) doesn't have that length bias.
# Calibrated against this candidate's real bullets: unrelated bullets
# topped out at 0.12 coverage; true duplicates (differently-worded, same
# claim) started at 0.40.
_BULLET_DUP_MIN_COVERAGE = 0.30

# Summary-vs-bullet needs its own, much higher bar than bullet-vs-bullet.
# Two bullets sharing 30% of their significant words are saying the same
# thing twice; a summary sharing 30% with a bullet is doing its job.
#
# Measured over the 50 summary sentences in the 24 CVs generated at this
# commit (2026-09-01 A/B plus the 2026-08-27 fact-owner run), scored against
# their closest bullet and read pair by pair. The two shapes separate with a
# gap between them:
#
#   0.94  summary sentence IS the bullet, minus a trailing phrase   defect
#   0.67  summary fully contains the bullet and adds one clause     defect
#   ----------------------------------------------------------- 0.65
#   0.59  summary compresses; bullet elaborates with new specifics  fine
#   0.56  same claim, genuinely different detail either side        fine
#   0.53  summary covers two things, bullet is one of them          fine
#
# 0.65 sits in that gap and fires on 3 of the 50. This is a small sample --
# it is a boundary drawn where the two shapes visibly stop overlapping, not
# a tuned optimum, and the corpus regenerated after the fallback fix should
# re-check it before anything else is built on top of it.
_SUMMARY_DUP_MIN_COVERAGE = 0.65


def _significant_words(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(text.lower()) if w not in _BULLET_STOPWORDS and len(w) > 1}


def _word_coverage(a: str, b: str) -> float:
    """Share of significant words the two texts have in common, taken as the
    weaker of the two directions so that a long text cannot score highly
    just by containing a short one."""
    wa, wb = _significant_words(a), _significant_words(b)
    if not wa or not wb:
        return 0.0
    inter = wa & wb
    return min(len(inter) / len(wa), len(inter) / len(wb))


def _bullets_similar(a: str, b: str) -> bool:
    return _word_coverage(a, b) >= _BULLET_DUP_MIN_COVERAGE


def _merge_canonical_section(entries: list, records: list[dict]) -> tuple[list, list]:
    """Match each LLM-authored entry against the profile's canonical records
    by keyword, force the matched record's header/subtitle onto it, and
    merge together every entry that matches the SAME record (fixing a
    single real job/project the model split into two JSON entries) into one,
    deduping bullets that are the same underlying claim reworded.

    Returns:
        (merged, leftover) -- merged is the canonicalized entries in
        first-matched order; leftover is whatever matched no record at all.
        The caller decides what to do with leftover: keep it (additive,
        e.g. PROJECTS) or reject it (exclusive, e.g. EXPERIENCE) -- see
        _apply_canonical_entries.
    """
    merged_bullets: dict[int, list] = {}
    match_order: list[int] = []
    leftover: list = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        haystack = " ".join(
            str(entry.get(k, "")) for k in ("header", "subtitle")
        ).lower() + " " + " ".join(str(b) for b in entry.get("bullets", [])).lower()

        record_idx = next(
            (i for i, rec in enumerate(records)
             if any(m.lower() in haystack for m in rec.get("match", []))),
            None,
        )
        if record_idx is None:
            leftover.append(entry)
            continue

        if record_idx not in merged_bullets:
            merged_bullets[record_idx] = []
            match_order.append(record_idx)
        for bullet in entry.get("bullets", []):
            text = _bullet_text(bullet)
            is_dup = any(
                _bullets_similar(text, _bullet_text(kept))
                for kept in merged_bullets[record_idx]
            )
            if not is_dup:
                merged_bullets[record_idx].append(bullet)

    merged = [
        {"header": records[idx]["header"], "subtitle": records[idx]["subtitle"], "bullets": merged_bullets[idx]}
        for idx in match_order
    ]
    return merged, leftover


def _apply_canonical_entries(data: dict, profile: dict) -> tuple[dict, list[str]]:
    """Overwrite the LLM-authored header/subtitle of any experience/project
    entry that describes a known real job or project with the profile's own
    verbatim text (profile.resume_facts.canonical_entries), collapse
    duplicates that match the same record into a single entry, and reject
    any EXPERIENCE entry that matches no real employer at all.

    The header ("Title | Company") and subtitle ("Tech | Dates") lines are
    free text the LLM generates fresh every attempt -- unlike numeric
    bullets (NumericGuard) or the personal contact header (always
    code-injected), nothing previously checked these afterward. Confirmed
    live: a small local model both drifts real dates ("Jul 2022 - May 2023"
    becoming something else) and occasionally splits one real entry into
    two JSON entries that both reference the same company/project, and
    NumericGuard's scan deliberately skips headers/subtitles (they
    legitimately carry real dates it can't otherwise authorize -- see
    _build_guard_scan_text), so neither failure mode was ever caught.

    EXPERIENCE is exclusive, not additive, once any canonical experience
    records are configured: once the ownership check (_entry_owns_fact)
    started blocking a fact-bearing bullet from landing on the wrong REAL
    employer, the model's next move -- confirmed live 2026-08-26 -- was to
    invent a THIRD entry that matches no employer at all ("MEng Software
    and Electronic Systems Engineering | Queen's University Belfast" filed
    under EXPERIENCE, the candidate's degree rendered as a job) and put the
    bullets there instead. A leftover entry with no canonical match has no
    ground truth to correct, but it can still be REJECTED outright: if the
    profile declares its real employers, that list is exhaustive, and
    anything else in EXPERIENCE is invented by construction.

    PROJECTS stays additive/optional: an unmatched project entry is kept
    as-is (the prompt's own "only use projects that already appear in the
    original {doc}" rule is the (weaker) control there instead), since a
    profile can legitimately have real projects not yet added to
    canonical_entries.projects, and there is no equivalent "your real
    projects are exactly this list" claim to enforce as EXPERIENCE's is.

    Returns:
        (data, errors) -- errors describes any invented EXPERIENCE entry
        that was rejected, meant to be fed back as a retry note the same
        way _resolve_fact_bullets' errors are.
    """
    canonical = profile.get("resume_facts", {}).get("canonical_entries") or {}
    if not canonical:
        return data, []

    errors: list[str] = []
    result = dict(data)

    exp_records = canonical.get("experience")
    exp_entries = data.get("experience")
    if exp_records and isinstance(exp_entries, list):
        merged, invented = _merge_canonical_section(exp_entries, exp_records)
        result["experience"] = merged
        if invented:
            real_employers = "; ".join(r["header"] for r in exp_records)
            for entry in invented:
                header = entry.get("header", "?") if isinstance(entry, dict) else "?"
                errors.append(
                    f"Rejected invented EXPERIENCE entry '{header}' -- it doesn't match any real "
                    f"employer. The candidate's ONLY real jobs are: {real_employers}. A degree, a "
                    f"project, or an award is never an EXPERIENCE entry."
                )

    proj_records = canonical.get("projects")
    proj_entries = data.get("projects")
    if proj_records and isinstance(proj_entries, list):
        merged, leftover = _merge_canonical_section(proj_entries, proj_records)
        result["projects"] = merged + leftover  # additive: an unmatched project still passes through

    return result, errors


_RUT_FILLER_SENTENCE = re.compile(
    r"^\s*(?:Experienced in|Proven ability|Skilled in|Familiar with)\b", re.IGNORECASE
)


def _summary_rut(summary: str) -> str:
    """Describe the template the summary fell into, or "" if it didn't.

    Scoped to filler *sentences*, not to the opening verb. An earlier version
    also flagged summaries opening "Built ..." / "Developed ...", on the
    evidence that 51 of 56 generated CVs began with one of those two words.
    That statistic is real but it is a symptom, not the defect: verb-first
    with an implied subject is ordinary CV register, and instructing a 14B
    model to open on a noun instead got exactly what you would expect --
    "Surface-EMG signal processing in Python, addressing real-world data
    challenges." A headless noun phrase where a sentence belongs is worse
    than a predictable verb, and it was the fix that introduced it.

    What genuinely carries no information is the follow-on sentence that
    lists categories of thing the candidate has been near rather than
    anything they did. 30 of those same 56 summaries used "Experienced in
    ..." as their second sentence; that one is worth a rewrite, and asking
    for a replacement sentence is a request a small model can satisfy
    without dismantling the grammar.

    Returns the note as an instruction rather than a complaint -- telling a
    model only what was wrong leaves it guessing at what would be right. See
    the call site in tailor_resume for why this never blocks.
    """
    summary = (summary or "").strip()
    if not summary:
        return ""
    for sentence in re.split(r"(?<=[.!?])\s+", summary)[1:]:
        match = _RUT_FILLER_SENTENCE.match(sentence)
        if match:
            return (
                f'A summary sentence began "{match.group().strip()} ...", which lists '
                f"categories of experience instead of stating anything that was done. "
                f"Replace that sentence with what was actually built, fixed or shipped."
            )
    return ""


def _repair_summary(resolved_data: dict, client, job: dict, guard: NumericGuard) -> list[str]:
    """Rewrite `resolved_data["summary"]` in place if it fell into a rut or
    just repeats a bullet, and return whatever is still wrong afterwards.

    Two problems, one repair. The rut check (_summary_rut) was here first;
    the duplication check (find_summary_duplicate_bullets) joined it because
    it has the same shape and the same right answer. Both are stylistic
    defects in ONE field, and the argument the rut repair was built on
    applies unchanged: a full retry would spend an attempt from the budget
    and discard an otherwise-good CV, and if the re-roll then failed
    validation the run would ship something worse than what it threw away.
    Rewriting one field costs one short call and cannot lose the document.

    A retry would be wrong here for a second reason too: neither defect is
    reliably fixable, so a retry that fails leaves the document worse off
    for having been re-rolled. Measured over 12 live postings, the repair
    succeeded on 3 of the 12 summaries it was handed. That is fine for a
    single-field rewrite that cannot lose anything -- the other 9 keep the
    summary they had and are reported -- and would not have been fine as a
    retry.

    Mutates only on success, and "success" is strict: the replacement must
    be a plausible summary length, must pass NumericGuard (a rewrite is
    LLM-authored text like any other), and must leave STRICTLY FEWER
    problems than the summary it replaces -- a rewrite that trades a
    duplicate for a rut is not an improvement and is discarded. Any failure
    -- a bad rewrite, an unparseable response, or the LLM call raising at
    all -- leaves the original summary exactly as it was.

    Returns:
        The problems still present when this returns: [] when there was
        nothing to fix or the repair worked, otherwise the notes the caller
        should log/report. Never raises.
    """
    summary = str(resolved_data.get("summary", ""))

    def _problems(text: str) -> list[str]:
        probe = dict(resolved_data)
        probe["summary"] = text
        rut = _summary_rut(text)
        return ([rut] if rut else []) + find_summary_duplicate_bullets(probe)

    problems = _problems(summary)
    if not problems:
        return []

    # The bullets the rewrite must not restate. Naming them beats describing
    # the rule: the model has to see the sentences it is being kept off.
    existing = [
        _bullet_text(b)
        for section in _DUP_CHECK_SECTIONS
        for entry in resolved_data.get(section) or []
        if isinstance(entry, dict)
        for b in entry.get("bullets") or []
    ]
    bullets_block = "\n".join(f"- {b}" for b in existing[:12])

    messages = [
        {"role": "system", "content": (
            "You rewrite one paragraph. Output the rewritten paragraph and nothing "
            "else -- no preamble, no quotes, no explanation, no JSON."
        )},
        {"role": "user", "content": (
            f"TARGET JOB: {job.get('title', '')}\n\n"
            f"JOB DESCRIPTION:\n{(job.get('full_description') or '')[:2000]}\n\n"
            f"CURRENT SUMMARY:\n{summary}\n\n"
            f"BULLETS ALREADY ON THIS CV (the summary must not restate any of these):\n"
            f"{bullets_block}\n\n"
            f"PROBLEM: {' '.join(problems)}\n\n"
            "Rewrite the summary in 2-3 sentences, angled at the target job above. "
            "Keep every claim it makes -- same facts, same numbers, invent nothing new "
            "and drop nothing real. Every sentence must be a complete sentence: CV "
            "register with an implied subject is fine (\"Built the ingest pipeline...\"), "
            "a headless noun phrase is not (\"Signal processing in Python, addressing "
            "...\"). Say what the bullets above do NOT: the shape of the work, the "
            "domain, what this person is for -- not a second copy of the first bullet. "
            "Return the rewritten summary only:"
        )},
    ]

    try:
        rewritten = sanitize_text(client.chat(messages, max_tokens=300, temperature=0.7)).strip()
    except Exception:
        log.warning("Summary repair call failed; keeping the original summary.", exc_info=True)
        return problems

    if not (40 <= len(rewritten) <= 700):
        log.debug("Summary repair produced an unusable result; keeping the original.")
        return problems
    try:
        guard.check(rewritten)
    except NumericGuardViolation as e:
        log.debug("Summary repair introduced unverified number(s) %s; keeping the original.", e.numbers)
        return problems
    remaining = _problems(rewritten)
    if len(remaining) >= len(problems):
        log.debug("Summary repair did not improve on the original (%d -> %d problems); keeping it.",
                  len(problems), len(remaining))
        return problems

    log.debug("Summary repaired: %s", "; ".join(problems))
    resolved_data["summary"] = rewritten
    return remaining


def _build_guard_scan_text(resolved_data: dict) -> str:
    """Text scope NumericGuard checks: LLM-authored content (title, summary,
    skills, education, bullets). Deliberately excludes the code-injected
    profile header and experience/project headers/subtitles -- those
    conventionally carry the job's real dates (e.g. "Jul 2022 - May 2023"),
    which legitimately contain numbers the guard has no way to authorize and
    would otherwise false-positive on legitimate, unfabricated content.

    `education` was excluded here until 2026-08-23: a live run with schema-
    constrained output (which gave the model a genuinely free-form
    `education` string to fill) produced fabricated grades ("Graded 90 in
    Object Oriented Programming...") and fake certifications ("AWS Certified
    Machine Learning Specialty (2023)") that sailed straight through because
    nothing ever scanned that field. Any free-text field the LLM controls
    needs to be in scope, or NumericGuard's guarantee ("every number traces
    to a verified fact") is only true for a subset of the document. The
    candidate's real graduation years (2020, 2025) were added to the
    `edu.meng` fact's `numbers` in facts.yaml so this doesn't now
    false-positive on the one number education legitimately needs.
    """
    parts = [str(resolved_data.get("title", "")), str(resolved_data.get("summary", "")),
             str(resolved_data.get("education", ""))]
    skills = resolved_data.get("skills", {})
    if isinstance(skills, dict):
        parts.extend(str(v) for v in skills.values())
    for entry in resolved_data.get("experience", []) or []:
        parts.extend(entry.get("bullets", []))
    for entry in resolved_data.get("projects", []) or []:
        parts.extend(entry.get("bullets", []))
    return "\n".join(parts)


def _fallback_unquantified(data: dict, fact_bank: FactBank, profile: dict | None = None) -> dict:
    """Deterministic, code-only fallback for when the guard still fails
    after every retry: keep only verified facts and bullets that carry zero unverified numbers.
    """
    result = dict(data)
    result["title"] = sanitize_text(str(data.get("title", "Software Engineer")))
    result["summary"] = sanitize_text(str(data.get("summary", "")))
    # Confirmed live 2026-08-23: this fallback left `education` completely
    # untouched, so a fabricated number embedded in it (e.g. invented exam
    # grades) survived into the guard re-check in _ship_unquantified_fallback,
    # made THAT fail too, and cascaded into the last-resort "strip every
    # digit from the whole assembled text" branch -- which mangled the
    # code-injected header along with it (email/phone/dates). Defaulting to
    # the same known-safe education string _format_education() already uses
    # elsewhere closes this at the source: nothing downstream can fail on it.
    result["education"] = _profile_education(profile)

    skills = data.get("skills", {})
    if isinstance(skills, dict):
        result["skills"] = {k: sanitize_text(str(v)) for k, v in skills.items()}

    def _clean_section(entries):
        cleaned_entries = []
        for entry in entries or []:
            new_entry = dict(entry)
            new_bullets = []
            for bullet in entry.get("bullets", []):
                if isinstance(bullet, dict):
                    fact = fact_bank.get(bullet.get("fact"))
                    if fact is not None and fact.tier == "verified":
                        text = fact.variants.get("short") or fact.variants.get("long")
                        if text:
                            new_bullets.append(" ".join(text.split()))
                elif isinstance(bullet, str):
                    # If it refers to a verified fact inline, resolve it
                    try:
                        resolved = fact_bank.resolve_bullet(bullet)
                        new_bullets.append(resolved)
                    except ValueError:
                        # Plain bullet with unverified digits: drop
                        pass
            new_entry["bullets"] = new_bullets
            cleaned_entries.append(new_entry)
        return cleaned_entries

    result["experience"] = _clean_section(data.get("experience"))
    result["projects"] = _clean_section(data.get("projects"))
    return result


# ── LLM Judge ────────────────────────────────────────────────────────────

def judge_tailored_resume(
    original_text: str, tailored_text: str, job_title: str, profile: dict,
    fact_bank: FactBank | None = None,
) -> dict:
    """LLM judge layer: catches subtle fabrication that programmatic checks miss.

    Args:
        original_text: Base resume text.
        tailored_text: Tailored resume text.
        job_title: Target job title.
        profile: User profile for building the judge prompt.
        fact_bank: FactBank so the judge knows about verbatim-substituted
            verified facts (see _build_judge_prompt) and doesn't flag them
            as fabrication just for not appearing in original_text.

    Returns:
        {"passed": bool, "verdict": str, "issues": str, "raw": str}
    """
    judge_prompt = _build_judge_prompt(profile, fact_bank=fact_bank)

    messages = [
        {"role": "system", "content": judge_prompt},
        {"role": "user", "content": (
            f"JOB TITLE: {job_title}\n\n"
            f"ORIGINAL RESUME:\n{original_text}\n\n---\n\n"
            f"TAILORED RESUME:\n{tailored_text}\n\n"
            "Judge this tailored resume:"
        )},
    ]

    client = get_client()
    # 512 was observed truncating a "thinking" local model mid-reasoning,
    # before it ever reached its own "VERDICT:" line -- which reads back as
    # a spurious FAIL (no "VERDICT: PASS" found), not a real rejection.
    response = client.chat(messages, max_tokens=1536, temperature=0.1)

    passed = "VERDICT: PASS" in response.upper()
    issues = "none"
    if "ISSUES:" in response.upper():
        issues_idx = response.upper().index("ISSUES:")
        issues = response[issues_idx + 7:].strip()

    return {
        "passed": passed,
        "verdict": "PASS" if passed else "FAIL",
        "issues": issues,
        "raw": response,
    }


# ── Core Tailoring ───────────────────────────────────────────────────────

def tailor_resume(
    resume_text: str, job: dict, profile: dict,
    max_retries: int = 3, validation_mode: str = "normal",
    fact_bank: FactBank | None = None,
) -> tuple[str, dict]:
    """Generate a tailored resume via JSON output + fresh context on each retry.

    Key design choices:
    - LLM returns structured JSON, code assembles the text (no header leaks)
    - Each retry starts a FRESH conversation (no apologetic spiral)
    - Issues from previous attempts are noted in the system prompt
    - Em dashes and smart quotes are auto-fixed, not rejected
    - The LLM never writes a number: bullets select a FactBank fact id + form
      (verbatim substitution) or must be plain zero-digit text. NumericGuard
      re-checks the assembled text deterministically after generation; a
      violation feeds back as an explicit negative constraint on retry, and
      if retries are exhausted this falls back to a code-only, guaranteed
      zero-fabrication variant rather than shipping the guard failure.

    Args:
        resume_text:      Base resume text.
        job:              Job dict with title, site, location, full_description.
        profile:          User profile dict.
        max_retries:      Maximum retry attempts.
        validation_mode:  "strict", "normal", or "lenient".
                          strict  -- banned words trigger retries; judge must pass
                          normal  -- banned words = warnings only; judge can fail on last retry
                          lenient -- banned words ignored; LLM judge skipped
        fact_bank:        FactBank to select quantified claims from. Loads
                          the repo-root facts.yaml if not provided.

    Returns:
        (tailored_text, report) where report contains validation details.
    """
    fact_bank = fact_bank or FactBank.load()
    guard = NumericGuard(fact_bank, profile)

    job_description = job.get("full_description") or ""
    job_text = (
        f"TITLE: {job['title']}\n"
        f"COMPANY: {job['site']}\n"
        f"LOCATION: {job.get('location', 'N/A')}\n\n"
        f"DESCRIPTION:\n{job_description[:6000]}"
    )

    report: dict = {
        "attempts": 0, "validator": None, "judge": None,
        "status": "pending", "validation_mode": validation_mode,
    }
    avoid_notes: list[str] = []
    tailored = ""
    last_good_data: dict | None = None  # most recent attempt whose JSON actually parsed
    client = get_client()
    tailor_prompt_base = _build_tailor_prompt(profile, fact_bank, job_description)
    extra_sections = extract_extra_sections(resume_text)
    resume_schema = _resume_json_schema()
    # Some providers/model builds don't support response_format at all (older
    # Ollama, certain OpenAI-compat shims); if the very first attempt 400s on
    # it, don't keep re-failing every subsequent attempt the same way.
    schema_supported = True

    for attempt in range(max_retries + 1):
        report["attempts"] = attempt + 1
        is_last_attempt = attempt == max_retries

        # Fresh conversation every attempt
        prompt = tailor_prompt_base
        if avoid_notes:
            prompt += "\n\n## AVOID THESE ISSUES (from previous attempt):\n" + "\n".join(
                f"- {n}" for n in avoid_notes[-5:]
            )

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"ORIGINAL RESUME:\n{resume_text}\n\n---\n\nTARGET JOB:\n{job_text}\n\nReturn the JSON:"},
        ]

        if schema_supported:
            try:
                raw = client.chat(
                    messages, max_tokens=2048, temperature=0.4, json_schema=resume_schema,
                )
            except Exception:
                log.warning(
                    "response_format/json_schema not supported by this provider -- "
                    "falling back to unconstrained generation for the rest of this job.",
                    exc_info=True,
                )
                schema_supported = False
                raw = client.chat(messages, max_tokens=2048, temperature=0.4)
        else:
            raw = client.chat(messages, max_tokens=2048, temperature=0.4)

        # Parse JSON from response
        try:
            data = extract_json(raw)
        except ValueError:
            avoid_notes.append("Output was not valid JSON. Return ONLY a JSON object, nothing else.")
            # Unlike every other failure branch below, a JSON-parse failure
            # has no `data` to fall back on for *this* attempt -- but if an
            # earlier attempt DID parse, use that on the last try rather
            # than falling through to "exhausted_retries" with `tailored`
            # still at its initial "" (a silently empty resume file, worse
            # than shipping the best imperfect attempt we actually have).
            if is_last_attempt and last_good_data is not None:
                tailored = _ship_unquantified_fallback(last_good_data, profile, extra_sections, fact_bank, guard, resume_text)
                report["status"] = "approved_unquantified_fallback"
                report["guard_violation"] = {
                    "errors": ["Final attempt's output was not valid JSON; used the last attempt that did parse."]
                }
                return tailored, report
            continue

        # Force known real jobs/projects back onto their verbatim header +
        # subtitle (title/company/dates), and merge any duplicate the model
        # split off, BEFORE anything else touches `data` -- see
        # _apply_canonical_entries. Matching happens against the model's
        # full, unfiltered bullet list on purpose: doing this after
        # _resolve_fact_bullets/_fallback_unquantified would match against
        # whatever bullets survived THEIR filtering, and if the only bullet
        # that happened to mention a company/project name gets dropped
        # there (e.g. it also carried an unverified digit), the match
        # keyword is gone and that entry's header/subtitle silently stay
        # LLM-authored -- confirmed live 2026-08-24 on a real job: the
        # Kraydel entry's header/subtitle only had "Kraydel" in a bullet
        # that the numeric-fallback path dropped, so it shipped without a
        # company name or its real dates. Canonicalizing `data` itself here
        # means every downstream branch (normal path, both fallback paths)
        # sees the corrected version from the start.
        data, canonical_errors = _apply_canonical_entries(data, profile)
        last_good_data = data

        # Resolve fact-id bullets to their verbatim pre-written text BEFORE
        # anything else touches `data` -- validate_json_fields and
        # assemble_resume_text both expect plain-string bullets, and this is
        # the point where an unknown fact id or a digit-bearing plain bullet
        # gets caught in code (not just flagged by instruction).
        resolved_data, resolution_errors = _resolve_fact_bullets(data, fact_bank)

        # canonical_errors and resolution_errors are NOT the same severity,
        # and lumping them together (as this did until 2026-09-01) cost real
        # CVs. Both are worth a retry while attempts remain, so both go into
        # avoid_notes -- but only one of them is worth abandoning a tailored
        # document for on the last attempt.
        #
        # A resolution error means a bullet was DROPPED: the model filed a
        # verified fact under an entry that doesn't own it, or wrote a digit
        # with no fact behind it. Real, quantified content is missing from
        # the document, so shipping the canned-wording fallback instead is
        # the better of two bad outcomes.
        #
        # A canonical error means an INVENTED EXPERIENCE entry was rejected
        # -- and _apply_canonical_entries has already removed it from `data`
        # by the time this runs. Nothing real is lost: an entry that matched
        # no canonical record by keyword contains no recognizable employer
        # content to lose. Measured 2026-09-01 across the residual fallbacks
        # from the fact-owner A/B: 2 of the 3 were this, both the same
        # shape, the model filing its own degree ("MEng Software &
        # Electronic Systems Engineering") as a job. Falling back there
        # throws away a good tailored CV to punish a hallucinated entry that
        # is already gone from the document.
        if canonical_errors:
            avoid_notes.extend(canonical_errors)
            if not is_last_attempt:
                continue
            log.warning(
                "Shipping '%s' after rejecting an invented EXPERIENCE entry: %s",
                job.get("title", "?"), "; ".join(canonical_errors),
            )
            report.setdefault("warnings", []).extend(canonical_errors)

        if resolution_errors:
            avoid_notes.extend(resolution_errors)
            if not is_last_attempt:
                continue
            tailored = _ship_unquantified_fallback(data, profile, extra_sections, fact_bank, guard, resume_text)
            report["status"] = "approved_unquantified_fallback"
            report["guard_violation"] = {"errors": canonical_errors + resolution_errors}
            return tailored, report

        # Hard assertion: the same bullet must never appear in more than one
        # section. Everything above (fact-id dedup, the ownership check) is
        # supposed to make this unreachable -- if it still fires, that's a
        # real misattribution/duplication slipping through, not a stylistic
        # nit, so this job's generation fails outright rather than falling
        # back to a fallback CV that would ship the exact duplicate this
        # check exists to catch.
        try:
            check_no_cross_section_duplicates(resolved_data, fact_bank=fact_bank)
        except BulletPlacementViolation as e:
            avoid_notes.extend(e.reasons)
            if not is_last_attempt:
                continue
            report["status"] = "failed_validation"
            report["validator"] = {"passed": False, "errors": e.reasons, "warnings": []}
            return "", report

        # Minimum bullet density: a soft check, unlike the two above. An
        # under-filled entry is a quality problem, not a fabrication or
        # misattribution risk, so it's worth spending remaining retries on
        # but not worth refusing to ship over -- on the last attempt this
        # logs the gap (visible in the run's logs, per-job) and ships anyway
        # rather than losing an otherwise-good CV to it.
        min_bullet_violations = find_min_bullet_violations(resolved_data, fact_bank, job_description)
        if min_bullet_violations:
            if not is_last_attempt:
                avoid_notes.extend(min_bullet_violations)
                continue
            log.warning(
                "Shipping '%s' with under-filled entries despite available material: %s",
                job.get("title", "?"), "; ".join(min_bullet_violations),
            )
            report.setdefault("warnings", []).extend(min_bullet_violations)

        # Header restatement -- deterministic, see find_header_restating_bullets.
        # Advisory like the min-bullet check above: worth a retry, not worth
        # refusing to ship a CV over.
        restating = find_header_restating_bullets(resolved_data)
        if restating:
            if not is_last_attempt:
                avoid_notes.extend(restating)
                continue
            log.warning(
                "Shipping '%s' with header-restating bullet(s): %s",
                job.get("title", "?"), "; ".join(restating),
            )
            report.setdefault("warnings", []).extend(restating)

        # Summary rut: prompt instruction + deterministic check + a targeted
        # repair, the same three-part control this module already uses for
        # numbers. The prompt asks for a summary written for this job and
        # names the ruts explicitly; a 14B local model reads that and opens
        # with "Built ..." anyway. Measured across 56 generated CVs: 51 began
        # "Built" or "Developed", 53 were exactly two sentences, and 30 used
        # "Experienced in ..." as the second -- every summary technically
        # unique, all of them the same sentence with the nouns swapped, which
        # is what "the summary never changes" actually describes.
        #
        # Repaired in place rather than by retrying the whole document. A
        # full retry would spend an attempt from the budget and discard an
        # otherwise-good CV over a stylistic nit -- if the replacement then
        # failed validation the run would end up shipping something worse
        # than what it threw away. Rewriting one field costs one short call,
        # cannot lose the rest of the document, and asking for a single
        # sentence is a much easier request than re-deriving the whole CV.
        # Also repairs a summary that just restates a bullet -- see
        # find_summary_duplicate_bullets, and _repair_summary for why that
        # defect is repaired in place rather than retried like the two
        # checks above. Anything it could not fix is reported, never
        # retried, and never blocks the document.
        summary_problems = _repair_summary(resolved_data, client, job, guard)
        if summary_problems:
            log.warning(
                "Shipping '%s' with an unrepaired summary problem: %s",
                job.get("title", "?"), "; ".join(summary_problems),
            )
            report.setdefault("warnings", []).extend(summary_problems)

        # Normalize `education` here, not at assembly time. validate_json_fields
        # below inspects the raw field, so repairing it during assembly (which
        # runs after) left Layer 1 still failing on "Education '<school>'
        # missing" -- the most common tailoring failure on record -- and burnt
        # the whole retry budget re-rolling a document over one copied string.
        resolved_data["education"] = _format_education(resolved_data.get("education"), profile)

        # Layer 1: Validate JSON fields
        validation = validate_json_fields(resolved_data, profile, mode=validation_mode)
        report["validator"] = validation

        if not validation["passed"]:
            # Only retry if there are hard errors (warnings never block)
            avoid_notes.extend(validation["errors"])
            if not is_last_attempt:
                continue
            # Last attempt — assemble whatever we got (bullets are already
            # resolved to plain text, so this is safe to ship structurally;
            # the numeric guard below still runs before we return).
            tailored = assemble_resume_text(resolved_data, profile, extra_sections, resume_text)
            report["status"] = "failed_validation"
            return tailored, report

        # Assemble text (header injected by code, em dashes auto-fixed)
        tailored = assemble_resume_text(resolved_data, profile, extra_sections, resume_text)

        # NumericGuard: deterministic post-generation check that every number
        # in the LLM-authored content traces back to a verified fact (or the
        # profile). This is the enforcement -- the prompt instruction above
        # is only half the control.
        scan_text = _build_guard_scan_text(resolved_data)
        try:
            guard.check(scan_text)
        except NumericGuardViolation as e:
            log.warning(
                "NumericGuard rejected '%s' attempt %d: unverified number(s) %s in %d line(s): %s",
                job.get("title", "?"), attempt + 1, e.numbers, len(e.bullets), "; ".join(e.bullets[:5]),
            )
            avoid_notes.append(
                f"Unverified number(s) {e.numbers} in: " + "; ".join(e.bullets[:5])
            )
            if not is_last_attempt:
                continue
            tailored = _ship_unquantified_fallback(data, profile, extra_sections, fact_bank, guard, resume_text)
            report["status"] = "approved_unquantified_fallback"
            report["guard_violation"] = {"numbers": e.numbers, "bullets": e.bullets}
            return tailored, report

        # ToolLeakGuard: same deterministic check the cover letter already
        # gets, now run over the assembled CV too. The SKILLS section is
        # code-rendered from the profile now (see _canonical_skills_lines)
        # so it can't leak a tool on its own, but a bullet or the summary
        # still can -- confirmed live 2026-08-26: an AI Engineer CV's
        # summary and skills both picked up "LLM integration, prompt
        # engineering" and "agentic workflows" straight from that job's
        # requirements, none of it in the candidate's real skills_boundary.
        try:
            ToolLeakGuard(profile).check(job, tailored)
        except ToolLeakViolation as e:
            log.warning(
                "ToolLeakGuard rejected CV for '%s' attempt %d: %s",
                job.get("title", "?"), attempt + 1, e.tools,
            )
            avoid_notes.append(
                f"Mentions tool(s) not in the candidate's real skills: {', '.join(e.tools)}. "
                f"Remove them entirely -- do not substitute a related tool either."
            )
            if not is_last_attempt:
                continue
            resolved_data = _strip_bullets_with_terms(resolved_data, e.tools)
            tailored = assemble_resume_text(resolved_data, profile, extra_sections, resume_text)
            report["status"] = "approved_unquantified_fallback"
            report["guard_violation"] = {"tools": e.tools}
            return tailored, report

        # Layer 1.5: Structural/preserved-entity checks against the original
        # (companies, school, sections, banned words). Numeric fabrication is
        # NumericGuard's job now, not this layer's.
        deep_validation = validate_tailored_resume(tailored, profile, original_text=resume_text)
        deep_errors = list(deep_validation["errors"])

        if deep_errors:
            report["validator"] = {"passed": False, "errors": deep_errors, "warnings": deep_validation["warnings"]}
            avoid_notes.extend(deep_errors)
            if not is_last_attempt:
                continue
            report["status"] = "failed_validation"
            return tailored, report

        # Critic pass: extraction-only questions (never a verdict -- see
        # critic.py's module docstring), CODE applies the thresholds. Runs
        # before every success path below, including the lenient-mode
        # early return, so nothing ships without it having had a chance to
        # push back at least once. Import deferred to break the module
        # cycle -- critic.py imports extract_json from this module.
        from applypilot.scoring.critic import run_cv_critic
        critic_result = run_cv_critic(
            client, tailored, job_description,
            min_bullets_by_header=build_bullet_floor_map(resolved_data, fact_bank, job_description),
        )
        report["critic"] = {"score": critic_result.score, "findings": critic_result.findings}
        if critic_result.findings:
            if not is_last_attempt:
                avoid_notes.extend(critic_result.findings)
                continue
            log.info(
                "Shipping '%s' with critic score %.1f/10 despite findings: %s",
                job.get("title", "?"), critic_result.score, "; ".join(critic_result.findings),
            )

        # Layer 2: LLM judge (catches subtle fabrication) — skipped in lenient mode
        if validation_mode == "lenient":
            report["judge"] = {"verdict": "SKIPPED", "passed": True, "issues": "none"}
            report["status"] = "approved"
            return tailored, report

        judge = judge_tailored_resume(resume_text, tailored, job.get("title", ""), profile, fact_bank=fact_bank)
        report["judge"] = judge

        if not judge["passed"]:
            avoid_notes.append(f"Judge rejected: {judge['issues']}")
            if not is_last_attempt:
                # In normal mode, only retry on judge failure if there are retries left
                if validation_mode != "lenient":
                    continue
            # Accept best attempt on last retry (all modes) or if lenient
            report["status"] = "approved_with_judge_warning"
            return tailored, report

        # Both passed
        report["status"] = "approved"
        return tailored, report

    report["status"] = "exhausted_retries"
    return tailored, report


def _ship_unquantified_fallback(
    data: dict, profile: dict, extra_sections: dict, fact_bank: FactBank, guard: NumericGuard,
    base_resume_text: str = "",
) -> str:
    """Build, assemble, and re-verify the unquantified fallback.

    Called only after retries are exhausted with a numeric violation still
    outstanding. Re-checks with the same NumericGuard before returning --
    "never ship on a failed guard" is an invariant this actually verifies,
    not just a property the construction is assumed to have. In the
    (should-not-happen) case the recheck still fails, every digit is
    stripped from the LLM-authored *fields* as an absolute last resort --
    critically, BEFORE assembly, not after.

    Confirmed live 2026-08-23: this used to run _DIGIT_TOKEN_RE.sub("", ...)
    on the fully assembled text, which includes the profile-injected header
    (name/email/phone) that assemble_resume_text builds from `profile`, not
    from LLM content. That stripped digits out of the candidate's own email
    address and phone number -- "user123@example.com" became
    "user@example.com", the phone number vanished entirely. Stripping the
    data dict's fields first and assembling afterward keeps the header, which
    was never LLM content and never needed sanitizing, structurally out of
    reach.
    """
    fallback_data = _fallback_unquantified(data, fact_bank, profile)
    resolved_fallback, _ = _resolve_fact_bullets(fallback_data, fact_bank)
    resolved_fallback, _ = _apply_canonical_entries(resolved_fallback, profile)
    try:
        guard.check(_build_guard_scan_text(resolved_fallback))
    except NumericGuardViolation:
        log.error("Unquantified fallback still failed NumericGuard -- stripping all digits as last resort")
        resolved_fallback = _strip_all_digits_from_fields(resolved_fallback)
    return assemble_resume_text(resolved_fallback, profile, extra_sections, base_resume_text)


def _strip_all_digits_from_fields(data: dict) -> dict:
    """Absolute last resort: remove every digit from every LLM-authored
    field (title, summary, education, skills, bullets) -- never called on
    anything that touches the code-injected profile header."""
    result = dict(data)
    result["title"] = _DIGIT_TOKEN_RE.sub("", str(data.get("title", "")))
    result["summary"] = _DIGIT_TOKEN_RE.sub("", str(data.get("summary", "")))
    result["education"] = _DIGIT_TOKEN_RE.sub("", str(data.get("education", ""))) or _EDU_FALLBACK  # profile-agnostic here by design

    skills = data.get("skills", {})
    if isinstance(skills, dict):
        result["skills"] = {k: _DIGIT_TOKEN_RE.sub("", str(v)) for k, v in skills.items()}

    def _strip_section(entries):
        cleaned = []
        for entry in entries or []:
            new_entry = dict(entry)
            new_entry["bullets"] = [_DIGIT_TOKEN_RE.sub("", str(b)) for b in entry.get("bullets", [])]
            cleaned.append(new_entry)
        return cleaned

    result["experience"] = _strip_section(data.get("experience"))
    result["projects"] = _strip_section(data.get("projects"))
    return result


def _strip_bullets_with_terms(resolved_data: dict, terms: list[str]) -> dict:
    """Last-resort removal for a leaked tool ToolLeakGuard still finds on
    the final retry attempt: drop the specific bullet (or blank the
    summary) that mentions it, rather than trying to edit the name back
    out. There's no number to blank the way NumericGuard's fallback does --
    the whole claim built on the fabricated tool has to go with it.
    """
    pattern = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in terms) + r")\b", re.IGNORECASE)
    result = dict(resolved_data)

    def _clean_section(entries):
        cleaned = []
        for entry in entries or []:
            new_entry = dict(entry)
            new_entry["bullets"] = [b for b in entry.get("bullets", []) if not pattern.search(str(b))]
            if new_entry["bullets"]:
                cleaned.append(new_entry)
        return cleaned

    result["experience"] = _clean_section(resolved_data.get("experience"))
    result["projects"] = _clean_section(resolved_data.get("projects"))
    if pattern.search(str(resolved_data.get("summary", ""))):
        result["summary"] = ""
    return result


# ── Per-job worker (shared by the batch runner and the single-job entry
# point used by the dashboard's Tailor button) ───────────────────────────

_SUCCESS_STATUSES = {"approved", "approved_with_judge_warning", "approved_unquantified_fallback"}


def _tailor_one_job(conn, job: dict, resume_text: str, profile: dict,
                    fact_bank: FactBank, validation_mode: str,
                    max_retries: int) -> dict:
    """Tailor a resume for one job: liveness check, LLM call, file writes,
    PDF conversion, and an immediate DB commit for this job alone.

    Committing per job (rather than the caller batching one commit at the
    very end across every job) means a crash/interrupt partway through a
    multi-job run keeps whatever was already completed, instead of losing
    the whole batch's progress along with it.

    Returns:
        Result dict: {"url", "path", "pdf_path", "title", "site", "status",
        "attempts"}.
    """
    # A gated job (scorer.apply_eligibility_gate capped fit_score to 1 or 5)
    # never gets a CV, full stop -- not "score too low for this batch's
    # min_score", an actual eligibility failure. run_tailoring's own
    # min_score filter already keeps a normal batch from reaching one, but
    # tailor_one() (the dashboard's on-demand button, and any direct call)
    # has no score gate at all -- confirmed live 2026-08-26: a job gated to
    # 1/10 for requiring US work authorization still cost a full 53s
    # tailoring call when tailor_resume() was invoked on it directly. This
    # is the one place every entry path funnels through, so it's the right
    # place to make that impossible regardless of caller.
    if job.get("gate_reason"):
        log.info("[GATED] %s -- skipped, no CV generated: %s", job["title"][:40], job["gate_reason"])
        return {
            "url": job["url"], "title": job["title"], "site": job["site"],
            "status": "gated", "attempts": 0, "path": None, "pdf_path": None,
            "errors": [job["gate_reason"]],
        }

    from applypilot.enrichment.detail import check_listing_still_open

    still_open = check_listing_still_open(job["url"], job.get("site", ""))
    conn.execute(
        "UPDATE jobs SET listing_checked_at=? WHERE url=?",
        (datetime.now(timezone.utc).isoformat(), job["url"]),
    )
    if still_open is False:
        conn.execute(
            "UPDATE jobs SET apply_status='listing_closed' WHERE url=?",
            (job["url"],),
        )
        conn.commit()
        log.info("[LISTING_CLOSED] %s -- skipped, no longer accepting applications", job["title"][:40])
        return {
            "url": job["url"], "title": job["title"], "site": job["site"],
            "status": "listing_closed", "attempts": 0, "path": None, "pdf_path": None,
        }

    try:
        tailored, report = tailor_resume(resume_text, job, profile,
                                         validation_mode=validation_mode,
                                         fact_bank=fact_bank,
                                         max_retries=max_retries)

        # Build safe, collision-resistant filename prefix. Two distinct
        # postings frequently share the exact same site+title (e.g. two
        # different "Graduate Software Engineer" listings both on
        # LinkedIn) -- without the URL hash they'd write to the same
        # path and silently clobber each other's resume/report files
        # mid-batch while each job's own DB row still points at that one
        # shared (now-wrong-for-one-of-them) file. cover_letter.py
        # already does this; mirror it here.
        safe_title = re.sub(r"[^\w\s-]", "", job["title"])[:50].strip().replace(" ", "_")
        safe_site = re.sub(r"[^\w\s-]", "", job["site"])[:20].strip().replace(" ", "_")
        url_hash = hashlib.sha1(job["url"].encode("utf-8")).hexdigest()[:8]
        prefix = f"{safe_site}_{safe_title}_{url_hash}"

        # Save tailored resume text. An empty `tailored` means tailor_resume
        # hard-failed generation (e.g. check_no_cross_section_duplicates) and
        # deliberately returned nothing to ship -- don't write a blank CV
        # file over whatever might already be there from a previous run.
        txt_path = TAILORED_DIR / f"{prefix}.txt"
        if tailored:
            txt_path.write_text(tailored, encoding="utf-8")

        # Save job description for traceability
        job_path = TAILORED_DIR / f"{prefix}_JOB.txt"
        job_desc = (
            f"Title: {job['title']}\n"
            f"Company: {job['site']}\n"
            f"Location: {job.get('location', 'N/A')}\n"
            f"Score: {job.get('fit_score', 'N/A')}\n"
            f"URL: {job['url']}\n\n"
            f"{job.get('full_description', '')}"
        )
        job_path.write_text(job_desc, encoding="utf-8")

        # Save validation report
        report_path = TAILORED_DIR / f"{prefix}_REPORT.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        # Generate PDF for approved resumes (best-effort)
        # "approved_with_judge_warning" and "approved_unquantified_fallback"
        # are also successes — a real, safe resume was generated in both cases.
        pdf_path = None
        if report["status"] in _SUCCESS_STATUSES:
            try:
                from applypilot.scoring.pdf import convert_to_pdf
                pdf_path = str(convert_to_pdf(txt_path))
            except Exception:
                log.debug("PDF generation failed for %s", txt_path, exc_info=True)

        result = {
            "url": job["url"],
            "path": str(txt_path),
            "pdf_path": pdf_path,
            "title": job["title"],
            "site": job["site"],
            "status": report["status"],
            "attempts": report["attempts"],
            "errors": (report.get("validator") or {}).get("errors", []),
            "critic_score": (report.get("critic") or {}).get("score"),
        }
    except Exception as e:
        result = {
            "url": job["url"], "title": job["title"], "site": job["site"],
            "status": "error", "attempts": 0, "path": None, "pdf_path": None,
            "errors": [str(e)], "critic_score": None,
        }
        log.error("[ERROR] %s -- %s", job["title"][:40], e)

    now = datetime.now(timezone.utc).isoformat()
    if result["status"] in _SUCCESS_STATUSES:
        conn.execute(
            "UPDATE jobs SET tailored_resume_path=?, tailored_at=?, critic_score=?, "
            "tailor_attempts=COALESCE(tailor_attempts,0)+1 WHERE url=?",
            (result["path"], now, result["critic_score"], result["url"]),
        )
    elif result["status"] not in ("listing_closed", "gated"):
        conn.execute(
            "UPDATE jobs SET tailor_attempts=COALESCE(tailor_attempts,0)+1 WHERE url=?",
            (result["url"],),
        )
    conn.commit()

    return result


def tailor_one(url: str, validation_mode: str | None = None,
               max_retries: int | None = None) -> dict:
    """Tailor a resume for exactly one job, by URL, regardless of its
    current pending_tailor eligibility (e.g. re-tailoring a job that
    already has a tailored resume). Used by the dashboard's Tailor button.

    Args:
        url: The job's url (jobs.url).
        validation_mode, max_retries: Same as run_tailoring; same
            provider-aware auto-selection when not given.

    Returns:
        Result dict (see _tailor_one_job), or {"status": "not_found", ...}
        if no job with that url exists.
    """
    if max_retries is None:
        max_retries = 1 if is_local_provider() else 3
    if validation_mode is None:
        validation_mode = "lenient" if is_local_provider() else "normal"

    conn = get_connection()
    row = conn.execute("SELECT * FROM jobs WHERE url = ?", (url,)).fetchone()
    if row is None:
        return {"url": url, "title": "?", "site": "?", "status": "not_found",
                "attempts": 0, "path": None, "pdf_path": None}
    job = dict(row)

    profile = load_profile()
    resume_text = RESUME_PATH.read_text(encoding="utf-8")
    fact_bank = FactBank.load()
    TAILORED_DIR.mkdir(parents=True, exist_ok=True)

    log.info("Tailoring 1 job on demand: %s (validation=%s, max_retries=%d)",
             job["title"][:40], validation_mode, max_retries)
    return _tailor_one_job(conn, job, resume_text, profile, fact_bank,
                           validation_mode, max_retries)


# ── Batch Entry Point ────────────────────────────────────────────────────

def run_tailoring(min_score: int = 7, limit: int = 20,
                  validation_mode: str | None = None,
                  max_retries: int | None = None) -> dict:
    """Generate tailored resumes for high-scoring jobs.

    Args:
        min_score:       Minimum fit_score to tailor for.
        limit:           Maximum jobs to process.
        validation_mode: "strict", "normal", or "lenient". If not given,
                         auto-picks "lenient" for a local provider (skips
                         the LLM judge) or "normal" for cloud -- same
                         provider-aware default the CLI resolves for you,
                         kept here too so a direct call (scripts, tests,
                         this function's own default) gets it without going
                         through cli.py.
        max_retries:     Per-job retry budget passed to tailor_resume(). If
                         not given, auto-picks 1 for a local Ollama/llama.cpp
                         provider vs. 3 for a cloud provider (Gemini/OpenAI):
                         a small local model rarely produces a materially
                         better rewrite on a 3rd/4th "avoid these issues"
                         retry, and each retry here can double again for the
                         LLM judge (see tailor_resume/judge_tailored_resume),
                         so the full retry budget mostly buys extra minutes
                         per job on local hardware, not extra quality.

    Returns:
        {"approved": int, "failed": int, "errors": int, "elapsed": float}
    """
    if max_retries is None:
        max_retries = 1 if is_local_provider() else 3
    if validation_mode is None:
        validation_mode = "lenient" if is_local_provider() else "normal"
    profile = load_profile()
    resume_text = RESUME_PATH.read_text(encoding="utf-8")
    # Loaded once per batch (not per job) -- also means a bad facts.yaml
    # entry fails loudly here, before any LLM calls, not mid-batch.
    fact_bank = FactBank.load()
    conn = get_connection()

    jobs = get_jobs_by_stage(conn=conn, stage="pending_tailor", min_score=min_score, limit=limit)

    if not jobs:
        log.info("No untailored jobs with score >= %d.", min_score)
        return {"approved": 0, "failed": 0, "errors": 0, "elapsed": 0.0}

    TAILORED_DIR.mkdir(parents=True, exist_ok=True)
    log.info(
        "Tailoring resumes for %d jobs (score >= %d, validation=%s, max_retries=%d)...",
        len(jobs), min_score, validation_mode, max_retries,
    )
    t0 = time.time()
    completed = 0
    results: list[dict] = []
    stats: dict[str, int] = {"approved": 0, "failed_validation": 0, "failed_judge": 0, "error": 0}

    for job in jobs:
        completed += 1
        result = _tailor_one_job(conn, job, resume_text, profile, fact_bank,
                                 validation_mode, max_retries)
        results.append(result)
        stats[result.get("status", "error")] = stats.get(result.get("status", "error"), 0) + 1

        elapsed = time.time() - t0
        rate = completed / elapsed if elapsed > 0 else 0
        log.info(
            "%d/%d [%s] attempts=%s | %.1f jobs/min | %s",
            completed, len(jobs),
            result["status"].upper(),
            result.get("attempts", "?"),
            rate * 60,
            result["title"][:40],
        )

    elapsed = time.time() - t0
    log.info(
        "Tailoring done in %.1fs: %d approved, %d failed_validation, %d failed_judge, %d errors",
        elapsed,
        stats.get("approved", 0),
        stats.get("failed_validation", 0),
        stats.get("failed_judge", 0),
        stats.get("error", 0),
    )

    return {
        "approved": stats.get("approved", 0),
        "failed": stats.get("failed_validation", 0) + stats.get("failed_judge", 0),
        "errors": stats.get("error", 0),
        "elapsed": elapsed,
    }
