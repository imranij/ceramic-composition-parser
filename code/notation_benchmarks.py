"""Score every parser configuration on the two hand-written notation benchmarks.

Benchmarks (both written by the parser's author; labels are unchanged from the
submitted version so that no result is obtained by relabelling):

* ``data/stress_benchmark.csv``  24 strings in 15 notation families, now with the
  exact expected element amounts for each resolvable case.
* ``data/dopant_notation_benchmark.csv``  the 27-row seed benchmark.

Scoring per string and configuration (exact, not merely "returned something"):

* expected ``parse``: ``exact`` if the returned amounts equal the expected amounts
  (relative tolerance 1e-9 per element, identical element set); ``wrong`` if a
  different composition is returned; ``refused`` otherwise (a false refusal).
* expected ``reject``: ``refused`` is correct; any returned composition is ``wrong``.

A *silent mis-parse* is ``wrong`` in either case.

Outputs ``data/notation_benchmarks_scored.csv`` (one row per string, one column
group per configuration, plus the v0.2 record's controlled ``parse_status`` and
``ambiguity_flags``) and ``data/processed_results/notation_benchmarks_summary.csv``.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from composition_record import build_record, validate_record  # noqa: E402
from literature_eval import PARSERS, PARSER_LABEL, run_parser  # noqa: E402

PAPER = Path(__file__).resolve().parents[1]
DATA = PAPER / "data"


def parse_amounts(text: str) -> dict[str, float]:
    if not isinstance(text, str) or not text.strip():
        return {}
    out = {}
    for part in text.split(";"):
        el, v = part.split(":")
        out[el.strip()] = float(v)
    return out


def exact(got: dict[str, float], want: dict[str, float]) -> bool:
    return set(got) == set(want) and all(
        math.isclose(got[k], want[k], rel_tol=1e-9, abs_tol=1e-12) for k in want)


def load() -> pd.DataFrame:
    st = pd.read_csv(DATA / "stress_benchmark.csv")
    st = st.assign(benchmark="stress24", notation_class=st["family"])
    sd = pd.read_csv(DATA / "dopant_notation_benchmark.csv")
    sd = sd.rename(columns={"notation_type": "notation_class",
                            "expected_behavior": "expected"})
    sd = sd.assign(benchmark="seed27")
    cols = ["benchmark", "notation_class", "formula", "expected", "expected_amounts"]
    return pd.concat([st[cols], sd[cols]], ignore_index=True)


def score(df: pd.DataFrame) -> pd.DataFrame:
    for name in PARSERS:
        outs, dets = [], []
        for f, exp, want in zip(df["formula"], df["expected"], df["expected_amounts"]):
            got, detail = run_parser(name, f)
            dets.append(detail)
            if got is None:
                outs.append("refused")
            elif exp == "parse" and exact(got, parse_amounts(want)):
                outs.append("exact")
            else:
                outs.append("wrong")
        df[f"{name}_outcome"] = outs
        df[f"{name}_detail"] = dets
        df[f"{name}_correct"] = [
            (o == "exact") if e == "parse" else (o == "refused")
            for o, e in zip(outs, df["expected"])]
        df[f"{name}_silent_mis_parse"] = [o == "wrong" for o in outs]
    recs = [validate_record(build_record(f)) for f in df["formula"]]
    df["v02_record_parse_status"] = [r["parse_status"] for r in recs]
    df["v02_record_ambiguity_flags"] = [";".join(r["ambiguity_flags"]) for r in recs]
    df["v02_record_backend"] = [r["provenance"]["parser_backend"] for r in recs]
    return df


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for subset, part in [("stress24", df[df.benchmark == "stress24"]),
                         ("seed27", df[df.benchmark == "seed27"]),
                         ("pooled51", df)]:
        for name in PARSERS:
            res = part[part.expected == "parse"]
            rej = part[part.expected == "reject"]
            rows.append({
                "subset": subset, "configuration": name, "label": PARSER_LABEL[name],
                "n": len(part),
                "resolvable_n": len(res),
                "resolvable_exact": int((res[f"{name}_outcome"] == "exact").sum()),
                "resolvable_false_refusals": int((res[f"{name}_outcome"] == "refused").sum()),
                "resolvable_wrong": int((res[f"{name}_outcome"] == "wrong").sum()),
                "ambiguous_n": len(rej),
                "ambiguous_refused": int((rej[f"{name}_outcome"] == "refused").sum()),
                "ambiguous_returned": int((rej[f"{name}_outcome"] == "wrong").sum()),
                "silent_mis_parses": int(part[f"{name}_silent_mis_parse"].sum()),
                "correct": int(part[f"{name}_correct"].sum()),
            })
    return pd.DataFrame(rows)


def main() -> None:
    df = score(load())
    df.to_csv(DATA / "notation_benchmarks_scored.csv", index=False)
    summ = summarise(df)
    (DATA / "processed_results").mkdir(exist_ok=True)
    summ.to_csv(DATA / "processed_results" / "notation_benchmarks_summary.csv", index=False)
    print(summ.drop(columns=["label"]).to_string(index=False))


if __name__ == "__main__":
    main()
