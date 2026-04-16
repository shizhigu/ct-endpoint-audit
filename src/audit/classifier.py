"""
Core change-detection primitives for the CT.gov primary-endpoint audit.

  - Canonicalize outcomes: lowercase, strip brackets as separators,
    retain parenthetical abbreviations, expand a small dictionary of
    field-specific acronyms
  - Token Jaccard similarity: pairs with >= 0.5 considered same measure
  - Token superstring containment: if >= 75% of one measure's content
    tokens appear in the other, considered same measure (handles
    cosmetic expansion like "PFS" -> "progression free survival
    per RECIST 1.1")
  - "Meaningful change" requires >= 1 text add or remove after
    normalisation; raw count changes without text shift are NOT counted

Temporal A/B/C classification lives in `batch_audit.py`.
"""

import json
import re
import time
import urllib.parse
import urllib.request
from collections import Counter

BASE = "https://clinicaltrials.gov/api/int/studies"
V2_BASE = "https://clinicaltrials.gov/api/v2/studies"


def get_json(url: str, retries: int = 2) -> dict | None:
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ctgov-audit/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            if i == retries:
                return None
            time.sleep(1.0)
    return None


# ---------- normalization ----------
STOP_PREFIXES = [
    "change from baseline in ",
    "change from baseline of ",
    "change in ",
    "mean change in ",
    "mean change from baseline in ",
    "percent change from baseline in ",
    "absolute change from baseline in ",
    "time to ",
    "number of ",
    "incidence of ",
    "proportion of participants with ",
    "proportion of subjects with ",
    "percentage of participants with ",
    "percentage of subjects with ",
]

CDR_EXPAND = {
    "cdr-sb": "clinical dementia rating sum of boxes",
    "adas-cog": "alzheimer disease assessment scale cognitive",
    "alsfrs-r": "amyotrophic lateral sclerosis functional rating scale revised",
    "pfs": "progression free survival",
    "os": "overall survival",
    "orr": "objective response rate",
    "dor": "duration of response",
    "panss": "positive and negative syndrome scale",
    "madrs": "montgomery asberg depression rating scale",
    "hamd": "hamilton depression rating scale",
    "ham-d": "hamilton depression rating scale",
}

TOKEN_RE = re.compile(r"[a-z0-9]+")


def normalize(text: str) -> str:
    t = text.lower().strip()
    # keep parenthetical abbreviations (e.g., "(Cmax)" is meaningful); just remove brackets
    t = re.sub(r"[()\[\]]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    # strip common prefixes
    for p in STOP_PREFIXES:
        if t.startswith(p):
            t = t[len(p):]
            break
    # expand known abbreviations so short/long forms match
    for short, full in CDR_EXPAND.items():
        t = re.sub(rf"\b{re.escape(short)}\b", full, t)
    return t


def tokens(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower()))


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b) if (a | b) else 0.0


STOPWORDS = {
    "of", "the", "in", "to", "at", "a", "an", "and", "or", "for", "with",
    "by", "on", "over", "from", "is", "are", "was", "were", "be", "as",
    "time", "change", "number", "score", "measure", "measured",
    "participants", "subjects", "patients", "study", "core", "extension",
    "phase", "week", "weeks", "month", "months", "day", "days", "baseline",
}


def content_tokens(text: str) -> set[str]:
    return {t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS and len(t) > 2}


def outcome_fingerprint(o: dict) -> tuple[str, set[str]]:
    text = normalize(o.get("measure", ""))
    return text, content_tokens(text)


def is_cosmetic_superstring(short_tokens: set[str], long_tokens: set[str]) -> bool:
    """True if short is fully contained in long (i.e., long is cosmetic expansion of short)."""
    if not short_tokens:
        return False
    overlap = short_tokens & long_tokens
    return len(overlap) / len(short_tokens) >= 0.75


def meaningful_diff(old: list[dict], new: list[dict]) -> dict:
    """Return added_new, removed_old, count_changed.

    A pair of measures is treated as 'same' if either:
      - Jaccard(content_tokens) >= 0.5, OR
      - one is a token-superset of the other (>=75% content tokens shared)
    """
    old_fp = [outcome_fingerprint(o) for o in old]
    new_fp = [outcome_fingerprint(o) for o in new]

    def find_match(target_tokens, candidates):
        for text, cand_tokens in candidates:
            if jaccard(target_tokens, cand_tokens) >= 0.5:
                return True
            if is_cosmetic_superstring(target_tokens, cand_tokens):
                return True
            if is_cosmetic_superstring(cand_tokens, target_tokens):
                return True
        return False

    added = []
    for nf in new_fp:
        if not find_match(nf[1], old_fp):
            added.append(nf[0])
    removed = []
    for of in old_fp:
        if not find_match(of[1], new_fp):
            removed.append(of[0])

    count_changed = len(old) != len(new)
    meaningful = bool(added or removed)  # raw count change alone not enough
    return {
        "meaningful": meaningful,
        "added": added,
        "removed": removed,
        "old_count": len(old),
        "new_count": len(new),
    }


# ---------- API wrappers ----------
def history(nct: str) -> list[dict]:
    d = get_json(f"{BASE}/{nct}/history")
    if d is None:
        return []
    return d.get("changes", [])


def version(nct: str, v: int) -> dict | None:
    return get_json(f"{BASE}/{nct}/history/{v}")


def extract_primary(ver: dict) -> list[dict]:
    if not ver:
        return []
    return (
        ver.get("study", {})
        .get("protocolSection", {})
        .get("outcomesModule", {})
        .get("primaryOutcomes", [])
        or []
    )


def extract_completion(ver: dict) -> str | None:
    if not ver:
        return None
    status = (
        ver.get("study", {}).get("protocolSection", {}).get("statusModule", {}) or {}
    )
    pcd = status.get("primaryCompletionDateStruct", {}) or {}
    cd = status.get("completionDateStruct", {}) or {}
    return pcd.get("date") or cd.get("date")


# ---------- audit a single NCT ----------
def audit(nct: str) -> dict:
    hist = history(nct)
    if not hist:
        return {"nct": nct, "error": "no history", "n_changes": 0}

    outcome_versions = [
        c["version"] for c in hist
        if any("Outcome" in lab for lab in (c.get("moduleLabels") or []))
    ]

    # Sample: v0, every outcome-touching version, and last
    sample_v = sorted({0, *outcome_versions, hist[-1]["version"]})

    # Fetch
    data = {}
    for v in sample_v:
        d = version(nct, v)
        if d is None:
            continue
        data[v] = {
            "date": next((c["date"] for c in hist if c["version"] == v), None),
            "primary": extract_primary(d),
            "completion": extract_completion(d),
            "status": next((c.get("status") for c in hist if c["version"] == v), None),
        }
        time.sleep(0.1)

    # Consecutive diffs
    versions_sorted = sorted(data.keys())
    diffs = []
    for i in range(1, len(versions_sorted)):
        va, vb = versions_sorted[i - 1], versions_sorted[i]
        d = meaningful_diff(data[va]["primary"], data[vb]["primary"])
        if d["meaningful"]:
            post_completion = False
            comp = data[vb]["completion"]
            if comp and data[vb]["date"] >= comp:
                post_completion = True
            diffs.append({
                "from_v": va,
                "to_v": vb,
                "from_date": data[va]["date"],
                "to_date": data[vb]["date"],
                "status_at_change": data[vb]["status"],
                "completion_at_change": comp,
                "post_completion": post_completion,
                **d,
            })

    return {
        "nct": nct,
        "total_versions": len(hist),
        "outcome_touching_versions": len(outcome_versions),
        "meaningful_changes": diffs,
        "n_meaningful_changes": len(diffs),
        "n_post_completion_changes": sum(1 for d in diffs if d["post_completion"]),
        "initial_primary": [o.get("measure") for o in data[versions_sorted[0]]["primary"]],
        "final_primary": [o.get("measure") for o in data[versions_sorted[-1]]["primary"]],
    }


# ---------- batch ----------
def batch(ncts: list[str]) -> list[dict]:
    results = []
    for i, nct in enumerate(ncts):
        print(f"[{i+1}/{len(ncts)}] {nct} ...", end=" ", flush=True)
        try:
            r = audit(nct)
            print(f"ver={r.get('total_versions','?')}  changes={r.get('n_meaningful_changes','?')}  post_comp={r.get('n_post_completion_changes','?')}")
            results.append(r)
        except Exception as e:
            print(f"ERROR {e}")
            results.append({"nct": nct, "error": str(e)})
        time.sleep(0.3)
    return results


if __name__ == "__main__":
    import sys
    ncts = sys.argv[1:]
    if not ncts:
        # High-profile recent Phase 3 trials for methodology validation
        ncts = [
            "NCT02477800",  # Aduhelm EMERGE
            "NCT02484547",  # Aduhelm ENGAGE
            "NCT04372277",  # Leqembi Clarity AD
            "NCT02913417",  # Cassava Sciences simufilam Phase 2 RETHINK-ALZ
            "NCT04994483",  # Cassava simufilam Phase 3 RETHINK-ALZ
            "NCT05026177",  # Cassava simufilam Phase 3 REFOCUS-ALZ
            "NCT03887455",  # Donanemab TRAILBLAZER-ALZ
            "NCT05429528",  # Donanemab TRAILBLAZER-ALZ 4
            "NCT02759419",  # Niraparib NOVA (ovarian)
            "NCT03406507",  # Tofersen VALOR (SOD1 ALS)
        ]
    results = batch(ncts)
    out_path = "batch_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print()
    print(f"=== SUMMARY of {len(results)} NCTs ===")
    for r in results:
        if r.get("error"):
            continue
        print(f"  {r['nct']}  vers={r['total_versions']}  meaningful={r['n_meaningful_changes']}  post_completion={r['n_post_completion_changes']}")
    print()
    print(f"Saved -> batch_results.json")
