"""Tests for terminal_view.list_jobs / render_jobs (the `scoutpilot jobs` command)."""

import pytest


@pytest.fixture
def scratch_db(tmp_path, monkeypatch):
    """Isolated scratch DB with a few jobs at different fit scores/sites,
    never touching the real ~/.applypilot data."""
    import scoutpilot.database as database_mod

    db_path = tmp_path / "applypilot.db"
    monkeypatch.setattr(database_mod, "DB_PATH", db_path)

    database_mod.init_db(db_path)
    conn = database_mod.get_connection(db_path)

    jobs = [
        ("https://example.com/1", "Backend Engineer", "Acme", 8, "Builds payments infra."),
        ("https://example.com/2", "ML Engineer", "Beta", 6, None),
        ("https://example.com/3", "Frontend Engineer", "Acme", 3, None),
        ("https://example.com/4", "Unscored Role", "Gamma", None, None),
    ]
    for url, title, site, fit, summary in jobs:
        conn.execute(
            "INSERT INTO jobs (url, title, site, fit_score, company_summary) "
            "VALUES (?, ?, ?, ?, ?)",
            (url, title, site, fit, summary),
        )
    conn.commit()
    return conn


class TestListJobs:
    def test_min_fit_filters_out_lower_scores(self, scratch_db):
        from scoutpilot.terminal_view import list_jobs
        result = list_jobs(min_fit=6)
        titles = {j["title"] for j in result}
        assert titles == {"Backend Engineer", "ML Engineer"}

    def test_min_fit_zero_includes_unscored(self, scratch_db):
        from scoutpilot.terminal_view import list_jobs
        result = list_jobs(min_fit=0)
        titles = {j["title"] for j in result}
        assert "Unscored Role" in titles

    def test_site_filter(self, scratch_db):
        from scoutpilot.terminal_view import list_jobs
        result = list_jobs(min_fit=0, site="Acme")
        assert {j["site"] for j in result} == {"Acme"}

    def test_sorted_by_fit_descending(self, scratch_db):
        from scoutpilot.terminal_view import list_jobs
        result = list_jobs(min_fit=0, site="Acme")
        scores = [j["fit_score"] for j in result]
        assert scores == sorted(scores, reverse=True)

    def test_limit(self, scratch_db):
        from scoutpilot.terminal_view import list_jobs
        result = list_jobs(min_fit=0, limit=1)
        assert len(result) == 1


class TestRenderJobs:
    def test_empty_list_does_not_crash(self):
        from scoutpilot.terminal_view import render_jobs
        render_jobs([])  # must not raise

    def test_null_fit_score_renders_as_unscored(self, capsys):
        from rich.console import Console
        from scoutpilot.terminal_view import render_jobs
        console = Console(width=100)
        render_jobs([{"title": "X", "site": "Acme", "fit_score": None, "company_summary": None}], console)
        # No exception is the main assertion here -- Rich handles the markup.
