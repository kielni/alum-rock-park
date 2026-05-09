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
- Modeling the entire QGIS project schema upfront (expand from `arp.qgz` only)
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

**`.qml` files parsed with Pydantic.** QML is XML; parse it into typed models
so symbology can be edited in code without touching the QGIS UI. QGIS UI is
used for viewing only. Start from `park_symbols.qml` to drive the v1 schema.
Cross-layer operations (bump all symbol sizes, swap palette) follow naturally.

**JSON over YAML for the serialized artifact.** Pydantic-native, unambiguous
types, schema validation. Comments don't survive round-trips in either format,
so YAML's main advantage doesn't apply here. Humans edit `project.py`; the
`.json` is the diffable build artifact.

**Derived data (slope, hillshade) is gitignored, regenerated from recorded
commands.** Each transform is a shell command string and a comment explaining
intent, stored in `project.py`. Not implemented in v1 — added when
reproducible derived data is needed.

## Workflow

1. `make dump SRC=path/to/existing.qgz` — generate `project.py`,
   `styles/*.qml`, `project.json`. Commit.
2. `make build` — emit `build/project.qgs`. Open in QGIS. Verify it matches
   the original.
3. Edit `project.py` in VSCode (rename layer, swap source, etc.). `make
   build`. Reload in QGIS with Ctrl-R (Reload Project plugin) or via the
   Reloader plugin's auto-watch. Commit `project.py` + `project.json`.
4. Two directions for symbology:
   - **Code → QGIS**: edit `project.py`, `make build`, reload in QGIS to view.
   - **QGIS → code**: tweak in QGIS UI, Save Style to overwrite `.qml` in
     `styles/`, then `make dump` to re-parse QML back into `project.py`.
     `git diff` to review what changed; commit.
5. Hit something the model doesn't capture → add a field to `models.py`,
   re-run `make dump` on a fresh copy of the project, diff. Or stuff it in
   `extra` and move on.

### Exploration capture

For "tried hillshade, then slope, then slope-with-buckets, want to keep only
the last":

- Derive the command (gdal, grass, etc.) from QGIS Processing → History, an
  LLM suggestion, or the tool's own docs. Add it to `project.py` as a shell
  command string and a comment explaining intent. `make build` re-runs only
  stale transforms.
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

No PyQGIS — parse XML directly. A `.qgz` is a zip; unzip to get `.qgs`.

- Unzip `arp.qgz` → `project.qgs` (XML)
- Parse with `lxml` or `xml.etree`
- Per `<maplayer>`: extract `datasource`, `srs/authid`, `provider`, `layername`
- Extract embedded or linked `.qml` style per layer
- Parse QML into `StyleSpec` Pydantic model (drive schema from `park_symbols.qml`)
- Write `project.py` as a Python literal. Run `ruff format` for clean diffs.
- Lossy is acceptable in v1. Round-trip fidelity verified visually in QGIS.

## Render implementation notes

No PyQGIS — generate XML directly.

- Load `ProjectSpec` from `project.py`
- Start from a minimal `.qgs` XML template (extract from `arp.qgz` as baseline)
- Inject layer entries, CRS, extent, title by manipulating the XML tree
- Serialize each `StyleSpec` back to QML XML
- Write `build/project.qgs`
- Build is incremental: only re-render layers or styles whose spec has changed

## Build incrementality

Track a content hash (or mtime) per artifact:
- `project.qgs` — regenerate if any `ProjectSpec` field changes
- Per-layer QML — regenerate only if that layer's `StyleSpec` changes
- Transform outputs — re-run only if source data or transform params change

Simple approach for v1: hash `project.py` and compare to a stored hash in
`build/.state`. Full dependency graph if complexity warrants it later.

## Reload in QGIS

Use the **Reloader** and **Reload Project** plugins from the QGIS plugin
repository. Reloader watches files; Reload Project adds Ctrl-R for the whole
project. Manual reload is fine for v1; automate later if it gets old.

## Deferred

Add when concrete need arises, not before:

- Structured transform tracking (v1 captures commands as plain strings;
  structured params, dependency tracking, and partial re-runs come later)
- Symbol library integration (NPS symbols, etc.)
- DVC for large derived rasters
- File watcher that triggers Ctrl-R automatically

## First task for Claude Code

1. Inspect `arp.qgz` and `park_symbols.qml` to understand the actual XML schema
2. Draft `src/models.py` — `ProjectSpec`, `LayerSpec`, `StyleSpec` — driven by
   what's actually in those files, not hypothetical fields
3. Implement `dump.py` using `lxml` to parse `arp.qgz` → `project.py`
4. Implement `render.py` to generate `build/project.qgs` from `project.py`
5. Verify round-trip: dump → build → open in QGIS → confirm visual match
6. Add incremental build state tracking to `build.py`

Do not build features beyond v1 until the round-trip works on a real project.
