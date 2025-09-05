# spn_screener/pipeline.py — clean version with skip-remote + size-by-acres footprint
import os
import csv
import math
from dataclasses import dataclass, asdict
from typing import Dict, Any

from .config import SEARCH_RADIUS_MILES, DC_PER_ACRE_KW, DC_AC_RATIO
from .hosting_capacity import get_national_grid_feeders_near, summarize_best_capacity
from .boundaries import lookup_municipality
from .landcover import estimate_cleared_acres
from .wetlands import wetlands_overlaps

# Read the env var set by the Streamlit checkbox in app.py
SKIP_REMOTE = os.getenv("SPN_SKIP_REMOTE") == "1"


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
    """
    Placeholder until service-territory intersection is wired:
    return 'National Grid' for Upstate default. You can enhance this by
    intersecting the NYS utility service territories layer.
    """
    return "National Grid"


def _square_polygon_by_acres(lon: float, lat: float, acres: float) -> Dict[str, Any]:
    """
    Build a rough square polygon centered at (lon, lat) with area ≈ acres.
    This is a coarse proxy for parcel footprint, good enough for screening.

    side_m = sqrt(acres * 4046.85642)
    half_m = side_m / 2
    Convert meters to degrees very roughly: 1 deg ≈ 111,139 m
    """
    side_m = math.sqrt(max(acres, 0.1) * 4046.85642)
    half_m = side_m / 2.0
    m_to_deg = 1.0 / 111_139.0
    ddeg = half_m * m_to_deg
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon - ddeg, lat - ddeg],
            [lon + ddeg, lat - ddeg],
            [lon + ddeg, lat + ddeg],
            [lon - ddeg, lat + ddeg],
            [lon - ddeg, lat - ddeg],
        ]]
    }


def process_row(row: Dict[str, Any]) -> SiteResult:
    # Basic fields
    addr = f"{row['address']}, {row['city']}, {row['state']} {row['zip']}"
    price = float(row["price_usd"])
    acres = float(row["acres"])
    lat = float(row["lat"])
    lon = float(row["lon"])

    # Utility & municipality (lightweight)
    utility = detect_utility(lon, lat)
    muni_info = lookup_municipality(lon, lat) or {}
    municipality = muni_info.get("name", "") or ""
    county = muni_info.get("county", "") or ""

    # Cleared acres (heuristic, can be replaced with CDL/NLCD)
    est_cleared = estimate_cleared_acres(acres, row.get("cleared_hint", ""))

    # Parcel-like footprint sized by acres
    parcel_poly = _square_polygon_by_acres(lon, lat, acres)

    # Wetlands: fail-soft or skip if offline
    if not SKIP_REMOTE:
        try:
            wet = wetlands_overlaps(parcel_poly)
        except Exception:
            wet = {"dec_wetlands_ac": 0.0, "dec_adjacent_area_ac": 0.0, "nwi_ac": 0.0}
    else:
        wet = {"dec_wetlands_ac": 0.0, "dec_adjacent_area_ac": 0.0, "nwi_ac": 0.0}

    # Buildable acres = cleared minus wetlands overlaps (DEC + adjacent + NWI)
    wetlands_total = (wet.get("dec_wetlands_ac", 0.0)
                      + wet.get("dec_adjacent_area_ac", 0.0)
                      + wet.get("nwi_ac", 0.0))
    est_buildable = max(est_cleared - wetlands_total, 0.0)

    # DC/AC sizing
    req_dc_kw = round(est_buildable * DC_PER_ACRE_KW, 0)
    req_ac_mw = round(req_dc_kw / (DC_AC_RATIO * 1000.0), 3)

    # Hosting capacity (National Grid): fail-soft or skip if offline
    best_mw = 0.0
    if not SKIP_REMOTE:
        try:
            hc = get_national_grid_feeders_near(lon, lat, SEARCH_RADIUS_MILES)
            best = summarize_best_capacity(hc) or (0.0, 0.0)
            best_mw = float(best[0])
        except Exception:
            best_mw = 0.0

    # Decision logic
    decision = "PASS"
    notes = []

    if price > 5_000_000:
        decision = "FAIL"
        notes.append("Price over $5M.")
    if acres < 5:
        decision = "FAIL"
        notes.append("Acreage under 5.")
    # 750 kWdc threshold ≈ 1.875 acres at 400 kWdc/ac
    if est_buildable * 400 < 750:
        decision = "FAIL"
        notes.append("Buildable area < 1.875 acres for 750 kW DC.")

    # Capacity hint
    if best_mw < (req_ac_mw or 0.0):
        # Only downgrade to REVIEW if not already FAIL
        if decision == "PASS":
            decision = "REVIEW"
        notes.append("Feeder hosting capacity may be insufficient within 1.5 miles.")

    if decision == "PASS" and notes:
        decision = "REVIEW"

    return SiteResult(
        address=addr,
        price_usd=price,
        acres=acres,
        lat=lat,
        lon=lon,
        utility=utility,
        municipality=municipality,
        county=county,
        est_cleared_acres=round(est_cleared, 2),
        dec_wetlands_ac=round(wet.get("dec_wetlands_ac", 0.0), 2),
        dec_adjacent_area_ac=round(wet.get("dec_adjacent_area_ac", 0.0), 2),
        nwi_ac=round(wet.get("nwi_ac", 0.0), 2),
        est_buildable_acres=round(est_buildable, 2),
        req_dc_kw=req_dc_kw,
        req_ac_mw=req_ac_mw,
        hc_feeder_best_mw=best_mw,
        decision=decision,
        notes="; ".join(notes),
    )


def run_pipeline(csv_in: str, csv_out: str) -> None:
    """
    Read an input CSV of listings, score them, and write the output CSV.
    """
    rows_out = []
    with open(csv_in, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                res = process_row(r)
                rows_out.append(asdict(res))
            except Exception as e:
                rows_out.append({
                    "address": f"{r.get('address', '')}",
                    "error": str(e)
                })

    fieldnames = list(rows_out[0].keys()) if rows_out else []
    os.makedirs(os.path.dirname(csv_out), exist_ok=True)
    with open(csv_out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

