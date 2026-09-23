#!/usr/bin/env python3
"""Rebuild the PDMX corpus with the vendored converter, then split it by protected score.

The converter's paths are fixed relative to its own git root, so it is run with the
vendored tree as its working directory and the source linked into the layout it expects.
Linked, not copied: mxl/ is 254,035 files, and a build that begins by duplicating them
turns a 30-minute job into an hour of I/O for nothing.

Three things here exist because of how this corpus has failed before:

* **The renderer is checked, not assumed.** verovio was once absent from the build
  environment entirely. The converter's response was to skip every file and exit 0 with
  an empty index, which reads exactly like a corpus with strict filters.
* **rsvg-convert is checked.** Same failure, one stage later: SVG renders fine and every
  rasterisation fails, silently.
* **The split reserves archived evaluation scores.** Not a fresh random draw - see
  pdmx_split_protected in the vendored tree for why a reconversion must not redraw it.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "homr-stage2"


def _require_renderers(python: str) -> None:
    if not shutil.which("rsvg-convert"):
        raise SystemExit(
            "rsvg-convert not found. Every rasterisation would fail silently and the "
            "build would produce an empty corpus with a zero exit code. "
            "Install it: apt-get install librsvg2-bin"
        )
    probe = subprocess.run(
        [python, "-c", "import verovio; print(verovio.toolkit().getVersion())"],
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0:
        raise SystemExit(
            f"{python} cannot import verovio, so every render would be skipped and the "
            f"index would come out empty. Install it into this interpreter."
        )
    print(f"verovio {probe.stdout.strip()}")


def _link_source(source: Path, datasets: Path) -> None:
    datasets.mkdir(parents=True, exist_ok=True)
    for name in ("PDMX.csv", "mxl"):
        target = source / name
        if not target.exists():
            raise SystemExit(f"missing source input: {target}")
        link = datasets / name
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(target.resolve())
    (datasets / "out").mkdir(exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, required=True, help="holds PDMX.csv and mxl/")
    parser.add_argument("--python", default=sys.executable, help="interpreter with the build deps")
    parser.add_argument("--workers", type=int, default=0, help="0 leaves the converter's default")
    parser.add_argument("--skip-convert", action="store_true", help="split an existing index only")
    args = parser.parse_args()

    if not VENDOR.is_dir():
        raise SystemExit(
            f"{VENDOR} is absent. Vendor the converter first: "
            f"make vendor SOURCE=/path/to/homr"
        )
    _require_renderers(args.python)
    datasets = VENDOR / "datasets" / "pdmx"
    _link_source(args.source, datasets)

    env = dict(os.environ, PYTHONPATH=str(VENDOR))
    # Every BLAS thread in every worker fights the others for the same cores; capped
    # before the pool starts because a hung pool looks exactly like a finished one.
    env.update(
        OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        NUMEXPR_NUM_THREADS="1",
        VECLIB_MAXIMUM_THREADS="1",
    )
    if args.workers:
        env["HOMR_CONVERT_WORKERS"] = str(args.workers)

    if not args.skip_convert:
        subprocess.run(
            [args.python, "-u", "-m", "training.omr_datasets.convert_pdmx"],
            cwd=VENDOR,
            env=env,
            check=True,
        )

    index = datasets / "index.txt"
    rows = len([line for line in index.read_text().splitlines() if line.strip()])
    if not rows:
        raise SystemExit(f"{index} is empty; the converter rendered nothing")
    print(f"index: {rows:,} windows")

    subprocess.run(
        [
            args.python,
            "-m",
            "training.omr_datasets.pdmx_split_protected",
            str(index),
            "--root",
            str(VENDOR),
            "--audit",
            str(ROOT / "pdmx-split-audit.json"),
        ],
        cwd=VENDOR,
        env=env,
        check=True,
    )
    audit = json.loads((ROOT / "pdmx-split-audit.json").read_text())
    print(json.dumps(audit["windows"], indent=2))


if __name__ == "__main__":
    main()
