from pathlib import Path

from models import Layer, SimpleFill, SingleSymbol, Symbol

park_polygon = Layer(
    id="park_polygon",
    name="park_polygon",
    type="vector",
    source="./data/park_polygon.geojson",
    provider="ogr",
    crs="EPSG:4326",
    visible=True,
    style_xml=Path("styles/park_polygon.xml"),
    renderer=SingleSymbol(
        symbol=Symbol(
            type="fill",
            layers=[
                SimpleFill(
                    color="125,17,196,0,hsv:0.76702777777777775,0.91371023117418171,0.7686274509803922,0",
                    outline_color="112,9,209,255,hsv:0.75269444444444444,0.95939574273289085,0.82142366674296174,1",
                    outline_width=1.0,
                )
            ],
        )
    ),
)
