from pathlib import Path

from models import Layer, Rule, RuleRenderer, SimpleMarker, SvgMarker, Symbol

_renderer = RuleRenderer(
    rules_key="{bb04642b-f9da-4f52-8c90-270a8056b0ff}",
    rules=[
        Rule(
            key="{7fc325ed-e2de-4cff-a2f1-262229909fff}",
            label="parking",
            filter="\"symbol\" = 'parking'",
            symbol_index=0,
        ),
        Rule(
            key="{f6a95713-252a-45da-b62d-7a9430575dfb}",
            label="picnic",
            filter="\"symbol\" = 'picnic'",
            symbol_index=1,
        ),
        Rule(
            key="{b2d4f8a3-b727-4969-b0bd-cfd2ae17e769}",
            label="ranger station",
            filter="\"symbol\" = 'ranger station'",
            symbol_index=2,
        ),
        Rule(
            key="{ee7e2257-8cba-446a-a49a-1ad2b3413e81}",
            label="shelter",
            filter="\"symbol\" = 'shelter'",
            symbol_index=3,
        ),
        Rule(
            key="{e198d526-e4ab-404b-bcbe-dbad9eba2e2d}",
            label="stream",
            filter="\"symbol\" = 'stream'",
            symbol_index=4,
            active=False,
        ),
        Rule(
            key="{7feccf46-df16-454b-88bf-832515a6b9be}",
            label="toilets",
            filter="\"symbol\" = 'toilets'",
            symbol_index=5,
        ),
        Rule(
            key="{b1d42b8d-7d64-4335-99b9-a696ae0ac3fa}",
            filter="ELSE",
            symbol_index=6,
            active=False,
        ),
    ],
    symbols=[
        Symbol(
            type="marker",
            layers=[
                SvgMarker(
                    name="transportation (NRGS NPS Respository)/svg/parking_light.svg",
                    color="75,75,75,255,hsv:0,0,0.29285114824139774,1",
                    outline_color="0,0,0,255,rgb:0,0,0,1",
                    outline_width=0.4,
                )
            ],
        ),
        Symbol(
            type="marker",
            layers=[
                SvgMarker(
                    name="camping (NRGS NPS Respository)/svg/picnic_area_light.svg",
                    color="25,201,148,255,hsv:0.45000000000000001,0.87450980392156863,0.78823529411764703,1",
                    outline_color="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1",
                )
            ],
        ),
        Symbol(
            type="marker",
            layers=[
                SvgMarker(
                    name="park_buildings (NRGS NPS Respository)/svg/ranger_light.svg",
                    color="230,100,193,255,hsv:0.88055555555555554,0.56470588235294117,0.90196078431372551,1",
                    outline_color="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1",
                )
            ],
        ),
        Symbol(
            type="marker",
            layers=[
                SvgMarker(
                    name="camping (NRGS NPS Respository)/svg/picnic_shelter_light.svg",
                    color="131,175,229,255,hsv:0.59166666666666667,0.42745098039215684,0.89803921568627454,1",
                    outline_color="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1",
                )
            ],
        ),
        Symbol(
            type="marker",
            layers=[
                SimpleMarker(
                    color="100,34,200,255,hsv:0.73333333333333328,0.83137254901960789,0.78431372549019607,1",
                    outline_color="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1",
                )
            ],
        ),
        Symbol(
            type="marker",
            layers=[
                SvgMarker(
                    name="services (NRGS NPS Respository)/svg/restrooms_light.svg",
                    color="107,221,87,255,hsv:0.30833333333333335,0.60784313725490191,0.8666666666666667,1",
                    outline_color="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1",
                )
            ],
        ),
        Symbol(
            type="marker",
            layers=[
                SimpleMarker(
                    color="230,227,60,255,hsv:0.16388888888888889,0.74117647058823533,0.90196078431372551,1",
                    outline_color="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1",
                )
            ],
        ),
    ],
)

park_features_symbol_points = Layer(
    id="park_features_symbol_points",
    name="park_features_symbol",
    type="vector",
    source="./data/park_features_symbol.geojson|geometrytype=Point",
    provider="ogr",
    crs="EPSG:4326",
    visible=True,
    style_xml=Path("styles/park_features_symbol_points.xml"),
    renderer=_renderer,
)
