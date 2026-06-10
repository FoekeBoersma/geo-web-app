import { fetchPlace, fetchRoute, fetchRoutes, fetchPoints, exportMapViewSvg, exportPoiExtentSvg } from './api.js';
import { updateUI } from './ui.js';
import { state, setOrigin, setDestination } from "./state.js";
import { addRoute, map, showPointsOfInterest, showRoute } from "./map.js";

// initial UI sync
updateUI();

const searchBtn = document.getElementById('search');
const routeBtn = document.getElementById('route-btn');
const downloadBtn = document.getElementById('download-btn');
const statusEl = document.getElementById('status');
const exportMapViewSvgBtn = document.getElementById('export-map-view-svg-btn');
const exportPoiExtentSvgBtn = document.getElementById('export-poi-extent-svg-btn');

exportMapViewSvgBtn.addEventListener('click', async() => {
    try {
        await exportMapViewSvg();
    } catch (err) {
        console.error("Failed to export map SVG:", err);
    }
});
exportPoiExtentSvgBtn.addEventListener('click', async() => {
    try {
        await exportPoiExtentSvg();
    } catch (err) {
        console.error("Failed to export POI extent SVG:", err);
    }
})
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

(async () => {
    try {
        const routes = await fetchRoutes();
        routes.forEach(route => {
            const geojson = JSON.parse(route.geojson);
            const coords = geojson.features[0].geometry.coordinates;

            addRoute(coords)
        })
    } catch (err) {
        console.error("Failed to fetch routes:", err);
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
