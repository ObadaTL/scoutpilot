"""Extraction-only "critic" pass over a tailored CV and cover letter.

Catches weak-but-true content none of the other guards can, because none
of it is a rule violation: nothing here is fabricated, misplaced, or an
exact/paraphrased duplicate (NumericGuard, BulletPlacementViolation,
ToolLeakGuard, and check_no_cross_section_duplicates already own those). A
bullet can be perfectly true and still address nothing in the posting --
and a cover letter sentence can be true in spirit while asserting something
the CV itself never actually backs.

A SAME_WORK_PAIRS question used to live here, asking the model whether two
bullets described the same underlying work. It was removed on 2026-08-27:
check_no_cross_section_duplicates now compares every bullet pair in the
document, including pairs inside one section, and decides the same question
from the fact bank in code. Measured across the 2026-08-26 corpus, this
model answers countable questions reliably and semantic ones unreliably, so
where a check can be made structural it should be -- and it should then run
in one place, not two.

A HEADER_RESTATING_BULLETS question went the same way on 2026-08-27, for a
blunter reason: it returned an empty list on all 10 extractions across all
6 postings in the validation corpus, including CVs carrying the defect in
plain sight. tailor.find_header_restating_bullets now decides it by
comparing each bullet against its own header, subtitle and date range.

DESIGN CONSTRAINT -- read before changing any prompt here: the critic is
NEVER asked for a verdict. A small local model asked "is this good?" or
"rate this 1-10" rubber-stamps its own output; this codebase already
avoids that pattern everywhere else (score_job's HARD RULEs exist because
free-form seniority judgment from a 14B model is unreliable on its own).
Every question below asks for something QUOTABLE -- an exact count, an
exact quote copied from the source text, or the literal token "NONE" --
and CODE (evaluate_cv_observations / evaluate_letter_observations) applies
the fixed thresholds to those answers. If a change here starts asking the
model to characterize, judge, or score anything itself, it has broken the
one property that makes this trustworthy: every finding traces back to
text a human can go re-read and confirm for themselves.

The critic never rewrites anything. Findings are fed back through the same
avoid_notes retry mechanism every other check in this package uses (see
tailor_resume / generate_cover_letter).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from scoutpilot.scoring.tailor import extract_json

log = logging.getLogger(__name__)

DEFAULT_MIN_BULLETS = 2
DEFAULT_MAX_BULLETS = 5

# Raised from 1/3 on 2026-08-27 after the 10-CV validation corpus showed the
# old fraction firing on the CV a human rated best (Revolut round 2, 6/11
# NONE) while the CV that was genuinely off-target for its posting (a Java
# role carrying ML bullets) still cleared 1/2 comfortably. "Over a third of
# your bullets address no specific line in the posting" is the normal shape
# of any CV that carries a differentiator layer -- a venture, a self-directed
# project, a competition win. "Over half" is where the CV really did stop
# being about this job.
_JD_IRRELEVANCE_MAX_FRACTION = 1 / 2

# Below this many countable bullets the fraction is noise, not signal: on a
# 3-bullet sample one NONE is already 33%.
_JD_IRRELEVANCE_MIN_SAMPLE = 4

# Bullets exempt from the JD-relevance count entirely, matched in CODE from
# the bullet's own text -- never by asking the model "is this an award?",
# which would be exactly the characterization this module refuses to request.
#
# An award, a placement, a grant, a funding round: no job description has a
# line for any of these, so the extraction question can only ever answer NONE
# for them, and counting that NONE penalises the CV for carrying the content
# a human reader values most -- the thing that separates this candidate from
# the other 400 applicants to the same graduate scheme. Exempt means removed
# from BOTH sides of the fraction: not a hit, not a miss, not the kind of
# thing the question is about.
_DIFFERENTIATOR_BULLET_RE = re.compile(
    r"\b("
    r"1st place|first place|2nd place|second place|3rd place|third place"
    r"|won|winner|winning"
    r"|finalist|finals|shortlisted|runner-up"
    r"|award(?:ed|s)?|prize|medal|scholarship"
    r"|dragon.?s den|hackathon"
    r"|secur(?:ed|ing) (?:initial |seed |pre-seed )?funding"
    r"|rais(?:ed|ing) (?:initial |seed |pre-seed )?(?:funding|investment)"
    r"|grant programme|grant funding"
    r")\b",
    re.IGNORECASE,
)


def _is_differentiator_bullet(text: str) -> bool:
    """True for an award/recognition/funding bullet -- see
    _DIFFERENTIATOR_BULLET_RE. Deterministic and auditable: a human can read
    the bullet and the pattern and agree or disagree with no model involved.
    """
    return bool(_DIFFERENTIATOR_BULLET_RE.search(text or ""))


def _quote_key(text: str) -> str:
    """Normalised form for checking a model-supplied quote against the CV.

    Case and whitespace are normalised and a leading bullet marker is
    stripped, because the model quotes bullets AS RENDERED ("- Built ...")
    while nothing else in the pipeline carries the dash. Nothing else is
    normalised: the point of this check is that the quote is verbatim, so
    loosening it any further would defeat it.
    """
    return " ".join(re.sub(r"^[-\u2022*]\s*", "", (text or "").strip()).split()).casefold()


def drop_unverifiable_quotes(observations: dict, cv_text: str) -> tuple[dict, list[str]]:
    """Remove any model-quoted bullet that does not actually occur in the CV.

    The critic is built on the promise that every finding traces back to
    text a human can go re-read (see the module docstring). A quote that
    isn't in the document breaks that promise outright, and it happens: on
    2026-08-26, r1 Slovakia, the critic reported
    '- Corrected data-leakage that inflated model accuracy' as a bullet.
    That line appears nowhere in that CV. The real text was a clause inside
    the SUMMARY paragraph -- 'diagnosing and correcting data-leakage that
    inflated model accuracy' -- which the model reformatted into a bullet
    and then reported on. A finding built on invented evidence is worse
    than no finding: it goes into avoid_notes and asks the next attempt to
    fix something that was never there.

    Containment is checked against the WHOLE rendered CV, not against the
    bullet lines alone, which is the rule as specified. Note the
    consequence: a real SUMMARY sentence quoted as though it were a bullet
    still passes here. Only quotes with no basis in the document at all are
    dropped.

    Returns:
        (cleaned observations, list of dropped quotes). The input is never
        mutated. With no cv_text, nothing is dropped.
    """
    if not cv_text:
        return observations, []

    hay = " ".join(cv_text.split()).casefold()
    dropped: list[str] = []
    cleaned = dict(observations)

    relevance = observations.get("bullet_jd_relevance")
    if isinstance(relevance, list):
        kept_rel = []
        for r in relevance:
            if not isinstance(r, dict):
                continue
            q = _quote_key(str(r.get("bullet", "")))
            if q and q in hay:
                kept_rel.append(r)
            else:
                dropped.append(str(r.get("bullet", "")))
        cleaned["bullet_jd_relevance"] = kept_rel

    return cleaned, dropped


def _normalize_header(header: str) -> str:
    """Loose key for matching a header the model quoted back out of the CV
    against the same header as tailor.py built it. Only case and whitespace
    are normalised -- the model is instructed to copy headers exactly, and
    anything looser risks collapsing two real entries onto one floor."""
    return " ".join((header or "").split()).casefold().rstrip(" .,;:-|")


# Weights are deliberately simple and visible here, not tuned into some
# opaque function -- a critic score should be as auditable as the findings
# it's built from. Adjust these, not a black-box formula, if the balance
# ever needs to change.
_WEIGHT_BULLET_COUNT = 1.5
_WEIGHT_JD_IRRELEVANCE = 1.5
_WEIGHT_UNSUPPORTED_CLAIM = 2.0


@dataclass(frozen=True)
class CriticResult:
    """score is COMPUTED from discrete findings (10.0 minus each finding's
    weight, floored at 0), never model-assigned -- unlike fit_score, which
    the scoring LLM assigns directly as an integer. See the module
    docstring for why that distinction matters."""

    score: float
    findings: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)
    # Quotes the model attributed to the CV that are not in it, dropped
    # before any threshold ran. See drop_unverifiable_quotes.
    dropped_quotes: list[str] = field(default_factory=list)


# ── CV critic ────────────────────────────────────────────────────────────

_CV_CRITIC_INSTRUCTIONS = """You are extracting factual observations from a CV, tailored for a specific job. Do NOT evaluate, judge, rate, or comment on quality anywhere in your answer -- only quote and count what is literally present in the text you are given. Every quote must be copied EXACTLY as it appears in the CV; do not paraphrase, summarize, correct, or shorten it.

Answer these two extraction questions about the CV:

1. BULLET_COUNTS: For each entry under the CV's EXPERIENCE section, count how many bullet lines appear under it. Key each count by that entry's exact header line (e.g. "Software Engineering Intern | Acme Ltd"), value is the integer count of bullets under it.

2. BULLET_JD_RELEVANCE: For EVERY bullet on the CV (every bullet, in both experience and projects, one entry per bullet), quote the specific line from the JOB DESCRIPTION that bullet most directly addresses. If no single line in the job description matches what that bullet describes, write exactly the word NONE instead of a quote for that bullet.

Output ONLY a JSON object with exactly these two keys: bullet_counts, bullet_jd_relevance. No commentary, no markdown fences, no text before or after the JSON."""

_CV_CRITIC_SCHEMA = {
    "type": "object",
    "properties": {
        "bullet_counts": {"type": "object", "additionalProperties": {"type": "integer"}},
        "bullet_jd_relevance": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"bullet": {"type": "string"}, "jd_line": {"type": "string"}},
                "required": ["bullet", "jd_line"],
            },
        },
    },
    "required": ["bullet_counts", "bullet_jd_relevance"],
}


def _build_cv_critic_user_message(cv_text: str, job_description: str) -> str:
    return (
        f"CV:\n{cv_text}\n\n---\n\nJOB DESCRIPTION:\n{(job_description or '')[:6000]}\n\n"
        "Extract the observations now. Output ONLY the JSON object."
    )


def evaluate_cv_observations(
    observations: dict, min_bullets: int = DEFAULT_MIN_BULLETS, max_bullets: int = DEFAULT_MAX_BULLETS,
    min_bullets_by_header: dict[str, int] | None = None,
) -> tuple[list[str], float]:
    """Apply fixed, code-side thresholds to the model's raw extraction.
    Never trusts the model's own framing of severity -- only the counts
    and quotes it returned, checked against numbers this function owns.

    `min_bullets_by_header` overrides the flat `min_bullets` floor for the
    entries it names, and is what keeps this check from ever arguing for
    invented content. A flat floor of 2 is wrong for an entry the fact bank
    has exactly one verified fact for: the finding lands in avoid_notes and
    the retry has nothing true left to write with, so the only way to satisfy
    it is to make something up. Every other guard in this codebase exists to
    prevent precisely that. See tailor.build_bullet_floor_map for how the
    per-entry floors are derived.
    """
    findings: list[str] = []
    penalty = 0.0
    floors = {
        _normalize_header(h): v
        for h, v in (min_bullets_by_header or {}).items()
        if isinstance(v, int) and not isinstance(v, bool)
    }

    bullet_counts = observations.get("bullet_counts")
    if isinstance(bullet_counts, dict):
        for header, count in bullet_counts.items():
            if not isinstance(count, int) or isinstance(count, bool):
                continue
            floor = floors.get(_normalize_header(header), min_bullets)
            if count < floor:
                findings.append(f"'{header}' has {count} bullet(s), below the minimum of {floor}.")
                penalty += _WEIGHT_BULLET_COUNT
            elif count > max_bullets:
                findings.append(f"'{header}' has {count} bullet(s), above the maximum of {max_bullets}.")
                penalty += _WEIGHT_BULLET_COUNT

    relevance = observations.get("bullet_jd_relevance")
    if isinstance(relevance, list) and relevance:
        counted = [
            r for r in relevance
            if isinstance(r, dict) and not _is_differentiator_bullet(str(r.get("bullet", "")))
        ]
        exempt = len(relevance) - len(counted)
        none_count = sum(
            1 for r in counted if str(r.get("jd_line", "")).strip().upper() == "NONE"
        )
        total = len(counted)
        if total >= _JD_IRRELEVANCE_MIN_SAMPLE and (none_count / total) > _JD_IRRELEVANCE_MAX_FRACTION:
            exempt_note = f" ({exempt} award/funding bullet(s) exempt)" if exempt else ""
            findings.append(
                f"{none_count}/{total} bullets don't address any specific line in the job "
                f"description (over {_JD_IRRELEVANCE_MAX_FRACTION:.0%}){exempt_note}."
            )
            penalty += _WEIGHT_JD_IRRELEVANCE

    return findings, max(0.0, round(10.0 - penalty, 1))


def run_cv_critic(
    client, cv_text: str, job_description: str,
    min_bullets: int = DEFAULT_MIN_BULLETS, max_bullets: int = DEFAULT_MAX_BULLETS,
    min_bullets_by_header: dict[str, int] | None = None,
) -> CriticResult:
    messages = [
        {"role": "system", "content": _CV_CRITIC_INSTRUCTIONS},
        {"role": "user", "content": _build_cv_critic_user_message(cv_text, job_description)},
    ]
    raw = client.chat(messages, max_tokens=2048, temperature=0.0, json_schema=_CV_CRITIC_SCHEMA)
    observations = extract_json(raw)
    observations, dropped = drop_unverifiable_quotes(observations, cv_text)
    if dropped:
        log.warning(
            "Critic quoted %d bullet(s) that are not in the CV; dropped before scoring: %s",
            len(dropped), "; ".join(repr(d[:80]) for d in dropped[:3]),
        )
    findings, score = evaluate_cv_observations(
        observations, min_bullets, max_bullets, min_bullets_by_header=min_bullets_by_header,
    )
    return CriticResult(score=score, findings=findings, raw=observations, dropped_quotes=dropped)


# ── Cover letter critic ─────────────────────────────────────────────────

_LETTER_CRITIC_INSTRUCTIONS = """You are extracting factual observations from a cover letter, checking it against the candidate's own CV. Do NOT evaluate, judge, or rate anything -- only quote what is literally present.

UNSUPPORTED_CLAIMS: Quote any sentence in the cover letter that makes a factual claim about the candidate's own work, skills, or experience that is NOT supported by anything on the CV given to you. A claim is supported if a CV bullet, the summary, or a skills entry states the same underlying fact, even worded differently. A sentence expressing intent, interest, opinion, or enthusiasm ("I would enjoy...", "I am excited about...", "Happy to discuss...", "This is somewhere I want to be") is NOT a factual claim -- do not list those, even if you're unsure. Quote each unsupported sentence exactly as it appears in the letter. Empty list if none.

Output ONLY a JSON object with exactly this one key: unsupported_claims. No commentary, no markdown fences, no text before or after the JSON."""

_LETTER_CRITIC_SCHEMA = {
    "type": "object",
    "properties": {"unsupported_claims": {"type": "array", "items": {"type": "string"}}},
    "required": ["unsupported_claims"],
}


def _build_letter_critic_user_message(letter: str, cv_text: str) -> str:
    return (
        f"COVER LETTER:\n{letter}\n\n---\n\nCV:\n{cv_text}\n\n"
        "Extract the observations now. Output ONLY the JSON object."
    )


def evaluate_letter_observations(observations: dict) -> tuple[list[str], float]:
    findings: list[str] = []
    penalty = 0.0
    claims = observations.get("unsupported_claims")
    if isinstance(claims, list):
        for c in claims:
            if isinstance(c, str) and c.strip():
                findings.append(f"Unsupported claim: {c.strip()!r}")
                penalty += _WEIGHT_UNSUPPORTED_CLAIM
    return findings, max(0.0, round(10.0 - penalty, 1))


def run_letter_critic(client, letter: str, cv_text: str) -> CriticResult:
    messages = [
        {"role": "system", "content": _LETTER_CRITIC_INSTRUCTIONS},
        {"role": "user", "content": _build_letter_critic_user_message(letter, cv_text)},
    ]
    raw = client.chat(messages, max_tokens=1024, temperature=0.0, json_schema=_LETTER_CRITIC_SCHEMA)
    observations = extract_json(raw)
    findings, score = evaluate_letter_observations(observations)
    return CriticResult(score=score, findings=findings, raw=observations)


def combined_critic_score(cv_score: float | None, letter_score: float | None) -> float | None:
    """The single critic_score value stored on the job row: the average of
    whichever sub-scores exist yet. A job with only a CV critic result
    (cover letter not generated yet) stores that score alone; once the
    letter critic also runs, the stored value updates to the average of
    both -- never silently drops the CV half.
    """
    scores = [s for s in (cv_score, letter_score) if s is not None]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 1)
