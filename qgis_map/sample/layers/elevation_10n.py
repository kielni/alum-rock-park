from pathlib import Path

from models import Layer, ProcessingStep

elevation_10n = Layer(
    id="elevation_10n",
    name="elevation-10N",
    type="raster",
    source="./output/elevation_10n.tif",
    provider="gdal",
    crs="EPSG:26910",
    visible=False,
    style_xml=Path("styles/elevation_10n.xml"),
    processing_step=ProcessingStep(
        algorithm="gdalwarp -t_srs EPSG:26910 -r bilinear {input} {output}",
        depends_on=["elevation"],
        output=Path("output/elevation_10n.tif"),
    ),
)
