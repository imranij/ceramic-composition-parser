# FROZEN COPY of composition_parser.py as submitted (package v0.1.0). Do not edit.
# Used only to report the as-submitted behaviour alongside v0.2.0.
"""Parse and standardize real materials formula records.

The script prefers pymatgen when installed. Without pymatgen, it uses a
deterministic formula parser that supports element symbols, decimals, and
parentheses. The default input is the real dielectric-constant dataset downloaded
for Paper 1, so no dummy formula records are required.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.request import urlretrieve

import pandas as pd

# matplotlib and seaborn are imported inside save_figures() rather than at module
# scope: as of the 2026-09-10 packaging pass this module is importable as a library
# (``pip install ceramic-composition-parser``), and a parser should not require a
# plotting stack to parse. They remain hard requirements of the figure path only,
# declared under the ``figures`` extra in pyproject.toml.


DATA_URL = "https://ndownloader.figshare.com/files/13213475"
TOKEN_RE = re.compile(r"([A-Z][a-z]?|\(|\)|[0-9]*\.?[0-9]+)")
NUMBER_RE = re.compile(r"[0-9]*\.?[0-9]+")
ELEMENT_SYMBOLS = {
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
    "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds",
    "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
}


def try_pymatgen_parse(formula: str) -> dict[str, float] | None:
    try:
        from pymatgen.core import Composition  # type: ignore
    except Exception:
        return None
    comp = Composition(formula)
    return {str(el): float(amount) for el, amount in comp.get_el_amt_dict().items()}


def _reject_unresolvable_notation(formula: str) -> None:
    """Raise ValueError on notation that does not determine a composition.

    These two checks used to live only inside ``parse_formula_fallback``, which meant
    they protected the fallback grammar but not a `pymatgen`-preferring caller. That is
    a real regression, not a hypothetical one: `pymatgen.core.Composition` parses
    ``BaTiO3.2H2O`` without error, silently returning ``O:4.2`` for the same reason the
    fallback grammar once did (the tokenizer cannot tell a decimal subscript from a
    water-of-crystallization multiplier). Once `pymatgen` is installed -- it is listed
    in ``requirements.txt`` -- `parse_formula` prefers it, so without this shared guard
    the hydrate mis-parse this package's stress test exists to catch would resurface in
    the exact code path the paper's headline example claims to have fixed. The guard is
    therefore applied before either backend is tried, so both are covered identically.
    """
    if "," in formula:
        raise ValueError(
            f"Ambiguous comma site notation requires an explicit fraction expansion: {formula}"
        )
    if re.search(r"[.·*]\s*\d*\s*H2O\b", formula) or "·" in formula:
        raise ValueError(
            "Ambiguous hydrate notation: a decimal subscript cannot be distinguished "
            f"from a water-of-crystallization multiplier; expand explicitly: {formula}"
        )


def parse_formula_fallback(formula: str) -> dict[str, float]:
    # Reject ambiguous comma site notation (e.g. "(Ba,Sr)TiO3") explicitly instead of silently
    # dropping the comma and mis-parsing it as a fixed 1:1 mixture. Such notation does not encode
    # the substitution fraction and must be expanded with an explicit composition before parsing.
    # Reject hydrate dot notation. "BaTiO3.2H2O" is syntactically indistinguishable
    # from a decimal subscript: the tokenizer reads "O3.2" as oxygen at amount 3.2 and
    # then folds the water's oxygen in on top, silently yielding O:4.2 for what the
    # author wrote as BaTiO3 with two waters. Refusing is required because the string
    # genuinely does not determine which reading is meant -- the caller must expand the
    # hydrate explicitly. Detected via the "*H2O" / "*nH2O" idiom rather than by banning
    # decimals, which are legitimate subscripts in doped compositions.
    _reject_unresolvable_notation(formula)

    compact = formula.replace(" ", "")
    tokens = TOKEN_RE.findall(compact)
    if not tokens:
        raise ValueError(f"Could not tokenize formula: {formula}")
    if "".join(tokens) != compact:
        raise ValueError(
            "Unsupported characters or separators in formula; expand mixtures, hydrates, "
            f"charges, and arithmetic notation before parsing: {formula}"
        )

    stack: list[defaultdict[str, float]] = [defaultdict(float)]
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == "(":
            stack.append(defaultdict(float))
            i += 1
        elif token == ")":
            if len(stack) == 1:
                raise ValueError(f"Unmatched parenthesis in formula: {formula}")
            group = stack.pop()
            i += 1
            multiplier = 1.0
            if i < len(tokens) and NUMBER_RE.fullmatch(tokens[i]):
                multiplier = float(tokens[i])
                if multiplier <= 0:
                    raise ValueError(f"Non-positive group multiplier in formula: {formula}")
                i += 1
            for element, amount in group.items():
                stack[-1][element] += amount * multiplier
        elif re.fullmatch(r"[A-Z][a-z]?", token):
            element = token
            if element not in ELEMENT_SYMBOLS:
                raise ValueError(f"Unknown element symbol {element!r} in formula: {formula}")
            i += 1
            amount = 1.0
            if i < len(tokens) and NUMBER_RE.fullmatch(tokens[i]):
                amount = float(tokens[i])
                if amount <= 0:
                    raise ValueError(f"Non-positive element amount in formula: {formula}")
                i += 1
            stack[-1][element] += amount
        else:
            raise ValueError(f"Unexpected token {token!r} in formula: {formula}")

    if len(stack) != 1:
        raise ValueError(f"Unclosed parenthesis in formula: {formula}")
    if not stack[0]:
        raise ValueError(f"Formula contains no elements: {formula}")
    return dict(stack[0])


def parse_formula_with_backend(formula: str) -> tuple[dict[str, float], str]:
    """Parse ``formula`` and report which backend produced the result.

    Applies the shared refusal guards first (see ``_reject_unresolvable_notation``),
    then prefers `pymatgen` and falls back to the deterministic grammar. A `pymatgen`
    result is additionally checked against the known element-symbol table: `pymatgen`
    accepts its own reserved dummy species (e.g. ``Xx``, used for anonymized
    compositions) as a valid element with no diagnostic, which would silently pass an
    invalid or unrecognized symbol that the fallback grammar correctly rejects. This
    keeps element-symbol validation identical regardless of which backend resolved the
    string, so the choice of backend is an implementation detail, not a difference in
    what counts as a valid formula.
    """
    _reject_unresolvable_notation(formula)
    parsed = try_pymatgen_parse(formula)
    if parsed is not None:
        unknown = sorted(set(parsed) - ELEMENT_SYMBOLS)
        if unknown:
            raise ValueError(
                f"Unknown element symbol(s) {unknown!r} in formula: {formula}"
            )
        return parsed, "pymatgen"
    return parse_formula_fallback(formula), "fallback"


def parse_formula(formula: str) -> dict[str, float]:
    amounts, _backend = parse_formula_with_backend(formula)
    return amounts


def atomic_fractions(amounts: dict[str, float]) -> dict[str, float]:
    total = sum(amounts.values())
    if total <= 0:
        raise ValueError("Formula contains no positive element amounts")
    return {element: amount / total for element, amount in amounts.items()}


def ensure_default_input() -> Path:
    paper1_data = Path(__file__).resolve().parents[2] / "Paper_1_Uncertainty_Calibrated_Data_Repair_for_Ceramic_Materials" / "data"
    paper1_data.mkdir(parents=True, exist_ok=True)
    target = paper1_data / "dielectric_constant.json.gz"
    if not target.exists():
        urlretrieve(DATA_URL, target)
    return target


def load_formula_records(path: Path | None) -> pd.DataFrame:
    if path is None:
        path = ensure_default_input()
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            raw = json.load(handle)
        df = pd.DataFrame(raw["data"], columns=raw["columns"], index=raw["index"])
    else:
        df = pd.read_csv(path)
    df["source_dataset"] = path.name.replace(".json.gz", "").replace(".csv", "")
    return df


def load_shared_formula_records() -> pd.DataFrame:
    root = Path(__file__).resolve().parents[2]
    frames = [load_formula_records(None)]
    shared_dir = root / "shared_datasets" / "matminer"
    for path in sorted(shared_dir.glob("*.json.gz")):
        try:
            frame = load_formula_records(path)
            if "formula" in frame.columns:
                frames.append(frame)
        except Exception as exc:
            print(f"Skipping {path.name}: {exc}")
    return pd.concat(frames, ignore_index=True, sort=False)


def build_composition_table(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if "formula" not in df.columns:
        raise ValueError("Input data must contain a 'formula' column")

    rows: list[dict[str, float | str | int]] = []
    failures: list[dict[str, str]] = []

    formula_df = df[["formula", "source_dataset"]].dropna().astype(str).drop_duplicates()
    for _, formula_record in formula_df.iterrows():
        formula = formula_record["formula"]
        source_dataset = formula_record["source_dataset"]
        try:
            amounts, backend = parse_formula_with_backend(formula)
            fracs = atomic_fractions(amounts)
            row: dict[str, float | str | int] = {
                "formula": formula,
                "source_dataset": source_dataset,
                "n_elements": len(amounts),
                "total_atoms_reduced": sum(amounts.values()),
                "backend": backend,
            }
            for element, fraction in fracs.items():
                row[f"frac_{element}"] = fraction
            rows.append(row)
        except Exception as exc:
            failures.append({"formula": formula, "source_dataset": source_dataset, "error": str(exc)})

    out = pd.DataFrame(rows).fillna(0.0)
    failure_df = pd.DataFrame(failures, columns=["formula", "source_dataset", "error"])
    if failures:
        failure_df.to_csv(Path(__file__).resolve().parents[1] / "data" / "parser_failures.csv", index=False)
    return out, failure_df


def formula_complexity(table: pd.DataFrame) -> pd.DataFrame:
    frac_cols = [col for col in table.columns if col.startswith("frac_")]
    rows: list[dict[str, float | str | int | bool]] = []
    for _, record in table.iterrows():
        fractions = [float(record[col]) for col in frac_cols if float(record[col]) > 0]
        entropy = -sum(value * math.log(value) for value in fractions)
        formula = str(record["formula"])
        rows.append(
            {
                "formula": formula,
                "source_dataset": str(record["source_dataset"]),
                "n_elements": int(record["n_elements"]),
                "total_atoms_reduced": float(record["total_atoms_reduced"]),
                "formula_length": len(formula),
                "has_parentheses": "(" in formula or ")" in formula,
                "has_decimal_stoichiometry": bool(re.search(r"\d+\.\d+|\.\d+", formula)),
                "max_element_fraction": max(fractions) if fractions else 0.0,
                "composition_entropy": entropy,
            }
        )
    return pd.DataFrame(rows)


def write_diagnostics(raw_df: pd.DataFrame, table: pd.DataFrame, failure_df: pd.DataFrame, data_dir: Path) -> pd.DataFrame:
    formula_df = raw_df[["formula", "source_dataset"]].dropna().astype(str).drop_duplicates()
    complexity = formula_complexity(table)
    complexity_path = data_dir / "paper2_formula_complexity.csv"
    complexity.to_csv(complexity_path, index=False)

    total = formula_df.groupby("source_dataset", as_index=False).agg(total_unique_formulas=("formula", "count"))
    parsed = table.groupby("source_dataset", as_index=False).agg(parsed_formulas=("formula", "count"))
    if failure_df.empty:
        failed = pd.DataFrame(columns=["source_dataset", "failed_formulas"])
    else:
        failed = failure_df.groupby("source_dataset", as_index=False).agg(failed_formulas=("formula", "count"))
    complexity_summary = complexity.groupby("source_dataset", as_index=False).agg(
        mean_n_elements=("n_elements", "mean"),
        max_n_elements=("n_elements", "max"),
        mean_formula_length=("formula_length", "mean"),
        formulas_with_parentheses=("has_parentheses", "sum"),
        formulas_with_decimal_stoichiometry=("has_decimal_stoichiometry", "sum"),
        mean_composition_entropy=("composition_entropy", "mean"),
    )

    coverage = total.merge(parsed, on="source_dataset", how="left").merge(failed, on="source_dataset", how="left")
    coverage = coverage.merge(complexity_summary, on="source_dataset", how="left")
    coverage["parsed_formulas"] = pd.to_numeric(coverage["parsed_formulas"], errors="coerce").fillna(0).astype(int)
    coverage["failed_formulas"] = pd.to_numeric(coverage["failed_formulas"], errors="coerce").fillna(0).astype(int)
    coverage["parse_success_rate"] = coverage["parsed_formulas"] / coverage["total_unique_formulas"]
    for col in [
        "mean_n_elements",
        "max_n_elements",
        "mean_formula_length",
        "formulas_with_parentheses",
        "formulas_with_decimal_stoichiometry",
        "mean_composition_entropy",
    ]:
        coverage[col] = coverage[col].fillna(0)
    int_cols = ["total_unique_formulas", "parsed_formulas", "failed_formulas", "max_n_elements", "formulas_with_parentheses", "formulas_with_decimal_stoichiometry"]
    coverage[int_cols] = coverage[int_cols].astype(int)
    coverage = coverage.sort_values("source_dataset")
    coverage.to_csv(data_dir / "paper2_parser_source_coverage.csv", index=False)
    return complexity


def save_figures(table: pd.DataFrame, complexity: pd.DataFrame, coverage: pd.DataFrame, figures_dir: Path) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_theme(style="ticks", context="paper", font_scale=1.0)
    plt.rcParams.update(
        {
            "axes.edgecolor": "#222222",
            "axes.linewidth": 0.8,
            "grid.color": "#D8DDE3",
            "grid.linewidth": 0.6,
            "font.family": "DejaVu Sans",
        }
    )

    counts: Counter[str] = Counter()
    for col in table.columns:
        if col.startswith("frac_"):
            counts[col.replace("frac_", "")] = int((table[col] > 0).sum())

    top = pd.DataFrame(counts.most_common(20), columns=["element", "formula_count"])
    plt.figure(figsize=(7.2, 4.2))
    sns.barplot(data=top, x="element", y="formula_count", color="#1B4D89")
    plt.xlabel("Element")
    plt.ylabel("Number of real formulas containing element")
    plt.title("Element Coverage in Parsed Real Materials Datasets")
    plt.grid(axis="y", alpha=0.9)
    plt.tight_layout()
    plt.savefig(figures_dir / "paper2_element_coverage_origin_style.png", dpi=300)
    plt.close()

    ordered_coverage = coverage.sort_values("parsed_formulas", ascending=True)
    plt.figure(figsize=(7.4, 4.4))
    ax = sns.barplot(data=ordered_coverage, y="source_dataset", x="parsed_formulas", hue="source_dataset", palette="colorblind", legend=False)
    for _, row in ordered_coverage.iterrows():
        ax.text(
            row["parsed_formulas"],
            list(ordered_coverage["source_dataset"]).index(row["source_dataset"]),
            f"  {row['parse_success_rate']:.1%}",
            va="center",
            fontsize=8,
        )
    plt.xlabel("Parsed unique formulas")
    plt.ylabel("Source dataset")
    plt.title("Formula Parsing Coverage Across Real Open Datasets")
    plt.xlim(0, ordered_coverage["parsed_formulas"].max() * 1.14)
    plt.grid(axis="x", alpha=0.9)
    plt.tight_layout()
    plt.savefig(figures_dir / "paper2_parser_coverage_by_dataset_origin_style.png", dpi=300)
    plt.close()

    complexity_plot = complexity.copy()
    order = (
        complexity_plot.groupby("source_dataset")["composition_entropy"]
        .median()
        .sort_values(ascending=False)
        .index.tolist()
    )
    plt.figure(figsize=(7.6, 4.5))
    sns.boxplot(
        data=complexity_plot,
        x="source_dataset",
        y="composition_entropy",
        order=order,
        hue="source_dataset",
        palette="colorblind",
        width=0.55,
        fliersize=1.5,
        linewidth=0.8,
        legend=False,
    )
    plt.xlabel("Source dataset")
    plt.ylabel("Composition entropy")
    plt.title("Formula Complexity Distribution After Normalization")
    plt.xticks(rotation=25, ha="right")
    plt.grid(axis="y", alpha=0.9)
    plt.tight_layout()
    plt.savefig(figures_dir / "paper2_formula_complexity_origin_style.png", dpi=300)
    plt.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=None, help="CSV or matminer JSON.GZ with a formula column")
    parser.add_argument("--shared", action="store_true", help="Parse all downloaded shared matminer formula datasets")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    df = load_shared_formula_records() if args.shared or args.input is None else load_formula_records(args.input)
    table, failure_df = build_composition_table(df)
    out_path = data_dir / "paper2_parsed_composition_vectors.csv"
    table.to_csv(out_path, index=False)
    complexity = write_diagnostics(df, table, failure_df, data_dir)
    coverage = pd.read_csv(data_dir / "paper2_parser_source_coverage.csv")
    save_figures(table, complexity, coverage, root / "figures")
    print(f"Parsed formulas: {len(table)}")
    print(f"Composition table: {out_path}")


if __name__ == "__main__":
    main()
