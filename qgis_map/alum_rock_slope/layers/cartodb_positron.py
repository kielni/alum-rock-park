from pathlib import Path

from models import Layer

cartodb_positron = Layer(
    id="cartodb_positron",
    name="CartoDB Positron",
    type="raster",
    source="http-header:referer=&type=xyz&url=https://basemaps.cartocdn.com/light_all/%7Bz%7D/%7Bx%7D/%7By%7D.png&zmax=19&zmin=0",
    provider="wms",
    crs="EPSG:3857",
    visible=True,
    style_xml=Path("styles/cartodb_positron.xml"),
)
