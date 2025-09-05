# Optional: Pull listings from unofficial RapidAPI endpoints (use at your own risk; respect TOS)
# This module shows how to call a RapidAPI endpoint and map fields to our CSV schema.
import os, requests, csv

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

def fetch_realtor_listings(city: str, state_code: str, min_lot_sqft=217800, max_price=5_000_000):
    """Example against a RapidAPI 'Realty in US' style endpoint. Replace with your subscribed API base & params."""
    if not RAPIDAPI_KEY:
        raise RuntimeError("RAPIDAPI_KEY not set")
    url = "https://realty-in-us.p.rapidapi.com/properties/list-for-sale"
    params = {"city": city, "state_code": state_code, "offset":"0","limit":"50","sort":"relevance"}
    headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "realty-in-us.p.rapidapi.com"}
    r = requests.get(url, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    # map to our schema...
    out = []
    for p in data.get("listings", []):
        lot_sqft = p.get("lot_size", {}).get("size", 0)
        price = p.get("price", 0)
        if lot_sqft and lot_sqft >= min_lot_sqft and price <= max_price:
            out.append({
                "address": p.get("address",""),
                "city": p.get("address_new",{}).get("city",""),
                "state": p.get("address_new",{}).get("state_code","NY"),
                "zip": p.get("address_new",{}).get("postal_code",""),
                "price_usd": price,
                "acres": round(lot_sqft/43560, 2),
                "lat": p.get("lat"),
                "lon": p.get("lon"),
                "cleared_hint": ""
            })
    return out

def write_csv(rows, path="data/from_api.csv"):
    if not rows: return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    return path
