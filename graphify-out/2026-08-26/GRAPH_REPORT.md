# Graph Report - ApplyPilot-main  (2026-08-26)

## Corpus Check
- 48 files · ~115,786 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1042 nodes · 2045 edges · 54 communities (50 shown, 4 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 85 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5a082e89`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- smartextract.py
- workday.py
- _canonical_skills_lines
- detail.py
- database.py
- jobspy.py
- chrome.py
- prompt.py
- launcher.py
- pipeline.py
- main
- pdf.py
- LLMClient
- ToolLeakViolation
- run_wizard
- tailor.py
- test_discovery.py
- cli.py
- scorer.py
- init_db
- ApplyPilot
- scoring/__init__.py
- applypilot
- config.py
- ToolLeakGuard
- ._bank
- FactBank
- facts.py
- apply_eligibility_gate
- run_job
- is_local_provider
- _strip_preamble
- load_search_config
- scrape_detail_page
- [0.2.0] - 2026-02-17
- _parse_score_response
- list_jobs
- critic.py
- rules/graphify.md
- workflows/graphify.md
- TestCrossSectionDuplicateAssertion
- validator.py
- get_client
- cover_letter.py
- _HTMLStripper
- get_connection
- load_location_focus
- _store_jobs_filtered
- judge_tailored_resume
- close_connection
- .load

## God Nodes (most connected - your core abstractions)
1. `get_connection()` - 55 edges
2. `FactBank` - 45 edges
3. `init_db()` - 32 edges
4. `tailor_resume()` - 29 edges
5. `Fact` - 21 edges
6. `generate_cover_letter()` - 20 edges
7. `ToolLeakGuard` - 18 edges
8. `run_job()` - 17 edges
9. `NumericGuard` - 17 edges
10. `get_client()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `TestFactBankLoad` --uses--> `FactBankLoadError`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py
- `TestNumericGuard` --uses--> `NumericGuardViolation`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py
- `TestCrossSectionDuplicateAssertion` --uses--> `BulletPlacementViolation`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py
- `TestBulletOwnership` --uses--> `Fact`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py
- `TestCrossSectionDuplicateAssertion` --uses--> `Fact`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py

## Import Cycles
- None detected.

## Communities (54 total, 4 thin omitted)

### Community 0 - "smartextract.py"
Cohesion: 0.12
Nodes (25): ask_llm(), clean_card_html(), clean_page_html(), collect_page_intelligence(), execute_api_response(), execute_css_selectors(), execute_json_ld(), format_strategy_briefing() (+17 more)

### Community 1 - "workday.py"
Cohesion: 0.09
Nodes (32): fetch_details(), _fetch_one_detail(), load_employers(), _load_location_filter(), _location_ok(), _process_one(), Connection, Workday ATS direct API scraper: searches employer career portals. Scrapes… (+24 more)

### Community 2 - "_canonical_skills_lines"
Cohesion: 0.17
Nodes (9): _canonical_skills_lines(), The TECHNICAL SKILLS lines, one per profile.skills_boundary category, composed…, Once canonical_entries.experience is configured, it's exhaustive: an EXPERIENCE…, The exact incident: the model filed the candidate's own degree as a job once…, The same unmatched-entry situation in PROJECTS is kept, not rejected -- a…, TECHNICAL SKILLS renders only what the profile actually declares -- the LLM's…, The exact incident: the model added 'LangChain (agent frameworks)' and…, TestCanonicalExperienceRejection (+1 more)

### Community 3 - "detail.py"
Cohesion: 0.15
Nodes (20): _load_base_urls(), Connection, Detail page enrichment: scrapes full descriptions and apply URLs. For each job…, Resolve all relative URLs in the database. Returns stats., Re-fetch WTTJ Algolia API to get proper detail URLs and fix slug-as-title.…, Process all jobs for one site using shared browser context. If conn is None,…, Groups pending jobs by site and processes each batch. Sequential by default.…, Set proxy config from an external caller. (+12 more)

### Community 4 - "database.py"
Cohesion: 0.15
Nodes (19): apply_duplicate_marks(), ensure_columns(), find_duplicate_groups(), get_stats(), log_event(), _normalize_title(), Connection, ApplyPilot database layer: schema, migrations, stats, and connection helpers.… (+11 more)

### Community 5 - "jobspy.py"
Cohesion: 0.15
Nodes (18): _full_crawl(), _load_location_config(), _location_ok(), parse_proxy(), Connection, JobSpy-based job discovery: searches Indeed, LinkedIn, Glassdoor, ZipRecruiter.…, Store JobSpy DataFrame results into the DB. Returns (new, existing)., Run a single search query and store results in DB. (+10 more)

### Community 6 - "chrome.py"
Cohesion: 0.14
Nodes (21): Popen, cleanup_on_exit(), cleanup_worker(), kill_all_chrome(), _kill_on_port(), _kill_process_tree(), launch_chrome(), Path (+13 more)

### Community 7 - "prompt.py"
Cohesion: 0.14
Nodes (18): _build_captcha_section(), _build_hard_rules(), _build_location_check(), _build_profile_summary(), build_prompt(), _build_salary_section(), _build_screening_section(), Prompt builder for the autonomous job application agent. Constructs the full… (+10 more)

### Community 8 - "launcher.py"
Cohesion: 0.11
Nodes (25): Apply pipeline: Chrome management, prompt building, orchestration, and…, acquire_job(), _is_permanent_failure(), _load_blocked(), mark_job(), mark_result(), Apply orchestration: acquire jobs, spawn Claude Code sessions, track results.…, Record an attempt's outcome and mirror it onto the job. (+17 more)

### Community 9 - "pipeline.py"
Cohesion: 0.08
Nodes (26): Event, Record the start of one pipeline stage invocation. Args: conn: Database…, start_run(), _count_pending(), ApplyPilot Pipeline Orchestrator. Runs pipeline stages in sequence or…, Stage: Detail enrichment — scrape full descriptions and apply URLs., Stage: LLM scoring — assign fit scores 1-10., Stage: Resume tailoring — generate tailored resumes for high-fit jobs. (+18 more)

### Community 10 - "main"
Cohesion: 0.12
Nodes (20): Group, add_event(), get_state(), get_totals(), init_worker(), Rich live dashboard for the apply pipeline. Displays real-time worker status,…, Build the Rich table showing all worker statuses. Returns: A Rich Table object…, Render the dashboard table plus the recent events panel. Returns: A Rich Group… (+12 more)

### Community 11 - "pdf.py"
Cohesion: 0.09
Nodes (27): Stage: PDF conversion — convert tailored resumes and cover letters to PDF., _run_pdf(), batch_convert(), build_cover_letter_html(), build_html(), _cover_letter_font_faces(), _cv_font_faces(), _fit_resume_html() (+19 more)

### Community 12 - "LLMClient"
Cohesion: 0.13
Nodes (11): Response, _GeminiCompatForbidden, LLMClient, Exception, Thin LLM client supporting OpenAI-compatible and native Gemini endpoints. For…, Call the native Gemini generateContent API. Used automatically when the OpenAI-…, Call the OpenAI-compatible endpoint. json_schema, when given, is passed as…, Call Ollama's native /api/chat, optionally with a JSON-schema `format`.… (+3 more)

### Community 13 - "ToolLeakViolation"
Cohesion: 0.18
Nodes (9): _build_skills_set(), Exception, Build the set of allowed skills from the profile's skills_boundary., Validate individual JSON fields from an LLM-generated tailored resume. Args:…, Programmatic validation of a tailored resume against the user's profile. Args:…, Raised by ToolLeakGuard when a job-description tool the candidate doesn't have…, ToolLeakViolation, validate_json_fields() (+1 more)

### Community 14 - "run_wizard"
Cohesion: 0.17
Nodes (15): ensure_dirs(), Create all required directories., ApplyPilot first-time setup wizard. Interactive flow that creates…, Generate a searches.yaml from user input., Ask about AI scoring/tailoring — optional LLM configuration., Configure autonomous job application (requires Claude Code CLI)., Run the full interactive setup wizard., Prompt for resume file and copy into APP_DIR. (+7 more)

### Community 15 - "tailor.py"
Cohesion: 0.06
Nodes (53): BulletPlacementViolation, Raised when a resolved bullet is rendered under an entry other than its…, Split arbitrary CV/resume text into sections keyed by ALL-CAPS headers. Unlike…, split_sections(), _apply_canonical_entries(), assemble_resume_text(), _base_summary(), _build_guard_scan_text() (+45 more)

### Community 16 - "test_discovery.py"
Cohesion: 0.06
Nodes (45): Store discovered jobs, skipping duplicates by URL. Args: conn: Database…, store_jobs(), fetch_ashby_jobs(), fetch_greenhouse_jobs(), fetch_lever_jobs(), _http_get_json(), infer_opportunity_type(), Direct ATS API harvester: scrapes Greenhouse, Ashby, and Lever career portals.… (+37 more)

### Community 17 - "cli.py"
Cohesion: 0.08
Nodes (39): callback, command, apply(), _bootstrap(), dashboard(), doctor(), events(), init() (+31 more)

### Community 18 - "scorer.py"
Cohesion: 0.14
Nodes (14): _build_candidate_level(), _clean_optional_field(), _normalize_country(), Job fit scoring: LLM-powered evaluation of candidate-job match quality. Scores…, Format the candidate's experience level for the scoring prompt. Scoring is done…, Strip a captured field and map a literal 'NULL' response to None. The scoring…, Deterministic removal of any REASONING sentence that credits the candidate with…, Score a single job against the resume. Args: resume_text: The candidate's full… (+6 more)

### Community 19 - "init_db"
Cohesion: 0.17
Nodes (19): discover(), Run specific or all discovery harvesters to find jobs, graduate schemes, and…, init_db(), Create the full jobs table with all columns from every pipeline stage. This is…, Scrape configured Greenhouse, Ashby, and Lever employers and store results into…, run_direct_ats_discovery(), Run search operator discovery against ATS domains and funded training…, run_dorking_discovery() (+11 more)

### Community 20 - "ApplyPilot"
Cohesion: 0.05
Nodes (39): Adding New Career Sites, Adding New Workday Employers, Bug Fixes and Features, Clone and Install, Code Style Guidelines, Contributing to ApplyPilot, Development Setup, How to Contribute (+31 more)

### Community 23 - "config.py"
Cohesion: 0.15
Nodes (14): get_chrome_user_data(), load_ats_employers(), load_base_urls(), load_blocked_sso(), load_schemes_config(), load_sites_config(), Path, ApplyPilot configuration: paths, platform detection, user data. (+6 more)

### Community 26 - "ToolLeakGuard"
Cohesion: 0.08
Nodes (23): _company_tokens(), Lowercase word tokens from the job's company name. This codebase already treats…, Deterministic check: a tool/tech token in the job description but absent from…, Every job-description tool the candidate doesn't have that appears as a whole…, Raise ToolLeakViolation if a job-description tool the candidate doesn't have…, ToolLeakGuard, _bank(), _CleanClient (+15 more)

### Community 27 - "._bank"
Cohesion: 0.06
Nodes (30): NumericGuard, Deterministic, post-generation check: every number in the assembled resume text…, Raise NumericGuardViolation if any line contains a number that isn't in the…, _bank(), _embedded_fact(), _FakeClient, _kraydel_multiparty_fact(), _qualitative_fact() (+22 more)

### Community 28 - "FactBank"
Cohesion: 0.10
Nodes (18): Fact, FactBank, One verifiable, pre-written claim the LLM may select for a bullet., Parses facts.yaml and is the sole gate on what quantified claims the tailoring…, Best-effort recovery for a plain-string bullet that has a digit but is actually…, All tier == 'verified' facts. The ONLY facts ever exposed to the LLM., Every number the tailoring output is allowed to contain: the union of every…, Verified facts worth offering the LLM for this job. Facts with no `use_when`… (+10 more)

### Community 29 - "facts.py"
Cohesion: 0.12
Nodes (14): _accept_reworded(), _extract_numbers(), FactBankError, FactBankLoadError, NumericGuardViolation, Exception, Verified-fact bank for resume tailoring. facts.yaml (repo root) is the ONLY…, Base class for fact-bank problems. (+6 more)

### Community 30 - "apply_eligibility_gate"
Cohesion: 0.27
Nodes (5): apply_eligibility_gate(), Deterministic hard-eligibility check, run after the LLM's own score and before…, 0.9 does not satisfy a 1-year minimum -- an 11-month placement is under a year,…, Deterministic post-LLM enforcement: the model extracts what the posting says…, TestEligibilityGate

### Community 31 - "run_job"
Cohesion: 0.20
Nodes (11): _check_playwright_mcp(), gen_prompt(), _make_mcp_config(), Path, Generate a prompt file and print the Claude CLI command for manual debugging.…, Inspect a system/init stream-json event for playwright MCP health. Browser…, Spawn a Claude Code session for one job application. Returns: Tuple of…, Build MCP config dict for a specific CDP port. (+3 more)

### Community 32 - "is_local_provider"
Cohesion: 0.18
Nodes (13): check_listing_still_open(), Best-effort check for whether a job listing is still accepting applications,…, is_local_provider(), True when generation will hit a local (non-cloud) LLM_URL endpoint. Mirrors…, Tailor a resume for one job: liveness check, LLM call, file writes, PDF…, Tailor a resume for exactly one job, by URL, regardless of its current…, Generate tailored resumes for high-scoring jobs. Args: min_score: Minimum…, run_tailoring() (+5 more)

### Community 33 - "_strip_preamble"
Cohesion: 0.21
Nodes (7): Remove LLM preamble before 'Dear Hiring Manager,' if present. Gemini and other…, Truncate anything after the sign-off line. Models occasionally add notes/P.S.…, _strip_after_signoff(), _strip_preamble(), An incidental earlier mention of the name must not truncate the real body that…, endeared'/'dearest' mid-preamble must not be mistaken for the letter's real…, TestStripHelpers

### Community 34 - "load_search_config"
Cohesion: 0.27
Nodes (10): load_search_config(), Load search configuration from ~/.applypilot/searches.yaml., build_scrape_targets(), _load_location_filter(), load_sites(), Main entry point for AI-powered smart extraction. Loads sites from…, Load location accept/reject lists from search config., Load scraping target sites from config/sites.yaml. (+2 more)

### Community 35 - "scrape_detail_page"
Cohesion: 0.18
Nodes (12): clean_description(), collect_detail_intelligence(), extract_apply_url_deterministic(), extract_description_deterministic(), extract_from_json_ld(), Collect signals from a detail page. Lighter than discovery -- no API…, Extract description and apply URL from JSON-LD JobPosting. Returns…, Try known CSS patterns for apply buttons/links. (+4 more)

### Community 36 - "[0.2.0] - 2026-02-17"
Cohesion: 0.25
Nodes (7): [0.1.0] - 2026-02-17, [0.2.0] - 2026-02-17, Added, Added, Changed, Changelog, Fixed

### Community 37 - "_parse_score_response"
Cohesion: 0.27
Nodes (5): _parse_score_response(), Parse the LLM's score response into structured data. Args: response: Raw LLM…, REASONING used to be a greedy capture-to-end-of-string -- once…, Older-style responses (or a model that ignores the new fields) must not crash…, TestParseScoreResponse

### Community 38 - "list_jobs"
Cohesion: 0.14
Nodes (11): Console, list_jobs(), Fetch scored jobs for terminal display, filtered and sorted by fit. Args:…, Render one Rich panel per job with fit score, company context, tailored…, render_jobs(), fixture, Tests for terminal_view.list_jobs / render_jobs (the `applypilot jobs` command)., Isolated scratch DB with a few jobs at different fit scores/sites, never… (+3 more)

### Community 39 - "critic.py"
Cohesion: 0.09
Nodes (20): _build_cv_critic_user_message(), _build_letter_critic_user_message(), combined_critic_score(), CriticResult, evaluate_cv_observations(), evaluate_letter_observations(), Extraction-only "critic" pass over a tailored CV and cover letter. Catches…, Apply fixed, code-side thresholds to the model's raw extraction. Never trusts… (+12 more)

### Community 43 - "TestCrossSectionDuplicateAssertion"
Cohesion: 0.33
Nodes (3): check_no_cross_section_duplicates is the hard backstop: even if ownership/dedup…, Backward compatible: omitting fact_bank still catches exact duplicates, just…, TestCrossSectionDuplicateAssertion

### Community 44 - "validator.py"
Cohesion: 0.08
Nodes (29): find_fabricated_numbers(), has_bad_signoff(), has_dangling_reference(), has_lifted_jd_span(), has_repeated_phrase(), _is_mostly_filler(), Resume and cover letter validation: banned words, fabrication detection,…, Find number-bearing claims in tailored text with no basis in the original.… (+21 more)

### Community 45 - "get_client"
Cohesion: 0.14
Nodes (15): extract_json(), judge_api_responses(), Use the LLM to filter API responses, keeping only job-relevant ones., Extract JSON from LLM response, handling think tags and code fences., clean_content_html(), extract_main_content(), extract_with_llm(), Extract the main content area, stripped of navigation noise. (+7 more)

### Community 46 - "cover_letter.py"
Cohesion: 0.09
Nodes (32): get_locale_style(), load_profile(), Infer document terminology and layout conventions from the candidate's country.…, Load user profile from ~/.applypilot/profile.json., format_facts_block(), Render verified facts as an id-keyed list for a prompt. Shared by resume…, _build_cover_letter_prompt(), _check_company_mentioned() (+24 more)

### Community 47 - "_HTMLStripper"
Cohesion: 0.25
Nodes (3): HTMLParser, _HTMLStripper, Strip HTML tags, keep text content.

### Community 48 - "get_connection"
Cohesion: 0.14
Nodes (16): Reset all failed jobs so they can be retried. Returns: Number of jobs reset., Clear one job's apply status back to pending, e.g. after a wrong manual mark or…, reset_failed(), reset_job(), get_connection(), hide_job(), Get a thread-local cached SQLite connection with WAL mode enabled. Each thread…, Mark a job hidden so it stops showing by default and stops being picked up for… (+8 more)

### Community 49 - "load_location_focus"
Cohesion: 0.12
Nodes (17): load_location_focus(), Load the optional `location_focus` section from searches.yaml. A temporary,…, classify_location(), get_jobs_by_stage(), _is_relevant_remote(), _location_priority_tier(), Register the `loc_priority(location)` SQL function used to rank/filter jobs by…, True if a (lowercased) location's "remote" claim is UK/NI-relevant or… (+9 more)

### Community 50 - "_store_jobs_filtered"
Cohesion: 0.40
Nodes (5): _location_ok(), Connection, Check if a job location passes the user's location filter., Store jobs with location filtering. Returns (new, existing)., _store_jobs_filtered()

### Community 51 - "judge_tailored_resume"
Cohesion: 0.50
Nodes (4): _build_judge_prompt(), judge_tailored_resume(), LLM judge layer: catches subtle fabrication that programmatic checks miss.…, Build the LLM judge prompt from the user's profile. The judge only ever sees…

### Community 52 - "close_connection"
Cohesion: 0.67
Nodes (3): close_connection(), Path, Close the cached connection for the current thread.

### Community 55 - ".load"
Cohesion: 0.20
Nodes (7): Path, A known gap: a plausible claim that needs a real value filled in before it can…, Parse facts.yaml into Facts, validating every verified fact's numbers against…, Unverified entries pending a real value, for a CLI prompt flow., UnfilledFact, A verified fact whose declared number isn't backed by its own evidence string…, TestFactBankLoad

## Knowledge Gaps
- **37 isolated node(s):** `applypilot`, `graphify`, `Workflow: graphify`, `Added`, `Fixed` (+32 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_connection()` connect `get_connection` to `smartextract.py`, `workday.py`, `detail.py`, `database.py`, `jobspy.py`, `launcher.py`, `pipeline.py`, `main`, `tailor.py`, `test_discovery.py`, `cli.py`, `scorer.py`, `init_db`, `run_job`, `is_local_provider`, `list_jobs`, `cover_letter.py`, `load_location_focus`, `close_connection`?**
  _High betweenness centrality (0.195) - this node is a cross-community bridge._
- **Why does `FactBank` connect `FactBank` to `is_local_provider`, `TestCrossSectionDuplicateAssertion`, `cover_letter.py`, `tailor.py`, `judge_tailored_resume`, `.load`, `ToolLeakGuard`, `._bank`, `facts.py`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `get_client()` connect `get_client` to `smartextract.py`, `detail.py`, `LLMClient`, `cover_letter.py`, `tailor.py`, `scorer.py`, `judge_tailored_resume`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Are the 22 inferred relationships involving `FactBank` (e.g. with `_build_cover_letter_prompt()` and `cover_letter_one()`) actually correct?**
  _`FactBank` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `tailor_resume()` (e.g. with `BulletPlacementViolation` and `FactBank`) actually correct?**
  _`tailor_resume()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `Fact` (e.g. with `TestBulletOwnership` and `TestCrossSectionDedup`) actually correct?**
  _`Fact` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `applypilot`, `graphify`, `Workflow: graphify` to the rest of the system?**
  _37 weakly-connected nodes found - possible documentation gaps or missing edges._