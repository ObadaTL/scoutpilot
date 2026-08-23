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

from applypilot.config import RESUME_PATH, load_profile
from applypilot.database import get_connection, get_jobs_by_stage
from applypilot.llm import get_client

log = logging.getLogger(__name__)


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

RESPOND IN EXACTLY THIS FORMAT (no other text):
SCORE: [1-10]
KEYWORDS: [comma-separated ATS keywords from the job description that match or could match the candidate]
REASONING: [2-3 sentences explaining the score, EXPLICITLY addressing seniority fit]
COMPANY_SUMMARY: [2 sentences: what the company does, what the team builds. NULL if the description doesn't say.]
COMPANY_HOOK: [one concrete, specific thing worth mentioning in a cover letter -- a product, a technical problem, a domain. NULL if there's nothing specific enough.]"""


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
        lines.append(f"- Years of professional experience: {years}")
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

    score_match = re.search(r"\b(?:SCORE|Score)\b[:\*\s]*(\d+)", response, re.IGNORECASE)
    if score_match:
        try:
            score = int(score_match.group(1))
            score = max(1, min(10, score))
        except (ValueError, TypeError):
            score = 0

    kw_match = re.search(r"\b(?:KEYWORDS|Keywords)\b[:\*\s]*([^\n]+)", response, re.IGNORECASE)
    if kw_match:
        keywords = kw_match.group(1).strip().strip("*_")

    # Non-greedy, bounded to the next known field header (or end of string) --
    # REASONING used to grab everything to the end of the response, which
    # would swallow COMPANY_SUMMARY/COMPANY_HOOK whole once those were added.
    reason_match = re.search(
        r"\b(?:REASONING|Reasoning)\b[:\*\s]*([\s\S]+?)(?=\n\s*(?:COMPANY_SUMMARY|COMPANY_HOOK)\s*:|\Z)",
        response, re.IGNORECASE,
    )
    if reason_match:
        reasoning = reason_match.group(1).strip()
    else:
        reasoning = response.strip()

    summary_match = re.search(
        r"\bCOMPANY_SUMMARY\b[:\*\s]*([\s\S]+?)(?=\n\s*COMPANY_HOOK\s*:|\Z)",
        response, re.IGNORECASE,
    )
    company_summary = _clean_optional_field(summary_match.group(1) if summary_match else None)

    hook_match = re.search(r"\bCOMPANY_HOOK\b[:\*\s]*([^\n]+)", response, re.IGNORECASE)
    company_hook = _clean_optional_field(hook_match.group(1) if hook_match else None)

    return {
        "score": score, "keywords": keywords, "reasoning": reasoning,
        "company_summary": company_summary, "company_hook": company_hook,
    }


def score_job(resume_text: str, job: dict, profile: dict | None = None) -> dict:
    """Score a single job against the resume.

    Args:
        resume_text: The candidate's full resume text.
        job: Job dict with keys: title, site, location, full_description.
        profile: User profile dict -- used to make the candidate's actual
            experience level explicit (see _build_candidate_level). Optional
            only so score_job stays callable in isolation/tests.

    Returns:
        {"score": int, "keywords": str, "reasoning": str,
         "company_summary": str | None, "company_hook": str | None}
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
        return _parse_score_response(response)
    except Exception as e:
        log.error("LLM error scoring job '%s': %s", job.get("title", "?"), e)
        return {
            "score": 0, "keywords": "", "reasoning": f"LLM error: {e}",
            "company_summary": None, "company_hook": None,
        }


def run_scoring(limit: int = 0, rescore: bool = False) -> dict:
    """Score unscored jobs that have full descriptions.

    Args:
        limit: Maximum number of jobs to score in this run.
        rescore: If True, re-score all jobs (not just unscored ones).

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
    else:
        jobs = get_jobs_by_stage(conn=conn, stage="pending_score", limit=limit)

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
            "company_summary = ?, company_hook = ? WHERE url = ?",
            (result["score"], f"{result['keywords']}\n{result['reasoning']}",
             datetime.now(timezone.utc).isoformat(),
             result.get("company_summary"), result.get("company_hook"), job["url"]),
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
