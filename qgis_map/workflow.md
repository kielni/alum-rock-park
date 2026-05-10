# QGIS Map Workflow

Step-by-step prompts and descriptions for building a new project using the text-to-map tools.

---

## 1. Start a new project

**Prompts:**

> create alum_rock_slope/project.py with map extent -121.846852,37.385582 : -121.761683,37.414863
> CRS NAD83 / UTM zone 10N (coordinates will need to be updated for this CRS)

**What this does:**

- Creates `<project_dir>/project.py` defining a `Project` with title, CRS, and extent.
- The extent is given in WGS84 (lon/lat) and converted to the project CRS (EPSG:26910 UTM zone 10N) using pyproj.
- The `layers` list starts empty.

**Files created:**
- `<project_dir>/project.py`

---

## 2. Add a basemap tile layer

**Prompt:**

> set cartodb positron as basemap layer : https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png

**What this does:**

- Creates `<project_dir>/layers/cartodb_positron.py` — a `Layer` with provider `wms`, using the XYZ tile URL encoded in QGIS datasource format (`http-header:referer=&type=xyz&url=...&zmax=19&zmin=0`).
- Copies `styles/cartodb_positron.xml` from the sample — this is the full `<maplayer>` XML that QGIS needs to load the layer (CRS, renderer, pipe settings, etc.).
- Adds the layer to `project.py`'s `layers` list.

**Files created:**
- `<project_dir>/layers/cartodb_positron.py`
- `<project_dir>/styles/cartodb_positron.xml` (copied from sample)

---

## 3. Build the project

**Prompt:**

> build and generate output that I can load in qgis

**What this does:**

- Copies `styles/base.qgs` from the sample — a minimal QGIS project XML skeleton (same QGIS version, same CRS) that the build system patches with the project's extent, CRS, title, layer tree, and layer definitions.
- Runs `make build DIR=<project_dir>`, which:
  1. Formats Python files with black
  2. Loads `project.py` and resolves each layer
  3. Injects each layer's `<maplayer>` XML (from `styles/*.xml`) into `projectlayers`
  4. Rebuilds the layer tree, legend, and layer order
  5. Writes `<project_dir>/output/project.qgs`

**Files created:**
- `<project_dir>/styles/base.qgs` (copied from sample)
- `<project_dir>/output/project.qgs` — open this in QGIS

---

## Notes

- Every new project needs `styles/base.qgs`. Copy it from `sample/styles/base.qgs` — it works for any project using the same QGIS version and CRS.
- Every layer with a `style_xml` path needs a corresponding XML file in `styles/`. These can be copied from sample or exported from QGIS via Layer Properties → Style → Save Style.
- Layers without `style_xml` appear in the layer tree but not in `projectlayers`, so QGIS won't load them.
