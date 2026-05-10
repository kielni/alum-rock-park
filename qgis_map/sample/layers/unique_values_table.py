from pathlib import Path

from models import Layer

unique_values_table = Layer(
    id="unique_values_table",
    name="Unique values table",
    type="vector",
    source="memory?geometry=NoGeometry&crs=EPSG:4326&field=value:double(20,8)&field=count:int8(20,0)&field=m2:double(20,8)",
    provider="memory",
    crs=None,
    visible=True,
    style_xml=Path("styles/unique_values_table.xml"),
)
