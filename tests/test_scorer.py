"""Tests for the company_summary/company_hook capture added to fit scoring."""

from applypilot.scoring.scorer import _parse_score_response


class TestParseScoreResponse:
    def test_extracts_company_fields(self):
        response = (
            "SCORE: 8\n"
            "KEYWORDS: python, aws, docker\n"
            "REASONING: Strong technical match with appropriate seniority.\n"
            "COMPANY_SUMMARY: This company builds a fraud-detection platform "
            "for e-commerce merchants. The team owns the real-time scoring pipeline.\n"
            "COMPANY_HOOK: Real-time fraud scoring at high transaction volume."
        )
        result = _parse_score_response(response)
        assert result["score"] == 8
        assert result["company_summary"].startswith("This company builds")
        assert result["company_hook"] == "Real-time fraud scoring at high transaction volume."

    def test_literal_null_maps_to_none(self):
        response = (
            "SCORE: 6\n"
            "KEYWORDS: python\n"
            "REASONING: Moderate match.\n"
            "COMPANY_SUMMARY: NULL\n"
            "COMPANY_HOOK: NULL"
        )
        result = _parse_score_response(response)
        assert result["company_summary"] is None
        assert result["company_hook"] is None

    def test_reasoning_does_not_swallow_company_fields(self):
        """REASONING used to be a greedy capture-to-end-of-string -- once
        COMPANY_SUMMARY/COMPANY_HOOK were appended after it in the prompt,
        that would have pulled them into the reasoning field whole."""
        response = (
            "SCORE: 7\n"
            "KEYWORDS: python\n"
            "REASONING: Good fit overall.\n"
            "COMPANY_SUMMARY: Builds analytics tooling for retailers.\n"
            "COMPANY_HOOK: Analytics for retail."
        )
        result = _parse_score_response(response)
        assert result["reasoning"] == "Good fit overall."
        assert "COMPANY_SUMMARY" not in result["reasoning"]
        assert "COMPANY_HOOK" not in result["reasoning"]

    def test_missing_company_fields_default_to_none(self):
        """Older-style responses (or a model that ignores the new fields)
        must not crash the parser -- just come back as None."""
        response = "SCORE: 5\nKEYWORDS: sql\nREASONING: Partial match."
        result = _parse_score_response(response)
        assert result["company_summary"] is None
        assert result["company_hook"] is None

    def test_extracts_eligibility_fields(self):
        response = (
            "SCORE: 6\nKEYWORDS: python\nREASONING: Partial match.\n"
            "COMPANY_SUMMARY: NULL\nCOMPANY_HOOK: NULL\n"
            "REQUIRED_COUNTRY: United States\n"
            "REQUIRED_WORK_AUTH: STEM OPT/F1\n"
            "MIN_YEARS_COMMERCIAL: 3"
        )
        result = _parse_score_response(response)
        assert result["required_country"] == "United States"
        assert result["required_work_auth"] == "STEM OPT/F1"
        assert result["min_years_commercial"] == 3

    def test_missing_eligibility_fields_default_to_none(self):
        response = "SCORE: 5\nKEYWORDS: sql\nREASONING: Partial match."
        result = _parse_score_response(response)
        assert result["required_country"] is None
        assert result["required_work_auth"] is None
        assert result["min_years_commercial"] is None


class TestEligibilityGate:
    """Deterministic post-LLM enforcement: the model extracts what the
    posting says (STEP 3 of SCORE_PROMPT), the comparison against the
    candidate's real profile happens in code."""

    def _profile(self, **overrides):
        base = {
            "personal": {"country": "United Kingdom"},
            "work_authorization": {"work_permit_type": "Settled Status"},
            "experience": {"years_of_experience_total": "0.9"},
        }
        base.update(overrides)
        return base

    def test_country_mismatch_caps_at_one(self):
        from applypilot.scoring.scorer import apply_eligibility_gate
        parsed = {"score": 8, "required_country": "United States", "required_work_auth": None, "min_years_commercial": None}
        result = apply_eligibility_gate(parsed, self._profile())
        assert result["score"] == 1
        assert "United States" in result["gate_reason"]

    def test_work_auth_mismatch_caps_at_one(self):
        from applypilot.scoring.scorer import apply_eligibility_gate
        parsed = {"score": 9, "required_country": None, "required_work_auth": "STEM OPT/F1", "min_years_commercial": None}
        result = apply_eligibility_gate(parsed, self._profile())
        assert result["score"] == 1
        assert "STEM OPT/F1" in result["gate_reason"]

    def test_insufficient_years_caps_at_five(self):
        from applypilot.scoring.scorer import apply_eligibility_gate
        parsed = {"score": 7, "required_country": None, "required_work_auth": None, "min_years_commercial": 3}
        result = apply_eligibility_gate(parsed, self._profile())
        assert result["score"] == 5
        assert "3" in result["gate_reason"]

    def test_exactly_meeting_years_requirement_does_not_gate(self):
        """0.9 does not satisfy a 1-year minimum -- an 11-month placement is
        under a year, not rounded up to meet it."""
        from applypilot.scoring.scorer import apply_eligibility_gate
        parsed = {"score": 7, "required_country": None, "required_work_auth": None, "min_years_commercial": 1}
        result = apply_eligibility_gate(parsed, self._profile())
        assert result["score"] == 5

    def test_no_requirements_stated_never_gates(self):
        from applypilot.scoring.scorer import apply_eligibility_gate
        parsed = {"score": 8, "required_country": None, "required_work_auth": None, "min_years_commercial": None}
        result = apply_eligibility_gate(parsed, self._profile())
        assert result["score"] == 8
        assert result["gate_reason"] is None

    def test_matching_country_does_not_gate(self):
        from applypilot.scoring.scorer import apply_eligibility_gate
        parsed = {"score": 8, "required_country": "UK", "required_work_auth": None, "min_years_commercial": None}
        result = apply_eligibility_gate(parsed, self._profile())
        assert result["score"] == 8
        assert result["gate_reason"] is None

    def test_country_and_years_combine_to_the_lower_cap(self):
        from applypilot.scoring.scorer import apply_eligibility_gate
        parsed = {"score": 8, "required_country": "United States", "required_work_auth": None, "min_years_commercial": 3}
        result = apply_eligibility_gate(parsed, self._profile())
        assert result["score"] == 1  # country cap (1) wins over years cap (5)
        assert "United States" in result["gate_reason"] and "3" in result["gate_reason"]


class TestStripFabricatedSkillSentences:
    def _profile(self):
        return {"skills_boundary": {"programming_languages": ["Python", "Java"]}}

    def test_strips_sentence_naming_an_unlisted_tool(self):
        from applypilot.scoring.scorer import _strip_fabricated_skill_sentences
        job = {"site": "Acme", "full_description": "We use Hugging Face and LangChain extensively."}
        reasoning = (
            "The candidate has strong Python skills. They also have experience with "
            "Hugging Face, which matches the role well."
        )
        cleaned = _strip_fabricated_skill_sentences(reasoning, job, self._profile())
        assert "Hugging Face" not in cleaned
        assert "strong Python skills" in cleaned

    def test_leaves_clean_reasoning_untouched(self):
        from applypilot.scoring.scorer import _strip_fabricated_skill_sentences
        job = {"site": "Acme", "full_description": "We use Python and Java."}
        reasoning = "The candidate has strong Python and Java skills."
        assert _strip_fabricated_skill_sentences(reasoning, job, self._profile()) == reasoning
