"""Re-score 10 of the 7+ postings three times each.

Gates corpus membership: if the scorer moves a posting across the 7
boundary between runs, membership in corpus A is itself noisy and every
metric computed over it inherits that noise. Read-only against the DB.
"""
import hashlib
import json
import os
import pathlib
import re
import sqlite3
import statistics
import sys

os.environ["LLM_URL"] = "http://localhost:11434/v1"
os.environ["LLM_MODEL"] = "qwen3:14b"
os.environ.pop("GEMINI_API_KEY", None)

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from scoutpilot.config import load_profile
from scoutpilot.scoring.scorer import score_job

resume_text = pathlib.Path(os.path.expanduser("~/.applypilot/resume.txt")).read_text(encoding="utf-8")
profile = load_profile()

db = os.path.expanduser("~/.applypilot/applypilot.db")
c = sqlite3.connect(db)
c.row_factory = sqlite3.Row
rows = [dict(r) for r in c.execute("""
    select url, title, company, site, location, fit_score,
           coalesce(nullif(full_description,''), description) as full_description
    from jobs
    where fit_score >= 7 and coalesce(hidden,0) = 0
      and length(coalesce(nullif(full_description,''), description)) > 800
""")]
seen, uniq = set(), []
for r in sorted(rows, key=lambda x: hashlib.sha1(x["url"].encode()).hexdigest()):
    k = ((r["title"] or "").lower().strip(), (r["company"] or "").lower().strip())
    if k in seen or not r["title"]:
        continue
    seen.add(k)
    uniq.append(r)

sample = uniq[:10]
print(f"re-scoring {len(sample)} postings x 3 runs, temperature as production\n")

results = []
for i, job in enumerate(sample, 1):
    scores = []
    for run in range(3):
        try:
            out = score_job(resume_text, job, profile)
            scores.append(out.get("score"))
        except Exception as e:
            print(f"  !! {job['title'][:40]} run {run+1}: {type(e).__name__}: {e}")
            scores.append(None)
    got = [s for s in scores if isinstance(s, int)]
    crosses = bool(got) and (min(got) < 7 <= max(got))
    results.append(dict(title=job["title"], stored=job["fit_score"], scores=scores,
                        crosses=crosses))
    print(f"{i:>2}. stored={job['fit_score']}  runs={scores}  "
          f"{'<<< CROSSES THE 7 BOUNDARY' if crosses else ''}  {job['title'][:44]}")

print("\n" + "=" * 88)
print("SCORER STABILITY OVER THE 7 BOUNDARY")
print("=" * 88)
allgot = [s for r in results for s in r["scores"] if isinstance(s, int)]
ranges = [max(g) - min(g) for r in results
          if (g := [s for s in r["scores"] if isinstance(s, int)])] or [0]
crossed = [r for r in results if r["crosses"]]
below = [r for r in results
         if (g := [s for s in r["scores"] if isinstance(s, int)]) and max(g) < 7]
print(f"postings re-scored          : {len(results)}")
print(f"identical across all 3 runs : "
      f"{sum(1 for r in results if len(set(r['scores'])) == 1)}/{len(results)}")
print(f"per-posting score range     : min={min(ranges)} median={statistics.median(ranges)} max={max(ranges)}")
print(f"CROSS the 7 boundary        : {len(crossed)}/{len(results)}")
print(f"now score BELOW 7 every run : {len(below)}/{len(results)}")
for r in crossed:
    print(f"   crosses: stored={r['stored']} runs={r['scores']}  {r['title'][:60]}")
for r in below:
    print(f"   fell out: stored={r['stored']} runs={r['scores']}  {r['title'][:60]}")

(ROOT / "corpus_v2").mkdir(exist_ok=True)
(ROOT / "corpus_v2" / "scorer_stability.json").write_text(
    json.dumps(results, indent=2), encoding="utf-8")
print("\nwrote corpus_v2/scorer_stability.json")
