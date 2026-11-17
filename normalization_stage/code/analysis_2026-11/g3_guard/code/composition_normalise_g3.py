"""G3: name-stoichiometry consistency guard on top of the frozen H2b stage (paper 12, 5 Nov 2026).

Imports ``composition_normalise.py`` (H2, SHA-256 1b06a5a4...163d12) and ``composition_normalise_guarded.py``
(H2b guard G1/G2, SHA-256 4577aa0f...36e858) unchanged. G3 runs only on strings that H2b resolved after v0.2.0
refused them. When a stripped descriptor names a compound, G3 derives what the name implies and refuses the
string (keeping the original v0.2.0 refusal) if the formula contradicts it.

Hazard class: a name whose stoichiometry contradicts the attached formula, for example
``strontium nitrate [Sr(NO3)]`` (strontium nitrate is Sr(NO3)2) or ``tantalum dioxide [Ta2O5]``.

  G3a  fixed-charge anion salt: exactly one unprefixed anion class word (nitrate, carbonate, hydroxide, sulfate,
       phosphate, fluoride, chloride, bromide, iodide), no ``ammonium``. The oxyanion's own oxygen must be present;
       extra oxygen counts as oxide (-2). Cations take the states a trivial name implies (pymatgen common states,
       mixed valence allowed between lowest and highest); they must balance the anion charge within 2%.
       Formulas with hydrogen outside a hydroxide are not judged.
  G3b  multiplicity prefix on a binary anion word (dioxide, trichloride, ...) with a binary formula: the anion
       count as written, or the anion-to-cation ratio, must equal the prefix number.
  G3c  stated oxidation state (Roman numeral after an element name; ferric, ferrous, cupric, cuprous, stannic,
       stannous) fixes that element's state in the G3a balance, or, for an oxide without an anion class word, in
       the oxygen balance (other cations: pymatgen common and ICSD states, as in G2).
"""
from __future__ import annotations

import re
from collections import Counter
from functools import lru_cache

from composition_parser import CompositionRefusal, parse_formula_with_backend
from composition_normalise import ELEMENT_NAMES, normalise
import composition_normalise_guarded as G

G3_VERSION = "g3-1"
G3_LOG: dict[str, str] = {}

# anion stem -> (central element or None, oxygen per central atom, charge per anion unit, element that counts units)
FIXED_ANIONS = {
    "nitrate": ("N", 3, -1), "carbonate": ("C", 3, -2), "sulfate": ("S", 4, -2), "sulphate": ("S", 4, -2),
    "phosphate": ("P", 4, -3), "hydroxide": ("H", 1, -1),
    "fluoride": ("F", 0, -1), "chloride": ("Cl", 0, -1), "bromide": ("Br", 0, -1), "iodide": ("I", 0, -1),
}
BINARY_ANIONS = {"oxide": "O", "sulfide": "S", "sulphide": "S", "chloride": "Cl", "fluoride": "F",
                 "bromide": "Br", "iodide": "I", "nitride": "N", "carbide": "C", "boride": "B",
                 "selenide": "Se", "telluride": "Te", "phosphide": "P", "hydride": "H", "silicide": "Si"}
MULT = {"di": 2, "tri": 3, "tetra": 4, "penta": 5, "hexa": 6, "hepta": 7, "octa": 8, "deca": 10}
_ANY_PREFIX = re.compile(r"^(di|tri|tetra|penta|hexa|hepta|octa|deca|dodeca|meta|ortho|pyro|poly|oxy)")
_MULT_RE = re.compile(rf"^({'|'.join(sorted(MULT, key=len, reverse=True))})"
                      rf"({'|'.join(sorted(BINARY_ANIONS, key=len, reverse=True))})s?$")
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7}
TRIVIAL_STATE = {"ferric": ("Fe", 3), "ferrous": ("Fe", 2), "cupric": ("Cu", 2), "cuprous": ("Cu", 1),
                 "stannic": ("Sn", 4), "stannous": ("Sn", 2)}


@lru_cache(maxsize=None)
def _common_range(el: str):
    from pymatgen.core import Element
    try:
        st = [s for s in Element(el).common_oxidation_states if s > 0]
    except Exception:  # noqa: BLE001
        return None
    return (float(min(st)), float(max(st))) if st else None


def _stripped_words(s: str, residual: str) -> list[str]:
    """Lower-case words present in the original string but removed by H2 (hyphenated labels split)."""
    orig = Counter(s.split())
    for t in residual.split():
        if orig[t] > 0:
            orig[t] -= 1
    words = []
    for tok, n in orig.items():
        for _ in range(n):
            for part in re.split(r"-", tok):
                part = part.strip("()[],;.")
                if part:
                    words.append(part)
    return words


def _stated_states(s: str) -> dict[str, float]:
    """Oxidation states fixed by the name: 'iron (III)', 'Copper (I)', 'ferric'."""
    out: dict[str, float] = {}
    toks = s.split()
    for i, t in enumerate(toks):
        w = t.lower()
        if w in TRIVIAL_STATE:
            el, v = TRIVIAL_STATE[w]; out[el] = float(v)
        m = re.fullmatch(r"\((I|II|III|IV|V|VI|VII)\)", t)
        if m and i > 0 and toks[i - 1].lower() in ELEMENT_NAMES:
            out[ELEMENT_NAMES[toks[i - 1].lower()]] = float(ROMAN[m.group(1)])
    return out


def _balances(cations: dict[str, float], anion_charge: float, fixed: dict[str, float], ranges) -> bool | None:
    lo = hi = 0.0
    for el, n in cations.items():
        if el in fixed:
            lo += n * fixed[el]; hi += n * fixed[el]; continue
        r = ranges(el)
        if r is None:
            return None          # no oxidation data: do not judge
        lo += n * r[0]; hi += n * r[1]
    tol = max(0.05, 0.02 * anion_charge)
    return lo - tol <= anion_charge <= hi + tol


def g3_check(s: str, residual: str, amounts: dict[str, float]) -> str | None:
    """Return a refusal reason if the stripped name contradicts the formula, else None."""
    words = [w.lower() for w in _stripped_words(s, residual)]
    stated = {el: v for el, v in _stated_states(s).items() if el in amounts}
    # G3b: multiplicity prefix on a binary anion word, binary formula
    for w in words:
        m = _MULT_RE.match(w)
        if m and len(amounts) == 2:
            an = BINARY_ANIONS[m.group(2)]
            if an in amounts:
                n = MULT[m.group(1)]
                cat = [v for e, v in amounts.items() if e != an][0]
                if not (abs(amounts[an] - n) < 1e-6 or abs(amounts[an] / cat - n) < 1e-6):
                    return "G3b_multiplicity_prefix_contradicted"
    # G3a: fixed-charge anion salts (unprefixed class word only)
    anion_words = [w.rstrip("s") if w.rstrip("s") in FIXED_ANIONS else w for w in words]
    anion_words = [w for w in anion_words if w in FIXED_ANIONS]
    if "ammonium" in words:
        return None
    if len(anion_words) == 1:
        stem = anion_words[0]
        central, k, q = FIXED_ANIONS[stem]
        if central not in amounts:
            return None          # the class word's element is absent: H2 would not have stripped it
        if "H" in amounts and stem != "hydroxide":
            return None          # hydrates, acid salts: not judged
        n_units = amounts[central]
        need_o = k * n_units
        o = amounts.get("O", 0.0)
        if k and o < need_o - 1e-6:
            return "G3a_anion_oxygen_missing"
        if stem == "hydroxide" and o < n_units - 1e-6:
            return "G3a_anion_oxygen_missing"
        extra_o = max(0.0, o - need_o) if k else o
        anion_charge = -q * n_units + 2.0 * extra_o
        skip = {central, "O"}
        cations = {e: v for e, v in amounts.items() if e not in skip}
        if not cations:
            return None
        ok = _balances(cations, anion_charge, stated, _common_range)
        if ok is False:
            return "G3c_stated_state_contradicted" if stated else "G3a_salt_charge_contradicted"
        return None
    # G3c in an oxide context: a stated state must fit the oxygen balance (other cations as in G2)
    if stated and "O" in amounts and not anion_words and "H" not in amounts:
        cations = {e: v for e, v in amounts.items() if e != "O"}
        ok = _balances(cations, 2.0 * amounts["O"], stated, G._ox_range)
        if ok is False:
            return "G3c_stated_state_contradicted"
    return None


def parse_formula_g3(s: str) -> tuple[dict[str, float], str, list[str]]:
    try:
        amounts, backend = parse_formula_with_backend(s)
        return amounts, backend, []
    except CompositionRefusal as original:
        amounts, backend, flags = G.parse_formula_guarded(s)   # raises the original refusal if H2b refuses
        residual, _ = normalise(s)
        reason = g3_check(s, residual, amounts)
        if reason:
            G3_LOG[s] = reason
            raise original
        return amounts, backend, flags
