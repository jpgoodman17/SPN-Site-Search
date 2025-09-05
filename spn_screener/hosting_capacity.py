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

def summarize_best_capacity(features: Dict[str, Any], capacity_field_candidates=("PVHC_MW","HC_MW","Avail_MW","AvailHC_MW")) -> Optional[Tuple[float, float]]:
    """Return (best_capacity_mw, distance_m) from the result features if a capacity field is present."""
    best = None
    for feat in features.get("features", []):
        attrs = feat.get("attributes", {})
        cap = None
        for f in capacity_field_candidates:
            if f in attrs and isinstance(attrs[f], (int,float)):
                cap = attrs[f]; break
        if cap is None: 
            continue
        # naive distance if geometry has 'paths' or 'rings' — else skip
        # For brevity, we won't compute accurate distance here; consider using shapely in production
        dist_m = 0.0
        cand = (cap, dist_m)
        if best is None or cap > best[0]:
            best = cand
    return best
