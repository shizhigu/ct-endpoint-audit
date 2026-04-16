# Paper 2 — structural outline v2 (post-critic)

Restructured after peer-review-style critic. Key changes:
- Title dropped "Most...Not Manipulation" (tautological)
- Demoted "undocumented API" to methods paragraph (AACT already exists)
- PTC case study reframed as "registry audits are FLOOR not CEILING"
- Dropped Roche sponsor finding (CI overlaps base rate)
- Added prior-work comparison (COMPare, AACT, Chen 2019, Cochrane OCS)
- Added Wilson CIs on every percentage

Venue target: Zenodo preprint (ready after writing). BMJ-EBM /
Drug Safety require further work (pre-registration, second rater,
random-sample replication).

## 1. Introduction (~700 words)

- Problem: outcome-switching in trial registration undermines
  trial-evidence credibility
- Prior work:
    * **Goldacre et al. 2019 (COMPare)** — manual comparison of
      67 trials, publication vs registration
    * **Chen et al. 2019** — JAMA analysis of registry changes
    * **Cochrane systematic review on outcome reporting bias**
    * **AACT database (CTTI, Duke)** — aggregated historical
      CT.gov data
    * **ICMJE 2005 / FDAAA 2007 Final Rule** — policy context
- Gap: prevalence estimates depend on the temporal anchor used,
  yet no prior work has quantified this dependency
- Contribution (3 items only):
    1. **Quantification of anchor-choice sensitivity**: 4.1-fold
       difference in estimated "post-completion amendment" rate
       between `results_first_posted` and `results_first_submitted`
       anchors, in a 1000-trial cohort
    2. **Reusable pipeline** released on GitHub, enabling
       live per-trial audit without AACT database dump (useful
       for targeted audits, not replacing AACT for systematic work)
    3. **Case-study illustration** that registry text-level audits
       systematically miss SAP-level manipulation (population
       switches, statistical method changes), demonstrated via
       PTC ataluren's FDA NDA withdrawal (Feb 2026)

## 2. Methods (~900 words)

### 2.1 Prior data sources and why another?
- AACT: authoritative, database clone, updated daily, full history
- ctti-clinicaltrials tooling: wraps AACT
- pytrials (PyPI): v1 API wrapper, no history
- Our pipeline: direct internal endpoint query for live,
  per-trial, no-setup audit (fits a different use case:
  journalistic or targeted investigation, not systematic)

### 2.2 Data source: CT.gov internal history API
- Endpoint: `api/int/studies/{NCT}/history` and
  `/history/{version}`
- Not in official v2 API docs but powers the public UI
- Returns `studyVersion`, `protocolSection`, `resultsSection`,
  `moduleLabels`, `date` per version
- Validation: spot-check against AACT for 5 trials; results match

### 2.3 Sampling
- N=1000 Phase 3 industry-sponsored trials
- Enrolment ≥ 300
- Status = COMPLETED or TERMINATED
- Sort: `LastUpdatePostDate:desc` (recency bias — see Limitations)
- Query: April 2026
- **Generalizability claim restricted to this exact population**,
  not "Phase 3 industry trials" globally

### 2.4 Primary-outcome change classifier
- Token normalization: lowercase, strip parens as separators, expand
  common abbreviations (CDR-SB, ALSFRS-R, PFS, OS, etc.)
- Similarity: Jaccard ≥ 0.5 OR token-superstring ≥ 0.75 → "same
  measure"
- Meaningful change if: (text add) OR (text remove)
- Thresholds NOT calibrated against ground-truth swap dataset —
  see Limitations

### 2.5 Temporal classification (v2, critic-fixed)
- A: change before `primary_completion_date`
- B: `primary_completion_date` ≤ change < (`results_first_submitted` − 7d)
- C: within ±30d of `results_first_submitted`
- D: beyond `results_first_posted + 30d`
- The 7d buffer is a **pragmatic convention** to avoid bordering
  single-day coincidences, not a policy-grounded threshold; see
  Limitations
- Both `results_first_posted` and `results_first_submitted`
  variants reported for reader comparison

### 2.6 Case-study verification protocol
- Top 3 candidates selected by prior journalistic interest
- For each: web search for published paper, FDA/EMA documents,
  press releases, independent commentary
- **Limitation**: single-rater, no blinded adjudication, no kappa —
  this is illustrative not representative

## 3. Results (~700 words)

### 3.1 Headline numbers (with Wilson 95% CI)

| | N | % | 95% CI |
|---|---|---|---|
| Any primary-outcome amendment | 275 | 27.5% | 24.8–30.3% |
| A (amendment pre-completion) | 132 | 13.2% | 11.2–15.4% |
| **B-window v1 (`posted` anchor)** | 115 | 11.5% | 9.7–13.6% |
| **B-window v2 (`submitted` anchor)** | **28** | **2.8%** | **1.9–4.0%** |
| C (results reporting rewording) | 83 | 8.3% | 6.7–10.2% |

**Anchor effect: 4.1× reduction (from 11.5% to 2.8%) purely from
changing the C-window anchor from `results_first_posted` to
`results_first_submitted`.**

### 3.2 Reclassification distribution
- Of 115 v1 B-hits, 87 (75.7%, 95% CI 66.9–82.6%) reclassify
  to C under v2
- Median time between change and `results_first_posted` for
  reclassified hits: [to compute]

### 3.3 Three case studies (illustrative, not representative)
- **NCT04569084 Tanabe oral edaravone** — registry ALSFRS-R→CAFS
  amendment 4 months after publication; both endpoints in paper
  failed; registry lag behind publication timing, no manipulation
- **NCT04738487 Merck pembrolizumab+vibostolimab (KEYVIBE-003)** —
  v45 registry listing (5 primaries) was erroneous; v136 corrected
  to match pre-specified protocol; trial later failed futility
  Dec 2024; entire vibostolimab program discontinued
- **NCT03179631 PTC ataluren** — my classifier flagged a
  cosmetic 1→4 primary-outcome expansion, but the REAL
  manipulation (population switch in SAP) was invisible to text
  comparison; FDA NDA withdrawn Feb 13, 2026

**Interpretation**: text-level audits are a LOWER BOUND on
manipulation; they cannot detect SAP-level changes. This is
the core limitation of any registry-text methodology.

## 4. Discussion (~500 words)

### 4.1 What this paper does and does not claim
- DOES claim: anchor choice matters 4-fold; most text changes
  near results posting are administrative; pipeline is useful
  for targeted audit
- DOES NOT claim: "manipulation rate" (unearned, needs rater
  adjudication); generalisable base rate (sample biased);
  sponsor-level culture effects (CIs too wide)

### 4.2 Relation to prior work
- COMPare (Goldacre 2019): manual paper-vs-registration compare;
  complementary to our registry-only analysis
- AACT (CTTI): same underlying data source, complementary
  infrastructure; our pipeline does not replace AACT for
  systematic work
- Chen 2019: similar registry-change focus, different era
  and sampling

### 4.3 Limitations (explicit)
- Sampling bias: `LastUpdatePostDate:desc` over-represents
  conscientious sponsors
- Single-rater case-study triage; no inter-rater kappa
- Similarity thresholds not calibrated against ground-truth
  swap dataset
- Primary completion date used is the current registered value,
  not the historical value at each amendment
- 7d B-window buffer is pragmatic, not policy-grounded
- CANNOT detect SAP-level manipulation; registry-text is one
  layer of several

### 4.4 Conclusion
- Report both anchor variants in future systematic audits
- Text-level registry audits are a lower bound; SAP-level audit
  is required for complete manipulation detection
- The pipeline we release is for targeted investigation, not as
  a replacement for AACT's systematic infrastructure

## 5. Data & code availability

- Pipeline: GitHub repo `shizhigu/ct-endpoint-audit`
- Audit outputs: JSON + CSV on Zenodo (DOI to mint)
- License: MIT (code), CC-BY-4.0 (manuscript)
