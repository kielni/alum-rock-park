# qgis_map

QGIS projects managed as code. Pydantic models in Python serialize to JSON;
a build script renders a `.qgs` file that QGIS opens as a viewer. See
[DESIGN.md](DESIGN.md) for the architecture and rationale.

## Layout

```
qgis_map/
  models.py          — Pydantic types for layers, renderers, symbols
  dump.py            — import a .qgz into a project directory
  render.py          — render project.py → build/project.qgs
  build.py           — entry point with incremental rebuild

  alum_rock_slope/   — one directory per project
    project.py       — source of truth (edit this)
    project.json     — committed artifact, used for diffs
    styles/          — per-layer XML extracted from the .qgz
    build/           — generated .qgs (gitignored)
```

## Python setup

```bash
uv sync
```

## Quick start: Alum Rock Park

```bash
# import arp.qgz into alum_rock_slope/
make dump-arp

# render alum_rock_slope/project.py → alum_rock_slope/build/project.qgs
make build-arp

# open alum_rock_slope/build/project.qgs in QGIS
# after rebuilds, reload with Ctrl-R
```

## Adding a new project

```bash
make dump SRC=path/to/file.qgz DIR=my_project
make build DIR=my_project
```

## Workflow

Edit `project.py` in your IDE. Run `make build-arp` (or `make build DIR=...`).
Reload in QGIS. Commit `project.py`, `project.json`, and any changed `styles/`.

## Requirements

- QGIS 3.x desktop app at `/Applications/QGIS.app`
- [uv](https://docs.astral.sh/uv/)

### QGIS reload shortcut

Bind Ctrl-R to reload the current project from disk:

`Settings → Keyboard Shortcuts`, search for "Revert", assign Ctrl+R.

### QGIS plugins

Install via `Plugins → Manage and Install Plugins`:

- **Reloader** (optional) — watches individual data files and auto-reloads
  affected layers when bytes change on disk.
