#!/usr/bin/env python3
r"""Refuse to call paper 12's deposit ready while any gate is open.

This deposit is paper 12's actual deliverable (see AUTHOR_GATED.md: not a
standalone journal submission). Exits 0 only when all four conditions hold:

  1. manuscript/main.tex has \def\depositdoi set to something other than
     NOT-YET-MINTED, AND \depositdoilink is actually called somewhere in the
     document;
  2. zenodo.json metadata.license is non-empty;
  3. zenodo.json metadata.version is non-empty;
  4. MANIFEST.csv matches the tree.

usage:  python3 check_deposit_ready.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # the paper folder (reorganised 17 Nov 2026: manuscript/ sits beside code/main/)
MAIN = ROOT / "manuscript" / "deposit_doi.tex"  # the DOI lives here; main.tex inputs it
ZEN = HERE / "zenodo.json"


def strip_under(o):
    if isinstance(o, dict):
        return {k: strip_under(v) for k, v in o.items() if not k.startswith("_")}
    if isinstance(o, list):
        return [strip_under(v) for v in o]
    return o


def main() -> int:
    fail = []

    t = MAIN.read_text(encoding="utf-8")
    m = re.search(r"\\def\\depositdoi\{([^}]*)\}", t)
    if not m:
        fail.append(r"GATE 1  manuscript/main.tex has no \def\depositdoi -- the DOI gate is missing")
    elif m.group(1).strip() == "NOT-YET-MINTED":
        fail.append(r"GATE 1  \depositdoi is still NOT-YET-MINTED; the manuscript states that no public deposit exists yet")
    calls = [
        i + 1
        for i, line in enumerate((ROOT / "manuscript" / "main.tex").read_text(encoding="utf-8").split("\n"))
        if r"\depositdoilink" in line
        and not line.lstrip().startswith("%")
        and r"\newcommand{\depositdoilink}" not in line
    ]
    if not calls:
        fail.append(r"GATE 1  \depositdoilink is never called, so no banner prints anywhere")

    z = json.loads(ZEN.read_text(encoding="utf-8"))
    md = z["metadata"]
    if not str(md.get("license", "")).strip():
        fail.append("GATE 2  zenodo.json metadata.license is empty (no licence chosen; author decision)")
    if not str(md.get("version", "")).strip():
        fail.append("GATE 3  zenodo.json metadata.version is empty (fill with the release tag)")

    r = subprocess.run(
        [sys.executable, str(HERE / "build_manifest.py"), "--check"],
        capture_output=True, text=True,
    )
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        fail.append("GATE 4  MANIFEST.csv does not match the tree (see the lines above). "
                    "Re-run build_manifest.py only after confirming each change is intended.")

    if fail:
        print("\nDEPOSIT NOT READY:")
        for f in fail:
            print("  " + f)
        return 1

    up = HERE / "zenodo.upload.json"
    up.write_text(json.dumps(strip_under(z), indent=2, ensure_ascii=False) + "\n",
                  encoding="utf-8", newline="")
    print(f"\nALL GATES CLEAR -- wrote {up.name}")
    return 0


raise SystemExit(main())
