# Dataset sources

## Database corpus (six matminer datasets, 28,100 unique formula strings)

Each dataset is identified by the figshare file and SHA-256 that matminer 0.10.1
records for it. Normalization: rows with a
missing formula are dropped; formulas are compared as exact strings; duplicate
(formula, dataset) pairs are removed; formulas repeated across datasets are kept
in each. The parsed vectors are `paper2_parsed_composition_vectors.csv`.

| matminer dataset | figshare file | SHA-256 | rows | unique formulas | source |
|---|---|---|---|---|---|
| castelli_perovskites | 13284197 | fc8b44d7213515f9bc2ef3a5a5d3e4b946b321c1311f14c8be31f857b61b10d7 | 18,928 | 18,928 | Castelli et al., Energy Environ. Sci. 5, 9034 (2012), doi:10.1039/C2EE22341D |
| wolverton_oxides | 13354616 | 3e66c2a5bd23dac335f045210258ca14babf730824bf989b0127640c24bcb78b | 4,914 | 4,914 | Emery & Wolverton, Sci. Data 4, 170153 (2017), doi:10.1038/sdata.2017.153 |
| double_perovskites_gap | 13309157 | 746072db995ec46f44b67c3f55fccdc24a7ec6233be1b96cc52dab8db4bf0ba4 | 1,306 | 1,306 | Pilania et al., Sci. Rep. 6, 19375 (2016), doi:10.1038/srep19375 |
| phonon_dielectric_mp | 13297571 | 53044ba423c06b5c08e8d3991c6c2140a2391160f90af03377d4e1734ce475f9 | 1,296 | 1,190 | Petretto et al., Sci. Data 5, 180065 (2018), doi:10.1038/sdata.2018.65 |
| dielectric_constant | 13213475 | 8eb24812148732786cd7c657eccfc6b5ee66533429c2cfbcc4f0059c0295e8b6 | 1,056 | 964 | Petousis et al., Sci. Data 4, 160134 (2017), doi:10.1038/sdata.2016.134 |
| piezoelectric_tensor | 13220621 | dc9d04836f7f91ecb4ef6dc23e42468571be857f0fccafdfb51a5a40f19db898 | 941 | 798 | de Jong et al., Sci. Data 2, 150053 (2015), doi:10.1038/sdata.2015.53 |

The retrieval date of the original download is not recorded in the project. The
local copies can be checked against the digests above, and their file dates
reported, with `python code/verify_corpus_files.py --dir <folder>`.

## Literature corpora (not redistributed)

Kononova et al., "Text-mined dataset of inorganic materials synthesis recipes",
Sci. Data 6, 203 (2019), doi:10.1038/s41597-019-0224-1; release 2020-07-13 from
https://github.com/CederGroupHub/text-mined-synthesis_public at commit
fca0a994ddb36b37d39b803e8a21880aaecb1d71.

| file | SHA-256 | role |
|---|---|---|
| solid-state_dataset_20200713.json.xz | 0ae448935bc23e933fa12cabdaa044f232412ba99cf0f966a33e439f6e8334c5 | development set (19,443 unique target strings, 16,225 DOIs) |
| sol-gel_dataset_20200713.json.xz | d7d092b7f1b35b609669eb3530b48429eb349cf68b0621ce605bee18db609df8 | held-out set (3,524 strings not in the development set) |

The repository carries no licence file, so the releases are fetched by
`code/fetch_literature_corpus.py` rather than redistributed. The per-string
evaluation tables (`literature_strings_*.csv`) contain the strings, their DOIs and
the outcomes, which are needed to audit every reported count.

## Hand-written benchmarks

`stress_benchmark.csv` (24 strings) and `dopant_notation_benchmark.csv` (27 rows)
were written by the package's author; labels are unchanged from the submitted
version. `paper2_thesis_*` are the six thesis-derived items (ESI S4).
