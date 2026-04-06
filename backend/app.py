# -*- coding: utf-8 -*-
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import asynccontextmanager
from sqlmodel import Session, SQLModel

from backend.db import init_db
from .fetch_osm_data import fetch_osm_data
from fastapi.middleware.cors import CORSMiddleware
import httpx # useful for async requests; parallel API calls; potentially faster response times
from dotenv import load_dotenv
import os
from .models import RouteLog
from .db import route_engine, points_engine, init_db
import UploadFile, File   
import Form
import StaticFiles
import FileResponse
import shutil
import PointOfInterest


class RouteLogCreate(SQLModel):
    origin: str
    destination: str
    geojson: str

class PointOfInterestCreate(SQLModel):
    latitude: float
    longitude: float
    name: Optional[str] = None
    description: Optional[str] = None
    picture: Optional[UploadFile] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    init_db()
    yield
    # Shutdown (optional)
    # close connections, cleanup, etc.

    
app = FastAPI(lifespan=lifespan)
app.mount("/pictures", StaticFiles(directory="pictures"), name="pictures")

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

@app.post("/log-route")
def log_route(payload: RouteLogCreate):
    with Session(route_engine) as session:
        entry = RouteLog(
            origin=payload.origin,
            destination=payload.destination,
            geojson=payload.geojson
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return {"status": "saved", "id": entry.id}
    
@app.post("/add-point-of-interest")
def create_point_of_interest(latitude: float = Form(...), longitude: float = Form(...),
    name: Optional[str] = Form(None), description: Optional[str] = Form(None), 
    picture: Optional[UploadFile] = File(None)):
    picture_path = None
    if picture:
        os.makedirs("pictures", exist_ok = True)
        file_path = f"pictures/{picture.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(picture.file, buffer)
        picture_path = file_path
    with Session(points_engine) as session: # use Session with points_engine to save to points.db
        point = PointOfInterest(
            latitude=latitude,
            longitude=longitude,
            name=name,
            description=description,
            picture_path=picture_path
        )
        session.add(point) 
        session.commit()
        session.refresh(point)
        return {"status": "saved", "id": point.id}
    