"""Write every number the revised manuscript quotes as a LaTeX macro, and its tables.

Nothing in ``manuscript/main.tex`` is typed by hand that a file below can supply:
the text uses ``\\NDevStrings`` and the like, and the tables are ``\\input`` from the
``generated_*.tex`` files written here. Re-running this script after any change to
the data regenerates the numbers; ``tests/test_reproduces_published_tables.py``
fails if the committed macros differ from a fresh run.
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from composition_parser import FLAG_CLASS, PARSER_VERSION  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RES = DATA / "processed_results"
MS = ROOT / "manuscript"

CFG = ["v02_package", "v01_guarded", "v01_fallback", "raw_pymatgen"]
CFG_TEX = {"v02_package": "v0.2.0 package", "v02_grammar": "v0.2.0 grammar alone",
           "v01_guarded": "v0.1.0 as submitted", "v01_fallback": "v0.1.0 grammar alone",
           "raw_pymatgen": "raw \\texttt{pymatgen}"}
CFG_MACRO = {"v02_package": "Vtwo", "v02_grammar": "VtwoGr", "v01_guarded": "Vone",
             "v01_fallback": "VoneFb", "raw_pymatgen": "Pmg"}


def n(x) -> str:
    return f"{int(x):,}".replace(",", "{,}")


def pct(a, b, d=1) -> str:
    return f"{100 * a / b:.{d}f}"


def pval(p: float) -> str:
    """Relation and value, for use as $p\\Macro$ in math mode."""
    if p >= 1e-3:
        return f"={p:.2f}" if p >= 0.01 else f"={p:.3f}"
    k = math.floor(-math.log10(p))
    return f"<10^{{-{k}}}"


def tex_escape(s: str) -> str:
    return (str(s).replace("\\", r"\textbackslash{}").replace("_", r"\_").replace("%", r"\%")
            .replace("&", r"\&").replace("#", r"\#").replace("δ", r"$\delta$").replace("·", r"$\cdot$"))


def main() -> None:
    M: dict[str, str] = {"ParserVersion": PARSER_VERSION}
    # ------------------------------------------------------------------ corpus
    cb = pd.read_csv(RES / "corpus_backend_check.csv").set_index("source_dataset")
    M["NCorpus"] = n(cb.loc["TOTAL", "formulas"])
    M["NCorpusDatasets"] = str(len(cb) - 1)
    M["NCorpusDistinct"] = n(pd.read_csv(DATA / "paper2_parsed_composition_vectors.csv", usecols=["formula"]).formula.nunique())
    st = pd.read_csv(DATA / "stress_benchmark.csv")
    sd = pd.read_csv(DATA / "dopant_notation_benchmark.csv")
    M["NStress"] = str(len(st)); M["NStressFamilies"] = str(st.family.nunique())
    M["NSeed"] = str(len(sd)); M["NBench"] = str(len(st) + len(sd))
    agree_all = all(int(cb.loc["TOTAL", f"{c}_matches_committed"]) == int(cb.loc["TOTAL", "formulas"])
                    for c in CFG + ["v02_grammar"])
    if not agree_all:
        raise SystemExit("corpus: a configuration no longer reproduces the committed vectors")
    dup = pd.read_csv(RES / "corpus_duplicate_compositions.csv").set_index("source_dataset")
    M["NCorpusReduced"] = n(dup.loc["ALL", "distinct_reduced_compositions"])
    M["NCorpusCrossDataset"] = n(dup.loc["ALL", "compositions_in_more_than_one_dataset"])
    cov = pd.read_csv(DATA / "paper2_parser_source_coverage.csv")
    M["NCorpusParen"] = n(cov.formulas_with_parentheses.sum())
    M["PctCorpusParen"] = pct(cov.formulas_with_parentheses.sum(), cov.total_unique_formulas.sum(), 2)
    M["NCorpusDecimal"] = n(cov.formulas_with_decimal_stoichiometry.sum())
    # dielectric subset (downstream illustration)
    vec = pd.read_csv(DATA / "paper2_parsed_composition_vectors.csv")
    d = vec[vec.source_dataset == "dielectric_constant"]
    fc = [c for c in d.columns if c.startswith("frac_")]
    systems = d[fc].gt(0).apply(lambda r: "-".join(sorted(c[5:] for c, b in r.items() if b)), axis=1)
    vc = systems.value_counts()
    M["NDiel"] = n(len(d))
    M["NDielReduced"] = n(dup.loc["dielectric_constant", "distinct_reduced_compositions"])
    M["NDielSystems"] = n(vc.size)
    M["NDielSharedSystems"] = n((vc > 1).sum())
    M["NDielInSharedSystems"] = n(vc[vc > 1].sum())

    # ------------------------------------------------------ hand-written benchmarks
    nb = pd.read_csv(RES / "notation_benchmarks_summary.csv")
    nb = nb.set_index(["subset", "configuration"])
    for c in CFG + ["v02_grammar"]:
        k = CFG_MACRO[c]
        M[f"BenchSilent{k}"] = str(int(nb.loc[("pooled51", c), "silent_mis_parses"]))
        M[f"BenchExact{k}"] = str(int(nb.loc[("pooled51", c), "resolvable_exact"]))
        M[f"BenchFalseRef{k}"] = str(int(nb.loc[("pooled51", c), "resolvable_false_refusals"]))
        M[f"BenchCorrect{k}"] = str(int(nb.loc[("pooled51", c), "correct"]))
    M["BenchResolvable"] = str(int(nb.loc[("pooled51", "v02_package"), "resolvable_n"]))
    M["BenchAmbiguous"] = str(int(nb.loc[("pooled51", "v02_package"), "ambiguous_n"]))
    write_benchmark_table(nb)

    # --------------------------------------------------------- literature corpora
    out = pd.read_csv(RES / "literature_outcomes.csv")
    dev = pd.read_csv(DATA / "literature_strings_eval.csv")
    ho = pd.read_csv(DATA / "literature_strings_heldout_solgel.csv")
    for tag, df, setname in [("Dev", dev, "development"), ("Ho", ho, "heldout")]:
        M[f"N{tag}Strings"] = n(len(df))
        M[f"N{tag}DOIs"] = n(df.first_doi.nunique())
        o = out[out.set == setname].set_index("configuration")
        M[f"N{tag}Det"] = n(o.loc["v02_package", "determinate"])
        M[f"N{tag}Indet"] = n(o.loc["v02_package", "indeterminate"])
        M[f"N{tag}Mix"] = n(o.loc["v02_package", "mixture"])
        for c in CFG + ["v02_grammar"]:
            k = CFG_MACRO[c]
            M[f"{tag}Agree{k}"] = n(o.loc[c, "determinate_agree"])
            M[f"{tag}AgreePct{k}"] = pct(o.loc[c, "determinate_agree"], o.loc[c, "determinate"])
            M[f"{tag}Disc{k}"] = n(o.loc[c, "discordant_returns"])
            M[f"{tag}Dummy{k}"] = n(o.loc[c, "of_which_dummy_species"])
            M[f"{tag}DiscExDummy{k}"] = n(o.loc[c, "discordant_excluding_dummy"])
            M[f"{tag}Refused{k}"] = n(o.loc[c, "determinate_refused"])
        det = df[df.reference_class == "determinate"]
        M[f"{tag}GrammarOnly"] = n(df.v02_package_detail.eq("resolved:grammar_only_pymatgen_refused").sum())
        M[f"{tag}BackendDisagree"] = n(df.v02_package_detail.str.contains("backend_disagreement").sum())
        reasons = df[df.reference_class == "indeterminate"].reference_reason.value_counts()
        for r, macro in [("free_variable_amount", "FreeVar"), ("free_variable_coefficient", "FreeCoef"),
                         ("oxygen_deficiency_marker", "OxDef"), ("element_variable", "ElVar"),
                         ("unquantified_dopant_in_string", "UnqDopant"), ("nonpositive_amount", "ZeroAmt")]:
            M[f"{tag}Reason{macro}"] = n(reasons.get(r, 0))
        _ = det
    M["NHoDoiInDev"] = n(ho.loc[ho.doi_in_dev, "first_doi"].nunique())
    M["NLitStrings"] = n(len(dev) + len(ho))
    M["NLitDOIs"] = n(pd.concat([dev.first_doi, ho.first_doi]).nunique())

    mc = pd.read_csv(RES / "literature_mcnemar.csv")

    def mrow(setname, a, b, endpoint):
        r = mc[(mc.set == setname) & (mc.a == a) & (mc.b == b) & (mc.endpoint == endpoint)].iloc[0]
        return r

    for tag, setname in [("Dev", "development"), ("Ho", "heldout")]:
        for b, kb in [("raw_pymatgen", "Pmg"), ("v01_guarded", "Vone")]:
            for ep, ke in [("discordant_return", "Disc"), ("discordant_return_excluding_dummy", "DiscExDummy"),
                           ("determinate_agree", "Agree")]:
                r = mrow(setname, "v02_package", b, ep)
                M[f"{tag}Mc{ke}{kb}A"] = n(r.a_only)
                M[f"{tag}Mc{ke}{kb}B"] = n(r.b_only)
                M[f"{tag}Mc{ke}{kb}P"] = pval(r.p_exact_strings)
                M[f"{tag}Mc{ke}{kb}PDoi"] = pval(r.p_exact_dois)

    disc = pd.read_csv(RES / "literature_discordant_v02.csv")
    M["NVtwoDiscTotal"] = n(len(disc))
    cost = pd.read_csv(RES / "literature_refusal_cost.csv")
    M["DevCost"] = n((cost.set == "development").sum())
    M["HoCost"] = n((cost.set == "heldout").sum())
    for cat, macro in [("core_shell_or_composite_at_sign", "At"), ("whitespace_separated_phases_or_labels", "Space"),
                       ("single_element_group_dopant", "Group"), ("dot_ambiguous_decimal_or_adduct", "Dot"),
                       ("hydrate_dot", "Hydrate"), ("other", "Other")]:
        for tag, setname in [("Dev", "development"), ("Ho", "heldout")]:
            M[f"{tag}Cost{macro}"] = n(((cost.set == setname) & (cost.category == cat)).sum())
    mix = pd.read_csv(RES / "literature_mixture_layer.csv").set_index("set")
    for tag, setname in [("Dev", "development"), ("Ho", "heldout")]:
        M[f"{tag}MixAgree"] = n(mix.loc[setname, "agree"])
        M[f"{tag}MixRefused"] = n(mix.loc[setname, "refused"])
        M[f"{tag}MixDisagree"] = n(0 if pd.isna(mix.loc[setname].get("disagree")) else mix.loc[setname, "disagree"])
    cat = pd.read_csv(RES / "literature_hazard_catalogue.csv")
    M["NHazDev"] = n(cat.development.sum())
    M["NHazHo"] = n(cat.heldout.sum())
    M["NHazClasses"] = str(len(cat))
    M["NHazVone"] = n(cat.v01_also_returned.sum())
    # the removed doubled-symbol rule: how many database formulas it would refuse
    from composition_parser import _scan
    def doubled_digit_free(f: str) -> bool:
        toks, _l, _u = _scan("".join(str(f).split()))
        return (not any(t[0] == "num" for t in toks)
                and any(a[0] == b[0] == "el" and a[1] == b[1] for a, b in zip(toks, toks[1:])))
    M["NRemovedRuleCorpus"] = n(sum(doubled_digit_free(f) for f in vec["formula"]))
    M["NFlags"] = str(len(FLAG_CLASS))
    ann = pd.read_csv(ROOT / "annotation" / "expert_annotation_sample.csv")
    M["NAnnotation"] = n(len(ann))
    write_literature_table(out)
    write_hazard_table(cat)
    write_rules_table()
    write_provenance_table(cov)

    lines = ["% Generated by code/make_manuscript_numbers.py -- do not edit by hand."]
    for k in sorted(M):
        lines.append(f"\\newcommand{{\\{k}}}{{{M[k]}}}")
    (MS / "generated_numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(M)} macros")


def write_benchmark_table(nb: pd.DataFrame) -> None:
    rows = [r"\begin{table}[!t]", r"\centering",
            r"\caption{The 51 hand-written strings, scored by exact element amounts. $R$: resolvable "
            r"strings returned with the exact expected amounts; FR: resolvable strings refused (false "
            r"refusals); $A$: ambiguous strings refused; SM: silent mis-parses (a composition returned "
            r"for an ambiguous string, or a wrong one for a resolvable string). Labels are those of the "
            r"submitted version. These are constructed challenge sets, not samples, so no interval is "
            r"attached to any count. One of raw \texttt{pymatgen}'s three SM, \texttt{Xx2O3}, is a "
            r"\texttt{DummySpecies} return, a mismatch with a schema restricted to real elements.}",
            r"\label{tab:benchmarks}", r"\footnotesize", r"\setlength{\tabcolsep}{3pt}",
            r"\begin{tabular}{@{}lcccccccc@{}}", r"\toprule",
            r" & \multicolumn{3}{c}{Stress test (17 + 7)} & \multicolumn{3}{c}{Seed set (21 + 6)} & "
            r"\multicolumn{2}{c}{Pooled 51} \\",
            r"\cmidrule(lr){2-4}\cmidrule(lr){5-7}\cmidrule(l){8-9}",
            r"Configuration & $R$ & FR & $A$ & $R$ & FR & $A$ & SM & Correct \\", r"\midrule"]
    for c in ["v02_package", "v02_grammar", "v01_guarded", "v01_fallback", "raw_pymatgen"]:
        s, d, p = nb.loc[("stress24", c)], nb.loc[("seed27", c)], nb.loc[("pooled51", c)]
        rows.append(f"{CFG_TEX[c]} & {s.resolvable_exact} & {s.resolvable_false_refusals} & "
                    f"{s.ambiguous_refused} & {d.resolvable_exact} & {d.resolvable_false_refusals} & "
                    f"{d.ambiguous_refused} & {p.silent_mis_parses} & {p.correct}/{p.n} \\\\")
    rows += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    (MS / "generated_benchmark_table.tex").write_text("\n".join(rows), encoding="utf-8")


def write_literature_table(out: pd.DataFrame) -> None:
    rows = [r"\begin{table*}[!t]", r"\centering",
            r"\caption{Literature strings, by reference class and outcome. Agree: a determinate string "
            r"resolved to the reference composition (same elements, atomic fractions within $10^{-3}$). "
            r"Refused: any refusal. Disagree: a composition that differs from a determinate reference. "
            r"Returned: a composition for a string whose reference is indeterminate or a multi-component "
            r"mixture. Discordant returns = disagree + returned; they are candidates for silent "
            r"mis-parses, not confirmed errors (Section~\ref{sec:lit_dev}). Dummy: discordant returns that "
            r"contain a \texttt{pymatgen} \texttt{DummySpecies}.}",
            r"\label{tab:literature}", r"\footnotesize", r"\setlength{\tabcolsep}{4pt}",
            r"\begin{tabular}{@{}llrrrrrrr@{}}", r"\toprule",
            r" & & \multicolumn{3}{c}{Determinate} & Indeterminate & Mixture & \multicolumn{2}{c}{Discordant returns} \\",
            r"\cmidrule(lr){3-5}\cmidrule(lr){6-6}\cmidrule(lr){7-7}\cmidrule(l){8-9}",
            r"Set & Configuration & Agree & Refused & Disagree & Returned & Returned & All & Dummy \\",
            r"\midrule"]
    for setname, label in [("development", "Development"), ("heldout", "Held-out")]:
        o = out[out.set == setname].set_index("configuration")
        first = True
        for c in ["v02_package", "v01_guarded", "v01_fallback", "raw_pymatgen"]:
            r = o.loc[c]
            head = (f"{label} ($n={n(r.strings)}$; {n(r.determinate)} / {n(r.indeterminate)} / "
                    f"{n(r.mixture)})") if first else ""
            rows.append(f"{head} & {CFG_TEX[c]} & {n(r.determinate_agree)} & {n(r.determinate_refused)} & "
                        f"{n(r.determinate_disagree)} & {n(r.indeterminate_returned)} & {n(r.mixture_returned)} & "
                        f"{n(r.discordant_returns)} & {n(r.of_which_dummy_species)} \\\\")
            first = False
        rows.append(r"\midrule" if setname == "development" else r"\bottomrule")
    rows += [r"\end{tabular}", r"\end{table*}", ""]
    (MS / "generated_literature_table.tex").write_text("\n".join(rows), encoding="utf-8")


HAZ_LABEL = {
    "unknown_element_symbol:dummy_species": "placeholder symbol accepted as a \\texttt{DummySpecies}",
    "non_formula_word": "label or second phase joined across a space",
    "unconsumed_separator": "core--shell or composite \\texttt{@} ignored",
    "single_element_group": "parenthesised dopant read as one atom",
    "nonpositive_amount": "zero subscript dropped",
    "unknown_element_symbol:isotope_letter_as_H": "acronym letter T or D read as hydrogen",
    "hydration_or_dot_notation": "dot read as a decimal point",
    "mixture_or_arithmetic_notation": "hyphen read as a negative subscript",
}


def write_hazard_table(cat: pd.DataFrame) -> None:
    rows = [r"\begin{table*}[!t]", r"\centering",
            r"\caption{Catalogue of candidate notation hazards in the literature corpora: strings that raw "
            r"\texttt{pymatgen} resolves with no diagnostic and that the v0.2.0 screen refuses, because the "
            r"string alone does not settle its reading or is not a single formula. They are candidates, not "
            r"confirmed errors. Classes are named by the v0.2.0 refusal flag. "
            r"``v0.1'' counts the strings of the class that the submitted version also returned. The example "
            r"is the shortest development-set instance; its source is given by DOI.}",
            r"\label{tab:hazards}", r"\footnotesize", r"\setlength{\tabcolsep}{4pt}",
            r"\begin{tabular}{@{}p{4.8cm}rrrlp{3.0cm}p{2.4cm}@{}}", r"\toprule",
            r"Hazard (v0.2.0 flag) & Dev. & Held-out & v0.1 & Example & Source DOI & \texttt{pymatgen} reads \\",
            r"\midrule"]
    for _, r in cat.iterrows():
        flag = r.hazard.split(":")[0]
        rows.append(f"{HAZ_LABEL.get(r.hazard, r.hazard)}\\newline\\texttt{{\\scriptsize {tex_escape(flag)}}} & {n(r.development)} & "
                    f"{n(r.heldout)} & {n(r.v01_also_returned)} & \\texttt{{{tex_escape(r.example)}}} & "
                    f"{{\\scriptsize\\url{{{r.example_doi}}}}} & "
                    f"{tex_escape(r.pymatgen_reads_it_as).replace(';', ', ')} \\\\")
    rows += [r"\midrule",
             f"Total & {n(cat.development.sum())} & {n(cat.heldout.sum())} & {n(cat.v01_also_returned.sum())} & & & \\\\",
             r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]
    (MS / "generated_hazard_table.tex").write_text("\n".join(rows), encoding="utf-8")


RULES = [
    ("comma_site_fraction_missing", "any comma", "(Ba,Sr)TiO3"),
    ("hydration_or_dot_notation", "middle dot; \\texttt{.nH2O}; a dot not preceded by a digit (unless followed by 0)", "Li2O.2SiO2"),
    ("free_variable_stoichiometry", "x, y, z, $\\delta$, $\\pm$ outside an element symbol", "Ba1-xSrxTiO3"),
    ("dopant_convention_missing", "a colon", "Y2O3:Eu"),
    ("unit_convention_missing", "a percent sign; at\\% without a count convention", "CaSc2O4:1%Ce3+"),
    ("charge_balance_unspecified", "element, digits, then a sign", "Ba2+Ti4+O3"),
    ("single_element_group", "a group holding one bare symbol, no multiplier", "La(Sr)GaO3"),
    ("nonpositive_amount", "a zero subscript or multiplier", "BaW0"),
    ("mixture_or_arithmetic_notation", "+, -, =, /, \\textasciicircum, \\textasciitilde{} outside a rational subscript; a leading coefficient", "BaO-2SiO2"),
    ("non_formula_word", "lower-case letters outside symbols; a space separating words or phases", "Pt Nb2O5"),
    ("unknown_element_symbol", "a capitalised token not among the 118 symbols (incl. D, T, M, Ln, Xx)", "MS2"),
    ("unconsumed_separator", "any other character, e.g.\\ \\texttt{@}", "CdS@ZrO2"),
    ("malformed_grouping", "unmatched or mismatched brackets", "Ba(Ti0.9Zr0.1]O3"),
    ("backend_disagreement", "grammar and \\texttt{pymatgen} return different compositions", "--"),
    ("manual_validation_required", "empty input or no element", "--"),
]


def write_rules_table() -> None:
    if {r[0] for r in RULES} != set(FLAG_CLASS):
        raise SystemExit("rules table and FLAG_CLASS differ")
    rows = [r"\begin{table*}[!t]", r"\centering",
            r"\caption{The shared screen and grammar refusals, with their controlled flag and status class "
            r"(A: \texttt{ambiguous\_rejected}, the string does not determine a composition; U: "
            r"\texttt{unsupported\_rejected}, not a single formula in this grammar; E: \texttt{parse\_error}). "
            r"A refusal carries every flag that applies, not only the first.}",
            r"\label{tab:rules}", r"\footnotesize", r"\setlength{\tabcolsep}{4pt}",
            r"\begin{tabular}{@{}lcp{8.2cm}l@{}}", r"\toprule",
            r"Flag & Class & Trigger & Example \\", r"\midrule"]
    for flag, trig, ex in RULES:
        cls = {"ambiguous": "A", "unsupported": "U", "error": "E"}[FLAG_CLASS[flag]]
        rows.append(f"\\texttt{{{tex_escape(flag)}}} & {cls} & {trig} & "
                    f"{'--' if ex == '--' else chr(92) + 'texttt{' + tex_escape(ex) + '}'} \\\\")
    rows += [r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]
    (MS / "generated_rules_table.tex").write_text("\n".join(rows), encoding="utf-8")


DATASET_BIB = {"castelli_perovskites": "castelli2012perovskites", "dielectric_constant": "petousis2017dielectric",
               "double_perovskites_gap": "pilania2016doubleperovskites", "phonon_dielectric_mp": "petretto2018phonons",
               "piezoelectric_tensor": "dejong2015piezo", "wolverton_oxides": "emery2017perovskites"}


def write_provenance_table(cov: pd.DataFrame) -> None:
    import matminer
    meta = json.load(open(os.path.join(os.path.dirname(matminer.__file__), "datasets", "dataset_metadata.json")))
    rows = [r"\begin{table*}[!t]", r"\centering",
            r"\caption{Provenance of the six database corpora: the figshare file identifier and SHA-256 that "
            r"matminer~0.10.1 records for each named dataset, its row count, and the unique formula strings "
            r"retained. Normalization: rows with a missing formula are dropped, formulas are "
            r"compared as exact strings, and duplicate (formula, dataset) pairs are removed; formulas repeated "
            r"across datasets are kept in each. Dec./Par.: formulas with decimal subscripts / parentheses.}",
            r"\label{tab:provenance}", r"\footnotesize", r"\setlength{\tabcolsep}{4pt}",
            r"\begin{tabular}{@{}llllrrrrr@{}}", r"\toprule",
            r"matminer dataset & Source & figshare file & SHA-256 (first 16) & Rows & Unique & Dec. & Par. & $\bar n_{\mathrm{el}}$ \\",
            r"\midrule"]
    for _, r in cov.sort_values("total_unique_formulas", ascending=False).iterrows():
        ds = r.source_dataset
        md = meta[ds]
        fid = md["url"].rsplit("/", 1)[-1]
        rows.append(f"\\texttt{{{tex_escape(ds)}}} & \\cite{{{DATASET_BIB[ds]}}} & {fid} & "
                    f"\\texttt{{{md['hash'][:16]}}} & {n(md['num_entries'])} & {n(r.total_unique_formulas)} & "
                    f"{int(r.formulas_with_decimal_stoichiometry)} & {int(r.formulas_with_parentheses)} & "
                    f"{r.mean_n_elements:.2f} \\\\")
    rows += [r"\midrule",
             f"Total & & & & & {n(cov.total_unique_formulas.sum())} & {int(cov.formulas_with_decimal_stoichiometry.sum())} & "
             f"{int(cov.formulas_with_parentheses.sum())} & \\\\",
             r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]
    (MS / "generated_provenance_table.tex").write_text("\n".join(rows), encoding="utf-8")


if __name__ == "__main__":
    main()
