export const state = {
    origin: null,
    destination: null,
    route: null,
    loading: false,
    error: null,
}

// Mutators
export function setOrigin(data) {
    state.origin = data;
    state.error = null;
}

export function setDestination(data) {
    state.destination = data;
    state.error = null
}

export function setRoute(geojson) {
    state.route = geojson;
}

export function setLoading(isLoading) {
    state.loading = isLoading;
}

export function setError(message) {
    state.error = message;
}