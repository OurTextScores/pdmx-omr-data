#!/usr/bin/env python3
"""Pin a downloaded source archive's digest into sources.lock.json.

mxl.tar.gz ships without a recorded digest: the 2026-06-02 download was extracted and the
archive discarded, so the only honest lock entry is a null one. fetch_source.py refuses a
null digest rather than downloading 1.8GB unverified, which leaves exactly one gap to
close - download once, pin it, and every later build is verified.

This writes the digest of the file you actually have. It is a statement about your copy,
not an endorsement of it: check the byte length against the lock and the record on Zenodo
before pinning, because a digest computed from a corrupt download is a lock that
faithfully reproduces corruption.
"""

import argparse
import hashlib
import json
from pathlib import Path

CHUNK = 1024 * 1024


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", help="key from sources.lock.json")
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--lock", type=Path, default=Path("sources.lock.json"))
    parser.add_argument(
        "--force", action="store_true", help="overwrite a digest that is already pinned"
    )
    args = parser.parse_args()

    lock = json.loads(args.lock.read_text())
    spec = lock["sources"].get(args.source)
    if not spec:
        raise SystemExit(f"unknown source: {args.source}")
    if spec.get("sha256") and not args.force:
        raise SystemExit(f"{args.source} is already pinned; pass --force to replace it")

    size = args.archive.stat().st_size
    if spec.get("bytes") and size != spec["bytes"]:
        raise SystemExit(
            f"{args.archive} is {size:,} bytes, lock expects {spec['bytes']:,}. "
            f"Refusing to pin a digest for a file of the wrong length."
        )

    spec["sha256"] = digest(args.archive)
    args.lock.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print(f"pinned {args.source}: {spec['sha256']}")


if __name__ == "__main__":
    main()
