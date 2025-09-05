# Placeholder: CDL fetch via ArcGIS or STAC; here we simply pass through a `cleared_hint` or acres
def estimate_cleared_acres(acres: float, cleared_hint: str = "") -> float:
    """Very rough heuristic until CDL/NLCD raster intersection is wired in.
    If hint includes 'majority cleared' -> 0.8, 'mostly cleared' -> 0.7, 'partially' -> 0.5; else 0.6
    """
    hint = (cleared_hint or "").lower()
    if "majority" in hint: frac = 0.8
    elif "mostly" in hint: frac = 0.7
    elif "partial" in hint: frac = 0.5
    elif "pasture" in hint or "hay" in hint or "farm" in hint or "field" in hint: frac = 0.75
    else: frac = 0.6
    return round(acres * frac, 2)
