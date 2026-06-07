# -*- coding: utf-8 -*-
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, Form, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
import shutil
from .models import PointOfInterest

import json
import zipfile
from io import BytesIO
from pathlib import Path
from fastapi.responses import StreamingResponse
from sqlmodel import select
import base64
import html

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

@app.get("/get-points-of-interest")
def get_points_of_interest():
    with Session(points_engine) as session:
        points = session.query(PointOfInterest).all()
        return points


@app.post("/create-point-of-interest")
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
    
def build_export_html(points):
    exported_points = []
    for point in points:
        image_name = Path(point.picture_path).name if point.picture_path else None
        exported_points.append({
            "lat": point.latitude,
            "lon": point.longitude,
            "name": point.name or "",
            "description": point.description or "",
            "image": f"images/{image_name}" if image_name else None
        })

    points_json = json.dumps(exported_points, indent=2)

    return f"""<!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <title>POI Map Export</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            body, html {{ margin: 0; padding: 0; height: 100%; }}
            #map {{ width: 100%; height: 100%; }}
            .leaflet-popup-content img {{ max-width:180px; max-height:180px; display:block; margin-top:8px; }}
        </style>
        </head>
        <body>
        <div id="map"></div>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
        const pointsData = {points_json};
        const map = L.map('map').setView([20, 0], 2);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 19,
            attribution: '&copy; OpenStreetMap contributors'
        }}).addTo(map);

        const markers = [];
        pointsData.forEach(p => {{
        const title = p.name || p.description || 'POI';
        const descriptionHtml = p.description ? `<div style="margin-top:4px;">${{p.description}}</div>` : '';
        const imageHtml = p.image ? `<div><img src="${{p.image}}" alt="${{title}}" /></div>` : '';
        const popup = `
            <div>
            <strong>${{title}}</strong>
            ${{descriptionHtml}}
            ${{imageHtml}}
            </div>
        `;
        const marker = L.marker([p.lat, p.lon]).addTo(map).bindPopup(popup);
        markers.push(marker);
        }});
        if (markers.length > 0) {{
            const group = L.featureGroup(markers);
            map.fitBounds(group.getBounds(), {{ padding: [20, 20] }});
        }}
        </script>
    </body>
    </html>"""
    
@app.get("/export-poi-map")
def export_poi_map():
    with Session(points_engine) as session:
        statement = select(PointOfInterest).where(PointOfInterest.picture_path != None)
        points = session.exec(statement).all()

    valid_points = []
    for point in points:
        if not point.picture_path:
            continue
        image_path = Path(point.picture_path)
        if image_path.is_file():
            valid_points.append((point, image_path))

    if not valid_points:
        raise HTTPException(status_code=404, detail="No valid points of interest with images found")

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("index.html", build_export_html([p for p, _ in valid_points]))

        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [point.longitude, point.latitude]
                    },
                    "properties": {
                        "name": point.name,
                        "description": point.description,
                        "image": f"images/{image_path.name}"
                    }
                }
                for point, image_path in valid_points
            ]
        }

        archive.writestr("points.geojson", json.dumps(geojson, indent=2))

        for point, image_path in valid_points:
            archive.write(image_path, f"images/{image_path.name}")

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=poi_map_export.zip"}
    )


def generate_svg_map(points_with_images):
    """Generate SVG with embedded map and POI pictures"""
    if not points_with_images:
        raise HTTPException(status_code=404, detail="No points of interest with images found.")
    
    # Calculate SVG viewport bounds from POI coordinates
    lats = [p.latitude for p, _ in points_with_images]
    lons = [p.longitude for p, _ in points_with_images]
    
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    
    # Add padding
    lat_range = max_lat - min_lat if max_lat != min_lat else 1
    lon_range = max_lon - min_lon if max_lon != min_lon else 1
    padding = 0.1
    
    min_lat -= lat_range * padding
    max_lat += lat_range * padding
    min_lon -= lon_range * padding
    max_lon += lon_range * padding
    
    # SVG size
    svg_width = 1200
    svg_height = 800
    
    # Conversion functions
    def lon_to_x(lon):
        return (lon - min_lon) / (max_lon - min_lon) * svg_width
    
    def lat_to_y(lat):
        return (max_lat - lat) / (max_lat - min_lat) * svg_height
    
    # Start building SVG
    svg_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">',
        '<defs><style>',
        '.marker-circle {{ fill: #ff6b6b; stroke: white; stroke-width: 2; }}',
        '.marker-text {{ font-size: 12px; fill: black; }}',
        '.poi-image {{ border: 1px solid #ccc; }}',
        '</style></defs>',
        '<rect width="100%" height="100%" fill="#e8f4f8"/>',  # Light blue background
    ]
    
    # Add grid lines for reference
    for i in range(5):
        x = (i / 4) * svg_width
        svg_lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{svg_height}" stroke="#ddd" stroke-width="1"/>')
        y = (i / 4) * svg_height
        svg_lines.append(f'<line x1="0" y1="{y}" x2="{svg_width}" y2="{y}" stroke="#ddd" stroke-width="1"/>')
    
    # Add POI markers and pictures
    y_offset = 50
    for idx, (point, image_path) in enumerate(points_with_images):
        x = lon_to_x(point.longitude)
        y = lat_to_y(point.latitude)
        
        # Marker circle
        svg_lines.append(f'<circle cx="{x}" cy="{y}" r="8" class="marker-circle"/>')
        
        # POI label
        title = html.escape(point.name or point.description or "POI")
        svg_lines.append(f'<text x="{x + 12}" y="{y}" class="marker-text">{title}</text>')
        
        # Embed image as base64
        try:
            with open(image_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Determine image type
            img_ext = image_path.suffix.lower()
            mime_type = 'image/jpeg' if img_ext in ['.jpg', '.jpeg'] else 'image/png'
            
            # Add embedded image below the map
            img_x = 20
            img_y = y_offset
            img_size = 150
            
            svg_lines.append(f'<g>')
            svg_lines.append(f'  <rect x="{img_x - 5}" y="{img_y - 5}" width="{img_size + 10}" height="{img_size + 10}" fill="white" stroke="#ccc" stroke-width="1"/>')
            svg_lines.append(f'  <image x="{img_x}" y="{img_y}" width="{img_size}" height="{img_size}" href="data:{mime_type};base64,{img_data}"/>')
            svg_lines.append(f'  <text x="{img_x}" y="{img_y + img_size + 20}" font-size="12" font-weight="bold">{title}</text>')
            if point.description:
                desc = html.escape(point.description[:50])
                svg_lines.append(f'  <text x="{img_x}" y="{img_y + img_size + 35}" font-size="10" fill="#666">{desc}</text>')
            svg_lines.append(f'</g>')
            
            y_offset += img_size + 70
        except Exception as e:
            pass  # Skip image if can't read
    
    svg_lines.append('</svg>')
    
    return '\n'.join(svg_lines)


@app.get("/export-poi-map-svg")
def export_poi_map_svg():
    """Export POI map with embedded pictures as SVG"""
    with Session(points_engine) as session:
        statement = select(PointOfInterest).where(PointOfInterest.picture_path != None)
        points = session.exec(statement).all()

    valid_points = []
    for point in points:
        if not point.picture_path:
            continue
        image_path = Path(point.picture_path)
        if image_path.is_file():
            valid_points.append((point, image_path))

    svg_content = generate_svg_map(valid_points)
    
    return StreamingResponse(
        iter([svg_content]),
        media_type="image/svg+xml",
        headers={"Content-Disposition": "attachment; filename=poi-map-export.svg"}
    )
