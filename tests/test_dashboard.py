"""Dashboard behaviour: CV/cover-letter independence, and the two things
that made the served page slow.

Both fixes here came from the same complaint -- "the dashboard is slow and
sometimes the CV never appears" -- and neither cause was what it looked
like. The page was slow because a config file was re-parsed once per job and
because every job description was inlined into the HTML; the CV went missing
because a cover-letter failure was reported as a failure of the whole job.
"""

from pathlib import Path

import pytest


# ── The CV must survive a failed cover letter ────────────────────────────

class TestTailorCoverSeparation:
    """A cover-letter failure used to set the job's single status field to
    "error". The page only reloads on success, so the CV -- already written
    to disk and recorded in the database -- never appeared on the card."""

    @pytest.fixture(autouse=True)
    def _clean_state(self):
        import scoutpilot.view as view
        view._tailor_jobs.clear()
        yield
        view._tailor_jobs.clear()

    def _patch(self, monkeypatch, tailor_status="approved", cover=None):
        import scoutpilot.scoring.cover_letter as cl_mod
        import scoutpilot.scoring.tailor as tailor_mod
        monkeypatch.setattr(
            tailor_mod, "tailor_one",
            lambda url, max_retries=1: {"status": tailor_status, "errors": ["nope"]},
        )
        if cover is not None:
            monkeypatch.setattr(cl_mod, "cover_letter_one", cover)

    def test_blocked_cover_letter_still_reports_the_cv_as_done(self, monkeypatch):
        import scoutpilot.view as view
        self._patch(monkeypatch, cover=lambda url, max_retries=1: {
            "status": "blocked", "errors": ["ToolLeakGuard: llm"]})
        view._run_tailor_and_cover("job-1")

        status = view.get_tailor_status("job-1")
        assert status["cv"] == "done"
        assert status["cover"] == "error"
        # Overall status must NOT be an error: the page keys its reload off
        # this, and there is a real CV to show.
        assert status["status"] == "done"
        assert "ToolLeakGuard" in status["cover_error"]

    def test_a_cover_letter_that_raises_is_contained(self, monkeypatch):
        import scoutpilot.view as view

        def boom(url, max_retries=1):
            raise RuntimeError("provider down")

        self._patch(monkeypatch, cover=boom)
        view._run_tailor_and_cover("job-2")

        status = view.get_tailor_status("job-2")
        assert status["cv"] == "done" and status["status"] == "done"
        assert status["cover"] == "error" and "provider down" in status["cover_error"]

    def test_a_failed_cv_is_still_an_overall_error(self, monkeypatch):
        """The separation must not swallow the failure that genuinely means
        there is nothing to show."""
        import scoutpilot.view as view
        self._patch(monkeypatch, tailor_status="failed_validation")
        view._run_tailor_and_cover("job-3")

        status = view.get_tailor_status("job-3")
        assert status["status"] == "error"
        assert status["cv"] == "error"
        assert status["cover"] == "skipped"

    def test_a_letter_only_run_never_touches_cv_state(self, monkeypatch):
        """The retry path runs against the CV already on disk, so it must
        report into `cover` alone."""
        import scoutpilot.scoring.cover_letter as cl_mod
        import scoutpilot.view as view
        monkeypatch.setattr(cl_mod, "cover_letter_one",
                            lambda url, max_retries=1: {"status": "generated", "errors": []})
        view._run_cover_letter("job-4")

        status = view.get_tailor_status("job-4")
        assert status["cover"] == "done"
        assert "cv" not in status


# ── The config file was re-parsed once per job ───────────────────────────

class TestYamlConfigCache:
    """load_search_config() was called 1843 times rendering one dashboard --
    once per job via classify_location -- and re-parsed the YAML every time.
    25.6 of the page's 34 seconds were inside yaml.safe_load."""

    def test_an_unchanged_file_is_parsed_once(self, tmp_path, monkeypatch):
        import yaml as yaml_mod

        from scoutpilot import config as config_mod

        path = tmp_path / "searches.yaml"
        path.write_text("location_focus:\n  enabled: true\n  priority:\n    - [Belfast]\n",
                        encoding="utf-8")
        config_mod._yaml_cache.clear()

        calls = []
        real = yaml_mod.safe_load
        monkeypatch.setattr(yaml_mod, "safe_load", lambda t: (calls.append(1), real(t))[1])

        first = config_mod._load_yaml_cached(path)
        for _ in range(50):
            config_mod._load_yaml_cached(path)
        assert len(calls) == 1
        assert first["location_focus"]["enabled"] is True

    def test_editing_the_file_takes_effect_without_a_restart(self, tmp_path):
        """searches.yaml is hand-edited, so the cache is keyed on the file's
        own mtime/size rather than cached outright."""
        import os

        from scoutpilot import config as config_mod

        path = tmp_path / "searches.yaml"
        path.write_text("a: 1\n", encoding="utf-8")
        config_mod._yaml_cache.clear()
        assert config_mod._load_yaml_cached(path) == {"a": 1}

        path.write_text("a: 2\nb: 3\n", encoding="utf-8")
        # Bump mtime explicitly: the two writes can land in the same clock
        # tick on Windows, and the size check alone would not catch an
        # edit that happened to preserve length.
        st = path.stat()
        os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))
        assert config_mod._load_yaml_cached(path) == {"a": 2, "b": 3}

    def test_a_missing_file_returns_none_rather_than_raising(self, tmp_path):
        from scoutpilot import config as config_mod
        assert config_mod._load_yaml_cached(tmp_path / "nope.yaml") is None


# ── The search box depends on the descriptions being in the DOM ──────────

class TestSearchHaystack:
    """applyFilters() matches the search term against `card.textContent`.
    On 2026-09-02 the full descriptions were moved out of the page to make
    it smaller, which quietly shrank what a search could reach -- and since
    the active search term is persisted in localStorage, a stored term that
    had matched hundreds of jobs suddenly matched almost none on every
    reload. It reads to the user as "all my jobs disappeared".

    These pin the coupling so the next size optimisation has to deal with
    the search first instead of discovering this the same way.
    """

    def _render(self, tmp_path, monkeypatch, **kwargs):
        import scoutpilot.view as view

        rows = [{
            "url": "https://example.com/job/1", "title": "Backend Engineer",
            "salary": None, "description": "short preview",
            "full_description": ("Backend role on the platform team. " * 12
                                 + "We need someone who knows KUBERNETES and Elixir."),
            "location": "Belfast", "site": "TestSite", "strategy": None,
            "application_url": None, "detail_error": None, "fit_score": 8,
            "score_reasoning": "keywords\nreasoning text", "company_summary": None,
            "company_hook": None, "gate_reason": None, "critic_score": None,
            "tailored_resume_path": None, "tailored_at": None, "tailor_attempts": 0,
            "cover_letter_path": None, "cover_letter_at": None, "cover_attempts": 0,
            "applied_at": None, "apply_status": None, "apply_error": None,
            "apply_attempts": 0, "last_attempted_at": None,
            "verification_confidence": None, "hidden": 0,
            "discovered_at": "2026-09-01T00:00:00+00:00",
        }]

        class _Row(dict):
            def __getitem__(self, k):
                return dict.get(self, k)

        class _Cur:
            def __init__(self, result): self._r = result
            def fetchone(self): return self._r[0] if self._r else None
            def fetchall(self): return self._r
            def __iter__(self): return iter(self._r)

        class _Conn:
            def execute(self, sql, params=()):
                s = " ".join(sql.split()).lower()
                if s.startswith("select count"):
                    return _Cur([[1]])
                if "group by fit_score" in s:
                    return _Cur([[8, 1]])
                if "group by site" in s:
                    return _Cur([])
                if "from jobs where fit_score is not null or" in s:
                    return _Cur([_Row(r) for r in rows])
                return _Cur([])

        monkeypatch.setattr(view, "get_connection", lambda: _Conn())
        out = tmp_path / "dash.html"
        return Path(view.generate_dashboard(str(out), **kwargs)).read_text(
            encoding="utf-8", errors="replace")

    def test_a_page_without_descriptions_must_have_server_side_search(self, tmp_path, monkeypatch):
        """The real invariant. A description that is neither in the DOM nor
        reachable by /api/search is not searchable at all, which is the bug
        that emptied the board on 2026-09-02. Either mechanism is fine; the
        absence of both is not."""
        for serve_base_url in ("http://127.0.0.1:8765", None):
            kwargs = {"serve_base_url": serve_base_url} if serve_base_url else {}
            html = self._render(tmp_path, monkeypatch, **kwargs)
            inline = "KUBERNETES" in html
            server_side = "const SERVER_SEARCH = true;" in html
            assert inline or server_side, (
                f"serve_base_url={serve_base_url!r}: descriptions are not in the "
                "page and there is no server-side search to reach them"
            )

    def test_the_static_snapshot_inlines_descriptions(self, tmp_path, monkeypatch):
        """A file:// page has no server, so its search is still the
        textContent one and the descriptions have to be present."""
        html = self._render(tmp_path, monkeypatch)
        assert "const SERVER_SEARCH = false;" in html
        assert "KUBERNETES" in html

    def test_the_served_page_drops_descriptions_and_searches_in_sql(self, tmp_path, monkeypatch):
        html = self._render(tmp_path, monkeypatch,
                            serve_base_url="http://127.0.0.1:8765")
        assert "const SERVER_SEARCH = true;" in html
        # The 280-char preview stays inline; the body past it does not, which
        # is where the ~11.7 MB across the real board actually lives.
        assert "KUBERNETES" not in html
        assert "loadFullDesc" in html         # still reachable on expand

    def test_the_static_snapshot_has_no_relative_api_calls(self, tmp_path, monkeypatch):
        """A file:// page cannot reach /api/... -- every such call fails as
        "Failed to fetch". The manage buttons are served-mode only for
        exactly this reason."""
        html = self._render(tmp_path, monkeypatch)
        # The class names are always in the stylesheet; what must be absent
        # is the markup that wires a button to a POST.
        assert 'onclick="tailorJob(' not in html
        assert 'onclick="coverLetterJob(' not in html
        assert 'onclick="hideJob(' not in html

    def test_the_served_page_does_wire_those_buttons(self, tmp_path, monkeypatch):
        html = self._render(tmp_path, monkeypatch,
                            serve_base_url="http://127.0.0.1:8765")
        assert 'onclick="tailorJob(' in html


# ── Grouping ads by employer ─────────────────────────────────────────────

class TestDeriveCompany:
    """`company` is set on only 21% of stored jobs, because
    store_jobspy_results read it off every LinkedIn/Indeed row and then left
    it out of the INSERT (fixed 2026-09-02, but the stored rows remain).
    derive_company recovers the rest from what else is on the row."""

    def test_the_column_wins_when_it_is_set(self):
        from scoutpilot.database import derive_company
        assert derive_company({"company": "Kraydel", "site": "linkedin",
                               "company_summary": "Someone Else is a firm."}) == "Kraydel"

    def test_an_ats_board_site_names_the_employer(self):
        from scoutpilot.database import derive_company
        for site, expected in [("Greenhouse (GitLab)", "GitLab"),
                               ("Ashby (Supabase)", "Supabase"),
                               ("Lever (Spotify)", "Spotify")]:
            assert derive_company({"company": None, "site": site}) == expected

    def test_a_per_employer_scraper_puts_the_employer_in_site(self):
        from scoutpilot.database import derive_company
        assert derive_company({"company": "", "site": "Thomson Reuters"}) == "Thomson Reuters"

    def test_an_aggregator_site_is_never_treated_as_an_employer(self):
        from scoutpilot.database import UNKNOWN_COMPANY, derive_company
        for site in ("linkedin", "indeed", "Glassdoor"):
            assert derive_company({"company": None, "site": site}) == UNKNOWN_COMPANY

    def test_the_company_summary_is_the_last_resort(self):
        from scoutpilot.database import derive_company
        cases = {
            "Riff Financial is a pre-launch UK fintech company.": "Riff Financial",
            "Esri develops industry-leading ArcGIS products.": "Esri",
            "Motorola Solutions builds mission-critical communications.": "Motorola Solutions",
            "Cisco's Webex Engineering Group is building tools.": "Cisco",
        }
        for summary, expected in cases.items():
            assert derive_company(
                {"company": None, "site": "linkedin", "company_summary": summary}
            ) == expected

    def test_nothing_recoverable_returns_the_shared_unknown_label(self):
        from scoutpilot.database import UNKNOWN_COMPANY, derive_company
        assert derive_company({"company": None, "site": "indeed",
                               "company_summary": None}) == UNKNOWN_COMPANY
        assert derive_company({}) == UNKNOWN_COMPANY


class TestGroupNearIdentical:
    """Advisory badge only. It must never be wired to duplicate_of: the
    2026-09-02 audit found employers reusing one description across
    genuinely different roles (three Ciena postings differing only by air
    force base; an iOS and an Android graduate programme scoring 6 and 8),
    and demoting those would drop real postings out of the pipeline."""

    def _job(self, url, text):
        return {"url": url, "full_description": text, "description": None}

    def _long(self, extra=""):
        return (" ".join(f"we build reliable backend services word{i}" for i in range(60))
                + " " + extra)

    def test_two_copies_of_one_ad_are_grouped(self):
        from scoutpilot.database import group_near_identical
        text = self._long()
        marks = group_near_identical([self._job("a", text),
                                      self._job("b", text + " apply today")])
        assert marks["a"] == marks["b"]

    def test_unrelated_ads_are_not_grouped(self):
        from scoutpilot.database import group_near_identical
        a = self._long()
        b = " ".join(f"marketing campaigns for retail brands item{i}" for i in range(60))
        assert group_near_identical([self._job("a", a), self._job("b", b)]) == {}

    def test_a_job_with_no_similar_sibling_is_absent_from_the_result(self):
        from scoutpilot.database import group_near_identical
        text = self._long()
        marks = group_near_identical([
            self._job("a", text), self._job("b", text),
            self._job("c", " ".join(f"unrelated legal editing work item{i}" for i in range(60))),
        ])
        assert "c" not in marks and marks["a"] == marks["b"]

    def test_a_description_too_short_to_fingerprint_is_ignored(self):
        from scoutpilot.database import group_near_identical
        assert group_near_identical([self._job("a", "hi"), self._job("b", "hi")]) == {}

    def test_the_threshold_matches_what_was_measured(self):
        """Below 0.8 Jaccard, 0 of 1093 sampled same-employer pairs were
        duplicates by the production difflib measure. If someone lowers this,
        the badge becomes noise."""
        from scoutpilot.database import _NEAR_IDENTICAL_JACCARD
        assert _NEAR_IDENTICAL_JACCARD >= 0.8
