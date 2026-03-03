# -*- coding: utf-8 -*-
from fastapi import FastAPI
from .fetch_osm_data import fetch_osm_data
from fastapi.middleware.cors import CORSMiddleware
import httpx # useful for async requests; parallel API calls; potentially faster response times
from dotenv import load_dotenv
import os

app = FastAPI()

ORS_API_KEY = os.getenv("ORS_API_KEY")
ORS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"

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