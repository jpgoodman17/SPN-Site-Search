from typing import Dict, Any, Optional, Tuple, List
import requests, math

def _miles_to_meters(mi: float) -> float:
    return mi * 1609.344

def query_point_buffer(layer_url: str, lon: float, lat: float, radius_miles: float, out_fields: str = "*") -> Dict[str, Any]:
    """Query an ArcGIS FeatureServer/MapServer layer by a circular buffer around lon/lat (WGS84)."""
    buffer_m = _miles_to_meters(radius_miles)
    # Use a simple circular buffer via distance= with geometry type=esriGeometryPoint
    params = {
        "f": "json",
        "where": "1=1",
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "distance": buffer_m,
        "units": "esriSRUnit_Meter",
        "outFields": out_fields,
        "returnGeometry": "true",
    }
    r = requests.get(f"{layer_url}/query", params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def query_polygon_intersect(layer_url: str, polygon_geojson: Dict[str, Any], out_fields: str="*") -> Dict[str, Any]:
    """Query a layer for features intersecting a polygon (GeoJSON in WGS84)."""
    # Convert GeoJSON polygon to ArcGIS JSON
    rings = polygon_geojson["coordinates"]
    geom = {"rings": rings, "spatialReference": {"wkid": 4326}}
    params = {
        "f": "json",
        "where": "1=1",
        "geometry": geom,
        "geometryType": "esriGeometryPolygon",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": out_fields,
        "returnGeometry": "true",
    }
    r = requests.post(f"{layer_url}/query", json=params, timeout=60)
    r.raise_for_status()
    return r.json()
