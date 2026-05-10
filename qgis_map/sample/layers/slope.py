from pathlib import Path

from models import Layer, ProcessingStep

slope = Layer(
    id="slope",
    name="Slope",
    type="raster",
    source="./output/slope.tif",
    provider="gdal",
    crs="EPSG:26910",
    visible=False,
    style_xml=Path("styles/slope.xml"),
    processing_step=ProcessingStep(
        algorithm="gdaldem slope {input} {output}",
        depends_on=["elevation_10n"],
        output=Path("output/slope.tif"),
    ),
)
