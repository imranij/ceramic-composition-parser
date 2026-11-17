"""POST HOC DIAGNOSTIC (not a held-out test). Scores the frozen G3 guard on the two spent held-out pools.
Both pools were used before G3 was designed, and the G3 designer had seen the pool-2 wrong reads.
Args: code_dir frozen_sha_file paper_next_steps_dir out_dir."""
import hashlib, math, sys
from pathlib import Path
import numpy as np, pandas as pd
CODE, FROZEN, NS, OUT = map(Path, sys.argv[1:5])
sys.path.insert(0, str(CODE))
for line in FROZEN.read_text().splitlines()[:3]:
    h, f = line.split()
    assert hashlib.sha256((CODE / f).read_bytes()).hexdigest() == h, f"{f} changed after freeze"
import composition_normalise_guarded as G
import composition_normalise_g3 as G3

def mcnemar_exact(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)

def g3_outcome(s, prev_outcome):
    """prev_outcome: outcome of the configuration G3 builds on for this string."""
    if prev_outcome == "refused":
        return "refused", ""
    try:
        G3.parse_formula_g3(s); return prev_outcome, ""
    except Exception:
        return "refused", G3.G3_LOG.get(s, "refused_upstream")

def h2b_outcome(s, h2_outcome):
    if h2_outcome == "refused":
        return "refused"
    try:
        G.parse_formula_guarded(s); return h2_outcome
    except Exception:
        return "refused"

pools = {
  "pool1_solgel_targets": (NS / "results/h2_heldout_all_strings.csv", NS / "results/h2_heldout_rescued_handchecked.csv"),
  "pool2_fresh_precursors": (NS / "results_fresh/fresh_all_strings.csv", NS / "results_fresh/fresh_rescued_handchecked.csv"),
}
lines = ["POST HOC DIAGNOSTIC. Both pools were spent before G3 was designed. Not a held-out test.", ""]
summary, mcrows, refused_rows = [], [], []
for name, (allf, hcf) in pools.items():
    df = pd.read_csv(allf, keep_default_na=False)
    if "v03b_guarded_outcome" not in df:
        df["v03b_guarded_outcome"] = [h2b_outcome(s, o) for s, o in zip(df.string, df.v03_strip_outcome)]
    out, why = [], []
    for s, o, v2 in zip(df.string, df.v03b_guarded_outcome, df.v02_package_outcome):
        if v2 != "refused":                 # G3 never touches strings v0.2.0 resolves
            out.append(v2); why.append(""); continue
        a, b = g3_outcome(s, o); out.append(a); why.append(b)
    df["v03c_g3_outcome"], df["g3_reason"] = out, why
    det = df.reference_class.eq("determinate")
    for c in ["raw_pymatgen", "v01_guarded", "v02_package", "v03_strip", "v03b_guarded", "v03c_g3"]:
        o = df[f"{c}_outcome"]
        summary.append({"pool": name, "configuration": c, "determinate": int(det.sum()),
                        "determinate_agree": int((det & o.eq("agree")).sum()),
                        "agree_pct": round(100 * (det & o.eq("agree")).sum() / det.sum(), 2),
                        "discordant_returns": int(o.isin(["disagree", "returned"]).sum())})
    rng = np.random.default_rng(20261104)
    udoi, inv = np.unique(df.first_doi.values, return_inverse=True)
    for b in ["raw_pymatgen", "v01_guarded", "v03b_guarded", "v02_package"]:
        fa, fb = df.v03c_g3_outcome.eq("agree"), df[f"{b}_outcome"].eq("agree")
        oa, ob = int((fa & ~fb).sum()), int((~fa & fb).sum())
        dv = (fa.astype(int) - fb.astype(int)).values * det.values
        pd_, pn = np.bincount(inv, weights=dv), np.bincount(inv, weights=det.values.astype(float))
        bs = [100 * pd_[i].sum() / pn[i].sum() for i in (rng.integers(0, len(udoi), len(udoi)) for _ in range(4000))]
        ea = df.v03c_g3_outcome.isin(["disagree", "returned"]); eb = df[f"{b}_outcome"].isin(["disagree", "returned"])
        mcrows.append({"pool": name, "a": "v03c_g3", "b": b, "gain_strings": oa - ob, "a_only": oa, "b_only": ob,
                       "p_exact_strings": mcnemar_exact(oa, ob), "diff_points": round(100 * dv.sum() / det.sum(), 2),
                       "ci95_low": round(float(np.percentile(bs, 2.5)), 2), "ci95_high": round(float(np.percentile(bs, 97.5)), 2),
                       "discordant_a_only": int((ea & ~eb).sum()), "discordant_b_only": int((~ea & eb).sum())})
    ref = df[df.g3_reason.str.startswith("G3")]
    for _, r in ref.iterrows():
        refused_rows.append({"pool": name, "string": r.string, "reference_class": r.reference_class,
                             "reference_amounts": r.reference_amounts, "h2b_outcome": r.v03b_guarded_outcome,
                             "g3_reason": r.g3_reason})
    # wrong reads among the hand-checked rescued strings
    hc = pd.read_csv(hcf, keep_default_na=False)
    g3_ref = set(ref.string)
    stillin = hc[~hc.string.isin(g3_ref) & hc.string.isin(df.loc[df.v03c_g3_outcome.ne("refused"), "string"])]
    lines.append(f"[{name}] H2b-or-H2 rescued strings hand-checked: {len(hc)}; H2b guard refuses {int((~hc.string.isin(set(df.loc[df.v03b_guarded_outcome.ne('refused'), 'string']))).sum())}, G3 refuses {int(hc.string.isin(g3_ref).sum())} of them; "
                 f"still returned after G3: {len(stillin)}")
    for subset, lab in [(hc, "all hand-checked"), (hc[hc.get('in_registered_sample', pd.Series(True, index=hc.index)).astype(str).eq('True')], "registered sample")]:
        wr = subset[subset.hand_check.eq("wrong_read")]
        returned_c = set(df.loc[df.v03c_g3_outcome.ne("refused"), "string"])
        returned_b = set(df.loc[df.v03b_guarded_outcome.ne("refused"), "string"])
        lb = wr[wr.string.isin(returned_b)]; left = wr[wr.string.isin(returned_c)]
        lines.append(f"   {lab}: n={len(subset)}, wrong reads returned by H2 {len(wr)}, by H2b {len(lb)}, by H2b+G3 {len(left)}: {list(left.string)}")
    unc = hc[hc.hand_check.eq("uncertain")]
    if len(unc):
        lines.append(f"   uncertain reads: {len(unc)}, still returned by H2b+G3: {int(unc.string.isin(set(df.loc[df.v03c_g3_outcome.ne('refused'), 'string'])).sum())}")
    lines.append(f"   strings refused by G3 in this pool: {len(ref)} -> {list(zip(ref.string, ref.g3_reason, ref.v03b_guarded_outcome))}")
    lines.append("")
    df.to_csv(OUT / f"posthoc_{name}_all_strings.csv", index=False)
pd.DataFrame(summary).to_csv(OUT / "posthoc_outcomes.csv", index=False)
pd.DataFrame(mcrows).to_csv(OUT / "posthoc_mcnemar.csv", index=False)
pd.DataFrame(refused_rows).to_csv(OUT / "posthoc_refused_by_g3.csv", index=False)
pd.set_option("display.width", 250)
lines += [pd.DataFrame(summary).to_string(index=False), "", pd.DataFrame(mcrows).to_string(index=False)]
(OUT / "posthoc_diagnostic_log.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
