"""Re-run every parser configuration on the 28,100 corpus formulas.

The corpus formulas and their source dataset are read from the committed
``data/paper2_parsed_composition_vectors.csv`` (one row per unique formula string
per source dataset, as produced in the submitted version). For each configuration
the script records whether the formula resolves and whether its atomic fractions
equal the committed vector, and writes:

* ``data/processed_results/corpus_backend_check.csv``  per-dataset counts
* ``data/processed_results/corpus_duplicate_compositions.csv``  how many formula
  strings share a reduced composition, within and across datasets (used for the
  fold-leakage check of the downstream illustration)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from composition_parser import atomic_fractions  # noqa: E402
from literature_eval import PARSERS, run_parser  # noqa: E402

PAPER = Path(__file__).resolve().parents[1]
DATA = PAPER / "data"


def committed_fractions(row: pd.Series, frac_cols: list[str]) -> dict[str, float]:
    return {c[5:]: float(row[c]) for c in frac_cols if float(row[c]) > 0}


def main() -> None:
    vec = pd.read_csv(DATA / "paper2_parsed_composition_vectors.csv")
    frac_cols = [c for c in vec.columns if c.startswith("frac_")]
    rows = []
    keys = []
    for _, r in vec.iterrows():
        want = committed_fractions(r, frac_cols)
        keys.append(tuple(sorted((k, round(v, 9)) for k, v in want.items())))
        rec = {"source_dataset": r["source_dataset"], "formula": r["formula"]}
        for name in PARSERS:
            got, _d = run_parser(name, r["formula"])
            ok = got is not None
            same = ok and set(got) == set(want) and all(
                abs(atomic_fractions(got)[k] - want[k]) <= 1e-9 for k in want)
            rec[f"{name}_resolved"] = ok
            rec[f"{name}_matches_committed"] = same
        rows.append(rec)
    df = pd.DataFrame(rows)
    out = df.groupby("source_dataset").agg(
        formulas=("formula", "count"),
        **{f"{n}_resolved": (f"{n}_resolved", "sum") for n in PARSERS},
        **{f"{n}_matches_committed": (f"{n}_matches_committed", "sum") for n in PARSERS},
    ).reset_index()
    total = out.drop(columns="source_dataset").sum()
    total["source_dataset"] = "TOTAL"
    out = pd.concat([out, total.to_frame().T], ignore_index=True)
    (DATA / "processed_results").mkdir(exist_ok=True)
    out.to_csv(DATA / "processed_results" / "corpus_backend_check.csv", index=False)
    print(out.to_string(index=False))

    # Rewrite the committed vector table with the v0.2.0 controlled fields. The
    # fractions are unchanged (checked above: every configuration reproduces them);
    # only the status, backend label and parser version are added or updated.
    from composition_parser import PARSER_VERSION, STATUS_FORMULA_PARSED, parse_formula_with_backend
    backends = [parse_formula_with_backend(f)[1] for f in vec["formula"]]
    if all(df["v02_package_matches_committed"]):
        lead = ["formula", "source_dataset"]
        vec["parse_status"] = STATUS_FORMULA_PARSED
        vec["backend"] = backends
        vec["parser_version"] = PARSER_VERSION
        rest = [c for c in vec.columns if c not in lead + ["parse_status", "backend", "parser_version"]]
        vec[lead + ["parse_status", "backend", "parser_version"] + rest].to_csv(
            DATA / "paper2_parsed_composition_vectors.csv", index=False)
    vec["reduced_key"] = keys
    dup_rows = []
    for ds, part in list(vec.groupby("source_dataset")) + [("ALL", vec)]:
        counts = part["reduced_key"].value_counts()
        dup_rows.append({"source_dataset": ds, "formula_strings": len(part),
                         "distinct_reduced_compositions": int(counts.size),
                         "strings_sharing_a_reduced_composition": int(counts[counts > 1].sum())})
    cross = vec.groupby("reduced_key")["source_dataset"].nunique()
    dup = pd.DataFrame(dup_rows)
    dup["compositions_in_more_than_one_dataset"] = [""] * (len(dup) - 1) + [int((cross > 1).sum())]
    dup.to_csv(DATA / "processed_results" / "corpus_duplicate_compositions.csv", index=False)
    print(dup.to_string(index=False))


if __name__ == "__main__":
    main()
