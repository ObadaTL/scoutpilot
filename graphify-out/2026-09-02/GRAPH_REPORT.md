# Graph Report - ApplyPilot-main  (2026-09-02)

## Corpus Check
- 60 files · ~186,884 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1290 nodes · 2499 edges · 79 communities (74 shown, 5 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 117 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `20b167f4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- smartextract.py
- _HTMLStripper
- ._run
- detail.py
- get_connection
- evaluate_cv_observations
- chrome.py
- prompt.py
- launcher.py
- _StageTracker
- dashboard.py
- pdf.py
- LLMClient
- validator.py
- config.py
- tailor.py
- test_discovery.py
- cli.py
- TestEligibilityGate
- init_db
- ApplyPilot
- scoring/__init__.py
- applypilot
- test_critic.py
- ToolLeakGuard
- ._bank
- .match_similar
- facts.py
- check_no_cross_section_duplicates
- derive_company
- cover_letter.py
- _strip_preamble
- jobspy.py
- workday.py
- [0.2.0] - 2026-02-17
- find_header_restating_bullets
- list_jobs
- critic.py
- rules/graphify.md
- workflows/graphify.md
- test_cover_letter.py
- validate_cover_letter
- judge_tailored_resume
- Fact
- drop_unverifiable_quotes
- manifest.json
- tailor_resume
- _store_jobs_filtered
- combined_critic_score
- build_corpus.py
- Critic calibration corpus v2
- _CleanClient
- FactBank
- evaluate_letter_observations
- has_bad_signoff
- analyse
- main
- scrape_detail_page
- _repair_summary
- pipeline.py
- find_summary_duplicate_bullets
- hacker_news.py
- NumericGuard
- worker_loop
- test_facts.py
- group_near_identical
- _parse_score_response
- main
- run_job
- TestRewordedFactBullets
- _load_yaml_cached
- _resolve_fact_bullets
- dorking.py
- TestBulletOwnership
- get_locale_style
- strip_numbered_sentences

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
  tests/test_facts.py → src/applypilot/facts.py
- `TestNumericGuard` --uses--> `NumericGuardViolation`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py
- `TestCrossSectionDuplicateAssertion` --uses--> `BulletPlacementViolation`  [INFERRED]
  tests/test_facts.py → src/applypilot/facts.py
- `analyse()` --uses--> `BulletPlacementViolation`  [INFERRED]
  tools/corpus/report_corpus.py → src/applypilot/facts.py
- `_fact()` --uses--> `Fact`  [INFERRED]
  tests/test_critic.py → src/applypilot/facts.py

## Import Cycles
- None detected.

## Communities (79 total, 5 thin omitted)

### Community 0 - "smartextract.py"
Cohesion: 0.07
Nodes (43): load_search_config(), Load search configuration from ~/.applypilot/searches.yaml. Cached on the…, ask_llm(), build_scrape_targets(), clean_card_html(), clean_page_html(), collect_page_intelligence(), execute_api_response() (+35 more)

### Community 1 - "_HTMLStripper"
Cohesion: 0.25
Nodes (3): HTMLParser, _HTMLStripper, Strip HTML tags, keep text content.

### Community 2 - "._run"
Cohesion: 0.12
Nodes (10): Shipping is the LAST-attempt behaviour, not the first: while attempts remain, a…, Once canonical_entries.experience is configured, it's exhaustive: an EXPERIENCE…, The exact incident: the model filed the candidate's own degree as a job once…, The same unmatched-entry situation in PROJECTS is kept, not rejected -- a…, TECHNICAL SKILLS renders only what the profile actually declares -- the LLM's…, The exact incident: the model added 'LangChain (agent frameworks)' and…, The rejected entry is already deleted from the data by the time the error is…, TestCanonicalExperienceRejection (+2 more)

### Community 3 - "detail.py"
Cohesion: 0.14
Nodes (22): load_base_urls(), Load site base URLs for URL resolution from sites.yaml., _load_base_urls(), Connection, Detail page enrichment: scrapes full descriptions and apply URLs. For each job…, Resolve all relative URLs in the database. Returns stats., Re-fetch WTTJ Algolia API to get proper detail URLs and fix slug-as-title.…, Process all jobs for one site using shared browser context. If conn is None,… (+14 more)

### Community 4 - "get_connection"
Cohesion: 0.06
Nodes (49): Clear one job's apply status back to pending, e.g. after a wrong manual mark or…, reset_job(), apply_duplicate_marks(), clean_non_tech_jobs(), description_shingles(), ensure_columns(), find_duplicate_groups(), get_connection() (+41 more)

### Community 5 - "evaluate_cv_observations"
Cohesion: 0.11
Nodes (13): evaluate_cv_observations(), Apply fixed, code-side thresholds to the model's raw extraction. Never trusts…, On three bullets a single NONE is already a third: the fraction carries no…, The exact incident: Revolut round 2 (2026-08-26) was flagged 6/11 while a human…, The counterpart the exemption must not swallow: round 1's Java Software…, The exact incident: 'VIOFEEL has 1 bullet, below the minimum of 2' landed on 6…, The floor drops only where the material genuinely runs out. Kraydel has nine…, The model quotes the header back out of the rendered CV; only case and spacing… (+5 more)

### Community 6 - "chrome.py"
Cohesion: 0.14
Nodes (21): Popen, cleanup_on_exit(), cleanup_worker(), kill_all_chrome(), _kill_on_port(), _kill_process_tree(), launch_chrome(), Path (+13 more)

### Community 7 - "prompt.py"
Cohesion: 0.15
Nodes (19): _build_captcha_section(), _build_hard_rules(), _build_location_check(), _build_profile_summary(), build_prompt(), _build_salary_section(), _build_screening_section(), Prompt builder for the autonomous job application agent. Constructs the full… (+11 more)

### Community 8 - "launcher.py"
Cohesion: 0.18
Nodes (13): Apply pipeline: Chrome management, prompt building, orchestration, and…, acquire_job(), _load_blocked(), Apply orchestration: acquire jobs, spawn Claude Code sessions, track results.…, Atomically acquire the next job to apply to and open an attempt for it. Args:…, is_manual_ats(), load_blocked_sites(), load_sites_config() (+5 more)

### Community 9 - "_StageTracker"
Cohesion: 0.18
Nodes (7): Event, Thread-safe tracker for which stages have finished producing work., Run a single stage in streaming mode: loop until upstream done + no work. For…, Execute stages concurrently with DB as conveyor belt., _run_stage_streaming(), _run_streaming(), _StageTracker

### Community 10 - "dashboard.py"
Cohesion: 0.16
Nodes (14): Group, get_state(), get_totals(), init_worker(), Rich live dashboard for the apply pipeline. Displays real-time worker status,…, Build the Rich table showing all worker statuses. Returns: A Rich Table object…, Render the dashboard table plus the recent events panel. Returns: A Rich Group…, Compute aggregate totals across all workers. Returns: Dict with keys: applied,… (+6 more)

### Community 11 - "pdf.py"
Cohesion: 0.09
Nodes (30): Stage: PDF conversion — convert tailored resumes and cover letters to PDF., _run_pdf(), batch_convert(), build_cover_letter_html(), build_html(), convert_to_pdf(), _cover_letter_font_faces(), _cv_font_faces() (+22 more)

### Community 12 - "LLMClient"
Cohesion: 0.13
Nodes (11): Response, _GeminiCompatForbidden, LLMClient, Exception, Thin LLM client supporting OpenAI-compatible and native Gemini endpoints. For…, Call the native Gemini generateContent API. Used automatically when the OpenAI-…, Call the OpenAI-compatible endpoint. json_schema, when given, is passed as…, Call Ollama's native /api/chat, optionally with a JSON-schema `format`.… (+3 more)

### Community 13 - "validator.py"
Cohesion: 0.15
Nodes (15): _company_tokens(), find_fabricated_numbers(), has_dangling_reference(), has_lifted_jd_span(), has_repeated_phrase(), _is_mostly_filler(), Resume and cover letter validation: banned words, fabrication detection,…, Find number-bearing claims in tailored text with no basis in the original.… (+7 more)

### Community 14 - "config.py"
Cohesion: 0.10
Nodes (27): doctor(), Check your setup and diagnose missing requirements., ensure_dirs(), get_chrome_path(), get_profile_keywords(), get_tier(), load_env(), ApplyPilot configuration: paths, platform detection, user data. (+19 more)

### Community 15 - "tailor.py"
Cohesion: 0.08
Nodes (40): Split arbitrary CV/resume text into sections keyed by ALL-CAPS headers. Unlike…, split_sections(), _apply_canonical_entries(), assemble_resume_text(), _base_summary(), _build_guard_scan_text(), _bullet_text(), _bullets_similar() (+32 more)

### Community 16 - "test_discovery.py"
Cohesion: 0.15
Nodes (21): fetch_ashby_jobs(), fetch_greenhouse_jobs(), fetch_lever_jobs(), _http_get_json(), infer_opportunity_type(), is_relevant_tech_role(), Direct ATS API harvester: scrapes Greenhouse, Ashby, and Lever career portals.…, Helper to fetch and parse JSON from a public endpoint. (+13 more)

### Community 17 - "cli.py"
Cohesion: 0.10
Nodes (30): command, Reset all failed jobs so they can be retried. Returns: Number of jobs reset., reset_failed(), apply(), _bootstrap(), clean(), dashboard(), events() (+22 more)

### Community 18 - "TestEligibilityGate"
Cohesion: 0.09
Nodes (21): apply_eligibility_gate(), _candidate_is_unrestricted(), _country_in_text(), _normalize_country(), Deterministic removal of any REASONING sentence that credits the candidate with…, First country named anywhere in a free-text requirement, normalised.…, Whether the candidate needs nothing from an employer to be hired in their own…, Deterministic hard-eligibility check, run after the LLM's own score and before… (+13 more)

### Community 19 - "init_db"
Cohesion: 0.11
Nodes (26): discover(), Run specific or all discovery harvesters to find jobs, graduate schemes, and…, close_connection(), init_db(), Path, Close the cached connection for the current thread., Create the full jobs table with all columns from every pipeline stage. This is…, Store discovered jobs, skipping duplicates by URL. Args: conn: Database… (+18 more)

### Community 20 - "ApplyPilot"
Cohesion: 0.05
Nodes (39): Adding New Career Sites, Adding New Workday Employers, Bug Fixes and Features, Clone and Install, Code Style Guidelines, Contributing to ApplyPilot, Development Setup, How to Contribute (+31 more)

### Community 23 - "test_critic.py"
Cohesion: 0.17
Nodes (10): build_bullet_floor_map(), Per-entry minimum bullet counts for the critic, derived from how much real…, _fact(), Tests for the critic pass's CODE-side threshold logic (critic.py). These test…, Stands in for FactBank: the floor map only ever asks it which verified facts…, build_bullet_floor_map lives in tailor.py but exists only to feed…, The critic counts bullets under PROJECTS as well, so a floor is needed there or…, No verified material behind an entry means nothing to ask for -- the guard must… (+2 more)

### Community 26 - "ToolLeakGuard"
Cohesion: 0.16
Nodes (11): Exception, Raised by ToolLeakGuard when a job-description tool the candidate doesn't have…, Deterministic check: a tool/tech token in the job description but absent from…, Every job-description tool the candidate doesn't have that appears as a whole…, Raise ToolLeakViolation if a job-description tool the candidate doesn't have…, ToolLeakGuard, ToolLeakViolation, _profile() (+3 more)

### Community 27 - "._bank"
Cohesion: 0.23
Nodes (7): _kraydel_multiparty_fact(), Bullets that carry no fact id must contain no digits -- enforced in code, not…, Mirrors the real kraydel.multiparty_calls entry in facts.yaml., A plausible-but-unevidenced fact that must never reach the LLM., The core guarantee: relevant_facts() (what actually goes into the LLM prompt)…, TestFactBankRejectsUnverified, _unverified_fact()

### Community 28 - ".match_similar"
Cohesion: 0.22
Nodes (6): _accept_reworded(), Best-effort recovery for a plain-string bullet that has a digit but is actually…, Turn one LLM-output bullet into literal text. See resolve_bullet_ex for the…, Turn one LLM-output bullet into (literal text, fact id or None). A fact-…, Whether the model's own wording of `fact` may be used in place of the fact's…, _significant_words()

### Community 29 - "facts.py"
Cohesion: 0.12
Nodes (15): BulletPlacementViolation, _extract_numbers(), FactBankError, FactBankLoadError, NumericGuardViolation, Exception, Verified-fact bank for resume tailoring. facts.yaml (repo root) is the ONLY…, Base class for fact-bank problems. (+7 more)

### Community 30 - "check_no_cross_section_duplicates"
Cohesion: 0.15
Nodes (11): check_no_cross_section_duplicates(), _normalize_bullet_for_dup_check(), Hard assertion: the same claim may not appear twice anywhere in the assembled…, check_no_cross_section_duplicates is the hard backstop: even if ownership/dedup…, Exact-text matching alone missed this live 2026-08-26: the same fact, worded…, The blind spot the projects-vs-experience loop had by construction: two bullets…, The exact pairing named in _likely_fact_id's docstring: 'Built dual ML…, Same section, two different headings -- also invisible to the old loop, which… (+3 more)

### Community 31 - "derive_company"
Cohesion: 0.06
Nodes (19): Row, derive_company(), Best available employer name for a job, for grouping in the dashboard. Derived…, fixture, Dashboard behaviour: CV/cover-letter independence, and the two things that made…, searches.yaml is hand-edited, so the cache is keyed on the file's own…, applyFilters() matches the search term against `card.textContent`. On…, A cover-letter failure used to set the job's single status field to "error".… (+11 more)

### Community 32 - "cover_letter.py"
Cohesion: 0.08
Nodes (42): load_location_focus(), load_profile(), Load the optional `location_focus` section from searches.yaml. A temporary,…, Load user profile from ~/.applypilot/profile.json., classify_location(), Human-readable place label for a job's location, for the dashboard's place…, is_local_provider(), Unified LLM client for ApplyPilot. Auto-detects provider from environment:… (+34 more)

### Community 33 - "_strip_preamble"
Cohesion: 0.21
Nodes (7): Remove LLM preamble before 'Dear Hiring Manager,' if present. Gemini and other…, Truncate anything after the sign-off line. Models occasionally add notes/P.S.…, _strip_after_signoff(), _strip_preamble(), An incidental earlier mention of the name must not truncate the real body that…, endeared'/'dearest' mid-preamble must not be mistaken for the letter's real…, TestStripHelpers

### Community 34 - "jobspy.py"
Cohesion: 0.12
Nodes (21): _full_crawl(), _load_location_config(), _location_ok(), parse_proxy(), Connection, JobSpy-based job discovery: searches Indeed, LinkedIn, Glassdoor, ZipRecruiter.…, Store JobSpy DataFrame results into the DB. Returns (new, existing)., Run a single search query and store results in DB. (+13 more)

### Community 35 - "workday.py"
Cohesion: 0.09
Nodes (32): fetch_details(), _fetch_one_detail(), load_employers(), _load_location_filter(), _location_ok(), _process_one(), Connection, Workday ATS direct API scraper: searches employer career portals. Scrapes… (+24 more)

### Community 36 - "[0.2.0] - 2026-02-17"
Cohesion: 0.25
Nodes (7): [0.1.0] - 2026-02-17, [0.2.0] - 2026-02-17, Added, Added, Changed, Changelog, Fixed

### Community 37 - "find_header_restating_bullets"
Cohesion: 0.18
Nodes (9): _entry_span_months(), find_header_restating_bullets(), Length in months of the first date range in `text`, or None. An open-ended…, Bullets that only say again what their own entry header already says. This…, The code check that replaced the model clause., The exact bullet the model never flagged: '11-month industry placement ...'…, 1st place, QUB Dragon's Den 2024' under 'Apr 2024 - Mar 2026' shares a year and…, Aug 2026 - Present' has no fixed span, so a duration claim against it can't be… (+1 more)

### Community 38 - "list_jobs"
Cohesion: 0.14
Nodes (11): Console, list_jobs(), Fetch scored jobs for terminal display, filtered and sorted by fit. Args:…, Render one Rich panel per job with fit score, company context, tailored…, render_jobs(), fixture, Tests for terminal_view.list_jobs / render_jobs (the `applypilot jobs` command)., Isolated scratch DB with a few jobs at different fit scores/sites, never… (+3 more)

### Community 39 - "critic.py"
Cohesion: 0.26
Nodes (11): _build_cv_critic_user_message(), _build_letter_critic_user_message(), CriticResult, _normalize_header(), Extraction-only "critic" pass over a tailored CV and cover letter. Catches…, Loose key for matching a header the model quoted back out of the CV against the…, score is COMPUTED from discrete findings (10.0 minus each finding's weight,…, run_cv_critic() (+3 more)

### Community 43 - "test_cover_letter.py"
Cohesion: 0.20
Nodes (10): _bank(), _FabricatingClient, isolated_env(), _multiparty_fact(), fixture, Tests for the six cover-letter-generation defect fixes. Fast unit tests…, Always fabricates the same unverified number, regardless of retry feedback --…, Retries must keep sampling temperature, not drop it. The old behaviour was 0.7… (+2 more)

### Community 44 - "validate_cover_letter"
Cohesion: 0.19
Nodes (10): Programmatic validation of a cover letter. Args: text: The cover letter text to…, validate_cover_letter(), ...with % accuracy" -- the digit-blanking fallback's signature., A first body paragraph opening on a referent that was deleted., Only the FIRST body paragraph can dangle -- a later "That ..." points at the…, lenient tolerates style sins, not a letter with holes in it -- and lenient is…, The same 5+ word claim showing up twice reads as padding, not two different…, Reciting the posting's own marketing copy back at it isn't personalization. (+2 more)

### Community 45 - "judge_tailored_resume"
Cohesion: 0.50
Nodes (4): _build_judge_prompt(), judge_tailored_resume(), LLM judge layer: catches subtle fabrication that programmatic checks miss.…, Build the LLM judge prompt from the user's profile. The judge only ever sees…

### Community 46 - "Fact"
Cohesion: 0.18
Nodes (9): Fact, format_facts_block(), One verifiable, pre-written claim the LLM may select for a bullet., All tier == 'verified' facts. The ONLY facts ever exposed to the LLM., Verified facts worth offering the LLM for this job. Facts with no `use_when`…, Render verified facts as an id-keyed list for a prompt. Shared by resume…, Once on the id line isn't enough: the variant text is what the model reads when…, A letter has no entries, so ownership is meaningless there. (+1 more)

### Community 47 - "drop_unverifiable_quotes"
Cohesion: 0.21
Nodes (8): drop_unverifiable_quotes(), _quote_key(), Normalised form for checking a model-supplied quote against the CV. Case and…, Remove any model-quoted bullet that does not actually occur in the CV. The…, The guard that keeps a finding from resting on a quote the CV does not contain.…, The model quotes bullets as rendered; resolved bullets have no dash. Stripping…, Documented consequence of the rule as specified: containment is checked against…, TestDropUnverifiableQuotes

### Community 48 - "manifest.json"
Cohesion: 0.18
Nodes (10): contract, corpus_A_size, corpus_B_size, critic_commit, dropped_stale_on_rescore, generator_commit, model, tailor_settings (+2 more)

### Community 49 - "tailor_resume"
Cohesion: 0.11
Nodes (20): check_listing_still_open(), Best-effort check for whether a job listing is still accepting applications,…, _facts_available_for_entry(), find_min_bullet_violations(), The verified facts this CV entry is the real-world owner of. A Fact's `source`…, For each canonical EXPERIENCE entry with at least `min_bullets` relevant…, Generate a tailored resume via JSON output + fresh context on each retry. Key…, Last-resort removal for a leaked tool ToolLeakGuard still finds on the final… (+12 more)

### Community 50 - "_store_jobs_filtered"
Cohesion: 0.40
Nodes (5): _location_ok(), Connection, Check if a job location passes the user's location filter., Store jobs with location filtering. Returns (new, existing)., _store_jobs_filtered()

### Community 51 - "combined_critic_score"
Cohesion: 0.39
Nodes (3): combined_critic_score(), The single critic_score value stored on the job row: the average of whichever…, TestCombinedCriticScore

### Community 52 - "build_corpus.py"
Cohesion: 0.36
Nodes (6): build(), enrich(), extract(), load(), log(), Build corpus v2 -- two corpora, separate files, never pooled. A. Calibration…

### Community 53 - "Critic calibration corpus v2"
Cohesion: 0.29
Nodes (6): Critic calibration corpus v2, Known limitation — read before calibrating anything against this, Reproducing, Supporting files, The contract, Two corpora, never pooled

### Community 54 - "_CleanClient"
Cohesion: 0.40
Nodes (3): _CleanClient, A well-behaved local model: no fabricated numbers, no leaked tools, names the…, TestRunCoverLettersIntegration

### Community 55 - "FactBank"
Cohesion: 0.10
Nodes (19): FactBank, Path, A known gap: a plausible claim that needs a real value filled in before it can…, Parses facts.yaml and is the sole gate on what quantified claims the tailoring…, Parse facts.yaml into Facts, validating every verified fact's numbers against…, Unverified entries pending a real value, for a CLI prompt flow., UnfilledFact, _build_cover_letter_prompt() (+11 more)

### Community 57 - "has_bad_signoff"
Cohesion: 0.40
Nodes (3): has_bad_signoff(), Return a description of what's wrong with the sign-off, or None. The prompt…, The prompt asks for 'Sincerely,' then the name and nothing else -- a trailing…

### Community 58 - "analyse"
Cohesion: 0.33
Nodes (5): _is_differentiator_bullet(), True for an award/recognition/funding bullet -- see _DIFFERENTIATOR_BULLET_RE.…, analyse(), parse_cv(), Sufficiency report for corpus A, firing table for corpus B. Extractions were…

### Community 59 - "main"
Cohesion: 0.67
Nodes (3): callback, main(), ApplyPilot — AI-powered end-to-end job application pipeline.

### Community 60 - "scrape_detail_page"
Cohesion: 0.12
Nodes (18): clean_content_html(), clean_description(), collect_detail_intelligence(), extract_apply_url_deterministic(), extract_description_deterministic(), extract_from_json_ld(), extract_main_content(), extract_with_llm() (+10 more)

### Community 61 - "_repair_summary"
Cohesion: 0.28
Nodes (7): Rewrite `resolved_data["summary"]` in place if it fell into a rut or just…, _repair_summary(), _Client, The duplication defect fires on nearly every CV, so it repairs one field rather…, Describing the rule isn't enough -- the model has to see the sentences it is…, A rewrite is LLM-authored text like any other and gets the same numeric…, TestRepairSummary

### Community 62 - "pipeline.py"
Cohesion: 0.14
Nodes (15): _count_pending(), ApplyPilot Pipeline Orchestrator. Runs pipeline stages in sequence or…, Stage: Detail enrichment — scrape full descriptions and apply URLs., Stage: Resume tailoring — generate tailored resumes for high-fit jobs., Stage: Cover letter generation., Resolve 'all' and validate/order stage names., Count pending work items for a stage., Execute stages one at a time (original behavior). (+7 more)

### Community 63 - "find_summary_duplicate_bullets"
Cohesion: 0.18
Nodes (10): find_summary_duplicate_bullets(), Summary sentences that are a bullet below, retyped.…, Share of significant words the two texts have in common, taken as the weaker of…, _significant_words(), _word_coverage(), check_no_cross_section_duplicates only ever walked EXPERIENCE and PROJECTS, so…, The signal that was removed 2026-09-01 fired here, on 12 of 12 live CVs, and…, The pair that motivated _SUMMARY_DUP_MIN_COVERAGE, from the 2026-09-01 sample:… (+2 more)

### Community 64 - "hacker_news.py"
Cohesion: 0.20
Nodes (14): _clean_hn_html(), fetch_comment_item(), find_latest_who_is_hiring_story(), _get_json(), parse_hn_comment(), Hacker News 'Who is Hiring?' Harvester. Fetches the latest monthly 'Ask HN: Who…, Discover jobs from the latest Hacker News 'Who is Hiring?' thread. Args:…, Clean HTML from HN comments to readable text. (+6 more)

### Community 65 - "NumericGuard"
Cohesion: 0.19
Nodes (8): NumericGuard, Deterministic, post-generation check: every number in the assembled resume text…, Raise NumericGuardViolation if any line contains a number that isn't in the…, _qualitative_fact(), Canonical example: an injected, unevidenced 500 must be caught., The real 4-to-9 participant fact must pass cleanly., A zero-number verified fact (mirrors kraydel.audit_system)., TestNumericGuard

### Community 66 - "worker_loop"
Cohesion: 0.15
Nodes (14): add_event(), Update the worker's state fields. Args: worker_id: Which worker to update.…, Add a timestamped event to the scrolling event log. Args: msg: Rich markup…, update_state(), _is_permanent_failure(), mark_result(), Record an attempt's outcome and mirror it onto the job., Release the in_progress lock without recording a terminal outcome. Used when a… (+6 more)

### Community 67 - "test_facts.py"
Cohesion: 0.15
Nodes (10): _bank(), _DegreeAsJobClient, _embedded_fact(), _FakeClient, Tests for the FactBank / NumericGuard architectural fabrication guard. Fixtures…, Always returns the same fabricated response, regardless of the 'AVOID THESE…, A use_when-restricted fact (mirrors edu.embedded_marks)., A model that files the candidate's own degree as an EXPERIENCE entry. Measured… (+2 more)

### Community 68 - "group_near_identical"
Cohesion: 0.28
Nodes (6): group_near_identical(), Map url -> a group number, for ads that read as the same posting. Only urls…, shingle_jaccard(), Advisory badge only. It must never be wired to duplicate_of: the 2026-09-02…, Below 0.8 Jaccard, 0 of 1093 sampled same-employer pairs were duplicates by the…, TestGroupNearIdentical

### Community 69 - "_parse_score_response"
Cohesion: 0.22
Nodes (7): _clean_optional_field(), _parse_score_response(), Strip a captured field and map a literal 'NULL' response to None. The scoring…, Parse the LLM's score response into structured data. Args: response: Raw LLM…, REASONING used to be a greedy capture-to-end-of-string -- once…, Older-style responses (or a model that ignores the new fields) must not crash…, TestParseScoreResponse

### Community 70 - "main"
Cohesion: 0.22
Nodes (11): gen_prompt(), main(), mark_job(), Path, Generate a prompt file and print the Claude CLI command for manual debugging.…, Manually mark a job's apply status in the database. Records this as a completed…, Launch the apply pipeline. Args: limit: Max jobs to apply to (0 or with…, end_run() (+3 more)

### Community 71 - "run_job"
Cohesion: 0.20
Nodes (10): _check_playwright_mcp(), _make_mcp_config(), Inspect a system/init stream-json event for playwright MCP health. Browser…, Spawn a Claude Code session for one job application. Returns: Tuple of…, Build MCP config dict for a specific CDP port., run_job(), attach_tool_result(), Record the total cost for an attempt (from the final result event). (+2 more)

### Community 72 - "TestRewordedFactBullets"
Cohesion: 0.20
Nodes (4): The wording is the model's; the numbers are not. A rewording that reaches for a…, Tighter than NumericGuard's global allowed set on purpose: 11 is verified, but…, Back-compat: the original select-a-variant shape is unchanged., TestRewordedFactBullets

### Community 73 - "_load_yaml_cached"
Cohesion: 0.22
Nodes (9): get_chrome_user_data(), load_ats_employers(), load_schemes_config(), _load_yaml_cached(), Path, Parse `path` as YAML, reusing the previous parse while it is unchanged. Returns…, Load Direct ATS employers from config/ats_employers.yaml., Load Graduate Schemes & Funded Training config from config/schemes.yaml. (+1 more)

### Community 74 - "_resolve_fact_bullets"
Cohesion: 0.28
Nodes (6): Resolve every experience/project bullet into literal text. A fact-id bullet is…, _resolve_fact_bullets(), A fact is one real thing; it belongs on the CV once -- even if that means a…, The duplicate bullet goes; the entry survives on its other one., If dedup would leave PROJECTS with no entries at all, it stays empty --…, TestCrossSectionDedup

### Community 75 - "dorking.py"
Cohesion: 0.33
Nodes (6): _clean_ddg_url(), Search Operator ('Google Dorking') & Direct ATS Discovery Agent. Executes…, Extract destination URL from DuckDuckGo redirect link., Execute search query against DuckDuckGo HTML interface., search_duckduckgo(), test_clean_ddg_url()

### Community 76 - "TestBulletOwnership"
Cohesion: 0.40
Nodes (3): A fact bound to one real employer/project (Fact.source, set from its facts.yaml…, No canonical record matched this entry -- there's no ground truth to check it…, TestBulletOwnership

### Community 77 - "get_locale_style"
Cohesion: 0.50
Nodes (4): get_locale_style(), Infer document terminology and layout conventions from the candidate's country.…, _build_tailor_prompt(), Build the resume tailoring system prompt from the user's profile. All skills…

### Community 78 - "strip_numbered_sentences"
Cohesion: 0.50
Nodes (3): Deterministic, code-only last resort for a guard failure that survived every…, strip_numbered_sentences(), The fallback drops the paragraph rather than leaving its units stranded. Less…

## Knowledge Gaps
- **51 isolated node(s):** `generator_commit`, `critic_commit`, `model`, `max_retries`, `validation_mode` (+46 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_connection()` connect `get_connection` to `hacker_news.py`, `smartextract.py`, `worker_loop`, `jobspy.py`, `workday.py`, `detail.py`, `main`, `run_job`, `launcher.py`, `cover_letter.py`, `list_jobs`, `dorking.py`, `tailor.py`, `test_discovery.py`, `cli.py`, `init_db`, `pipeline.py`?**
  _High betweenness centrality (0.185) - this node is a cross-community bridge._
- **Why does `FactBank` connect `FactBank` to `cover_letter.py`, `test_facts.py`, `TestRewordedFactBullets`, `_resolve_fact_bullets`, `test_cover_letter.py`, `TestBulletOwnership`, `judge_tailored_resume`, `Fact`, `tailor.py`, `get_locale_style`, `tailor_resume`, `test_critic.py`, `._bank`, `.match_similar`, `facts.py`, `check_no_cross_section_duplicates`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `get_client()` connect `smartextract.py` to `cover_letter.py`, `detail.py`, `get_connection`, `LLMClient`, `judge_tailored_resume`, `tailor.py`, `tailor_resume`, `FactBank`, `scrape_detail_page`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `FactBank` (e.g. with `_build_cover_letter_prompt()` and `cover_letter_one()`) actually correct?**
  _`FactBank` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `tailor_resume()` (e.g. with `BulletPlacementViolation` and `FactBank`) actually correct?**
  _`tailor_resume()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `Fact` (e.g. with `_fact()` and `TestBulletOwnership`) actually correct?**
  _`Fact` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `generator_commit`, `critic_commit`, `model` to the rest of the system?**
  _51 weakly-connected nodes found - possible documentation gaps or missing edges._