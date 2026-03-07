import { showMarkers, showRoute } from "./map.js"

export async function fetchPlace() {
    const place = document.getElementById("place").value.trim(); // "Amsterdam " > "Amsterdam"
    const url = `http://127.0.0.1:8000/fetch_osm_data?placename=${encodeURIComponent(place)}`;

    const res = await fetch(url);
    const payload = await res.json();

    showMarkers(payload.data ?? payload)
}

export async function fetchRoute() {
    const origin = document.getElementById("origin").value.trim();
    const destination = document.getElementById("destination").value.trim();

    const url = `http://127.0.0.1:8000/ors-route?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}`;

    const res = await fetch(url);
    const data = await res.json();

    showRoute(data.route.features[0].geometry.coordinates)
}