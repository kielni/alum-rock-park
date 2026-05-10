from pathlib import Path

from models import Layer, ProcessingStep

elevation_polygon = Layer(
    id="elevation_polygon",
    name="USGS Elevation (clipped)",
    type="raster",
    source="./data/USGS_elevation_polygon.tif",
    provider="gdal",
    crs="EPSG:4269",
    alpha_band=2,
    visible=True,
    processing_step=ProcessingStep(
        description="Clip the USGS elevation raster to the park boundary polygon, adding an alpha channel so pixels outside the park are transparent.",
        algorithm="gdalwarp -cutline ./data/park_polygon.geojson -crop_to_cutline -dstalpha ./data/USGS_elevation.tif {output}",
        depends_on=[],
        output=Path("data/USGS_elevation_polygon.tif"),
    ),
)
