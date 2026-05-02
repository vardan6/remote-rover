import math

EARTH_RADIUS_M = 6378137.0
DEFAULT_GEOREFERENCE = {
    "type": "local_tangent_plane",
    "origin_lat": 40.170000,
    "origin_lon": 44.500000,
    "origin_alt": 0.0,
    "origin_local": [0.0, 0.0, 0.0],
}


def _num(value, default=0.0):
    if isinstance(value, (int, float)):
        return float(value)
    return float(default)


def normalize_georeference(raw):
    cfg = {**DEFAULT_GEOREFERENCE, **(raw or {})}
    origin_local = cfg.get("origin_local") or DEFAULT_GEOREFERENCE["origin_local"]
    return {
        "type": str(cfg.get("type") or DEFAULT_GEOREFERENCE["type"]),
        "origin_lat": _num(cfg.get("origin_lat"), DEFAULT_GEOREFERENCE["origin_lat"]),
        "origin_lon": _num(cfg.get("origin_lon"), DEFAULT_GEOREFERENCE["origin_lon"]),
        "origin_alt": _num(cfg.get("origin_alt"), DEFAULT_GEOREFERENCE["origin_alt"]),
        "origin_local": [
            _num(origin_local[0] if len(origin_local) > 0 else 0.0),
            _num(origin_local[1] if len(origin_local) > 1 else 0.0),
            _num(origin_local[2] if len(origin_local) > 2 else 0.0),
        ],
    }


def local_to_gps(position, georeference):
    geo = normalize_georeference(georeference)
    origin_local = geo["origin_local"]
    east_m = float(position.x) - origin_local[0]
    north_m = float(position.y) - origin_local[1]
    up_m = float(position.z) - origin_local[2]

    lat_rad = math.radians(geo["origin_lat"])
    lat = geo["origin_lat"] + math.degrees(north_m / EARTH_RADIUS_M)
    lon = geo["origin_lon"] + math.degrees(east_m / (EARTH_RADIUS_M * max(0.01, math.cos(lat_rad))))
    alt = geo["origin_alt"] + up_m
    return {"lat": lat, "lon": lon, "alt": alt}
