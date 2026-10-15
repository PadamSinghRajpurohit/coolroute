# CoolRoute

CoolRoute is a local-first pedestrian route planner. It compares the shortest walk with a route that trades distance for a lower relative heat-exposure score.

## Live app

- OpenStreetMap tiles and real nearby pedestrian streets
- Mapped trees and buildings used to estimate which street segments may have shade
- Open-Meteo hourly forecast for temperature, humidity, cloud cover and shortwave radiation
- Local shortest-path and heat-budget routing, with distance, walk time, shaded share and confidence shown side by side
- Map-click start/end selection, browser location, step-free filter, shade toggle, closed-street mode, time and heat-budget controls

Shade is an estimate from nearby mapped features, not an observed shadow measurement. Heat is a relative comparison score and not medical advice. See `README.md` and `11_Real_Data_Implementation_Plan.pdf` for the data flow and operating limits.

## Run locally

Use Python 3.10+, then run `start_windows.bat` or follow the PowerShell commands in `README.md`. The app opens at `http://127.0.0.1:8765`.

## API

- `GET /api/v1/health`
- `GET /api/v1/real/area?bbox=south,west,north,east`
- `GET /api/v1/real/weather?lat=...&lon=...&hour=...`
- `POST /api/v1/real/route`

The original synthetic endpoints are kept for controlled demos and comparisons.
