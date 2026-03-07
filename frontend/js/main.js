const map = L.map('map').setView([20,0], 2);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

const statusEl = document.getElementById('status');
const searchBtn = document.getElementById('search');
const placeInput = document.getElementById('place');
let markersLayer = L.layerGroup().addTo(map);

async function fetchPlace(place) {
    statusEl.textContent = 'Loading…';
    markersLayer.clearLayers();

    try {
    const url = `http://127.0.0.1:8000/fetch_osm_data?placename=${encodeURIComponent(place)}`;
    const res = await fetch(url);

    if (!res.ok) throw new Error(res.statusText);

    const payload = await res.json();
    const data = payload.data ?? payload;

    if (!Array.isArray(data) || data.length === 0) {
        statusEl.textContent = 'No results';
        return;
    }

    const bounds = [];

    data.forEach(item => {
        const lat = item.lat, lon = item.lon;
        const name = item.name || place;

        if (lat == null || lon == null) return;

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

searchBtn.addEventListener('click', () => fetchPlace(placeInput.value.trim()));
placeInput.addEventListener('keypress', e => {
    if (e.key === 'Enter') fetchPlace(placeInput.value.trim());
});
document.getElementById('route-btn').addEventListener('click', fetchRoute);
document.getElementById('destination').addEventListener('keypress', e => {
    if (e.key === 'Enter') fetchRoute();
});

// initial search
fetchPlace(placeInput.value.trim());

let routeLayer = L.layerGroup().addTo(map);

async function fetchRoute() {
    const origin = document.getElementById("origin").value.trim();
    const destination = document.getElementById("destination").value.trim();

    if (!origin || !destination) {
    statusEl.textContent = "Please enter both origin and destination!";
    return;
    }

    statusEl.textContent = "Fetching route...";
    routeLayer.clearLayers();

    try {
    const url = `http://127.0.0.1:8000/ors-route?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}`;
    const res = await fetch(url);

    if (!res.ok) throw new Error(res.statusText);

    const data = await res.json()

    const coords = data.route.features[0].geometry.coordinates;
    const latlngs = coords.map(c => [c[1], c[[0]]]); // ORS has different format [lon, lat] than Leaflet [lat, lon]

    const polyline = L.polyline(latlngs, { color: "blue", wieght: 4 }).addTo(routeLayer);
    map.fitBounds(polyline.getBounds(), { padding: [20, 20] });

    statusEl.textContent = `Route loaded (${origin} → ${destination})`;
    } catch (err) {
    statusEl.textContent = 'Error fetching route: ' + err.message;
    }
    
}