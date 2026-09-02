"""ScoutPilot discovery engines: JobSpy, Workday, SmartExtract, Direct ATS, Hacker News, Schemes & Training, and Search Operators."""

from scoutpilot.discovery.direct_ats import run_direct_ats_discovery
from scoutpilot.discovery.dorking import run_dorking_discovery
from scoutpilot.discovery.hacker_news import run_hn_discovery
from scoutpilot.discovery.jobspy import run_discovery
from scoutpilot.discovery.schemes_and_training import run_schemes_discovery
from scoutpilot.discovery.smartextract import run_smart_extract
from scoutpilot.discovery.workday import run_workday_discovery

__all__ = [
    "run_discovery",
    "run_workday_discovery",
    "run_smart_extract",
    "run_direct_ats_discovery",
    "run_hn_discovery",
    "run_schemes_discovery",
    "run_dorking_discovery",
]
