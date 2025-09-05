import csv, math
from typing import Dict, Any
from dataclasses import dataclass, asdict
from .config import SEARCH_RADIUS_MILES, DC_PER_ACRE_KW, DC_AC_RATIO
from .hosting_capacity import get_national_grid_feeders_near, summarize_best_capacity
from .boundaries import lookup_municipality
from .landcover import estimate_cleared_acres
from .wetlands import wetlands_overlaps

@dataclass
class SiteResult:
    address: str
    price_usd: float
    acres: float
    lat: float
    lon: float
    utility: str
    municipality: str
    county: str
    est_cleared_acres: float
    dec_wetlands_ac: float
    dec_adjacent_area_ac: float
    nwi_ac: float
    est_buildable_acres: float
    req_dc_kw: float
    req_ac_mw: float
    hc_feeder_best_mw: float
    decision: str
    notes: str

def detect_utility(lon: float, lat: float) -> str:
    # For prototype, rough bbox rules; production should intersect service territories layer.
    # Upstate default to one of {National Grid, NYSEG/RGE, O&R, Central Hudson}; we return "National Grid" as placeholder.
    return "National Grid"

def process_row(row: Dict[str, Any]) -> SiteResult:
    addr = f"{row['address']}, {row['city']}, {row['state']} {row['zip']}"
    price = float(row["price_usd"])
    acres = float(row["acres"])
    lat, lon = float(row["lat"]), float(row["lon"])

    utility = detect_utility(lon, lat)
    muni = lookup_municipality(lon, lat) or {}
    municipality = muni.get("name","")
    county = muni.get("county","")

    est_cleared = estimate_cleared_acres(acres, row.get("cleared_hint",""))
    # Create a crude square parcel around point for wetlands check (production: use parcel polygon)
    # ~ 150m half-width square (approx 18 acres at 300x300m)
    ddeg = 150 / 111139
    parcel_poly = {"type":"Polygon","coordinates":[
        [[lon-ddeg,lat-ddeg],[lon+ddeg,lat-ddeg],[lon+ddeg,lat+ddeg],[lon-ddeg,lat+ddeg],[lon-ddeg,lat-ddeg]]
    ]}
    wet = wetlands_overlaps(parcel_poly)
    est_buildable = max(est_cleared - (wet["dec_wetlands_ac"] + wet["dec_adjacent_area_ac"] + wet["nwi_ac"]), 0.0)

    req_dc_kw = round(est_buildable * DC_PER_ACRE_KW, 0)
    req_ac_mw = round(req_dc_kw / (DC_AC_RATIO * 1000), 2)

    # Hosting capacity — prototype for National Grid only
    hc = get_national_grid_feeders_near(lon, lat, SEARCH_RADIUS_MILES)
    best = summarize_best_capacity(hc) or (0.0, 0.0)
    best_mw = float(best[0])

    decision = "PASS"
    notes = []
    if price > 5_000_000: 
        decision = "FAIL"; notes.append("Price over $5M.")
    if acres < 5: 
        decision = "FAIL"; notes.append("Acreage under 5.")
    if est_buildable * 400 < 750: 
        decision = "FAIL"; notes.append("Buildable area < 1.875 acres for 750 kW DC.")
    if best_mw < req_ac_mw: 
        decision = "REVIEW"; notes.append("Feeder HC may be insufficient within 1.5 mi.")
    if decision == "PASS" and notes:
        decision = "REVIEW"

    return SiteResult(
        address=addr, price_usd=price, acres=acres, lat=lat, lon=lon,
        utility=utility, municipality=municipality, county=county,
        est_cleared_acres=round(est_cleared,2),
        dec_wetlands_ac=round(wet["dec_wetlands_ac"],2),
        dec_adjacent_area_ac=round(wet["dec_adjacent_area_ac"],2),
        nwi_ac=round(wet["nwi_ac"],2),
        est_buildable_acres=round(est_buildable,2),
        req_dc_kw=req_dc_kw, req_ac_mw=req_ac_mw,
        hc_feeder_best_mw=best_mw,
        decision=decision, notes="; ".join(notes)
    )

def run_pipeline(csv_in: str, csv_out: str) -> None:
    rows = []
    with open(csv_in, newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                res = process_row(r)
                rows.append(asdict(res))
            except Exception as e:
                rows.append({"address": f"{r.get('address','')}", "error": str(e)})

    # write out
    fieldnames = list(rows[0].keys()) if rows else []
    with open(csv_out, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
