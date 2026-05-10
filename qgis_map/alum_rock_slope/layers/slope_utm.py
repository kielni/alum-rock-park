from pathlib import Path

from models import Layer, ProcessingStep

slope_utm = Layer(
    id="slope_utm",
    name="Slope (UTM)",
    type="raster",
    source="./data/USGS_slope_utm.tif",
    provider="gdal",
    crs="EPSG:26910",
    visible=False,
    processing_step=ProcessingStep(
        description="Calculate slope in degrees from the UTM-projected elevation raster.",
        algorithm="gdaldem slope {input} {output}",
        depends_on=["elevation_utm"],
        output=Path("data/USGS_slope_utm.tif"),
    ),
)
