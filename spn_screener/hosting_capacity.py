# spn_screener/hosting_capacity.py
# Color-based hosting capacity screening for National Grid (NY).
# We detect "potential capacity" if any nearby HC feature is rendered in BLUE or GREEN
# on the utility’s ArcGIS web map. (Other utilities can be added similarly.)

from typing import Dict, Any, List, Optional, Tuple
import requests

from .arcgis_utils import query_point_buffer

# -------------------------
# National Grid (NY) Web Map item (ArcGIS Online) for PV Hosting Capacity
# We read its operational layers and inspect their renderers for blue/green symbology.
# -------------------------
NG_WEBMAP_ITEM = "25aa1fb79d7b44b4be119b8753430474"  # PV Hosting Capacity Web Map (public)

# Some capacity fields we might see if/when numeric HC is available
_CAP_FIELDS = ("PVHC_MW", "HC_MW", "Avail_MW", "AvailHC_MW", "PVHostingCapacityMW")


# ---------- Basic color helpers ----------
def _is_green(rgb: List[int]) -> bool:
    """
    Accept any shade of green: G dominant and reasonably bright.
    ESRI color arrays are typically [r, g, b, a]; we ignore alpha.
    """
    if not (isinstance(rgb, list) and len(rgb) >= 3):
        return False
    r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
    return (g >= 120) and (g > r + 20) and (g > b + 20)


def _is_blue(rgb: List[int]) -> bool:
    """
    Accept any shade of blue: B dominant and reasonably bright.
    """
    if not (isinstance(rgb, list) and len(rgb) >= 3):
        return False
    r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
    return (b >= 120) and (b > r + 20) and (b > g + 20)


# ---------- Renderer parsing ----------
def _extract_colored_classes(renderer: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse an ESRI renderer (simple / uniqueValue / classBreaks) and return:
      {
        "fields": [field names that drive the renderer]  (may be empty)
        "accept_all": True if the whole layer is blue/green (simple renderer)
        "accept_values": set([...]) for unique value classes that are blue/green
        "accept_ranges": [(min, max), ...] for class breaks in blue/green
      }
    """
    out = {
        "fields": [],
        "accept_all": False,
        "accept_values": set(),
        "accept_ranges": []  # list of (min, max)
    }
    if not isinstance(renderer, dict):
        return out

    rtype = (renderer.get("type") or "").lower()

    # Simple renderer: if the symbol is blue/green, accept all features
    if rtype == "simple":
        sym = renderer.get("symbol", {}) or {}
        color = sym.get("color") or (sym.get("outline", {}) or {}).get("color")
        if isinstance(color, list) and (_is_blue(color) or _is_green(color)):
            out["accept_all"] = True
        return out

    # Unique value renderer
    if rtype == "uniquevalue":
        fields = [renderer.get("field1"), renderer.get("field2"), renderer.get("field3")]
        out["fields"] = [f for f in fields if f]
        for info in (renderer.get("uniqueValueInfos") or []):
            sym = (info or {}).get("symbol", {}) or {}
            color = sym.get("color") or (sym.get("outline", {}) or {}).get("color")
            if isinstance(color, list) and (_is_blue(color) or _is_green(color)):
                # Accept this class's "value"
                val = info.get("value")
                if val is not None:
                    out["accept_values"].add(val)
        return out

    # Class breaks renderer
    if rtype == "classbreaks":
        field = renderer.get("field")
        if field:
            out["fields"] = [field]
        for info in (renderer.get("classBreakInfos") or []):
            sym = (info or {}).get("symbol", {}) or {}
            color = sym.get("color") or (sym.get("outline", {}) or {}).get("color")
            if isinstance(color, list) and (_is_blue(color) or _is_green(color)):
                mn = info.get("minValue")
                mx = info.get("maxValue")
                out["accept_ranges"].append((mn, mx))
        return out

    return out


# ---------- ArcGIS helpers ----------
def _get_layer_urls_from_webmap(item_id: str) -> List[str]:
    """
    Read an ArcGIS Web Map item and extract all operational layer URLs (and sublayers).
    """
    try:
        item_url = f"https://www.arcgis.com/sharing/rest/content/items/{item_id}/data"
        r = requests.get(item_url, params={"f": "json"}, timeout=20)
        r.raise_for_status()
        data = r.json()
        urls: List[str] = []
        for lyr in (data.get("operationalLayers") or []):
            if isinstance(lyr, dict):
                if isinstance(lyr.get("url"), str):
                    urls.append(lyr["url"])
                for sl in (lyr.get("layers") or []):
                    if isinstance(sl, dict) and isinstance(sl.get("url"), str):
                        urls.append(sl["url"])
        # dedupe while preserving order
        return list(dict.fromkeys(urls))
    except Exception:
        return []


def _get_renderer_for_layer(layer_url: str) -> Optional[Dict[str, Any]]:
    """
    Fetch the layer metadata and return drawingInfo.renderer if present.
    """
    try:
        r = requests.get(layer_url, params={"f": "pjson"}, timeout=15)
        r.raise_for_status()
        meta = r.json()
        di = meta.get("drawingInfo") or {}
        return di.get("renderer")
    except Exception:
        return None


def _feature_is_blue_green(attrs: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    """
    Decide whether a feature's attributes match a blue/green class/range from the renderer.
    If 'accept_all' is True, all features match.
    Otherwise:
      - if 'fields' + 'accept_values' given, check equality on the first field
      - if 'fields' + 'accept_ranges' given, check numeric min/max on the first field
    """
    if rule.get("accept_all"):
        return True

    fields: List[str] = rule.get("fields") or []
    if not fields:
        return False

    key = fields[0]
    val = attrs.get(key)

    # Unique values case
    if rule.get("accept_values"):
        return val in rule["accept_values"]

    # Class breaks case
    for (mn, mx) in rule.get("accept_ranges") or []:
        try:
            x = float(val)
        except (TypeError, ValueError):
            continue
        if (mn is None or x >= float(mn)) and (mx is None or x <= float(mx)):
            return True

    return False


# ---------- Public API used by pipeline ----------
def get_national_grid_feeders_near(lon: float, lat: float, radius_miles: float) -> Dict[str, Any]:
    """
    Backwards-compatible: return a pseudo-FeatureSet for pipeline integration.
    This function now gathers features from all HC layers in NG's web map.
    """
    features_all: Dict[str, Any] = {"features": []}
    urls = _get_layer_urls_from_webmap(NG_WEBMAP_ITEM)
    for u in urls:
        try:
            res = query_point_buffer(u, lon, lat, radius_miles, out_fields="*")
            if isinstance(res, dict) and res.get("features"):
                features_all["features"].extend(res["features"])
        except Exception:
            continue
    return features_all


def summarize_best_capacity(features: Dict[str, Any], capacity_field_candidates: Tuple[str, ...] = _CAP_FIELDS):
    """
    Try to extract a numeric capacity (MW) if present. If none found, return None.
    """
    best = None
    for feat in features.get("features", []):
        attrs = feat.get("attributes", {}) or {}
        cap = next((attrs.get(f) for f in capacity_field_candidates if isinstance(attrs.get(f), (int, float))), None)
        if cap is None:
            continue
        dist_m = 0.0  # distance omitted in prototype
        capf = float(cap)
        if best is None or capf > best[0]:
            best = (capf, dist_m)
    return best


def has_blue_green_capacity_ng(lon: float, lat: float, radius_miles: float) -> bool:
    """
    Return True if any feature within the radius belongs to a layer whose renderer
    marks blue/green classes (or is entirely blue/green).
    """
    urls = _get_layer_urls_from_webmap(NG_WEBMAP_ITEM)
    if not urls:
        return False

    # Build renderer rules for each layer
    rules_by_layer: Dict[str, Dict[str, Any]] = {}
    for u in urls:
        ren = _get_renderer_for_layer(u)
        if ren:
            rules_by_layer[u] = _extract_colored_classes(ren)

    # If no renderer info, we can't color-screen
    if not rules_by_layer:
        return False

    # Query each layer and test features against its rule
    for u in urls:
        rule = rules_by_layer.get(u)
        if not rule:
            continue
        try:
            res = query_point_buffer(u, lon, lat, radius_miles, out_fields="*")
            for feat in res.get("features", []):
                attrs = feat.get("attributes", {}) or {}
                if _feature_is_blue_green(attrs, rule):
                    return True
        except Exception:
            continue

    return False

