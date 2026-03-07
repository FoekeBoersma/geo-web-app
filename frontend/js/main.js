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
    }); // create file in memory

    const url = URL.createObjectURL(blob); // create a temp URL to file
 
    const a = document.createElement('a'); // create a link element
    a.href = url; // set link to blob-URL
    a.download = `route${encodeURIComponent(lastOrigin)}_${encodeURIComponent(lastDestination)}.geojson`
    a.click()

    URL.revokeObjectURL(url)
});
