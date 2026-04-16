"""
Spot-check that the internal history endpoint's LATEST version agrees
with what the public v2 API returns for the same trial. This validates
the Methods claim that the internal endpoint exposes the same data
the public system has.

We cannot easily check AACT without Postgres setup, but this test
establishes the equivalent property: the internal endpoint is not
returning stale or divergent data relative to the public v2 API.
"""

import json
import pytest
import urllib.parse
import urllib.request


INT_BASE = "https://clinicaltrials.gov/api/int/studies"
V2_BASE = "https://clinicaltrials.gov/api/v2/studies"


def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ct-audit-test/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _primary_measures(study_doc):
    """Extract list of primaryOutcomes.measure strings from a CT.gov response."""
    ps = study_doc.get("protocolSection") or study_doc.get("study", {}).get("protocolSection", {})
    return [
        (o.get("measure") or "").strip()
        for o in (ps.get("outcomesModule", {}) or {}).get("primaryOutcomes", []) or []
    ]


@pytest.mark.parametrize(
    "nct",
    [
        "NCT04006457",  # Pfizer alopecia
        "NCT04991935",  # Celgene eosinophilic esophagitis
        "NCT03179631",  # PTC ataluren
        "NCT04738487",  # Merck KEYVIBE-003
        "NCT02477800",  # Aduhelm EMERGE
    ],
)
def test_internal_latest_matches_v2_public(nct):
    """The internal endpoint's latest version must match the v2 public API."""
    # Get latest version number from internal history
    hist = _fetch(f"{INT_BASE}/{nct}/history")
    last_v = hist["changes"][-1]["version"]
    internal = _fetch(f"{INT_BASE}/{nct}/history/{last_v}")

    # Get v2 public API current record
    v2 = _fetch(f"{V2_BASE}/{nct}?fields=OutcomesModule")

    int_measures = sorted(_primary_measures(internal))
    v2_measures = sorted(_primary_measures(v2))

    assert int_measures == v2_measures, (
        f"Primary-outcome mismatch for {nct}:\n"
        f"  internal latest: {int_measures}\n"
        f"  v2 public API:   {v2_measures}"
    )
