from pathlib import Path

from models import Layer, ProcessingStep

slope_polygon = Layer(
    id="slope_polygon",
    name="Slope (clipped)",
    type="raster",
    source="./data/USGS_slope_polygon.tif",
    provider="gdal",
    crs="EPSG:26910",
    alpha_band=2,
    visible=True,
    processing_step=ProcessingStep(
        description="Clip the slope raster to the park boundary polygon, adding an alpha channel so pixels outside the park are transparent.",
        algorithm="gdalwarp -cutline ./data/park_polygon.geojson -crop_to_cutline -dstalpha {input} {output}",
        depends_on=["slope_utm"],
        output=Path("data/USGS_slope_polygon.tif"),
    ),
)
