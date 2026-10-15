# CoolRoute

CoolRoute is a local-first pedestrian route planner. It compares the shortest walk with a route that trades distance for a lower relative heat-exposure score.

The current app uses OpenStreetMap street data, nearby mapped trees/buildings for an approximate shade proxy, Open-Meteo hourly weather, and local route search. Map-click start/end selection, browser location, step-free filter, street closures, time/budget controls, and route comparison are available.

Shade is not measured shadow data, and heat is a route comparison score rather than medical advice. See `README.md` and `11_Real_Data_Implementation_Plan.pdf`.

Run on Windows with `start_windows.bat`, or follow the setup commands in `README.md`. Open `http://127.0.0.1:8765`.
