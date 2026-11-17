# Deposit scaffold - paper 12

UPDATED 2026-09-17: Imran's ruling reversed the earlier "not a standalone
submission" framing. This project is now a real submission to RSC *Digital
Discovery* (see `AUTHOR_GATED.md` and `submission/SUBMISSION_CHECKLIST.md`).
This deposit - the installable parser package, its schema, benchmarks, result
tables and figures, with a Zenodo DOI - is the code+data release the
manuscript's Data and Code Availability sections point to; paper 04 also
already cites it.

`zenodo.json` - metadata, with `license` and `version` deliberately empty (author decision; see `_gates`).
`MANIFEST.csv` - every deposited file's path, size and SHA-256, built by `build_manifest.py`.
`build_manifest.py` - regenerate (`python3 build_manifest.py`) or verify (`--check`) the manifest against the tree.
`check_deposit_ready.py` - refuses (exit 1) until the DOI is minted and called, license and version are set, and the manifest matches the tree. Writes `zenodo.upload.json` on success.

UPDATED 2026-11-17 (after the paper-folder reorganisation). `build_manifest.py` now collects from
the reorganised paper folder: the package from `code/main/`, `manuscript/` and `figures/` from the
paper folder, the normalization stage (modules, pre-registrations, freeze digests, scripts, results,
hand-check labels, annotation guide and blank sheets) into `normalization_stage/` (its README is
`NORMALIZATION_STAGE_README.md` here), and the superseded folders from
`n submission/archive/12_Digital_Discovery/revision_R1/source/`. Withheld: the two third-party
`*.json.xz` releases and the annotation answer key (until the annotators return their sheets).
MANIFEST.csv has a `source` column giving each file's location in the paper folder.

Build the upload:  `python build_manifest.py` (on the Windows machine, so the archive folder
is reachable), then `python build_manifest.py --zip <out.zip>`, then upload the zip to Zenodo.
`make_stage_numbers.py` run on the unzipped archive reproduces `manuscript/stage_numbers.tex` exactly
(checked 17 Nov 2026).
