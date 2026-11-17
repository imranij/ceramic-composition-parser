"""G3 design check on the development release only (dev half, or dev-test half when asked)."""
import sys
sys.path.insert(0, "/mnt/user-data/outputs/p12/work/pkg/code")
import pandas as pd
import composition_normalise_g3 as G3
import composition_normalise_guarded as G
half = sys.argv[1]
d = pd.read_csv(f"/mnt/user-data/outputs/p12/work/design_{half}.csv", keep_default_na=False)
r = d[(d.v02_package_outcome == "refused") & (d.h2_outcome != "refused")]
res = []
for s in r.string:
    try:
        G.parse_formula_guarded(s)
    except Exception:
        res.append("H2b_refused"); continue
    try:
        G3.parse_formula_g3(s); res.append("kept")
    except Exception:
        res.append(G3.G3_LOG.get(s, "refused_other"))
r = r.assign(g3=res)
print(half, "H2-rescued", len(r), r.g3.value_counts().to_dict())
print(r[~r.g3.isin(["kept", "H2b_refused"])][["string", "h2_amounts", "reference_class", "h2_outcome", "g3"]].to_string())
