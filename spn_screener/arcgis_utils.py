# spn_screener/arcgis_utils.py
# Safe ArcGIS helpers that won't crash if the server returns HTML or empty text.

from typing import Dict, Any
import requests

def _safe_json(resp: requests.Response) -> Dict[str, Any]:
    """Return JSON if possible; otherwise return an empty, harmless structure."""
    try:
        return resp.json()
    except Exception:
        return {
            "features": [],
            "error": "non_json_response",
            "status_code": getattr(resp, "status_code", None),
            "text_snippet": resp.text[:200] if hasattr(resp, "text") else None,
        }

def query_point_buffer(layer_url: str, lon: float, lat: float, radius_miles: float, out_fields: str = "*") -> Dict[str, Any]:
    """Query an ArcGIS layer around a point + radius. Returns empty features on failure."""
    buffer_m = radius_miles * 1609.344
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
    headers = {"User-Agent": "SPN-Screener/0.1"}
    try:
        r = requests.get(f"{layer_url}/query", params=params, headers=headers, timeout=25)
        r.raise_for_status()
        return _safe_json(r)
    except Exception as e:
        return {"features": [], "error": f"request_failed: {e}"}

def query_polygon_intersect(layer_url: str, polygon_geojson: Dict[str, Any], out_fields: str = "*") -> Dict[str, Any]:
    """Query an ArcGIS layer for features intersecting a polygon."""
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
    headers = {"User-Agent": "SPN-Screener/0.1"}
    try:
        r = requests.post(f"{layer_url}/query", json=params, headers=headers, timeout=45)
        r.raise_for_status()
        return _safe_json(r)
    except Exception as e:
        return {"features": [], "error": f"request_failed: {e}"}

