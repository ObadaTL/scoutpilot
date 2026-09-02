# Graph Report - ApplyPilot-main  (2026-09-02)

## Corpus Check
- 62 files · ~190,410 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1325 nodes · 2620 edges · 74 communities (68 shown, 6 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 117 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `71364e97`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- sanitize_text
- test_prefilter.py
- ._run
- get_connection
- smartextract.py
- evaluate_cv_observations
- chrome.py
- config.py
- .verified
- _StageTracker
- validator.py
- init_db
- LLMClient
- workday.py
- pdf.py
- launcher.py
- test_discovery.py
- cli.py
- TestEligibilityGate
- test_cover_letter.py
- Contributing to ScoutPilot
- jobspy.py
- prompt.py
- test_critic.py
- run_wizard
- tailor_resume
- load_search_config
- ._bank
- critic.py
- generate_dashboard
- check_no_cross_section_duplicates
- derive_company
- scorer.py
- _parse_score_response
- run_pipeline
- view.py
- [0.2.0] - 2026-02-17
- find_header_restating_bullets
- list_jobs
- UnfilledFact
- rules/graphify.md
- workflows/graphify.md
- ToolLeakGuard
- validate_cover_letter
- _strip_preamble
- Fact
- drop_unverifiable_quotes
- manifest.json
- _tailor_one_job
- scoring/__init__.py
- combined_critic_score
- build_corpus.py
- Critic calibration corpus v2
- scoutpilot
- FactBank
- evaluate_letter_observations
- analyse
- NumericGuardViolation
- _repair_summary
- format_facts_block
- tailor.py
- _CleanClient
- NumericGuard
- _store_jobs_filtered
- test_facts.py
- group_near_identical
- has_bad_signoff
- judge_tailored_resume
- find_min_bullet_violations
- TestRewordedFactBullets
- main

## God Nodes (most connected - your core abstractions)
1. `get_connection()` - 59 edges
2. `FactBank` - 49 edges
3. `init_db()` - 33 edges
4. `tailor_resume()` - 32 edges
5. `Fact` - 28 edges
6. `evaluate_prefilter()` - 24 edges
7. `evaluate_cv_observations()` - 22 edges
8. `store_jobs()` - 20 edges
9. `generate_cover_letter()` - 20 edges
10. `TestEligibilityGate` - 20 edges

## Surprising Connections (you probably didn't know these)
- `TestNumericGuard` --uses--> `NumericGuardViolation`  [INFERRED]
  tests/test_facts.py → src/scoutpilot/facts.py
- `TestCrossSectionDuplicateAssertion` --uses--> `BulletPlacementViolation`  [INFERRED]
  tests/test_facts.py → src/scoutpilot/facts.py
- `analyse()` --uses--> `BulletPlacementViolation`  [INFERRED]
  tools/corpus/report_corpus.py → src/scoutpilot/facts.py
- `_fact()` --uses--> `Fact`  [INFERRED]
  tests/test_critic.py → src/scoutpilot/facts.py
- `TestBulletOwnership` --uses--> `Fact`  [INFERRED]
  tests/test_facts.py → src/scoutpilot/facts.py

## Import Cycles
- None detected.

## Communities (74 total, 6 thin omitted)

### Community 0 - "sanitize_text"
Cohesion: 0.12
Nodes (20): Split arbitrary CV/resume text into sections keyed by ALL-CAPS headers. Unlike…, split_sections(), assemble_resume_text(), _base_summary(), _canonical_education_line(), _canonical_skills_lines(), extract_extra_sections(), _fallback_unquantified() (+12 more)

### Community 1 - "test_prefilter.py"
Cohesion: 0.10
Nodes (39): parametrize, close_connection(), _is_relevant_remote(), Path, Close the cached connection for the current thread., True if a (lowercased) location's "remote" claim is UK/NI-relevant or…, _check_experience(), _check_location() (+31 more)

### Community 2 - "._run"
Cohesion: 0.10
Nodes (12): _DegreeAsJobClient, Shipping is the LAST-attempt behaviour, not the first: while attempts remain, a…, Once canonical_entries.experience is configured, it's exhaustive: an EXPERIENCE…, The exact incident: the model filed the candidate's own degree as a job once…, The same unmatched-entry situation in PROJECTS is kept, not rejected -- a…, TECHNICAL SKILLS renders only what the profile actually declares -- the LLM's…, The exact incident: the model added 'LangChain (agent frameworks)' and…, A model that files the candidate's own degree as an EXPERIENCE entry. Measured… (+4 more)

### Community 3 - "get_connection"
Cohesion: 0.06
Nodes (63): mark_job(), Manually mark a job's apply status in the database. Records this as a completed…, Clear one job's apply status back to pending, e.g. after a wrong manual mark or…, reset_job(), Show pipeline statistics from the database., status(), load_location_focus(), Load the optional `location_focus` section from searches.yaml. A temporary,… (+55 more)

### Community 4 - "smartextract.py"
Cohesion: 0.11
Nodes (29): ask_llm(), clean_card_html(), clean_page_html(), collect_page_intelligence(), execute_api_response(), execute_css_selectors(), execute_json_ld(), extract_json() (+21 more)

### Community 5 - "evaluate_cv_observations"
Cohesion: 0.11
Nodes (13): evaluate_cv_observations(), Apply fixed, code-side thresholds to the model's raw extraction. Never trusts…, On three bullets a single NONE is already a third: the fraction carries no…, The exact incident: Revolut round 2 (2026-08-26) was flagged 6/11 while a human…, The counterpart the exemption must not swallow: round 1's Java Software…, The exact incident: 'VIOFEEL has 1 bullet, below the minimum of 2' landed on 6…, The floor drops only where the material genuinely runs out. Kraydel has nine…, The model quotes the header back out of the rendered CV; only case and spacing… (+5 more)

### Community 6 - "chrome.py"
Cohesion: 0.16
Nodes (17): Popen, cleanup_on_exit(), cleanup_worker(), kill_all_chrome(), _kill_on_port(), _kill_process_tree(), Path, Chrome lifecycle management for apply workers. Handles launching an isolated… (+9 more)

### Community 7 - "config.py"
Cohesion: 0.13
Nodes (20): _deep_merge(), get_chrome_user_data(), get_profile_keywords(), load_ats_employers(), load_base_urls(), load_prefilter_config(), load_schemes_config(), load_sites_config() (+12 more)

### Community 8 - ".verified"
Cohesion: 0.13
Nodes (10): _accept_reworded(), _extract_numbers(), Recursively pull every integer token out of a nested structure. Used to fold…, Best-effort recovery for a plain-string bullet that has a digit but is actually…, All tier == 'verified' facts. The ONLY facts ever exposed to the LLM., Every number the tailoring output is allowed to contain: the union of every…, Turn one LLM-output bullet into literal text. See resolve_bullet_ex for the…, Turn one LLM-output bullet into (literal text, fact id or None). A fact-… (+2 more)

### Community 10 - "validator.py"
Cohesion: 0.15
Nodes (15): _company_tokens(), find_fabricated_numbers(), has_dangling_reference(), has_lifted_jd_span(), has_repeated_phrase(), _is_mostly_filler(), Resume and cover letter validation: banned words, fabrication detection,…, Find number-bearing claims in tailored text with no basis in the original.… (+7 more)

### Community 11 - "init_db"
Cohesion: 0.08
Nodes (40): init_db(), Create the full jobs table with all columns from every pipeline stage. This is…, clean_content_html(), clean_description(), collect_detail_intelligence(), extract_apply_url_deterministic(), extract_description_deterministic(), extract_from_json_ld() (+32 more)

### Community 12 - "LLMClient"
Cohesion: 0.13
Nodes (11): Response, _GeminiCompatForbidden, LLMClient, Exception, Thin LLM client supporting OpenAI-compatible and native Gemini endpoints. For…, Call the native Gemini generateContent API. Used automatically when the OpenAI-…, Call the OpenAI-compatible endpoint. json_schema, when given, is passed as…, Call Ollama's native /api/chat, optionally with a JSON-schema `format`.… (+3 more)

### Community 13 - "workday.py"
Cohesion: 0.07
Nodes (33): HTMLParser, fetch_details(), _fetch_one_detail(), _HTMLStripper, load_employers(), _load_location_filter(), _location_ok(), _process_one() (+25 more)

### Community 14 - "pdf.py"
Cohesion: 0.08
Nodes (34): get_locale_style(), Infer document terminology and layout conventions from the candidate's country.…, Stage: PDF conversion — convert tailored resumes and cover letters to PDF., _run_pdf(), _preflight_pdf_converter(), Smoke-test the PDF pipeline once per batch, before any LLM calls. Exercises the…, batch_convert(), build_cover_letter_html() (+26 more)

### Community 15 - "launcher.py"
Cohesion: 0.05
Nodes (57): launch_chrome(), Launch a Chrome instance with remote debugging for a worker. Args: worker_id:…, Wipe and recreate a worker's isolated working directory. Each job gets a fresh…, reset_worker_dir(), add_event(), get_state(), get_totals(), init_worker() (+49 more)

### Community 16 - "test_discovery.py"
Cohesion: 0.06
Nodes (61): Store discovered jobs, skipping duplicates by URL. Args: conn: Database…, store_jobs(), fetch_ashby_jobs(), fetch_greenhouse_jobs(), fetch_lever_jobs(), _http_get_json(), infer_opportunity_type(), is_relevant_tech_role() (+53 more)

### Community 17 - "cli.py"
Cohesion: 0.08
Nodes (41): command, Reset all failed jobs so they can be retried. Returns: Number of jobs reset., reset_failed(), apply(), _bootstrap(), clean(), dashboard(), discover() (+33 more)

### Community 18 - "TestEligibilityGate"
Cohesion: 0.09
Nodes (21): apply_eligibility_gate(), _candidate_is_unrestricted(), _country_in_text(), _normalize_country(), Deterministic removal of any REASONING sentence that credits the candidate with…, First country named anywhere in a free-text requirement, normalised.…, Whether the candidate needs nothing from an employer to be hired in their own…, Deterministic hard-eligibility check, run after the LLM's own score and before… (+13 more)

### Community 19 - "test_cover_letter.py"
Cohesion: 0.20
Nodes (10): _bank(), _FabricatingClient, isolated_env(), _multiparty_fact(), fixture, Tests for the six cover-letter-generation defect fixes. Fast unit tests…, Always fabricates the same unverified number, regardless of retry feedback --…, Retries must keep sampling temperature, not drop it. The old behaviour was 0.7… (+2 more)

### Community 20 - "Contributing to ScoutPilot"
Cohesion: 0.08
Nodes (23): Adding New Career Sites, Adding New Workday Employers, Bug Fixes and Features, Clone and Install, Code Style Guidelines, Contributing to ScoutPilot, Development Setup, How to Contribute (+15 more)

### Community 21 - "jobspy.py"
Cohesion: 0.13
Nodes (19): _full_crawl(), _load_location_config(), _location_ok(), parse_proxy(), Connection, JobSpy-based job discovery: searches Indeed, LinkedIn, Glassdoor, ZipRecruiter.…, Store JobSpy DataFrame results into the DB. Returns (new, existing)., Run a single search query and store results in DB. (+11 more)

### Community 22 - "prompt.py"
Cohesion: 0.15
Nodes (19): _build_captcha_section(), _build_hard_rules(), _build_location_check(), _build_profile_summary(), build_prompt(), _build_salary_section(), _build_screening_section(), Prompt builder for the autonomous job application agent. Constructs the full… (+11 more)

### Community 23 - "test_critic.py"
Cohesion: 0.17
Nodes (10): build_bullet_floor_map(), Per-entry minimum bullet counts for the critic, derived from how much real…, _fact(), Tests for the critic pass's CODE-side threshold logic (critic.py). These test…, Stands in for FactBank: the floor map only ever asks it which verified facts…, build_bullet_floor_map lives in tailor.py but exists only to feed…, The critic counts bullets under PROJECTS as well, so a floor is needed there or…, No verified material behind an entry means nothing to ask for -- the guard must… (+2 more)

### Community 24 - "run_wizard"
Cohesion: 0.17
Nodes (15): ensure_dirs(), Create all required directories., ScoutPilot first-time setup wizard. Interactive flow that creates…, Generate a searches.yaml from user input., Ask about AI scoring/tailoring — optional LLM configuration., Configure autonomous job application (requires Claude Code CLI)., Run the full interactive setup wizard., Prompt for resume file and copy into APP_DIR. (+7 more)

### Community 25 - "tailor_resume"
Cohesion: 0.10
Nodes (22): _build_guard_scan_text(), _build_tailor_prompt(), Text scope NumericGuard checks: LLM-authored content (title, summary, skills,…, Generate a tailored resume via JSON output + fresh context on each retry. Key…, Build, assemble, and re-verify the unquantified fallback. Called only after…, Absolute last resort: remove every digit from every LLM-authored field (title,…, Last-resort removal for a leaked tool ToolLeakGuard still finds on the final…, JSON Schema for the tailor prompt's expected output shape. Passed as… (+14 more)

### Community 26 - "load_search_config"
Cohesion: 0.27
Nodes (10): load_search_config(), Load search configuration from ~/.applypilot/searches.yaml. Cached on the…, build_scrape_targets(), _load_location_filter(), load_sites(), Main entry point for AI-powered smart extraction. Loads sites from…, Load location accept/reject lists from search config., Load scraping target sites from config/sites.yaml. (+2 more)

### Community 27 - "._bank"
Cohesion: 0.17
Nodes (10): _kraydel_multiparty_fact(), Bullets that carry no fact id must contain no digits -- enforced in code, not…, Mirrors the real kraydel.multiparty_calls entry in facts.yaml., A fact bound to one real employer/project (Fact.source, set from its facts.yaml…, No canonical record matched this entry -- there's no ground truth to check it…, A plausible-but-unevidenced fact that must never reach the LLM., The core guarantee: relevant_facts() (what actually goes into the LLM prompt)…, TestBulletOwnership (+2 more)

### Community 28 - "critic.py"
Cohesion: 0.26
Nodes (11): _build_cv_critic_user_message(), _build_letter_critic_user_message(), CriticResult, _normalize_header(), Extraction-only "critic" pass over a tailored CV and cover letter. Catches…, Loose key for matching a header the model quoted back out of the CV against the…, score is COMPUTED from discrete findings (10.0 minus each finding's weight,…, run_cv_critic() (+3 more)

### Community 29 - "generate_dashboard"
Cohesion: 0.25
Nodes (9): classify_location(), _location_priority_tier(), 0-indexed priority tier for a job's location (lower = higher priority). Checked…, Human-readable place label for a job's location, for the dashboard's place…, generate_dashboard(), open_dashboard(), Path, Generate a static dashboard snapshot and open it in the default browser -- a… (+1 more)

### Community 30 - "check_no_cross_section_duplicates"
Cohesion: 0.15
Nodes (11): check_no_cross_section_duplicates(), _normalize_bullet_for_dup_check(), Hard assertion: the same claim may not appear twice anywhere in the assembled…, check_no_cross_section_duplicates is the hard backstop: even if ownership/dedup…, Exact-text matching alone missed this live 2026-08-26: the same fact, worded…, The blind spot the projects-vs-experience loop had by construction: two bullets…, The exact pairing named in _likely_fact_id's docstring: 'Built dual ML…, Same section, two different headings -- also invisible to the old loop, which… (+3 more)

### Community 31 - "derive_company"
Cohesion: 0.06
Nodes (19): Row, derive_company(), Best available employer name for a job, for grouping in the dashboard. Derived…, fixture, Dashboard behaviour: CV/cover-letter independence, and the two things that made…, searches.yaml is hand-edited, so the cache is keyed on the file's own…, applyFilters() matches the search term against `card.textContent`. On…, A cover-letter failure used to set the job's single status field to "error".… (+11 more)

### Community 32 - "scorer.py"
Cohesion: 0.19
Nodes (11): _detect_provider(), get_client(), Unified LLM client for ScoutPilot. Auto-detects provider from environment:…, Return (base_url, model, api_key) based on environment variables. Reads env at…, Return (or create) the module-level LLMClient singleton., _build_candidate_level(), Job fit scoring: LLM-powered evaluation of candidate-job match quality. Scores…, Format the candidate's experience level for the scoring prompt. Scoring is done… (+3 more)

### Community 33 - "_parse_score_response"
Cohesion: 0.22
Nodes (7): _clean_optional_field(), _parse_score_response(), Strip a captured field and map a literal 'NULL' response to None. The scoring…, Parse the LLM's score response into structured data. Args: response: Raw LLM…, REASONING used to be a greedy capture-to-end-of-string -- once…, Older-style responses (or a model that ignores the new fields) must not crash…, TestParseScoreResponse

### Community 34 - "run_pipeline"
Cohesion: 0.12
Nodes (17): Event, Group, Build the Rich table showing all worker statuses. Returns: A Rich Table object…, Render the dashboard table plus the recent events panel. Returns: A Rich Group…, render_dashboard(), render_full(), Resolve 'all' and validate/order stage names., Run a single stage in streaming mode: loop until upstream done + no work. For… (+9 more)

### Community 35 - "view.py"
Cohesion: 0.15
Nodes (21): load_profile(), Load user profile from ~/.applypilot/profile.json., is_local_provider(), True when generation will hit a local (non-cloud) LLM_URL endpoint. Mirrors…, cover_letter_one(), Generate a cover letter for exactly one job, by URL, regardless of its current…, Tailor a resume for exactly one job, by URL, regardless of its current…, tailor_one() (+13 more)

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
Cohesion: 0.16
Nodes (11): Exception, Raised by ToolLeakGuard when a job-description tool the candidate doesn't have…, Deterministic check: a tool/tech token in the job description but absent from…, Every job-description tool the candidate doesn't have that appears as a whole…, Raise ToolLeakViolation if a job-description tool the candidate doesn't have…, ToolLeakGuard, ToolLeakViolation, _profile() (+3 more)

### Community 44 - "validate_cover_letter"
Cohesion: 0.16
Nodes (11): Programmatic validation of a cover letter. Args: text: The cover letter text to…, validate_cover_letter(), ...with % accuracy" -- the digit-blanking fallback's signature., A first body paragraph opening on a referent that was deleted., Only the FIRST body paragraph can dangle -- a later "That ..." points at the…, lenient tolerates style sins, not a letter with holes in it -- and lenient is…, The fallback drops the paragraph rather than leaving its units stranded. Less…, The same 5+ word claim showing up twice reads as padding, not two different… (+3 more)

### Community 45 - "_strip_preamble"
Cohesion: 0.21
Nodes (7): Remove LLM preamble before 'Dear Hiring Manager,' if present. Gemini and other…, Truncate anything after the sign-off line. Models occasionally add notes/P.S.…, _strip_after_signoff(), _strip_preamble(), An incidental earlier mention of the name must not truncate the real body that…, endeared'/'dearest' mid-preamble must not be mistaken for the letter's real…, TestStripHelpers

### Community 46 - "Fact"
Cohesion: 0.16
Nodes (10): Fact, Verified-fact bank for resume tailoring. facts.yaml (repo root) is the ONLY…, One verifiable, pre-written claim the LLM may select for a bullet., Deterministic keyword extraction from a fact's free-text `use_when`.…, Verified facts worth offering the LLM for this job. Facts with no `use_when`…, _use_when_keywords(), A fact is one real thing; it belongs on the CV once -- even if that means a…, The duplicate bullet goes; the entry survives on its other one. (+2 more)

### Community 47 - "drop_unverifiable_quotes"
Cohesion: 0.21
Nodes (8): drop_unverifiable_quotes(), _quote_key(), Normalised form for checking a model-supplied quote against the CV. Case and…, Remove any model-quoted bullet that does not actually occur in the CV. The…, The guard that keeps a finding from resting on a quote the CV does not contain.…, The model quotes bullets as rendered; resolved bullets have no dash. Stripping…, Documented consequence of the rule as specified: containment is checked against…, TestDropUnverifiableQuotes

### Community 48 - "manifest.json"
Cohesion: 0.18
Nodes (10): contract, corpus_A_size, corpus_B_size, critic_commit, dropped_stale_on_rescore, generator_commit, model, tailor_settings (+2 more)

### Community 49 - "_tailor_one_job"
Cohesion: 0.50
Nodes (4): check_listing_still_open(), Best-effort check for whether a job listing is still accepting applications,…, Tailor a resume for one job: liveness check, LLM call, file writes, PDF…, _tailor_one_job()

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
Nodes (29): FactBank, FactBankLoadError, Path, Raised when facts.yaml fails integrity checks at load time., Parses facts.yaml and is the sole gate on what quantified claims the tailoring…, Parse facts.yaml into Facts, validating every verified fact's numbers against…, Stage: Cover letter generation., _run_cover() (+21 more)

### Community 58 - "analyse"
Cohesion: 0.33
Nodes (5): _is_differentiator_bullet(), True for an award/recognition/funding bullet -- see _DIFFERENTIATOR_BULLET_RE.…, analyse(), parse_cv(), Sufficiency report for corpus A, firing table for corpus B. Extractions were…

### Community 60 - "NumericGuardViolation"
Cohesion: 0.22
Nodes (7): BulletPlacementViolation, FactBankError, NumericGuardViolation, Exception, Base class for fact-bank problems., Raised by NumericGuard when the assembled resume text contains a number that…, Raised when a resolved bullet is rendered under an entry other than its…

### Community 61 - "_repair_summary"
Cohesion: 0.28
Nodes (7): Rewrite `resolved_data["summary"]` in place if it fell into a rut or just…, _repair_summary(), _Client, The duplication defect fires on nearly every CV, so it repairs one field rather…, Describing the rule isn't enough -- the model has to see the sentences it is…, A rewrite is LLM-authored text like any other and gets the same numeric…, TestRepairSummary

### Community 62 - "format_facts_block"
Cohesion: 0.33
Nodes (5): format_facts_block(), Render verified facts as an id-keyed list for a prompt. Shared by resume…, Once on the id line isn't enough: the variant text is what the model reads when…, A letter has no entries, so ownership is meaningless there., TestFormatFactsBlockOwner

### Community 63 - "tailor.py"
Cohesion: 0.10
Nodes (24): _apply_canonical_entries(), _bullet_text(), _bullets_similar(), _entry_owns_fact(), find_summary_duplicate_bullets(), _likely_fact_id(), _merge_canonical_section(), Resume tailoring: LLM-powered ATS-optimized resume generation per job. THIS IS… (+16 more)

### Community 64 - "_CleanClient"
Cohesion: 0.40
Nodes (3): _CleanClient, A well-behaved local model: no fabricated numbers, no leaked tools, names the…, TestRunCoverLettersIntegration

### Community 65 - "NumericGuard"
Cohesion: 0.19
Nodes (8): NumericGuard, Deterministic, post-generation check: every number in the assembled resume text…, Raise NumericGuardViolation if any line contains a number that isn't in the…, _qualitative_fact(), Canonical example: an injected, unevidenced 500 must be caught., The real 4-to-9 participant fact must pass cleanly., A zero-number verified fact (mirrors kraydel.audit_system)., TestNumericGuard

### Community 66 - "_store_jobs_filtered"
Cohesion: 0.40
Nodes (5): _location_ok(), Connection, Check if a job location passes the user's location filter., Store jobs with location filtering. Returns (new, existing)., _store_jobs_filtered()

### Community 67 - "test_facts.py"
Cohesion: 0.20
Nodes (8): _bank(), _embedded_fact(), _FakeClient, Tests for the FactBank / NumericGuard architectural fabrication guard. Fixtures…, Always returns the same fabricated response, regardless of the 'AVOID THESE…, A use_when-restricted fact (mirrors edu.embedded_marks)., TestFactBankJobAwareSelection, TestGuardFailureFallsBack

### Community 68 - "group_near_identical"
Cohesion: 0.23
Nodes (8): description_shingles(), group_near_identical(), Set of 5-word shingle hashes over a description's first 600 words. Order-…, Map url -> a group number, for ads that read as the same posting. Only urls…, shingle_jaccard(), Advisory badge only. It must never be wired to duplicate_of: the 2026-09-02…, Below 0.8 Jaccard, 0 of 1093 sampled same-employer pairs were duplicates by the…, TestGroupNearIdentical

### Community 69 - "has_bad_signoff"
Cohesion: 0.40
Nodes (3): has_bad_signoff(), Return a description of what's wrong with the sign-off, or None. The prompt…, The prompt asks for 'Sincerely,' then the name and nothing else -- a trailing…

### Community 70 - "judge_tailored_resume"
Cohesion: 0.50
Nodes (4): _build_judge_prompt(), judge_tailored_resume(), LLM judge layer: catches subtle fabrication that programmatic checks miss.…, Build the LLM judge prompt from the user's profile. The judge only ever sees…

### Community 71 - "find_min_bullet_violations"
Cohesion: 0.50
Nodes (4): _facts_available_for_entry(), find_min_bullet_violations(), The verified facts this CV entry is the real-world owner of. A Fact's `source`…, For each canonical EXPERIENCE entry with at least `min_bullets` relevant…

### Community 72 - "TestRewordedFactBullets"
Cohesion: 0.20
Nodes (4): The wording is the model's; the numbers are not. A rewording that reaches for a…, Tighter than NumericGuard's global allowed set on purpose: 11 is verified, but…, Back-compat: the original select-a-variant shape is unchanged., TestRewordedFactBullets

### Community 73 - "main"
Cohesion: 0.67
Nodes (3): callback, main(), ScoutPilot — scouts early-career jobs, scores fit, and tailors your CV per…

## Knowledge Gaps
- **39 isolated node(s):** `generator_commit`, `critic_commit`, `model`, `max_retries`, `validation_mode` (+34 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_connection()` connect `get_connection` to `scorer.py`, `test_prefilter.py`, `view.py`, `smartextract.py`, `list_jobs`, `init_db`, `workday.py`, `launcher.py`, `test_discovery.py`, `cli.py`, `jobspy.py`, `FactBank`, `generate_dashboard`, `tailor.py`?**
  _High betweenness centrality (0.151) - this node is a cross-community bridge._
- **Why does `FactBank` connect `FactBank` to `sanitize_text`, `view.py`, `get_connection`, `test_facts.py`, `judge_tailored_resume`, `UnfilledFact`, `.verified`, `find_min_bullet_violations`, `TestRewordedFactBullets`, `Fact`, `_tailor_one_job`, `test_cover_letter.py`, `test_critic.py`, `tailor_resume`, `._bank`, `NumericGuardViolation`, `check_no_cross_section_duplicates`, `tailor.py`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Why does `get_client()` connect `scorer.py` to `smartextract.py`, `judge_tailored_resume`, `init_db`, `LLMClient`, `FactBank`, `tailor_resume`, `tailor.py`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `FactBank` (e.g. with `_build_cover_letter_prompt()` and `cover_letter_one()`) actually correct?**
  _`FactBank` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `tailor_resume()` (e.g. with `BulletPlacementViolation` and `FactBank`) actually correct?**
  _`tailor_resume()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `Fact` (e.g. with `_fact()` and `TestBulletOwnership`) actually correct?**
  _`Fact` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `generator_commit`, `critic_commit`, `model` to the rest of the system?**
  _39 weakly-connected nodes found - possible documentation gaps or missing edges._