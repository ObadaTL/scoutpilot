# Graph Report - ApplyPilot-main  (2026-08-25)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 848 nodes · 1613 edges · 57 communities (52 shown, 5 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 62 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e5d6d8e8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- _run_one_site
- workday.py
- _ship_unquantified_fallback
- detail.py
- database.py
- jobspy.py
- chrome.py
- prompt.py
- config.py
- _StageTracker
- main
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
- test_cover_letter.py
- _kraydel_multiparty_fact
- facts.py
- view.py
- pipeline.py
- scrape_detail_page
- get_connection
- _strip_preamble
- smartextract.py
- cover_letter.py
- [0.2.0] - 2026-02-17
- launcher.py
- list_jobs
- tailor_resume
- rules/graphify.md
- workflows/graphify.md
- NumericGuard
- validate_cover_letter
- get_client
- FactBank
- test_facts.py
- load_location_focus
- Fact
- ._bank
- convert_to_pdf
- NumericGuardViolation
- run_cover_letters
- _store_jobs_filtered
- UnfilledFact
- extract_extra_sections

## God Nodes (most connected - your core abstractions)
1. `get_connection()` - 51 edges
2. `FactBank` - 40 edges
3. `tailor_resume()` - 22 edges
4. `init_db()` - 21 edges
5. `generate_cover_letter()` - 19 edges
6. `NumericGuard` - 17 edges
7. `Fact` - 17 edges
8. `run_job()` - 17 edges
9. `get_client()` - 16 edges
10. `main()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `TestNumericGuard` --uses--> `NumericGuardViolation`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py
- `_bank()` --calls--> `FactBank`  [EXTRACTED]
  tests/test_facts.py → src/applypilot/facts.py
- `TestCrossSectionDedup` --uses--> `FactBank`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py
- `TestRewordedFactBullets` --uses--> `FactBank`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py
- `TestRewordedFactBullets` --uses--> `Fact`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py

## Import Cycles
- None detected.

## Communities (57 total, 5 thin omitted)

### Community 0 - "_run_one_site"
Cohesion: 0.10
Nodes (24): ask_llm(), clean_page_html(), collect_page_intelligence(), execute_api_response(), execute_css_selectors(), execute_json_ld(), extract_json(), format_strategy_briefing() (+16 more)

### Community 1 - "workday.py"
Cohesion: 0.07
Nodes (31): HTMLParser, fetch_details(), _fetch_one_detail(), _HTMLStripper, load_employers(), _location_ok(), _process_one(), Connection (+23 more)

### Community 2 - "_ship_unquantified_fallback"
Cohesion: 0.25
Nodes (8): _build_guard_scan_text(), Text scope NumericGuard checks: LLM-authored content (title, summary, skills,…, Build, assemble, and re-verify the unquantified fallback. Called only after…, Absolute last resort: remove every digit from every LLM-authored field (title,…, Resolve every experience/project bullet into literal text. A fact-id bullet is…, _resolve_fact_bullets(), _ship_unquantified_fallback(), _strip_all_digits_from_fields()

### Community 3 - "detail.py"
Cohesion: 0.13
Nodes (24): ensure_columns(), init_db(), Create the full jobs table with all columns from every pipeline stage. This is…, Add any missing columns to the jobs table (forward migration). Reads the…, _load_base_urls(), Connection, Detail page enrichment: scrapes full descriptions and apply URLs. For each job…, Resolve all relative URLs in the database. Returns stats. (+16 more)

### Community 4 - "database.py"
Cohesion: 0.10
Nodes (27): apply_duplicate_marks(), find_duplicate_groups(), hide_job(), _is_relevant_remote(), _location_priority_tier(), log_event(), _normalize_title(), Connection (+19 more)

### Community 5 - "jobspy.py"
Cohesion: 0.14
Nodes (20): _full_crawl(), _load_location_config(), _location_ok(), parse_proxy(), Connection, JobSpy-based job discovery: searches Indeed, LinkedIn, Glassdoor, ZipRecruiter.…, Store JobSpy DataFrame results into the DB. Returns (new, existing)., Run a single search query and store results in DB. (+12 more)

### Community 6 - "chrome.py"
Cohesion: 0.14
Nodes (21): Popen, cleanup_on_exit(), cleanup_worker(), kill_all_chrome(), _kill_on_port(), _kill_process_tree(), launch_chrome(), Path (+13 more)

### Community 7 - "prompt.py"
Cohesion: 0.13
Nodes (20): _build_captcha_section(), _build_hard_rules(), _build_location_check(), _build_profile_summary(), build_prompt(), _build_salary_section(), _build_screening_section(), Prompt builder for the autonomous job application agent. Constructs the full… (+12 more)

### Community 8 - "config.py"
Cohesion: 0.17
Nodes (16): doctor(), Check your setup and diagnose missing requirements., check_tier(), get_chrome_path(), get_chrome_user_data(), get_tier(), load_base_urls(), load_env() (+8 more)

### Community 10 - "main"
Cohesion: 0.15
Nodes (17): Group, get_state(), get_totals(), init_worker(), Rich live dashboard for the apply pipeline. Displays real-time worker status,…, Build the Rich table showing all worker statuses. Returns: A Rich Table object…, Render the dashboard table plus the recent events panel. Returns: A Rich Group…, Compute aggregate totals across all workers. Returns: Dict with keys: applied,… (+9 more)

### Community 11 - "pdf.py"
Cohesion: 0.09
Nodes (27): Stage: PDF conversion — convert tailored resumes and cover letters to PDF., _run_pdf(), batch_convert(), build_cover_letter_html(), build_html(), _cover_letter_font_faces(), _cv_font_faces(), _fit_resume_html() (+19 more)

### Community 12 - "LLMClient"
Cohesion: 0.13
Nodes (11): Response, _GeminiCompatForbidden, LLMClient, Exception, Thin LLM client supporting OpenAI-compatible and native Gemini endpoints. For…, Call the native Gemini generateContent API. Used automatically when the OpenAI-…, Call the OpenAI-compatible endpoint. json_schema, when given, is passed as…, Call Ollama's native /api/chat, optionally with a JSON-schema `format`.… (+3 more)

### Community 13 - "validator.py"
Cohesion: 0.24
Nodes (9): _build_skills_set(), find_fabricated_numbers(), Resume and cover letter validation: banned words, fabrication detection,…, Build the set of allowed skills from the profile's skills_boundary., Validate individual JSON fields from an LLM-generated tailored resume. Args:…, Programmatic validation of a tailored resume against the user's profile. Args:…, Find number-bearing claims in tailored text with no basis in the original.…, validate_json_fields() (+1 more)

### Community 14 - "run_wizard"
Cohesion: 0.17
Nodes (15): ensure_dirs(), Create all required directories., ApplyPilot first-time setup wizard. Interactive flow that creates…, Generate a searches.yaml from user input., Ask about AI scoring/tailoring — optional LLM configuration., Configure autonomous job application (requires Claude Code CLI)., Run the full interactive setup wizard., Prompt for resume file and copy into APP_DIR. (+7 more)

### Community 15 - "tailor.py"
Cohesion: 0.23
Nodes (11): check_listing_still_open(), Best-effort check for whether a job listing is still accepting applications,…, _apply_canonical_entries(), _bullet_text(), _bullets_similar(), _merge_canonical_section(), Resume tailoring: LLM-powered ATS-optimized resume generation per job. THIS IS…, Best-effort plain text for a bullet, which may still be a raw {"fact": id,… (+3 more)

### Community 16 - "sanitize_text"
Cohesion: 0.20
Nodes (12): assemble_resume_text(), _base_summary(), _fallback_unquantified(), _format_education(), _profile_education(), Deterministic, code-only fallback for when the guard still fails after every…, The education line as the profile itself states it., Normalize `education` into the single "degree | institution | honours | dates"… (+4 more)

### Community 17 - "cli.py"
Cohesion: 0.12
Nodes (23): command, Reset all failed jobs so they can be retried. Returns: Number of jobs reset., reset_failed(), apply(), _bootstrap(), dashboard(), events(), init() (+15 more)

### Community 18 - "_parse_score_response"
Cohesion: 0.19
Nodes (8): _clean_optional_field(), _parse_score_response(), Parse the LLM's score response into structured data. Args: response: Raw LLM…, Strip a captured field and map a literal 'NULL' response to None. The scoring…, Tests for the company_summary/company_hook capture added to fit scoring., REASONING used to be a greedy capture-to-end-of-string -- once…, Older-style responses (or a model that ignores the new fields) must not crash…, TestParseScoreResponse

### Community 19 - "main"
Cohesion: 0.67
Nodes (3): callback, main(), ApplyPilot — AI-powered end-to-end job application pipeline.

### Community 20 - "ApplyPilot"
Cohesion: 0.05
Nodes (39): Adding New Career Sites, Adding New Workday Employers, Bug Fixes and Features, Clone and Install, Code Style Guidelines, Contributing to ApplyPilot, Development Setup, How to Contribute (+31 more)

### Community 26 - "test_cover_letter.py"
Cohesion: 0.08
Nodes (25): _company_tokens(), Exception, Raised by ToolLeakGuard when a job-description tool the candidate doesn't have…, Lowercase word tokens from the job's company name. This codebase already treats…, Deterministic check: a tool/tech token in the job description but absent from…, Raise ToolLeakViolation if a job-description tool the candidate doesn't have…, ToolLeakGuard, ToolLeakViolation (+17 more)

### Community 27 - "_kraydel_multiparty_fact"
Cohesion: 0.22
Nodes (7): _kraydel_multiparty_fact(), Bullets that carry no fact id must contain no digits -- enforced in code, not…, Mirrors the real kraydel.multiparty_calls entry in facts.yaml., A plausible-but-unevidenced fact that must never reach the LLM., The core guarantee: relevant_facts() (what actually goes into the LLM prompt)…, TestFactBankRejectsUnverified, _unverified_fact()

### Community 28 - "facts.py"
Cohesion: 0.11
Nodes (14): _accept_reworded(), _extract_numbers(), Verified-fact bank for resume tailoring. facts.yaml (repo root) is the ONLY…, Recursively pull every integer token out of a nested structure. Used to fold…, Deterministic keyword extraction from a fact's free-text `use_when`.…, Best-effort recovery for a plain-string bullet that has a digit but is actually…, All tier == 'verified' facts. The ONLY facts ever exposed to the LLM., Every number the tailoring output is allowed to contain: the union of every… (+6 more)

### Community 29 - "view.py"
Cohesion: 0.19
Nodes (13): is_local_provider(), Unified LLM client for ApplyPilot. Auto-detects provider from environment:…, True when generation will hit a local (non-cloud) LLM_URL endpoint. Mirrors…, cover_letter_one(), Generate a cover letter for exactly one job, by URL, regardless of its current…, Tailor a resume for exactly one job, by URL, regardless of its current…, tailor_one(), get_tailor_status() (+5 more)

### Community 30 - "pipeline.py"
Cohesion: 0.11
Nodes (26): Event, end_run(), Record the start of one pipeline stage invocation. Args: conn: Database…, Record the end of a pipeline stage invocation. Args: conn: Database connection.…, start_run(), _count_pending(), ApplyPilot Pipeline Orchestrator. Runs pipeline stages in sequence or…, Stage: Detail enrichment — scrape full descriptions and apply URLs. (+18 more)

### Community 31 - "scrape_detail_page"
Cohesion: 0.12
Nodes (18): clean_content_html(), clean_description(), collect_detail_intelligence(), extract_apply_url_deterministic(), extract_description_deterministic(), extract_from_json_ld(), extract_main_content(), extract_with_llm() (+10 more)

### Community 32 - "get_connection"
Cohesion: 0.12
Nodes (19): Clear one job's apply status back to pending, e.g. after a wrong manual mark or…, reset_job(), close_connection(), get_connection(), get_jobs_by_stage(), Path, Get a thread-local cached SQLite connection with WAL mode enabled. Each thread…, Close the cached connection for the current thread. (+11 more)

### Community 33 - "_strip_preamble"
Cohesion: 0.21
Nodes (7): Remove LLM preamble before 'Dear Hiring Manager,' if present. Gemini and other…, Truncate anything after the sign-off line. Models occasionally add notes/P.S.…, _strip_after_signoff(), _strip_preamble(), An incidental earlier mention of the name must not truncate the real body that…, endeared'/'dearest' mid-preamble must not be mistaken for the letter's real…, TestStripHelpers

### Community 34 - "smartextract.py"
Cohesion: 0.13
Nodes (21): load_search_config(), Load search configuration from ~/.applypilot/searches.yaml., get_stats(), Return job counts by pipeline stage. Provides a snapshot of how many jobs are…, build_scrape_targets(), clean_card_html(), _load_location_filter(), load_sites() (+13 more)

### Community 35 - "cover_letter.py"
Cohesion: 0.13
Nodes (21): get_locale_style(), Infer document terminology and layout conventions from the candidate's country.…, format_facts_block(), Render verified facts as an id-keyed list for a prompt. Shared by resume…, _build_cover_letter_prompt(), _check_company_mentioned(), generate_cover_letter(), _generate_one_cover_letter() (+13 more)

### Community 36 - "[0.2.0] - 2026-02-17"
Cohesion: 0.25
Nodes (7): [0.1.0] - 2026-02-17, [0.2.0] - 2026-02-17, Added, Added, Changed, Changelog, Fixed

### Community 37 - "launcher.py"
Cohesion: 0.08
Nodes (40): add_event(), Update the worker's state fields. Args: worker_id: Which worker to update.…, Add a timestamped event to the scrolling event log. Args: msg: Rich markup…, update_state(), Apply pipeline: Chrome management, prompt building, orchestration, and…, acquire_job(), _check_playwright_mcp(), gen_prompt() (+32 more)

### Community 38 - "list_jobs"
Cohesion: 0.14
Nodes (11): Console, list_jobs(), Fetch scored jobs for terminal display, filtered and sorted by fit. Args:…, Render one Rich panel per job with fit score, company context, tailored…, render_jobs(), fixture, Tests for terminal_view.list_jobs / render_jobs (the `applypilot jobs` command)., Isolated scratch DB with a few jobs at different fit scores/sites, never… (+3 more)

### Community 39 - "tailor_resume"
Cohesion: 0.25
Nodes (8): _build_tailor_prompt(), extract_json(), Generate a tailored resume via JSON output + fresh context on each retry. Key…, JSON Schema for the tailor prompt's expected output shape. Passed as…, Robustly extract JSON from LLM response (handles fences, preamble). Args: raw:…, Build the resume tailoring system prompt from the user's profile. All skills…, _resume_json_schema(), tailor_resume()

### Community 43 - "NumericGuard"
Cohesion: 0.16
Nodes (8): NumericGuard, Deterministic, post-generation check: every number in the assembled resume text…, Raise NumericGuardViolation if any line contains a number that isn't in the…, _qualitative_fact(), Canonical example: an injected, unevidenced 500 must be caught., The real 4-to-9 participant fact must pass cleanly., A zero-number verified fact (mirrors kraydel.audit_system)., TestNumericGuard

### Community 44 - "validate_cover_letter"
Cohesion: 0.18
Nodes (10): has_dangling_reference(), True if a body paragraph opens with a back-reference to a sentence that isn't…, Programmatic validation of a cover letter. Args: text: The cover letter text to…, validate_cover_letter(), ...with % accuracy" -- the digit-blanking fallback's signature., A first body paragraph opening on a referent that was deleted., Only the FIRST body paragraph can dangle -- a later "That ..." points at the…, lenient tolerates style sins, not a letter with holes in it -- and lenient is… (+2 more)

### Community 45 - "get_client"
Cohesion: 0.25
Nodes (8): _detect_provider(), get_client(), Return (base_url, model, api_key) based on environment variables. Reads env at…, Return (or create) the module-level LLMClient singleton., _build_judge_prompt(), judge_tailored_resume(), LLM judge layer: catches subtle fabrication that programmatic checks miss.…, Build the LLM judge prompt from the user's profile. The judge only ever sees…

### Community 46 - "FactBank"
Cohesion: 0.22
Nodes (8): FactBank, FactBankLoadError, Path, Raised when facts.yaml fails integrity checks at load time., Parses facts.yaml and is the sole gate on what quantified claims the tailoring…, Parse facts.yaml into Facts, validating every verified fact's numbers against…, A verified fact whose declared number isn't backed by its own evidence string…, TestFactBankLoad

### Community 47 - "test_facts.py"
Cohesion: 0.18
Nodes (8): _bank(), _embedded_fact(), _FakeClient, Tests for the FactBank / NumericGuard architectural fabrication guard. Fixtures…, Always returns the same fabricated response, regardless of the 'AVOID THESE…, A use_when-restricted fact (mirrors edu.embedded_marks)., TestFactBankJobAwareSelection, TestGuardFailureFallsBack

### Community 48 - "load_location_focus"
Cohesion: 0.22
Nodes (11): load_location_focus(), Load the optional `location_focus` section from searches.yaml. A temporary,…, classify_location(), Human-readable place label for a job's location, for the dashboard's place…, generate_dashboard(), open_dashboard(), Path, Generate a static dashboard snapshot and open it in the default browser -- a… (+3 more)

### Community 49 - "Fact"
Cohesion: 0.27
Nodes (6): Fact, One verifiable, pre-written claim the LLM may select for a bullet., A fact is one real thing; it belongs on the CV once. But deduping a section out…, The duplicate bullet goes; the entry survives on its other one., If dedup would leave PROJECTS with no entries at all, the section falls back to…, TestCrossSectionDedup

### Community 50 - "._bank"
Cohesion: 0.31
Nodes (4): The wording is the model's; the numbers are not. A rewording that reaches for a…, Tighter than NumericGuard's global allowed set on purpose: 11 is verified, but…, Back-compat: the original select-a-variant shape is unchanged., TestRewordedFactBullets

### Community 51 - "convert_to_pdf"
Cohesion: 0.25
Nodes (9): load_profile(), Load user profile from ~/.applypilot/profile.json., convert_to_pdf(), Path, Convert a text resume or cover letter to a formatted PDF. Args: text_path: Path…, Tailor a resume for one job: liveness check, LLM call, file writes, PDF…, Generate tailored resumes for high-scoring jobs. Args: min_score: Minimum…, run_tailoring() (+1 more)

### Community 52 - "NumericGuardViolation"
Cohesion: 0.22
Nodes (9): FactBankError, NumericGuardViolation, Exception, Base class for fact-bank problems., Raised by NumericGuard when the assembled resume text contains a number that…, Describe the template the summary fell into, or "" if it didn't. Scoped to…, Rewrite `resolved_data["summary"]` in place if it fell into a rut. Mutates only…, _repair_summary_rut() (+1 more)

### Community 53 - "run_cover_letters"
Cohesion: 0.33
Nodes (6): Stage: Cover letter generation., _run_cover(), _preflight_pdf_converter(), Smoke-test the PDF pipeline once per batch, before any LLM calls. Exercises the…, Generate cover letters for high-scoring jobs that have tailored resumes. Args:…, run_cover_letters()

### Community 54 - "_store_jobs_filtered"
Cohesion: 0.40
Nodes (5): _location_ok(), Connection, Check if a job location passes the user's location filter., Store jobs with location filtering. Returns (new, existing)., _store_jobs_filtered()

### Community 55 - "UnfilledFact"
Cohesion: 0.40
Nodes (3): A known gap: a plausible claim that needs a real value filled in before it can…, Unverified entries pending a real value, for a CLI prompt flow., UnfilledFact

### Community 56 - "extract_extra_sections"
Cohesion: 0.50
Nodes (4): Split arbitrary CV/resume text into sections keyed by ALL-CAPS headers. Unlike…, split_sections(), extract_extra_sections(), Pull any non-standard sections out of the base CV, verbatim. The LLM's…

## Knowledge Gaps
- **37 isolated node(s):** `Adding New Career Sites`, `Adding New Workday Employers`, `Bug Fixes and Features`, `Clone and Install`, `Code Style Guidelines` (+32 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_connection()` connect `get_connection` to `workday.py`, `smartextract.py`, `detail.py`, `database.py`, `launcher.py`, `jobspy.py`, `cover_letter.py`, `list_jobs`, `main`, `tailor.py`, `load_location_focus`, `cli.py`, `convert_to_pdf`, `run_cover_letters`, `view.py`, `pipeline.py`?**
  _High betweenness centrality (0.207) - this node is a cross-community bridge._
- **Why does `FactBank` connect `FactBank` to `_ship_unquantified_fallback`, `cover_letter.py`, `tailor_resume`, `NumericGuard`, `get_client`, `tailor.py`, `sanitize_text`, `Fact`, `test_facts.py`, `convert_to_pdf`, `._bank`, `run_cover_letters`, `UnfilledFact`, `test_cover_letter.py`, `facts.py`, `view.py`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Why does `get_client()` connect `get_client` to `_run_one_site`, `get_connection`, `smartextract.py`, `detail.py`, `cover_letter.py`, `tailor_resume`, `LLMClient`, `tailor.py`, `view.py`, `scrape_detail_page`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `FactBank` (e.g. with `_build_cover_letter_prompt()` and `cover_letter_one()`) actually correct?**
  _`FactBank` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `tailor_resume()` (e.g. with `FactBank` and `NumericGuardViolation`) actually correct?**
  _`tailor_resume()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Adding New Career Sites`, `Adding New Workday Employers`, `Bug Fixes and Features` to the rest of the system?**
  _37 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `_run_one_site` be split into smaller, more focused modules?**
  _Cohesion score 0.10144927536231885 - nodes in this community are weakly interconnected._