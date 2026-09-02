# ScoutPilot

ScoutPilot scouts early-career and graduate software jobs, scores each one against
your profile, and tailors your CV and cover letter to the roles worth applying to.
It **submits applications only where applying is cheap** — a plain career-page form —
and hands you everything prepared for the rest.

The old name (ApplyPilot) implied that auto-applying to everything was the point.
It isn't. Firing a generic CV at a thousand listings is easy and doesn't work. The
work that matters is *finding* the few roles you'd actually get an interview for and
putting a tailored, truthful CV in front of them.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-green.svg)](LICENSE)

---

## What it actually does

A six-stage pipeline over a single SQLite database. Each stage reads rows the
previous stage produced and writes its own columns back; you can run one stage,
a few, or all of them.

| Stage | What it does | Key guarantee |
|-------|--------------|---------------|
| **discover** | Harvests postings from job boards (LinkedIn / Indeed / Glassdoor / ZipRecruiter / Google via JobSpy), Workday employer portals, direct ATS boards (Greenhouse / Ashby / Lever), Hacker News "Who is Hiring", and a curated list of UK/Ireland graduate schemes. Deduplicates by URL. | A cheap deterministic pre-filter drops obviously-wrong rows (wrong region, senior titles, multi-year experience asks) before any LLM sees them. |
| **enrich** | Fetches the full job description for each posting — JSON-LD first, then CSS-selector patterns, then LLM extraction for unknown layouts. | — |
| **score** | An LLM rates fit 1–10 against your profile, then a deterministic eligibility gate runs after it (work authorisation, region). Only `fit_score >= min_score` (default 7) proceeds. | The gate can only *lower* a score, never raise it. |
| **tailor** | Rewrites your CV per job: reorders entries, re-emphasises relevant work, pulls in the job's own vocabulary. | Every quantified claim must trace to `facts.yaml`. `NumericGuard` rejects any number with no source; `ToolLeakGuard` rejects any tool/tech you don't have; a bullet may state a fact once, in the entry that owns it. An LLM judge and an extraction-only critic run last. |
| **cover** | Writes one cover letter per job, grounded in the same fact bank. | Same numeric and fabrication guards as tailoring. |
| **pdf** | Renders the tailored CV and cover letter to PDF, sized to your locale (A4 / 2 pages for the UK, Letter / 1 page for the US). | — |
| **apply** *(optional)* | For jobs whose apply URL is a simple form, a Claude Code session drives a headless Chrome instance to fill and submit it. Manual-ATS domains are skipped, not attempted. | `--dry-run` fills without submitting. |

Run `scoutpilot run` for stages 1–6, `scoutpilot apply` for the last one.

---

## How it's measured

**The success metric is interviews, not scores.** The critic score, the judge, and
the guards are there to stop the tool shipping a CV with a fabricated number or a
skill you don't have — they are a floor, not a target. A CV that scores 9.8 and gets
no callback is worse than one that scores 8.0 and gets three.

Two numbers drive the tuning:

- **Per-source hit rate** — of the jobs scored from a given source, the share that
  reach `fit_score >= 7`. This is how discovery effort is allocated: high-yield
  sources are scored first; low-yield ones are sampled rather than scored
  exhaustively so the number stays honest. `scoutpilot status` shows the table.
- **Fabrication-guard fire rate** — how often the numeric / tool-leak / placement
  guards or the judge reject a draft. A rising rate means the prompt or the fact
  bank drifted, not that the guards should be relaxed.

Everything in `facts.yaml` is a claim you've verified once and can defend in an
interview. Nothing else is allowed into a CV.

---

## Install

```bash
pip install scoutpilot
# python-jobspy pins an exact numpy in its metadata that fights pip's resolver
# but runs fine against any modern numpy — install it without deps, then its
# real runtime deps:
pip install --no-deps python-jobspy && pip install pydantic tls-client requests markdownify regex

scoutpilot init      # one-time: profile, resume, search config, API key
scoutpilot doctor    # shows what's installed and what's missing
```

| Component | Needed for | Notes |
|-----------|-----------|-------|
| Python 3.11+ | everything | |
| Gemini API key | score, tailor, cover | Free tier (15 RPM / 1M tokens/day) is enough. OpenAI and local models (Ollama / llama.cpp) also work. |
| Node.js 18+ | `apply` | runs the Playwright MCP server via `npx` |
| Chrome / Chromium | `apply` | auto-detected; override with `CHROME_PATH` |
| Claude Code CLI | `apply` | [claude.ai/code](https://claude.ai/code) |
| CapSolver API key | `apply`, optional | CAPTCHA solving; without it, CAPTCHA-blocked forms fail gracefully |

---

## Configuration

`scoutpilot init` writes these under `~/.applypilot/` (the state directory name is
unchanged so existing data keeps working):

- **`profile.json`** — contact details, work authorisation, compensation,
  experience, skills, and `resume_facts` (preserved verbatim during tailoring).
- **`searches.yaml`** — search queries, target titles, locations, which sources
  are enabled, and an optional `location_focus` block to work one region at a time.
- **`.env`** — `GEMINI_API_KEY`, optional `LLM_MODEL`, optional `CAPSOLVER_API_KEY`.
- **`facts.yaml`** (repo root) — the verified fact bank. The only source of
  quantified claims in any generated document.

Shipped with the package, in `src/scoutpilot/config/`:

- `employers.yaml` — Workday employer registry
- `ats_employers.yaml` — Greenhouse / Ashby / Lever board slugs
- `schemes.yaml` — curated graduate schemes and funded-training programmes
- `sites.yaml` — direct career sites, blocked sites, manual-ATS domains
- `searches.example.yaml` — example search config

---

## CLI reference

```
scoutpilot init                       # first-time setup wizard
scoutpilot doctor                     # verify setup, diagnose missing pieces
scoutpilot run [stages...]            # run pipeline stages (default: all of 1-6)
scoutpilot run --workers 4            # parallel discovery / enrichment
scoutpilot run --stream               # run stages concurrently (DB as conveyor)
scoutpilot run --min-score 8          # override the fit threshold
scoutpilot run --dry-run              # preview without executing
scoutpilot run --validation lenient   # relax banned-word retries (Gemini free tier)
scoutpilot status                     # pipeline stats + per-source hit-rate table
scoutpilot dashboard                  # open the HTML results dashboard
scoutpilot jobs                       # browse scored jobs in the terminal

scoutpilot apply                      # drive Chrome to submit simple-form jobs
scoutpilot apply --workers 3          # parallel browser workers
scoutpilot apply --dry-run            # fill forms without submitting
scoutpilot apply --continuous         # keep polling for new jobs
scoutpilot apply --url URL            # apply to one specific job
scoutpilot apply --mark-applied URL   # record a manual application
scoutpilot apply --reset-failed       # requeue all failed jobs
scoutpilot apply --gen --url URL      # write the agent prompt to a file for debugging
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[GNU Affero General Public License v3.0](LICENSE). If you deploy a modified version
as a service, you must release your source under the same license.
