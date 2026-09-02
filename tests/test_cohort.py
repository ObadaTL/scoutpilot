"""Tests for start-date / cohort inference (discovery/cohort.py) and the
discovery-backlog archive (database.archive_discovery_results)."""

from datetime import datetime, timezone

import pytest

from scoutpilot.discovery import cohort
from scoutpilot.discovery.cohort import infer_cohort_start, cohort_bucket, cohort_rank
from scoutpilot.database import (
    init_db,
    store_jobs,
    get_jobs_by_stage,
    scoring_queue,
    archive_discovery_results,
    unarchive_discovery_results,
    close_connection,
)

FIXED_NOW = datetime(2026, 9, 2, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _freeze_now(monkeypatch):
    monkeypatch.setattr(cohort, "_NOW", FIXED_NOW)


# ── infer_cohort_start ─────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("Graduate Scheme starting September 2026", "2026-09"),
    ("Join our Autumn 2027 cohort", "2027-09"),
    ("Summer 2026 internship", "2026-06"),
    ("2026 intake now open", "2026"),
    ("Programme commencing in 2027", "2027"),
    ("intake: September 2026", "2026-09"),
    ("Immediate start available", "immediate"),
    ("We need someone to start ASAP", "immediate"),
])
def test_infer_cohort_start_hits(text, expected):
    assert infer_cohort_start("Some Role", text) == expected


@pytest.mark.parametrize("text", [
    "Software Engineer, Belfast",
    "Great team, competitive salary",
    "We were founded in 2019 and have grown fast",   # year, but not a start
    "Looking for 3+ years experience",
    "Class of 2015 alumni network",                   # year outside window
])
def test_infer_cohort_start_misses(text):
    assert infer_cohort_start("Software Engineer", text) is None


def test_infer_cohort_start_from_title():
    assert infer_cohort_start("Graduate Engineer - September 2026 start", None) == "2026-09"


def test_year_window_rejects_far_future():
    # +3 is the edge (2029 ok), +4 is out
    assert infer_cohort_start("x", "2029 intake") == "2029"
    assert infer_cohort_start("x", "2031 intake") is None


# ── buckets / ranks ───────────────────────────────────────────────────

def test_cohort_bucket_and_rank():
    assert cohort_bucket("immediate") == "immediate"
    assert cohort_bucket("2026-09") == "this_year"
    assert cohort_bucket("2027") == "next_year"
    assert cohort_bucket("2029") == "future"
    assert cohort_bucket(None) == "unknown"
    assert cohort_bucket(None, deadline="2027-11-30") == "next_year"   # deadline fallback

    assert cohort_rank("immediate") < cohort_rank("2026-09") < cohort_rank(None)
    assert cohort_rank(None) < cohort_rank("2027") < cohort_rank("2029")


# ── archive_discovery_results ─────────────────────────────────────────

@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr("scoutpilot.config.load_prefilter_config",
                        lambda: {"prefilter": {"enabled": False},
                                 "scoring_queue": {"enabled": True, "hit_score": 7,
                                                   "floor": 0.05, "min_sample": 15,
                                                   "sample_divisor": 6}})
    monkeypatch.setattr("scoutpilot.database.load_location_focus", lambda: None)
    path = tmp_path / "arch.db"
    conn = init_db(path)
    yield conn
    close_connection(path)


def test_archive_scopes_to_untouched_discovery_rows(db, tmp_path):
    store_jobs(db, [
        {"url": "raw1", "title": "Engineer", "location": "UK", "full_description": "x" * 300},
        {"url": "raw2", "title": "Engineer", "location": "UK", "full_description": "x" * 300},
    ], site="B", strategy="t")
    # one row that's been tailored, one that's been applied -- history, keep live
    # (a tailored/applied job has also been scored)
    db.execute("UPDATE jobs SET tailored_resume_path = '/p.pdf', fit_score = 8 WHERE url = 'raw1'")
    store_jobs(db, [{"url": "done", "title": "Engineer", "location": "UK", "full_description": "x" * 300}],
               site="B", strategy="t")
    db.execute("UPDATE jobs SET applied_at = '2026-08-01', fit_score = 7 WHERE url = 'done'")
    db.commit()

    note = tmp_path / "undo.txt"
    res = archive_discovery_results(db, note_path=note)

    assert res["archived"] == 1                      # only raw2
    rows = dict(db.execute("SELECT url, archived_at FROM jobs").fetchall())
    assert rows["raw2"] == res["timestamp"]
    assert rows["raw1"] is None and rows["done"] is None

    text = note.read_text()
    assert res["timestamp"] in text
    assert "UPDATE jobs SET archived_at = NULL WHERE archived_at =" in text

    # archived row is out of the scoring queue and pending_score
    assert scoring_queue(db) == []
    assert get_jobs_by_stage(db, stage="pending_score") == []

    # undo brings it back
    restored = unarchive_discovery_results(db, res["timestamp"])
    assert restored == 1
    assert [j["url"] for j in get_jobs_by_stage(db, stage="pending_score")] == ["raw2"]


def test_archive_is_idempotent(db, tmp_path):
    store_jobs(db, [{"url": "a", "title": "Engineer", "location": "UK", "full_description": "x" * 300}],
               site="B", strategy="t")
    r1 = archive_discovery_results(db, note_path=tmp_path / "n1.txt")
    r2 = archive_discovery_results(db, note_path=tmp_path / "n2.txt")
    assert r1["archived"] == 1
    assert r2["archived"] == 0        # nothing left un-archived


# ── cohort filter + queue ordering ───────────────────────────────────

def test_cohort_filter_and_queue_order(db):
    store_jobs(db, [
        {"url": "imm", "title": "Engineer", "location": "UK",
         "full_description": "Immediate start. " + "x" * 300},
        {"url": "y26", "title": "Graduate Engineer", "location": "UK",
         "full_description": "2026 intake. " + "x" * 300},
        {"url": "y28", "title": "Graduate Engineer", "location": "UK",
         "full_description": "Join our 2028 cohort. " + "x" * 300},
        {"url": "none", "title": "Engineer", "location": "UK", "full_description": "x" * 300},
    ], site="B", strategy="t")

    got = {r["url"]: r["cohort_start"] for r in
           db.execute("SELECT url, cohort_start FROM jobs").fetchall()}
    assert got["imm"] == "immediate"
    assert got["y26"] == "2026"
    assert got["y28"] == "2028"
    assert got["none"] is None

    imm_only = get_jobs_by_stage(db, stage="pending_score", cohort="immediate")
    assert [j["url"] for j in imm_only] == ["imm"]
    y26_only = get_jobs_by_stage(db, stage="pending_score", cohort="2026")
    assert [j["url"] for j in y26_only] == ["y26"]

    # queue: immediate before this-year before unknown before far-future
    q = scoring_queue(db)
    assert q.index("imm") < q.index("y26") < q.index("none") < q.index("y28")
