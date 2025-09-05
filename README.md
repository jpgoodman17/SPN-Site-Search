# SPN Site Screener (NYS) — v0.1

An end-to-end, **automated screening pipeline** for NY State large‑scale solar site selection.  
It ingests listings (CSV or Realtor.com via RapidAPI), enriches them with **utility service territory**, **hosting capacity within 1.5 miles**, **municipality & zoning pointers**, and **wetlands & cleared‑area** checks, then outputs a scored shortlist.

> This is a working prototype designed for local use. Fill in API keys in `.env` (if using external APIs), then run the CLI.

---

## What it does

1. **Ingests listings**  
   - From a CSV (`data/example_listings.csv`) with columns: `address, city, state, zip, price_usd, acres, lat, lon, cleared_hint`  
   - OR (optional) pulls **Realtor.com** listings via RapidAPI (unofficial)—see `realtor_ingest.py`.  
   - **Filter**: price ≤ $5,000,000, acreage ≥ 5.

2. **Locates the utility & feeder/substation context**
   - Finds the **service territory** (National Grid, NYSEG, RG&E, O&R, Central Hudson) using NYS official service‑territory GIS.  
   - Pulls **hosting capacity** features within a configurable radius (default **1.5 miles**) for the detected utility.  
   - Computes **required capacity** from cleared area using your rule **400 kW DC / acre** and a DC:AC ratio (default **1.3**).

3. **Municipality & zoning pointers**
   - Computes the **municipality (town/city/village)** by intersecting with NYS civil boundaries.  
   - Provides **links** and an **AI summary** of local code if an **eCode360/Municode** URL is configured (see `zoning.py`).

4. **Wetlands screening**
   - Intersects parcel footprint/point buffer with **NYS DEC Informational Freshwater Wetlands** and **USFWS NWI**; applies a **100‑ft adjacent‑area** buffer for DEC wetlands (configurable).  
   - Deducts wetland & buffer overlap from cleared acreage.

5. **Cleared‑land estimation (optional)**
   - If `cleared_hint` or `acres_cleared` is missing, estimates from **USDA Cropland Data Layer (CDL 2024, 10m)** / NLCD categories (cultivated crops, pasture/hay, grass/open).

6. **Scores & exports**
   - Generates a **ranked CSV + GeoJSON** with fields: utility, feeder capacity snapshot, substation proximity, municipality, code URLs, wetlands flags, estimated buildable acres, **req. DC size**, and **go/no‑go** rationale.

---

## Data sources (public)
- **Hosting capacity (Joint Utilities of NY):**
  - National Grid NY System Data Portal (ArcGIS REST): `.../NYSDP/Hosting_Capacity_Data/MapServer`  
  - NYSEG/RG&E Portal (ArcGIS apps; layers accessible via ArcGIS items)  
  - Central Hudson / O&R portals (ESRI web maps)
- **Service territories:** NYS Electric Utility Service Territories (Open Data NY / ArcGIS)
- **Municipal boundaries:** NYS Civil Boundaries (State, County, Town, Village) ArcGIS REST
- **Wetlands:** NYS DEC Environmental Resource Mapper (Informational Freshwater Wetlands, 100‑ft adjacent area note) and **USFWS NWI** (ArcGIS REST / WMS)
- **Land cover (cleared proxy):** USDA **Cropland Data Layer** (2024 release @ 10 m)

See the README citations section for links.

---

## Quick start

### 1) Install
```bash
# Python 3.10+ recommended
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add keys for RapidAPI (optional)
```

### 2) Prepare input
Edit `data/example_listings.csv` or drop your own CSV with **lat/lon**. (If you only have addresses, set `AUTO_GEOCODE=True` in `.env` and provide a geocoding API key.)

### 3) Run
```bash
python scripts/run_cli.py --in data/example_listings.csv --out out/sites.csv --geo out/sites.geojson
```

### 4) Streamlit app (optional)
```bash
streamlit run app.py
```

---

## Output fields (selected)

- `address`, `price_usd`, `acres`, `utility`
- `est_cleared_acres`, `est_buildable_acres` (after wetlands & buffer)
- `req_dc_kw` (= `est_buildable_acres * 400_000`)
- `req_ac_mw` (= `req_dc_kw / (dc_ac_ratio*1000)`)
- `hc_feeder_best_mw`, `hc_feeder_dist_m` (nearest within 1.5 miles)
- `substation_name`, `substation_dist_m`, `substation_mva`, `substation_connected_mva` (if available)
- `municipality`, `county`, `zoning_links`, `zoning_ai_summary`
- `wetlands_overlap_ac`, `nwi_overlap_ac`, `dec_adjacent_area_overlap_ac`
- `score`, `decision`, `notes`

---

## Configuration

See `spn_screener/config.py` for defaults:
- `SEARCH_RADIUS_MILES = 1.5`
- `DC_PER_ACRE_KW = 400_000`
- `DC_AC_RATIO = 1.3`
- `DEC_ADJ_BUFFER_FT = 100`

Override via environment variables in `.env`.

---

## Ethics & Terms
- **Realtor.com**: scraping may violate Terms. Use an approved API or RapidAPI at your discretion, or import CSVs exported manually from your account.
- **Hosting capacity**: informational only; final interconnection outcomes require utility studies.
- **Wetlands**: DEC ERM is **informational**; a **jurisdictional determination** is the only definitive method.

---

## Citations / References

- Joint Utilities of NY hosting capacity overview (and utility links).  
- National Grid NY **ArcGIS REST** endpoint for hosting capacity data.  
- NYS DEC Environmental Resource Mapper (wetlands; 100‑ft adjacent area).  
- Informational Freshwater Wetlands layer (ArcGIS).  
- NYS **Civil Boundaries** (ArcGIS REST).  
- NYS Electric Utility Service Territories (Open Data NY / ArcGIS Hub).  
- **USFWS National Wetlands Inventory** (REST/WMS).  
- **USDA Cropland Data Layer 2024** (10‑m) release.

See inline comments in the code for direct URLs.
