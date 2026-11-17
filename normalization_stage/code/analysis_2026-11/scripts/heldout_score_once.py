"""Score the frozen H2 stage ONCE on the held-out sol-gel strings (paper 12, 4 Nov 2026 plan).

Checks the SHA-256 of composition_normalise.py against H2_FROZEN_before_heldout.sha256 first.
Writes h2_heldout_outcomes.csv, h2_heldout_mcnemar.csv, h2_heldout_rescued.csv and prints a summary.
"""
import hashlib, math, sys
from pathlib import Path
import numpy as np, pandas as pd

CODE = Path(sys.argv[1]); DATA = Path(sys.argv[2]); OUT = Path(sys.argv[3]); FROZEN = Path(sys.argv[4])
sys.path.insert(0, str(CODE))
digest = hashlib.sha256((CODE / "composition_normalise.py").read_bytes()).hexdigest()
assert digest == FROZEN.read_text().split()[0], "normaliser changed after freeze"
from literature_eval import fractions_match
from composition_parser import ELEMENT_SYMBOLS
from composition_normalise import parse_formula_normalised

def amounts_of(s):
    return {k: float(v) for k, v in (p.split(":") for p in s.split(";"))} if s else None

def mcnemar_exact(b, c):
    n = b + c
    if n == 0: return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)

df = pd.read_csv(DATA / "literature_strings_heldout_solgel.csv", keep_default_na=False)
out, amt, fl, mech = [], [], [], []
for s, cls, ref in zip(df.string, df.reference_class, df.reference_amounts):
    try:
        got, be, flags = parse_formula_normalised(s)
    except Exception:
        out.append("refused"); amt.append(""); fl.append(""); mech.append(""); continue
    amt.append(";".join(f"{k}:{got[k]:g}" for k in sorted(got))); fl.append("|".join(flags))
    if set(got) - ELEMENT_SYMBOLS:
        m = "dummy_species_accepted"
    else:
        m = ""
    if cls == "determinate":
        ok = set(got) <= ELEMENT_SYMBOLS and fractions_match(got, amounts_of(ref))
        out.append("agree" if ok else "disagree"); mech.append("" if ok else (m or "differs"))
    else:
        out.append("returned"); mech.append(m or "returned_despite_" + (df.loc[len(out)-1, "reference_reason"] or cls))
df["v03_strip_outcome"], df["v03_strip_amounts"], df["v03_strip_flags"], df["v03_strip_mechanism"] = out, amt, fl, mech

CONF = ["raw_pymatgen", "v01_guarded", "v02_package", "v03_strip"]
det = df.reference_class.eq("determinate")
rows = []
for c in CONF:
    o = df[f"{c}_outcome"]; disc = o.isin(["disagree", "returned"])
    dummy = df[f"{c}_mechanism"].eq("dummy_species_accepted")
    rows.append({"configuration": c, "strings": len(df), "determinate": int(det.sum()),
                 "determinate_agree": int((det & o.eq("agree")).sum()),
                 "agree_pct": round(100 * (det & o.eq("agree")).sum() / det.sum(), 2),
                 "determinate_refused": int((det & o.eq("refused")).sum()),
                 "determinate_disagree": int((det & o.eq("disagree")).sum()),
                 "nondeterminate_returned": int(o.eq("returned").sum()),
                 "discordant_returns": int(disc.sum()),
                 "discordant_excluding_dummy": int((disc & ~dummy).sum())})
summ = pd.DataFrame(rows); summ.to_csv(OUT / "h2_heldout_outcomes.csv", index=False)

rng = np.random.default_rng(20261104)
dois = df.first_doi.values; udoi, inv = np.unique(dois, return_inverse=True)
mc = []
for a, b in [("v03_strip", "raw_pymatgen"), ("v03_strip", "v01_guarded"), ("v03_strip", "v02_package")]:
    for ep in ["determinate_agree", "discordant_return", "discordant_return_excluding_dummy"]:
        if ep == "determinate_agree":
            fa, fb = df[f"{a}_outcome"].eq("agree"), df[f"{b}_outcome"].eq("agree")
        else:
            fa = df[f"{a}_outcome"].isin(["disagree", "returned"]); fb = df[f"{b}_outcome"].isin(["disagree", "returned"])
            if ep.endswith("dummy"):
                fa = fa & ~df[f"{a}_mechanism"].eq("dummy_species_accepted")
                fb = fb & ~df[f"{b}_mechanism"].eq("dummy_species_accepted")
        oa, ob = int((fa & ~fb).sum()), int((~fa & fb).sum())
        g = pd.DataFrame({"doi": df.first_doi, "a": fa, "b": fb}).groupby("doi").any()
        da, db = int((g.a & ~g.b).sum()), int((~g.a & g.b).sum())
        row = {"a": a, "b": b, "endpoint": ep, "a_only": oa, "b_only": ob,
               "p_exact_strings": mcnemar_exact(oa, ob), "doi_a_only": da, "doi_b_only": db,
               "p_exact_dois": mcnemar_exact(da, db)}
        if ep == "determinate_agree":
            # paired difference in determinate agreement (points), DOI-cluster bootstrap 95% CI
            dvec = (fa.astype(int) - fb.astype(int)).values * det.values
            per_doi_d = np.bincount(inv, weights=dvec); per_doi_n = np.bincount(inv, weights=det.values.astype(float))
            boots = []
            for _ in range(4000):
                idx = rng.integers(0, len(udoi), len(udoi))
                boots.append(100 * per_doi_d[idx].sum() / per_doi_n[idx].sum())
            row["diff_points"] = round(100 * dvec.sum() / det.sum(), 2)
            row["ci95_low"], row["ci95_high"] = [round(x, 2) for x in np.percentile(boots, [2.5, 97.5])]
        mc.append(row)
mcd = pd.DataFrame(mc); mcd.to_csv(OUT / "h2_heldout_mcnemar.csv", index=False)

resc = df[df.v02_package_outcome.eq("refused") & df.v03_strip_outcome.ne("refused")]
resc[["string", "first_doi", "stratum", "reference_class", "reference_reason", "reference_amounts",
      "v03_strip_amounts", "v03_strip_outcome", "v03_strip_flags", "raw_pymatgen_outcome", "v01_guarded_outcome"]] \
    .assign(hand_check="", hand_note="").to_csv(OUT / "h2_heldout_rescued.csv", index=False)
df.to_csv(OUT / "h2_heldout_all_strings.csv", index=False)
pd.set_option("display.width", 250)
print(summ.to_string(index=False)); print(mcd.to_string(index=False))
print("rescued:", len(resc), resc.v03_strip_outcome.value_counts().to_dict())
print(resc.stratum.value_counts().to_dict())
bothother = df[det & df.stratum.eq("other") & df.v02_package_outcome.eq("refused") & df.raw_pymatgen_outcome.eq("refused")]
print("other-stratum determinate both-refused:", len(bothother), "of which v03 agree:", int(bothother.v03_strip_outcome.eq("agree").sum()))
