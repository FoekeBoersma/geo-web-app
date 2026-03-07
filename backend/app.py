# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException
from .fetch_osm_data import fetch_osm_data
from fastapi.middleware.cors import CORSMiddleware
import httpx # useful for async requests; parallel API calls; potentially faster response times
from dotenv import load_dotenv
import os

app = FastAPI()

load_dotenv() # load environment variables from .env file

ORS_API_KEY = os.getenv("ORS_API_KEY")
ORS_URL = "https://api.openrouteservice.org/v2/directions/driving-car?format=geojson"

'''
Cross-Origin Resource Sharing to allow frontend 
(running on a different port) to access backend API
'''

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # NOTE: in production, replace with specific domain(s)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the OSM Data Fetcher API!"}

@app.get("/fetch_osm_data")
def fetch_osm_data_endpoint(placename: str):
    try:
        data = fetch_osm_data(placename)
        return {"status": 200, "data": data}
    except Exception as e:
        return {"status": 500, "error": str(e)}
    
@app.get("/ors-route")
async def get_route(origin: str, destination: str) -> dict:
    """
    origin: name of place A 
    destination: name of place B   

    returns: JSON response containing route information between the two places
    """

    # geocode both places via ORS geocoding API
    geocode_url = "https://api.openrouteservice.org/geocode/search"

    async with httpx.AsyncClient() as client:
        r1 = await client.get(
            geocode_url,
            params={"api_key": ORS_API_KEY, "text": origin}
        )
        data1 = r1.json()
        if not data1["features"]:
            raise HTTPException(404, f"Destination '{origin}' not found")
        lon1, lat1 = data1["features"][0]["geometry"]["coordinates"]

        # destination geocoding
        r2 = await client.get(
            geocode_url,
            params={"api_key": ORS_API_KEY, "text": destination}
        )
        data2 = r2.json()
        if not data2["features"]:
            raise HTTPException(404, f"Destination '{destination}' not found")
        lon2, lat2 = data2["features"][0]["geometry"]["coordinates"]

        route_url = (
        f"https://api.openrouteservice.org/v2/directions/driving-car"
        f"?start={lon1},{lat1}&end={lon2},{lat2}&format=geojson"
        )

        r3 = await client.get(
            route_url,
            headers={"Authorization": ORS_API_KEY}
        )
        if r3.status_code != 200:
            raise HTTPException(r3.status_code, f"ORS API error: {r3.text}")
        
        route_data = r3.json()

    return {
        "origin": origin,
        "destination": destination,
        "route": route_data
    }