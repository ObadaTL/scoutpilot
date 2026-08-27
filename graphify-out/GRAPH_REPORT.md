# Graph Report - ApplyPilot-main  (2026-08-27)

## Corpus Check
- 59 files · ~178,906 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1178 nodes · 2293 edges · 60 communities (55 shown, 5 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 92 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `de7b89df`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- _run_one_site
- _HTMLStripper
- _canonical_skills_lines
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
- run_wizard
- tailor.py
- test_discovery.py
- cli.py
- scorer.py
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
- sanitize_text
- load_profile
- _strip_preamble
- smartextract.py
- workday.py
- [0.2.0] - 2026-02-17
- find_header_restating_bullets
- list_jobs
- critic.py
- rules/graphify.md
- workflows/graphify.md
- test_cover_letter.py
- validate_cover_letter
- get_client
- cover_letter.py
- drop_unverifiable_quotes
- manifest.json
- .verified
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

## God Nodes (most connected - your core abstractions)
1. `get_connection()` - 56 edges
2. `FactBank` - 49 edges
3. `init_db()` - 32 edges
4. `tailor_resume()` - 32 edges
5. `Fact` - 25 edges
6. `evaluate_cv_observations()` - 22 edges
7. `generate_cover_letter()` - 20 edges
8. `TestEligibilityGate` - 20 edges
9. `apply_eligibility_gate()` - 19 edges
10. `ToolLeakGuard` - 18 edges

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

## Communities (60 total, 5 thin omitted)

### Community 0 - "_run_one_site"
Cohesion: 0.06
Nodes (42): ask_llm(), clean_page_html(), collect_page_intelligence(), execute_api_response(), execute_css_selectors(), execute_json_ld(), extract_json(), format_strategy_briefing() (+34 more)

### Community 1 - "_HTMLStripper"
Cohesion: 0.08
Nodes (19): HTMLParser, fetch_details(), _fetch_one_detail(), _HTMLStripper, _location_ok(), Convert HTML to plain text., Open a URL using the configured opener (with or without proxy)., Search jobs via Workday CXS API. Returns JSON with total + jobPostings. (+11 more)

### Community 2 - "_canonical_skills_lines"
Cohesion: 0.17
Nodes (9): _canonical_skills_lines(), The TECHNICAL SKILLS lines, one per profile.skills_boundary category, composed…, Once canonical_entries.experience is configured, it's exhaustive: an EXPERIENCE…, The exact incident: the model filed the candidate's own degree as a job once…, The same unmatched-entry situation in PROJECTS is kept, not rejected -- a…, TECHNICAL SKILLS renders only what the profile actually declares -- the LLM's…, The exact incident: the model added 'LangChain (agent frameworks)' and…, TestCanonicalExperienceRejection (+1 more)

### Community 3 - "detail.py"
Cohesion: 0.16
Nodes (18): _load_base_urls(), Connection, Detail page enrichment: scrapes full descriptions and apply URLs. For each job…, Resolve all relative URLs in the database. Returns stats., Re-fetch WTTJ Algolia API to get proper detail URLs and fix slug-as-title.…, Process all jobs for one site using shared browser context. If conn is None,…, Groups pending jobs by site and processes each batch. Sequential by default.…, Set proxy config from an external caller. (+10 more)

### Community 4 - "get_connection"
Cohesion: 0.05
Nodes (66): mark_job(), Path, Release the in_progress lock without recording a terminal outcome. Used when a…, Manually mark a job's apply status in the database. Records this as a completed…, Clear one job's apply status back to pending, e.g. after a wrong manual mark or…, Spawn a Claude Code session for one job application. Returns: Tuple of…, release_lock(), reset_job() (+58 more)

### Community 5 - "evaluate_cv_observations"
Cohesion: 0.11
Nodes (13): evaluate_cv_observations(), Apply fixed, code-side thresholds to the model's raw extraction. Never trusts…, On three bullets a single NONE is already a third: the fraction carries no…, The exact incident: Revolut round 2 (2026-08-26) was flagged 6/11 while a human…, The counterpart the exemption must not swallow: round 1's Java Software…, The exact incident: 'VIOFEEL has 1 bullet, below the minimum of 2' landed on 6…, The floor drops only where the material genuinely runs out. Kraydel has nine…, The model quotes the header back out of the rendered CV; only case and spacing… (+5 more)

### Community 6 - "chrome.py"
Cohesion: 0.12
Nodes (24): Popen, cleanup_on_exit(), cleanup_worker(), kill_all_chrome(), _kill_on_port(), _kill_process_tree(), launch_chrome(), Path (+16 more)

### Community 7 - "prompt.py"
Cohesion: 0.13
Nodes (21): _build_captcha_section(), _build_hard_rules(), _build_location_check(), _build_profile_summary(), build_prompt(), _build_salary_section(), _build_screening_section(), Prompt builder for the autonomous job application agent. Constructs the full… (+13 more)

### Community 8 - "launcher.py"
Cohesion: 0.06
Nodes (42): add_event(), Update the worker's state fields. Args: worker_id: Which worker to update.…, Add a timestamped event to the scrolling event log. Args: msg: Rich markup…, update_state(), Apply pipeline: Chrome management, prompt building, orchestration, and…, acquire_job(), _check_playwright_mcp(), _is_permanent_failure() (+34 more)

### Community 9 - "_StageTracker"
Cohesion: 0.18
Nodes (7): Event, Thread-safe tracker for which stages have finished producing work., Run a single stage in streaming mode: loop until upstream done + no work. For…, Execute stages concurrently with DB as conveyor belt., _run_stage_streaming(), _run_streaming(), _StageTracker

### Community 10 - "dashboard.py"
Cohesion: 0.16
Nodes (14): Group, get_state(), get_totals(), init_worker(), Rich live dashboard for the apply pipeline. Displays real-time worker status,…, Build the Rich table showing all worker statuses. Returns: A Rich Table object…, Render the dashboard table plus the recent events panel. Returns: A Rich Group…, Compute aggregate totals across all workers. Returns: Dict with keys: applied,… (+6 more)

### Community 11 - "pdf.py"
Cohesion: 0.09
Nodes (27): Stage: PDF conversion — convert tailored resumes and cover letters to PDF., _run_pdf(), batch_convert(), build_cover_letter_html(), build_html(), _cover_letter_font_faces(), _cv_font_faces(), _fit_resume_html() (+19 more)

### Community 12 - "LLMClient"
Cohesion: 0.13
Nodes (11): Response, _GeminiCompatForbidden, LLMClient, Exception, Thin LLM client supporting OpenAI-compatible and native Gemini endpoints. For…, Call the native Gemini generateContent API. Used automatically when the OpenAI-…, Call the OpenAI-compatible endpoint. json_schema, when given, is passed as…, Call Ollama's native /api/chat, optionally with a JSON-schema `format`.… (+3 more)

### Community 13 - "validator.py"
Cohesion: 0.15
Nodes (15): _company_tokens(), find_fabricated_numbers(), has_dangling_reference(), has_lifted_jd_span(), has_repeated_phrase(), _is_mostly_filler(), Resume and cover letter validation: banned words, fabrication detection,…, Find number-bearing claims in tailored text with no basis in the original.… (+7 more)

### Community 14 - "run_wizard"
Cohesion: 0.17
Nodes (15): init(), Run the first-time setup wizard (profile, resume, search config)., ApplyPilot first-time setup wizard. Interactive flow that creates…, Generate a searches.yaml from user input., Ask about AI scoring/tailoring — optional LLM configuration., Configure autonomous job application (requires Claude Code CLI)., Run the full interactive setup wizard., Prompt for resume file and copy into APP_DIR. (+7 more)

### Community 15 - "tailor.py"
Cohesion: 0.08
Nodes (37): _apply_canonical_entries(), _build_guard_scan_text(), _bullet_text(), _bullets_similar(), _entry_owns_fact(), _facts_available_for_entry(), find_min_bullet_violations(), _likely_fact_id() (+29 more)

### Community 16 - "test_discovery.py"
Cohesion: 0.09
Nodes (30): fetch_ashby_jobs(), fetch_greenhouse_jobs(), fetch_lever_jobs(), _http_get_json(), infer_opportunity_type(), Helper to fetch and parse JSON from a public endpoint., Fetch jobs from a Greenhouse board via its public JSON API. Endpoint:…, Fetch jobs from an Ashby board via its public JSON API. Endpoint:… (+22 more)

### Community 17 - "cli.py"
Cohesion: 0.05
Nodes (63): command, gen_prompt(), main(), Generate a prompt file and print the Claude CLI command for manual debugging.…, Launch the apply pipeline. Args: limit: Max jobs to apply to (0 or with…, apply(), _bootstrap(), clean() (+55 more)

### Community 18 - "scorer.py"
Cohesion: 0.06
Nodes (34): apply_eligibility_gate(), _build_candidate_level(), _candidate_is_unrestricted(), _clean_optional_field(), _country_in_text(), _normalize_country(), _parse_score_response(), Job fit scoring: LLM-powered evaluation of candidate-job match quality. Scores… (+26 more)

### Community 19 - "init_db"
Cohesion: 0.06
Nodes (55): discover(), Run specific or all discovery harvesters to find jobs, graduate schemes, and…, init_db(), Create the full jobs table with all columns from every pipeline stage. This is…, Store discovered jobs, skipping duplicates by URL. Args: conn: Database…, store_jobs(), is_relevant_tech_role(), Direct ATS API harvester: scrapes Greenhouse, Ashby, and Lever career portals.… (+47 more)

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
Cohesion: 0.06
Nodes (33): Fact, One verifiable, pre-written claim the LLM may select for a bullet., _bank(), _embedded_fact(), _FakeClient, _kraydel_multiparty_fact(), _qualitative_fact(), Tests for the FactBank / NumericGuard architectural fabrication guard. Fixtures… (+25 more)

### Community 28 - ".match_similar"
Cohesion: 0.22
Nodes (6): _accept_reworded(), Best-effort recovery for a plain-string bullet that has a digit but is actually…, Turn one LLM-output bullet into literal text. See resolve_bullet_ex for the…, Turn one LLM-output bullet into (literal text, fact id or None). A fact-…, Whether the model's own wording of `fact` may be used in place of the fact's…, _significant_words()

### Community 29 - "facts.py"
Cohesion: 0.11
Nodes (17): BulletPlacementViolation, FactBankError, FactBankLoadError, NumericGuard, NumericGuardViolation, Exception, Verified-fact bank for resume tailoring. facts.yaml (repo root) is the ONLY…, Base class for fact-bank problems. (+9 more)

### Community 30 - "check_no_cross_section_duplicates"
Cohesion: 0.15
Nodes (11): check_no_cross_section_duplicates(), _normalize_bullet_for_dup_check(), Hard assertion: the same claim may not appear twice anywhere in the assembled…, check_no_cross_section_duplicates is the hard backstop: even if ownership/dedup…, Exact-text matching alone missed this live 2026-08-26: the same fact, worded…, The blind spot the projects-vs-experience loop had by construction: two bullets…, The exact pairing named in _likely_fact_id's docstring: 'Built dual ML…, Same section, two different headings -- also invisible to the old loop, which… (+3 more)

### Community 31 - "sanitize_text"
Cohesion: 0.13
Nodes (18): Split arbitrary CV/resume text into sections keyed by ALL-CAPS headers. Unlike…, split_sections(), assemble_resume_text(), _base_summary(), _canonical_education_line(), extract_extra_sections(), _fallback_unquantified(), _format_education() (+10 more)

### Community 32 - "load_profile"
Cohesion: 0.12
Nodes (22): get_profile_keywords(), load_profile(), Extract full list of technical skills, domains, and role keywords from…, Load user profile from ~/.applypilot/profile.json., is_local_provider(), True when generation will hit a local (non-cloud) LLM_URL endpoint. Mirrors…, Stage: Cover letter generation., _run_cover() (+14 more)

### Community 33 - "_strip_preamble"
Cohesion: 0.21
Nodes (7): Remove LLM preamble before 'Dear Hiring Manager,' if present. Gemini and other…, Truncate anything after the sign-off line. Models occasionally add notes/P.S.…, _strip_after_signoff(), _strip_preamble(), An incidental earlier mention of the name must not truncate the real body that…, endeared'/'dearest' mid-preamble must not be mistaken for the letter's real…, TestStripHelpers

### Community 34 - "smartextract.py"
Cohesion: 0.20
Nodes (13): build_scrape_targets(), clean_card_html(), _load_location_filter(), load_sites(), AI-powered smart extraction: discovers jobs from arbitrary websites. Two-phase…, Run smart extract on all targets. Sequential by default. When workers > 1,…, Main entry point for AI-powered smart extraction. Loads sites from…, Load location accept/reject lists from search config. (+5 more)

### Community 35 - "workday.py"
Cohesion: 0.16
Nodes (16): load_employers(), _load_location_filter(), _process_one(), Connection, Workday ATS direct API scraper: searches employer career portals. Scrapes…, Configure a global urllib opener with proxy support., Store corporate jobs in DB. Returns (new, existing)., Load Workday employer registry from config/employers.yaml. (+8 more)

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
Cohesion: 0.21
Nodes (13): _build_cv_critic_user_message(), _build_letter_critic_user_message(), CriticResult, _is_differentiator_bullet(), _normalize_header(), Extraction-only "critic" pass over a tailored CV and cover letter. Catches…, Loose key for matching a header the model quoted back out of the CV against the…, score is COMPUTED from discrete findings (10.0 minus each finding's weight,… (+5 more)

### Community 43 - "test_cover_letter.py"
Cohesion: 0.20
Nodes (10): _bank(), _FabricatingClient, isolated_env(), _multiparty_fact(), fixture, Tests for the six cover-letter-generation defect fixes. Fast unit tests…, Always fabricates the same unverified number, regardless of retry feedback --…, Retries must keep sampling temperature, not drop it. The old behaviour was 0.7… (+2 more)

### Community 44 - "validate_cover_letter"
Cohesion: 0.16
Nodes (11): Programmatic validation of a cover letter. Args: text: The cover letter text to…, validate_cover_letter(), ...with % accuracy" -- the digit-blanking fallback's signature., A first body paragraph opening on a referent that was deleted., Only the FIRST body paragraph can dangle -- a later "That ..." points at the…, lenient tolerates style sins, not a letter with holes in it -- and lenient is…, The fallback drops the paragraph rather than leaving its units stranded. Less…, The same 5+ word claim showing up twice reads as padding, not two different… (+3 more)

### Community 45 - "get_client"
Cohesion: 0.22
Nodes (9): _detect_provider(), get_client(), Unified LLM client for ApplyPilot. Auto-detects provider from environment:…, Return (base_url, model, api_key) based on environment variables. Reads env at…, Return (or create) the module-level LLMClient singleton., _build_judge_prompt(), judge_tailored_resume(), LLM judge layer: catches subtle fabrication that programmatic checks miss.… (+1 more)

### Community 46 - "cover_letter.py"
Cohesion: 0.15
Nodes (17): format_facts_block(), Render verified facts as an id-keyed list for a prompt. Shared by resume…, _build_cover_letter_prompt(), _check_company_mentioned(), generate_cover_letter(), _normalize_greeting_spacing(), Cover letter generation: LLM-powered, profile-driven, with validation.…, Guarantee exactly one blank line between the "Dear ...," greeting and the first… (+9 more)

### Community 47 - "drop_unverifiable_quotes"
Cohesion: 0.21
Nodes (8): drop_unverifiable_quotes(), _quote_key(), Normalised form for checking a model-supplied quote against the CV. Case and…, Remove any model-quoted bullet that does not actually occur in the CV. The…, The guard that keeps a finding from resting on a quote the CV does not contain.…, The model quotes bullets as rendered; resolved bullets have no dash. Stripping…, Documented consequence of the rule as specified: containment is checked against…, TestDropUnverifiableQuotes

### Community 48 - "manifest.json"
Cohesion: 0.18
Nodes (10): contract, corpus_A_size, corpus_B_size, critic_commit, dropped_stale_on_rescore, generator_commit, model, tailor_settings (+2 more)

### Community 49 - ".verified"
Cohesion: 0.20
Nodes (7): _extract_numbers(), Recursively pull every integer token out of a nested structure. Used to fold…, Deterministic keyword extraction from a fact's free-text `use_when`.…, All tier == 'verified' facts. The ONLY facts ever exposed to the LLM., Every number the tailoring output is allowed to contain: the union of every…, Verified facts worth offering the LLM for this job. Facts with no `use_when`…, _use_when_keywords()

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
Cohesion: 0.12
Nodes (17): check_listing_still_open(), Best-effort check for whether a job listing is still accepting applications,…, FactBank, Path, A known gap: a plausible claim that needs a real value filled in before it can…, Parses facts.yaml and is the sole gate on what quantified claims the tailoring…, Parse facts.yaml into Facts, validating every verified fact's numbers against…, Unverified entries pending a real value, for a CLI prompt flow. (+9 more)

### Community 57 - "has_bad_signoff"
Cohesion: 0.40
Nodes (3): has_bad_signoff(), Return a description of what's wrong with the sign-off, or None. The prompt…, The prompt asks for 'Sincerely,' then the name and nothing else -- a trailing…

### Community 58 - "analyse"
Cohesion: 0.50
Nodes (3): analyse(), parse_cv(), Sufficiency report for corpus A, firing table for corpus B. Extractions were…

### Community 59 - "main"
Cohesion: 0.67
Nodes (3): callback, main(), ApplyPilot — AI-powered end-to-end job application pipeline.

## Knowledge Gaps
- **51 isolated node(s):** `generator_commit`, `critic_commit`, `model`, `max_retries`, `validation_mode` (+46 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_connection()` connect `get_connection` to `load_profile`, `smartextract.py`, `workday.py`, `detail.py`, `list_jobs`, `launcher.py`, `cover_letter.py`, `tailor.py`, `cli.py`, `scorer.py`, `init_db`, `FactBank`?**
  _High betweenness centrality (0.164) - this node is a cross-community bridge._
- **Why does `FactBank` connect `FactBank` to `load_profile`, `prompt.py`, `test_cover_letter.py`, `get_client`, `cover_letter.py`, `tailor.py`, `.verified`, `test_critic.py`, `._bank`, `.match_similar`, `facts.py`, `check_no_cross_section_duplicates`, `sanitize_text`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Why does `get_client()` connect `get_client` to `_run_one_site`, `smartextract.py`, `detail.py`, `LLMClient`, `cover_letter.py`, `tailor.py`, `scorer.py`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `FactBank` (e.g. with `_build_cover_letter_prompt()` and `cover_letter_one()`) actually correct?**
  _`FactBank` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `tailor_resume()` (e.g. with `BulletPlacementViolation` and `FactBank`) actually correct?**
  _`tailor_resume()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `Fact` (e.g. with `_fact()` and `TestBulletOwnership`) actually correct?**
  _`Fact` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `generator_commit`, `critic_commit`, `model` to the rest of the system?**
  _51 weakly-connected nodes found - possible documentation gaps or missing edges._