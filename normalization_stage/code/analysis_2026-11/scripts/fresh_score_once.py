"""Score the frozen H2b stage ONCE on the fresh precursor-string set (paper 12, 4 Nov 2026).
Args: code_dir pool_csv out_dir frozen_sha_file. Checks both SHA-256 values first.
Configurations: raw_pymatgen, v01_guarded, v02_package, v03_strip (H2, secondary), v03b_guarded (H2b, decision)."""
import hashlib, math, sys
from pathlib import Path
import numpy as np, pandas as pd
CODE, POOL, OUT, FROZEN = map(Path, sys.argv[1:5])
sys.path.insert(0, str(CODE))
for line in FROZEN.read_text().splitlines()[:2]:
    h, f = line.split()
    assert hashlib.sha256((CODE / f).read_bytes()).hexdigest() == h, f"{f} changed after freeze"
from literature_eval import run_parser, fractions_match
from composition_parser import ELEMENT_SYMBOLS
from composition_normalise import parse_formula_normalised
import composition_normalise_guarded as G

def amounts_of(s):
    return {k: float(v) for k, v in (p.split(":") for p in s.split(";"))} if s else None
def mcnemar_exact(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)

df = pd.read_csv(POOL, keep_default_na=False)
def run(name, s):
    if name == "v03_strip":
        try: a, _, f = parse_formula_normalised(s); return a, "|".join(f)
        except Exception: return None, ""
    if name == "v03b_guarded":
        try: a, _, f = G.parse_formula_guarded(s); return a, "|".join(f)
        except Exception: return None, G.GUARD_LOG.get(s, "")
    a, det = run_parser(name, s); return a, det
CONF = ["raw_pymatgen", "v01_guarded", "v02_package", "v03_strip", "v03b_guarded"]
for c in CONF:
    out, amt, det_, mech = [], [], [], []
    for s, cls, ref in zip(df.string, df.reference_class, df.reference_amounts):
        got, d = run(c, s); det_.append(d)
        if got is None: out.append("refused"); amt.append(""); mech.append(""); continue
        amt.append(";".join(f"{k}:{got[k]:g}" for k in sorted(got)))
        dummy = bool(set(got) - ELEMENT_SYMBOLS)
        if cls == "determinate":
            ok = not dummy and fractions_match(got, amounts_of(ref))
            out.append("agree" if ok else "disagree"); mech.append("" if ok else ("dummy_species_accepted" if dummy else "differs"))
        else:
            out.append("returned"); mech.append("dummy_species_accepted" if dummy else "returned_despite_" + cls)
    df[f"{c}_outcome"], df[f"{c}_amounts"], df[f"{c}_detail"], df[f"{c}_mechanism"] = out, amt, det_, mech
det = df.reference_class.eq("determinate")
rows = []
for c in CONF:
    o = df[f"{c}_outcome"]; disc = o.isin(["disagree", "returned"]); dm = df[f"{c}_mechanism"].eq("dummy_species_accepted")
    rows.append({"configuration": c, "strings": len(df), "determinate": int(det.sum()),
                 "determinate_agree": int((det & o.eq("agree")).sum()),
                 "agree_pct": round(100 * (det & o.eq("agree")).sum() / det.sum(), 2),
                 "determinate_refused": int((det & o.eq("refused")).sum()),
                 "determinate_disagree": int((det & o.eq("disagree")).sum()),
                 "nondeterminate_returned": int(o.eq("returned").sum()),
                 "discordant_returns": int(disc.sum()), "discordant_excluding_dummy": int((disc & ~dm).sum())})
summ = pd.DataFrame(rows); summ.to_csv(OUT / "fresh_outcomes.csv", index=False)
rng = np.random.default_rng(20261104)
udoi, inv = np.unique(df.first_doi.values, return_inverse=True)
mc = []
for a, b in [("v03b_guarded", "raw_pymatgen"), ("v03b_guarded", "v01_guarded"), ("v03b_guarded", "v02_package"),
             ("v03_strip", "raw_pymatgen"), ("v03_strip", "v01_guarded"), ("v03b_guarded", "v03_strip")]:
    for ep in ["determinate_agree", "discordant_return"]:
        if ep == "determinate_agree":
            fa, fb = df[f"{a}_outcome"].eq("agree"), df[f"{b}_outcome"].eq("agree")
        else:
            fa, fb = df[f"{a}_outcome"].isin(["disagree", "returned"]), df[f"{b}_outcome"].isin(["disagree", "returned"])
        oa, ob = int((fa & ~fb).sum()), int((~fa & fb).sum())
        g = pd.DataFrame({"doi": df.first_doi, "a": fa, "b": fb}).groupby("doi").any()
        da, db = int((g.a & ~g.b).sum()), int((~g.a & g.b).sum())
        row = {"a": a, "b": b, "endpoint": ep, "a_only": oa, "b_only": ob, "p_exact_strings": mcnemar_exact(oa, ob),
               "doi_a_only": da, "doi_b_only": db, "p_exact_dois": mcnemar_exact(da, db)}
        if ep == "determinate_agree":
            dv = (fa.astype(int) - fb.astype(int)).values * det.values
            pd_, pn = np.bincount(inv, weights=dv), np.bincount(inv, weights=det.values.astype(float))
            bs = [100 * pd_[i].sum() / pn[i].sum() for i in (rng.integers(0, len(udoi), len(udoi)) for _ in range(4000))]
            row["diff_points"] = round(100 * dv.sum() / det.sum(), 2)
            row["ci95_low"], row["ci95_high"] = [round(x, 2) for x in np.percentile(bs, [2.5, 97.5])]
        mc.append(row)
mcd = pd.DataFrame(mc); mcd.to_csv(OUT / "fresh_mcnemar.csv", index=False)
resc = df[df.v02_package_outcome.eq("refused") & df.v03b_guarded_outcome.ne("refused")]
resc[["string", "first_doi", "stratum", "reference_class", "reference_reason", "reference_amounts", "v03b_guarded_amounts",
      "v03b_guarded_outcome", "v03b_guarded_detail", "raw_pymatgen_outcome", "v01_guarded_outcome"]] \
    .assign(hand_check="", hand_note="").to_csv(OUT / "fresh_rescued.csv", index=False)
guarded = df[df.v03_strip_outcome.ne("refused") & df.v03b_guarded_outcome.eq("refused")]
guarded[["string", "reference_class", "reference_amounts", "v03_strip_amounts", "v03_strip_outcome", "v03b_guarded_detail"]] \
    .to_csv(OUT / "fresh_refused_by_guard.csv", index=False)
df.to_csv(OUT / "fresh_all_strings.csv", index=False)
pd.set_option("display.width", 250)
print(summ.to_string(index=False)); print(mcd.to_string(index=False))
print("rescued by H2b:", len(resc), resc.v03b_guarded_outcome.value_counts().to_dict(), resc.stratum.value_counts().to_dict())
print("refused by guard (H2 returned):", len(guarded), guarded.v03_strip_outcome.value_counts().to_dict())
bh = df[det & df.v02_package_outcome.ne("agree") & df.raw_pymatgen_outcome.ne("agree")]
print("headroom: determinate strings neither v0.2.0 nor pymatgen agrees on:", len(bh), bh.stratum.value_counts().to_dict())
