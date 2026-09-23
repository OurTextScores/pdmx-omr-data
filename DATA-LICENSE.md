# Licensing of the derived PDMX corpus

## What the sources are

Every score the converter reads carries one of two licences, recorded per row in
`PDMX.csv`:

| `license`      | `license_url`                                          |
|----------------|--------------------------------------------------------|
| `publicdomain` | https://creativecommons.org/publicdomain/mark/1.0/     |
| `cc-zero`      | https://creativecommons.org/publicdomain/zero/1.0/     |

Measured over the first 40,000 rows of `PDMX.csv`: 33,135 `publicdomain` and 6,865
`cc-zero`. No other value appears.

## What is excluded, and by what

`convert_pdmx.py` requires `subset:no_license_conflict == True` and
`subset:all_valid == True`. In that same 40,000-row sample, 5,023 rows carry
`license_conflict == True` and are dropped by the first condition. So no score with a
recorded licence conflict reaches the corpus.

This is a filter in the converter, not a claim about the upstream dataset as a whole.
If the filter is removed or the upstream schema changes, the guarantee goes with it -
which is why `scripts/check_inputs.py` fails when those columns are absent rather than
letting a build proceed without them.

## What the derived corpus is

The rendered images, token files and notation sidecars are derivatives of public-domain
and CC0 source. Redistribution is not restricted by the source licences.

Two obligations survive anyway, neither of them legal:

* **Credit PDMX.** The corpus is worthless without it. Cite the dataset and the Zenodo
  record (15571083) that `sources.lock.json` pins.
* **Do not present the renders as the originals.** They are Verovio engravings of the
  source MusicXML at a pinned version, cut into overlapping windows. They are not
  scans, and they are not what the submitter saw in MuseScore.

## What this does not cover

* The scripts in this repository: MIT, see `LICENSE`.
* The vendored HOMR converter under `vendor/`: **AGPL-3.0**. It is the code that
  produces the corpus, and vendoring it here is what makes the build reproducible.
  Distributing a modified version of it carries the AGPL's obligations.
