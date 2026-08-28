import { showMarkers, showRoute } from "./map.js"
import { state, setOrigin, setDestination, setRoute, setLoading, setError } from "./state.js";
import { map } from "./map.js";

export async function fetchPlace() {
    const place = document.getElementById("place").value.trim(); // "Amsterdam " > "Amsterdam"
    if (!place) {
        setError("Please enter a place name.");
        return;
    }
    const url = `http://127.0.0.1:8000/fetch_osm_data?place_name=${encodeURIComponent(place)}`;

    try {
        setLoading(true);

        const res = await fetch(url);
        const payload = await res.json();

        const data = payload.data ?? payload;

        setOrigin({
            name: place,
            lat: data.lat,
            lon: data.lon
        });
        
        // update map
        showMarkers(data);
    } catch (err) {
        setError("Failed to fetch place data. Please try again.");
    } finally {
        setLoading(false);
    }
}

export async function fetchRoute() {
    const origin = document.getElementById("origin").value.trim();
    const destination = document.getElementById("destination").value.trim();

    if (!origin || !destination) {
        setError("Please enter both origin and destination.");
        return;
    }

    const url = `http://127.0.0.1:8000/ors-route?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}`;

    try {
        setLoading(true);

        const res = await fetch(url);
        const geojson = await res.json();

        // update state
        setOrigin({ name: origin });
        setDestination({ name: destination })
        setRoute(geojson.route);

        const coords = geojson.route.features[0].geometry.coordinates;
        showRoute(coords);

        // Post route log to backend (FastAPI at 8000) after successful route fetch + map update
        await fetch("http://127.0.0.1:8000/log-route", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                origin,
                destination,
                geojson: JSON.stringify(geojson.route)
            })
        });
    } catch (err) {
        setError("Failed to fetch route. Please try again.");
    } finally {
        setLoading(false)
    }
}

export async function fetchRoutes() {
    const res = await fetch("http://127.0.0.1:8000/routes");
    return await res.json();
}

export async function createPoint(latitude, longitude, name, description, pictureFile) {
    const formData = new FormData();
    formData.append("latitude", latitude);
    formData.append("longitude", longitude);
    formData.append("name", name);
    if (description) formData.append("description", description);
    if (pictureFile) formData.append("picture", pictureFile);

    const res = await fetch("http://127.0.0.1:8000/create-point-of-interest", {
        method: "POST",
        body: formData
    });
    return await res.json();
}

export async function fetchPoints() {
    const res = await fetch("http://127.0.0.1:8000/get-points-of-interest");
    return await res.json();
}

function buildExportUrl(mode) {
    const zoom = map.getZoom();
    const bounds = map.getBounds();
    const bbox = [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()].join(",");

    const params = new URLSearchParams({
        zoom: String(zoom),
        bbox,
        mode,
        route: JSON.stringify(state.route)
    });

    return `http://127.0.0.1:8000/export-poi-map-svg?${params}`;
}

export function exportMapViewSvg() {
    window.location.href = buildExportUrl("map");
}

export function exportPoiExtentSvg() {
    window.location.href = buildExportUrl("pois");
}

export async function fetchIsochroneFromPlace(place, minutes, networkType) {
    let url = "http://127.0.0.1:8000/fetch_isochrone"    
    url += "?place_name=" + encodeURIComponent(place)
    + "&minutes=" + encodeURIComponent(minutes)
    + "&network_type=" + encodeURIComponent(networkType);

    const res = await fetch(url);
    const payload = await res.json();

    if (!res.ok || payload.status === 500) {
        throw new Error(payload.error || "Failed to fetch isochrone data.");
    }

    return payload.data ?? payload;
}