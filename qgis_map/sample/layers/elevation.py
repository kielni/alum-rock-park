from pathlib import Path

from models import Layer

elevation = Layer(
    id="elevation",
    name="elevation-import",
    type="raster",
    source="./data/elevation.tif",
    provider="gdal",
    crs="EPSG:4269",
    visible=False,
    style_xml=Path("styles/elevation.xml"),
)
