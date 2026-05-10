from pathlib import Path

from models import Layer, SimpleFill, SingleSymbol, Symbol

park_features_symbol_polygons = Layer(
    id="park_features_symbol_polygons",
    name="park_features_symbol",
    type="vector",
    source="./data/park_features_symbol.geojson|geometrytype=Polygon",
    provider="ogr",
    crs="EPSG:4326",
    visible=True,
    style_xml=Path("styles/park_features_symbol_polygons.xml"),
    renderer=SingleSymbol(
        symbol=Symbol(
            type="fill",
            layers=[
                SimpleFill(
                    color="114,118,118,255,hsv:0.51255555555555554,0.04060425726710918,0.46428625925078204,1",
                    outline_color="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1",
                    outline_width=0.26,
                )
            ],
        )
    ),
)
