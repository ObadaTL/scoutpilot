# Graph Report - ApplyPilot-main  (2026-08-26)

## Corpus Check
- 48 files · ~116,620 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1050 nodes · 2069 edges · 51 communities (47 shown, 4 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 85 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5a082e89`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- smartextract.py
- workday.py
- TestCanonicalSkillsLines
- run_enrichment
- database.py
- jobspy.py
- chrome.py
- prompt.py
- launcher.py
- pipeline.py
- main
- pdf.py
- LLMClient
- validator.py
- run_wizard
- tailor.py
- test_discovery.py
- cli.py
- scorer.py
- init_db
- ApplyPilot
- scoring/__init__.py
- applypilot
- get_chrome_user_data
- ToolLeakGuard
- ._bank
- FactBank
- facts.py
- apply_eligibility_gate
- run_job
- load_profile
- _strip_preamble
- run_workday_discovery
- detail.py
- [0.2.0] - 2026-02-17
- end_run
- list_jobs
- critic.py
- rules/graphify.md
- workflows/graphify.md
- validate_cover_letter
- get_client
- cover_letter.py
- view.py
- load_location_focus
- _store_jobs_filtered
- get_connection
- .load

## God Nodes (most connected - your core abstractions)
1. `get_connection()` - 56 edges
2. `FactBank` - 45 edges
3. `init_db()` - 32 edges
4. `tailor_resume()` - 29 edges
5. `Fact` - 21 edges
6. `generate_cover_letter()` - 20 edges
7. `ToolLeakGuard` - 18 edges
8. `run_job()` - 17 edges
9. `NumericGuard` - 17 edges
10. `load_profile()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `TestNumericGuard` --uses--> `NumericGuardViolation`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py
- `TestCrossSectionDuplicateAssertion` --uses--> `BulletPlacementViolation`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py
- `TestCrossSectionDedup` --uses--> `Fact`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py
- `_bank()` --calls--> `FactBank`  [EXTRACTED]
  tests/test_facts.py → src/applypilot/facts.py
- `TestBulletOwnership` --uses--> `FactBank`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py

## Import Cycles
- None detected.

## Communities (51 total, 4 thin omitted)

### Community 0 - "smartextract.py"
Cohesion: 0.11
Nodes (29): ask_llm(), clean_card_html(), clean_page_html(), collect_page_intelligence(), execute_api_response(), execute_css_selectors(), execute_json_ld(), extract_json() (+21 more)

### Community 1 - "workday.py"
Cohesion: 0.07
Nodes (31): HTMLParser, fetch_details(), _fetch_one_detail(), _HTMLStripper, load_employers(), _location_ok(), _process_one(), Connection (+23 more)

### Community 2 - "TestCanonicalSkillsLines"
Cohesion: 0.18
Nodes (7): Once canonical_entries.experience is configured, it's exhaustive: an EXPERIENCE…, The exact incident: the model filed the candidate's own degree as a job once…, The same unmatched-entry situation in PROJECTS is kept, not rejected -- a…, TECHNICAL SKILLS renders only what the profile actually declares -- the LLM's…, The exact incident: the model added 'LangChain (agent frameworks)' and…, TestCanonicalExperienceRejection, TestCanonicalSkillsLines

### Community 3 - "run_enrichment"
Cohesion: 0.17
Nodes (15): Connection, Resolve all relative URLs in the database. Returns stats., Re-fetch WTTJ Algolia API to get proper detail URLs and fix slug-as-title.…, Process all jobs for one site using shared browser context. If conn is None,…, Groups pending jobs by site and processes each batch. Sequential by default.…, Set proxy config from an external caller., Streaming detail scraper: polls DB for un-scraped jobs, scrapes sites…, Main entry point for detail page enrichment. Fetches pending jobs from the… (+7 more)

### Community 4 - "database.py"
Cohesion: 0.11
Nodes (25): apply_duplicate_marks(), attach_tool_result(), clean_non_tech_jobs(), ensure_columns(), find_duplicate_groups(), finish_attempt(), get_stats(), log_event() (+17 more)

### Community 5 - "jobspy.py"
Cohesion: 0.14
Nodes (20): _full_crawl(), _load_location_config(), _location_ok(), parse_proxy(), Connection, JobSpy-based job discovery: searches Indeed, LinkedIn, Glassdoor, ZipRecruiter.…, Store JobSpy DataFrame results into the DB. Returns (new, existing)., Run a single search query and store results in DB. (+12 more)

### Community 6 - "chrome.py"
Cohesion: 0.14
Nodes (21): Popen, cleanup_on_exit(), cleanup_worker(), kill_all_chrome(), _kill_on_port(), _kill_process_tree(), launch_chrome(), Path (+13 more)

### Community 7 - "prompt.py"
Cohesion: 0.13
Nodes (20): _build_captcha_section(), _build_hard_rules(), _build_location_check(), _build_profile_summary(), build_prompt(), _build_salary_section(), _build_screening_section(), Prompt builder for the autonomous job application agent. Constructs the full… (+12 more)

### Community 8 - "launcher.py"
Cohesion: 0.11
Nodes (22): Apply pipeline: Chrome management, prompt building, orchestration, and…, acquire_job(), _load_blocked(), Apply orchestration: acquire jobs, spawn Claude Code sessions, track results.…, Atomically acquire the next job to apply to and open an attempt for it. Args:…, get_profile_keywords(), is_manual_ats(), load_ats_employers() (+14 more)

### Community 9 - "pipeline.py"
Cohesion: 0.11
Nodes (18): Event, _count_pending(), ApplyPilot Pipeline Orchestrator. Runs pipeline stages in sequence or…, Stage: Cover letter generation., Resolve 'all' and validate/order stage names., Thread-safe tracker for which stages have finished producing work., Count pending work items for a stage., Run a single stage in streaming mode: loop until upstream done + no work. For… (+10 more)

### Community 10 - "main"
Cohesion: 0.13
Nodes (18): Group, add_event(), get_state(), get_totals(), init_worker(), Rich live dashboard for the apply pipeline. Displays real-time worker status,…, Build the Rich table showing all worker statuses. Returns: A Rich Table object…, Render the dashboard table plus the recent events panel. Returns: A Rich Group… (+10 more)

### Community 11 - "pdf.py"
Cohesion: 0.09
Nodes (27): Stage: PDF conversion — convert tailored resumes and cover letters to PDF., _run_pdf(), batch_convert(), build_cover_letter_html(), build_html(), _cover_letter_font_faces(), _cv_font_faces(), _fit_resume_html() (+19 more)

### Community 12 - "LLMClient"
Cohesion: 0.13
Nodes (11): Response, _GeminiCompatForbidden, LLMClient, Exception, Thin LLM client supporting OpenAI-compatible and native Gemini endpoints. For…, Call the native Gemini generateContent API. Used automatically when the OpenAI-…, Call the OpenAI-compatible endpoint. json_schema, when given, is passed as…, Call Ollama's native /api/chat, optionally with a JSON-schema `format`.… (+3 more)

### Community 13 - "validator.py"
Cohesion: 0.16
Nodes (12): _build_skills_set(), find_fabricated_numbers(), Exception, Resume and cover letter validation: banned words, fabrication detection,…, Find number-bearing claims in tailored text with no basis in the original.…, Build the set of allowed skills from the profile's skills_boundary., Validate individual JSON fields from an LLM-generated tailored resume. Args:…, Programmatic validation of a tailored resume against the user's profile. Args:… (+4 more)

### Community 14 - "run_wizard"
Cohesion: 0.17
Nodes (15): ensure_dirs(), Create all required directories., ApplyPilot first-time setup wizard. Interactive flow that creates…, Generate a searches.yaml from user input., Ask about AI scoring/tailoring — optional LLM configuration., Configure autonomous job application (requires Claude Code CLI)., Run the full interactive setup wizard., Prompt for resume file and copy into APP_DIR. (+7 more)

### Community 15 - "tailor.py"
Cohesion: 0.06
Nodes (55): Split arbitrary CV/resume text into sections keyed by ALL-CAPS headers. Unlike…, split_sections(), _apply_canonical_entries(), assemble_resume_text(), _base_summary(), _build_guard_scan_text(), _build_judge_prompt(), _bullet_text() (+47 more)

### Community 16 - "test_discovery.py"
Cohesion: 0.08
Nodes (39): fetch_ashby_jobs(), fetch_greenhouse_jobs(), fetch_lever_jobs(), _http_get_json(), infer_opportunity_type(), is_relevant_tech_role(), Direct ATS API harvester: scrapes Greenhouse, Ashby, and Lever career portals.…, Helper to fetch and parse JSON from a public endpoint. (+31 more)

### Community 17 - "cli.py"
Cohesion: 0.08
Nodes (41): callback, command, apply(), _bootstrap(), clean(), dashboard(), doctor(), events() (+33 more)

### Community 18 - "scorer.py"
Cohesion: 0.13
Nodes (14): _build_candidate_level(), _clean_optional_field(), _normalize_country(), _parse_score_response(), Job fit scoring: LLM-powered evaluation of candidate-job match quality. Scores…, Format the candidate's experience level for the scoring prompt. Scoring is done…, Strip a captured field and map a literal 'NULL' response to None. The scoring…, Parse the LLM's score response into structured data. Args: response: Raw LLM… (+6 more)

### Community 19 - "init_db"
Cohesion: 0.13
Nodes (25): discover(), Run specific or all discovery harvesters to find jobs, graduate schemes, and…, init_db(), Create the full jobs table with all columns from every pipeline stage. This is…, Store discovered jobs, skipping duplicates by URL. Args: conn: Database…, store_jobs(), Scrape configured Greenhouse, Ashby, and Lever employers and store results into…, run_direct_ats_discovery() (+17 more)

### Community 20 - "ApplyPilot"
Cohesion: 0.05
Nodes (39): Adding New Career Sites, Adding New Workday Employers, Bug Fixes and Features, Clone and Install, Code Style Guidelines, Contributing to ApplyPilot, Development Setup, How to Contribute (+31 more)

### Community 23 - "get_chrome_user_data"
Cohesion: 0.67
Nodes (3): get_chrome_user_data(), Path, Default Chrome user data directory, cross-platform.

### Community 26 - "ToolLeakGuard"
Cohesion: 0.08
Nodes (23): _company_tokens(), Lowercase word tokens from the job's company name. This codebase already treats…, Deterministic check: a tool/tech token in the job description but absent from…, Every job-description tool the candidate doesn't have that appears as a whole…, Raise ToolLeakViolation if a job-description tool the candidate doesn't have…, ToolLeakGuard, _bank(), _CleanClient (+15 more)

### Community 27 - "._bank"
Cohesion: 0.05
Nodes (38): Fact, NumericGuard, One verifiable, pre-written claim the LLM may select for a bullet., Deterministic, post-generation check: every number in the assembled resume text…, Raise NumericGuardViolation if any line contains a number that isn't in the…, check_no_cross_section_duplicates(), Hard assertion: no bullet's text may appear in more than one section of the…, _bank() (+30 more)

### Community 28 - "FactBank"
Cohesion: 0.12
Nodes (15): FactBank, Parses facts.yaml and is the sole gate on what quantified claims the tailoring…, Best-effort recovery for a plain-string bullet that has a digit but is actually…, All tier == 'verified' facts. The ONLY facts ever exposed to the LLM., Every number the tailoring output is allowed to contain: the union of every…, Verified facts worth offering the LLM for this job. Facts with no `use_when`…, Turn one LLM-output bullet into literal text. See resolve_bullet_ex for the…, Turn one LLM-output bullet into (literal text, fact id or None). A fact-… (+7 more)

### Community 29 - "facts.py"
Cohesion: 0.13
Nodes (14): _accept_reworded(), BulletPlacementViolation, _extract_numbers(), FactBankError, NumericGuardViolation, Exception, Verified-fact bank for resume tailoring. facts.yaml (repo root) is the ONLY…, Base class for fact-bank problems. (+6 more)

### Community 30 - "apply_eligibility_gate"
Cohesion: 0.19
Nodes (8): apply_eligibility_gate(), Deterministic removal of any REASONING sentence that credits the candidate with…, Deterministic hard-eligibility check, run after the LLM's own score and before…, _strip_fabricated_skill_sentences(), 0.9 does not satisfy a 1-year minimum -- an 11-month placement is under a year,…, Deterministic post-LLM enforcement: the model extracts what the posting says…, TestEligibilityGate, TestStripFabricatedSkillSentences

### Community 31 - "run_job"
Cohesion: 0.12
Nodes (19): Update the worker's state fields. Args: worker_id: Which worker to update.…, update_state(), _check_playwright_mcp(), gen_prompt(), _is_permanent_failure(), _make_mcp_config(), mark_result(), Path (+11 more)

### Community 32 - "load_profile"
Cohesion: 0.12
Nodes (25): load_profile(), Load user profile from ~/.applypilot/profile.json., check_listing_still_open(), Best-effort check for whether a job listing is still accepting applications,…, is_local_provider(), True when generation will hit a local (non-cloud) LLM_URL endpoint. Mirrors…, cover_letter_one(), _generate_one_cover_letter() (+17 more)

### Community 33 - "_strip_preamble"
Cohesion: 0.21
Nodes (7): Remove LLM preamble before 'Dear Hiring Manager,' if present. Gemini and other…, Truncate anything after the sign-off line. Models occasionally add notes/P.S.…, _strip_after_signoff(), _strip_preamble(), An incidental earlier mention of the name must not truncate the real body that…, endeared'/'dearest' mid-preamble must not be mistaken for the letter's real…, TestStripHelpers

### Community 34 - "run_workday_discovery"
Cohesion: 0.19
Nodes (14): load_search_config(), Load search configuration from ~/.applypilot/searches.yaml., build_scrape_targets(), _load_location_filter(), load_sites(), Main entry point for AI-powered smart extraction. Loads sites from…, Load location accept/reject lists from search config., Load scraping target sites from config/sites.yaml. (+6 more)

### Community 35 - "detail.py"
Cohesion: 0.12
Nodes (23): clean_content_html(), clean_description(), collect_detail_intelligence(), extract_apply_url_deterministic(), extract_description_deterministic(), extract_from_json_ld(), extract_main_content(), extract_with_llm() (+15 more)

### Community 36 - "[0.2.0] - 2026-02-17"
Cohesion: 0.25
Nodes (7): [0.1.0] - 2026-02-17, [0.2.0] - 2026-02-17, Added, Added, Changed, Changelog, Fixed

### Community 37 - "end_run"
Cohesion: 0.21
Nodes (12): mark_job(), Manually mark a job's apply status in the database. Records this as a completed…, end_run(), Record the start of one pipeline stage invocation. Args: conn: Database…, Record the end of a pipeline stage invocation. Args: conn: Database connection.…, start_run(), Stage: Detail enrichment — scrape full descriptions and apply URLs., Stage: LLM scoring — assign fit scores 1-10. (+4 more)

### Community 38 - "list_jobs"
Cohesion: 0.14
Nodes (11): Console, list_jobs(), Fetch scored jobs for terminal display, filtered and sorted by fit. Args:…, Render one Rich panel per job with fit score, company context, tailored…, render_jobs(), fixture, Tests for terminal_view.list_jobs / render_jobs (the `applypilot jobs` command)., Isolated scratch DB with a few jobs at different fit scores/sites, never… (+3 more)

### Community 39 - "critic.py"
Cohesion: 0.09
Nodes (20): _build_cv_critic_user_message(), _build_letter_critic_user_message(), combined_critic_score(), CriticResult, evaluate_cv_observations(), evaluate_letter_observations(), Extraction-only "critic" pass over a tailored CV and cover letter. Catches…, Apply fixed, code-side thresholds to the model's raw extraction. Never trusts… (+12 more)

### Community 44 - "validate_cover_letter"
Cohesion: 0.08
Nodes (24): has_bad_signoff(), has_dangling_reference(), has_lifted_jd_span(), has_repeated_phrase(), _is_mostly_filler(), True if a body paragraph opens with a back-reference to a sentence that isn't…, True if an n-gram is mostly stopwords/connective filler ('in order to be able…, Return the first phrase of `min_words` or more that appears more than once in… (+16 more)

### Community 45 - "get_client"
Cohesion: 0.40
Nodes (5): _detect_provider(), get_client(), Unified LLM client for ApplyPilot. Auto-detects provider from environment:…, Return (base_url, model, api_key) based on environment variables. Reads env at…, Return (or create) the module-level LLMClient singleton.

### Community 46 - "cover_letter.py"
Cohesion: 0.13
Nodes (21): get_locale_style(), Infer document terminology and layout conventions from the candidate's country.…, format_facts_block(), Render verified facts as an id-keyed list for a prompt. Shared by resume…, _build_cover_letter_prompt(), _check_company_mentioned(), generate_cover_letter(), _normalize_greeting_spacing() (+13 more)

### Community 48 - "view.py"
Cohesion: 0.13
Nodes (19): Clear one job's apply status back to pending, e.g. after a wrong manual mark or…, reset_job(), hide_job(), Mark a job hidden so it stops showing by default and stops being picked up for…, Reverse hide_job() -- the job becomes visible and eligible for the pipeline…, unhide_job(), generate_dashboard(), get_tailor_status() (+11 more)

### Community 49 - "load_location_focus"
Cohesion: 0.17
Nodes (12): load_location_focus(), Load the optional `location_focus` section from searches.yaml. A temporary,…, classify_location(), get_jobs_by_stage(), _is_relevant_remote(), _location_priority_tier(), Register the `loc_priority(location)` SQL function used to rank/filter jobs by…, True if a (lowercased) location's "remote" claim is UK/NI-relevant or… (+4 more)

### Community 50 - "_store_jobs_filtered"
Cohesion: 0.40
Nodes (5): _location_ok(), Connection, Check if a job location passes the user's location filter., Store jobs with location filtering. Returns (new, existing)., _store_jobs_filtered()

### Community 52 - "get_connection"
Cohesion: 0.22
Nodes (8): Reset all failed jobs so they can be retried. Returns: Number of jobs reset., reset_failed(), close_connection(), get_connection(), Path, Get a thread-local cached SQLite connection with WAL mode enabled. Each thread…, Close the cached connection for the current thread., Terminal job-detail listing: fit score and company context for individual jobs,…

### Community 55 - ".load"
Cohesion: 0.15
Nodes (9): FactBankLoadError, Path, Raised when facts.yaml fails integrity checks at load time., A known gap: a plausible claim that needs a real value filled in before it can…, Parse facts.yaml into Facts, validating every verified fact's numbers against…, Unverified entries pending a real value, for a CLI prompt flow., UnfilledFact, A verified fact whose declared number isn't backed by its own evidence string… (+1 more)

## Knowledge Gaps
- **37 isolated node(s):** `applypilot`, `graphify`, `Workflow: graphify`, `Added`, `Fixed` (+32 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_connection()` connect `get_connection` to `smartextract.py`, `workday.py`, `database.py`, `jobspy.py`, `launcher.py`, `pipeline.py`, `main`, `tailor.py`, `test_discovery.py`, `cli.py`, `scorer.py`, `init_db`, `run_job`, `load_profile`, `detail.py`, `end_run`, `list_jobs`, `cover_letter.py`, `view.py`, `load_location_focus`?**
  _High betweenness centrality (0.174) - this node is a cross-community bridge._
- **Why does `FactBank` connect `FactBank` to `load_profile`, `cover_letter.py`, `tailor.py`, `.load`, `ToolLeakGuard`, `._bank`, `facts.py`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Why does `ToolLeakGuard` connect `ToolLeakGuard` to `validator.py`, `cover_letter.py`, `tailor.py`, `scorer.py`, `apply_eligibility_gate`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 22 inferred relationships involving `FactBank` (e.g. with `_build_cover_letter_prompt()` and `cover_letter_one()`) actually correct?**
  _`FactBank` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `tailor_resume()` (e.g. with `BulletPlacementViolation` and `FactBank`) actually correct?**
  _`tailor_resume()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `applypilot`, `graphify`, `Workflow: graphify` to the rest of the system?**
  _37 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `smartextract.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10574712643678161 - nodes in this community are weakly interconnected._