"""Build the fresh held-out pool for paper 12 (H2b test, 4 Nov 2026).

Source: the same two Kononova et al. text-mined releases (2020-07-13; SHA-256 checked), field
precursors[].material_string, which neither earlier set used (both used target.material_string only).
Every precursor record carries a composition assigned by the same Ceder-group pipeline, so the
reference classes of literature_eval.reference_class apply unchanged.
Kept: unique precursor strings not present in the development or the sol-gel held-out set.
Each string is attached to its first DOI (solid-state release read first, then sol-gel).
"""
import lzma, json, sys, hashlib
from pathlib import Path
import pandas as pd
CODE, EXT, DATA, OUT = map(Path, sys.argv[1:5])
sys.path.insert(0, str(CODE))
from literature_eval import CORPUS_SHA256, reference_class, stratum_of
used = set(pd.read_csv(DATA / "literature_strings_eval.csv", keep_default_na=False).string) | \
       set(pd.read_csv(DATA / "literature_strings_heldout_solgel.csv", keep_default_na=False).string)
dev_dois = set(pd.read_csv(DATA / "literature_strings_eval.csv", keep_default_na=False).first_doi)
first, dois, release = {}, {}, {}
for f in ["solid-state_dataset_20200713.json.xz", "sol-gel_dataset_20200713.json.xz"]:
    raw = (EXT / f).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == CORPUS_SHA256[f]
    with lzma.open(EXT / f, "rt", encoding="utf-8") as fh:
        R = json.load(fh)["reactions"]
    for r in R:
        for p in r.get("precursors") or []:
            s = p.get("material_string")
            if not s or s in used:
                continue
            dois.setdefault(s, set()).add(r["doi"])
            if s not in first:
                first[s] = (r["doi"], p); release[s] = f.split("_")[0]
rows = []
for s, (doi, p) in first.items():
    cls, reason, ref = reference_class(p, s)
    rows.append({"string": s, "first_doi": doi, "n_dois": len(dois[s]), "release": release[s],
                 "doi_in_dev_targets": doi in dev_dois, "stratum": stratum_of(s),
                 "reference_class": cls, "reference_reason": reason,
                 "reference_amounts": "" if ref is None else ";".join(f"{k}:{ref[k]:.6g}" for k in sorted(ref))})
df = pd.DataFrame(rows).sort_values("string").reset_index(drop=True)
df.to_csv(OUT / "fresh_pool_precursor_strings.csv", index=False)
print(len(df), df.first_doi.nunique(), df.reference_class.value_counts().to_dict(), df.release.value_counts().to_dict())
