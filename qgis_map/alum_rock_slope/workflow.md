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

## 4. Add a GeoJSON vector layer

**Prompts:**

> add new layer to alum_rock_park project from data/park_polygon.geojson ; this is a polygon layer that should draw on top of basemap

> style the park polygon as a thick purple outline, transparent inside

**What this does:**

- Creates `<project_dir>/layers/<name>.py` with a `Layer` definition:
  - `type="vector"`, `provider="ogr"`, `crs="EPSG:4326"` (GeoJSON is always WGS84)
  - `geometry_type="Polygon"` (or `"LineString"` / `"Point"`) — this enables XML-free layer generation
  - `source="./data/<name>.geojson"` — path relative to the project directory
  - An inline `renderer` describing the style
- No style XML file is needed. The build system generates the `<maplayer>` element from the layer definition, using pyproj to embed the CRS.
- Layer order in `project.py` controls draw order: layers listed first draw on top.
- CRS mismatch between layer and project is handled automatically by QGIS (on-the-fly reprojection).

**Style primitives for polygons:**

| Goal | Key fields |
|---|---|
| Transparent fill | `style="no"` |
| Solid fill | `style="solid"`, `color="R,G,B,255"` |
| Outline color | `outline_color="R,G,B,255"` |
| Outline thickness | `outline_width=1.5` (mm) |

**Files created:**
- `<project_dir>/layers/<name>.py`

---

## 5. Add an elevation raster layer

### Data source

- **Download tool:** [The National Map Downloader](https://apps.nationalmap.gov/downloader/) — select Elevation Products (3DEP), 1/3 arc-second (~10m), GeoTIFF
- **Dataset used:** [USGS 1/3 arc-second DEM tile](https://www.sciencebase.gov/catalog/item/68afba8fd4be02645f9b293f)
- Native CRS: **EPSG:4269** (NAD83 geographic)
- Place the downloaded file at `<project_dir>/data/USGS_elevation.tif`

### Clip to park boundary

Run once manually before building:

```bash
gdalwarp \
  -cutline ./data/park_polygon.geojson \
  -crop_to_cutline \
  -dstalpha \
  ./data/USGS_elevation.tif \
  ./data/USGS_elevation_polygon.tif
```

`-dstalpha` adds a second band as an alpha channel so pixels outside the polygon are transparent rather than black.

### Prompt

> I downloaded elevation data from the national map and put it in alum_rock_slope/data/USGS_elevation.tif. I want to clip the data to the polygon in alum_rock_slope/data/park_polygon.geojson and output as alum_rock_slope/data/USGS_elevation_polygon.tif. Record the processing step and add the output layer to the project

**What this does:**

- Runs `gdalwarp` to clip the raster to the park polygon with an alpha channel.
- Creates `<project_dir>/layers/<name>.py` with:
  - `type="raster"`, `provider="gdal"`, `crs="EPSG:4269"`
  - `alpha_band=2` — tells QGIS to use band 2 (the `-dstalpha` output) as the transparency mask; without this the nodata area renders as solid black
  - `processing_step` — records the gdalwarp command and output path for reproducibility
- No style XML needed. The build generates a singleband gray renderer with stretch-to-min/max.
- Layer order: place between the park polygon (top) and basemap (bottom).

**Files created:**
- `<project_dir>/layers/<name>.py`
- `<project_dir>/data/USGS_elevation_polygon.tif` (from gdalwarp)

---

## Notes

- Every new project needs `styles/base.qgs`. Copy it from `sample/styles/base.qgs` — it works for any project using the same QGIS version and CRS.
- Vector layers with `geometry_type` set and an inline `renderer` need no XML file. The build generates the `<maplayer>` element automatically.
- Raster layers also work without a style XML file. The build generates a default singleband gray renderer. Set `alpha_band=2` if the file was created with `gdalwarp -dstalpha`.
- Tile basemap layers (provider `wms`) still require a `style_xml` file (copy from sample or export from QGIS via Layer Properties → Style → Save Style).
- Layers with neither `style_xml` nor `geometry_type` appear in the layer tree but not in `projectlayers`, so QGIS won't load them.
