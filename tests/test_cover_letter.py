"""Tests for the six cover-letter-generation defect fixes.

Fast unit tests (ToolLeakGuard, strip helpers, generate_cover_letter retry
behavior) use synthetic fixtures directly, no DB/filesystem involved. The
two behaviorally-significant integration cases (PDF failure doesn't burn a
retry; missing tailored resume falls back loudly) use a fully isolated
scratch environment so they never touch the real ~/.applypilot data.
"""

import json

import pytest

from scoutpilot.facts import Fact, FactBank
from scoutpilot.scoring.validator import ToolLeakGuard, ToolLeakViolation


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

    def test_allcaps_heading_words_not_flagged(self):
        """Confirmed live 2026-09-02: an IBM posting's "UK-BASED" /
        "OFFICE-BASED" made 'based' register as a tool; the CV contains
        the word 'based', so ToolLeakGuard failed the tailored CV."""
        guard = ToolLeakGuard(_profile())
        job = {"site": "IBM", "full_description":
               "This is a UK-BASED role. WHAT YOU WILL DO: JOIN US and BUILD great things. OFFICE-BASED."}
        # a CV/letter that naturally uses these words must pass
        guard.check(job, "A Belfast-based engineer, I build backend services and want to join the team.")


# ── _strip_preamble / _strip_after_signoff ─────────────────────────────

class TestStripHelpers:
    def test_strip_preamble_removes_meta_commentary(self):
        from scoutpilot.scoring.cover_letter import _strip_preamble
        text = "Here is the cover letter:\n\nDear Hiring Manager,\n\nBody."
        assert _strip_preamble(text).startswith("Dear Hiring Manager,")

    def test_strip_preamble_not_fooled_by_mid_word_dear(self):
        """'endeared'/'dearest' mid-preamble must not be mistaken for the
        letter's real opening -- only a line-start Dear counts."""
        from scoutpilot.scoring.cover_letter import _strip_preamble
        text = "I have always been endeared to this company.\nDear Hiring Manager,\n\nBody."
        result = _strip_preamble(text)
        assert result.startswith("Dear Hiring Manager,")

    def test_strip_preamble_noop_when_already_clean(self):
        from scoutpilot.scoring.cover_letter import _strip_preamble
        text = "Dear Hiring Manager,\n\nBody.\n\nJordan"
        assert _strip_preamble(text) == text

    def test_strip_after_signoff_truncates_trailing_notes(self):
        from scoutpilot.scoring.cover_letter import _strip_after_signoff
        text = "Dear Hiring Manager,\n\nBody.\n\nJordan\n\nP.S. I also do freelance work."
        result = _strip_after_signoff(text, "Jordan")
        assert result.endswith("Jordan")
        assert "P.S." not in result

    def test_strip_after_signoff_uses_last_occurrence(self):
        """An incidental earlier mention of the name must not truncate the
        real body that follows it."""
        from scoutpilot.scoring.cover_letter import _strip_after_signoff
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
        import scoutpilot.scoring.cover_letter as cl_mod

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

    def test_temperature_stays_high_across_retries(self, monkeypatch):
        """Retries must keep sampling temperature, not drop it.

        The old behaviour was 0.7 on the first attempt and 0.3 on every
        retry, which asked the model to find a *different* phrasing for
        whatever the guard rejected while giving it less freedom to do so.
        In practice it re-emitted near-identical text, failed the same
        check, and burned the attempt budget down into the deterministic
        strip fallback -- the path that produced the mangled letters of
        2026-08-25.
        """
        import scoutpilot.scoring.cover_letter as cl_mod

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

        assert len(seen_temperatures) == 3  # every attempt ran
        assert all(t == 0.7 for t in seen_temperatures)


# ── run_cover_letters: isolated integration cases ──────────────────────

@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Fully isolated scratch environment: temp DB, profile, resume,
    facts.yaml -- never touches the real ~/.applypilot data."""
    import scoutpilot.config as config_mod
    import scoutpilot.database as database_mod
    import scoutpilot.facts as facts_mod
    import scoutpilot.scoring.cover_letter as cl_mod

    app_dir = tmp_path / "scoutpilot_home"
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
        monkeypatch.setattr("scoutpilot.scoring.pdf.convert_to_pdf", _flaky_convert)

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
        monkeypatch.setattr("scoutpilot.scoring.pdf.convert_to_pdf",
                            lambda path: path.with_suffix(".pdf"))

        import logging
        with caplog.at_level(logging.WARNING):
            result = cl_mod.run_cover_letters(min_score=1, validation_mode="lenient")

        assert result["fallback_to_base"] == 1
        assert any("falling back to the base resume" in r.message for r in caplog.records)


class _CleanClient:
    """A well-behaved local model: no fabricated numbers, no leaked tools,
    names the company (required by _check_company_mentioned), and produces a
    letter of real length and shape -- validate_cover_letter now rejects a
    stub in every mode, so a two-line fixture would fail for reasons that
    have nothing to do with what these integration tests are checking.

    Also stands in for the critic pass's extraction call (json_schema set):
    a letter this clean has no unsupported claims to report, so these
    integration tests -- about PDF failure and retry-budget accounting, not
    about the critic -- see it pass straight through.
    """

    def chat(self, messages, max_tokens=1024, temperature=0.7, json_schema=None):
        if json_schema is not None:
            return '{"unsupported_claims": []}'
        return (
            "Dear Hiring Manager,\n\n"
            "I built a reporting workflow that removed a manual end-of-month "
            "process end to end, from the ingest job through to the queries the "
            "finance team actually ran. That is the same shape of problem Acme "
            "describes in this posting, and it is the part of the work I like "
            "most.\n\n"
            "Most of my production experience is backend: services owned end to "
            "end, deployed and monitored rather than handed over at merge. I have "
            "spent as much time on the failure paths as the happy ones, which is "
            "usually where the interesting bugs live, and I am comfortable being "
            "the person who goes and finds them.\n\n"
            "The service ownership Acme describes is the reason I applied. "
            "Happy to walk through any of this in more detail.\n\n"
            "Sincerely,\n\nJordan"
        )


# ── Structural integrity: the 2026-08-25 shipped-garbage regressions ────
#
# Five letters shipped with cover_letter_passed=1 after the deterministic
# numeric fallback had gutted them. Each case below is one of those letters,
# reduced to the shape that made it through. They are regression tests in
# the literal sense: every one of them passed validation at the time.

class TestStructuralValidation:
    def _wrap(self, body: str) -> str:
        return f"Dear Hiring Manager,\n\n{body}\n\nSincerely,\n\nJordan"

    def test_orphaned_percent_is_rejected(self):
        """"...with % accuracy" -- the digit-blanking fallback's signature."""
        from scoutpilot.scoring.validator import validate_cover_letter

        letter = self._wrap(
            "I built a machine-learning pipeline for signal processing that "
            "classifies hand gestures with % accuracy, solving the same problem "
            "your team is facing. This system also includes a correction module "
            "that improved robustness by reducing overfitting by %. At Acme I "
            "designed and shipped an audit-event system across the backend, the "
            "hub and the datastore, which kept data integrity intact in a live "
            "production environment under real load."
        )
        result = validate_cover_letter(letter, mode="lenient")
        assert result["passed"] is False
        assert any("%" in e for e in result["errors"])

    def test_dangling_opener_is_rejected(self):
        """A first body paragraph opening on a referent that was deleted."""
        from scoutpilot.scoring.validator import validate_cover_letter

        letter = self._wrap(
            "This directly addresses the challenge of developing robust models "
            "from noisy, real-world data, a core requirement for the research "
            "work described in the posting and something I have spent a good "
            "deal of time on.\n\n"
            "These results demonstrate an ability to build models with Python "
            "and scikit-learn, skills that apply directly to the analysis work "
            "your team does day to day across its research systems."
        )
        result = validate_cover_letter(letter, mode="lenient")
        assert result["passed"] is False
        assert any("back-reference" in e for e in result["errors"])

    def test_midletter_back_reference_is_allowed(self):
        """Only the FIRST body paragraph can dangle -- a later "That ..."
        points at the paragraph above it and is ordinary English."""
        from scoutpilot.scoring.validator import has_dangling_reference

        letter = self._wrap(
            "I built a reporting workflow that removed a manual end-of-month "
            "process, from ingest through to the queries the finance team "
            "actually ran.\n\n"
            "That combination of ownership and follow-through is what I would "
            "bring here, and it is why the posting caught my attention in the "
            "first place rather than any one technology on the list."
        )
        assert has_dangling_reference(letter) is False

    def test_stub_letter_is_rejected_even_in_lenient_mode(self):
        """lenient tolerates style sins, not a letter with holes in it --
        and lenient is what a local provider runs in by default."""
        from scoutpilot.scoring.validator import validate_cover_letter

        letter = self._wrap(
            "At Acme I designed and shipped an audit-event system across the "
            "backend and the datastore."
        )
        result = validate_cover_letter(letter, mode="lenient")
        assert result["passed"] is False
        assert any("Too short" in e for e in result["errors"])

    def test_strip_no_longer_blanks_digits(self):
        """The fallback drops the paragraph rather than leaving its units
        stranded. Less text is recoverable; mangled text is not."""
        from scoutpilot.scoring.validator import strip_numbered_sentences

        stripped = strip_numbered_sentences(
            "Built it and reached 92% accuracy. Improved it by a further 15%.\n\n"
            "Owned the service end to end."
        )
        assert "%" not in stripped
        assert stripped == "Owned the service end to end."

    def test_dangling_opener_glued_to_salutation_is_still_caught(self):
        """The real bug: no blank line between "Dear Hiring Manager," and the
        dangling first sentence used to hide the whole paragraph from the
        check (it starts with "dear", so it looked like pure greeting)."""
        from scoutpilot.scoring.validator import has_dangling_reference

        letter = (
            "Dear Hiring Manager,\n"
            "This directly solves the same data challenges your team faces when "
            "building scalable systems and data pipelines.\n\n"
            "At Acme I designed and shipped an audit-event system across the "
            "backend and the datastore, keeping data integrity intact under load."
        )
        assert has_dangling_reference(letter) is True

    def test_repeated_phrase_is_rejected(self):
        """The same 5+ word claim showing up twice reads as padding, not two
        different pieces of evidence."""
        from scoutpilot.scoring.validator import validate_cover_letter

        letter = self._wrap(
            "I want to build scalable systems and data pipelines for teams that "
            "need reliable infrastructure they can depend on every day.\n\n"
            "At Acme I designed and shipped an audit-event system, which is the "
            "same rigorous approach your team needs to build scalable systems "
            "and data pipelines that hold up under real production load."
        )
        result = validate_cover_letter(letter, mode="lenient")
        assert result["passed"] is False
        assert any("Repeats the phrase" in e for e in result["errors"])

    def test_lifted_jd_span_is_rejected(self):
        """Reciting the posting's own marketing copy back at it isn't
        personalization."""
        from scoutpilot.scoring.validator import validate_cover_letter

        jd = (
            "Acme is building a global financial super app, offering services "
            "such as spending, saving, investing, exchanging, and traveling."
        )
        letter = self._wrap(
            "I built a reporting pipeline that removed a manual end-of-month "
            "process for the finance team, cutting a two-day close down to an "
            "afternoon.\n\n"
            "Acme is building a global financial super app, offering services "
            "such as spending, saving, investing, exchanging, and traveling, "
            "and that is exactly where I want to spend my time next."
        )
        result = validate_cover_letter(letter, mode="lenient", job_description=jd)
        assert result["passed"] is False
        assert any("near-verbatim from the job description" in e for e in result["errors"])

    def test_meta_reference_with_company_name_swapped_in_is_still_caught(self):
        """LLM_LEAK_PHRASES only banned the literal 'the job description
        mentions ...' -- swapping in the company's own possessive
        ('Revolut's description mentions ...') said the identical
        narrating-instead-of-claiming thing and passed. Confirmed live
        2026-08-26."""
        from scoutpilot.scoring.validator import validate_cover_letter

        letter = self._wrap(
            "I built a reporting pipeline that removed a manual end-of-month "
            "process, cutting a two-day close down to an afternoon for the "
            "whole finance team every single month.\n\n"
            "Acme's description mentions building data pipelines to support "
            "reporting and analytics, and that is exactly the kind of work I "
            "want to keep doing next in my career."
        )
        result = validate_cover_letter(letter, mode="lenient")
        assert result["passed"] is False
        assert any("Narrates the source" in e for e in result["errors"])

    def test_clean_signoff_is_not_flagged(self):
        from scoutpilot.scoring.validator import has_bad_signoff
        assert has_bad_signoff("Sincerely,\n\nJordan", "Jordan") is None

    def test_signoff_with_trailing_text_is_rejected(self):
        """The prompt asks for 'Sincerely,' then the name and nothing else --
        a trailing note past that point is the model not stopping where told."""
        from scoutpilot.scoring.validator import has_bad_signoff

        error = has_bad_signoff("Sincerely,\n\nJordan\nP.S. I would love to chat!", "Jordan")
        assert error is not None
        assert "more than just the name" in error
