"""Namespaced facade over the flat analysis modules in ``code/``.

The result-producing scripts import each other by bare module name, which is how
the published numbers were generated; that layout is preserved verbatim. This
package re-exports the stable public surface under one importable name so that a
library consumer does not have to depend on module names as generic as
``composition_parser``.

    from ceramic_composition_parser import build_record, parse_formula
"""

from __future__ import annotations

from composition_parser import (
    FLAG_CLASS,
    PARSER_VERSION,
    CompositionRefusal,
    lexical_screen,
    parse_formula_grammar,
    ELEMENT_SYMBOLS,
    atomic_fractions,
    parse_formula,
    parse_formula_fallback,
    parse_formula_with_backend,
    try_pymatgen_parse,
)
from composition_record import (
    SCHEMA_PATH,
    build_record,
    build_mixture_record,
    build_percentage_record,
    build_records,
    load_schema,
    validate_record,
)

__version__ = "0.2.0"

__all__ = [
    "FLAG_CLASS",
    "PARSER_VERSION",
    "CompositionRefusal",
    "lexical_screen",
    "parse_formula_grammar",
    "build_mixture_record",
    "build_percentage_record",
    "ELEMENT_SYMBOLS",
    "SCHEMA_PATH",
    "atomic_fractions",
    "build_record",
    "build_records",
    "load_schema",
    "parse_formula",
    "parse_formula_fallback",
    "parse_formula_with_backend",
    "try_pymatgen_parse",
    "validate_record",
]
