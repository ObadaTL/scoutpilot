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


@dataclass(frozen=True)
class Fact:
    """One verifiable, pre-written claim the LLM may select for a bullet."""

    id: str
    tier: str
    numbers: list[int]
    variants: dict[str, str]
    evidence: str
    use_when: str | None = None


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
            evidence=evidence, use_when=use_when,
        )
        return fact, errors

    # -- Access ----------------------------------------------------------

    def get(self, fact_id: str) -> Fact | None:
        return self._facts.get(fact_id)

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
        """Turn one LLM-output bullet into literal text.

        A fact-referencing bullet (``{"fact": id, "form": "short"|"long"}``)
        is replaced VERBATIM with that fact's pre-written variant -- the
        LLM's own phrasing for it, if any, is discarded entirely, so it
        cannot rewrite numeric content no matter what it outputs alongside
        the id. A plain-string bullet passes through only if it contains no
        digits at all.

        Raises:
            ValueError: unknown/unverified fact id, missing variant text,
                a non-fact bullet containing a digit, or an unrecognized
                bullet shape.
        """
        if isinstance(bullet, dict):
            fact_id = bullet.get("fact")
            fact = self._facts.get(fact_id)
            if fact is None or fact.tier != "verified":
                raise ValueError(f"Unknown or unverified fact id: {fact_id!r}")
            form = bullet.get("form", "short")
            text = fact.variants.get(form) or fact.variants.get("short")
            if not text:
                raise ValueError(f"Fact {fact_id!r} has no usable variant text")
            return " ".join(text.split())  # collapse YAML block-scalar line wrapping
        if isinstance(bullet, str):
            if _NUMBER_TOKEN_RE.search(bullet):
                raise ValueError(f"Bullet without a fact id contains a digit: {bullet!r}")
            return bullet
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
