"""
Detect if primary_completion_date was AMENDED across versions — the
critical critic #7 in critic_notes.md.

For each trial, pull primary_completion_date at each historical version;
if the date was pushed later by >30 days, flag it. If the completion
date was pushed later by >180 days AFTER the original completion would
have passed, that's a strong manipulation signal.
"""

import json
import time
from audit_batch import history, version, get_json


def completion_at_version(ver_doc: dict) -> str | None:
    if not ver_doc:
        return None
    p = ver_doc.get("study", {}).get("protocolSection", {})
    status = p.get("statusModule", {}) or {}
    return (
        (status.get("primaryCompletionDateStruct", {}) or {}).get("date")
        or (status.get("completionDateStruct", {}) or {}).get("date")
    )


def completion_drift(nct: str) -> dict:
    hist = history(nct)
    if not hist:
        return {"nct": nct, "error": "no history"}

    # sample versions where StatusModule / StudyStatus was touched
    status_versions = [
        c["version"] for c in hist
        if any("Status" in lab for lab in (c.get("moduleLabels") or []))
    ]
    sample = sorted({0, *status_versions, hist[-1]["version"]})

    date_trace = []
    for v in sample:
        d = version(nct, v)
        cd = completion_at_version(d)
        v_date = next((c["date"] for c in hist if c["version"] == v), None)
        date_trace.append({"v": v, "version_date": v_date, "primary_completion": cd})
        time.sleep(0.08)

    # detect amendments
    amendments = []
    prev_cd = None
    for entry in date_trace:
        cd = entry["primary_completion"]
        if cd is None:
            continue
        if prev_cd and cd != prev_cd:
            amendments.append({
                "from_date": prev_cd, "to_date": cd,
                "changed_in_v": entry["v"], "changed_on": entry["version_date"],
            })
        prev_cd = cd

    # classify amendments: pushed later / earlier
    from datetime import datetime
    def to_dt(s):
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            return None

    pushed_later = 0
    for am in amendments:
        a, b = to_dt(am["from_date"]), to_dt(am["to_date"])
        if a and b and (b - a).days > 30:
            pushed_later += 1

    # most suspicious pattern: original completion date was in the past when it was changed
    suspicious_pushes = []
    for am in amendments:
        from_dt = to_dt(am["from_date"])
        change_dt = to_dt(am["changed_on"])
        to_dt_ = to_dt(am["to_date"])
        if from_dt and change_dt and to_dt_:
            # amendment happened after the original completion date
            if change_dt > from_dt and (to_dt_ - from_dt).days > 30:
                suspicious_pushes.append(am)

    return {
        "nct": nct,
        "n_completion_amendments": len(amendments),
        "n_pushed_later_30d": pushed_later,
        "n_suspicious_pushes": len(suspicious_pushes),
        "amendments": amendments,
        "suspicious_pushes": suspicious_pushes,
        "final_completion": prev_cd,
    }


if __name__ == "__main__":
    import sys
    ncts = sys.argv[1:] or [
        "NCT02477800",  # Aduhelm EMERGE — known terminated early
        "NCT04991935",  # Celgene CC-93538
        "NCT04006457",  # Pfizer alopecia
        "NCT04368728",  # R23 hit
    ]
    for nct in ncts:
        r = completion_drift(nct)
        print(f"\n=== {nct} ===")
        print(f"  final_completion: {r.get('final_completion')}")
        print(f"  n_amendments: {r.get('n_completion_amendments')}  pushed_later>30d: {r.get('n_pushed_later_30d')}  suspicious: {r.get('n_suspicious_pushes')}")
        for am in r.get("amendments", [])[:5]:
            print(f"    {am['from_date']} → {am['to_date']}   (changed v{am['changed_in_v']} on {am['changed_on']})")
        if r.get("suspicious_pushes"):
            print("  🚩 SUSPICIOUS PUSHES (changed after original completion date had passed):")
            for am in r["suspicious_pushes"]:
                print(f"    {am['from_date']} → {am['to_date']}   (changed {am['changed_on']})")
