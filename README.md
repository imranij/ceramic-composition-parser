# ceramic-composition-parser

An auditable parser for composition strings from the materials literature. A string that does not
determine a composition is refused with a controlled reason instead of being turned into an
atomic-fraction vector. This repository holds the package (v0.2.0, record schema 1.1.0), its
evaluation, the optional normalization stage and the manuscript sources for the paper
*Refusing Ambiguous Composition Notation: An Auditable Parser, a Guarded Normalization Stage and a
Catalogue of Notation Hazards* (Imran, KFUPM), revised for *Digital Discovery* (RSC), November 2026.

Archived release: https://doi.org/10.5281/zenodo.24311164

## What is here

| folder | contents |
|---|---|
| `code/` | the parser (`composition_parser.py`), unit semantics, record writer, the normalization-stage modules (`composition_normalise.py`, `composition_normalise_guarded.py`), the literature evaluation, benchmarks, figure and table generators, and `run_all.py` |
| `code/legacy/` | the frozen v0.1.0 parser, used only for comparison |
| `ceramic_composition_parser/`, `schema/` | the installable package facade and the JSON Schema record model |
| `tests/` | the test suite |
| `data/` | benchmark strings with expected amounts, per-string literature outcomes (`processed_results/`), SHA-256 digests of the parser files and of the third-party releases |
| `annotation/` | the stratified sample prepared for independent expert annotation (labels blank) |
| `normalization_stage/` | pre-registrations, freeze digests, design and one-shot scoring scripts, results of both held-out runs with hand-check labels, the post hoc name-stoichiometry guard, and the expert-annotation guide and blank sheets; see its `README.md` |
| `figures/`, `manuscript/` | figures, LaTeX sources, generated tables and number macros, built PDFs |
| `deposit/` | `MANIFEST.csv` (path, source, size and SHA-256 of every file), the manifest builder and the release check |

The GitHub mirror holds everything except two items kept only in the Zenodo archive: the superseded
v0.1.0 evaluation and the withdrawn figures (`_superseded_*`, kept for audit), and one large intermediate
table (`data/paper2_parsed_composition_vectors.csv`). `deposit/MANIFEST.csv` lists every archived file
with its SHA-256.

## Data

The two text-mined synthesis releases of Kononova et al. (Sci. Data 6, 203, 2019,
doi:10.1038/s41597-019-0224-1) are not redistributed. `code/fetch_literature_corpus.py` downloads
them from https://github.com/CederGroupHub/text-mined-synthesis_public at commit `fca0a99` and checks
their SHA-256 digests against `data/external/`.

## Reproduce

```
pip install -e .[dev,baselines,figures]
python code/fetch_literature_corpus.py
python code/run_all.py
python -m pytest tests -q
```

`pymatgen` is pinned to 2026.5.4, the version behind every reported number.

## Licence

Code: MIT (see `LICENSE`). Result files, figures and text: CC BY 4.0.

## Citation

See `CITATION.cff`.
