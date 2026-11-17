"""Build a thesis-derived ratio-expression benchmark for Paper 2.

The benchmark is extracted from the original thesis text already stored in
``thesis_analysis/thesis_paragraphs.csv``. It is not a synthetic formula set.
Complete expressions are parsed into atomic fractions; rule-only or ambiguous
expressions are retained with explicit parse-status and ambiguity flags.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


PAPER_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PAPER_ROOT / "code"))

from composition_parser import atomic_fractions, parse_formula  # noqa: E402


EXPRESSION_PARAGRAPHS = {
    1411: {
        "expression_type": "atomic_percent_rule",
        "thesis_expression": "chi at% additive to host",
        "unit": "at%",
        "parse_status": "semantic_rule_extracted",
        "ambiguity_flag": "rule paragraph; no complete formula instance",
    },
    1447: {
        "expression_type": "molar_percent_rule",
        "thesis_expression": "chi mol% additive to host",
        "unit": "mol%",
        "parse_status": "semantic_rule_extracted",
        "ambiguity_flag": "rule paragraph; no complete formula instance",
    },
    1498: {
        "expression_type": "weight_percent_rule",
        "thesis_expression": "wt% additive to host with molar-mass conversion",
        "unit": "wt%",
        "parse_status": "semantic_rule_extracted",
        "ambiguity_flag": "requires molecular-weight conversion and addition order",
    },
    1519: {
        "expression_type": "normalized_mixture_expression",
        "thesis_expression": "0.9977076(BaTiO3)+0.003924(Y2O3)+0.019(C)",
        "unit": "normalized_ratio",
        "parse_status": "fully_normalized_expression_parsed",
        "ambiguity_flag": "none",
    },
    1535: {
        "expression_type": "atomic_percent_example",
        "thesis_expression": "(BaTiO3)+0.25at%(Y2)",
        "unit": "at%",
        "parse_status": "semantic_expression_extracted_with_ambiguity",
        "ambiguity_flag": "additive appears as Y2 in extracted thesis text; chemistry may require manual validation",
    },
    1548: {
        "expression_type": "ratio_parser_workflow",
        "thesis_expression": "host/additive/alloying workflow for wt%, at%, and mol%",
        "unit": "mixed",
        "parse_status": "workflow_rule_extracted",
        "ambiguity_flag": "workflow paragraph; no single formula instance",
    },
}


def load_thesis_paragraphs() -> pd.DataFrame:
    path = WORKSPACE_ROOT / "thesis_analysis" / "thesis_paragraphs.csv"
    if not path.exists():
        raise FileNotFoundError(f"Run tools/deconstruct_thesis.py first: {path}")
    return pd.read_csv(path)


def parse_components(expression: str) -> list[dict[str, object]]:
    pattern = re.compile(r"([0-9]*\.?[0-9]+)\(([^)]+)\)")
    components: list[dict[str, object]] = []
    for coeff_text, formula in pattern.findall(expression):
        coeff = float(coeff_text)
        amounts = parse_formula(formula)
        for element, amount in amounts.items():
            components.append(
                {
                    "formula": formula,
                    "coefficient": coeff,
                    "element": element,
                    "weighted_amount": coeff * amount,
                }
            )
    return components


def normalized_mixture_fractions(expression: str) -> pd.DataFrame:
    components = parse_components(expression)
    if not components:
        return pd.DataFrame()
    comp = pd.DataFrame(components)
    element_amounts = comp.groupby("element", as_index=False).agg(weighted_amount=("weighted_amount", "sum"))
    total = element_amounts["weighted_amount"].sum()
    element_amounts["atomic_fraction"] = element_amounts["weighted_amount"] / total
    element_amounts["source_expression"] = expression
    return element_amounts.sort_values("atomic_fraction", ascending=False)


def extract_formula_parts(expression: str) -> tuple[str, str, float | None]:
    host = ""
    additive = ""
    pct: float | None = None
    formulas = re.findall(r"\(([^)]+)\)", expression)
    if formulas:
        host = formulas[0]
    if len(formulas) > 1:
        additive = formulas[1]
    match = re.search(r"([0-9]*\.?[0-9]+)\s*(?:at|mol|wt)%", expression)
    if match:
        pct = float(match.group(1))
    return host, additive, pct


def build_expression_table(thesis_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for raw_index, meta in EXPRESSION_PARAGRAPHS.items():
        source = thesis_df.loc[thesis_df["raw_index"] == raw_index, "text"]
        source_excerpt = source.iloc[0] if not source.empty else ""
        expression = str(meta["thesis_expression"])
        host, additive, pct = extract_formula_parts(expression)
        parsed_host = ""
        parsed_additive = ""
        if host:
            try:
                parsed_host = "; ".join(f"{k}:{v:g}" for k, v in parse_formula(host).items())
            except Exception as exc:
                parsed_host = f"parse_error: {exc}"
        if additive:
            try:
                parsed_additive = "; ".join(f"{k}:{v:g}" for k, v in parse_formula(additive).items())
            except Exception as exc:
                parsed_additive = f"parse_error: {exc}"
        rows.append(
            {
                "source_paragraph": raw_index,
                "expression_type": meta["expression_type"],
                "thesis_expression": expression,
                "unit": meta["unit"],
                "percentage": "" if pct is None else pct,
                "host_formula": host,
                "additive_formula": additive,
                "parsed_host_amounts": parsed_host,
                "parsed_additive_amounts": parsed_additive,
                "parse_status": meta["parse_status"],
                "ambiguity_flag": meta["ambiguity_flag"],
                "source_excerpt": source_excerpt,
            }
        )
    return pd.DataFrame(rows)


def save_figures(expression_table: pd.DataFrame, fractions: pd.DataFrame, figures_dir: Path) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(
        context="paper",
        style="whitegrid",
        font="DejaVu Sans",
        rc={
            "axes.edgecolor": "0.15",
            "axes.linewidth": 0.8,
            "grid.color": "0.82",
            "grid.linewidth": 0.5,
            "savefig.dpi": 300,
        },
    )

    status_counts = expression_table["parse_status"].value_counts().reset_index()
    status_counts.columns = ["parse_status", "count"]
    plt.figure(figsize=(8.0, 4.6))
    sns.barplot(data=status_counts, x="count", y="parse_status", color="#1B4D89")
    plt.xlabel("Thesis-derived expression count")
    plt.ylabel("Parse status")
    plt.title("Thesis Ratio-Expression Benchmark Status")
    plt.tight_layout()
    plt.savefig(figures_dir / "paper2_thesis_ratio_status_origin_style.png")
    plt.close()

    if not fractions.empty:
        plt.figure(figsize=(6.8, 4.2))
        sns.barplot(data=fractions, x="element", y="atomic_fraction", color="#009E73")
        plt.xlabel("Element")
        plt.ylabel("Atomic fraction")
        plt.title("Normalized Thesis Mixture: BaTiO3 + Y2O3 + C")
        plt.tight_layout()
        plt.savefig(figures_dir / "paper2_thesis_mixture_atomic_fractions_origin_style.png")
        plt.close()


def main() -> None:
    data_dir = PAPER_ROOT / "data"
    figures_dir = PAPER_ROOT / "figures"
    data_dir.mkdir(parents=True, exist_ok=True)

    thesis_df = load_thesis_paragraphs()
    expression_table = build_expression_table(thesis_df)
    expression_table.to_csv(data_dir / "paper2_thesis_ratio_expression_benchmark.csv", index=False)

    complete_expression = EXPRESSION_PARAGRAPHS[1519]["thesis_expression"]
    fractions = normalized_mixture_fractions(str(complete_expression))
    fractions.to_csv(data_dir / "paper2_thesis_normalized_mixture_atomic_fractions.csv", index=False)
    save_figures(expression_table, fractions, figures_dir)

    print(f"Thesis-derived expressions: {len(expression_table)}")
    print(f"Normalized mixture elements: {len(fractions)}")
    print(f"Outputs written to: {data_dir}")


if __name__ == "__main__":
    main()
