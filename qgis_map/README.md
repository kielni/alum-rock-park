# qgis-project

QGIS project managed as code. Pydantic models in Python serialize to JSON;
a build script renders a `.qgs` file that QGIS opens as a viewer. See
[DESIGN.md](DESIGN.md) for the architecture and rationale.

## Quick start

```bash
# one-time: import an existing .qgz into the repo
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

- QGIS 3.x with PyQGIS
- Python 3.11+
- `pip install pydantic`

PyQGIS standalone setup is OS-specific; see the Makefile.
