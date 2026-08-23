# Graph Report - ApplyPilot-main  (2026-08-23)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 461 nodes · 863 edges · 26 communities (24 shown, 2 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 11 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

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
- pipeline.py
- dashboard.py
- pdf.py
- LLMClient
- worker_loop
- run_wizard
- cli.py
- init_db
- _bootstrap
- score_job
- main
- get_chrome_user_data
- scoring/__init__.py
- applypilot

## God Nodes (most connected - your core abstractions)
1. `get_connection()` - 33 edges
2. `init_db()` - 21 edges
3. `get_client()` - 16 edges
4. `build_prompt()` - 14 edges
5. `convert_to_pdf()` - 13 edges
6. `_run_one_site()` - 12 edges
7. `worker_loop()` - 12 edges
8. `run_pipeline()` - 12 edges
9. `tailor_resume()` - 12 edges
10. `run_job()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `build_prompt()` --calls--> `load_search_config()`  [EXTRACTED]
  src/applypilot/apply/prompt.py → src/applypilot/config.py
- `run_discovery()` --calls--> `load_search_config()`  [EXTRACTED]
  src/applypilot/discovery/jobspy.py → src/applypilot/config.py
- `_load_location_filter()` --calls--> `load_search_config()`  [EXTRACTED]
  src/applypilot/discovery/workday.py → src/applypilot/config.py
- `run_workday_discovery()` --calls--> `load_search_config()`  [EXTRACTED]
  src/applypilot/discovery/workday.py → src/applypilot/config.py
- `_run_discover()` --calls--> `run_smart_extract()`  [EXTRACTED]
  src/applypilot/pipeline.py → src/applypilot/discovery/smartextract.py

## Import Cycles
- None detected.

## Communities (26 total, 2 thin omitted)

### Community 0 - "smartextract.py"
Cohesion: 0.06
Nodes (49): load_search_config(), Load search configuration from ~/.applypilot/searches.yaml., ask_llm(), build_scrape_targets(), clean_card_html(), clean_page_html(), collect_page_intelligence(), execute_api_response() (+41 more)

### Community 1 - "workday.py"
Cohesion: 0.06
Nodes (37): HTMLParser, fetch_details(), _fetch_one_detail(), _HTMLStripper, load_employers(), _load_location_filter(), _location_ok(), _process_one() (+29 more)

### Community 2 - "tailor.py"
Cohesion: 0.07
Nodes (40): Stage: Resume tailoring — generate tailored resumes for high-fit jobs., _run_tailor(), _build_cover_letter_prompt(), generate_cover_letter(), Remove LLM preamble before 'Dear Hiring Manager,' if present. Gemini and other…, Generate a cover letter with fresh context on each retry + auto-sanitize. Same…, Build the cover letter system prompt from the user's profile. All personal…, _strip_preamble() (+32 more)

### Community 3 - "detail.py"
Cohesion: 0.08
Nodes (38): clean_content_html(), clean_description(), collect_detail_intelligence(), extract_apply_url_deterministic(), extract_description_deterministic(), extract_from_json_ld(), extract_main_content(), _load_base_urls() (+30 more)

### Community 4 - "get_connection"
Cohesion: 0.13
Nodes (23): load_profile(), ApplyPilot configuration: paths, platform detection, user data., Load user profile from ~/.applypilot/profile.json., close_connection(), ensure_columns(), get_connection(), get_jobs_by_stage(), Connection (+15 more)

### Community 5 - "jobspy.py"
Cohesion: 0.12
Nodes (22): Store discovered jobs, skipping duplicates by URL. Args: conn: Database…, store_jobs(), _full_crawl(), _load_location_config(), _location_ok(), parse_proxy(), Connection, JobSpy-based job discovery: searches Indeed, LinkedIn, Glassdoor, ZipRecruiter.… (+14 more)

### Community 6 - "chrome.py"
Cohesion: 0.14
Nodes (21): Popen, cleanup_on_exit(), cleanup_worker(), kill_all_chrome(), _kill_on_port(), _kill_process_tree(), launch_chrome(), Path (+13 more)

### Community 7 - "prompt.py"
Cohesion: 0.13
Nodes (20): _build_captcha_section(), _build_hard_rules(), _build_location_check(), _build_profile_summary(), build_prompt(), _build_salary_section(), _build_screening_section(), Prompt builder for the autonomous job application agent. Constructs the full… (+12 more)

### Community 8 - "launcher.py"
Cohesion: 0.11
Nodes (19): Apply pipeline: Chrome management, prompt building, orchestration, and…, acquire_job(), _load_blocked(), mark_job(), Apply orchestration: acquire jobs, spawn Claude Code sessions, track results.…, Manually mark a job's apply status in the database. Args: url: Job URL to mark.…, Reset all failed jobs so they can be retried. Returns: Number of jobs reset., Atomically acquire the next job to apply to. Args: target_url: Apply to a… (+11 more)

### Community 9 - "pipeline.py"
Cohesion: 0.12
Nodes (14): Event, _count_pending(), ApplyPilot Pipeline Orchestrator. Runs pipeline stages in sequence or…, Stage: LLM scoring — assign fit scores 1-10., Stage: Cover letter generation., Thread-safe tracker for which stages have finished producing work., Count pending work items for a stage., Run a single stage in streaming mode: loop until upstream done + no work. For… (+6 more)

### Community 10 - "dashboard.py"
Cohesion: 0.13
Nodes (18): Group, get_state(), get_totals(), init_worker(), Rich live dashboard for the apply pipeline. Displays real-time worker status,…, Build the Rich table showing all worker statuses. Returns: A Rich Table object…, Render the dashboard table plus the recent events panel. Returns: A Rich Group…, Compute aggregate totals across all workers. Returns: Dict with keys: applied,… (+10 more)

### Community 11 - "pdf.py"
Cohesion: 0.14
Nodes (18): Stage: PDF conversion — convert tailored resumes and cover letters to PDF., _run_pdf(), batch_convert(), build_html(), convert_to_pdf(), parse_entries(), parse_resume(), parse_skills() (+10 more)

### Community 12 - "LLMClient"
Cohesion: 0.14
Nodes (10): Exception, Response, _GeminiCompatForbidden, LLMClient, Call the native Gemini generateContent API. Used automatically when the OpenAI-…, Call the OpenAI-compatible endpoint., Send a chat completion request and return the assistant message text., Convenience: single user prompt -> assistant response. (+2 more)

### Community 13 - "worker_loop"
Cohesion: 0.14
Nodes (17): add_event(), Add a timestamped event to the scrolling event log. Args: msg: Rich markup…, gen_prompt(), _is_permanent_failure(), _make_mcp_config(), mark_result(), Path, Update a job's apply status in the database. (+9 more)

### Community 14 - "run_wizard"
Cohesion: 0.17
Nodes (15): ensure_dirs(), Create all required directories., ApplyPilot first-time setup wizard. Interactive flow that creates…, Generate a searches.yaml from user input., Ask about AI scoring/tailoring — optional LLM configuration., Configure autonomous job application (requires Claude Code CLI)., Run the full interactive setup wizard., Prompt for resume file and copy into APP_DIR. (+7 more)

### Community 15 - "cli.py"
Cohesion: 0.20
Nodes (12): doctor(), ApplyPilot CLI — the main entry point., Check your setup and diagnose missing requirements., check_tier(), get_chrome_path(), get_tier(), load_env(), Load environment variables from ~/.applypilot/.env if it exists. (+4 more)

### Community 16 - "init_db"
Cohesion: 0.15
Nodes (15): Show pipeline statistics from the database., status(), get_stats(), init_db(), Return job counts by pipeline stage. Provides a snapshot of how many jobs are…, Create the full jobs table with all columns from every pipeline stage. This is…, Run smart extract on all targets. Sequential by default. When workers > 1,…, _run_all() (+7 more)

### Community 17 - "_bootstrap"
Cohesion: 0.18
Nodes (13): command, apply(), _bootstrap(), dashboard(), init(), Run pipeline stages: discover, enrich, score, tailor, cover, pdf., Launch auto-apply to submit job applications., Generate and open the HTML dashboard in your browser. (+5 more)

### Community 18 - "score_job"
Cohesion: 0.33
Nodes (6): _build_candidate_level(), _parse_score_response(), Score a single job against the resume. Args: resume_text: The candidate's full…, Format the candidate's experience level for the scoring prompt. Scoring is done…, Parse the LLM's score response into structured data. Args: response: Raw LLM…, score_job()

### Community 19 - "main"
Cohesion: 0.67
Nodes (3): callback, main(), ApplyPilot — AI-powered end-to-end job application pipeline.

### Community 20 - "get_chrome_user_data"
Cohesion: 0.67
Nodes (3): get_chrome_user_data(), Path, Default Chrome user data directory, cross-platform.

## Knowledge Gaps
- **1 isolated node(s):** `applypilot`
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_connection()` connect `get_connection` to `smartextract.py`, `workday.py`, `tailor.py`, `detail.py`, `jobspy.py`, `launcher.py`, `pipeline.py`, `worker_loop`, `cli.py`, `init_db`, `_bootstrap`?**
  _High betweenness centrality (0.189) - this node is a cross-community bridge._
- **Why does `init_db()` connect `init_db` to `smartextract.py`, `workday.py`, `detail.py`, `get_connection`, `jobspy.py`, `pipeline.py`, `cli.py`, `_bootstrap`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Why does `get_client()` connect `smartextract.py` to `tailor.py`, `detail.py`, `get_connection`, `LLMClient`, `score_job`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **What connects `applypilot` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `smartextract.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0611764705882353 - nodes in this community are weakly interconnected._
- **Should `workday.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06423034330011074 - nodes in this community are weakly interconnected._
- **Should `tailor.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07084785133565621 - nodes in this community are weakly interconnected._