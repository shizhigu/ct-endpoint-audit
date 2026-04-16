# Abstract — paper 2, v2 after critic review

## Title (revised per critic feedback)

The Choice of Data-Lock Anchor Changes Estimated Post-Completion
Endpoint-Amendment Rates 4-fold on ClinicalTrials.gov:
A Methodological Note With a Reusable Pipeline

## Abstract (~280 words)

**Background.** Prior audits of ClinicalTrials.gov (CT.gov) (Goldacre
et al. 2019, Chen et al. 2019) quantify outcome reporting between
registration and publication. Few have systematically examined when,
relative to trial data-lock, primary-outcome text changes occur in
the registration itself. This choice of temporal anchor directly
affects any prevalence estimate.

**Objective.** Quantify how the choice of data-lock anchor
(`results_first_posted` vs `results_first_submitted`) affects the
estimated rate of "post-completion" primary-endpoint amendments in
Phase 3 industry-sponsored trials.

**Methods.** We sampled the 1{,}000 most-recently-updated COMPLETED or
TERMINATED Phase 3 industry-sponsored trials (enrolment ≥300) on
CT.gov (queried April 2026). For each trial, we retrieved the
complete version history via CT.gov's internal history API (an
endpoint that mirrors what AACT provides in aggregated form, but
enables live per-trial querying without a database clone) and
classified every meaningful primary-outcome amendment into three
temporal windows relative to `primary_completion_date` and the chosen
data-lock anchor. Similarity thresholds (token Jaccard ≥ 0.5;
token-superstring ≥ 0.75) were applied uniformly.

**Results.** 275/1000 trials (27.5%, 95% CI 24.8–30.4%) had at least
one meaningful primary-outcome amendment. Classified against
`results_first_posted`, 115/1000 (11.5%, 95% CI 9.6–13.7%) fell in
the naïve "post-completion" window. Replacing the anchor with
`results_first_submitted` reduced this to 28/1000 (2.8%, 95% CI
1.9–4.1%) — a **4.1-fold** reduction attributable entirely to
anchor choice. Independent case-study verification of three
high-profile trials (Tanabe oral edaravone, Merck pembrolizumab-
vibostolimab, PTC ataluren) illustrated that registry text-level
audits are a **lower bound**: they miss manipulation at the
statistical-analysis-plan level (demonstrated by PTC's
population-switch to ITT, which preceded FDA NDA withdrawal
Feb 2026).

**Conclusions.** Future systematic audits of CT.gov should use
`results_first_submitted` as the data-lock anchor. Registry
text audits capture only text-level endpoint changes and
should not be interpreted as comprehensive manipulation
detection; SAP-level auditing via FDA briefing documents is
complementary. We release the pipeline to enable replication
and extension.

## Keywords

clinical-trial integrity; outcome switching; ClinicalTrials.gov;
registry methodology; statistical analysis plan; systematic audit

## Changes from v1 abstract (critic-driven)

- **Title**: removed "Most...Are Administrative Lag, Not Manipulation"
  (tautological; unearned without rater adjudication)
- **Framing**: measurement paper on anchor choice, NOT integrity
  paper claiming manipulation rate
- **"Undocumented API" claim**: demoted; AACT comparison explicit
- **PTC case study**: reframed as "registry audits are floor, not
  ceiling" — consistent with claim that text audits underestimate
- **CIs added** for all percentages (Wilson 95% CI)
- **Roche sponsor finding**: removed (CI overlaps base rate)
- **Generalizability**: confined to sampled population
  (recently-updated recent trials, not "Phase 3 industry trials")
