# Graph Report - ApplyPilot-main  (2026-08-24)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 749 nodes · 1396 edges · 49 communities (45 shown, 4 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 48 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ce971753`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- _run_one_site
- workday.py
- tailor.py
- detail.py
- get_connection
- jobspy.py
- chrome.py
- prompt.py
- launcher.py
- _StageTracker
- main
- pdf.py
- LLMClient
- smartextract.py
- run_wizard
- config.py
- run_pipeline
- _bootstrap
- _parse_score_response
- cli.py
- ApplyPilot
- scoring/__init__.py
- applypilot
- ToolLeakGuard
- _bank
- FactBank
- cover_letter.py
- pipeline.py
- list_jobs
- _HTMLStripper
- _strip_preamble
- .load
- validator.py
- [0.2.0] - 2026-02-17
- run_job
- render_jobs
- NumericGuardViolation
- rules/graphify.md
- workflows/graphify.md
- scrape_detail_page
- view.py
- get_client
- get_tier
- _store_jobs_filtered
- judge_tailored_resume

## God Nodes (most connected - your core abstractions)
1. `get_connection()` - 46 edges
2. `FactBank` - 27 edges
3. `init_db()` - 21 edges
4. `tailor_resume()` - 19 edges
5. `_bank()` - 18 edges
6. `run_job()` - 17 edges
7. `NumericGuard` - 16 edges
8. `get_client()` - 16 edges
9. `generate_cover_letter()` - 16 edges
10. `main()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `TestToolLeakGuard` --uses--> `ToolLeakViolation`  [INFERRED]
  tests/test_cover_letter.py → src/applypilot/scoring/validator.py
- `TestNumericGuard` --uses--> `NumericGuardViolation`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py
- `TestFactBankLoad` --uses--> `FactBank`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py
- `TestToolLeakGuard` --uses--> `ToolLeakGuard`  [INFERRED]
  tests/test_cover_letter.py → src/applypilot/scoring/validator.py
- `TestNumericGuard` --uses--> `NumericGuard`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py

## Import Cycles
- None detected.

## Communities (49 total, 4 thin omitted)

### Community 0 - "_run_one_site"
Cohesion: 0.10
Nodes (24): ask_llm(), clean_page_html(), collect_page_intelligence(), execute_api_response(), execute_css_selectors(), execute_json_ld(), extract_json(), format_strategy_briefing() (+16 more)

### Community 1 - "workday.py"
Cohesion: 0.09
Nodes (30): fetch_details(), _fetch_one_detail(), load_employers(), _load_location_filter(), _location_ok(), _process_one(), Connection, Workday ATS direct API scraper: searches employer career portals. Scrapes… (+22 more)

### Community 2 - "tailor.py"
Cohesion: 0.10
Nodes (31): Split arbitrary CV/resume text into sections keyed by ALL-CAPS headers. Unlike…, split_sections(), assemble_resume_text(), _build_guard_scan_text(), _build_tailor_prompt(), extract_extra_sections(), extract_json(), _fallback_unquantified() (+23 more)

### Community 3 - "detail.py"
Cohesion: 0.12
Nodes (25): close_connection(), init_db(), Path, Close the cached connection for the current thread., Create the full jobs table with all columns from every pipeline stage. This is…, _load_base_urls(), Connection, Detail page enrichment: scrapes full descriptions and apply URLs. For each job… (+17 more)

### Community 4 - "get_connection"
Cohesion: 0.13
Nodes (25): apply_duplicate_marks(), attach_tool_result(), ensure_columns(), find_duplicate_groups(), get_connection(), get_jobs_by_stage(), get_stats(), _normalize_title() (+17 more)

### Community 5 - "jobspy.py"
Cohesion: 0.14
Nodes (20): _full_crawl(), _load_location_config(), _location_ok(), parse_proxy(), Connection, JobSpy-based job discovery: searches Indeed, LinkedIn, Glassdoor, ZipRecruiter.…, Store JobSpy DataFrame results into the DB. Returns (new, existing)., Run a single search query and store results in DB. (+12 more)

### Community 6 - "chrome.py"
Cohesion: 0.14
Nodes (21): Popen, cleanup_on_exit(), cleanup_worker(), kill_all_chrome(), _kill_on_port(), _kill_process_tree(), launch_chrome(), Path (+13 more)

### Community 7 - "prompt.py"
Cohesion: 0.14
Nodes (18): _build_captcha_section(), _build_hard_rules(), _build_location_check(), _build_profile_summary(), build_prompt(), _build_salary_section(), _build_screening_section(), Prompt builder for the autonomous job application agent. Constructs the full… (+10 more)

### Community 8 - "launcher.py"
Cohesion: 0.12
Nodes (23): Apply pipeline: Chrome management, prompt building, orchestration, and…, acquire_job(), _is_permanent_failure(), _load_blocked(), mark_job(), mark_result(), Apply orchestration: acquire jobs, spawn Claude Code sessions, track results.…, Record an attempt's outcome and mirror it onto the job. (+15 more)

### Community 9 - "_StageTracker"
Cohesion: 0.18
Nodes (7): Event, Thread-safe tracker for which stages have finished producing work., Run a single stage in streaming mode: loop until upstream done + no work. For…, Execute stages concurrently with DB as conveyor belt., _run_stage_streaming(), _run_streaming(), _StageTracker

### Community 10 - "main"
Cohesion: 0.13
Nodes (17): add_event(), get_state(), get_totals(), init_worker(), Rich live dashboard for the apply pipeline. Displays real-time worker status,…, Compute aggregate totals across all workers. Returns: Dict with keys: applied,…, Tracks the current state of the apply worker., Register the worker in the dashboard state. (+9 more)

### Community 11 - "pdf.py"
Cohesion: 0.11
Nodes (23): Stage: PDF conversion — convert tailored resumes and cover letters to PDF., _run_pdf(), batch_convert(), build_cover_letter_html(), build_html(), _cover_letter_font_faces(), _cv_font_faces(), _fit_resume_html() (+15 more)

### Community 12 - "LLMClient"
Cohesion: 0.13
Nodes (11): Response, _GeminiCompatForbidden, LLMClient, Exception, Call the native Gemini generateContent API. Used automatically when the OpenAI-…, Call the OpenAI-compatible endpoint. json_schema, when given, is passed as…, Call Ollama's native /api/chat with a JSON-schema `format`. Ollama's OpenAI-…, Send a chat completion request and return the assistant message text.… (+3 more)

### Community 13 - "smartextract.py"
Cohesion: 0.18
Nodes (15): load_search_config(), Load search configuration from ~/.applypilot/searches.yaml., build_scrape_targets(), clean_card_html(), _load_location_filter(), load_sites(), AI-powered smart extraction: discovers jobs from arbitrary websites. Two-phase…, Run smart extract on all targets. Sequential by default. When workers > 1,… (+7 more)

### Community 14 - "run_wizard"
Cohesion: 0.20
Nodes (13): ApplyPilot first-time setup wizard. Interactive flow that creates…, Generate a searches.yaml from user input., Ask about AI scoring/tailoring — optional LLM configuration., Configure autonomous job application (requires Claude Code CLI)., Run the full interactive setup wizard., Prompt for resume file and copy into APP_DIR., Walk through profile questions and return a nested profile dict., run_wizard() (+5 more)

### Community 15 - "config.py"
Cohesion: 0.19
Nodes (12): get_chrome_path(), get_chrome_user_data(), load_base_urls(), load_blocked_sso(), load_sites_config(), Path, ApplyPilot configuration: paths, platform detection, user data., Load sites.yaml configuration (sites list, manual_ats, blocked, etc.). (+4 more)

### Community 16 - "run_pipeline"
Cohesion: 0.18
Nodes (12): Group, Build the Rich table showing all worker statuses. Returns: A Rich Table object…, Render the dashboard table plus the recent events panel. Returns: A Rich Group…, render_dashboard(), render_full(), Resolve 'all' and validate/order stage names., Execute stages one at a time (original behavior)., Run pipeline stages. Args: stages: List of stage names, or None / ["all"] for… (+4 more)

### Community 17 - "_bootstrap"
Cohesion: 0.15
Nodes (17): command, apply(), _bootstrap(), events(), jobs(), logs(), Run pipeline stages: discover, enrich, score, tailor, cover, pdf., Launch auto-apply to submit job applications. (+9 more)

### Community 18 - "_parse_score_response"
Cohesion: 0.14
Nodes (12): _build_candidate_level(), _clean_optional_field(), _parse_score_response(), Parse the LLM's score response into structured data. Args: response: Raw LLM…, Score a single job against the resume. Args: resume_text: The candidate's full…, Format the candidate's experience level for the scoring prompt. Scoring is done…, Strip a captured field and map a literal 'NULL' response to None. The scoring…, score_job() (+4 more)

### Community 19 - "cli.py"
Cohesion: 0.17
Nodes (9): callback, Reset all failed jobs so they can be retried. Returns: Number of jobs reset., reset_failed(), init(), main(), ApplyPilot CLI — the main entry point., ApplyPilot — AI-powered end-to-end job application pipeline., Run the first-time setup wizard (profile, resume, search config). (+1 more)

### Community 20 - "ApplyPilot"
Cohesion: 0.05
Nodes (39): Adding New Career Sites, Adding New Workday Employers, Bug Fixes and Features, Clone and Install, Code Style Guidelines, Contributing to ApplyPilot, Development Setup, How to Contribute (+31 more)

### Community 26 - "ToolLeakGuard"
Cohesion: 0.09
Nodes (21): _company_tokens(), Lowercase word tokens from the job's company name. This codebase already treats…, Deterministic check: a tool/tech token in the job description but absent from…, Raise ToolLeakViolation if a job-description tool the candidate doesn't have…, ToolLeakGuard, _bank(), _CleanClient, _FabricatingClient (+13 more)

### Community 27 - "_bank"
Cohesion: 0.09
Nodes (23): NumericGuard, Deterministic, post-generation check: every number in the assembled resume text…, Raise NumericGuardViolation if any line contains a number that isn't in the…, _bank(), _embedded_fact(), _FakeClient, _kraydel_multiparty_fact(), _qualitative_fact() (+15 more)

### Community 28 - "FactBank"
Cohesion: 0.12
Nodes (16): _extract_numbers(), Fact, FactBank, Verified-fact bank for resume tailoring. facts.yaml (repo root) is the ONLY…, Deterministic keyword extraction from a fact's free-text `use_when`.…, Parses facts.yaml and is the sole gate on what quantified claims the tailoring…, All tier == 'verified' facts. The ONLY facts ever exposed to the LLM., Unverified entries pending a real value, for a CLI prompt flow. (+8 more)

### Community 29 - "cover_letter.py"
Cohesion: 0.16
Nodes (15): load_profile(), Load user profile from ~/.applypilot/profile.json., check_listing_still_open(), Best-effort check for whether a job listing is still accepting applications,…, Stage: Cover letter generation., _run_cover(), _preflight_pdf_converter(), Smoke-test the PDF pipeline once per batch, before any LLM calls. Exercises the… (+7 more)

### Community 30 - "pipeline.py"
Cohesion: 0.19
Nodes (15): end_run(), Record the start of one pipeline stage invocation. Args: conn: Database…, Record the end of a pipeline stage invocation. Args: conn: Database connection.…, start_run(), _count_pending(), ApplyPilot Pipeline Orchestrator. Runs pipeline stages in sequence or…, Stage: Detail enrichment — scrape full descriptions and apply URLs., Stage: LLM scoring — assign fit scores 1-10. (+7 more)

### Community 31 - "list_jobs"
Cohesion: 0.21
Nodes (7): list_jobs(), Fetch scored jobs for terminal display, filtered and sorted by fit. Args:…, fixture, Tests for terminal_view.list_jobs / render_jobs (the `applypilot jobs` command)., Isolated scratch DB with a few jobs at different fit scores/sites, never…, scratch_db(), TestListJobs

### Community 32 - "_HTMLStripper"
Cohesion: 0.20
Nodes (5): HTMLParser, _HTMLStripper, Convert HTML to plain text., Strip HTML tags, keep text content., strip_html()

### Community 33 - "_strip_preamble"
Cohesion: 0.21
Nodes (7): Remove LLM preamble before 'Dear Hiring Manager,' if present. Gemini and other…, Truncate anything after the sign-off line. Models occasionally add notes/P.S.…, _strip_after_signoff(), _strip_preamble(), An incidental earlier mention of the name must not truncate the real body that…, endeared'/'dearest' mid-preamble must not be mistaken for the letter's real…, TestStripHelpers

### Community 34 - ".load"
Cohesion: 0.27
Nodes (6): FactBankLoadError, Path, Parse facts.yaml into Facts, validating every verified fact's numbers against…, Raised when facts.yaml fails integrity checks at load time., A verified fact whose declared number isn't backed by its own evidence string…, TestFactBankLoad

### Community 35 - "validator.py"
Cohesion: 0.16
Nodes (12): _build_skills_set(), find_fabricated_numbers(), Exception, Resume and cover letter validation: banned words, fabrication detection,…, Build the set of allowed skills from the profile's skills_boundary., Validate individual JSON fields from an LLM-generated tailored resume. Args:…, Programmatic validation of a tailored resume against the user's profile. Args:…, Raised by ToolLeakGuard when a job-description tool the candidate doesn't have… (+4 more)

### Community 36 - "[0.2.0] - 2026-02-17"
Cohesion: 0.25
Nodes (7): [0.1.0] - 2026-02-17, [0.2.0] - 2026-02-17, Added, Added, Changed, Changelog, Fixed

### Community 37 - "run_job"
Cohesion: 0.14
Nodes (15): _check_playwright_mcp(), gen_prompt(), _make_mcp_config(), Path, Generate a prompt file and print the Claude CLI command for manual debugging.…, Inspect a system/init stream-json event for playwright MCP health. Browser…, Spawn a Claude Code session for one job application. Returns: Tuple of…, Build MCP config dict for a specific CDP port. (+7 more)

### Community 38 - "render_jobs"
Cohesion: 0.47
Nodes (4): Console, Render one Rich panel per job with fit score, company context, tailored…, render_jobs(), TestRenderJobs

### Community 39 - "NumericGuardViolation"
Cohesion: 0.29
Nodes (5): FactBankError, NumericGuardViolation, Exception, Base class for fact-bank problems., Raised by NumericGuard when the assembled resume text contains a number that…

### Community 43 - "scrape_detail_page"
Cohesion: 0.12
Nodes (18): clean_content_html(), clean_description(), collect_detail_intelligence(), extract_apply_url_deterministic(), extract_description_deterministic(), extract_from_json_ld(), extract_main_content(), extract_with_llm() (+10 more)

### Community 44 - "view.py"
Cohesion: 0.24
Nodes (9): dashboard(), Open the HTML dashboard in your browser. Serves it live by default (regenerates…, generate_dashboard(), open_dashboard(), ApplyPilot HTML Dashboard Generator. Generates an interactive, self-contained…, Generate an HTML dashboard of all jobs with fit scores, tailored assets, and…, Generate a static dashboard snapshot and open it in the default browser -- a…, Serve the dashboard over a local HTTP server, regenerating fresh from the DB on… (+1 more)

### Community 45 - "get_client"
Cohesion: 0.14
Nodes (18): get_locale_style(), Infer document terminology and layout conventions from the candidate's country.…, _detect_provider(), get_client(), Unified LLM client for ApplyPilot. Auto-detects provider from environment:…, Return (base_url, model, api_key) based on environment variables. Reads env at…, Return (or create) the module-level LLMClient singleton., _build_cover_letter_prompt() (+10 more)

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
- **37 isolated node(s):** `Adding New Career Sites`, `Adding New Workday Employers`, `Bug Fixes and Features`, `Clone and Install`, `Code Style Guidelines` (+32 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_connection()` connect `get_connection` to `workday.py`, `tailor.py`, `detail.py`, `run_job`, `jobspy.py`, `launcher.py`, `main`, `view.py`, `smartextract.py`, `get_client`, `_bootstrap`, `cli.py`, `cover_letter.py`, `pipeline.py`, `list_jobs`?**
  _High betweenness centrality (0.220) - this node is a cross-community bridge._
- **Why does `FactBank` connect `FactBank` to `tailor.py`, `.load`, `NumericGuardViolation`, `get_client`, `judge_tailored_resume`, `ToolLeakGuard`, `_bank`, `cover_letter.py`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Why does `get_client()` connect `get_client` to `_run_one_site`, `tailor.py`, `detail.py`, `get_connection`, `scrape_detail_page`, `LLMClient`, `smartextract.py`, `judge_tailored_resume`, `_parse_score_response`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `FactBank` (e.g. with `generate_cover_letter()` and `run_cover_letters()`) actually correct?**
  _`FactBank` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `tailor_resume()` (e.g. with `FactBank` and `NumericGuardViolation`) actually correct?**
  _`tailor_resume()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Adding New Career Sites`, `Adding New Workday Employers`, `Bug Fixes and Features` to the rest of the system?**
  _37 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `_run_one_site` be split into smaller, more focused modules?**
  _Cohesion score 0.10144927536231885 - nodes in this community are weakly interconnected._