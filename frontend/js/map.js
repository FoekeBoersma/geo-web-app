import { createPoint, fetchPoints } from './api.js';

export const map = L.map("map").setView([20, 0], 2);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

const markersLayer = L.layerGroup().addTo(map);
const routeLayer = L.layerGroup().addTo(map)
const pointsOfInterestLayer = L.layerGroup().addTo(map);
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

export function showPointsOfInterest(pois) {
    pointsOfInterestLayer.clearLayers();

    pois.forEach(p => {
        if (!p.latitude || !p.longitude ) return;

        const popupContent = `
            <div>
            <strong>${p.description || "Point of Interest"}</strong><br>
            ${p.image ? `img src="http://127.0.0.1:8000/pictures/${p.picture_path}" style="width:120px;margin-top:5px;">` : ""}
            </div>
            `;

            L.marker([p.latitude, p.longitude])
                .addTo(pointsOfInterestLayer)
                .bindPopup(popupContent);
    })
}

map.on("click", (e) => {
    const latitude = e.latlng.lat;
    const longitude = e.latlng.lng;

    showPointForm(latitude, longitude);
} )

function showPointForm(latitude, longitude) {
    const formHtml = `
    <div id="point-form" style="position: absolute; top: 10px; right: 10px; background: white; padding: 10px; border: 1px solid blackl z-index: 1000;">
    <h3>Add Point of Interest</h3>
    <label>Name: <input type="text" id="poi-name"></label><br>
    <label>Description: <input type="text" id="poi-desc"></label><br>
    <label>Picture: <input type="file" id="poi-pic" accept="image/*"></label><br>
    <button id="save-poi">Save</button>
    <button id="cancel-poi">Cancel</button>
    </div>
    `;

    document.body.insertAdjacentHTML('beforeend', formHtml);

    document.getElementById('save-poi').addEventListener('click', async () => {
        const name = document.getElementById('poi-name').value;
        const desc = document.getElementById('poi-desc').value;
        const pic = document.getElementById('poi-pic').files[0];
        try {
            await createPoint(latitude, longitude, name, desc, pic);
            const points = await fetchPoints();
            showPointsOfInterest(points);
            document.getElementById('point-form').remove();
        } catch (err) {
            alert('Error saving point: ' + err.message);
        }
    });

    document.getElementById('cancel-poi').addEventListener('click', () => {
        document.getElementById('point-form').remove();
    });
}