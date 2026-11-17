# ceramic-composition-parser 0.2.0: reproducibility guide

Every number, table and figure in the revised manuscript (`manuscript/main.tex`)
and its ESI (`manuscript/esi.tex`) is regenerated from the committed inputs by one
entry point. Every number quoted in the text is a LaTeX macro written by the code
(`manuscript/generated_numbers.tex`), never typed by hand. CPU only; a full run
takes about two minutes.

## 1. Environment

| Component | Version |
| --- | --- |
| Python | 3.10 to 3.13 |
| pymatgen | 2026.5.4 (with pymatgen-core 2026.8.30) |
| matminer | 0.10.1 (dataset metadata; downstream illustration only) |
| pandas | 2.2.3 |
| jsonschema | >= 4.21 |

```bash
pip install -e ".[dev,figures,baselines]"
```

## 2. Inputs

* `data/paper2_parsed_composition_vectors.csv`: the 28,100 database formulas of
  six matminer datasets (provenance: main-text Table V, `data/DATASET_SOURCES.md`).
* `data/stress_benchmark.csv`, `data/dopant_notation_benchmark.csv`: the 51
  hand-written strings with expected amounts.
* The two Kononova et al. literature releases, **not redistributed**. Fetch and
  verify them (pinned commit, SHA-256 checked):

```bash
python code/fetch_literature_corpus.py
```

## 3. Run

```bash
python code/run_all.py      # every result, table, figure and number macro
python -m pytest tests -q   # parser rules, schema contract on every output file,
                            # and committed numbers == a fresh regeneration
cd manuscript && pdflatex main && bibtex main && pdflatex main && pdflatex main
pdflatex esi && pdflatex esi
```

`run_all.py` is deterministic: a second run leaves every committed file unchanged.

## 4. What each step produces

| Step | Output | Appears as |
| --- | --- | --- |
| `corpus_backend_check.py` | `processed_results/corpus_backend_check.csv` | Sec. V-A |
| `notation_benchmarks.py` | `notation_benchmarks_scored.csv`, `processed_results/notation_benchmarks_summary.csv` | Table VI, ESI S1 |
| `literature_eval.py` (twice) | `literature_strings_eval.csv`, `literature_strings_heldout_solgel.csv` | Table VII, Fig. 4 |
| `literature_summary.py` | outcome, McNemar, discordant, refusal-cost and hazard tables; annotation sample | Sec. V-C to V-F, Table VIII |
| `semantic_unit_eval.py` | `paper2_semantic_unit_conversions.csv` | Table IX |
| `build_data_figures.py`, `build_revision_figures.py` | `figures/*.pdf` | Figs. 1 to 4, ESI Figs. S1 to S5 |
| `make_manuscript_numbers.py`, `make_esi.py` | `manuscript/generated_*.tex`, `esi_generated_*.tex` | every number and generated table |

## 5. Parser identity

`data/external/RELEASED_v0.2.0_parser.sha256` is the digest of the released
`code/composition_parser.py`; every reported number was produced by that file.
`data/external/v0.2.0-rc1_parser_frozen_before_heldout.sha256` is the digest at
the moment the held-out evaluation was first run (one rule was removed after
that run; no held-out outcome changed).

## 6. Downstream illustration (ESI S5)

Needs matminer's `dielectric_constant` file locally (figshare file 13213475,
SHA-256 checked on load):

```bash
python code/downstream_illustration.py --property-file <path>/dielectric_constant.json.gz
```

## 7. Superseded material

`_superseded_20261103_v0.1_evaluation/` holds the scripts, outputs, tables and
manuscript source of the submitted version (v0.1.0), unchanged, with a README
mapping each to its replacement.
