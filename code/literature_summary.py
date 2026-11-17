"""Summary tables and paired tests for the literature-string evaluation.

Reads ``data/literature_strings_eval.csv`` (development corpus, solid-state release)
and ``data/literature_strings_heldout_solgel.csv`` (held-out corpus, sol-gel release,
strings not present in the development corpus) and writes:

* ``processed_results/literature_outcomes.csv``     outcome counts per configuration
* ``processed_results/literature_mcnemar.csv``      paired exact McNemar tests
* ``processed_results/literature_discordant_v02.csv`` every v0.2 discordant return
* ``processed_results/literature_refusal_cost.csv`` strings v0.2 refuses but raw
  pymatgen resolves in agreement with the reference, by deterministic category
* ``processed_results/literature_strata.csv``       notation strata x reference class
* ``annotation/expert_annotation_sample.csv``        a stratified sample for two
  independent annotators (labels left blank; see the file header)
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from literature_eval import PARSERS  # noqa: E402

PAPER = Path(__file__).resolve().parents[1]
DATA = PAPER / "data"
OUT = DATA / "processed_results"
SETS = {"development": DATA / "literature_strings_eval.csv",
        "heldout": DATA / "literature_strings_heldout_solgel.csv"}


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def discordant(df: pd.DataFrame, name: str) -> pd.Series:
    return df[f"{name}_outcome"].isin(["disagree", "returned"])


def dummy(df: pd.DataFrame, name: str) -> pd.Series:
    return df[f"{name}_mechanism"].fillna("").eq("dummy_species_accepted")


def outcomes(df: pd.DataFrame, setname: str) -> list[dict]:
    rows = []
    det = df.reference_class.eq("determinate")
    for name in PARSERS:
        o = df[f"{name}_outcome"]
        rows.append({
            "set": setname, "configuration": name, "strings": len(df),
            "determinate": int(det.sum()),
            "determinate_agree": int((det & o.eq("agree")).sum()),
            "determinate_refused": int((det & o.eq("refused")).sum()),
            "determinate_disagree": int((det & o.eq("disagree")).sum()),
            "indeterminate": int(df.reference_class.eq("indeterminate").sum()),
            "indeterminate_returned": int((df.reference_class.eq("indeterminate") & o.eq("returned")).sum()),
            "mixture": int(df.reference_class.eq("mixture").sum()),
            "mixture_returned": int((df.reference_class.eq("mixture") & o.eq("returned")).sum()),
            "discordant_returns": int(discordant(df, name).sum()),
            "of_which_dummy_species": int(dummy(df, name).sum()),
            "discordant_excluding_dummy": int((discordant(df, name) & ~dummy(df, name)).sum()),
        })
    return rows


def paired(df: pd.DataFrame, setname: str) -> list[dict]:
    rows = []
    pairs = [("v02_package", "raw_pymatgen"), ("v02_package", "v01_guarded"),
             ("v01_guarded", "raw_pymatgen"), ("v02_package", "v01_fallback")]
    for a, b in pairs:
        for endpoint, fa, fb in [
            ("discordant_return", discordant(df, a), discordant(df, b)),
            ("discordant_return_excluding_dummy", discordant(df, a) & ~dummy(df, a),
             discordant(df, b) & ~dummy(df, b)),
            ("determinate_agree", df[f"{a}_outcome"].eq("agree"), df[f"{b}_outcome"].eq("agree")),
        ]:
            only_a, only_b = int((fa & ~fb).sum()), int((~fa & fb).sum())
            # DOI-level sensitivity: a DOI counts once, flagged if any of its strings is
            dois = pd.DataFrame({"doi": df.first_doi, "a": fa, "b": fb}).groupby("doi").any()
            da, db = int((dois.a & ~dois.b).sum()), int((~dois.a & dois.b).sum())
            rows.append({"set": setname, "a": a, "b": b, "endpoint": endpoint,
                         "a_only": only_a, "b_only": only_b,
                         "p_exact_strings": mcnemar_exact(only_a, only_b),
                         "doi_a_only": da, "doi_b_only": db,
                         "p_exact_dois": mcnemar_exact(da, db)})
    return rows


def cost_category(s: str) -> str:
    if "@" in s:
        return "core_shell_or_composite_at_sign"
    if re.search(r"[.·]\s*\d*\s*H2O", s):
        return "hydrate_dot"
    if re.search(r"(?<!\d)\.", s):
        return "dot_ambiguous_decimal_or_adduct"
    if re.search(r"\(\s*[A-Z][a-z]?\s*\)(?!\d)", s):
        return "single_element_group_dopant"
    if len(s.split()) > 1:
        return "whitespace_separated_phases_or_labels"
    return "other"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    frames = {k: pd.read_csv(v) for k, v in SETS.items()}
    pd.DataFrame([r for k, d in frames.items() for r in outcomes(d, k)]).to_csv(
        OUT / "literature_outcomes.csv", index=False)
    pd.DataFrame([r for k, d in frames.items() for r in paired(d, k)]).to_csv(
        OUT / "literature_mcnemar.csv", index=False)

    disc = []
    for k, d in frames.items():
        x = d[discordant(d, "v02_package")]
        for _, r in x.iterrows():
            disc.append({"set": k, "string": r.string, "first_doi": r.first_doi,
                         "reference_class": r.reference_class,
                         "reference_reason": r.reference_reason,
                         "reference_amounts": r.reference_amounts,
                         "v02_amounts": r.v02_package_amounts,
                         "raw_pymatgen_amounts": r.raw_pymatgen_amounts})
    pd.DataFrame(disc).to_csv(OUT / "literature_discordant_v02.csv", index=False)

    cost = []
    for k, d in frames.items():
        x = d[d.reference_class.eq("determinate") & d.v02_package_outcome.eq("refused")
              & d.raw_pymatgen_outcome.eq("agree")]
        for _, r in x.iterrows():
            cost.append({"set": k, "string": r.string, "first_doi": r.first_doi,
                         "category": cost_category(r.string),
                         "v02_flags": r.v02_package_detail})
    cost = pd.DataFrame(cost)
    cost.to_csv(OUT / "literature_refusal_cost.csv", index=False)

    strata = pd.concat([d.assign(set=k) for k, d in frames.items()])
    strata.groupby(["set", "stratum", "reference_class"]).size().unstack(fill_value=0).to_csv(
        OUT / "literature_strata.csv")

    mix = []
    for k, d in frames.items():
        m = d[d.reference_class.eq("mixture")]
        mix.append({"set": k, "mixture_strings": len(m),
                    **m.mixture_layer_outcome.value_counts().to_dict(),
                    "returned_for_non_mixture": int((d.reference_class.ne("mixture")
                                                     & d.mixture_layer_outcome.ne("refused")).sum())})
    pd.DataFrame(mix).to_csv(OUT / "literature_mixture_layer.csv", index=False)

    # stratified sample for independent expert annotation (labels intentionally blank)
    pool = pd.concat([d.assign(set=k) for k, d in frames.items()])
    pool = pool.assign(stratum_class=pool.stratum + "|" + pool.reference_class)
    sample = (pool.groupby("stratum_class", group_keys=False)
              .apply(lambda g: g.sample(min(len(g), 12), random_state=20261103)))
    sample = sample.sample(frac=1, random_state=1)[["set", "string", "first_doi", "stratum"]]
    sample = sample.assign(annotator_A_composition="", annotator_A_decision="",
                           annotator_B_composition="", annotator_B_decision="", adjudicated="")
    (PAPER / "annotation").mkdir(exist_ok=True)
    sample.to_csv(PAPER / "annotation" / "expert_annotation_sample.csv", index=False)

    print(pd.read_csv(OUT / "literature_outcomes.csv").to_string(index=False))
    print(pd.read_csv(OUT / "literature_mcnemar.csv").to_string(index=False))
    print(cost.groupby(["set", "category"]).size())
    print(pd.read_csv(OUT / "literature_mixture_layer.csv").to_string(index=False))
    print("annotation sample:", len(sample))


if __name__ == "__main__":
    main()


# ------------------------------------------------------------------ hazard catalogue
HAZARD_ORDER = [
    "hydration_or_dot_notation", "non_formula_word", "unconsumed_separator",
    "unknown_element_symbol", "mixture_or_arithmetic_notation", "single_element_group",
    "nonpositive_amount", "charge_balance_unspecified", "free_variable_stoichiometry",
    "comma_site_fraction_missing", "dopant_convention_missing", "unit_convention_missing",
    "backend_disagreement", "malformed_grouping",
]


def hazard_class(row: pd.Series) -> str:
    flags = str(row.v02_package_detail).replace("refused:", "").split("|")
    primary = next((f for f in HAZARD_ORDER if f.split(":")[0] in flags), flags[0])
    if primary.startswith("unknown_element_symbol"):
        got = str(row.raw_pymatgen_amounts)
        from composition_parser import ELEMENT_SYMBOLS
        els = {p.split(":")[0] for p in got.split(";") if p}
        return ("unknown_element_symbol:dummy_species" if els - ELEMENT_SYMBOLS
                else "unknown_element_symbol:isotope_letter_as_H")
    return primary


def hazard_catalogue() -> pd.DataFrame:
    rows = []
    for k, path in SETS.items():
        d = pd.read_csv(path)
        x = d[d.raw_pymatgen_outcome.ne("refused") & d.v02_package_outcome.eq("refused")].copy()
        x["hazard"] = x.apply(hazard_class, axis=1)
        x["set"] = k
        rows.append(x)
    allx = pd.concat(rows)
    allx[["set", "hazard", "string", "first_doi", "raw_pymatgen_amounts", "v01_guarded_outcome",
          "v02_package_detail"]].to_csv(OUT / "literature_hazard_instances.csv", index=False)
    cat = []
    for h, g in allx.groupby("hazard"):
        dev, ho = g[g.set == "development"], g[g.set == "heldout"]
        ex = g.assign(_len=g.string.str.len()).sort_values(["set", "_len", "string"]).iloc[0]
        cat.append({"hazard": h, "development": len(dev), "heldout": len(ho),
                    "v01_also_returned": int(g.v01_guarded_outcome.ne("refused").sum()),
                    "example": ex.string, "example_doi": ex.first_doi,
                    "pymatgen_reads_it_as": ex.raw_pymatgen_amounts})
    cat = pd.DataFrame(cat).sort_values("development", ascending=False)
    cat.to_csv(OUT / "literature_hazard_catalogue.csv", index=False)
    return cat


if __name__ == "__main__" and "--catalogue" in sys.argv:
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 50)
    print(hazard_catalogue().to_string(index=False))
