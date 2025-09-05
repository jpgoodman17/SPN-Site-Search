from typing import Dict, Any, Optional
from .arcgis_utils import query_point_buffer
from .config import ENDPOINTS

def lookup_municipality(lon: float, lat: float) -> Optional[Dict[str, Any]]:
    """Query NYS Civil Boundaries MapServer for Towns/Cities/Villages at a point."""
    # Towns layer is commonly index 3 or 4; we try multiple
    candidates = [f"{ENDPOINTS['civil_boundaries_mapserver']}/{i}" for i in (3,4,5,6)]
    for layer in candidates:
        try:
            res = query_point_buffer(layer, lon, lat, 0.01, out_fields="*")
            if res.get("features"):
                attrs = res["features"][0]["attributes"]
                return {"layer": layer, "name": attrs.get("NAME") or attrs.get("TOWN") or attrs.get("CITY") or attrs.get("VILLAGE"),
                        "county": attrs.get("COUNTY") or attrs.get("COUNTY_NAME")}
        except Exception:
            continue
    return None
