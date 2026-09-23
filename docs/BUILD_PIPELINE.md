# PDMX build pipeline

## Stages

```
sources/PDMX.csv + sources/mxl/        Zenodo 15571083, SHA-256 pinned
        |
        |  _load_filtered_paths()      subset:no_license_conflict, subset:all_valid,
        |                              n_tracks <= 2, complexity <= 2, then a
        |                              round-robin across the six (tracks, complexity)
        |                              buckets, seed 42, capped at _TARGET_FILES = 10000
        v
10,000 .mxl files
        |
        |  _convert_file_impl()        per file: parse MusicXML -> cut into overlapping
        |                              8-measure windows -> inject dynamics markings ->
        |                              Verovio SVG (breaks: none) -> rsvg-convert -> JPEG
        |                              -> tokens -> notation sidecar
        v
out/<h>/<h>/<score>-v<n>-w<n>.{jpg,tokens,tokens.notation.json}   + index.txt
        |
        |  pdmx_split_protected.py     every score in pdmx_protected_scores.json goes to
        |                              validation; nothing else does
        v
index_train.txt + index_valid.txt + pdmx-split-audit.json
        |
        |  package_dataset.py          materialise symlinks, relativise index paths,
        |                              verify, write MANIFEST.json
        v
a portable corpus
```

## The filters, and where the numbers come from

The six buckets, counted from `PDMX.csv`:

```
tracks=1 complexity=0     9,276        tracks=2 complexity=0    14,574
tracks=1 complexity=1   166,357        tracks=2 complexity=1         3
tracks=1 complexity=2     6,693        tracks=2 complexity=2         3
```

196,906 files pass the licence and validity filters; `_TARGET_FILES = 10000` caps what is
converted. The round-robin means the cap does not simply take 10,000 single-track
complexity-1 files - it interleaves the buckets, so the two three-file buckets are
exhausted immediately and the mix stays deliberate rather than reflecting bucket size.

## Expected yields

Measured on an 8-core laptop, `HOMR_CONVERT_WORKERS=7`, verovio 6.2.1:

* **~5.2 files/s**, so ~30 minutes for the 10,000-file cap.
* **~29% of files are skipped** (unsupported clefs, no grand staff, tuplet ratio, or a
  Verovio segfault). The August 2026 build recorded `skipped_source_files=3062` of
  10,000, i.e. 31% - so a run far from ~30% skipped means a filter moved.
* **~4-6 windows per converted file.**

A run that reports 0 skipped and 0 windows has not found its renderer. See
`tools/build_pdmx.py`, which checks for both before converting anything.

## Why the split is not random

`pdmx_split.py` in the HOMR tree draws validation scores at random with seed 0. That is
how the current holdout came to be, and re-running it after a reconversion draws a
*different* one - putting scores that archived evaluations measured into training and
invalidating every published PDMX number retroactively.

`pdmx_protected_scores.json` is a snapshot of that original validation set: 632 scores,
3,349 rows. `pdmx_split_protected.py` sends all of them to validation and nothing else,
and raises rather than writing an index if a protected score would land in training.

It preserves **score membership, not pixels.** Re-rendered windows are not byte-identical
to the originals: Verovio's engraving and the converter's filters have both moved since.
A checkpoint evaluated on the rebuilt validation split is being measured on the same
music, differently engraved.

## Renderer version

Verovio's engraving changes between releases, so the version is part of the corpus
definition. Builds to date used **6.2.1**. Nothing in the sidecar records it, which is a
provenance gap: two corpora rendered by different Verovio versions are not
interchangeable and there is no way to tell them apart after the fact.
