"""Render project.py → build/project.qgs."""

from __future__ import annotations

import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).parent.parent  # qgis_map/
BUILD = HERE / "build"
STYLES = HERE / "styles"

_QGS_DOCTYPE = "<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>\n"


def _load_spec():
    spec_path = HERE / "project.py"
    if not spec_path.exists():
        raise SystemExit("project.py not found — run 'make dump SRC=...' first")
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


def _inject_layers(root: ET.Element, spec) -> None:
    pl = root.find("projectlayers")
    if pl is None:
        pl = ET.SubElement(root, "projectlayers")

    for layer in spec.layers:
        if layer.style_xml is None:
            continue
        xml_path = HERE / layer.style_xml
        if not xml_path.exists():
            print(f"  warning: {xml_path} not found, skipping {layer.name!r}")
            continue
        ml = ET.parse(xml_path).getroot()
        ds = ml.find("datasource")
        if ds is not None:
            ds.text = layer.source
        nm = ml.find("layername")
        if nm is not None:
            nm.text = layer.name
        pl.append(ml)


def render(spec) -> None:
    base_path = STYLES / "base.qgs"
    if not base_path.exists():
        raise SystemExit("styles/base.qgs not found — run 'make dump SRC=...' first")

    content = base_path.read_text()
    # Strip DOCTYPE before parsing (ET doesn't handle it)
    if content.startswith("<!DOCTYPE"):
        content = content[content.index(">") + 1 :].lstrip()

    root = ET.fromstring(content)

    if spec.extent:
        _update_extent(root, spec.extent)
    _update_crs(root, spec.crs)
    _update_title(root, spec.title)
    _inject_layers(root, spec)
    _rebuild_layer_tree(root, spec)
    _rebuild_legend(root, spec)
    _rebuild_layerorder(root, spec)

    BUILD.mkdir(exist_ok=True)
    out = BUILD / "project.qgs"
    out.write_text(_QGS_DOCTYPE + ET.tostring(root, encoding="unicode"))
    print(f"Wrote {out}")
