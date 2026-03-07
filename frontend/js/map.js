export const map = L.map("map").setView([20, 0], 2);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

const markersLayer = L.layerGroup().addTo(map);
const routeLayer = L.layerGroup().addTo(map)
const statusEl = document.getElementById('status');

export function showMarkers(data) {
    statusEl.textContent = 'Loading...';
    markersLayer.clearLayers();
    try {
    const bounds = [];

    data.forEach(item => {
        const lat = item.lat, lon = item.lon
        const name = item.name || place;

        if(!item.lat || !item.lon) return;

        L.marker([lat, lon]).addTo(markersLayer).bindPopup(name);

        if (item.bbox) {
        bounds.push([item.bbox.south, item.bbox.west]);
        bounds.push([item.bbox.north, item.bbox.east]);
        } else {
        bounds.push([lat, lon]);
        }
    });

    if (bounds.length) {
        map.fitBounds(bounds, { padding: [20,20] });
        statusEl.textContent = `Found ${markersLayer.getLayers().length} result(s)`;
    } else {
        statusEl.textContent = 'Results had no coordinates';
    }

    } catch (err) {
    statusEl.textContent = 'Error: ' + err.message;
    }
}


export function showRoute(coords) {
    routeLayer.clearLayers();

    const latlngs = coords.map(c => [c[1], c[0]]);
    const polyline = L.polyline(latlngs, { color: "blue", weight: 4}).addTo(routeLayer);

    map.fitBounds(polyline.getBounds())
}