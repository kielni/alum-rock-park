"""Gallery pipeline: turn source photos in PHOTOS_DIR into web-size
thumbnails and a photos.json manifest for the gallery pane."""

import json
import os
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image, ImageOps
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry

Area = tuple[str, BaseGeometry]


def load_areas() -> list[Area]:
    """Load ARP_areas.geojson polygons as shapely geometries.

    Returns a list of (name, geometry) pairs, used to tag a photo's
    GPS point with its enclosing work area.
    """
    geojson_path: Path = Path(__file__).parent.parent / "ARP_areas.geojson"
    with open(geojson_path) as f:
        data: dict[str, Any] = json.load(f)

    areas: list[Area] = []
    for feature in data["features"]:
        name: str = feature["properties"]["name"]
        geometry: BaseGeometry = shape(feature["geometry"])
        areas.append((name, geometry))
    return areas


def find_location(lon: float, lat: float, areas: list[Area]) -> str:
    """Return the name of the enclosing work-area polygon for a point.

    Returns "Other" if the point falls outside every known polygon.
    """
    point = Point(lon, lat)
    for name, geometry in areas:
        if geometry.contains(point):
            return name
    return "Other"


def dms_to_decimal(dms: tuple[float, float, float], ref: str) -> float:
    """Convert an EXIF GPS coordinate to decimal degrees.

    Takes a (degrees, minutes, seconds) tuple and a reference ("N",
    "S", "E", or "W"), negating the result for South/West references.
    """
    degrees, minutes, seconds = dms
    decimal: float = degrees + minutes / 60 + seconds / 3600
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal


def read_photo_description(exif: Image.Exif, exif_ifd: dict[int, Any]) -> str | None:
    """Return a photo's caption from its EXIF tags, if any.

    Checks ImageDescription first, then UserComment. Returns None if
    neither tag is present or non-empty.
    """
    description: str | None = exif.get(270)  # ImageDescription
    if description and description.strip():
        return description.strip()

    user_comment: bytes | str | None = exif_ifd.get(37510)  # UserComment
    if isinstance(user_comment, bytes):
        # Strip the 8-byte character-code prefix (eg b"ASCII\0\0\0")
        # before decoding.
        user_comment = user_comment[8:].decode("utf-8", errors="ignore")
    if user_comment and user_comment.strip():
        return user_comment.strip()

    return None


def process_photo(
    path: Path, areas: list[Area], output_dir: Path
) -> dict[str, str | None] | None:
    """Build one gallery record for a photo, resizing it as a side effect.

    Extracts date, location, and description from EXIF, resizes the
    image for web viewing, and writes it to output_dir. Returns None
    if the photo has no usable date.
    """
    with Image.open(path) as img:
        exif: Image.Exif = img.getexif()
        exif_ifd: dict[int, Any] = exif.get_ifd(ExifTags.IFD.Exif)
        gps_ifd: dict[int, Any] = exif.get_ifd(ExifTags.IFD.GPSInfo)

        date: str | None = exif_ifd.get(36867) or exif.get(306)  # DateTimeOriginal
        if not date:
            print(f"skipping {path.name}: no date in EXIF")
            return None
        date = date.replace(":", "-", 2).replace(" ", "T")

        location: str | None = None
        if gps_ifd.get(2) and gps_ifd.get(4):
            lat: float = dms_to_decimal(gps_ifd[2], gps_ifd.get(1, "N"))
            lon: float = dms_to_decimal(gps_ifd[4], gps_ifd.get(3, "E"))
            location = find_location(lon, lat, areas)

        description: str | None = read_photo_description(exif, exif_ifd)

        image = ImageOps.exif_transpose(img)
        image.thumbnail((800, 800))
        image.save(output_dir / path.name, "JPEG", quality=85)

    record =  {
        "filename": path.name,
        "date": date,
        "location": location,
        "description": description,
    }
    print(record)
    return record


def build_gallery() -> None:
    """Regenerate the gallery from every photo under PHOTOS_DIR.

    Writes resized thumbnails to gallery/output/pictures and a manifest
    (date, location tag, description) to gallery/output/photos.json, from
    scratch on every run.
    """
    photos_dir: Path = Path(os.environ["PHOTOS_DIR"])
    gallery_dir: Path = Path(__file__).parent / "output"
    output_dir: Path = gallery_dir / "pictures"
    output_dir.mkdir(parents=True, exist_ok=True)

    areas: list[Area] = load_areas()
    paths: list[Path] = sorted(
        p
        for p in photos_dir.rglob("*")
        if p.suffix.lower() in (".jpg", ".jpeg") and output_dir not in p.parents
    )

    records: list[dict[str, str | None]] = []
    for path in paths:
        record = process_photo(path, areas, output_dir)
        if record is not None:
            records.append(record)

    records.sort(key=lambda r: r["date"], reverse=True)

    manifest_path: Path = gallery_dir / "photos.json"
    with open(manifest_path, "w") as f:
        json.dump(records, f, indent=2)

    print(f"wrote {len(records)} photos to {manifest_path}")


if __name__ == "__main__":
    build_gallery()
