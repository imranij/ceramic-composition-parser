"""Evaluate composition parsers on composition strings as written in the literature.

Source corpus
-------------
Kononova et al. (2019), "Text-mined dataset of inorganic materials synthesis
recipes", Sci. Data 6, 203; release 2020-07-13 (``solid-state_dataset_20200713.json.xz``),
GitHub repository CederGroupHub/text-mined-synthesis_public at commit
``fca0a994ddb36b37d39b803e8a21880aaecb1d71``. The file is not redistributed in this
package; ``fetch_literature_corpus.py`` retrieves it and checks its SHA-256.

Each reaction entry carries the DOI of the source article, the target material
string *as written in the paper* (``target.material_string``), and the composition
that the Ceder-group extraction pipeline assigned to it (``target.composition``,
plus ``amounts_vars``, ``elements_vars``, ``additives`` and ``oxygen_deficiency``).
That assignment was produced by another group's pipeline, independently of this
package's author, and it is used here as an *independent machine reference*, not
as an expert gold label.

Unit of analysis
----------------
The unique raw target string. Each string is attached to the first DOI at which it
occurs in the release, and to the number of distinct DOIs that use it.

Reference classes (decided from the reference record alone, before any parser runs)
----------------------------------------------------------------------------------
``determinate``    one composition component, coefficient 1, every element amount a
                   positive number, every element a real element symbol, no
                   element variables, no oxygen-deficiency marker, and no dopant
                   named in the string without an amount. A dopant or variable
                   value stated elsewhere in the paper does not make the string
                   indeterminate. The reference composition is compared with what
                   each parser returns.
``mixture``        several components, every coefficient and amount numeric, no
                   variables: a fully specified multi-phase expression. A
                   single-formula parser is expected to refuse it; resolving it
                   is the job of a mixture layer.
``indeterminate``  anything else: free variables (x, y, delta), dopant or additive
                   annotations without amounts, placeholder elements (M, RE),
                   non-numeric amounts. The string alone does not determine a
                   composition, so the expected single-formula behaviour is refusal.

Outcomes per parser and string
------------------------------
``agree``      returned a composition whose atomic fractions match the reference
               (same element set, max |delta fraction| <= TOL)
``disagree``   returned a composition that does not match a determinate reference
``returned``   returned a composition for a mixture or indeterminate string
``refused``    raised (any refusal)

A *reference-discordant return* is ``disagree`` or ``returned``. It is a candidate
silent mis-parse, and it is only a candidate: the reference can itself be wrong.
Discordant returns are therefore classified by mechanism with deterministic rules
(``mechanism_of``) and reported in full, rather than all counted as parser errors.

Parsers
-------
``guarded``        the package as shipped: shared refusal guards, then pymatgen,
                   then the element-symbol check (``parse_formula_with_backend``)
``fallback_only``  the deterministic fallback grammar alone, with the same shared
                   guards (``parse_formula_fallback``)
``raw_pymatgen``   ``pymatgen.core.Composition`` with no guards

    python literature_eval.py --corpus <path to solid-state_dataset_20200713.json.xz>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import math
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from composition_parser import (  # noqa: E402
    ELEMENT_SYMBOLS,
    atomic_fractions,
    parse_formula_fallback,
    parse_formula_with_backend,
)

PAPER = Path(__file__).resolve().parents[1]
DATA = PAPER / "data"
CORPUS_SHA256 = {
    "solid-state_dataset_20200713.json.xz": "0ae448935bc23e933fa12cabdaa044f232412ba99cf0f966a33e439f6e8334c5",
    "sol-gel_dataset_20200713.json.xz": "d7d092b7f1b35b609669eb3530b48429eb349cf68b0621ce605bee18db609df8",
}
CORPUS_COMMIT = "fca0a994ddb36b37d39b803e8a21880aaecb1d71"
TOL = 1e-3          # reference amounts are rounded to three decimals (1/3 -> 0.333)


# --------------------------------------------------------------------------- parsers
from legacy import composition_parser_v0_1_0 as v01  # noqa: E402
from composition_parser import parse_formula_grammar, refusal_of  # noqa: E402
from composition_record import build_mixture_record  # noqa: E402

PARSERS = ("v02_package", "v02_grammar", "v01_guarded", "v01_fallback", "raw_pymatgen")
PARSER_LABEL = {
    "v02_package": "package v0.2.0 (screen + grammar, pymatgen cross-check)",
    "v02_grammar": "package v0.2.0 grammar alone (no pymatgen)",
    "v01_guarded": "package v0.1.0 as submitted (pymatgen preferred, two guards)",
    "v01_fallback": "package v0.1.0 fallback grammar alone",
    "raw_pymatgen": "pymatgen.core.Composition, unguarded",
}


def _raw_pymatgen(s: str) -> dict[str, float]:
    from pymatgen.core import Composition

    comp = Composition(s)
    amounts = {str(el): float(a) for el, a in comp.get_el_amt_dict().items()}
    if not amounts:
        raise ValueError("Formula contains no elements")
    return amounts


def run_parser(name: str, s: str) -> tuple[dict[str, float] | None, str]:
    """Return (amounts or None, detail). detail is a controlled vocabulary value."""
    try:
        if name == "v02_package":
            amounts, backend = parse_formula_with_backend(s)
            return amounts, f"resolved:{backend}"
        if name == "v02_grammar":
            return parse_formula_grammar(s), "resolved:grammar"
        if name == "v01_guarded":
            amounts, backend = v01.parse_formula_with_backend(s)
            return amounts, f"resolved:{backend}"
        if name == "v01_fallback":
            return v01.parse_formula_fallback(s), "resolved:fallback"
        if name == "raw_pymatgen":
            return _raw_pymatgen(s), "resolved:pymatgen"
    except Exception as exc:  # noqa: BLE001 - any refusal is a refusal
        if name.startswith("v02"):
            _status, flags, _d = refusal_of(exc)
            return None, "refused:" + "|".join(flags)
        return None, "refused"  # comparators carry no controlled vocabulary; no class names
    raise KeyError(name)


# ------------------------------------------------------------------------- reference
def _num(x: str) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


_SYM = re.compile(r"[A-Z][a-z]?")


def reference_class(t: dict, string: str) -> tuple[str, str, dict[str, float] | None]:
    """Classify what the reference says about the *string* (not about the material).

    Returns (class, reason, reference amounts or None). Context that the paper states
    outside the string (an additive named elsewhere in the paragraph, a variable
    whose values are listed elsewhere) does not make the string itself
    indeterminate; an unquantified dopant or a free variable *inside* the string
    does.
    """
    comps = t.get("composition") or []
    if not comps:
        return "indeterminate", "no_reference_composition", None
    if t.get("elements_vars"):
        return "indeterminate", "element_variable", None
    if t.get("oxygen_deficiency"):
        return "indeterminate", "oxygen_deficiency_marker", None
    parsed: list[tuple[float, dict[str, float]]] = []
    for c in comps:
        coef = _num(c.get("amount"))
        if coef is None:
            return "indeterminate", "free_variable_coefficient", None
        els: dict[str, float] = {}
        for el, a in (c.get("elements") or {}).items():
            if el not in ELEMENT_SYMBOLS:
                return "indeterminate", "placeholder_element", None
            v = _num(a)
            if v is None:
                return "indeterminate", "free_variable_amount", None
            if v <= 0:
                return "indeterminate", "nonpositive_amount", None
            els[el] = v
        if coef <= 0 or not els:
            return "indeterminate", "nonpositive_amount", None
        parsed.append((coef, els))
    ref_elements = set().union(*(e for _, e in parsed))
    in_string = {m for m in _SYM.findall(string) if m in ELEMENT_SYMBOLS}
    for add in t.get("additives") or []:
        for el in _SYM.findall(add):
            if el in ELEMENT_SYMBOLS and el in in_string and el not in ref_elements:
                return "indeterminate", "unquantified_dopant_in_string", None
    if len(parsed) == 1 and parsed[0][0] == 1.0:
        return "determinate", "", parsed[0][1]
    totals: dict[str, float] = {}
    for coef, els in parsed:
        for el, v in els.items():
            totals[el] = totals.get(el, 0.0) + coef * v
    return "mixture", "multi_component", totals


def fractions_match(a: dict[str, float], b: dict[str, float]) -> bool:
    if set(a) != set(b):
        return False
    fa, fb = atomic_fractions(a), atomic_fractions(b)
    return max(abs(fa[k] - fb[k]) for k in fa) <= TOL


# ------------------------------------------------------------------ notation strata
STRATA = [
    ("dopant_annotation", re.compile(r":|doped|-doped", re.I)),
    ("percent_unit", re.compile(r"%")),
    ("free_variable", re.compile(r"(?<![A-Z])[xyzδΔ](?![a-z])|[±]")),
    ("mixture_or_dot", re.compile(r"[+·•∙⋅]|\d\s*[-–]\s*\d*\.?\d*[A-Z]|[a-z\d)]\.[A-Z]|[A-Z]\.\d+[A-Z]")),
    ("comma", re.compile(r",")),
    ("fraction_slash", re.compile(r"/")),
    ("decimal_subscript", re.compile(r"\d*\.\d+")),
    ("parenthetical", re.compile(r"[()\[\]]")),
]


def stratum_of(s: str) -> str:
    for name, rx in STRATA:
        if rx.search(s):
            return name
    if re.fullmatch(r"\s*(?:[A-Z][a-z]?\d*)+\s*", s):
        return "integer_formula"
    return "other"


# ------------------------------------------------------------- discordant mechanisms
def mechanism_of(s: str, ref_class: str, reason: str, ref: dict[str, float] | None,
                 got: dict[str, float]) -> str:
    """Deterministic mechanism label for a reference-discordant return."""
    if set(got) - ELEMENT_SYMBOLS:
        return "dummy_species_accepted"
    if ref_class == "determinate" and ref is not None:
        if set(got) != set(ref):
            return "element_set_differs"
        return "amounts_differ"
    if ref_class == "mixture":
        return "mixture_read_as_single_formula"
    return "returned_despite_" + reason


# ----------------------------------------------------------------------------- main
def load_corpus(path: Path) -> list[dict]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != CORPUS_SHA256.get(path.name):
        raise SystemExit(f"corpus SHA-256 mismatch for {path.name}: {digest}")
    with lzma.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)["reactions"]


def build_strings(reactions: list[dict]) -> pd.DataFrame:
    first: dict[str, dict] = {}
    dois: dict[str, set[str]] = {}
    for r in reactions:
        t = r["target"]
        s = t.get("material_string")
        if not s:
            continue
        dois.setdefault(s, set()).add(r["doi"])
        if s not in first:
            first[s] = {"doi": r["doi"], "target": t}
    rows = []
    for s, v in first.items():
        cls, reason, ref = reference_class(v["target"], s)
        rows.append({
            "string": s,
            "first_doi": v["doi"],
            "n_dois": len(dois[s]),
            "stratum": stratum_of(s),
            "reference_class": cls,
            "reference_reason": reason,
            "reference_amounts": None if ref is None else
                ";".join(f"{k}:{ref[k]:.6g}" for k in sorted(ref)),
            "_ref": ref,
        })
    return pd.DataFrame(rows)


def evaluate(df: pd.DataFrame) -> pd.DataFrame:
    for name in PARSERS:
        outcomes, details, amounts_col, mech = [], [], [], []
        for s, cls, reason, ref in zip(df["string"], df["reference_class"], df["reference_reason"], df["_ref"]):
            got, detail = run_parser(name, s)
            details.append(detail)
            if got is None:
                outcomes.append("refused")
                amounts_col.append("")
                mech.append("")
                continue
            amounts_col.append(";".join(f"{k}:{got[k]:g}" for k in sorted(got)))
            if cls == "determinate":
                if set(got) <= ELEMENT_SYMBOLS and fractions_match(got, ref):
                    outcomes.append("agree")
                    mech.append("")
                    continue
                outcomes.append("disagree")
            else:
                outcomes.append("returned")
            mech.append(mechanism_of(s, cls, reason, ref, got))
        df[f"{name}_outcome"] = outcomes
        df[f"{name}_detail"] = details
        df[f"{name}_amounts"] = amounts_col
        df[f"{name}_mechanism"] = mech
    return df


def evaluate_mixture_layer(df: pd.DataFrame) -> pd.DataFrame:
    """Score the v0.2 mixture layer on every string; only mixture references are compared."""
    outcomes, status = [], []
    for s, cls, ref in zip(df["string"], df["reference_class"], df["_ref"]):
        rec = build_mixture_record(s, hyphen_separator=True)
        status.append(rec["parse_status"])
        if rec["parse_status"] != "mixture_parsed":
            outcomes.append("refused")
        elif cls == "mixture" and fractions_match(rec["atomic_fractions"], ref):
            outcomes.append("agree")
        elif cls == "mixture":
            outcomes.append("disagree")
        else:
            outcomes.append("returned")
    df["mixture_layer_status"] = status
    df["mixture_layer_outcome"] = outcomes
    return df


def doi_split(doi: str) -> str:
    return "dev" if int(hashlib.sha256(doi.encode()).hexdigest(), 16) % 2 == 0 else "test"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path,
                    default=DATA / "external" / "solid-state_dataset_20200713.json.xz")
    ap.add_argument("--out", type=Path, default=DATA / "literature_strings_eval.csv")
    ap.add_argument("--exclude-strings-of", type=Path, default=None,
                    help="held-out mode: drop strings (and report DOIs) already present in this corpus")
    a = ap.parse_args(argv)
    df = build_strings(load_corpus(a.corpus))
    if a.exclude_strings_of is not None:
        dev_reactions = load_corpus(a.exclude_strings_of)
        dev = build_strings(dev_reactions)
        dev_strings = set(dev["string"])
        dev_dois = {r["doi"] for r in dev_reactions}      # every DOI in the development release
        n0 = len(df)
        df = df[~df["string"].isin(dev_strings)].reset_index(drop=True)
        df["doi_in_dev"] = df["first_doi"].isin(dev_dois)
        print(f"held-out: {n0} strings, {n0 - len(df)} already in dev, {len(df)} kept; "
              f"{int(df['doi_in_dev'].sum())} kept strings, from {df.loc[df.doi_in_dev, 'first_doi'].nunique()} DOIs, "
              "come from a DOI that also occurs in dev")
    df["split"] = df["first_doi"].map(doi_split)
    df = evaluate(df)
    df = evaluate_mixture_layer(df)
    df.drop(columns=["_ref"]).sort_values(["stratum", "string"]).to_csv(a.out, index=False)
    print(f"unique strings: {len(df)}  DOIs: {df['first_doi'].nunique()}")
    print(df["reference_class"].value_counts().to_string())
    for name in PARSERS + ("mixture_layer",):
        print(name, sorted(Counter(zip(df["reference_class"], df[f"{name}_outcome"])).items()))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
