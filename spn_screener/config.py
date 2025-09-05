import os

SEARCH_RADIUS_MILES = float(os.getenv("SEARCH_RADIUS_MILES", 1.5))
DC_PER_ACRE_KW = float(os.getenv("DC_PER_ACRE_KW", 400_000))
DC_AC_RATIO = float(os.getenv("DC_AC_RATIO", 1.3))
DEC_ADJ_BUFFER_FT = float(os.getenv("DEC_ADJ_BUFFER_FT", 100))

# ArcGIS REST Endpoints (documented in README with citations)
ENDPOINTS = {
    "service_territories": "https://services7.arcgis.com/6cx5zz3lE8WoCfhq/arcgis/rest/services/NYS_Electric_Utility_Service_Territories/FeatureServer/0",
    # NYS Civil Boundaries (Towns/Cities/Villages)
    "civil_boundaries_mapserver": "https://gisservices.its.ny.gov/arcgis/rest/services/NYS_Civil_Boundaries/MapServer",
    # DEC Informational Freshwater Wetlands (feature layer)
    "dec_wetlands_informational": "https://gisservices.dec.ny.gov/arcgis/rest/services/erm/erm_wetlands/MapServer/1",
    # USFWS NWI wetlands (MapServer layer 0)
    "nwi_wetlands": "https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/services/Wetlands/MapServer/0",
    # National Grid NY Hosting Capacity (MapServer root)
    "ng_hosting_capacity_root": "https://systemdataportal.nationalgrid.com/arcgis/rest/services/NYSDP/Hosting_Capacity_Data/MapServer",
    # NYSEG/RGE & others can be added as discovered
}

# Land cover (USDA CDL imagery service — example ArcGIS item, may be proxied via STAC in production)
CDL_INFO = {
    "year": 2024,
    "notes": "CDL 2024 released Feb 27, 2025 at 10m native resolution."
}
