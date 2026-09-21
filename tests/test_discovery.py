"""Comprehensive tests for multi-channel discovery harvesters and opportunity classification."""

import json
import sqlite3
import pytest
from unittest.mock import patch, MagicMock

from scoutpilot.database import init_db, store_jobs, ensure_columns, get_connection
from scoutpilot.discovery.direct_ats import (
    infer_opportunity_type,
    fetch_greenhouse_jobs,
    fetch_ashby_jobs,
    fetch_lever_jobs,
    fetch_smartrecruiters_jobs,
    fetch_pinpoint_jobs,
    fetch_personio_jobs,
    fetch_teamtailor_jobs,
    run_direct_ats_discovery,
)
from scoutpilot.discovery.hacker_news import (
    parse_hn_comment,
    _clean_hn_html,
    run_hn_discovery,
)
from scoutpilot.discovery.remote_boards import (
    fetch_remote_com_jobs,
    fetch_weworkremotely_jobs,
)
from scoutpilot.discovery.schemes_and_training import (
    parse_github_jobs_markdown,
    run_schemes_discovery,
)
from scoutpilot.discovery.dorking import (
    _clean_ddg_url,
    search_duckduckgo,
    run_dorking_discovery,
)
from scoutpilot.pipeline import _run_discover


# ── Opportunity Type Inference Tests ────────────────────────────────────────

def test_infer_opportunity_type_graduate():
    assert infer_opportunity_type("Technology Graduate Scheme 2026") == "graduate_scheme"
    assert infer_opportunity_type("Graduate Software Engineer") == "graduate_scheme"
    assert infer_opportunity_type("Early Career Software Developer") == "graduate_scheme"
    assert infer_opportunity_type("Junior Software Engineer", "Rotational tech graduate program") == "graduate_scheme"


def test_infer_opportunity_type_funded_training():
    assert infer_opportunity_type("Skills Bootcamp in Software Development") == "funded_training"
    assert infer_opportunity_type("Funded Cloud Computing Bootcamp") == "funded_training"
    assert infer_opportunity_type("AI Engineering Residency") == "funded_training"


def test_infer_opportunity_type_internship():
    assert infer_opportunity_type("Software Engineering Intern Summer 2026") == "internship"
    assert infer_opportunity_type("Software Placement Student") == "internship"


def test_infer_opportunity_type_direct_job():
    assert infer_opportunity_type("Backend Engineer (Python / FastAPI)") == "direct_job"
    assert infer_opportunity_type("Full Stack Developer") == "direct_job"


# ── Direct ATS Harvester Tests ──────────────────────────────────────────────

def test_fetch_greenhouse_jobs_mocked():
    sample_gh_response = {
        "jobs": [
            {
                "id": 12345,
                "title": "Graduate Software Engineer",
                "absolute_url": "https://boards.greenhouse.io/kainos/jobs/12345",
                "location": {"name": "Belfast, UK"},
                "content": "<p>Exciting graduate technology scheme in Belfast.</p>",
                "updated_at": "2026-08-26T12:00:00Z",
            },
            {
                "id": 12346,
                "title": "Senior Staff Architect",
                "absolute_url": "https://boards.greenhouse.io/kainos/jobs/12346",
                "location": {"name": "London, UK"},
                "content": "<p>Senior architecture leadership role.</p>",
                "updated_at": "2026-08-26T12:00:00Z",
            },
        ]
    }

    with patch("scoutpilot.discovery.direct_ats._http_get_json", return_value=sample_gh_response):
        jobs = fetch_greenhouse_jobs("kainos", "Kainos")
        assert len(jobs) == 2
        assert jobs[0]["title"] == "Graduate Software Engineer"
        assert jobs[0]["company"] == "Kainos"
        assert jobs[0]["location"] == "Belfast, UK"
        assert jobs[0]["opportunity_type"] == "graduate_scheme"
        assert jobs[0]["channel"] == "direct_ats"
        assert jobs[0]["application_url"] == "https://boards.greenhouse.io/kainos/jobs/12345"


def test_fetch_ashby_jobs_mocked():
    sample_ashby_response = {
        "jobPostings": [
            {
                "id": "ashby-1",
                "title": "Junior Backend Engineer",
                "jobUrl": "https://jobs.ashbyhq.com/openai/ashby-1",
                "locationName": "Remote",
                "isRemote": True,
                "descriptionPlain": "Build backend pipelines with Python and FastAPI.",
            }
        ]
    }

    with patch("scoutpilot.discovery.direct_ats._http_get_json", return_value=sample_ashby_response):
        jobs = fetch_ashby_jobs("openai", "OpenAI")
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Junior Backend Engineer"
        assert jobs[0]["company"] == "OpenAI"
        assert "Remote" in jobs[0]["location"]
        assert jobs[0]["opportunity_type"] == "direct_job"


def test_fetch_lever_jobs_mocked():
    sample_lever_response = [
        {
            "id": "lever-1",
            "text": "Software Engineering Trainee",
            "hostedUrl": "https://jobs.lever.co/spotify/lever-1",
            "categories": {"location": "London, UK"},
            "descriptionPlain": "Early career software engineering opportunity.",
        }
    ]

    with patch("scoutpilot.discovery.direct_ats._http_get_json", return_value=sample_lever_response):
        jobs = fetch_lever_jobs("spotify", "Spotify")
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Software Engineering Trainee"
        assert jobs[0]["opportunity_type"] == "graduate_scheme"


def test_fetch_smartrecruiters_jobs_mocked():
    # Shape confirmed live 2026-09-21 against
    # api.smartrecruiters.com/v1/companies/smartrecruiters/postings
    sample_response = {
        "totalFound": 1,
        "content": [
            {
                "id": "744000148454651",
                "name": "Graduate Software Engineer",
                "location": {"city": "London", "country": "uk"},
            }
        ],
    }
    with patch("scoutpilot.discovery.direct_ats._http_get_json", return_value=sample_response):
        jobs = fetch_smartrecruiters_jobs("acme", "Acme")
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Graduate Software Engineer"
        assert jobs[0]["company"] == "Acme"
        assert jobs[0]["url"] == "https://jobs.smartrecruiters.com/acme/744000148454651"
        assert jobs[0]["opportunity_type"] == "graduate_scheme"
        assert "full_description" not in jobs[0]   # shallow row -- enrichment fills it in


def test_fetch_pinpoint_jobs_mocked():
    # Shape confirmed live 2026-09-21 against cazoo.pinpointhq.com/postings.json
    sample_response = {
        "data": [
            {
                "title": "Junior Backend Engineer",
                "url": "https://cazoo.pinpointhq.com/en/postings/abc123",
                "description": "Build backend services with Python.",
                "location": {"name": "London"},
                "workplace_type_text": "Remote",
                "deadline_at": "2026-12-01",
            }
        ]
    }
    with patch("scoutpilot.discovery.direct_ats._http_get_json", return_value=sample_response):
        jobs = fetch_pinpoint_jobs("cazoo", "Cazoo")
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Junior Backend Engineer"
        assert jobs[0]["company"] == "Cazoo"
        assert "Remote" in jobs[0]["location"]
        assert jobs[0]["full_description"] == "Build backend services with Python."
        assert jobs[0]["deadline"] == "2026-12-01"


def test_fetch_personio_jobs_mocked():
    # Schema confirmed live 2026-09-21 against personio.jobs.personio.de/xml
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<workzag-jobs>
<position>
    <id>1834171</id>
    <office>Munich</office>
    <name>Graduate Software Engineer</name>
    <jobDescriptions>Build data pipelines.</jobDescriptions>
    <yourProfile>Python experience.</yourProfile>
    <whatWeOffer>Great benefits.</whatWeOffer>
</position>
</workzag-jobs>"""
    with patch("scoutpilot.discovery.direct_ats._http_get_text", return_value=sample_xml):
        jobs = fetch_personio_jobs("acme", "Acme")
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Graduate Software Engineer"
        assert jobs[0]["company"] == "Acme"
        assert jobs[0]["location"] == "Munich"
        assert jobs[0]["url"] == "https://acme.jobs.personio.de/job/1834171"
        assert "Build data pipelines." in jobs[0]["full_description"]
        assert jobs[0]["opportunity_type"] == "graduate_scheme"

    with patch("scoutpilot.discovery.direct_ats._http_get_text", return_value=None):
        assert fetch_personio_jobs("dead-board") == []


def test_fetch_teamtailor_jobs_mocked():
    # JSON Feed shape (jsonfeed.org) confirmed live 2026-09-21 against
    # storytel.teamtailor.com/jobs.json
    sample_response = {
        "version": "https://jsonfeed.org/version/1",
        "title": "Acme",
        "items": [
            {
                "title": "Senior Data Engineer",
                "url": "https://acme.teamtailor.com/jobs/123-senior-data-engineer",
                "summary": "Own the data platform.",
            }
        ],
    }
    with patch("scoutpilot.discovery.direct_ats._http_get_json", return_value=sample_response):
        jobs = fetch_teamtailor_jobs("acme", "Acme")
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Senior Data Engineer"
        assert jobs[0]["full_description"] == "Own the data platform."


# ── Remote Boards Harvester Tests ───────────────────────────────────────────

def test_fetch_remote_com_jobs_mocked():
    # Row shape confirmed live 2026-09-21 against remote.com/jobs/all?page=1
    page1_html = (
        'href="/jobs/acme-c1/junior-software-engineer-j1"><span>Junior Software Engineer</span>'
        '</a><span>Acme</span>'
        'href="/jobs/acme-c1/sales-manager-j2"><span>Sales Manager</span></a><span>Acme</span>'
    )
    with patch("scoutpilot.discovery.remote_boards._http_get_text", side_effect=[page1_html, None]):
        jobs = fetch_remote_com_jobs(pages=3)
        assert len(jobs) == 1   # Sales Manager filtered out by is_relevant_tech_role
        assert jobs[0]["title"] == "Junior Software Engineer"
        assert jobs[0]["company"] == "Acme"
        assert jobs[0]["url"] == "https://remote.com/jobs/acme-c1/junior-software-engineer-j1"
        assert "full_description" not in jobs[0]   # shallow row -- enrichment fills it in


def test_fetch_remote_com_jobs_dedupes_and_stops_on_empty_page():
    page1_html = 'href="/jobs/acme-c1/junior-software-engineer-j1"><span>Junior Software Engineer</span></a><span>Acme</span>'
    with patch("scoutpilot.discovery.remote_boards._http_get_text", side_effect=[page1_html, page1_html, ""]):
        jobs = fetch_remote_com_jobs(pages=5)
        assert len(jobs) == 1   # same URL on "page 2" -> deduped, then empty page stops the loop


def test_fetch_weworkremotely_jobs_mocked():
    # Item shape confirmed live 2026-09-21 against
    # weworkremotely.com/categories/remote-back-end-programming-jobs.rss
    sample_rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<item>
  <title>Acme: Junior Backend Engineer</title>
  <link>https://weworkremotely.com/remote-jobs/acme-junior-backend-engineer</link>
  <region>Anywhere in the World</region>
  <description>&lt;p&gt;Build backend services with Python.&lt;/p&gt;</description>
</item>
<item>
  <title>Acme: Sales Manager</title>
  <link>https://weworkremotely.com/remote-jobs/acme-sales-manager</link>
  <region>USA Only</region>
  <description>&lt;p&gt;Own the sales pipeline.&lt;/p&gt;</description>
</item>
</channel></rss>"""
    with patch("scoutpilot.discovery.remote_boards._http_get_text", return_value=sample_rss):
        jobs = fetch_weworkremotely_jobs(categories=["remote-back-end-programming-jobs"])
        assert len(jobs) == 1   # Sales Manager filtered out by is_relevant_tech_role
        assert jobs[0]["title"] == "Junior Backend Engineer"
        assert jobs[0]["company"] == "Acme"
        assert jobs[0]["location"] == "Anywhere in the World (Remote)"
        assert "Build backend services with Python." in jobs[0]["full_description"]


# ── Hacker News Harvester Tests ─────────────────────────────────────────────

def test_clean_hn_html():
    raw = "Stripe | Software Engineer | Belfast / Remote | ONSITE / REMOTE<p>Join us to build global economic infrastructure.</p>"
    clean = _clean_hn_html(raw)
    assert "<p>" not in clean
    assert "Stripe | Software Engineer | Belfast / Remote" in clean


def test_parse_hn_comment():
    item = {
        "id": 99901,
        "text": "Kraydel | Junior Python Engineer | Belfast, UK | REMOTE | https://kraydel.com/careers<p>Looking for a junior Python engineer to work on IoT and healthcare systems. Contact: jobs@kraydel.com</p>",
    }
    parsed = parse_hn_comment(item, story_id=99900)
    assert parsed is not None
    assert parsed["company"] == "Kraydel"
    assert parsed["title"] == "Junior Python Engineer"
    assert "Belfast" in parsed["location"]
    assert parsed["channel"] == "hacker_news"
    assert "https://kraydel.com/careers" in parsed["application_url"] or "mailto:jobs@kraydel.com" in parsed["application_url"]


# ── Schemes & Funded Training Tests ─────────────────────────────────────────

def test_parse_github_jobs_markdown():
    md = """
| Company | Role | Location | Application/Link | Date |
| --- | --- | --- | --- | --- |
| [Kainos](https://kainos.com) | [Graduate Software Engineer](https://boards.greenhouse.io/kainos/jobs/101) | Belfast, UK | [Apply](https://boards.greenhouse.io/kainos/jobs/101) | Aug 26 |
| Allstate | Associate Engineer | Derry, UK | https://allstate.com/jobs/202 | Aug 25 |
    """
    jobs = parse_github_jobs_markdown(md, source_name="Test GitHub Repo")
    assert len(jobs) == 2
    assert jobs[0]["company"] == "Kainos"
    assert jobs[0]["title"] == "Graduate Software Engineer"
    assert jobs[0]["url"] == "https://boards.greenhouse.io/kainos/jobs/101"
    assert jobs[0]["opportunity_type"] == "graduate_scheme"


def test_run_schemes_discovery(tmp_path):
    db_file = tmp_path / "test_schemes.db"
    with patch("scoutpilot.database.DB_PATH", db_file):
        init_db(db_file)
        res = run_schemes_discovery()
        assert res["total_found"] > 0
        assert res["new"] > 0

        conn = sqlite3.connect(str(db_file))
        rows = conn.execute("SELECT title, company, opportunity_type, funding_status FROM jobs").fetchall()
        assert len(rows) > 0
        opp_types = {r[2] for r in rows}
        assert "graduate_scheme" in opp_types or "funded_training" in opp_types
        conn.close()


# ── Search Operator (Dorking) Tests ─────────────────────────────────────────

def test_clean_ddg_url():
    ddg_link = "/l/?uddg=https%3A%2F%2Fboards.greenhouse.io%2Fkainos%2Fjobs%2F123&rut=abc"
    assert _clean_ddg_url(ddg_link) == "https://boards.greenhouse.io/kainos/jobs/123"


def test_run_dorking_discovery(tmp_path):
    db_file = tmp_path / "test_dorking.db"
    fake_hits = [
        {
            "url": "https://boards.greenhouse.io/monzo/jobs/991",
            "title": "Graduate Backend Engineer",
            "snippet": "Monzo is looking for Graduate Backend Engineers in the UK. Remote available.",
        }
    ]

    with patch("scoutpilot.database.DB_PATH", db_file), \
         patch("scoutpilot.discovery.dorking.search_duckduckgo", return_value=fake_hits):
        init_db(db_file)
        res = run_dorking_discovery(queries=["site:boards.greenhouse.io graduate software"])
        assert res["total_found"] == 1
        assert res["new"] == 1

        conn = sqlite3.connect(str(db_file))
        row = conn.execute("SELECT title, company, site, channel, opportunity_type FROM jobs WHERE url = ?", ("https://boards.greenhouse.io/monzo/jobs/991",)).fetchone()
        assert row is not None
        assert row[0] == "Graduate Backend Engineer"
        assert row[1] == "Monzo"
        assert row[3] == "dorking"
        assert row[4] == "graduate_scheme"
        conn.close()


# ── Database Schema Migration & Opportunity Storage Tests ──────────────────

def test_database_opportunity_columns(tmp_path):
    db_file = tmp_path / "test_migration.db"
    conn = init_db(db_file)

    cols = {row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    assert "opportunity_type" in cols
    assert "deadline" in cols
    assert "funding_status" in cols
    assert "cohort_start" in cols
    assert "channel" in cols
    assert "company" in cols

    job_data = [{
        "url": "https://example.com/grad-scheme-1",
        "title": "Graduate Cloud Engineer",
        "company": "Kainos",
        "salary": "£32,000",
        "description": "Graduate cloud engineering program in Belfast.",
        "location": "Belfast, Northern Ireland",
        "opportunity_type": "graduate_scheme",
        "funding_status": "standard_salary",
        "deadline": "2026-11-30",
        "cohort_start": "2026-09-01",
        "channel": "direct_ats",
        "full_description": "Full description of graduate cloud role. " * 10,
        "application_url": "https://example.com/grad-scheme-1/apply",
    }]

    new_count, existing_count = store_jobs(conn, job_data, site="Direct ATS", strategy="direct_ats")
    assert new_count == 1
    assert existing_count == 0

    row = conn.execute(
        "SELECT title, company, location, opportunity_type, funding_status, deadline, cohort_start, channel, full_description, application_url, detail_scraped_at "
        "FROM jobs WHERE url = ?",
        ("https://example.com/grad-scheme-1",)
    ).fetchone()

    assert row[0] == "Graduate Cloud Engineer"
    assert row[1] == "Kainos"
    assert row[2] == "Belfast, Northern Ireland"
    assert row[3] == "graduate_scheme"
    assert row[4] == "standard_salary"
    assert row[5] == "2026-11-30"
    assert row[6] == "2026-09-01"
    assert row[7] == "direct_ats"
    assert row[8] == job_data[0]["full_description"]
    assert row[9] == "https://example.com/grad-scheme-1/apply"
    assert row[10] is not None  # Auto-populated detail_scraped_at
    conn.close()
