#!/usr/bin/env python3
"""Pin, refresh and verify the vendored HOMR runtime.

The corpus is built by HOMR's own converter, and vendoring it here is what lets someone
rebuild the dataset without a HOMR checkout. That only means anything if the vendored copy
names the commit it came from: "the current converter" is not a reproducible claim, and a
snapshot whose origin is unrecorded cannot be audited or refreshed on purpose.

`--verify` is the check worth wiring into a build: it re-reads every vendored file and
reports any that differ from the pin, which catches a hand-edit of the vendored tree - the
failure mode where the published dataset stops matching the code that claims to produce it.
"""

import argparse
import filecmp
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "homr-stage2"
PIN = ROOT / "vendor" / "PIN.json"
#: Subtrees the build imports. Sources only - weights and ONNX graphs are fetched by
#: HOMR's own pinned downloader at run time and are not vendored.
SUBTREES = ("homr", "training")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _vendored_files() -> list[Path]:
    return sorted(p for p in VENDOR.rglob("*.py") if "__pycache__" not in p.parts)


def refresh(source: Path) -> dict:
    commit = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "-C", str(source), "status", "--porcelain", "--untracked-files=no"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if dirty:
        raise SystemExit(
            f"{source} has uncommitted changes; pin to a commit that exists or the pin "
            f"names something nobody else can check out:\n{dirty}"
        )

    if VENDOR.exists():
        shutil.rmtree(VENDOR)
    copied = 0
    for subtree in SUBTREES:
        for path in sorted((source / subtree).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            target = VENDOR / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            copied += 1
    licence = source / "LICENSE"
    if licence.is_file():
        shutil.copy2(licence, VENDOR / "LICENSE-AGPL-3.0.txt")

    pin = {
        "repository": "https://github.com/jhlusko/homr",
        "commit": commit,
        "subtrees": list(SUBTREES),
        "files": {
            str(path.relative_to(VENDOR)): _digest(path) for path in _vendored_files()
        },
    }
    PIN.write_text(json.dumps(pin, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"vendored {copied} files from {commit[:12]}")
    return pin


def verify() -> int:
    if not PIN.is_file():
        raise SystemExit(f"no pin recorded at {PIN}")
    pin = json.loads(PIN.read_text(encoding="utf-8"))
    for overlay in pin.get("localPatches", []):
        manifest_path = ROOT / overlay["manifest"]
        if not manifest_path.is_file() or _digest(manifest_path) != overlay["sha256"]:
            print(f"  changed or missing patch manifest: {manifest_path}")
            return 1
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        patch_path = ROOT / manifest["patch"]
        if not patch_path.is_file() or _digest(patch_path) != manifest["sha256"]:
            print(f"  changed or missing patch: {patch_path}")
            return 1
    recorded = pin["files"]
    present = {str(p.relative_to(VENDOR)): _digest(p) for p in _vendored_files()}
    changed = sorted(k for k in recorded.keys() & present.keys() if recorded[k] != present[k])
    missing = sorted(recorded.keys() - present.keys())
    extra = sorted(present.keys() - recorded.keys())
    for name in changed:
        print(f"  changed since the pin: {name}")
    for name in missing:
        print(f"  missing: {name}")
    for name in extra:
        print(f"  not in the pin: {name}")
    if changed or missing or extra:
        print(f"vendored runtime does NOT match pin {pin['commit'][:12]}")
        return 1
    overlays = len(pin.get("localPatches", []))
    print(f"vendored runtime matches base {pin['commit'][:12]} + {overlays} recorded patches ({len(recorded)} files)")
    return 0


def compare(source: Path) -> int:
    """Which vendored files differ from a checkout, without touching anything."""
    differing = []
    for path in _vendored_files():
        upstream = source / path.relative_to(VENDOR)
        if not upstream.is_file() or not filecmp.cmp(path, upstream, shallow=False):
            differing.append(str(path.relative_to(VENDOR)))
    for name in differing:
        print(f"  differs from checkout: {name}")
    print(f"{len(differing)} of {len(_vendored_files())} vendored files differ")
    return 1 if differing else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--source", type=Path, default=Path.home() / "workspace" / "homr", help="HOMR checkout"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--refresh", action="store_true", help="re-vendor and re-pin")
    group.add_argument("--verify", action="store_true", help="check the tree against the pin")
    group.add_argument("--compare", action="store_true", help="diff the tree against a checkout")
    args = parser.parse_args()

    if args.refresh:
        refresh(args.source)
        raise SystemExit(verify())
    if args.verify:
        raise SystemExit(verify())
    raise SystemExit(compare(args.source))


if __name__ == "__main__":
    main()
