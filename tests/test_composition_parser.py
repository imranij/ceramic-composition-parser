"""Parser v0.2.0: screen rules, grammar, cross-check, and the frozen v0.1.0 behaviour.

Every refusal example below is a string that occurs in the literature corpora
(Kononova et al. solid-state or sol-gel release) or in the hand-written benchmarks.
"""

from __future__ import annotations

import pandas as pd
import pytest

from composition_parser import (
    BACKEND_AGREE,
    BACKEND_GRAMMAR_ONLY,
    ELEMENT_SYMBOLS,
    FLAG_CLASS,
    STATUS_AMBIGUOUS_REJECTED,
    STATUS_UNSUPPORTED_REJECTED,
    CompositionRefusal,
    atomic_fractions,
    parse_formula,
    parse_formula_grammar,
    parse_formula_with_backend,
    try_pymatgen_parse,
)
from legacy import composition_parser_v0_1_0 as v01


def flags(s: str) -> list[str]:
    with pytest.raises(CompositionRefusal) as e:
        parse_formula(s)
    return e.value.flags


def test_element_table_is_the_118_iupac_symbols():
    assert len(ELEMENT_SYMBOLS) == 118
    assert {"Nh", "Mc", "Ts", "Og"} <= ELEMENT_SYMBOLS
    assert not ({"D", "T", "M", "Ln", "RE", "Xx", "A"} & ELEMENT_SYMBOLS)


@pytest.mark.parametrize("s,flag,status", [
    ("(Ba,Sr)TiO3", "comma_site_fraction_missing", STATUS_AMBIGUOUS_REJECTED),
    ("BaTiO3.2H2O", "hydration_or_dot_notation", STATUS_AMBIGUOUS_REJECTED),
    ("FeCl3.6H2O", "hydration_or_dot_notation", STATUS_AMBIGUOUS_REJECTED),
    ("Li2O.2SiO2", "hydration_or_dot_notation", STATUS_AMBIGUOUS_REJECTED),
    ("Ba.9Sr.1TiO3", "hydration_or_dot_notation", STATUS_AMBIGUOUS_REJECTED),
    ("VOHPO4·0.5H2O", "hydration_or_dot_notation", STATUS_AMBIGUOUS_REJECTED),
    ("Ba(1-x)SrxTiO3", "free_variable_stoichiometry", STATUS_AMBIGUOUS_REJECTED),
    ("Gd0.95Ba2.05Cu3Oy", "free_variable_stoichiometry", STATUS_AMBIGUOUS_REJECTED),
    ("LaBaCo2O5+δ", "free_variable_stoichiometry", STATUS_AMBIGUOUS_REJECTED),
    ("Y2O3:Eu", "dopant_convention_missing", STATUS_AMBIGUOUS_REJECTED),
    ("CaSc2O4:1%Ce3+", "unit_convention_missing", STATUS_AMBIGUOUS_REJECTED),
    ("Ba2+Ti4+O3", "charge_balance_unspecified", STATUS_AMBIGUOUS_REJECTED),
    ("La(Sr)GaO3", "single_element_group", STATUS_AMBIGUOUS_REJECTED),
    ("BaW0", "nonpositive_amount", STATUS_AMBIGUOUS_REJECTED),
    ("Cu2Zn0.0Mg1.0SnS4", "nonpositive_amount", STATUS_AMBIGUOUS_REJECTED),
    ("BaO-2SiO2", "mixture_or_arithmetic_notation", STATUS_UNSUPPORTED_REJECTED),
    ("0.94Na0.5Bi0.5TiO3-0.06BaTiO3", "mixture_or_arithmetic_notation", STATUS_UNSUPPORTED_REJECTED),
    ("NaCl+KCl", "mixture_or_arithmetic_notation", STATUS_UNSUPPORTED_REJECTED),
    ("Pt Nb2O5", "non_formula_word", STATUS_UNSUPPORTED_REJECTED),
    ("CP Cu3Mo6S8", "non_formula_word", STATUS_UNSUPPORTED_REJECTED),
    ("PBN [Pb0.63Ba0.38Nb2O6]", "non_formula_word", STATUS_UNSUPPORTED_REJECTED),
    ("mullite", "non_formula_word", STATUS_UNSUPPORTED_REJECTED),
    ("Xx2O3", "unknown_element_symbol", STATUS_UNSUPPORTED_REJECTED),
    ("MS2", "unknown_element_symbol", STATUS_UNSUPPORTED_REJECTED),
    ("Ln0.85Ca0.15MnO3", "unknown_element_symbol", STATUS_UNSUPPORTED_REJECTED),
    ("BNT", "unknown_element_symbol", STATUS_UNSUPPORTED_REJECTED),
    ("CdS@ZrO2", "unconsumed_separator", STATUS_UNSUPPORTED_REJECTED),
])
def test_screen_rule_fires_with_controlled_flag(s, flag, status):
    with pytest.raises(CompositionRefusal) as e:
        parse_formula(s)
    assert flag in e.value.flags
    assert e.value.status == status
    assert all(f in FLAG_CLASS for f in e.value.flags)


@pytest.mark.parametrize("s,expected", [
    ("Ba0.9Sr0.1TiO3", {"Ba": 0.9, "Sr": 0.1, "Ti": 1, "O": 3}),
    ("(Ba0.9(Sr0.5Ca0.5)0.1)TiO3", {"Ba": 0.9, "Sr": 0.05, "Ca": 0.05, "Ti": 1, "O": 3}),
    ("La4O4[AsO4]Br", {"La": 4, "O": 8, "As": 1, "Br": 1}),
    ("Bi(Ni1/2Ti1/2)O3", {"Bi": 1, "Ni": 0.5, "Ti": 0.5, "O": 3}),
    ("(La0.98Bi.02)2MgTiO6", {"La": 1.96, "Bi": 0.04, "Mg": 1, "Ti": 1, "O": 6}),
    ("Ba (Bi0.5Nb0.5)O3", {"Ba": 1, "Bi": 0.5, "Nb": 0.5, "O": 3}),
    ("InInO3", {"In": 2, "O": 3}),
    ("YYOFN", {"Y": 2, "O": 1, "F": 1, "N": 1}),
    ("Ca10(PO4)6(OH)2", {"Ca": 10, "P": 6, "O": 26, "H": 2}),
])
def test_grammar_resolves_exactly(s, expected):
    got = parse_formula_grammar(s)
    assert set(got) == set(expected)
    for k, v in expected.items():
        assert got[k] == pytest.approx(v)
    assert sum(atomic_fractions(got).values()) == pytest.approx(1.0)


def test_mismatched_bracket_types_are_refused():
    with pytest.raises(CompositionRefusal):
        parse_formula("Ba(Ti0.9Zr0.1]O3")


def test_cross_check_attribution():
    if try_pymatgen_parse("BaTiO3") is None:
        pytest.skip("pymatgen not installed")
    assert parse_formula_with_backend("BaTiO3")[1] == BACKEND_AGREE
    assert parse_formula_with_backend("La2/3Sr1/3MnO3")[1] == BACKEND_GRAMMAR_ONLY


def test_accepted_language_does_not_depend_on_pymatgen():
    for s in ["BaTiO3", "Bi(Ni1/2Ti1/2)O3", "La4O4[AsO4]Br"]:
        assert parse_formula_with_backend(s, cross_check=False)[0] == parse_formula_with_backend(s)[0]


# ---- the hazards raw pymatgen accepts, kept as tests so a pymatgen change is noticed

@pytest.mark.parametrize("s,check", [
    ("BaTiO3.2H2O", lambda d: d["O"] == pytest.approx(4.2)),
    ("Li2O.2SiO2", lambda d: d["O"] == pytest.approx(2.2)),
    ("BaO-2SiO2", lambda d: "O" not in d),
    ("BNT", lambda d: "H" in d),
    ("Xx2O3", lambda d: "Xx" in d),
])
def test_raw_pymatgen_still_shows_the_hazard(s, check):
    raw = try_pymatgen_parse(s)
    if raw is None:
        pytest.skip("pymatgen not installed")
    assert check(raw)


# ---- the frozen v0.1.0 parser behaves exactly as submitted

def test_v01_frozen_behaviour():
    assert v01.parse_formula_fallback("Ba.9Sr.1TiO3")["Ba"] == pytest.approx(0.9)
    with pytest.raises(ValueError, match="hydrate"):
        v01.parse_formula_with_backend("BaTiO3.2H2O")
    with pytest.raises(ValueError, match="[Uu]nknown element"):
        v01.parse_formula_with_backend("Xx2O3")
    if try_pymatgen_parse("BaTiO3") is not None:
        assert v01.parse_formula_with_backend("BaO-2SiO2")[0] == {"Ba": 1.0, "Si": 1.0}


def test_corpus_formulas_all_resolve_and_match_committed_vectors():
    df = pd.read_csv(__import__("pathlib").Path(__file__).resolve().parents[1]
                     / "data" / "processed_results" / "corpus_backend_check.csv")
    total = df[df.source_dataset == "TOTAL"].iloc[0]
    for cfg in ("v02_package", "v02_grammar", "v01_guarded", "v01_fallback", "raw_pymatgen"):
        assert int(total[f"{cfg}_resolved"]) == 28100
        assert int(total[f"{cfg}_matches_committed"]) == 28100
