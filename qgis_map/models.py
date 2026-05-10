from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ── Symbol layers ─────────────────────────────────────────────────────────────


class SimpleFill(BaseModel):
    kind: Literal["SimpleFill"] = "SimpleFill"
    color: str = "0,0,0,255"
    style: str = "solid"
    outline_color: str = "35,35,35,255"
    outline_style: str = "solid"
    outline_width: float = 0.5
    outline_width_unit: str = "MM"
    joinstyle: str = "bevel"
    offset: str = "0,0"


class SimpleLine(BaseModel):
    kind: Literal["SimpleLine"] = "SimpleLine"
    line_color: str = "0,0,0,255"
    line_style: str = "solid"
    line_width: float = 0.5
    line_width_unit: str = "MM"
    capstyle: str = "square"
    joinstyle: str = "bevel"
    offset: str = "0"


class SvgMarker(BaseModel):
    kind: Literal["SvgMarker"] = "SvgMarker"
    name: str  # path to SVG file
    size: float = 6.0
    size_unit: str = "MM"
    color: str = "0,0,0,255"
    outline_color: str = "35,35,35,255"
    outline_width: float = 0.0
    outline_width_unit: str = "MM"
    angle: float = 0.0
    offset: str = "0,0"
    offset_unit: str = "MM"


class SimpleMarker(BaseModel):
    kind: Literal["SimpleMarker"] = "SimpleMarker"
    name: str = "circle"  # shape: circle, square, diamond, …
    size: float = 2.0
    size_unit: str = "MM"
    color: str = "0,0,0,255"
    outline_color: str = "35,35,35,255"
    outline_width: float = 0.0
    outline_width_unit: str = "MM"
    angle: float = 0.0
    offset: str = "0,0"
    offset_unit: str = "MM"
    joinstyle: str = "bevel"


SymbolLayer = Annotated[
    SimpleFill | SimpleLine | SvgMarker | SimpleMarker,
    Field(discriminator="kind"),
]

# ── Symbol ────────────────────────────────────────────────────────────────────


class Symbol(BaseModel):
    type: Literal["fill", "line", "marker"]
    alpha: float = 1.0
    layers: list[SymbolLayer]


# ── Renderers ─────────────────────────────────────────────────────────────────


class Rule(BaseModel):
    key: str
    label: str = ""
    filter: str = ""
    symbol_index: int
    active: bool = True


class SingleSymbol(BaseModel):
    kind: Literal["singleSymbol"] = "singleSymbol"
    symbol: Symbol


class RuleRenderer(BaseModel):
    kind: Literal["RuleRenderer"] = "RuleRenderer"
    rules_key: str
    rules: list[Rule]
    symbols: list[Symbol]


Renderer = Annotated[
    SingleSymbol | RuleRenderer,
    Field(discriminator="kind"),
]

# ── Processing step ───────────────────────────────────────────────────────────


class ProcessingStep(BaseModel):
    algorithm: str           # shell command template, e.g. "gdaldem slope {input} {output}"
    depends_on: list[str]    # IDs of layers that are algorithm inputs
    output: Path             # algorithm output path, e.g. Path("output/slope.tif")


# ── Layer and Project ─────────────────────────────────────────────────────────


class Layer(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    type: Literal["vector", "raster"]
    source: str
    provider: str = "ogr"
    style_xml: Path | None = None  # styles/{layer_id}.xml — full <maplayer> element
    crs: str | None = None
    visible: bool = True
    renderer: Renderer | None = None
    processing_step: ProcessingStep | None = None
    extra: dict[str, Any] = {}


class Project(BaseModel):
    model_config = ConfigDict(extra="allow")
    title: str
    crs: str
    layers: list[Layer]
    extent: tuple[float, float, float, float] | None = None
    extra: dict[str, Any] = {}
