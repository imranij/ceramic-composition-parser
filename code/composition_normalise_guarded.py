"""H2b: the frozen H2 normalisation stage plus an element-list guard (paper 12, 4 Nov 2026).

``composition_normalise.py`` (H2, frozen 3 Nov 2026, SHA-256 1b06a5a4...163d12) is imported unchanged.
This module adds one check that runs only on strings the H2 stage resolved after v0.2.0 refused them.
Strings that v0.2.0 resolves on its own are never touched.

Hazard class (found by the 3 Nov held-out hand check): element-list shorthand written like a formula
(``CeZrO2 oxide``, ``VZrPO oxide``, ``alpha-SiAlON``). Once a descriptor word or prefix is stripped, the residual
looks like a stoichiometry although the authors only listed the elements of a mixed phase.

Guard (designed on the development release only):
  G1  element-list signature: the residual formula carries no digit at all and has four or more elements;
  G2  charge implausibility for oxides: the composition contains oxygen, and no assignment of the cations'
      known oxidation states (union of pymatgen's common and ICSD states; oxygen fixed at -2; mixed valence
      allowed, i.e. each cation may take any value between its lowest and highest state) gives zero net charge
      within 2% of the oxygen charge (subscripts in papers are rounded).
A string that fails G1 or G2 keeps its original v0.2.0 refusal; the guard reason is recorded in
``GUARD_LOG`` for reporting.
"""
from __future__ import annotations

import re
from functools import lru_cache

from composition_parser import CompositionRefusal, parse_formula_with_backend
from composition_normalise import normalise, parse_formula_normalised

GUARD_VERSION = "h2b-guard-1"
GUARD_LOG: dict[str, str] = {}


@lru_cache(maxsize=None)
def _ox_range(el: str) -> tuple[float, float] | None:
    from pymatgen.core import Element
    try:
        states = set(Element(el).common_oxidation_states) | set(Element(el).icsd_oxidation_states)
    except Exception:  # noqa: BLE001
        return None
    states.add(0) if el in {"H"} else None
    if not states:
        return None
    return float(min(states)), float(max(states))


def g1_element_list(residual: str, amounts: dict[str, float]) -> bool:
    return not re.search(r"\d", residual) and len(amounts) >= 4


def g2_charge_implausible(amounts: dict[str, float]) -> bool:
    if "O" not in amounts:
        return False
    lo = hi = -2.0 * amounts["O"]
    for el, n in amounts.items():
        if el == "O":
            continue
        r = _ox_range(el)
        if r is None:
            return False          # no oxidation data: do not judge
        lo += n * r[0]; hi += n * r[1]
    # subscripts in papers are rounded (K0.8Ti1.73Li0.27O4 balances to 7.99 against 8):
    # allow 2% of the oxygen charge
    tol = max(0.05, 0.02 * 2.0 * amounts["O"])
    return not (lo - tol <= 0.0 <= hi + tol)


def parse_formula_guarded(s: str) -> tuple[dict[str, float], str, list[str]]:
    try:
        amounts, backend = parse_formula_with_backend(s)
        return amounts, backend, []
    except CompositionRefusal as original:
        amounts, backend, flags = parse_formula_normalised(s)   # raises the original refusal if H2 fails
        residual, _ = normalise(s)
        if g1_element_list(residual, amounts):
            GUARD_LOG[s] = "G1_element_list"; raise original
        if g2_charge_implausible(amounts):
            GUARD_LOG[s] = "G2_charge_implausible"; raise original
        return amounts, backend, flags
