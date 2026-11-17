"""The schema is a runtime contract on every output path, including the CSV files."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
import pytest

from composition_parser import FLAG_CLASS, PARSER_VERSION
from composition_record import (
    SCHEMA_PATH,
    SCHEMA_VERSION,
    build_mixture_record,
    build_percentage_record,
    build_record,
    load_schema,
    validate_record,
)
from composition_semantics import Additive, additive_ratios

jsonschema = pytest.importorskip("jsonschema")

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def test_schema_is_valid_and_versioned():
    schema = load_schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    assert schema["properties"]["schema_version"]["const"] == SCHEMA_VERSION


def test_flag_vocabulary_is_identical_in_code_and_schema():
    enum = load_schema()["properties"]["ambiguity_flags"]["items"]["enum"]
    assert set(enum) == set(FLAG_CLASS)


def test_packaged_schema_copy_is_identical():
    packaged = ROOT / "ceramic_composition_parser" / "schema" / "composition_record_schema.json"
    assert packaged.read_bytes() == SCHEMA_PATH.read_bytes()


@pytest.mark.parametrize("bench", ["stress_benchmark.csv", "dopant_notation_benchmark.csv"])
def test_every_benchmark_string_yields_a_valid_record(bench):
    for f in pd.read_csv(DATA / bench)["formula"]:
        rec = validate_record(build_record(f))
        assert rec["provenance"]["parser_version"] == PARSER_VERSION


def test_refusal_has_flags_and_no_fractions():
    rec = validate_record(build_record("(Ba,Sr)TiO3"))
    assert rec["parse_status"] == "ambiguous_rejected"
    assert rec["ambiguity_flags"] == ["comma_site_fraction_missing"]
    assert rec["atomic_fractions"] == {} and rec["components"] == []


@pytest.mark.parametrize("corrupt", [
    lambda r: r["atomic_fractions"].update({"Ba": 1.5}),
    lambda r: r.update({"ambiguity_flags": ["ValueError"]}),
    lambda r: r.update({"parse_status": "ambiguous_rejected"}),     # refusal with fractions
    lambda r: r["components"][0].update({"unit": "ppm"}),
])
def test_corrupted_records_fail_validation(corrupt):
    rec = build_record("BaTiO3")
    corrupt(rec)
    with pytest.raises(jsonschema.ValidationError):
        validate_record(rec)


def test_roles_are_never_inferred():
    rec = validate_record(build_mixture_record("0.98BaTiO3+0.02Y2O3"))
    assert [c["role"] for c in rec["components"]] == ["unknown", "unknown"]
    assert {c["role_source"] for c in rec["components"]} == {"unassigned"}
    rec = validate_record(build_mixture_record("0.98BaTiO3+0.02Y2O3", roles=["host", "additive"]))
    assert [c["role"] for c in rec["components"]] == ["host", "additive"]
    rec = validate_record(build_mixture_record("0.98BaTiO3+0.02Y2O3", role_rule="largest_coefficient_is_host"))
    assert rec["components"][0]["role_source"] == "rule:largest_coefficient_is_host"


def test_hyphen_mixture_requires_opt_in_coefficients_and_unit_sum():
    assert build_mixture_record("0.94Na0.5Bi0.5TiO3-0.06BaTiO3")["parse_status"] == "unsupported_rejected"
    ok = validate_record(build_mixture_record("0.94Na0.5Bi0.5TiO3-0.06BaTiO3", hyphen_separator=True))
    assert ok["parse_status"] == "mixture_parsed"
    assert build_mixture_record("BaO-2SiO2", hyphen_separator=True)["parse_status"] != "mixture_parsed"
    assert build_mixture_record("Ba1-xSrxTiO3", hyphen_separator=True)["parse_status"] != "mixture_parsed"


def test_thesis_mixture_fractions_match_figure():
    rec = build_mixture_record("0.9977076(BaTiO3)+0.003924(Y2O3)+0.019(C)")
    fr = rec["atomic_fractions"]
    for el, v in {"O": 0.5977, "Ba": 0.1985, "Ti": 0.1985, "C": 0.0038, "Y": 0.0016}.items():
        assert fr[el] == pytest.approx(v, abs=6e-5)


@pytest.mark.parametrize("unit,basis,counts,dop,expected", [
    ("mol%", "total_mixture", None, None, 0.01 / 0.99),
    ("mol%", "per_host", None, None, 0.01),
    ("at%", "total_mixture", "additive_phase_atoms", None, 0.01 / 0.99),
    ("at%", "total_mixture", "dopant_element_atoms", "Y", 0.01 * (5 / 0.975) / 2),
    ("at%", "per_host", "dopant_element_atoms", "Y", 0.025),
])
def test_unit_conventions_against_hand_computation(unit, basis, counts, dop, expected):
    r = additive_ratios("BaTiO3", [Additive("Y2O3", 1.0, dop)], unit, basis, counts)
    assert math.isclose(r[0], expected, rel_tol=1e-12)
    rec = validate_record(build_percentage_record("BaTiO3", [Additive("Y2O3", 1.0, dop)],
                                                  unit=unit, basis=basis, at_counts=counts))
    if counts == "dopant_element_atoms" and basis == "total_mixture":
        assert rec["atomic_fractions"]["Y"] == pytest.approx(0.01)


def test_at_percent_without_a_count_convention_is_refused():
    rec = validate_record(build_percentage_record("BaTiO3", [Additive("Y2O3", 1.0)], unit="at%",
                                                  basis="total_mixture"))
    assert rec["ambiguity_flags"] == ["unit_convention_missing"]


def test_dopant_element_present_in_host_is_refused():
    rec = build_percentage_record("BaTiO3", [Additive("BaO", 1.0, "Ba")], unit="at%",
                                  basis="total_mixture", at_counts="dopant_element_atoms")
    assert rec["parse_status"] == "ambiguous_rejected"


# ---------------------------------------------------------------- CSV output paths
STATUS_ENUM = set(json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))["properties"]["parse_status"]["enum"])


def _controlled(value: str) -> bool:
    return value in FLAG_CLASS


CSV_COLUMNS = {
    "paper2_parsed_composition_vectors.csv": [("parse_status", "status")],
    "notation_benchmarks_scored.csv": [("v02_record_parse_status", "status"),
                                       ("v02_record_ambiguity_flags", "flags"),
                                       ("v02_package_detail", "detail")],
    "literature_strings_eval.csv": [("v02_package_detail", "detail")],
    "literature_strings_heldout_solgel.csv": [("v02_package_detail", "detail")],
}


@pytest.mark.parametrize("name", sorted(CSV_COLUMNS))
def test_csv_outputs_use_only_the_controlled_vocabulary(name):
    df = pd.read_csv(DATA / name, dtype=str, keep_default_na=False)
    for col, kind in CSV_COLUMNS[name]:
        for v in df[col]:
            if kind == "status":
                assert v in STATUS_ENUM, (name, col, v)
            elif kind == "flags":
                assert all(_controlled(f) for f in v.split(";") if f), (name, col, v)
            else:
                assert v.startswith(("resolved:", "refused:")), (name, col, v)
                if v.startswith("refused:"):
                    assert all(_controlled(f) for f in v[8:].split("|")), (name, col, v)
    text = (DATA / name).read_text(encoding="utf-8")
    for cls in ("ValueError", "KeyError", "TypeError", "Exception:"):
        assert cls not in text, f"{name} still carries an exception class name"
