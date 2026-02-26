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
  "high recent activity": "#006837",
  "moderate recent activity": "#31a354",
  "minimal recent work": "#78c679",
  "planned priorities": "#c2e699",
  "no recent activity": "#ffffcc",
};

async function loadData() {
  const response = await fetch(HOST + "ARP_areas.geojson");
  return await response.json();
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
      "fill-opacity": 0.2,
      // "fill-color": ["get", "color"],
      "fill-color": "#efefef",
    },
  });

  // outline polygon with feature color
  map.addLayer({
    id: "areas-outline",
    type: "line",
    source: "areas",
    paint: {
      "line-color": ["get", "color"],
      "line-width": 2,
    },
  });

  return ["areas-fill", "areas-outline"];
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

function mergeData(geoData, sheetData) {
  geoData.features.forEach((feature) => {
    const id = feature.properties.id;
    if (sheetData[id]) {
      feature.properties.color = sheetData[id].color;
      feature.properties.description =
        sheetData[id].description || "No recent activity.";
    } else {
      feature.properties.color = CATEGORIES["no recent activity"];
      feature.properties.description = "";
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
