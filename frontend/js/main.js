import { fetchPlace, fetchRoute, lastRouteGeoJSON, lastOrigin, lastDestination } from './api.js';
import { map } from "./map.js";

const searchBtn = document.getElementById('search');
const routeBtn = document.getElementById('route-btn');
const downloadBtn = document.getElementById('download-btn');
const statusEl = document.getElementById('status');

searchBtn.addEventListener('click', () => fetchPlace());
routeBtn.addEventListener('click', fetchRoute)
downloadBtn.addEventListener('click', () => {
    statusEl.textContent = 'downloading...';
    if(!lastRouteGeoJSON) {
        alert("No route to download. Please fetch a route first.");
        return;
    }

    const blob = new Blob([JSON.stringify(lastRouteGeoJSON, null, 2)], {
        type: "application/geo+json"
    });

    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `route${encodeURIComponent(lastOrigin)}_${encodeURIComponent(lastDestination)}.geojson`
    a.click()

    URL.revokeObjectURL(url)
});
