# qgis_map

QGIS project managed as code. Pydantic models in Python serialize to JSON;
a build script renders a `.qgs` file that QGIS opens as a viewer. See
[DESIGN.md](DESIGN.md) for the architecture and rationale.

## Python setup

```bash
uv sync
```

## Quick start

```bash
# import an existing .qgz
make dump SRC=path/to/existing.qgz

# build the .qgs from project.py
make build

# open in QGIS, then reload with Ctrl-R after rebuilds
```

## Layout

- `project.py` — source of truth (Pydantic ProjectSpec instance)
- `project.json` — committed build artifact, used for diffs
- `styles/` — `.qml` style files, committed as opaque blobs
- `data/` — raw input data
- `src/` — models, dump, render
- `build/` — generated `.qgs` (gitignored)

## Workflow

Edit `project.py` in your IDE. Run `make build`. Reload in QGIS. Commit.

For symbology, edit in QGIS UI → Save Style → overwrites the `.qml` in
`styles/`. Commit the `.qml`.

For Processing algorithms (slope, hillshade, etc.), copy the snippet from
QGIS's `Processing → History` and translate to a TransformSpec (not yet
implemented).

## Requirements

- QGIS 3.x desktop app at `/Applications/QGIS.app`
- [uv](https://docs.astral.sh/uv/)

### QGIS reload shortcut

Bind Ctrl-R to reload the current project from disk:

`Settings → Keyboard Shortcuts`, search for "Revert", assign Ctrl+R.

Used after every `make build` to pick up changes to `build/project.qgs`.

### QGIS plugins

Install via `Plugins → Manage and Install Plugins`:

- **Reloader** (optional) — watches individual data files and auto-reloads
  affected layers when bytes change on disk. Useful once derived data
  (transforms) is in the workflow; not needed for v1.