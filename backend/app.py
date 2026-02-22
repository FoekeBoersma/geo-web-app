# -*- coding: utf-8 -*-
from fastapi import FastAPI
from .fetch_osm_data import fetch_osm_data

app = FastAPI()

@app.get("/fetch_osm_data")
def fetch_osm_data_endpoint(placename: str):
    try:
        data = fetch_osm_data(placename)
        return {"status": 200, "data": data}
    except Exception as e:
        return {"status": 500, "error": str(e)}
    