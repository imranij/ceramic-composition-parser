import sys
sys.path.insert(0, "/mnt/user-data/outputs/p12/work/pkg/code")
import pandas as pd
import composition_normalise_guarded as G
half = sys.argv[1]
d = pd.read_csv(f"/mnt/user-data/outputs/p12/work/design_{half}.csv", keep_default_na=False)
r = d[(d.v02_package_outcome == "refused") & (d.h2_outcome != "refused")]
out = []
for s in r.string:
    try: G.parse_formula_guarded(s); out.append("kept")
    except Exception: out.append(G.GUARD_LOG.get(s, "refused_other"))
r = r.assign(guard=out)
print(half, "H2-rescued", len(r), r.guard.value_counts().to_dict())
print(r[r.guard != "kept"][["string", "h2_amounts", "reference_class", "h2_outcome", "guard"]].to_string())
det = d.reference_class == "determinate"
print("v03b determinate agree =", int((det & d.h2_outcome.eq("agree")).sum()) - int((r.guard.ne("kept") & r.h2_outcome.eq("agree")).sum()))
