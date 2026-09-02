# Graph Report - ApplyPilot-main  (2026-09-02)

## Corpus Check
- 60 files · ~186,784 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1274 nodes · 2483 edges · 66 communities (60 shown, 6 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 117 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `30e1b6aa`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- tailor.py
- _HTMLStripper
- ._run
- get_connection
- smartextract.py
- evaluate_cv_observations
- main
- launcher.py
- facts.py
- _StageTracker
- dashboard.py
- scrape_detail_page
- LLMClient
- workday.py
- pdf.py
- run_job
- test_discovery.py
- cli.py
- scorer.py
- pipeline.py
- Contributing to ScoutPilot
- jobspy.py
- prompt.py
- test_critic.py
- run_wizard
- validator.py
- load_search_config
- _kraydel_multiparty_fact
- critic.py
- generate_dashboard
- check_no_cross_section_duplicates
- derive_company
- get_client
- end_run
- run_pipeline
- _run_cover_letter
- [0.2.0] - 2026-02-17
- find_header_restating_bullets
- list_jobs
- UnfilledFact
- rules/graphify.md
- workflows/graphify.md
- ToolLeakGuard
- validate_cover_letter
- _load_base_urls
- Fact
- drop_unverifiable_quotes
- manifest.json
- check_listing_still_open
- scoring/__init__.py
- combined_critic_score
- build_corpus.py
- Critic calibration corpus v2
- scoutpilot
- FactBank
- evaluate_letter_observations
- analyse
- _repair_summary
- find_summary_duplicate_bullets
- NumericGuard
- test_facts.py
- group_near_identical
- ._bank

## God Nodes (most connected - your core abstractions)
1. `get_connection()` - 56 edges
2. `FactBank` - 49 edges
3. `init_db()` - 32 edges
4. `tailor_resume()` - 32 edges
5. `Fact` - 28 edges
6. `evaluate_cv_observations()` - 22 edges
7. `generate_cover_letter()` - 20 edges
8. `TestEligibilityGate` - 20 edges
9. `NumericGuard` - 19 edges
10. `apply_eligibility_gate()` - 19 edges

## Surprising Connections (you probably didn't know these)
- `TestFactBankLoad` --uses--> `FactBankLoadError`  [INFERRED]
  tests/test_facts.py → src/scoutpilot/facts.py
- `TestNumericGuard` --uses--> `NumericGuardViolation`  [INFERRED]
  tests/test_facts.py → src/scoutpilot/facts.py
- `TestCrossSectionDuplicateAssertion` --uses--> `BulletPlacementViolation`  [INFERRED]
  tests/test_facts.py → src/scoutpilot/facts.py
- `analyse()` --uses--> `BulletPlacementViolation`  [INFERRED]
  tools/corpus/report_corpus.py → src/scoutpilot/facts.py
- `_fact()` --uses--> `Fact`  [INFERRED]
  tests/test_critic.py → src/scoutpilot/facts.py

## Import Cycles
- None detected.

## Communities (66 total, 6 thin omitted)

### Community 0 - "tailor.py"
Cohesion: 0.06
Nodes (54): Split arbitrary CV/resume text into sections keyed by ALL-CAPS headers. Unlike…, split_sections(), _apply_canonical_entries(), assemble_resume_text(), _base_summary(), _build_guard_scan_text(), _bullet_text(), _bullets_similar() (+46 more)

### Community 1 - "_HTMLStripper"
Cohesion: 0.25
Nodes (3): HTMLParser, _HTMLStripper, Strip HTML tags, keep text content.

### Community 2 - "._run"
Cohesion: 0.12
Nodes (10): Shipping is the LAST-attempt behaviour, not the first: while attempts remain, a…, Once canonical_entries.experience is configured, it's exhaustive: an EXPERIENCE…, The exact incident: the model filed the candidate's own degree as a job once…, The same unmatched-entry situation in PROJECTS is kept, not rejected -- a…, TECHNICAL SKILLS renders only what the profile actually declares -- the LLM's…, The exact incident: the model added 'LangChain (agent frameworks)' and…, The rejected entry is already deleted from the data by the time the error is…, TestCanonicalExperienceRejection (+2 more)

### Community 3 - "get_connection"
Cohesion: 0.07
Nodes (43): Clear one job's apply status back to pending, e.g. after a wrong manual mark or…, reset_job(), apply_duplicate_marks(), attach_tool_result(), clean_non_tech_jobs(), close_connection(), ensure_columns(), find_duplicate_groups() (+35 more)

### Community 4 - "smartextract.py"
Cohesion: 0.08
Nodes (36): get_stats(), Return job counts by pipeline stage. Provides a snapshot of how many jobs are…, ask_llm(), clean_card_html(), clean_page_html(), collect_page_intelligence(), execute_api_response(), execute_css_selectors() (+28 more)

### Community 5 - "evaluate_cv_observations"
Cohesion: 0.11
Nodes (13): evaluate_cv_observations(), Apply fixed, code-side thresholds to the model's raw extraction. Never trusts…, On three bullets a single NONE is already a third: the fraction carries no…, The exact incident: Revolut round 2 (2026-08-26) was flagged 6/11 while a human…, The counterpart the exemption must not swallow: round 1's Java Software…, The exact incident: 'VIOFEEL has 1 bullet, below the minimum of 2' landed on 6…, The floor drops only where the material genuinely runs out. Kraydel has nine…, The model quotes the header back out of the rendered CV; only case and spacing… (+5 more)

### Community 6 - "main"
Cohesion: 0.11
Nodes (26): Popen, cleanup_on_exit(), cleanup_worker(), kill_all_chrome(), _kill_on_port(), _kill_process_tree(), launch_chrome(), Path (+18 more)

### Community 7 - "launcher.py"
Cohesion: 0.08
Nodes (32): Apply pipeline: Chrome management, prompt building, orchestration, and…, acquire_job(), _load_blocked(), mark_job(), Apply orchestration: acquire jobs, spawn Claude Code sessions, track results.…, Manually mark a job's apply status in the database. Records this as a completed…, Reset all failed jobs so they can be retried. Returns: Number of jobs reset., Atomically acquire the next job to apply to and open an attempt for it. Args:… (+24 more)

### Community 8 - "facts.py"
Cohesion: 0.07
Nodes (23): _accept_reworded(), BulletPlacementViolation, _extract_numbers(), FactBankError, FactBankLoadError, NumericGuardViolation, Exception, Verified-fact bank for resume tailoring. facts.yaml (repo root) is the ONLY… (+15 more)

### Community 9 - "_StageTracker"
Cohesion: 0.17
Nodes (7): Event, _count_pending(), Thread-safe tracker for which stages have finished producing work., Count pending work items for a stage., Run a single stage in streaming mode: loop until upstream done + no work. For…, _run_stage_streaming(), _StageTracker

### Community 10 - "dashboard.py"
Cohesion: 0.16
Nodes (14): Group, get_state(), get_totals(), init_worker(), Rich live dashboard for the apply pipeline. Displays real-time worker status,…, Build the Rich table showing all worker statuses. Returns: A Rich Table object…, Render the dashboard table plus the recent events panel. Returns: A Rich Group…, Compute aggregate totals across all workers. Returns: Dict with keys: applied,… (+6 more)

### Community 11 - "scrape_detail_page"
Cohesion: 0.07
Nodes (31): clean_content_html(), clean_description(), collect_detail_intelligence(), extract_apply_url_deterministic(), extract_description_deterministic(), extract_from_json_ld(), extract_main_content(), extract_with_llm() (+23 more)

### Community 12 - "LLMClient"
Cohesion: 0.13
Nodes (11): Response, _GeminiCompatForbidden, LLMClient, Exception, Thin LLM client supporting OpenAI-compatible and native Gemini endpoints. For…, Call the native Gemini generateContent API. Used automatically when the OpenAI-…, Call the OpenAI-compatible endpoint. json_schema, when given, is passed as…, Call Ollama's native /api/chat, optionally with a JSON-schema `format`.… (+3 more)

### Community 13 - "workday.py"
Cohesion: 0.10
Nodes (28): fetch_details(), _fetch_one_detail(), load_employers(), _location_ok(), _process_one(), Connection, Workday ATS direct API scraper: searches employer career portals. Scrapes…, Convert HTML to plain text. (+20 more)

### Community 14 - "pdf.py"
Cohesion: 0.09
Nodes (27): Stage: PDF conversion — convert tailored resumes and cover letters to PDF., _run_pdf(), batch_convert(), build_cover_letter_html(), build_html(), _cover_letter_font_faces(), _cv_font_faces(), _fit_resume_html() (+19 more)

### Community 15 - "run_job"
Cohesion: 0.11
Nodes (23): add_event(), Update the worker's state fields. Args: worker_id: Which worker to update.…, Add a timestamped event to the scrolling event log. Args: msg: Rich markup…, update_state(), _check_playwright_mcp(), gen_prompt(), _is_permanent_failure(), _make_mcp_config() (+15 more)

### Community 16 - "test_discovery.py"
Cohesion: 0.08
Nodes (39): fetch_ashby_jobs(), fetch_greenhouse_jobs(), fetch_lever_jobs(), _http_get_json(), infer_opportunity_type(), is_relevant_tech_role(), Direct ATS API harvester: scrapes Greenhouse, Ashby, and Lever career portals.…, Helper to fetch and parse JSON from a public endpoint. (+31 more)

### Community 17 - "cli.py"
Cohesion: 0.07
Nodes (43): callback, command, apply(), _bootstrap(), clean(), dashboard(), doctor(), events() (+35 more)

### Community 18 - "scorer.py"
Cohesion: 0.06
Nodes (34): apply_eligibility_gate(), _build_candidate_level(), _candidate_is_unrestricted(), _clean_optional_field(), _country_in_text(), _normalize_country(), _parse_score_response(), Job fit scoring: LLM-powered evaluation of candidate-job match quality. Scores… (+26 more)

### Community 19 - "pipeline.py"
Cohesion: 0.10
Nodes (36): discover(), Run specific or all discovery harvesters to find jobs, graduate schemes, and…, init_db(), Create the full jobs table with all columns from every pipeline stage. This is…, Store discovered jobs, skipping duplicates by URL. Args: conn: Database…, store_jobs(), Scrape configured Greenhouse, Ashby, and Lever employers and store results into…, run_direct_ats_discovery() (+28 more)

### Community 20 - "Contributing to ScoutPilot"
Cohesion: 0.08
Nodes (23): Adding New Career Sites, Adding New Workday Employers, Bug Fixes and Features, Clone and Install, Code Style Guidelines, Contributing to ScoutPilot, Development Setup, How to Contribute (+15 more)

### Community 21 - "jobspy.py"
Cohesion: 0.13
Nodes (19): _full_crawl(), _load_location_config(), _location_ok(), parse_proxy(), Connection, JobSpy-based job discovery: searches Indeed, LinkedIn, Glassdoor, ZipRecruiter.…, Store JobSpy DataFrame results into the DB. Returns (new, existing)., Run a single search query and store results in DB. (+11 more)

### Community 22 - "prompt.py"
Cohesion: 0.16
Nodes (17): _build_captcha_section(), _build_hard_rules(), _build_location_check(), _build_profile_summary(), build_prompt(), _build_salary_section(), _build_screening_section(), Prompt builder for the autonomous job application agent. Constructs the full… (+9 more)

### Community 23 - "test_critic.py"
Cohesion: 0.17
Nodes (10): build_bullet_floor_map(), Per-entry minimum bullet counts for the critic, derived from how much real…, _fact(), Tests for the critic pass's CODE-side threshold logic (critic.py). These test…, Stands in for FactBank: the floor map only ever asks it which verified facts…, build_bullet_floor_map lives in tailor.py but exists only to feed…, The critic counts bullets under PROJECTS as well, so a floor is needed there or…, No verified material behind an entry means nothing to ask for -- the guard must… (+2 more)

### Community 24 - "run_wizard"
Cohesion: 0.17
Nodes (15): ensure_dirs(), Create all required directories., ScoutPilot first-time setup wizard. Interactive flow that creates…, Generate a searches.yaml from user input., Ask about AI scoring/tailoring — optional LLM configuration., Configure autonomous job application (requires Claude Code CLI)., Run the full interactive setup wizard., Prompt for resume file and copy into APP_DIR. (+7 more)

### Community 25 - "validator.py"
Cohesion: 0.18
Nodes (10): _build_skills_set(), find_fabricated_numbers(), Exception, Resume and cover letter validation: banned words, fabrication detection,…, Find number-bearing claims in tailored text with no basis in the original.…, Build the set of allowed skills from the profile's skills_boundary., Validate individual JSON fields from an LLM-generated tailored resume. Args:…, Raised by ToolLeakGuard when a job-description tool the candidate doesn't have… (+2 more)

### Community 26 - "load_search_config"
Cohesion: 0.21
Nodes (12): load_search_config(), Load search configuration from ~/.applypilot/searches.yaml. Cached on the…, build_scrape_targets(), _load_location_filter(), load_sites(), Main entry point for AI-powered smart extraction. Loads sites from…, Load location accept/reject lists from search config., Load scraping target sites from config/sites.yaml. (+4 more)

### Community 27 - "_kraydel_multiparty_fact"
Cohesion: 0.22
Nodes (7): _kraydel_multiparty_fact(), Bullets that carry no fact id must contain no digits -- enforced in code, not…, Mirrors the real kraydel.multiparty_calls entry in facts.yaml., A plausible-but-unevidenced fact that must never reach the LLM., The core guarantee: relevant_facts() (what actually goes into the LLM prompt)…, TestFactBankRejectsUnverified, _unverified_fact()

### Community 28 - "critic.py"
Cohesion: 0.26
Nodes (11): _build_cv_critic_user_message(), _build_letter_critic_user_message(), CriticResult, _normalize_header(), Extraction-only "critic" pass over a tailored CV and cover letter. Catches…, Loose key for matching a header the model quoted back out of the CV against the…, score is COMPUTED from discrete findings (10.0 minus each finding's weight,…, run_cv_critic() (+3 more)

### Community 29 - "generate_dashboard"
Cohesion: 0.18
Nodes (11): classify_location(), _is_relevant_remote(), _location_priority_tier(), True if a (lowercased) location's "remote" claim is UK/NI-relevant or…, 0-indexed priority tier for a job's location (lower = higher priority). Checked…, Human-readable place label for a job's location, for the dashboard's place…, generate_dashboard(), Path (+3 more)

### Community 30 - "check_no_cross_section_duplicates"
Cohesion: 0.15
Nodes (11): check_no_cross_section_duplicates(), _normalize_bullet_for_dup_check(), Hard assertion: the same claim may not appear twice anywhere in the assembled…, check_no_cross_section_duplicates is the hard backstop: even if ownership/dedup…, Exact-text matching alone missed this live 2026-08-26: the same fact, worded…, The blind spot the projects-vs-experience loop had by construction: two bullets…, The exact pairing named in _likely_fact_id's docstring: 'Built dual ML…, Same section, two different headings -- also invisible to the old loop, which… (+3 more)

### Community 31 - "derive_company"
Cohesion: 0.06
Nodes (19): Row, derive_company(), Best available employer name for a job, for grouping in the dashboard. Derived…, fixture, Dashboard behaviour: CV/cover-letter independence, and the two things that made…, searches.yaml is hand-edited, so the cache is keyed on the file's own…, applyFilters() matches the search term against `card.textContent`. On…, A cover-letter failure used to set the job's single status field to "error".… (+11 more)

### Community 32 - "get_client"
Cohesion: 0.22
Nodes (9): _detect_provider(), get_client(), Unified LLM client for ScoutPilot. Auto-detects provider from environment:…, Return (base_url, model, api_key) based on environment variables. Reads env at…, Return (or create) the module-level LLMClient singleton., _build_judge_prompt(), judge_tailored_resume(), LLM judge layer: catches subtle fabrication that programmatic checks miss.… (+1 more)

### Community 33 - "end_run"
Cohesion: 0.29
Nodes (8): end_run(), Record the start of one pipeline stage invocation. Args: conn: Database…, Record the end of a pipeline stage invocation. Args: conn: Database connection.…, start_run(), Stage: LLM scoring — assign fit scores 1-10., Stage: Resume tailoring — generate tailored resumes for high-fit jobs., _run_score(), _run_tailor()

### Community 34 - "run_pipeline"
Cohesion: 0.25
Nodes (8): Resolve 'all' and validate/order stage names., Execute stages one at a time (original behavior)., Execute stages concurrently with DB as conveyor belt., Run pipeline stages. Args: stages: List of stage names, or None / ["all"] for…, _resolve_stages(), run_pipeline(), _run_sequential(), _run_streaming()

### Community 35 - "_run_cover_letter"
Cohesion: 0.36
Nodes (8): _error_summary(), _on_demand_retries(), Background-thread target: tailor the CV, then generate the cover letter,…, Retry budget for a single on-demand click. A batch run defaults to 1 retry on a…, Generate the cover letter for one job, reporting into the job's `cover` field…, _run_cover_letter(), _run_tailor_and_cover(), _set_tailor_status()

### Community 36 - "[0.2.0] - 2026-02-17"
Cohesion: 0.25
Nodes (7): [0.1.0] - 2026-02-17, [0.2.0] - 2026-02-17, Added, Added, Changed, Changelog, Fixed

### Community 37 - "find_header_restating_bullets"
Cohesion: 0.18
Nodes (9): _entry_span_months(), find_header_restating_bullets(), Length in months of the first date range in `text`, or None. An open-ended…, Bullets that only say again what their own entry header already says. This…, The code check that replaced the model clause., The exact bullet the model never flagged: '11-month industry placement ...'…, 1st place, QUB Dragon's Den 2024' under 'Apr 2024 - Mar 2026' shares a year and…, Aug 2026 - Present' has no fixed span, so a duration claim against it can't be… (+1 more)

### Community 38 - "list_jobs"
Cohesion: 0.14
Nodes (11): Console, list_jobs(), Fetch scored jobs for terminal display, filtered and sorted by fit. Args:…, Render one Rich panel per job with fit score, company context, tailored…, render_jobs(), fixture, Tests for terminal_view.list_jobs / render_jobs (the `scoutpilot jobs` command)., Isolated scratch DB with a few jobs at different fit scores/sites, never… (+3 more)

### Community 39 - "UnfilledFact"
Cohesion: 0.40
Nodes (3): A known gap: a plausible claim that needs a real value filled in before it can…, Unverified entries pending a real value, for a CLI prompt flow., UnfilledFact

### Community 43 - "ToolLeakGuard"
Cohesion: 0.06
Nodes (30): Remove LLM preamble before 'Dear Hiring Manager,' if present. Gemini and other…, Truncate anything after the sign-off line. Models occasionally add notes/P.S.…, _strip_after_signoff(), _strip_preamble(), _company_tokens(), Lowercase word tokens from the job's company name. This codebase already treats…, Deterministic check: a tool/tech token in the job description but absent from…, Every job-description tool the candidate doesn't have that appears as a whole… (+22 more)

### Community 44 - "validate_cover_letter"
Cohesion: 0.08
Nodes (24): has_bad_signoff(), has_dangling_reference(), has_lifted_jd_span(), has_repeated_phrase(), _is_mostly_filler(), True if a body paragraph opens with a back-reference to a sentence that isn't…, True if an n-gram is mostly stopwords/connective filler ('in order to be able…, Return the first phrase of `min_words` or more that appears more than once in… (+16 more)

### Community 45 - "_load_base_urls"
Cohesion: 0.50
Nodes (4): _load_base_urls(), Load site base URLs from config/sites.yaml., Resolve a stored URL to an absolute URL., resolve_url()

### Community 46 - "Fact"
Cohesion: 0.13
Nodes (13): Fact, format_facts_block(), One verifiable, pre-written claim the LLM may select for a bullet., Render verified facts as an id-keyed list for a prompt. Shared by resume…, _build_tailor_prompt(), Build the resume tailoring system prompt from the user's profile. All skills…, A fact is one real thing; it belongs on the CV once -- even if that means a…, The duplicate bullet goes; the entry survives on its other one. (+5 more)

### Community 47 - "drop_unverifiable_quotes"
Cohesion: 0.21
Nodes (8): drop_unverifiable_quotes(), _quote_key(), Normalised form for checking a model-supplied quote against the CV. Case and…, Remove any model-quoted bullet that does not actually occur in the CV. The…, The guard that keeps a finding from resting on a quote the CV does not contain.…, The model quotes bullets as rendered; resolved bullets have no dash. Stripping…, Documented consequence of the rule as specified: containment is checked against…, TestDropUnverifiableQuotes

### Community 48 - "manifest.json"
Cohesion: 0.18
Nodes (10): contract, corpus_A_size, corpus_B_size, critic_commit, dropped_stale_on_rescore, generator_commit, model, tailor_settings (+2 more)

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
Cohesion: 0.07
Nodes (44): get_locale_style(), load_profile(), Infer document terminology and layout conventions from the candidate's country.…, Load user profile from ~/.applypilot/profile.json., FactBank, Path, Parses facts.yaml and is the sole gate on what quantified claims the tailoring…, Parse facts.yaml into Facts, validating every verified fact's numbers against… (+36 more)

### Community 58 - "analyse"
Cohesion: 0.33
Nodes (5): _is_differentiator_bullet(), True for an award/recognition/funding bullet -- see _DIFFERENTIATOR_BULLET_RE.…, analyse(), parse_cv(), Sufficiency report for corpus A, firing table for corpus B. Extractions were…

### Community 61 - "_repair_summary"
Cohesion: 0.28
Nodes (7): Rewrite `resolved_data["summary"]` in place if it fell into a rut or just…, _repair_summary(), _Client, The duplication defect fires on nearly every CV, so it repairs one field rather…, Describing the rule isn't enough -- the model has to see the sentences it is…, A rewrite is LLM-authored text like any other and gets the same numeric…, TestRepairSummary

### Community 63 - "find_summary_duplicate_bullets"
Cohesion: 0.18
Nodes (10): find_summary_duplicate_bullets(), Summary sentences that are a bullet below, retyped.…, Share of significant words the two texts have in common, taken as the weaker of…, _significant_words(), _word_coverage(), check_no_cross_section_duplicates only ever walked EXPERIENCE and PROJECTS, so…, The signal that was removed 2026-09-01 fired here, on 12 of 12 live CVs, and…, The pair that motivated _SUMMARY_DUP_MIN_COVERAGE, from the 2026-09-01 sample:… (+2 more)

### Community 65 - "NumericGuard"
Cohesion: 0.19
Nodes (8): NumericGuard, Deterministic, post-generation check: every number in the assembled resume text…, Raise NumericGuardViolation if any line contains a number that isn't in the…, _qualitative_fact(), Canonical example: an injected, unevidenced 500 must be caught., The real 4-to-9 participant fact must pass cleanly., A zero-number verified fact (mirrors kraydel.audit_system)., TestNumericGuard

### Community 67 - "test_facts.py"
Cohesion: 0.14
Nodes (10): _bank(), _DegreeAsJobClient, _embedded_fact(), _FakeClient, Tests for the FactBank / NumericGuard architectural fabrication guard. Fixtures…, Always returns the same fabricated response, regardless of the 'AVOID THESE…, A use_when-restricted fact (mirrors edu.embedded_marks)., A model that files the candidate's own degree as an EXPERIENCE entry. Measured… (+2 more)

### Community 68 - "group_near_identical"
Cohesion: 0.23
Nodes (8): description_shingles(), group_near_identical(), Set of 5-word shingle hashes over a description's first 600 words. Order-…, Map url -> a group number, for ads that read as the same posting. Only urls…, shingle_jaccard(), Advisory badge only. It must never be wired to duplicate_of: the 2026-09-02…, Below 0.8 Jaccard, 0 of 1093 sampled same-employer pairs were duplicates by the…, TestGroupNearIdentical

### Community 72 - "._bank"
Cohesion: 0.19
Nodes (7): The wording is the model's; the numbers are not. A rewording that reaches for a…, Tighter than NumericGuard's global allowed set on purpose: 11 is verified, but…, Back-compat: the original select-a-variant shape is unchanged., A fact bound to one real employer/project (Fact.source, set from its facts.yaml…, No canonical record matched this entry -- there's no ground truth to check it…, TestBulletOwnership, TestRewordedFactBullets

## Knowledge Gaps
- **39 isolated node(s):** `generator_commit`, `critic_commit`, `model`, `max_retries`, `validation_mode` (+34 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_connection()` connect `get_connection` to `tailor.py`, `end_run`, `smartextract.py`, `main`, `launcher.py`, `list_jobs`, `_StageTracker`, `workday.py`, `run_job`, `test_discovery.py`, `cli.py`, `scorer.py`, `pipeline.py`, `jobspy.py`, `FactBank`, `generate_dashboard`?**
  _High betweenness centrality (0.189) - this node is a cross-community bridge._
- **Why does `FactBank` connect `FactBank` to `tailor.py`, `get_client`, `test_facts.py`, `UnfilledFact`, `facts.py`, `._bank`, `ToolLeakGuard`, `Fact`, `test_critic.py`, `check_no_cross_section_duplicates`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `get_client()` connect `get_client` to `tailor.py`, `get_connection`, `smartextract.py`, `scrape_detail_page`, `LLMClient`, `scorer.py`, `FactBank`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `FactBank` (e.g. with `_build_cover_letter_prompt()` and `cover_letter_one()`) actually correct?**
  _`FactBank` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `tailor_resume()` (e.g. with `BulletPlacementViolation` and `FactBank`) actually correct?**
  _`tailor_resume()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `Fact` (e.g. with `_fact()` and `TestBulletOwnership`) actually correct?**
  _`Fact` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `generator_commit`, `critic_commit`, `model` to the rest of the system?**
  _39 weakly-connected nodes found - possible documentation gaps or missing edges._