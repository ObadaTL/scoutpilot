"""Build corpus v2 -- two corpora, separate files, never pooled.

A. Calibration corpus: 30 distinct postings, fit_score >= 7 RE-SCORED under
   the pinned commit (stored scores are stale: the 2026-08-27 stability run
   found 1 in 10 no longer scores 7+, deterministically, because the
   eligibility gate landed after those scores were written).
B. Negative-control holdout: 10 postings, lowest scores, off-target role
   families. Firing validation only. Never enters calibration, never enters
   corpus-level metrics.

Every CV comes from generator_commit and nothing else. Extractions are
taken in one pass from one critic version afterwards.
"""
import hashlib
import json
import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import time
from collections import Counter

os.environ["LLM_URL"] = "http://localhost:11434/v1"
os.environ["LLM_MODEL"] = "qwen3:14b"
os.environ.pop("GEMINI_API_KEY", None)

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "corpus_v2"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "src"))

from applypilot.config import load_profile
from applypilot.facts import FactBank
from applypilot.llm import get_client
from applypilot.scoring.critic import run_cv_critic
from applypilot.scoring.scorer import score_job
from applypilot.scoring.tailor import build_bullet_floor_map, tailor_resume

SHA = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                     capture_output=True, text=True).stdout.strip()
MAX_RETRIES, VALIDATION_MODE = 1, "lenient"   # production defaults for a local provider


def log(msg):
    print(msg, flush=True)


REQ = re.compile(r"^\s*[*\u2022\-]\s+\S")
GRAD = re.compile(r"\b(graduate|intern|placement|entry[- ]level|junior|trainee)\b", re.I)
FAM = [
    ("qa", r"\b(qa|sdet)\b|\b(test|quality assurance)\s+(engineer|analyst)\b"),
    ("frontend", r"\b(front[- ]?end|react|vue|angular)\s+(developer|engineer)\b"),
    ("data-eng", r"\b(data|analytics)\s+engineer\b"),
    ("devops-sre", r"\b(devops|sre|platform|infrastructure|cloud)\s+engineer\b"),
    ("mobile", r"\b(ios|android|mobile|flutter)\s+(developer|engineer)\b"),
    ("security", r"\b(security|appsec|cyber\w*)\s+(engineer|analyst)\b"),
    ("nontech", r"\b(support|service desk|business|sales|marketing|hr|finance)\s+"
                r"(engineer|analyst|manager|advisor|specialist)\b"
                r"|\b(project manager|scrum master|product manager|account executive|"
                r"solutions architect|engineering manager|director)\b"),
    ("ml", r"\b(machine learning|ml|ai|data)\s+(engineer|scientist)\b|\bdata scientist\b"),
    ("backend", r"\b(back[- ]?end|java|python|golang|\.net|c#|software)\s+(developer|engineer)\b"),
]


def enrich(r):
    t = (r["title"] or "").strip()
    jd = r["full_description"] or ""
    r["req_lines"] = len([l for l in jd.splitlines() if REQ.match(l)])
    r["jd_len"] = len(jd)
    r["grad"] = bool(GRAD.search(t))
    r["family"] = next((k for k, p in FAM if re.search(p, t, re.I)), "other")
    return r


db = os.path.expanduser("~/.applypilot/applypilot.db")
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
SELECT = """
    select url, title, company, site, location, fit_score,
           coalesce(nullif(full_description,''), description) as full_description
    from jobs
    where coalesce(hidden,0) = 0
      and length(coalesce(nullif(full_description,''), description)) > 800
      and {where}
"""


def load(where):
    rows = [enrich(dict(r)) for r in conn.execute(SELECT.format(where=where))]
    seen, uniq = set(), []
    for r in sorted(rows, key=lambda x: hashlib.sha1(x["url"].encode()).hexdigest()):
        k = ((r["title"] or "").lower().strip(), (r["company"] or "").lower().strip())
        if k in seen or not (r["title"] or "").strip():
            continue
        seen.add(k)
        uniq.append(r)
    return uniq


resume_text = pathlib.Path(os.path.expanduser("~/.applypilot/resume.txt")).read_text(encoding="utf-8")
profile = load_profile()
fact_bank = FactBank.load()
client = get_client()

# ── phase 1/2: corpus A, re-scored under the pinned commit ───────────────
pool_a = load("fit_score >= 7")
log(f"[A] stored-7+ pool: {len(pool_a)} distinct postings")

PLAN_A = [
    ("data-engineering", 4, dict(family="data-eng")),
    ("mobile", 2, dict(family="mobile")),
    ("ml-graduate", 3, dict(family="ml", grad=True)),
    ("ml-mid", 3, dict(family="ml", grad=False)),
    ("backend-graduate", 4, dict(family="backend", grad=True)),
    ("backend-mid", 4, dict(family="backend", grad=False)),
    ("other-role", 3, dict(family="other")),
    ("rich-requirements", 3, dict(min_req=20)),
    ("prose-no-bullets", 2, dict(max_req=0)),
    ("short-jd", 2, dict(max_len=2000)),
]


def matches(r, cond):
    if "family" in cond and r["family"] != cond["family"]:
        return False
    if "grad" in cond and r["grad"] != cond["grad"]:
        return False
    if "min_req" in cond and r["req_lines"] < cond["min_req"]:
        return False
    if "max_req" in cond and r["req_lines"] > cond["max_req"]:
        return False
    if "max_len" in cond and r["jd_len"] > cond["max_len"]:
        return False
    return True


chosen, corpus_a, stale = set(), [], []
t0 = time.time()
for label, n, cond in PLAN_A:
    got = 0
    for r in pool_a:
        if got == n:
            break
        if r["url"] in chosen or not matches(r, cond):
            continue
        fresh = score_job(resume_text, r, profile)
        fs = fresh.get("score")
        if not isinstance(fs, int) or fs < 7:
            stale.append(dict(title=r["title"], stored=r["fit_score"], fresh=fs,
                              gate=fresh.get("gate_reason")))
            chosen.add(r["url"])
            continue
        r["fresh_score"] = fs
        r["stratum"] = label
        chosen.add(r["url"])
        corpus_a.append(r)
        got += 1
    log(f"[A] {label:<20} want {n:>2} got {got:>2}  (elapsed {time.time()-t0:.0f}s)")

log(f"[A] selected {len(corpus_a)}; dropped as stale/<7 on re-score: {len(stale)}")

# ── phase 3: corpus B, negative controls ─────────────────────────────────
pool_b = load("fit_score is not null and fit_score <= 3")
OFF_TARGET = {"nontech", "qa", "frontend", "devops-sre", "security", "mobile", "other"}
corpus_b, seen_fam = [], Counter()
for r in sorted(pool_b, key=lambda x: (x["fit_score"], x["url"])):
    if len(corpus_b) == 10:
        break
    if r["family"] not in OFF_TARGET or seen_fam[r["family"]] >= 3:
        continue
    seen_fam[r["family"]] += 1
    r["stratum"] = f"negative-control:{r['family']}"
    r["fresh_score"] = None
    corpus_b.append(r)
log(f"[B] selected {len(corpus_b)} negative controls: {dict(seen_fam)}")

# ── phase 4/5: generate CVs, then extract in one pass ────────────────────
def build(rows, tag):
    out = []
    for i, r in enumerate(rows, 1):
        t = time.time()
        try:
            cv, report = tailor_resume(resume_text, r, profile,
                                       max_retries=MAX_RETRIES,
                                       validation_mode=VALIDATION_MODE,
                                       fact_bank=fact_bank)
        except Exception as e:
            log(f"[{tag}] {i}/{len(rows)} FAILED {type(e).__name__}: {e}  {r['title'][:40]}")
            continue
        out.append(dict(
            url=r["url"], title=r["title"], company=r["company"], site=r["site"],
            stratum=r["stratum"], family=r["family"], grad=r["grad"],
            req_lines=r["req_lines"], jd_len=r["jd_len"],
            stored_score=r["fit_score"], fresh_score=r.get("fresh_score"),
            jd=r["full_description"], cv=cv,
            tailor_status=report.get("status"), tailor_attempts=report.get("attempts"),
            warnings=report.get("warnings", []),
        ))
        log(f"[{tag}] {i}/{len(rows)} {report.get('status'):<28} "
            f"{time.time()-t:>5.1f}s  {r['title'][:44]}")
        (OUT / f"corpus_{tag}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


log("\n[gen] corpus A ...")
gen_a = build(corpus_a, "A")
log("\n[gen] corpus B ...")
gen_b = build(corpus_b, "B")


def extract(rows, tag):
    for i, r in enumerate(rows, 1):
        try:
            data = {"experience": [], "projects": []}   # floors need structure
            res = run_cv_critic(client, r["cv"], r["jd"])
            r["critic_score"] = res.score
            r["critic_findings"] = res.findings
            r["critic_raw"] = res.raw
            r["dropped_quotes"] = res.dropped_quotes
        except Exception as e:
            log(f"[{tag}-critic] {i} FAILED {type(e).__name__}: {e}")
            r["critic_score"] = None
        log(f"[{tag}-critic] {i}/{len(rows)} score={r.get('critic_score')} "
            f"findings={len(r.get('critic_findings') or [])} "
            f"dropped={len(r.get('dropped_quotes') or [])}")
        (OUT / f"corpus_{tag}.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")


log("\n[critic] one pass, one critic version ...")
extract(gen_a, "A")
extract(gen_b, "B")

(OUT / "manifest.json").write_text(json.dumps({
    "generator_commit": SHA,
    "critic_commit": SHA,
    "model": "qwen3:14b via local Ollama",
    "tailor_settings": {"max_retries": MAX_RETRIES, "validation_mode": VALIDATION_MODE},
    "contract": "Corpus A is the calibration set (fit_score >= 7, re-scored under "
                "generator_commit). Corpus B is a negative-control holdout for firing "
                "validation only -- it never enters threshold calibration and never "
                "appears in corpus-level metrics. Never pool them. Never append a "
                "round generated from a different commit.",
    "corpus_A_size": len(gen_a),
    "corpus_B_size": len(gen_b),
    "dropped_stale_on_rescore": stale,
}, indent=2), encoding="utf-8")
log(f"\nDONE. A={len(gen_a)} B={len(gen_b)} commit={SHA[:8]}")
