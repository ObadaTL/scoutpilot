# Graph Report - ApplyPilot-main  (2026-08-24)

## Corpus Check
- 41 files · ~66,382 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 768 nodes · 1434 edges · 45 communities (40 shown, 5 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 49 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6b1bff79`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- smartextract.py
- workday.py
- tailor.py
- detail.py
- get_connection
- jobspy.py
- chrome.py
- prompt.py
- launcher.py
- _StageTracker
- dashboard.py
- pdf.py
- LLMClient
- load_search_config
- run_wizard
- config.py
- _bootstrap
- _parse_score_response
- cli.py
- ApplyPilot
- scoring/__init__.py
- applypilot
- ToolLeakGuard
- _bank
- FactBank
- run_tailoring
- pipeline.py
- list_jobs
- _strip_preamble
- .load
- cover_letter.py
- [0.2.0] - 2026-02-17
- run_job
- render_jobs
- NumericGuardViolation
- rules/graphify.md
- workflows/graphify.md
- get_client
- get_tier
- _store_jobs_filtered
- judge_tailored_resume

## God Nodes (most connected - your core abstractions)
1. `get_connection()` - 46 edges
2. `FactBank` - 30 edges
3. `init_db()` - 21 edges
4. `tailor_resume()` - 20 edges
5. `_bank()` - 18 edges
6. `run_job()` - 17 edges
7. `generate_cover_letter()` - 17 edges
8. `NumericGuard` - 16 edges
9. `get_client()` - 16 edges
10. `main()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `TestNumericGuard` --uses--> `NumericGuardViolation`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py
- `TestFactBankLoad` --uses--> `FactBank`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py
- `TestFactBankLoad` --uses--> `FactBankLoadError`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py
- `_multiparty_fact()` --calls--> `Fact`  [EXTRACTED]
  tests/test_cover_letter.py → src/applypilot/facts.py
- `_embedded_fact()` --calls--> `Fact`  [EXTRACTED]
  tests/test_facts.py → src/applypilot/facts.py

## Import Cycles
- None detected.

## Communities (45 total, 5 thin omitted)

### Community 0 - "smartextract.py"
Cohesion: 0.11
Nodes (29): ask_llm(), clean_card_html(), clean_page_html(), collect_page_intelligence(), execute_api_response(), execute_css_selectors(), execute_json_ld(), extract_json() (+21 more)

### Community 1 - "workday.py"
Cohesion: 0.07
Nodes (35): HTMLParser, fetch_details(), _fetch_one_detail(), _HTMLStripper, load_employers(), _load_location_filter(), _location_ok(), _process_one() (+27 more)

### Community 2 - "tailor.py"
Cohesion: 0.08
Nodes (37): Split arbitrary CV/resume text into sections keyed by ALL-CAPS headers. Unlike…, split_sections(), _apply_canonical_entries(), assemble_resume_text(), _build_guard_scan_text(), _build_tailor_prompt(), _bullet_text(), _bullets_similar() (+29 more)

### Community 3 - "detail.py"
Cohesion: 0.08
Nodes (40): init_db(), Create the full jobs table with all columns from every pipeline stage. This is…, clean_content_html(), clean_description(), collect_detail_intelligence(), extract_apply_url_deterministic(), extract_description_deterministic(), extract_from_json_ld() (+32 more)

### Community 4 - "get_connection"
Cohesion: 0.09
Nodes (32): apply_duplicate_marks(), attach_tool_result(), close_connection(), ensure_columns(), find_duplicate_groups(), get_connection(), get_jobs_by_stage(), get_stats() (+24 more)

### Community 5 - "jobspy.py"
Cohesion: 0.14
Nodes (20): _full_crawl(), _load_location_config(), _location_ok(), parse_proxy(), Connection, JobSpy-based job discovery: searches Indeed, LinkedIn, Glassdoor, ZipRecruiter.…, Store JobSpy DataFrame results into the DB. Returns (new, existing)., Run a single search query and store results in DB. (+12 more)

### Community 6 - "chrome.py"
Cohesion: 0.13
Nodes (22): Popen, cleanup_on_exit(), cleanup_worker(), kill_all_chrome(), _kill_on_port(), _kill_process_tree(), launch_chrome(), Path (+14 more)

### Community 7 - "prompt.py"
Cohesion: 0.15
Nodes (19): _build_captcha_section(), _build_hard_rules(), _build_location_check(), _build_profile_summary(), build_prompt(), _build_salary_section(), _build_screening_section(), Prompt builder for the autonomous job application agent. Constructs the full… (+11 more)

### Community 8 - "launcher.py"
Cohesion: 0.12
Nodes (23): Apply pipeline: Chrome management, prompt building, orchestration, and…, acquire_job(), _is_permanent_failure(), _load_blocked(), mark_job(), mark_result(), Apply orchestration: acquire jobs, spawn Claude Code sessions, track results.…, Record an attempt's outcome and mirror it onto the job. (+15 more)

### Community 10 - "dashboard.py"
Cohesion: 0.16
Nodes (15): Group, get_state(), get_totals(), init_worker(), Rich live dashboard for the apply pipeline. Displays real-time worker status,…, Build the Rich table showing all worker statuses. Returns: A Rich Table object…, Render the dashboard table plus the recent events panel. Returns: A Rich Group…, Compute aggregate totals across all workers. Returns: Dict with keys: applied,… (+7 more)

### Community 11 - "pdf.py"
Cohesion: 0.10
Nodes (28): Stage: PDF conversion — convert tailored resumes and cover letters to PDF., _run_pdf(), batch_convert(), build_cover_letter_html(), build_html(), convert_to_pdf(), _cover_letter_font_faces(), _cv_font_faces() (+20 more)

### Community 12 - "LLMClient"
Cohesion: 0.13
Nodes (11): Response, _GeminiCompatForbidden, LLMClient, Exception, Thin LLM client supporting OpenAI-compatible and native Gemini endpoints. For…, Call the native Gemini generateContent API. Used automatically when the OpenAI-…, Call the OpenAI-compatible endpoint. json_schema, when given, is passed as…, Call Ollama's native /api/chat, optionally with a JSON-schema `format`.… (+3 more)

### Community 13 - "load_search_config"
Cohesion: 0.27
Nodes (10): load_search_config(), Load search configuration from ~/.applypilot/searches.yaml., build_scrape_targets(), _load_location_filter(), load_sites(), Main entry point for AI-powered smart extraction. Loads sites from…, Load location accept/reject lists from search config., Load scraping target sites from config/sites.yaml. (+2 more)

### Community 14 - "run_wizard"
Cohesion: 0.20
Nodes (13): ApplyPilot first-time setup wizard. Interactive flow that creates…, Generate a searches.yaml from user input., Ask about AI scoring/tailoring — optional LLM configuration., Configure autonomous job application (requires Claude Code CLI)., Run the full interactive setup wizard., Prompt for resume file and copy into APP_DIR., Walk through profile questions and return a nested profile dict., run_wizard() (+5 more)

### Community 15 - "config.py"
Cohesion: 0.19
Nodes (12): get_chrome_path(), get_chrome_user_data(), load_base_urls(), load_blocked_sso(), load_sites_config(), Path, ApplyPilot configuration: paths, platform detection, user data., Load sites.yaml configuration (sites list, manual_ats, blocked, etc.). (+4 more)

### Community 17 - "_bootstrap"
Cohesion: 0.15
Nodes (17): command, apply(), _bootstrap(), events(), jobs(), logs(), Run pipeline stages: discover, enrich, score, tailor, cover, pdf., Launch auto-apply to submit job applications. (+9 more)

### Community 18 - "_parse_score_response"
Cohesion: 0.19
Nodes (8): _clean_optional_field(), _parse_score_response(), Parse the LLM's score response into structured data. Args: response: Raw LLM…, Strip a captured field and map a literal 'NULL' response to None. The scoring…, Tests for the company_summary/company_hook capture added to fit scoring., REASONING used to be a greedy capture-to-end-of-string -- once…, Older-style responses (or a model that ignores the new fields) must not crash…, TestParseScoreResponse

### Community 19 - "cli.py"
Cohesion: 0.13
Nodes (13): callback, Reset all failed jobs so they can be retried. Returns: Number of jobs reset., reset_failed(), dashboard(), init(), main(), ApplyPilot CLI — the main entry point., Open the HTML dashboard in your browser. Serves it live by default (regenerates… (+5 more)

### Community 20 - "ApplyPilot"
Cohesion: 0.05
Nodes (39): Adding New Career Sites, Adding New Workday Employers, Bug Fixes and Features, Clone and Install, Code Style Guidelines, Contributing to ApplyPilot, Development Setup, How to Contribute (+31 more)

### Community 26 - "ToolLeakGuard"
Cohesion: 0.08
Nodes (24): _company_tokens(), Exception, Raised by ToolLeakGuard when a job-description tool the candidate doesn't have…, Lowercase word tokens from the job's company name. This codebase already treats…, Deterministic check: a tool/tech token in the job description but absent from…, Raise ToolLeakViolation if a job-description tool the candidate doesn't have…, ToolLeakGuard, ToolLeakViolation (+16 more)

### Community 27 - "_bank"
Cohesion: 0.09
Nodes (23): NumericGuard, Deterministic, post-generation check: every number in the assembled resume text…, Raise NumericGuardViolation if any line contains a number that isn't in the…, _bank(), _embedded_fact(), _FakeClient, _kraydel_multiparty_fact(), _qualitative_fact() (+15 more)

### Community 28 - "FactBank"
Cohesion: 0.10
Nodes (19): _extract_numbers(), Fact, FactBank, Verified-fact bank for resume tailoring. facts.yaml (repo root) is the ONLY…, Recursively pull every integer token out of a nested structure. Used to fold…, Deterministic keyword extraction from a fact's free-text `use_when`.…, Parses facts.yaml and is the sole gate on what quantified claims the tailoring…, Best-effort recovery for a plain-string bullet that has a digit but is actually… (+11 more)

### Community 29 - "run_tailoring"
Cohesion: 0.17
Nodes (12): load_profile(), Load user profile from ~/.applypilot/profile.json., check_listing_still_open(), Best-effort check for whether a job listing is still accepting applications,…, Stage: Cover letter generation., _run_cover(), _preflight_pdf_converter(), Smoke-test the PDF pipeline once per batch, before any LLM calls. Exercises the… (+4 more)

### Community 30 - "pipeline.py"
Cohesion: 0.10
Nodes (30): Event, main(), Launch the apply pipeline. Args: limit: Max jobs to apply to (0 or with…, ensure_dirs(), Create all required directories., end_run(), Record the start of one pipeline stage invocation. Args: conn: Database…, Record the end of a pipeline stage invocation. Args: conn: Database connection.… (+22 more)

### Community 31 - "list_jobs"
Cohesion: 0.39
Nodes (3): list_jobs(), Fetch scored jobs for terminal display, filtered and sorted by fit. Args:…, TestListJobs

### Community 33 - "_strip_preamble"
Cohesion: 0.21
Nodes (7): Remove LLM preamble before 'Dear Hiring Manager,' if present. Gemini and other…, Truncate anything after the sign-off line. Models occasionally add notes/P.S.…, _strip_after_signoff(), _strip_preamble(), An incidental earlier mention of the name must not truncate the real body that…, endeared'/'dearest' mid-preamble must not be mistaken for the letter's real…, TestStripHelpers

### Community 34 - ".load"
Cohesion: 0.27
Nodes (6): FactBankLoadError, Path, Parse facts.yaml into Facts, validating every verified fact's numbers against…, Raised when facts.yaml fails integrity checks at load time., A verified fact whose declared number isn't backed by its own evidence string…, TestFactBankLoad

### Community 35 - "cover_letter.py"
Cohesion: 0.11
Nodes (24): _build_cover_letter_prompt(), _check_company_mentioned(), generate_cover_letter(), Cover letter generation: LLM-powered, profile-driven, with validation.…, Proactively swap any sentence carrying a digit for the matching verified fact's…, A cover letter that never names the company it's addressed to reads as…, Generate a cover letter with fresh context on each retry + auto-sanitize. Same…, Build the cover letter system prompt from the user's profile. All personal… (+16 more)

### Community 36 - "[0.2.0] - 2026-02-17"
Cohesion: 0.25
Nodes (7): [0.1.0] - 2026-02-17, [0.2.0] - 2026-02-17, Added, Added, Changed, Changelog, Fixed

### Community 37 - "run_job"
Cohesion: 0.11
Nodes (19): add_event(), Update the worker's state fields. Args: worker_id: Which worker to update.…, Add a timestamped event to the scrolling event log. Args: msg: Rich markup…, update_state(), _check_playwright_mcp(), gen_prompt(), _make_mcp_config(), Path (+11 more)

### Community 38 - "render_jobs"
Cohesion: 0.22
Nodes (8): Console, Render one Rich panel per job with fit score, company context, tailored…, render_jobs(), fixture, Tests for terminal_view.list_jobs / render_jobs (the `applypilot jobs` command)., Isolated scratch DB with a few jobs at different fit scores/sites, never…, scratch_db(), TestRenderJobs

### Community 39 - "NumericGuardViolation"
Cohesion: 0.29
Nodes (5): FactBankError, NumericGuardViolation, Exception, Base class for fact-bank problems., Raised by NumericGuard when the assembled resume text contains a number that…

### Community 45 - "get_client"
Cohesion: 0.19
Nodes (12): _detect_provider(), get_client(), is_local_provider(), Unified LLM client for ApplyPilot. Auto-detects provider from environment:…, True when generation will hit a local (non-cloud) LLM_URL endpoint. Mirrors…, Return (base_url, model, api_key) based on environment variables. Reads env at…, Return (or create) the module-level LLMClient singleton., _build_candidate_level() (+4 more)

### Community 46 - "get_tier"
Cohesion: 0.40
Nodes (6): doctor(), Check your setup and diagnose missing requirements., get_tier(), load_env(), Load environment variables from ~/.applypilot/.env if it exists., Detect the current tier based on available dependencies. Tier 1 (Discovery):…

### Community 47 - "_store_jobs_filtered"
Cohesion: 0.40
Nodes (5): _location_ok(), Connection, Check if a job location passes the user's location filter., Store jobs with location filtering. Returns (new, existing)., _store_jobs_filtered()

### Community 48 - "judge_tailored_resume"
Cohesion: 0.50
Nodes (4): _build_judge_prompt(), judge_tailored_resume(), Build the LLM judge prompt from the user's profile. The judge only ever sees…, LLM judge layer: catches subtle fabrication that programmatic checks miss.…

## Knowledge Gaps
- **37 isolated node(s):** `applypilot`, `graphify`, `Workflow: graphify`, `Added`, `Fixed` (+32 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_connection()` connect `get_connection` to `smartextract.py`, `workday.py`, `tailor.py`, `detail.py`, `cover_letter.py`, `run_job`, `jobspy.py`, `launcher.py`, `get_client`, `_bootstrap`, `cli.py`, `run_tailoring`, `pipeline.py`, `list_jobs`?**
  _High betweenness centrality (0.208) - this node is a cross-community bridge._
- **Why does `FactBank` connect `FactBank` to `tailor.py`, `.load`, `cover_letter.py`, `NumericGuardViolation`, `judge_tailored_resume`, `ToolLeakGuard`, `_bank`, `run_tailoring`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Why does `get_client()` connect `get_client` to `smartextract.py`, `tailor.py`, `cover_letter.py`, `detail.py`, `LLMClient`, `judge_tailored_resume`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `FactBank` (e.g. with `generate_cover_letter()` and `_recover_numeric_sentences()`) actually correct?**
  _`FactBank` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `tailor_resume()` (e.g. with `FactBank` and `NumericGuardViolation`) actually correct?**
  _`tailor_resume()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `applypilot`, `graphify`, `Workflow: graphify` to the rest of the system?**
  _37 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `smartextract.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10574712643678161 - nodes in this community are weakly interconnected._