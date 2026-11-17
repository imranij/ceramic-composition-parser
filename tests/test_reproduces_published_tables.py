"""The committed number macros and generated tables equal a fresh regeneration.

Every number quoted in manuscript/main.tex is a macro in generated_numbers.tex.
This test regenerates the macros and tables from the committed result files and
fails if anything differs, so a change to the data cannot silently move a number.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MS = ROOT / "manuscript"
GENERATED = ["generated_numbers.tex", "generated_benchmark_table.tex", "generated_literature_table.tex",
             "generated_hazard_table.tex", "generated_rules_table.tex", "generated_provenance_table.tex"]


def test_macros_and_tables_regenerate_identically(tmp_path):
    for g in GENERATED:
        shutil.copy(MS / g, tmp_path / g)
    subprocess.run([sys.executable, str(ROOT / "code" / "make_manuscript_numbers.py")], check=True,
                   cwd=ROOT, stdout=subprocess.DEVNULL)
    for g in GENERATED:
        assert (MS / g).read_text(encoding="utf-8") == (tmp_path / g).read_text(encoding="utf-8"), g


def test_main_text_uses_macros_not_typed_headline_numbers():
    text = (MS / "main.tex").read_text(encoding="utf-8")
    for typed in ["19,443", "19{,}443", "3,524", "6,588", "399", "28,100", "28{,}100"]:
        assert typed not in text, f"headline number {typed} typed by hand in main.tex"


def test_every_macro_used_in_main_text_is_defined():
    import re
    defined = set(re.findall(r"\\newcommand\{\\(\w+)\}", (MS / "generated_numbers.tex").read_text()))
    used = set(re.findall(r"\\((?:N|Dev|Ho|Bench|Pct)[A-Za-z]+)", (MS / "main.tex").read_text()))
    assert used <= defined, used - defined


def test_hazard_examples_are_real_corpus_strings():
    cat = pd.read_csv(ROOT / "data" / "processed_results" / "literature_hazard_catalogue.csv")
    inst = pd.read_csv(ROOT / "data" / "processed_results" / "literature_hazard_instances.csv")
    assert set(cat.example) <= set(inst.string)
    assert int(cat.development.sum() + cat.heldout.sum()) == len(inst)


def test_semantic_unit_table_matches_closed_forms():
    df = pd.read_csv(ROOT / "data" / "paper2_semantic_unit_conversions.csv").set_index("case_id")
    assert df.loc["A1", "ratio_n_additive_per_n_host"] == "0.010101"
    assert df.loc["A4", "ratio_n_additive_per_n_host"] == "0.010101"
    assert df.loc["A5", "ratio_n_additive_per_n_host"] == "0.025641"
