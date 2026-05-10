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
        algorithm="gdalwarp -cutline ./data/park_polygon.geojson -crop_to_cutline -dstalpha ./data/USGS_elevation.tif {output}",
        depends_on=[],
        output=Path("data/USGS_elevation_polygon.tif"),
    ),
)
