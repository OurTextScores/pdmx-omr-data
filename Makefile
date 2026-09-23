.DEFAULT_GOAL := help

SOURCE_DIR ?= sources
CORPUS_DIR ?= corpus
ARCHIVE_BASE_URL ?=
PYTHON ?= python3

fetch-source:
	python3 scripts/fetch_source.py pdmx-csv --dest "$(SOURCE_DIR)" $(if $(ARCHIVE_BASE_URL),--base-url "$(ARCHIVE_BASE_URL)")
	python3 scripts/fetch_source.py pdmx-mxl --dest "$(SOURCE_DIR)" $(if $(ARCHIVE_BASE_URL),--base-url "$(ARCHIVE_BASE_URL)")

extract-source: fetch-source
	python3 scripts/fetch_source.py pdmx-mxl --dest "$(SOURCE_DIR)" --extract

lock-mxl:
	python3 tools/lock_source.py pdmx-mxl --archive "$(SOURCE_DIR)/mxl.tar.gz"

fetch-corpus:
	python3 scripts/fetch_corpus.py --dest "$(CORPUS_DIR)" $(if $(SPLIT),--split "$(SPLIT)")

verify-corpus:
	python3 scripts/fetch_corpus.py --dest "$(CORPUS_DIR)" --verify-only $(if $(SPLIT),--split "$(SPLIT)")

check-inputs:
	python3 scripts/check_inputs.py --pdmx "$(SOURCE_DIR)"

vendor:
	test -n "$(SOURCE)"
	python3 tools/vendor_runtime.py --source "$(SOURCE)" --refresh

verify-runtime:
	python3 tools/vendor_runtime.py --verify

build: check-inputs verify-runtime
	python3 tools/build_pdmx.py --source "$(SOURCE_DIR)" --python "$(PYTHON)" $(if $(WORKERS),--workers "$(WORKERS)")

split:
	python3 tools/build_pdmx.py --source "$(SOURCE_DIR)" --python "$(PYTHON)" --skip-convert

package:
	test -n "$(OUT)"
	python3 tools/package_dataset.py --root "$(OUT)"

verify:
	test -n "$(OUT)"
	python3 tools/package_dataset.py --root "$(OUT)" --verify-only

help:
	@echo "make vendor SOURCE=/path/to/homr   Vendor and pin the HOMR converter (needs a clean checkout)."
	@echo "make verify-runtime                Check the vendored converter against its pin."
	@echo "make fetch-corpus [SPLIT=valid]      Download the built corpus (1.94GB, or 142MB for valid)."
	@echo "make verify-corpus [SPLIT=valid]     Re-check downloaded shards against the pinned digests."
	@echo "make extract-source                Fetch, SHA-256 verify and extract the PDMX source."
	@echo "make lock-mxl                      Pin mxl.tar.gz's digest after the first download."
	@echo "make check-inputs                  Validate PDMX.csv columns and the mxl/ tree."
	@echo "make build [WORKERS=n PYTHON=...]  Reconvert the corpus and write the protected split."
	@echo "make split                         Re-split an existing index without reconverting."
	@echo "make package OUT=/path             Make a materialized dataset portable and verify it."
