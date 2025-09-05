from typing import Dict, Any, Optional, Tuple
import requests, math
from .config import ENDPOINTS
from .arcgis_utils import query_point_buffer
import requests

# National Grid NY PV Hosting Capacity Web Map item (ArcGIS Online)
NG_WEBMAP_ITEM = "25aa1fb79d7b44b4be119b8753430474"

def _get_ng_layer_urls_from_webmap() -> list[str]:
    """Return a list of FeatureServer/MapServer layer URLs from NG's PV Hosting Capacity web map."""
    try:
        item_url = f"https://www.arcgis.com/sharing/rest/content/items/{NG_WEBMAP_ITEM}/data"
        r = requests.get(item_url, params={"f": "json"}, timeout=20)
        r.raise_for_status()
        data = r.json()
        urls = []
        for lyr in (data.get("operationalLayers") or []):
            # Some layers have a direct "url", some are group layers with sublayers
            if "url" in lyr and isinstance(lyr["url"], str):
                urls.append(lyr["url"])
            for sl in (lyr.get("layers") or []):
                if "url" in sl and isinstance(sl["url"], str):
                    urls.append(sl["url"])
        # Deduplicate
        urls = list(dict.fromkeys(urls))
        return urls
    except Exception:
        return []

from .arcgis_utils import query_point_buffer

# Fields we've seen on NG HC layers. Adjust if NG changes field names.
_CAP_FIELDS = ("PVHC_MW", "HC_MW", "Avail_MW", "AvailHC_MW", "PVHostingCapacityMW")

def get_national_grid_feeders_near(lon: float, lat: float, radius_miles: float) -> dict:
    """Query all NG PV Hosting Capacity layers near a point and merge features."""
    features_all = {"features": []}
    urls = _get_ng_layer_urls_from_webmap()
    for u in urls:
        try:
            res = query_point_buffer(u, lon, lat, radius_miles, out_fields="*")
            if isinstance(res, dict) and res.get("features"):
                features_all["features"].extend(res["features"])
        except Exception:
            continue
    return features_all

def summarize_best_capacity(features: Dict[str, Any], capacity_field_candidates=_CAP_FIELDS):
    """Safely pick the largest available capacity value from returned features."""
    best = None
    for feat in features.get("features", []):
        attrs = feat.get("attributes", {}) or {}
        cap = next((attrs.get(f) for f in capacity_field_candidates if isinstance(attrs.get(f), (int, float))), None)
        if cap is None:
            continue
        dist_m = 0.0  # (optional) compute geometry distance later
        if best is None or float(cap) > best[0]:
            best = (float(cap), dist_m)
    return best

