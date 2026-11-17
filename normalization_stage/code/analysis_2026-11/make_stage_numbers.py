"""Write stage_numbers.tex (LaTeX macros) and stage_numbers_sources.csv for the normalization-stage results.
Every value is read from a result file; nothing is typed. Args: next_steps_dir g3_dir out_dir."""
import math, sys
from pathlib import Path
import pandas as pd
NS, G3D, OUT = map(Path, sys.argv[1:4])
EVAL = Path(sys.argv[4])   # next_steps_2026-11-04/package_copy/data/literature_strings_eval.csv
rows = []
def put(name, value, source, how):
    rows.append((name, value, source, how))
def fmt_int(n): return f"{int(n):,}".replace(",", "{,}")
def fmt_p(p):
    if p >= 0.01: return f"={p:.3g}"
    e = math.floor(math.log10(p)); m = p / 10 ** e
    return f"={m:.1f}\\times10^{{{e}}}"
def wilson(k, n, z=1.959964):
    ph = k / n; d = 1 + z * z / n; c = ph + z * z / (2 * n); h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
    return 100 * (c - h) / d, 100 * (c + h) / d
rd = lambda p: pd.read_csv(p, keep_default_na=False)
# ---------------- pool 1: sol-gel held-out targets (H2 run, 3 Nov)
f = "next_steps_2026-11-04/results/h2_heldout_outcomes.csv"; o = rd(NS / "results/h2_heldout_outcomes.csv").set_index("configuration")
put("StOneDet", fmt_int(o.loc["v03_strip", "determinate"]), f, "v03_strip determinate")
put("StOneAgree", fmt_int(o.loc["v03_strip", "determinate_agree"]), f, "v03_strip determinate_agree")
put("StOneAgreePct", f'{o.loc["v03_strip", "agree_pct"]:.1f}', f, "v03_strip agree_pct, 1 dp")
put("StOneDisc", fmt_int(o.loc["v03_strip", "discordant_returns"]), f, "v03_strip discordant_returns")
f = "next_steps_2026-11-04/results/h2_heldout_mcnemar.csv"; m = rd(NS / "results/h2_heldout_mcnemar.csv")
def mrow(df, a, b, ep): return df[(df.a == a) & (df.b == b) & (df.endpoint == ep)].iloc[0]
for tag, b in [("Pmg", "raw_pymatgen"), ("Vone", "v01_guarded"), ("Vtwo", "v02_package")]:
    r = mrow(m, "v03_strip", b, "determinate_agree")
    put(f"StOneGain{tag}", fmt_int(r.a_only - r.b_only), f, f"v03_strip vs {b} determinate_agree: a_only - b_only")
    put(f"StOneMcA{tag}", fmt_int(r.a_only), f, f"... a_only"); put(f"StOneMcB{tag}", fmt_int(r.b_only), f, f"... b_only")
    put(f"StOneP{tag}", fmt_p(r.p_exact_strings), f, "... p_exact_strings")
    put(f"StOneDoiA{tag}", fmt_int(r.doi_a_only), f, "... doi_a_only"); put(f"StOneDoiB{tag}", fmt_int(r.doi_b_only), f, "... doi_b_only")
    put(f"StOnePDoi{tag}", fmt_p(r.p_exact_dois), f, "... p_exact_dois")
    put(f"StOneDiff{tag}", f"{float(r.diff_points):.2f}", f, "... diff_points")
    put(f"StOneLo{tag}", f"{float(r.ci95_low):.2f}", f, "... ci95_low"); put(f"StOneHi{tag}", f"{float(r.ci95_high):.2f}", f, "... ci95_high")
r = mrow(m, "v03_strip", "v02_package", "discordant_return")
put("StOneNewDiscA", fmt_int(r.a_only), f, "v03_strip vs v02_package discordant_return a_only")
f = "next_steps_2026-11-04/results/h2_heldout_rescued_handchecked.csv"; h = rd(NS / "results/h2_heldout_rescued_handchecked.csv")
n1, w1, u1 = len(h), int(h.hand_check.eq("wrong_read").sum()), int(h.hand_check.eq("uncertain").sum())
put("StOneRescued", fmt_int(n1), f, "rows"); put("StOneRescuedAgree", fmt_int(h.v03_strip_outcome.eq("agree").sum()), f, "v03_strip_outcome == agree")
put("StOneWrong", str(w1), f, "hand_check == wrong_read"); put("StOneUncertain", str(u1), f, "hand_check == uncertain")
put("StOneCorrect", str(int(h.hand_check.eq("correct").sum())), f, "hand_check == correct")
put("StOneRescuedOther", str(int(h.stratum.eq("other").sum())), f, "stratum == other")
lo, hi = wilson(w1, n1); put("StOneWrongPct", f"{100*w1/n1:.1f}", f, "wrong/rows"); put("StOneWrongLo", f"{lo:.1f}", f, "Wilson 95% low"); put("StOneWrongHi", f"{hi:.1f}", f, "Wilson 95% high")
lo, hi = wilson(w1 + u1, n1); put("StOneWrongUPct", f"{100*(w1+u1)/n1:.1f}", f, "(wrong+uncertain)/rows"); put("StOneWrongULo", f"{lo:.1f}", f, "Wilson"); put("StOneWrongUHi", f"{hi:.1f}", f, "Wilson")
put("StOneThreshold", str(math.ceil(0.03 * o.loc["v03_strip", "determinate"])), "next_steps_2026-11-04/PREREGISTRATION_H2_12.md", "ceil(0.03 x determinate) = 43 as registered")
# ---------------- pool 2: fresh precursor strings (H2b run, 4 Nov)
f = "next_steps_2026-11-04/results_fresh/fresh_all_strings.csv"; a = rd(NS / "results_fresh/fresh_all_strings.csv")
put("StTwoStrings", fmt_int(len(a)), f, "rows"); put("StTwoDOIs", fmt_int(a.first_doi.nunique()), f, "unique first_doi")
for c, lab in [("determinate", "Det"), ("mixture", "Mix"), ("indeterminate", "Indet")]:
    put(f"StTwo{lab}", fmt_int(a.reference_class.eq(c).sum()), f, f"reference_class == {c}")
put("StTwoSolid", fmt_int(a.release.eq("solid-state").sum()), f, "release == solid-state"); put("StTwoSolgel", fmt_int(a.release.eq("sol-gel").sum()), f, "release == sol-gel")
f = "next_steps_2026-11-04/results_fresh/fresh_outcomes.csv"; o2 = rd(NS / "results_fresh/fresh_outcomes.csv").set_index("configuration")
for c, lab in [("raw_pymatgen", "Pmg"), ("v01_guarded", "Vone"), ("v02_package", "Vtwo"), ("v03_strip", "Strip"), ("v03b_guarded", "Stage")]:
    put(f"StTwoAgree{lab}", fmt_int(o2.loc[c, "determinate_agree"]), f, f"{c} determinate_agree")
    put(f"StTwoAgreePct{lab}", f'{o2.loc[c, "agree_pct"]:.1f}', f, f"{c} agree_pct, 1 dp")
    put(f"StTwoDisc{lab}", fmt_int(o2.loc[c, "discordant_returns"]), f, f"{c} discordant_returns")
f = "next_steps_2026-11-04/results_fresh/fresh_mcnemar.csv"; m2 = rd(NS / "results_fresh/fresh_mcnemar.csv")
for tag, b in [("Pmg", "raw_pymatgen"), ("Vone", "v01_guarded"), ("Vtwo", "v02_package")]:
    r = mrow(m2, "v03b_guarded", b, "determinate_agree")
    put(f"StTwoGain{tag}", fmt_int(r.a_only - r.b_only), f, f"v03b_guarded vs {b} determinate_agree: a_only - b_only")
    put(f"StTwoMcA{tag}", fmt_int(r.a_only), f, "... a_only"); put(f"StTwoMcB{tag}", fmt_int(r.b_only), f, "... b_only")
    put(f"StTwoP{tag}", fmt_p(r.p_exact_strings), f, "... p_exact_strings")
    put(f"StTwoDoiA{tag}", fmt_int(r.doi_a_only), f, "... doi_a_only"); put(f"StTwoDoiB{tag}", fmt_int(r.doi_b_only), f, "... doi_b_only")
    put(f"StTwoPDoi{tag}", fmt_p(r.p_exact_dois), f, "... p_exact_dois")
    put(f"StTwoDiff{tag}", f"{float(r.diff_points):.2f}", f, "... diff_points")
    put(f"StTwoLo{tag}", f"{float(r.ci95_low):.2f}", f, "... ci95_low"); put(f"StTwoHi{tag}", f"{float(r.ci95_high):.2f}", f, "... ci95_high")
r = mrow(m2, "v03b_guarded", "v02_package", "discordant_return")
put("StTwoNewDiscA", fmt_int(r.a_only), f, "v03b_guarded vs v02_package discordant_return a_only")
r = mrow(m2, "v03b_guarded", "v03_strip", "determinate_agree")
put("StTwoGuardCostB", str(int(r.b_only)), f, "v03b_guarded vs v03_strip determinate_agree b_only"); put("StTwoGuardCostP", fmt_p(r.p_exact_strings), f, "... p_exact_strings")
put("StTwoThreshold", str(math.ceil(0.03 * o2.loc["v03b_guarded", "determinate"])), "next_steps_2026-11-04/REPORT_12.md Addendum A1", "ceil(0.03 x determinate) = 104 as registered")
f = "next_steps_2026-11-04/results_fresh/fresh_refused_by_guard.csv"; g = rd(NS / "results_fresh/fresh_refused_by_guard.csv")
put("StTwoGuardRefused", str(len(g)), f, "rows")
f = "next_steps_2026-11-04/results_fresh/fresh_rescued_handchecked.csv"; h2 = rd(NS / "results_fresh/fresh_rescued_handchecked.csv")
s = h2[h2.in_registered_sample.astype(str).eq("True")]
n2, w2 = len(s), int(s.hand_check.eq("wrong_read").sum()); na, wa = len(h2), int(h2.hand_check.eq("wrong_read").sum())
put("StTwoRescued", fmt_int(na), f, "rows"); put("StTwoRescuedAgree", fmt_int(h2.v03b_guarded_outcome.eq("agree").sum()), f, "v03b_guarded_outcome == agree")
put("StTwoSample", str(n2), f, "in_registered_sample == True"); put("StTwoWrong", str(w2), f, "sample, hand_check == wrong_read")
lo, hi = wilson(w2, n2); put("StTwoWrongPct", f"{100*w2/n2:.1f}", f, "wrong/sample"); put("StTwoWrongLo", f"{lo:.1f}", f, "Wilson"); put("StTwoWrongHi", f"{hi:.1f}", f, "Wilson")
put("StTwoWrongAll", str(wa), f, "all rows, hand_check == wrong_read")
lo, hi = wilson(wa, na); put("StTwoWrongAllPct", f"{100*wa/na:.1f}", f, "wrong/all"); put("StTwoWrongAllLo", f"{lo:.1f}", f, "Wilson"); put("StTwoWrongAllHi", f"{hi:.1f}", f, "Wilson")
put("StTwoSuspect", str(int(h2.hand_check.eq("correct_faithful_suspect_source").sum())), f, "hand_check == correct_faithful_suspect_source")
# ---------------- G3, post hoc diagnostic
f = "revision_2026-11-05/g3_guard/posthoc/posthoc_outcomes.csv"; po = rd(G3D / "posthoc/posthoc_outcomes.csv")
gp = lambda pool, c, col: po[(po.pool == pool) & (po.configuration == c)][col].iloc[0]
put("GthreeTwoAgree", fmt_int(gp("pool2_fresh_precursors", "v03c_g3", "determinate_agree")), f, "pool2 v03c_g3 determinate_agree")
put("GthreeTwoAgreePct", f'{gp("pool2_fresh_precursors", "v03c_g3", "agree_pct"):.1f}', f, "pool2 v03c_g3 agree_pct")
put("GthreeOneAgree", fmt_int(gp("pool1_solgel_targets", "v03c_g3", "determinate_agree")), f, "pool1 v03c_g3 determinate_agree")
put("GuardOneAgree", fmt_int(gp("pool1_solgel_targets", "v03b_guarded", "determinate_agree")), f, "pool1 v03b_guarded determinate_agree (post hoc)")
f = "revision_2026-11-05/g3_guard/posthoc/posthoc_mcnemar.csv"; pm = rd(G3D / "posthoc/posthoc_mcnemar.csv")
r = pm[(pm.pool == "pool2_fresh_precursors") & (pm.b == "raw_pymatgen")].iloc[0]
put("GthreeTwoGainPmg", fmt_int(r.gain_strings), f, "pool2 v03c_g3 vs raw_pymatgen gain_strings")
put("GthreeTwoDiffPmg", f"{float(r.diff_points):.2f}", f, "diff_points"); put("GthreeTwoLoPmg", f"{float(r.ci95_low):.2f}", f, "ci95_low"); put("GthreeTwoHiPmg", f"{float(r.ci95_high):.2f}", f, "ci95_high")
put("GthreeTwoPPmg", fmt_p(r.p_exact_strings), f, "p_exact_strings")
r = pm[(pm.pool == "pool2_fresh_precursors") & (pm.b == "v03b_guarded")].iloc[0]
put("GthreeTwoCost", str(int(r.b_only)), f, "pool2 v03c_g3 vs v03b_guarded b_only"); put("GthreeTwoCostP", fmt_p(r.p_exact_strings), f, "p_exact_strings")
f = "revision_2026-11-05/g3_guard/posthoc/posthoc_refused_by_g3.csv"; pr = rd(G3D / "posthoc/posthoc_refused_by_g3.csv")
put("GthreeTwoRefused", str(int(pr.pool.eq("pool2_fresh_precursors").sum())), f, "pool2 rows")
put("GthreeOneRefused", str(int(pr.pool.eq("pool1_solgel_targets").sum())), f, "pool1 rows")
# ---------------- development release halves and rescued-string details
f = "next_steps_2026-11-04/package_copy/data/literature_strings_eval.csv"; ev = pd.read_csv(EVAL, keep_default_na=False, usecols=["split", "reference_class"])
put("StDevHalf", fmt_int(ev.split.eq("dev").sum()), f, "split == dev"); put("StDevTestHalf", fmt_int(ev.split.eq("test").sum()), f, "split == test")
put("StDevHalfDet", fmt_int((ev.split.eq("dev") & ev.reference_class.eq("determinate")).sum()), f, "split == dev & determinate")
put("StDevTestHalfDet", fmt_int((ev.split.eq("test") & ev.reference_class.eq("determinate")).sum()), f, "split == test & determinate")
f = "next_steps_2026-11-04/results_fresh/fresh_rescued_handchecked.csv"
put("StTwoRescuedOther", fmt_int(h2.stratum.eq("other").sum()), f, "stratum == other"); put("StTwoRescuedParen", fmt_int(h2.stratum.eq("parenthetical").sum()), f, "stratum == parenthetical")
put("StTwoRescuedPmgRefused", fmt_int(h2.raw_pymatgen_outcome.eq("refused").sum()), f, "raw_pymatgen_outcome == refused")
put("StOneRescuedPmgRefused", fmt_int(h.raw_pymatgen_outcome.eq("refused").sum()), "next_steps_2026-11-04/results/h2_heldout_rescued_handchecked.csv", "raw_pymatgen_outcome == refused")
# ---------------- write
tex = ["% Generated by make_stage_numbers.py from the result files listed in stage_numbers_sources.csv -- do not edit by hand."]
tex += [f"\\newcommand{{\\{n}}}{{{v}}}" for n, v, _, _ in rows]
(OUT / "stage_numbers.tex").write_text("\n".join(tex) + "\n")
pd.DataFrame(rows, columns=["macro", "value", "source_file", "field"]).to_csv(OUT / "stage_numbers_sources.csv", index=False)
for n, v, _, _ in rows: print(n, v)
