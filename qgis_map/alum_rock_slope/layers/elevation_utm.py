from pathlib import Path

from models import Layer, ProcessingStep

elevation_utm = Layer(
    id="elevation_utm",
    name="Elevation (UTM)",
    type="raster",
    source="./data/USGS_elevation_utm.tif",
    provider="gdal",
    crs="EPSG:26910",
    visible=False,
    processing_step=ProcessingStep(
        description="Reproject the USGS elevation raster from NAD83 geographic (EPSG:4269) to UTM zone 10N (EPSG:26910) so horizontal and vertical units match for slope calculation.",
        algorithm="gdalwarp -t_srs EPSG:26910 -r bilinear ./data/USGS_elevation.tif {output}",
        depends_on=[],
        output=Path("data/USGS_elevation_utm.tif"),
    ),
)
