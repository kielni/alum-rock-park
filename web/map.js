const CATEGORIES = {
  /*
  "high recent activity": "#edf8fb",
  "minimal recent work": "#b3cde3",
  "moderate recent activity": "#8c96c6",
  "plannned priorities": "#8856a7",
  "no recent activity": "#810f7c",
  */
  /*
  "high recent activity": "#993404",
  "minimal recent work": "#d95f0e",
  "moderate recent activity": "#fe9929",
  "planned priorities": "#fed98e",
  "no recent activity": "#ffffd4",
*/
  /* green
  "high recent activity": "#006837",
  "moderate recent activity": "#31a354",
  "minimal recent work": "#78c679",
  "planned priorities": "#c2e699",
  "no recent activity": "#ffffcc",
*/
  // "no recent activity": "#edf8fb",
  "high recent activity": "#810f7c",
  "moderate recent activity": "#8856a7",
  "minimal recent work": "#8c96c6",
  "no recent activity": "#bfd3e6",
};

const WORK_DAY_WINDOW_DAYS = 180;

// Matches an unmapped-cluster location (eg "June 22" or "June 22, July
// 1" - see cluster_name() in preprocess.py) as opposed to a named work
// area (eg "Pine gulch"), which never starts with a capitalized word
// followed by a number.
const CLUSTER_LOCATION_PATTERN = /^[A-Z][a-z]+ \d+/;

async function loadData() {
  const response = await fetch(HOST + "ARP_areas.geojson");
  return await response.json();
}

// Count of unique EXIF day-strings within the last WORK_DAY_WINDOW_DAYS
// among the given records - shared by the per-area counts below and by
// createClusterMarkers's per-cluster counts.
function workDaysInWindow(records) {
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - WORK_DAY_WINDOW_DAYS);

  const days = new Set();
  records.forEach((record) => {
    if (new Date(record.date) < cutoff) return;
    days.add(record.date.slice(0, 10));
  });
  return days.size;
}

// Unique EXIF work-days per named location within the last
// WORK_DAY_WINDOW_DAYS, from photos.json records (see loadPhotos()
// in gallery.js) - drives the choropleth color ramp below. Excludes
// unmapped-cluster locations, which get their own markers (see
// createClusterMarkers) rather than a named-area color.
function countWorkDays(records) {
  const byLocation = {};
  records.forEach((record) => {
    if (!record.location || CLUSTER_LOCATION_PATTERN.test(record.location))
      return;
    if (!byLocation[record.location]) {
      byLocation[record.location] = [];
    }
    byLocation[record.location].push(record);
  });

  const counts = {};
  Object.keys(byLocation).forEach((location) => {
    counts[location] = workDaysInWindow(byLocation[location]);
  });
  return counts;
}

// Thresholds are a starting point, not measured against a full season of
// data yet - tune once more months of photos are processed. Scored
// against the WORK_DAY_WINDOW_DAYS-day window computed above, not all time.
function categoryForWorkDays(workDays) {
  if (workDays >= 5) return "high recent activity";
  if (workDays >= 2) return "moderate recent activity";
  if (workDays >= 1) return "minimal recent work";
  return "no recent activity";
}

function drawAreas(map, data) {
  map.addSource("areas", {
    type: "geojson",
    data: data,
  });

  // fill polygon with feature color
  map.addLayer({
    id: "areas-fill",
    type: "fill",
    source: "areas",
    paint: {
      "fill-opacity": 0.4,
      "fill-color": ["get", "color"],
      //"fill-color": "#efefef",
    },
  });

  // outline polygon with feature color
  map.addLayer({
    id: "areas-outline",
    type: "line",
    source: "areas",
    paint: {
      // "line-color": ["get", "color"],
      "line-color": "#333333",
      "line-width": 2,
    },
  });

  return ["areas-fill", "areas-outline"];
}

// Sets the paint property of whichever layer matches eventDetail's
// location to bright green for the matching feature, default color for
// the rest - "areas-outline"/line-color/"#333333" for a named area, or
// "other-clusters-circle"/circle-stroke-color/"#ffffff" for an unmapped
// cluster (see CLUSTER_LOCATION_PATTERN). Driven by gallery.js's
// "location-in-view" event (see index.html), fired with the
// location-tag <a> element itself when it scrolls into view in the
// gallery pane, so the map calls out whichever area's photos are
// currently on screen.
function highlightFeature(map, name) {
  const isCluster = CLUSTER_LOCATION_PATTERN.test(name);
  const layerId = isCluster ? "other-clusters-circle" : "areas-outline";
  const paintProperty = isCluster ? "circle-stroke-color" : "line-color";

  map.setPaintProperty(layerId, paintProperty, [
    "case",
    ["==", ["get", "name"], name],
    "#00ff00",
    isCluster ? "#ffffff" : "#333333",
  ]);
}

function addPopups(map, layerId) {
  const popup = new maptilersdk.Popup({
    closeButton: false,
    closeOnClick: false,
  });
  map.on("mouseenter", layerId, function (e) {
    // Change the cursor style as a UI indicator.
    map.getCanvas().style.cursor = "pointer";

    const feature = e.features[0];
    const props = feature.properties;
    const coordinates = feature.geometry.coordinates.slice();
    const description = `<b>${props.name}</b>: ${props.description}`;

    // Ensure that if the map is zoomed out such that multiple
    // copies of the feature are visible, the popup appears
    // over the copy being pointed to.
    while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
      coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
    }

    // Populate the popup and set its coordinates
    // based on the feature found.
    popup.setLngLat(coordinates).setHTML(description).addTo(map);
  });

  map.on("mouseleave", layerId, function () {
    map.getCanvas().style.cursor = "";
    popup.remove();
  });
}

// Clicking a polygon or marker sets the same window.location.hash filter
// that location-tag chips in the gallery pane use (see currentLocationFilter
// in gallery.js), so both filter entry points share one state.
function addFilterClick(map, layerId) {
  map.on("click", layerId, function (e) {
    const feature = e.features[0];
    window.location.hash =
      "location=" + encodeURIComponent(feature.properties.name);
  });

  map.on("mouseenter", layerId, function () {
    map.getCanvas().style.cursor = "pointer";
  });
  map.on("mouseleave", layerId, function () {
    map.getCanvas().style.cursor = "";
  });
}

function createPoints(map, data) {
  // create point features at polygon centroids, for marker anchors
  const pointFeatures = {
    type: "FeatureCollection",
    features: data.features.map((feature) => {
      // Calculate centroid of polygon
      const coordinates = feature.geometry.coordinates[0];
      let x = 0,
        y = 0;
      const numPoints = coordinates.length;

      coordinates.forEach((coord) => {
        x += coord[0];
        y += coord[1];
      });

      let centroid = [x / numPoints, y / numPoints];

      // Adjust centroid for specific IDs to avoid label overlap
      const id = feature.properties.id;
      let adjustmentFactor = 0.0001;

      if (id === 14 || id === 17 || id === 10 || id === 8) {
        centroid[1] -= adjustmentFactor; // move down
      }
      if (id === 15 || id === 20) {
        centroid[1] += adjustmentFactor; // move up
      }
      // smaller adjustments
      adjustmentFactor /= 2;
      if (id == 6 || id == 12 || id == 14) {
        centroid[1] -= adjustmentFactor; // move down
      }
      if (id == 15) {
        centroid[1] += adjustmentFactor; // move up
      }
      if (id == 20) {
        centroid[0] += adjustmentFactor; // move right
      }

      return {
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: centroid,
        },
        properties: feature.properties,
      };
    }),
  };

  // add points as a source
  map.addSource("area-centroids", {
    type: "geojson",
    data: pointFeatures,
  });

  // add a layer with points, but do not show; only for marker anchors
  const layerId = "centroid-points";

  map.addLayer({
    id: layerId,
    type: "symbol",
    source: "area-centroids",
    minzoom: 10,
    layout: {
      //"text-field": ["get", "name"],
      "text-field": ["concat", ["get", "id"], " ", ["get", "name"]],
      "text-size": ["step", ["zoom"], 11, 17, 15],
      "text-font": ["Noto Sans Bold"],
      "text-allow-overlap": true,
    },
    paint: {
      //'text-color': "#efefef"
      //"text-color": "#483D8B",
      "text-color": "#191970",
      "text-halo-color": "#ffffff",
      "text-halo-width": 1,
    },
  });

  return layerId;
}

function createMarkers(map, data) {
  const layerId = createPoints(map, data);
  addPopups(map, layerId);
  return layerId;
}

// Groups photos.json records tagged with an unmapped-cluster location
// (see cluster_other_photos() in preprocess.py) by that tag, averages
// each group's lat/lon for a marker position - the clustering decision
// already happened in Python; this is just centroid averaging of
// already-grouped points - and adds one circle+label marker per cluster
// showing its work-day count, colored the same way as named areas.
function createClusterMarkers(map, records) {
  const byCluster = {};
  records.forEach((record) => {
    if (!record.location || !CLUSTER_LOCATION_PATTERN.test(record.location))
      return;
    if (!byCluster[record.location]) {
      byCluster[record.location] = [];
    }
    byCluster[record.location].push(record);
  });

  const features = Object.keys(byCluster).map((location) => {
    const clusterRecords = byCluster[location];
    const lat =
      clusterRecords.reduce((sum, r) => sum + r.lat, 0) / clusterRecords.length;
    const lon =
      clusterRecords.reduce((sum, r) => sum + r.lon, 0) / clusterRecords.length;
    const workDays = workDaysInWindow(clusterRecords);

    return {
      type: "Feature",
      geometry: { type: "Point", coordinates: [lon, lat] },
      properties: {
        name: location,
        workDays: workDays,
        color: CATEGORIES[categoryForWorkDays(workDays)],
      },
    };
  });

  map.addSource("other-clusters", {
    type: "geojson",
    data: { type: "FeatureCollection", features },
  });

  map.addLayer({
    id: "other-clusters-circle",
    type: "circle",
    source: "other-clusters",
    paint: {
      "circle-radius": 10,
      "circle-color": ["get", "color"],
      "circle-stroke-width": 1,
      "circle-stroke-color": "#ffffff",
    },
  });

  map.addLayer({
    id: "other-clusters-label",
    type: "symbol",
    source: "other-clusters",
    layout: {
      "text-field": ["to-string", ["get", "workDays"]],
      "text-size": 10,
      "text-font": ["Noto Sans Bold"],
      "text-allow-overlap": true,
    },
    paint: {
      "text-color": "#ffffff",
    },
  });

  return { layerId: "other-clusters-circle", features };
}

// Zooms/centers the map to fit every named area's polygon plus every
// cluster marker, so nothing added above starts off-screen. Also resets
// labelLayerId's minzoom relative to the zoom fitBounds actually lands
// on, since a fixed minzoom (eg 10) can end up above whatever that turns
// out to be, forcing an extra manual zoom-in before labels appear.
// Called once after all sources/layers are in place.
function fitMapToMarkers(map, geoData, clusterFeatures, labelLayerId) {
  const bounds = new maptilersdk.LngLatBounds();

  geoData.features.forEach((feature) => {
    feature.geometry.coordinates[0].forEach((coord) => bounds.extend(coord));
  });
  clusterFeatures.forEach((feature) => {
    bounds.extend(feature.geometry.coordinates);
  });

  // animate: false makes fitBounds apply synchronously, so getZoom()
  // below reflects the landed-on zoom rather than mid-animation.
  map.fitBounds(bounds, { padding: 40, animate: false });

  const fitZoom = map.getZoom();
  map.setLayerZoomRange(labelLayerId, fitZoom + 2, 24);
}

function mergeData(geoData, sheetData, workDayCounts) {
  geoData.features.forEach((feature) => {
    const id = feature.properties.id;
    const name = feature.properties.name;

    // Color always comes from photo-derived work-day counts (see
    // countWorkDays above), not the curated sheet - sheetData only
    // supplies a description override when present.
    const workDays = (workDayCounts && workDayCounts[name]) || 0;
    feature.properties.color = CATEGORIES[categoryForWorkDays(workDays)];

    if (sheetData[id] && sheetData[id].description) {
      feature.properties.description = sheetData[id].description;
    } else {
      feature.properties.description =
        workDays > 0
          ? `${workDays} work day${workDays === 1 ? "" : "s"} with photos.`
          : "";
    }
  });

  return geoData;
}

async function loadSheetData() {
  const url =
    `https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/` +
    `values/areas?key=${SHEETS_API_KEY}`;
  const response = await fetch(url);
  const data = await response.json();

  const headers = data["values"][0];
  const rows = data["values"].slice(1);

  const parsedData = {};
  rows.forEach((row) => {
    const obj = {};
    headers.forEach((header, index) => {
      obj[header] = row[index] || "";
    });
    // Add color based on category
    const category = obj["category"];
    obj["color"] = CATEGORIES[category] || CATEGORIES["no recent activity"];
    parsedData[obj["id"]] = obj;
  });

  console.log("loaded sheet data:", parsedData);
  return parsedData;
}

function addControls(map, outlineLayerId) {
  map.addControl(
    new LegendControl({
      layerId: outlineLayerId,
    }),
    "bottom-left",
  );

  map.addControl(
    new maptilersdk.ScaleControl({
      maxWidth: 120,
      unit: "imperial",
    }),
    "bottom-right",
  );
}

// legend
class LegendControl {
  constructor(options) {
    this._options = { ...options };
    this._container = document.createElement("div");
    this._container.classList.add("maplibregl-ctrl");
    this._container.classList.add("maplibregl-ctrl-choropleth");
    this.mousemove = this._mousemove.bind(this);
    this.mouseleave = this._mouseleave.bind(this);
  }
  onAdd(map) {
    this._map = map;
    const layer = this._map.getLayer(this._options.layerId);
    if (!layer) {
      console.warn("layer ", this._options.layerId, "not found for legend");
      return this._container;
    }
    const labels = [];

    Object.entries(CATEGORIES).forEach(([category, color]) => {
      labels.push(
        `<li><span style="background-color: ${color}"></span><label>${category}</label></li>`,
      );
    });
    const title = "<h3>Alum Rock Adopt-a-Park<br>work areas</h3>";
    this._container.innerHTML = `${title}<ul class="legend">${labels.join("")}</ul>`;
    this._map.on("mousemove", this._options.layerId, this.mousemove);
    this._map.on("mouseleave", this._options.layerId, this.mouseleave);
    return this._container;
  }
  _mousemove(e) {}
  _mouseleave() {}
  onRemove() {
    if (!this._map || !this._container) {
      return;
    }
    this._map.off("mousemove", this._options.layerId, this.mousemove);
    this._map.off("mouseleave", this._options.layerId, this.mouseleave);
    this._container.parentNode.removeChild(this._container);
    this._map = undefined;
    delete this._map;
  }
}

// print

window.onbeforeprint = function () {
  map.resize();
  // Give tiles time to load
  setTimeout(() => {
    const canvas = map.getCanvas();
    const img = document.createElement("img");
    img.src = canvas.toDataURL();
    img.id = "print-map";
    img.style = "width:100%;height:auto;";
    document.getElementById("map").style.display = "none";
    document.body.appendChild(img);
  }, 500);
};

window.onafterprint = function () {
  document.getElementById("map").style.display = "";
  const img = document.getElementById("print-map");
  if (img) img.remove();
};
