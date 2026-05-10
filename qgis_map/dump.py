"""Parse a .qgz file into layers/*.py and styles/*.xml."""

from __future__ import annotations

import copy
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from models import (
    Layer,
    Project,
    Renderer,
    Rule,
    RuleRenderer,
    SimpleFill,
    SimpleLine,
    SimpleMarker,
    SingleSymbol,
    SvgMarker,
    Symbol,
    SymbolLayer,
)

HERE = Path(__file__).parent  # qgis_map/

_LAYER_IMPORTS = (
    "Layer, Rule, RuleRenderer, SimpleFill,"
    " SimpleLine, SimpleMarker, SingleSymbol, SvgMarker, Symbol"
)

# ── XML helpers ───────────────────────────────────────────────────────────────


def _authid(el: ET.Element | None) -> str | None:
    if el is None:
        return None
    return el.findtext(".//authid") or None


def _resolve_source(raw: str, base_dir: Path) -> str:
    """Return source relative to HERE; leave URIs and absolute paths as-is."""
    if not (raw.startswith("./") or raw.startswith("../")):
        return raw
    geom_suffix = ""
    path_part = raw
    if "|" in raw:
        path_part, geom_suffix = raw.split("|", 1)
        geom_suffix = "|" + geom_suffix
    abs_path = (base_dir / path_part).resolve()
    return os.path.relpath(abs_path, HERE.resolve()) + geom_suffix


def _layer_type(ml: ET.Element) -> str:
    t = ml.get("type", "vector")
    return t if t in ("vector", "raster") else "vector"


# ── Human ID generation ───────────────────────────────────────────────────────

_GEOM_SUFFIXES = {
    "Point": "_points",
    "MultiPoint": "_points",
    "LineString": "_lines",
    "MultiLineString": "_lines",
    "Polygon": "_polygons",
    "MultiPolygon": "_polygons",
}


def _human_id(layer_name: str, source: str, used: set[str]) -> str:
    """Derive a human-friendly layer ID from source path and layer name."""
    geom_suffix = ""
    path_part = source
    if "|" in source:
        path_part, geom_part = source.split("|", 1)
        params = dict(p.split("=", 1) for p in geom_part.split("&") if "=" in p)
        geom_suffix = _GEOM_SUFFIXES.get(params.get("geometrytype", ""), "")

    if path_part.startswith("../") or path_part.startswith("./"):
        stem = Path(path_part).stem
        base = re.sub(r"[^a-z0-9]+", "_", stem.lower()).strip("_")
    else:
        base = re.sub(r"[^a-z0-9]+", "_", layer_name.lower()).strip("_")

    candidate = base + geom_suffix
    if candidate not in used:
        return candidate
    i = 2
    while f"{candidate}_{i}" in used:
        i += 1
    return f"{candidate}_{i}"


# ── Style parsing ─────────────────────────────────────────────────────────────


def _opts(el: ET.Element) -> dict[str, str]:
    result = {}
    for opt in el.findall("Option"):
        name = opt.get("name")
        value = opt.get("value")
        if name and value is not None:
            result[name] = value
    return result


def _parse_symbol_layer(layer_el: ET.Element) -> SymbolLayer | None:
    kind = layer_el.get("class")
    opts_el = layer_el.find("Option[@type='Map']")
    if opts_el is None:
        return None
    o = _opts(opts_el)

    if kind == "SimpleFill":
        return SimpleFill(
            color=o.get("color", "0,0,0,255"),
            style=o.get("style", "solid"),
            outline_color=o.get("outline_color", "35,35,35,255"),
            outline_style=o.get("outline_style", "solid"),
            outline_width=float(o.get("outline_width", "0.5")),
            outline_width_unit=o.get("outline_width_unit", "MM"),
            joinstyle=o.get("joinstyle", "bevel"),
            offset=o.get("offset", "0,0"),
        )
    if kind == "SimpleLine":
        return SimpleLine(
            line_color=o.get("line_color", "0,0,0,255"),
            line_style=o.get("line_style", "solid"),
            line_width=float(o.get("line_width", "0.5")),
            line_width_unit=o.get("line_width_unit", "MM"),
            capstyle=o.get("capstyle", "square"),
            joinstyle=o.get("joinstyle", "bevel"),
            offset=o.get("offset", "0"),
        )
    if kind == "SvgMarker":
        return SvgMarker(
            name=o.get("name", ""),
            size=float(o.get("size", "6")),
            size_unit=o.get("size_unit", "MM"),
            color=o.get("color", "0,0,0,255"),
            outline_color=o.get("outline_color", "35,35,35,255"),
            outline_width=float(o.get("outline_width", "0")),
            outline_width_unit=o.get("outline_width_unit", "MM"),
            angle=float(o.get("angle", "0")),
            offset=o.get("offset", "0,0"),
            offset_unit=o.get("offset_unit", "MM"),
        )
    if kind == "SimpleMarker":
        return SimpleMarker(
            name=o.get("name", "circle"),
            size=float(o.get("size", "2")),
            size_unit=o.get("size_unit", "MM"),
            color=o.get("color", "0,0,0,255"),
            outline_color=o.get("outline_color", "35,35,35,255"),
            outline_width=float(o.get("outline_width", "0")),
            outline_width_unit=o.get("outline_width_unit", "MM"),
            angle=float(o.get("angle", "0")),
            offset=o.get("offset", "0,0"),
            offset_unit=o.get("offset_unit", "MM"),
            joinstyle=o.get("joinstyle", "bevel"),
        )
    return None


def _parse_symbol(sym_el: ET.Element) -> Symbol | None:
    sym_type = sym_el.get("type")
    if sym_type not in ("fill", "line", "marker"):
        return None
    alpha = float(sym_el.get("alpha", "1"))
    layers = [
        sl
        for layer_el in sym_el.findall("layer")
        if (sl := _parse_symbol_layer(layer_el)) is not None
    ]
    if not layers:
        return None
    return Symbol(type=sym_type, alpha=alpha, layers=layers)


def _parse_renderer(ml: ET.Element) -> Renderer | None:
    renderer_el = ml.find("renderer-v2")
    if renderer_el is None:
        return None
    rtype = renderer_el.get("type")

    if rtype == "singleSymbol":
        symbols_el = renderer_el.find("symbols")
        if symbols_el is None:
            return None
        sym_el = symbols_el.find("symbol")
        if sym_el is None:
            return None
        sym = _parse_symbol(sym_el)
        return SingleSymbol(symbol=sym) if sym else None

    if rtype == "RuleRenderer":
        rules_el = renderer_el.find("rules")
        if rules_el is None:
            return None
        rules = [
            Rule(
                key=r.get("key", ""),
                label=r.get("label", ""),
                filter=r.get("filter", ""),
                symbol_index=int(r.get("symbol", "0")),
                active=r.get("checkstate", "1") != "0",
            )
            for r in rules_el.findall("rule")
            if r.get("symbol") is not None
        ]
        symbols_el = renderer_el.find("symbols")
        symbols = []
        if symbols_el is not None:
            for sym_el in sorted(
                symbols_el.findall("symbol"),
                key=lambda e: int(e.get("name", "0")),
            ):
                sym = _parse_symbol(sym_el)
                if sym:
                    symbols.append(sym)
        return RuleRenderer(
            rules_key=rules_el.get("key", ""),
            rules=rules,
            symbols=symbols,
        )

    return None


# ── Code generation ───────────────────────────────────────────────────────────


def _py_repr(val: Any) -> str:
    """Recursively generate a Python constructor expression for a value."""
    if isinstance(val, BaseModel):
        cls = type(val).__name__
        pairs = []
        for name, field_info in type(val).model_fields.items():
            if name == "kind":
                continue
            v = getattr(val, name)
            if v == field_info.default:
                continue
            pairs.append(f"{name}={_py_repr(v)}")
        return f"{cls}({', '.join(pairs)})"
    if isinstance(val, list):
        return f"[{', '.join(_py_repr(i) for i in val)}]"
    if isinstance(val, dict):
        items = ", ".join(f"{_py_repr(k)}: {_py_repr(v)}" for k, v in val.items())
        return f"{{{items}}}"
    if isinstance(val, Path):
        return f"Path({str(val)!r})"
    return repr(val)


def _write_layer_py(layer: Layer, layers_dir: Path, skip_existing: bool = True) -> bool:
    """Write layers/{layer.id}.py. Returns True if written, False if skipped."""
    out_path = layers_dir / f"{layer.id}.py"
    if skip_existing and out_path.exists():
        return False

    lines = [
        "from pathlib import Path",
        "",
        f"from models import {_LAYER_IMPORTS}",
        "",
    ]

    renderer_var = None
    if isinstance(layer.renderer, RuleRenderer):
        renderer_var = "_renderer"
        lines += [f"_renderer = {_py_repr(layer.renderer)}", ""]

    style = f"Path({str(layer.style_xml)!r})" if layer.style_xml else "None"
    layer_lines = [
        f"{layer.id} = Layer(",
        f"    id={layer.id!r},",
        f"    name={layer.name!r},",
        f"    type={layer.type!r},",
        f"    source={layer.source!r},",
        f"    provider={layer.provider!r},",
        f"    crs={layer.crs!r},",
        f"    visible={layer.visible!r},",
        f"    style_xml={style},",
    ]
    if layer.renderer is not None:
        renderer_repr = renderer_var if renderer_var else _py_repr(layer.renderer)
        layer_lines.append(f"    renderer={renderer_repr},")
    layer_lines.append(")")
    lines += layer_lines + [""]

    out_path.write_text("\n".join(lines))
    return True


def _write_project_py(spec: Project, human_ids: list[str], project_dir: Path) -> None:
    """Write slim project.py that imports from layers/ and assembles Project."""
    import_lines = [f"from layers.{hid} import {hid}" for hid in human_ids]
    lines = [
        "from pathlib import Path",
        "",
        "from models import Project",
        "",
        *import_lines,
        "",
        "spec = Project(",
        f"    title={spec.title!r},",
        f"    crs={spec.crs!r},",
        f"    extent={spec.extent!r},",
        "    layers=[",
        *[f"        {hid}," for hid in human_ids],
        "    ],",
        ")",
        "",
    ]
    (project_dir / "project.py").write_text("\n".join(lines))


# ── Main ──────────────────────────────────────────────────────────────────────


def _parse_layers(
    root: ET.Element, qgz_dir: Path, project_dir: Path
) -> list[tuple[str, Layer]]:
    """Parse maplayers in tree order, write style XMLs, return (hid, Layer) pairs."""
    visibility: dict[str, bool] = {
        ltl.get("id", ""): ltl.get("checked") == "Qt::Checked"
        for ltl in root.findall(".//layer-tree-layer")
    }
    tree_order: list[str] = [
        ltl.get("id", "")
        for ltl in root.findall(".//layer-tree-layer")
        if ltl.get("id")
    ]
    maplayers: dict[str, ET.Element] = {
        ml.findtext("id"): ml
        for ml in root.findall(".//maplayer")
        if ml.findtext("id")
    }

    styles_dir = project_dir / "styles"
    styles_dir.mkdir(parents=True, exist_ok=True)

    used_ids: set[str] = set()
    pairs: list[tuple[str, Layer]] = []

    for lid in tree_order:
        ml = maplayers.get(lid)
        if ml is None:
            continue

        src_raw = ml.findtext("datasource") or ""
        source = _resolve_source(src_raw, qgz_dir)
        provider = ml.findtext("provider") or "ogr"
        crs = _authid(ml.find(".//srs/spatialrefsys"))
        layer_name = ml.findtext("layername") or lid

        hid = _human_id(layer_name, source, used_ids)
        used_ids.add(hid)

        style_path = styles_dir / f"{hid}.xml"
        style_path.write_text(ET.tostring(ml, encoding="unicode"))

        pairs.append((
            hid,
            Layer(
                id=hid,
                name=layer_name,
                type=_layer_type(ml),
                source=source,
                provider=provider,
                crs=crs,
                visible=visibility.get(lid, True),
                style_xml=Path(f"styles/{hid}.xml"),
                renderer=_parse_renderer(ml),
            ),
        ))

    return pairs


def _save_base_qgs(root: ET.Element, path: Path) -> None:
    base = copy.deepcopy(root)

    pl = base.find("projectlayers")
    if pl is not None:
        for child in list(pl):
            pl.remove(child)

    ltg = base.find("layer-tree-group")
    if ltg is not None:
        for child in list(ltg):
            if child.tag in ("layer-tree-layer", "custom-order"):
                ltg.remove(child)

    legend = base.find("legend")
    if legend is not None:
        for child in list(legend):
            if child.tag == "legendlayer":
                legend.remove(child)

    lo = base.find("layerorder")
    if lo is not None:
        for child in list(lo):
            lo.remove(child)

    path.write_text(
        "<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>\n"
        + ET.tostring(base, encoding="unicode")
    )


def dump(qgz_path: Path, project_dir: Path, force_layer: str | None = None) -> None:
    qgz_path = qgz_path.resolve()
    project_dir = project_dir.resolve()
    qgz_dir = qgz_path.parent

    with zipfile.ZipFile(qgz_path) as z:
        qgs_names = [n for n in z.namelist() if n.endswith(".qgs")]
        if not qgs_names:
            raise SystemExit(f"No .qgs file found in {qgz_path}")
        xml_bytes = z.read(qgs_names[0])

    root = ET.fromstring(xml_bytes)
    pairs = _parse_layers(root, qgz_dir, project_dir)

    _save_base_qgs(root, project_dir / "styles" / "base.qgs")
    print(f"Wrote {project_dir / 'styles' / 'base.qgs'}")

    layers_dir = project_dir / "layers"
    layers_dir.mkdir(exist_ok=True)

    human_ids = [hid for hid, _ in pairs]
    for hid, layer in pairs:
        skip = force_layer != hid
        written = _write_layer_py(layer, layers_dir, skip_existing=skip)
        action = "wrote" if written else "skipped (exists; use --force to overwrite)"
        renderer_tag = f" [{type(layer.renderer).__name__}]" if layer.renderer else ""
        print(f"  [{layer.type}] {layer.name!r}{renderer_tag} → {hid}: {action}")

    title = root.findtext("title") or ""
    project_crs = _authid(root.find("projectCrs/spatialrefsys")) or ""
    extent: tuple[float, float, float, float] | None = None
    for canvas in root.findall("mapcanvas"):
        if canvas.get("name") == "theMapCanvas":
            ext = canvas.find("extent")
            if ext is not None:
                try:
                    extent = (
                        float(ext.findtext("xmin")),
                        float(ext.findtext("ymin")),
                        float(ext.findtext("xmax")),
                        float(ext.findtext("ymax")),
                    )
                except (TypeError, ValueError):
                    pass
            break

    spec = Project(
        title=title,
        crs=project_crs,
        extent=extent,
        layers=[layer for _, layer in pairs],
    )
    _write_project_py(spec, human_ids, project_dir)
    print(f"Wrote {project_dir / 'project.py'}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python dump.py <path/to/file.qgz> <project_dir> [--force LAYER_ID]")
        sys.exit(1)
    force = None
    args = list(sys.argv[1:])
    if "--force" in args:
        idx = args.index("--force")
        force = args[idx + 1] if idx + 1 < len(args) else None
        args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]
    dump(Path(args[0]), Path(args[1]), force_layer=force)
