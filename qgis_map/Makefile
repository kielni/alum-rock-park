# Makefile for qgis-project (macOS only)

QGIS     := /Applications/QGIS.app
QGIS_ENV := QGIS_PREFIX_PATH=$(QGIS)/Contents/MacOS \
             DYLD_FRAMEWORK_PATH=$(QGIS)/Contents/Frameworks \
             DYLD_LIBRARY_PATH=$(QGIS)/Contents/Frameworks \
             QT_QPA_PLATFORM=offscreen

RUN      := $(QGIS_ENV) uv run python
ARP_QGZ  := ../arp.qgz

.PHONY: help dump dump-arp build lint clean

help:
	@echo "Targets:"
	@echo "  make dump-arp           - import arp.qgz into source"
	@echo "  make dump SRC=file.qgz  - import an arbitrary .qgz into source"
	@echo "  make build              - render project.py to build/project.qgs"
	@echo "  make lint               - run black and flake8"
	@echo "  make clean              - remove build/ artifacts"

dump-arp:
	$(RUN) -m src.dump $(ARP_QGZ)

dump:
	@if [ -z "$(SRC)" ]; then echo "Usage: make dump SRC=path/to/file.qgz"; exit 1; fi
	$(RUN) -m src.dump $(SRC)

build:
	mkdir -p build
	$(RUN) build.py

lint:
	uv run black src/ build.py project.py
	uv run flake8 src/ build.py

clean:
	rm -rf build/
