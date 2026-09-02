"""Tests for the ingest pre-filter (discovery/prefilter.py) and the
yield-ordered scoring queue (database.source_hit_rates / scoring_queue).

The pre-filter is a pure function of (job dict, config), so most of these
pass an explicit config and never touch the shipped YAML or the user's
searches.yaml. The integration tests monkeypatch load_prefilter_config so
store_jobs / scoring_queue run against a known ruleset.
"""

import pytest

from scoutpilot.discovery.prefilter import evaluate_prefilter, prefilter_breakdown
from scoutpilot.database import (
    init_db,
    store_jobs,
    get_jobs_by_stage,
    source_hit_rates,
    scoring_queue,
    refresh_prefilter,
    get_connection,
    close_connection,
)

# A compact ruleset mirroring config/prefilter.yaml's shape.
CFG = {
    "prefilter": {
        "enabled": True,
        "location": {
            "enabled": True,
            "strict_channels": ["direct_ats", "workday_api"],
            "allow_terms": ["united kingdom", "uk", "belfast", "london", "ireland", "dublin"],
            "deny_terms": ["united states", "usa", "new york", "san francisco",
                           "toronto", "berlin", "india", "bangalore", "amer"],
        },
        "seniority_title": {
            "enabled": True,
            "terms": ["senior", "staff", "principal", "lead", "director", "head of",
                      "vice president", "architect", "manager"],
            "allow_terms": ["graduate", "junior", "intern", "placement", "trainee",
                            "early career", "new grad"],
        },
        "experience_years": {
            "enabled": True,
            "max_years": 2,
            "scan": "title_and_body",
            "patterns": [
                r"(\d+)\s*\+?\s*years?[^.\n]{0,40}?\b(?:experience|exp)\b",
                r"(?:minimum|at\s+least|min\.?)\s+(?:of\s+)?(\d+)\s*\+?\s*years?",
                r"(\d+)\s*[-–]\s*\d+\s*years?[^.\n]{0,40}?\b(?:experience|exp)\b",
            ],
        },
    },
    "scoring_queue": {
        "enabled": True, "hit_score": 7, "floor": 0.05,
        "min_sample": 10, "sample_divisor": 4,
    },
}


def _job(**kw):
    base = {"title": "Software Engineer", "location": "Belfast, UK",
            "description": "", "full_description": ""}
    base.update(kw)
    return base


# ── location rule ────────────────────────────────────────────────────────

def test_location_foreign_is_filtered():
    r = evaluate_prefilter(_job(location="New York, NY, United States"), CFG)
    assert r and r.startswith("location:")


def test_location_uk_passes():
    assert evaluate_prefilter(_job(location="London, England, United Kingdom"), CFG) is None


def test_location_uk_remote_passes():
    assert evaluate_prefilter(_job(location="Remote - UK"), CFG) is None


def test_location_bare_remote_passes():
    # no deny term at all -> rule can't fire
    assert evaluate_prefilter(_job(location="Remote"), CFG) is None


def test_location_foreign_remote_is_filtered():
    r = evaluate_prefilter(_job(location="Remote - United States"), CFG)
    assert r and r.startswith("location:")


def test_location_blank_passes():
    assert evaluate_prefilter(_job(location=None), CFG) is None
    assert evaluate_prefilter(_job(location=""), CFG) is None


def test_location_substring_not_matched_as_word():
    # "uk" inside "Paducah"? no -- but guard against "uk" matching "ukraine"
    assert evaluate_prefilter(_job(location="Kyiv, Ukraine"), CFG) is None  # ukraine not in deny list, uk not a word


# ── strict channels: global ATS must positively signal UK/IE ────────────

def test_strict_channel_needs_uk_signal():
    # non-strict channel: "Remote" is fine, no deny term -> passes
    assert evaluate_prefilter(_job(location="Remote / Unspecified"), CFG, channel="jobspy") is None
    # strict channel: bare/blank/"Remote" location with no UK signal -> filtered
    for loc in ("Remote / Unspecified", "Remote", "", None, "San Francisco, CA"):
        r = evaluate_prefilter(_job(location=loc), CFG, channel="direct_ats")
        assert r and "no UK/Ireland signal" in r, loc
    # strict channel with a UK signal in the location -> passes
    assert evaluate_prefilter(_job(location="London, UK"), CFG, channel="direct_ats") is None
    # strict channel, UK signal only in the body -> passes
    assert evaluate_prefilter(
        _job(location="Remote", full_description="This role is open to candidates in the United Kingdom."),
        CFG, channel="direct_ats") is None


def test_strict_channel_read_from_job_dict():
    r = evaluate_prefilter(
        {"title": "Engineer", "location": "San Francisco", "strategy": "direct_ats"}, CFG)
    assert r and r.startswith("location:")


# ── seniority rule ──────────────────────────────────────────────────────

@pytest.mark.parametrize("title", [
    "Senior Software Engineer",
    "Staff Backend Engineer",
    "Principal Data Scientist",
    "Engineering Lead",
    "Director of Engineering",
    "Head of Platform",
    "Software Architect",
])
def test_seniority_titles_filtered(title):
    r = evaluate_prefilter(_job(title=title, location="Belfast"), CFG)
    assert r and r.startswith("seniority:")


@pytest.mark.parametrize("title", [
    "Graduate Software Engineer",
    "Junior Backend Developer",
    "Software Engineer Intern",
    "Senior-friendly Graduate Scheme Lead Trainee",  # has 'graduate' + 'trainee'
])
def test_junior_qualifier_rescues_title(title):
    assert evaluate_prefilter(_job(title=title, location="Belfast"), CFG) is None


def test_lead_does_not_match_leader_word_boundary():
    # 'leadership' should not trip the 'lead' term
    assert evaluate_prefilter(_job(title="Graduate Leadership Programme", location="UK"), CFG) is None


# ── experience-years rule ───────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "5+ years of commercial experience",
    "minimum 3 years experience",
    "at least 4 years",
    "3-5 years of experience",
    "You have 8 years experience in backend systems",
])
def test_multi_year_requirement_filtered(text):
    r = evaluate_prefilter(_job(title="Software Engineer", location="UK", full_description=text), CFG)
    assert r and r.startswith("experience:")


@pytest.mark.parametrize("text", [
    "2 years experience preferred",          # == cap, not over
    "1+ years experience",
    "graduating in 2025, 2026 cohort welcome",  # bare years, no 'experience'
    "we have 20 years of history as a company",  # 'years of history' not 'experience'
])
def test_experience_non_triggers(text):
    assert evaluate_prefilter(_job(title="Graduate Engineer", location="UK", full_description=text), CFG) is None


def test_experience_default_scan_is_title_only():
    """Shipped default is scan=title: a body '5+ years experience' does NOT
    trip the filter, but a title one does."""
    cfg_title_only = {
        "prefilter": {
            "enabled": True,
            "location": {"enabled": False},
            "seniority_title": {"enabled": False},
            "experience_years": {
                "enabled": True, "max_years": 2,
                "patterns": [r"(\d+)\s*\+?\s*years?[^.\n]{0,40}?\b(?:experience|exp)\b"],
            },
        }
    }
    assert evaluate_prefilter(
        _job(title="Software Engineer", full_description="7+ years experience required"),
        cfg_title_only,
    ) is None
    r = evaluate_prefilter(
        _job(title="Software Engineer, 7+ years experience", full_description=""),
        cfg_title_only,
    )
    assert r and r.startswith("experience:")


# ── config gates ────────────────────────────────────────────────────────

def test_disabled_prefilter_returns_none():
    cfg = {"prefilter": {"enabled": False}}
    assert evaluate_prefilter(_job(title="Senior Engineer", location="New York"), cfg) is None


def test_breakdown_lists_every_rule_tripped():
    job = _job(title="Senior Engineer", location="San Francisco, USA",
               full_description="7+ years experience required")
    reasons = prefilter_breakdown(job, CFG)
    assert len(reasons) == 3
    assert any(r.startswith("location:") for r in reasons)
    assert any(r.startswith("seniority:") for r in reasons)
    assert any(r.startswith("experience:") for r in reasons)


# ── integration: store_jobs stamps the column, queue skips it ────────────

@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr("scoutpilot.config.load_prefilter_config", lambda: CFG)
    monkeypatch.setattr("scoutpilot.database.load_location_focus", lambda: None)
    path = tmp_path / "pf.db"
    conn = init_db(path)
    yield conn
    close_connection(path)


def test_store_jobs_stamps_prefilter_reason(db):
    jobs = [
        {"url": "u1", "title": "Graduate Engineer", "location": "Belfast, UK",
         "full_description": "x" * 300},
        {"url": "u2", "title": "Senior Engineer", "location": "Belfast, UK",
         "full_description": "x" * 300},
        {"url": "u3", "title": "Data Analyst", "location": "New York, USA",
         "full_description": "x" * 300},
    ]
    new, existing = store_jobs(db, jobs, site="TestBoard", strategy="test")
    assert new == 3
    rows = dict(db.execute("SELECT url, prefilter_reason FROM jobs").fetchall())
    assert rows["u1"] is None
    assert rows["u2"].startswith("seniority:")
    assert rows["u3"].startswith("location:")

    pending = get_jobs_by_stage(db, stage="pending_score", limit=0)
    assert [j["url"] for j in pending] == ["u1"]


# ── source_hit_rates ────────────────────────────────────────────────────

def _add_scored(conn, url, site, fit):
    conn.execute(
        "INSERT INTO jobs (url, title, site, full_description, fit_score, scored_at) "
        "VALUES (?, ?, ?, ?, ?, '2026-09-02')",
        (url, "Engineer", site, "x" * 300, fit),
    )


def test_source_hit_rates_and_trust(db):
    for i in range(12):
        _add_scored(db, f"hi{i}", "GoodBoard", 8 if i < 6 else 3)   # 6/12 = 50%
    for i in range(20):
        _add_scored(db, f"lo{i}", "BadBoard", 8 if i == 0 else 2)   # 1/20 = 5%
    _add_scored(db, "s1", "TinyBoard", 9)                            # 1/1, tiny sample
    db.commit()

    rates = source_hit_rates(db, hit_score=7, min_sample=10)
    assert rates["GoodBoard"]["scored"] == 12
    assert rates["GoodBoard"]["hits"] == 6
    assert rates["GoodBoard"]["rate"] == pytest.approx(0.5)
    assert rates["GoodBoard"]["trusted"] is True
    assert rates["BadBoard"]["rate"] == pytest.approx(0.05)
    assert rates["BadBoard"]["trusted"] is True
    assert rates["TinyBoard"]["trusted"] is False
    # sorted by rate desc
    assert list(rates)[0] == "TinyBoard" or list(rates)[0] == "GoodBoard"


# ── scoring_queue ordering + sampling ──────────────────────────────────

def test_scoring_queue_orders_by_yield_and_samples_low(db):
    # history: GoodBoard 50%, BadBoard 5% (both trusted), NewBoard no history
    for i in range(12):
        _add_scored(db, f"h{i}", "GoodBoard", 8 if i < 6 else 3)
    for i in range(20):
        _add_scored(db, f"l{i}", "BadBoard", 8 if i == 0 else 2)
    db.commit()

    # pending rows (fit_score NULL) across the three sources
    pend = []
    for i in range(10):
        pend.append({"url": f"g{i}", "title": "Engineer", "location": "UK", "full_description": "x" * 300})
    for i in range(10):
        pend.append({"url": f"b{i}", "title": "Engineer", "location": "UK", "full_description": "x" * 300})
    for i in range(10):
        pend.append({"url": f"n{i}", "title": "Engineer", "location": "UK", "full_description": "x" * 300})
    store_jobs(db, pend[:10], site="GoodBoard", strategy="t")
    store_jobs(db, pend[10:20], site="BadBoard", strategy="t")
    store_jobs(db, pend[20:], site="NewBoard", strategy="t")

    q = scoring_queue(db, limit=0, cfg=CFG)

    good = [u for u in q if u.startswith("g")]
    new = [u for u in q if u.startswith("n")]
    bad = [u for u in q if u.startswith("b")]

    assert len(good) == 10                     # high-yield: all queued
    assert len(new) == 10                      # unknown: all queued
    assert 0 < len(bad) < 10                   # low-yield: sampled, not exhausted
    # high-yield sources come before unknown, which come before sampled low-yield
    assert q.index(good[-1]) < q.index(new[0])
    assert q.index(new[-1]) < q.index(bad[0])


def test_scoring_queue_excludes_prefiltered_and_respects_limit(db):
    pend = [
        {"url": "keep1", "title": "Engineer", "location": "UK", "full_description": "x" * 300},
        {"url": "keep2", "title": "Engineer", "location": "UK", "full_description": "x" * 300},
        {"url": "drop1", "title": "Senior Engineer", "location": "UK", "full_description": "x" * 300},
        {"url": "drop2", "title": "Engineer", "location": "New York, USA", "full_description": "x" * 300},
    ]
    store_jobs(db, pend, site="NewBoard", strategy="t")

    q = scoring_queue(db, limit=0, cfg=CFG)
    assert set(q) == {"keep1", "keep2"}
    assert len(scoring_queue(db, limit=1, cfg=CFG)) == 1


def test_refresh_prefilter_rewrites_reason(db, monkeypatch):
    # stored under the fixture CFG (strict direct_ats) -> "Remote" is filtered
    store_jobs(db, [
        {"url": "k", "title": "Engineer", "location": "Remote", "full_description": "x" * 300},
    ], site="B", strategy="direct_ats")
    assert dict(db.execute("SELECT url, prefilter_reason FROM jobs").fetchall())["k"].startswith("location:")

    # config changed to disabled -> refresh clears the marker
    monkeypatch.setattr("scoutpilot.config.load_prefilter_config",
                        lambda: {"prefilter": {"enabled": False}})
    res = refresh_prefilter(db)
    assert res["now_cleared"] == 1 and res["changed"] == 1
    assert dict(db.execute("SELECT url, prefilter_reason FROM jobs").fetchall())["k"] is None

    # config changed back -> refresh re-applies it
    monkeypatch.setattr("scoutpilot.config.load_prefilter_config", lambda: CFG)
    res = refresh_prefilter(db)
    assert res["now_filtered"] == 1
    assert dict(db.execute("SELECT url, prefilter_reason FROM jobs").fetchall())["k"].startswith("location:")


def test_scoring_queue_disabled_falls_back_to_recency(db):
    pend = [{"url": f"x{i}", "title": "Engineer", "location": "UK", "full_description": "y" * 300}
            for i in range(5)]
    store_jobs(db, pend, site="NewBoard", strategy="t")
    cfg = {**CFG, "scoring_queue": {**CFG["scoring_queue"], "enabled": False}}
    q = scoring_queue(db, limit=0, cfg=cfg)
    assert len(q) == 5
