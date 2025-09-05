from typing import Dict, Any, Tuple
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
import shapely
from .arcgis_utils import query_polygon_intersect
from .config import ENDPOINTS, DEC_ADJ_BUFFER_FT

def _acre_area(geom) -> float:
    return geom.area * (111139**2) / 4046.856e+0  # VERY rough if coords in degrees; replace with projected calc in production

def wetlands_overlaps(polygon_geojson: Dict[str, Any]) -> Dict[str, float]:
    """Return overlapping acres with DEC informational wetlands (plus 100ft adjacent area) and USFWS NWI polygons.
    NOTE: In production, reproject to NYSP CS (ft) before buffering/areas.
    """
    parcel = shape(polygon_geojson)
    out = {"dec_wetlands_ac": 0.0, "dec_adjacent_area_ac": 0.0, "nwi_ac": 0.0}

    # DEC informational wetlands
    dec = query_polygon_intersect(ENDPOINTS["dec_wetlands_informational"], polygon_geojson)
    dec_polys = [shape(f["geometry"]) for f in (dec.get("features", []) if isinstance(dec, dict) else []) if f.get("geometry")]
    if dec_polys:
        dec_union = unary_union(dec_polys)
        out["dec_wetlands_ac"] = _acre_area(parcel.intersection(dec_union))
        # adjacent area buffer (100 ft) – crude buffer in degrees, replace with projected buffer in production
        ft_to_deg = 1/(3.28084*111139)  # very rough
        adj = dec_union.buffer(DEC_ADJ_BUFFER_FT * ft_to_deg)
        out["dec_adjacent_area_ac"] = _acre_area(parcel.intersection(adj))

    # NWI
    nwi = query_polygon_intersect(ENDPOINTS["nwi_wetlands"], polygon_geojson)
    nwi_polys = [shape(f["geometry"]) for f in (nwi.get("features", []) if isinstance(nwi, dict) else []) if f.get("geometry")]
    if nwi_polys:
        nwi_union = unary_union(nwi_polys)
        out["nwi_ac"] = _acre_area(parcel.intersection(nwi_union))

    return out
