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


# ── Reworded fact bullets: authorship back, numbers still verified ──────
#
# Unconditional verbatim substitution made fabricated numbers impossible and
# tailored documents impossible at the same time: 450 bullets across 58
# generated CVs collapsed to 87 distinct strings, because selecting a fact id
# was the model's only real lever. The fact now licenses the NUMBERS while
# the model writes the SENTENCE.

class TestRewordedFactBullets:
    def _bank(self):
        from applypilot.facts import Fact, FactBank
        return FactBank(
            [
                Fact(
                    id="emg.dual_pipeline", tier="verified", numbers=[2],
                    variants={"short": "Built 2 parallel ML pipelines on surface-EMG signals"},
                    evidence="resume: 2 ML pipelines",
                ),
                Fact(
                    id="kraydel.tenure", tier="verified", numbers=[11],
                    variants={"short": "11-month industry placement on a production platform"},
                    evidence="LinkedIn: 11 mos",
                ),
            ],
            unfilled=[], forbidden=[],
        )

    def test_own_wording_is_kept_when_numbers_check_out(self):
        bank = self._bank()
        text, fact_id = bank.resolve_bullet_ex({
            "fact": "emg.dual_pipeline",
            "text": "Designed and evaluated 2 independent classification pipelines end to end",
        })
        assert text == "Designed and evaluated 2 independent classification pipelines end to end"
        assert fact_id == "emg.dual_pipeline"

    def test_smuggled_number_falls_back_to_the_verbatim_variant(self):
        """The wording is the model's; the numbers are not. A rewording that
        reaches for a number the fact isn't evidenced for is discarded
        entirely rather than partially trusted."""
        bank = self._bank()
        text, fact_id = bank.resolve_bullet_ex({
            "fact": "emg.dual_pipeline",
            "text": "Built 2 pipelines reaching 92 percent accuracy on held-out data",
        })
        assert text == "Built 2 parallel ML pipelines on surface-EMG signals"
        assert fact_id == "emg.dual_pipeline"

    def test_number_from_a_different_fact_is_not_borrowed(self):
        """Tighter than NumericGuard's global allowed set on purpose: 11 is
        verified, but not for this fact, so this bullet may not carry it."""
        bank = self._bank()
        text, _ = bank.resolve_bullet_ex({
            "fact": "emg.dual_pipeline",
            "text": "Built 2 pipelines over 11 months of signal data collection",
        })
        assert text == "Built 2 parallel ML pipelines on surface-EMG signals"

    def test_fragment_falls_back_to_the_variant(self):
        bank = self._bank()
        text, _ = bank.resolve_bullet_ex({"fact": "emg.dual_pipeline", "text": "Built pipelines"})
        assert text == "Built 2 parallel ML pipelines on surface-EMG signals"

    def test_form_selection_still_works(self):
        """Back-compat: the original select-a-variant shape is unchanged."""
        bank = self._bank()
        text, fact_id = bank.resolve_bullet_ex({"fact": "kraydel.tenure", "form": "short"})
        assert text == "11-month industry placement on a production platform"
        assert fact_id == "kraydel.tenure"


# ── Cross-section dedup ────────────────────────────────────────────────

class TestCrossSectionDedup:
    """A fact is one real thing; it belongs on the CV once -- even if that
    means a section ends up empty and generation has to retry with
    different content. A duplicate is never silently kept just to avoid
    that retry (see tailor.py's check_no_cross_section_duplicates, which
    hard-fails generation if a duplicate ever reaches the assembled text)."""

    def _data_and_bank(self, dup: bool):
        from applypilot.facts import Fact, FactBank
        facts = [
            Fact(id="emg.dual", tier="verified", numbers=[2],
                 variants={"short": "Built 2 parallel ML pipelines on EMG signals",
                           "long": "Built two parallel machine-learning pipelines over EMG signals"},
                 evidence="resume: 2 pipelines"),
            Fact(id="work.audit", tier="verified", numbers=[],
                 variants={"short": "Shipped an end-to-end audit-event system"},
                 evidence="report: audit events"),
        ]
        other = "emg.dual" if dup else "work.audit"
        data = {
            "experience": [{"header": "Placement", "bullets": [{"fact": "emg.dual", "form": "short"}]}],
            "projects": [{"header": "EMG", "bullets": [{"fact": other, "form": "short"}]}],
        }
        return data, FactBank(facts, unfilled=[], forbidden=[])

    def test_repeated_fact_is_dropped_from_the_later_section(self):
        """The duplicate bullet goes; the entry survives on its other one."""
        from applypilot.facts import Fact, FactBank
        from applypilot.scoring.tailor import _resolve_fact_bullets

        bank = FactBank(
            [
                Fact(id="emg.dual", tier="verified", numbers=[2],
                     variants={"short": "Built 2 parallel ML pipelines on EMG signals"},
                     evidence="resume: 2 pipelines"),
                Fact(id="work.audit", tier="verified", numbers=[],
                     variants={"short": "Shipped an end-to-end audit-event system"},
                     evidence="report: audit events"),
            ],
            unfilled=[], forbidden=[],
        )
        data = {
            "experience": [{"header": "Placement", "bullets": [{"fact": "work.audit", "form": "short"}]}],
            "projects": [{"header": "EMG", "bullets": [
                {"fact": "work.audit", "form": "short"},   # already used above
                {"fact": "emg.dual", "form": "short"},     # unique to this section
            ]}],
        }
        resolved, _ = _resolve_fact_bullets(data, bank)
        assert resolved["projects"][0]["bullets"] == ["Built 2 parallel ML pipelines on EMG signals"]

    def test_a_duplicate_section_ends_up_empty_with_an_actionable_error(self):
        """If dedup would leave PROJECTS with no entries at all, it stays
        empty -- validate_json_fields will require a retry for it, but the
        retry note explains why (write new bullets, don't repeat
        experience) instead of the run silently shipping the fact twice."""
        from applypilot.scoring.tailor import _resolve_fact_bullets
        data, bank = self._data_and_bank(dup=True)
        resolved, errors = _resolve_fact_bullets(data, bank)
        assert resolved["projects"] == []
        assert any("PROJECTS ended up empty" in e for e in errors)


class TestBulletOwnership:
    """A fact bound to one real employer/project (Fact.source, set from its
    facts.yaml group) must never be rendered under a different entry -- the
    exact VIOFEEL/EMG misattribution seen live 2026-08-26."""

    def _bank(self):
        from applypilot.facts import Fact, FactBank
        return FactBank(
            [
                Fact(id="emg.dual", tier="verified", numbers=[2], source="emg",
                     variants={"short": "Built 2 parallel ML pipelines on EMG signals"},
                     evidence="resume: 2 pipelines"),
                Fact(id="viofeel.dragons_den", tier="verified", numbers=[1, 2024], source="viofeel",
                     variants={"short": "1st place, QUB Dragon's Den 2024"},
                     evidence="resume: 1st place 2024"),
            ],
            unfilled=[], forbidden=[],
        )

    def test_fact_under_the_wrong_entry_is_dropped_not_moved(self):
        from applypilot.scoring.tailor import _resolve_fact_bullets
        data = {
            "experience": [
                {"header": "Co-Founder & Shareholder | VIOFEEL Ltd", "bullets": [
                    {"fact": "viofeel.dragons_den", "form": "short"},
                    {"fact": "emg.dual", "form": "short"},  # misplaced: belongs to the EMG project
                ]},
            ],
            "projects": [
                {"header": "Surface EMG-Based Gesture Recognition", "bullets": [
                    {"fact": "emg.dual", "form": "short"},
                ]},
            ],
        }
        resolved, errors = _resolve_fact_bullets(data, self._bank())
        assert resolved["experience"][0]["bullets"] == ["1st place, QUB Dragon's Den 2024"]
        assert resolved["projects"][0]["bullets"] == ["Built 2 parallel ML pipelines on EMG signals"]
        assert any("emg.dual" in e and "VIOFEEL" in e for e in errors)

    def test_fact_under_an_uncanonicalized_entry_is_allowed(self):
        """No canonical record matched this entry -- there's no ground
        truth to check it against, so it passes through untouched."""
        from applypilot.scoring.tailor import _resolve_fact_bullets
        data = {
            "experience": [{"header": "Freelance Consulting", "bullets": [{"fact": "emg.dual", "form": "short"}]}],
            "projects": [],
        }
        resolved, errors = _resolve_fact_bullets(data, self._bank())
        assert resolved["experience"][0]["bullets"] == ["Built 2 parallel ML pipelines on EMG signals"]
        assert errors == []


class TestCrossSectionDuplicateAssertion:
    """check_no_cross_section_duplicates is the hard backstop: even if
    ownership/dedup somehow let a duplicate through, the assembled CV must
    never actually ship with the same bullet under two headings."""

    def test_raises_on_identical_bullet_in_both_sections(self):
        from applypilot.facts import BulletPlacementViolation
        from applypilot.scoring.tailor import check_no_cross_section_duplicates
        data = {
            "experience": [{"header": "VIOFEEL", "bullets": ["Built two parallel ML pipelines on EMG signals."]}],
            "projects": [{"header": "EMG Project", "bullets": ["Built two parallel ML pipelines on EMG signals."]}],
        }
        try:
            check_no_cross_section_duplicates(data)
            assert False, "expected BulletPlacementViolation"
        except BulletPlacementViolation as e:
            assert "VIOFEEL" in e.reasons[0] and "EMG Project" in e.reasons[0]

    def test_passes_on_distinct_bullets(self):
        from applypilot.scoring.tailor import check_no_cross_section_duplicates
        data = {
            "experience": [{"header": "VIOFEEL", "bullets": ["1st place, QUB Dragon's Den 2024"]}],
            "projects": [{"header": "EMG Project", "bullets": ["Built two parallel ML pipelines on EMG signals."]}],
        }
        check_no_cross_section_duplicates(data)  # must not raise

    def test_catches_a_paraphrased_duplicate_by_fact_id(self):
        """Exact-text matching alone missed this live 2026-08-26: the same
        fact, worded differently in each section, with too little word
        overlap for _bullets_similar and too little for match_similar to
        assign a shared fact id during resolution either."""
        from applypilot.facts import BulletPlacementViolation, Fact, FactBank
        from applypilot.scoring.tailor import check_no_cross_section_duplicates

        bank = FactBank(
            [
                Fact(id="emg.dual", tier="verified", numbers=[2], source="emg",
                     variants={"short": "Built 2 parallel ML pipelines on surface-EMG signals in Python/scikit-learn"},
                     evidence="resume: 2 pipelines"),
            ],
            unfilled=[], forbidden=[],
        )
        data = {
            "experience": [{"header": "VIOFEEL", "bullets": [
                "Built two parallel machine-learning pipelines for surface-EMG signal processing in Python",
            ]}],
            "projects": [{"header": "EMG Project", "bullets": [
                "Built dual ML pipelines in Python and scikit-learn for hand-gesture classification from surface-EMG signals",
            ]}],
        }
        try:
            check_no_cross_section_duplicates(data, fact_bank=bank)
            assert False, "expected BulletPlacementViolation"
        except BulletPlacementViolation as e:
            assert "emg.dual" in e.reasons[0]

    def test_raises_on_identical_bullet_twice_in_one_entry(self):
        """The blind spot the projects-vs-experience loop had by
        construction: two bullets under the SAME heading were never held up
        against each other at all."""
        from applypilot.facts import BulletPlacementViolation
        from applypilot.scoring.tailor import check_no_cross_section_duplicates
        data = {
            "projects": [{"header": "EMG Project", "bullets": [
                "Built two parallel ML pipelines on EMG signals.",
                "Built two parallel ML pipelines on EMG signals.",
            ]}],
        }
        try:
            check_no_cross_section_duplicates(data)
            assert False, "expected BulletPlacementViolation"
        except BulletPlacementViolation as e:
            assert "twice under" in e.reasons[0]
            assert "EMG Project" in e.reasons[0]

    def test_raises_on_reworded_duplicate_inside_one_entry(self):
        """The exact pairing named in _likely_fact_id's docstring: 'Built
        dual ML pipelines...' against a fact worded 'Built 2 parallel ML
        pipelines...'. No shared fact id at resolution time and too little
        literal overlap for text equality -- only _likely_fact_id unifies
        them, and only an all-pairs loop ever compares them."""
        from applypilot.facts import BulletPlacementViolation, Fact, FactBank
        from applypilot.scoring.tailor import check_no_cross_section_duplicates

        bank = FactBank(
            [
                Fact(id="emg.dual", tier="verified", numbers=[2], source="emg",
                     variants={"short": "Built 2 parallel ML pipelines on surface-EMG signals in Python/scikit-learn"},
                     evidence="resume: 2 pipelines"),
            ],
            unfilled=[], forbidden=[],
        )
        data = {
            "projects": [{"header": "EMG Project", "bullets": [
                "Built two parallel machine-learning pipelines for surface-EMG signal processing in Python",
                "Built dual ML pipelines in Python and scikit-learn for hand-gesture classification from surface-EMG signals",
            ]}],
        }
        try:
            check_no_cross_section_duplicates(data, fact_bank=bank)
            assert False, "expected BulletPlacementViolation"
        except BulletPlacementViolation as e:
            assert "emg.dual" in e.reasons[0]
            assert "Two bullets under" in e.reasons[0]

    def test_raises_on_reworded_duplicate_across_entries_in_one_section(self):
        """Same section, two different headings -- also invisible to the old
        loop, which only ever walked projects against experience."""
        from applypilot.facts import BulletPlacementViolation, Fact, FactBank
        from applypilot.scoring.tailor import check_no_cross_section_duplicates

        bank = FactBank(
            [
                Fact(id="emg.dual", tier="verified", numbers=[2], source="emg",
                     variants={"short": "Built 2 parallel ML pipelines on surface-EMG signals in Python/scikit-learn"},
                     evidence="resume: 2 pipelines"),
            ],
            unfilled=[], forbidden=[],
        )
        data = {
            "projects": [
                {"header": "EMG Gesture Recognition", "bullets": [
                    "Built two parallel machine-learning pipelines for surface-EMG signal processing in Python",
                ]},
                {"header": "EMG Biometrics", "bullets": [
                    "Built dual ML pipelines in Python and scikit-learn for hand-gesture classification from surface-EMG signals",
                ]},
            ],
        }
        try:
            check_no_cross_section_duplicates(data, fact_bank=bank)
            assert False, "expected BulletPlacementViolation"
        except BulletPlacementViolation as e:
            assert "emg.dual" in e.reasons[0]
            assert "EMG Gesture Recognition" in e.reasons[0]
            assert "EMG Biometrics" in e.reasons[0]

    def test_two_distinct_bullets_in_one_entry_are_not_a_duplicate(self):
        """All-pairs must not turn every multi-bullet entry into a finding.
        Every CV in the 2026-08-26 corpus had 2-9 bullets under one heading
        and none of them was a self-duplicate."""
        from applypilot.facts import Fact, FactBank
        from applypilot.scoring.tailor import check_no_cross_section_duplicates

        bank = FactBank(
            [
                Fact(id="emg.dual", tier="verified", numbers=[2], source="emg",
                     variants={"short": "Built 2 parallel ML pipelines on surface-EMG signals in Python/scikit-learn"},
                     evidence="resume: 2 pipelines"),
                Fact(id="emg.leakage", tier="verified", numbers=[], source="emg",
                     variants={"short": "Diagnosed and corrected evaluation data-leakage that had inflated reported accuracy"},
                     evidence="resume: leakage"),
            ],
            unfilled=[], forbidden=[],
        )
        data = {
            "projects": [{"header": "EMG Project", "bullets": [
                "Built 2 parallel ML pipelines on surface-EMG signals in Python/scikit-learn",
                "Diagnosed and corrected evaluation data-leakage that had inflated reported accuracy",
            ]}],
        }
        check_no_cross_section_duplicates(data, fact_bank=bank)  # must not raise

    def test_no_fact_bank_falls_back_to_exact_text_only(self):
        """Backward compatible: omitting fact_bank still catches exact
        duplicates, just not paraphrased ones."""
        from applypilot.scoring.tailor import check_no_cross_section_duplicates
        data = {
            "experience": [{"header": "VIOFEEL", "bullets": ["A genuinely different bullet entirely"]}],
            "projects": [{"header": "EMG Project", "bullets": ["Built two parallel ML pipelines on EMG signals."]}],
        }
        check_no_cross_section_duplicates(data)  # must not raise -- no shared text


class TestCanonicalExperienceRejection:
    """Once canonical_entries.experience is configured, it's exhaustive:
    an EXPERIENCE entry matching no real employer is rejected outright, not
    passed through untouched the way an unmatched PROJECTS entry still is."""

    def _profile(self):
        return {
            "resume_facts": {
                "canonical_entries": {
                    "experience": [
                        {"match": ["Kraydel"], "header": "Software Engineering Intern | Kraydel LTD", "subtitle": "Jul 2022 - May 2023"},
                    ],
                }
            }
        }

    def test_invented_experience_entry_is_dropped(self):
        """The exact incident: the model filed the candidate's own degree
        as a job once EMG bullets could no longer land on VIOFEEL."""
        from applypilot.scoring.tailor import _apply_canonical_entries
        data = {
            "experience": [
                {"header": "Software Engineering Intern | Kraydel LTD", "bullets": ["Shipped an audit-event system"]},
                {"header": "MEng Software and Electronic Systems Engineering | Queen's University Belfast", "bullets": ["Built ML pipelines"]},
            ],
        }
        result, errors = _apply_canonical_entries(data, self._profile())
        headers = [e["header"] for e in result["experience"]]
        assert "Software Engineering Intern | Kraydel LTD" in headers
        assert not any("Queen's University Belfast" in h for h in headers)
        assert any("Rejected invented EXPERIENCE entry" in e for e in errors)

    def test_projects_stay_additive_when_unmatched(self):
        """The same unmatched-entry situation in PROJECTS is kept, not
        rejected -- a profile can have real projects not yet registered."""
        from applypilot.scoring.tailor import _apply_canonical_entries
        profile = self._profile()
        profile["resume_facts"]["canonical_entries"]["projects"] = [
            {"match": ["EMG"], "header": "EMG Project", "subtitle": "2020 - 2025"},
        ]
        data = {
            "experience": [{"header": "Software Engineering Intern | Kraydel LTD", "bullets": ["Shipped it"]}],
            "projects": [
                {"header": "EMG stuff", "bullets": ["Built pipelines"]},
                {"header": "An unrelated personal project", "bullets": ["Did a thing"]},
            ],
        }
        result, _ = _apply_canonical_entries(data, profile)
        headers = [e["header"] for e in result["projects"]]
        assert "EMG Project" in headers  # canonicalized
        assert "An unrelated personal project" in headers  # kept, not rejected


class TestCanonicalSkillsLines:
    """TECHNICAL SKILLS renders only what the profile actually declares --
    the LLM's own skills text is used purely to choose display order."""

    def _profile(self):
        return {"skills_boundary": {"programming_languages": ["Python", "Java", "Kotlin"]}}

    def test_llm_cannot_add_a_skill(self):
        """The exact incident: the model added 'LangChain (agent frameworks)'
        and 'Kubernetes' to categories that never listed them, lifted
        straight from the job's own requirements."""
        from applypilot.scoring.tailor import _canonical_skills_lines
        data = {"skills": {"Programming Languages": "Python (LLM integration, LangChain), Java, Kubernetes"}}
        lines = _canonical_skills_lines(data, self._profile())
        assert len(lines) == 1
        assert "LangChain" not in lines[0]
        assert "Kubernetes" not in lines[0]
        assert "Python" in lines[0] and "Java" in lines[0] and "Kotlin" in lines[0]

    def test_llm_text_only_reorders(self):
        from applypilot.scoring.tailor import _canonical_skills_lines
        data = {"skills": {"Programming Languages": "Kotlin is the main one, then Java, then Python."}}
        lines = _canonical_skills_lines(data, self._profile())
        assert lines[0] == "Programming Languages: Kotlin, Java, Python"

    def test_no_skills_boundary_returns_empty(self):
        from applypilot.scoring.tailor import _canonical_skills_lines
        assert _canonical_skills_lines({"skills": {}}, {}) == []
