"""Gallery pipeline: turn source photos in PHOTOS_DIR into web-size
thumbnails and a photos.json manifest for the gallery pane."""

import json
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image, ImageOps
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry

Area = tuple[str, BaseGeometry]
PhotoRecord = dict[str, str | float | None]


def load_areas() -> list[Area]:
    """Load ARP_areas.geojson polygons as shapely geometries.

    Returns a list of (name, geometry) pairs, used to tag a photo's
    GPS point with its enclosing work area.
    """
    geojson_path: Path = Path(__file__).parent / "ARP_areas.geojson"
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
    decimal: float = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
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


def unique_filename(base: str, used_filenames: set[str]) -> str:
    """Return base, or base with a -2, -3, ... suffix if already taken.

    Guards against two photos landing on the same yyyymmdd_hhmmss.jpg
    name (eg a burst of shots within the same second).
    """
    if base not in used_filenames:
        used_filenames.add(base)
        return base

    stem, ext = base.rsplit(".", 1)
    counter = 2
    candidate = f"{stem}-{counter}.{ext}"
    while candidate in used_filenames:
        counter += 1
        candidate = f"{stem}-{counter}.{ext}"
    used_filenames.add(candidate)
    return candidate


def process_photo(
    path: Path, areas: list[Area], output_dir: Path, used_filenames: set[str]
) -> PhotoRecord | None:
    """Build one gallery record for a photo, resizing it as a side effect.

    Extracts date, location, and description from EXIF, resizes the
    image for web viewing, and writes it to output_dir under a
    yyyymmdd_hhmmss.jpg name derived from its date (see unique_filename
    for collisions). Returns None if the photo has no usable date.
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
        lat: float | None = None
        lon: float | None = None
        if gps_ifd.get(2) and gps_ifd.get(4):
            lat = dms_to_decimal(gps_ifd[2], gps_ifd.get(1, "N"))
            lon = dms_to_decimal(gps_ifd[4], gps_ifd.get(3, "E"))
            location = find_location(lon, lat, areas)

        description: str | None = read_photo_description(exif, exif_ifd)

        timestamp = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")
        base_filename = timestamp.strftime("%Y%m%d_%H%M%S") + ".jpg"
        filename = unique_filename(base_filename, used_filenames)

        image = ImageOps.exif_transpose(img)
        image.thumbnail((800, 800))
        image.save(output_dir / filename, "JPEG", quality=85)

    record: PhotoRecord = {
        "filename": filename,
        "date": date,
        "location": location,
        "lat": lat,
        "lon": lon,
        "description": description,
    }
    print(record)
    return record


def backfill_location_by_day(records: list[PhotoRecord]) -> None:
    """Fill in "Other"/missing locations from the rest of that day's photos.

    If every dated photo's confirmed (non-"Other") location on a given
    day agrees, apply that location to the day's "Other" or GPS-less
    photos too - unmatched points are often GPS drift near a work area's
    boundary, or a shot taken from the trail just outside it, not a
    genuinely different location. Ambiguous days (more than one distinct
    confirmed location) are left alone rather than guessed at.
    """
    by_day: dict[str, list[PhotoRecord]] = {}
    for record in records:
        by_day.setdefault(record["date"][:10], []).append(record)

    for day_records in by_day.values():
        known_locations = {
            record["location"]
            for record in day_records
            if record["location"] not in (None, "Other")
        }
        if len(known_locations) != 1:
            continue
        (location,) = known_locations
        for record in day_records:
            if record["location"] in (None, "Other"):
                record["location"] = location


EARTH_RADIUS_METERS = 6_371_000
CLUSTER_RADIUS_METERS = 40


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in meters."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_METERS * math.asin(math.sqrt(a))


def cluster_label(index: int) -> str:
    """Convert a 1-indexed cluster number to a letter label.

    A, B, ..., Z, AA, AB, ... - same scheme as spreadsheet columns.
    """
    label = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        label = chr(ord("A") + remainder) + label
    return label


def cluster_centroid(cluster: dict[str, Any]) -> None:
    """Recompute a cluster's centroid as the mean of its records' points."""
    cluster["lat"] = sum(r["lat"] for r in cluster["records"]) / len(cluster["records"])
    cluster["lon"] = sum(r["lon"] for r in cluster["records"]) / len(cluster["records"])


def cluster_other_photos(records: list[PhotoRecord]) -> None:
    """Group "Other" photos into "Area X" locations, in two passes.

    First, every day's "Other" photos become one cluster - one off-map
    stop is one session, even if GPS wanders a bit within it. Second,
    any two clusters whose centroids are within CLUSTER_RADIUS_METERS
    are merged, repeated until no pair overlaps - so multiple days at
    the same off-map spot end up in one cluster, including transitively
    (A overlaps B, B overlaps C -> A, B, and C all merge, even if A and
    C alone wouldn't have). Mutates each matched record's "location" in
    place (eg "Area A"), so unmapped GPS points still get a map
    marker instead of disappearing into an undifferentiated "Other"
    bucket.
    """
    by_day: dict[str, list[PhotoRecord]] = {}
    for record in records:
        if record["location"] != "Other":
            continue
        by_day.setdefault(record["date"][:10], []).append(record)

    # Pass 1: one cluster per day.
    clusters: list[dict[str, Any]] = []
    for day_records in by_day.values():
        cluster = {"records": list(day_records)}
        cluster_centroid(cluster)
        clusters.append(cluster)

    # Pass 2: merge overlapping clusters until none remain.
    merged_any = True
    while merged_any:
        merged_any = False
        for i, cluster_a in enumerate(clusters):
            for cluster_b in clusters[i + 1 :]:
                if (
                    haversine_meters(
                        cluster_a["lat"],
                        cluster_a["lon"],
                        cluster_b["lat"],
                        cluster_b["lon"],
                    )
                    <= CLUSTER_RADIUS_METERS
                ):
                    cluster_a["records"].extend(cluster_b["records"])
                    cluster_centroid(cluster_a)
                    clusters.remove(cluster_b)
                    merged_any = True
                    break
            if merged_any:
                break

    for index, cluster in enumerate(clusters, start=1):
        for record in cluster["records"]:
            record["location"] = f"Area {cluster_label(index)}"


def build_gallery() -> None:
    """Regenerate the gallery from every photo under PHOTOS_DIR.

    Writes resized thumbnails to photos/ and a manifest (date,
    location tag, description) to photos.json, from scratch on every
    run.
    """
    photos_dir: Path = Path(os.environ["PHOTOS_DIR"])
    project_dir: Path = Path(__file__).parent
    output_dir: Path = project_dir / "photos"
    output_dir.mkdir(parents=True, exist_ok=True)

    areas: list[Area] = load_areas()
    paths: list[Path] = sorted(
        p
        for p in photos_dir.rglob("*")
        if p.suffix.lower() in (".jpg", ".jpeg") and output_dir not in p.parents
    )

    records: list[PhotoRecord] = []
    used_filenames: set[str] = set()
    for path in paths:
        record = process_photo(path, areas, output_dir, used_filenames)
        if record is not None:
            records.append(record)

    backfill_location_by_day(records)
    cluster_other_photos(records)

    # Newest day first overall, but oldest-to-newest within a day: sort
    # ascending by full timestamp first, then stable-sort by day
    # descending - the stable sort preserves the ascending order already
    # established within each day's group.
    records.sort(key=lambda r: r["date"])
    records.sort(key=lambda r: r["date"][:10], reverse=True)

    manifest_path: Path = project_dir / "photos.json"
    with open(manifest_path, "w") as f:
        json.dump(records, f, indent=2)

    print(f"wrote {len(records)} photos to {manifest_path}")


if __name__ == "__main__":
    build_gallery()
