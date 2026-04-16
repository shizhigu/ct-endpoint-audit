"""
Generate the two paper figures from the 1000-trial audit + v2 reclassifier
output.

Figure 1: histogram of (change_date - results_first_submitted) in days
          for all meaningful amendments across the 1000 trials. Highlights
          the submission-preparation cluster that makes the anchor choice
          load-bearing.

Figure 2: v1 vs v2 B-window rate bar chart with Wilson 95% CIs.

Both figures are rendered to paper/figures/ as vector PDFs with serif
fonts matching the LaTeX paper.
"""

import json
import sys
from datetime import datetime
from math import sqrt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ------------------ config ------------------
ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "paper" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Computer Modern Roman", "Times New Roman"],
    "font.size": 10,
    "axes.labelsize": 10,
    "axes.titlesize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.dpi": 120,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.03,
    "pdf.fonttype": 42,
})

ACCENT = "#2874A6"
BENIGN = "#7F8C8D"
FLAG = "#C0392B"


def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    spread = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0, center - spread), min(1, center + spread))


def parse_date(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    return None


# ------------------ figure 1 ------------------
def figure_1_distribution():
    """Distribution of change-date offsets from results_first_submitted."""
    # Use the R23 reclassified data (all v1 B-hits) for the distribution
    data_path = ROOT.parent / "round22_ctgov" / "r23_reclassified_v2.json"
    if not data_path.exists():
        # Try local copy
        data_path = ROOT / "data" / "r23_reclassified_v2.json"
    if not data_path.exists():
        print(f"WARNING: {data_path} not found; skipping figure 1")
        return

    with open(data_path) as f:
        rs = json.load(f)

    offsets = []
    labels = []
    for r in rs:
        rfs = parse_date(r.get("results_first_submitted"))
        if rfs is None:
            continue
        for c in r.get("changes_v2", []):
            cd = parse_date(c.get("to_date"))
            if cd is None:
                continue
            delta = (rfs - cd).days
            offsets.append(delta)
            labels.append(c.get("new_window", "?"))

    print(f"Figure 1: {len(offsets)} points to plot")

    fig, ax = plt.subplots(figsize=(6.5, 3.2))

    # Split into three categories for stacked histogram
    b_offsets = [o for o, l in zip(offsets, labels) if l == "B_between_v2"]
    c_offsets = [o for o, l in zip(offsets, labels) if l in ("C_results_reporting_v2", "C_post_results")]

    bins = list(range(-30, 1100, 30))
    ax.hist([b_offsets, c_offsets], bins=bins, stacked=True,
            label=["B-window (v2)", "C-window (benign)"],
            color=[FLAG, BENIGN], edgecolor="white", linewidth=0.4)
    ax.axvline(7, linestyle="--", linewidth=0.8, color=ACCENT,
               label="7-day buffer boundary")
    ax.set_xlabel("Days between amendment date and ResultsFirstSubmitDate")
    ax.set_ylabel("Number of amendments")
    ax.set_title("Distribution of post-completion amendment dates\n"
                 "relative to results submission (v1 B-window hits, n={})".format(len(offsets)))
    ax.legend(loc="upper right", frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(-30, 1100)

    out = FIG_DIR / "fig1_distribution.pdf"
    plt.savefig(out)
    plt.close()
    print(f"  saved -> {out}")


# ------------------ figure 2 ------------------
def figure_2_anchor_comparison():
    """Bar chart: v1 vs v2 B-window rate with Wilson CIs."""
    # Hardcoded from audit results
    N = 1000
    v1_k, v2_k = 115, 28

    v1_p = v1_k / N
    v2_p = v2_k / N
    v1_lo, v1_hi = wilson(v1_k, N)
    v2_lo, v2_hi = wilson(v2_k, N)

    fig, ax = plt.subplots(figsize=(5.8, 3.4))

    x = [0, 1]
    heights = [v1_p * 100, v2_p * 100]
    errs_lo = [(v1_p - v1_lo) * 100, (v2_p - v2_lo) * 100]
    errs_hi = [(v1_hi - v1_p) * 100, (v2_hi - v2_p) * 100]

    bars = ax.bar(x, heights,
                  color=[FLAG, ACCENT],
                  width=0.55,
                  edgecolor="black", linewidth=0.5,
                  yerr=[errs_lo, errs_hi],
                  capsize=6, ecolor="black")

    # Value labels on bars
    for xi, h, k in zip(x, heights, [v1_k, v2_k]):
        ax.text(xi, h + 1.0, f"{h:.1f}%\n({k}/{N})",
                ha="center", va="bottom", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels([
        "v1 anchor\n(ResultsFirstPostDate)",
        "v2 anchor\n(ResultsFirstSubmitDate)",
    ])
    ax.set_ylabel("B-window amendment rate (%)")
    ax.set_title("Anchor choice changes the estimated rate 4.1-fold\n"
                 "(same 1,000 Phase 3 industry trials)")
    ax.set_ylim(0, 18)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Annotation of ratio
    ax.annotate("",
                xy=(1, v2_p * 100 + 0.5),
                xytext=(0, v1_p * 100 + 0.5),
                arrowprops=dict(arrowstyle="->", color="black",
                                connectionstyle="arc3,rad=-0.25"))
    ax.text(0.5, 7.5, "4.1× reduction\n(87/115 reclassified as benign)",
            ha="center", va="center", fontsize=9, style="italic")

    out = FIG_DIR / "fig2_anchor_comparison.pdf"
    plt.savefig(out)
    plt.close()
    print(f"  saved -> {out}")


if __name__ == "__main__":
    figure_1_distribution()
    figure_2_anchor_comparison()
