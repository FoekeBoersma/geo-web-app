import osmnx as ox
import networkx as nx

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

def get_place_center(place_name: str) -> tuple[float, float]:
    """
    Get the center coordinates (latitude, longitude) of a place using OSM data.
    :param place_name: Name of the place to geocode.
    :return: Tuple of (latitude, longitude)."""
    gdf = ox.geocode_to_gdf(place_name)
    if gdf.empty: 
        raise ValueError(f"Place '{place_name}' not found.")
    centroid = gdf.iloc[0].geometry.centroid
    return centroid.y, centroid.x  # Return as (latitude, longitude)

def _build_isochrone_from_point(lat: float, lon: float, minutes = int, network_type: str = "walk") -> dict:
    if minutes <= 0:
        raise ValueError("Minutes must be a positive integer.")

    allowed = {"walk", "bike", "drive"}

    if network_type not in allowed:
        raise ValueError(f"Invalid network_type '{network_type}'. Allowed values are: {allowed}")

    speed_kph_by_type = {
        "walk": 5.0,
        "bike": 15.0,
        "drive": 50.0
    }
    speed_kph = speed_kph_by_type[network_type]
    meters_per_minute = (speed_kph * 1000) / 60

    graph_dist = int(minutes * meters_per_minute)

    # Download and create a graph within some distance of a lat-lon point
    G = ox.graph_from_point((lat,lon), dist=graph_dist, network_type=network_type)

    # add time travel to each edge
    for _, _, _, data in G.edges(keys=True, data=True):
        """
        _, _, _, data means: “I know this loop gives me 4 values, but I only care about the 4th one.”

        In loop, NetworkX yields something like:

        from-node
        to-node
        edge key
        edge attributes dict (data) --> only this is relevant to us
        """
        length_m = data.get("length", 0)
        data["travel_time"] = (length_m / meters_per_minute) if length_m else 0

    # Pick a center node robustly, thereby avoiding optional nearest-neighbor deps.
    center_node = min(
        G.nodes,
        key=lambda n: (G.nodes[n]["y"] - lat) ** 2 + (G.nodes[n]["x"] - lon) ** 2
    )

    subgraph = nx.ego_graph(G, center_node, radius=minutes, distance="travel_time")
    if subgraph.number_of_nodes() == 0:
        raise ValueError(f"No reachable area found within {minutes} minutes from the given point.") 

    # Convert subgraph nodes to a polygon
    nodes_gdf = ox.graph_to_gdfs(subgraph, edges=False)
    polygon = nodes_gdf.geometry.unary_union.convex_hull
    if polygon.is_empty:
        raise ValueError(f"Could not create an isochrone polygon for the reachable area from '{place_name}'.")

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "place": place_name,
                    "minutes": minutes,
                    "network_type": network_type
                },
                "geometry": polygon.__geo_interface__

            }
        ],
        "center": {
            "lat": lat,
            "lon": lon
        }
    }

def fetch_isochrone(place_name: str, minutes: int, network_type: str = "walk") -> dict:
    lat, lon = get_place_center(place_name)
    geojson = _build_isochrone_from_point(lat, lon, minutes, network_type)
    geojson["features"][0]["properties"]["place"] = place_name
    return geojson


