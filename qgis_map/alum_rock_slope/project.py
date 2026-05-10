from models import Project

from layers.cartodb_positron import cartodb_positron

spec = Project(
    title="Alum Rock Slope",
    crs="EPSG:26910",
    extent=(
        602083.987295319,
        4138271.4191198526,
        609581.3368248403,
        4141615.633206291,
    ),
    layers=[
        cartodb_positron,
    ],
)
