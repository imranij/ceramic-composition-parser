"""Fetch the two Kononova et al. text-mined synthesis releases and verify them.

The files are not redistributed with this package (the source repository carries
no licence file). They are taken from the public GitHub repository at a fixed
commit and checked against the SHA-256 digests the evaluation was run on.

    python code/fetch_literature_corpus.py
"""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path

REPO = "https://github.com/CederGroupHub/text-mined-synthesis_public"
COMMIT = "fca0a994ddb36b37d39b803e8a21880aaecb1d71"
FILES = {
    "solid-state_dataset_20200713.json.xz": "0ae448935bc23e933fa12cabdaa044f232412ba99cf0f966a33e439f6e8334c5",
    "sol-gel_dataset_20200713.json.xz": "d7d092b7f1b35b609669eb3530b48429eb349cf68b0621ce605bee18db609df8",
}
DEST = Path(__file__).resolve().parents[1] / "data" / "external"


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "clone", "--quiet", REPO, tmp], check=True)
        subprocess.run(["git", "-C", tmp, "checkout", "--quiet", COMMIT], check=True)
        for name, digest in FILES.items():
            data = (Path(tmp) / name).read_bytes()
            got = hashlib.sha256(data).hexdigest()
            if got != digest:
                raise SystemExit(f"{name}: SHA-256 {got} != {digest}")
            (DEST / name).write_bytes(data)
            print(f"ok  {name}  {digest}")


if __name__ == "__main__":
    main()
