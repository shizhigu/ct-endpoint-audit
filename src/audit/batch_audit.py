"""
Round 23 — Refined CT.gov endpoint audit.

Fixes Round 22's over-sensitive "post-completion" filter by classifying
each endpoint change into three windows:

  A. BEFORE primary_completion_date
       → protocol amendment during trial (most common, strategic
         significance varies)
  B. BETWEEN primary_completion_date and results_first_posted_date,
     by more than 30 days
       → data is locked (trial ended) but spec is still being changed,
         before results go public → TRUE RED FLAG (window c)
  C. AT results reporting (within 30 days of results_first_posted_date)
       → mandatory specification for results submission, benign

Also collects sponsor names for scorecard.
"""

import json
import re
import time
import urllib.parse
import urllib.request
import sys
from collections import Counter, defaultdict
from datetime import date, datetime

from audit_batch import (
    meaningful_diff,
    history,
    version,
    extract_primary,
    get_json,
)

V2 = "https://clinicaltrials.gov/api/v2/studies"


def parse_date(s: str | None) -> date | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def fetch_phase3_ncts(n: int = 500) -> list[str]:
    params = {
        "filter.overallStatus": "COMPLETED,TERMINATED",
        "filter.advanced": "AREA[Phase]PHASE3 AND AREA[LeadSponsorClass]INDUSTRY",
        "sort": "LastUpdatePostDate:desc",
        "countTotal": "true",
        "pageSize": "100",
        "fields": "NCTId,EnrollmentCount",
    }
    ncts = []
    page_token = None
    while len(ncts) < n:
        p = dict(params)
        if page_token:
            p["pageToken"] = page_token
        url = V2 + "?" + urllib.parse.urlencode(p)
        d = get_json(url)
        if not d:
            break
        for s in d.get("studies", []):
            nct = (
                s.get("protocolSection", {})
                .get("identificationModule", {})
                .get("nctId")
            )
            enroll = (
                s.get("protocolSection", {}).get("designModule", {})
                .get("enrollmentInfo", {})
                .get("count", 0)
            )
            if nct and enroll and enroll >= 300:
                ncts.append(nct)
        page_token = d.get("nextPageToken")
        if not page_token:
            break
        time.sleep(0.15)
    return ncts[:n]


def fetch_meta(nct: str) -> dict:
    """Fetch sponsor, primary_completion, results_first_post from V2 API."""
    url = (
        f"{V2}/{nct}?fields="
        "BriefTitle,LeadSponsorName,OverallStatus,EnrollmentCount,"
        "PrimaryCompletionDate,CompletionDate,ResultsFirstPostDate,"
        "ResultsFirstSubmitDate,Condition"
    )
    d = get_json(url)
    if not d:
        return {}
    p = d.get("protocolSection", {})
    status = p.get("statusModule", {})
    return {
        "title": p.get("identificationModule", {}).get("briefTitle"),
        "sponsor": p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name"),
        "enroll": p.get("designModule", {}).get("enrollmentInfo", {}).get("count"),
        "conditions": p.get("conditionsModule", {}).get("conditions"),
        "primary_completion": status.get("primaryCompletionDateStruct", {}).get("date"),
        "results_first_post": status.get("resultsFirstPostDateStruct", {}).get("date"),
        "overall_status": status.get("overallStatus"),
    }


def classify_change(change_date: str, primary_comp: str | None, results_post: str | None) -> str:
    """Return 'A_amendment' | 'B_between' | 'C_results_reporting' | 'unknown'."""
    cd = parse_date(change_date)
    pc = parse_date(primary_comp)
    rp = parse_date(results_post)
    if cd is None:
        return "unknown"
    if pc and cd < pc:
        return "A_amendment"
    # change is on/after primary completion
    if rp is None:
        return "B_between"  # no results posted → change after completion is limbo
    # within 30d of results posting = C
    days_to_post = (rp - cd).days
    if -30 <= days_to_post <= 30:
        return "C_results_reporting"
    if cd < rp:
        return "B_between"
    return "C_post_results"


def audit_refined(nct: str) -> dict:
    hist = history(nct)
    if not hist:
        return {"nct": nct, "error": "no history"}

    meta = fetch_meta(nct)

    outcome_vs = [
        c["version"] for c in hist
        if any("Outcome" in lab for lab in (c.get("moduleLabels") or []))
    ]
    sample_v = sorted({0, *outcome_vs, hist[-1]["version"]})

    data = {}
    for v in sample_v:
        d = version(nct, v)
        if d is None:
            continue
        data[v] = {
            "date": next((c["date"] for c in hist if c["version"] == v), None),
            "primary": extract_primary(d),
        }
        time.sleep(0.08)

    versions_sorted = sorted(data.keys())
    diffs = []
    for i in range(1, len(versions_sorted)):
        va, vb = versions_sorted[i - 1], versions_sorted[i]
        d = meaningful_diff(data[va]["primary"], data[vb]["primary"])
        if not d["meaningful"]:
            continue
        window = classify_change(
            data[vb]["date"],
            meta.get("primary_completion"),
            meta.get("results_first_post"),
        )
        diffs.append({
            "from_v": va, "to_v": vb,
            "from_date": data[va]["date"], "to_date": data[vb]["date"],
            "window": window,
            "added": d["added"], "removed": d["removed"],
            "old_count": d["old_count"], "new_count": d["new_count"],
        })

    n_A = sum(1 for d in diffs if d["window"] == "A_amendment")
    n_B = sum(1 for d in diffs if d["window"] == "B_between")
    n_C = sum(1 for d in diffs if d["window"] == "C_results_reporting")
    n_post = sum(1 for d in diffs if d["window"] == "C_post_results")

    return {
        "nct": nct,
        "sponsor": meta.get("sponsor"),
        "title": meta.get("title"),
        "conditions": meta.get("conditions"),
        "enroll": meta.get("enroll"),
        "primary_completion": meta.get("primary_completion"),
        "results_first_post": meta.get("results_first_post"),
        "total_versions": len(hist),
        "n_meaningful_changes": len(diffs),
        "n_A_amendment": n_A,
        "n_B_between": n_B,
        "n_C_results_reporting": n_C,
        "n_C_post_results": n_post,
        "changes": diffs,
    }


def main(n: int = 500):
    print(f"Fetching {n} Phase 3 industry-sponsored trials...")
    ncts = fetch_phase3_ncts(n)
    print(f"Got {len(ncts)} NCTs")
    print()

    results = []
    for i, nct in enumerate(ncts):
        try:
            r = audit_refined(nct)
            tag = ""
            if r.get("n_B_between", 0) > 0:
                tag = " 🚩 B-WINDOW"
            print(f"[{i+1:>3}/{len(ncts)}] {nct}  "
                  f"v={r.get('total_versions','?'):>3}  "
                  f"chg={r.get('n_meaningful_changes',0)}  "
                  f"A={r.get('n_A_amendment',0)} B={r.get('n_B_between',0)} C={r.get('n_C_results_reporting',0)}{tag}")
            results.append(r)
        except Exception as e:
            print(f"[{i+1:>3}/{len(ncts)}] {nct}  ERROR {e}")
            results.append({"nct": nct, "error": str(e)})
        time.sleep(0.1)

    with open("round23_refined_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    # summary
    n_ok = [r for r in results if not r.get("error")]
    n_any = [r for r in n_ok if r.get("n_meaningful_changes", 0) > 0]
    n_A = [r for r in n_ok if r.get("n_A_amendment", 0) > 0]
    n_B = [r for r in n_ok if r.get("n_B_between", 0) > 0]
    n_C = [r for r in n_ok if r.get("n_C_results_reporting", 0) > 0]

    print()
    print("=" * 60)
    print(f"Audited trials (valid):     {len(n_ok)}")
    print(f"Any meaningful change:      {len(n_any)}  ({len(n_any)/max(1,len(n_ok))*100:.1f}%)")
    print(f"A (pre-completion amendmt): {len(n_A)}")
    print(f"B (BETWEEN window — 🚩):    {len(n_B)}  ({len(n_B)/max(1,len(n_ok))*100:.2f}%)")
    print(f"C (at results reporting):   {len(n_C)}")

    # sponsor scorecard on B hits
    if n_B:
        print()
        print("B-WINDOW HITS (data locked, spec still changing before results posted):")
        for r in n_B:
            print(f"  {r['nct']}  [{r.get('sponsor') or '?'}]")
            print(f"    title: {(r.get('title') or '')[:100]}")
            print(f"    primary_completion: {r.get('primary_completion')}  results_first_post: {r.get('results_first_post')}")
            for c in r["changes"]:
                if c["window"] == "B_between":
                    print(f"    change {c['from_date']} → {c['to_date']}:")
                    for a in c["added"][:3]:
                        print(f"      + {a[:110]}")
                    for rm in c["removed"][:3]:
                        print(f"      - {rm[:110]}")

    # sponsor leaderboard across all B-window hits
    sponsor_B_counts = Counter()
    sponsor_total_counts = Counter()
    for r in n_ok:
        sp = r.get("sponsor") or "?"
        sponsor_total_counts[sp] += 1
        if r.get("n_B_between", 0) > 0:
            sponsor_B_counts[sp] += 1
    print()
    print("Top-10 sponsors in audit (any B-window hits):")
    for sp, c in sponsor_B_counts.most_common(10):
        print(f"  {c:>2} B-hit / {sponsor_total_counts[sp]:>3} trials  {sp}")

    print()
    print("Saved -> round23_refined_results.json")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    main(n)
