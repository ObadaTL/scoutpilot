"""ApplyPilot configuration: paths, platform detection, user data."""

import os
import platform
import re
import shutil
from pathlib import Path

# User data directory — all user-specific files live here
APP_DIR = Path(os.environ.get("APPLYPILOT_DIR", Path.home() / ".applypilot"))

# Core paths
DB_PATH = APP_DIR / "applypilot.db"
PROFILE_PATH = APP_DIR / "profile.json"
RESUME_PATH = APP_DIR / "resume.txt"
RESUME_PDF_PATH = APP_DIR / "resume.pdf"
SEARCH_CONFIG_PATH = APP_DIR / "searches.yaml"
ENV_PATH = APP_DIR / ".env"

# Generated output
TAILORED_DIR = APP_DIR / "tailored_resumes"
COVER_LETTER_DIR = APP_DIR / "cover_letters"
LOG_DIR = APP_DIR / "logs"

# Chrome worker isolation
CHROME_WORKER_DIR = APP_DIR / "chrome-workers"
APPLY_WORKER_DIR = APP_DIR / "apply-workers"

# Package-shipped config (YAML registries)
PACKAGE_DIR = Path(__file__).parent
CONFIG_DIR = PACKAGE_DIR / "config"


def get_chrome_path() -> str:
    """Auto-detect Chrome/Chromium executable path, cross-platform.

    Override with CHROME_PATH environment variable.
    """
    env_path = os.environ.get("CHROME_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    system = platform.system()

    if system == "Windows":
        candidates = [
            Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
        ]
    elif system == "Darwin":
        candidates = [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        ]
    else:  # Linux
        candidates = []
        for name in ("google-chrome", "google-chrome-stable", "chromium-browser", "chromium"):
            found = shutil.which(name)
            if found:
                candidates.append(Path(found))

    for c in candidates:
        if c and c.exists():
            return str(c)

    # Fall back to PATH search
    for name in ("google-chrome", "google-chrome-stable", "chromium-browser", "chromium", "chrome"):
        found = shutil.which(name)
        if found:
            return found

    raise FileNotFoundError(
        "Chrome/Chromium not found. Install Chrome or set CHROME_PATH environment variable."
    )


def get_chrome_user_data() -> Path:
    """Default Chrome user data directory, cross-platform."""
    system = platform.system()
    if system == "Windows":
        return Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data"
    elif system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    else:
        return Path.home() / ".config" / "google-chrome"


def ensure_dirs():
    """Create all required directories."""
    for d in [APP_DIR, TAILORED_DIR, COVER_LETTER_DIR, LOG_DIR, CHROME_WORKER_DIR, APPLY_WORKER_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def load_profile() -> dict:
    """Load user profile from ~/.applypilot/profile.json."""
    import json
    if not PROFILE_PATH.exists():
        raise FileNotFoundError(
            f"Profile not found at {PROFILE_PATH}. Run `applypilot init` first."
        )
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))

    # A profile with no name at all breaks downstream consumers in confusing
    # ways (e.g. prompt.py's _build_profile_summary does personal["full_name"]
    # with no fallback) -- fail here, at the shared load point, with a clear
    # message instead of a KeyError several modules away.
    personal = profile.get("personal", {})
    sign_off_name = (personal.get("preferred_name") or personal.get("full_name", "")).strip()
    if not sign_off_name:
        raise ValueError(
            f"Profile at {PROFILE_PATH} has no 'personal.full_name' or "
            "'personal.preferred_name' -- there's no name to sign a cover "
            "letter or build a resume header with. Fill one in and try again."
        )

    return profile


def get_profile_keywords(profile: dict | None = None) -> list[str]:
    """Extract full list of technical skills, domains, and role keywords from candidate profile."""
    if profile is None:
        try:
            profile = load_profile()
        except Exception:
            profile = {}

    keywords = set()

    # 1. Skills Boundary
    skills_b = profile.get("skills_boundary", {})
    if isinstance(skills_b, dict):
        for category, items in skills_b.items():
            if isinstance(items, list):
                for item in items:
                    if item and isinstance(item, str):
                        keywords.add(item.strip())
            elif isinstance(items, str):
                keywords.add(items.strip())

    # 2. Target Role & Experience
    exp = profile.get("experience", {})
    if isinstance(exp, dict):
        target = exp.get("target_role", "")
        if target:
            # Extract key role phrases
            for chunk in re.split(r"[,/|;]|\bor\b|\band\b", target, flags=re.IGNORECASE):
                cleaned = chunk.strip()
                if cleaned and len(cleaned) > 2:
                    keywords.add(cleaned)

    # 3. Canonical resume facts tech terms
    rf = profile.get("resume_facts", {})
    if isinstance(rf, dict):
        can = rf.get("canonical_entries", {})
        if isinstance(can, dict):
            for section in ("experience", "projects"):
                for entry in can.get(section, []):
                    sub = entry.get("subtitle", "")
                    if "|" in sub:
                        tech_part = sub.split("|")[0]
                        for t in tech_part.split(","):
                            if t.strip():
                                keywords.add(t.strip())

    # Common canonical variations
    keywords.update([
        "Python", "AI", "Machine Learning", "Signal Processing", "DSP",
        "Software Engineer", "Backend", "Full Stack", "Data", "Cloud", "AWS",
        "Graduate", "Junior", "Java", "Kotlin", "Embedded", "IoT",
    ])

    return sorted(list(keywords), key=lambda x: -len(x))


# ---------------------------------------------------------------------------
# Locale-driven CV/resume conventions
# ---------------------------------------------------------------------------

_US_COUNTRIES = {"united states", "usa", "us", "u.s.", "u.s.a.", "america"}

_CURRENCY_SYMBOLS = {"USD": "$", "GBP": "£", "EUR": "€", "CAD": "$", "AUD": "$", "NZD": "$"}


def get_locale_style(profile: dict) -> dict:
    """Infer document terminology and layout conventions from the candidate's country.

    Most English-speaking hiring markets outside the US call it a CV, expect
    2 pages, and use British spelling. The US (and largely Canada) calls it a
    resume and expects 1 page. Everything downstream -- LLM prompts, PDF page
    size -- reads from this instead of assuming the US default.
    """
    country = profile.get("personal", {}).get("country", "").strip().lower()
    if country in _US_COUNTRIES:
        return {"doc_name": "resume", "pages": 1, "spelling": "American", "page_size": "Letter"}
    return {"doc_name": "CV", "pages": 2, "spelling": "British", "page_size": "A4"}


def get_currency_symbol(currency_code: str) -> str:
    """Best-effort currency symbol for a 3-letter code; falls back to the code itself."""
    return _CURRENCY_SYMBOLS.get(currency_code, "")


def load_search_config() -> dict:
    """Load search configuration from ~/.applypilot/searches.yaml."""
    import yaml
    if not SEARCH_CONFIG_PATH.exists():
        # Fall back to package-shipped example
        example = CONFIG_DIR / "searches.example.yaml"
        if example.exists():
            return yaml.safe_load(example.read_text(encoding="utf-8"))
        return {}
    return yaml.safe_load(SEARCH_CONFIG_PATH.read_text(encoding="utf-8"))


def load_sites_config() -> dict:
    """Load sites.yaml configuration (sites list, manual_ats, blocked, etc.)."""
    import yaml
    path = CONFIG_DIR / "sites.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_ats_employers() -> dict:
    """Load Direct ATS employers from config/ats_employers.yaml."""
    import yaml
    path = CONFIG_DIR / "ats_employers.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("employers", {})


def load_schemes_config() -> dict:
    """Load Graduate Schemes & Funded Training config from config/schemes.yaml."""
    import yaml
    path = CONFIG_DIR / "schemes.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("schemes", {})


def is_manual_ats(url: str | None) -> bool:
    """Check if a URL routes through an ATS that requires manual application."""
    if not url:
        return False
    sites_cfg = load_sites_config()
    domains = sites_cfg.get("manual_ats", [])
    url_lower = url.lower()
    return any(domain in url_lower for domain in domains)


def load_location_focus() -> dict | None:
    """Load the optional `location_focus` section from searches.yaml.

    A temporary, reversible way to work through one specific regional job
    search without touching any existing DB rows or discovery config: when
    present and enabled, the tailor/apply job-selection queries (see
    database.get_jobs_by_stage, apply.launcher.acquire_job) filter to only
    jobs whose location matches one of the listed priority tiers, ordering
    results by tier (tier 0 first) then fit_score. Absent or
    `enabled: false` -> those queries behave exactly as before this feature
    existed.

    Expected shape in searches.yaml:
        location_focus:
          enabled: true
          priority:
            - ["Belfast"]
            - ["Northern Ireland", "Antrim", "Down", ...]
            - ["Remote"]

    Returns:
        The focus dict ({"enabled": True, "priority": [...]})  if enabled
        with at least one tier, else None.
    """
    cfg = load_search_config()
    focus = cfg.get("location_focus")
    if not focus or not focus.get("enabled") or not focus.get("priority"):
        return None
    return focus


def load_blocked_sites() -> tuple[set[str], list[str]]:
    """Load blocked sites and URL patterns from sites.yaml.

    Returns:
        (blocked_site_names, blocked_url_patterns)
    """
    cfg = load_sites_config()
    blocked = cfg.get("blocked", {})
    sites = set(blocked.get("sites", []))
    patterns = blocked.get("url_patterns", [])
    return sites, patterns


def load_blocked_sso() -> list[str]:
    """Load blocked SSO domains from sites.yaml."""
    cfg = load_sites_config()
    return cfg.get("blocked_sso", [])


def load_base_urls() -> dict[str, str | None]:
    """Load site base URLs for URL resolution from sites.yaml."""
    cfg = load_sites_config()
    return cfg.get("base_urls", {})


# ---------------------------------------------------------------------------
# Default values — referenced across modules instead of magic numbers
# ---------------------------------------------------------------------------

DEFAULTS = {
    "min_score": 7,
    "max_apply_attempts": 3,
    # Cross-run attempt budget per job before it's excluded from further
    # tailor/cover-letter runs. Each single run already retries internally
    # (see tailor.py's own max_retries), so this only governs how many
    # separate `applypilot run tailor`/`run cover` invocations a job gets
    # across sessions. Lowered from 5 -> 3 (2026-08-23): live testing showed
    # tailoring failures are dominated by the LLM not following the
    # requested JSON schema, not transient issues -- repeating a
    # structurally-hard job 5x across runs rarely helps beyond what 3
    # already captures, and the extra 2 attempts were mostly wasted compute
    # on jobs that were never going to succeed.
    "max_tailor_attempts": 3,
    "max_cover_attempts": 3,
    "poll_interval": 60,
    "apply_timeout": 300,
    "viewport": "1280x900",
}


def load_env():
    """Load environment variables from ~/.applypilot/.env if it exists."""
    from dotenv import load_dotenv
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)
    # Also try CWD .env as fallback
    load_dotenv()


# ---------------------------------------------------------------------------
# Tier system — feature gating by installed dependencies
# ---------------------------------------------------------------------------

TIER_LABELS = {
    1: "Discovery",
    2: "AI Scoring & Tailoring",
    3: "Full Auto-Apply",
}

TIER_COMMANDS: dict[int, list[str]] = {
    1: ["init", "run discover", "run enrich", "status", "dashboard"],
    2: ["run score", "run tailor", "run cover", "run pdf", "run"],
    3: ["apply"],
}


def get_tier() -> int:
    """Detect the current tier based on available dependencies.

    Tier 1 (Discovery):            Python + pip
    Tier 2 (AI Scoring & Tailoring): + LLM API key
    Tier 3 (Full Auto-Apply):       + Claude Code CLI + Chrome
    """
    load_env()

    has_llm = any(os.environ.get(k) for k in ("GEMINI_API_KEY", "OPENAI_API_KEY", "LLM_URL"))
    if not has_llm:
        return 1

    has_claude = shutil.which("claude") is not None
    try:
        get_chrome_path()
        has_chrome = True
    except FileNotFoundError:
        has_chrome = False

    if has_claude and has_chrome:
        return 3

    return 2


def check_tier(required: int, feature: str) -> None:
    """Raise SystemExit with a clear message if the current tier is too low.

    Args:
        required: Minimum tier needed (1, 2, or 3).
        feature: Human-readable description of the feature being gated.
    """
    current = get_tier()
    if current >= required:
        return

    from rich.console import Console
    _console = Console(stderr=True)

    missing: list[str] = []
    if required >= 2 and not any(os.environ.get(k) for k in ("GEMINI_API_KEY", "OPENAI_API_KEY", "LLM_URL")):
        missing.append("LLM API key — run [bold]applypilot init[/bold] or set GEMINI_API_KEY")
    if required >= 3:
        if not shutil.which("claude"):
            missing.append("Claude Code CLI — install from [bold]https://claude.ai/code[/bold]")
        try:
            get_chrome_path()
        except FileNotFoundError:
            missing.append("Chrome/Chromium — install or set CHROME_PATH")

    _console.print(
        f"\n[red]'{feature}' requires {TIER_LABELS.get(required, f'Tier {required}')} (Tier {required}).[/red]\n"
        f"Current tier: {TIER_LABELS.get(current, f'Tier {current}')} (Tier {current})."
    )
    if missing:
        _console.print("\n[yellow]Missing:[/yellow]")
        for m in missing:
            _console.print(f"  - {m}")
    _console.print()
    raise SystemExit(1)
