"""Descriptor-word and stray-punctuation normalisation stage (H2, candidate for v0.3).

This stage runs only after the unchanged v0.2.0 pipeline (``parse_formula_with_backend``)
has refused a string. It removes material-label words from a closed lexicon and a few
patterns of stray punctuation, and passes the residual string back through the same
v0.2.0 lexical screen, grammar and pymatgen cross-check. It never overrides a refusal
flag that the residual still triggers, and every string it resolves carries one or more
controlled normalisation flags (``NORMALISATION_FLAGS``).

Safety rules (designed on the development release, split == "dev", only):
  * a word that changes or qualifies the composition (doped, coated, composite, rich,
    deficient, precursor, ...) blocks the stage entirely (``BLOCK_WORDS``);
  * a chemical-class word (titanate, ferrite, oxide, ...) or an element name (barium,
    lithium, ...) is removed only if every element it names occurs in the residual
    formula, so ``silver TiO2`` or ``titanate BaZrO3`` stay refused;
  * colons, percentages, slashes, plus signs, free variables and hyphens other than a
    polymorph prefix are never touched, so every v0.2.0 hazard class keeps its refusal;
  * the residual must contain at least two distinct elements and at least one amount
    of 1 or more (guards against fragments such as ``(Ba,`` or ``(Ba0.5Sr0.5,`` cut out
    of a longer formula);
  * no name-to-formula lookup: a string that is only a name (``barium titanate``)
    stays refused.
"""

from __future__ import annotations

import re

from composition_parser import (
    ELEMENT_SYMBOLS,
    CompositionRefusal,
    parse_formula_with_backend,
)

NORMALISER_VERSION = "h2-frozen"

NORMALISATION_FLAGS = {
    "descriptor_word_stripped",      # material-label word removed (closed lexicon)
    "polymorph_prefix_stripped",     # alpha-, beta-, c-, m-, h- ... before a formula
    "state_label_stripped",          # thermodynamic state label (s), (l), (cr) at the end
    "stray_punctuation_stripped",    # trailing , ; . or a dangling bracket from running text
    "standard_uncertainty_stripped", # crystallographic e.s.d. "0.13(2)" -> "0.13"
}

# ---------------------------------------------------------------- lexicon
ELEMENT_NAMES = {
    "hydrogen": "H", "lithium": "Li", "beryllium": "Be", "boron": "B", "carbon": "C",
    "nitrogen": "N", "oxygen": "O", "fluorine": "F", "sodium": "Na", "magnesium": "Mg",
    "aluminium": "Al", "aluminum": "Al", "silicon": "Si", "phosphorus": "P",
    "sulfur": "S", "sulphur": "S", "chlorine": "Cl", "potassium": "K", "calcium": "Ca",
    "scandium": "Sc", "titanium": "Ti", "vanadium": "V", "chromium": "Cr",
    "manganese": "Mn", "iron": "Fe", "cobalt": "Co", "nickel": "Ni", "copper": "Cu",
    "zinc": "Zn", "gallium": "Ga", "germanium": "Ge", "arsenic": "As", "selenium": "Se",
    "bromine": "Br", "rubidium": "Rb", "strontium": "Sr", "yttrium": "Y",
    "zirconium": "Zr", "niobium": "Nb", "molybdenum": "Mo", "ruthenium": "Ru",
    "rhodium": "Rh", "palladium": "Pd", "silver": "Ag", "cadmium": "Cd", "indium": "In",
    "tin": "Sn", "antimony": "Sb", "tellurium": "Te", "iodine": "I", "caesium": "Cs",
    "cesium": "Cs", "barium": "Ba", "lanthanum": "La", "cerium": "Ce",
    "praseodymium": "Pr", "neodymium": "Nd", "samarium": "Sm", "europium": "Eu",
    "gadolinium": "Gd", "terbium": "Tb", "dysprosium": "Dy", "holmium": "Ho",
    "erbium": "Er", "thulium": "Tm", "ytterbium": "Yb", "lutetium": "Lu",
    "hafnium": "Hf", "tantalum": "Ta", "tungsten": "W", "rhenium": "Re", "osmium": "Os",
    "iridium": "Ir", "platinum": "Pt", "gold": "Au", "mercury": "Hg", "thallium": "Tl",
    "lead": "Pb", "bismuth": "Bi", "thorium": "Th", "uranium": "U",
    "ferric": "Fe", "ferrous": "Fe", "cupric": "Cu", "cuprous": "Cu",
    "stannic": "Sn", "stannous": "Sn",
}

# chemical-class stems -> elements that must occur in the residual formula
_CLASS_STEMS = {
    "oxide": "O", "peroxide": "O", "hydroxide": "OH", "oxyfluoride": "OF", "oxynitride": "ON",
    "oxysulfide": "OS", "oxychloride": "OCl", "oxyphosphate": "OP",
    "nitride": "N", "carbide": "C", "boride": "B", "silicide": "Si", "sulfide": "S",
    "sulphide": "S", "selenide": "Se", "telluride": "Te", "fluoride": "F", "chloride": "Cl",
    "bromide": "Br", "iodide": "I", "hydride": "H", "phosphide": "P", "arsenide": "As",
    "antimonide": "Sb",
    "titanate": "TiO", "niobate": "NbO", "tantalate": "TaO", "zirconate": "ZrO",
    "hafnate": "HfO", "stannate": "SnO", "germanate": "GeO", "silicate": "SiO",
    "aluminate": "AlO", "gallate": "GaO", "indate": "InO", "borate": "BO",
    "phosphate": "PO", "arsenate": "AsO", "vanadate": "VO", "chromate": "CrO",
    "chromite": "CrO", "molybdate": "MoO", "tungstate": "WO", "manganite": "MnO",
    "manganate": "MnO", "ferrite": "FeO", "ferrate": "FeO", "cobaltite": "CoO",
    "cobaltate": "CoO", "nickelate": "NiO", "cuprate": "CuO", "cerate": "CeO",
    "bismuthate": "BiO", "antimonate": "SbO", "antimonite": "SbO", "tellurite": "TeO",
    "tellurate": "TeO", "selenite": "SeO", "sulfate": "SO", "sulphate": "SO",
    "carbonate": "CO", "nitrate": "NO", "ammonium": "NH", "phosphosilicate": "PSiO", "borosilicate": "BSiO",
    "aluminosilicate": "AlSiO", "nitridosilicate": "SiN", "oxyorthosilicate": "SiO",
}
_CLASS_PREFIX = r"(?:di|tri|tetra|penta|hexa|hepta|octa|deca|dodeca|meta|ortho|pyro|poly|oxy)*"
_CLASS_RE = re.compile(rf"^{_CLASS_PREFIX}({'|'.join(sorted(_CLASS_STEMS, key=len, reverse=True))})s?$")

# words that carry no composition information (structure type, form, morphology, role)
PLAIN_WORDS = {
    # structure and mineral types
    "perovskite", "perovskites", "double", "layered", "spinel", "spinels", "inverse",
    "garnet", "garnets", "delafossite", "fluorite", "pyrochlore", "pyrochlores",
    "columbite", "pyroxene", "argyrodite", "anorthite", "triplite", "olivine",
    "scheelite", "wolframite", "ilmenite", "rutile", "anatase", "brookite", "wurtzite",
    "zincblende", "sillenite", "apatite", "nasicon", "lisicon", "brownmillerite",
    "aurivillius", "hollandite", "magnetoplumbite", "hexaferrite", "hexaferrites",
    "bronze", "type", "structure", "structured", "lattice",
    # crystal system, polymorph and phase words
    "monoclinic", "tetragonal", "cubic", "hexagonal", "orthorhombic", "rhombohedral",
    "trigonal", "triclinic", "amorphous", "crystalline", "polycrystalline",
    "nanocrystalline", "alpha", "beta", "gamma", "phase", "phases", "pure", "single",
    "single-phase", "polymorph",
    # form and morphology
    "nanoparticle", "nanoparticles", "np", "nps", "mnp", "mnps", "particles", "particle",
    "nanopowder", "nanopowders", "powder", "powders", "film", "films", "thin", "thick",
    "ceramic", "ceramics", "glass", "glasses", "bulk", "crystal", "crystals",
    "nanocrystal", "nanocrystals", "microcrystals", "nanorods", "nanorod", "nanowires",
    "nanowire", "nanofibers", "nanofibres", "nanotubes", "nanosheets", "nanoplates",
    "nanocubes", "nanospheres", "microspheres", "nanostructures", "nanoflakes",
    "fibers", "fibres", "whiskers", "aerogel", "xerogel", "nano", "micro",
    "sample", "samples", "compound", "compounds", "material", "materials",
    "pristine", "undoped", "as-prepared", "as-synthesized", "as-synthesised",
    "synthesized", "synthesised", "prepared", "obtained",
    # role and property labels
    "phosphor", "phosphors", "catalyst", "catalysts", "photocatalyst", "electrolyte",
    "cathode", "anode", "conductor", "superconductor", "semiconductor", "alloy", "alloys",
    "magnetic", "ferroelectric", "multiferroic", "n-type", "p-type", "binary", "ternary",
    "quaternary", "complex", "mixed-metal", "the", "our", "novel", "new",
}

PROTOTYPE_WORDS = {"type", "structure", "structured", "like", "related"}

# words that qualify or change the composition: their presence blocks the stage
BLOCK_WORDS = re.compile(
    r"dop|coat|load|support|modif|substitut|defici|rich|poor|excess|added|addition|"
    r"contain|with|and|composite|hybrid|core|shell|mix|precursor|free|matrix|host|"
    r"solution|based|stabili|activat|codop|impregnat|decorat|grafted|blend|deficient|"
    r"nonstoich|non-stoich|overstoich|sub|hyper|hypo",
    re.I)

_GREEK = "αβγεζηθικλμνξπρστυφϕχψω"   # delta (δ) deliberately absent: it is a variable
_POLY_PREFIX = re.compile(rf"^(?:[{_GREEK}][′'’]*[-\s]+|(?![xyz]-)[a-z]{{1,2}}-\s*)(?=[A-Z(\[])")
_STATE_LABEL = re.compile(r"\s*\((?:s|l|g|cr|am|c)\)$")
_ESD = re.compile(r"(\d\.\d+)\(\d{1,2}\)")
_ROMAN = re.compile(r"^\((?:I|II|III|IV|V|VI|VII)\)$")


def _word_ok(word: str, residual_elements: set[str]) -> str | None:
    """Return the normalisation flag if *word* may be removed, else None."""
    w = word.lower().strip().strip("-")
    if not w:
        return None
    if w in PLAIN_WORDS:
        return "descriptor_word_stripped"
    if w in ELEMENT_NAMES:
        return "descriptor_word_stripped" if ELEMENT_NAMES[w] in residual_elements else None
    m = _CLASS_RE.match(w)
    if m:
        need = set(re.findall(r"[A-Z][a-z]?", _CLASS_STEMS[m.group(1)]))
        return "descriptor_word_stripped" if need <= residual_elements else None
    if "-" in w:   # hyphenated label: every part must be removable ("perovskite-type")
        parts = [p for p in w.split("-") if p]
        if parts and all(_word_ok(p, residual_elements) for p in parts):
            return "descriptor_word_stripped"
    return None


def _is_formula_token(tok: str) -> bool:
    return bool(re.search(r"[A-Z]", tok))


def _elements_in(text: str) -> set[str]:
    return {m for m in re.findall(r"[A-Z][a-z]?", text) if m in ELEMENT_SYMBOLS}


def normalise(s: str) -> tuple[str, list[str]]:
    """Return (residual string, normalisation flags). Flags empty means untouched."""
    flags: list[str] = []
    t = s.strip()
    if any(BLOCK_WORDS.search(w) for w in re.findall(r"[A-Za-z][a-z]{2,}", t)):
        return s, []
    # stray punctuation from running text
    t2 = t.lstrip("*†‡")
    t2b = re.sub(r"[,;.]+$", "", t2).rstrip()
    if t2b != t2 and t2b.count("(") + t2b.count("[") == t2b.count(")") + t2b.count("]") + 1 \
            and t2b[:1] in "([":
        t2b = t2b[1:]
    t2c = re.sub(r"\s*[(\[]$", "", t2b)
    if t2c != t:
        flags.append("stray_punctuation_stripped")
    t = t2c
    # thermodynamic state label
    t3 = _STATE_LABEL.sub("", t)
    if t3 != t:
        flags.append("state_label_stripped"); t = t3
    # crystallographic standard uncertainties
    t4 = _ESD.sub(r"\1", t)
    if t4 != t:
        flags.append("standard_uncertainty_stripped"); t = t4
    # descriptor words: split on whitespace, peel a hyphen-attached label word
    toks: list[str] = []
    for tok in t.split():
        if "-" in tok and _is_formula_token(tok):
            head, _, rest = tok.partition("-")
            left, _, tail = tok.rpartition("-")
            if head and not _is_formula_token(head) and _is_formula_token(rest):
                toks += [head + "-", rest]; continue
            if tail and not _is_formula_token(tail) and _is_formula_token(left):
                if tail.lower() in PROTOTYPE_WORDS:
                    # "ThCr2Si2-type CeNi2As2": the prototype formula is a label, not a component
                    toks.append("\x00" + tok); continue
                toks += [left, "-" + tail]; continue
        toks.append(tok)
    def _is_label(x: str) -> bool:
        return (x.startswith("\x00") or bool(_ROMAN.match(x)) or x.lower().strip("-") in PLAIN_WORDS
                or x.lower().strip("-") in ELEMENT_NAMES or bool(_CLASS_RE.match(x.lower().strip("-"))))
    formula_idx = [i for i, x in enumerate(toks) if _is_formula_token(x) and not _is_label(x)]
    residual_elements = _elements_in(" ".join(toks[i] for i in formula_idx))
    kept: list[str] = []
    removed_idx: list[int] = []
    for i, x in enumerate(toks):
        if i in formula_idx:
            kept.append(x); continue
        if x.startswith("\x00"):
            if formula_idx:
                removed_idx.append(i); continue
            kept.append(x[1:]); continue
        if _ROMAN.match(x):
            # an oxidation-state numeral is removed only right after an element name
            # ("Copper (I) aluminate"); a bare "(V)" may be vanadium and is kept
            if i > 0 and toks[i - 1].lower() in ELEMENT_NAMES:
                removed_idx.append(i)
            else:
                kept.append(x)
            continue
        if _word_ok(x, residual_elements):
            removed_idx.append(i)
        else:
            kept.append(x)
    if removed_idx and formula_idx and any(min(formula_idx) < i < max(formula_idx) for i in removed_idx):
        # a label word between two formula chunks may separate two phases: leave the refusal
        return s, []
    if removed_idx:
        flags.append("descriptor_word_stripped")
    t = " ".join(kept)
    # polymorph prefix on the (first) formula token
    t5 = _POLY_PREFIX.sub("", t, count=1)
    if t5 != t:
        flags.append("polymorph_prefix_stripped"); t = t5
    return t, list(dict.fromkeys(flags))


def parse_formula_normalised(s: str) -> tuple[dict[str, float], str, list[str]]:
    """v0.2.0 first; on refusal, normalise and re-run v0.2.0 on the residual."""
    try:
        amounts, backend = parse_formula_with_backend(s)
        return amounts, backend, []
    except CompositionRefusal as original:
        residual, flags = normalise(s)
        if not flags or residual.strip() == s.strip() or not residual.strip():
            raise original
        try:
            amounts, backend = parse_formula_with_backend(residual)
        except CompositionRefusal:
            raise original
        if len([e for e in amounts if amounts[e] > 0]) < 2:
            raise original
        if max(amounts.values()) < 1:
            # every amount fractional, e.g. "(Ba0.5Sr0.5," or "(Cr1/12Al1/12": a site group
            # cut out of a longer formula, not a whole formula
            raise original
        return amounts, backend, flags
