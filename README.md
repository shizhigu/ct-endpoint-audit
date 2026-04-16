# ct-endpoint-audit

**Audit ClinicalTrials.gov primary-endpoint amendments via the platform's internal version-history API.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-17%20passing-brightgreen)](./tests)

---

## TL;DR

A reusable pipeline that audits primary-outcome amendments in `ClinicalTrials.gov` registrations via the platform's `api/int/studies/{NCT}/history` endpoint. The audit of 1,000 Phase 3 industry-sponsored trials revealed:

- **27.5%** had at least one meaningful primary-outcome amendment
- **11.5%** flagged as "post-completion" using a naïve `ResultsFirstPostDate` anchor (95% CI 9.7–13.6%)
- **2.8%** using the corrected `ResultsFirstSubmitDate` anchor (95% CI 1.9–4.0%)
- **The anchor choice alone causes a 4.1× difference** in the estimated rate
- Case-study verification shows registry text audits are a *lower bound*: they cannot detect statistical-analysis-plan manipulation (see PTC ataluren case)

## What this repository contains

- [`src/audit/`](./src/audit) — Python audit pipeline
    * `classifier.py` — primary-outcome change detection (Jaccard + token-superstring)
    * `batch_audit.py` — batch driver with A/B/C temporal classification
    * `reclassify.py` — apply `ResultsFirstSubmitDate` anchor to existing v1 results
    * `completion_drift.py` — detect historical amendments to `primary_completion_date`
- [`paper/`](./paper) — LaTeX source + compiled PDF of the methodology note
- [`tests/`](./tests) — 12 unit tests covering the classifier
- [`docs/`](./docs) — background documentation

## Quick start

```bash
# 1. Install
git clone https://github.com/shizhigu/ct-endpoint-audit
cd ct-endpoint-audit
pip install -e ".[dev]"

# 2. Run tests
pytest

# 3. Audit N trials
python -m src.audit.batch_audit 100

# 4. Apply v2 anchor to existing results
python -m src.audit.reclassify
```

## How it works

The `ClinicalTrials.gov` UI exposes a public "History of Changes" tab for every registered trial. That tab is powered by an internal endpoint that is not listed in the v2 API reference:

```
GET https://clinicaltrials.gov/api/int/studies/{NCT}/history
GET https://clinicaltrials.gov/api/int/studies/{NCT}/history/{version}
```

The same historical data is available in aggregated form through [AACT (CTTI)](https://aact.ctti-clinicaltrials.org/). This pipeline uses the internal endpoint directly, which enables targeted per-trial audit without setting up an AACT database clone.

For each trial we retrieve every version that touched the Outcome Measures module, compare adjacent primary-outcome lists using token-level similarity (Jaccard ≥ 0.5 OR token-superstring ≥ 0.75 = "same measure"), and classify each meaningful change into one of three temporal windows relative to primary completion and results submission.

## Key methodological finding

Using `ResultsFirstPostDate` ± 30 days as the benign-zone anchor misclassifies administrative rewording during the sponsor's results-submission preparation window (typically 30–120 days before posting) as "post-completion manipulation." Replacing the anchor with `ResultsFirstSubmitDate` reclassifies 75.7% of naïvely flagged cases as benign.

**Future systematic audits should report both anchor variants.**

## What registry audits cannot detect

The PTC ataluren (Duchenne muscular dystrophy) case study illustrates a fundamental limitation. Our classifier flagged a cosmetic primary-outcome text change. The actual manipulation in that trial was a statistical-analysis-plan population switch (pre-specified subgroup → ITT), invisible to registry text comparison but consequential enough to contribute to FDA withdrawal of the NDA resubmission on 13 February 2026.

**Text-level registry audits are a lower bound on manipulation. Complete detection requires access to SAP documents or FDA briefing materials.**

## Citation

```bibtex
@software{gu2026ct_endpoint_audit,
  author       = {Shizhi Gu},
  title        = {ct-endpoint-audit: An automated audit of primary-endpoint
                  amendments on ClinicalTrials.gov via the internal
                  version-history API},
  year         = {2026},
  version      = {1.0.0},
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.XXXXXXX},
}
```

## License

Code: [MIT](./LICENSE). Manuscript: CC-BY-4.0.

## Contact

Shizhi Gu — independent researcher. GitHub issues or shizhigu97@gmail.com.
