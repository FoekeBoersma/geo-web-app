import { fetchPlace, fetchRoute, fetchPoints, exportPoiMap, exportPoiMapSvg } from './api.js';
import { updateUI } from './ui.js';
import { state, setOrigin, setDestination } from "./state.js";
import { map, showPointsOfInterest } from "./map.js";

// initial UI sync
updateUI();

const searchBtn = document.getElementById('search');
const routeBtn = document.getElementById('route-btn');
const downloadBtn = document.getElementById('download-btn');
const statusEl = document.getElementById('status');
const exportPoiBtn = document.getElementById('export-poi-btn');
const exportPoiSvgBtn = document.getElementById('export-poi-svg-btn');


exportPoiBtn.addEventListener('click', async() => {
    try {
        await exportPoiMap();
    } catch (err) {
        console.error("Failed to export POI map:", err);
    }
});

exportPoiSvgBtn.addEventListener('click', async() => {
    try {
        await exportPoiMapSvg();
    } catch (err) {
        console.error("Failed to export POI map SVG:", err);
    }
});
searchBtn.addEventListener('click', async() => {
     await fetchPlace();
     updateUI();
});
routeBtn.addEventListener('click', async() => { 
    await fetchRoute();
    updateUI();
});

(async () => {
    try {
        const pois = await fetchPoints();
        showPointsOfInterest(pois);
    } catch (err) {
        console.error("Failed to fetch points of interest:", err);
    }
})();
document.getElementById('origin').addEventListener('input', (e) => {
    const value = e.target.value.trim()
    
    console.log("origin:", value);
    setOrigin(value ? { name: value } : null );
    updateUI();
})

document.getElementById('destination').addEventListener('input', (e) => {
    const value = e.target.value.trim();
    setDestination(value ? { name: value } : null);
    updateUI();
})

downloadBtn.addEventListener('click', () => {
    updateUI();
    statusEl.textContent = state.loading ? "Downloading route..." : "";
    if(!state.route) {
        alert("No route to download. Please fetch a route first.");
        return;
    }

    const blob = new Blob([JSON.stringify(state.route, null, 2)], {
        type: "application/geo+json"
    }); // create file in memory

    const url = URL.createObjectURL(blob); // create a temp URL to file
 
    const a = document.createElement('a'); // create a link element
    a.href = url; // set link to blob-URL
    a.download = `route${encodeURIComponent(state.origin.name)}_${encodeURIComponent(state.destination.name)}.geojson`
    a.click()

    URL.revokeObjectURL(url)
});
