"""Entry point: render project.py → build/project.qgs with incremental rebuild."""

import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).parent
STATE_FILE = HERE / "build" / ".state"
PROJECT_PY = HERE / "project.py"


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _needs_rebuild() -> bool:
    if not (HERE / "build" / "project.qgs").exists():
        return True
    if not STATE_FILE.exists():
        return True
    if not PROJECT_PY.exists():
        return True
    return STATE_FILE.read_text().strip() != _hash_file(PROJECT_PY)


def main() -> None:
    force = "--force" in sys.argv

    if not PROJECT_PY.exists():
        print("project.py not found — run 'make dump SRC=...' first")
        sys.exit(1)

    if not force and not _needs_rebuild():
        print("project.qgs is up to date")
        return

    # Add qgis_map/ to sys.path so `from src.models import ...` works
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))

    from src.render import _load_spec, render

    spec = _load_spec()
    render(spec)

    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(_hash_file(PROJECT_PY))


if __name__ == "__main__":
    main()
