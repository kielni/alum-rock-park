from models import Project

from layers.cartodb_positron import cartodb_positron

# from layers.elevation_utm import elevation_utm
from layers.park_polygon import park_polygon
from layers.slope_class import slope_class

# from layers.slope_polygon import slope_polygon

# from layers.slope_utm import slope_utm

spec = Project(
    title="Alum Rock Slope",
    crs="EPSG:26910",
    extent=(
        603659.2369696891,
        4138750.586180653,
        608034.1597646123,
        4140702.032939304,
    ),
    layers=[
        park_polygon,
        slope_class,
        # slope_polygon,
        # elevation_utm,
        # slope_utm,
        cartodb_positron,
    ],
)
