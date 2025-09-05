from typing import Dict, Any
import requests

def _safe_json(resp: requests.Response) -> Dict[str, Any]:
    try:
        return resp.json()
    except Exception:
        # Return an empty, harmless structure so pipeline can continue
        return {"features": [], "error": "non_json_response", "status_code": resp.status_code, "text_snippet": resp.text[:200]}

def query_point_buffer(layer_url: str, lon: float, lat: float, radius_miles: float, out_fields: str = "*") -> Dict[str, Any]:
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

def query_polygon_intersect(layer_url: str, polygon_geojson: Dict[str, Any], out_fields: str="*") -> Dict[str, Any]:
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

