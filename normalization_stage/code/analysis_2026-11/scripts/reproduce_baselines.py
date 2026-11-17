import sys, time
sys.path.insert(0, "/mnt/user-data/outputs/p12/work/pkg/code")
import pandas as pd
from literature_eval import run_parser, fractions_match
from composition_parser import ELEMENT_SYMBOLS

def amounts_of(s):
    if not isinstance(s,str) or not s: return None
    return {k: float(v) for k,v in (p.split(":") for p in s.split(";"))}

def score(df, name, fn):
    out=[]
    for s, cls, ref in zip(df.string, df.reference_class, df.reference_amounts):
        got, det = fn(s)
        if got is None: out.append("refused"); continue
        if cls=="determinate":
            r=amounts_of(ref)
            out.append("agree" if set(got)<=ELEMENT_SYMBOLS and fractions_match(got,r) else "disagree")
        else: out.append("returned")
    return out

for f in ["literature_strings_eval.csv","literature_strings_heldout_solgel.csv"]:
    df=pd.read_csv(f"/mnt/user-data/outputs/p12/work/pkg/data/{f}", keep_default_na=False)
    for name in ["v02_package","v01_guarded","raw_pymatgen"]:
        t=time.time()
        o=score(df,name,lambda s: run_parser(name,s))
        mism=(pd.Series(o)!=df[f"{name}_outcome"].values).sum()
        print(f, name, "mismatches:", mism, f"{time.time()-t:.0f}s", flush=True)
