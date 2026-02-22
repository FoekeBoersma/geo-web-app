import osmnx as ox

def fetch_osm_data(place_name):
    gdf = ox.geocode_to_gdf(place_name)
    # Convert to dictionaries with coordinates that is JSON serializable
    result = []
    for idx, row in gdf.iterrows():
        result.append({
            "name": row.get("name", place_name),
            "lat": row.geometry.centroid.y,
            "lon": row.geometry.centroid.x,
            "bbox": {
                "north": row.geometry.bounds[3],
                "south": row.geometry.bounds[1],
                "east": row.geometry.bounds[2],
                "west": row.geometry.bounds[0]
            }
        })
    return result if result else [{"name": place_name, "lat": None, "lon": None}]
