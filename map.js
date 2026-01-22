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
      "fill-opacity": 0.1,
      "fill-color": ["get", "color"],
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
      let adjustmentFactor = 0.0001; // ~22 meters at this latitude

      if (id === 14 || id === 17 || id === 10 || id === 8) {
        centroid[1] -= adjustmentFactor; // move down
      }
      if (id === 15 || id === 20) {
        centroid[1] += adjustmentFactor; // move up
      }
      adjustmentFactor /= 2;
      if (id == 6 || id == 12 || id == 14) {
        centroid[1] -= adjustmentFactor; // move down
      }
      if (id == 10 || id == 15 || id == 17) {
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
      "text-field": ["get", "name"],
      //'text-field': ['concat', ['get', 'id'], ' ', ['get', 'name']],
      "text-size": 11,
      "text-font": ["Noto Sans Bold"],
      "text-allow-overlap": true,
    },
    paint: {
      //'text-color': "#efefef"
      "text-color": "#1b5e4a",
      "text-halo-color": "#fff4d9",
      "text-halo-width": 1,
    },
  });

  return layerId;
}

function updateMarkers() {
  const markerStatus = markerManager.update();

  console.log("marker status:", markerStatus);

  if (!markerStatus) return;

  // Remove the div that corresponds to removed markers
  markerStatus.removed.forEach((abstractMarker) => {
    const markerDiv = markerLogicContainer[abstractMarker.id];
    delete markerLogicContainer[abstractMarker.id];
    markerContainer.removeChild(markerDiv);
  });

  // Update the div that corresponds to updated markers
  markerStatus.updated.forEach((abstractMarker) => {
    const markerDiv = markerLogicContainer[abstractMarker.id];
    updateMarkerDiv(abstractMarker, markerDiv);
  });

  // Create the div that corresponds to the new markers
  markerStatus.new.forEach((abstractMarker) => {
    const markerDiv = makeMarker(abstractMarker);
    markerLogicContainer[abstractMarker.id] = markerDiv;
    markerContainer.appendChild(markerDiv);
  });
}

function softUpdateMarkers() {
  // A previous run of .update() yieding no result or not being ran at all
  // would stop the soft update
  if (!markerStatus) return;

  markerStatus.updated.forEach((abstractMarker) => {
    markerManager.softUpdateAbstractMarker(abstractMarker);
    const markerDiv = markerLogicContainer[abstractMarker.id];
    updateMarkerDiv(abstractMarker, markerDiv);
  });

  markerStatus.new.forEach((abstractMarker) => {
    markerManager.softUpdateAbstractMarker(abstractMarker);
    const markerDiv = markerLogicContainer[abstractMarker.id];
    updateMarkerDiv(abstractMarker, markerDiv);
  });
}

function makeMarker(abstractMarker) {
  const marker = document.createElement("div");
  marker.classList.add("marker");
  marker.classList.add("fade-in-animation");
  marker.style.setProperty("width", `${abstractMarker.size[0]}px`);
  marker.style.setProperty("height", `${abstractMarker.size[1]}px`);
  marker.style.setProperty(
    "transform",
    `translate(${abstractMarker.position[0]}px, ${abstractMarker.position[1]}px)`,
  );

  const feature = abstractMarker.features[0];

  marker.innerHTML = `
    <div class="markerPointy"></div>
    <div class="markerBody">
        <div class="markerTop">${feature.properties["name"]}</div>
    </div>
    `;
  return marker;
}

function updateMarkerDiv(abstractMarker, marker) {
  marker.style.setProperty("width", `${abstractMarker.size[0]}px`);
  marker.style.setProperty("height", `${abstractMarker.size[1]}px`);
  marker.style.setProperty(
    "transform",
    `translate(${abstractMarker.position[0]}px, ${abstractMarker.position[1]}px)`,
  );
}
