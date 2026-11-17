"""Design-time scoring of the H2 stage on the development release only."""
import sys
sys.path.insert(0, "/mnt/user-data/outputs/p12/work/pkg/code")
import pandas as pd
from literature_eval import fractions_match
from composition_parser import ELEMENT_SYMBOLS
from composition_normalise import parse_formula_normalised

def amounts_of(s):
    if not isinstance(s,str) or not s: return None
    return {k: float(v) for k,v in (p.split(":") for p in s.split(";"))}

half = sys.argv[1]   # dev or test (DOI-hash halves of the development release)
df=pd.read_csv("/mnt/user-data/outputs/p12/work/pkg/data/literature_strings_eval.csv", keep_default_na=False)
d=df[df.split==half].copy()
out, amt, fl = [], [], []
for s, cls, ref in zip(d.string, d.reference_class, d.reference_amounts):
    try:
        got, be, flags = parse_formula_normalised(s)
    except Exception:
        out.append("refused"); amt.append(""); fl.append(""); continue
    amt.append(";".join(f"{k}:{got[k]:g}" for k in sorted(got))); fl.append("|".join(flags))
    if cls=="determinate":
        out.append("agree" if set(got)<=ELEMENT_SYMBOLS and fractions_match(got,amounts_of(ref)) else "disagree")
    else: out.append("returned")
d["h2_outcome"]=out; d["h2_amounts"]=amt; d["h2_flags"]=fl
det=d.reference_class=="determinate"
print(half, "strings", len(d), "determinate", det.sum())
for c in ["raw_pymatgen","v01_guarded","v02_package","h2"]:
    o=d[f"{c}_outcome"]
    print(f"  {c:13s} agree {int((det&o.eq('agree')).sum())}  disagree {int((det&o.eq('disagree')).sum())}  returned(non-det) {int(o.eq('returned').sum())}")
resc=d[(d.v02_package_outcome=="refused")&(d.h2_outcome!="refused")]
print("rescued", len(resc), resc.h2_outcome.value_counts().to_dict())
pd.set_option("display.width",250); pd.set_option("display.max_colwidth",70); pd.set_option("display.max_rows",500)
print(resc[["string","reference_class","reference_amounts","h2_amounts","h2_outcome","h2_flags"]].to_string())
d.to_csv(f"/mnt/user-data/outputs/p12/work/design_{half}.csv", index=False)
