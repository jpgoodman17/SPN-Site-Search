def summarize_best_capacity(features: Dict[str, Any], capacity_field_candidates=("PVHC_MW","HC_MW","Avail_MW","AvailHC_MW")):
    best = None
    for feat in features.get("features", []):
        attrs = feat.get("attributes", {}) or {}
        cap = next((attrs.get(f) for f in capacity_field_candidates if isinstance(attrs.get(f), (int, float))), None)
        if cap is None:
            continue
        dist_m = 0.0
        if best is None or cap > best[0]:
            best = (float(cap), dist_m)
    return best

