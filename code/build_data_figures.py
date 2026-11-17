"""Rebuild the five data-bearing figures of this paper from the committed CSVs.

Why this script exists (2026-09-10)
-----------------------------------
A traceability check written the same day
(``code/verify_figure_values.py``) found that five of the paper's six
data-bearing figures printed numbers that appear in no committed file, and in
two cases named datasets that this paper never used:

* ``paper2_parser_coverage_by_dataset_origin_style`` showed six datasets
  labelled Dielectric / Matbench-e / Concrete / Glass RI / AFLOW / ICSD-Doped
  with parse rates 94 / 96 / 91 / 87 / 82 / 78 per cent. The corpus is six
  matminer datasets (castelli_perovskites, dielectric_constant,
  double_perovskites_gap, phonon_dielectric_mp, piezoelectric_tensor,
  wolverton_oxides) and every one of them parses at 1.000 with zero failures.
  Four of the six names do not occur anywhere in this paper's data.
* ``paper2_element_coverage_origin_style`` showed a per-element "coverage rate"
  from 0.98 down to 0.43. No committed file defines such a quantity.
* ``paper2_formula_complexity_origin_style`` showed a density curve over
  0.1--3.5 bits peaking near 1.5. The committed ``composition_entropy`` column
  spans 0 to 1.609 bits with zero mass above 1.75.
* ``paper2_thesis_ratio_status_origin_style`` showed 58 / 21 / 15 / 6 per cent
  across four statuses and asserted a 6 per cent failure rate. The committed
  benchmark has six rows, four statuses, and no failures at all.
* ``paper2_thesis_mixture_atomic_fractions_origin_style`` showed O 0.514,
  Ba 0.142, Ti 0.142, C 0.146, Y 0.056. The committed values are O 0.598,
  Ba 0.198, Ti 0.198, C 0.004, Y 0.002.

The sixth, ``paper2_silent_mis_parse_origin_style``, was already generated from
its CSV by ``code/build_backend_comparison_figure.py`` and traced correctly.

Every number this script draws is read from a committed CSV. The element-count
figure additionally writes the counts it plots to
``data/processed_results/paper2_element_formula_counts.csv``, so that figure
traces to a file as well.

Style note: the retired figures were drawn through Visio COM automation
(``code/build_figures_visio.py``), which needs Visio and cannot run in a
headless environment. These replacements are matplotlib, so they do not match
the Visio house style of the two schematics. Correct numbers in a different
style were judged better than house-style numbers that do not exist; re-drawing
them in the house style is an author task and is recorded as one.

    python code/build_data_figures.py
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from composition_parser import parse_formula_with_backend  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = DATA / "processed_results"
FIG = ROOT / "figures"

INK = "#1F2933"
NAVY = "#1B4D89"
SLATE = "#5A7184"
AMBER = "#D08A3A"
ROSE = "#B33A3A"
GREEN = "#2E6F4E"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8.5,
    "axes.labelsize": 8.5,
    "axes.titlesize": 9.5,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.edgecolor": "#333333",
    "axes.linewidth": 0.8,
    "grid.color": "#DCE1E6",
    "grid.linewidth": 0.6,
    "pdf.fonttype": 42,
})

PRETTY = {
    "castelli_perovskites": "castelli\nperovskites",
    "dielectric_constant": "dielectric\nconstant",
    "double_perovskites_gap": "double\nperovskites gap",
    "phonon_dielectric_mp": "phonon\ndielectric mp",
    "piezoelectric_tensor": "piezoelectric\ntensor",
    "wolverton_oxides": "wolverton\noxides",
}


def _save(fig, stem: str) -> None:
    fig.savefig(FIG / (stem + ".pdf"), bbox_inches="tight")
    fig.savefig(FIG / (stem + ".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("wrote %s.pdf" % stem)


# --------------------------------------------------------------- parser coverage
def parser_coverage() -> None:
    df = pd.read_csv(DATA / "paper2_parser_source_coverage.csv")
    df = df.sort_values("total_unique_formulas", ascending=False).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    x = np.arange(len(df))
    bars = ax.bar(x, df["parsed_formulas"], color=NAVY, width=0.62, zorder=3)
    for b, n, rate, fail in zip(bars, df["parsed_formulas"],
                                df["parse_success_rate"], df["failed_formulas"]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.06,
                "%s\n%.3f" % (format(int(n), ","), rate),
                ha="center", va="bottom", fontsize=7.4, color=INK)
        assert int(fail) == 0 or rate < 1.0
    ax.set_xticks(x)
    ax.set_xticklabels([PRETTY.get(s, s) for s in df["source_dataset"]], fontsize=7)
    ax.set_yscale("log")
    ax.set_ylim(300, df["parsed_formulas"].max() * 3.2)
    ax.set_ylabel("Unique formulas parsed (log scale)")
    ax.set_title("Formula parse coverage by source dataset")
    ax.grid(axis="y", zorder=0)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.text(0.0, -0.30,
            "Count above each bar, parse-success rate below it. Every dataset "
            "parses at 1.000 with zero failures:\nthe corpus contains no decimal "
            "stoichiometry, so it cannot separate two parsers that differ only on it.",
            transform=ax.transAxes, ha="left", va="top", fontsize=6.8, color="#444444")
    _save(fig, "paper2_parser_coverage_by_dataset_origin_style")


# --------------------------------------------------------------- element coverage
def element_coverage(top: int = 14) -> None:
    complexity = pd.read_csv(DATA / "paper2_formula_complexity.csv")
    counts: Counter[str] = Counter()
    refused = 0
    for f in complexity["formula"].astype(str):
        try:
            amounts, _backend = parse_formula_with_backend(f)
        except Exception:  # noqa: BLE001
            refused += 1
            continue
        counts.update(amounts.keys())
    n_formulas = len(complexity)
    rows = [{"element": el, "formula_count": c,
             "fraction_of_corpus": c / n_formulas}
            for el, c in counts.most_common()]
    out = pd.DataFrame(rows)
    RESULTS.mkdir(parents=True, exist_ok=True)
    out.to_csv(RESULTS / "paper2_element_formula_counts.csv", index=False)
    print("wrote paper2_element_formula_counts.csv (%d elements, %d formulas "
          "refused)" % (len(out), refused))

    d = out.head(top)
    fig, ax = plt.subplots(figsize=(5.8, 3.1))
    x = np.arange(len(d))
    ax.bar(x, d["formula_count"], color=SLATE, width=0.66, zorder=3)
    for xi, (c, fr) in enumerate(zip(d["formula_count"], d["fraction_of_corpus"])):
        ax.text(xi, c + n_formulas * 0.015, "%s\n%.2f" % (format(int(c), ","), fr),
                ha="center", va="bottom", fontsize=6.8, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels(d["element"])
    ax.set_ylim(0, d["formula_count"].max() * 1.30)
    ax.set_ylabel("Formulas containing the element")
    ax.set_xlabel("Element")
    ax.set_title("Element coverage across the %s-formula corpus"
                 % format(n_formulas, ","))
    ax.grid(axis="y", zorder=0)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.text(0.0, -0.26,
            "Count above each bar, share of the corpus below it. The %d most "
            "frequent of %d elements present."
            % (top, len(out)),
            transform=ax.transAxes, ha="left", va="top", fontsize=6.8, color="#444444")
    _save(fig, "paper2_element_coverage_origin_style")


# -------------------------------------------------------------- formula complexity
def formula_complexity() -> None:
    d = pd.read_csv(DATA / "paper2_formula_complexity.csv")
    e = pd.to_numeric(d["composition_entropy"], errors="coerce").dropna().to_numpy()
    fig, ax = plt.subplots(figsize=(5.6, 3.0))
    bins = np.arange(0.0, e.max() + 0.1, 0.05)
    ax.hist(e, bins=bins, color=NAVY, edgecolor="white", linewidth=0.3, zorder=3)
    ax.set_xlim(-0.05, 1.75)
    ax.set_xlabel("Shannon composition entropy (nats, natural logarithm)")
    ax.set_ylabel("Formulas")
    ax.set_title("Composition entropy of the %s parsed formulas"
                 % format(len(d), ","))
    ax.grid(axis="y", zorder=0)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.axvline(float(np.median(e)), color=ROSE, lw=1.0, ls="--", zorder=4)
    ax.text(float(np.median(e)) + 0.02, ax.get_ylim()[1] * 0.92,
            "median %.3f" % np.median(e), color=ROSE, fontsize=7.2, ha="left")
    ax.text(0.0, -0.28,
            "Range %.3f to %.3f nats, mean %.3f. The distribution is bounded "
            "above by ln 5: no formula in this\ncorpus has more than five "
            "distinct elements, and %.1f%% have three or four."
            % (abs(e.min()), e.max(), e.mean(),
               100 * d["n_elements"].isin([3, 4]).mean()),
            transform=ax.transAxes, ha="left", va="top", fontsize=6.8, color="#444444")
    _save(fig, "paper2_formula_complexity_origin_style")


# ------------------------------------------------------------ thesis ratio status
def thesis_ratio_status() -> None:
    d = pd.read_csv(DATA / "paper2_thesis_ratio_expression_benchmark.csv")
    counts = d["parse_status"].value_counts()
    n = int(counts.sum())
    label = {
        "semantic_rule_extracted": "semantic rule\nextracted",
        "fully_normalized_expression_parsed": "fully normalized\nexpression parsed",
        "semantic_expression_extracted_with_ambiguity":
            "extracted with\nambiguity flag",
        "workflow_rule_extracted": "workflow rule\nextracted",
    }
    fig, ax = plt.subplots(figsize=(5.4, 3.0))
    x = np.arange(len(counts))
    colors = [GREEN if k == "fully_normalized_expression_parsed"
              else AMBER if "ambiguity" in k else SLATE for k in counts.index]
    ax.bar(x, counts.to_numpy(), color=colors, width=0.58, zorder=3)
    for xi, c in enumerate(counts.to_numpy()):
        ax.text(xi, c + 0.06, "%d of %d" % (c, n), ha="center", va="bottom",
                fontsize=7.6, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels([label.get(k, k) for k in counts.index], fontsize=7)
    ax.set_ylim(0, counts.max() + 0.9)
    ax.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(1))
    ax.set_ylabel("Expressions")
    ax.set_title("Parse status of the %d thesis-derived items" % n)
    ax.grid(axis="y", zorder=0)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.text(0.0, -0.30,
            "All %d expressions are accounted for and none fails outright. "
            "Counts, not percentages: %d expressions\nis far too few for a rate. "
            "Three are rule paragraphs carrying no complete formula instance."
            % (n, n),
            transform=ax.transAxes, ha="left", va="top", fontsize=6.8, color="#444444")
    _save(fig, "paper2_thesis_ratio_status_origin_style")


# ---------------------------------------------------------- thesis mixture fracs
def thesis_mixture() -> None:
    d = pd.read_csv(DATA / "paper2_thesis_normalized_mixture_atomic_fractions.csv")
    d = d.sort_values("atomic_fraction", ascending=False).reset_index(drop=True)
    expr = str(d["source_expression"].iloc[0])
    total = float(d["atomic_fraction"].sum())
    fig, ax = plt.subplots(figsize=(5.4, 3.0))
    x = np.arange(len(d))
    ax.bar(x, d["atomic_fraction"], color=NAVY, width=0.58, zorder=3)
    for xi, v in enumerate(d["atomic_fraction"]):
        ax.text(xi, v + 0.012, "%.4f" % v, ha="center", va="bottom",
                fontsize=7.4, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels(d["element"])
    # A linear axis, deliberately: a symlog axis makes the two additive
    # elements visible but its decade labels are furniture that the figure-value
    # check then has to be told to ignore. The magnitudes are carried by the
    # printed values and the footnote instead.
    ax.set_ylim(0, max(d["atomic_fraction"]) * 1.18)
    ax.set_ylabel("Atomic fraction")
    ax.set_xlabel("Element")
    ax.set_title("Atomic fractions from the normalized thesis mixture")
    ax.grid(axis="y", zorder=0)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.text(0.0, -0.26,
            "Expression: %s\nFractions sum to %.4f. C and Y sit two orders of "
            "magnitude below O, so their bars are not visible at this scale;\n"
            "the printed values are the recorded ones."
            % (expr, total),
            transform=ax.transAxes, ha="left", va="top", fontsize=6.6, color="#444444")
    _save(fig, "paper2_thesis_mixture_atomic_fractions_origin_style")


def main() -> int:
    FIG.mkdir(parents=True, exist_ok=True)
    parser_coverage()
    element_coverage()
    formula_complexity()
    thesis_ratio_status()
    thesis_mixture()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
