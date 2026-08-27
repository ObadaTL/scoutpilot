"""Tests for the critic pass's CODE-side threshold logic (critic.py).

These test only the deterministic half -- evaluate_cv_observations,
evaluate_letter_observations, combined_critic_score -- given a canned
extraction dict, exactly as if the LLM had already answered. The LLM
extraction call itself (run_cv_critic / run_letter_critic) is exercised
separately, against the real local model, in the validation script (not
a pytest-suite concern: there is no deterministic "correct" LLM output to
assert against, only the fixed threshold math this file covers).
"""

from applypilot.facts import Fact
from applypilot.scoring.critic import (
    combined_critic_score,
    evaluate_cv_observations,
    evaluate_letter_observations,
)
from applypilot.scoring.tailor import build_bullet_floor_map


class _StubBank:
    """Stands in for FactBank: the floor map only ever asks it which
    verified facts are relevant to this job."""

    def __init__(self, facts):
        self._facts = facts

    def relevant_facts(self, job_description):
        return self._facts


def _fact(fact_id, source):
    return Fact(id=fact_id, tier="verified", numbers=[], variants={}, evidence="e", source=source)


class TestEvaluateCvObservations:
    def test_clean_cv_scores_ten(self):
        observations = {
            "bullet_counts": {"Acme": 3},
            "header_restating_bullets": [],
            "bullet_jd_relevance": [
                {"bullet": "a", "jd_line": "requirement 1"},
                {"bullet": "b", "jd_line": "requirement 2"},
                {"bullet": "c", "jd_line": "requirement 3"},
            ],
            "same_work_pairs": [],
        }
        findings, score = evaluate_cv_observations(observations)
        assert findings == []
        assert score == 10.0

    def test_bullet_count_below_minimum_is_flagged(self):
        observations = {
            "bullet_counts": {"Acme": 1},
            "header_restating_bullets": [], "bullet_jd_relevance": [], "same_work_pairs": [],
        }
        findings, score = evaluate_cv_observations(observations, min_bullets=2, max_bullets=5)
        assert len(findings) == 1
        assert "below the minimum" in findings[0]
        assert score == 8.5

    def test_bullet_count_above_maximum_is_flagged(self):
        """The exact incident: Storm Reply round 2 had 9 Kraydel bullets."""
        observations = {
            "bullet_counts": {"Kraydel LTD": 9},
            "header_restating_bullets": [], "bullet_jd_relevance": [], "same_work_pairs": [],
        }
        findings, score = evaluate_cv_observations(observations, min_bullets=2, max_bullets=5)
        assert len(findings) == 1
        assert "above the maximum" in findings[0]

    def test_header_restating_no_longer_penalised(self):
        """Removed 2026-08-27: tailor.find_header_restating_bullets decides
        this deterministically. A stale key in an extraction is ignored."""
        observations = {
            "bullet_counts": {},
            "header_restating_bullets": ["Worked at Kraydel from Jul 2022 to May 2023"],
            "bullet_jd_relevance": [],
        }
        findings, score = evaluate_cv_observations(observations)
        assert findings == []
        assert score == 10.0

    def test_over_half_none_relevance_is_flagged(self):
        observations = {
            "bullet_counts": {},
            "header_restating_bullets": [],
            "bullet_jd_relevance": [
                {"bullet": "a", "jd_line": "NONE"},
                {"bullet": "b", "jd_line": "NONE"},
                {"bullet": "c", "jd_line": "NONE"},
                {"bullet": "d", "jd_line": "requirement 1"},
            ],
            "same_work_pairs": [],
        }
        findings, score = evaluate_cv_observations(observations)
        assert len(findings) == 1
        assert "3/4" in findings[0]

    def test_half_or_fewer_none_relevance_is_not_flagged(self):
        observations = {
            "bullet_counts": {},
            "header_restating_bullets": [],
            "bullet_jd_relevance": [
                {"bullet": "a", "jd_line": "NONE"},
                {"bullet": "b", "jd_line": "NONE"},
                {"bullet": "c", "jd_line": "requirement 1"},
                {"bullet": "d", "jd_line": "requirement 2"},
            ],
            "same_work_pairs": [],
        }
        findings, score = evaluate_cv_observations(observations)
        assert findings == []

    def test_relevance_not_judged_on_too_small_a_sample(self):
        """On three bullets a single NONE is already a third: the fraction
        carries no signal until there are enough bullets to divide."""
        observations = {
            "bullet_counts": {},
            "header_restating_bullets": [],
            "bullet_jd_relevance": [
                {"bullet": "a", "jd_line": "NONE"},
                {"bullet": "b", "jd_line": "NONE"},
                {"bullet": "c", "jd_line": "requirement 1"},
            ],
            "same_work_pairs": [],
        }
        findings, score = evaluate_cv_observations(observations)
        assert findings == []

    def test_award_bullets_are_exempt_from_the_relevance_count(self):
        """The exact incident: Revolut round 2 (2026-08-26) was flagged 6/11
        while a human rated it the best CV in the corpus. No posting has a
        line for a Dragon's Den win or a funding round, so those bullets can
        only ever answer NONE -- counting them penalised the CV for carrying
        the content that distinguishes the candidate at all. Exempt on both
        sides of the fraction: 2 awards out of 6 leaves 2/4, which clears."""
        observations = {
            "bullet_counts": {},
            "header_restating_bullets": [],
            "bullet_jd_relevance": [
                {"bullet": "Won 1st place at the 2024 QUB Dragon's Den", "jd_line": "NONE"},
                {"bullet": "Pitched the venture and secured initial funding", "jd_line": "NONE"},
                {"bullet": "c", "jd_line": "NONE"},
                {"bullet": "d", "jd_line": "NONE"},
                {"bullet": "e", "jd_line": "requirement 1"},
                {"bullet": "f", "jd_line": "requirement 2"},
            ],
            "same_work_pairs": [],
        }
        findings, score = evaluate_cv_observations(observations)
        assert findings == []

    def test_award_exemption_does_not_rescue_a_genuinely_off_target_cv(self):
        """The counterpart the exemption must not swallow: round 1's Java
        Software Developer CV, which carried ML and identity-management
        bullets on a Java posting. One award exempt still leaves 3/5."""
        observations = {
            "bullet_counts": {},
            "header_restating_bullets": [],
            "bullet_jd_relevance": [
                {"bullet": "1st place, QUB Dragon's Den 2024", "jd_line": "NONE"},
                {"bullet": "Rebuilt the supporter sign-up flow with Keycloak", "jd_line": "NONE"},
                {"bullet": "Diagnosed and corrected evaluation data-leakage", "jd_line": "NONE"},
                {"bullet": "Built 2 parallel ML pipelines on surface-EMG signals", "jd_line": "NONE"},
                {"bullet": "Designed an audit-event system", "jd_line": "Developing cloud-native applications"},
                {"bullet": "Automated AWS IoT Core policy migration", "jd_line": "Developing cloud-native applications"},
            ],
            "same_work_pairs": [],
        }
        findings, score = evaluate_cv_observations(observations)
        assert len(findings) == 1
        assert "3/5" in findings[0]
        assert "1 award/funding bullet(s) exempt" in findings[0]

    def test_per_entry_floor_overrides_the_flat_minimum(self):
        """The exact incident: 'VIOFEEL has 1 bullet, below the minimum of 2'
        landed on 6 of 10 CVs in the 2026-08-26 corpus, and was wrong on
        every one -- the fact bank holds exactly one verified VIOFEEL fact,
        so the only way to satisfy the finding was to invent a second."""
        observations = {
            "bullet_counts": {"Co-Founder & Shareholder | VIOFEEL Ltd": 1},
            "header_restating_bullets": [], "bullet_jd_relevance": [], "same_work_pairs": [],
        }
        findings, score = evaluate_cv_observations(
            observations, min_bullets_by_header={"Co-Founder & Shareholder | VIOFEEL Ltd": 1},
        )
        assert findings == []
        assert score == 10.0

    def test_per_entry_floor_still_flags_an_entry_with_material_to_spare(self):
        """The floor drops only where the material genuinely runs out.
        Kraydel has nine verified facts; one bullet is still a finding."""
        observations = {
            "bullet_counts": {"Software Engineering Intern | Kraydel LTD": 1},
            "header_restating_bullets": [], "bullet_jd_relevance": [], "same_work_pairs": [],
        }
        findings, score = evaluate_cv_observations(
            observations, min_bullets_by_header={"Software Engineering Intern | Kraydel LTD": 2},
        )
        assert len(findings) == 1
        assert "below the minimum of 2" in findings[0]

    def test_floor_lookup_tolerates_whitespace_and_case_drift(self):
        """The model quotes the header back out of the rendered CV; only
        case and spacing may drift, and a missed match must not silently
        reinstate the flat floor."""
        observations = {
            "bullet_counts": {"co-founder  &  SHAREHOLDER | VIOFEEL Ltd": 1},
            "header_restating_bullets": [], "bullet_jd_relevance": [], "same_work_pairs": [],
        }
        findings, score = evaluate_cv_observations(
            observations, min_bullets_by_header={"Co-Founder & Shareholder | VIOFEEL Ltd": 1},
        )
        assert findings == []

    def test_unknown_header_falls_back_to_the_flat_minimum(self):
        observations = {
            "bullet_counts": {"Some Entry The Map Never Saw": 1},
            "header_restating_bullets": [], "bullet_jd_relevance": [], "same_work_pairs": [],
        }
        findings, score = evaluate_cv_observations(
            observations, min_bullets_by_header={"Co-Founder & Shareholder | VIOFEEL Ltd": 1},
        )
        assert len(findings) == 1

    def test_same_work_pairs_no_longer_penalised(self):
        """Removed 2026-08-27: check_no_cross_section_duplicates decides this
        in code from the fact bank, over every bullet pair in the document.
        A stale key left in an extraction must be ignored, not double-count."""
        observations = {
            "bullet_counts": {},
            "header_restating_bullets": [], "bullet_jd_relevance": [],
            "same_work_pairs": [["Built two parallel ML pipelines", "Built dual ML pipelines"]],
        }
        findings, score = evaluate_cv_observations(observations)
        assert findings == []
        assert score == 10.0

    def test_score_never_goes_below_zero(self):
        observations = {
            "bullet_counts": {"A": 20, "B": 20, "C": 20, "D": 20, "E": 20, "F": 20, "G": 20},
            "header_restating_bullets": [], "bullet_jd_relevance": [], "same_work_pairs": [],
        }
        findings, score = evaluate_cv_observations(observations)
        assert score == 0.0

    def test_malformed_observation_fields_are_ignored_not_crashed_on(self):
        """The model returning the wrong shape for a field must degrade to
        'no finding for that field', never raise."""
        observations = {
            "bullet_counts": "not a dict",
            "header_restating_bullets": "not a list",
            "bullet_jd_relevance": None,
            "same_work_pairs": [["only one item"]],
        }
        findings, score = evaluate_cv_observations(observations)
        assert findings == []
        assert score == 10.0


class TestEvaluateLetterObservations:
    def test_no_claims_scores_ten(self):
        findings, score = evaluate_letter_observations({"unsupported_claims": []})
        assert findings == []
        assert score == 10.0

    def test_unsupported_claim_is_flagged(self):
        observations = {"unsupported_claims": ["I have led a team of 10 engineers."]}
        findings, score = evaluate_letter_observations(observations)
        assert len(findings) == 1
        assert "Unsupported claim" in findings[0]
        assert score == 8.0

    def test_multiple_claims_stack_penalties(self):
        observations = {"unsupported_claims": ["Claim one.", "Claim two.", "Claim three."]}
        findings, score = evaluate_letter_observations(observations)
        assert len(findings) == 3
        assert score == 4.0


class TestCombinedCriticScore:
    def test_neither_present_returns_none(self):
        assert combined_critic_score(None, None) is None

    def test_only_cv_score_present(self):
        assert combined_critic_score(8.0, None) == 8.0

    def test_only_letter_score_present(self):
        assert combined_critic_score(None, 6.0) == 6.0

    def test_both_present_averages(self):
        assert combined_critic_score(8.0, 6.0) == 7.0

    def test_rounds_to_one_decimal(self):
        assert combined_critic_score(10.0, 8.7) == 9.3


class TestBuildBulletFloorMap:
    """build_bullet_floor_map lives in tailor.py but exists only to feed
    evaluate_cv_observations, so it is covered alongside it."""

    def _bank(self):
        return _StubBank([
            _fact("kraydel.tenure", "kraydel"),
            _fact("kraydel.audit_system", "kraydel"),
            _fact("kraydel.iot_policy_script", "kraydel"),
            _fact("viofeel.dragons_den", "viofeel"),
            _fact("emg.dual_pipeline", "emg"),
            _fact("emg.leakage_correction", "emg"),
        ])

    def test_entry_with_one_fact_gets_a_floor_of_one(self):
        data = {"experience": [
            {"header": "Co-Founder & Shareholder | VIOFEEL Ltd",
             "subtitle": "MedTech Wearable Tech | 2023 - Mar 2026", "bullets": ["x"]},
        ]}
        floors = build_bullet_floor_map(data, self._bank(), "any job")
        assert floors == {"Co-Founder & Shareholder | VIOFEEL Ltd": 1}

    def test_entry_with_plenty_of_facts_keeps_the_default_floor(self):
        data = {"experience": [
            {"header": "Software Engineering Intern | Kraydel LTD - Belfast",
             "subtitle": "Kotlin, Java | Jul 2022 - May 2023", "bullets": ["x"]},
        ]}
        floors = build_bullet_floor_map(data, self._bank(), "any job")
        assert floors == {"Software Engineering Intern | Kraydel LTD - Belfast": 2}

    def test_projects_are_covered_too(self):
        """The critic counts bullets under PROJECTS as well, so a floor is
        needed there or those entries silently keep the flat minimum."""
        data = {"projects": [
            {"header": "Surface EMG-Based Gesture Recognition & Biometric Identification",
             "subtitle": "Python, scikit-learn", "bullets": ["x"]},
        ]}
        floors = build_bullet_floor_map(data, self._bank(), "any job")
        assert floors["Surface EMG-Based Gesture Recognition & Biometric Identification"] == 2

    def test_unrecognized_entry_never_demands_content(self):
        """No verified material behind an entry means nothing to ask for --
        the guard must not argue for invention where every other guard in
        the codebase argues against it."""
        data = {"experience": [
            {"header": "Volunteer Mentor | Some Charity", "subtitle": "2024", "bullets": ["x"]},
        ]}
        floors = build_bullet_floor_map(data, self._bank(), "any job")
        assert floors == {"Volunteer Mentor | Some Charity": 1}

    def test_malformed_entries_are_skipped_not_crashed_on(self):
        data = {"experience": ["not a dict", {"subtitle": "no header", "bullets": ["x"]}],
                "projects": None}
        assert build_bullet_floor_map(data, self._bank(), "any job") == {}


class TestDropUnverifiableQuotes:
    """The guard that keeps a finding from resting on a quote the CV does
    not contain. Origin: 2026-08-26, r1 Slovakia -- the critic reported
    '- Corrected data-leakage that inflated model accuracy' as a bullet;
    that line is nowhere in that CV, the SUMMARY said 'diagnosing and
    correcting data-leakage that inflated model accuracy'."""

    CV = (
        "SUMMARY\n"
        "Built two parallel machine-learning pipelines, diagnosing and correcting "
        "data-leakage that inflated model accuracy.\n\n"
        "EXPERIENCE\n"
        "Software Engineering Intern | Kraydel LTD\n"
        "- Designed and shipped an end-to-end audit-event system\n"
    )

    def test_quote_absent_from_the_cv_is_dropped(self):
        from applypilot.scoring.critic import drop_unverifiable_quotes
        obs = {"bullet_counts": {}, "bullet_jd_relevance": [
            {"bullet": "- Corrected data-leakage that inflated model accuracy", "jd_line": "NONE"},
        ]}
        cleaned, dropped = drop_unverifiable_quotes(obs, self.CV)
        assert cleaned["bullet_jd_relevance"] == []
        assert len(dropped) == 1

    def test_real_bullet_survives_despite_the_rendered_dash(self):
        """The model quotes bullets as rendered; resolved bullets have no
        dash. Stripping it is the whole reason _quote_key exists."""
        from applypilot.scoring.critic import drop_unverifiable_quotes
        obs = {"bullet_counts": {}, "bullet_jd_relevance": [
            {"bullet": "- Designed and shipped an end-to-end audit-event system", "jd_line": "x"},
        ]}
        cleaned, dropped = drop_unverifiable_quotes(obs, self.CV)
        assert dropped == []
        assert len(cleaned["bullet_jd_relevance"]) == 1

    def test_a_summary_sentence_quoted_as_a_bullet_still_passes(self):
        """Documented consequence of the rule as specified: containment is
        checked against the whole CV, so real summary text quoted as a
        bullet is not a fabrication. Only text with no basis at all goes."""
        from applypilot.scoring.critic import drop_unverifiable_quotes
        obs = {"bullet_counts": {}, "bullet_jd_relevance": [
            {"bullet": "diagnosing and correcting data-leakage that inflated model accuracy",
             "jd_line": "NONE"},
        ]}
        cleaned, dropped = drop_unverifiable_quotes(obs, self.CV)
        assert dropped == []

    def test_dropping_shrinks_the_relevance_denominator(self):
        from applypilot.scoring.critic import drop_unverifiable_quotes
        obs = {"bullet_counts": {}, "bullet_jd_relevance": [
            {"bullet": "- Designed and shipped an end-to-end audit-event system", "jd_line": "x"},
            {"bullet": "Invented bullet that is not in the document", "jd_line": "NONE"},
        ]}
        cleaned, dropped = drop_unverifiable_quotes(obs, self.CV)
        assert len(cleaned["bullet_jd_relevance"]) == 1
        assert len(dropped) == 1

    def test_no_cv_text_drops_nothing(self):
        from applypilot.scoring.critic import drop_unverifiable_quotes
        obs = {"bullet_counts": {}, "bullet_jd_relevance": [{"bullet": "anything", "jd_line": "x"}]}
        cleaned, dropped = drop_unverifiable_quotes(obs, "")
        assert dropped == []
        assert cleaned is obs


class TestFindHeaderRestatingBullets:
    """The code check that replaced the model clause."""

    def test_bullet_adding_nothing_to_its_header_is_flagged(self):
        from applypilot.scoring.tailor import find_header_restating_bullets
        data = {"experience": [{
            "header": "Software Engineering Intern | Kraydel LTD - Belfast",
            "subtitle": "Kotlin, Java | Jul 2022 - May 2023",
            "bullets": ["Software engineering intern at Kraydel LTD in Belfast"],
        }]}
        v = find_header_restating_bullets(data)
        assert len(v) == 1 and "adds nothing" in v[0]

    def test_duration_restating_the_date_range_is_flagged(self):
        """The exact bullet the model never flagged: '11-month industry
        placement ...' under a subtitle already reading Jul 2022 - May 2023."""
        from applypilot.scoring.tailor import find_header_restating_bullets
        data = {"experience": [{
            "header": "Software Engineering Intern | Kraydel LTD - Belfast",
            "subtitle": "Kotlin, Java | Jul 2022 - May 2023",
            "bullets": ["11-month industry placement on a production video-care platform"],
        }]}
        v = find_header_restating_bullets(data)
        assert len(v) == 1 and "restates the date range as a duration" in v[0]

    def test_repeating_the_date_range_verbatim_is_flagged(self):
        from applypilot.scoring.tailor import find_header_restating_bullets
        data = {"experience": [{
            "header": "Software Engineering Intern | Kraydel LTD",
            "subtitle": "Kotlin, Java | Jul 2022 - May 2023",
            "bullets": ["Worked on the platform from Jul 2022 - May 2023 shipping audit events"],
        }]}
        v = find_header_restating_bullets(data)
        assert len(v) == 1 and "repeats the entry's own date range" in v[0]

    def test_real_bullet_is_not_flagged(self):
        from applypilot.scoring.tailor import find_header_restating_bullets
        data = {"experience": [{
            "header": "Software Engineering Intern | Kraydel LTD - Belfast",
            "subtitle": "Kotlin, Java | Jul 2022 - May 2023",
            "bullets": ["Designed and shipped an end-to-end audit-event system across hub, cloud and DynamoDB"],
        }]}
        assert find_header_restating_bullets(data) == []

    def test_a_year_shared_with_the_date_range_is_not_a_restatement(self):
        """'1st place, QUB Dragon's Den 2024' under 'Apr 2024 - Mar 2026'
        shares a year and is still real content. A bare year must never
        flag on its own."""
        from applypilot.scoring.tailor import find_header_restating_bullets
        data = {"experience": [{
            "header": "Co-Founder & Shareholder | VIOFEEL Ltd",
            "subtitle": "MedTech Wearable Tech | Apr 2024 - Mar 2026",
            "bullets": ["1st place, QUB Dragon's Den 2024"],
        }]}
        assert find_header_restating_bullets(data) == []

    def test_open_ended_range_never_produces_a_duration_finding(self):
        """'Aug 2026 - Present' has no fixed span, so a duration claim
        against it can't be decided deterministically and must not fire."""
        from applypilot.scoring.tailor import find_header_restating_bullets
        data = {"projects": [{
            "header": "ApplyPilot",
            "subtitle": "Python, SQLite | Aug 2026 - Present",
            "bullets": ["Spent 3 months building an autonomous application pipeline in Python"],
        }]}
        assert find_header_restating_bullets(data) == []
