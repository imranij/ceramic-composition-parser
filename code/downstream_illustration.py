"""Downstream illustration (ESI S5): dielectric constant from composition alone.

Not evidence for the parser. Every configuration compared in the paper parses the
964 formulas of this dataset identically, so this task cannot discriminate between
parsers; it only illustrates the record layer feeding a model.

Design (revised):
* target ``poly_total`` from matminer's ``dielectric_constant`` (Petousis et al.
  2017), averaged per formula string;
* folds grouped by chemical system (the set of elements), so that, e.g., MnO and
  Mn2O3 never sit on both sides of a split; 5 folds x 5 repeats;
* three representations: character 1-3-gram TF-IDF of the raw string; the
  package's atomic-fraction vector; and matminer's Magpie ``ElementProperty``
  statistics computed from the same parsed composition (the standard
  composition-only baseline);
* one model, ``RandomForestRegressor(n_estimators=500, max_features=1/3,
  min_samples_leaf=1, random_state=seed)``;
* per-fold RMSE and MAE; paired Wilcoxon signed-rank tests across the 25 folds.

    python downstream_illustration.py --property-file <dielectric_constant.json.gz>

Writes ``data/processed_results/downstream_illustration_folds.csv`` and
``..._summary.csv``. The property file is not redistributed (matminer / figshare
file 13213475, SHA-256 8eb24812...95e8b6, checked on load).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

PAPER = Path(__file__).resolve().parents[1]
DATA = PAPER / "data"
SHA = "8eb24812148732786cd7c657eccfc6b5ee66533429c2cfbcc4f0059c0295e8b6"


def load(path: Path) -> pd.DataFrame:
    if hashlib.sha256(path.read_bytes()).hexdigest() != SHA:
        raise SystemExit("property file SHA-256 does not match matminer's metadata")
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        raw = json.load(fh)
    props = pd.DataFrame(raw["data"], columns=raw["columns"], index=raw["index"])
    props = props.dropna(subset=["formula", "poly_total"])
    props = props.groupby("formula", as_index=False)["poly_total"].mean()
    vec = pd.read_csv(DATA / "paper2_parsed_composition_vectors.csv")
    vec = vec[vec.source_dataset == "dielectric_constant"]
    df = props.merge(vec, on="formula", how="inner").reset_index(drop=True)
    frac = [c for c in df.columns if c.startswith("frac_")]
    df["chemical_system"] = df[frac].gt(0).apply(
        lambda r: "-".join(sorted(c[5:] for c, b in r.items() if b)), axis=1)
    return df


def magpie(df: pd.DataFrame) -> np.ndarray:
    from matminer.featurizers.composition import ElementProperty
    from pymatgen.core import Composition

    ep = ElementProperty.from_preset("magpie", impute_nan=True)
    comps = [Composition({c[5:]: v for c, v in r.items() if c.startswith("frac_") and v > 0})
             for _, r in df.iterrows()]
    return np.array([ep.featurize(c) for c in comps], dtype=float)


def main(argv: list[str] | None = None) -> None:
    from scipy.stats import wilcoxon
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    from sklearn.model_selection import GroupKFold

    ap = argparse.ArgumentParser()
    ap.add_argument("--property-file", type=Path, required=True)
    ap.add_argument("--repeats", type=int, default=5)
    a = ap.parse_args(argv)
    df = load(a.property_file)
    y = df["poly_total"].to_numpy()
    groups = df["chemical_system"].to_numpy()
    X_frac = df[[c for c in df.columns if c.startswith("frac_")]].to_numpy()
    X_mag = magpie(df)
    rows = []
    for seed in range(a.repeats):
        gkf = GroupKFold(n_splits=5, shuffle=True, random_state=seed)
        for fold, (tr, te) in enumerate(gkf.split(X_frac, y, groups)):
            tf = TfidfVectorizer(analyzer="char", ngram_range=(1, 3)).fit(df.formula.iloc[tr])
            reps = {"char_tfidf": (tf.transform(df.formula.iloc[tr]), tf.transform(df.formula.iloc[te])),
                    "atomic_fractions": (X_frac[tr], X_frac[te]),
                    "magpie": (X_mag[tr], X_mag[te])}
            for name, (Xtr, Xte) in reps.items():
                rf = RandomForestRegressor(n_estimators=500, max_features=1 / 3,
                                           random_state=seed, n_jobs=-1).fit(Xtr, y[tr])
                p = rf.predict(Xte)
                rows.append({"repeat": seed, "fold": fold, "representation": name,
                             "rmse": float(np.sqrt(mean_squared_error(y[te], p))),
                             "mae": float(mean_absolute_error(y[te], p)), "n_test": len(te)})
    folds = pd.DataFrame(rows)
    out = DATA / "processed_results"
    folds.to_csv(out / "downstream_illustration_folds.csv", index=False)
    summ = folds.groupby("representation")[["rmse", "mae"]].agg(["mean", "std"])
    piv = folds.pivot_table(index=["repeat", "fold"], columns="representation", values="mae")
    tests = {f"{b}_vs_{c}": float(wilcoxon(piv[b], piv[c]).pvalue)
             for b, c in [("atomic_fractions", "char_tfidf"), ("magpie", "atomic_fractions")]}
    summ.to_csv(out / "downstream_illustration_summary.csv")
    print(summ, tests, f"n={len(df)} systems={df.chemical_system.nunique()}")


if __name__ == "__main__":
    main()
