"""Parse a .qgz file into project.py, project.json, and styles/*.xml."""

from __future__ import annotations

import copy
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from src.models import LayerSpec, ProjectSpec

HERE = Path(__file__).parent.parent  # qgis_map/
STYLES = HERE / "styles"

_PROVIDER_MAP = {
    "ogr": "ogr",
    "gdal": "gdal",
    "wms": "wms",
    "memory": "memory",
    "postgres": "postgres",
}


def _authid(el: ET.Element | None) -> str | None:
    if el is None:
        return None
    return el.findtext(".//authid") or None


def _resolve_source(raw: str, base_dir: Path) -> str:
    """Resolve datasource paths relative to the .qgz location."""
    if raw.startswith("./") or raw.startswith("../"):
        geom_suffix = ""
        path_part = raw
        if "|" in raw:
            path_part, geom_suffix = raw.split("|", 1)
            geom_suffix = "|" + geom_suffix
        resolved = str((base_dir / path_part).resolve()) + geom_suffix
        return resolved
    return raw


def _layer_type(ml: ET.Element) -> str:
    t = ml.get("type", "vector")
    return t if t in ("vector", "raster") else "vector"


def _build_spec(root: ET.Element, qgz_dir: Path) -> ProjectSpec:
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
                except TypeError, ValueError:
                    pass
            break

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
        ml.findtext("id"): ml for ml in root.findall(".//maplayer") if ml.findtext("id")
    }

    STYLES.mkdir(exist_ok=True)
    layers: list[LayerSpec] = []

    for lid in tree_order:
        ml = maplayers.get(lid)
        if ml is None:
            continue

        style_path = STYLES / f"{lid}.xml"
        style_path.write_text(ET.tostring(ml, encoding="unicode"))

        src_raw = ml.findtext("datasource") or ""
        source = _resolve_source(src_raw, qgz_dir)
        provider = ml.findtext("provider") or "ogr"
        crs = _authid(ml.find(".//srs/spatialrefsys"))

        layers.append(
            LayerSpec(
                id=lid,
                name=ml.findtext("layername") or lid,
                type=_layer_type(ml),
                source=source,
                provider=provider,
                crs=crs,
                visible=visibility.get(lid, True),
                style_xml=Path(f"styles/{lid}.xml"),
            )
        )

    return ProjectSpec(
        title=title,
        crs=project_crs,
        extent=extent,
        layers=layers,
    )


def _save_base_qgs(root: ET.Element, path: Path) -> None:
    """Save QGS template with layer sections cleared for render.py to repopulate."""
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

    xml_str = ET.tostring(base, encoding="unicode")
    path.write_text(
        "<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>\n" + xml_str
    )


def _write_project_py(spec: ProjectSpec) -> None:
    lines = [
        "from pathlib import Path",
        "",
        "from src.models import LayerSpec, ProjectSpec",
        "",
        "spec = ProjectSpec(",
        f"    title={spec.title!r},",
        f"    crs={spec.crs!r},",
        f"    extent={spec.extent!r},",
        "    layers=[",
    ]
    for layer in spec.layers:
        style = f"Path({str(layer.style_xml)!r})" if layer.style_xml else "None"
        lines += [
            "        LayerSpec(",
            f"            id={layer.id!r},",
            f"            name={layer.name!r},",
            f"            type={layer.type!r},",
            f"            source={layer.source!r},",
            f"            provider={layer.provider!r},",
            f"            crs={layer.crs!r},",
            f"            visible={layer.visible!r},",
            f"            style_xml={style},",
            "        ),",
        ]
    lines += ["    ],", ")", ""]
    (HERE / "project.py").write_text("\n".join(lines))


def dump(qgz_path: Path) -> None:
    qgz_path = qgz_path.resolve()
    qgz_dir = qgz_path.parent

    with zipfile.ZipFile(qgz_path) as z:
        qgs_names = [n for n in z.namelist() if n.endswith(".qgs")]
        if not qgs_names:
            raise SystemExit(f"No .qgs file found in {qgz_path}")
        xml_bytes = z.read(qgs_names[0])

    root = ET.fromstring(xml_bytes)
    spec = _build_spec(root, qgz_dir)

    _save_base_qgs(root, STYLES / "base.qgs")
    print(f"Wrote {STYLES / 'base.qgs'}")

    _write_project_py(spec)
    print(f"Wrote {HERE / 'project.py'}")

    (HERE / "project.json").write_text(spec.model_dump_json(indent=2))
    print(f"Wrote {HERE / 'project.json'}")

    for layer in spec.layers:
        print(f"  [{layer.type}] {layer.name!r} → styles/{layer.id}.xml")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.dump <path/to/file.qgz>")
        sys.exit(1)
    dump(Path(sys.argv[1]))
