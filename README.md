# CoolRoute

**Heat-aware pedestrian route planner** — compares the shortest walk with a cooler (shaded) alternative using real OpenStreetMap streets and live Open-Meteo weather. Runs entirely on your local machine. No paid API key required.

The app includes local email/password sign-in and sign-up. Accounts, sessions, and each user's saved route history are stored in the ignored `data/coolroute.sqlite3` file; passwords are salted PBKDF2 hashes and the browser receives an HttpOnly session cookie. Route history is not automatically deleted. No email verification or password-reset email is sent because no mail provider is configured. There are no private third-party API keys in the browser bundle; map, geocoding, street and weather data use public services.

---

## Quick Start (Windows)

Double-click `start_windows.bat` — or open PowerShell in this folder and run:

```powershell
.\start_windows.bat
```

The launcher selects an available port from 8765–8769 and opens the correct URL only after the backend is ready. If another program is already using 8765, CoolRoute may open on 8766 or the next free port; use the exact URL printed in the launcher, not an old browser bookmark. Keep the terminal open while using the app; press **Ctrl+C** to stop it.

To start manually instead, open a terminal in this folder and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn api_server:app --host 127.0.0.1 --port 8765
```

> **First launch** creates a `.venv` and installs two packages (starlette, uvicorn). Requires Python 3.10+.
> Restart the server after updating the project files so the account and city-search endpoints load.

---

## How to use

1. Start the backend and open the local URL above. Do not open `index.html` directly; the backend API needs to run.
2. Create a local account or sign in. Accounts are local to this server; use **Create account** the first time.
3. The map loads first and automatically tries backup tile sources if the primary basemap is unavailable. Search for any city or place above the map; Jaipur is only the initial view. Place search uses free OpenStreetMap Nominatim and does not ask for device location permission.
4. **Click anywhere** on the map to set your **start point**, then click again to set your destination. You can also use the Start and End controls.
5. Optionally adjust time-of-day, heat budget, step-free toggle, shade toggle.
6. Click **Find my cooler route** — two routes are drawn:
   - 🟠 Orange = shortest distance
   - 🟢 Teal = cooler (shaded) route
6. Route metrics and live weather are shown in the panel. Each planned walk is saved under **Your walk history** for the signed-in account and can be restored with **Use route**.

### Keeping route history

The SQLite database at `data/coolroute.sqlite3` is local and Git-ignored. Do not delete the `data` folder if you want to keep accounts and saved walks. To make a backup, stop CoolRoute with **Ctrl+C**, then copy `data/coolroute.sqlite3` to a safe location. To restore it, stop the app and copy the backup back into `data/`.

The map-selection message is a small banner and does not cover the map. If all basemap providers are unavailable, the map area remains visible and the app will still draw real street segments when Overpass responds. If street data is still loading, the app shows a clearly labeled straight-line estimate; re-plan once the street overlay appears.

After updating files, restart the backend with `start_windows.bat` so account and place-search routes are loaded. If the server is already running in a terminal, press **Ctrl+C** there before starting the batch file again.

---

## File Overview

| File | Purpose |
|---|---|
| `api_server.py` | Starlette HTTP server — serves frontend + JSON API |
| `core.py` | Routing algorithm: Dijkstra + Lagrangian bisection, sun model |
| `real_data.py` | OSM/Overpass street data + Open-Meteo weather adapters |
| `index.html` | Frontend HTML shell |
| `styles.css` | Dark/light theme, fully offline (no CDN) |
| `frontend.js` | All client-side logic — map, routing, weather |
| `auth_store.py` | Local account hashes and server-side sessions |
| `leaflet.css` | Leaflet map library CSS — **served locally** |
| `leaflet.js` | Leaflet map library JS — **served locally** |
| `images/` | Leaflet marker/layer images — **served locally** |
| `requirements.txt` | Python deps: starlette, uvicorn |
| `start_windows.bat` | One-click Windows launcher |
| `test_core.py` | 13 unit tests for routing logic |
| `test_api.py` | Live API integration tests (server must be running) |

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `GET /api/v1/health` | GET | Server status |
| `GET /api/v1/sun?hour=13&lat=26.9` | GET | Sun strength 0–1 |
| `GET /api/v1/graph` | GET | Synthetic demo graph |
| `POST /api/v1/route` | POST | Synthetic demo routing |
| `GET /api/v1/real/area?bbox=S,W,N,E` | GET | OSM streets + graph |
| `GET /api/v1/real/weather?lat=&lon=&hour=` | GET | Open-Meteo forecast |
| `POST /api/v1/real/route` | POST | **Main** — real heat-aware routing |

### POST /api/v1/real/route — request body

```json
{
  "origin":          { "lat": 26.912, "lon": 75.787 },
  "destination":     { "lat": 26.920, "lon": 75.795 },
  "bbox":            [26.905, 75.780, 26.925, 75.800],
  "hour":            13,
  "heat_budget_pct": 60,
  "step_free":       false,
  "shade_available": true,
  "closed_edge_ids": []
}
```

---

## Mathematics

**Heat exposure per edge:**
```
heat = length × (1 − shade) × sun(t)
```

**Sun strength (astronomical model):**
```
sin(elev) = sin(φ)·sin(δ) + cos(φ)·cos(δ)·cos(h)
δ = 23.45° × sin(360/365 × (day − 81))
h = 15° × (hour − 12)
```

**CoolRoute algorithm — Lagrangian relaxation:**
```
cost = distance + λ × heat
```
Bisection search over λ (40 iterations) finds the smallest λ such that `heat ≤ budget`.

**Shade proxy from OSM features:**
- Mapped tree within 14 m → +0.48 shade
- Mapped building centre within 18 m → +0.28 shade (fast proxy)
- Capped at 0.85

---

## Data Sources

| Source | What | Licence |
|---|---|---|
| OpenStreetMap via Overpass API | Streets, trees, buildings | ODbL |
| Open-Meteo | Hourly forecast (temp, humidity, cloud, radiation) | CC BY 4.0 (non-commercial free tier) |

No API key required for either source. For commercial deployment use a paid/self-hosted Overpass instance.

---

## Run Tests

```powershell
# Unit tests (no server needed)
py -3 test_core.py

# API integration tests (server must be running on :8765)
py -3 test_api.py
```
