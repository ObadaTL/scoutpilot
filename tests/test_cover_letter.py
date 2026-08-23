"""Tests for the six cover-letter-generation defect fixes.

Fast unit tests (ToolLeakGuard, strip helpers, generate_cover_letter retry
behavior) use synthetic fixtures directly, no DB/filesystem involved. The
two behaviorally-significant integration cases (PDF failure doesn't burn a
retry; missing tailored resume falls back loudly) use a fully isolated
scratch environment so they never touch the real ~/.applypilot data.
"""

import json

import pytest

from applypilot.facts import Fact, FactBank
from applypilot.scoring.validator import ToolLeakGuard, ToolLeakViolation


# ── Fixtures ────────────────────────────────────────────────────────────

def _multiparty_fact() -> Fact:
    return Fact(
        id="kraydel.multiparty_calls", tier="verified", numbers=[4, 9],
        variants={"short": "Raised multi-party video call capacity from 4 to 9 participants"},
        evidence="report: raised capacity to 9 from 4",
    )


def _bank(*facts) -> FactBank:
    return FactBank(list(facts), unfilled=[], forbidden=[])


def _profile(**overrides) -> dict:
    base = {
        "personal": {"full_name": "Jordan Smith", "preferred_name": "Jordan"},
        "skills_boundary": {"languages": ["Python", "SQL"], "devops": ["Docker", "AWS"]},
        "resume_facts": {"preserved_companies": [], "preserved_projects": [], "preserved_school": ""},
        "experience": {"education_level": "Bachelor's Degree"},
    }
    base.update(overrides)
    return base


# ── ToolLeakGuard ───────────────────────────────────────────────────────

class TestToolLeakGuard:
    def test_shape_heuristic_catches_acronym_tool(self):
        guard = ToolLeakGuard(_profile())
        job = {"site": "Acme", "full_description": "Must know AWS and GCP."}
        with pytest.raises(ToolLeakViolation) as exc:
            guard.check(job, "Dear Hiring Manager, I have used GCP extensively.")
        assert "gcp" in exc.value.tools

    def test_curated_list_catches_title_case_tool(self):
        """The fabrications that actually happen: plain Title-Case names
        like Kubernetes/Snowflake, invisible to any shape heuristic."""
        guard = ToolLeakGuard(_profile())
        job = {"site": "Acme", "full_description": "We run Kubernetes and Snowflake pipelines."}
        with pytest.raises(ToolLeakViolation) as exc:
            guard.check(job, "Dear Hiring Manager, I have deployed Kubernetes clusters.")
        assert "kubernetes" in exc.value.tools

    def test_allowed_skill_passes(self):
        guard = ToolLeakGuard(_profile())
        job = {"site": "Acme", "full_description": "Need Docker and AWS experience."}
        guard.check(job, "Dear Hiring Manager, I have used Docker and AWS daily.")  # no raise

    def test_company_acronym_not_flagged(self):
        """The prompt tells the model to name the company -- an acronym
        employer name (IBM, SAP, NCR) must never be treated as a tool leak."""
        guard = ToolLeakGuard(_profile())
        job = {"site": "IBM", "full_description": "Join IBM as a backend engineer."}
        guard.check(job, "Dear Hiring Manager, I would be excited to join IBM.")  # no raise

    def test_generic_acronym_stopwords_not_flagged(self):
        guard = ToolLeakGuard(_profile())
        job = {"site": "Acme", "full_description": "UK role, HR will reach out, AI-adjacent team."}
        guard.check(job, "Dear Hiring Manager, based in the UK, happy for HR to follow up.")  # no raise


# ── _strip_preamble / _strip_after_signoff ─────────────────────────────

class TestStripHelpers:
    def test_strip_preamble_removes_meta_commentary(self):
        from applypilot.scoring.cover_letter import _strip_preamble
        text = "Here is the cover letter:\n\nDear Hiring Manager,\n\nBody."
        assert _strip_preamble(text).startswith("Dear Hiring Manager,")

    def test_strip_preamble_not_fooled_by_mid_word_dear(self):
        """'endeared'/'dearest' mid-preamble must not be mistaken for the
        letter's real opening -- only a line-start Dear counts."""
        from applypilot.scoring.cover_letter import _strip_preamble
        text = "I have always been endeared to this company.\nDear Hiring Manager,\n\nBody."
        result = _strip_preamble(text)
        assert result.startswith("Dear Hiring Manager,")

    def test_strip_preamble_noop_when_already_clean(self):
        from applypilot.scoring.cover_letter import _strip_preamble
        text = "Dear Hiring Manager,\n\nBody.\n\nJordan"
        assert _strip_preamble(text) == text

    def test_strip_after_signoff_truncates_trailing_notes(self):
        from applypilot.scoring.cover_letter import _strip_after_signoff
        text = "Dear Hiring Manager,\n\nBody.\n\nJordan\n\nP.S. I also do freelance work."
        result = _strip_after_signoff(text, "Jordan")
        assert result.endswith("Jordan")
        assert "P.S." not in result

    def test_strip_after_signoff_uses_last_occurrence(self):
        """An incidental earlier mention of the name must not truncate the
        real body that follows it."""
        from applypilot.scoring.cover_letter import _strip_after_signoff
        text = "Dear Hiring Manager,\n\nMy name is Jordan and I built X.\n\nMore body.\n\nJordan"
        result = _strip_after_signoff(text, "Jordan")
        assert "More body." in result
        assert result.endswith("Jordan")


# ── generate_cover_letter: guard failure never ships ───────────────────

class _FabricatingClient:
    """Always fabricates the same unverified number, regardless of retry
    feedback -- simulates a local model that keeps inventing a number."""

    def chat(self, messages, max_tokens=1024, temperature=0.7):
        return (
            "Dear Hiring Manager,\n\n"
            "I built a platform serving 500 concurrent users with zero downtime.\n\n"
            "I'd love to discuss further.\n\nJordan"
        )


class TestGenerateCoverLetterNeverShipsOnFailedGuard:
    def test_exhausted_retries_returns_passed_false(self, monkeypatch):
        import applypilot.scoring.cover_letter as cl_mod

        monkeypatch.setattr(cl_mod, "get_client", lambda: _FabricatingClient())

        bank = _bank(_multiparty_fact())
        profile = _profile()
        job = {"title": "Backend Engineer", "site": "Acme", "location": "Remote",
              "full_description": "Backend role, Python, AWS."}

        letter, validation = cl_mod.generate_cover_letter(
            "SUMMARY\nExperienced engineer.\n", job, profile,
            max_retries=1, validation_mode="lenient", fact_bank=bank,
        )

        assert validation["passed"] is False
        assert any("500" in e for e in validation["errors"])

    def test_temperature_lowered_after_first_attempt(self, monkeypatch):
        import applypilot.scoring.cover_letter as cl_mod

        seen_temperatures = []

        class _RecordingClient:
            def chat(self, messages, max_tokens=1024, temperature=0.7):
                seen_temperatures.append(temperature)
                return (
                    "Dear Hiring Manager,\n\nBuilt something with 500 users.\n\nJordan"
                )

        monkeypatch.setattr(cl_mod, "get_client", lambda: _RecordingClient())
        bank = _bank(_multiparty_fact())
        job = {"title": "Backend Engineer", "site": "Acme", "location": "Remote",
              "full_description": "Backend role."}

        cl_mod.generate_cover_letter(
            "SUMMARY\nExperienced engineer.\n", job, _profile(),
            max_retries=2, validation_mode="lenient", fact_bank=bank,
        )

        assert seen_temperatures[0] == 0.7
        assert all(t == 0.3 for t in seen_temperatures[1:])


# ── run_cover_letters: isolated integration cases ──────────────────────

@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Fully isolated scratch environment: temp DB, profile, resume,
    facts.yaml -- never touches the real ~/.applypilot data."""
    import applypilot.config as config_mod
    import applypilot.database as database_mod
    import applypilot.facts as facts_mod
    import applypilot.scoring.cover_letter as cl_mod

    app_dir = tmp_path / "applypilot_home"
    app_dir.mkdir()
    cover_dir = app_dir / "cover_letters"
    cover_dir.mkdir()
    db_path = app_dir / "applypilot.db"

    profile_path = app_dir / "profile.json"
    profile_path.write_text(json.dumps(_profile()), encoding="utf-8")

    resume_path = app_dir / "resume.txt"
    resume_path.write_text("SUMMARY\nExperienced engineer.\n", encoding="utf-8")

    facts_path = tmp_path / "facts.yaml"
    facts_path.write_text(
        "role:\n"
        "  - id: real.metric\n"
        "    tier: verified\n"
        "    numbers: [4, 9]\n"
        "    evidence: \"report: raised capacity to 9 from 4\"\n"
        "    variants:\n"
        "      short: \"Raised capacity from 4 to 9\"\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(config_mod, "PROFILE_PATH", profile_path)
    monkeypatch.setattr(database_mod, "DB_PATH", db_path)
    monkeypatch.setattr(facts_mod, "FACTS_PATH", facts_path)
    monkeypatch.setattr(cl_mod, "RESUME_PATH", resume_path)
    monkeypatch.setattr(cl_mod, "COVER_LETTER_DIR", cover_dir)

    database_mod.init_db(db_path)
    conn = database_mod.get_connection(db_path)

    tailored_dir = app_dir / "tailored_resumes"
    tailored_dir.mkdir()
    tailored_txt = tailored_dir / "job1.txt"
    tailored_txt.write_text("SUMMARY\nTailored for this job.\n", encoding="utf-8")

    conn.execute("""
        INSERT INTO jobs (
            url, title, site, location, full_description, fit_score,
            tailored_resume_path, tailored_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "https://example.com/job1", "Backend Engineer", "Acme", "Remote",
        "Backend role, Python, AWS.", 8,
        str(tailored_dir / "job1.pdf"),  # tailor.py stores the .pdf path; .txt is the sibling
        "2026-01-01T00:00:00+00:00",
    ))
    conn.commit()

    return {"conn": conn, "cl_mod": cl_mod, "db_path": db_path, "tailored_txt": tailored_txt}


class TestRunCoverLettersIntegration:
    def test_pdf_failure_does_not_burn_a_retry(self, isolated_env, monkeypatch):
        cl_mod = isolated_env["cl_mod"]
        conn = isolated_env["conn"]

        # Preflight must pass (so the batch isn't aborted), but every
        # per-job PDF conversion fails.
        calls = {"n": 0}

        def _flaky_convert(path):
            calls["n"] += 1
            if calls["n"] == 1:
                return path.with_suffix(".pdf")  # preflight probe succeeds
            raise RuntimeError("Chromium crashed")

        monkeypatch.setattr(cl_mod, "get_client", lambda: _CleanClient())
        monkeypatch.setattr("applypilot.scoring.pdf.convert_to_pdf", _flaky_convert)

        result = cl_mod.run_cover_letters(min_score=1, validation_mode="lenient")

        assert result["pdf_failed"] == 1
        assert result["generated"] == 0

        row = conn.execute(
            "SELECT cover_letter_path, cover_attempts, cover_letter_passed "
            "FROM jobs WHERE url = ?",
            ("https://example.com/job1",),
        ).fetchone()
        assert row["cover_letter_path"] is None
        assert row["cover_attempts"] == 0  # not burned -- infra failure, not content failure
        assert row["cover_letter_passed"] == 0

    def test_missing_tailored_txt_falls_back_loudly(self, isolated_env, monkeypatch, caplog):
        cl_mod = isolated_env["cl_mod"]
        isolated_env["tailored_txt"].unlink()  # remove the .txt sibling

        monkeypatch.setattr(cl_mod, "get_client", lambda: _CleanClient())
        monkeypatch.setattr("applypilot.scoring.pdf.convert_to_pdf",
                            lambda path: path.with_suffix(".pdf"))

        import logging
        with caplog.at_level(logging.WARNING):
            result = cl_mod.run_cover_letters(min_score=1, validation_mode="lenient")

        assert result["fallback_to_base"] == 1
        assert any("falling back to the base resume" in r.message for r in caplog.records)


class _CleanClient:
    """A well-behaved local model: no fabricated numbers, no leaked tools,
    and names the company (required by _check_company_mentioned)."""

    def chat(self, messages, max_tokens=1024, temperature=0.7):
        return (
            "Dear Hiring Manager,\n\n"
            "I built a reporting workflow that removed a manual process end to end, "
            "and I'd bring that same instinct to Acme.\n\n"
            "Happy to discuss further.\n\nJordan"
        )
