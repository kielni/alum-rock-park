# qgis_map

QGIS projects managed as code. Pydantic models in Python serialize to JSON;
a build script renders a `.qgs` file that QGIS opens as a viewer. See
[DESIGN.md](DESIGN.md) for the architecture and rationale.

## Layout

```
qgis_map/
  models.py          — Pydantic types for layers, renderers, symbols
  dump.py            — import a .qgz into a project directory
  render.py          — render project.py → output/project.qgs
  build.py           — entry point with incremental rebuild

  sample/            — one directory per project
    project.py       — source of truth (edit this)
    data/            - data files
    styles/          — per-layer XML extracted from the .qgz
    output/          — generated .qgs and derived rasters (gitignored)
```

## Python setup

```bash
uv sync
```

## Quick start: sample project

```bash
# place sample.qgz inside sample/, then:
make dump DIR=sample

# render sample/project.py → sample/output/project.qgs
make build DIR=sample

# open sample/output/project.qgs in QGIS
# after rebuilds, reload with Ctrl-R
```

## Adding a new project

```bash
make dump DIR=my_project   # reads my_project/my_project.qgz
make build DIR=my_project
```

## Workflow

Edit a layer file in your IDE. Run `make build DIR=my_project`.
Reload in QGIS. Commit `project.py` and any changed `styles/`.

## Requirements

- QGIS 3.x desktop app at `/Applications/QGIS.app`
- [uv](https://docs.astral.sh/uv/)

### QGIS reload

Copy / merge `qgis_startup.py` to QGIS startup script: 
~/Library/Application Support/QGIS/QGIS3/startup.py

### QGIS plugins

Install via `Plugins → Manage and Install Plugins`:

- **Reloader** (optional) — watches individual data files and auto-reloads
  affected layers when bytes change on disk.
