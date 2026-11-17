"""Check local copies of the six matminer corpus files against matminer's SHA-256.

    python code/verify_corpus_files.py --dir <folder holding the *.json.gz files>

Prints one line per dataset (ok / MISMATCH / missing) and the file's modification
time, which is the closest available record of when it was retrieved. Exit code 1
on any mismatch.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

DATASETS = ["castelli_perovskites", "dielectric_constant", "double_perovskites_gap",
            "phonon_dielectric_mp", "piezoelectric_tensor", "wolverton_oxides"]


def main() -> int:
    import matminer

    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    a = ap.parse_args()
    meta = json.load(open(os.path.join(os.path.dirname(matminer.__file__), "datasets",
                                       "dataset_metadata.json")))
    bad = 0
    for ds in DATASETS:
        p = a.dir / f"{ds}.json.gz"
        if not p.exists():
            print(f"missing   {ds}")
            bad += 1
            continue
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        ok = got == meta[ds]["hash"]
        bad += not ok
        when = dt.datetime.fromtimestamp(p.stat().st_mtime).date().isoformat()
        print(f"{'ok      ' if ok else 'MISMATCH'}  {ds:24s} {got[:16]}  file date {when}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
