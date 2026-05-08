# DESIGN.md

Handoff document for working on this repo with Claude Code. Captures
architecture decisions made before any code was written. Read this first.

## Goal

Treat QGIS projects as build output, not source. Source of truth is Python +
JSON + `.qml` style files in this repo. A build script renders a `.qgs` file
that QGIS opens. QGIS is used as a viewer; edits happen in code or via
narrowly scoped UI actions that get captured back into source.

## Why

Coming from software engineering, the user wants:

- Minimal repetitive clicking through QGIS menus
- Batch edits via text files
- Incremental commits with metadata and meaningful diffs
- Reproducibility — a fresh checkout rebuilds the project exactly
- Browse/edit configuration with Python in an IDE
- No hand-editing XML; no committing compressed binaries

## Non-goals (for now)

- Writing a QGIS plugin
- Reinventing the PyQGIS API
- Modeling the entire QGIS project schema upfront
- Building a generic framework before getting hands-on experience

Generalize after friction, not before.

## Architecture

```
repo/
  project.py              # ProjectSpec instance — committed source of truth
  project.json            # Pydantic dump — committed for diffs
  src/
    models.py             # Pydantic: ProjectSpec, LayerSpec
    dump.py               # .qgz → project.py (one-shot import + re-runs)
    render.py             # project.py → build/project.qgs
  styles/                 # .qml files, committed as-is (opaque blobs)
  data/                   # raw inputs, committed (move to DVC if large)
  build.py                # entry point
  build/                  # gitignored; project.qgs lands here
  Makefile                # PyQGIS env setup + targets
```

### Key choices

**Pydantic models, hybrid typing.** Typed fields for things we touch (layer
source, CRS, style path); `extra: Any` dict and `model_config(extra="allow")`
for everything else. Expand the typed surface as we hit specific needs.

**`.qgs` not `.qgz`.** Uncompressed XML output, gitignored. Compressed
projects defeat diffing.

**`.qml` files committed as opaque blobs.** No XML hand-editing, no Pydantic
modeling of symbology in v1. QGIS UI edits → Save Style → overwrites the
`.qml` → commit. Cross-layer style operations get added later if needed.

**JSON over YAML for the serialized artifact.** Pydantic-native, unambiguous
types, schema validation. Comments don't survive round-trips in either format,
so YAML's main advantage doesn't apply here. Humans edit `project.py`; the
`.json` is the diffable build artifact.

**Derived data (slope, hillshade) is gitignored, regenerated from
TransformSpecs.** Not implemented in v1 — added when reproducible derived data
is needed.

## Workflow

1. `make dump SRC=path/to/existing.qgz` — generate `project.py`,
   `styles/*.qml`, `project.json`. Commit.
2. `make build` — emit `build/project.qgs`. Open in QGIS. Verify it matches
   the original.
3. Edit `project.py` in VSCode (rename layer, swap source, etc.). `make
   build`. Reload in QGIS with Ctrl-R (Reload Project plugin) or via the
   Reloader plugin's auto-watch. Commit `project.py` + `project.json`.
4. Tweak symbology in QGIS UI → Save Style → overwrite the `.qml` in
   `styles/`. Commit.
5. Hit something the model doesn't capture → add a field to `models.py`,
   re-run `make dump` on a fresh copy of the project, diff. Or stuff it in
   `extra` and move on.

### Exploration capture

For "tried hillshade, then slope, then slope-with-buckets, want to keep only
the last":

- Processing → History in QGIS logs every algorithm call as a runnable Python
  snippet with parameters. Copy the keeper, translate into a TransformSpec
  entry (when transforms are implemented).
- For non-Processing changes (symbology, layer order): `make dump` produces a
  fresh `project.py`. `git diff` shows what changed. Keep what you want;
  revert the rest with `git checkout`.

## Models (v1)

```python
from pydantic import BaseModel, ConfigDict
from pathlib import Path
from typing import Any, Literal

class LayerSpec(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str                          # stable handle
    name: str                        # display name
    type: Literal["vector", "raster"]
    source: str                      # path or URI
    provider: str = "ogr"            # ogr, gdal, postgres, ...
    style_qml: Path | None = None    # path to .qml in styles/
    crs: str | None = None           # "EPSG:4326"
    visible: bool = True
    extra: dict[str, Any] = {}

class ProjectSpec(BaseModel):
    model_config = ConfigDict(extra="allow")
    title: str
    crs: str
    layers: list[LayerSpec]
    extent: tuple[float, float, float, float] | None = None
    extra: dict[str, Any] = {}
```

Start here. Add fields when something concrete needs them.

## Dump implementation notes

- Open project via `QgsProject.instance().read(path)`
- Iterate `mapLayers().values()`
- Per layer: `layer.source()`, `layer.crs().authid()`, `layer.providerType()`
- Save style via `layer.saveNamedStyle(styles/<id>.qml)`
- Write `project.py` as a Python file containing a `project = ProjectSpec(...)`
  literal. Use `black` or `ruff format` on output for clean diffs.
- Lossy is acceptable in v1. Round-trip fidelity is verified visually in QGIS.

## Render implementation notes

- `QgsApplication([], False); QgsApplication.initQgis()` at startup
- Fresh `QgsProject()`, set CRS, set title
- Per LayerSpec: construct `QgsVectorLayer` or `QgsRasterLayer`, validate
  `isValid()`, call `loadNamedStyle(style_qml)` if set
- `project.write("build/project.qgs")`
- `QgsApplication.exitQgis()` at end

## Reload in QGIS

Use the **Reloader** and **Reload Project** plugins from the QGIS plugin
repository. Reloader watches files; Reload Project adds Ctrl-R for the whole
project. Manual reload is fine for v1; automate later if it gets old.

## Deferred

Add when concrete need arises, not before:

- TransformSpec (Processing algorithms with serialized params)
- Symbology models (cross-layer edits like "bump all symbol sizes 20%")
- Symbol library integration (NPS symbols, etc.)
- DVC for large derived rasters
- File watcher that triggers Ctrl-R automatically

## First task for Claude Code

1. Set up `src/models.py` per the v1 spec above
2. Confirm Makefile targets work for the user's OS (PyQGIS paths vary)
3. Implement `dump.py` against the user's actual `.qgz` (ask for the path)
4. Implement `render.py`
5. Verify round-trip: dump → build → open in QGIS → confirm visual match

Do not build features beyond v1 until the round-trip works on a real project.
