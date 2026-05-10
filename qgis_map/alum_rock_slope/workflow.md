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

## 6. Calculate slope from elevation

**Prompt:**

> I want to calculate slope in degrees from the elevation layer ; walk me through the options

> reproject elevation, run slope, and clip

**What this does:**

Runs a three-step pipeline — each step recorded as a layer with a `ProcessingStep`:

| Step | Command | Input | Output |
|---|---|---|---|
| Reproject | `gdalwarp -t_srs EPSG:26910 -r bilinear` | `USGS_elevation.tif` | `USGS_elevation_utm.tif` |
| Slope | `gdaldem slope` | `USGS_elevation_utm.tif` | `USGS_slope_utm.tif` |
| Clip | `gdalwarp -cutline … -crop_to_cutline -dstalpha` | `USGS_slope_utm.tif` | `USGS_slope_polygon.tif` |

Why reproject first: the source DEM is in EPSG:4269 (geographic degrees). `gdaldem slope` needs horizontal and vertical units to match — UTM gives consistent metres in all three axes. Reprojecting before slope avoids the approximation error of the `-s` scale factor.

Creates three layer files:
- `layers/elevation_utm.py` — hidden intermediate; depends_on=[]
- `layers/slope_utm.py` — hidden intermediate; depends_on=["elevation_utm"]
- `layers/slope_polygon.py` — visible display layer; `alpha_band=2`, depends_on=["slope_utm"]

**Intermediate layers in `project.py`:**

The `_utm` layers are recorded in `layers/` for reproducibility but are not display layers. They are commented out of `project.py` so they don't appear in QGIS:

```python
# from layers.elevation_utm import elevation_utm
from layers.slope_polygon import slope_polygon
# from layers.slope_utm import slope_utm

layers=[
    park_polygon,
    slope_polygon,
    elevation_polygon,
    # elevation_utm,
    # slope_utm,
    cartodb_positron,
]
```

To force a rebuild after commenting layers in or out: `make build-all DIR=<project_dir>`.

**Files created:**
- `layers/elevation_utm.py`, `layers/slope_utm.py`, `layers/slope_polygon.py`
- `data/USGS_elevation_utm.tif`, `data/USGS_slope_utm.tif`, `data/USGS_slope_polygon.tif`

---

## 7. Classify slope into categories

**Prompts:**

> tell me about slope degree breakpoints for flat, moderate, steep etc commonly used in vegetation management contexts

> classify the slope layer into categories using Mechanical treatment access categories

> update the word "deg" in the category labels with the degree symbol

> set the transparency of the slope_class layer to 60%

**What this does:**

Runs `gdal_calc.py` to reclassify the continuous slope raster into five integer categories based on mechanical treatment access breakpoints:

| Value | Label | Range | Meaning |
|---|---|---|---|
| 1 | Flat | 0–5° | All equipment |
| 2 | Gentle | 5–11° | Wheeled tractors, mowers |
| 3 | Moderate | 11–22° | Tracked equipment |
| 4 | Steep | 22–31° | Hand crews |
| 5 | Very steep | >31° | Hand crews only |

The classification formula uses `numpy.select` inside `gdal_calc.py`, masked by the alpha band (band 2) so areas outside the park polygon stay as nodata (value 0):

```bash
gdal_calc.py -A USGS_slope_polygon.tif --A_band=1 \
             -B USGS_slope_polygon.tif --B_band=2 \
             --outfile=USGS_slope_class.tif \
             --calc="numpy.where(B>0, numpy.select([A<5, A<11, A<22, A<31], [1,2,3,4], 5), 0)" \
             --type=Byte --NoDataValue=0 --quiet
```

**Styling with `PalettedRenderer`:**

Uses the `PalettedRenderer` model with one `PaletteEntry` per class. Each entry takes an integer `value`, a hex `color`, and a `label` (shown in the QGIS legend):

```python
renderer=PalettedRenderer(
    opacity=0.6,
    entries=[
        PaletteEntry(value=1, color="#1a9641", label="Flat (0-5°)"),
        PaletteEntry(value=2, color="#a6d96a", label="Gentle (5-11°)"),
        PaletteEntry(value=3, color="#fdae61", label="Moderate (11-22°)"),
        PaletteEntry(value=4, color="#d7191c", label="Steep (22-31°)"),
        PaletteEntry(value=5, color="#7b0000", label="Very steep (>31°)"),
    ],
)
```

`opacity` on `PalettedRenderer` sets layer transparency (0.0 = invisible, 1.0 = fully opaque). No style XML needed.

**Files created:**
- `layers/slope_class.py`
- `data/USGS_slope_class.tif`

---

## Notes

- Every new project needs `styles/base.qgs`. Copy it from `sample/styles/base.qgs` — it works for any project using the same QGIS version and CRS.
- Vector layers with `geometry_type` set and an inline `renderer` need no XML file. The build generates the `<maplayer>` element automatically.
- Raster layers also work without a style XML file. The build generates a default singleband gray renderer. Set `alpha_band=2` if the file was created with `gdalwarp -dstalpha`.
- Tile basemap layers (provider `wms`) still require a `style_xml` file (copy from sample or export from QGIS via Layer Properties → Style → Save Style).
- Layers with neither `style_xml` nor `geometry_type` appear in the layer tree but not in `projectlayers`, so QGIS won't load them.
