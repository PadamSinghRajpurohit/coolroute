"""CoolRoute real-data adapters — OpenStreetMap (Overpass) + Open-Meteo weather.

All network calls are isolated here so the rest of the app can be tested
without internet access.  No third-party libraries are required beyond the
Python standard library.
"""
from __future__ import annotations

import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request

# ── provider URLs — multiple Overpass mirrors tried in order ───────────────
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
WEATHER  = "https://api.open-meteo.com/v1/forecast"
GEOCODER = "https://nominatim.openstreetmap.org/search"
PHOTON_GEOCODER = "https://photon.komoot.io/api/"
FOOT_ROUTER = "https://routing.openstreetmap.de/routed-foot/route/v1/driving"
VALHALLA_ROUTER = "https://valhalla1.openstreetmap.de/route"

# ── in-memory cache  {key: (timestamp, data)} ─────────────────────────────
_AREA_CACHE: dict = {}
CACHE_TTL = 900  # 15 min


def walking_directions(origin: dict, destination: dict) -> dict:
    """Fetch a complete pedestrian route, using Valhalla if OSRM has no route."""
    coords = f"{float(origin['lon']):.6f},{float(origin['lat']):.6f};{float(destination['lon']):.6f},{float(destination['lat']):.6f}"
    query = urllib.parse.urlencode({"overview": "full", "geometries": "geojson", "steps": "true", "alternatives": "false"})
    url = f"{FOOT_ROUTER}/{coords}?{query}"
    osrm_error = None
    try:
        data = fetch_json(url, timeout=8)
        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]
            directions = []
            for leg in route.get("legs", []):
                for step in leg.get("steps", []):
                    maneuver = step.get("maneuver", {})
                    kind = maneuver.get("type", "continue").replace("_", " ")
                    modifier = maneuver.get("modifier", "")
                    name = step.get("name") or "unnamed path"
                    instruction = (f"Head {modifier} on {name}" if kind == "depart" and modifier else
                                   f"Start on {name}" if kind == "depart" else
                                   "Arrive at your destination" if kind == "arrive" else
                                   f"{kind.capitalize()}{(' ' + modifier) if modifier else ''} onto {name}")
                    directions.append({"instruction": instruction, "distance_m": round(step.get("distance", 0)), "duration_s": round(step.get("duration", 0))})
            return {
                "coordinates": [[lat, lon] for lon, lat in route["geometry"]["coordinates"]],
                "distance_m": round(route.get("distance", 0), 1),
                "duration_s": round(route.get("duration", 0)),
                "directions": directions,
                "source": "OpenStreetMap · FOSSGIS OSRM pedestrian routing",
                "router": "OSRM",
            }
        osrm_error = data.get("message") or data.get("code") or "No route returned"
    except Exception as exc:
        osrm_error = str(exc)

    # Independent OSM router used when OSRM has no path or is unavailable.
    payload = json.dumps({
        "locations": [{"lat": float(origin["lat"]), "lon": float(origin["lon"]), "type": "break"},
                      {"lat": float(destination["lat"]), "lon": float(destination["lon"]), "type": "break"}],
        "costing": "pedestrian", "units": "kilometers", "shape_format": "polyline6",
        "directions_options": {"units": "kilometers"},
    }).encode("utf-8")
    try:
        data = fetch_json(VALHALLA_ROUTER, payload, timeout=10,
                          headers={"Content-Type": "application/json", "X-Client-Id": "CoolRoute-local"})
        trip = data.get("trip", {})
        leg = (trip.get("legs") or [])[0]
        coordinates = _decode_polyline6(leg["shape"])
        summary = trip.get("summary", {})
        directions = [{
            "instruction": m.get("instruction") or "Continue along the walking route",
            "distance_m": round(float(m.get("length", 0)) * 1000),
            "duration_s": round(float(m.get("time", 0))),
        } for m in leg.get("maneuvers", [])]
        if len(coordinates) < 2:
            raise ValueError("Router returned incomplete route geometry.")
        return {
            "coordinates": coordinates,
            "distance_m": round(float(summary.get("length", 0)) * 1000, 1),
            "duration_s": round(float(summary.get("time", 0))),
            "directions": directions,
            "source": "OpenStreetMap · FOSSGIS Valhalla pedestrian routing",
            "router": "Valhalla",
        }
    except Exception as exc:
        raise RuntimeError(f"OSRM: {osrm_error}; Valhalla: {exc}") from exc


def _decode_polyline6(encoded: str) -> list[list[float]]:
    """Decode Valhalla's default precision-6 polyline into [lat, lon] pairs."""
    values, index = [], 0
    while index < len(encoded):
        pair = []
        for _ in range(2):
            result = shift = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            pair.append(~(result >> 1) if result & 1 else result >> 1)
        if values:
            lat = values[-1][0] + pair[0]
            lon = values[-1][1] + pair[1]
        else:
            lat, lon = pair
        values.append([lat / 1e6, lon / 1e6])
    return values


# ─────────────────────────────────────── HTTP helper ──
def fetch_json(url: str, post_data: bytes | None = None, timeout: int = 35,
               headers: dict | None = None) -> dict:
    """GET or POST, return decoded JSON.  Raises on HTTP errors."""
    req = urllib.request.Request(
        url, data=post_data,
        headers={
            "User-Agent": "CoolRoute/2.0 (pedestrian heat-routing; non-commercial)",
            "Accept":     "application/json",
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        raise RuntimeError(f"HTTP {exc.code} from {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error reaching {url}: {exc.reason}") from exc


def geocode_place(query: str) -> dict:
    """Resolve a place quickly with Photon, falling back to Nominatim."""
    query = " ".join(query.split())
    if not query or len(query) > 120:
        raise ValueError("Enter a place name between 1 and 120 characters.")
    photon_url = PHOTON_GEOCODER + "?" + urllib.parse.urlencode({"q": query, "limit": 1})
    try:
        result = fetch_json(photon_url, timeout=5).get("features", [])
        if result:
            item = result[0]
            lon, lat = item["geometry"]["coordinates"][:2]
            props = item.get("properties", {})
            name = ", ".join(str(props[k]) for k in ("name", "city", "state", "country") if props.get(k))
            return {"name": name or query, "lat": float(lat), "lon": float(lon)}
    except Exception:
        pass
    url = GEOCODER + "?" + urllib.parse.urlencode({
        "q": query, "format": "jsonv2", "limit": 1,
    })
    req = urllib.request.Request(url, headers={
        "User-Agent": "CoolRoute/2.1 (pedestrian heat-routing; non-commercial)",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"Place search is temporarily unavailable: {exc}") from exc
    if not result:
        raise LookupError("No matching place found. Try a city name plus country.")
    item = result[0]
    return {"name": item.get("display_name", query),
            "lat": float(item["lat"]), "lon": float(item["lon"])}


def search_places(query: str) -> list[dict]:
    """Return a short autocomplete list from Photon, with Nominatim fallback."""
    query = " ".join(query.split())
    if len(query) < 2 or len(query) > 120:
        raise ValueError("Type at least 2 characters to search for a place.")
    url = PHOTON_GEOCODER + "?" + urllib.parse.urlencode({"q": query, "limit": 6})
    try:
        features = fetch_json(url, timeout=5).get("features", [])
        matches = []
        for feature in features:
            props = feature.get("properties", {})
            lon, lat = feature["geometry"]["coordinates"][:2]
            label = ", ".join(dict.fromkeys(str(props[k]) for k in
                ("name", "street", "district", "city", "state", "country") if props.get(k)))
            if label:
                matches.append({"name": label, "lat": float(lat), "lon": float(lon)})
        if matches:
            return matches[:6]
    except Exception:
        pass
    params = urllib.parse.urlencode({"q": query, "format": "jsonv2", "limit": 6})
    req = urllib.request.Request(GEOCODER + "?" + params, headers={
        "User-Agent": "CoolRoute/2.1 (pedestrian heat-routing; non-commercial)",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            results = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"Place suggestions are temporarily unavailable: {exc}") from exc
    return [{"name": item.get("display_name", query), "lat": float(item["lat"]), "lon": float(item["lon"])}
            for item in results[:6]]


def fetch_overpass(query: str) -> dict:
    """Try independent Overpass endpoints using normal TLS verification."""
    payload  = urllib.parse.urlencode({"data": query}).encode("ascii")
    last_err: Exception = RuntimeError("No Overpass mirrors configured.")

    for mirror in OVERPASS_MIRRORS:
        try:
            req = urllib.request.Request(
                mirror, data=payload,
                headers={
                    "User-Agent": "CoolRoute/2.0 (pedestrian heat-routing; non-commercial)",
                    "Accept":     "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            # Keep a slow public mirror from blocking the map for nearly a minute.
            with urllib.request.urlopen(req, timeout=4) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
            last_err = exc

    raise RuntimeError(
        f"All Overpass mirrors failed. Last error: {last_err}. "
        "Check your internet connection or try again in a moment."
    )


# ─────────────────────────────────────── bbox validation ──
def bounded_bbox(values) -> tuple[float, float, float, float]:
    """Parse and validate a south,west,north,east bounding box.

    Maximum ~3.5 km × 3.5 km to keep public-API queries small.
    """
    try:
        south, west, north, east = map(float, values)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"bbox must be four numbers (south,west,north,east): {exc}") from exc
    if not (-85 < south < north < 85):
        raise ValueError("south and north must satisfy -85 < south < north < 85")
    if not (-180 <= west < east <= 180):
        raise ValueError("west and east must satisfy -180 ≤ west < east ≤ 180")
    if north - south > 0.045 or east - west > 0.045:
        raise ValueError("Map area too large — please zoom in (max ~4 km across).")
    return south, west, north, east


# ─────────────────────────────────────── OSM area data ──
def area_data(bbox) -> dict:
    """Fetch streets, trees and buildings for a bounding box from Overpass.

    Results are cached in memory for CACHE_TTL seconds.
    Returns: {bbox, ways, trees, buildings, source, attribution, fetched_at}
    """
    south, west, north, east = bounded_bbox(bbox)
    # Quantize to roughly 10 m so small map drags reuse the same cached area.
    key = tuple(round(v, 4) for v in (south, west, north, east))
    cached = _AREA_CACHE.get(key)
    if cached and time.time() - cached[0] < CACHE_TTL:
        return cached[1]

    box = f"{south},{west},{north},{east}"
    # Keep the request local to the visible neighbourhood. The basemap itself
    # renders immediately; this smaller request only adds shade intelligence.
    # Return full geometry only for walkable streets. Tree ways and buildings
    # need only a representative centre for the shade estimate; this cuts the
    # response size substantially in dense city blocks.
    query = f"""[out:json][timeout:4];
(
  way[highway~"^(footway|path|pedestrian|steps|residential|living_street|service|unclassified|tertiary|secondary|primary)$"]({box});
)->.roads;
(
  node[natural=tree]({box});
  way[natural=tree]({box});
)->.trees;
way[building]({box})->.buildings;
.roads out body geom;
.trees out center;
.buildings out center;"""
    raw = fetch_overpass(query)

    ways: list      = []
    trees: list     = []
    buildings: list = []

    for item in raw.get("elements", []):
        tags = item.get("tags", {})
        geom = [{"lat": p["lat"], "lon": p["lon"]}
                for p in item.get("geometry", []) if "lat" in p and "lon" in p]
        center = item.get("center") or item

        if tags.get("natural") == "tree" and "lat" in center and "lon" in center:
            trees.append({"lat": center["lat"], "lon": center["lon"]})

        elif item["type"] == "way" and "highway" in tags and len(geom) > 1:
            is_steps = (tags.get("highway") == "steps" or
                        tags.get("wheelchair") in ("no", "limited"))
            surface  = tags.get("surface", "")
            ways.append({
                "id":      item["id"],
                "name":    tags.get("name") or tags.get("name:en") or "Unnamed street",
                "highway": tags["highway"],
                "surface": surface,
                "lit":     tags.get("lit", ""),
                "steps":   is_steps,
                "geometry": geom,
            })

        elif item["type"] == "way" and "building" in tags and "lat" in center and "lon" in center:
            buildings.append({"lat": center["lat"], "lon": center["lon"]})

    result = {
        "bbox":        list(key),
        "ways":        ways,
        "trees":       trees,
        "buildings":   buildings,
        "source":      "OpenStreetMap via Overpass API",
        "fetched_at":  int(time.time()),
        "attribution": "© OpenStreetMap contributors",
    }
    _AREA_CACHE[key] = (time.time(), result)
    return result


# ─────────────────────────────────────── weather ──
def weather_at(lat: float, lon: float, hour=None) -> dict:
    """Return Open-Meteo forecast for the chosen hour (or current time)."""
    params = urllib.parse.urlencode({
        "latitude":     round(float(lat), 4),
        "longitude":    round(float(lon), 4),
        "hourly":       "temperature_2m,relative_humidity_2m,cloud_cover,shortwave_radiation,wind_speed_10m",
        "forecast_days": 2,
        "timezone":     "auto",
    })
    data    = fetch_json(f"{WEATHER}?{params}", timeout=15)
    hourly  = data.get("hourly", {})
    times   = hourly.get("time", [])
    if not times:
        raise ValueError("Weather provider returned no hourly data.")

    now_ts = time.time()
    def ts(t: str) -> float:
        try:
            return time.mktime(time.strptime(t, "%Y-%m-%dT%H:%M"))
        except Exception:
            return 0.0

    if hour is None:
        idx = min(range(len(times)), key=lambda i: abs(ts(times[i]) - now_ts))
    else:
        target = float(hour)
        idx = min(range(len(times)),
                  key=lambda i: abs(int(times[i][11:13]) + int(times[i][14:16]) / 60.0 - target))

    def take(name):
        return hourly.get(name, [None] * len(times))[idx]

    return {
        "time":                    times[idx],
        "timezone":                data.get("timezone", "local"),
        "utc_offset_seconds":      data.get("utc_offset_seconds"),
        "temperature_c":           take("temperature_2m"),
        "relative_humidity_pct":   take("relative_humidity_2m"),
        "cloud_cover_pct":         take("cloud_cover"),
        "shortwave_radiation_w_m2": take("shortwave_radiation"),
        "wind_speed_kmh":          take("wind_speed_10m"),
        "source":                  "Open-Meteo forecast",
        "license":                 "CC BY 4.0",
    }


# ─────────────────────────────────────── astronomical sun ──
def sun_for_location(lat: float, hour: float, day_of_year: int | None = None,
                     lon: float = 0.0, utc_offset_seconds: float | None = None) -> float:
    """Approximate solar elevation strength for a location and local clock hour."""
    day = day_of_year or time.localtime().tm_yday
    dec = math.radians(23.45 * math.sin(math.radians(360 / 365 * (day - 81))))
    phi = math.radians(float(lat))
    # Correct local clock time to approximate solar time using longitude and
    # the provider's UTC offset.  If the provider is down, estimate the civil
    # offset from longitude's nearest 15-degree time-zone meridian.
    offset_hours = (float(utc_offset_seconds) / 3600.0
                    if utc_offset_seconds is not None else round(float(lon) / 15.0))
    solar_hour = float(hour) + float(lon) / 15.0 - offset_hours
    h   = math.radians(15.0 * (solar_hour - 12.0))
    elev = math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(h)
    return max(0.0, elev)


# ─────────────────────────────────────── graph builder ──
def graph_from_area(area: dict) -> dict:
    """Convert area_data() result into a routing graph compatible with core.py.

    Shade is estimated from:
      • Mapped trees within 14 m  → +0.48
      • Building centre within 18 m → +0.28 (fast shade proxy)
    Capped at 0.85.  Confidence 0.82 if shade source found, else 0.32.
    """
    nodes:  list = []
    lookup: dict = {}
    edges:  list = []

    # Metres per degree at the mid-latitude of the bbox
    bbox    = area["bbox"]
    mid_lat = (bbox[0] + bbox[2]) / 2.0
    mlat    = 111_132.0
    mlon    = 111_320.0 * math.cos(math.radians(mid_lat))

    def node_id(p: dict) -> int:
        key = (round(p["lat"], 6), round(p["lon"], 6))
        if key not in lookup:
            nid = len(nodes)
            lookup[key] = nid
            nodes.append({
                "id":  nid,
                "lat": key[0],
                "lon": key[1],
                "x":   key[1] * mlon,
                "y":   key[0] * mlat,
            })
        return lookup[key]

    trees     = area.get("trees", [])
    buildings = area.get("buildings", [])

    # Index shade features into metre-sized cells. The previous full scan of
    # every tree/building for every street edge became quadratic in city areas.
    def spatial_index(points: list[dict], cell_size: float) -> dict:
        index: dict[tuple[int, int], list[tuple[float, float]]] = {}
        for feature in points:
            x, y = feature["lon"] * mlon, feature["lat"] * mlat
            cell = (math.floor(x / cell_size), math.floor(y / cell_size))
            index.setdefault(cell, []).append((x, y))
        return index

    tree_cell, building_cell = 14.0, 18.0
    tree_index = spatial_index(trees, tree_cell)
    building_index = spatial_index(buildings, building_cell)

    def close_to_feature(p: dict, index: dict, cell_size: float, radius: float) -> bool:
        x, y = p["lon"] * mlon, p["lat"] * mlat
        cx, cy = math.floor(x / cell_size), math.floor(y / cell_size)
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                for fx, fy in index.get((cx + ox, cy + oy), ()):
                    if math.hypot(fx - x, fy - y) < radius:
                        return True
        return False

    for way in area.get("ways", []):
        geom = way["geometry"]
        for a, b in zip(geom, geom[1:]):
            length = math.hypot(
                (b["lat"] - a["lat"]) * mlat,
                (b["lon"] - a["lon"]) * mlon,
            )
            if length < 1.0:
                continue
            mid = {"lat": (a["lat"] + b["lat"]) / 2.0,
                   "lon": (a["lon"] + b["lon"]) / 2.0}
            has_tree     = close_to_feature(mid, tree_index, tree_cell, 14.0)
            has_building = close_to_feature(mid, building_index, building_cell, 18.0)
            shade        = min(0.85, (0.48 if has_tree else 0.0) +
                                      (0.28 if has_building else 0.0))
            confidence   = 0.82 if (has_tree or has_building) else 0.32
            sources      = ([s for s, ok in (("mapped tree", has_tree),
                                              ("nearby building", has_building)) if ok])
            edges.append({
                "a":             node_id(a),
                "b":             node_id(b),
                "length":        round(length, 2),
                "shade":         round(shade, 3),
                "slope":         0.0,
                "step_free":     not way.get("steps", False),
                "wait":          0,
                "crossing_shade": 0.0,
                "confidence":    confidence,
                "closed":        False,
                "name":          way.get("name", "Unnamed street"),
                "highway":       way.get("highway", ""),
                "surface":       way.get("surface", ""),
                "geometry":      [a, b],
                "shade_sources": sources,
            })

    return {
        "nodes":   nodes,
        "edges":   edges,
        "n":       len(nodes),
        "spacing": 1,
        "tree_count":     len(trees),
        "building_count": len(buildings),
    }


# ─────────────────────────── standalone test ──
if __name__ == "__main__":
    bbox = [26.895, 75.775, 26.925, 75.805]
    print("Fetching area …")
    area = area_data(bbox)
    print(f"  Ways: {len(area['ways'])}, Trees: {len(area['trees'])}, "
          f"Buildings: {len(area['buildings'])}")
    g = graph_from_area(area)
    print(f"  Graph: {len(g['nodes'])} nodes, {len(g['edges'])} edges")
    print("Fetching weather …")
    w = weather_at(26.91, 75.79, hour=13)
    print(f"  {w['temperature_c']}°C, {w['cloud_cover_pct']}% cloud, "
          f"{w['shortwave_radiation_w_m2']} W/m²")
