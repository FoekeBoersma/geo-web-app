import { fetchPlace, fetchRoute } from './api.js';
import { map } from "./map.js";

const searchBtn = document.getElementById('search');
const routeBtn = document.getElementById('route-btn');

searchBtn.addEventListener('click', () => fetchPlace());
routeBtn.addEventListener('click', fetchRoute)
