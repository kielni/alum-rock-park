// Renders the recent-first photo stream in #gallery from photos.json,
// grouped by day then location, with location-tag filtering driven by
// window.location.hash so map clicks (see addFilterClick in map.js) and
// tag clicks share one filter state.

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function loadPhotos() {
  const response = await fetch(HOST + "photos.json");
  return await response.json();
}

function dayLabel(isoDate) {
  return new Date(isoDate).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

// Groups consecutive records sharing the same key, preserving order -
// photos.json is already sorted recent-first, so this keeps that order
// intact rather than clustering by key across the whole list.
function groupBy(records, keyFn) {
  const groups = [];
  let current = null;
  for (const record of records) {
    const key = keyFn(record);
    if (!current || current.key !== key) {
      current = { key, records: [] };
      groups.push(current);
    }
    current.records.push(record);
  }
  return groups;
}

function currentLocationFilter() {
  const match = window.location.hash.match(/location=([^&]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function locationTag(location) {
  const tags = el("div", "tags");
  const tag = el("a", "tag location-tag", location);
  tag.href = "#location=" + encodeURIComponent(location);
  tags.appendChild(tag);
  return tags;
}

function photoCard(record) {
  const column = el("div", "column is-6");
  const figure = el("figure", "image");
  const img = document.createElement("img");
  img.src = HOST + "photos/" + encodeURIComponent(record.filename);
  img.alt = record.description || "";
  img.loading = "lazy";
  figure.appendChild(img);
  column.appendChild(figure);
  if (record.description) {
    column.appendChild(el("p", "photo-caption", record.description));
  }
  return column;
}

function locationGroup(group) {
  const wrapper = el("div", "location-group");
  if (group.key) {
    wrapper.appendChild(locationTag(group.key));
  }
  const columns = el("div", "columns is-multiline");
  group.records.forEach((record) => columns.appendChild(photoCard(record)));
  wrapper.appendChild(columns);
  return wrapper;
}

function dayGroup(day) {
  const box = el("div", "box day-group");
  box.appendChild(
    el("p", "title is-5 day-header", dayLabel(day.records[0].date)),
  );
  groupBy(day.records, (record) => record.location).forEach((group) => {
    box.appendChild(locationGroup(group));
  });
  return box;
}

function clearFilterLink() {
  const link = el("a", null, "Show all");
  link.href = "#";
  return link;
}

function filterNotice(location) {
  const notice = el("div", "notification filter-notice");
  notice.append("Showing photos for ");
  notice.appendChild(el("strong", null, location));
  notice.append(". ");
  notice.appendChild(clearFilterLink());
  return notice;
}

function emptyState(filter) {
  const p = el("p", "has-text-grey empty-state");
  if (filter) {
    p.append("No photos yet for ");
    p.appendChild(el("strong", null, filter));
    p.append(". ");
    p.appendChild(clearFilterLink());
  } else {
    p.textContent = "No photos yet.";
  }
  return p;
}

// Fires a "location-in-view" event on window (see index.html, which owns
// the map instance) whenever a location-tag chip scrolls into #gallery's
// viewport, so map.js can highlight the matching polygon. Re-observes
// current .location-tag elements each render, since renderGallery replaces
// them wholesale.
let tagObserver = null;

function observeLocationTags() {
  if (tagObserver) tagObserver.disconnect();

  tagObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        window.dispatchEvent(
          new CustomEvent("location-in-view", {
            detail: entry.target.textContent,
          }),
        );
      });
    },
    { root: document.getElementById("gallery") },
  );

  document
    .querySelectorAll(".location-tag")
    .forEach((tag) => tagObserver.observe(tag));
}

function renderGallery(records) {
  const container = document.getElementById("gallery");
  container.innerHTML = "";

  const filter = currentLocationFilter();
  const filtered = filter
    ? records.filter((record) => record.location === filter)
    : records;

  if (filtered.length === 0) {
    container.appendChild(emptyState(filter));
    return;
  }

  if (filter) {
    container.appendChild(filterNotice(filter));
  }

  groupBy(filtered, (record) => record.date.slice(0, 10)).forEach((day) => {
    container.appendChild(dayGroup(day));
  });

  observeLocationTags();
}

async function initGallery() {
  const container = document.getElementById("gallery");
  container.innerHTML = "";
  container.appendChild(
    el("p", "has-text-grey loading-state", "Loading photos…"),
  );

  const records = await loadPhotos();
  renderGallery(records);
  window.addEventListener("hashchange", () => renderGallery(records));
}

document.addEventListener("DOMContentLoaded", initGallery);
