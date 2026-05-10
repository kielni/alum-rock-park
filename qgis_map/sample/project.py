from models import Project

from layers.arp_areas import arp_areas
from layers.arp_slope import arp_slope
from layers.cartodb_positron import cartodb_positron
from layers.elevation import elevation
from layers.elevation_10n import elevation_10n
from layers.esri_satellite import esri_satellite
from layers.park_features_symbol_lines import park_features_symbol_lines
from layers.park_features_symbol_points import park_features_symbol_points
from layers.park_features_symbol_polygons import park_features_symbol_polygons
from layers.park_polygon import park_polygon
from layers.slope import slope
from layers.unique_values_table import unique_values_table

spec = Project(
    title="",
    crs="EPSG:26910",
    extent=(
        605148.0975601125,
        4139304.783319104,
        605845.1453876096,
        4140093.2879730943,
    ),
    layers=[
        park_polygon,
        unique_values_table,
        slope,
        elevation_10n,
        arp_areas,
        park_features_symbol_points,
        park_features_symbol_lines,
        park_features_symbol_polygons,
        arp_slope,
        cartodb_positron,
        esri_satellite,
        elevation,
    ],
)
