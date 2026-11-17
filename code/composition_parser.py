"""Deterministic composition parser for doped-ceramic formula strings (package v0.2.0).

Design rule: a string that does not determine a composition is refused with a
controlled reason, never coerced into a vector.

Pipeline for one string:
  1. ``lexical_screen``: every refusal rule that needs no parse (comma site sharing,
     dot and hydrate notation, free variables, colon dopants, percentages, charges,
     words, unknown or placeholder symbols, single-element groups, zero amounts).
  2. ``parse_formula_grammar``: the deterministic grammar (elements, decimal and
     rational subscripts, nested (), [] and {} groups with multipliers).
  3. Cross-check against ``pymatgen.core.Composition`` when it is installed: a
     disagreement is refused, a pymatgen refusal leaves the grammar result standing.

The as-submitted v0.1.0 behaviour (pymatgen preferred, two shared guards) is kept
verbatim in ``legacy/composition_parser_v0_1_0.py`` for comparison only.
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


PARSER_VERSION = "0.2.0"
DATA_URL = "https://ndownloader.figshare.com/files/13213475"
NUMBER_RE = re.compile(r"\d+/\d+|\d+\.\d+|\.\d+|\d+")
# IUPAC-recognised element symbols Z = 1-118, including the four names ratified in
# 2016 (Nh, Mc, Ts, Og). Isotope letters (D, T), placeholders (M, Ln, RE, A, B as
# site labels) and pymatgen's dummy species (Xx) are deliberately absent.
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

# Controlled vocabulary (mirrors schema/composition_record_schema.json).
STATUS_FORMULA_PARSED = "formula_parsed"
STATUS_AMBIGUOUS_REJECTED = "ambiguous_rejected"
STATUS_UNSUPPORTED_REJECTED = "unsupported_rejected"
STATUS_PARSE_ERROR = "parse_error"

# flag -> status class. "ambiguous": the string does not determine a composition.
# "unsupported": the string may determine one, but not as a single formula in this
# grammar (a mixture, a word, an unknown symbol). "error": malformed input.
FLAG_CLASS = {
    "comma_site_fraction_missing": "ambiguous",
    "hydration_or_dot_notation": "ambiguous",
    "free_variable_stoichiometry": "ambiguous",
    "dopant_convention_missing": "ambiguous",
    "unit_convention_missing": "ambiguous",
    "charge_balance_unspecified": "ambiguous",
    "single_element_group": "ambiguous",
    "nonpositive_amount": "ambiguous",
    "mixture_or_arithmetic_notation": "unsupported",
    "non_formula_word": "unsupported",
    "unknown_element_symbol": "unsupported",
    "unconsumed_separator": "unsupported",
    "backend_disagreement": "error",
    "malformed_grouping": "error",
    "manual_validation_required": "error",
}
_STATUS_OF_CLASS = {
    "ambiguous": STATUS_AMBIGUOUS_REJECTED,
    "unsupported": STATUS_UNSUPPORTED_REJECTED,
    "error": STATUS_PARSE_ERROR,
}


class CompositionRefusal(ValueError):
    """A principled refusal. Carries controlled ``status`` and ``flags``.

    Subclassing ValueError keeps every pre-0.2 caller that catches ValueError working.
    """

    def __init__(self, flags: list[str], detail: str):
        flags = list(dict.fromkeys(flags)) or ["manual_validation_required"]
        unknown = [f for f in flags if f not in FLAG_CLASS]
        if unknown:
            raise KeyError(f"uncontrolled refusal flag(s): {unknown}")
        classes = {FLAG_CLASS[f] for f in flags}
        cls = "ambiguous" if "ambiguous" in classes else (
            "unsupported" if "unsupported" in classes else "error")
        self.flags = flags
        self.status = _STATUS_OF_CLASS[cls]
        self.detail = detail
        super().__init__(f"{self.status} [{', '.join(flags)}]: {detail}")


_OPEN = {"(": ")", "[": "]", "{": "}"}
_CLOSE = {v: k for k, v in _OPEN.items()}
_VARIABLE_CHARS = set("xyzδΔ±")
_DOTLIKE = "·•∙⋅*"


def _scan(compact: str) -> tuple[list[tuple[str, str]], list[str], list[str]]:
    """Tokenize a whitespace-free string.

    Returns (tokens, leftovers, unknown_symbols). A token is (kind, text) with kind in
    {"el", "num", "open", "close"}. Two-letter symbols are preferred only when they
    are real elements, so "Sx" is S followed by the variable x, while "Xx" and "Ln"
    are reported as unknown symbols rather than split.
    """
    tokens: list[tuple[str, str]] = []
    leftovers: list[str] = []
    unknown: list[str] = []
    i, n = 0, len(compact)
    while i < n:
        c = compact[i]
        if c.isascii() and c.isupper():
            two = compact[i:i + 2]
            if len(two) == 2 and two[1].islower() and two in ELEMENT_SYMBOLS:
                tokens.append(("el", two)); i += 2; continue
            if c in ELEMENT_SYMBOLS:
                tokens.append(("el", c)); i += 1; continue
            sym = two if (len(two) == 2 and two[1].isascii() and two[1].islower()) else c
            unknown.append(sym); tokens.append(("el", sym)); i += len(sym); continue
        if c.isdigit() or (c == "." and i + 1 < n and compact[i + 1].isdigit()):
            m = NUMBER_RE.match(compact, i)
            tokens.append(("num", m.group())); i = m.end(); continue
        if c in _OPEN:
            tokens.append(("open", c)); i += 1; continue
        if c in _CLOSE:
            tokens.append(("close", c)); i += 1; continue
        leftovers.append(c); i += 1
    return tokens, leftovers, unknown


def _num(text: str) -> float:
    if "/" in text:
        a, b = text.split("/")
        if float(b) == 0:
            raise CompositionRefusal(["nonpositive_amount"], f"zero denominator in {text!r}")
        return float(a) / float(b)
    return float(text)


def lexical_screen(formula: str) -> list[tuple[str, str]]:
    """Apply every refusal rule that does not need a parse, and return the tokens.

    This screen is shared by both backends: it runs before the grammar and before
    pymatgen, so the set of strings the package accepts does not depend on which
    backend is installed. Every rule raises a CompositionRefusal carrying all of
    the controlled flags that apply, not only the first.
    """
    if not isinstance(formula, str) or not formula.strip():
        raise CompositionRefusal(["manual_validation_required"], "empty expression")
    s = formula.strip()
    flags: list[str] = []
    if re.search(r"[A-Z][a-z]?\d+[+\-−–](?![\d.xyzδΔ\s])", s):
        flags.append("charge_balance_unspecified")
    if "," in s:
        flags.append("comma_site_fraction_missing")
    if ":" in s:
        flags.append("dopant_convention_missing")
    if "%" in s:
        flags.append("unit_convention_missing")
    if (any(ch in s for ch in _DOTLIKE) or re.search(r"\.\s*\d*\.?\d*\s*H2O", s)
            or re.search(r"(?<!\d)\.(?!0)", s)):
        # A dot not preceded by a digit ("Ba.9", "Li2O.2SiO2") and any middle dot are
        # ambiguous between a decimal point and an adduct separator; "x.nH2O" is the
        # hydrate case of the same ambiguity. A leading dot followed by 0 ("Bi.02") is
        # accepted, because an adduct multiplier never starts with zero.
        flags.append("hydration_or_dot_notation")
    chunks = s.split()
    if len(chunks) > 1:
        # Whitespace is accepted only where it cannot separate two words or two phases:
        # inside a chunk-with-digits sequence, before a subscript ("Pr 0.6"), after a
        # bare subscript ("0.4 MnO"), or between a symbol and a group ("Ba (Bi0.5...").
        # "Pt Nb2O5", "BaO B2O3" and "CP Cu3Mo6S8" are refused: the space may separate
        # phases or a label, and the string does not say which.
        for j, chunk in enumerate(chunks):
            nxt = chunks[j + 1] if j + 1 < len(chunks) else ""
            prv = chunks[j - 1] if j > 0 else ""
            ok = (bool(re.search(r"\d", chunk))
                  or (re.fullmatch(r"[A-Z][a-z]?", chunk) and (nxt[:1].isdigit() or nxt[:1] in "([{"))
                  or (re.search(r"[A-Z][a-z]?$", chunk) and nxt[:1].isdigit())
                  or bool(re.fullmatch(r"[\d.]+", prv)))
            if not ok:
                flags.append("non_formula_word")
                break
    compact = "".join(chunks)
    tokens, leftovers, unknown = _scan(compact)
    lower_words = [ch for ch in leftovers if ch.isalpha() and ch not in _VARIABLE_CHARS]
    if any(ch in _VARIABLE_CHARS for ch in leftovers):
        flags.append("free_variable_stoichiometry")
    if lower_words:
        flags.append("non_formula_word")
    if any(ch in "+-−–=/^~" for ch in leftovers) or (tokens and tokens[0][0] == "num"):
        flags.append("mixture_or_arithmetic_notation")
    if unknown:
        flags.append("unknown_element_symbol")
    other = [ch for ch in leftovers if not ch.isalpha() and ch not in "+-−–=/^~.,:%"
             and ch not in _DOTLIKE]
    if "." in leftovers and "hydration_or_dot_notation" not in flags:
        other.append(".")
    if other:
        flags.append("unconsumed_separator")
    for k in range(len(tokens) - 1):
        a, b = tokens[k], tokens[k + 1]
        if (a[0] == "open" and b[0] == "el" and k + 2 < len(tokens)
                and tokens[k + 2][0] == "close"
                and not (k + 3 < len(tokens) and tokens[k + 3][0] == "num")):
            flags.append("single_element_group")
        if a[0] in ("el", "close") and b[0] == "num" and _num_safe(b[1]) == 0:
            flags.append("nonpositive_amount")
    if not tokens and not flags:
        flags.append("manual_validation_required")
    if flags:
        raise CompositionRefusal(flags, formula)
    return tokens


def _num_safe(text: str) -> float | None:
    try:
        return _num(text)
    except CompositionRefusal:
        return 0.0


def parse_formula_grammar(formula: str) -> dict[str, float]:
    """The package's deterministic grammar (Sec. 2.2), after the shared screen."""
    tokens = lexical_screen(formula)
    stack: list[tuple[str, defaultdict[str, float]]] = [("", defaultdict(float))]
    i = 0
    while i < len(tokens):
        kind, text = tokens[i]
        if kind == "open":
            stack.append((text, defaultdict(float))); i += 1
        elif kind == "close":
            if len(stack) == 1 or _OPEN[stack[-1][0]] != text:
                raise CompositionRefusal(["malformed_grouping"], f"unmatched {text!r} in {formula}")
            _, group = stack.pop(); i += 1
            mult = 1.0
            if i < len(tokens) and tokens[i][0] == "num":
                mult = _num(tokens[i][1]); i += 1
            for el, amt in group.items():
                stack[-1][1][el] += amt * mult
        elif kind == "el":
            i += 1
            amt = 1.0
            if i < len(tokens) and tokens[i][0] == "num":
                amt = _num(tokens[i][1]); i += 1
            stack[-1][1][text] += amt
        else:  # a number not following an element or a close bracket
            raise CompositionRefusal(["mixture_or_arithmetic_notation"],
                                     f"unexpected coefficient {text!r} in {formula}")
    if len(stack) != 1:
        raise CompositionRefusal(["malformed_grouping"], f"unclosed group in {formula}")
    amounts = {el: a for el, a in stack[0][1].items()}
    if not amounts:
        raise CompositionRefusal(["manual_validation_required"], f"no elements in {formula}")
    if any(a <= 0 for a in amounts.values()):
        raise CompositionRefusal(["nonpositive_amount"], formula)
    return amounts


# Backward-compatible name: the grammar was called the "fallback" in v0.1.
parse_formula_fallback = parse_formula_grammar


def try_pymatgen_parse(formula: str) -> dict[str, float] | None:
    """Raw pymatgen.core.Composition, no guards. None if pymatgen is not installed."""
    try:
        from pymatgen.core import Composition  # type: ignore
    except Exception:
        return None
    comp = Composition(formula)
    return {str(el): float(amount) for el, amount in comp.get_el_amt_dict().items()}


def _same_composition(a: dict[str, float], b: dict[str, float], tol: float = 1e-9) -> bool:
    if set(a) != set(b):
        return False
    fa, fb = atomic_fractions(a), atomic_fractions(b)
    return all(abs(fa[k] - fb[k]) <= tol for k in fa)


BACKEND_AGREE = "grammar+pymatgen_agree"
BACKEND_GRAMMAR_ONLY = "grammar_only_pymatgen_refused"
BACKEND_NO_PYMATGEN = "grammar_only_pymatgen_unavailable"


def parse_formula_with_backend(formula: str, cross_check: bool = True) -> tuple[dict[str, float], str]:
    """Parse with the grammar; use pymatgen, when installed, as an independent check.

    The accepted language is fixed by ``lexical_screen`` and the grammar, so it is
    the same with or without pymatgen. When pymatgen also resolves the string the
    two results must agree, otherwise the string is refused with
    ``backend_disagreement``; when pymatgen refuses a string the grammar resolves
    (rational subscripts such as ``La2/3Sr1/3MnO3``), the grammar result is returned
    and attributed as grammar-only.
    """
    amounts = parse_formula_grammar(formula)
    if not cross_check:
        return amounts, BACKEND_NO_PYMATGEN
    try:
        pm = try_pymatgen_parse("".join(formula.split()))
    except Exception:  # noqa: BLE001 - pymatgen refusal
        return amounts, BACKEND_GRAMMAR_ONLY
    if pm is None:
        return amounts, BACKEND_NO_PYMATGEN
    if not _same_composition(amounts, pm):
        raise CompositionRefusal(["backend_disagreement"],
                                 f"grammar {amounts} vs pymatgen {pm} for {formula}")
    return amounts, BACKEND_AGREE


def parse_formula(formula: str) -> dict[str, float]:
    amounts, _backend = parse_formula_with_backend(formula)
    return amounts


def atomic_fractions(amounts: dict[str, float]) -> dict[str, float]:
    total = sum(amounts.values())
    if total <= 0:
        raise ValueError("Formula contains no positive element amounts")
    return {element: amount / total for element, amount in amounts.items()}


def refusal_of(exc: BaseException) -> tuple[str, list[str], str]:
    """(status, flags, detail) for any exception raised by the parser."""
    if isinstance(exc, CompositionRefusal):
        return exc.status, exc.flags, exc.detail
    return STATUS_PARSE_ERROR, ["manual_validation_required"], str(exc)


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
                "parse_status": STATUS_FORMULA_PARSED,
                "n_elements": len(amounts),
                "total_atoms_reduced": sum(amounts.values()),
                "backend": backend,
            }
            for element, fraction in fracs.items():
                row[f"frac_{element}"] = fraction
            rows.append(row)
        except Exception as exc:  # noqa: BLE001 - recorded with controlled vocabulary
            status, flags, detail = refusal_of(exc)
            failures.append({"formula": formula, "source_dataset": source_dataset,
                             "parse_status": status, "ambiguity_flags": ";".join(flags),
                             "detail": detail})

    out = pd.DataFrame(rows).fillna(0.0)
    failure_df = pd.DataFrame(failures, columns=["formula", "source_dataset", "parse_status",
                                                 "ambiguity_flags", "detail"])
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
