"""Tests for the HTTP-first (tier 0) detail-page path in enrichment/detail.py."""

from scoutpilot.enrichment import detail

JOB_LD = """
<html><head><title>Software Engineer | Enisca Browne</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"JobPosting","title":"Software Engineer",
 "description":"<p>We are hiring a software engineer to build things. """ + ("x" * 80) + """</p>",
 "hiringOrganization":{"@type":"Organization","name":"Enisca Browne"},
 "url":"https://www.nijobs.com/job/software-engineer/enisca-browne-job1"}
</script></head><body>...</body></html>
"""

NO_LD = "<html><head><title>Nope</title></head><body><p>no structured data here</p></body></html>"


def test_intel_from_html_parses_json_ld():
    intel = detail._intel_from_html(JOB_LD, "https://x/final")
    assert intel["final_url"] == "https://x/final"
    assert "Enisca Browne" in intel["page_title"]
    assert len(intel["json_ld"]) == 1
    assert intel["json_ld"][0]["@type"] == "JobPosting"


def test_http_first_detail_uses_json_ld(monkeypatch):
    monkeypatch.setattr(detail, "_http_fetch_html", lambda url, timeout=30.0: (JOB_LD, url))
    res = detail._http_first_detail("https://www.nijobs.com/job/x-job1")
    assert res is not None
    assert res["tier_used"] == 0
    assert res["status"] in ("ok", "partial")
    assert "software engineer" in res["full_description"].lower()


def test_http_first_detail_none_without_json_ld(monkeypatch):
    monkeypatch.setattr(detail, "_http_fetch_html", lambda url, timeout=30.0: (NO_LD, url))
    assert detail._http_first_detail("https://example.com/job") is None


def test_http_first_detail_none_on_fetch_failure(monkeypatch):
    monkeypatch.setattr(detail, "_http_fetch_html", lambda url, timeout=30.0: None)
    assert detail._http_first_detail("https://example.com/job") is None


def test_scrape_detail_page_short_circuits_on_http_first(monkeypatch):
    """When tier 0 succeeds, page.goto is never called."""
    monkeypatch.setattr(detail, "_http_fetch_html", lambda url, timeout=30.0: (JOB_LD, url))

    class _BoomPage:
        def goto(self, *a, **k):
            raise AssertionError("browser should not be used when tier 0 succeeds")

    res = detail.scrape_detail_page(_BoomPage(), "https://www.nijobs.com/job/x-job1")
    assert res["tier_used"] == 0
    assert "elapsed" in res
