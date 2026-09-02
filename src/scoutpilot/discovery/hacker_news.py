"""Hacker News 'Who is Hiring?' Harvester.

Fetches the latest monthly 'Ask HN: Who is hiring?' thread via the official
Hacker News / Algolia public APIs. Parses company names, roles, locations, remote status,
and direct founder/engineering contact links.
"""

import html
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import urllib.request

from scoutpilot.database import get_connection, init_db, store_jobs
from scoutpilot.discovery.direct_ats import infer_opportunity_type, is_relevant_tech_role

log = logging.getLogger(__name__)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

_EMAIL_RE = re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")
_URL_RE = re.compile(r'https?://[^\s<>"\']+')
_TAG_RE = re.compile(r"<[^>]+>")


def _clean_hn_html(raw_html: str) -> str:
    """Clean HTML from HN comments to readable text."""
    if not raw_html:
        return ""
    text = html.unescape(raw_html)
    text = text.replace("<p>", "\n\n").replace("<br>", "\n")
    text = _TAG_RE.sub("", text)
    return text.strip()


def _get_json(url: str, timeout: int = 12) -> dict | list | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = response.read().decode("utf-8", errors="replace")
                return json.loads(data)
    except Exception as e:
        log.debug("HN API GET failed for %s: %s", url, e)
    return None


def find_latest_who_is_hiring_story() -> dict | None:
    """Find the most recent 'Ask HN: Who is hiring?' story item."""
    # Try Algolia search first (fastest, structured)
    algolia_url = "https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&query=Who%20is%20hiring"
    data = _get_json(algolia_url)
    if data and isinstance(data, dict) and data.get("hits"):
        for hit in data["hits"]:
            title = hit.get("title", "")
            if "Who is hiring?" in title:
                return {
                    "id": hit.get("objectID") or hit.get("story_id"),
                    "title": title,
                    "created_at": hit.get("created_at"),
                }

    # Fallback to Firebase API user profile
    user_data = _get_json("https://hacker-news.firebaseio.com/v0/user/whoishiring.json")
    if user_data and isinstance(user_data, dict):
        submitted = user_data.get("submitted", [])
        for item_id in submitted[:10]:
            item = _get_json(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json")
            if item and "Who is hiring?" in item.get("title", ""):
                return item
    return None


def fetch_comment_item(item_id: int | str) -> dict | None:
    """Fetch a single HN comment item."""
    url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
    return _get_json(url)


def parse_hn_comment(item: dict, story_id: str | int) -> dict | None:
    """Parse a top-level HN comment into a structured job dictionary."""
    if not item or item.get("deleted") or item.get("dead"):
        return None

    raw_text = item.get("text", "")
    if not raw_text or len(raw_text) < 30:
        return None

    clean_text = _clean_hn_html(raw_text)
    lines = [line.strip() for line in clean_text.split("\n") if line.strip()]
    if not lines:
        return None

    header = lines[0]
    parts = [p.strip() for p in header.split("|")]

    company = parts[0] if len(parts) >= 1 else "Hacker News Employer"
    title = parts[1] if len(parts) >= 2 else "Software Engineer"
    location = parts[2] if len(parts) >= 3 else "Remote / Unspecified"

    if not is_relevant_tech_role(title, clean_text):
        return None

    # Additional location hints in the header
    is_remote = any("remote" in p.lower() for p in parts) or "remote" in clean_text.lower()
    if is_remote and "remote" not in location.lower():
        location = f"{location} (Remote)"

    # Extract apply link or contact email
    urls = _URL_RE.findall(clean_text)
    emails = _EMAIL_RE.findall(clean_text)

    item_id = item.get("id")
    hn_item_url = f"https://news.ycombinator.com/item?id={item_id}"
    apply_url = urls[0] if urls else (f"mailto:{emails[0]}" if emails else hn_item_url)

    opp_type = infer_opportunity_type(title, clean_text)

    return {
        "url": hn_item_url,
        "title": title[:120],
        "company": company[:80],
        "location": location[:100],
        "description": f"HN Who is Hiring: {company} - {title}. Contact: {apply_url}",
        "full_description": clean_text,
        "application_url": apply_url,
        "site": "Hacker News",
        "opportunity_type": opp_type,
        "channel": "hacker_news",
        "deadline": None,
        "funding_status": "standard_salary",
    }


def run_hn_discovery(max_comments: int = 150, workers: int = 4) -> dict:
    """Discover jobs from the latest Hacker News 'Who is Hiring?' thread.

    Args:
        max_comments: Number of top-level comments to inspect.
        workers: Thread pool workers.

    Returns:
        Dict with total_found, new_stored, existing_stored, errors.
    """
    story = find_latest_who_is_hiring_story()
    if not story:
        log.warning("Could not locate active 'Ask HN: Who is hiring?' story.")
        return {"total_found": 0, "new": 0, "existing": 0, "errors": 1}

    story_id = story.get("id")
    log.info("Found HN Story: %s (ID: %s)", story.get("title"), story_id)

    # Fetch full story details to get comment IDs if not already present
    story_details = _get_json(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
    comment_ids = (story_details or {}).get("kids", [])[:max_comments]

    if not comment_ids:
        log.info("No comments found in story %s", story_id)
        return {"total_found": 0, "new": 0, "existing": 0, "errors": 0}

    conn = init_db()
    jobs = []
    total_errors = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_comment_item, cid): cid for cid in comment_ids}
        for future in as_completed(futures):
            try:
                item = future.result()
                if item:
                    parsed = parse_hn_comment(item, story_id)
                    if parsed:
                        jobs.append(parsed)
            except Exception as e:
                log.debug("Error fetching HN comment: %s", e)
                total_errors += 1

    total_found = len(jobs)
    total_new = 0
    total_existing = 0

    if jobs:
        total_new, total_existing = store_jobs(conn, jobs, site="Hacker News", strategy="hn_api")

    log.info(
        "HN Discovery complete: %d parsed -> %d new, %d existing in DB",
        total_found, total_new, total_existing,
    )

    return {
        "total_found": total_found,
        "new": total_new,
        "existing": total_existing,
        "errors": total_errors,
    }
