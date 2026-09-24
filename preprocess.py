"""Gallery pipeline: turn source photos in PHOTOS_DIR into web-size
thumbnails and a photos.json manifest for the gallery pane."""

import json
import math
import os
from datetime import date, datetime
from pathlib import Path
import re
from typing import Any, Self

from PIL import ExifTags, Image, ImageOps
from pydantic import BaseModel, field_validator, model_validator
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry

Area = tuple[str, BaseGeometry]

EXIF_DATE_FORMAT: str = "%Y:%m:%d %H:%M:%S"
EXIF_DATE_PATTERN: re.Pattern[str] = re.compile(r"^\d{4}:\d{2}:\d{2} ")


class PhotoRecord(BaseModel):
    """One photo and its metadata.

    Sample record:

        {
          "filename": "20260622_113323.jpg",
          "original_filename": "IMG_1234.jpeg",
          "dt": "2026-06-22T11:33:23",
          "location": "June 22",
          "lat": 37.39535333333333,
          "lon": -121.82527166666667,
          "description": null
        }

    Field order matches the JSON key order, since that's the order
    model_dump() writes them in. filename is derived from dt when not
    given (see set_filename).
    """

    filename: str = ""
    original_filename: str | None = None
    dt: datetime
    location: str | None = None
    lat: float | None = None
    lon: float | None = None
    description: str | None = None

    @field_validator("dt", mode="before")
    @classmethod
    def parse_exif_date(cls, value: str | datetime) -> datetime:
        """Accept EXIF-format dates (2026:06:22 11:33:23) as well as ISO."""
        if isinstance(value, datetime):
            return value
        if EXIF_DATE_PATTERN.match(value):
            return datetime.strptime(value, EXIF_DATE_FORMAT)
        return datetime.fromisoformat(value)

    @model_validator(mode="after")
    def set_filename(self) -> Self:
        """Default filename to a yyyymmdd_hhmmss.jpg name from dt."""
        if not self.filename:
            self.filename = self.dt.strftime("%Y%m%d_%H%M%S") + ".jpg"
        return self

    @property
    def day(self) -> date:
        """The calendar day the photo was taken."""
        return self.dt.date()


def load_areas() -> list[Area]:
    """Load ARP_areas.geojson polygons as shapely geometries.

    Returns a list of (name, geometry) pairs, used to tag a photo's
    GPS point with its enclosing work area.
    """
    geojson = Path(os.environ["PROJECT_DIR"]) / "web" / "ARP_areas.geojson"
    print(f"loading {geojson}")
    with open(geojson) as f:
        data: dict[str, Any] = json.load(f)

    areas: list[Area] = []
    for feature in data["features"]:
        name: str = feature["properties"]["name"]
        geometry: BaseGeometry = shape(feature["geometry"])
        areas.append((name, geometry))
    return areas


def in_location(lon: float, lat: float, areas: list[Area]) -> str | None:
    """Return the name of the enclosing work-area polygon for a point.

    Returns None if the point falls outside every known polygon.
    """
    point = Point(lon, lat)
    for name, geometry in areas:
        if geometry.contains(point):
            return name
    return None


def nearby_location(lon: float, lat: float, areas: list[Area]) -> str | None:
    """Return the work area that most overlaps a circle around a point.

    Draws a NEARBY_RADIUS_DEGREES circle around the point and picks
    the area with the largest overlap.
    Returns None if the circle overlaps no area.
    """
    # about ~111m north-south and ~89m east-west at 37°N
    circle: BaseGeometry = Point(lon, lat).buffer(0.001)
    best_name: str | None = None
    best_overlap: float = 0.0
    for name, geometry in areas:
        overlap: float = circle.intersection(geometry).area
        if overlap > best_overlap:
            best_name, best_overlap = name, overlap
    return best_name


def find_location(lon: float, lat: float, areas: list[Area]) -> str:
    """Return the work area for a point, falling back to nearby areas.

    Uses the enclosing polygon if there is one, otherwise the area that
    most overlaps a NEARBY_RADIUS_DEGREES circle around the point.
    Returns "Other" if neither matches.
    """
    loc = in_location(lon, lat, areas)
    if loc:
        return loc
    return nearby_location(lon, lat, areas) or "Other"


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


def process_photo(
    path: Path, areas: list[Area], output_dir: Path, processed: set[str]
) -> PhotoRecord | None:
    """Build one gallery record for a photo, resizing it as a side effect.

    Extracts date, location, and description from EXIF, and resizes the
    image for web viewing and writes it to output_dir under a
    yyyymmdd_hhmmss.jpg name derived from its datetime - unless that name
    is already present in output_dir, in which case the existing
    thumbnail is left alone. Returns None without opening the image if
    path's name is in processed (ie already in photos.json), or if the
    photo has no usable datetime.
    """
    if path.name in processed:
        print(f"skipping {path.name}: already processed")
        return None

    with Image.open(path) as img:
        exif: Image.Exif = img.getexif()
        exif_ifd: dict[int, Any] = exif.get_ifd(ExifTags.IFD.Exif)
        gps_ifd: dict[int, Any] = exif.get_ifd(ExifTags.IFD.GPSInfo)

        dt: str | None = exif_ifd.get(36867) or exif.get(306)  # DateTimeOriginal
        if not dt:
            print(f"skipping {path.name}: no date in EXIF")
            return None
        record = PhotoRecord(
            original_filename=path.name,
            dt=dt,
            description=read_photo_description(exif, exif_ifd),
        )
        print(f"{path}\t{record.filename}")

        if gps_ifd.get(2) and gps_ifd.get(4):
            record.lat = dms_to_decimal(gps_ifd[2], gps_ifd.get(1, "N"))
            record.lon = dms_to_decimal(gps_ifd[4], gps_ifd.get(3, "E"))
            record.location = find_location(record.lon, record.lat, areas)

        thumbnail_path = output_dir / record.filename
        if not thumbnail_path.exists():
            print(f"resizing {path} to {record.filename}")
            image = ImageOps.exif_transpose(img)
            image.thumbnail((800, 800))
            image.save(thumbnail_path, "JPEG", quality=85)

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
    by_day: dict[date, list[PhotoRecord]] = {}
    for record in records:
        by_day.setdefault(record.day, []).append(record)

    for day_records in by_day.values():
        known_locations = {
            record.location
            for record in day_records
            if record.location not in (None, "Other")
        }
        if len(known_locations) != 1:
            continue
        (location,) = known_locations
        for record in day_records:
            if record.location in (None, "Other"):
                record.location = location


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


def cluster_name(records: list[PhotoRecord]) -> str:
    """Build an "<dates>" label from a cluster's distinct photo days.

    Eg "June 22" for a single-day cluster, "June 22, July 1" once
    merging (see cluster_other_photos) spans multiple days - so unmapped
    clusters carry a recognizable date instead of an arbitrary letter.
    """
    names: list[str] = []
    for day in sorted({record.day for record in records}):
        names.append(f"{day.strftime('%B')} {day.day}")
    return ", ".join(names)


def cluster_centroid(cluster: dict[str, Any]) -> None:
    """Recompute a cluster's centroid as the mean of its records' points."""
    cluster["lat"] = sum(r.lat for r in cluster["records"]) / len(cluster["records"])
    cluster["lon"] = sum(r.lon for r in cluster["records"]) / len(cluster["records"])


def cluster_other_photos(records: list[PhotoRecord]) -> None:
    """Group "Other" photos into "Mon 1" locations, in two passes.

    First, every day's "Other" photos become one cluster - one off-map
    stop is one session, even if GPS wanders a bit within it. Second,
    any two clusters whose centroids are within CLUSTER_RADIUS_METERS
    are merged, repeated until no pair overlaps - so multiple days at
    the same off-map spot end up in one cluster, including transitively
    (A overlaps B, B overlaps C -> A, B, and C all merge, even if A and
    C alone wouldn't have). Mutates each matched record's "location" in
    place (eg "June 22"), so unmapped GPS points still get a map
    marker instead of disappearing into an undifferentiated "Other"
    bucket.
    """
    by_day: dict[date, list[PhotoRecord]] = {}
    for record in records:
        if record.location != "Other":
            continue
        by_day.setdefault(record.day, []).append(record)

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

    for cluster in clusters:
        name = cluster_name(cluster["records"])
        for record in cluster["records"]:
            record.location = name


def load_records(json_path: Path) -> list[PhotoRecord]:
    """Load and validate photos.json, or return [] if it doesn't exist yet."""
    if not json_path.exists():
        return []
    with open(json_path) as f:
        return [PhotoRecord.model_validate(d) for d in json.load(f)]


def write_records(json_path: Path, records: list[PhotoRecord]) -> None:
    """Write records to photos.json."""
    with open(json_path, "w") as f:
        json.dump([r.model_dump(mode="json") for r in records], f, indent=2)


def build_gallery() -> None:
    """Build the gallery from photos under PHOTOS_DIR.

    Writes resized thumbnails to photos/ and a manifest (datetime,
    location tag, description) to photos.json. Only photos not already
    in photos.json are processed; they're merged into the existing
    records by filename, with new records replacing old ones.
    """
    photos_dir: Path = Path(os.environ["PHOTOS_DIR"])
    project_dir: Path = Path(os.environ["PROJECT_DIR"]) / "web"
    output_dir: Path = project_dir / "photos"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_filename: Path = project_dir / "photos.json"

    existing: list[PhotoRecord] = load_records(json_filename)
    filenames: set[str] = {
        r.original_filename for r in existing if r.original_filename is not None
    }

    areas: list[Area] = load_areas()
    all_paths: list[Path] = []
    for p in photos_dir.rglob("*"):
        if not p.suffix.lower() in (".jpg", ".jpeg"):
            continue
        all_paths.append(p)

    all_paths = sorted(all_paths, key=lambda p: p.name, reverse=True)
    print(f"{len(all_paths)} photos")
    # edited photos have two files: IMG_000.JPG and IMG_000_edited.jpeg
    # keep only edited
    paths: list[Path] = []
    prev_number = ""
    for p in all_paths:
        if match := re.search(r"_(\d+)", p.name):
            if match.group(1) == prev_number:
                print(f"skipping unedited {p.name}")
                continue
            prev_number = match.group(1)
        paths.append(p)
    print(f"read {len(paths)} photos from {photos_dir}")
    print(f"writing thumbnails to {output_dir}")

    records: list[PhotoRecord] = []
    for path in paths:
        record = process_photo(path, areas, output_dir, filenames)
        if record is not None:
            records.append(record)

    # Only new records: existing locations are already resolved (eg
    # "June 22"), so they're left as-is.
    backfill_location_by_day(records)
    cluster_other_photos(records)

    # Merge and dedupe by filename; new records replace existing ones.
    by_filename: dict[str, PhotoRecord] = {r.filename: r for r in existing}
    by_filename.update({r.filename: r for r in records})
    merged: list[PhotoRecord] = list(by_filename.values())

    # Newest day first overall, but oldest-to-newest within a day: sort
    # ascending by full timestamp first, then stable-sort by day
    # descending - the stable sort preserves the ascending order already
    # established within each day's group.
    merged.sort(key=lambda r: r.dt)
    merged.sort(key=lambda r: r.day, reverse=True)

    write_records(json_filename, merged)
    print(f"wrote {len(merged)} photos ({len(records)} new) to {json_filename}")


if __name__ == "__main__":
    build_gallery()
