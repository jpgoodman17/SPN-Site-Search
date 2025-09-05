# spn_screener/hosting_capacity.py
# Color-based hosting capacity screening:
# - Pull the utility's ArcGIS Web Map (when public)
# - Read layer renderers for blue/green symbology
# - Query features within the search radius
# - If any features with blue/green classes are near the site, flag "potential capacity"

from typing import Dict, Any, List, Optional, Tuple
import requests

from .arcgis_utils import query_point_buffer

# --- Public ArcGIS "web map" items (or landing pages) per utility ---
# National Grid NY: public web map item (PV/ESS HC) -> we can read renderer/colors
NG_WEBMAP_ITEM = "25aa1fb79d7b44b4be119b8753430474"  # PV Hosting Capacity Web Map (NY System Data Portal) :contentReference[oaicite:0]{index=0}

# Avangrid (NYSEG/RG&E) & O&R/Central Hudson often require a portal login for full layer URLs.
# We'll still try to resolve, but if not accessible, we fail-soft (no crash) and return no URLs.
AVANGRID_PORTAL_APPID = "5fc7fc4820af48838cb5bdfd54e5baad"  # NYSEG/RGE Hosting Capacity Portal (Instant App) :contentReference[oaicite:1]{index=1}

# Central Hudson links (maps are public pages; underlying layers sometimes shift)
# We'll attempt to parse if exposed in the public web map; otherwise skip. :contentReference[oaicite:2]{index=2}

# --- Color helpers ----------------------------------------------------

def _is_green(rgb: List[int]) -> bool:
    # Accept any shade of green: G dominant, reasonably bright
    if len(rgb) < 3: return False
    r, g, b = rgb[0], rgb[1], rgb[2]
    return (g >= 120) and (g > r + 20) and (g > b + 20)

def _is_blue(rgb: List[int]) -> bool:
    # Accept any shade of blue: B dominant, reasonably bright
    if len(rgb) < 3: return False
    r, g, b = rgb[0], rgb[1], rgb[2]
    return (b >= 120) and (b > r + 20) and (b > g + 20)

def _extract_colored_classes(renderer: Dict[str, Any]) -> Dict[str, Any]:
    """
    Look at an ESRI renderer (simple/uniqueValue/classBreaks) and return a spec
    describing which classes are blue/green, and which field(s) drive the renderer.
    """
    out = {"fields": [], "accept_values": set(), "accept_ranges": []}  # values for uniqueValue; ranges for classBreaks
    if not isinstance(renderer, dict): 
        return out

    rtype = (renderer.get("type") or "").lower()

    # Simple renderer: if the lineSymbol is blue/green, just accept all features
    if rtype == "simple":
        sym = renderer.get("symbol", {})
        color = sym.get("color") or sym.get("outline", {}).get("color")
        if isinstance(color, list) and (_is_blue(color) or _is_green(color)):
            out["fields"] = []  # no filtering by attribute
            out["accept_values"] = {"__ALL__"}
        return out

    # Unique value renderer: check each class' symbol color
    if rtype == "uniquevalue":
        fields = [renderer.get("field1"), renderer.get("field2"), renderer.get("field3")]
        out["fields"] = [f for f in fields if f]
        for info in (renderer.get("uniqueValueInfos") or []):
            sym = (info or {}).get("symbol", {})
            color = sym.get("color") or sym.get("outline", {}).get("color")
            if isinstance(color, list) and (_is_blue(color) or _is_green(color)):
                if "value" in info:
                    out["accept_values"].add(info["value"])
        return out

    # Class breaks renderer: accept ranges whose symbol is blue/green
    if rtype == "classbreaks":
        field = renderer.get("field")
        if field: out["fields"] = [field]
        for info in (renderer.get("classBreakInfos") or []):
            sym = (info or {}).get("symbol", {})
            color = sym.get("color") or sym.get("outline", {}).get("color")
            if isinstance(color, list) and (_is_blue(color) or _is_green(color)):
                mn = info.get("minValue")
                mx = info.get("maxValue")
                out["accept_ranges"].append((mn, mx))
        return out

    return out

def _get_layer_urls_from_webmap(item_id: str) -> List[str]:
    """
    Given an ArcGIS Online web map item id, return all layer URLs referenced by it.
    """
    try:
        item_url = f"https://www.arcgis.com/sharing/rest/content/items/{item_id}/data"
        r = requests.get(item_url, params={"f": "json"}, timeout=20)
        r.raise_for_status()
        data = r.json()
        urls = []
        for lyr in (data.get("operationalLayers") or []):
            if "url" in lyr and isinstance(lyr["url"], str):
                urls.append(lyr["url"])
            # Sublayers nested
            for sl in (lyr.get("layers") or []):
                if "url" in sl and isinstance(sl["url"], str):
                    urls.append(sl["url"])
        # dedupe
        return list(dict.fromkeys(urls))
    except Exception:
        return []

def _get_renderers_for_layers(layer_urls: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    For each layer URL, fetch its drawingInfo.renderer (if public).
    """
    out = {}
    for u in layer_urls:
        try:
            # /?f=pjson returns layer metadata including drawingInfo
            r = requests.get(u, params={"f": "pjson"}, timeout=15)
            r.raise_for_status()
            meta = r.json()
            renderer = (meta.get("drawingInfo") or {}).get("renderer")
            if renderer:
                out[u] = renderer
        except Exception:
            continue
    return out

def _feature_matches_color_rule(attrs: Dict[str, Any

