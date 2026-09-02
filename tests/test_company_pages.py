"""Tests for the company-first (employer career page) harvester."""

import pytest

from scoutpilot.discovery import company_pages as cp
from scoutpilot.database import init_db, get_jobs_by_stage, close_connection

CFG = {
    "northern_ireland": [
        {"name": "FinTrU (Belfast)", "location": "Belfast", "careers_url": "https://fintru.example/careers"},
    ],
    "uk": [
        {"name": "Graphcore", "location": "Bristol", "ats": {"type": "greenhouse", "board": "graphcore"}},
        {"name": "DeadBoard", "location": "London", "ats": {"type": "greenhouse", "board": "nope"},
         "careers_url": "https://dead.example/jobs"},
    ],
    "known_boards": {
        "Monzo": {"type": "greenhouse", "board": "monzo"},
    },
}


def test_registry_entries_flattens_and_skips_known_boards():
    entries = cp._registry_entries(CFG)
    names = {e["name"] for e in entries}
    assert names == {"FinTrU (Belfast)", "Graphcore", "DeadBoard"}


def test_pointer_row_shape():
    r = cp._pointer_row("Acme", "https://acme.example/careers", "Belfast")
    assert r["url"] == "https://acme.example/careers"
    assert r["channel"] == "company_pages"
    assert r["company"] == "Acme"
    assert r["site"] == "Career Page (Acme)"
    assert r["application_url"] == r["url"]


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr("scoutpilot.config.load_company_pages_config", lambda: CFG)
    monkeypatch.setattr("scoutpilot.config.load_prefilter_config",
                        lambda: {"prefilter": {"enabled": False}})
    monkeypatch.setattr("scoutpilot.database.load_location_focus", lambda: None)
    path = tmp_path / "cp.db"
    conn = init_db(path)
    monkeypatch.setattr(cp, "init_db", lambda *a, **k: conn)
    monkeypatch.setattr("scoutpilot.database.get_connection", lambda *a, **k: conn)

    def fake_gh(board, name):
        if board == "graphcore":
            return [{
                "url": f"https://gh.example/{name}/1", "title": "Graduate Software Engineer",
                "company": name, "location": "Bristol, UK",
                "description": "d", "full_description": "f", "application_url": "u",
                "site": f"Greenhouse ({name})", "channel": "direct_ats",
                "opportunity_type": "graduate_scheme", "funding_status": "standard_salary",
            }]
        return []   # "nope", "monzo" -> empty

    monkeypatch.setattr(cp, "fetch_greenhouse_jobs", fake_gh)
    monkeypatch.setattr(cp, "_FETCHERS", {"greenhouse": fake_gh})
    yield conn
    close_connection(path)


def test_run_expands_ats_and_stores_pointers(env):
    res = cp.run_company_pages_discovery(workers=2, include_db_seeds=False)
    assert res["errors"] == 0
    assert res["new"] == 3   # graphcore role + FinTrU pointer + DeadBoard fallback pointer

    rows = {r["url"]: r for r in env.execute(
        "SELECT url, site, channel, company FROM jobs").fetchall()}
    gh = rows["https://gh.example/Graphcore/1"]
    assert gh["channel"] == "company_pages"
    assert gh["site"] == "Career Page (Graphcore)"          # re-tagged from Greenhouse (...)
    assert "https://fintru.example/careers" in rows
    assert "https://dead.example/jobs" in rows              # empty ATS -> careers_url fallback

    pending = get_jobs_by_stage(env, stage="pending_score")
    assert any(j["title"] == "Graduate Software Engineer" for j in pending)


def test_db_seed_adds_matching_company(env):
    env.execute("INSERT INTO jobs (url, title, company) VALUES ('x', 't', 'Monzo')")
    env.commit()
    # Monzo is in known_boards; fake_gh returns [] for it, and it has no
    # careers_url, so it contributes 0 rows but must not error.
    res = cp.run_company_pages_discovery(workers=2, include_db_seeds=True)
    assert res["errors"] == 0
    seeded = cp._db_seed_entries(CFG, env)
    assert [e["name"] for e in seeded] == ["Monzo"]
