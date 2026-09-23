"""Validate the PDMX source tree before a build reads it.

A missing mxl/ tree does not fail loudly: the converter's filters simply skip every file
it cannot open, and the run ends with an empty index and a cheerful exit code. So the
check is on the two inputs the converter actually reads - the metadata table and the
MusicXML archive - and on the columns the filters depend on, because a schema change
upstream would silently drop the whole corpus the same way.
"""

import argparse
import csv
from pathlib import Path

REQUIRED_COLUMNS = (
    "mxl",
    "n_tracks",
    "complexity",
    "license",
    "subset:no_license_conflict",
    "subset:all_valid",
)

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--pdmx", type=Path, required=True, help="directory holding PDMX.csv and mxl/")
parser.add_argument("--min-mxl", type=int, default=200000, help="fail below this many .mxl files")
args = parser.parse_args()

csv_path = args.pdmx / "PDMX.csv"
mxl_root = args.pdmx / "mxl"
for path in (csv_path, mxl_root):
    if not path.exists():
        raise SystemExit(f"missing required input: {path}")

with csv_path.open(newline="", encoding="utf-8") as f:
    columns = set(csv.DictReader(f).fieldnames or [])
missing = [c for c in REQUIRED_COLUMNS if c not in columns]
if missing:
    raise SystemExit(f"{csv_path}: missing column(s) {', '.join(missing)}")

count = sum(1 for _ in mxl_root.rglob("*.mxl"))
if count < args.min_mxl:
    raise SystemExit(f"{mxl_root}: found {count:,} .mxl files, expected at least {args.min_mxl:,}")

print(f"PDMX source check passed: {count:,} .mxl files, all required columns present.")
print("Every score used is public-domain or CC0; see DATA-LICENSE.md before redistributing.")
