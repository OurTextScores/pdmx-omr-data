# PDMX-OMR data build

Code and provenance for rebuilding a portable HOMR structured-notation dataset from the
public-domain PDMX MusicXML corpus. This repository contains **no images, MusicXML,
tokens, sidecars or weights** - the source is fetched from Zenodo and SHA-256 verified,
and the corpus is generated.

Unlike the scan corpora, nothing here is scanned: the images are Verovio engravings of
public-domain MusicXML, cut into overlapping 8-measure windows. That makes the corpus
cheap to regenerate and the ground truth exact, and it makes it *synthetic* - it is
training data for the notation heads, not a measure of performance on real scans.

## Locked source input

`sources.lock.json` records the Zenodo URL, byte length and SHA-256 for each input.

* `pdmx-csv` - `PDMX.csv`, 225,399,738 bytes, digest pinned.
* `pdmx-mxl` - `mxl.tar.gz`, 1,894,335,797 bytes, **digest not pinned.** The archive
  from the 2026-06-02 download was extracted and discarded, so no honest digest exists
  for it. `fetch_source.py` refuses to download an unpinned source rather than accept
  1.8GB unverified; run `make lock-mxl` once after the first download to close the gap.

The record also carries ~9.6GB of rendered PDFs and a MIDI set. The converter reads
neither, so neither is locked or fetched.

## Build from scratch

```bash
git clone https://github.com/jhlusko/pdmx-omr-data.git
cd pdmx-omr-data

make vendor SOURCE=/path/to/homr     # once: vendor and pin the converter
make extract-source                  # fetch + verify + extract from Zenodo
make lock-mxl                        # pin mxl.tar.gz now that you have it
make check-inputs
make build WORKERS=7                 # ~30 min on 8 cores
make package OUT=/path/to/corpus
```

`make build` refuses to start without `rsvg-convert` and an importable `verovio`. Both
have silently produced empty corpora with a zero exit code before; see
`docs/BUILD_PIPELINE.md`.

## Build environment

Linux, Python 3.11-3.12, and:

* `librsvg2-bin` for `rsvg-convert` (SVG -> raster).
* `verovio` **6.2.1** - the engraving changes between releases, so the version is part
  of the corpus definition.
* The vendored converter's own dependencies (`opencv`, `torch` for the vocabulary
  module). No GPU is needed: conversion is CPU-only.

MuseScore is *not* required. It is a ground-truth source elsewhere in HOMR, but the
renderer here is Verovio, chosen for `breaks: "none"` continuous-system output, five
SMuFL fonts as augmentation, and in-memory MusicXML rendering.

## The validation split is not redrawn

`pdmx_protected_scores.json` reserves the 632 scores (3,349 rows) that archived
evaluations were measured on. A reconversion must not draw a fresh random split, or
those scores land in training and every published PDMX number silently stops referring
to held-out data. `make build` enforces this and fails rather than writing a
contaminated index.

## Vendored runtime

`vendor/homr-stage2/` holds the converter at a pinned commit, with per-file digests in
`vendor/PIN.json`. `make verify-runtime` re-reads the tree and reports any file that
differs, which catches a hand-edit that would make the published corpus stop matching
the code that claims to produce it. The vendored tree is AGPL-3.0.

## Licence

Scripts: MIT (`LICENSE`). Vendored converter: AGPL-3.0. Source scores: public domain or
CC0, with licence-conflict rows excluded by the converter. See `DATA-LICENSE.md` - it
records what was measured rather than asserting a blanket claim.
