"""Entry point: render <project_dir>/project.py → <project_dir>/build/project.qgs."""

import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).parent  # qgis_map/


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _needs_rebuild(project_dir: Path) -> bool:
    project_py = project_dir / "project.py"
    state_file = project_dir / "build" / ".state"
    if not (project_dir / "build" / "project.qgs").exists():
        return True
    if not state_file.exists():
        return True
    if not project_py.exists():
        return True
    return state_file.read_text().strip() != _hash_file(project_py)


def main() -> None:
    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("Usage: python build.py <project_dir> [--force]")
        sys.exit(1)

    project_dir = (HERE / args[0]).resolve()
    project_py = project_dir / "project.py"

    if not project_py.exists():
        print(f"project.py not found in {project_dir} — run 'make dump-arp' first")
        sys.exit(1)

    if not force and not _needs_rebuild(project_dir):
        print("project.qgs is up to date")
        return

    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))

    from render import _load_spec, render

    spec = _load_spec(project_dir)
    render(spec, project_dir)

    state_file = project_dir / "build" / ".state"
    state_file.parent.mkdir(exist_ok=True)
    state_file.write_text(_hash_file(project_py))


if __name__ == "__main__":
    main()
