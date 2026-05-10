"""Entry point: render <project_dir>/project.py → <project_dir>/output/project.qgs."""

import hashlib
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent  # qgis_map/


def _source_hash(project_dir: Path) -> str:
    h = hashlib.sha256()
    project_py = project_dir / "project.py"
    if project_py.exists():
        h.update(project_py.read_bytes())
    layers_dir = project_dir / "layers"
    if layers_dir.exists():
        for f in sorted(layers_dir.glob("*.py")):
            h.update(f.read_bytes())
    return h.hexdigest()


def _needs_rebuild(project_dir: Path) -> bool:
    output_dir = project_dir / "output"
    if not (output_dir / "project.qgs").exists():
        return True
    state_file = output_dir / ".state"
    if not state_file.exists():
        return True
    return state_file.read_text().strip() != _source_hash(project_dir)


def main() -> None:
    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("Usage: python build.py <project_dir> [--force]")
        sys.exit(1)

    project_dir = (HERE / args[0]).resolve()
    project_py = project_dir / "project.py"

    if not project_py.exists():
        print(f"project.py not found in {project_dir} — run 'make dump' first")
        sys.exit(1)

    if not force and not _needs_rebuild(project_dir):
        print("project.qgs is up to date")
        return

    fmt_targets = [str(project_py)]
    layers_dir = project_dir / "layers"
    if layers_dir.exists():
        fmt_targets += [str(layers_dir)]
    subprocess.run(["uv", "run", "black"] + fmt_targets, check=True)

    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))

    from render import _load_spec, render

    spec = _load_spec(project_dir)
    render(spec, project_dir)

    output_dir = project_dir / "output"
    output_dir.mkdir(exist_ok=True)
    (output_dir / ".state").write_text(_source_hash(project_dir))


if __name__ == "__main__":
    main()
