"""Executable unit-semantics examples with every convention declared (Table 9).

Each case states the host, the additive(s), the stated percentage, the unit, the
basis and (for at%) what is counted. The script computes the additive-to-host
formula-unit ratio r = n_A / n_H with ``composition_semantics.additive_ratios``
and, independently, with the closed-form expression written in the ``derivation``
column, and fails if the two differ. It writes
``data/paper2_semantic_unit_conversions.csv`` and
``manuscript/generated_semantic_unit_table.tex``.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from composition_parser import parse_formula  # noqa: E402
from composition_record import build_percentage_record, validate_record  # noqa: E402
from composition_semantics import Additive, additive_ratios, formula_mass  # noqa: E402

PAPER = Path(__file__).resolve().parents[1]
DATA = PAPER / "data"
MANUSCRIPT = PAPER / "manuscript"

M = {f: formula_mass(parse_formula(f)) for f in ("BaTiO3", "Y2O3", "Al2O3", "MgO", "C")}

# (case, host, [(additive, percent, dopant_element)], unit, basis, at_counts,
#  derivation text, closed-form value(s))
CASES = [
    ("A1", "BaTiO3", [("Y2O3", 1.0, None)], "mol%", "total_mixture", None,
     "0.01/(1-0.01)", [0.01 / 0.99]),
    ("A2", "BaTiO3", [("Y2O3", 1.0, None)], "mol%", "per_host", None,
     "0.01", [0.01]),
    ("A3", "BaTiO3", [("Y2O3", 1.0, None)], "wt%", "total_mixture", None,
     "(0.01/M_Y2O3)/(0.99/M_BaTiO3)", [(0.01 / M["Y2O3"]) / (0.99 / M["BaTiO3"])]),
    ("A4", "BaTiO3", [("Y2O3", 1.0, None)], "at%", "total_mixture", "additive_phase_atoms",
     "0.01*5/(0.99*5)", [0.01 * 5 / (0.99 * 5)]),
    ("A5", "BaTiO3", [("Y2O3", 1.0, "Y")], "at%", "total_mixture", "dopant_element_atoms",
     "0.01*T/2, T=5/(1-5*0.01/2)", [0.01 * (5 / (1 - 5 * 0.01 / 2)) / 2]),
    ("A6", "BaTiO3", [("Y2O3", 1.0, "Y")], "at%", "per_host", "dopant_element_atoms",
     "0.01*5/2", [0.01 * 5 / 2]),
    ("A7", "BaTiO3", [("C", 1.9, None)], "mol%", "total_mixture", None,
     "0.019/(1-0.019)", [0.019 / 0.981]),
    ("A8", "Al2O3", [("Y2O3", 0.5, None), ("MgO", 0.2, None)], "mol%", "total_mixture", None,
     "0.005/0.993; 0.002/0.993", [0.005 / 0.993, 0.002 / 0.993]),
]

COUNT_LABEL = {None: "--", "additive_phase_atoms": "additive atoms",
               "dopant_element_atoms": "dopant atoms"}
BASIS_LABEL = {"total_mixture": "total", "per_host": "per host"}


def main() -> None:
    rows = []
    for case, host, adds, unit, basis, counts, derivation, closed in CASES:
        additives = [Additive(f, p, e) for f, p, e in adds]
        r = additive_ratios(host, additives, unit, basis, counts)
        for got, want in zip(r, closed):
            if not math.isclose(got, want, rel_tol=1e-12):
                raise SystemExit(f"{case}: code {got} != closed form {want}")
        rec = validate_record(build_percentage_record(host, additives, unit=unit, basis=basis,
                                                      at_counts=counts))
        fr = rec["atomic_fractions"]
        rows.append({
            "case_id": case, "host": host,
            "additives": "; ".join(f for f, _, _ in adds),
            "stated_percent": "; ".join(f"{p:g}" for _, p, _ in adds),
            "unit": unit, "basis": basis, "at_percent_counts": counts or "",
            "dopant_element": "; ".join(e for *_, e in adds if e) or "",
            "derivation": derivation,
            "ratio_n_additive_per_n_host": "; ".join(f"{x:.6f}" for x in r),
            "additive_formula_unit_fraction": "; ".join(f"{x / (1 + sum(r)):.6f}" for x in r),
            "atomic_fractions": ";".join(f"{k}:{v:.6f}" for k, v in sorted(fr.items())),
            "molar_masses_used": "; ".join(f"{f}={M[f]:.4f}" for f in [host] + [a for a, _, _ in adds]
                                           if f in M) if unit == "wt%" else "",
        })
    out = pd.DataFrame(rows)
    out.to_csv(DATA / "paper2_semantic_unit_conversions.csv", index=False)
    write_latex(out)
    print(out.drop(columns=["atomic_fractions"]).to_string(index=False))


def _tex(s: str) -> str:
    return (str(s).replace("_", r"\_").replace("%", r"\%"))


def _chem(f: str) -> str:
    import re
    return re.sub(r"(\d+)", r"$_{\1}$", f)


def write_latex(out: pd.DataFrame) -> None:
    lines = [
        r"\begin{table*}[!t]",
        r"\centering",
        r"\caption{Unit-semantics examples with every convention declared. $r=n_A/n_H$ is the "
        r"additive-to-host formula-unit ratio (host coefficient 1); $x_A=n_A/(n_H+\sum n)$ is the "
        r"additive share of all formula units. ``Total'' basis: the percentage is of the whole "
        r"mixture; ``per host'': of the host alone. For at\%, ``additive atoms'' counts every atom "
        r"of the additive formula unit and ``dopant atoms'' only the named dopant element. "
        r"Molar masses for A3: BaTiO$_3$ 233.1922, Y$_2$O$_3$ 225.8099\,g\,mol$^{-1}$. "
        r"Each $r$ is checked against the closed form shown.}",
        r"\label{tab:semantic_unit_eval}",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\begin{tabular}{@{}lllrlllrr@{}}",
        r"\toprule",
        r"Case & Host & Additive & \% & Unit & Basis & at\% counts & Derivation of $r$ & $r$ \\",
        r"\midrule",
    ]
    for _, row in out.iterrows():
        adds = "; ".join(_chem(a) for a in row["additives"].split("; "))
        lines.append(
            f"{row.case_id} & {_chem(row.host)} & {adds} & {_tex(row.stated_percent)} & "
            f"{_tex(row.unit)} & {BASIS_LABEL[row.basis]} & "
            f"{COUNT_LABEL[row.at_percent_counts or None]} & "
            f"\\texttt{{{_tex(row.derivation)}}} & {_tex(row.ratio_n_additive_per_n_host)} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]
    (MANUSCRIPT / "generated_semantic_unit_table.tex").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
