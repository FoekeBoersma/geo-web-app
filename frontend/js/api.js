import { showMarkers, showRoute } from "./map.js"
import { setOrigin, setDestination, setRoute, setLoading, setError } from "./state.js";

export async function fetchPlace() {
    const place = document.getElementById("place").value.trim(); // "Amsterdam " > "Amsterdam"
    if (!place) {
        setError("Please enter a place name.");
        return;
    }
    const url = `http://127.0.0.1:8000/fetch_osm_data?placename=${encodeURIComponent(place)}`;

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
    } catch (err) {
        setError("Failed to fetch route. Please try again.");
    } finally {
        setLoading(false)
    }
}