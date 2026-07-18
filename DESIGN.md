# Alum Rock Park habitat restoration gallery

Goal: show photo gallery of habitat restoration progress in Alum Rock Park.
Highlight frequency and distribution, with photo gallery as newest first detail view
or activity log.

## Inputs

  - ARP_areas.geojson named polygons
  - full size photo files with date, description, and location EXIF data,
    in a directory outside the project root, path set via PHOTOS_DIR in
    local.env (not checked into the repo; originals are not web-served)
  - existing MapTiler map showing ARP_areas.geojson in index.html

## Outputs

Desktop: map pane on top (roughly 1/3 height), gallery pane below.
Mobile: drop the map pane, photo stream only.

On the map, show where volunteers work, highlighting by number of work days
in the last 180 days (unique dates from EXIF data).

Photos whose GPS point falls outside every named work area are grouped by
day and proximity into "Area A", "Area B", ... pseudo-locations (see
Ideas/preprocess.py). Each cluster gets its own map marker showing its
work-day count, same as a named
area's marker.

Initially, show recent-first photo stream, with separators by day (ie June 22, 2026)
and location tag (ie Bathtub seep) if available.  Show EXIF description as a caption
below photo if available.

Click a location tag to show a recent-first photo stream for only that location.
On desktop, clicking a polygon/marker on the map applies the same filter.

Gallery shows web-viewing-size images only (resized on processing, see Ideas);
full-resolution originals are not published.

No click-to-enlarge or zoom.

### Layout

Fully custom grid/filter logic — no gallery library (see below). For
components (headers, tags, grid), use Bulma: CSS-only, no JS, single CDN
`<link>` (same pattern as the existing MapTiler CDN script), no build step.
Retheme Bulma's accent to navy/purple — map.js's existing choropleth range —
via CSS custom properties; no Sass compilation needed.

  - day header: Bulma title/subtitle
  - location tag chip: Bulma `.tag` / `.tags`
  - 2-up photo layout: Bulma `.columns` grid
  - day-group container: Bulma `.box` or `.card`

Each day group:

  - day header (ie "June 22, 2026")
  - location tag chip (ie "Bathtub seep"), clickable to filter
  - photos laid out 2-up, most recent day first
  - EXIF description as caption below each photo, if available

A gallery library (eg lightGallery) was considered for the grid/filter
component, but was rejected: since there's no enlarge/zoom, the one thing a
library like PhotoSwipe would have done disappears, and a packaged
grid/filter component only adds unused chrome (toolbar, card shadows, zoom
badges) that would need to be overridden to match the existing palette
instead of just written directly.

TODO: define remaining interaction details (transitions, empty states,
loading), use clean modern light mode patterns

## Ideas

Keep a cache so that ongoing monthly updates can detect and process only
new files.

For each file not in cache

  - resize to a reasonable web-view size (800px), keeping original aspect ratio
  - get date and location from EXIF
  - create location tag with name from location's enclosing polygon, else other
  - save processed image to photos/, named yyyymmdd_hhmmss.jpg from its
    EXIF date (not the original filename); a -2, -3, ... suffix is added
    on the rare collision (eg two shots in the same second)
  - save thumbnail filename, date, location tag in cache file (photos.json)

## Deployment

photos/ and photos.json are written flat at the project root (not
nested under gallery/), so their relative paths are identical locally and
on S3 — same pattern as ARP_areas.geojson, no HOST-relative path
special-casing needed (see Constraints).

  - photos/ (processed images) synced to $(S3_BUCKET)/arp/photos via a
    new `sync-photos` Makefile target (aws s3 sync, since it's a
    directory), alongside the existing `sync` target for
    index.html/map.js/style.css/ARP_areas.geojson
  - photos.json added to the existing `sync` target (single flat file,
    same pattern as ARP_areas.geojson)

## Constraints

This seems like a well known problem: static page generation, with some light
styling of the final design. But the static
page needs to support interactivity. How to hand off to a dependency to 
reduce complexity, yet not create a dependency management burden?

Don't reinvent the wheel. Look first for well regarded open source solutions.

One expected tension is prefer Python for file and data processing, yet need
a JavaScript browser runtime.

Resolved: split along the Python/JS boundary rather than introducing a
frontend framework. Python (preprocess.py) runs only at build time (EXIF
extraction, point-in-polygon location tagging, resizing) and writes static
photos.json + photos/, both flat at the project root like
ARP_areas.geojson — so local (HOST=http://localhost:8000/) and S3
(HOST=https://.../arp/) resolve the same relative paths with no
special-casing. The browser only ever reads that static output;
map.js/gallery.js render it with plain JS, matching the existing
vanilla-JS + MapTiler pattern already used for index.html.

## Enhancements

Write rss.xml with one item per date.
## TODO

Ordered as an implementation punchlist: pipeline first (done), then
frontend (depends on the pipeline's output), then deployment (depends on
the frontend's files existing). Each item references the DESIGN.md
section it implements.

### 1. Pipeline (done — see Inputs, Ideas)

  - [x] add PHOTOS_DIR to local.env (see Inputs)
  - [x] add shapely to pyproject.toml for point-in-polygon location
        tagging (see Ideas)
  - [x] preprocess.py build_gallery(): extract EXIF (date, GPS,
        description), resolve location tag via ARP_areas.geojson, resize
        to 800px, write photos/ + photos.json (flat at project root),
        from scratch on every run, no cache file (see Ideas)
        - verified against photos-orig/'s 34 photos: 12 matched a named
          work area, 22 tagged "Other"
        - none of the sample photos carry a description in EXIF or XMP;
          real photo library may differ, pipeline already treats it as
          optional
        - backfill_location_by_day(): if a day's other photos agree on
          one confirmed (non-"Other") location, apply it to that day's
          "Other"/GPS-less photos too (GPS drift near a boundary, or a
          shot from the trail just outside the polygon); ambiguous days
          (more than one confirmed location) are left alone
        - re-verified: 22 -> 17 "Other" after backfill, all 34 photos
          still accounted for (9 Pine gulch, 5 Bathtub seep, 3 Horseshoe
          field, 17 Other)
        - each record now also carries lat/lon (decimal degrees, cast to
          float - Pillow's EXIF rationals aren't JSON-serializable as-is)
        - cluster_other_photos(): two passes. First, every day's
          "Other" photos become one cluster - a day's photos always
          land together, even if GPS wanders a bit within the day.
          Second, any two clusters within CLUSTER_RADIUS_METERS=40m of
          each other's centroid are merged, repeated until none overlap
          - so multiple days at the same off-map spot end up in one
          cluster, including transitively (A overlaps B, B overlaps C ->
          all three merge, even if A and C alone wouldn't have)
        - clusters are relabeled "Area A", "Area B", ... (letters,
          title case; cluster_label() extends past Z the way spreadsheet
          columns do: AA, AB, ...), so unmapped GPS points still get a
          map marker (see Outputs) instead of disappearing into one
          undifferentiated "Other" bucket
        - re-verified: 17 "Other" -> 4 day-respecting clusters (sizes
          3/7/2/5 for A/B/C/D), all 34 photos still accounted for
        - thumbnail filenames changed from the original filename (eg
          IMG_5310.jpeg) to yyyymmdd_hhmmss.jpg derived from EXIF date
          (unique_filename() adds -2, -3, ... on collision); gallery.js
          needed no change since it already reads record.filename from
          photos.json rather than assuming a naming scheme
        - does NOT delete old-named thumbnails left in photos/ from
          before this change, or stale thumbnails for photos removed
          from PHOTOS_DIR since the last run - photos/ is
          append-only, generated files are never auto-deleted (learned
          the hard way: an earlier version of this change added exactly
          that cleanup step and was told directly not to)
        - re-verified: 34 photos, all named yyyymmdd_hhmmss.jpg, no
          collisions in the current data
  - [x] make lint-py / make gallery Makefile targets (black + flake8;
        source local.env && run the pipeline)

### 2. Frontend (see Outputs, Layout)

  - [x] add Bulma CDN `<link>` to index.html; retheme accent to
        navy/purple (map.js's existing choropleth range) via CSS custom
        properties, no Sass build (see Layout)
        - retheme applied directly to gallery classes (.location-tag,
          .day-header) in style.css rather than Bulma's internal HSL
          theming variables, to avoid depending on undocumented-here
          variable names
  - [x] add #gallery pane to index.html alongside #map; CSS for
        stacked desktop (map top/gallery below) / stacked-no-map mobile
        layout (see Outputs)
        - #app flex wrapper in index.html; #map switched from
          absolute-positioned full-bleed to a flex child
        - originally side-by-side (map 1/3 width); switched to vertical
          (map 1/3 height, on top) after the side-by-side split left the
          map too narrow for the park's wide/short shape - #map already
          precedes #gallery in the DOM, so flex-direction: column alone
          was enough, no markup reorder needed
  - [x] write gallery.js: fetch photos.json, render recent-first
        photo stream grouped by day, using Bulma title/subtitle for day
        headers, .tag/.tags for location chips, .columns for the 2-up
        photo grid, .box or .card per day group (see Layout)
        - groups by day, then by location within each day (consecutive
          runs, preserving chronological order rather than clustering)
        - built via DOM APIs (createElement/textContent), not innerHTML
          strings, so EXIF descriptions/location names can't break markup
  - [x] wire location-tag click and map polygon/marker click to a shared
        filter, driven by window.location.hash for shareable links (see
        Outputs)
        - gallery.js chips are <a href="#location=..."> links;
          map.js's new addFilterClick() sets the same hash on
          areas-fill + centroid-points click; gallery.js's hashchange
          listener re-renders on either source
  - [x] compute per-polygon work-day counts (unique dates per location in
        photos.json) and feed into map.js's existing CATEGORIES
        choropleth coloring (see Outputs)
        - countWorkDays()/categoryForWorkDays() in map.js; color always
          comes from photo-derived work-day counts now, not the
          curated Google Sheet - sheetData only supplies a description
          override when present, never the fill color
        - countWorkDays() only counts EXIF dates within the last
          WORK_DAY_WINDOW_DAYS (180) days, so the choropleth reflects
          recent activity, not all-time history
        - dropped the "planned priorities" category: it was only ever
          reachable via curated sheet data (categoryForWorkDays() never
          returned it), which no longer drives color at all
        - thresholds (5/2/1 work days) are a placeholder, not tuned
          against a full season of data yet, and are now scored against
          the 180-day window rather than all-time counts
  - [x] define remaining interaction details: transitions, empty states,
        loading (see Outputs, Layout)
        - loading text while photos.json is in flight; empty state
          (with a "Show all" link) when a filter matches zero photos;
          hover transition on location-tag chips
  - [x] add one map marker per "Area X" location (see Outputs;
        clustering itself is done, in preprocess.py's
        cluster_other_photos - this item is map.js rendering only):
        - group photos.json records by location starting with
          "Area ", average each group's lat/lon for marker placement
          (the clustering decision already happened in Python; this is
          just centroid averaging of already-grouped points, not real
          clustering)
        - render via a GeoJSON point source ("other-clusters") +
          circle/symbol layers (matching the existing centroid-points
          pattern), color by categoryForWorkDays() same as named areas,
          work-day count as the symbol text
        - reuse addFilterClick() by giving each cluster feature a
          properties.name equal to its "Area X" tag, so clicking one
          filters the gallery same as a named-area marker
        - createClusterMarkers() in map.js; countWorkDays() and the new
          workDaysInWindow() helper both exclude "Area *" locations from
          the named-area choropleth so the two don't double-count
  - [x] within a day, sort photos from oldest to newest; keep overall
        newest day first sort order for photo stream
        - build_gallery(): two-pass stable sort (ascending by full
          timestamp, then descending by day) rather than a single
          descending sort, which put each day newest-first internally too
        - verified against the real 34-photo set: days still descend
          (07-13 -> 05-11), each day's times now ascend (eg 07-13:
          08:44:12 -> 08:44:19 -> 08:44:36 -> 10:46:23 -> 11:25:11)
  - [x] after load, adjust map zoom and center to show all markers
        - fitMapToMarkers() in map.js: builds a maptilersdk.LngLatBounds
          from every named area's polygon coordinates plus every cluster
          marker's point, then map.fitBounds() once after all
          layers/sources are added
        - createClusterMarkers() now returns { layerId, features } (was
          just the layer id string) so index.html can pass the cluster
          points into fitMapToMarkers - call site updated to destructure
        - not verified in-browser (no browser tool available this
          session) - relies on maptilersdk.LngLatBounds/map.fitBounds
          existing, which they should as MapLibre-compatible SDK methods
          (same family as the already-used Popup/ScaleControl), but
          worth confirming after reload
        - follow-up fix: centroid-points' fixed minzoom (10) meant labels
          often needed an extra manual zoom-in beyond wherever fitBounds
          actually landed. fitMapToMarkers() now takes a labelLayerId
          param, calls fitBounds with animate:false (so getZoom()
          reflects the landed-on zoom immediately, not mid-animation),
          and calls map.setLayerZoomRange(labelLayerId, fitZoom + 2, 24)
          - labels appear 2 zoom levels past the fit-to-bounds zoom,
          not a fixed level unrelated to it
  - [x] map area is long and skinny; redo map / photos split to be
        vertical, with map on top (see Outputs, and the #gallery pane
        item above for the CSS change - decided top over bottom after
        discussion: the map is a functional filter control clicked
        repeatedly, not passive context, and sticky-map-above-scrolling-
        list is a well-established pattern vs. the much rarer
        sticky-bottom map, which also competes with mobile browser
        chrome/home-indicator safe areas

Verified: all asset paths (photos.json, photos/*, gallery.js, etc.)
resolve identically under `python -m http.server 8000` at the project
root, matching config.js's HOST. `node --check` passed on gallery.js and
map.js; `make lint` (prettier) clean. Not verified: actual in-browser
rendering, click-to-filter behavior, and map interaction — no browser
automation tool was available this session, so this still needs a manual
click-through before considering it done.

### 3. Deployment (see Deployment)

  - [x] add sync-photos Makefile target: photos/ ->
        $(S3_BUCKET)/arp/photos (aws s3 sync, directory)
  - [x] add photos.json to the existing sync target (flat file, same
        pattern as ARP_areas.geojson)
  - [x] add gallery.js to the existing sync target, alongside
        index.html/map.js/style.css/ARP_areas.geojson
        - verified with `make -n sync` / `make -n sync-photos` (dry
          run only - not actually run, this pushes to production S3)