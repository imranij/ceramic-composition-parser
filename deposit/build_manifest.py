#!/usr/bin/env python3
"""Regenerate MANIFEST.csv for paper 12's Zenodo deposit, and build the archive.

UPDATED 2026-11-17: the paper folder was reorganised on 17 Nov 2026. The package
now lives in <paper>/code/main/ (this file's grandparent), the manuscript in
<paper>/manuscript/, the figures in <paper>/figures/, and the normalization-stage
analysis in <paper>/code/analysis_2026-11/, <paper>/results/ and <paper>/docs/.
The archive layout is unchanged for the package (paths relative to the package
root) and adds `manuscript/`, `figures/` and `normalization_stage/`. Every row
is measured from a file that exists right now: archive path, source path, byte
size, SHA-256, role, and whether the file is deposited. Nothing is estimated.

usage:  python3 build_manifest.py            # writes MANIFEST.csv
        python3 build_manifest.py --check    # verifies MANIFEST.csv, exit 1 on drift
        python3 build_manifest.py --zip OUT  # writes the deposit zip (deposited rows only)
"""
import csv, hashlib, os, sys, zipfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]          # <paper>/code/main
PAPER = PKG.parents[1]                             # <paper>
ARCHIVE_OLD = Path(os.environ.get("P12_ARCHIVE_SOURCE",
                   PAPER.parent / "archive" / "12_Digital_Discovery" / "revision_R1" / "source"))
OUT = Path(__file__).resolve().parent / "MANIFEST.csv"
STAGE = "normalization_stage/"

# (source root, glob, archive prefix or None = same relative path, role, deposited, note)
RULES = [
    # --- the package (archive paths = paths relative to the package root) ---
    (PKG, "code/*.py",                          None, "pipeline, evaluation and figure code", "yes", ""),
    (PKG, "code/legacy/*.py",                   None, "frozen v0.1.0 parser (comparison only)", "yes", ""),
    (PKG, "code/requirements.txt",              None, "environment pin",                "yes", ""),
    (PKG, "code/strip_titles.json",             None, "figure config",                  "yes", ""),
    (PKG, ".github/workflows/ci.yml",           None, "CI configuration",               "yes", ""),
    (PKG, "ceramic_composition_parser/__init__.py",   None, "installable package",  "yes", ""),
    (PKG, "ceramic_composition_parser/schema/*.json", None, "installable package",  "yes", ""),
    (PKG, "schema/*.json",                      None, "record schema 1.1.0",           "yes", ""),
    (PKG, "tests/*.py",                         None, "test suite",                    "yes", ""),
    (PKG, "pyproject.toml",                     None, "package metadata",              "yes", ""),
    (PKG, "data/*.csv",                         None, "benchmark, corpus and per-string evaluation table", "yes", ""),
    (PKG, "data/DATASET_SOURCES.md",            None, "documentation",                 "yes", ""),
    (PKG, "data/external/*.sha256",             None, "parser file digests (released, and frozen for the held-out run)", "yes", ""),
    (PKG, "data/external/*.json.xz",            None, "third-party literature release", "no", "not redistributed; fetched by code/fetch_literature_corpus.py at a pinned commit and SHA-256"),
    (PKG, "data/processed_results/*.csv",       None, "result record",                 "yes", ""),
    (PKG, "annotation/*.csv",                   None, "stratified sample for independent annotation (labels blank)", "yes", ""),
    (PKG, "REPRODUCIBILITY.md",                 None, "documentation",                 "yes", ""),
    (PKG, "README.md",                          None, "documentation",                 "yes", ""),
    (PKG, "LICENSE",                            None, "licence",                       "yes", ""),
    (PKG, "CITATION.cff",                       None, "citation metadata",             "yes", ""),
    (PKG, "deposit/build_manifest.py",          None, "deposit tooling",               "yes", ""),
    (PKG, "deposit/check_deposit_ready.py",     None, "deposit tooling",               "yes", ""),
    (PKG, "deposit/zenodo.json",                None, "deposit metadata",              "yes", ""),
    (PKG, "deposit/README.md",                  None, "documentation",                 "yes", ""),
    # --- manuscript and figures (from the paper folder) ---
    (PAPER, "figures/*.pdf",                    None, "figure (vector, generated)",    "yes", ""),
    (PAPER, "figures/*.png",                    None, "figure (raster preview)",       "yes", ""),
    (PAPER, "figures/README.md",                None, "documentation",                 "yes", ""),
    (PAPER, "manuscript/main.tex",              None, "manuscript source",             "yes", ""),
    (PAPER, "manuscript/esi.tex",               None, "ESI source",                    "yes", ""),
    (PAPER, "manuscript/references.bib",        None, "manuscript source",             "yes", ""),
    (PAPER, "manuscript/deposit_doi.tex",       None, "manuscript source",             "yes", ""),
    (PAPER, "manuscript/stage_numbers.tex",     None, "generated number macros (normalization stage)", "yes", ""),
    (PAPER, "manuscript/generated_*.tex",       None, "generated table or number macros", "yes", ""),
    (PAPER, "manuscript/esi_generated_*.tex",   None, "generated ESI table",           "yes", ""),
    (PAPER, "manuscript/IEEEtran.cls",          None, "LaTeX class (IEEEtran, LPPL)",  "yes", ""),
    (PAPER, "manuscript/IEEEtran.bst",          None, "BibTeX style (IEEEtran, LPPL)", "yes", ""),
    (PAPER, "manuscript/main.pdf",              None, "built manuscript",              "yes", ""),
    (PAPER, "manuscript/12_R1_ESI.pdf",         "manuscript/esi.pdf", "built ESI", "yes", ""),
    # --- normalization stage (archive prefix normalization_stage/, paper-relative layout kept) ---
    (PKG,   "deposit/NORMALIZATION_STAGE_README.md", STAGE + "README.md", "documentation", "yes", ""),
    (PAPER, "code/analysis_2026-11/make_stage_numbers.py", STAGE, "stage number macros (writes manuscript/stage_numbers.tex)", "yes", ""),
    (PAPER, "code/analysis_2026-11/scripts/*.py",          STAGE, "stage design and one-shot held-out scoring scripts", "yes", "absolute paths as run; see normalization_stage/README.md"),
    (PAPER, "code/analysis_2026-11/g3_guard/code/*.py",    STAGE, "G3 name-stoichiometry guard module (post hoc)", "yes", ""),
    (PAPER, "code/analysis_2026-11/g3_guard/*.py",         STAGE, "G3 guard design, benchmark and post hoc diagnostic scripts", "yes", "absolute paths as run; see normalization_stage/README.md"),
    (PAPER, "docs/PREREGISTRATION_H2_12.md",               STAGE, "pre-registration",              "yes", ""),
    (PAPER, "docs/H2_FROZEN_before_heldout.sha256",        STAGE, "freeze digest (before held-out run 1)", "yes", ""),
    (PAPER, "docs/H2b_FROZEN_before_fresh.sha256",         STAGE, "freeze digest (before held-out run 2)", "yes", ""),
    (PAPER, "docs/g3_guard/*.md",                          STAGE, "G3 pre-registration, pool search and results", "yes", ""),
    (PAPER, "docs/g3_guard/G3_FROZEN.sha256",              STAGE, "freeze digest (G3)",            "yes", ""),
    (PAPER, "results/next_steps_2026-11-04/results/*",       STAGE, "held-out run 1: per-string outcomes, tests, hand-check labels, log", "yes", ""),
    (PAPER, "results/next_steps_2026-11-04/results_fresh/*", STAGE, "held-out run 2: per-string outcomes, tests, hand-check labels, log, addenda", "yes", ""),
    (PAPER, "results/g3_guard/*.txt",                      STAGE, "G3 run log",                    "yes", ""),
    (PAPER, "results/g3_guard/posthoc/*",                  STAGE, "G3 post hoc diagnostic outputs", "yes", ""),
    (PAPER, "results/stage_numbers_sources.csv",           STAGE, "source of every stage number macro", "yes", ""),
    (PAPER, "docs/H1_annotation_package/LABELLING_GUIDE.md",   STAGE, "expert annotation: labelling guide", "yes", ""),
    (PAPER, "docs/H1_annotation_package/annotation_sheet_*.csv", STAGE, "expert annotation: blank sheets", "yes", ""),
    (PAPER, "docs/H1_annotation_package/annotation_analysis.py", STAGE, "expert annotation: analysis script", "yes", ""),
    (PAPER, "docs/H1_annotation_package/annotation_KEY_do_not_give_to_annotators.csv", STAGE, "expert annotation: parser outputs and reference per item", "no", "withheld until the annotators have returned their sheets"),
    # --- superseded material kept auditable (moved to the archive folder on 17 Nov 2026) ---
    (ARCHIVE_OLD, "_superseded_20261103_v0.1_evaluation/**/*", None, "v0.1.0 evaluation as submitted (kept for traceability)", "yes", ""),
    (ARCHIVE_OLD, "_superseded_20260910/fabricated_figures_20260910/*", None, "withdrawn figure + its README (kept auditable)", "yes", ""),
    (ARCHIVE_OLD, "_superseded_20260911/*",     None, "superseded figure", "yes", ""),
]

EXCLUDE_SUBSTR = ("__pycache__", "_tmp.vsdx", ".bak", "_prestyle_backup",
                  "_predesign_backup", "_figrebuild_backup", "_vsdx_shell",
                  "_superseded_assets", "_selftest", "README_FOR_IMRAN",
                  ".pre_20260910", ".pre_cleanup", ".RETIRED.", ".gemini")
FIELDS = ["path", "source", "bytes", "sha256", "role", "deposited", "note"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collect():
    rows, seen = [], set()
    for root, pat, prefix, role, dep, note in RULES:
        hits = sorted(root.glob(pat)) if root.exists() else []
        if not hits:
            print(f"WARNING  no file matches {pat} under {root}", file=sys.stderr)
        for p in hits:
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            if any(s in rel for s in EXCLUDE_SUBSTR):
                continue
            if prefix is None:
                arc = rel
            elif prefix.endswith("/"):
                arc = prefix + rel
            else:
                arc = prefix
            if arc in seen:
                continue
            seen.add(arc)
            try:
                src = p.relative_to(PAPER).as_posix()
            except ValueError:
                src = "../archive/12_Digital_Discovery/revision_R1/source/" + p.relative_to(ARCHIVE_OLD).as_posix()
            rows.append({"path": arc, "source": src, "bytes": p.stat().st_size,
                         "sha256": sha256(p), "role": role,
                         "deposited": dep, "note": note})
    rows.sort(key=lambda r: r["path"])
    return rows


def main():
    rows = collect()
    if "--check" in sys.argv:
        if not OUT.exists():
            print("MANIFEST.csv absent"); return 1
        old = list(csv.DictReader(OUT.open(encoding="utf-8")))
        oldmap = {r["path"]: r for r in old}
        newmap = {r["path"]: r for r in rows}
        bad = 0
        for path in sorted(set(oldmap) | set(newmap)):
            if path not in oldmap:
                print(f"NEW      {path}"); bad += 1
            elif path not in newmap:
                print(f"MISSING  {path}"); bad += 1
            elif oldmap[path]["sha256"] != newmap[path]["sha256"]:
                print(f"CHANGED  {path}"); bad += 1
        print(f"{len(rows)} files, {bad} discrepancies")
        return 1 if bad else 0
    if "--zip" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--zip") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        n = 0
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for r in rows:
                if r["deposited"] != "yes":
                    continue
                pre = "../archive/12_Digital_Discovery/revision_R1/source/"
                src = (ARCHIVE_OLD / r["source"][len(pre):]) if r["source"].startswith(pre) else PAPER / r["source"]
                z.write(src, r["path"]); n += 1
            z.write(OUT, "MANIFEST.csv"); n += 1
        print(f"wrote {out}  {n} files"); return 0
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    dep = sum(1 for r in rows if r["deposited"] == "yes")
    print(f"wrote MANIFEST.csv  {len(rows)} files  ({dep} deposited, {len(rows)-dep} withheld)")
    return 0


raise SystemExit(main())
