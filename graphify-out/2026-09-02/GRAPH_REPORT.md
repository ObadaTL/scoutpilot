# Graph Report - ApplyPilot-main  (2026-09-02)

## Corpus Check
- 68 files · ~196,724 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1403 nodes · 2834 edges · 70 communities (65 shown, 5 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 123 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cb3b1c43`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- tailor.py
- test_prefilter.py
- ._run
- database.py
- _run_one_site
- evaluate_cv_observations
- chrome.py
- config.py
- .verified
- _StageTracker
- test_cohort.py
- detail.py
- LLMClient
- _HTMLStripper
- pdf.py
- run_job
- datetime
- cli.py
- scorer.py
- init_db
- Contributing to ScoutPilot
- jobspy.py
- prompt.py
- test_critic.py
- run_wizard
- validator.py
- launcher.py
- ._bank
- critic.py
- workday.py
- check_no_cross_section_duplicates
- TestSearchHaystack
- get_client
- hacker_news.py
- main
- scrape_detail_page
- [0.2.0] - 2026-02-17
- execute_api_response
- list_jobs
- UnfilledFact
- rules/graphify.md
- workflows/graphify.md
- ToolLeakGuard
- validate_cover_letter
- generate_cover_letter
- Fact
- drop_unverifiable_quotes
- manifest.json
- scrape_site_batch
- scoring/__init__.py
- combined_critic_score
- build_corpus.py
- Critic calibration corpus v2
- scoutpilot
- FactBank
- evaluate_letter_observations
- analyse
- facts.py
- extract_with_llm
- get_locale_style
- find_header_restating_bullets
- TestBulletOwnership
- _store_jobs_filtered
- test_facts.py
- view.py
- TestRewordedFactBullets
- main

## God Nodes (most connected - your core abstractions)
1. `get_connection()` - 65 edges
2. `FactBank` - 49 edges
3. `init_db()` - 40 edges
4. `tailor_resume()` - 32 edges
5. `store_jobs()` - 31 edges
6. `Fact` - 28 edges
7. `evaluate_prefilter()` - 27 edges
8. `evaluate_cv_observations()` - 22 edges
9. `generate_cover_letter()` - 20 edges
10. `TestEligibilityGate` - 20 edges

## Surprising Connections (you probably didn't know these)
- `test_rediscovery_does_not_revive_applied_row()` --calls--> `store_jobs()`  [EXTRACTED]
  tests/test_cohort.py → src/scoutpilot/database.py
- `TestFactBankLoad` --uses--> `FactBankLoadError`  [INFERRED]
  tests/test_facts.py → src/scoutpilot/facts.py
- `TestNumericGuard` --uses--> `NumericGuardViolation`  [INFERRED]
  tests/test_facts.py → src/scoutpilot/facts.py
- `TestCrossSectionDuplicateAssertion` --uses--> `BulletPlacementViolation`  [INFERRED]
  tests/test_facts.py → src/scoutpilot/facts.py
- `analyse()` --uses--> `BulletPlacementViolation`  [INFERRED]
  tools/corpus/report_corpus.py → src/scoutpilot/facts.py

## Import Cycles
- None detected.

## Communities (70 total, 5 thin omitted)

### Community 0 - "tailor.py"
Cohesion: 0.06
Nodes (48): check_listing_still_open(), Best-effort check for whether a job listing is still accepting applications,…, Split arbitrary CV/resume text into sections keyed by ALL-CAPS headers. Unlike…, split_sections(), _apply_canonical_entries(), assemble_resume_text(), _base_summary(), _build_guard_scan_text() (+40 more)

### Community 1 - "test_prefilter.py"
Cohesion: 0.12
Nodes (36): _is_relevant_remote(), True if a (lowercased) location's "remote" claim is UK/NI-relevant or…, _check_experience(), _check_location(), _check_seniority(), _contains_term(), evaluate_prefilter(), prefilter_breakdown() (+28 more)

### Community 2 - "._run"
Cohesion: 0.10
Nodes (12): _DegreeAsJobClient, Shipping is the LAST-attempt behaviour, not the first: while attempts remain, a…, Once canonical_entries.experience is configured, it's exhaustive: an EXPERIENCE…, The exact incident: the model filed the candidate's own degree as a job once…, The same unmatched-entry situation in PROJECTS is kept, not rejected -- a…, TECHNICAL SKILLS renders only what the profile actually declares -- the LLM's…, The exact incident: the model added 'LangChain (agent frameworks)' and…, A model that files the candidate's own degree as an EXPERIENCE entry. Measured… (+4 more)

### Community 3 - "database.py"
Cohesion: 0.05
Nodes (69): gen_prompt(), mark_job(), Release the in_progress lock without recording a terminal outcome. Used when a…, Generate a prompt file and print the Claude CLI command for manual debugging.…, Manually mark a job's apply status in the database. Records this as a completed…, release_lock(), apply(), Launch auto-apply to submit job applications. (+61 more)

### Community 4 - "_run_one_site"
Cohesion: 0.16
Nodes (16): ask_llm(), clean_page_html(), collect_page_intelligence(), execute_css_selectors(), extract_json(), format_strategy_briefing(), judge_api_responses(), Load a page with Playwright and collect every signal a scraping engineer would… (+8 more)

### Community 5 - "evaluate_cv_observations"
Cohesion: 0.11
Nodes (13): evaluate_cv_observations(), Apply fixed, code-side thresholds to the model's raw extraction. Never trusts…, On three bullets a single NONE is already a third: the fraction carries no…, The exact incident: Revolut round 2 (2026-08-26) was flagged 6/11 while a human…, The counterpart the exemption must not swallow: round 1's Java Software…, The exact incident: 'VIOFEEL has 1 bullet, below the minimum of 2' landed on 6…, The floor drops only where the material genuinely runs out. Kraydel has nine…, The model quotes the header back out of the rendered CV; only case and spacing… (+5 more)

### Community 6 - "chrome.py"
Cohesion: 0.13
Nodes (23): Popen, cleanup_on_exit(), cleanup_worker(), kill_all_chrome(), _kill_on_port(), _kill_process_tree(), launch_chrome(), Path (+15 more)

### Community 7 - "config.py"
Cohesion: 0.09
Nodes (30): _deep_merge(), load_ats_employers(), load_company_pages_config(), load_grad_boards_config(), load_prefilter_config(), load_schemes_config(), load_search_config(), _load_yaml_cached() (+22 more)

### Community 8 - ".verified"
Cohesion: 0.11
Nodes (13): _accept_reworded(), _extract_numbers(), Recursively pull every integer token out of a nested structure. Used to fold…, Deterministic keyword extraction from a fact's free-text `use_when`.…, Best-effort recovery for a plain-string bullet that has a digit but is actually…, All tier == 'verified' facts. The ONLY facts ever exposed to the LLM., Every number the tailoring output is allowed to contain: the union of every…, Verified facts worth offering the LLM for this job. Facts with no `use_when`… (+5 more)

### Community 9 - "_StageTracker"
Cohesion: 0.20
Nodes (5): Event, Thread-safe tracker for which stages have finished producing work., Run a single stage in streaming mode: loop until upstream done + no work. For…, _run_stage_streaming(), _StageTracker

### Community 10 - "test_cohort.py"
Cohesion: 0.05
Nodes (39): close_connection(), get_jobs_by_stage(), Fetch jobs filtered by pipeline stage. Args: conn: Database connection. Uses…, Close the cached connection for the current thread., cohort_bucket(), cohort_rank(), infer_cohort_start(), _now() (+31 more)

### Community 11 - "detail.py"
Cohesion: 0.17
Nodes (15): load_base_urls(), Load site base URLs for URL resolution from sites.yaml., parse_proxy(), Parse host:port:user:pass into components., _load_base_urls(), Detail page enrichment: scrapes full descriptions and apply URLs. For each job…, Resolve all relative URLs in the database. Returns stats., Set proxy config from an external caller. (+7 more)

### Community 12 - "LLMClient"
Cohesion: 0.13
Nodes (11): Response, _GeminiCompatForbidden, LLMClient, Exception, Thin LLM client supporting OpenAI-compatible and native Gemini endpoints. For…, Call the native Gemini generateContent API. Used automatically when the OpenAI-…, Call the OpenAI-compatible endpoint. json_schema, when given, is passed as…, Call Ollama's native /api/chat, optionally with a JSON-schema `format`.… (+3 more)

### Community 13 - "_HTMLStripper"
Cohesion: 0.08
Nodes (19): HTMLParser, fetch_details(), _fetch_one_detail(), _HTMLStripper, _location_ok(), Convert HTML to plain text., Open a URL using the configured opener (with or without proxy)., Search jobs via Workday CXS API. Returns JSON with total + jobPostings. (+11 more)

### Community 14 - "pdf.py"
Cohesion: 0.09
Nodes (27): Stage: PDF conversion — convert tailored resumes and cover letters to PDF., _run_pdf(), batch_convert(), build_cover_letter_html(), build_html(), _cover_letter_font_faces(), _cv_font_faces(), _fit_resume_html() (+19 more)

### Community 15 - "run_job"
Cohesion: 0.10
Nodes (21): add_event(), Update the worker's state fields. Args: worker_id: Which worker to update.…, Add a timestamped event to the scrolling event log. Args: msg: Rich markup…, update_state(), _check_playwright_mcp(), _make_mcp_config(), mark_result(), Path (+13 more)

### Community 16 - "datetime"
Cohesion: 0.10
Nodes (37): datetime, fetch_ashby_jobs(), fetch_greenhouse_jobs(), fetch_lever_jobs(), _http_get_json(), infer_opportunity_type(), is_relevant_tech_role(), Direct ATS API harvester: scrapes Greenhouse, Ashby, and Lever career portals.… (+29 more)

### Community 17 - "cli.py"
Cohesion: 0.06
Nodes (53): command, Reset all failed jobs so they can be retried. Returns: Number of jobs reset., reset_failed(), archive_discovery(), _bootstrap(), clean(), dashboard(), doctor() (+45 more)

### Community 18 - "scorer.py"
Cohesion: 0.06
Nodes (34): apply_eligibility_gate(), _build_candidate_level(), _candidate_is_unrestricted(), _clean_optional_field(), _country_in_text(), _normalize_country(), _parse_score_response(), Job fit scoring: LLM-powered evaluation of candidate-job match quality. Scores… (+26 more)

### Community 19 - "init_db"
Cohesion: 0.09
Nodes (34): discover(), Run specific or all discovery harvesters to find jobs, graduate schemes, and…, init_db(), Create the full jobs table with all columns from every pipeline stage. This is…, Store discovered jobs, skipping duplicates by URL. Args: conn: Database…, store_jobs(), _db_seed_entries(), _expand_ats() (+26 more)

### Community 20 - "Contributing to ScoutPilot"
Cohesion: 0.08
Nodes (23): Adding New Career Sites, Adding New Workday Employers, Bug Fixes and Features, Clone and Install, Code Style Guidelines, Contributing to ScoutPilot, Development Setup, How to Contribute (+15 more)

### Community 21 - "jobspy.py"
Cohesion: 0.23
Nodes (11): _full_crawl(), _load_location_config(), _location_ok(), JobSpy-based job discovery: searches Indeed, LinkedIn, Glassdoor, ZipRecruiter.…, Run a single search query and store results in DB., Run all search queries from search config across all locations., Call scrape_jobs with retry on transient failures., Extract accept/reject location lists from search config. Falls back to sensible… (+3 more)

### Community 22 - "prompt.py"
Cohesion: 0.15
Nodes (19): _build_captcha_section(), _build_hard_rules(), _build_location_check(), _build_profile_summary(), build_prompt(), _build_salary_section(), _build_screening_section(), Prompt builder for the autonomous job application agent. Constructs the full… (+11 more)

### Community 23 - "test_critic.py"
Cohesion: 0.17
Nodes (10): build_bullet_floor_map(), Per-entry minimum bullet counts for the critic, derived from how much real…, _fact(), Tests for the critic pass's CODE-side threshold logic (critic.py). These test…, Stands in for FactBank: the floor map only ever asks it which verified facts…, build_bullet_floor_map lives in tailor.py but exists only to feed…, The critic counts bullets under PROJECTS as well, so a floor is needed there or…, No verified material behind an entry means nothing to ask for -- the guard must… (+2 more)

### Community 24 - "run_wizard"
Cohesion: 0.17
Nodes (15): ensure_dirs(), Create all required directories., ScoutPilot first-time setup wizard. Interactive flow that creates…, Generate a searches.yaml from user input., Ask about AI scoring/tailoring — optional LLM configuration., Configure autonomous job application (requires Claude Code CLI)., Run the full interactive setup wizard., Prompt for resume file and copy into APP_DIR. (+7 more)

### Community 25 - "validator.py"
Cohesion: 0.14
Nodes (14): _build_skills_set(), find_fabricated_numbers(), Exception, Resume and cover letter validation: banned words, fabrication detection,…, Find number-bearing claims in tailored text with no basis in the original.…, Build the set of allowed skills from the profile's skills_boundary., Deterministic, code-only last resort for a guard failure that survived every…, Validate individual JSON fields from an LLM-generated tailored resume. Args:… (+6 more)

### Community 26 - "launcher.py"
Cohesion: 0.12
Nodes (19): Apply pipeline: Chrome management, prompt building, orchestration, and…, acquire_job(), _is_permanent_failure(), _load_blocked(), Apply orchestration: acquire jobs, spawn Claude Code sessions, track results.…, Determine if a failure should never be retried., Atomically acquire the next job to apply to and open an attempt for it. Args:…, is_manual_ats() (+11 more)

### Community 27 - "._bank"
Cohesion: 0.16
Nodes (10): _kraydel_multiparty_fact(), Bullets that carry no fact id must contain no digits -- enforced in code, not…, Canonical example: an injected, unevidenced 500 must be caught., The real 4-to-9 participant fact must pass cleanly., Mirrors the real kraydel.multiparty_calls entry in facts.yaml., A plausible-but-unevidenced fact that must never reach the LLM., The core guarantee: relevant_facts() (what actually goes into the LLM prompt)…, TestFactBankRejectsUnverified (+2 more)

### Community 28 - "critic.py"
Cohesion: 0.26
Nodes (11): _build_cv_critic_user_message(), _build_letter_critic_user_message(), CriticResult, _normalize_header(), Extraction-only "critic" pass over a tailored CV and cover letter. Catches…, Loose key for matching a header the model quoted back out of the CV against the…, score is COMPUTED from discrete findings (10.0 minus each finding's weight,…, run_cv_critic() (+3 more)

### Community 29 - "workday.py"
Cohesion: 0.16
Nodes (16): load_employers(), _load_location_filter(), _process_one(), Connection, Workday ATS direct API scraper: searches employer career portals. Scrapes…, Configure a global urllib opener with proxy support., Store corporate jobs in DB. Returns (new, existing)., Load Workday employer registry from config/employers.yaml. (+8 more)

### Community 30 - "check_no_cross_section_duplicates"
Cohesion: 0.15
Nodes (11): check_no_cross_section_duplicates(), _normalize_bullet_for_dup_check(), Hard assertion: the same claim may not appear twice anywhere in the assembled…, check_no_cross_section_duplicates is the hard backstop: even if ownership/dedup…, Exact-text matching alone missed this live 2026-08-26: the same fact, worded…, The blind spot the projects-vs-experience loop had by construction: two bullets…, The exact pairing named in _likely_fact_id's docstring: 'Built dual ML…, Same section, two different headings -- also invisible to the old loop, which… (+3 more)

### Community 31 - "TestSearchHaystack"
Cohesion: 0.09
Nodes (14): fixture, Dashboard behaviour: CV/cover-letter independence, and the two things that made…, searches.yaml is hand-edited, so the cache is keyed on the file's own…, applyFilters() matches the search term against `card.textContent`. On…, A cover-letter failure used to set the job's single status field to "error".…, The real invariant. A description that is neither in the DOM nor reachable by…, A file:// page has no server, so its search is still the textContent one and…, A file:// page cannot reach /api/... -- every such call fails as "Failed to… (+6 more)

### Community 32 - "get_client"
Cohesion: 0.22
Nodes (9): _detect_provider(), get_client(), Unified LLM client for ScoutPilot. Auto-detects provider from environment:…, Return (base_url, model, api_key) based on environment variables. Reads env at…, Return (or create) the module-level LLMClient singleton., _build_judge_prompt(), judge_tailored_resume(), LLM judge layer: catches subtle fabrication that programmatic checks miss.… (+1 more)

### Community 33 - "hacker_news.py"
Cohesion: 0.20
Nodes (14): _clean_hn_html(), fetch_comment_item(), find_latest_who_is_hiring_story(), _get_json(), parse_hn_comment(), Hacker News 'Who is Hiring?' Harvester. Fetches the latest monthly 'Ask HN: Who…, Discover jobs from the latest Hacker News 'Who is Hiring?' thread. Args:…, Clean HTML from HN comments to readable text. (+6 more)

### Community 34 - "main"
Cohesion: 0.15
Nodes (16): Group, get_state(), get_totals(), init_worker(), Rich live dashboard for the apply pipeline. Displays real-time worker status,…, Build the Rich table showing all worker statuses. Returns: A Rich Table object…, Render the dashboard table plus the recent events panel. Returns: A Rich Group…, Compute aggregate totals across all workers. Returns: Dict with keys: applied,… (+8 more)

### Community 35 - "scrape_detail_page"
Cohesion: 0.18
Nodes (12): clean_description(), collect_detail_intelligence(), extract_apply_url_deterministic(), extract_description_deterministic(), extract_from_json_ld(), Collect signals from a detail page. Lighter than discovery -- no API…, Extract description and apply URL from JSON-LD JobPosting. Returns…, Try known CSS patterns for apply buttons/links. (+4 more)

### Community 36 - "[0.2.0] - 2026-02-17"
Cohesion: 0.25
Nodes (7): [0.1.0] - 2026-02-17, [0.2.0] - 2026-02-17, Added, Added, Changed, Changelog, Fixed

### Community 37 - "execute_api_response"
Cohesion: 0.25
Nodes (8): execute_api_response(), execute_json_ld(), Navigate a JSON path and return whatever is there (including lists/dicts)., Simple JSON path resolver with type coercion for display., Extract jobs from JSON-LD JobPosting entries., Extract jobs from intercepted API response data., resolve_json_path(), resolve_json_path_raw()

### Community 38 - "list_jobs"
Cohesion: 0.13
Nodes (12): Console, list_jobs(), Terminal job-detail listing: fit score and company context for individual jobs,…, Fetch scored jobs for terminal display, filtered and sorted by fit. Args:…, Render one Rich panel per job with fit score, company context, tailored…, render_jobs(), fixture, Tests for terminal_view.list_jobs / render_jobs (the `scoutpilot jobs` command). (+4 more)

### Community 39 - "UnfilledFact"
Cohesion: 0.40
Nodes (3): A known gap: a plausible claim that needs a real value filled in before it can…, Unverified entries pending a real value, for a CLI prompt flow., UnfilledFact

### Community 43 - "ToolLeakGuard"
Cohesion: 0.06
Nodes (30): Remove LLM preamble before 'Dear Hiring Manager,' if present. Gemini and other…, Truncate anything after the sign-off line. Models occasionally add notes/P.S.…, _strip_after_signoff(), _strip_preamble(), _company_tokens(), Lowercase word tokens from the job's company name. This codebase already treats…, Deterministic check: a tool/tech token in the job description but absent from…, Every job-description tool the candidate doesn't have that appears as a whole… (+22 more)

### Community 44 - "validate_cover_letter"
Cohesion: 0.08
Nodes (24): has_bad_signoff(), has_dangling_reference(), has_lifted_jd_span(), has_repeated_phrase(), _is_mostly_filler(), True if a body paragraph opens with a back-reference to a sentence that isn't…, True if an n-gram is mostly stopwords/connective filler ('in order to be able…, Return the first phrase of `min_words` or more that appears more than once in… (+16 more)

### Community 45 - "generate_cover_letter"
Cohesion: 0.25
Nodes (8): generate_cover_letter(), _normalize_greeting_spacing(), Guarantee exactly one blank line between the "Dear ...," greeting and the first…, Deterministic, code-only removal of any sentence naming one of the given leaked…, Proactively swap any sentence carrying a digit for the matching verified fact's…, Generate a cover letter with fresh context on each retry + auto-sanitize. Same…, _recover_numeric_sentences(), _strip_tool_sentences()

### Community 46 - "Fact"
Cohesion: 0.18
Nodes (8): Fact, One verifiable, pre-written claim the LLM may select for a bullet., A fact is one real thing; it belongs on the CV once -- even if that means a…, If dedup would leave PROJECTS with no entries at all, it stays empty --…, Once on the id line isn't enough: the variant text is what the model reads when…, A letter has no entries, so ownership is meaningless there., TestCrossSectionDedup, TestFormatFactsBlockOwner

### Community 47 - "drop_unverifiable_quotes"
Cohesion: 0.21
Nodes (8): drop_unverifiable_quotes(), _quote_key(), Normalised form for checking a model-supplied quote against the CV. Case and…, Remove any model-quoted bullet that does not actually occur in the CV. The…, The guard that keeps a finding from resting on a quote the CV does not contain.…, The model quotes bullets as rendered; resolved bullets have no dash. Stripping…, Documented consequence of the rule as specified: containment is checked against…, TestDropUnverifiableQuotes

### Community 48 - "manifest.json"
Cohesion: 0.18
Nodes (10): contract, corpus_A_size, corpus_B_size, critic_commit, dropped_stale_on_rescore, generator_commit, model, tailor_settings (+2 more)

### Community 49 - "scrape_site_batch"
Cohesion: 0.33
Nodes (7): Connection, Re-fetch WTTJ Algolia API to get proper detail URLs and fix slug-as-title.…, Process all jobs for one site using shared browser context. If conn is None,…, Groups pending jobs by site and processes each batch. Sequential by default.…, resolve_wttj_urls(), _run_detail_scraper(), scrape_site_batch()

### Community 51 - "combined_critic_score"
Cohesion: 0.39
Nodes (3): combined_critic_score(), The single critic_score value stored on the job row: the average of whichever…, TestCombinedCriticScore

### Community 52 - "build_corpus.py"
Cohesion: 0.36
Nodes (6): build(), enrich(), extract(), load(), log(), Build corpus v2 -- two corpora, separate files, never pooled. A. Calibration…

### Community 53 - "Critic calibration corpus v2"
Cohesion: 0.29
Nodes (6): Critic calibration corpus v2, Known limitation — read before calibrating anything against this, Reproducing, Supporting files, The contract, Two corpora, never pooled

### Community 55 - "FactBank"
Cohesion: 0.09
Nodes (34): get_profile_keywords(), load_profile(), Extract full list of technical skills, domains, and role keywords from…, Load user profile from ~/.applypilot/profile.json., FactBank, Path, Parses facts.yaml and is the sole gate on what quantified claims the tailoring…, Parse facts.yaml into Facts, validating every verified fact's numbers against… (+26 more)

### Community 58 - "analyse"
Cohesion: 0.33
Nodes (5): _is_differentiator_bullet(), True for an award/recognition/funding bullet -- see _DIFFERENTIATOR_BULLET_RE.…, analyse(), parse_cv(), Sufficiency report for corpus A, firing table for corpus B. Extractions were…

### Community 60 - "facts.py"
Cohesion: 0.14
Nodes (13): BulletPlacementViolation, FactBankError, FactBankLoadError, NumericGuard, NumericGuardViolation, Exception, Verified-fact bank for resume tailoring. facts.yaml (repo root) is the ONLY…, Base class for fact-bank problems. (+5 more)

### Community 61 - "extract_with_llm"
Cohesion: 0.33
Nodes (6): clean_content_html(), extract_main_content(), extract_with_llm(), Extract the main content area, stripped of navigation noise., Clean detail page HTML for LLM consumption., Send focused HTML to LLM for extraction. Fallback tier.

### Community 62 - "get_locale_style"
Cohesion: 0.29
Nodes (8): get_locale_style(), Infer document terminology and layout conventions from the candidate's country.…, format_facts_block(), Render verified facts as an id-keyed list for a prompt. Shared by resume…, _build_cover_letter_prompt(), Build the cover letter system prompt from the user's profile. All personal…, _build_tailor_prompt(), Build the resume tailoring system prompt from the user's profile. All skills…

### Community 63 - "find_header_restating_bullets"
Cohesion: 0.06
Nodes (33): _bullet_text(), _bullets_similar(), _entry_span_months(), find_header_restating_bullets(), find_summary_duplicate_bullets(), _likely_fact_id(), _merge_canonical_section(), Length in months of the first date range in `text`, or None. An open-ended… (+25 more)

### Community 64 - "TestBulletOwnership"
Cohesion: 0.40
Nodes (3): A fact bound to one real employer/project (Fact.source, set from its facts.yaml…, No canonical record matched this entry -- there's no ground truth to check it…, TestBulletOwnership

### Community 66 - "_store_jobs_filtered"
Cohesion: 0.40
Nodes (5): _location_ok(), Connection, Check if a job location passes the user's location filter., Store jobs with location filtering. Returns (new, existing)., _store_jobs_filtered()

### Community 67 - "test_facts.py"
Cohesion: 0.16
Nodes (10): _bank(), _embedded_fact(), _FakeClient, _qualitative_fact(), Tests for the FactBank / NumericGuard architectural fabrication guard. Fixtures…, Always returns the same fabricated response, regardless of the 'AVOID THESE…, A zero-number verified fact (mirrors kraydel.audit_system)., A use_when-restricted fact (mirrors edu.embedded_marks). (+2 more)

### Community 68 - "view.py"
Cohesion: 0.06
Nodes (37): Row, Clear one job's apply status back to pending, e.g. after a wrong manual mark or…, reset_job(), classify_location(), derive_company(), description_shingles(), group_near_identical(), _location_priority_tier() (+29 more)

### Community 72 - "TestRewordedFactBullets"
Cohesion: 0.20
Nodes (4): The wording is the model's; the numbers are not. A rewording that reaches for a…, Tighter than NumericGuard's global allowed set on purpose: 11 is verified, but…, Back-compat: the original select-a-variant shape is unchanged., TestRewordedFactBullets

### Community 73 - "main"
Cohesion: 0.67
Nodes (3): callback, main(), ScoutPilot — scouts early-career jobs, scores fit, and tailors your CV per…

## Knowledge Gaps
- **39 isolated node(s):** `generator_commit`, `critic_commit`, `model`, `max_retries`, `validation_mode` (+34 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_connection()` connect `database.py` to `tailor.py`, `hacker_news.py`, `main`, `view.py`, `list_jobs`, `config.py`, `test_cohort.py`, `detail.py`, `run_job`, `datetime`, `cli.py`, `scorer.py`, `init_db`, `jobspy.py`, `FactBank`, `launcher.py`, `workday.py`?**
  _High betweenness centrality (0.174) - this node is a cross-community bridge._
- **Why does `FactBank` connect `FactBank` to `tailor.py`, `get_client`, `TestBulletOwnership`, `test_facts.py`, `UnfilledFact`, `.verified`, `TestRewordedFactBullets`, `ToolLeakGuard`, `generate_cover_letter`, `Fact`, `check_no_cross_section_duplicates`, `test_critic.py`, `._bank`, `facts.py`, `get_locale_style`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `FactBank` (e.g. with `_build_cover_letter_prompt()` and `cover_letter_one()`) actually correct?**
  _`FactBank` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `tailor_resume()` (e.g. with `BulletPlacementViolation` and `FactBank`) actually correct?**
  _`tailor_resume()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `generator_commit`, `critic_commit`, `model` to the rest of the system?**
  _39 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `tailor.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06448979591836734 - nodes in this community are weakly interconnected._
- **Should `test_prefilter.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11948790896159317 - nodes in this community are weakly interconnected._