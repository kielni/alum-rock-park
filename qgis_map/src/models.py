from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class LayerSpec(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    type: Literal["vector", "raster"]
    source: str
    provider: str = "ogr"
    style_xml: Path | None = None  # styles/{layer_id}.xml — full <maplayer> element
    crs: str | None = None
    visible: bool = True
    extra: dict[str, Any] = {}


class ProjectSpec(BaseModel):
    model_config = ConfigDict(extra="allow")
    title: str
    crs: str
    layers: list[LayerSpec]
    extent: tuple[float, float, float, float] | None = None
    extra: dict[str, Any] = {}
