"""ApplyPilot discovery engines: JobSpy, Workday, SmartExtract, Direct ATS, Hacker News, Schemes & Training, and Search Operators."""

from applypilot.discovery.direct_ats import run_direct_ats_discovery
from applypilot.discovery.dorking import run_dorking_discovery
from applypilot.discovery.hacker_news import run_hn_discovery
from applypilot.discovery.jobspy import run_discovery
from applypilot.discovery.schemes_and_training import run_schemes_discovery
from applypilot.discovery.smartextract import run_smart_extract
from applypilot.discovery.workday import run_workday_discovery

__all__ = [
    "run_discovery",
    "run_workday_discovery",
    "run_smart_extract",
    "run_direct_ats_discovery",
    "run_hn_discovery",
    "run_schemes_discovery",
    "run_dorking_discovery",
]
