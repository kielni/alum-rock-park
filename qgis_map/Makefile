# Makefile for qgis-project (macOS only)
# Copy local.env.example to local.env and set QGIS before use.

-include local.env

RUN := uv run python

.PHONY: help dump build lint clean

help:
	@echo "Targets:"
	@echo "  make dump QGZ=path/to/file.qgz DIR=project_dir"
	@echo "  make build DIR=project_dir"
	@echo "  make lint"
	@echo "  make clean DIR=project_dir"

dump:
	@if [ -z "$(QGZ)" ] || [ -z "$(DIR)" ]; then \
		echo "Usage: make dump QGZ=path/to/file.qgz DIR=project_dir"; exit 1; fi
	$(RUN) -m dump $(QGZ) $(DIR)

build:
	@if [ -z "$(DIR)" ]; then echo "Usage: make build DIR=project_dir"; exit 1; fi
	$(RUN) build.py $(DIR)

lint:
	uv run black models.py dump.py render.py build.py
	uv run flake8 models.py dump.py render.py build.py

clean:
	@if [ -z "$(DIR)" ]; then echo "Usage: make clean DIR=project_dir"; exit 1; fi
	rm -rf $(DIR)/build/
