"""Unit tests for primary-outcome change classifier.

Tests cover normalisation, token content extraction, Jaccard +
superstring-containment "same measure" detection, and the meaningful-
diff logic.
"""
from src.audit.classifier import (
    normalize,
    content_tokens,
    jaccard,
    is_cosmetic_superstring,
    meaningful_diff,
)


def test_normalize_lowercases_and_strips_brackets():
    assert normalize("Change From Baseline in CDR-SB Score") == (
        "clinical dementia rating sum of boxes score"
    )
    # parens kept as separators
    assert "cmax" in normalize("Cmax (pharmacokinetic parameter)")


def test_normalize_expands_common_abbreviations():
    # ALSFRS-R is expanded
    n = normalize("ALSFRS-R score at week 48")
    assert "amyotrophic" in n
    assert "rating" in n


def test_content_tokens_excludes_stopwords():
    tokens = content_tokens("Number of participants with CDR-SB change")
    assert "number" not in tokens  # stopword
    assert "participants" not in tokens  # stopword
    assert "change" not in tokens  # stopword


def test_jaccard_identical_sets():
    assert jaccard({"a", "b", "c"}, {"a", "b", "c"}) == 1.0


def test_jaccard_disjoint():
    assert jaccard({"a"}, {"b"}) == 0.0


def test_jaccard_partial():
    assert jaccard({"a", "b"}, {"b", "c"}) == 1 / 3


def test_cosmetic_superstring_full_containment():
    short = {"cdr-sb"}
    long_ = {"cdr-sb", "score", "baseline", "week", "72"}
    assert is_cosmetic_superstring(short, long_) is True


def test_cosmetic_superstring_partial_fails():
    short = {"pfs", "progression"}
    long_ = {"os", "survival"}
    assert is_cosmetic_superstring(short, long_) is False


def test_meaningful_diff_identical_outcomes_no_change():
    old = [{"measure": "Change from baseline in CDR-SB score at week 72"}]
    new = [{"measure": "Change From Baseline in CDR-SB Score at Week 72"}]
    d = meaningful_diff(old, new)
    assert d["meaningful"] is False
    assert d["added"] == []
    assert d["removed"] == []


def test_meaningful_diff_pfs_to_os_flags():
    old = [{"measure": "Progression-free survival"}]
    new = [{"measure": "Overall survival"}]
    d = meaningful_diff(old, new)
    assert d["meaningful"] is True
    # PFS and OS share "survival" token - Jaccard ~0.33, should flag
    assert len(d["added"]) >= 1 or len(d["removed"]) >= 1


def test_meaningful_diff_adding_new_outcome_flags():
    old = [{"measure": "Overall survival at 24 months"}]
    new = [
        {"measure": "Overall survival at 24 months"},
        {"measure": "Progression-free survival at 12 months"},
    ]
    d = meaningful_diff(old, new)
    assert d["meaningful"] is True
    assert len(d["added"]) == 1
    assert d["old_count"] == 1
    assert d["new_count"] == 2


def test_meaningful_diff_count_change_without_text_shift_not_meaningful():
    # If same measure is listed twice (data quality quirk), count changes
    # but tokens are identical - classifier should NOT flag as meaningful
    old = [{"measure": "Change in CDR-SB score"}]
    new = [
        {"measure": "Change in CDR-SB score"},
        {"measure": "Change in CDR-SB Score at Week 72 — (cosmetic expansion)"},
    ]
    d = meaningful_diff(old, new)
    # The cosmetic expansion IS same measure per superstring rule
    assert d["meaningful"] is False
