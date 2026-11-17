"""Runtime contract between the parser and ``schema/composition_record_schema.json``.

Three builders, one record type (``CeramicCompositionRecord``, schema 1.1.0):

``build_record(formula)``
    one formula string. Resolved, or refused with controlled ``parse_status`` and
    ``ambiguity_flags`` taken directly from the parser's ``CompositionRefusal``.
``build_mixture_record(expression, roles=...)``
    a coefficient-weighted mixture such as ``0.98BaTiO3+0.02Y2O3``.
``build_percentage_record(host, additives, unit=..., basis=...)``
    a host with one or more additives stated in mol%, wt% or at%.

Role assignment is explicit. A record never infers which component is the host:
roles are supplied by the caller (``role_source = caller_supplied``), or assigned by
the one named opt-in rule ``largest_coefficient_is_host``, or left ``unknown``
(``role_source = unassigned``). A percentage record is host-plus-additives by
construction, because the caller names the host.

Every record carries ``schema_version``, ``provenance.parser_version`` and
``provenance.parser_backend``. ``validate_record`` checks a record against the
committed schema with ``jsonschema``.
"""

from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from composition_parser import (  # noqa: E402
    FLAG_CLASS,
    PARSER_VERSION,
    STATUS_AMBIGUOUS_REJECTED,
    STATUS_FORMULA_PARSED,
    STATUS_PARSE_ERROR,
    STATUS_UNSUPPORTED_REJECTED,
    CompositionRefusal,
    atomic_fractions,
    parse_formula_with_backend,
    refusal_of,
)

SCHEMA_VERSION = "1.1.0"
STATUS_MIXTURE_PARSED = "mixture_parsed"
ROLE_RULE_LARGEST = "rule:largest_coefficient_is_host"

# Names kept from v0.1 so that existing callers and tests continue to import them.
FLAG_COMMA = "comma_site_fraction_missing"
FLAG_HYDRATE = "hydration_or_dot_notation"
FLAG_UNKNOWN_ELEMENT = "unknown_element_symbol"
FLAG_UNCONSUMED_SEPARATOR = "unconsumed_separator"
FLAG_MANUAL = "manual_validation_required"


def _locate_schema() -> Path:
    here = Path(__file__).resolve()
    for candidate in (
        here.parents[1] / "schema" / "composition_record_schema.json",
        here.parent / "ceramic_composition_parser" / "schema" / "composition_record_schema.json",
    ):
        if candidate.is_file():
            return candidate
    return here.parents[1] / "schema" / "composition_record_schema.json"


SCHEMA_PATH = _locate_schema()


@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_record(record: dict[str, Any]) -> dict[str, Any]:
    """Validate against the committed schema. Raises ``jsonschema.ValidationError``."""
    import jsonschema

    jsonschema.validate(instance=record, schema=load_schema())
    return record


def _empty(expression: str, provenance: dict[str, Any] | None) -> dict[str, Any]:
    prov = dict(provenance or {})
    prov.setdefault("parser_version", PARSER_VERSION)
    prov["parser_backend"] = "not_resolved"
    return {
        "schema_version": SCHEMA_VERSION,
        "raw_expression": str(expression),
        "parse_status": STATUS_PARSE_ERROR,
        "components": [],
        "atomic_fractions": {},
        "provenance": prov,
        "ambiguity_flags": [],
    }


def _refuse(record: dict[str, Any], exc: BaseException) -> dict[str, Any]:
    status, flags, detail = refusal_of(exc)
    record["parse_status"] = status
    record["ambiguity_flags"] = flags
    record["components"] = []
    record["atomic_fractions"] = {}
    record["provenance"]["curator_note"] = detail
    return record


# ------------------------------------------------------------------ single formula
def build_record(expression: str, *, provenance: dict[str, Any] | None = None,
                 role: str | None = None) -> dict[str, Any]:
    """Record for one formula string. Never raises on an unparseable string."""
    record = _empty(expression, provenance)
    try:
        amounts, backend = parse_formula_with_backend(str(expression))
    except Exception as exc:  # noqa: BLE001 - any refusal is a refusal
        return _refuse(record, exc)
    record["parse_status"] = STATUS_FORMULA_PARSED
    record["atomic_fractions"] = {k: float(v) for k, v in atomic_fractions(amounts).items()}
    record["components"] = [{
        "role": role or "unknown",
        "role_source": "caller_supplied" if role else "single_formula",
        "formula": str(expression),
        "coefficient": 1.0,
        "unit": "formula_units",
    }]
    record["provenance"]["parser_backend"] = backend
    return record


def build_records(expressions: Iterable[str], **kwargs: Any) -> list[dict[str, Any]]:
    return [build_record(e, **kwargs) for e in expressions]


# --------------------------------------------------------------- mixture expression
_COEF = r"(?:\d+/\d+|\d+\.\d+|\d+)"
_TERM = re.compile(rf"^\s*({_COEF})?\s*(.+?)\s*$")


def _split_top_level(expr: str, seps: str) -> list[str]:
    parts, depth, cur = [], 0, []
    for ch in expr:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch in seps and depth == 0:
            parts.append("".join(cur)); cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return parts


def _coef(text: str | None) -> float:
    if text is None:
        return 1.0
    if "/" in text:
        a, b = text.split("/")
        return float(a) / float(b)
    return float(text)


def parse_mixture_expression(expression: str, *, hyphen_separator: bool = False) -> list[tuple[float, str]]:
    """Split ``c1 F1 + c2 F2 + ...`` into (coefficient, formula) terms.

    ``+`` is the separator. A hyphen is accepted as a separator only when the
    caller opts in *and* every term carries an explicit coefficient *and* the
    coefficients sum to 1 within 1e-6, because otherwise a hyphen cannot be told
    apart from a minus sign inside a subscript (``Ba1-xSrxTiO3``).
    """
    seps = "+-–" if hyphen_separator else "+"
    raw_terms = _split_top_level(expression, seps)
    if len(raw_terms) < 2 or any(not t.strip() for t in raw_terms):
        raise CompositionRefusal(["mixture_or_arithmetic_notation"],
                                 f"not a two-or-more-term mixture: {expression}")
    terms: list[tuple[float, str]] = []
    for t in raw_terms:
        m = _TERM.match(t)
        coef_txt, formula = m.group(1), m.group(2)
        if formula.startswith("(") and formula.endswith(")") and coef_txt is not None:
            inner = formula[1:-1]
            if inner.count("(") == inner.count(")"):
                formula = inner
        terms.append((_coef(coef_txt), formula))
        if hyphen_separator and coef_txt is None:
            raise CompositionRefusal(["mixture_or_arithmetic_notation"],
                                     f"hyphen-separated term without coefficient: {t!r}")
    if hyphen_separator and abs(sum(c for c, _ in terms) - 1.0) > 1e-6:
        raise CompositionRefusal(["mixture_or_arithmetic_notation"],
                                 f"hyphen-separated coefficients do not sum to 1: {expression}")
    if any(c <= 0 for c, _ in terms):
        raise CompositionRefusal(["nonpositive_amount"], expression)
    return terms


def _assign_roles(n: int, coefs: list[float], roles: list[str] | None,
                  role_rule: str | None) -> tuple[list[str], str]:
    if roles is not None:
        if len(roles) != n:
            raise ValueError(f"{len(roles)} roles supplied for {n} components")
        return list(roles), "caller_supplied"
    if role_rule == "largest_coefficient_is_host":
        top = max(coefs)
        if coefs.count(top) > 1:
            raise CompositionRefusal(["manual_validation_required"],
                                     "largest-coefficient rule is tied; supply roles")
        return ["host" if c == top else "additive" for c in coefs], ROLE_RULE_LARGEST
    if role_rule is not None:
        raise ValueError(f"unknown role rule {role_rule!r}")
    return ["unknown"] * n, "unassigned"


def build_mixture_record(expression: str, *, roles: list[str] | None = None,
                         role_rule: str | None = None, hyphen_separator: bool = False,
                         unit: str = "formula_units",
                         provenance: dict[str, Any] | None = None) -> dict[str, Any]:
    """Record for a coefficient-weighted mixture expression."""
    record = _empty(expression, provenance)
    try:
        terms = parse_mixture_expression(expression, hyphen_separator=hyphen_separator)
        resolved = [(c, f, *parse_formula_with_backend(f)) for c, f in terms]
        coefs = [c for c, *_ in resolved]
        role_list, source = _assign_roles(len(resolved), coefs, roles, role_rule)
    except Exception as exc:  # noqa: BLE001
        return _refuse(record, exc)
    totals: dict[str, float] = {}
    for c, _f, amounts, _b in resolved:
        for el, a in amounts.items():
            totals[el] = totals.get(el, 0.0) + c * a
    backends = {b for *_, b in resolved}
    record["parse_status"] = STATUS_MIXTURE_PARSED
    record["atomic_fractions"] = atomic_fractions(totals)
    record["components"] = [
        {"role": r, "role_source": source, "formula": f, "coefficient": float(c), "unit": unit}
        for (c, f, _a, _b), r in zip(resolved, role_list)
    ]
    record["provenance"]["parser_backend"] = (backends.pop() if len(backends) == 1
                                              else "grammar_only_pymatgen_refused"
                                              if "grammar_only_pymatgen_refused" in backends
                                              else "grammar+pymatgen_agree")
    return record


# ------------------------------------------------------------- percentage records
def build_percentage_record(host: str, additives: list[Any], *, unit: str, basis: str,
                            at_counts: str | None = None,
                            provenance: dict[str, Any] | None = None) -> dict[str, Any]:
    """Record for host + additives stated as percentages under a declared convention.

    ``additives`` is a list of ``composition_semantics.Additive``. The host is the
    component the caller names as host; nothing is inferred.
    """
    from composition_semantics import additive_ratios, mixture_atomic_fractions, percentage_mixture

    label = " + ".join(f"{a.percent:g} {unit} {a.formula}" for a in additives)
    record = _empty(f"{host} + {label}", provenance)
    try:
        ratios = additive_ratios(host, additives, unit, basis, at_counts)
        fractions = mixture_atomic_fractions(percentage_mixture(host, additives, unit, basis, at_counts))
        _amounts, backend = parse_formula_with_backend(host)
    except Exception as exc:  # noqa: BLE001
        return _refuse(record, exc)
    host_c = {"role": "host", "role_source": "caller_supplied", "formula": host,
              "coefficient": 1.0, "unit": "formula_units", "unit_basis": "not_applicable"}
    comps = [host_c]
    for a, r in zip(additives, ratios):
        c = {"role": "additive", "role_source": "caller_supplied", "formula": a.formula,
             "coefficient": float(r), "unit": unit, "percent": float(a.percent),
             "unit_basis": basis}
        if unit == "at%":
            c["at_percent_counts"] = at_counts
            if at_counts == "dopant_element_atoms":
                c["dopant_element"] = a.dopant_element
        comps.append(c)
    record["parse_status"] = STATUS_MIXTURE_PARSED
    record["components"] = comps
    record["atomic_fractions"] = fractions
    record["provenance"]["parser_backend"] = backend
    return record


def main(argv: list[str] | None = None) -> int:
    """CLI: emit one JSON record per formula given on the command line."""
    import argparse

    ap = argparse.ArgumentParser(description=main.__doc__)
    ap.add_argument("expressions", nargs="+")
    ap.add_argument("--mixture", action="store_true", help="treat each argument as a mixture expression")
    ap.add_argument("--no-validate", action="store_true")
    a = ap.parse_args(argv)
    out = []
    for expr in a.expressions:
        rec = build_mixture_record(expr) if a.mixture else build_record(expr)
        if not a.no_validate:
            validate_record(rec)
        out.append(rec)
    print(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
