"""Reproduce the counts in POOL_SEARCH.md. Args: paper folder (12_Digital_Discovery)."""
import lzma, json, re, sys
from pathlib import Path
import pandas as pd
P = Path(sys.argv[1])
rd = lambda f: set(pd.read_csv(f, keep_default_na=False).string)
used = rd(P / "code/main/data/literature_strings_eval.csv") | \
       rd(P / "code/main/data/literature_strings_heldout_solgel.csv") | \
       rd(P / "results/next_steps_2026-11-04/results_fresh/fresh_all_strings.csv")
ts, tgt, prec, names, forms, verb = set(), set(), set(), set(), set(), set()
for f in ["solid-state_dataset_20200713.json.xz", "sol-gel_dataset_20200713.json.xz"]:
    for r in json.load(lzma.open(P / "code/main/data/external" / f, "rt", encoding="utf-8"))["reactions"]:
        tgt.add(r["target"]["material_string"])
        for p in r.get("precursors") or []:
            prec.add(p["material_string"])
        for m in [r["target"]] + (r.get("precursors") or []):
            if m.get("material_name"): names.add(m["material_name"])
            if m.get("material_formula"): forms.add(m["material_formula"])
        for t in r.get("targets_string") or []:
            if t not in used:
                ts.add(t)
                if t in (r.get("paragraph_string") or ""): verb.add(t)
print("targets_string unused", len(ts), "verbatim in paragraph", len(verb),
      "with a word or space", sum(1 for t in ts if re.search(r"[a-z]{3,}", t) or " " in t))
print("target unused", len(tgt - used), "precursor unused", len(prec - used),
      "material_name unused", len(names - used), "material_formula unused", len(forms - used))
