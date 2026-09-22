# Graph Report - ApplyPilot-main  (2026-09-22)

## Corpus Check
- 64 files · ~130,827 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1494 nodes · 3097 edges · 67 communities (62 shown, 5 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 128 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `69c00bd1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- tailor.py
- test_prefilter.py
- ._run
- database.py
- smartextract.py
- evaluate_cv_observations
- chrome.py
- view.py
- .verified
- _StageTracker
- test_cohort.py
- detail.py
- LLMClient
- workday.py
- pdf.py
- load_prefilter_config
- test_discovery.py
- cli.py
- scorer.py
- find_header_restating_bullets
- Contributing to ScoutPilot
- init_db
- config.py
- build_bullet_floor_map
- run_wizard
- remote_boards.py
- launcher.py
- ._bank
- critic.py
- direct_ats.py
- check_no_cross_section_duplicates
- group_near_identical
- get_client
- _run_cover_letter
- render_full
- hacker_news.py
- [0.2.0] - 2026-02-17
- TestCanonicalSkillsLines
- list_jobs
- UnfilledFact
- rules/graphify.md
- workflows/graphify.md
- ToolLeakGuard
- validator.py
- TestNumericGuard
- TestBulletOwnership
- drop_unverifiable_quotes
- pipeline.py
- store_jobs
- scoring/__init__.py
- combined_critic_score
- build_corpus.py
- scoutpilot
- FactBank
- test_critic.py
- test_enrichment.py
- facts.py
- Fact
- _HTMLStripper
- _store_jobs_filtered
- test_facts.py
- test_company_pages.py
- within_cohort_horizon
- TestRewordedFactBullets
- main

## God Nodes (most connected - your core abstractions)
1. `get_connection()` - 70 edges
2. `FactBank` - 49 edges
3. `init_db()` - 46 edges
4. `store_jobs()` - 38 edges
5. `tailor_resume()` - 32 edges
6. `Fact` - 28 edges
7. `evaluate_prefilter()` - 27 edges
8. `infer_opportunity_type()` - 25 edges
9. `scoring_queue()` - 23 edges
10. `is_relevant_tech_role()` - 23 edges

## Surprising Connections (you probably didn't know these)
- `test_rediscovery_does_not_revive_applied_row()` --calls--> `store_jobs()`  [EXTRACTED]
  tests/test_cohort.py → src/scoutpilot/database.py
- `test_run_expands_ats_and_stores_pointers()` --calls--> `get_jobs_by_stage()`  [EXTRACTED]
  tests/test_company_pages.py → src/scoutpilot/database.py
- `test_infer_opportunity_type_direct_job()` --calls--> `infer_opportunity_type()`  [EXTRACTED]
  tests/test_discovery.py → src/scoutpilot/discovery/direct_ats.py
- `test_infer_opportunity_type_funded_training()` --calls--> `infer_opportunity_type()`  [EXTRACTED]
  tests/test_discovery.py → src/scoutpilot/discovery/direct_ats.py
- `test_infer_opportunity_type_graduate()` --calls--> `infer_opportunity_type()`  [EXTRACTED]
  tests/test_discovery.py → src/scoutpilot/discovery/direct_ats.py

## Import Cycles
- None detected.

## Communities (67 total, 5 thin omitted)

### Community 0 - "tailor.py"
Cohesion: 0.05
Nodes (64): check_listing_still_open(), Best-effort check for whether a job listing is still accepting applications,…, Split arbitrary CV/resume text into sections keyed by ALL-CAPS headers. Unlike…, split_sections(), _apply_canonical_entries(), assemble_resume_text(), _base_summary(), _build_guard_scan_text() (+56 more)

### Community 1 - "test_prefilter.py"
Cohesion: 0.21
Nodes (23): evaluate_prefilter(), Return a short reason string if `job` should be filtered at ingest, else None.…, _job(), parametrize, Tests for the ingest pre-filter (discovery/prefilter.py) and the yield-ordered…, Shipped default is scan=title: a body '5+ years experience' does NOT trip the…, test_breakdown_lists_every_rule_tripped(), test_disabled_prefilter_returns_none() (+15 more)

### Community 2 - "._run"
Cohesion: 0.18
Nodes (7): Shipping is the LAST-attempt behaviour, not the first: while attempts remain, a…, Once canonical_entries.experience is configured, it's exhaustive: an EXPERIENCE…, The exact incident: the model filed the candidate's own degree as a job once…, The same unmatched-entry situation in PROJECTS is kept, not rejected -- a…, The rejected entry is already deleted from the data by the time the error is…, TestCanonicalExperienceRejection, TestInventedExperienceEntryShipsAnyway

### Community 3 - "database.py"
Cohesion: 0.07
Nodes (52): archive_discovery(), backfill_cohort(), Set aside the current discovery backlog before a fresh search. Stamps one…, Re-run cohort/start-date inference against rows that already exist in the DB…, Show pipeline statistics from the database., status(), applied_companies(), apply_duplicate_marks() (+44 more)

### Community 4 - "smartextract.py"
Cohesion: 0.08
Nodes (41): load_search_config(), Load search configuration from ~/.applypilot/searches.yaml. Cached on the…, ask_llm(), build_scrape_targets(), clean_card_html(), clean_page_html(), collect_page_intelligence(), execute_api_response() (+33 more)

### Community 5 - "evaluate_cv_observations"
Cohesion: 0.11
Nodes (13): evaluate_cv_observations(), Apply fixed, code-side thresholds to the model's raw extraction. Never trusts…, On three bullets a single NONE is already a third: the fraction carries no…, The exact incident: Revolut round 2 (2026-08-26) was flagged 6/11 while a human…, The counterpart the exemption must not swallow: round 1's Java Software…, The exact incident: 'VIOFEEL has 1 bullet, below the minimum of 2' landed on 6…, The floor drops only where the material genuinely runs out. Kraydel has nine…, The model quotes the header back out of the rendered CV; only case and spacing… (+5 more)

### Community 6 - "chrome.py"
Cohesion: 0.16
Nodes (19): Popen, cleanup_on_exit(), cleanup_worker(), kill_all_chrome(), _kill_on_port(), _kill_process_tree(), launch_chrome(), Path (+11 more)

### Community 7 - "view.py"
Cohesion: 0.13
Nodes (18): Clear one job's apply status back to pending, e.g. after a wrong manual mark or…, reset_job(), classify_location(), _location_priority_tier(), 0-indexed priority tier for a job's location (lower = higher priority). Checked…, Human-readable place label for a job's location, for the dashboard's place…, generate_dashboard(), get_tailor_status() (+10 more)

### Community 8 - ".verified"
Cohesion: 0.11
Nodes (13): _accept_reworded(), _extract_numbers(), Recursively pull every integer token out of a nested structure. Used to fold…, Deterministic keyword extraction from a fact's free-text `use_when`.…, Best-effort recovery for a plain-string bullet that has a digit but is actually…, All tier == 'verified' facts. The ONLY facts ever exposed to the LLM., Every number the tailoring output is allowed to contain: the union of every…, Verified facts worth offering the LLM for this job. Facts with no `use_when`… (+5 more)

### Community 10 - "test_cohort.py"
Cohesion: 0.17
Nodes (17): infer_cohort_start(), Normalised start marker, or None if the posting doesn't state one. Only years…, db(), _freeze_now(), fixture, parametrize, Tests for start-date / cohort inference (discovery/cohort.py) and the…, test_archive_is_idempotent() (+9 more)

### Community 11 - "detail.py"
Cohesion: 0.06
Nodes (56): browser_title(), clean_content_html(), clean_description(), collect_detail_intelligence(), extract_apply_url_deterministic(), extract_description_deterministic(), extract_from_json_ld(), extract_main_content() (+48 more)

### Community 12 - "LLMClient"
Cohesion: 0.13
Nodes (11): Response, _GeminiCompatForbidden, LLMClient, Exception, Thin LLM client supporting OpenAI-compatible and native Gemini endpoints. For…, Call the native Gemini generateContent API. Used automatically when the OpenAI-…, Call the OpenAI-compatible endpoint. json_schema, when given, is passed as…, Call Ollama's native /api/chat, optionally with a JSON-schema `format`.… (+3 more)

### Community 13 - "workday.py"
Cohesion: 0.09
Nodes (30): fetch_details(), _fetch_one_detail(), load_employers(), _location_ok(), _process_one(), Connection, Workday ATS direct API scraper: searches employer career portals. Scrapes…, Convert HTML to plain text. (+22 more)

### Community 14 - "pdf.py"
Cohesion: 0.09
Nodes (27): Stage: PDF conversion — convert tailored resumes and cover letters to PDF., _run_pdf(), batch_convert(), build_cover_letter_html(), build_html(), _cover_letter_font_faces(), _cv_font_faces(), _fit_resume_html() (+19 more)

### Community 15 - "load_prefilter_config"
Cohesion: 0.20
Nodes (14): _deep_merge(), load_prefilter_config(), Recursively merge `over` onto a copy of `base` (dict values only)., Ingest pre-filter + scoring-queue budget config (config/prefilter.yaml). A…, _is_relevant_remote(), True if a (lowercased) location's "remote" claim is UK/NI-relevant or…, _check_experience(), _check_location() (+6 more)

### Community 16 - "test_discovery.py"
Cohesion: 0.09
Nodes (27): fetch_targetjobs_jobs(), fetch_targetjobs_urls(), _http_get_text(), _is_tech_role_strict(), targetjobs.co.uk graduate job board harvester. targetjobs.co.uk's own search…, Every live `/jobs/<slug>-<id>` URL from the sitemap., Tech-relevant job rows from the sitemap. No full_description -- see module…, Harvest targetjobs.co.uk via its sitemap and store results into the DB. (+19 more)

### Community 17 - "cli.py"
Cohesion: 0.08
Nodes (45): command, Reset all failed jobs so they can be retried. Returns: Number of jobs reset., reset_failed(), add(), apply(), _bootstrap(), clean(), dashboard() (+37 more)

### Community 18 - "scorer.py"
Cohesion: 0.05
Nodes (37): apply_eligibility_gate(), _build_candidate_level(), _candidate_is_unrestricted(), _clean_optional_field(), _countries_in_text(), _country_in_text(), _normalize_country(), _parse_score_response() (+29 more)

### Community 19 - "find_header_restating_bullets"
Cohesion: 0.07
Nodes (25): _bullet_text(), _entry_span_months(), find_header_restating_bullets(), find_summary_duplicate_bullets(), Length in months of the first date range in `text`, or None. An open-ended…, Bullets that only say again what their own entry header already says. This…, Summary sentences that are a bullet below, retyped.…, Best-effort plain text for a bullet, which may still be a raw {"fact": id,… (+17 more)

### Community 20 - "Contributing to ScoutPilot"
Cohesion: 0.08
Nodes (23): Adding New Career Sites, Adding New Workday Employers, Bug Fixes and Features, Clone and Install, Code Style Guidelines, Contributing to ScoutPilot, Development Setup, How to Contribute (+15 more)

### Community 21 - "init_db"
Cohesion: 0.07
Nodes (41): init_db(), Create the full jobs table with all columns from every pipeline stage. This is…, _clean_ddg_url(), Search Operator ('Google Dorking') & Direct ATS Discovery Agent. Executes…, Run search operator discovery against ATS domains and funded training…, Extract destination URL from DuckDuckGo redirect link., Execute search query against DuckDuckGo HTML interface., run_dorking_discovery() (+33 more)

### Community 22 - "config.py"
Cohesion: 0.08
Nodes (37): _build_captcha_section(), _build_hard_rules(), _build_location_check(), _build_profile_summary(), build_prompt(), _build_salary_section(), _build_screening_section(), Prompt builder for the autonomous job application agent. Constructs the full… (+29 more)

### Community 23 - "build_bullet_floor_map"
Cohesion: 0.30
Nodes (6): build_bullet_floor_map(), Per-entry minimum bullet counts for the critic, derived from how much real…, build_bullet_floor_map lives in tailor.py but exists only to feed…, The critic counts bullets under PROJECTS as well, so a floor is needed there or…, No verified material behind an entry means nothing to ask for -- the guard must…, TestBuildBulletFloorMap

### Community 24 - "run_wizard"
Cohesion: 0.17
Nodes (15): ensure_dirs(), Create all required directories., ScoutPilot first-time setup wizard. Interactive flow that creates…, Generate a searches.yaml from user input., Ask about AI scoring/tailoring — optional LLM configuration., Configure autonomous job application (requires Claude Code CLI)., Run the full interactive setup wizard., Prompt for resume file and copy into APP_DIR. (+7 more)

### Community 25 - "remote_boards.py"
Cohesion: 0.22
Nodes (12): _clean_html(), fetch_remote_com_jobs(), fetch_weworkremotely_jobs(), _http_get_text(), Remote-first job board harvesters: remote.com and We Work Remotely. Both are…, Fetch and parse We Work Remotely's per-category RSS feeds., Run both remote.com and We Work Remotely harvesters and store results. Returns…, Scrape https://remote.com/jobs/all, `pages` pages deep. No JD text is available… (+4 more)

### Community 26 - "launcher.py"
Cohesion: 0.05
Nodes (59): Wipe and recreate a worker's isolated working directory. Each job gets a fresh…, reset_worker_dir(), add_event(), get_state(), get_totals(), init_worker(), Rich live dashboard for the apply pipeline. Displays real-time worker status,…, Compute aggregate totals across all workers. Returns: Dict with keys: applied,… (+51 more)

### Community 27 - "._bank"
Cohesion: 0.23
Nodes (7): _kraydel_multiparty_fact(), Bullets that carry no fact id must contain no digits -- enforced in code, not…, Mirrors the real kraydel.multiparty_calls entry in facts.yaml., A plausible-but-unevidenced fact that must never reach the LLM., The core guarantee: relevant_facts() (what actually goes into the LLM prompt)…, TestFactBankRejectsUnverified, _unverified_fact()

### Community 28 - "critic.py"
Cohesion: 0.21
Nodes (13): _build_cv_critic_user_message(), _build_letter_critic_user_message(), CriticResult, _is_differentiator_bullet(), _normalize_header(), Extraction-only "critic" pass over a tailored CV and cover letter. Catches…, Loose key for matching a header the model quoted back out of the CV against the…, score is COMPUTED from discrete findings (10.0 minus each finding's weight,… (+5 more)

### Community 29 - "direct_ats.py"
Cohesion: 0.11
Nodes (36): datetime, _db_seed_entries(), _expand_ats(), _pointer_row(), Company-first discovery: harvest employer career pages, not job boards. Same…, Harvest the company-first registry. Returns {total_found, new, existing,…, Flatten the NI/UK employer lists into a single list of entry dicts., jobs.company values that match the known_boards map -> ATS entries. (+28 more)

### Community 30 - "check_no_cross_section_duplicates"
Cohesion: 0.15
Nodes (11): check_no_cross_section_duplicates(), _normalize_bullet_for_dup_check(), Hard assertion: the same claim may not appear twice anywhere in the assembled…, check_no_cross_section_duplicates is the hard backstop: even if ownership/dedup…, Exact-text matching alone missed this live 2026-08-26: the same fact, worded…, The blind spot the projects-vs-experience loop had by construction: two bullets…, The exact pairing named in _likely_fact_id's docstring: 'Built dual ML…, Same section, two different headings -- also invisible to the old loop, which… (+3 more)

### Community 31 - "group_near_identical"
Cohesion: 0.06
Nodes (22): description_shingles(), group_near_identical(), Set of 5-word shingle hashes over a description's first 600 words. Order-…, Map url -> a group number, for ads that read as the same posting. Only urls…, shingle_jaccard(), fixture, Dashboard behaviour: CV/cover-letter independence, and the two things that made…, searches.yaml is hand-edited, so the cache is keyed on the file's own… (+14 more)

### Community 32 - "get_client"
Cohesion: 0.22
Nodes (9): _detect_provider(), get_client(), Unified LLM client for ScoutPilot. Auto-detects provider from environment:…, Return (base_url, model, api_key) based on environment variables. Reads env at…, Return (or create) the module-level LLMClient singleton., _build_judge_prompt(), judge_tailored_resume(), LLM judge layer: catches subtle fabrication that programmatic checks miss.… (+1 more)

### Community 33 - "_run_cover_letter"
Cohesion: 0.36
Nodes (8): _error_summary(), _on_demand_retries(), Generate the cover letter for one job, reporting into the job's `cover` field…, Background-thread target: tailor the CV, then generate the cover letter,…, Retry budget for a single on-demand click. A batch run defaults to 1 retry on a…, _run_cover_letter(), _run_tailor_and_cover(), _set_tailor_status()

### Community 34 - "render_full"
Cohesion: 0.40
Nodes (6): Group, Build the Rich table showing all worker statuses. Returns: A Rich Table object…, Render the dashboard table plus the recent events panel. Returns: A Rich Group…, render_dashboard(), render_full(), Table

### Community 35 - "hacker_news.py"
Cohesion: 0.20
Nodes (14): _clean_hn_html(), fetch_comment_item(), find_latest_who_is_hiring_story(), _get_json(), parse_hn_comment(), Hacker News 'Who is Hiring?' Harvester. Fetches the latest monthly 'Ask HN: Who…, Discover jobs from the latest Hacker News 'Who is Hiring?' thread. Args:…, Clean HTML from HN comments to readable text. (+6 more)

### Community 36 - "[0.2.0] - 2026-02-17"
Cohesion: 0.25
Nodes (7): [0.1.0] - 2026-02-17, [0.2.0] - 2026-02-17, Added, Added, Changed, Changelog, Fixed

### Community 37 - "TestCanonicalSkillsLines"
Cohesion: 0.29
Nodes (3): TECHNICAL SKILLS renders only what the profile actually declares -- the LLM's…, The exact incident: the model added 'LangChain (agent frameworks)' and…, TestCanonicalSkillsLines

### Community 38 - "list_jobs"
Cohesion: 0.14
Nodes (11): Console, list_jobs(), Fetch scored jobs for terminal display, filtered and sorted by fit. Args:…, Render one Rich panel per job with fit score, company context, tailored…, render_jobs(), fixture, Tests for terminal_view.list_jobs / render_jobs (the `scoutpilot jobs` command)., Isolated scratch DB with a few jobs at different fit scores/sites, never… (+3 more)

### Community 39 - "UnfilledFact"
Cohesion: 0.40
Nodes (3): A known gap: a plausible claim that needs a real value filled in before it can…, Unverified entries pending a real value, for a CLI prompt flow., UnfilledFact

### Community 43 - "ToolLeakGuard"
Cohesion: 0.06
Nodes (29): Remove LLM preamble before 'Dear Hiring Manager,' if present. Gemini and other…, Truncate anything after the sign-off line. Models occasionally add notes/P.S.…, _strip_after_signoff(), _strip_preamble(), Deterministic check: a tool/tech token in the job description but absent from…, Every job-description tool the candidate doesn't have that appears as a whole…, Raise ToolLeakViolation if a job-description tool the candidate doesn't have…, ToolLeakGuard (+21 more)

### Community 44 - "validator.py"
Cohesion: 0.06
Nodes (36): Row, derive_company(), Best available employer name for a job, for grouping in the dashboard. Derived…, _check_company_mentioned(), A cover letter that never names the company it's addressed to reads as…, _company_tokens(), find_fabricated_numbers(), has_bad_signoff() (+28 more)

### Community 45 - "TestNumericGuard"
Cohesion: 0.25
Nodes (5): _qualitative_fact(), Canonical example: an injected, unevidenced 500 must be caught., The real 4-to-9 participant fact must pass cleanly., A zero-number verified fact (mirrors kraydel.audit_system)., TestNumericGuard

### Community 46 - "TestBulletOwnership"
Cohesion: 0.40
Nodes (3): A fact bound to one real employer/project (Fact.source, set from its facts.yaml…, No canonical record matched this entry -- there's no ground truth to check it…, TestBulletOwnership

### Community 47 - "drop_unverifiable_quotes"
Cohesion: 0.21
Nodes (8): drop_unverifiable_quotes(), _quote_key(), Normalised form for checking a model-supplied quote against the CV. Case and…, Remove any model-quoted bullet that does not actually occur in the CV. The…, The guard that keeps a finding from resting on a quote the CV does not contain.…, The model quotes bullets as rendered; resolved bullets have no dash. Stripping…, Documented consequence of the rule as specified: containment is checked against…, TestDropUnverifiableQuotes

### Community 48 - "pipeline.py"
Cohesion: 0.10
Nodes (30): Event, end_run(), Record the start of one pipeline stage invocation. Args: conn: Database…, Record the end of a pipeline stage invocation. Args: conn: Database connection.…, start_run(), Main entry point for JobSpy-based job discovery. Loads search queries and…, run_discovery(), _count_pending() (+22 more)

### Community 49 - "store_jobs"
Cohesion: 0.16
Nodes (16): get_jobs_by_stage(), Store discovered jobs, skipping duplicates by URL. Args: conn: Database…, Fetch jobs filtered by pipeline stage. Args: conn: Database connection. Uses…, store_jobs(), test_cohort_filter_and_queue_order(), test_cohort_horizon_disabled_restores_old_behavior(), test_rediscovery_revives_archived_row(), test_database_opportunity_columns() (+8 more)

### Community 51 - "combined_critic_score"
Cohesion: 0.39
Nodes (3): combined_critic_score(), The single critic_score value stored on the job row: the average of whichever…, TestCombinedCriticScore

### Community 52 - "build_corpus.py"
Cohesion: 0.36
Nodes (6): build(), enrich(), extract(), load(), log(), Build corpus v2 -- two corpora, separate files, never pooled. A. Calibration…

### Community 55 - "FactBank"
Cohesion: 0.06
Nodes (53): Pattern, get_locale_style(), get_profile_keywords(), load_profile(), Extract full list of technical skills, domains, and role keywords from…, Infer document terminology and layout conventions from the candidate's country.…, Load user profile from ~/.applypilot/profile.json., FactBank (+45 more)

### Community 56 - "test_critic.py"
Cohesion: 0.20
Nodes (6): evaluate_letter_observations(), _fact(), Tests for the critic pass's CODE-side threshold logic (critic.py). These test…, Stands in for FactBank: the floor map only ever asks it which verified facts…, _StubBank, TestEvaluateLetterObservations

### Community 57 - "test_enrichment.py"
Cohesion: 0.14
Nodes (6): _clean_title(), Trim a page <title> down to the job title: drop a " | Company" / " - Company" /…, Tests for the HTTP-first (tier 0) detail-page path in enrichment/detail.py., When tier 0 succeeds, page.goto is never called., test_manual_clean_title(), test_scrape_detail_page_short_circuits_on_http_first()

### Community 60 - "facts.py"
Cohesion: 0.11
Nodes (16): BulletPlacementViolation, FactBankError, FactBankLoadError, NumericGuard, NumericGuardViolation, Exception, Verified-fact bank for resume tailoring. facts.yaml (repo root) is the ONLY…, Base class for fact-bank problems. (+8 more)

### Community 62 - "Fact"
Cohesion: 0.13
Nodes (13): Fact, format_facts_block(), One verifiable, pre-written claim the LLM may select for a bullet., Render verified facts as an id-keyed list for a prompt. Shared by resume…, Resolve every experience/project bullet into literal text. A fact-id bullet is…, _resolve_fact_bullets(), A fact is one real thing; it belongs on the CV once -- even if that means a…, The duplicate bullet goes; the entry survives on its other one. (+5 more)

### Community 65 - "_HTMLStripper"
Cohesion: 0.25
Nodes (3): HTMLParser, _HTMLStripper, Strip HTML tags, keep text content.

### Community 66 - "_store_jobs_filtered"
Cohesion: 0.40
Nodes (5): _location_ok(), Connection, Check if a job location passes the user's location filter., Store jobs with location filtering. Returns (new, existing)., _store_jobs_filtered()

### Community 67 - "test_facts.py"
Cohesion: 0.15
Nodes (10): _bank(), _DegreeAsJobClient, _embedded_fact(), _FakeClient, Tests for the FactBank / NumericGuard architectural fabrication guard. Fixtures…, Always returns the same fabricated response, regardless of the 'AVOID THESE…, A use_when-restricted fact (mirrors edu.embedded_marks)., A model that files the candidate's own degree as an EXPERIENCE entry. Measured… (+2 more)

### Community 68 - "test_company_pages.py"
Cohesion: 0.10
Nodes (11): close_connection(), Close the cached connection for the current thread., env(), fixture, Tests for the company-first (employer career page) harvester., test_run_expands_ats_and_stores_pointers(), env(), fixture (+3 more)

### Community 71 - "within_cohort_horizon"
Cohesion: 0.24
Nodes (11): cohort_bucket(), _cohort_effective_month(), cohort_rank(), _now(), Start-date / cohort inference for a discovered opportunity. A role that starts…, Coarse class for filtering/ordering: 'immediate', 'this_year', 'next_year',…, (year, month) a positively-inferred cohort_start resolves to, or None for…, True unless `cohort_start` names a start later than `horizon_months` from now… (+3 more)

### Community 72 - "TestRewordedFactBullets"
Cohesion: 0.22
Nodes (4): The wording is the model's; the numbers are not. A rewording that reaches for a…, Tighter than NumericGuard's global allowed set on purpose: 11 is verified, but…, Back-compat: the original select-a-variant shape is unchanged., TestRewordedFactBullets

### Community 73 - "main"
Cohesion: 0.67
Nodes (3): callback, main(), ScoutPilot — scouts early-career jobs, scores fit, and tailors your CV per…

## Knowledge Gaps
- **25 isolated node(s):** `scoutpilot`, `graphify`, `Workflow: graphify`, `Added`, `Fixed` (+20 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_connection()` connect `database.py` to `tailor.py`, `hacker_news.py`, `smartextract.py`, `list_jobs`, `view.py`, `detail.py`, `workday.py`, `pipeline.py`, `cli.py`, `store_jobs`, `scorer.py`, `init_db`, `FactBank`, `remote_boards.py`, `launcher.py`, `direct_ats.py`?**
  _High betweenness centrality (0.131) - this node is a cross-community bridge._
- **Why does `FactBank` connect `FactBank` to `tailor.py`, `get_client`, `test_facts.py`, `UnfilledFact`, `.verified`, `TestRewordedFactBullets`, `ToolLeakGuard`, `TestBulletOwnership`, `check_no_cross_section_duplicates`, `build_bullet_floor_map`, `._bank`, `facts.py`, `Fact`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Why does `derive_company()` connect `validator.py` to `store_jobs`, `database.py`, `view.py`, `FactBank`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `FactBank` (e.g. with `_build_cover_letter_prompt()` and `cover_letter_one()`) actually correct?**
  _`FactBank` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `tailor_resume()` (e.g. with `BulletPlacementViolation` and `FactBank`) actually correct?**
  _`tailor_resume()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `scoutpilot`, `graphify`, `Workflow: graphify` to the rest of the system?**
  _25 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `tailor.py` be split into smaller, more focused modules?**
  _Cohesion score 0.04794210764360018 - nodes in this community are weakly interconnected._