# IBM BOB implementation brief

Build and maintain CoolRoute as a local-first pedestrian route planner.

## Current implementation

- `index.html`, `styles.css`, and `frontend.js` are the map-first responsive interface. Keep map clicks, start/end selection, route comparison, time and heat budget sliders, step-free filter, shade toggle, street closures, location control, theme toggle, and clear warnings working.
- `api_server.py` is the Starlette API and local web server. `real_data.py` reads bounded OpenStreetMap street/tree/building data from Overpass and hourly weather from Open-Meteo. `core.py` performs shortest-path and heat-aware routing.
- Public endpoints need internet and can be rate-limited. Keep provider URLs configurable and cache requests. Never add a paid API key to frontend code or commit secrets.
- OSM tree/building proximity is only a shade proxy. Label it as estimated. Do not describe it as actual measured shade or medical heat risk.

## Product direction

Keep the dark forest/teal visual identity, readable contrast, mobile layout, large controls, correct action colors, visible OpenStreetMap attribution, and a concise route verdict. Use orange for the shortest route, teal for the cooler route, green for shade, and red for closed streets/errors. All route metrics must come from backend results, not fabricated frontend values.

## Local run

Use Python 3.10+ and `pip install -r requirements.txt`, then `python -m uvicorn api_server:app --host 127.0.0.1 --port 8765`; open `http://127.0.0.1:8765`. Follow `README.md` and the numbered PDF architecture/data-source documents before changing the data flow.
