"""Tests for the FactBank / NumericGuard architectural fabrication guard.

Fixtures deliberately construct FactBank instances directly (not via
FactBank.load()) so these tests don't depend on the mutable state of the
repo's real facts.yaml -- except test_load_* below, which exercises the
YAML loader itself against small, self-contained files.
"""

import json

import pytest

from applypilot.facts import (
    Fact,
    FactBank,
    FactBankLoadError,
    NumericGuard,
    NumericGuardViolation,
)


# ── Fixtures ────────────────────────────────────────────────────────────

def _kraydel_multiparty_fact() -> Fact:
    """Mirrors the real kraydel.multiparty_calls entry in facts.yaml."""
    return Fact(
        id="kraydel.multiparty_calls",
        tier="verified",
        numbers=[4, 9],
        variants={
            "short": "Raised multi-party video call capacity from 4 to 9 participants",
            "long": (
                "Extended the multi-party calling subsystem to raise concurrent "
                "participant capacity from 4 to 9, then tested and verified the "
                "change end-to-end on physical hub hardware."
            ),
        },
        evidence="PlacementReport Week 14: increase multi-party call participants to 9 from 4",
    )


def _qualitative_fact() -> Fact:
    """A zero-number verified fact (mirrors kraydel.audit_system)."""
    return Fact(
        id="kraydel.audit_system",
        tier="verified",
        numbers=[],
        variants={"short": "Designed and shipped an end-to-end audit-event system"},
        evidence="PlacementReport Weeks 3-6: audit events across cloud, hub, DynamoDB",
    )


def _embedded_fact() -> Fact:
    """A use_when-restricted fact (mirrors edu.embedded_marks)."""
    return Fact(
        id="edu.embedded_marks",
        tier="verified",
        numbers=[89, 83],
        variants={"short": "Graded 89 and 83 across Embedded Systems I and II"},
        evidence="transcript: ECS 1001 Embedded Systems 89; ELE 2025 Embedded Systems 2 83",
        use_when="embedded / firmware / hardware-adjacent roles only",
    )


def _unverified_fact() -> Fact:
    """A plausible-but-unevidenced fact that must never reach the LLM."""
    return Fact(
        id="kraydel.fabricated_fleet_size",
        tier="unverified",
        numbers=[300],
        variants={"short": "Updated device policies across a 300-device fleet"},
        evidence="",
    )


def _bank(*facts) -> FactBank:
    return FactBank(list(facts), unfilled=[], forbidden=[])


# ── FactBank: unverified facts must never reach the LLM ───────────────────

class TestFactBankRejectsUnverified:
    def test_unverified_excluded_from_verified(self):
        bank = _bank(_kraydel_multiparty_fact(), _unverified_fact())
        ids = {f.id for f in bank.verified()}
        assert "kraydel.multiparty_calls" in ids
        assert "kraydel.fabricated_fleet_size" not in ids

    def test_unverified_excluded_from_prompt_payload(self):
        """The core guarantee: relevant_facts() (what actually goes into the
        LLM prompt) never includes an unverified entry, no matter how the
        job description is phrased."""
        bank = _bank(_kraydel_multiparty_fact(), _unverified_fact())
        relevant_ids = {f.id for f in bank.relevant_facts("300 devices fleet migration")}
        assert "kraydel.fabricated_fleet_size" not in relevant_ids
        assert "kraydel.multiparty_calls" in relevant_ids

    def test_unverified_excluded_from_allowed_numbers(self):
        bank = _bank(_kraydel_multiparty_fact(), _unverified_fact())
        allowed = bank.allowed_numbers()
        assert 300 not in allowed
        assert {4, 9}.issubset(allowed)

    def test_resolve_bullet_rejects_unverified_fact_id(self):
        bank = _bank(_unverified_fact())
        with pytest.raises(ValueError):
            bank.resolve_bullet({"fact": "kraydel.fabricated_fleet_size", "form": "short"})

    def test_resolve_bullet_rejects_unknown_fact_id(self):
        bank = _bank(_kraydel_multiparty_fact())
        with pytest.raises(ValueError):
            bank.resolve_bullet({"fact": "does.not.exist", "form": "short"})

    def test_resolve_bullet_rejects_plain_bullet_with_digit(self):
        """Bullets that carry no fact id must contain no digits -- enforced
        in code, not just by prompt instruction."""
        bank = _bank(_kraydel_multiparty_fact())
        with pytest.raises(ValueError):
            bank.resolve_bullet("Shipped 5 features this quarter")

    def test_resolve_bullet_accepts_verbatim_fact_text(self):
        bank = _bank(_kraydel_multiparty_fact())
        text = bank.resolve_bullet({"fact": "kraydel.multiparty_calls", "form": "short"})
        assert text == "Raised multi-party video call capacity from 4 to 9 participants"

    def test_resolve_bullet_accepts_clean_plain_bullet(self):
        bank = _bank(_kraydel_multiparty_fact())
        text = bank.resolve_bullet("Automated a manual reporting workflow")
        assert text == "Automated a manual reporting workflow"


class TestFactBankJobAwareSelection:
    def test_use_when_gates_facts_to_matching_jobs(self):
        bank = _bank(_embedded_fact())
        assert bank.relevant_facts("Senior Backend Engineer, Python, AWS, PostgreSQL") == []
        assert bank.relevant_facts("Embedded Systems Engineer, C, RTOS, firmware") != []

    def test_facts_without_use_when_always_relevant(self):
        bank = _bank(_kraydel_multiparty_fact())
        assert bank.relevant_facts("literally any job description") != []
        assert bank.relevant_facts("") != []


class TestFactBankLoad:
    def test_raises_on_evidence_number_mismatch(self, tmp_path):
        """A verified fact whose declared number isn't backed by its own
        evidence string must fail loudly at load time."""
        bad = tmp_path / "facts.yaml"
        bad.write_text(
            "role:\n"
            "  - id: fake.metric\n"
            "    tier: verified\n"
            "    numbers: [500]\n"
            "    evidence: \"no digits here at all\"\n"
            "    variants:\n"
            "      short: \"Shipped something with 500 whatevers\"\n",
            encoding="utf-8",
        )
        with pytest.raises(FactBankLoadError):
            FactBank.load(bad)

    def test_accepts_evidence_backed_facts(self, tmp_path):
        good = tmp_path / "facts.yaml"
        good.write_text(
            "role:\n"
            "  - id: real.metric\n"
            "    tier: verified\n"
            "    numbers: [4, 9]\n"
            "    evidence: \"report: raised capacity to 9 from 4\"\n"
            "    variants:\n"
            "      short: \"Raised capacity from 4 to 9\"\n",
            encoding="utf-8",
        )
        bank = FactBank.load(good)
        assert bank.get("real.metric") is not None
        assert bank.get("real.metric").numbers == [4, 9]

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FactBankLoadError):
            FactBank.load(tmp_path / "nope.yaml")


# ── NumericGuard ────────────────────────────────────────────────────────

class TestNumericGuard:
    def test_catches_injected_fabricated_figure(self):
        """Canonical example: an injected, unevidenced 500 must be caught."""
        guard = NumericGuard(_bank(_kraydel_multiparty_fact()))
        with pytest.raises(NumericGuardViolation) as exc_info:
            guard.check("Automated a workflow serving 500 concurrent users")
        assert 500 in exc_info.value.numbers

    def test_passes_on_real_participant_fact(self):
        """The real 4-to-9 participant fact must pass cleanly."""
        guard = NumericGuard(_bank(_kraydel_multiparty_fact()))
        guard.check("Raised multi-party video call capacity from 4 to 9 participants")

    def test_mixed_text_flags_only_the_fabricated_number(self):
        guard = NumericGuard(_bank(_kraydel_multiparty_fact()))
        text = (
            "Raised multi-party video call capacity from 4 to 9 participants\n"
            "Cut latency by 500ms across the board"
        )
        with pytest.raises(NumericGuardViolation) as exc_info:
            guard.check(text)
        assert exc_info.value.numbers == [500]
        assert any("500" in line for line in exc_info.value.bullets)
        assert all("4 to 9" not in line for line in exc_info.value.bullets)

    def test_allowed_numbers_includes_profile_numbers(self):
        profile = {"experience": {"years_of_experience_total": "7"}}
        guard = NumericGuard(_bank(_qualitative_fact()), profile)
        assert 7 in guard.allowed_numbers

    def test_qualitative_fact_text_has_no_allowed_numbers_needed(self):
        guard = NumericGuard(_bank(_qualitative_fact()))
        guard.check("Designed and shipped an end-to-end audit-event system")


# ── tailor_resume: guard failure must never ship, falls back instead ──────

class _FakeClient:
    """Always returns the same fabricated response, regardless of the
    'AVOID THESE ISSUES' retry feedback -- simulates a local model that
    keeps inventing the same plausible number no matter how it's told not to.
    """

    def chat(self, messages, max_tokens=2048, temperature=0.4):
        return json.dumps({
            "title": "Backend Engineer",
            "summary": "Shipped a platform serving 500 concurrent users with zero downtime.",
            "skills": {"Languages": "Python, SQL"},
            "experience": [{
                "header": "Engineer at TestCo",
                "subtitle": "Python | 2022 - 2023",
                "bullets": ["Automated a manual reporting workflow"],
            }],
            "projects": [{
                "header": "Side Project",
                "subtitle": "Python",
                "bullets": ["Built a small automation tool"],
            }],
            "education": "Test University | Bachelor's Degree",
        })


class TestGuardFailureFallsBack:
    def test_exhausted_retries_falls_back_instead_of_shipping(self, monkeypatch):
        import applypilot.scoring.tailor as tailor_mod

        monkeypatch.setattr(tailor_mod, "get_client", lambda: _FakeClient())

        bank = _bank(_kraydel_multiparty_fact())
        profile: dict = {}
        job = {
            "title": "Backend Engineer", "site": "TestCo", "location": "Remote",
            "full_description": "Backend role, Python, AWS.",
        }
        resume_text = "SUMMARY\nExperienced engineer.\n"

        tailored, report = tailor_mod.tailor_resume(
            resume_text, job, profile,
            max_retries=1, validation_mode="lenient", fact_bank=bank,
        )

        # Never ships on a failed guard -- the fabricated 500 must not
        # appear anywhere in what's actually written to disk/PDF.
        assert "500" not in tailored
        assert report["status"] == "approved_unquantified_fallback"
        # Every attempt was used (the fake client never produces a clean response).
        assert report["attempts"] == 2
        assert "guard_violation" in report
