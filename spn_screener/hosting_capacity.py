from typing import Dict, Any, Optional, Tuple
import requests, math
from .config import ENDPOINTS
from .arcgis_utils import query_point_buffer

def get_national_grid_feeders_near(lon: float, lat: float, radius_miles: float) -> Dict[str, Any]:
    """Pull nearby hosting capacity features from National Grid NY MapServer.
    The root has multiple layers; in production you would iterate layers to find the feeder lines / nodes with HC attributes.
    """
    # Example layer 0 often contains feeders — adjust as needed by inspecting the service.
    layer_url = f"{ENDPOINTS['ng_hosting_capacity_root']}/0"
    data = query_point_buffer(layer_url, lon, lat, radius_miles, out_fields="*")
    return data

def summarize_best_capacity(features: Dict[str, Any], capacity_field_candidates=("PVHC_MW", "HC_MW", "Avail_MW", "AvailHC_MW")):
    """Safely pick the largest available capacity value from returned features."""
    best = None
    for feat in features.get("features", []):
        attrs = feat.get("attributes", {}) or {}
        cap = next((attrs.get(f) for f in capacity_field_candidates if isinstance(attrs.get(f), (int, float))), None)
        if cap is None:
            continue
        dist_m = 0.0  # distance calculation omitted in prototype
        if best is None or float(cap) > best[0]:
            best = (float(cap), dist_m)
    return best  # may be None if no capacity fields found

