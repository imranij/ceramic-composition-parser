"""Generate the ESI tables and record examples (manuscript/esi_generated_*.tex)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from composition_record import (  # noqa: E402
    build_mixture_record, build_percentage_record, build_record, validate_record)
from composition_semantics import Additive  # noqa: E402
from make_manuscript_numbers import tex_escape  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MS = ROOT / "manuscript"
SHORT = {"exact": "E", "refused": "R", "wrong": "W"}


def benchmark_table() -> None:
    df = pd.read_csv(DATA / "notation_benchmarks_scored.csv")
    rows = [r"\begin{longtable}{@{}>{\raggedright\arraybackslash}p{2.5cm}lcp{2.9cm}cccc>{\raggedright\arraybackslash}p{2.7cm}@{}}",
            r"\caption{All 51 hand-written strings. Expected: P (parse to the listed amounts) or R (refuse). "
            r"Outcome per configuration: E exact, R refused, W wrong (silent mis-parse). Columns: v0.2.0 package, "
            r"v0.1.0 as submitted, v0.1.0 grammar alone, raw pymatgen. Flags: the v0.2.0 record's controlled "
            r"flags.}\label{tab:s1}\\",
            r"\toprule", r"Set: class & String & Exp. & Expected amounts & v0.2 & v0.1 & v0.1g & pmg & v0.2 flags \\",
            r"\midrule\endhead"]
    for _, r in df.iterrows():
        amts = "" if pd.isna(r.expected_amounts) else str(r.expected_amounts).replace(";", ", ")
        rows.append(" & ".join([
            ("stress: " if r.benchmark == "stress24" else "seed: ") + tex_escape(r.notation_class),
            r"\texttt{" + tex_escape(r.formula) + "}", "P" if r.expected == "parse" else "R",
            tex_escape(amts),
            *[SHORT[r[f"{c}_outcome"]] for c in ("v02_package", "v01_guarded", "v01_fallback", "raw_pymatgen")],
            r"{\scriptsize\texttt{" + tex_escape("" if pd.isna(r.v02_record_ambiguity_flags)
                                                else r.v02_record_ambiguity_flags).replace(";", "; ").replace(r"\_", r"\_\allowbreak{}") + "}}"]) + r" \\")
    rows += [r"\bottomrule", r"\end{longtable}", ""]
    (MS / "esi_generated_benchmarks.tex").write_text("\n".join(rows), encoding="utf-8")


def record_examples() -> None:
    recs = [
        ("A single formula resolved through both backends", build_record("Ba0.9Sr0.1TiO3")),
        ("A refusal", build_record("BaO-2SiO2")),
        ("A mixture expression with caller-supplied roles",
         build_mixture_record("0.98BaTiO3+0.02Y2O3", roles=["host", "additive"])),
        ("A percentage specification (1 at% Y, counting dopant atoms, total basis)",
         build_percentage_record("BaTiO3", [Additive("Y2O3", 1.0, "Y")], unit="at%",
                                 basis="total_mixture", at_counts="dopant_element_atoms")),
    ]
    out = []
    for title, rec in recs:
        validate_record(rec)
        rec = json.loads(json.dumps(rec), parse_float=lambda x: round(float(x), 6))
        out.append(r"\paragraph{" + tex_escape(title) + "}")
        out.append(r"\begin{verbatim}" + "\n" + json.dumps(rec, indent=2, ensure_ascii=True) + "\n" + r"\end{verbatim}")
    (MS / "esi_generated_records.tex").write_text("\n".join(out) + "\n", encoding="utf-8")


def thesis_table() -> None:
    d = pd.read_csv(DATA / "paper2_thesis_ratio_expression_benchmark.csv")
    rows = [r"\begin{tabular}{@{}rlp{5.5cm}l@{}}", r"\toprule",
            r"Paragraph & Item type & Thesis expression & Status \\", r"\midrule"]
    for _, r in d.iterrows():
        rows.append(f"{r.source_paragraph} & {tex_escape(r.expression_type)} & "
                    f"\\texttt{{{tex_escape(r.thesis_expression)}}} & {tex_escape(r.parse_status)} \\\\")
    rows += [r"\bottomrule", r"\end{tabular}", ""]
    (MS / "esi_generated_thesis.tex").write_text("\n".join(rows), encoding="utf-8")


if __name__ == "__main__":
    benchmark_table()
    record_examples()
    thesis_table()
    print("wrote ESI tables")
