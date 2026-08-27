"""Verified-fact bank for resume tailoring.

facts.yaml (repo root) is the ONLY source of quantified claims the tailoring
LLM is allowed to use. Tailoring runs against a local model, and a 14B model
asked to "quantify achievements" will invent plausible-looking numbers. The
fix here is architectural, not a prompt instruction: only `tier: verified`
facts, each traceable to real evidence, are ever exposed to the LLM (see
`verified()`/`relevant_facts()`), and every verified fact's numbers are
checked against its own evidence string at load time -- a bad entry fails
loudly at startup (`FactBank.load()`), not silently at generation time.

NumericGuard is the second half of the control: a deterministic,
post-generation check that every number in the assembled resume text traces
back to `FactBank.allowed_numbers()`. The prompt instruction alone is not
the enforcement; this is.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

# Repo-root facts.yaml -- deliberately NOT under the per-user ~/.applypilot
# dir (see config.APP_DIR): this is curated once per candidate alongside the
# codebase, not per-machine profile data. Override for tests/alt locations.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FACTS_PATH = Path(os.environ.get("APPLYPILOT_FACTS_PATH", str(_REPO_ROOT / "facts.yaml")))

# Top-level facts.yaml keys that are NOT fact-list groupings.
_RESERVED_KEYS = {"meta", "unverified", "forbidden"}

_NUMBER_TOKEN_RE = re.compile(r"\d+")

# Generic filler words stripped when turning a fact's free-text `use_when`
# into keywords for job-description matching.
_USE_WHEN_STOPWORDS = {"only", "roles", "role", "and", "or"}

# Generic words stripped before comparing a rejected plain bullet against a
# verified fact's `short` variant in _match_similar_fact -- common enough
# that requiring them wouldn't distinguish one fact from another.
_BULLET_MATCH_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "at", "to", "for",
    "with", "from", "by", "into", "across", "using", "via",
}
_WORD_RE = re.compile(r"[a-z0-9]+")


def _significant_words(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(text.lower()) if w not in _BULLET_MATCH_STOPWORDS and len(w) > 1}


# A rewording shorter than this isn't a bullet, it's a fragment -- almost
# always the model echoing the fact id or emitting a stub. Fall back to the
# pre-written variant rather than shipping it.
_MIN_REWORD_WORDS = 5


def _accept_reworded(text: str, fact: "Fact") -> bool:
    """Whether the model's own wording of `fact` may be used in place of the
    fact's pre-written variant.

    Verbatim substitution (the original design) made fabricated numbers
    impossible, but at the cost of the model's authorship: with 11 verified
    facts and 2 variants each, every tailored CV became a permutation of the
    same 22 sentences, and 450 bullets across 58 generated CVs collapsed to
    87 distinct strings. The claim was safe and the document was generic.

    The number is the part that has to be verified; the sentence around it
    does not. So the model writes the sentence and this checks the digits:
    the rewording is accepted only if every number in it is one this fact's
    own evidence covers. A rewording that reaches for any other number is
    rejected outright and the pre-written variant substituted -- the caller
    never sees a bullet carrying a number the FactBank can't account for, so
    NumericGuard's guarantee downstream is exactly as strong as before.

    Note this is deliberately *tighter* than NumericGuard's global allowed
    set: a bullet about the EMG pipelines may not borrow a number evidenced
    only for the Kraydel placement, even though both are verified facts.
    """
    if not text or not text.strip():
        return False
    if len(text.split()) < _MIN_REWORD_WORDS:
        return False
    numbers = {int(n) for n in _NUMBER_TOKEN_RE.findall(text)}
    return numbers <= set(fact.numbers)


def format_facts_block(facts: list, show_owner: bool = False) -> str:
    """Render verified facts as an id-keyed list for a prompt.

    Shared by resume tailoring and cover-letter generation. The variants are
    shown as reference wordings the model may reuse or rewrite -- what it
    may NOT do is introduce a number the fact isn't evidenced for (see
    `_accept_reworded`, and NumericGuard for the document-wide check).

    `show_owner` names the entry each fact belongs under. Resume tailoring
    needs it and cover letters don't (a letter has no entries). Without it
    the model had no way to know that an "emg" fact may only sit under the
    EMG project: it guessed, guessed wrong constantly, and
    tailor._entry_owns_fact dropped the bullet. Measured over 30 postings
    on 2026-08-27: 182 bullets dropped this way, 158 of them under the
    VIOFEEL entry, which pushed 27 of 30 CVs onto the unquantified
    fallback path.
    """
    if not facts:
        return "(none relevant to this job -- do not use any numbers at all)"
    lines = []
    for fact in facts:
        numbers = ", ".join(str(n) for n in fact.numbers) if fact.numbers else "none"
        source = (getattr(fact, "source", "") or "").lower()
        owner = ""
        if show_owner and source and source != "education":
            owner = f'; belongs ONLY under the entry whose header names "{source}"'
        lines.append(f'- "{fact.id}"  (the only numbers this fact licenses: {numbers}{owner})')
        for form in ("short", "long"):
            text = fact.variants.get(form)
            if text:
                lines.append(f'    {form}: "{" ".join(text.split())}"')
    return "\n".join(lines)


class FactBankError(Exception):
    """Base class for fact-bank problems."""


class FactBankLoadError(FactBankError):
    """Raised when facts.yaml fails integrity checks at load time."""


class NumericGuardViolation(FactBankError):
    """Raised by NumericGuard when the assembled resume text contains a
    number that doesn't trace back to a verified fact (or the profile)."""

    def __init__(self, numbers: list[int], bullets: list[str]):
        self.numbers = numbers
        self.bullets = bullets
        super().__init__(
            f"Unverified number(s) {numbers} found in {len(bullets)} line(s): "
            + "; ".join(bullets[:5])
        )


class BulletPlacementViolation(FactBankError):
    """Raised when a resolved bullet is rendered under an entry other than
    its verified fact's real owner (e.g. an "emg" fact under the VIOFEEL
    experience entry), or when the identical bullet text appears in more
    than one section of the assembled CV."""

    def __init__(self, reasons: list[str]):
        self.reasons = reasons
        super().__init__("; ".join(reasons))


@dataclass(frozen=True)
class Fact:
    """One verifiable, pre-written claim the LLM may select for a bullet."""

    id: str
    tier: str
    numbers: list[int]
    variants: dict[str, str]
    evidence: str
    use_when: str | None = None
    # The facts.yaml top-level group this fact was parsed from (e.g.
    # "kraydel", "emg", "viofeel"). This is the fact's real-world owner --
    # the employer or project it actually describes -- and is the binding
    # tailor.py's bullet-placement check uses to catch a fact resolved under
    # the wrong entry (e.g. an "emg" fact rendered under the VIOFEEL
    # experience entry). Defaults to "" for Facts built directly in tests,
    # where no ownership check is exercised.
    source: str = ""


@dataclass(frozen=True)
class UnfilledFact:
    """A known gap: a plausible claim that needs a real value filled in
    before it can be promoted to a verified Fact. Never exposed to the LLM."""

    id: str
    question: str
    value: object | None
    would_unlock: str | None = None


def _extract_numbers(obj) -> set[int]:
    """Recursively pull every integer token out of a nested structure.

    Used to fold legitimate numbers already present in the user profile
    (years of experience, etc.) into the allowed set, without hardcoding
    any of them here.
    """
    numbers: set[int] = set()
    if isinstance(obj, dict):
        for v in obj.values():
            numbers.update(_extract_numbers(v))
    elif isinstance(obj, (list, tuple, set)):
        for v in obj:
            numbers.update(_extract_numbers(v))
    elif isinstance(obj, bool):
        pass
    elif isinstance(obj, int):
        numbers.add(obj)
    elif isinstance(obj, float):
        numbers.add(int(obj))
    elif isinstance(obj, str):
        numbers.update(int(n) for n in _NUMBER_TOKEN_RE.findall(obj))
    return numbers


def _use_when_keywords(use_when: str) -> list[str]:
    """Deterministic keyword extraction from a fact's free-text `use_when`.

    Deliberately simple (no LLM call): this decides what gets exposed to
    the tailoring model at all, so it needs to be auditable rather than
    another thing that could hallucinate a match.
    """
    words = re.split(r"[^a-zA-Z]+", use_when.lower())
    return [w for w in words if len(w) >= 4 and w not in _USE_WHEN_STOPWORDS]


class FactBank:
    """Parses facts.yaml and is the sole gate on what quantified claims the
    tailoring LLM ever sees."""

    def __init__(self, facts: list[Fact], unfilled: list[UnfilledFact],
                forbidden: list[str]):
        self._facts: dict[str, Fact] = {f.id: f for f in facts}
        self._unfilled = list(unfilled)
        self.forbidden = list(forbidden)

    # -- Loading -------------------------------------------------------

    @classmethod
    def load(cls, path: Path | str | None = None) -> "FactBank":
        """Parse facts.yaml into Facts, validating every verified fact's
        numbers against its own evidence string.

        Raises:
            FactBankLoadError: the file is missing/malformed, or any
                verified fact declares a number its own evidence doesn't
                support. Deliberate: a bad entry must fail loudly here,
                not silently at generation time.
        """
        p = Path(path) if path is not None else FACTS_PATH
        if not p.exists():
            raise FactBankLoadError(f"facts.yaml not found at {p}")

        try:
            raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            raise FactBankLoadError(f"facts.yaml is not valid YAML: {e}") from e

        facts: list[Fact] = []
        load_errors: list[str] = []

        for section, entries in raw.items():
            if section in _RESERVED_KEYS or not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    load_errors.append(f"[{section}] non-dict entry: {entry!r}")
                    continue
                fact, entry_errors = cls._parse_fact(entry, section)
                load_errors.extend(entry_errors)
                if fact is not None:
                    facts.append(fact)

        unfilled = [
            UnfilledFact(
                id=e.get("id", "?"),
                question=e.get("question", ""),
                value=e.get("value"),
                would_unlock=e.get("would_unlock"),
            )
            for e in (raw.get("unverified") or [])
        ]
        forbidden = list(raw.get("forbidden") or [])

        if load_errors:
            raise FactBankLoadError(
                f"facts.yaml failed integrity checks ({len(load_errors)}):\n"
                + "\n".join(f"  - {e}" for e in load_errors)
            )

        return cls(facts, unfilled, forbidden)

    @staticmethod
    def _parse_fact(entry: dict, section: str) -> tuple[Fact | None, list[str]]:
        errors: list[str] = []
        fact_id = entry.get("id")
        if not fact_id:
            return None, [f"[{section}] entry missing 'id': {entry!r}"]

        tier = entry.get("tier", "")
        numbers = [int(n) for n in (entry.get("numbers") or [])]
        evidence = entry.get("evidence", "") or ""
        variants = entry.get("variants") or {}
        use_when = entry.get("use_when")

        if tier == "verified":
            evidence_numbers = {int(n) for n in _NUMBER_TOKEN_RE.findall(evidence)}
            missing = [n for n in numbers if n not in evidence_numbers]
            if missing:
                errors.append(
                    f"{fact_id}: number(s) {missing} not found in its own evidence "
                    f"string ({evidence!r})"
                )
            if not variants.get("short"):
                errors.append(f"{fact_id}: verified fact has no 'short' variant")

        fact = Fact(
            id=fact_id, tier=tier, numbers=numbers, variants=variants,
            evidence=evidence, use_when=use_when, source=section,
        )
        return fact, errors

    # -- Access ----------------------------------------------------------

    def get(self, fact_id: str) -> Fact | None:
        if not fact_id or not isinstance(fact_id, str):
            return None
        # 1. Exact match
        if fact_id in self._facts:
            return self._facts[fact_id]
        # 2. Normalized match (replace _ with .)
        norm = fact_id.lower().replace("_", ".").strip()
        if norm in self._facts:
            return self._facts[norm]
        # 3. Fuzzy keyword matching for known facts in facts.yaml
        if "audit" in norm:
            return self._facts.get("kraydel.audit_system")
        if "keycloak" in norm:
            return self._facts.get("kraydel.keycloak_signup")
        if "docker" in norm:
            return self._facts.get("kraydel.dockerized_service")
        if "iot" in norm or "policy" in norm:
            return self._facts.get("kraydel.iot_policy_script")
        if "usage" in norm or "dashboard" in norm:
            return self._facts.get("kraydel.usage_dashboard")
        if "sonar" in norm or "ci" in norm or "quality" in norm:
            return self._facts.get("kraydel.ci_quality")
        if "i18n" in norm or "spanish" in norm or "local" in norm:
            return self._facts.get("kraydel.i18n")
        if "call" in norm or "multiparty" in norm:
            return self._facts.get("kraydel.multiparty_calls")
        if "tenure" in norm or "placement" in norm:
            return self._facts.get("kraydel.tenure")
        if "leak" in norm:
            return self._facts.get("emg.leakage_correction")
        if "gesture" in norm or "emg" in norm or "pipeline" in norm:
            return self._facts.get("emg.dual_pipeline")
        if "dragon" in norm or "viofeel" in norm:
            return self._facts.get("viofeel.dragons_den")
        if "meng" in norm or "degree" in norm:
            return self._facts.get("edu.meng")
        return None

    def match_similar(self, text: str) -> tuple[str, str] | None:
        """Best-effort recovery for a plain-string bullet that has a digit
        but is actually just a reworded version of an existing verified
        fact the model forgot to reference by id.

        Confirmed live 2026-08-24: the model independently wrote "Built 2
        parallel ML pipelines on surface-EMG signals in Python/scikit-learn"
        as plain text -- word-for-word `emg.dual_pipeline`'s own `short`
        variant -- instead of emitting {"fact": "emg.dual_pipeline", "form":
        "short"}. resolve_bullet used to just drop bullets like this, which
        thins the resume (fewer bullets -> more empty space on the rendered
        PDF) for a reason that has nothing to do with the claim being
        unverified -- it demonstrably already IS one of the two ways to say
        THIS SPECIFIC AND VERIFIED thing.

        Matching is on whole words with underscore/word-boundary tokenizing
        (not raw substring, and not a general text-similarity score like
        difflib's SequenceMatcher -- tested live and found unreliable here:
        a true reworded match against a short/terse fact variant scored
        LOWER than an unrelated fact purely because of length mismatch).
        A fact only matches if EVERY significant word in its own `short`
        variant, and every number in its own `numbers` list, is literally
        present in the bullet -- this can't accidentally fire on a bullet
        that merely shares a couple of common words with a fact, since it
        requires the fact's full (short) claim to already be present.
        Returns (fact_id, text) -- text is the fact's own `short` text
        (never anything derived from the bullet), so this is exactly as
        safe as the id-reference path: nothing the LLM wrote is ever used,
        only pre-verified text. The fact_id lets a caller recognize two
        differently-worded bullets that both resolved to the same
        underlying fact (see _resolve_fact_bullets's dedup).
        """
        bullet_words = _significant_words(text)
        bullet_numbers = {int(n) for n in _NUMBER_TOKEN_RE.findall(text)}
        if not bullet_words:
            return None

        best: tuple[float, str, str] | None = None
        for fact in self.verified():
            short = fact.variants.get("short")
            if not short:
                continue
            fact_words = _significant_words(short)
            if not fact_words or not fact_words <= bullet_words:
                continue
            if fact.numbers and not set(fact.numbers) <= bullet_numbers:
                continue
            # Prefer the fact whose short text covers more of the bullet --
            # keeps an overly generic/short fact from winning over a more
            # specific one when both technically qualify.
            coverage = len(fact_words) / len(bullet_words)
            if best is None or coverage > best[0]:
                best = (coverage, fact.id, " ".join(short.split()))
        return (best[1], best[2]) if best else None

    def verified(self) -> list[Fact]:
        """All tier == 'verified' facts. The ONLY facts ever exposed to the LLM."""
        return [f for f in self._facts.values() if f.tier == "verified"]

    def unfilled(self) -> list[UnfilledFact]:
        """Unverified entries pending a real value, for a CLI prompt flow."""
        return list(self._unfilled)

    def allowed_numbers(self, profile: dict | None = None) -> set[int]:
        """Every number the tailoring output is allowed to contain: the
        union of every verified fact's numbers, plus years/dates already
        present in the user profile."""
        numbers: set[int] = set()
        for fact in self.verified():
            numbers.update(fact.numbers)
        if profile:
            numbers.update(_extract_numbers(profile))
        return numbers

    def relevant_facts(self, job_description: str) -> list[Fact]:
        """Verified facts worth offering the LLM for this job.

        Facts with no `use_when` are always offered. Facts with a
        `use_when` (e.g. embedded-systems marks) are only offered when the
        job description actually matches -- so embedded marks surface for
        embedded roles and stay out of the prompt otherwise.
        """
        text = (job_description or "").lower()
        relevant = []
        for fact in self.verified():
            if not fact.use_when:
                relevant.append(fact)
                continue
            if any(kw in text for kw in _use_when_keywords(fact.use_when)):
                relevant.append(fact)
        return relevant

    def resolve_bullet(self, bullet) -> str:
        """Turn one LLM-output bullet into literal text. See resolve_bullet_ex
        for the full contract; this just drops the fact-id half of it for
        callers that only need the text."""
        return self.resolve_bullet_ex(bullet)[0]

    def resolve_bullet_ex(self, bullet) -> tuple[str, str | None]:
        """Turn one LLM-output bullet into (literal text, fact id or None).

        A fact-referencing bullet comes in two shapes:

        * ``{"fact": id, "text": "<the model's own wording>"}`` -- the
          model keeps authorship of the SENTENCE while the fact licenses
          the NUMBERS. Its wording is accepted only if every number in it
          is one this fact is evidenced for (``fact.numbers``); otherwise
          the pre-written variant is substituted instead. See
          `_accept_reworded` for why this replaced verbatim-only
          substitution.
        * ``{"fact": id, "form": "short"|"long"}`` -- the original shape,
          replaced VERBATIM with that fact's pre-written variant. Still
          supported, and still what a rejected rewording falls back to.

        A plain-string bullet passes through only if it contains no digits
        at all. The fact id (None for a plain bullet with no digits) lets a
        caller recognize two differently-worded bullets that both resolved
        to the same fact -- see _resolve_fact_bullets's dedup, which needs
        this because two bullets pointing at the same fact can land on very
        different-length text (a fact's `short` vs `long` variant) that a
        text-similarity check alone won't reliably catch.

        Raises:
            ValueError: unknown/unverified fact id, missing variant text,
                a non-fact bullet containing a digit, or an unrecognized
                bullet shape.
        """
        if isinstance(bullet, dict):
            fact_id = bullet.get("fact") or bullet.get("id")
            if isinstance(fact_id, dict):
                fact_id = fact_id.get("id") or fact_id.get("fact") or str(fact_id)
            if not isinstance(fact_id, str):
                # If the dict contains a text bullet without a valid fact id
                text = bullet.get("text") or bullet.get("bullet") or bullet.get("desc")
                if text and isinstance(text, str):
                    return self.resolve_bullet_ex(text)
                raise ValueError(f"Invalid fact id format in bullet: {bullet!r}")

            fact = self._facts.get(fact_id)
            if fact is None or fact.tier != "verified":
                raise ValueError(f"Unknown or unverified fact id: {fact_id!r}")

            # The model's own wording of this fact, when it supplied one and
            # it doesn't smuggle in a number the fact isn't evidenced for.
            reworded = bullet.get("text") or bullet.get("bullet")
            if isinstance(reworded, str) and _accept_reworded(reworded, fact):
                return " ".join(reworded.split()), fact.id

            form = bullet.get("form", "short")
            text = fact.variants.get(form) or fact.variants.get("short") or fact.variants.get("long")
            if not text:
                raise ValueError(f"Fact {fact_id!r} has no usable variant text")
            return " ".join(text.split()), fact.id  # collapse YAML block-scalar line wrapping

        if isinstance(bullet, (list, tuple)):
            # If bullet is a list of items, join them into a single string
            return " ".join(str(b) for b in bullet if b), None

        if isinstance(bullet, str):
            # Check for inline fact references like (fact: kraydel.audit_event_system) or [fact: ...]
            match = re.search(r"[\(\[\{]?\s*fact\s*:\s*([a-zA-Z0-9_\.]+)\s*[\)\]\}]?", bullet, re.IGNORECASE)
            if match:
                fact_id = match.group(1)
                fact = self._facts.get(fact_id)
                if fact is not None and fact.tier == "verified":
                    form = "long" if "long" in bullet.lower() else "short"
                    text = fact.variants.get(form) or fact.variants.get("short") or fact.variants.get("long")
                    if text:
                        return " ".join(text.split()), fact.id
                elif fact is None:
                    raise ValueError(f"Unknown fact id in bullet: {fact_id!r}")
            if _NUMBER_TOKEN_RE.search(bullet):
                recovered = self.match_similar(bullet)
                if recovered is not None:
                    return recovered[1], recovered[0]
                raise ValueError(f"Bullet without a fact id contains a digit: {bullet!r}")
            return bullet, None
        raise ValueError(f"Unrecognized bullet format: {bullet!r}")


class NumericGuard:
    """Deterministic, post-generation check: every number in the assembled
    resume text must trace back to FactBank.allowed_numbers()."""

    def __init__(self, fact_bank: FactBank, profile: dict | None = None):
        self._fact_bank = fact_bank
        self._allowed = fact_bank.allowed_numbers(profile)

    @property
    def allowed_numbers(self) -> set[int]:
        return set(self._allowed)

    def check(self, text: str) -> None:
        """Raise NumericGuardViolation if any line contains a number that
        isn't in the allowed set. Scans line by line so the violation can
        name which bullet(s) are responsible.

        Raises:
            NumericGuardViolation: structured error with the offending
                numbers and the lines/bullets containing them.
        """
        offending_numbers: set[int] = set()
        offending_lines: list[str] = []
        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            found = {int(n) for n in _NUMBER_TOKEN_RE.findall(stripped)}
            bad = found - self._allowed
            if bad:
                offending_numbers.update(bad)
                offending_lines.append(stripped)
        if offending_numbers:
            raise NumericGuardViolation(sorted(offending_numbers), offending_lines)
