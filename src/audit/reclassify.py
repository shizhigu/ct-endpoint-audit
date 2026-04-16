"""
Apply critic's fix #2: reclassify using results_first_submitted as
anchor, not results_first_posted. Widen C-window to cover admin-lag
amendments (changes between primary_completion and results_first_submitted
that are within 60 days of submission are benign).

New classification:
  A = change_date < primary_completion (amendment during trial)
  B = primary_completion ≤ change_date < (results_first_submitted - 7d)
      → truly locked data with specification still changing
  C = (results_first_submitted - 7d) ≤ change_date ≤ (results_first_posted + 30d)
      → results-reporting phase, benign admin

If results_first_submitted is unavailable, approximate as
results_first_posted - 45d (rough median for CT.gov review queue).
"""

import json
import urllib.request
import urllib.parse
import time
from datetime import datetime, timedelta


V2 = "https://clinicaltrials.gov/api/v2/studies"


def parse_date(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            return datetime.strptime(s, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def fetch_submitted(nct):
    """Fetch results_first_submitted via V2."""
    url = f"{V2}/{nct}?fields=ResultsFirstSubmitDate,ResultsFirstPostDate"
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            d = json.loads(r.read())
        status = d.get("protocolSection", {}).get("statusModule", {}) or {}
        return {
            "results_first_submitted": status.get("resultsFirstSubmitDate"),
            "results_first_post": (status.get("resultsFirstPostDateStruct", {}) or {}).get("date"),
        }
    except Exception:
        return None


def reclassify(hit):
    """Given a B-window hit from R23, reclassify using new criteria."""
    nct = hit["nct"]
    meta = fetch_submitted(nct)
    if meta is None:
        return None
    rfs = parse_date(meta.get("results_first_submitted"))
    rfp = parse_date(meta.get("results_first_post"))
    pc = parse_date(hit.get("primary_completion"))

    # For each change in this hit
    out = {"nct": nct, "sponsor": hit.get("sponsor"),
           "primary_completion": hit.get("primary_completion"),
           "results_first_submitted": str(rfs) if rfs else None,
           "results_first_post": str(rfp) if rfp else None,
           "changes_v2": []}

    for c in hit.get("changes", []):
        cd = parse_date(c.get("to_date"))
        if cd is None:
            continue
        # Approximate rfs if missing: rfp - 45d
        rfs_eff = rfs if rfs else (rfp - timedelta(days=45) if rfp else None)
        # New window boundaries
        if pc and cd < pc:
            window = "A_amendment"
        elif rfs_eff and cd >= rfs_eff - timedelta(days=7) and (not rfp or cd <= rfp + timedelta(days=30)):
            window = "C_results_reporting_v2"
        elif pc and cd >= pc and (not rfs_eff or cd < rfs_eff - timedelta(days=7)):
            window = "B_between_v2"
        elif rfp and cd > rfp + timedelta(days=30):
            window = "D_post_results"
        else:
            window = "unknown"
        out["changes_v2"].append({
            "to_date": c.get("to_date"),
            "old_window": c.get("window"),
            "new_window": window,
            "rfs_effective": str(rfs_eff) if rfs_eff else None,
        })
    return out


def main():
    with open("round23_refined_results.json") as f:
        rs = json.load(f)
    hits = [r for r in rs if r.get("n_B_between", 0) > 0]
    print(f"Reclassifying {len(hits)} R23 B-window hits with v2 criteria...")
    print()
    results = []
    old_b_count = 0
    new_b_count = 0
    reclassified_c = 0
    for hit in hits:
        r = reclassify(hit)
        if r is None:
            continue
        results.append(r)
        for c in r["changes_v2"]:
            if c["old_window"] == "B_between":
                old_b_count += 1
                if c["new_window"] == "B_between_v2":
                    new_b_count += 1
                elif c["new_window"] == "C_results_reporting_v2":
                    reclassified_c += 1
        time.sleep(0.2)

    print(f"Total R23 B-window changes: {old_b_count}")
    print(f"Remain B under v2 criteria:  {new_b_count}")
    print(f"Reclassified to C (benign):  {reclassified_c}")
    print()
    print("Per-trial v2 status:")
    for r in results:
        nb = sum(1 for c in r["changes_v2"] if c["new_window"] == "B_between_v2")
        nc = sum(1 for c in r["changes_v2"] if c["new_window"] == "C_results_reporting_v2")
        tag = " 🚩 STILL B" if nb > 0 else " → benign"
        print(f"  {r['nct']} [{r.get('sponsor','?')}]  rfs={r.get('results_first_submitted') or '(approx)'}  B={nb} C={nc}{tag}")

    with open("r23_reclassified_v2.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print()
    print("Saved -> r23_reclassified_v2.json")


if __name__ == "__main__":
    main()
