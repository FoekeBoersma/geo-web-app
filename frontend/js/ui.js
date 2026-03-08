import { state } from "./state.js";

export function updateUI() {
    const statusEl = document.getElementById('status');
    const errorEl = document.getElementById('error'); // make HTML element with id 'error' to show error messages

    // loading indicator
    statusEl.textContent = state.loading ? "Loading..." : "";

    // error message 
    if (state.error) {
        errorEl.textContent = state.error;
        errorEl.style.display = 'block';
    } else {
        errorEl.textContent = "";
        errorEl.style.display = 'none';
    }

    // route button only enabled when we have both origin and destination
    document.getElementById("route-btn").disabled = !(state.origin && state.destination);
}