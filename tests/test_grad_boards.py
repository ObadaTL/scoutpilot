"""Tests for the NI/UK graduate job-board harvesters (discovery/grad_boards.py)."""

import pytest

from scoutpilot.discovery import grad_boards as gb
from scoutpilot.database import init_db, get_jobs_by_stage, close_connection

NIJOBS_HTML = """
<html><body>
<a href="/job/graduate-software-engineer/kainos-software-job100001">x</a>
<a href="/job/senior-devops-engineer/mcs-group-job100002">x</a>
<a href="/job/software-developer-ni-hybrid/vanrath-job100003">x</a>
<a href="/job/marketing-manager/acme-agency-job100004">x</a>
<a href="/job/graduate-software-engineer/kainos-software-job100001">dup</a>
</body></html>
"""

CFG = {
    "nijobs": {
        "enabled": True,
        "base_url": "https://www.nijobs.com",
        "list_paths": ["/jobs/software"],
        "location": "Northern Ireland",
        "max_pages": 1,
    },
    "gradcracker": {"enabled": False, "base_url": "https://x", "list_paths": ["/y"]},
}


def test_parse_nijobs_filters_and_dedups():
    rows = gb._parse_nijobs(NIJOBS_HTML, "https://www.nijobs.com", "Northern Ireland")
    urls = {r["url"] for r in rows}
    # marketing manager filtered out by is_relevant_tech_role; dup collapsed
    assert urls == {
        "https://www.nijobs.com/job/graduate-software-engineer/kainos-software-job100001",
        "https://www.nijobs.com/job/senior-devops-engineer/mcs-group-job100002",
        "https://www.nijobs.com/job/software-developer-ni-hybrid/vanrath-job100003",
    }
    grad = next(r for r in rows if "kainos" in r["url"])
    assert grad["title"] == "Graduate Software Engineer"
    assert grad["company"] == "Kainos Software"
    assert grad["site"] == "NIJobs"
    assert grad["channel"] == "grad_boards"
    assert grad["opportunity_type"] == "graduate_scheme"


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr("scoutpilot.config.load_grad_boards_config", lambda: CFG)
    monkeypatch.setattr("scoutpilot.config.load_prefilter_config",
                        lambda: {"prefilter": {"enabled": False}})
    monkeypatch.setattr("scoutpilot.database.load_location_focus", lambda: None)
    path = tmp_path / "gb.db"
    conn = init_db(path)
    monkeypatch.setattr(gb, "init_db", lambda *a, **k: conn)
    monkeypatch.setattr(gb, "_http_get", lambda url, timeout=20: NIJOBS_HTML)
    yield conn
    close_connection(path)


def test_run_only_enabled_boards(env):
    res = gb.run_grad_boards_discovery()
    assert res["boards"] == 1          # nijobs only; gradcracker disabled
    assert res["errors"] == 0
    assert res["new"] == 3
    # stored as discovery rows awaiting enrichment (no full_description yet)
    sites = {r[0] for r in env.execute(
        "SELECT site FROM jobs WHERE channel = 'grad_boards'").fetchall()}
    assert sites == {"NIJobs"}
    assert env.execute(
        "SELECT COUNT(*) FROM jobs WHERE detail_scraped_at IS NULL AND channel='grad_boards'"
    ).fetchone()[0] == 3


def test_run_with_only_filter(env):
    assert gb.run_grad_boards_discovery(only="gradcracker")["boards"] == 0
    assert gb.run_grad_boards_discovery(only="nijobs")["boards"] == 1
