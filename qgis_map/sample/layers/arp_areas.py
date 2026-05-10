from pathlib import Path

from models import Layer, SimpleFill, SingleSymbol, Symbol

arp_areas = Layer(
    id="arp_areas",
    name="ARP_areas",
    type="vector",
    source="./data/ARP_areas.geojson",
    provider="ogr",
    crs="EPSG:4326",
    visible=True,
    style_xml=Path("styles/arp_areas.xml"),
    renderer=SingleSymbol(
        symbol=Symbol(
            type="fill",
            alpha=0.506,
            layers=[
                SimpleFill(
                    color="152,125,183,0,rgb:0.5960784,0.4901961,0.7176471,0",
                    outline_color="39,32,47,255,hsv:0.74424999999999997,0.31694514381628136,0.18571755550469216,1",
                )
            ],
        )
    ),
)
