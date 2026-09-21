"""Job fit scoring: LLM-powered evaluation of candidate-job match quality.

Scores jobs on a 1-10 scale by comparing the user's resume against each
job description. All personal data is loaded at runtime from the user's
profile and resume file.
"""

import json
import logging
import re
import time
from datetime import datetime, timezone

from scoutpilot.config import RESUME_PATH, load_profile
from scoutpilot.database import get_connection, get_jobs_by_stage, scoring_queue
from scoutpilot.llm import get_client
from scoutpilot.scoring.validator import ToolLeakGuard

log = logging.getLogger(__name__)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _strip_fabricated_skill_sentences(reasoning: str, job: dict, profile: dict) -> str:
    """Deterministic removal of any REASONING sentence that credits the
    candidate with a job-description tool/tech they don't actually have
    (see ToolLeakGuard).

    Confirmed live 2026-08-26: REASONING claimed "experience with LLM APIs
    (via Hugging Face)" for a candidate whose real resume never mentions
    Hugging Face, purely because the job posting asked for it. There's no
    retry budget in scoring to ask the model to redo this (score_job makes
    exactly one call), so this is sentence-level surgery -- the same
    failure mode cover_letter.py's retry-exhaustion fallback already
    handles for letters, applied here since scoring has no fallback path
    of its own to reuse.
    """
    if not reasoning:
        return reasoning
    guard = ToolLeakGuard(profile or {})
    sentences = _SENTENCE_SPLIT_RE.split(reasoning)
    kept = [s for s in sentences if not guard.find_leaks(job, s)]
    if not kept:
        return "Reasoning omitted after removing unverified skill claims."
    return " ".join(kept).strip()


# ── Scoring Prompt ────────────────────────────────────────────────────────

SCORE_PROMPT = """You are a job fit evaluator. Given a candidate's profile, resume, and a job description, score how well the candidate fits the role.

STEP 1 -- Determine the job's seniority level from the title AND the responsibilities (mentoring others, owning architecture/technical direction, X+ years required, Staff/Lead/Principal/Senior in the title all signal senior). Compare against the candidate's actual level from CANDIDATE LEVEL below -- not just their skills.

STEP 2 -- Score using these criteria:
- 9-10: Perfect match on BOTH skills AND seniority level.
- 7-8: Strong match. Most required skills present, minor gaps, AND seniority level is appropriate.
- 5-6: Moderate match. Some relevant skills but missing key requirements, OR a one-level seniority gap with no explicit junior-friendly language.
- 3-4: Weak match. Significant skill gaps, OR a clear seniority mismatch, unless the posting explicitly welcomes junior/graduate applicants.
- 1-2: Poor match. Completely different field, experience level, or seniority tier.

HARD RULE: A candidate with under 2 years of professional experience applying to a role titled or scoped as Senior/Staff/Lead/Principal/Architect (owns architecture, mentors others, X+ years explicitly required) should score 4 or below UNLESS the posting explicitly says junior/graduate candidates are welcome or experience requirements are flexible.

HARD RULE ON GRADUATE/ENTRY-LEVEL ROLES: Having SOME prior placement, internship, or industry experience is NEVER a penalty for a graduate/entry-level/junior posting -- it is a genuine advantage over a candidate with none, and REASONING must never describe it as excessive, a mismatch, or "slightly below" what the role wants. A candidate is only overqualified for a graduate role if their experience is at Senior level or above; a single placement/internship is not that, regardless of how many months it lasted.

IMPORTANT FACTORS:
- Weight technical skills heavily (programming languages, frameworks, tools)
- Consider transferable experience (automation, scripting, API work)
- Factor in the candidate's project experience
- Seniority mismatch is a HARD factor, not a minor deduction -- strong skill overlap does not outweigh a real seniority gap

HARD RULE ON COMPANY FIELDS: Base COMPANY_SUMMARY and COMPANY_HOOK ONLY on
what this job description actually says. Do not use anything you think you
know about this company from training. If the description doesn't say what
the company does or build, output NULL for both -- a guess is worse than
nothing.

HARD RULE ON REASONING: REASONING may only credit the candidate with a skill, tool, or technology that is LITERALLY present in the RESUME text below. Never write that the candidate has experience with something only because the JOB POSTING mentions it -- if the resume doesn't name it, it is not one of their skills, no matter how close the job's stack is to what they do have.

STEP 3 -- ELIGIBILITY EXTRACTION (separate from the score above; a deterministic
check applies these afterward, you are only extracting what the posting itself
says). Read the FULL posting body, not just a location tag -- a board can mislabel
location while the body states the real requirement (e.g. tagged "Remote GB" while
the body says "must be authorised to work in the USA").
- REQUIRED_COUNTRY: the single country/region this role legally requires the
  candidate to already be authorised to work in, if the posting states one
  explicitly (e.g. "USA", "United Kingdom", "must be an EU citizen"). A
  "Remote" tag does NOT by itself mean NULL here -- a role can be fully remote
  and still require the candidate to already live in and hold work
  authorisation for one specific country (e.g. "Remote (must be authorised to
  work in the USA)" is a real US requirement despite the word "Remote"). NULL
  only if the posting doesn't name a required country at all, is explicitly
  open to candidates anywhere, or explicitly offers visa sponsorship/relocation.
- REQUIRED_WORK_AUTH: the specific authorisation/visa status explicitly required
  or explicitly listed as acceptable (e.g. "US citizenship", "STEM OPT/F1",
  "UK right to work", "EU work permit"). NULL if not stated.
- MIN_YEARS_COMMERCIAL: the minimum years of commercial/professional (not
  academic/project) experience explicitly required, as a plain integer. NULL if
  the posting doesn't state a specific number.

RESPOND IN EXACTLY THIS FORMAT (no other text):
SCORE: [1-10]
KEYWORDS: [comma-separated ATS keywords from the job description that match or could match the candidate]
REASONING: [2-3 sentences explaining the score, EXPLICITLY addressing seniority fit]
COMPANY_SUMMARY: [2 sentences: what the company does, what the team builds. NULL if the description doesn't say.]
COMPANY_HOOK: [one concrete, specific thing worth mentioning in a cover letter -- a product, a technical problem, a domain. NULL if there's nothing specific enough.]
REQUIRED_COUNTRY: [see STEP 3. NULL if none stated.]
REQUIRED_WORK_AUTH: [see STEP 3. NULL if none stated.]
MIN_YEARS_COMMERCIAL: [see STEP 3. NULL if none stated.]"""


def _build_candidate_level(profile: dict) -> str:
    """Format the candidate's experience level for the scoring prompt.

    Scoring is done against the raw resume text alone, and smaller/local
    models are much weaker than large cloud models at inferring seniority
    from unstructured text -- they default to keyword/skill overlap and can
    badly overscore Senior/Staff/Lead roles for a graduate candidate. Making
    the candidate's actual level explicit closes that gap.
    """
    exp = profile.get("experience", {})
    years = exp.get("years_of_experience_total", "")
    target = exp.get("target_role", "")
    education = exp.get("education_level", "")

    lines = ["CANDIDATE LEVEL:"]
    if years:
        lines.append(
            f"- Years of professional experience: {years} "
            f"-- state this precisely in REASONING, do not round up to the next whole year"
        )
    if target:
        lines.append(f"- Target role: {target}")
    if education:
        lines.append(f"- Education: {education}")
    try:
        is_junior = years and float(years) < 2
    except (ValueError, TypeError):
        is_junior = False
    if is_junior:
        lines.append("- This candidate is looking for graduate/entry-level roles, NOT senior positions.")
    return "\n".join(lines)


_NULL_RE = re.compile(r"^[\"'*_\s]*null[\"'*_\s]*$", re.IGNORECASE)


def _clean_optional_field(raw: str | None) -> str | None:
    """Strip a captured field and map a literal 'NULL' response to None.

    The scoring prompt is explicitly told to output the literal word NULL
    for COMPANY_SUMMARY/COMPANY_HOOK when the job description doesn't
    support a real answer -- this turns that sentinel into an actual
    Python/DB NULL instead of storing the string "NULL".
    """
    if raw is None:
        return None
    cleaned = raw.strip().strip("*_")
    if not cleaned or _NULL_RE.match(cleaned):
        return None
    return cleaned


def _parse_score_response(response: str) -> dict:
    """Parse the LLM's score response into structured data.

    Args:
        response: Raw LLM response text.

    Returns:
        {"score": int, "keywords": str, "reasoning": str,
         "company_summary": str | None, "company_hook": str | None}
    """
    score = 0
    keywords = ""
    reasoning = ""

    # Field-label prefix: colon/asterisks then ONLY horizontal whitespace --
    # never \s, which also matches newlines. Confirmed live 2026-08-24: with
    # the old `[:\*\s]*` prefix, a genuinely empty KEYWORDS field (model
    # wrote "KEYWORDS:" then went straight to a newline, no content) let
    # that greedy prefix swallow the newline and start capturing from
    # "REASONING: <actual reasoning text>" instead -- keywords ended up
    # holding the reasoning's own first line (mislabeled), and the dashboard
    # then rendered that as "ATS keyword" chips. Same failure mode was
    # latent in every other field here; fixed uniformly.
    _LABEL_SEP = r"[:\*]*[ \t]*"

    score_match = re.search(rf"\b(?:SCORE|Score)\b{_LABEL_SEP}(\d+)", response, re.IGNORECASE)
    if score_match:
        try:
            score = int(score_match.group(1))
            score = max(1, min(10, score))
        except (ValueError, TypeError):
            score = 0

    kw_match = re.search(rf"\b(?:KEYWORDS|Keywords)\b{_LABEL_SEP}([^\n]+)", response, re.IGNORECASE)
    if kw_match:
        keywords = kw_match.group(1).strip().strip("*_")

    # Non-greedy, bounded to the next known field header (or end of string) --
    # REASONING used to grab everything to the end of the response, which
    # would swallow COMPANY_SUMMARY/COMPANY_HOOK whole once those were added.
    reason_match = re.search(
        rf"\b(?:REASONING|Reasoning)\b{_LABEL_SEP}([\s\S]+?)(?=\n\s*(?:COMPANY_SUMMARY|COMPANY_HOOK)\s*:|\Z)",
        response, re.IGNORECASE,
    )
    if reason_match:
        reasoning = reason_match.group(1).strip()
    else:
        reasoning = response.strip()

    summary_match = re.search(
        rf"\bCOMPANY_SUMMARY\b{_LABEL_SEP}([\s\S]+?)(?=\n\s*COMPANY_HOOK\s*:|\Z)",
        response, re.IGNORECASE,
    )
    company_summary = _clean_optional_field(summary_match.group(1) if summary_match else None)

    hook_match = re.search(rf"\bCOMPANY_HOOK\b{_LABEL_SEP}([^\n]+)", response, re.IGNORECASE)
    company_hook = _clean_optional_field(hook_match.group(1) if hook_match else None)

    country_match = re.search(rf"\bREQUIRED_COUNTRY\b{_LABEL_SEP}([^\n]+)", response, re.IGNORECASE)
    required_country = _clean_optional_field(country_match.group(1) if country_match else None)

    auth_match = re.search(rf"\bREQUIRED_WORK_AUTH\b{_LABEL_SEP}([^\n]+)", response, re.IGNORECASE)
    required_work_auth = _clean_optional_field(auth_match.group(1) if auth_match else None)

    years_match = re.search(rf"\bMIN_YEARS_COMMERCIAL\b{_LABEL_SEP}([^\n]+)", response, re.IGNORECASE)
    years_raw = _clean_optional_field(years_match.group(1) if years_match else None)
    min_years_commercial = None
    if years_raw:
        digits = re.search(r"\d+", years_raw)
        if digits:
            min_years_commercial = int(digits.group())

    return {
        "score": score, "keywords": keywords, "reasoning": reasoning,
        "company_summary": company_summary, "company_hook": company_hook,
        "required_country": required_country, "required_work_auth": required_work_auth,
        "min_years_commercial": min_years_commercial,
    }


# A country name/adjective the posting used -> its normalized canonical form,
# for comparing REQUIRED_COUNTRY (LLM-extracted, from the posting's own text)
# against the candidate's profile.personal.country. Deliberately covers only
# the handful of names likely to show up as an explicit eligibility
# requirement -- an unrecognized name still compares as itself, so a country
# missing from this map degrades to "no match" (gate fires) rather than
# "silently ignored", which is the safer failure direction for a hard gate.
_COUNTRY_ALIASES: dict[str, str] = {
    "usa": "united states", "us": "united states", "u.s.": "united states",
    "u.s.a.": "united states", "america": "united states",
    "united states of america": "united states",
    "uk": "united kingdom", "u.k.": "united kingdom", "great britain": "united kingdom",
    "britain": "united kingdom", "england": "united kingdom", "scotland": "united kingdom",
    "wales": "united kingdom", "northern ireland": "united kingdom",
    # ISO-3166 codes. Their absence produced the most obviously wrong gate
    # reason in the database (30 jobs on 2026-08-27): "Requires work
    # authorisation/location in GB; profile is based in United Kingdom."
    "gb": "united kingdom", "gbr": "united kingdom",
    "united kingdom of great britain and northern ireland": "united kingdom",
    "usa": "united states", "u.s.a": "united states",
}

# Permit types that confer an UNRESTRICTED right to work in the holder's own
# country -- i.e. the holder needs no sponsorship and no employer action.
# Matched as substrings of the profile's free-text work_permit_type.
_UNRESTRICTED_PERMITS = (
    "settled status", "pre-settled status", "eu settlement scheme",
    "indefinite leave to remain", "ilr", "right of abode",
    "citizen", "citizenship", "national",
    "permanent resident", "permanent residency", "green card",
)

# "UK"/"US" are only country names when capitalised -- lowercase "us" is a
# pronoun and matched "join us" style boilerplate. Everything else is
# unambiguous enough to match case-insensitively.
_CASE_SENSITIVE_COUNTRY_TOKENS = {"UK", "US", "GB", "EU"}

# A requirement phrased as a GENERIC right to work, as opposed to one naming
# a specific visa category. The distinction matters: an unrestricted permit
# at home satisfies "must have the right to work here", but it says nothing
# about "STEM OPT/F1", which is a specific US status the candidate either
# holds or doesn't.
_GENERIC_RIGHT_TO_WORK_RE = re.compile(
    r"\b(right to work"
    r"|authoris(?:ed|ation)\s+to\s+work|authoriz(?:ed|ation)\s+to\s+work"
    r"|eligible\s+to\s+work|permission\s+to\s+work"
    r"|work\s+authoris\w*|work\s+authoriz\w*"
    r"|legally\s+(?:able|entitled|authorised|authorized)\s+to\s+work"
    r"|able\s+to\s+work\s+(?:in|within))\b",
    re.IGNORECASE,
)


def _countries_in_text(text: str) -> set[str]:
    """Every country/region named anywhere in a free-text string, each
    resolved to its canonical name.

    "Belfast, Northern Ireland" -> {"united kingdom"};
    "UK / Ireland" -> {"united kingdom", "ireland"};
    "Remote (must be authorised to work in the USA)" -> {"united states"}.
    """
    found: set[str] = set()
    if not text:
        return found
    tokens = sorted(
        set(_COUNTRY_ALIASES) | set(_COUNTRY_ALIASES.values()), key=len, reverse=True
    )
    for tok in tokens:
        upper = tok.upper()
        if upper in _CASE_SENSITIVE_COUNTRY_TOKENS:
            if re.search(rf"\b{re.escape(upper)}\b", text):
                found.add(_COUNTRY_ALIASES.get(tok, tok))
        elif re.search(rf"\b{re.escape(tok)}\b", text, re.IGNORECASE):
            found.add(_COUNTRY_ALIASES.get(tok, tok))
    return found


def _country_in_text(text: str) -> str | None:
    """First country named anywhere in a free-text requirement, normalised.

    `required_country` is often null while the requirement string itself
    names the country ("Must be authorised to work in the United States"),
    so the work-auth check needs to resolve a country of its own rather
    than relying on the separate extraction.
    """
    if not text:
        return None
    tokens = sorted(
        set(_COUNTRY_ALIASES) | set(_COUNTRY_ALIASES.values()), key=len, reverse=True
    )
    for tok in tokens:
        upper = tok.upper()
        if upper in _CASE_SENSITIVE_COUNTRY_TOKENS:
            if re.search(rf"\b{re.escape(upper)}\b", text):
                return _COUNTRY_ALIASES.get(tok, tok)
        elif re.search(rf"\b{re.escape(tok)}\b", text, re.IGNORECASE):
            return _COUNTRY_ALIASES.get(tok, tok)
    return None


def _candidate_is_unrestricted(work_auth: dict) -> bool:
    """Whether the candidate needs nothing from an employer to be hired in
    their own country.

    Reads the profile's STRUCTURED fields first. The gate used to compare
    the posting's free-text requirement against the free-text
    `work_permit_type` by substring in both directions, which meant
    "Right to work in the UK" vs "Settled Status" failed to match and
    capped the score at 1 -- settled status being, of course, exactly an
    unrestricted right to work in the UK. That single mismatch gated 112
    jobs in the live database on 2026-08-27, with another 6 gated on a
    security-clearance line the same way.
    """
    if work_auth.get("legally_authorized_to_work") is True and not work_auth.get("require_sponsorship"):
        return True
    permit = str(work_auth.get("work_permit_type") or "").strip().lower()
    return any(tok in permit for tok in _UNRESTRICTED_PERMITS)


def _normalize_country(name: str | None) -> str | None:
    if not name:
        return None
    cleaned = re.sub(r"[^a-z\s.]", "", name.lower()).strip()
    if not cleaned:
        return None
    return _COUNTRY_ALIASES.get(cleaned, cleaned)


def apply_eligibility_gate(parsed: dict, profile: dict | None) -> dict:
    """Deterministic hard-eligibility check, run after the LLM's own score
    and before it's stored.

    The LLM only extracts what the posting itself says (REQUIRED_COUNTRY /
    REQUIRED_WORK_AUTH / MIN_YEARS_COMMERCIAL, read from the full body --
    see SCORE_PROMPT's STEP 3, deliberately NOT the job board's `location`
    column, which can disagree with the posting's own text, e.g. tagged
    "Remote GB" while the body requires US work authorization). The
    comparison against the candidate's actual profile happens here in code,
    not in the LLM's own judgement -- the same separation NumericGuard uses
    for numbers: the model reads and extracts, code enforces the hard rule.

    A posting requiring work authorization/location the candidate doesn't
    hold caps the score at 1 -- nothing else about the fit matters if
    they're not eligible to be hired. A posting requiring more commercial
    experience than the profile shows caps at 5. Both can fire together
    (the lower cap wins); neither fires if the LLM didn't extract a
    requirement, so a posting silent on eligibility is never gated.

    Returns:
        `parsed` with "score" capped if gated, plus a new "gate_reason" key
        (a human-readable string, or None if nothing was gated).
    """
    result = dict(parsed)
    profile = profile or {}
    reasons: list[str] = []
    caps: list[int] = []

    personal = profile.get("personal", {}) or {}
    work_auth = profile.get("work_authorization", {}) or {}
    candidate_country = _normalize_country(personal.get("country"))
    required_raw = parsed.get("required_country")
    # Resolve REQUIRED_COUNTRY to the set of countries/regions it actually
    # names, not one normalised string. A compound or qualified value like
    # "Belfast, Northern Ireland" or "UK / Ireland" used to normalise to
    # "belfast northern ireland" -- no alias match -- and cap every NI
    # employer to score 1 (measured 2026-09-02: Version 1, KX, Black Duck,
    # Expleo, all real Belfast schemes). The bar only fires when a country
    # is named AND the candidate's own country is not among those named.
    required_countries = _countries_in_text(str(required_raw or ""))
    whole = _normalize_country(required_raw)
    if whole and whole in set(_COUNTRY_ALIASES.values()):
        required_countries.add(whole)
    if required_countries and candidate_country and candidate_country not in required_countries:
        caps.append(1)
        reasons.append(
            f"Requires work authorisation/location in {required_raw}; "
            f"profile is based in {personal.get('country') or 'unknown'}."
        )

    required_auth_raw = str(parsed.get("required_work_auth") or "").strip()
    required_auth = required_auth_raw.lower()
    candidate_permit = str(work_auth.get("work_permit_type") or "").strip().lower()
    if required_auth:
        # A requirement naming a country the candidate isn't in is a real
        # bar, whatever their permit says at home.
        auth_country = _country_in_text(required_auth_raw)
        if auth_country and candidate_country and auth_country != candidate_country:
            # Don't double-report if the REQUIRED_COUNTRY check above already
            # accounted for this same country.
            if auth_country not in required_countries:
                caps.append(1)
                reasons.append(
                    f"Requires work authorisation in {auth_country.title()}; "
                    f"profile is based in {personal.get('country') or 'unknown'}."
                )
        elif _candidate_is_unrestricted(work_auth) and (
            _GENERIC_RIGHT_TO_WORK_RE.search(required_auth_raw)
            or (auth_country and auth_country == candidate_country)
        ):
            # Unrestricted at home, and the requirement is either a generic
            # right-to-work line or explicitly names the candidate's own
            # country. A named foreign visa category still falls through.
            pass
        elif required_auth not in candidate_permit and candidate_permit not in required_auth:
            caps.append(1)
            reasons.append(
                f"Requires '{parsed.get('required_work_auth')}'; profile's work authorisation is "
                f"'{work_auth.get('work_permit_type') or 'not specified'}'."
            )

    min_years = parsed.get("min_years_commercial")
    if min_years is not None:
        try:
            candidate_years = float((profile.get("experience", {}) or {}).get("years_of_experience_total") or 0)
        except (TypeError, ValueError):
            candidate_years = 0.0
        if min_years > candidate_years:
            caps.append(5)
            reasons.append(
                f"Requires {min_years}+ years commercial experience; profile shows {candidate_years:g}."
            )

    if reasons:
        result["gate_reason"] = " ".join(reasons)
        original_score = result.get("score") or 0
        result["score"] = min([original_score] + caps) if original_score else min(caps)
    else:
        result["gate_reason"] = None
    return result


def score_job(resume_text: str, job: dict, profile: dict | None = None) -> dict:
    """Score a single job against the resume.

    Args:
        resume_text: The candidate's full resume text.
        job: Job dict with keys: title, site, location, full_description.
        profile: User profile dict -- used to make the candidate's actual
            experience level explicit (see _build_candidate_level), and to
            apply the eligibility gate (see apply_eligibility_gate). Optional
            only so score_job stays callable in isolation/tests -- with no
            profile, the gate has nothing to compare against and never fires.

    Returns:
        {"score": int, "keywords": str, "reasoning": str,
         "company_summary": str | None, "company_hook": str | None,
         "gate_reason": str | None}
    """
    job_text = (
        f"TITLE: {job['title']}\n"
        f"COMPANY: {job['site']}\n"
        f"LOCATION: {job.get('location', 'N/A')}\n\n"
        f"DESCRIPTION:\n{(job.get('full_description') or '')[:6000]}"
    )

    candidate_level = _build_candidate_level(profile) + "\n\n" if profile else ""

    messages = [
        {"role": "system", "content": SCORE_PROMPT},
        {"role": "user", "content": f"{candidate_level}RESUME:\n{resume_text}\n\n---\n\nJOB POSTING:\n{job_text}"},
    ]

    try:
        client = get_client()
        response = client.chat(messages, max_tokens=1024, temperature=0.2)
        parsed = _parse_score_response(response)
        if profile is not None:
            parsed["reasoning"] = _strip_fabricated_skill_sentences(parsed["reasoning"], job, profile)
        return apply_eligibility_gate(parsed, profile)
    except Exception as e:
        log.error("LLM error scoring job '%s': %s", job.get("title", "?"), e)
        return {
            "score": 0, "keywords": "", "reasoning": f"LLM error: {e}",
            "company_summary": None, "company_hook": None, "gate_reason": None,
        }


def run_scoring(
    limit: int = 0,
    rescore: bool = False,
    channel: str | None = None,
    opp_type: str | None = None,
    keywords: str | list[str] | None = None,
    cohort: str | None = None,
    sample: bool = True,
) -> dict:
    """Score unscored jobs that have full descriptions.

    Args:
        limit: Maximum number of jobs to score in this run (0 = all available).
        rescore: If True, re-score all jobs (not just unscored ones).
        channel: Optional channel filter (e.g. 'direct_ats', 'hacker_news', 'graduate_schemes').
        opp_type: Optional opportunity type filter (e.g. 'graduate_scheme', 'funded_training').
        keywords: Optional keyword filter (e.g. 'AI, python, signal processing, machine learning').
        sample: On the default (no channel/opp_type/keywords/cohort) path, whether
            low-yield sources are sampled (see database.scoring_queue). False
            scores the whole eligible backlog instead of ~1-in-6 of it.

    Returns:
        {"scored": int, "errors": int, "elapsed": float, "distribution": list}
    """
    resume_text = RESUME_PATH.read_text(encoding="utf-8")
    profile = load_profile()
    conn = get_connection()

    if rescore:
        query = "SELECT * FROM jobs WHERE full_description IS NOT NULL"
        if limit > 0:
            query += f" LIMIT {limit}"
        jobs = conn.execute(query).fetchall()
    elif channel or opp_type or keywords or cohort:
        # Targeted run: honour the explicit filter, skip the yield-ordered queue.
        jobs = get_jobs_by_stage(
            conn=conn,
            stage="pending_score",
            limit=limit,
            channel=channel,
            opp_type=opp_type,
            keywords=keywords,
            cohort=cohort,
        )
    else:
        # Default run: order the backlog by each source's live hit rate, so
        # high-yield sources are scored first and low-yield ones are sampled
        # (see database.scoring_queue).
        urls = scoring_queue(conn=conn, limit=limit, sample=sample)
        if urls:
            placeholders = ",".join("?" for _ in urls)
            fetched = conn.execute(
                f"SELECT * FROM jobs WHERE url IN ({placeholders})", urls
            ).fetchall()
            by_url = {r["url"]: r for r in fetched}
            jobs = [by_url[u] for u in urls if u in by_url]
        else:
            jobs = []

    if not jobs:
        log.info("No unscored jobs with descriptions found.")
        return {"scored": 0, "errors": 0, "elapsed": 0.0, "distribution": []}

    # Convert sqlite3.Row to dicts if needed
    if jobs and not isinstance(jobs[0], dict):
        columns = jobs[0].keys()
        jobs = [dict(zip(columns, row)) for row in jobs]

    log.info("Scoring %d jobs sequentially...", len(jobs))
    t0 = time.time()
    completed = 0
    errors = 0
    results: list[dict] = []

    # Commit after every job (not just at the end) -- a run over hundreds of
    # jobs against a local model can take a long time, and a single
    # end-of-batch commit means any interruption loses all progress.
    for job in jobs:
        result = score_job(resume_text, job, profile)
        result["url"] = job["url"]
        completed += 1

        if result["score"] == 0:
            errors += 1

        results.append(result)

        conn.execute(
            "UPDATE jobs SET fit_score = ?, score_reasoning = ?, scored_at = ?, "
            "company_summary = ?, company_hook = ?, gate_reason = ? WHERE url = ?",
            (result["score"], f"{result['keywords']}\n{result['reasoning']}",
             datetime.now(timezone.utc).isoformat(),
             result.get("company_summary"), result.get("company_hook"),
             result.get("gate_reason"), job["url"]),
        )
        conn.commit()

        log.info(
            "[%d/%d] score=%d  %s",
            completed, len(jobs), result["score"], job.get("title", "?")[:60],
        )

    elapsed = time.time() - t0
    log.info("Done: %d scored in %.1fs (%.1f jobs/sec)", len(results), elapsed, len(results) / elapsed if elapsed > 0 else 0)

    # Score distribution
    dist = conn.execute("""
        SELECT fit_score, COUNT(*) FROM jobs
        WHERE fit_score IS NOT NULL
        GROUP BY fit_score ORDER BY fit_score DESC
    """).fetchall()
    distribution = [(row[0], row[1]) for row in dist]

    return {
        "scored": len(results),
        "errors": errors,
        "elapsed": elapsed,
        "distribution": distribution,
    }
