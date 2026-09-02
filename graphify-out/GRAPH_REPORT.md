# Graph Report - ApplyPilot-main  (2026-09-02)

## Corpus Check
- 62 files · ~123,356 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1429 nodes · 2912 edges · 76 communities (72 shown, 4 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 124 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a9fe4cbd`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- tailor.py
- test_prefilter.py
- ._run
- get_connection
- smartextract.py
- evaluate_cv_observations
- chrome.py
- view.py
- FactBank
- _StageTracker
- test_cohort.py
- detail.py
- LLMClient
- _process_one
- pdf.py
- worker_loop
- test_discovery.py
- _bootstrap
- scorer.py
- _repair_summary
- Contributing to ScoutPilot
- init_db
- prompt.py
- build_bullet_floor_map
- run_wizard
- validator.py
- launcher.py
- _kraydel_multiparty_fact
- critic.py
- database.py
- check_no_cross_section_duplicates
- TestSearchHaystack
- get_client
- find_header_restating_bullets
- main
- pipeline.py
- [0.2.0] - 2026-02-17
- run_job
- list_jobs
- .load
- rules/graphify.md
- workflows/graphify.md
- ToolLeakGuard
- validate_cover_letter
- NumericGuard
- _load_yaml_cached
- drop_unverifiable_quotes
- end_run
- get_jobs_by_stage
- scoring/__init__.py
- combined_critic_score
- build_corpus.py
- company_pages.py
- scoutpilot
- cover_letter.py
- test_critic.py
- test_enrichment.py
- render_jobs
- facts.py
- get_tier
- format_facts_block
- find_summary_duplicate_bullets
- scoring_queue
- _HTMLStripper
- _store_jobs_filtered
- test_facts.py
- test_company_pages.py
- test_grad_boards.py
- close_connection
- cohort.py
- ._bank
- cli.py
- run_pipeline
- get_chrome_user_data

## God Nodes (most connected - your core abstractions)
1. `get_connection()` - 66 edges
2. `FactBank` - 49 edges
3. `init_db()` - 42 edges
4. `tailor_resume()` - 32 edges
5. `store_jobs()` - 31 edges
6. `Fact` - 28 edges
7. `evaluate_prefilter()` - 27 edges
8. `evaluate_cv_observations()` - 22 edges
9. `apply_eligibility_gate()` - 22 edges
10. `TestEligibilityGate` - 22 edges

## Surprising Connections (you probably didn't know these)
- `test_rediscovery_does_not_revive_applied_row()` --calls--> `store_jobs()`  [EXTRACTED]
  tests/test_cohort.py → src/scoutpilot/database.py
- `test_run_expands_ats_and_stores_pointers()` --calls--> `get_jobs_by_stage()`  [EXTRACTED]
  tests/test_company_pages.py → src/scoutpilot/database.py
- `TestFactBankLoad` --uses--> `FactBankLoadError`  [INFERRED]
  tests/test_facts.py → src/scoutpilot/facts.py
- `TestNumericGuard` --uses--> `NumericGuardViolation`  [INFERRED]
  tests/test_facts.py → src/scoutpilot/facts.py
- `TestCrossSectionDuplicateAssertion` --uses--> `BulletPlacementViolation`  [INFERRED]
  tests/test_facts.py → src/scoutpilot/facts.py

## Import Cycles
- None detected.

## Communities (76 total, 4 thin omitted)

### Community 0 - "tailor.py"
Cohesion: 0.06
Nodes (51): Split arbitrary CV/resume text into sections keyed by ALL-CAPS headers. Unlike…, split_sections(), _apply_canonical_entries(), assemble_resume_text(), _base_summary(), _build_guard_scan_text(), _build_tailor_prompt(), _bullet_text() (+43 more)

### Community 1 - "test_prefilter.py"
Cohesion: 0.12
Nodes (36): _is_relevant_remote(), True if a (lowercased) location's "remote" claim is UK/NI-relevant or…, _check_experience(), _check_location(), _check_seniority(), _contains_term(), evaluate_prefilter(), prefilter_breakdown() (+28 more)

### Community 2 - "._run"
Cohesion: 0.12
Nodes (10): Shipping is the LAST-attempt behaviour, not the first: while attempts remain, a…, Once canonical_entries.experience is configured, it's exhaustive: an EXPERIENCE…, The exact incident: the model filed the candidate's own degree as a job once…, The same unmatched-entry situation in PROJECTS is kept, not rejected -- a…, TECHNICAL SKILLS renders only what the profile actually declares -- the LLM's…, The exact incident: the model added 'LangChain (agent frameworks)' and…, The rejected entry is already deleted from the data by the time the error is…, TestCanonicalExperienceRejection (+2 more)

### Community 3 - "get_connection"
Cohesion: 0.09
Nodes (29): clean_non_tech_jobs(), ensure_columns(), find_duplicate_groups(), get_connection(), get_stats(), hide_job(), _normalize_title(), Connection (+21 more)

### Community 4 - "smartextract.py"
Cohesion: 0.08
Nodes (41): load_search_config(), Load search configuration from ~/.applypilot/searches.yaml. Cached on the…, ask_llm(), build_scrape_targets(), clean_card_html(), clean_page_html(), collect_page_intelligence(), execute_api_response() (+33 more)

### Community 5 - "evaluate_cv_observations"
Cohesion: 0.11
Nodes (13): evaluate_cv_observations(), Apply fixed, code-side thresholds to the model's raw extraction. Never trusts…, On three bullets a single NONE is already a third: the fraction carries no…, The exact incident: Revolut round 2 (2026-08-26) was flagged 6/11 while a human…, The counterpart the exemption must not swallow: round 1's Java Software…, The exact incident: 'VIOFEEL has 1 bullet, below the minimum of 2' landed on 6…, The floor drops only where the material genuinely runs out. Kraydel has nine…, The model quotes the header back out of the rendered CV; only case and spacing… (+5 more)

### Community 6 - "chrome.py"
Cohesion: 0.14
Nodes (21): Popen, cleanup_on_exit(), cleanup_worker(), kill_all_chrome(), _kill_on_port(), _kill_process_tree(), launch_chrome(), Path (+13 more)

### Community 7 - "view.py"
Cohesion: 0.05
Nodes (40): Row, Clear one job's apply status back to pending, e.g. after a wrong manual mark or…, reset_job(), classify_location(), derive_company(), description_shingles(), group_near_identical(), _location_priority_tier() (+32 more)

### Community 8 - "FactBank"
Cohesion: 0.08
Nodes (26): _accept_reworded(), Fact, FactBank, One verifiable, pre-written claim the LLM may select for a bullet., A known gap: a plausible claim that needs a real value filled in before it can…, Parses facts.yaml and is the sole gate on what quantified claims the tailoring…, Best-effort recovery for a plain-string bullet that has a digit but is actually…, All tier == 'verified' facts. The ONLY facts ever exposed to the LLM. (+18 more)

### Community 9 - "_StageTracker"
Cohesion: 0.15
Nodes (9): Event, _count_pending(), Thread-safe tracker for which stages have finished producing work., Count pending work items for a stage., Run a single stage in streaming mode: loop until upstream done + no work. For…, Execute stages concurrently with DB as conveyor belt., _run_stage_streaming(), _run_streaming() (+1 more)

### Community 10 - "test_cohort.py"
Cohesion: 0.29
Nodes (9): infer_cohort_start(), Normalised start marker, or None if the posting doesn't state one. Only years…, parametrize, Tests for start-date / cohort inference (discovery/cohort.py) and the…, test_infer_cohort_start_from_title(), test_infer_cohort_start_hits(), test_infer_cohort_start_misses(), test_rediscovery_does_not_revive_applied_row() (+1 more)

### Community 11 - "detail.py"
Cohesion: 0.09
Nodes (36): browser_title(), clean_content_html(), clean_description(), collect_detail_intelligence(), extract_apply_url_deterministic(), extract_description_deterministic(), extract_from_json_ld(), extract_main_content() (+28 more)

### Community 12 - "LLMClient"
Cohesion: 0.13
Nodes (11): Response, _GeminiCompatForbidden, LLMClient, Exception, Thin LLM client supporting OpenAI-compatible and native Gemini endpoints. For…, Call the native Gemini generateContent API. Used automatically when the OpenAI-…, Call the OpenAI-compatible endpoint. json_schema, when given, is passed as…, Call Ollama's native /api/chat, optionally with a JSON-schema `format`.… (+3 more)

### Community 13 - "_process_one"
Cohesion: 0.09
Nodes (23): fetch_details(), _fetch_one_detail(), _location_ok(), _process_one(), Connection, Convert HTML to plain text., Open a URL using the configured opener (with or without proxy)., Search jobs via Workday CXS API. Returns JSON with total + jobPostings. (+15 more)

### Community 14 - "pdf.py"
Cohesion: 0.11
Nodes (23): build_cover_letter_html(), build_html(), _cover_letter_font_faces(), _cv_font_faces(), _fit_resume_html(), _font_b64(), _font_face(), parse_entries() (+15 more)

### Community 15 - "worker_loop"
Cohesion: 0.15
Nodes (14): add_event(), Update the worker's state fields. Args: worker_id: Which worker to update.…, Add a timestamped event to the scrolling event log. Args: msg: Rich markup…, update_state(), _is_permanent_failure(), mark_result(), Record an attempt's outcome and mirror it onto the job., Release the in_progress lock without recording a terminal outcome. Used when a… (+6 more)

### Community 16 - "test_discovery.py"
Cohesion: 0.08
Nodes (32): fetch_ashby_jobs(), fetch_greenhouse_jobs(), fetch_lever_jobs(), _http_get_json(), infer_opportunity_type(), Helper to fetch and parse JSON from a public endpoint., Fetch jobs from a Greenhouse board via its public JSON API. Endpoint:…, Fetch jobs from an Ashby board via its public JSON API. Endpoint:… (+24 more)

### Community 17 - "_bootstrap"
Cohesion: 0.09
Nodes (32): command, add(), apply(), archive_discovery(), _bootstrap(), clean(), events(), init() (+24 more)

### Community 18 - "scorer.py"
Cohesion: 0.05
Nodes (37): apply_eligibility_gate(), _build_candidate_level(), _candidate_is_unrestricted(), _clean_optional_field(), _countries_in_text(), _country_in_text(), _normalize_country(), _parse_score_response() (+29 more)

### Community 19 - "_repair_summary"
Cohesion: 0.28
Nodes (7): Rewrite `resolved_data["summary"]` in place if it fell into a rut or just…, _repair_summary(), _Client, The duplication defect fires on nearly every CV, so it repairs one field rather…, Describing the rule isn't enough -- the model has to see the sentences it is…, A rewrite is LLM-authored text like any other and gets the same numeric…, TestRepairSummary

### Community 20 - "Contributing to ScoutPilot"
Cohesion: 0.08
Nodes (23): Adding New Career Sites, Adding New Workday Employers, Bug Fixes and Features, Clone and Install, Code Style Guidelines, Contributing to ScoutPilot, Development Setup, How to Contribute (+15 more)

### Community 21 - "init_db"
Cohesion: 0.07
Nodes (37): init_db(), Create the full jobs table with all columns from every pipeline stage. This is…, _full_crawl(), _load_location_config(), _location_ok(), parse_proxy(), Connection, Store JobSpy DataFrame results into the DB. Returns (new, existing). (+29 more)

### Community 22 - "prompt.py"
Cohesion: 0.15
Nodes (19): _build_captcha_section(), _build_hard_rules(), _build_location_check(), _build_profile_summary(), build_prompt(), _build_salary_section(), _build_screening_section(), Prompt builder for the autonomous job application agent. Constructs the full… (+11 more)

### Community 23 - "build_bullet_floor_map"
Cohesion: 0.30
Nodes (6): build_bullet_floor_map(), Per-entry minimum bullet counts for the critic, derived from how much real…, build_bullet_floor_map lives in tailor.py but exists only to feed…, The critic counts bullets under PROJECTS as well, so a floor is needed there or…, No verified material behind an entry means nothing to ask for -- the guard must…, TestBuildBulletFloorMap

### Community 24 - "run_wizard"
Cohesion: 0.17
Nodes (15): ensure_dirs(), Create all required directories., ScoutPilot first-time setup wizard. Interactive flow that creates…, Generate a searches.yaml from user input., Ask about AI scoring/tailoring — optional LLM configuration., Configure autonomous job application (requires Claude Code CLI)., Run the full interactive setup wizard., Prompt for resume file and copy into APP_DIR. (+7 more)

### Community 25 - "validator.py"
Cohesion: 0.16
Nodes (12): _build_skills_set(), find_fabricated_numbers(), Exception, Resume and cover letter validation: banned words, fabrication detection,…, Find number-bearing claims in tailored text with no basis in the original.…, Build the set of allowed skills from the profile's skills_boundary., Validate individual JSON fields from an LLM-generated tailored resume. Args:…, Programmatic validation of a tailored resume against the user's profile. Args:… (+4 more)

### Community 26 - "launcher.py"
Cohesion: 0.15
Nodes (15): Apply pipeline: Chrome management, prompt building, orchestration, and…, acquire_job(), _load_blocked(), Apply orchestration: acquire jobs, spawn Claude Code sessions, track results.…, Reset all failed jobs so they can be retried. Returns: Number of jobs reset., Atomically acquire the next job to apply to and open an attempt for it. Args:…, reset_failed(), is_manual_ats() (+7 more)

### Community 27 - "_kraydel_multiparty_fact"
Cohesion: 0.22
Nodes (7): _kraydel_multiparty_fact(), Bullets that carry no fact id must contain no digits -- enforced in code, not…, Mirrors the real kraydel.multiparty_calls entry in facts.yaml., A plausible-but-unevidenced fact that must never reach the LLM., The core guarantee: relevant_facts() (what actually goes into the LLM prompt)…, TestFactBankRejectsUnverified, _unverified_fact()

### Community 28 - "critic.py"
Cohesion: 0.21
Nodes (13): _build_cv_critic_user_message(), _build_letter_critic_user_message(), CriticResult, _is_differentiator_bullet(), _normalize_header(), Extraction-only "critic" pass over a tailored CV and cover letter. Catches…, Loose key for matching a header the model quoted back out of the CV against the…, score is COMPUTED from discrete findings (10.0 minus each finding's weight,… (+5 more)

### Community 29 - "database.py"
Cohesion: 0.12
Nodes (26): datetime, _deep_merge(), load_prefilter_config(), ScoutPilot configuration: paths, platform detection, user data., Recursively merge `over` onto a copy of `base` (dict values only)., Ingest pre-filter + scoring-queue budget config (config/prefilter.yaml). A…, ScoutPilot database layer: schema, migrations, stats, and connection helpers.…, Store discovered jobs, skipping duplicates by URL. Args: conn: Database… (+18 more)

### Community 30 - "check_no_cross_section_duplicates"
Cohesion: 0.15
Nodes (11): check_no_cross_section_duplicates(), _normalize_bullet_for_dup_check(), Hard assertion: the same claim may not appear twice anywhere in the assembled…, check_no_cross_section_duplicates is the hard backstop: even if ownership/dedup…, Exact-text matching alone missed this live 2026-08-26: the same fact, worded…, The blind spot the projects-vs-experience loop had by construction: two bullets…, The exact pairing named in _likely_fact_id's docstring: 'Built dual ML…, Same section, two different headings -- also invisible to the old loop, which… (+3 more)

### Community 31 - "TestSearchHaystack"
Cohesion: 0.09
Nodes (14): fixture, Dashboard behaviour: CV/cover-letter independence, and the two things that made…, searches.yaml is hand-edited, so the cache is keyed on the file's own…, applyFilters() matches the search term against `card.textContent`. On…, A cover-letter failure used to set the job's single status field to "error".…, The real invariant. A description that is neither in the DOM nor reachable by…, A file:// page has no server, so its search is still the textContent one and…, A file:// page cannot reach /api/... -- every such call fails as "Failed to… (+6 more)

### Community 32 - "get_client"
Cohesion: 0.22
Nodes (9): _detect_provider(), get_client(), Unified LLM client for ScoutPilot. Auto-detects provider from environment:…, Return (base_url, model, api_key) based on environment variables. Reads env at…, Return (or create) the module-level LLMClient singleton., _build_judge_prompt(), judge_tailored_resume(), LLM judge layer: catches subtle fabrication that programmatic checks miss.… (+1 more)

### Community 33 - "find_header_restating_bullets"
Cohesion: 0.18
Nodes (9): _entry_span_months(), find_header_restating_bullets(), Length in months of the first date range in `text`, or None. An open-ended…, Bullets that only say again what their own entry header already says. This…, The code check that replaced the model clause., The exact bullet the model never flagged: '11-month industry placement ...'…, 1st place, QUB Dragon's Den 2024' under 'Apr 2024 - Mar 2026' shares a year and…, Aug 2026 - Present' has no fixed span, so a duration claim against it can't be… (+1 more)

### Community 34 - "main"
Cohesion: 0.15
Nodes (16): Group, get_state(), get_totals(), init_worker(), Rich live dashboard for the apply pipeline. Displays real-time worker status,…, Build the Rich table showing all worker statuses. Returns: A Rich Table object…, Render the dashboard table plus the recent events panel. Returns: A Rich Group…, Compute aggregate totals across all workers. Returns: Dict with keys: applied,… (+8 more)

### Community 35 - "pipeline.py"
Cohesion: 0.08
Nodes (33): discover(), Run specific or all discovery harvesters to find jobs, graduate schemes, and…, Scrape configured Greenhouse, Ashby, and Lever employers and store results into…, run_direct_ats_discovery(), Run search operator discovery against ATS domains and funded training…, run_dorking_discovery(), fetch_comment_item(), find_latest_who_is_hiring_story() (+25 more)

### Community 36 - "[0.2.0] - 2026-02-17"
Cohesion: 0.25
Nodes (7): [0.1.0] - 2026-02-17, [0.2.0] - 2026-02-17, Added, Added, Changed, Changelog, Fixed

### Community 37 - "run_job"
Cohesion: 0.14
Nodes (15): _check_playwright_mcp(), gen_prompt(), _make_mcp_config(), Path, Generate a prompt file and print the Claude CLI command for manual debugging.…, Inspect a system/init stream-json event for playwright MCP health. Browser…, Spawn a Claude Code session for one job application. Returns: Tuple of…, Build MCP config dict for a specific CDP port. (+7 more)

### Community 38 - "list_jobs"
Cohesion: 0.21
Nodes (7): list_jobs(), Fetch scored jobs for terminal display, filtered and sorted by fit. Args:…, fixture, Tests for terminal_view.list_jobs / render_jobs (the `scoutpilot jobs` command)., Isolated scratch DB with a few jobs at different fit scores/sites, never…, scratch_db(), TestListJobs

### Community 39 - ".load"
Cohesion: 0.13
Nodes (14): check_listing_still_open(), Best-effort check for whether a job listing is still accepting applications,…, Path, Parse facts.yaml into Facts, validating every verified fact's numbers against…, is_local_provider(), True when generation will hit a local (non-cloud) LLM_URL endpoint. Mirrors…, Tailor a resume for one job: liveness check, LLM call, file writes, PDF…, Tailor a resume for exactly one job, by URL, regardless of its current… (+6 more)

### Community 43 - "ToolLeakGuard"
Cohesion: 0.06
Nodes (31): Remove LLM preamble before 'Dear Hiring Manager,' if present. Gemini and other…, Truncate anything after the sign-off line. Models occasionally add notes/P.S.…, _strip_after_signoff(), _strip_preamble(), _company_tokens(), Lowercase word tokens from the job's company name. This codebase already treats…, Deterministic check: a tool/tech token in the job description but absent from…, Every job-description tool the candidate doesn't have that appears as a whole… (+23 more)

### Community 44 - "validate_cover_letter"
Cohesion: 0.08
Nodes (24): has_bad_signoff(), has_dangling_reference(), has_lifted_jd_span(), has_repeated_phrase(), _is_mostly_filler(), True if a body paragraph opens with a back-reference to a sentence that isn't…, True if an n-gram is mostly stopwords/connective filler ('in order to be able…, Return the first phrase of `min_words` or more that appears more than once in… (+16 more)

### Community 45 - "NumericGuard"
Cohesion: 0.19
Nodes (8): NumericGuard, Deterministic, post-generation check: every number in the assembled resume text…, Raise NumericGuardViolation if any line contains a number that isn't in the…, _qualitative_fact(), Canonical example: an injected, unevidenced 500 must be caught., The real 4-to-9 participant fact must pass cleanly., A zero-number verified fact (mirrors kraydel.audit_system)., TestNumericGuard

### Community 46 - "_load_yaml_cached"
Cohesion: 0.14
Nodes (14): load_ats_employers(), load_base_urls(), load_company_pages_config(), load_grad_boards_config(), load_schemes_config(), load_sites_config(), _load_yaml_cached(), Parse `path` as YAML, reusing the previous parse while it is unchanged. Returns… (+6 more)

### Community 47 - "drop_unverifiable_quotes"
Cohesion: 0.21
Nodes (8): drop_unverifiable_quotes(), _quote_key(), Normalised form for checking a model-supplied quote against the CV. Case and…, Remove any model-quoted bullet that does not actually occur in the CV. The…, The guard that keeps a finding from resting on a quote the CV does not contain.…, The model quotes bullets as rendered; resolved bullets have no dash. Stripping…, Documented consequence of the rule as specified: containment is checked against…, TestDropUnverifiableQuotes

### Community 48 - "end_run"
Cohesion: 0.21
Nodes (12): mark_job(), Manually mark a job's apply status in the database. Records this as a completed…, end_run(), Record the start of one pipeline stage invocation. Args: conn: Database…, Record the end of a pipeline stage invocation. Args: conn: Database connection.…, start_run(), Stage: Detail enrichment — scrape full descriptions and apply URLs., Stage: LLM scoring — assign fit scores 1-10. (+4 more)

### Community 49 - "get_jobs_by_stage"
Cohesion: 0.20
Nodes (11): archive_discovery_results(), get_jobs_by_stage(), Fetch jobs filtered by pipeline stage. Args: conn: Database connection. Uses…, Set `archived_at` to one timestamp on the whole live discovery backlog, so a…, Reverse archive_discovery_results. With `timestamp`, restores just that batch;…, unarchive_discovery_results(), test_archive_is_idempotent(), test_archive_scopes_to_untouched_discovery_rows() (+3 more)

### Community 51 - "combined_critic_score"
Cohesion: 0.39
Nodes (3): combined_critic_score(), The single critic_score value stored on the job row: the average of whichever…, TestCombinedCriticScore

### Community 52 - "build_corpus.py"
Cohesion: 0.36
Nodes (6): build(), enrich(), extract(), load(), log(), Build corpus v2 -- two corpora, separate files, never pooled. A. Calibration…

### Community 53 - "company_pages.py"
Cohesion: 0.29
Nodes (9): _db_seed_entries(), _expand_ats(), _pointer_row(), Company-first discovery: harvest employer career pages, not job boards. Same…, Harvest the company-first registry. Returns {total_found, new, existing,…, Flatten the NI/UK employer lists into a single list of entry dicts., jobs.company values that match the known_boards map -> ATS entries., _registry_entries() (+1 more)

### Community 55 - "cover_letter.py"
Cohesion: 0.09
Nodes (32): get_locale_style(), get_profile_keywords(), load_profile(), Extract full list of technical skills, domains, and role keywords from…, Infer document terminology and layout conventions from the candidate's country.…, Load user profile from ~/.applypilot/profile.json., _build_cover_letter_prompt(), _check_company_mentioned() (+24 more)

### Community 56 - "test_critic.py"
Cohesion: 0.20
Nodes (6): evaluate_letter_observations(), _fact(), Tests for the critic pass's CODE-side threshold logic (critic.py). These test…, Stands in for FactBank: the floor map only ever asks it which verified facts…, _StubBank, TestEvaluateLetterObservations

### Community 57 - "test_enrichment.py"
Cohesion: 0.14
Nodes (6): _clean_title(), Trim a page <title> down to the job title: drop a " | Company" / " - Company" /…, Tests for the HTTP-first (tier 0) detail-page path in enrichment/detail.py., When tier 0 succeeds, page.goto is never called., test_manual_clean_title(), test_scrape_detail_page_short_circuits_on_http_first()

### Community 58 - "render_jobs"
Cohesion: 0.32
Nodes (6): Console, jobs(), List individual jobs with fit score, company context, CV/cover letter links,…, Render one Rich panel per job with fit score, company context, tailored…, render_jobs(), TestRenderJobs

### Community 60 - "facts.py"
Cohesion: 0.11
Nodes (17): BulletPlacementViolation, _extract_numbers(), FactBankError, FactBankLoadError, NumericGuardViolation, Exception, Verified-fact bank for resume tailoring. facts.yaml (repo root) is the ONLY…, Base class for fact-bank problems. (+9 more)

### Community 61 - "get_tier"
Cohesion: 0.32
Nodes (8): doctor(), Check your setup and diagnose missing requirements., get_chrome_path(), get_tier(), load_env(), Auto-detect Chrome/Chromium executable path, cross-platform. Override with…, Load environment variables from ~/.applypilot/.env if it exists., Detect the current tier based on available dependencies. Tier 1 (Discovery):…

### Community 62 - "format_facts_block"
Cohesion: 0.33
Nodes (5): format_facts_block(), Render verified facts as an id-keyed list for a prompt. Shared by resume…, Once on the id line isn't enough: the variant text is what the model reads when…, A letter has no entries, so ownership is meaningless there., TestFormatFactsBlockOwner

### Community 63 - "find_summary_duplicate_bullets"
Cohesion: 0.22
Nodes (7): find_summary_duplicate_bullets(), Summary sentences that are a bullet below, retyped.…, check_no_cross_section_duplicates only ever walked EXPERIENCE and PROJECTS, so…, The signal that was removed 2026-09-01 fired here, on 12 of 12 live CVs, and…, The pair that motivated _SUMMARY_DUP_MIN_COVERAGE, from the 2026-09-01 sample:…, One sentence duplicated across three bullets is one problem to fix, not three…, TestFindSummaryDuplicateBullets

### Community 64 - "scoring_queue"
Cohesion: 0.25
Nodes (8): Same profile-domain ordering get_jobs_by_stage applies in SQL, in Python, so…, Stable 0..divisor-1 bucket for a URL (deterministic sampling)., Ordered list of job URLs to score next, highest-yield source first. Ordering:…, scoring_queue(), _title_domain_rank(), _url_bucket(), test_scoring_queue_disabled_falls_back_to_recency(), test_scoring_queue_excludes_prefiltered_and_respects_limit()

### Community 65 - "_HTMLStripper"
Cohesion: 0.25
Nodes (3): HTMLParser, _HTMLStripper, Strip HTML tags, keep text content.

### Community 66 - "_store_jobs_filtered"
Cohesion: 0.40
Nodes (5): _location_ok(), Connection, Check if a job location passes the user's location filter., Store jobs with location filtering. Returns (new, existing)., _store_jobs_filtered()

### Community 67 - "test_facts.py"
Cohesion: 0.14
Nodes (10): _bank(), _DegreeAsJobClient, _embedded_fact(), _FakeClient, Tests for the FactBank / NumericGuard architectural fabrication guard. Fixtures…, Always returns the same fabricated response, regardless of the 'AVOID THESE…, A use_when-restricted fact (mirrors edu.embedded_marks)., A model that files the candidate's own degree as an EXPERIENCE entry. Measured… (+2 more)

### Community 68 - "test_company_pages.py"
Cohesion: 0.25
Nodes (4): env(), fixture, Tests for the company-first (employer career page) harvester., test_run_expands_ats_and_stores_pointers()

### Community 69 - "test_grad_boards.py"
Cohesion: 0.25
Nodes (3): env(), fixture, Tests for the NI/UK graduate job-board harvesters (discovery/grad_boards.py).

### Community 70 - "close_connection"
Cohesion: 0.29
Nodes (7): close_connection(), Close the cached connection for the current thread., db(), _freeze_now(), fixture, db(), fixture

### Community 71 - "cohort.py"
Cohesion: 0.43
Nodes (6): cohort_bucket(), cohort_rank(), _now(), Start-date / cohort inference for a discovered opportunity. A role that starts…, Coarse class for filtering/ordering: 'immediate', 'this_year', 'next_year',…, test_cohort_bucket_and_rank()

### Community 72 - "._bank"
Cohesion: 0.19
Nodes (7): The wording is the model's; the numbers are not. A rewording that reaches for a…, Tighter than NumericGuard's global allowed set on purpose: 11 is verified, but…, Back-compat: the original select-a-variant shape is unchanged., A fact bound to one real employer/project (Fact.source, set from its facts.yaml…, No canonical record matched this entry -- there's no ground truth to check it…, TestBulletOwnership, TestRewordedFactBullets

### Community 73 - "cli.py"
Cohesion: 0.13
Nodes (15): callback, dashboard(), dedupe(), main(), ScoutPilot CLI — the main entry point., Flag reposts: the same ad discovered again under a new URL or from a second…, ScoutPilot — scouts early-career jobs, scores fit, and tailors your CV per…, Open the HTML dashboard in your browser. Serves it live by default (regenerates… (+7 more)

### Community 74 - "run_pipeline"
Cohesion: 0.33
Nodes (6): Resolve 'all' and validate/order stage names., Execute stages one at a time (original behavior)., Run pipeline stages. Args: stages: List of stage names, or None / ["all"] for…, _resolve_stages(), run_pipeline(), _run_sequential()

### Community 75 - "get_chrome_user_data"
Cohesion: 0.67
Nodes (3): get_chrome_user_data(), Path, Default Chrome user data directory, cross-platform.

## Knowledge Gaps
- **25 isolated node(s):** `scoutpilot`, `graphify`, `Workflow: graphify`, `Added`, `Fixed` (+20 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_connection()` connect `get_connection` to `tailor.py`, `smartextract.py`, `view.py`, `_StageTracker`, `detail.py`, `_process_one`, `worker_loop`, `_bootstrap`, `scorer.py`, `init_db`, `launcher.py`, `database.py`, `main`, `pipeline.py`, `run_job`, `list_jobs`, `.load`, `end_run`, `get_jobs_by_stage`, `company_pages.py`, `cover_letter.py`, `scoring_queue`, `cli.py`?**
  _High betweenness centrality (0.172) - this node is a cross-community bridge._
- **Why does `FactBank` connect `FactBank` to `tailor.py`, `get_client`, `test_facts.py`, `.load`, `._bank`, `ToolLeakGuard`, `cover_letter.py`, `build_bullet_floor_map`, `facts.py`, `check_no_cross_section_duplicates`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `FactBank` (e.g. with `_build_cover_letter_prompt()` and `cover_letter_one()`) actually correct?**
  _`FactBank` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `tailor_resume()` (e.g. with `BulletPlacementViolation` and `FactBank`) actually correct?**
  _`tailor_resume()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `scoutpilot`, `graphify`, `Workflow: graphify` to the rest of the system?**
  _25 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `tailor.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05957767722473605 - nodes in this community are weakly interconnected._
- **Should `test_prefilter.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11948790896159317 - nodes in this community are weakly interconnected._