"""Paper 12, H1: inter-annotator agreement and the paired parser comparison on expert labels.

Usage (from this folder; needs only python3, pandas and numpy):

    python annotation_analysis.py            # once both annotators have returned their sheets
    python annotation_analysis.py --selftest # check the script on simulated annotators

Inputs in this folder:
    annotation_KEY_do_not_give_to_annotators.csv     item_id -> reference and parser outputs
    annotation_sheet_part1_304_annotator_A.csv  / _B.csv    (filled by the annotators)
    annotation_sheet_part2_H2_rescued_annotator_A.csv / _B.csv   (optional block)
    annotation_sheet_part3_fresh_rescued_annotator_A.csv / _B.csv (optional block, fresh-set strings rescued by H2b)
    adjudication.csv  (written by the first run; the adjudicator fills two columns, then rerun)

Outputs (folder results/):
    agreement.csv           Cohen's kappa (3-class and binary) with 95% bootstrap CIs, % agreement
    adjudication.csv        (next to this script) the items on which A and B differ
    parser_outcomes.csv     per parser: correct returns, wrong returns, correct refusals, refusal costs
    parser_mcnemar.csv      exact two-sided McNemar tests on paired items
    reference_vs_expert.csv how the machine reference compares with the expert consensus
    item_level.csv          every item with consensus label and each parser's outcome
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DECISIONS = ("determinate", "indeterminate", "mixture")
PARSERS = ("raw_pymatgen", "v01_guarded", "v02_package", "v03_strip", "v03b_guarded")
PAIRS = [("v02_package", "raw_pymatgen"), ("v02_package", "v01_guarded"),
         ("v03_strip", "raw_pymatgen"), ("v03_strip", "v01_guarded"), ("v03_strip", "v02_package"),
         ("v03b_guarded", "raw_pymatgen"), ("v03b_guarded", "v01_guarded"), ("v03b_guarded", "v03_strip")]
SEED = 20261104


# ----------------------------------------------------------------- helpers
def parse_amounts(text: str) -> dict[str, float] | None:
    """'Ba:1;Ti:1;O:3' (amounts may be 0.5 or 1/3) -> dict; '' -> None; malformed -> ValueError."""
    text = (text or "").strip()
    if not text:
        return None
    out: dict[str, float] = {}
    for part in re.split(r"[;,]\s*", text):
        if not part:
            continue
        el, _, a = part.partition(":")
        el, a = el.strip(), a.strip()
        if not re.fullmatch(r"[A-Z][a-z]?", el) or not a:
            raise ValueError(f"malformed composition entry {part!r} in {text!r}")
        if "/" in a:
            n, d = a.split("/")
            v = float(n) / float(d)
        else:
            v = float(a)
        out[el] = out.get(el, 0.0) + v
    if not out or any(v <= 0 for v in out.values()):
        raise ValueError(f"empty or non-positive composition {text!r}")
    return out


def same(a: dict | None, b: dict | None, tol: float) -> bool:
    if a is None or b is None or set(a) != set(b):
        return False
    ta, tb = sum(a.values()), sum(b.values())
    return max(abs(a[k] / ta - b[k] / tb) for k in a) <= tol


def cohen_kappa(x: list[str], y: list[str]) -> float:
    cats = sorted(set(x) | set(y))
    n = len(x)
    po = sum(i == j for i, j in zip(x, y)) / n
    pe = sum((x.count(c) / n) * (y.count(c) / n) for c in cats)
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def kappa_ci(x: list[str], y: list[str], reps: int = 2000) -> tuple[float, float]:
    rng = np.random.default_rng(SEED)
    x, y = np.array(x), np.array(y)
    ks = []
    for _ in range(reps):
        i = rng.integers(0, len(x), len(x))
        ks.append(cohen_kappa(list(x[i]), list(y[i])))
    ks = [k for k in ks if not math.isnan(k)]
    return float(np.percentile(ks, 2.5)), float(np.percentile(ks, 97.5))


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    c = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    d = 1 + z * z / n
    return max(0.0, (p + z * z / (2 * n) - c) / d), min(1.0, (p + z * z / (2 * n) + c) / d)


# ----------------------------------------------------------------- loading
def load_sheet(path: Path, who: str) -> pd.DataFrame:
    d = pd.read_csv(path, dtype=str, keep_default_na=False)
    d["decision"] = d["decision"].str.strip().str.lower()
    bad = d[~d.decision.isin(DECISIONS)]
    if len(bad):
        raise SystemExit(f"{path.name}: {len(bad)} rows with a missing or invalid decision, e.g. "
                         f"{bad.item_id.head(5).tolist()}. Allowed: {DECISIONS}")
    problems = []
    for iid, dec, comp in zip(d.item_id, d.decision, d.composition):
        try:
            a = parse_amounts(comp)
        except (ValueError, ZeroDivisionError) as exc:
            problems.append(f"{iid}: {exc}")
            continue
        if dec == "determinate" and a is None:
            problems.append(f"{iid}: decision 'determinate' needs a composition")
    if problems:
        raise SystemExit(f"{path.name}:\n  " + "\n  ".join(problems[:20]))
    return d[["item_id", "decision", "composition", "confidence", "note"]].add_prefix(f"{who}_") \
        .rename(columns={f"{who}_item_id": "item_id"})


def consensus(m: pd.DataFrame, tol: float, adj_path: Path) -> pd.DataFrame:
    """Consensus = A where A and B agree (decision, and composition when determinate); else adjudicated."""
    agree = []
    for da, db, ca, cb in zip(m.A_decision, m.B_decision, m.A_composition, m.B_composition):
        ok = da == db and (da != "determinate" or same(parse_amounts(ca), parse_amounts(cb), tol))
        agree.append(ok)
    m["A_B_agree"] = agree
    dis = m[~m.A_B_agree]
    if adj_path.exists():
        adj = pd.read_csv(adj_path, dtype=str, keep_default_na=False)
    else:
        adj = pd.DataFrame(columns=["item_id", "adjudicated_decision", "adjudicated_composition"])
    new = dis[~dis.item_id.isin(adj.item_id)]
    if len(new):
        add = new[["item_id", "string", "A_decision", "A_composition", "B_decision", "B_composition",
                   "A_note", "B_note"]].assign(adjudicated_decision="", adjudicated_composition="")
        adj = pd.concat([adj, add], ignore_index=True)
        adj.to_csv(adj_path, index=False)
    adj = adj.set_index("item_id")
    dec, comp = [], []
    for r in m.itertuples():
        if r.A_B_agree:
            dec.append(r.A_decision); comp.append(r.A_composition)
        else:
            a = adj.loc[r.item_id] if r.item_id in adj.index else None
            d = (a["adjudicated_decision"].strip().lower() if a is not None else "")
            dec.append(d if d in DECISIONS else "")
            comp.append(a["adjudicated_composition"] if a is not None else "")
    m["consensus_decision"], m["consensus_composition"] = dec, comp
    return m


def parser_outcome(amounts_text: str, dec: str, comp: str, tol: float) -> str:
    got = parse_amounts(amounts_text) if amounts_text else None
    if got is None:
        return {"determinate": "refusal_cost", "indeterminate": "correct_refusal",
                "mixture": "correct_refusal"}[dec]
    if dec == "determinate":
        return "correct_return" if same(got, parse_amounts(comp), tol) else "wrong_return"
    return "wrong_return"


# ----------------------------------------------------------------- analysis
def analyse(key: pd.DataFrame, a: pd.DataFrame, b: pd.DataFrame, tol: float, outdir: Path,
            adj_path: Path) -> None:
    outdir.mkdir(exist_ok=True)
    m = key.merge(a, on="item_id").merge(b, on="item_id")
    missing = set(key.item_id) - set(m.item_id)
    if missing:
        print(f"note: {len(missing)} key items have no row in both sheets and are skipped")

    # 1. agreement, on the primary block and on all items
    rows = []
    for name, d in [("primary_304", m[m.block == "primary_304"]), ("all_items", m)]:
        if not len(d):
            continue
        x, y = d.A_decision.tolist(), d.B_decision.tolist()
        xb = ["determinate" if v == "determinate" else "not" for v in x]
        yb = ["determinate" if v == "determinate" else "not" for v in y]
        k3, k2 = cohen_kappa(x, y), cohen_kappa(xb, yb)
        both_det = d[(d.A_decision == "determinate") & (d.B_decision == "determinate")]
        comp_agree = sum(same(parse_amounts(p), parse_amounts(q), tol)
                         for p, q in zip(both_det.A_composition, both_det.B_composition))
        rows.append({"items": name, "n": len(d),
                     "pct_agree_decision": round(100 * np.mean([i == j for i, j in zip(x, y)]), 1),
                     "kappa_3class": round(k3, 3), "kappa_3class_ci95": "%.3f to %.3f" % kappa_ci(x, y),
                     "kappa_binary": round(k2, 3), "kappa_binary_ci95": "%.3f to %.3f" % kappa_ci(xb, yb),
                     "both_determinate": len(both_det), "composition_agree_when_both_determinate": int(comp_agree)})
    pd.DataFrame(rows).to_csv(outdir / "agreement.csv", index=False)
    print(pd.DataFrame(rows).to_string(index=False))

    # 2. consensus and adjudication
    m = consensus(m, tol, adj_path)
    pending = m[m.consensus_decision == ""]
    if len(pending):
        print(f"\n{len(pending)} items still need adjudication: fill adjudicated_decision and "
              f"adjudicated_composition in {adj_path.name}, then rerun. Parser scoring below uses "
              f"only the {len(m) - len(pending)} items with a consensus label.")
    s = m[m.consensus_decision != ""].copy()

    # 3. machine reference against the expert consensus
    ref = []
    for r in s.itertuples():
        if r.reference_class != r.consensus_decision:
            ref.append("class_differs")
        elif r.reference_class == "determinate":
            ref.append("same" if same(parse_amounts(r.reference_amounts), parse_amounts(r.consensus_composition), tol)
                       else "composition_differs")
        else:
            ref.append("same")
    s["reference_vs_expert"] = ref
    rv = pd.crosstab(s.reference_class, s.consensus_decision)
    rv.to_csv(outdir / "reference_vs_expert.csv")
    print("\nmachine reference (rows) against expert consensus (columns):\n", rv.to_string())
    print("reference kappa against consensus:",
          round(cohen_kappa(s.reference_class.tolist(), s.consensus_decision.tolist()), 3))

    # 4. parser outcomes against the consensus
    for p in PARSERS:
        s[f"{p}_vs_expert"] = [parser_outcome(t, d, c, tol) for t, d, c in
                               zip(s[f"{p}_amounts"], s.consensus_decision, s.consensus_composition)]
    out = []
    for block in ("primary_304", "h2_rescued_heldout", "h2b_rescued_fresh"):
        d = s[s.block == block]
        if not len(d):
            continue
        w = d.sampling_weight.astype(float) if block == "primary_304" else None
        for p in PARSERS:
            o = d[f"{p}_vs_expert"]
            row = {"block": block, "parser": p, "n": len(d)}
            for cat in ("correct_return", "wrong_return", "correct_refusal", "refusal_cost"):
                row[cat] = int((o == cat).sum())
            k = row["wrong_return"]; ret = row["correct_return"] + k
            lo, hi = wilson(k, ret)
            row["wrong_share_of_returns_pct"] = round(100 * k / ret, 1) if ret else float("nan")
            row["wrong_share_ci95"] = f"{100*lo:.1f} to {100*hi:.1f}" if ret else ""
            if w is not None:
                row["weighted_wrong_return_rate_pct"] = round(100 * (w * (o == "wrong_return")).sum() / w.sum(), 2)
                row["weighted_correct_rate_pct"] = round(
                    100 * (w * o.isin(["correct_return", "correct_refusal"])).sum() / w.sum(), 2)
            out.append(row)
    po = pd.DataFrame(out)
    po.to_csv(outdir / "parser_outcomes.csv", index=False)
    print("\n", po.to_string(index=False))

    # 5. paired exact McNemar on the primary block
    d = s[s.block == "primary_304"]
    mc = []
    for a_, b_ in PAIRS:
        for ep, fn in [("wrong_return", lambda o: o == "wrong_return"),
                       ("correct", lambda o: o.isin(["correct_return", "correct_refusal"])),
                       ("refusal_cost", lambda o: o == "refusal_cost")]:
            fa, fb = fn(d[f"{a_}_vs_expert"]), fn(d[f"{b_}_vs_expert"])
            oa, ob = int((fa & ~fb).sum()), int((~fa & fb).sum())
            mc.append({"a": a_, "b": b_, "endpoint": ep, "a_only": oa, "b_only": ob,
                       "p_exact": mcnemar_exact(oa, ob)})
    mc = pd.DataFrame(mc)
    mc.to_csv(outdir / "parser_mcnemar.csv", index=False)
    print("\n", mc.to_string(index=False))
    s.to_csv(outdir / "item_level.csv", index=False)
    print(f"\nwrote {outdir}")


def selftest() -> None:
    """Simulate two annotators from the machine reference with 10% label noise and run everything."""
    key = pd.read_csv(HERE / "annotation_KEY_do_not_give_to_annotators.csv", dtype=str, keep_default_na=False)
    rng = np.random.default_rng(1)
    tmp = HERE / "_selftest"
    tmp.mkdir(exist_ok=True)
    sheets = {}
    for who in "AB":
        dec = key.reference_class.copy()
        flip = rng.random(len(key)) < 0.10
        dec[flip] = rng.choice(DECISIONS, flip.sum())
        comp = np.where(dec == "determinate",
                        np.where(key.reference_amounts != "", key.reference_amounts, "Ba:1;Ti:1;O:3"), "")
        sheets[who] = pd.DataFrame({"item_id": key.item_id, "string": key.string, "first_doi": key.first_doi,
                                    "decision": dec, "composition": comp, "confidence": "2", "note": ""})
    adj = tmp / "adjudication.csv"
    # start from an empty adjudication file (overwrite rather than delete: some synced folders forbid deletes)
    pd.DataFrame(columns=["item_id", "adjudicated_decision", "adjudicated_composition"]).to_csv(adj, index=False)
    a, b = load_sheet_df(sheets["A"], "A"), load_sheet_df(sheets["B"], "B")
    analyse(key, a, b, 0.005, tmp / "results", adj)
    # adjudicate by the reference and rerun
    ad = pd.read_csv(adj, dtype=str, keep_default_na=False).merge(key[["item_id", "reference_class", "reference_amounts"]], on="item_id")
    ad["adjudicated_decision"] = ad.reference_class
    ad["adjudicated_composition"] = np.where(ad.reference_class == "determinate", ad.reference_amounts, "")
    ad.drop(columns=["reference_class", "reference_amounts"]).to_csv(adj, index=False)
    analyse(key, a, b, 0.005, tmp / "results", adj)
    print("\nSELFTEST OK (simulated labels; these numbers mean nothing)")


def load_sheet_df(d: pd.DataFrame, who: str) -> pd.DataFrame:
    p = HERE / f"_selftest/_sheet_{who}.csv"
    d.to_csv(p, index=False)
    return load_sheet(p, who)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--tol", type=float, default=0.005,
                    help="max |difference| in atomic fraction for two compositions to count as the same")
    a = ap.parse_args()
    if a.selftest:
        selftest(); return
    key = pd.read_csv(HERE / "annotation_KEY_do_not_give_to_annotators.csv", dtype=str, keep_default_na=False)
    sheets = {}
    for who in "AB":
        parts = []
        for p in sorted(HERE.glob(f"annotation_sheet_part*_annotator_{who}.csv")):
            raw = pd.read_csv(p, dtype=str, keep_default_na=False)
            if not raw["decision"].str.strip().any():
                print(f"note: {p.name} is still blank and is skipped")
                continue
            parts.append(load_sheet(p, who))
        if not parts:
            raise SystemExit(f"no filled sheet found for annotator {who}")
        sheets[who] = pd.concat(parts, ignore_index=True)
    analyse(key, sheets["A"], sheets["B"], a.tol, HERE / "results", HERE / "adjudication.csv")


if __name__ == "__main__":
    main()
