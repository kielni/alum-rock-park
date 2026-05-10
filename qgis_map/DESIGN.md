# DESIGN.md

Handoff document for working on this repo with Claude Code. Captures
architecture decisions made before any code was written. Read this first.

## Goal

Treat QGIS projects as build output, not source. Source of truth is Python +
`.qml` style files in this repo. A build script renders a `.qgs` file
that QGIS opens. QGIS is used as a viewer; edits happen in code or via
narrowly scoped UI actions that get captured back into source.

Data processing steps (reprojection, slope calculation, reclassification, etc.)
are also captured in code alongside the layers they produce. Each transform
records its inputs and the command to run, so the full pipeline is reproducible
from a fresh checkout and the system knows which downstream steps need re-running
when an input changes.

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
qgis_map/
  models.py               # Pydantic: Project, Layer, ProcessingStep, renderers, symbols
  dump.py                 # .qgz → layers/*.py + styles/*.xml
  render.py               # project.py → output/project.qgs
  prepare.py              # execute layer transforms (data prep, separate from build)
  build.py                # entry point
  Makefile
  local.env               # machine-local config (gitignored)
  local.env.example       # template

  <project_dir>/          # one directory per project
    project.py            # assembles Project from layers — edit this
    layers/               # one .py file per layer, named by layer ID
      slope.py
      elevation_10n.py
      park_polygon.py
      ...
    styles/               # per-layer XML extracted from .qgz, committed
    output/               # gitignored; derived rasters and project.qgs land here
```

### Key choices

**Pydantic models, hybrid typing.** Typed fields for things we touch (layer
source, CRS, style path); `extra: Any` dict and `model_config(extra="allow")`
for everything else. Expand the typed surface as we hit specific needs.

**`.qgs` not `.qgz`.** Uncompressed XML output, gitignored. Compressed
projects defeat diffing.

**`.qml` files parsed with Pydantic.** QML is XML; parse it into typed models
so symbology can be edited in code without touching the QGIS UI. QGIS UI is
used primarily for viewing, with light editing when convenient. Start from `park_symbols.qml` to drive the v1 schema.
Cross-layer operations (bump all symbol sizes, swap palette) follow naturally.

**Derived data (slope, hillshade) is gitignored, regenerated from recorded
transforms.** Each `Layer` with a `ProcessingStep` records the shell command and
its inputs. Re-running is triggered by `make prepare`, not `make build`.

## Layer IDs and filenames

Layer IDs are human-friendly strings: `"slope"`, `"elevation_10n"`,
`"park_polygon"`. Not QGIS-generated UUIDs. The ID is the stable handle used:

- as the filename: `layers/slope.py` contains a `Layer` with `id="slope"`
- in `depends_on` to declare transform inputs
- in `project.py` as the Python variable name after import

The ID (and filename stem) is derived by this priority:

| Layer type | ID rule | Example |
|---|---|---|
| File-backed source, one geometry type | stem of source file | `../park_polygon.geojson` → `park_polygon` |
| File-backed source, multiple geometry types from same file | stem + geometry suffix | `park_features_symbol_points`, `park_features_symbol_lines`, `park_features_symbol_polygons` |
| Derived / transform output | stem of `transform.output` | `output/slope.tif` → `slope` |
| Tile service or memory layer | descriptive name | `cartodb_positron`, `unique_values_table` |

When dumping an existing `.qgz`, replace the UUID-style IDs with human names
at that point. The QGIS project file uses whatever ID is in `project.py`.

## One layer per file

Each layer lives in `layers/{layer_id}.py` and exports a single variable with
the same name as the file. Complex renderers (`RuleRenderer`, multi-symbol
rules) are defined as named variables before the `Layer(...)` call in the same
file — not nested inline.

`project.py` only imports layers and assembles the `Project`:

```python
from layers.park_polygon import park_polygon
from layers.elevation_import import elevation_import
from layers.elevation_10n import elevation_10n
from layers.slope import slope

spec = Project(
    title="Alum Rock Park Slope",
    crs="EPSG:26910",
    layers=[park_polygon, elevation_import, elevation_10n, slope, ...],
)
```

`layers/slope.py` looks like:

```python
from pathlib import Path
from models import Layer, ProcessingStep

slope = Layer(
    id="slope",
    name="Slope",
    type="raster",
    source="output/slope.tif",
    provider="gdal",
    crs="EPSG:26910",
    processing_step=ProcessingStep(
        algorithm="gdaldem slope {input} {output}",
        depends_on=["elevation_10n"],
        output=Path("output/slope.tif"),
    ),
    style_xml=Path("styles/slope.xml"),
)
```

`layers/park_features_symbol.py` with a `RuleRenderer`:

```python
parking_rules = RuleRenderer(
    rules_key="{bb04642b-...}",
    rules=[
        Rule(key="{...}", label="parking", filter="\"symbol\" = 'parking'", symbol_index=0),
        Rule(key="{...}", label="picnic",  filter="\"symbol\" = 'picnic'",  symbol_index=1),
        ...
    ],
    symbols=[
        Symbol(type="marker", layers=[SvgMarker(name="transportation .../parking_light.svg", ...)]),
        Symbol(type="marker", layers=[SvgMarker(name="camping .../picnic_area_light.svg", ...)]),
        ...
    ],
)

park_features_symbol = Layer(
    id="park_features_symbol",
    name="park_features_symbol",
    type="vector",
    source="../park_features_symbol.geojson|geometrytype=Point",
    provider="ogr",
    crs="EPSG:4326",
    renderer=parking_rules,
    style_xml=Path("styles/park_features_symbol.xml"),
)
```

## LLM workflow documentation

Each project directory contains a `workflow.md` that records the LLM prompts used to build the project and what each one did. It is written collaboratively — the LLM drafts or updates it as work progresses.

**When to update:** after adding a layer, running a processing step, or making a non-trivial styling change. Update in the same session, not retroactively.

**What to capture per step:**

- The exact prompt (or close paraphrase)
- What the prompt caused to happen — files created, commands run, model fields set
- Any non-obvious choices (why a particular CRS, why alpha_band=2, etc.)
- Data source URLs and download instructions for external input files

**Format:** see `qgis_map/workflow.md` (the alum_rock_slope project) as a template. Sections are numbered steps; each step has a prompt block, a "What this does" description, and a files-created list.

**Purpose:** a new session can read `workflow.md` and reconstruct what was done and why — covering the intent and context that `git log` and the layer files alone don't capture.

## File ownership

Who writes what, and whether humans should edit it:

| File | Written by | Human edits? | Notes |
|---|---|---|---|
| `layers/*.py` | dump (once, bootstrap) | yes — source of truth after first dump | never overwritten by generator |
| `styles/*.xml` | dump / QGIS Save Style | no | always safe to overwrite; treat as opaque |
| `project.py` | human | yes | assembles layers into Project |
| `workflow.md` | LLM + human | yes | updated after each layer or processing step |
| `helpers.py` | human | yes | project-wide helper functions |
| `output/` | build / prepare | no | gitignored |

`styles/*.xml` absorbs all machine-written churn. Layer Python files are owned
by the human after bootstrap and never regenerated.

## Helper functions

Python functions related to transforms or styling belong as close to their use
as possible, promoted only when a second caller needs them:

- **Layer-specific** — define in `layers/{id}.py`, prefixed with `_`, above the
  `Layer(...)` call. These are never at risk of being overwritten.
- **Project-wide** — `{project_dir}/helpers.py`, imported by whichever layer
  files need it. Use for shared color ramps, standard fills, ARP house style, etc.
- **General / cross-project** — factory functions in `qgis_map/models.py`
  (construct common renderers), or `qgis_map/transforms.py` (gdal command
  builders, projection helpers).

Promote from layer file → `helpers.py` → `qgis_map/` only when a second caller
exists. Don't abstract in advance.

## Processing steps

Derived layers are produced by **Processing algorithms** — operations like
`gdal:slope`, `gdal:warpreproject`, or equivalent GDAL/GRASS shell commands.
Sources for the right algorithm and parameters: QGIS Processing Toolbox, QGIS
Processing History after an interactive run, GDAL/GRASS documentation, or an LLM.

`ProcessingStep` records a processing step: the algorithm invocation and its
`depends_on` layers:

```python
class ProcessingStep(BaseModel):
    algorithm: str     # shell command template, e.g. "gdaldem slope {input} {output}"
    depends_on: list[str]  # IDs of layers that are algorithm inputs
    output: Path       # algorithm output path, e.g. Path("output/slope.tif")
```

Only layers with a `ProcessingStep` have a processing step. Layers without one
(vector files, tile services, the raw elevation raster) are input-only and
appear only in `depends_on`.

### Two separate workflows

**`make build`** — renders `output/project.qgs` from `project.py`. Does not
run any Processing algorithms. Fast, pure Python.

**`make prepare`** — runs Processing algorithms for stale layers in dependency
order. Slow; involves executing GDAL, GRASS, or other algorithms. Run when
source data changes or an algorithm invocation is updated.

### Dependency graph and staleness

`prepare.py` builds a dependency graph from all layers' `depends_on` lists
and does a topological sort. A layer is stale if:

- its output does not exist, or
- any layer in `depends_on` is stale (transitively), or
- its `algorithm` has changed since the last run (tracked in `output/.state`)

Re-running a stale layer marks all downstream layers stale, so they re-run in
dependency order. Changing `elevation_10n` automatically re-runs `slope` and
any layer with `slope` in its `depends_on`.

## Models

```python
class ProcessingStep(BaseModel):
    algorithm: str         # shell command template
    depends_on: list[str]  # layer IDs that are algorithm inputs
    output: Path           # algorithm output path

class Layer(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str                          # human-friendly, e.g. "slope"
    name: str                        # QGIS display name
    type: Literal["vector", "raster"]
    source: str                      # path or URI; for derived layers, matches output/...
    provider: str = "ogr"
    style_xml: Path | None = None
    crs: str | None = None
    visible: bool = True
    renderer: Renderer | None = None
    processing_step: ProcessingStep | None = None
    extra: dict[str, Any] = {}

class Project(BaseModel):
    model_config = ConfigDict(extra="allow")
    title: str
    crs: str
    layers: list[Layer]
    extent: tuple[float, float, float, float] | None = None
    extra: dict[str, Any] = {}
```

Start here. Add fields when something concrete needs them.

## Workflow

1. Place `project_dir.qgz` inside `project_dir/`, then `make dump DIR=project_dir`
   — generates `layers/*.py` and `styles/*.xml`. Rename IDs to human-friendly
   names. Commit.
2. `make build DIR=project_dir` — emit `output/project.qgs`. Open in QGIS.
   Verify it matches the original.
3. Edit a layer file in VSCode. `make build DIR=...`. Reload in QGIS with
   Ctrl-R. Commit the layer file.
4. When a transform's source data changes or command is updated: `make prepare
   DIR=project_dir`. This re-runs stale transforms in dependency order, then
   `make build`.
5. Two directions for symbology:
   - **Code → QGIS**: edit the layer file, `make build`, reload in QGIS.
   - **QGIS → code**: tweak in QGIS UI, Save Style to overwrite the file in
     `styles/`. Commit the updated XML. Optionally re-parse it back into the
     layer's `renderer` field manually; `git diff` to review what changed.

## Dump implementation notes

No PyQGIS — parse XML directly. A `.qgz` is a zip; unzip to get `.qgs`.

- Unzip `arp.qgz` → `project.qgs` (XML)
- Parse with `lxml` or `xml.etree`
- Per `<maplayer>`: extract `datasource`, `srs/authid`, `provider`, `layername`
- Extract embedded or linked `.qml` style per layer
- Parse QML into `Renderer` Pydantic models
- **Bootstrap behavior**: write `layers/{id}.py` only if the file does not already
  exist. Skip existing files silently. Use `--force LAYER_ID` to overwrite a
  single named layer when a deliberate re-sync is needed.
- Always overwrite `styles/*.xml` — these are never human-edited.
- Replace UUID-style IDs with human-friendly names at dump time
- Run `black` on emitted Python for clean diffs
- Lossy is acceptable in v1. Round-trip fidelity verified visually in QGIS.

## Render implementation notes

No PyQGIS — generate XML directly.

- Load `Project` by importing `project.py`
- Start from a minimal `.qgs` XML template
- Inject layer entries, CRS, extent, title by manipulating the XML tree
- Serialize each `Renderer` back to QML XML (or embed `style_xml` contents)
- Write `output/project.qgs`

## Build incrementality

Track a content hash per artifact in `output/.state`:

- `project.qgs` — regenerate if any `Project` field or any layer file changes
- Per-layer QML — regenerate only if that layer's renderer changes
- ProcessingStep outputs — managed by `prepare.py`; re-run if source is stale or
  command hash changed

## Reload in QGIS

Use the **Reloader** and **Reload Project** plugins. Reloader watches files;
Reload Project adds Ctrl-R for the whole project.

## Deferred

Add when concrete need arises, not before:

- Symbol library integration (NPS symbols, etc.)
- DVC for large derived rasters
- File watcher that triggers Ctrl-R automatically
- Multi-step transforms (chain of commands, intermediate files)
