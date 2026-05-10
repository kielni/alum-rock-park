from models import Layer, SimpleFill, SingleSymbol, Symbol

park_polygon = Layer(
    id="park_polygon",
    name="park_polygon",
    type="vector",
    source="./data/park_polygon.geojson",
    provider="ogr",
    crs="EPSG:4326",
    geometry_type="Polygon",
    visible=True,
    renderer=SingleSymbol(
        symbol=Symbol(
            type="fill",
            layers=[
                SimpleFill(
                    style="no",
                    outline_color="128,0,200,255",
                    outline_width=1.5,
                )
            ],
        )
    ),
)
