from pathlib import Path

from models import Layer

esri_satellite = Layer(
    id="esri_satellite",
    name="ESRI satellite",
    type="raster",
    source="http-header:referer=&type=xyz&url=https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/%7Bz%7D/%7By%7D/%7Bx%7D&zmax=18&zmin=0",
    provider="wms",
    crs="EPSG:3857",
    visible=False,
    style_xml=Path("styles/esri_satellite.xml"),
)
