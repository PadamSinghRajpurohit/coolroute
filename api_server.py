"""CoolRoute API server — Starlette backend.

Run:
    python -m uvicorn api_server:app --host 127.0.0.1 --port 8765

Endpoints
---------
GET  /                          → index.html
GET  /styles.css                → styles.css
GET  /frontend.js               → frontend.js

GET  /api/v1/health             → service status
GET  /api/v1/sun?hour=          → astronomical sun strength
GET  /api/v1/graph              → synthetic demo graph
POST /api/v1/route              → synthetic demo routing

GET  /api/v1/real/area?bbox=    → OSM streets, trees, buildings + routing graph
GET  /api/v1/real/weather?lat&lon&hour → Open-Meteo hourly forecast
POST /api/v1/real/route         → real-data routing with heat model
POST /api/v1/real/directions    → fast pedestrian street route + turn instructions
"""
from __future__ import annotations

import copy
import json
import math
import os

import auth_store
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Route

from core import build_neighbourhood, plan, sun_factor
from real_data import (area_data, bounded_bbox, graph_from_area,
                       geocode_place, search_places, sun_for_location, walking_directions, weather_at)

# ── boot-time synthetic graph for demos ───────────────────────────────────
GRAPH   = build_neighbourhood()
N_EDGES = len(GRAPH["edges"])
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
auth_store.initialize()


# ─────────────────────────────────────── helpers ──
def err(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}},
                        status_code=status)


def snap_synthetic(point: dict) -> int:
    """Accept {"node": id} or {"x": m, "y": m} and return a synthetic node id."""
    if "node" in point:
        n = point["node"]
        if not isinstance(n, int) or not 0 <= n < len(GRAPH["nodes"]):
            raise ValueError(f"node must be an integer 0 – {len(GRAPH['nodes']) - 1}")
        return n
    if "x" in point and "y" in point:
        x, y = float(point["x"]), float(point["y"])
        return min(GRAPH["nodes"],
                   key=lambda nd: (nd["x"] - x) ** 2 + (nd["y"] - y) ** 2)["id"]
    raise ValueError("point needs 'node' or both 'x' and 'y'")


def route_summary_synthetic(g: dict, side: dict,
                             shade_on: bool, sun: float) -> dict:
    e_ids  = side["edges"]
    length = sum(g["edges"][k]["length"] for k in e_ids) or 1.0
    shaded = sum(g["edges"][k]["length"] *
                 (g["edges"][k]["shade"] if shade_on else 0.0)
                 for k in e_ids)
    m = side["m"]
    return {
        "nodes":                 side["nodes"],
        "distance_m":            round(m["dist"], 1),
        "walk_time_min":         round(m["time"] / 60, 1),
        "heat_exposure":         round(m["heat"], 1),
        "effort":                round(m["effort"], 1),
        "shaded_share":          round(shaded / length, 3),
        "data_confidence":       round(m["data_confidence"], 2),
        "missing_data_segments": m["missing_edges"],
        "segments":              m["n_edges"],
    }


def explain(r: dict, base: dict, cool: dict) -> str:
    if r["sun"] == 0:
        return ("No sun at this hour — heat exposure is zero and both routes are identical.")
    if base["heat_exposure"] == cool["heat_exposure"]:
        return ("The shortest route already fits your heat budget, so CoolRoute keeps it.")
    cut   = 100 * (1 - cool["heat_exposure"] / max(base["heat_exposure"], 1e-9))
    extra = cool["distance_m"] - base["distance_m"]
    pct   = 100 * (cool["distance_m"] / max(base["distance_m"], 1e-9) - 1)
    dt    = cool["walk_time_min"] - base["walk_time_min"]
    return (
        f"CoolRoute is {extra:.0f} m longer ({pct:+.1f}%) and takes "
        f"{abs(dt):.1f} min {'more' if dt >= 0 else 'less'}, but cuts "
        f"heat exposure by {cut:.0f}% by favouring shaded streets."
    )


def static_file(name: str) -> Response:
    path = os.path.join(BASE_DIR, name)
    if not os.path.exists(path):
        return err(404, "NOT_FOUND", f"Static file '{name}' not found.")
    return FileResponse(path)


# ─────────────────────────────────────── static routes ──
async def home(request: Request) -> Response:
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


async def serve_css(request: Request) -> Response:
    return static_file("styles.css")


async def serve_js(request: Request) -> Response:
    return static_file("frontend.js")


async def serve_leaflet_css(request: Request) -> Response:
    return static_file("leaflet.css")


async def serve_leaflet_js(request: Request) -> Response:
    return static_file("leaflet.js")


async def serve_image(request: Request) -> Response:
    name = request.path_params.get("name", "")
    if ".." in name or "/" in name:
        return err(400, "BAD_PATH", "Invalid image path.")
    return static_file(os.path.join("images", name))


# ─────────────────────────────────────── v1 endpoints ──
async def health(request: Request) -> JSONResponse:
    return JSONResponse({
        "status":            "ok",
        "version":           "2.0",
        "nodes":             len(GRAPH["nodes"]),
        "edges":             N_EDGES,
        "data_sources":      ["OpenStreetMap / Overpass", "Open-Meteo"],
        "real_data_enabled": True,
    })


async def sun_endpoint(request: Request) -> JSONResponse:
    try:
        hour = float(request.query_params.get("hour", "13"))
        lat  = float(request.query_params.get("lat",  "26.9"))
    except ValueError:
        return err(400, "BAD_INPUT", "hour and lat must be numbers")
    if not 0 <= hour <= 24:
        return err(400, "BAD_INPUT", "hour must be 0–24")
    return JSONResponse({
        "hour":         hour,
        "lat":          lat,
        "sun_strength": round(sun_factor(hour, lat), 4),
    })


async def graph_endpoint(request: Request) -> JSONResponse:
    return JSONResponse({
        "nodes": GRAPH["nodes"],
        "edges": [
            {"id": k,
             **{key: e[key] for key in
                ("a", "b", "length", "shade", "step_free", "wait", "confidence")}}
            for k, e in enumerate(GRAPH["edges"])
        ],
    })


async def route_endpoint(request: Request) -> JSONResponse:
    """Synthetic demo routing (no internet required)."""
    try:
        body = await request.json()
    except Exception:
        return err(400, "BAD_JSON", "Request body must be valid JSON.")
    try:
        src       = snap_synthetic(body["origin"])
        dst       = snap_synthetic(body["destination"])
        hour      = float(body.get("hour", 13))
        budget    = float(body.get("heat_budget_pct", 60))
        step_free = bool(body.get("step_free", False))
        shade_on  = bool(body.get("shade_available", True))
        closed    = body.get("closed_edge_ids", [])
        if not 0 <= hour <= 24:
            raise ValueError("hour must be 0–24")
        if not 10 <= budget <= 100:
            raise ValueError("heat_budget_pct must be 10–100")
        if not isinstance(closed, list) or \
                any((not isinstance(c, int) or not 0 <= c < N_EDGES) for c in closed):
            raise ValueError(f"closed_edge_ids must be integers 0–{N_EDGES - 1}")
        if src == dst:
            raise ValueError("origin and destination are the same place")
    except KeyError as exc:
        return err(400, "BAD_INPUT", f"Missing required field: {exc}")
    except (ValueError, TypeError) as exc:
        return err(400, "BAD_INPUT", str(exc))

    g = copy.deepcopy(GRAPH)
    for c in closed:
        g["edges"][c]["closed"] = True
    r = plan(g, src, dst, hour, budget, step_free, shade_on)
    if "error" in r:
        return err(404, "NO_ROUTE",
                   "No route exists with the closed footpaths and step-free rule given.")

    base = route_summary_synthetic(g, r["baseline"], shade_on, r["sun"])
    cool = route_summary_synthetic(g, r["cool"],     shade_on, r["sun"])
    warnings = []
    if not r["budget_met"]:
        warnings.append({"code": "BUDGET_NOT_MET",
                         "message": "Heat budget cannot be met. This is the coolest route available."})
    if cool["distance_m"] > 1.2 * base["distance_m"]:
        warnings.append({"code": "LARGE_DETOUR",
                         "message": "The cooler route adds more than 20% to your walk distance."})
    if cool["missing_data_segments"]:
        warnings.append({"code": "MISSING_DATA",
                         "message": f"{cool['missing_data_segments']} of "
                                    f"{cool['segments']} segments have missing shade data."})
    if step_free:
        warnings.append({"code": "STEP_FREE",
                         "message": "Only step-free (no-stairs) segments were used."})
    return JSONResponse({
        "sun_strength": round(r["sun"], 3),
        "heat_budget":  round(r["budget"], 1),
        "budget_met":   r["budget_met"],
        "baseline":     base,
        "coolroute":    cool,
        "explanation":  explain(r, base, cool),
        "warnings":     warnings,
        "note":         "Heat exposure is a relative planning score, not medical advice.",
    })


# ─────────────────────────────────────── real-data endpoints ──
async def real_area(request: Request) -> JSONResponse:
    try:
        raw_bbox = request.query_params.get("bbox", "")
        bbox     = bounded_bbox(raw_bbox.split(","))
        area     = await run_in_threadpool(area_data, bbox)
        graph    = await run_in_threadpool(graph_from_area, area)
        if not graph["edges"]:
            return err(404, "NO_STREETS",
                       "No walkable streets found here. Try zooming out slightly.")
        area["graph"] = graph
        return JSONResponse(area)
    except (ValueError, TypeError) as exc:
        return err(400, "BAD_INPUT", str(exc))
    except Exception as exc:
        return JSONResponse(
            {
                "error": {
                    "code":    "OPEN_DATA_UNAVAILABLE",
                    "message": str(exc),
                },
                "retryable": True,
            },
            status_code=502,
        )


async def real_weather(request: Request) -> JSONResponse:
    try:
        lat  = float(request.query_params["lat"])
        lon  = float(request.query_params["lon"])
        hour = request.query_params.get("hour")
        if not (-85 <= lat <= 85 and -180 <= lon <= 180):
            raise ValueError("lat/lon are outside valid bounds")
        result = await run_in_threadpool(weather_at, lat, lon, hour)
        return JSONResponse(result)
    except KeyError as exc:
        return err(400, "BAD_INPUT", f"Missing parameter: {exc}")
    except (ValueError, TypeError) as exc:
        return err(400, "BAD_INPUT", str(exc))
    except Exception as exc:
        return err(502, "WEATHER_UNAVAILABLE",
                   f"Weather data temporarily unavailable: {exc}")


async def geocode_endpoint(request: Request) -> JSONResponse:
    try:
        place = await run_in_threadpool(
            geocode_place, request.query_params.get("q", ""))
        return JSONResponse(place)
    except ValueError as exc:
        return err(400, "BAD_INPUT", str(exc))
    except LookupError as exc:
        return err(404, "PLACE_NOT_FOUND", str(exc))
    except Exception as exc:
        return err(502, "GEOCODER_UNAVAILABLE", str(exc))


async def place_suggestions_endpoint(request: Request) -> JSONResponse:
    try:
        places = await run_in_threadpool(search_places, request.query_params.get("q", ""))
        return JSONResponse({"places": places})
    except ValueError as exc:
        return err(400, "BAD_INPUT", str(exc))
    except Exception as exc:
        return err(502, "GEOCODER_UNAVAILABLE", str(exc))


def set_auth_cookie(response: Response, request: Request, token: str) -> None:
    response.set_cookie(
        "coolroute_session", token,
        max_age=auth_store.SESSION_SECONDS,
        httponly=True, secure=request.url.scheme == "https",
        samesite="strict", path="/",
    )


async def auth_me(request: Request) -> JSONResponse:
    email = await run_in_threadpool(
        auth_store.session_email, request.cookies.get("coolroute_session"))
    return JSONResponse({"authenticated": bool(email), "email": email})


async def auth_signup(request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except Exception:
        return err(400, "BAD_JSON", "Enter an email address and password.")
    try:
        email = await run_in_threadpool(auth_store.register,
                                        data.get("email"), data.get("password"))
        token, _ = await run_in_threadpool(auth_store.new_session, email)
        response = JSONResponse({"authenticated": True, "email": email}, status_code=201)
        set_auth_cookie(response, request, token)
        return response
    except LookupError as exc:
        return err(409, "ACCOUNT_EXISTS", str(exc))
    except ValueError as exc:
        return err(400, "BAD_INPUT", str(exc))
    except Exception:
        return err(500, "ACCOUNT_ERROR", "Could not create the local account.")


async def auth_signin(request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except Exception:
        return err(400, "BAD_JSON", "Enter an email address and password.")
    try:
        email = await run_in_threadpool(auth_store.authenticate,
                                        data.get("email"), data.get("password"))
        token, _ = await run_in_threadpool(auth_store.new_session, email)
        response = JSONResponse({"authenticated": True, "email": email})
        set_auth_cookie(response, request, token)
        return response
    except PermissionError as exc:
        return err(401, "INVALID_CREDENTIALS", str(exc))
    except ValueError as exc:
        return err(400, "BAD_INPUT", str(exc))
    except Exception:
        return err(500, "ACCOUNT_ERROR", "Could not sign in to this local account.")


async def auth_signout(request: Request) -> JSONResponse:
    await run_in_threadpool(auth_store.delete_session,
                            request.cookies.get("coolroute_session"))
    response = JSONResponse({"authenticated": False})
    response.delete_cookie("coolroute_session", path="/", httponly=True,
                           samesite="strict", secure=request.url.scheme == "https")
    return response


async def route_history_get(request: Request) -> JSONResponse:
    email = await run_in_threadpool(
        auth_store.session_email, request.cookies.get("coolroute_session"))
    if not email:
        return err(401, "AUTH_REQUIRED", "Sign in to view saved walks.")
    try:
        limit = max(1, min(100, int(request.query_params.get("limit", "50"))))
        offset = max(0, int(request.query_params.get("offset", "0")))
        history = await run_in_threadpool(auth_store.get_route_history, email, limit + 1, offset)
        has_more = len(history) > limit
        return JSONResponse({"history": history[:limit], "has_more": has_more})
    except Exception:
        return err(500, "HISTORY_ERROR", "Could not load saved walks from the local database.")


async def route_history_save(request: Request) -> JSONResponse:
    email = await run_in_threadpool(
        auth_store.session_email, request.cookies.get("coolroute_session"))
    if not email:
        return err(401, "AUTH_REQUIRED", "Sign in to save this walk.")
    try:
        body = await request.json()
        route_key = str(body.get("route_key", ""))
        if not route_key or len(route_key) > 80:
            raise ValueError("Missing route identifier.")

        def point(name: str) -> dict:
            raw = body.get(name)
            lat, lon = float(raw["lat"]), float(raw["lon"])
            if not (math.isfinite(lat) and math.isfinite(lon) and -85 <= lat <= 85 and -180 <= lon <= 180):
                raise ValueError(f"Invalid {name} coordinates.")
            return {"lat": lat, "lon": lon}

        def clean_metrics(raw: object) -> dict:
            if not isinstance(raw, dict):
                return {}
            clean = {}
            for key in ("distance_m", "walk_time_min", "shaded_share", "heat_exposure"):
                value = raw.get(key)
                if value is None:
                    clean[key] = None
                    continue
                number = float(value)
                if not math.isfinite(number) or number < 0:
                    raise ValueError("Route metrics must be non-negative numbers.")
                clean[key] = round(number, 3)
            return clean

        preferences = body.get("preferences") or {}
        record = {
            "route_key": route_key,
            "origin": point("origin"),
            "destination": point("destination"),
            "origin_label": str(body.get("origin_label") or "Start")[:160],
            "destination_label": str(body.get("destination_label") or "Destination")[:160],
            "city": str(body.get("city") or "")[:160],
            "preferences": {
                "hour": min(24.0, max(0.0, float(preferences.get("hour", 13)))),
                "heat_budget_pct": min(100.0, max(10.0, float(preferences.get("heat_budget_pct", 60)))),
                "step_free": bool(preferences.get("step_free", False)),
                "shade_available": bool(preferences.get("shade_available", True)),
            },
            "metrics": {
                "shortest": clean_metrics(body.get("shortest")),
                "coolroute": clean_metrics(body.get("coolroute")),
            },
        }
        result = await run_in_threadpool(auth_store.save_route_history, email, record)
        return JSONResponse({"saved": True, **result})
    except (ValueError, TypeError, KeyError) as exc:
        return err(400, "BAD_HISTORY", str(exc))
    except Exception:
        return err(500, "HISTORY_ERROR", "Could not save this walk to the local database.")


class RequireAccountMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/v1/") and not request.url.path.startswith("/api/v1/auth/"):
            email = await run_in_threadpool(
                auth_store.session_email, request.cookies.get("coolroute_session"))
            if not email:
                return err(401, "AUTH_REQUIRED", "Sign in to use CoolRoute.")
        return await call_next(request)


async def real_route(request: Request) -> JSONResponse:
    """Real-data routing using live OSM + Open-Meteo data."""
    try:
        body = await request.json()
    except Exception:
        return err(400, "BAD_JSON", "Request body must be valid JSON.")

    try:
        bbox        = bounded_bbox(body["bbox"])
        origin      = body["origin"]
        destination = body["destination"]
        lat         = float(origin["lat"])
        lon         = float(origin["lon"])
        dlat        = float(destination["lat"])
        dlon        = float(destination["lon"])
        hour        = float(body.get("hour", 13))
        budget      = float(body.get("heat_budget_pct", 60))
        step_free   = bool(body.get("step_free", False))
        shade_avail = bool(body.get("shade_available", True))

        if not 0 <= hour <= 24:
            raise ValueError("hour must be 0–24")
        if not 10 <= budget <= 100:
            raise ValueError("heat_budget_pct must be 10–100")
        if not (-85 <= lat <= 85 and -180 <= lon <= 180):
            raise ValueError("origin lat/lon are outside valid bounds")
        if not (-85 <= dlat <= 85 and -180 <= dlon <= 180):
            raise ValueError("destination lat/lon are outside valid bounds")

    except KeyError as exc:
        return err(400, "BAD_INPUT", f"Missing required field: {exc}")
    except (ValueError, TypeError) as exc:
        return err(400, "BAD_INPUT", str(exc))

    try:
        area  = await run_in_threadpool(area_data, bbox)
        graph = await run_in_threadpool(graph_from_area, area)
    except (ValueError, TypeError) as exc:
        return err(400, "BAD_INPUT", str(exc))
    except Exception as exc:
        return err(502, "OPEN_DATA_UNAVAILABLE",
                   f"Street data temporarily unavailable: {exc}")

    if not graph["edges"]:
        return err(404, "NO_STREETS",
                   "No walkable streets found in this map area.")

    # Validate and apply closed edge IDs
    closed = body.get("closed_edge_ids", [])
    if not isinstance(closed, list) or \
            any(not isinstance(i, int) or i < 0 or i >= len(graph["edges"])
                for i in closed):
        return err(400, "BAD_INPUT",
                   "closed_edge_ids must be valid edge IDs from the loaded map.")
    for eid in closed:
        graph["edges"][eid]["closed"] = True

    # Snap to nearest graph nodes
    def nearest(pt_lat: float, pt_lon: float) -> int:
        return min(graph["nodes"],
                   key=lambda n: (n["lat"] - pt_lat) ** 2 +
                                 (n["lon"] - pt_lon) ** 2)["id"]

    src = nearest(lat, lon)
    dst = nearest(dlat, dlon)
    if src == dst:
        return err(400, "BAD_INPUT",
                   "Origin and destination map to the same street junction — "
                   "please choose points further apart.")

    # Weather and sun
    try:
        weather = await run_in_threadpool(weather_at, lat, lon, hour)
    except Exception:
        # Routes can still be calculated with the local astronomical model if
        # the forecast provider is temporarily unavailable.
        weather = {
            "time": None, "timezone": "estimated from location",
            "utc_offset_seconds": None, "temperature_c": None,
            "relative_humidity_pct": None, "cloud_cover_pct": None,
            "shortwave_radiation_w_m2": None, "wind_speed_kmh": None,
            "source": "Astronomical sun estimate (forecast unavailable)",
            "license": None,
        }

    radiation   = weather.get("shortwave_radiation_w_m2")
    weather_sun = min(1.0, max(0.0, float(radiation or 0) / 850.0))
    solar_sun   = sun_for_location(
        lat, hour, lon=lon, utc_offset_seconds=weather.get("utc_offset_seconds"))
    sun         = weather_sun if radiation is not None else solar_sun

    # Run routing
    result = plan(graph, src, dst, hour, budget,
                  step_free, shade_avail, sun_override=sun)
    if "error" in result:
        return err(404, "NO_ROUTE",
                   "No route connects these points with the selected options.")

    def summary(side: dict) -> dict:
        m   = side["m"]
        ids = side["edges"]
        total_len = sum(graph["edges"][i]["length"] for i in ids) or 1.0
        shade_len = sum(graph["edges"][i]["length"] *
                        (graph["edges"][i]["shade"] if shade_avail else 0.0)
                        for i in ids)
        return {
            "nodes":       side["nodes"],
            "coordinates": [[graph["nodes"][i]["lat"], graph["nodes"][i]["lon"]]
                            for i in side["nodes"]],
            "distance_m":            round(m["dist"], 1),
            "walk_time_min":         round(m["time"] / 60, 1),
            "heat_exposure":         round(m["heat"], 1),
            "shaded_share":          round(shade_len / total_len, 3),
            "data_confidence":       round(m["data_confidence"], 2),
            "missing_data_segments": m["missing_edges"],
            "segments":              m["n_edges"],
            "edge_ids":              ids,
        }

    base = summary(result["baseline"])
    cool = summary(result["cool"])

    cut = max(0.0, 100 * (1 - cool["heat_exposure"] / max(base["heat_exposure"], 1e-9)))

    warnings = []
    if not result["budget_met"]:
        warnings.append({
            "code":    "BUDGET_NOT_MET",
            "message": "The heat budget cannot be met. This is the coolest route available.",
        })
    if cool["data_confidence"] < 0.6:
        warnings.append({
            "code":    "MISSING_SHADE",
            "message": "Shade is inferred from nearby mapped features; "
                       "unmapped shade is not included.",
        })
    if step_free:
        warnings.append({
            "code":    "STEP_FREE",
            "message": "Only step-free (no-stairs) segments were used.",
        })

    return JSONResponse({
        "sun_strength": round(sun, 3),
        "heat_budget":  round(result["budget"], 1),
        "budget_met":   result["budget_met"],
        "heat_cut_pct": round(cut, 1),
        "baseline":     base,
        "coolroute":    cool,
        "weather":      weather,
        "data_source":  area["source"],
        "shade_method": (
            "Mapped trees within 14 m (+0.48 shade) and building footprints "
            "within 9 m (+0.28 shade); proxy estimate, not a measured shadow."
        ),
        "attribution":  area["attribution"],
        "warnings":     warnings,
        "note":         "Heat exposure is a relative planning score, not medical advice.",
    })


async def real_directions(request: Request) -> JSONResponse:
    """Fast pedestrian street route independent of the slower shade-area fetch."""
    try:
        body = await request.json()
        origin, destination = body["origin"], body["destination"]
        for point in (origin, destination):
            lat, lon = float(point["lat"]), float(point["lon"])
            if not (-85 <= lat <= 85 and -180 <= lon <= 180):
                raise ValueError("Coordinates are outside valid bounds.")
        if abs(float(origin["lat"]) - float(destination["lat"])) + abs(float(origin["lon"]) - float(destination["lon"])) < 1e-6:
            raise ValueError("Choose start and destination points farther apart.")
    except (KeyError, TypeError, ValueError) as exc:
        return err(400, "BAD_INPUT", str(exc))
    except Exception:
        return err(400, "BAD_JSON", "Request body must contain valid origin and destination coordinates.")
    try:
        result = await run_in_threadpool(walking_directions, origin, destination)
    except Exception as exc:
        return err(502, "DIRECTIONS_UNAVAILABLE", f"Walking directions are temporarily unavailable: {exc}")
    return JSONResponse(result)


# ─────────────────────────────────────── CORS preflight ──
async def preflight(request: Request) -> Response:
    return Response(status_code=204, headers={
        "Access-Control-Allow-Origin":  "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    })


# ─────────────────────────────────────── app ──
app = Starlette(
    routes=[
        # Static files (all served locally — no CDN dependency)
        Route("/",                     home),
        Route("/styles.css",           serve_css),
        Route("/frontend.js",          serve_js),
        Route("/leaflet.css",          serve_leaflet_css),
        Route("/leaflet.js",           serve_leaflet_js),
        Route("/images/{name:str}",    serve_image),

        # Local account sessions
        Route("/api/v1/auth/me",     auth_me),
        Route("/api/v1/auth/signup", auth_signup, methods=["POST"]),
        Route("/api/v1/auth/signin", auth_signin, methods=["POST"]),
        Route("/api/v1/auth/signout", auth_signout, methods=["POST"]),

        # Durable, account-specific route history
        Route("/api/v1/history", route_history_get),
        Route("/api/v1/history", route_history_save, methods=["POST"]),

        # Core API
        Route("/api/v1/health",  health),
        Route("/api/v1/sun",     sun_endpoint),
        Route("/api/v1/graph",   graph_endpoint),
        Route("/api/v1/route",   route_endpoint,  methods=["POST", "OPTIONS"]),

        # Real-data API
        Route("/api/v1/real/area",    real_area),
        Route("/api/v1/real/weather", real_weather),
        Route("/api/v1/real/geocode", geocode_endpoint),
        Route("/api/v1/real/search", place_suggestions_endpoint),
        Route("/api/v1/real/route",   real_route,  methods=["POST", "OPTIONS"]),
        Route("/api/v1/real/directions", real_directions, methods=["POST", "OPTIONS"]),
    ],
    middleware=[Middleware(RequireAccountMiddleware)],
)
