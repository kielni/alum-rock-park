"""Render project.py → output/project.qgs."""

from __future__ import annotations

import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from models import (
    PalettedRenderer,
    Renderer,
    SimpleFill,
    SimpleLine,
    SimpleMarker,
    SingleSymbol,
    SvgMarker,
    Symbol,
    SymbolLayer,
    RuleRenderer,
)

HERE = Path(__file__).parent  # qgis_map/

_QGS_DOCTYPE = "<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>\n"


def _abs_source(source: str, project_dir: Path) -> str:
    """Resolve a source path to absolute for the QGS datasource.

    Paths starting with './' are project-dir-relative (derived outputs).
    All other relative paths are HERE-relative (source data alongside the repo).
    URIs and absolute paths are returned unchanged.
    """
    if source.startswith("/") or ":" in source.split("/")[0]:
        return source
    geom_suffix = ""
    path_part = source
    if "|" in source:
        path_part, geom_suffix = source.split("|", 1)
        geom_suffix = "|" + geom_suffix
    if path_part.startswith("./"):
        return str((project_dir / path_part).resolve()) + geom_suffix
    return str((HERE / path_part).resolve()) + geom_suffix


def _load_spec(project_dir: Path):
    spec_path = project_dir / "project.py"
    if not spec_path.exists():
        raise SystemExit(
            f"project.py not found in {project_dir} — run 'make dump' first"
        )
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))
    module_spec = importlib.util.spec_from_file_location("project", spec_path)
    mod = importlib.util.module_from_spec(module_spec)
    sys.modules["project"] = mod
    module_spec.loader.exec_module(mod)
    return mod.spec


def _update_extent(root: ET.Element, extent: tuple) -> None:
    xmin, ymin, xmax, ymax = extent
    for canvas in root.findall("mapcanvas"):
        if canvas.get("name") == "theMapCanvas":
            ext = canvas.find("extent")
            if ext is None:
                ext = ET.SubElement(canvas, "extent")
            for tag, val in (
                ("xmin", xmin),
                ("ymin", ymin),
                ("xmax", xmax),
                ("ymax", ymax),
            ):
                el = ext.find(tag)
                if el is None:
                    el = ET.SubElement(ext, tag)
                el.text = repr(val)
            break


def _update_crs(root: ET.Element, authid: str) -> None:
    srs = root.find("projectCrs/spatialrefsys")
    if srs is not None:
        el = srs.find("authid")
        if el is not None:
            el.text = authid


def _update_title(root: ET.Element, title: str) -> None:
    el = root.find("title")
    if el is not None:
        el.text = title
    root.set("projectname", title)


def _rebuild_layer_tree(root: ET.Element, spec) -> None:
    ltg = root.find("layer-tree-group")
    if ltg is None:
        return

    for layer in spec.layers:
        checked = "Qt::Checked" if layer.visible else "Qt::Unchecked"
        ltl = ET.SubElement(
            ltg,
            "layer-tree-layer",
            checked=checked,
            legend_exp="",
            legend_split_behavior="0",
            providerKey=layer.provider,
            patch_size="-1,-1",
            id=layer.id,
            source=layer.source,
            expanded="1",
            name=layer.name,
        )
        cp = ET.SubElement(ltl, "customproperties")
        ET.SubElement(cp, "Option")

    custom_order = ET.SubElement(ltg, "custom-order", enabled="0")
    for layer in spec.layers:
        item = ET.SubElement(custom_order, "item")
        item.text = layer.id


def _rebuild_legend(root: ET.Element, spec) -> None:
    legend = root.find("legend")
    if legend is None:
        legend = ET.SubElement(root, "legend", updateDrawingOrder="true")

    for layer in spec.layers:
        checked = "Qt::Checked" if layer.visible else "Qt::Unchecked"
        vis = "1" if layer.visible else "0"
        ll = ET.SubElement(
            legend,
            "legendlayer",
            checked=checked,
            open="true",
            showFeatureCount="0",
            drawingOrder="-1",
            name=layer.name,
        )
        fg = ET.SubElement(ll, "filegroup", hidden="false", open="true")
        ET.SubElement(
            fg, "legendlayerfile", layerid=layer.id, visible=vis, isInOverview="0"
        )


def _rebuild_layerorder(root: ET.Element, spec) -> None:
    lo = root.find("layerorder")
    if lo is None:
        lo = ET.SubElement(root, "layerorder")
    for layer in spec.layers:
        ET.SubElement(lo, "layer", id=layer.id)


# ── Renderer serialization ────────────────────────────────────────────────────

_SCALE = "3x:0,0,0,0,0,0"


def _ddp() -> ET.Element:
    ddp = ET.Element("data_defined_properties")
    m = ET.SubElement(ddp, "Option", type="Map")
    ET.SubElement(m, "Option", name="name", value="", type="QString")
    ET.SubElement(m, "Option", name="properties")
    ET.SubElement(m, "Option", name="type", value="collection", type="QString")
    return ddp


def _opt_map(props: dict[str, str]) -> ET.Element:
    el = ET.Element("Option", type="Map")
    for name, value in props.items():
        ET.SubElement(el, "Option", name=name, value=value, type="QString")
    return el


def _render_symbol_layer(sl: SymbolLayer) -> ET.Element:
    el = ET.Element(
        "layer", locked="0", enabled="1", **{"class": sl.kind, "pass": "0", "id": ""}
    )
    if isinstance(sl, SimpleFill):
        props = {
            "border_width_map_unit_scale": _SCALE,
            "color": sl.color,
            "joinstyle": sl.joinstyle,
            "offset": sl.offset,
            "offset_map_unit_scale": _SCALE,
            "offset_unit": "MM",
            "outline_color": sl.outline_color,
            "outline_style": sl.outline_style,
            "outline_width": str(sl.outline_width),
            "outline_width_unit": sl.outline_width_unit,
            "style": sl.style,
        }
    elif isinstance(sl, SimpleLine):
        props = {
            "capstyle": sl.capstyle,
            "customdash": "5;2",
            "customdash_map_unit_scale": _SCALE,
            "customdash_unit": "MM",
            "draw_inside_polygon": "0",
            "joinstyle": sl.joinstyle,
            "line_color": sl.line_color,
            "line_style": sl.line_style,
            "line_width": str(sl.line_width),
            "line_width_unit": sl.line_width_unit,
            "offset": sl.offset,
            "offset_map_unit_scale": _SCALE,
            "offset_unit": "MM",
            "ring_filter": "0",
            "use_custom_dash": "0",
            "width_map_unit_scale": _SCALE,
        }
    elif isinstance(sl, SvgMarker):
        props = {
            "angle": str(sl.angle),
            "color": sl.color,
            "fixedAspectRatio": "0",
            "horizontal_anchor_point": "1",
            "name": sl.name,
            "offset": sl.offset,
            "offset_map_unit_scale": _SCALE,
            "offset_unit": sl.offset_unit,
            "outline_color": sl.outline_color,
            "outline_width": str(sl.outline_width),
            "outline_width_map_unit_scale": _SCALE,
            "outline_width_unit": sl.outline_width_unit,
            "scale_method": "diameter",
            "size": str(sl.size),
            "size_map_unit_scale": _SCALE,
            "size_unit": sl.size_unit,
            "vertical_anchor_point": "1",
        }
    elif isinstance(sl, SimpleMarker):
        props = {
            "angle": str(sl.angle),
            "color": sl.color,
            "horizontal_anchor_point": "1",
            "joinstyle": sl.joinstyle,
            "name": sl.name,
            "offset": sl.offset,
            "offset_map_unit_scale": _SCALE,
            "offset_unit": sl.offset_unit,
            "outline_color": sl.outline_color,
            "outline_style": "solid",
            "outline_width": str(sl.outline_width),
            "outline_width_map_unit_scale": _SCALE,
            "outline_width_unit": sl.outline_width_unit,
            "scale_method": "diameter",
            "size": str(sl.size),
            "size_map_unit_scale": _SCALE,
            "size_unit": sl.size_unit,
            "vertical_anchor_point": "1",
        }
    else:
        props = {}
    el.append(_opt_map(props))
    el.append(_ddp())
    return el


def _render_symbol(sym: Symbol, name: str) -> ET.Element:
    el = ET.Element(
        "symbol",
        clip_to_extent="1",
        alpha=str(sym.alpha),
        type=sym.type,
        is_animated="0",
        frame_rate="10",
        force_rhr="0",
        name=name,
    )
    el.append(_ddp())
    for sl in sym.layers:
        el.append(_render_symbol_layer(sl))
    return el


def _render_renderer(renderer: Renderer) -> ET.Element:
    base = dict(
        forceraster="0", referencescale="-1", symbollevels="0", enableorderby="0"
    )
    if isinstance(renderer, SingleSymbol):
        el = ET.Element("renderer-v2", type="singleSymbol", **base)
        syms = ET.SubElement(el, "symbols")
        syms.append(_render_symbol(renderer.symbol, "0"))
        ET.SubElement(el, "rotation")
        ET.SubElement(el, "sizescale")
        return el
    if isinstance(renderer, RuleRenderer):
        el = ET.Element("renderer-v2", type="RuleRenderer", **base)
        rules_el = ET.SubElement(el, "rules", key=renderer.rules_key)
        for rule in renderer.rules:
            attrs: dict[str, str] = {
                "key": rule.key,
                "label": rule.label,
                "filter": rule.filter,
                "symbol": str(rule.symbol_index),
            }
            if not rule.active:
                attrs["checkstate"] = "0"
            ET.SubElement(rules_el, "rule", **attrs)
        syms = ET.SubElement(el, "symbols")
        for i, sym in enumerate(renderer.symbols):
            syms.append(_render_symbol(sym, str(i)))
        return el
    raise ValueError(f"Unknown renderer type: {type(renderer)}")


def _srs_element(authid: str) -> ET.Element:
    from pyproj import CRS as ProjCRS

    crs = ProjCRS(authid)
    epsg_code = authid.split(":")[-1]
    srs = ET.Element("srs")
    sys_el = ET.SubElement(srs, "spatialrefsys", nativeFormat="Wkt")
    ET.SubElement(sys_el, "wkt").text = crs.to_wkt()
    ET.SubElement(sys_el, "proj4").text = crs.to_proj4()
    ET.SubElement(sys_el, "srsid").text = "0"
    ET.SubElement(sys_el, "srid").text = epsg_code
    ET.SubElement(sys_el, "authid").text = authid
    ET.SubElement(sys_el, "description").text = crs.name
    ET.SubElement(sys_el, "projectionacronym").text = ""
    ET.SubElement(sys_el, "ellipsoidacronym").text = ""
    ET.SubElement(sys_el, "geographicflag").text = (
        "true" if crs.is_geographic else "false"
    )
    return srs


def _build_vector_maplayer(layer) -> ET.Element:
    ml = ET.Element(
        "maplayer",
        type="vector",
        geometry=layer.geometry_type,
        wkbType=layer.geometry_type,
        autoRefreshTime="0",
        autoRefreshMode="Disabled",
        styleCategories="AllStyleCategories",
        labelsEnabled="0",
        readOnly="0",
        refreshOnNotifyEnabled="0",
        refreshOnNotifyMessage="",
        maxScale="0",
        minScale="100000000",
        hasScaleBasedVisibilityFlag="0",
        simplifyDrawingHints="1",
        simplifyDrawingTol="1",
        simplifyMaxScale="1",
        simplifyAlgorithm="0",
        simplifyLocal="1",
        symbologyReferenceScale="-1",
        legendPlaceholderImage="",
    )
    ET.SubElement(ml, "id").text = layer.id
    ET.SubElement(ml, "datasource")
    ET.SubElement(ml, "layername").text = layer.name
    if layer.crs:
        ml.append(_srs_element(layer.crs))
    ET.SubElement(ml, "provider", encoding="UTF-8").text = layer.provider
    style_mgr = ET.SubElement(ml, "map-layer-style-manager", current="default")
    ET.SubElement(style_mgr, "map-layer-style", name="default")
    flags = ET.SubElement(ml, "flags")
    for flag, val in [
        ("Identifiable", "1"),
        ("Removable", "1"),
        ("Searchable", "1"),
        ("Private", "0"),
    ]:
        ET.SubElement(flags, flag).text = val
    ET.SubElement(ml, "fieldConfiguration")
    ET.SubElement(ml, "vectorjoins")
    ET.SubElement(ml, "layerDependencies")
    ET.SubElement(ml, "dataDependencies")
    ET.SubElement(ml, "expressionfields")
    return ml


def _build_paletted_pipe(renderer: PalettedRenderer) -> ET.Element:
    pipe = ET.Element("pipe")
    provider_el = ET.SubElement(pipe, "provider")
    ET.SubElement(
        provider_el,
        "resampling",
        maxOversampling="2",
        enabled="false",
        zoomedInResamplingMethod="nearestNeighbour",
        zoomedOutResamplingMethod="nearestNeighbour",
    )
    r = ET.SubElement(
        pipe,
        "rasterrenderer",
        type="paletted",
        band=str(renderer.band),
        alphaBand="-1",
        opacity=str(renderer.opacity),
        nodataColor="",
    )
    ET.SubElement(r, "rasterTransparency")
    mmo = ET.SubElement(r, "minMaxOrigin")
    for tag, val in [
        ("limits", "None"),
        ("extent", "WholeRaster"),
        ("statAccuracy", "Estimated"),
        ("cumulativeCutLower", "0.02"),
        ("cumulativeCutUpper", "0.98"),
        ("stdDevFactor", "2"),
    ]:
        ET.SubElement(mmo, tag).text = val
    palette = ET.SubElement(r, "colorPalette")
    for entry in renderer.entries:
        ET.SubElement(
            palette,
            "paletteEntry",
            value=str(entry.value),
            color=entry.color,
            alpha=str(entry.alpha),
            label=entry.label,
        )
    ET.SubElement(pipe, "brightnesscontrast", gamma="1", contrast="0", brightness="0")
    ET.SubElement(
        pipe,
        "huesaturation",
        colorizeRed="255",
        colorizeGreen="128",
        invertColors="0",
        colorizeOn="0",
        grayscaleMode="0",
        saturation="0",
        colorizeStrength="100",
        colorizeBlue="128",
    )
    ET.SubElement(pipe, "rasterresampler", maxOversampling="2")
    ET.SubElement(pipe, "resamplingStage").text = "resamplingFilter"
    return pipe


def _build_raster_maplayer(layer) -> ET.Element:
    ml = ET.Element(
        "maplayer",
        type="raster",
        autoRefreshTime="0",
        autoRefreshMode="Disabled",
        styleCategories="AllStyleCategories",
        refreshOnNotifyEnabled="0",
        refreshOnNotifyMessage="",
        maxScale="0",
        minScale="100000000",
        hasScaleBasedVisibilityFlag="0",
        legendPlaceholderImage="",
    )
    ET.SubElement(ml, "id").text = layer.id
    ET.SubElement(ml, "datasource")
    ET.SubElement(ml, "layername").text = layer.name
    if layer.crs:
        ml.append(_srs_element(layer.crs))
    ET.SubElement(ml, "provider").text = layer.provider
    style_mgr = ET.SubElement(ml, "map-layer-style-manager", current="default")
    ET.SubElement(style_mgr, "map-layer-style", name="default")
    flags = ET.SubElement(ml, "flags")
    for flag, val in [
        ("Identifiable", "1"),
        ("Removable", "1"),
        ("Searchable", "1"),
        ("Private", "0"),
    ]:
        ET.SubElement(flags, flag).text = val
    nodata = ET.SubElement(ml, "noData")
    ET.SubElement(nodata, "noDataList", useSrcNoData="1", bandNo="1")
    if isinstance(layer.renderer, PalettedRenderer):
        ml.append(_build_paletted_pipe(layer.renderer))
    else:
        pipe = ET.SubElement(ml, "pipe")
        provider_el = ET.SubElement(pipe, "provider")
        ET.SubElement(
            provider_el,
            "resampling",
            maxOversampling="2",
            enabled="false",
            zoomedInResamplingMethod="nearestNeighbour",
            zoomedOutResamplingMethod="nearestNeighbour",
        )
        r = ET.SubElement(
            pipe,
            "rasterrenderer",
            type="singlebandgray",
            grayBand="1",
            alphaBand=str(layer.alpha_band) if layer.alpha_band is not None else "-1",
            opacity="1",
            gradient="BlackToWhite",
            nodataColor="",
        )
        ET.SubElement(r, "rasterTransparency")
        mmo = ET.SubElement(r, "minMaxOrigin")
        for tag, val in [
            ("limits", "MinMax"),
            ("extent", "WholeRaster"),
            ("statAccuracy", "Estimated"),
            ("cumulativeCutLower", "0.02"),
            ("cumulativeCutUpper", "0.98"),
            ("stdDevFactor", "2"),
        ]:
            ET.SubElement(mmo, tag).text = val
        ce = ET.SubElement(r, "contrastEnhancement")
        ET.SubElement(ce, "minValue").text = "0"
        ET.SubElement(ce, "maxValue").text = "1"
        ET.SubElement(ce, "algorithm").text = "StretchToMinimumMaximum"
        ET.SubElement(pipe, "brightnesscontrast", gamma="1", contrast="0", brightness="0")
        ET.SubElement(
            pipe,
            "huesaturation",
            colorizeRed="255",
            colorizeGreen="128",
            invertColors="0",
            colorizeOn="0",
            grayscaleMode="0",
            saturation="0",
            colorizeStrength="100",
            colorizeBlue="128",
        )
        ET.SubElement(pipe, "rasterresampler", maxOversampling="2")
        ET.SubElement(pipe, "resamplingStage").text = "resamplingFilter"
    ET.SubElement(ml, "blendMode").text = "0"
    return ml


def _inject_layers(root: ET.Element, spec, project_dir: Path) -> None:
    pl = root.find("projectlayers")
    if pl is None:
        pl = ET.SubElement(root, "projectlayers")

    for layer in spec.layers:
        if layer.style_xml is None:
            if layer.type == "vector" and layer.geometry_type:
                ml = _build_vector_maplayer(layer)
            elif layer.type == "raster":
                ml = _build_raster_maplayer(layer)
            else:
                continue
        else:
            xml_path = project_dir / layer.style_xml
            if not xml_path.exists():
                print(f"  warning: {xml_path} not found, skipping {layer.name!r}")
                continue
            ml = ET.parse(xml_path).getroot()
        ml.set("id", layer.id)
        id_el = ml.find("id")
        if id_el is not None:
            id_el.text = layer.id
        ds = ml.find("datasource")
        if ds is not None:
            ds.text = _abs_source(layer.source, project_dir)
        nm = ml.find("layername")
        if nm is not None:
            nm.text = layer.name
        if layer.renderer is not None and layer.type == "vector":
            old = ml.find("renderer-v2")
            new = _render_renderer(layer.renderer)
            if old is not None:
                children = list(ml)
                ml.remove(old)
                ml.insert(children.index(old), new)
            else:
                ml.append(new)
        pl.append(ml)


def render(spec, project_dir: Path) -> None:
    base_path = project_dir / "styles" / "base.qgs"
    if not base_path.exists():
        raise SystemExit(
            f"styles/base.qgs not found in {project_dir} — run 'make dump' first"
        )

    content = base_path.read_text()
    if content.startswith("<!DOCTYPE"):
        content = content[content.index(">") + 1 :].lstrip()

    root = ET.fromstring(content)

    if spec.extent:
        _update_extent(root, spec.extent)
    _update_crs(root, spec.crs)
    _update_title(root, spec.title)
    _inject_layers(root, spec, project_dir)
    _rebuild_layer_tree(root, spec)
    _rebuild_legend(root, spec)
    _rebuild_layerorder(root, spec)

    output_dir = project_dir / "output"
    output_dir.mkdir(exist_ok=True)
    out = output_dir / "project.qgs"
    out.write_text(_QGS_DOCTYPE + ET.tostring(root, encoding="unicode"))
    print(f"Wrote {out}")
