# Makefile for qgis-project
#
# PyQGIS standalone setup varies by OS. This Makefile detects the platform
# and sets QGIS_PREFIX_PATH and PYTHONPATH so that `from qgis.core import *`
# works from a normal Python interpreter (not the QGIS Python console).
#
# Override QGIS_PREFIX on the command line if auto-detection fails:
#   make build QGIS_PREFIX=/custom/path

UNAME := $(shell uname -s)

# --- OS-specific PyQGIS paths -------------------------------------------------
ifeq ($(UNAME), Darwin)
  # macOS, QGIS.app installation
  QGIS_PREFIX ?= /Applications/QGIS.app/Contents/MacOS
  PYQGIS_PATH := /Applications/QGIS.app/Contents/Resources/python
  PYTHON      := /Applications/QGIS.app/Contents/MacOS/bin/python3
endif

ifeq ($(UNAME), Linux)
  # Linux, system package install
  QGIS_PREFIX ?= /usr
  PYQGIS_PATH := /usr/share/qgis/python
  PYTHON      := python3
endif

# Windows: use OSGeo4W shell instead. This Makefile is a no-op there;
# adapt by sourcing OSGeo4W's py3_env.bat before running python directly.

# --- Environment for PyQGIS scripts ------------------------------------------
export QGIS_PREFIX_PATH := $(QGIS_PREFIX)
export PYTHONPATH       := $(PYQGIS_PATH):$(PYTHONPATH)
export DYLD_FRAMEWORK_PATH := /Applications/QGIS.app/Contents/Frameworks  # macOS
export QT_QPA_PLATFORM  := offscreen  # headless rendering

# --- Targets ------------------------------------------------------------------
.PHONY: help build dump check clean install-deps

help:
	@echo "Targets:"
	@echo "  make check              - verify PyQGIS imports work"
	@echo "  make install-deps       - pip install python deps"
	@echo "  make dump SRC=file.qgz  - import an existing project into source"
	@echo "  make build              - render project.py to build/project.qgs"
	@echo "  make clean              - remove build/ artifacts"

check:
	@echo "QGIS_PREFIX_PATH=$(QGIS_PREFIX_PATH)"
	@echo "PYTHONPATH=$(PYTHONPATH)"
	@echo "PYTHON=$(PYTHON)"
	@$(PYTHON) -c "from qgis.core import QgsApplication; print('PyQGIS OK')"

install-deps:
	$(PYTHON) -m pip install pydantic

dump:
	@if [ -z "$(SRC)" ]; then echo "Usage: make dump SRC=path/to/file.qgz"; exit 1; fi
	$(PYTHON) -m src.dump $(SRC)

build:
	mkdir -p build
	$(PYTHON) build.py

clean:
	rm -rf build/
