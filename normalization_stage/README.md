# Normalization stage: modules, pre-registrations, scripts and results

This folder holds everything behind the optional normalization stage reported in the manuscript
(Sections on the stage design, the two held-out tests and the post hoc name-stoichiometry guard).
The archive keeps the layout of the paper folder, so paths quoted in the scripts and notes still resolve
relative to this folder. All numbers in `manuscript/stage_numbers.tex` are written by
`code/analysis_2026-11/make_stage_numbers.py` from the result files here; `results/stage_numbers_sources.csv`
names the file and the computation behind every macro.

## Modules

| file | what | frozen |
|---|---|---|
| `../code/composition_normalise.py` (package) | H2 stage: closed descriptor-word lexicon, polymorph prefixes, state labels and stray punctuation removed after a refusal; the residual goes back through the unchanged parser | before held-out run 1 (`docs/H2_FROZEN_before_heldout.sha256`) |
| `../code/composition_normalise_guarded.py` (package) | H2b: the H2 stage plus the element-list and amount guards | before held-out run 2 (`docs/H2b_FROZEN_before_fresh.sha256`) |
| `code/analysis_2026-11/g3_guard/code/composition_normalise_g3.py` | G3 name-stoichiometry guard, designed after the wrong reads were seen (post hoc) | `docs/g3_guard/G3_FROZEN.sha256` |

The SHA-256 of each module in this archive equals the digest recorded in its freeze file:

```
sha256sum code/composition_normalise.py code/composition_normalise_guarded.py          # from the archive root
sha256sum normalization_stage/code/analysis_2026-11/g3_guard/code/composition_normalise_g3.py
```

## Pre-registrations and freeze digests (`docs/`)

`PREREGISTRATION_H2_12.md` (written 3 Nov 2026, before design and before held-out scoring),
`g3_guard/PREREGISTRATION_G3_12.md`, the three `*.sha256` freeze files, `g3_guard/POOL_SEARCH.md`
(why no unused held-out pool remains for G3) and `g3_guard/G3_RESULTS.md`.

## Scripts (`code/analysis_2026-11/`)

| script | role |
|---|---|
| `scripts/design_eval.py`, `scripts/guard_design.py`, `scripts/reproduce_baselines.py` | design on the development release only |
| `scripts/heldout_score_once.py` | held-out run 1 (sol-gel targets); asserts the H2 digest before scoring |
| `scripts/build_fresh_pool.py`, `scripts/fresh_score_once.py` | held-out run 2 (unseen precursor strings); asserts both digests before scoring |
| `g3_guard/*.py` | G3 design, synthetic and benchmark checks, pool search, post hoc diagnostic |
| `make_stage_numbers.py` | writes `stage_numbers.tex` and `stage_numbers_sources.csv` |

The design and G3 scripts hard-code the paths of the session that ran them
(`/mnt/user-data/outputs/p12/work/pkg/...`). In this archive that prefix is the archive root (the package), and
`/mnt/user-data/outputs/p12/work/design_<half>.csv` is written by `design_eval.py`. The scripts are released as run,
unedited, so that they match the logs. To regenerate the stage numbers from the released result files:

```
cd normalization_stage
python code/analysis_2026-11/make_stage_numbers.py results/next_steps_2026-11-04 results/g3_guard <out_dir> ../data/literature_strings_eval.csv
```

## Results (`results/`)

- `next_steps_2026-11-04/results/`: held-out run 1. Per-string outcomes of every configuration, exact McNemar tests,
  run log, and `h2_heldout_rescued_handchecked.csv` (hand-check label and note for every recovered string).
- `next_steps_2026-11-04/results_fresh/`: held-out run 2. The fresh pool, per-string outcomes, McNemar tests, strings
  refused by the guard, run log, addenda A1 to A5, and `fresh_rescued_handchecked.csv`.
- `g3_guard/`: G3 run logs and the post hoc diagnostic on both pools.

The hand-check labels were made with an AI tool (see the manuscript's AI disclosure), not by an independent chemist.
They are provisional and are not expert labels.

## Expert annotation (`docs/H1_annotation_package/`)

The labelling guide, the blank sheets for two independent annotators (304 sampled strings; 67 and 303 strings
recovered by the stage) and `annotation_analysis.py`, which computes Cohen's kappa and the expert-labelled parser
comparison once the sheets are returned. The answer key (parser outputs and machine reference per item) is withheld
from the deposit until the annotators have returned their sheets; every value in it is reproducible from the released
per-string outcome files.
