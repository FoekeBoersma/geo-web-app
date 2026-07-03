# -*- coding: utf-8 -*-
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, UploadFile, Form, File
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import asynccontextmanager
from sqlmodel import Session, SQLModel

from backend.db import init_db
from .fetch_osm_data import fetch_osm_data
from fastapi.middleware.cors import CORSMiddleware
import httpx # useful for async requests; parallel API calls; potentially faster response times
from dotenv import load_dotenv
import os
import math
from .models import RouteLog
from .db import route_engine, points_engine, init_db  
import shutil
from .models import PointOfInterest

import json
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
        points = session.exec(
            select(PointOfInterest)
        ).all()
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

@app.post(("/create-route"))
def create_route(origin: str, destination: str, geojson: str):
    with Session(route_engine) as session:
        route  = RouteLog(
            origin=origin,
            destination=destination,
            geojson=geojson
        )
        session.add(route)
        session.commit()
        session.refresh(route)
        return {"status": "saved", "id": route.id}
    

@app.get("/routes")
def get_routes():
    with Session(route_engine) as session:
        return session.exec(select(RouteLog)).all()


def generate_svg_map(points_with_images, zoom=None, bbox=None, mode=None, route_coords=None):
    """Generate SVG with basemap, numbered POI markers, and linked pictures"""
    if not points_with_images:
        raise HTTPException(status_code=404, detail="No points of interest with images found.")

    map_width = 1200
    map_height = 600

    latitudes = [p.latitude for p, _ in points_with_images]
    longitudes = [p.longitude for p, _ in points_with_images]
    poi_min_lat, poi_max_lat = min(latitudes), max(latitudes)
    poi_min_lon, poi_max_lon = min(longitudes), max(longitudes)

    use_map_view = bool(bbox)
    if use_map_view:
        min_lon, min_lat, max_lon, max_lat = map(float, bbox.split(","))
        center_lon = (min_lon + max_lon) / 2
        center_lat = (min_lat + max_lat) / 2
    else:
        min_lat, max_lat = poi_min_lat, poi_max_lat
        min_lon, max_lon = poi_min_lon, poi_max_lon
        center_lat = sum(latitudes) / len(latitudes)
        center_lon = sum(longitudes) / len(longitudes)

    def deg2tile(lon, lat, z):
        lat_rad = math.radians(lat)
        n = 2.0 ** z
        xtile = (lon + 180.0) / 360.0 * n
        ytile = (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n
        return xtile, ytile

    def deg2px(lon, lat, z):
        lat_rad = math.radians(lat)
        n = 2.0 ** z
        x = (lon + 180.0) / 360.0 * n * 256
        y = (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n * 256
        return x, y

    def choose_zoom():
        if len(points_with_images) < 2 or (max_lat == min_lat and max_lon == min_lon):
            return 10

        x_min_14, y_top_14 = deg2px(min_lon, max_lat, 14)
        x_max_14, y_bottom_14 = deg2px(max_lon, min_lat, 14)
        width_px_14 = abs(x_max_14 - x_min_14)
        height_px_14 = abs(y_bottom_14 - y_top_14)

        if width_px_14 == 0 or height_px_14 == 0:
            return 10

        width_scale = map_width / width_px_14
        height_scale = map_height / height_px_14
        target_scale = max(width_scale, height_scale) * 0.7

        zoom_offset = math.floor(math.log2(target_scale)) if target_scale > 1 else 0
        computed_zoom = 14 - zoom_offset
        return max(8, min(12, computed_zoom))

    if zoom is None:
        zoom = choose_zoom()


    center_xtile, center_ytile = deg2tile(center_lon, center_lat, zoom)
    tile_x = int(center_xtile)
    tile_y = int(center_ytile)

    # Build a small mosaic of tiles around the center to give context and correct offsets
    tile_span = 3  # 3x3 tiles with the center tile in the middle
    half_span = tile_span // 2

    tiles = []  # list of tuples (tx, ty, b64)
    for dx in range(-half_span, half_span + 1):
        for dy in range(-half_span, half_span + 1):
            tx = tile_x + dx
            ty = tile_y + dy
            tile_url = f"https://tile.openstreetmap.org/{zoom}/{tx}/{ty}.png"
            try:
                tile_resp = httpx.get(tile_url, timeout=10.0)
                tile_resp.raise_for_status()
                tile_png = tile_resp.content
                tile_b64 = base64.b64encode(tile_png).decode('utf-8')
            except Exception:
                tile_b64 = None
            tiles.append((tx, ty, tile_b64))

    map_width = 1200
    map_height = 600
    total_height = map_height + (len(points_with_images) * 220)

    # Convert tile-space pixels to svg pixels for the mosaic (mosaic pixel width = tile_span*256)
    mosaic_px_width = tile_span * 256
    mosaic_px_height = tile_span * 256
    def globalpx_to_svg(px):
        return px * (map_width / mosaic_px_width)
    
    svg_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{map_width}" height="{total_height}" viewBox="0 0 {map_width} {total_height}">',
        '<defs><style>',
        '.coord-text { font-size: 9px; fill: #999; }',
        '.gallery-title { font-size: 18px; font-weight: bold; fill: black; }',
        '.gallery-item { stroke: #333; stroke-width: 1; fill: white; }',
        '.gallery-label { font-size: 12px; fill: black; }',
        '</style></defs>',
    ]
    
    svg_lines.append(f'<rect x="0" y="0" width="{map_width}" height="{map_height}" fill="#e9f7fd"/>')

    # Place mosaic tiles into the SVG. compute scaling separately for x/y to preserve map aspect.
    start_tx = tile_x - half_span
    start_ty = tile_y - half_span
    scale_x = map_width / mosaic_px_width
    scale_y = map_height / mosaic_px_height
    tile_w_svg = 256 * scale_x
    tile_h_svg = 256 * scale_y
    for tx, ty, tb64 in tiles:
        if not tb64:
            continue
        px_off = (tx - start_tx) * 256
        py_off = (ty - start_ty) * 256
        x_svg = px_off * scale_x
        y_svg = py_off * scale_y
        svg_lines.append(f'<image x="{x_svg}" y="{y_svg}" width="{tile_w_svg}" height="{tile_h_svg}" href="data:image/png;base64,{tb64}" preserveAspectRatio="none"/>')
    
    svg_lines.append(f'<rect x="0" y="0" width="{map_width}" height="{map_height}" fill="none" stroke="#333" stroke-width="2"/>')

    if route_coords:
        points = []
        for lon, lat in route_coords:
            px, py = deg2px(lon, lat, zoom)
            svg_x = (px - (start_tx * 256)) * scale_x
            svg_y = (py - (start_ty * 256)) * scale_y
            points.append(f"{svg_x},{svg_y}")

        svg_lines.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="#0074d9" stroke-width="4"/>')
    
    # Draw simple latitude/longitude grid lines
    for i in range(1, 4):
        x = i * (map_width / 4)
        y = i * (map_height / 4)
        svg_lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{map_height}" stroke="#ffffff" stroke-width="1" opacity="0.6"/>')
        svg_lines.append(f'<line x1="0" y1="{y}" x2="{map_width}" y2="{y}" stroke="#ffffff" stroke-width="1" opacity="0.6"/>')
    
    # marker placement relative to mosaic origin
    for idx, (point, _) in enumerate(points_with_images):
        px, py = deg2px(point.longitude, point.latitude, zoom)
        svg_x = (px - (start_tx * 256)) * scale_x
        svg_y = (py - (start_ty * 256)) * scale_y
        poi_number = idx + 1
        
        svg_lines.append(f'<circle cx="{svg_x}" cy="{svg_y}" r="18" fill="#ff6b6b" stroke="white" stroke-width="3"/>')
        svg_lines.append(f'<text x="{svg_x}" y="{svg_y + 1}" text-anchor="middle" dominant-baseline="middle" fill="white" font-size="14" font-weight="bold">{poi_number}</text>')
        title = html.escape(point.name or point.description or f"POI {poi_number}")
        svg_lines.append(f'<text x="{svg_x + 25}" y="{svg_y - 5}" fill="#111" font-size="12">{title[:30]}</text>')
        svg_lines.append(f'<text x="{svg_x + 25}" y="{svg_y + 12}" fill="#555" font-size="10">({point.latitude:.2f}, {point.longitude:.2f})</text>')
    
    gallery_y = map_height + 40
    svg_lines.append(f'<text x="20" y="{gallery_y}" class="gallery-title">Photo Gallery</text>')
    
    gallery_y += 30
    for idx, (point, image_path) in enumerate(points_with_images):
        poi_number = idx + 1
        
        try:
            with open(image_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
            img_ext = image_path.suffix.lower()
            mime_type = 'image/jpeg' if img_ext in ['.jpg', '.jpeg'] else 'image/png'
            img_x = 20
            img_y = gallery_y
            img_size = 180
            svg_lines.append(f'<rect x="{img_x}" y="{img_y}" width="{img_size + 10}" height="{img_size + 50}" class="gallery-item"/>')
            svg_lines.append(f'<circle cx="{img_x + 10}" cy="{img_y + 10}" r="15" fill="#ff6b6b"/>')
            svg_lines.append(f'<text x="{img_x + 10}" y="{img_y + 15}" text-anchor="middle" dominant-baseline="middle" fill="white" font-size="14" font-weight="bold">{poi_number}</text>')
            svg_lines.append(f'<image x="{img_x + 5}" y="{img_y + 5}" width="{img_size}" height="{img_size}" href="data:{mime_type};base64,{img_data}"/>')
            title = html.escape(point.name or point.description or f"POI {poi_number}")
            svg_lines.append(f'<text x="{img_x + 5}" y="{img_y + img_size + 20}" class="gallery-label" font-weight="bold">{title[:25]}</text>')
            if point.description:
                desc = html.escape(point.description[:50])
                svg_lines.append(f'<text x="{img_x + 5}" y="{img_y + img_size + 35}" class="gallery-label" fill="#666">{desc}</text>')
            gallery_y += img_size + 70
        except Exception:
            pass
    
    svg_lines.append('</svg>')
    return '\n'.join(svg_lines)



@app.get("/export-poi-map-svg")
def export_poi_map_svg(zoom: Optional[int] = None, bbox: Optional[str] = None, mode: str = "map", route: Optional[str] = None):
    """Export POI map with embedded pictures as SVG
    Add optional query parameters for map state (zoom level, bbox) to render the same view as the frontend map.
    """

    route_coords = None
    if route:
        try:
            route_json = json.loads(route)
            if isinstance(route_json, dict):
                features = route_json.get("features") or []
                if features:
                    geometry = features[0].get("geometry") or {}
                    route_coords = geometry.get("coordinates")
        except (TypeError, ValueError, json.JSONDecodeError):
            route_coords = None
    
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

    svg_content = generate_svg_map(valid_points, zoom=zoom, bbox=bbox, mode=mode, route_coords=route_coords)
    
    return StreamingResponse(
        iter([svg_content]),
        media_type="image/svg+xml",
        headers={"Content-Disposition": "attachment; filename=poi-map-export.svg"}
    )
