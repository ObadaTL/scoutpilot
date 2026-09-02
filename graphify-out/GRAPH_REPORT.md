# Graph Report - ApplyPilot-main  (2026-09-02)

## Corpus Check
- 70 files · ~199,188 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1432 nodes · 2890 edges · 75 communities (70 shown, 5 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 123 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b34b43e4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- sanitize_text
- config.py
- ._run
- database.py
- smartextract.py
- evaluate_cv_observations
- main
- view.py
- .verified
- _StageTracker
- datetime
- detail.py
- LLMClient
- workday.py
- pdf.py
- worker_loop
- direct_ats.py
- cli.py
- scorer.py
- _repair_summary
- Contributing to ScoutPilot
- jobspy.py
- prompt.py
- test_critic.py
- run_wizard
- tailor_resume
- launcher.py
- ._bank
- critic.py
- validator.py
- check_no_cross_section_duplicates
- derive_company
- get_client
- find_header_restating_bullets
- dashboard.py
- test_cover_letter.py
- [0.2.0] - 2026-02-17
- run_job
- list_jobs
- FactBank
- rules/graphify.md
- workflows/graphify.md
- ToolLeakGuard
- validate_cover_letter
- NumericGuard
- Fact
- drop_unverifiable_quotes
- manifest.json
- _strip_preamble
- scoring/__init__.py
- combined_critic_score
- build_corpus.py
- Critic calibration corpus v2
- scoutpilot
- cover_letter.py
- evaluate_letter_observations
- test_enrichment.py
- load_location_focus
- facts.py
- load_profile
- format_facts_block
- tailor.py
- TestBulletOwnership
- _HTMLStripper
- _store_jobs_filtered
- test_facts.py
- group_near_identical
- _CleanClient
- has_bad_signoff
- reset_failed
- TestRewordedFactBullets
- main
- find_min_bullet_violations

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

## Communities (75 total, 5 thin omitted)

### Community 0 - "sanitize_text"
Cohesion: 0.12
Nodes (20): Split arbitrary CV/resume text into sections keyed by ALL-CAPS headers. Unlike…, split_sections(), assemble_resume_text(), _base_summary(), _canonical_education_line(), _canonical_skills_lines(), extract_extra_sections(), _fallback_unquantified() (+12 more)

### Community 1 - "config.py"
Cohesion: 0.06
Nodes (63): _deep_merge(), get_chrome_user_data(), get_profile_keywords(), load_ats_employers(), load_base_urls(), load_company_pages_config(), load_grad_boards_config(), load_prefilter_config() (+55 more)

### Community 2 - "._run"
Cohesion: 0.10
Nodes (12): _DegreeAsJobClient, Shipping is the LAST-attempt behaviour, not the first: while attempts remain, a…, Once canonical_entries.experience is configured, it's exhaustive: an EXPERIENCE…, The exact incident: the model filed the candidate's own degree as a job once…, The same unmatched-entry situation in PROJECTS is kept, not rejected -- a…, TECHNICAL SKILLS renders only what the profile actually declares -- the LLM's…, The exact incident: the model added 'LangChain (agent frameworks)' and…, A model that files the candidate's own degree as an EXPERIENCE entry. Measured… (+4 more)

### Community 3 - "database.py"
Cohesion: 0.06
Nodes (69): mark_job(), Manually mark a job's apply status in the database. Records this as a completed…, Reverse `archive-discovery` — bring archived discovery rows back., Show pipeline statistics from the database., restore_discovery(), status(), apply_duplicate_marks(), archive_discovery_results() (+61 more)

### Community 4 - "smartextract.py"
Cohesion: 0.09
Nodes (31): ask_llm(), build_scrape_targets(), clean_card_html(), clean_page_html(), collect_page_intelligence(), execute_api_response(), execute_css_selectors(), execute_json_ld() (+23 more)

### Community 5 - "evaluate_cv_observations"
Cohesion: 0.11
Nodes (13): evaluate_cv_observations(), Apply fixed, code-side thresholds to the model's raw extraction. Never trusts…, On three bullets a single NONE is already a third: the fraction carries no…, The exact incident: Revolut round 2 (2026-08-26) was flagged 6/11 while a human…, The counterpart the exemption must not swallow: round 1's Java Software…, The exact incident: 'VIOFEEL has 1 bullet, below the minimum of 2' landed on 6…, The floor drops only where the material genuinely runs out. Kraydel has nine…, The model quotes the header back out of the rendered CV; only case and spacing… (+5 more)

### Community 6 - "main"
Cohesion: 0.13
Nodes (23): Popen, cleanup_on_exit(), cleanup_worker(), kill_all_chrome(), _kill_on_port(), _kill_process_tree(), launch_chrome(), Path (+15 more)

### Community 7 - "view.py"
Cohesion: 0.12
Nodes (25): Clear one job's apply status back to pending, e.g. after a wrong manual mark or…, reset_job(), hide_job(), Mark a job hidden so it stops showing by default and stops being picked up for…, Reverse hide_job() -- the job becomes visible and eligible for the pipeline…, unhide_job(), is_local_provider(), True when generation will hit a local (non-cloud) LLM_URL endpoint. Mirrors… (+17 more)

### Community 8 - ".verified"
Cohesion: 0.11
Nodes (13): _accept_reworded(), _extract_numbers(), Recursively pull every integer token out of a nested structure. Used to fold…, Deterministic keyword extraction from a fact's free-text `use_when`.…, Best-effort recovery for a plain-string bullet that has a digit but is actually…, All tier == 'verified' facts. The ONLY facts ever exposed to the LLM., Every number the tailoring output is allowed to contain: the union of every…, Verified facts worth offering the LLM for this job. Facts with no `use_when`… (+5 more)

### Community 9 - "_StageTracker"
Cohesion: 0.20
Nodes (5): Event, Thread-safe tracker for which stages have finished producing work., Run a single stage in streaming mode: loop until upstream done + no work. For…, _run_stage_streaming(), _StageTracker

### Community 10 - "datetime"
Cohesion: 0.06
Nodes (30): datetime, close_connection(), Close the cached connection for the current thread., cohort_bucket(), cohort_rank(), infer_cohort_start(), _now(), Start-date / cohort inference for a discovered opportunity. A role that starts… (+22 more)

### Community 11 - "detail.py"
Cohesion: 0.07
Nodes (48): parse_proxy(), Parse host:port:user:pass into components., extract_json(), Extract JSON from LLM response, handling think tags and code fences., clean_content_html(), clean_description(), collect_detail_intelligence(), extract_apply_url_deterministic() (+40 more)

### Community 12 - "LLMClient"
Cohesion: 0.13
Nodes (11): Response, _GeminiCompatForbidden, LLMClient, Exception, Thin LLM client supporting OpenAI-compatible and native Gemini endpoints. For…, Call the native Gemini generateContent API. Used automatically when the OpenAI-…, Call the OpenAI-compatible endpoint. json_schema, when given, is passed as…, Call Ollama's native /api/chat, optionally with a JSON-schema `format`.… (+3 more)

### Community 13 - "workday.py"
Cohesion: 0.09
Nodes (28): fetch_details(), _fetch_one_detail(), load_employers(), _load_location_filter(), _location_ok(), _process_one(), Connection, Workday ATS direct API scraper: searches employer career portals. Scrapes… (+20 more)

### Community 14 - "pdf.py"
Cohesion: 0.09
Nodes (27): Stage: PDF conversion — convert tailored resumes and cover letters to PDF., _run_pdf(), batch_convert(), build_cover_letter_html(), build_html(), _cover_letter_font_faces(), _cv_font_faces(), _fit_resume_html() (+19 more)

### Community 15 - "worker_loop"
Cohesion: 0.15
Nodes (14): add_event(), Update the worker's state fields. Args: worker_id: Which worker to update.…, Add a timestamped event to the scrolling event log. Args: msg: Rich markup…, update_state(), _is_permanent_failure(), mark_result(), Record an attempt's outcome and mirror it onto the job., Release the in_progress lock without recording a terminal outcome. Used when a… (+6 more)

### Community 16 - "direct_ats.py"
Cohesion: 0.06
Nodes (58): _db_seed_entries(), _expand_ats(), _pointer_row(), Company-first discovery: harvest employer career pages, not job boards. Same…, Harvest the company-first registry. Returns {total_found, new, existing,…, Flatten the NI/UK employer lists into a single list of entry dicts., jobs.company values that match the known_boards map -> ATS entries., _registry_entries() (+50 more)

### Community 17 - "cli.py"
Cohesion: 0.05
Nodes (72): command, add(), apply(), archive_discovery(), _bootstrap(), clean(), dashboard(), discover() (+64 more)

### Community 18 - "scorer.py"
Cohesion: 0.05
Nodes (35): apply_eligibility_gate(), _build_candidate_level(), _candidate_is_unrestricted(), _clean_optional_field(), _countries_in_text(), _country_in_text(), _normalize_country(), _parse_score_response() (+27 more)

### Community 19 - "_repair_summary"
Cohesion: 0.28
Nodes (7): Rewrite `resolved_data["summary"]` in place if it fell into a rut or just…, _repair_summary(), _Client, The duplication defect fires on nearly every CV, so it repairs one field rather…, Describing the rule isn't enough -- the model has to see the sentences it is…, A rewrite is LLM-authored text like any other and gets the same numeric…, TestRepairSummary

### Community 20 - "Contributing to ScoutPilot"
Cohesion: 0.08
Nodes (23): Adding New Career Sites, Adding New Workday Employers, Bug Fixes and Features, Clone and Install, Code Style Guidelines, Contributing to ScoutPilot, Development Setup, How to Contribute (+15 more)

### Community 21 - "jobspy.py"
Cohesion: 0.13
Nodes (16): _full_crawl(), _load_location_config(), _location_ok(), JobSpy-based job discovery: searches Indeed, LinkedIn, Glassdoor, ZipRecruiter.…, Run a single search query and store results in DB., Run a single job search via JobSpy and store results in DB., Run all search queries from search config across all locations., Call scrape_jobs with retry on transient failures. (+8 more)

### Community 22 - "prompt.py"
Cohesion: 0.15
Nodes (19): _build_captcha_section(), _build_hard_rules(), _build_location_check(), _build_profile_summary(), build_prompt(), _build_salary_section(), _build_screening_section(), Prompt builder for the autonomous job application agent. Constructs the full… (+11 more)

### Community 23 - "test_critic.py"
Cohesion: 0.17
Nodes (10): build_bullet_floor_map(), Per-entry minimum bullet counts for the critic, derived from how much real…, _fact(), Tests for the critic pass's CODE-side threshold logic (critic.py). These test…, Stands in for FactBank: the floor map only ever asks it which verified facts…, build_bullet_floor_map lives in tailor.py but exists only to feed…, The critic counts bullets under PROJECTS as well, so a floor is needed there or…, No verified material behind an entry means nothing to ask for -- the guard must… (+2 more)

### Community 24 - "run_wizard"
Cohesion: 0.12
Nodes (21): doctor(), init(), Run the first-time setup wizard (profile, resume, search config)., Check your setup and diagnose missing requirements., get_chrome_path(), get_tier(), Auto-detect Chrome/Chromium executable path, cross-platform. Override with…, Detect the current tier based on available dependencies. Tier 1 (Discovery):… (+13 more)

### Community 25 - "tailor_resume"
Cohesion: 0.10
Nodes (22): _build_guard_scan_text(), _build_tailor_prompt(), Text scope NumericGuard checks: LLM-authored content (title, summary, skills,…, Generate a tailored resume via JSON output + fresh context on each retry. Key…, Build, assemble, and re-verify the unquantified fallback. Called only after…, Absolute last resort: remove every digit from every LLM-authored field (title,…, Last-resort removal for a leaked tool ToolLeakGuard still finds on the final…, JSON Schema for the tailor prompt's expected output shape. Passed as… (+14 more)

### Community 26 - "launcher.py"
Cohesion: 0.18
Nodes (13): Apply pipeline: Chrome management, prompt building, orchestration, and…, acquire_job(), _load_blocked(), Apply orchestration: acquire jobs, spawn Claude Code sessions, track results.…, Atomically acquire the next job to apply to and open an attempt for it. Args:…, is_manual_ats(), load_blocked_sites(), load_sites_config() (+5 more)

### Community 27 - "._bank"
Cohesion: 0.23
Nodes (7): _kraydel_multiparty_fact(), Bullets that carry no fact id must contain no digits -- enforced in code, not…, Mirrors the real kraydel.multiparty_calls entry in facts.yaml., A plausible-but-unevidenced fact that must never reach the LLM., The core guarantee: relevant_facts() (what actually goes into the LLM prompt)…, TestFactBankRejectsUnverified, _unverified_fact()

### Community 28 - "critic.py"
Cohesion: 0.21
Nodes (13): _build_cv_critic_user_message(), _build_letter_critic_user_message(), CriticResult, _is_differentiator_bullet(), _normalize_header(), Extraction-only "critic" pass over a tailored CV and cover letter. Catches…, Loose key for matching a header the model quoted back out of the CV against the…, score is COMPUTED from discrete findings (10.0 minus each finding's weight,… (+5 more)

### Community 29 - "validator.py"
Cohesion: 0.15
Nodes (15): _company_tokens(), find_fabricated_numbers(), has_dangling_reference(), has_lifted_jd_span(), has_repeated_phrase(), _is_mostly_filler(), Resume and cover letter validation: banned words, fabrication detection,…, Find number-bearing claims in tailored text with no basis in the original.… (+7 more)

### Community 30 - "check_no_cross_section_duplicates"
Cohesion: 0.15
Nodes (11): check_no_cross_section_duplicates(), _normalize_bullet_for_dup_check(), Hard assertion: the same claim may not appear twice anywhere in the assembled…, check_no_cross_section_duplicates is the hard backstop: even if ownership/dedup…, Exact-text matching alone missed this live 2026-08-26: the same fact, worded…, The blind spot the projects-vs-experience loop had by construction: two bullets…, The exact pairing named in _likely_fact_id's docstring: 'Built dual ML…, Same section, two different headings -- also invisible to the old loop, which… (+3 more)

### Community 31 - "derive_company"
Cohesion: 0.06
Nodes (19): Row, derive_company(), Best available employer name for a job, for grouping in the dashboard. Derived…, fixture, Dashboard behaviour: CV/cover-letter independence, and the two things that made…, searches.yaml is hand-edited, so the cache is keyed on the file's own…, applyFilters() matches the search term against `card.textContent`. On…, A cover-letter failure used to set the job's single status field to "error".… (+11 more)

### Community 32 - "get_client"
Cohesion: 0.22
Nodes (9): _detect_provider(), get_client(), Unified LLM client for ScoutPilot. Auto-detects provider from environment:…, Return (base_url, model, api_key) based on environment variables. Reads env at…, Return (or create) the module-level LLMClient singleton., _build_judge_prompt(), judge_tailored_resume(), LLM judge layer: catches subtle fabrication that programmatic checks miss.… (+1 more)

### Community 33 - "find_header_restating_bullets"
Cohesion: 0.18
Nodes (9): _entry_span_months(), find_header_restating_bullets(), Length in months of the first date range in `text`, or None. An open-ended…, Bullets that only say again what their own entry header already says. This…, The code check that replaced the model clause., The exact bullet the model never flagged: '11-month industry placement ...'…, 1st place, QUB Dragon's Den 2024' under 'Apr 2024 - Mar 2026' shares a year and…, Aug 2026 - Present' has no fixed span, so a duration claim against it can't be… (+1 more)

### Community 34 - "dashboard.py"
Cohesion: 0.16
Nodes (14): Group, get_state(), get_totals(), init_worker(), Rich live dashboard for the apply pipeline. Displays real-time worker status,…, Build the Rich table showing all worker statuses. Returns: A Rich Table object…, Render the dashboard table plus the recent events panel. Returns: A Rich Group…, Compute aggregate totals across all workers. Returns: Dict with keys: applied,… (+6 more)

### Community 35 - "test_cover_letter.py"
Cohesion: 0.20
Nodes (10): _bank(), _FabricatingClient, isolated_env(), _multiparty_fact(), fixture, Tests for the six cover-letter-generation defect fixes. Fast unit tests…, Always fabricates the same unverified number, regardless of retry feedback --…, Retries must keep sampling temperature, not drop it. The old behaviour was 0.7… (+2 more)

### Community 36 - "[0.2.0] - 2026-02-17"
Cohesion: 0.25
Nodes (7): [0.1.0] - 2026-02-17, [0.2.0] - 2026-02-17, Added, Added, Changed, Changelog, Fixed

### Community 37 - "run_job"
Cohesion: 0.17
Nodes (13): _check_playwright_mcp(), gen_prompt(), _make_mcp_config(), Path, Generate a prompt file and print the Claude CLI command for manual debugging.…, Inspect a system/init stream-json event for playwright MCP health. Browser…, Spawn a Claude Code session for one job application. Returns: Tuple of…, Build MCP config dict for a specific CDP port. (+5 more)

### Community 38 - "list_jobs"
Cohesion: 0.13
Nodes (12): Console, list_jobs(), Terminal job-detail listing: fit score and company context for individual jobs,…, Fetch scored jobs for terminal display, filtered and sorted by fit. Args:…, Render one Rich panel per job with fit score, company context, tailored…, render_jobs(), fixture, Tests for terminal_view.list_jobs / render_jobs (the `scoutpilot jobs` command). (+4 more)

### Community 39 - "FactBank"
Cohesion: 0.13
Nodes (15): check_listing_still_open(), Best-effort check for whether a job listing is still accepting applications,…, FactBank, Path, A known gap: a plausible claim that needs a real value filled in before it can…, Parses facts.yaml and is the sole gate on what quantified claims the tailoring…, Parse facts.yaml into Facts, validating every verified fact's numbers against…, Unverified entries pending a real value, for a CLI prompt flow. (+7 more)

### Community 43 - "ToolLeakGuard"
Cohesion: 0.16
Nodes (11): Exception, Raised by ToolLeakGuard when a job-description tool the candidate doesn't have…, Deterministic check: a tool/tech token in the job description but absent from…, Every job-description tool the candidate doesn't have that appears as a whole…, Raise ToolLeakViolation if a job-description tool the candidate doesn't have…, ToolLeakGuard, ToolLeakViolation, _profile() (+3 more)

### Community 44 - "validate_cover_letter"
Cohesion: 0.16
Nodes (11): Programmatic validation of a cover letter. Args: text: The cover letter text to…, validate_cover_letter(), ...with % accuracy" -- the digit-blanking fallback's signature., A first body paragraph opening on a referent that was deleted., Only the FIRST body paragraph can dangle -- a later "That ..." points at the…, lenient tolerates style sins, not a letter with holes in it -- and lenient is…, The fallback drops the paragraph rather than leaving its units stranded. Less…, The same 5+ word claim showing up twice reads as padding, not two different… (+3 more)

### Community 45 - "NumericGuard"
Cohesion: 0.23
Nodes (7): NumericGuard, Deterministic, post-generation check: every number in the assembled resume text…, _qualitative_fact(), Canonical example: an injected, unevidenced 500 must be caught., The real 4-to-9 participant fact must pass cleanly., A zero-number verified fact (mirrors kraydel.audit_system)., TestNumericGuard

### Community 46 - "Fact"
Cohesion: 0.27
Nodes (6): Fact, One verifiable, pre-written claim the LLM may select for a bullet., A fact is one real thing; it belongs on the CV once -- even if that means a…, The duplicate bullet goes; the entry survives on its other one., If dedup would leave PROJECTS with no entries at all, it stays empty --…, TestCrossSectionDedup

### Community 47 - "drop_unverifiable_quotes"
Cohesion: 0.21
Nodes (8): drop_unverifiable_quotes(), _quote_key(), Normalised form for checking a model-supplied quote against the CV. Case and…, Remove any model-quoted bullet that does not actually occur in the CV. The…, The guard that keeps a finding from resting on a quote the CV does not contain.…, The model quotes bullets as rendered; resolved bullets have no dash. Stripping…, Documented consequence of the rule as specified: containment is checked against…, TestDropUnverifiableQuotes

### Community 48 - "manifest.json"
Cohesion: 0.18
Nodes (10): contract, corpus_A_size, corpus_B_size, critic_commit, dropped_stale_on_rescore, generator_commit, model, tailor_settings (+2 more)

### Community 49 - "_strip_preamble"
Cohesion: 0.21
Nodes (7): Remove LLM preamble before 'Dear Hiring Manager,' if present. Gemini and other…, Truncate anything after the sign-off line. Models occasionally add notes/P.S.…, _strip_after_signoff(), _strip_preamble(), An incidental earlier mention of the name must not truncate the real body that…, endeared'/'dearest' mid-preamble must not be mistaken for the letter's real…, TestStripHelpers

### Community 51 - "combined_critic_score"
Cohesion: 0.39
Nodes (3): combined_critic_score(), The single critic_score value stored on the job row: the average of whichever…, TestCombinedCriticScore

### Community 52 - "build_corpus.py"
Cohesion: 0.36
Nodes (6): build(), enrich(), extract(), load(), log(), Build corpus v2 -- two corpora, separate files, never pooled. A. Calibration…

### Community 53 - "Critic calibration corpus v2"
Cohesion: 0.29
Nodes (6): Critic calibration corpus v2, Known limitation — read before calibrating anything against this, Reproducing, Supporting files, The contract, Two corpora, never pooled

### Community 55 - "cover_letter.py"
Cohesion: 0.10
Nodes (28): get_locale_style(), Infer document terminology and layout conventions from the candidate's country.…, Stage: Cover letter generation., _run_cover(), _build_cover_letter_prompt(), _check_company_mentioned(), generate_cover_letter(), _generate_one_cover_letter() (+20 more)

### Community 57 - "test_enrichment.py"
Cohesion: 0.22
Nodes (3): Tests for the HTTP-first (tier 0) detail-page path in enrichment/detail.py., When tier 0 succeeds, page.goto is never called., test_scrape_detail_page_short_circuits_on_http_first()

### Community 58 - "load_location_focus"
Cohesion: 0.22
Nodes (11): load_location_focus(), Load the optional `location_focus` section from searches.yaml. A temporary,…, classify_location(), Human-readable place label for a job's location, for the dashboard's place…, generate_dashboard(), open_dashboard(), Path, Generate a static dashboard snapshot and open it in the default browser -- a… (+3 more)

### Community 60 - "facts.py"
Cohesion: 0.12
Nodes (14): BulletPlacementViolation, FactBankError, FactBankLoadError, NumericGuardViolation, Exception, Verified-fact bank for resume tailoring. facts.yaml (repo root) is the ONLY…, Base class for fact-bank problems., Raised when facts.yaml fails integrity checks at load time. (+6 more)

### Community 61 - "load_profile"
Cohesion: 0.24
Nodes (10): load_profile(), Load user profile from ~/.applypilot/profile.json., add_and_process_job(), _insert_stub(), Manually add a single job posting by URL and run it through enrichment +…, Insert a bare row for `url` if absent. Returns 'new' | 'existing' | 'revived'…, Add `url`, enrich it, score it. Returns a summary dict: {url, added,…, Score a single job against the resume. Args: resume_text: The candidate's full… (+2 more)

### Community 62 - "format_facts_block"
Cohesion: 0.33
Nodes (5): format_facts_block(), Render verified facts as an id-keyed list for a prompt. Shared by resume…, Once on the id line isn't enough: the variant text is what the model reads when…, A letter has no entries, so ownership is meaningless there., TestFormatFactsBlockOwner

### Community 63 - "tailor.py"
Cohesion: 0.10
Nodes (24): _apply_canonical_entries(), _bullet_text(), _bullets_similar(), _entry_owns_fact(), find_summary_duplicate_bullets(), _likely_fact_id(), _merge_canonical_section(), Resume tailoring: LLM-powered ATS-optimized resume generation per job. THIS IS… (+16 more)

### Community 64 - "TestBulletOwnership"
Cohesion: 0.40
Nodes (3): A fact bound to one real employer/project (Fact.source, set from its facts.yaml…, No canonical record matched this entry -- there's no ground truth to check it…, TestBulletOwnership

### Community 65 - "_HTMLStripper"
Cohesion: 0.25
Nodes (3): HTMLParser, _HTMLStripper, Strip HTML tags, keep text content.

### Community 66 - "_store_jobs_filtered"
Cohesion: 0.40
Nodes (5): _location_ok(), Connection, Check if a job location passes the user's location filter., Store jobs with location filtering. Returns (new, existing)., _store_jobs_filtered()

### Community 67 - "test_facts.py"
Cohesion: 0.20
Nodes (8): _bank(), _embedded_fact(), _FakeClient, Tests for the FactBank / NumericGuard architectural fabrication guard. Fixtures…, Always returns the same fabricated response, regardless of the 'AVOID THESE…, A use_when-restricted fact (mirrors edu.embedded_marks)., TestFactBankJobAwareSelection, TestGuardFailureFallsBack

### Community 68 - "group_near_identical"
Cohesion: 0.23
Nodes (8): description_shingles(), group_near_identical(), Set of 5-word shingle hashes over a description's first 600 words. Order-…, Map url -> a group number, for ads that read as the same posting. Only urls…, shingle_jaccard(), Advisory badge only. It must never be wired to duplicate_of: the 2026-09-02…, Below 0.8 Jaccard, 0 of 1093 sampled same-employer pairs were duplicates by the…, TestGroupNearIdentical

### Community 69 - "_CleanClient"
Cohesion: 0.40
Nodes (3): _CleanClient, A well-behaved local model: no fabricated numbers, no leaked tools, names the…, TestRunCoverLettersIntegration

### Community 70 - "has_bad_signoff"
Cohesion: 0.40
Nodes (3): has_bad_signoff(), Return a description of what's wrong with the sign-off, or None. The prompt…, The prompt asks for 'Sincerely,' then the name and nothing else -- a trailing…

### Community 71 - "reset_failed"
Cohesion: 0.33
Nodes (4): Reset all failed jobs so they can be retried. Returns: Number of jobs reset., reset_failed(), _count_pending(), Count pending work items for a stage.

### Community 72 - "TestRewordedFactBullets"
Cohesion: 0.20
Nodes (4): The wording is the model's; the numbers are not. A rewording that reaches for a…, Tighter than NumericGuard's global allowed set on purpose: 11 is verified, but…, Back-compat: the original select-a-variant shape is unchanged., TestRewordedFactBullets

### Community 73 - "main"
Cohesion: 0.67
Nodes (3): callback, main(), ScoutPilot — scouts early-career jobs, scores fit, and tailors your CV per…

### Community 74 - "find_min_bullet_violations"
Cohesion: 0.50
Nodes (4): _facts_available_for_entry(), find_min_bullet_violations(), The verified facts this CV entry is the real-world owner of. A Fact's `source`…, For each canonical EXPERIENCE entry with at least `min_bullets` relevant…

## Knowledge Gaps
- **39 isolated node(s):** `generator_commit`, `critic_commit`, `model`, `max_retries`, `validation_mode` (+34 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_connection()` connect `database.py` to `smartextract.py`, `main`, `view.py`, `detail.py`, `workday.py`, `worker_loop`, `direct_ats.py`, `cli.py`, `scorer.py`, `jobspy.py`, `launcher.py`, `run_job`, `list_jobs`, `FactBank`, `cover_letter.py`, `load_location_focus`, `load_profile`, `tailor.py`, `reset_failed`?**
  _High betweenness centrality (0.139) - this node is a cross-community bridge._
- **Why does `FactBank` connect `FactBank` to `get_client`, `sanitize_text`, `TestBulletOwnership`, `test_cover_letter.py`, `test_facts.py`, `view.py`, `.verified`, `TestRewordedFactBullets`, `find_min_bullet_violations`, `Fact`, `test_critic.py`, `cover_letter.py`, `tailor_resume`, `._bank`, `facts.py`, `check_no_cross_section_duplicates`, `tailor.py`?**
  _High betweenness centrality (0.113) - this node is a cross-community bridge._
- **Why does `apply_eligibility_gate()` connect `scorer.py` to `load_profile`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `FactBank` (e.g. with `_build_cover_letter_prompt()` and `cover_letter_one()`) actually correct?**
  _`FactBank` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `tailor_resume()` (e.g. with `BulletPlacementViolation` and `FactBank`) actually correct?**
  _`tailor_resume()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `generator_commit`, `critic_commit`, `model` to the rest of the system?**
  _39 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `sanitize_text` be split into smaller, more focused modules?**
  _Cohesion score 0.12105263157894737 - nodes in this community are weakly interconnected._