# Graph Report - ApplyPilot-main  (2026-08-25)

## Corpus Check
- 41 files · ~72,024 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 804 nodes · 1527 edges · 44 communities (39 shown, 5 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 53 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `427e7bca`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- smartextract.py
- workday.py
- tailor_resume
- detail.py
- get_connection
- init_db
- chrome.py
- prompt.py
- launcher.py
- _StageTracker
- dashboard.py
- pdf.py
- LLMClient
- validator.py
- run_wizard
- tailor.py
- sanitize_text
- cli.py
- _parse_score_response
- main
- ApplyPilot
- scoring/__init__.py
- applypilot
- ToolLeakGuard
- _bank
- FactBank
- view.py
- pipeline.py
- main
- mark_job
- _strip_preamble
- run_pipeline
- cover_letter.py
- [0.2.0] - 2026-02-17
- run_job
- list_jobs
- get_locale_style
- rules/graphify.md
- workflows/graphify.md
- get_client

## God Nodes (most connected - your core abstractions)
1. `get_connection()` - 51 edges
2. `FactBank` - 34 edges
3. `init_db()` - 21 edges
4. `tailor_resume()` - 20 edges
5. `generate_cover_letter()` - 19 edges
6. `_bank()` - 18 edges
7. `run_job()` - 17 edges
8. `NumericGuard` - 16 edges
9. `get_client()` - 16 edges
10. `main()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `TestNumericGuard` --uses--> `NumericGuardViolation`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py
- `TestToolLeakGuard` --uses--> `ToolLeakViolation`  [INFERRED]
  tests/test_cover_letter.py → src/applypilot/scoring/validator.py
- `TestFactBankLoad` --uses--> `FactBankLoadError`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py
- `_multiparty_fact()` --calls--> `Fact`  [EXTRACTED]
  tests/test_cover_letter.py → src/applypilot/facts.py
- `_embedded_fact()` --calls--> `Fact`  [EXTRACTED]
  tests/test_facts.py → src/applypilot/facts.py

## Import Cycles
- None detected.

## Communities (44 total, 5 thin omitted)

### Community 0 - "smartextract.py"
Cohesion: 0.08
Nodes (38): ask_llm(), build_scrape_targets(), clean_card_html(), clean_page_html(), collect_page_intelligence(), execute_api_response(), execute_css_selectors(), execute_json_ld() (+30 more)

### Community 1 - "workday.py"
Cohesion: 0.07
Nodes (35): HTMLParser, fetch_details(), _fetch_one_detail(), _HTMLStripper, load_employers(), _load_location_filter(), _location_ok(), _process_one() (+27 more)

### Community 2 - "tailor_resume"
Cohesion: 0.15
Nodes (16): NumericGuardViolation, Raised by NumericGuard when the assembled resume text contains a number that…, _build_guard_scan_text(), extract_json(), Build, assemble, and re-verify the unquantified fallback. Called only after…, Absolute last resort: remove every digit from every LLM-authored field (title,…, JSON Schema for the tailor prompt's expected output shape. Passed as…, Robustly extract JSON from LLM response (handles fences, preamble). Args: raw:… (+8 more)

### Community 3 - "detail.py"
Cohesion: 0.08
Nodes (38): parse_proxy(), Parse host:port:user:pass into components., clean_content_html(), clean_description(), collect_detail_intelligence(), extract_apply_url_deterministic(), extract_description_deterministic(), extract_from_json_ld() (+30 more)

### Community 4 - "get_connection"
Cohesion: 0.09
Nodes (34): apply_duplicate_marks(), close_connection(), ensure_columns(), find_duplicate_groups(), get_connection(), get_jobs_by_stage(), log_event(), _normalize_title() (+26 more)

### Community 5 - "init_db"
Cohesion: 0.14
Nodes (20): init_db(), Create the full jobs table with all columns from every pipeline stage. This is…, _full_crawl(), _load_location_config(), _location_ok(), Connection, JobSpy-based job discovery: searches Indeed, LinkedIn, Glassdoor, ZipRecruiter.…, Store JobSpy DataFrame results into the DB. Returns (new, existing). (+12 more)

### Community 6 - "chrome.py"
Cohesion: 0.13
Nodes (17): Popen, cleanup_worker(), launch_chrome(), Path, Chrome lifecycle management for apply workers. Handles launching an isolated…, Create an isolated Chrome profile for a worker. On first run, clones from an…, Clear Chrome's 'restore pages' nag by fixing Preferences. Chrome writes…, Launch a Chrome instance with remote debugging for a worker. Args: worker_id:… (+9 more)

### Community 7 - "prompt.py"
Cohesion: 0.15
Nodes (19): _build_captcha_section(), _build_hard_rules(), _build_location_check(), _build_profile_summary(), build_prompt(), _build_salary_section(), _build_screening_section(), Prompt builder for the autonomous job application agent. Constructs the full… (+11 more)

### Community 8 - "launcher.py"
Cohesion: 0.13
Nodes (20): Apply pipeline: Chrome management, prompt building, orchestration, and…, acquire_job(), _load_blocked(), Apply orchestration: acquire jobs, spawn Claude Code sessions, track results.…, Atomically acquire the next job to apply to and open an attempt for it. Args:…, is_manual_ats(), load_base_urls(), load_blocked_sites() (+12 more)

### Community 10 - "dashboard.py"
Cohesion: 0.16
Nodes (14): Group, get_state(), get_totals(), init_worker(), Rich live dashboard for the apply pipeline. Displays real-time worker status,…, Build the Rich table showing all worker statuses. Returns: A Rich Table object…, Render the dashboard table plus the recent events panel. Returns: A Rich Group…, Compute aggregate totals across all workers. Returns: Dict with keys: applied,… (+6 more)

### Community 11 - "pdf.py"
Cohesion: 0.10
Nodes (28): Stage: PDF conversion — convert tailored resumes and cover letters to PDF., _run_pdf(), batch_convert(), build_cover_letter_html(), build_html(), convert_to_pdf(), _cover_letter_font_faces(), _cv_font_faces() (+20 more)

### Community 12 - "LLMClient"
Cohesion: 0.13
Nodes (11): Response, _GeminiCompatForbidden, LLMClient, Exception, Thin LLM client supporting OpenAI-compatible and native Gemini endpoints. For…, Call the native Gemini generateContent API. Used automatically when the OpenAI-…, Call the OpenAI-compatible endpoint. json_schema, when given, is passed as…, Call Ollama's native /api/chat, optionally with a JSON-schema `format`.… (+3 more)

### Community 13 - "validator.py"
Cohesion: 0.16
Nodes (12): _build_skills_set(), find_fabricated_numbers(), Exception, Resume and cover letter validation: banned words, fabrication detection,…, Build the set of allowed skills from the profile's skills_boundary., Validate individual JSON fields from an LLM-generated tailored resume. Args:…, Programmatic validation of a tailored resume against the user's profile. Args:…, Raised by ToolLeakGuard when a job-description tool the candidate doesn't have… (+4 more)

### Community 14 - "run_wizard"
Cohesion: 0.15
Nodes (17): init(), Run the first-time setup wizard (profile, resume, search config)., ensure_dirs(), Create all required directories., ApplyPilot first-time setup wizard. Interactive flow that creates…, Generate a searches.yaml from user input., Ask about AI scoring/tailoring — optional LLM configuration., Configure autonomous job application (requires Claude Code CLI). (+9 more)

### Community 15 - "tailor.py"
Cohesion: 0.20
Nodes (13): check_listing_still_open(), Best-effort check for whether a job listing is still accepting applications,…, _apply_canonical_entries(), _bullet_text(), _bullets_similar(), _merge_canonical_section(), Resume tailoring: LLM-powered ATS-optimized resume generation per job. THIS IS…, Tailor a resume for one job: liveness check, LLM call, file writes, PDF… (+5 more)

### Community 16 - "sanitize_text"
Cohesion: 0.17
Nodes (12): Split arbitrary CV/resume text into sections keyed by ALL-CAPS headers. Unlike…, split_sections(), assemble_resume_text(), extract_extra_sections(), _fallback_unquantified(), _format_education(), Pull any non-standard sections out of the base CV, verbatim. The LLM's…, Normalize `education` into the single "degree | institution | honours | dates"… (+4 more)

### Community 17 - "cli.py"
Cohesion: 0.10
Nodes (32): command, Reset all failed jobs so they can be retried. Returns: Number of jobs reset., reset_failed(), apply(), _bootstrap(), dashboard(), doctor(), events() (+24 more)

### Community 18 - "_parse_score_response"
Cohesion: 0.14
Nodes (12): _build_candidate_level(), _clean_optional_field(), _parse_score_response(), Parse the LLM's score response into structured data. Args: response: Raw LLM…, Score a single job against the resume. Args: resume_text: The candidate's full…, Format the candidate's experience level for the scoring prompt. Scoring is done…, Strip a captured field and map a literal 'NULL' response to None. The scoring…, score_job() (+4 more)

### Community 19 - "main"
Cohesion: 0.67
Nodes (3): callback, main(), ApplyPilot — AI-powered end-to-end job application pipeline.

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
Cohesion: 0.07
Nodes (28): _extract_numbers(), Fact, FactBank, FactBankError, FactBankLoadError, Exception, Path, Verified-fact bank for resume tailoring. facts.yaml (repo root) is the ONLY… (+20 more)

### Community 29 - "view.py"
Cohesion: 0.08
Nodes (33): load_profile(), Load user profile from ~/.applypilot/profile.json., classify_location(), _is_relevant_remote(), _location_priority_tier(), True if a (lowercased) location's "remote" claim is UK/NI-relevant or…, 0-indexed priority tier for a job's location (lower = higher priority). Checked…, Human-readable place label for a job's location, for the dashboard's place… (+25 more)

### Community 30 - "pipeline.py"
Cohesion: 0.11
Nodes (26): Event, end_run(), Record the start of one pipeline stage invocation. Args: conn: Database…, Record the end of a pipeline stage invocation. Args: conn: Database connection.…, start_run(), Main entry point for AI-powered smart extraction. Loads sites from…, run_smart_extract(), Main entry point for detail page enrichment. Fetches pending jobs from the… (+18 more)

### Community 31 - "main"
Cohesion: 0.27
Nodes (10): cleanup_on_exit(), kill_all_chrome(), _kill_on_port(), _kill_process_tree(), Kill all Chrome instances and any port zombies. Called during graceful shutdown…, Atexit handler: kill all Chrome processes and sweep CDP ports. Register this…, Kill a process and all its children. On Windows, Chrome spawns 10+ child…, Kill any process listening on a specific port (zombie cleanup). Uses netstat on… (+2 more)

### Community 32 - "mark_job"
Cohesion: 0.20
Nodes (10): mark_job(), Manually mark a job's apply status in the database. Records this as a completed…, Clear one job's apply status back to pending, e.g. after a wrong manual mark or…, reset_job(), finish_attempt(), hide_job(), Mark a job hidden so it stops showing by default and stops being picked up for…, Record the outcome of an apply attempt and mirror it onto jobs. Args: conn:… (+2 more)

### Community 33 - "_strip_preamble"
Cohesion: 0.21
Nodes (7): Remove LLM preamble before 'Dear Hiring Manager,' if present. Gemini and other…, Truncate anything after the sign-off line. Models occasionally add notes/P.S.…, _strip_after_signoff(), _strip_preamble(), An incidental earlier mention of the name must not truncate the real body that…, endeared'/'dearest' mid-preamble must not be mistaken for the letter's real…, TestStripHelpers

### Community 34 - "run_pipeline"
Cohesion: 0.20
Nodes (10): get_stats(), Return job counts by pipeline stage. Provides a snapshot of how many jobs are…, Run smart extract on all targets. Sequential by default. When workers > 1,…, _run_all(), Resolve 'all' and validate/order stage names., Execute stages one at a time (original behavior)., Run pipeline stages. Args: stages: List of stage names, or None / ["all"] for…, _resolve_stages() (+2 more)

### Community 35 - "cover_letter.py"
Cohesion: 0.14
Nodes (19): _build_cover_letter_prompt(), _check_company_mentioned(), generate_cover_letter(), _generate_one_cover_letter(), _normalize_greeting_spacing(), Cover letter generation: LLM-powered, profile-driven, with validation.…, Guarantee exactly one blank line between the "Dear ...," greeting and the first…, Deterministic, code-only removal of any sentence naming one of the given leaked… (+11 more)

### Community 36 - "[0.2.0] - 2026-02-17"
Cohesion: 0.25
Nodes (7): [0.1.0] - 2026-02-17, [0.2.0] - 2026-02-17, Added, Added, Changed, Changelog, Fixed

### Community 37 - "run_job"
Cohesion: 0.10
Nodes (23): add_event(), Update the worker's state fields. Args: worker_id: Which worker to update.…, Add a timestamped event to the scrolling event log. Args: msg: Rich markup…, update_state(), _check_playwright_mcp(), gen_prompt(), _is_permanent_failure(), _make_mcp_config() (+15 more)

### Community 38 - "list_jobs"
Cohesion: 0.14
Nodes (11): Console, list_jobs(), Fetch scored jobs for terminal display, filtered and sorted by fit. Args:…, Render one Rich panel per job with fit score, company context, tailored…, render_jobs(), fixture, Tests for terminal_view.list_jobs / render_jobs (the `applypilot jobs` command)., Isolated scratch DB with a few jobs at different fit scores/sites, never… (+3 more)

### Community 39 - "get_locale_style"
Cohesion: 0.33
Nodes (6): get_locale_style(), Infer document terminology and layout conventions from the candidate's country.…, _build_tailor_prompt(), _format_facts_block(), Render verified facts as an id-keyed list of pre-written variants for the…, Build the resume tailoring system prompt from the user's profile. All skills…

### Community 45 - "get_client"
Cohesion: 0.22
Nodes (9): _detect_provider(), get_client(), Unified LLM client for ApplyPilot. Auto-detects provider from environment:…, Return (base_url, model, api_key) based on environment variables. Reads env at…, Return (or create) the module-level LLMClient singleton., _build_judge_prompt(), judge_tailored_resume(), Build the LLM judge prompt from the user's profile. The judge only ever sees… (+1 more)

## Knowledge Gaps
- **37 isolated node(s):** `applypilot`, `graphify`, `Workflow: graphify`, `Added`, `Fixed` (+32 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_connection()` connect `get_connection` to `mark_job`, `smartextract.py`, `run_pipeline`, `workday.py`, `detail.py`, `run_job`, `init_db`, `cover_letter.py`, `launcher.py`, `list_jobs`, `tailor.py`, `cli.py`, `view.py`, `pipeline.py`, `main`?**
  _High betweenness centrality (0.210) - this node is a cross-community bridge._
- **Why does `FactBank` connect `FactBank` to `tailor_resume`, `cover_letter.py`, `get_locale_style`, `get_client`, `tailor.py`, `sanitize_text`, `ToolLeakGuard`, `_bank`, `view.py`, `pipeline.py`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Why does `get_client()` connect `get_client` to `smartextract.py`, `tailor_resume`, `cover_letter.py`, `detail.py`, `get_connection`, `LLMClient`, `tailor.py`, `_parse_score_response`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `FactBank` (e.g. with `cover_letter_one()` and `generate_cover_letter()`) actually correct?**
  _`FactBank` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `tailor_resume()` (e.g. with `FactBank` and `NumericGuardViolation`) actually correct?**
  _`tailor_resume()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `applypilot`, `graphify`, `Workflow: graphify` to the rest of the system?**
  _37 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `smartextract.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07557354925775979 - nodes in this community are weakly interconnected._