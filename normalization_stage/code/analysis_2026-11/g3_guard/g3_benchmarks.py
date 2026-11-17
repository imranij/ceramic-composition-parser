import sys
sys.path.insert(0, "/mnt/user-data/outputs/p12/work/pkg/code")
import pandas as pd
import composition_normalise_g3 as G3, composition_normalise_guarded as G
d = pd.read_csv(sys.argv[1], keep_default_na=False)
col = [c for c in d.columns if c in ("string", "formula", "input", "raw_string", "notation", "formula_string", "text")][0]
def run(f, s):
    try: return str(sorted(f(s)[0].items()))
    except Exception: return "refused"
diff = [(s, run(G.parse_formula_guarded, s), run(G3.parse_formula_g3, s)) for s in d[col]]
ch = [x for x in diff if x[1] != x[2]]
print(sys.argv[1].split("/")[-1], "column", col, "strings", len(d), "changed by G3", len(ch)); print(ch)
