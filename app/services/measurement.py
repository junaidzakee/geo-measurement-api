from pyproj import CRS, Transformer
from shapely import force_2d, make_valid
from shapely.ops import transform

WGS84 = CRS.from_epsg(4326)

AREA_TYPES = {"Polygon", "MultiPolygon"}
LINE_TYPES = {"LineString", "MultiLineString"}


def pick_utm_crs(lon, lat):
    zone = int((lon + 180) // 6) + 1
    zone = min(max(zone, 1), 60)
    base = 32600 if lat >= 0 else 32700
    return CRS.from_epsg(base + zone)


def measure_feature(geom, source_crs):
    result = {
        "area_sq_m": None,
        "length_m": None,
        "projected_crs": None,
        "note": None,
    }
    notes = []

    if geom is None or geom.is_empty:
        result["note"] = "Empty geometry, nothing to measure"
        return result

    geom = force_2d(geom)

    if not geom.is_valid:
        geom = make_valid(geom)
        notes.append("Invalid geometry was repaired before measuring")

    gtype = geom.geom_type
    if gtype not in AREA_TYPES and gtype not in LINE_TYPES:
        notes.append(f"No measurement for {gtype}")
        result["note"] = "; ".join(notes)
        return result

    to_wgs84 = Transformer.from_crs(source_crs, WGS84, always_xy=True)
    centre = transform(to_wgs84.transform, geom).centroid
    lon, lat = centre.x, centre.y

    if not (-80 <= lat <= 84):
        notes.append("Outside the UTM latitude range, not measured")
        result["note"] = "; ".join(notes)
        return result

    utm = pick_utm_crs(lon, lat)
    to_utm = Transformer.from_crs(source_crs, utm, always_xy=True)
    projected = transform(to_utm.transform, geom)

    if gtype in AREA_TYPES:
        result["area_sq_m"] = projected.area
    else:
        result["length_m"] = projected.length
    result["projected_crs"] = utm.to_string()
    result["note"] = "; ".join(notes) or None
    return result