  ### 1. Architectural Overview

  ScoutPilot is an autonomous, AI-driven job discovery and application platform. Its architecture is divided into two primary subsystems coordinated
  around a centralized SQLite database:

  1. Preparation Pipeline (scoutpilot run): A linear or streaming data-processing pipeline that discovers jobs, enriches descriptions, scores fit against
  the candidate's profile, tailors resumes/cover letters, and renders PDFs.
  2. Autonomous Application Engine (scoutpilot apply): A multi-worker execution runtime that launches isolated Chrome instances over Chrome DevTools
  Protocol (CDP), orchestrates autonomous Claude Code CLI sessions, fills forms, uploads tailored assets, and tracks results in real-time.

    flowchart TD
        subgraph Discovery ["1. Job Discovery"]
            JS[JobSpy: LinkedIn / Indeed / Glassdoor]
            WD[Workday Scraper]
            SE[SmartExtract Scraper]
        end

        subgraph Pipeline ["2. Enrichment & Tailoring Pipeline"]
            EN[Enrichment: detail.py]
            SC[Scoring: score_job]
            TL[Tailoring: tailor.py]
            CL[Cover Letter Generation]
            PDF[PDF Converter: pdf.py]
        end

        subgraph State ["Central State & Storage"]
            DB[(SQLite DB: database.py)]
            FS[Disk: Tailored PDFs & Profile]
        end

        subgraph ApplyEngine ["3. Auto-Apply Engine"]
            LCH[Launcher / Worker Pool]
            PRM[Prompt Builder: prompt.py]
            CH[Chrome Controller: CDP]
            CC[Claude Code Agent]
            DASH[Live Rich Dashboard]
        end

        JS --> DB
        WD --> DB
        SE --> DB

        DB --> EN --> DB
        DB --> SC --> DB
        DB --> TL --> DB
        DB --> CL --> DB
        DB --> PDF --> FS

        DB --> LCH
        FS --> CC
        LCH --> PRM --> CC
        LCH --> CH
        CC -->|Submits Application| CH
        LCH --> DASH
        LCH -->|Update status| DB
  ──────
  ### 2. Key God Nodes (Core Central Abstractions)

  The knowledge graph identified the following high-centrality "god nodes" that bind the system together:

   God Node                  | Edges | Betweenness | Role in Architecture
  ---------------------------|-------|-------------|------------------------------------------------------------------------------------------------------
   database.py:35            |  33   |    0.189    | Central Data Backbone: Provides database connections across almost all modules (pipeline, launcher,
                             |       |             | scrapers, scoring, tailoring).
   database.py:42            |  21   |    0.069    | Schema Coordinator: Ensures tables, indices, and schema migrations across all pipeline stages exist.
   llm.py                    |  16   |    0.062    | LLM Gateway: Connects OpenAI-compatible APIs and native Gemini endpoints for scoring, extraction,
                             |       |             | and text generation.
   prompt.py                 |  14   |      -      | Agent Prompt Compiler: Assembles application instructions, personal profile data, screening answers,
                             |       |             | and hard rules for Claude Code.
   pdf.py                    |  13   |      -      | Document Renderer: Compiles tailored Markdown/HTML resumes and cover letters into PDF artifacts.
   smartextract.py           |  12   |      -      | Scraping Worker: Executes LLM-assisted web extraction routines for non-standard career pages.
   launcher.py / pipeline.py |  12   |      -      | Execution Loops: Manage streaming pipeline stages and concurrent auto-apply worker pools.
   tailor.py                 |  12   |      -      | Resume Customization Engine: Rewrites work history bullet points to match target job requirements.
   launcher.py               |  11   |      -      | Single Apply Lifecycle: Manages the end-to-end execution of a single application attempt via Claude
                             |       |             | Code and Chrome.
  ──────
  ### 3. Detected Communities & Subsystems

  The graph detected 26 modular communities grouped into the following subsystems:

  #### A. Discovery Subsystem

  • Community 0 (smartextract.py): AI-powered dynamic scraping for custom career sites and job boards using HTML cleaning and LLM extraction.
  • Community 1 (workday.py): Workday ATS-specific corporate crawler handling pagination, location filtering, and direct requisition endpoints.
  • Community 5 (jobspy.py): Aggregated discovery integrating JobSpy across LinkedIn, Indeed, Glassdoor, and ZipRecruiter.

  #### B. Enrichment & Scoring Subsystem

  • Community 3 (detail.py): Enriches shallow postings by parsing JSON-LD schema, stripping boilerplate HTML, and resolving direct apply URLs.
  • Community 18 (score_job) & Community 33 (scoring): Evaluates candidate fit on a 1–10 scale based on seniority level, tech stack, and location.

  #### C. Tailoring & Asset Generation

  • Community 2 (tailor.py): Resume modification and cover letter generation tailored to specific job descriptions.
  • Community 11 (pdf.py): Converts generated markdown and HTML into formatted PDF artifacts stored on disk.

  #### D. Auto-Apply Orchestration

  • Community 6 (chrome.py): Chrome lifecycle manager handling isolated user data directories, CDP port assignments, and process cleanup.
  • Community 7 (prompt.py): Generates agent system instructions, CAPTCHA handling guidelines, and salary expectation constraints.
  • Community 8 (launcher.py) & Community 13 (worker_loop): Thread-safe job queue dispatcher, Claude Code subprocess runner, and state recorder.
  • Community 10 (dashboard.py): Rich-based terminal UI displaying live worker statuses, success rates, and event logs.

  #### E. Core Infrastructure & CLI

  • Community 4 & 16 (get_connection / init_db): SQLite state management and cross-stage persistence.
  • Community 12 (LLMClient): Unified OpenAI/Gemini API abstraction with fallback handling.
  • Community 9 (pipeline.py): Sequential and streaming pipeline orchestrator.
  • Community 14, 15, 17, 19 (cli.py, run_wizard, _bootstrap, main): CLI interface, diagnostic doctor (scoutpilot doctor), and first-time setup wizard.
  ──────
  ### 4. End-to-End Data Flow: From Discovery to Application

  The lifecycle of a job posting moves through 6 distinct stages:

    [Job Discovery] ➔ [Enrichment] ➔ [Fit Scoring] ➔ [Tailoring & PDF] ➔ [Autonomous Apply] ➔ [Result Tracking]

  1. Discovery (discover):
      • jobspy, workday, or smartextract queries search criteria from ~/.applypilot/searches.yaml.
      • Postings are deduplicated by URL and inserted into SQLite via jobspy.py.
  2. Detail Enrichment (enrich):
      • detail.py queries jobs missing full descriptions.
      • It fetches full HTML, extracts JSON-LD metadata or main content, resolves direct application URLs, and updates the database record.
  3. Fit Scoring (score):
      • score.py sends candidate profile details and the job description to the LLM.
      • The LLM returns a structured fit score (1–10), category, pros, cons, and recommendations stored in the score and score_reason columns.
  4. Tailoring & PDF Generation (tailor, cover, pdf):
      • For jobs exceeding the fit score threshold, tailor.py adapts bullet points to emphasize relevant skills.
      • tailor.py drafts a customized cover letter.
      • pdf.py renders both into PDFs stored in ~/.applypilot/artifacts/{job_id}/.
  5. Autonomous Application (apply):
      • launcher.py atomically reserves a job (apply_status = 'in_progress').
      • chrome.py launches a dedicated Chrome instance bound to a worker CDP port.
      • prompt.py builds the instruction set, pointing Claude Code to the tailored PDF resumes and preconfigured answers.
      • Claude Code interacts with the browser via CDP/MCP to navigate the application form, fill fields, upload files, and submit.
  6. Result Recording & Status Updates:
      • The worker parses Claude Code's output and updates SQLite (apply_status = 'applied' | 'failed' | 'needs_review').
      • Live metrics and logs are streamed to dashboard.py.