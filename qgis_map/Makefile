# Makefile for qgis-project (macOS only)
# Copy local.env.example to local.env and set QGIS before use.

-include local.env

RUN := uv run python

.PHONY: help dump build validate lint clean

help:
	@echo "Targets:"
	@echo "  make dump DIR=project_dir      # reads DIR/DIR.qgz"
	@echo "  make build DIR=project_dir"
	@echo "  make validate DIR=project_dir  # check all source/style paths exist"
	@echo "  make lint"
	@echo "  make clean DIR=project_dir"

dump:
	@if [ -z "$(DIR)" ]; then echo "Usage: make dump DIR=project_dir"; exit 1; fi
	$(RUN) -m dump $(DIR)/$(notdir $(DIR)).qgz $(DIR)

build:
	@if [ -z "$(DIR)" ]; then echo "Usage: make build DIR=project_dir"; exit 1; fi
	$(RUN) build.py $(DIR)

validate:
	@if [ -z "$(DIR)" ]; then echo "Usage: make validate DIR=project_dir"; exit 1; fi
	$(RUN) validate.py $(DIR)

lint:
	uv run black models.py dump.py render.py build.py
	uv run flake8 models.py dump.py render.py build.py

clean:
	@if [ -z "$(DIR)" ]; then echo "Usage: make clean DIR=project_dir"; exit 1; fi
	rm -rf $(DIR)/output/
