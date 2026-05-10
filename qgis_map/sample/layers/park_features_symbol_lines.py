from pathlib import Path

from models import Layer, SimpleLine, SingleSymbol, Symbol

park_features_symbol_lines = Layer(
    id="park_features_symbol_lines",
    name="park_features_symbol",
    type="vector",
    source="./data/park_features_symbol.geojson|geometrytype=LineString",
    provider="ogr",
    crs="EPSG:4326",
    visible=True,
    style_xml=Path("styles/park_features_symbol_lines.xml"),
    renderer=SingleSymbol(
        symbol=Symbol(
            type="line",
            layers=[
                SimpleLine(
                    line_color="13,37,155,255,hsv:0.63800000000000001,0.9187762264438849,0.60784313725490191,1",
                    line_width=0.75,
                )
            ],
        )
    ),
)
