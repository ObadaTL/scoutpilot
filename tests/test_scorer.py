"""Tests for the company_summary/company_hook capture added to fit scoring."""

from scoutpilot.scoring.scorer import _parse_score_response


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
        from scoutpilot.scoring.scorer import apply_eligibility_gate
        parsed = {"score": 8, "required_country": "United States", "required_work_auth": None, "min_years_commercial": None}
        result = apply_eligibility_gate(parsed, self._profile())
        assert result["score"] == 1
        assert "United States" in result["gate_reason"]

    def test_work_auth_mismatch_caps_at_one(self):
        from scoutpilot.scoring.scorer import apply_eligibility_gate
        parsed = {"score": 9, "required_country": None, "required_work_auth": "STEM OPT/F1", "min_years_commercial": None}
        result = apply_eligibility_gate(parsed, self._profile())
        assert result["score"] == 1
        assert "STEM OPT/F1" in result["gate_reason"]

    def test_insufficient_years_caps_at_five(self):
        from scoutpilot.scoring.scorer import apply_eligibility_gate
        parsed = {"score": 7, "required_country": None, "required_work_auth": None, "min_years_commercial": 3}
        result = apply_eligibility_gate(parsed, self._profile())
        assert result["score"] == 5
        assert "3" in result["gate_reason"]

    def test_exactly_meeting_years_requirement_does_not_gate(self):
        """0.9 does not satisfy a 1-year minimum -- an 11-month placement is
        under a year, not rounded up to meet it."""
        from scoutpilot.scoring.scorer import apply_eligibility_gate
        parsed = {"score": 7, "required_country": None, "required_work_auth": None, "min_years_commercial": 1}
        result = apply_eligibility_gate(parsed, self._profile())
        assert result["score"] == 5

    def test_no_requirements_stated_never_gates(self):
        from scoutpilot.scoring.scorer import apply_eligibility_gate
        parsed = {"score": 8, "required_country": None, "required_work_auth": None, "min_years_commercial": None}
        result = apply_eligibility_gate(parsed, self._profile())
        assert result["score"] == 8
        assert result["gate_reason"] is None

    def test_matching_country_does_not_gate(self):
        from scoutpilot.scoring.scorer import apply_eligibility_gate
        parsed = {"score": 8, "required_country": "UK", "required_work_auth": None, "min_years_commercial": None}
        result = apply_eligibility_gate(parsed, self._profile())
        assert result["score"] == 8
        assert result["gate_reason"] is None

    # ---- work-authorisation gate: false rejections found 2026-08-27 ----

    def _uk_profile(self):
        """The real profile shape: structured authorisation flags alongside
        the free-text permit name."""
        return {
            "personal": {"country": "United Kingdom"},
            "work_authorization": {
                "legally_authorized_to_work": True,
                "require_sponsorship": False,
                "work_permit_type": "Settled Status",
            },
            "experience": {"years_of_experience_total": "0.9"},
        }

    def _parsed(self, **kw):
        base = {"score": 8, "required_country": None,
                "required_work_auth": None, "min_years_commercial": None}
        base.update(kw)
        return base

    def test_settled_status_satisfies_a_uk_right_to_work_requirement(self):
        """The exact defect: 'Right to work in the UK' vs 'Settled Status'
        matched as substrings in neither direction, so the gate capped the
        score at 1 -- on 112 jobs in the live database. Settled status IS an
        unrestricted right to work in the UK."""
        from scoutpilot.scoring.scorer import apply_eligibility_gate
        result = apply_eligibility_gate(
            self._parsed(required_work_auth="Right to work in the UK"), self._uk_profile())
        assert result["score"] == 8
        assert result["gate_reason"] is None

    def test_iso_country_code_gb_resolves_to_united_kingdom(self):
        """The most obviously wrong reason in the database, on 30 jobs:
        'Requires work authorisation/location in GB; profile is based in
        United Kingdom.' GB was simply missing from the alias map."""
        from scoutpilot.scoring.scorer import apply_eligibility_gate
        result = apply_eligibility_gate(
            self._parsed(required_country="GB"), self._uk_profile())
        assert result["score"] == 8
        assert result["gate_reason"] is None

    def test_requirement_naming_the_home_country_is_satisfied(self):
        """Covers the security-clearance phrasing that gated 6 more jobs:
        'UK security cleared or willing & eligible to go through the
        process' names the candidate's own country and is not a foreign
        visa category."""
        from scoutpilot.scoring.scorer import apply_eligibility_gate
        result = apply_eligibility_gate(
            self._parsed(required_work_auth=
                         "UK security cleared or willing & eligible to go through the process"),
            self._uk_profile())
        assert result["gate_reason"] is None

    def test_named_foreign_visa_category_still_gates(self):
        """The counterpart the fix must not swallow. An unrestricted permit
        at home says nothing about holding STEM OPT/F1, which names no
        country and is not a generic right-to-work line."""
        from scoutpilot.scoring.scorer import apply_eligibility_gate
        result = apply_eligibility_gate(
            self._parsed(required_work_auth="STEM OPT/F1"), self._uk_profile())
        assert result["score"] == 1
        assert "STEM OPT/F1" in result["gate_reason"]

    def test_requirement_naming_a_foreign_country_still_gates(self):
        from scoutpilot.scoring.scorer import apply_eligibility_gate
        result = apply_eligibility_gate(
            self._parsed(required_work_auth="Must be authorized to work in the United States"),
            self._uk_profile())
        assert result["score"] == 1
        assert "United States" in result["gate_reason"]

    def test_candidate_needing_sponsorship_still_gates(self):
        """The structured flags are what decide it, so a candidate who does
        need sponsorship is still gated by the same requirement that the
        settled-status holder passes."""
        from scoutpilot.scoring.scorer import apply_eligibility_gate
        profile = self._uk_profile()
        profile["work_authorization"] = {
            "legally_authorized_to_work": False,
            "require_sponsorship": True,
            "work_permit_type": "Student visa",
        }
        result = apply_eligibility_gate(
            self._parsed(required_work_auth="Right to work in the UK"), profile)
        assert result["score"] == 1

    def test_lowercase_us_pronoun_is_not_read_as_a_country(self):
        """'us' is a pronoun far more often than a country in job text, so
        the two-letter codes only count when capitalised."""
        from scoutpilot.scoring.scorer import _country_in_text
        assert _country_in_text("Come and build great things with us") is None
        assert _country_in_text("Authorised to work in the US") == "united states"

    def test_copyright_does_not_match_the_right_to_work_phrase(self):
        from scoutpilot.scoring.scorer import _GENERIC_RIGHT_TO_WORK_RE
        assert not _GENERIC_RIGHT_TO_WORK_RE.search("copyright to work products assigned")
        assert _GENERIC_RIGHT_TO_WORK_RE.search("must have the right to work here")

    def test_country_and_years_combine_to_the_lower_cap(self):
        from scoutpilot.scoring.scorer import apply_eligibility_gate
        parsed = {"score": 8, "required_country": "United States", "required_work_auth": None, "min_years_commercial": 3}
        result = apply_eligibility_gate(parsed, self._profile())
        assert result["score"] == 1  # country cap (1) wins over years cap (5)
        assert "United States" in result["gate_reason"] and "3" in result["gate_reason"]


class TestStripFabricatedSkillSentences:
    def _profile(self):
        return {"skills_boundary": {"programming_languages": ["Python", "Java"]}}

    def test_strips_sentence_naming_an_unlisted_tool(self):
        from scoutpilot.scoring.scorer import _strip_fabricated_skill_sentences
        job = {"site": "Acme", "full_description": "We use Hugging Face and LangChain extensively."}
        reasoning = (
            "The candidate has strong Python skills. They also have experience with "
            "Hugging Face, which matches the role well."
        )
        cleaned = _strip_fabricated_skill_sentences(reasoning, job, self._profile())
        assert "Hugging Face" not in cleaned
        assert "strong Python skills" in cleaned

    def test_leaves_clean_reasoning_untouched(self):
        from scoutpilot.scoring.scorer import _strip_fabricated_skill_sentences
        job = {"site": "Acme", "full_description": "We use Python and Java."}
        reasoning = "The candidate has strong Python and Java skills."
        assert _strip_fabricated_skill_sentences(reasoning, job, self._profile()) == reasoning
