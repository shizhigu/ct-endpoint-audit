"""Generate supplementary table S1: all 28 v2 B-window trials.

LaTeX output written to paper/tables/supp_table_s1_b_window.tex.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "r23_reclassified_v2.json"
OUT = ROOT / "paper" / "tables" / "supp_table_s1_b_window.tex"
OUT.parent.mkdir(parents=True, exist_ok=True)


def latex_escape(s):
    if s is None:
        return ""
    s = str(s)
    return (s.replace("&", r"\&")
             .replace("%", r"\%")
             .replace("_", r"\_")
             .replace("#", r"\#"))


with open(DATA) as f:
    rs = json.load(f)

b_hits = []
for r in rs:
    if any(c.get("new_window") == "B_between_v2" for c in r.get("changes_v2", [])):
        b_change = next((c for c in r["changes_v2"] if c["new_window"] == "B_between_v2"), None)
        b_hits.append({
            "nct": r["nct"],
            "sponsor": r.get("sponsor") or "?",
            "primary_completion": r.get("primary_completion") or "-",
            "results_first_submitted": r.get("results_first_submitted") or "(none)",
            "change_date": b_change.get("to_date") if b_change else "-",
        })

# Sort by primary_completion desc
b_hits.sort(key=lambda x: x["primary_completion"] or "", reverse=True)

# LaTeX table using tabularx for proper column wrapping of sponsor names
with open(OUT, "w") as f:
    f.write(r"""% Supplementary Table S1
% Auto-generated from data/r23_reclassified_v2.json
\begin{table}[htbp]
\centering
\caption{Supplementary Table S1. The 28 trials flagged as B-window
(locked-data, pre-submission) under the refined anchor. Sorted by
primary completion date (most recent first). \emph{(none)} in the
\emph{Results-first submitted} column indicates results not yet
submitted at query time; such trials remain B-window candidates
pending future data.}\label{tab:s1}
\footnotesize
\begin{tabularx}{\textwidth}{@{}l L l l l@{}}
\toprule
NCT & Sponsor & Primary & Results-first & Change \\
    &         & completion & submitted & date \\
\midrule
""")
    for h in b_hits:
        row = (
            f"{latex_escape(h['nct'])} & "
            f"{latex_escape(h['sponsor'])} & "
            f"{latex_escape(h['primary_completion'])} & "
            f"{latex_escape(h['results_first_submitted'])} & "
            f"{latex_escape(h['change_date'])} \\\\\n"
        )
        f.write(row)
    f.write(r"""\bottomrule
\end{tabularx}
\end{table}
""")

print(f"Wrote {len(b_hits)} rows -> {OUT}")
