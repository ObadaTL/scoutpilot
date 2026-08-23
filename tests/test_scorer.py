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
