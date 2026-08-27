"""Sufficiency report for corpus A, firing table for corpus B.

Extractions were stored raw, in one pass from one critic version; every
threshold is applied here at report time, so neither corpus is ever
re-generated to answer a question about a threshold. Read-only.
"""
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from applypilot.facts import BulletPlacementViolation, FactBank
from applypilot.scoring.critic import (
    _JD_IRRELEVANCE_MIN_SAMPLE,
    _is_differentiator_bullet,
    drop_unverifiable_quotes,
    evaluate_cv_observations,
)
from applypilot.scoring.tailor import (
    build_bullet_floor_map,
    check_no_cross_section_duplicates,
    find_header_restating_bullets,
)

OUT = ROOT / "corpus_v2"
bank = FactBank.load()
SECTIONS = {"SUMMARY", "TECHNICAL SKILLS", "EXPERIENCE", "PROJECTS", "EDUCATION",
            "LANGUAGES", "CERTIFICATIONS & AWARDS", "AVAILABILITY", "CERTIFICATIONS",
            "AWARDS", "INTERESTS"}


def parse_cv(cv):
    out = {"experience": [], "projects": []}
    section = entry = None
    for line in (cv or "").splitlines():
        st = line.strip()
        if st in SECTIONS:
            section = st.lower() if st in ("EXPERIENCE", "PROJECTS") else None
            entry = None
            continue
        if section is None or not st:
            continue
        if st.startswith("- "):
            if entry is not None:
                entry["bullets"].append(st[2:])
            continue
        if entry is None or entry["bullets"]:
            entry = {"header": st, "subtitle": "", "bullets": []}
            out[section].append(entry)
        else:
            entry["subtitle"] = st
    return out


def analyse(rows):
    for r in rows:
        obs = r.get("critic_raw") or {}
        cv, jd = r.get("cv") or "", r.get("jd") or ""
        data = parse_cv(cv)
        cleaned, dropped = drop_unverifiable_quotes(obs, cv)
        floors = build_bullet_floor_map(data, bank, jd)
        findings, score = evaluate_cv_observations(cleaned, min_bullets_by_header=floors)
        rel = [x for x in (cleaned.get("bullet_jd_relevance") or []) if isinstance(x, dict)]
        exempt = [x for x in rel if _is_differentiator_bullet(str(x.get("bullet", "")))]
        counted = [x for x in rel if x not in exempt]
        try:
            check_no_cross_section_duplicates(data, fact_bank=bank)
            dups = []
        except BulletPlacementViolation as e:
            dups = e.reasons
        r["_"] = dict(
            findings=findings, score=score, dropped=dropped,
            restating=find_header_restating_bullets(data), dups=dups,
            exempt=len(exempt), counted=len(counted), rel=len(rel),
            n_bullets=sum(len(e["bullets"]) for s in data.values() for e in s),
        )
    return rows


CHECKS = {
    "bullet-count below minimum": lambda a: any("below the minimum" in x for x in a["findings"]),
    "bullet-count above maximum": lambda a: any("above the maximum" in x for x in a["findings"]),
    "JD-relevance fires": lambda a: any("don't address any specific" in x for x in a["findings"]),
    "award exemption applies": lambda a: a["exempt"] > 0,
    "sample-size filter suppresses": lambda a: 0 < a["counted"] < _JD_IRRELEVANCE_MIN_SAMPLE,
    "quote-existence guard drops": lambda a: len(a["dropped"]) > 0,
    "header-restatement (code)": lambda a: len(a["restating"]) > 0,
    "duplicate bullets (all-pairs)": lambda a: len(a["dups"]) > 0,
}


def sufficiency(rows, bar=3):
    print("\n" + "=" * 92)
    print("CORPUS A -- SUFFICIENCY: distinct postings exercising each check")
    print("=" * 92)
    print(f"{'check':<34} {'postings':>9} {'/ total':>8}   verdict")
    print("-" * 78)
    under = []
    for name, fn in CHECKS.items():
        hit = [r for r in rows if fn(r["_"])]
        if len(hit) < bar:
            under.append((name, len(hit)))
        print(f"{name:<34} {len(hit):>9} {len(rows):>8}   "
              f"{'OK' if len(hit) >= bar else '>>> UNDER 3 POSTINGS'}")
    return under


a = analyse(json.loads((OUT / "corpus_A.json").read_text(encoding="utf-8")))
b = analyse(json.loads((OUT / "corpus_B.json").read_text(encoding="utf-8")))
man = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))

print("=" * 92)
print(f"CORPUS A -- CALIBRATION SET   (generator commit {man['generator_commit'][:8]})")
print("=" * 92)
print(f"postings            : {len(a)}")
print(f"total bullets       : {sum(r['_']['n_bullets'] for r in a)}")
print(f"flagged >=1 finding : {sum(1 for r in a if r['_']['findings'])}/{len(a)}")
print(f"mean critic score   : {sum(r['_']['score'] for r in a)/len(a):.2f}")
print(f"family              : {dict(Counter(r['family'] for r in a).most_common())}")
print(f"seniority           : {dict(Counter('graduate' if r['grad'] else 'mid' for r in a))}")
print(f"req-line buckets    : {dict(Counter('0' if r['req_lines']==0 else '1-9' if r['req_lines']<10 else '10-19' if r['req_lines']<20 else '20+' for r in a))}")
print(f"length buckets      : {dict(Counter('<2k' if r['jd_len']<2000 else '2-6k' if r['jd_len']<6000 else '6k+' for r in a))}")
print(f"tailor statuses     : {dict(Counter(r.get('tailor_status') for r in a))}")
print(f"dropped on re-score : {len(man.get('dropped_stale_on_rescore') or [])}")

under_a = sufficiency(a)

print("\n" + "=" * 92)
print("CORPUS B -- NEGATIVE-CONTROL HOLDOUT")
print("firing validation only; never enters calibration or corpus-level metrics")
print("=" * 92)
print(f"postings : {len(b)}")
print(f"families : {dict(Counter(r['family'] for r in b).most_common())}")
print(f"\n{'check':<34} {'fired?':>7} {'postings':>9}")
print("-" * 54)
for name, fn in CHECKS.items():
    hit = [r for r in b if fn(r["_"])]
    print(f"{name:<34} {('YES' if hit else 'no'):>7} {len(hit):>9}")

print("\n" + "=" * 92)
print("STILL UNCALIBRATED IN CORPUS A (under 3 distinct postings)")
print("=" * 92)
if under_a:
    for name, n in under_a:
        print(f"  {name}  --  {n} posting(s)")
else:
    print("  none: every check is exercised by 3 or more distinct postings.")

json.dump(
    {"corpus_A": [
        {"url": r["url"], "title": r["title"], "stratum": r["stratum"],
         "family": r["family"], "score": r["_"]["score"],
         "findings": r["_"]["findings"], "restating": r["_"]["restating"],
         "dups": r["_"]["dups"], "dropped_quotes": len(r["_"]["dropped"])}
        for r in a]},
    open(OUT / "report_A.json", "w", encoding="utf-8"), indent=2)
print(f"\nwrote {OUT / 'report_A.json'}")
