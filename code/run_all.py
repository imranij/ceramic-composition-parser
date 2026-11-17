"""Regenerate every result, table, figure and number macro of the revised manuscript.

    python code/fetch_literature_corpus.py      # once: fetch and checksum the two Kononova releases
    python code/run_all.py

Steps (all deterministic; no network access after the fetch):
  1. corpus_backend_check.py     every configuration on the 28,100 database formulas
  2. notation_benchmarks.py      the 51 hand-written strings, exact-amount scoring
  3. literature_eval.py          development corpus (solid-state release)
  4. literature_eval.py          held-out corpus (sol-gel release, unseen strings)
  5. literature_summary.py       outcome tables, paired tests, hazard catalogue
  6. semantic_unit_eval.py       unit-convention table with closed-form checks
  7. build_data_figures.py, build_revision_figures.py
  8. make_manuscript_numbers.py  every number quoted in the text, as LaTeX macros

The downstream illustration (ESI S5) needs the matminer property file locally and
is run separately: python code/downstream_illustration.py --property-file <path>.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
EXT = ROOT / "data" / "external"

STEPS = [
    ["corpus_backend_check.py"],
    ["notation_benchmarks.py"],
    ["literature_eval.py", "--corpus", str(EXT / "solid-state_dataset_20200713.json.xz")],
    ["literature_eval.py", "--corpus", str(EXT / "sol-gel_dataset_20200713.json.xz"),
     "--exclude-strings-of", str(EXT / "solid-state_dataset_20200713.json.xz"),
     "--out", str(ROOT / "data" / "literature_strings_heldout_solgel.csv")],
    ["literature_summary.py"],
    ["literature_summary.py", "--catalogue"],
    ["semantic_unit_eval.py"],
    ["build_data_figures.py"],
    ["build_revision_figures.py"],
    ["make_manuscript_numbers.py"],
    ["make_esi.py"],
]


def main() -> None:
    for step in STEPS:
        cmd = [sys.executable, str(CODE / step[0]), *step[1:]]
        print("Running:", " ".join(step), flush=True)
        r = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.DEVNULL)
        if r.returncode != 0:
            raise SystemExit(f"step failed: {step[0]}")
    print("done")


if __name__ == "__main__":
    main()
