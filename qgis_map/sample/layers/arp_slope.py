from pathlib import Path

from models import Layer

arp_slope = Layer(
    id="arp_slope",
    name="ARP slope",
    type="raster",
    source="./output/arp_slope.tif",
    provider="gdal",
    crs="EPSG:26910",
    visible=True,
    style_xml=Path("styles/arp_slope.xml"),
)
