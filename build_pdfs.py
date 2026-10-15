import json, os
from pdfkit import *
from core import sun_factor

S = json.load(open("stats.json"))
T = json.load(open("test_results.json"))
A = json.load(open("api_test_results.json"))
AS = json.load(open("api_samples.json"))
D, MANY, ML, REV = S["demo"], S["many"], S["ml"], S["rev"]
F = "figs/"
OUT = "pdfs/"
os.makedirs(OUT, exist_ok=True)
CW = W - 2 * M

cut_pct = 100 * (1 - D["cool_heat"] / D["base_heat"])
extra_m = D["cool_dist"] - D["base_dist"]
extra_pct = 100 * (D["cool_dist"] / D["base_dist"] - 1)
SP = Spacer(1, 4)

# =====================================================================
# 01  PITCH AND OVERVIEW
# =====================================================================
def doc01():
    s = [P("<b>One line:</b> CoolRoute is a walking route planner that finds the shortest route and a cooler route, "
           "then explains in plain words what the cooler route costs and gives.", "body"),
         H1("1. The problem"),
         P("The shortest walking route is often the hottest. It may run along open roads with no shade, cross wide junctions "
           "and make people stand in the sun at a red light. Normal map apps count distance and time. They do not count heat."),
         P("In a hot city like Jaipur this matters most for older people, children, workers who walk to work, tourists and "
           "people who cannot use steps. A good planner should (1) count shade, time of day, effort and accessibility, and "
           "(2) say honestly when the cooler route is too long or when its data is weak."),
         H1("2. Our solution"),
         bullets(["Streets and crossings are a <b>graph</b>. Each street piece has length, shade, slope, step-free flag, crossing wait and a data-confidence value.",
                  "We compute two routes: the <b>shortest route</b> and the <b>CoolRoute</b>, which is the shortest route that still fits a <b>heat budget</b> the user sets.",
                  "<b>Step-free</b> is a hard rule. We never trade it away for shade.",
                  "The app shows a <b>plain-words trade-off</b> ('23 m longer, 40% less heat'), flags <b>missing data</b>, and never presents heat as a medical risk."]),
         fig(F + "fig_routes.png", 105, "Figure 1. Shortest route (orange halo) and CoolRoute (teal) between A and B at 1 pm. Green streets are tree-lined."),
         H1("3. Result on the demo trip"),
         table([["Measure", "Shortest route", "CoolRoute", "Change"],
                ["Distance", f"{D['base_dist']:.0f} m", f"{D['cool_dist']:.0f} m", f"+{extra_m:.0f} m (+{extra_pct:.1f}%)"],
                ["Walk time (with crossing waits)", f"{D['base_time']/60:.1f} min", f"{D['cool_time']/60:.1f} min", f"{(D['cool_time']-D['base_time'])/60:+.1f} min"],
                ["Heat exposure", f"{D['base_heat']:.0f}", f"{D['cool_heat']:.0f}", f"-{cut_pct:.0f}%"],
                ["Shaded share of the walk", f"{100*D['base_shade']:.0f}%", f"{100*D['cool_shade']:.0f}%", f"+{100*(D['cool_shade']-D['base_shade']):.0f} points"]],
               [CW * .34, CW * .22, CW * .2, CW * .24]),
         SP,
         P(f"Over {MANY['trips']} random long trips at 1 pm with a 60% budget, the median route cut heat by <b>{MANY['median_cut']:.0f}%</b> "
           f"for a median <b>{MANY['median_extra']:.1f}%</b> extra distance (details in file 07).", "body"),
         H1("4. Does it cover every requirement?"),
         table([["Requirement from the problem statement", "How we cover it", "Where to see it"],
                ["Map or synthetic neighbourhood with at least two route choices", "8 x 8 street grid, two routes always drawn", "Prototype map"],
                ["Baseline shortest-path route and an exposure-aware route with trade-offs", "Dijkstra baseline + Lagrangian heat-budget route; plain-words verdict and comparison table", "Prototype: 'Which route should I walk?'"],
                ["Scenario controls: time of day, shade, closed footpath", "Time slider, shade toggle, tap-to-close footpath", "Prototype: Scenario controls"],
                ["Graph with length, shade, slope/accessibility, time-dependent heat", "All five attributes on every street piece; heat uses a solar model", "File 06 and 04"],
                ["Optimise a heat budget with hard constraints such as step-free", "Budget slider; step-free removes non-step-free segments before searching", "Prototype toggle; test 6 and 7"],
                ["Show missing data; no precise personal medical risk", "Dashed streets, warnings, data-confidence row; note on every result", "Prototype map and warnings"]],
               [CW * .36, CW * .40, CW * .24]),
         H1("5. What is real and what is a plan"),
         callout("<b>Real and tested:</b> the routing engine, the heat model, the browser prototype, a working JSON backend, and 25 automated checks. "
                 "<b>Plan for real cities:</b> loading OpenStreetMap streets, tree-cover and building-shadow data for Jaipur, and training the shade model on that data. "
                 "The prototype uses a synthetic neighbourhood, and the ML demo uses synthetic data, so its accuracy numbers show the pipeline works. They do not prove real-world accuracy.", HEAT),
         H1("6. Why this can win"),
         bullets(["It is <b>complete</b>: map, two routes, explanation, scenarios, hard constraints, missing-data warnings.",
                  "It is <b>honest</b>: it shows when the cooler route is too long or the data is weak, which is what the problem statement asks for.",
                  "It is <b>proven</b>: tests for failure cases, and the same results in Python and JavaScript on 60 random scenarios.",
                  "It is <b>simple to explain</b>: one formula for heat, one knob for the budget, one sentence for the trade-off.",
                  "It has a <b>business path</b>: city licences, a route API, and a premium app (file 08)."]),
         H1("7. The package"),
         table([["File", "What it contains"],
                ["01 Pitch and Overview", "This document"], ["02 App Flow", "User journey, system flow, edge cases"],
                ["03 Frontend", "Screens, stack, design rules, code structure"], ["04 Backend and Architecture", "Services, data model, algorithm, deployment"],
                ["05 API and Data Sources", "Our API, example calls, outside data sources"], ["06 Maths and ML", "All formulas with worked examples and charts"],
                ["07 Test Evidence", "Failure-case tests and experiment results"], ["08 Revenue and Business Model", "Customers, pricing, 3-year plan, risks"],
                ["09 Pitch Script and Q&A", "5-minute script, demo steps, judge questions"], ["10 Roadmap and Team Plan", "36-hour plan, next steps, setup"]],
               [CW * .33, CW * .67])]
    build(OUT + "01_Pitch_and_Overview.pdf", "Pitch and Overview", "What we built, why it matters, and how it meets every requirement", s, "01 Overview")


# =====================================================================
# 02  APP FLOW
# =====================================================================
def doc02():
    s = [H1("1. The user journey in seven steps"),
         fig(F + "fig_flow.png", 160, "Figure 1. From opening the app to an explained route choice."),
         table([["Step", "What the user does", "What the app does"],
                ["1", "Opens the app", "Shows the map with a sample trip and both routes already drawn, so the first screen is never empty."],
                ["2", "Taps a junction to set A and B", "Snaps the tap to the nearest junction and redraws both routes."],
                ["3", "Moves the time slider and the heat-budget slider", "Recomputes sun strength and both routes instantly (the search takes milliseconds on a small map)."],
                ["4", "Optional: turns on Step-free, turns off Shade, or closes a footpath", "Removes blocked segments before searching. Step-free is a hard rule."],
                ["5", "Looks at the shortest route", "Shows distance, time, heat, shade share, effort and data confidence."],
                ["6", "Looks at CoolRoute", "Shows the same numbers next to the shortest route, plus the change in each."],
                ["7", "Reads the verdict", "One sentence: how much longer, how much cooler, and why."]],
               [CW * .07, CW * .38, CW * .55]),
         H1("2. What happens inside one request"),
         code("""
User changes a control
  -> read state: A, B, hour, budget, step_free, shade_on, closed footpaths
  -> sun   = sun(hour)                        # 0 at night, about 0.77 at 1 pm
  -> graph = remove closed segments; if step_free: remove non-step-free segments
  -> base  = shortest path (lambda = 0)
  -> if no path: show 'No route found' message and stop
  -> budget = base.heat * budget_pct / 100
  -> if base.heat <= budget: cool = base
     else: search lambda by bisection (40 steps) so that cool.heat <= budget
  -> build warnings: budget not met, large detour, missing data, step-free note
  -> draw routes, fill table, write the verdict sentence
"""),
         H1("3. Edge cases the app must handle"),
         table([["Situation", "What the user sees", "Why"],
                ["No route exists (closed footpaths or step-free leave no path)", "'No route found' with a hint to reopen a footpath or turn off step-free", "Better than drawing a wrong route"],
                ["Heat budget too strict for this map", "Coolest route available plus warning 'budget cannot be met'", "The route is still useful; the user must know the limit"],
                ["Cooler route is more than 20% longer", "Warning 'Large detour' and a hint to raise the budget", "The problem statement asks to show when a cooler route adds too much distance"],
                ["Some streets have missing shade data", "Dashed streets, a count of missing segments, 'approximate' note", "Honest about uncertainty"],
                ["Night time (no sun)", "Both routes are the same; message explains why", "Heat is zero, so there is nothing to optimise"],
                ["Shortest route already fits the budget", "'CoolRoute keeps it'", "No pointless detour"],
                ["User sets A equal to B", "Tap on the same junction is ignored", "Avoids a zero-length trip"]],
               [CW * .33, CW * .37, CW * .30]),
         H1("4. Screen layout"),
         bullets(["<b>Phone:</b> map first, then scenario controls, then results, then the sun chart. One column, no sideways scrolling.",
                  "<b>Laptop (for the demo):</b> map on the left, controls and results on the right, so judges see everything without scrolling.",
                  "Every tap target is at least 32 px high. Colours work in light and dark mode."]),
         H1("5. Accessibility rules built into the flow"),
         bullets(["Step-free is a switch, not a hidden setting.",
                  "Routes differ by <b>line style and colour</b>, not colour alone (thick halo versus thin solid line).",
                  "Text explanation always accompanies the map, so screen-reader users get the same information.",
                  "Next step for production: audio and large-text versions of the verdict."])]
    build(OUT + "02_App_Flow.pdf", "App Flow", "How a person uses CoolRoute, and what the system does at each step", s, "02 App Flow")


# =====================================================================
# 03  FRONTEND
# =====================================================================
def doc03():
    s = [H1("1. What the frontend must do"),
         bullets(["Draw the street map and both routes clearly.", "Let the user change time, budget, shade, step-free and closed footpaths, and update at once.",
                  "Explain the trade-off in words, show a comparison table, and show warnings.", "Work on a phone and on a projector, in light and dark mode."]),
         H1("2. Stack: prototype and production"),
         table([["Layer", "Prototype (built)", "Production plan"],
                ["Language and UI", "Plain HTML, CSS and JavaScript in one file; no build step", "React with TypeScript"],
                ["Map", "SVG drawn from the street graph", "MapLibre GL JS with OpenStreetMap-based tiles"],
                ["Routing engine", "JavaScript port of the Python engine, runs in the browser", "Calls the backend /route API; same engine on the server"],
                ["Charts", "Inline SVG (sun curve)", "Recharts or Chart.js"],
                ["Styling", "CSS variables for colour tokens, light and dark themes", "Tailwind CSS with the same tokens"],
                ["Hosting", "Single static file", "Free static hosting such as GitHub Pages or Netlify"]],
               [CW * .18, CW * .41, CW * .41]),
         SP,
         P("The prototype is one file so it opens anywhere, even with no internet at the venue. All route calculations happen in the browser."),
         H1("3. Components"),
         table([["Component", "Job", "Input", "Output"],
                ["MapView", "Draws streets, crossings, missing-data dashes, closed footpaths, A and B pins, both routes", "graph, routes, state", "SVG"],
                ["ControlsPanel", "Time slider, budget slider, toggles, tap mode, buttons", "state", "state changes"],
                ["ResultsCard", "Verdict sentence, comparison table, warnings", "two routes, budget status", "text and table"],
                ["SunChart", "Sun strength through the day with the chosen time marked", "hour", "SVG"],
                ["HowItWorks", "Formulas in plain words and the 'not a medical risk' note", "none", "text"]],
               [CW * .17, CW * .43, CW * .2, CW * .2]),
         H1("4. State"),
         code("""
state = {
  start: 0, end: 63,        // junction ids
  hour: 13,                 // 5 .. 19, step 0.25
  budget: 60,               // percent of shortest-route heat
  stepFree: false,
  shade: true,              // shade available
  mode: "start" | "end" | "close"   // what a tap on the map does
}
graph.edges[k].closed       // true when the footpath is closed
render() = plan(graph, state) -> draw map -> fill table -> write verdict -> draw chart
"""),
         P("Every control calls one function, <font face='DVM'>render()</font>. There is no hidden state, so what the judge sees is always what the numbers say."),
         H1("5. Design rules"),
         table([["Rule", "How we applied it"],
                ["Colour has a meaning", "Teal = CoolRoute, orange = shortest route, green = shaded street, sand = sunny street, red dotted = closed"],
                ["Two ways to tell routes apart", "Colour and line style: the shortest route is a wide soft halo, CoolRoute is a thin solid line on top"],
                ["Plain words first", "The verdict sentence is above the table, in normal language"],
                ["Numbers line up", "Monospaced digits in the table so columns are easy to compare"],
                ["Light and dark", "All colours are tokens; dark mode redefines the tokens"],
                ["Phone first", "One column below 820 px; 16 px side gutters; tables scroll inside their own box"],
                ["Honest labels", "'Heat exposure' is a score for comparing routes. A note says it is not a medical risk"]],
               [CW * .3, CW * .7]),
         H1("6. File structure (production)"),
         code("""
frontend/
  src/
    components/  MapView.tsx  ControlsPanel.tsx  ResultsCard.tsx  SunChart.tsx
    lib/         api.ts  format.ts  sun.ts
    state/       useScenario.ts
    styles/      tokens.css
  public/        manifest.json   (installable PWA)
"""),
         H1("7. Performance and quality"),
         bullets(["The engine takes a few milliseconds on 64 junctions and 112 segments, so sliders update live.",
                  "For a real city, the backend does the search and the frontend only draws (see file 04).",
                  "Keyboard focus is visible, controls have labels, and tap targets are large.",
                  "The page was checked for script errors; engine results match Python exactly (file 07)."]),
         H1("8. How to run the prototype"),
         bullets(["Open <font face='DVM'>coolroute.html</font> in any browser. No install, no internet needed except for fonts, which fall back to system fonts.",
                  "The same page is also published as a link in the chat for easy sharing."])]
    build(OUT + "03_Frontend.pdf", "Frontend", "Screens, components, state and design rules", s, "03 Frontend")


# =====================================================================
# 04  BACKEND AND ARCHITECTURE
# =====================================================================
def doc04():
    s = [H1("1. Architecture at a glance"),
         fig(F + "fig_arch.png", 160, "Figure 1. Four layers: user, frontend, backend, data and models."),
         H1("2. Backend services"),
         table([["Service", "Job", "Status"],
                ["API gateway", "Checks input, returns JSON or clear errors", "Built (Starlette; moves to FastAPI with small changes)"],
                ["Routing engine", "Shortest path and heat-budget path (Dijkstra + lambda search)", "Built and tested"],
                ["Heat model", "heat = length x (1 - shade) x sun(t), plus crossing waits", "Built and tested"],
                ["Sun model", "Sun strength from latitude, date and hour", "Built and tested"],
                ["Shade model (ML)", "Predicts shade for each street piece from buildings and trees, with a confidence value", "Demo trained on synthetic data"],
                ["Data loader", "Builds the street graph from OpenStreetMap, adds tree and building data", "Plan (file 05)"],
                ["Cache", "Stores shade values by street piece and hour so routes are fast", "Plan"]],
               [CW * .2, CW * .5, CW * .3]),
         H1("3. Data model: one street piece (edge)"),
         table([["Field", "Meaning", "Example"],
                ["length", "Length in metres", "82.4"], ["shade", "Share of the street in shade, 0 to 1", "0.20"],
                ["slope", "Steepness in percent", "3"], ["step_free", "True if no steps or high kerb", "true"],
                ["wait", "Average wait at the crossing, seconds (0 if no crossing)", "35"],
                ["crossing_shade", "Share of the crossing in shade", "0.10"],
                ["confidence", "How much we trust the data, 0 to 1. Below 0.3 is shown as missing data", "0.71"],
                ["closed", "True if the footpath is closed in this scenario", "false"]],
               [CW * .2, CW * .55, CW * .25]),
         H1("4. The algorithm in plain steps"),
         code("""
function plan(graph, A, B, hour, budget_pct, step_free, shade_on):
    sun   = sun_strength(hour)
    adj   = build adjacency, skipping closed edges and (if step_free) non-step-free edges
    base  = dijkstra(adj, A, B, lambda = 0)                 # shortest distance
    if base is None: return NO_ROUTE
    budget = base.heat * budget_pct / 100
    if base.heat <= budget: return base, base
    lo, hi = 0, 50
    repeat 40 times:
        mid  = (lo + hi) / 2
        path = dijkstra(adj, A, B, lambda = mid)            # minimise distance + mid * heat
        if path.heat <= budget: best = path; hi = mid       # cool enough -> try a smaller lambda
        else:                   lo = mid                    # too hot -> push lambda up
    if nothing met the budget: best = dijkstra(..., lambda = hi)   # coolest available, flagged
    return base, best
"""),
         P("<b>Cost:</b> each Dijkstra run is O(E log V). We run it at most 41 times, so a request is about 41 x O(E log V). "
           "For a city-size graph we would add contraction hierarchies or a bounding box around A and B so each run stays fast."),
         H1("5. Database plan (production)"),
         code("""
-- PostgreSQL with PostGIS
CREATE TABLE edges (
  id BIGSERIAL PRIMARY KEY, a BIGINT, b BIGINT, geom geometry(LineString, 4326),
  length_m REAL, slope_pct REAL, step_free BOOLEAN, wait_s REAL, crossing_shade REAL
);
CREATE TABLE edge_shade (
  edge_id BIGINT REFERENCES edges(id), hour SMALLINT, shade REAL, confidence REAL,
  PRIMARY KEY (edge_id, hour)
);
CREATE INDEX edges_geom_idx ON edges USING GIST (geom);
"""),
         H1("6. Privacy and safety"),
         bullets(["No account is needed. Start and end points are used for the request and not stored.",
                  "Heat exposure is a <b>comparison score</b>. We never state a personal health risk. Every API response carries a note saying so.",
                  "Input is checked: bad ids, bad hours and bad budgets return a 400 error with a clear message (file 05).",
                  "When data is missing we lower the confidence and warn the user. We do not hide the gap."]),
         H1("7. Deployment (free-tier plan)"),
         table([["Part", "Option", "Note"],
                ["Frontend", "GitHub Pages or Netlify", "Static files. Check current free limits before relying on them"],
                ["Backend", "A free container host such as Render or Hugging Face Spaces", "Free tiers may sleep when idle. Warm it up before the demo"],
                ["Database", "A free PostgreSQL tier with PostGIS, or SQLite for the hackathon", "The prototype needs no database"],
                ["Fallback", "The browser prototype", "Works with no backend and no internet, so the demo cannot fail"]],
               [CW * .17, CW * .43, CW * .4]),
         H1("8. Backend tests"),
         P(f"We start the server, call it over HTTP, and check {len(A)} cases. All {sum(a['pass'] for a in A)} passed (see file 07)."),
         H1("9. Run it"),
         code("""
pip install uvicorn starlette
python3 -m uvicorn api_server:app --port 8765
curl -X POST localhost:8765/api/v1/route -H "Content-Type: application/json" \\
     -d '{"origin":{"node":0},"destination":{"node":63},"hour":13,"heat_budget_pct":60}'
""")]
    build(OUT + "04_Backend_and_Architecture.pdf", "Backend and Architecture", "Services, data model, algorithm, database and deployment", s, "04 Backend")


# =====================================================================
# 05  API AND DATA SOURCES
# =====================================================================
def doc05():
    rq = AS["route_request"]
    rs = AS["route_response"]
    short = {k: rs[k] for k in ("sun_strength", "heat_budget", "budget_met")}
    for side in ("baseline", "coolroute"):
        short[side] = {k: v for k, v in rs[side].items() if k != "nodes"}
    short["explanation"] = rs["explanation"]; short["warnings"] = rs["warnings"]
    s = [H1("1. Two kinds of API"),
         P("<b>Our API</b> is what the app calls. <b>Outside data sources</b> feed the real-city version. "
           "The prototype needs no outside API, which is why it cannot break during a demo."),
         H1("2. Our API (built and tested)"),
         table([["Method and path", "What it does", "Returns"],
                ["GET /api/v1/health", "Checks the server is up", "status, number of nodes and edges"],
                ["GET /api/v1/sun?hour=13", "Sun strength for an hour", "value from 0 to 1"],
                ["GET /api/v1/graph", "The street graph", "nodes and edges with attributes"],
                ["POST /api/v1/route", "Shortest route and CoolRoute", "both routes, explanation, warnings"]],
               [CW * .32, CW * .36, CW * .32]),
         H2("Request body for POST /api/v1/route"),
         table([["Field", "Type", "Default", "Meaning"],
                ["origin, destination", "{node} or {x, y}", "required", "Junction id, or metres on the local map (snapped to the nearest junction)"],
                ["hour", "number 0 to 24", "13", "Time of day"],
                ["heat_budget_pct", "number 10 to 100", "60", "Allowed heat as a percent of the shortest route's heat"],
                ["step_free", "true or false", "false", "Hard rule: use only step-free segments"],
                ["shade_available", "true or false", "true", "Set false to see the no-shade scenario"],
                ["closed_edge_ids", "list of ids", "[]", "Closed footpaths"]],
               [CW * .22, CW * .2, CW * .13, CW * .45]),
         H2("Real request"),
         code(json.dumps(rq, indent=1)),
         H2("Real response (route node lists left out for space)"),
         code(json.dumps(short, indent=1)),
         H2("Error responses (all tested)"),
         table([["Case", "HTTP", "Code", "Message"],
                ["Bad JSON, missing field, bad node, hour or budget", "400", "BAD_JSON / BAD_INPUT", "Says exactly what to fix"],
                ["No route with these closures or step-free rule", "404", "NO_ROUTE", "No route exists with the closed footpaths and step-free rule given."],
                ["Budget cannot be met", "200", "warning BUDGET_NOT_MET", "Returns the coolest route plus a warning"],
                ["Large detour", "200", "warning LARGE_DETOUR", "Cooler route is more than 20% longer"],
                ["Missing shade data on the route", "200", "warning MISSING_DATA", "Counts the weak segments"]],
               [CW * .38, CW * .08, CW * .22, CW * .32]),
         SP,
         P("A budget that cannot be met is a <b>200</b> and not an error, because the coolest route is still useful. A missing route is a <b>404</b> because there is nothing to show."),
         H1("3. Outside data sources for a real city"),
         table([["Need", "Source", "Key needed?", "Notes"],
                ["Walkable streets, crossings, kerbs, building outlines", "OpenStreetMap, via OSMnx or the Overpass API", "No", "Free and open. Respect the usage policy; for a whole city, download an extract instead of calling the live API"],
                ["Temperature and solar radiation", "Open-Meteo forecast API", "No key for non-commercial use", "Gives hourly temperature and radiation, so the sun factor can use real weather. Check terms before commercial use"],
                ["Tree cover (NDVI)", "Sentinel-2 imagery, or an open land-cover product", "Account may be needed", "Free imagery. Greenness is a good stand-in for tree shade"],
                ["Building heights", "OSM tags (height, building:levels), or a city dataset", "No", "Many buildings have no height. Missing values lower confidence"],
                ["Sun position", "pvlib or SunCalc library", "No", "Replaces our simple formula with exact azimuth and elevation"],
                ["Place search", "Nominatim (OSM)", "No", "Rate limited. For production use a paid or self-hosted geocoder"],
                ["Map tiles", "MapLibre GL JS with an OSM-based tile provider", "Depends on provider", "Read the provider's free-tier terms first"],
                ["Slope", "A free elevation dataset such as SRTM", "Account may be needed", "Turn elevation into slope per street piece"]],
               [CW * .25, CW * .25, CW * .17, CW * .33]),
         SP,
         callout("Limits and terms of free services change. Before launch, read each provider's current terms. For the hackathon, none of these is needed, because the prototype uses a built-in synthetic neighbourhood."),
         H1("4. How outside data becomes a graph (production)"),
         code("""
1. Download walk network for Jaipur with OSMnx           -> nodes, edges, length
2. Mark crossings and kerbs                              -> step_free, wait (default by road class)
3. Sample elevation at both ends of each edge            -> slope = rise / length x 100
4. For each hour: compute sun elevation and azimuth      -> pvlib
5. Building shadow per edge: L = H / tan(elevation)      -> shade_building (file 06)
6. Tree shade from NDVI around the edge                  -> shade_tree
7. ML model combines features                            -> shade, confidence
8. Save to PostGIS (edge_shade table)                    -> used by the router
""")]
    build(OUT + "05_API_and_Data_Sources.pdf", "API and Data Sources", "Our JSON API with real examples, and the outside data a real city needs", s, "05 API")


# =====================================================================
# 06  MATHS AND ML
# =====================================================================
def doc06():
    hours = [7, 9, 11, 13, 15, 17, 19]
    sun_rows = [["Hour"] + [f"{h}:00" for h in hours], ["sun(t)"] + [f"{sun_factor(h):.2f}" for h in hours]]
    pareto = S["pareto"]
    sel = [p for p in pareto if p[0] in (30, 40, 50, 60, 70, 80, 100)]
    ml_imp = sorted(ML["importance"].items(), key=lambda kv: -kv[1])
    s = [P("Every formula here is the one used in the code, with a worked example. Symbols are explained in plain words.", "body"),
         H1("1. Sun strength"),
         P("How strong is the sun at this hour? We use the angle of the sun above the horizon:"),
         code("sun(t) = max(0, sin(phi) x sin(delta) + cos(phi) x cos(delta) x cos(h))"),
         bullets(["<b>phi</b> = latitude (Jaipur 26.9 degrees)", "<b>delta</b> = sun's tilt for the date (about -10 degrees in mid-October)",
                  "<b>h</b> = hour angle = 15 degrees x (hour - 12), so it is 0 at noon", "Result is 0 at night and about 0.8 at midday, shown as a 0 to 1 strength"]),
         table(sun_rows, [CW * .16] + [CW * .84 / 7] * 7),
         SP, fig(F + "fig_sun.png", 150, "Figure 1. Left: sun strength through the day. Right: a building of height H casts a shadow of length L = H / tan(alpha)."),
         H1("2. Heat exposure of one street piece"),
         code("heat = length x (1 - shade) x sun(t)  +  wait x walking_speed x (1 - crossing_shade) x sun(t)"),
         P("Think of it as <b>metres walked in full sun</b>. A 100 m street with 80% shade at full sun is the same as 20 m in the sun. "
           "The second part counts the time you stand at a crossing: you stay where you are, so we count the distance you would have walked in that time (walking speed 1.3 m/s)."),
         H2("Worked example (at 1 pm, sun = 0.774)"),
         code("""
Street piece: length 82 m, shade 0.20, crossing wait 35 s, crossing shade 0.10
walking heat = 82 x (1 - 0.20) x 0.774          = 50.8
waiting heat = 35 x 1.3 x (1 - 0.10) x 0.774    = 31.7
heat of the piece                                = 82.5
"""),
         H1("3. Effort and time"),
         code("""
effort = length x (1 + 0.05 x slope%)        # a 6% slope makes 100 m feel like 130 m
time   = length / 1.3 + wait                 # seconds
"""),
         H1("4. The optimisation problem"),
         P("We want the shortest route that stays inside the heat budget:"),
         code("""
minimise   distance(route)
subject to heat(route) <= budget        budget = (budget% / 100) x heat(shortest route)
           every segment on the route is step-free   (if requested)
           no closed footpath on the route
"""),
         P("This is a <b>constrained shortest path</b>. Solving it exactly is hard (it is NP-hard in general), so we use a fast, well-known method called <b>Lagrangian relaxation</b>."),
         H2("Lagrangian relaxation in plain words"),
         P("Give heat a price, lambda. Each street piece then costs <b>distance + lambda x heat</b>. "
           "With lambda = 0, the cheapest route is the shortest one. As lambda grows, hot streets become expensive and the route moves to shade. "
           "We search for the smallest lambda whose route fits the budget."),
         code("cost(edge) = distance(edge) + lambda x heat(edge)"),
         P("<b>Why bisection works:</b> as lambda goes up, the heat of the best route never goes up, and its distance never goes down. "
           "So if one lambda is too hot we move up, and if it is cool enough we try lower. 40 steps pin lambda down very closely."),
         fig(F + "fig_lambda.png", 150, "Figure 2. As lambda rises, heat falls and distance grows, in steps. The search picks the smallest lambda whose heat is under the budget line (dotted vertical line)."),
         P("<b>Honest note:</b> this method finds a route on the efficient frontier, and it always fits the budget when one exists on that frontier. "
           "It may not be the single shortest route among all that fit, but it is close and very fast. An exact method (label-setting) is a planned upgrade."),
         H2("The trade-off curve"),
         fig(F + "fig_pareto.png", 125, "Figure 3. Tighter budgets cost more distance. This is the picture to show a judge."),
         table([["Budget", "Distance (m)", "Heat", "Budget met?"]] +
               [[f"{p[0]}%", f"{p[1]:.0f}", f"{p[2]:.0f}", "yes" if p[3] else "no, coolest route shown"] for p in sel],
               [CW * .2, CW * .25, CW * .2, CW * .35]),
         H1("5. Shade from geometry"),
         P("For a street with building height H, width W, at sun elevation alpha and sun direction gamma, with the street running along bearing theta:"),
         code("""
shadow length          L        = H / tan(alpha)
shadow across street   L_perp   = L x |sin(gamma - theta)|
building shade         s_b      = min(1, L_perp / W)
tree shade (from NDVI) s_t      = clip(1.4 x NDVI - 0.1, 0, 0.9)
combined shade         s        = 1 - (1 - s_b) x (1 - s_t)
"""),
         P("The last line says: a spot is sunny only if it is missed by <b>both</b> the building shadow and the tree shadow."),
         H1("6. Machine learning for shade and confidence"),
         P("Real cities have gaps: unknown building heights, old tree data. A model learns shade from features and also says how sure it is."),
         table([["Item", "Choice", "Why"],
                ["Inputs", "building height, street width, street bearing, tree greenness (NDVI), sun elevation, sun azimuth", "All can be taken from open data"],
                ["Model", "Gradient-boosted trees", "Works well on small tables, fast, no GPU needed"],
                ["Output", "Shade (middle estimate) and a range from the 10th to the 90th percentile", "The range becomes the confidence value"],
                ["Loss for the range", "Pinball (quantile) loss", "Teaches the model to give honest lower and upper bounds"]],
               [CW * .16, CW * .5, CW * .34]),
         SP,
         code("""
pinball loss (quantile q):   L_q = q x (y - y_hat)      if y >= y_hat
                                  (1 - q) x (y_hat - y) if y <  y_hat
MAE = average of |y - y_hat|        R2 = 1 - sum (y - y_hat)^2 / sum (y - mean(y))^2
confidence = 1 - (p90 - p10)        # narrow range -> high confidence
rule: confidence < 0.3  ->  draw the street dashed and warn the user
"""),
         fig(F + "fig_ml.png", 150, "Figure 4. Left: predicted versus actual shade on held-out data. Right: which inputs the model uses most."),
         table([["Measure (held-out data)", "Value"],
                ["Training samples", f"{ML['n']:,} (25% held out)"], ["R2", f"{ML['r2']:.2f}"], ["Mean absolute error", f"{ML['mae']:.3f} (on a 0 to 1 shade scale)"],
                ["Share of true values inside the 10-90 range", f"{100*ML['coverage80']:.0f}% (target 80%)"],
                ["Top inputs", ", ".join(f"{k} ({100*v:.0f}%)" for k, v in ml_imp[:3])]],
               [CW * .55, CW * .45]),
         SP,
         callout("<b>Be honest with judges:</b> this model was trained on synthetic data made from the shadow formula above, plus noise. "
                 "It shows that the pipeline and the confidence idea work. It does not show accuracy on real Jaipur streets. "
                 "Real accuracy needs real tree and shade data, which is the first item on the roadmap.", HEAT),
         H1("7. Complexity summary"),
         table([["Step", "Cost"], ["One shortest-path search", "O(E log V)"], ["Heat-budget search", "up to 41 searches"],
                ["Our prototype graph", "64 junctions, 112 street pieces: milliseconds"],
                ["Real city", "Add a bounding box around A and B, or contraction hierarchies"]],
               [CW * .45, CW * .55])]
    build(OUT + "06_Maths_and_ML.pdf", "Maths and ML", "Every formula with a worked example, simple charts and honest limits", s, "06 Maths")


# =====================================================================
# 07  TEST EVIDENCE
# =====================================================================
def doc07():
    s = [P("The hackathon asks us to <b>test failure cases</b> and <b>show evidence</b>. This file lists every check we ran and what we found, including results that are not flattering.", "body"),
         H1("1. Summary"),
         table([["Check", "Result"],
                ["Routing engine tests (Python)", f"{sum(t['pass'] for t in T)} of {len(T)} passed"],
                ["Backend API tests over HTTP", f"{sum(a['pass'] for a in A)} of {len(A)} passed"],
                ["JavaScript engine versus Python engine", "60 of 60 random scenarios gave identical routes and heat"],
                ["Large experiment", f"{MANY['trips']} random long trips at 1 pm with a 60% budget"]],
               [CW * .55, CW * .45]),
         H1("2. Engine tests (failure cases first)"),
         table([["#", "Test", "Result", "Detail"]] + [[str(i + 1), t["name"], "PASS" if t["pass"] else "FAIL", t["detail"]] for i, t in enumerate(T)],
               [CW * .05, CW * .5, CW * .1, CW * .35]),
         H1("3. Backend API tests"),
         table([["#", "Test", "Result"]] + [[str(i + 1), a["name"], "PASS" if a["pass"] else "FAIL"] for i, a in enumerate(A)],
               [CW * .06, CW * .74, CW * .2]),
         H1("4. Experiment: 148 random long trips"),
         P("We picked random start and end points at least 6 blocks apart, at 1 pm, with a 60% heat budget, and compared CoolRoute with the shortest route."),
         fig(F + "fig_hist.png", 140, "Figure 1. Left: how much heat CoolRoute removed on each trip. Right: how much extra distance it cost."),
         table([["Measure", "Value"],
                ["Median heat reduction", f"{MANY['median_cut']:.0f}%"], ["Mean heat reduction", f"{MANY['mean_cut']:.0f}%"],
                ["Median extra distance", f"{MANY['median_extra']:.1f}%"], ["90th percentile extra distance", f"{MANY['p90_extra']:.0f}%"],
                ["Trips where the 60% budget was met", f"{MANY['budget_met_pct']:.0f}%"],
                ["Trips needing more than 20% extra distance", f"{MANY['over20']:.0f}%"]],
               [CW * .6, CW * .4]),
         H2("What this tells us (the honest reading)"),
         bullets(["<b>Good:</b> the typical trip gets about 40% cooler for about 3% more distance. In this synthetic map the gain comes from its two shaded avenues.",
                  f"<b>Limit:</b> a 60% budget was met on only {MANY['budget_met_pct']:.0f}% of trips. On the rest, CoolRoute returns the coolest route it can find and the app says the budget was not met. This is the behaviour the problem statement asks for.",
                  f"<b>Cost:</b> {MANY['over20']:.0f}% of trips would need more than 20% extra distance. The app flags these as 'Large detour' so the user can choose.",
                  "<b>Why:</b> in our synthetic map only two avenues are well shaded. A real city with more tree cover would meet budgets more often. We have not tested on a real city yet."]),
         H1("5. Heat saved through the day"),
         fig(F + "fig_day.png", 130, "Figure 2. The gap between the lines is the heat CoolRoute saves. It is largest around midday and zero at night."),
         H1("6. Known limits"),
         bullets(["Synthetic neighbourhood and synthetic shade values. Real data will change the numbers.",
                  "The heat score does not include air temperature, humidity or wind. Open-Meteo data can be added.",
                  "Lagrangian search finds a route on the efficient frontier, not always the exact optimum.",
                  "No user testing yet with real pedestrians.",
                  "Shade is fixed per street for an hour. Real shade moves minute by minute."]),
         H1("7. How to repeat these results"),
         code("""
python3 test_core.py        # 13 engine tests
python3 make_cases.py && node verify.js     # JS vs Python on 60 scenarios
python3 test_api.py         # 12 API tests (start the server first)
python3 make_figs.py        # experiment and charts
""")]
    build(OUT + "07_Test_Evidence.pdf", "Test Evidence", "Failure-case tests, experiments, and what the results really say", s, "07 Evidence")


# =====================================================================
# 08  REVENUE
# =====================================================================
def doc08():
    tot = REV["total"]
    s = [callout("All money figures below are <b>planning assumptions</b> for discussion. They are not forecasts and have not been tested with customers. "
                 "Where we say 'to validate', the next step is to ask real buyers.", HEAT),
         H1("1. Who needs this"),
         table([["Customer", "Pain", "What they get"],
                ["City and smart-city offices", "Cannot see which streets are heat traps; need to decide where to plant trees and add shelters", "A heat map of walking routes and a tool to test shade plans"],
                ["Citizens (older people, parents, daily walkers)", "Hot, tiring walks; steps and long waits at crossings", "Free cooler routes, step-free option"],
                ["Delivery, ride and tourism apps", "Walking legs are unpleasant in summer; lost orders and bad reviews", "A route API that adds a cool-walk option"],
                ["Universities, campuses, hospitals, malls", "Safe and comfortable walking between buildings", "Campus routing and shade audit"]],
               [CW * .26, CW * .4, CW * .34]),
         H1("2. How it earns money"),
         table([["Stream", "Who pays", "Price assumption", "To validate"],
                ["City licence", "City or ward office", "Rs 6 lakh per city per year in year 1, rising to Rs 10 lakh with more features", "Ask two smart-city offices what they pay for similar tools"],
                ["Route API", "Delivery, tourism and mobility apps", "Rs 0.15 per route call", "Compare with map-API pricing and test willingness to pay"],
                ["Premium app", "Citizens", "Rs 399 per year (about Rs 33 a month) for saved places, alerts, audio guidance", "Run a survey and a small pilot"],
                ["Free tier", "Nobody", "Basic cool route for everyone", "Builds trust and data; keeps the public-good mission"]],
               [CW * .15, CW * .2, CW * .38, CW * .27]),
         H1("3. Three-year plan (illustrative)"),
         fig(F + "fig_rev.png", 125, "Figure 1. Revenue by stream under the assumptions in the table below."),
         table([["Assumption", "Year 1", "Year 2", "Year 3"],
                ["Cities paying", "1 at Rs 6 lakh", "3 at Rs 8 lakh", "8 at Rs 10 lakh"],
                ["API calls per year", "0.5 million", "3 million", "12 million"],
                ["Premium subscribers", "500", "4,000", "20,000"],
                ["<b>Revenue (Rs lakh)</b>", f"<b>{tot[0]:.1f}</b>", f"<b>{tot[1]:.1f}</b>", f"<b>{tot[2]:.1f}</b>"]],
               [CW * .34, CW * .22, CW * .22, CW * .22]),
         H1("4. Costs stay low"),
         bullets(["Open data (OpenStreetMap, open weather, free satellite imagery) and open-source tools keep data costs near zero at the start.",
                  "The engine is light. One small server can handle a city-size graph with caching.",
                  "Main costs later: a part-time data engineer, hosting, support for city pilots, and survey and field validation.",
                  "Cost per route call is tiny compared with the assumed price, so the API has room for a healthy margin once volume grows (to validate with real hosting bills)."]),
         H1("5. Go-to-market"),
         table([["Phase", "Action", "Proof we want"],
                ["0 to 3 months", "Pilot on the Manipal University Jaipur campus and one nearby ward; walk the routes and compare with the model", "Students and staff prefer the cool route; model matches what people feel"],
                ["3 to 9 months", "Offer a free pilot to a city office with a shade-planning report", "One signed paid licence"],
                ["9 to 18 months", "Open the route API to two partner apps", "API calls growing every month"],
                ["18 months on", "Premium app and more cities", "Subscribers and repeat renewals"]],
               [CW * .17, CW * .5, CW * .33]),
         H1("6. How we compare"),
         table([["", "Normal map apps", "CoolRoute"],
                ["Optimises", "Distance and time", "Distance, time, shade, heat budget, effort"],
                ["Time-of-day heat", "No", "Yes, through the sun model"],
                ["Step-free as a hard rule", "Sometimes as a filter", "Yes, always a hard rule"],
                ["Says when data is weak", "Rarely", "Yes, with warnings"],
                ["Explains the trade-off", "No", "Yes, one plain sentence"]],
               [CW * .28, CW * .32, CW * .4]),
         H1("7. Impact we can measure"),
         bullets(["Heat exposure avoided per trip (sun-metres), shown in the app.", "Share of walking done in shade.",
                  "Number of step-free routes found that other tools miss.", "For cities: the list of streets that cause most heat exposure, which is where trees and shelters help most."]),
         H1("8. Risks and answers"),
         table([["Risk", "Answer"],
                ["Shade data is wrong in the real city", "Confidence values, dashed streets and warnings; field checks in the pilot"],
                ["People read the score as a medical warning", "Wording and a note on every result: a comparison score, not a health risk"],
                ["Free data or API terms change", "Self-host OpenStreetMap extracts; keep the engine independent of any one provider"],
                ["Big map companies copy the idea", "Move first with city partnerships and local data; open, explainable method"],
                ["Cities buy slowly", "Start with campuses and the free tier; use pilots as proof"]],
               [CW * .4, CW * .6])]
    build(OUT + "08_Revenue_and_Business_Model.pdf", "Revenue and Business Model", "Customers, pricing, a three-year plan and the risks", s, "08 Business")


# =====================================================================
# 09  PITCH SCRIPT AND QA
# =====================================================================
def doc09():
    qa = [("Why not just use Google Maps?", "Map apps optimise distance and time. They do not count shade or time-of-day heat, and they do not let you set a heat budget. We add that, and we explain the trade-off in one sentence."),
          ("How do you measure heat?", "Heat exposure is metres walked in full sun: length x (1 - shade) x sun strength, plus waiting at crossings. It is a relative score for comparing routes."),
          ("Is the data real?", "The prototype uses a synthetic neighbourhood so the demo is reliable and we can test failure cases. The real-city pipeline uses OpenStreetMap, satellite tree cover and building heights, described in file 05."),
          ("Is the ML real?", "Yes, it runs and is tested, but it is trained on synthetic data built from the shadow formula. It shows the pipeline and the confidence range. Real accuracy needs real data, and we say so."),
          ("How do you solve the heat budget?", "We give heat a price lambda and minimise distance + lambda x heat. We search lambda by bisection until the route fits the budget. It is fast and explainable."),
          ("Is that optimal?", "It finds a route on the efficient frontier and always fits the budget when such a route exists there. It may miss the exact optimum between frontier points. Label-setting is our planned exact upgrade."),
          ("What if the budget cannot be met?", "We return the coolest route and show a warning. On our 148-trip test, a 60% budget was met on about half of trips, and the app tells the user when it is not."),
          ("What about accessibility?", "Step-free is a hard rule. Those segments are removed before the search, so no route ever uses them. If no step-free route exists, we say so."),
          ("What if data is missing?", "Each street piece has a confidence value. Low confidence is drawn dashed, counted in the warnings, and the heat value is called approximate."),
          ("Do you give health advice?", "No. The score compares routes. We say on every result that it is not a medical risk."),
          ("What if the cooler route is very long?", "A warning appears when it adds more than 20% distance, and the user can raise the heat budget."),
          ("How fast is it?", "Milliseconds on our map. For a real city we limit the search area around A and B and use caching or contraction hierarchies."),
          ("How did you test it?", "13 engine tests, 12 backend tests, a check that JavaScript and Python give identical results on 60 scenarios, and a 148-trip experiment. All in file 07."),
          ("How will you make money?", "City licences, a route API for apps and a premium citizen app. Figures are assumptions to validate (file 08)."),
          ("What would you do with more time?", "Load Jaipur from OpenStreetMap, train the shade model on real tree and building data, walk the routes to validate, and add live weather from Open-Meteo.")]
    s = [H1("1. Five-minute pitch script"),
         table([["Time", "Say", "Show"],
                ["0:00 to 0:40", "<b>Problem.</b> 'The shortest walk is often the hottest. In summer, a few minutes in the sun or standing at an open crossing makes a big difference, and for people who cannot use steps the choice is even smaller. Map apps count distance, not heat.'", "Slide: one hot, bare street"],
                ["0:40 to 1:20", "<b>Idea.</b> 'CoolRoute gives two routes: the shortest, and the shortest that fits your heat budget. Then it tells you, in one sentence, what the cooler route costs and gives.'", "Prototype: both routes at 1 pm"],
                ["1:20 to 2:30", "<b>Live demo.</b> Follow the demo steps in section 2.", "Prototype"],
                ["2:30 to 3:30", "<b>How it works.</b> 'Streets are a graph. Heat is length x (1 - shade) x sun. We give heat a price, lambda, and search for the lambda that fits the budget. Step-free is never traded away.'", "File 06: formula and trade-off curve"],
                ["3:30 to 4:15", "<b>Proof.</b> '25 automated checks. JavaScript and Python agree on 60 scenarios. On 148 random trips, the typical route is about 40% cooler for about 3% more distance. And we show you where it fails: a 60% budget is met on about half of trips.'", "File 07: histogram and test table"],
                ["4:15 to 5:00", "<b>Future.</b> 'Next: real Jaipur data, shade model on real trees and buildings, a pilot on campus, city licences and a route API.'", "File 08: revenue chart"]],
               [CW * .13, CW * .6, CW * .27]),
         H1("2. Live demo: click by click (about 70 seconds)"),
         table([["#", "Do", "Say"],
                ["1", "Open the prototype on the 'Hot afternoon' preset (1 pm, 60% budget)", "'Orange is the shortest route. Teal is CoolRoute.'"],
                ["2", "Point to the verdict sentence", "'23 metres longer, about 40% less heat. It keeps to the green, tree-lined avenue.'"],
                ["3", "Drag the time slider to evening", "'As the sun weakens, the heat gap shrinks. At night both routes are the same.'"],
                ["4", "Go back to 1 pm. Slide the budget down to 30%", "'A stricter budget costs more distance. When it cannot be met, we say so, and show the coolest route.'"],
                ["5", "Turn on Step-free", "'Step-free is a hard rule. Routes use only step-free segments, even if hotter.'"],
                ["6", "Choose 'Close footpath' and tap a street on the route", "'A closed footpath is avoided straight away.'"],
                ["7", "Point to the dashed streets and the warning list", "'Dashed means missing shade data. We show the gap and call the result approximate.'"]],
               [CW * .05, CW * .45, CW * .5]),
         H1("3. Likely judge questions and answers")] + \
        [KeepTogether([P(f"<b>Q{i+1}. {q}</b>", "body"), P(a, "body")]) for i, (q, a) in enumerate(qa)] + \
        [H1("4. Do and do not"),
         table([["Do", "Do not"],
                ["Say clearly that the data is synthetic and the ML demo is trained on synthetic data", "Claim real-world accuracy"],
                ["Show a failure case (budget not met, large detour) before a judge asks", "Hide the cases where the cooler route is too long"],
                ["Use the words 'comparison score'", "Say 'health risk' or 'heat stroke risk'"],
                ["Keep the browser prototype open as the backup", "Depend on live internet or a sleeping free server"],
                ["Tell the trade-off in one sentence", "Read formulas aloud; show the chart instead"]],
               [CW * .5, CW * .5]),
         H1("5. Checklist before you present"),
         bullets(["Open the prototype and test the sliders on the presentation laptop.", "Keep a screenshot of the main view as a backup.",
                  "Print or open files 06 and 07 to answer technical questions.", "Practise the script with a timer. Aim for 4:30 so you have a buffer.",
                  "Agree who speaks about product, who about technology, who about business."])]
    build(OUT + "09_Pitch_Script_and_QA.pdf", "Pitch Script and Q&A", "A five-minute script, a demo plan and answers to likely judge questions", s, "09 Pitch")


# =====================================================================
# 10  ROADMAP
# =====================================================================
def doc10():
    s = [H1("1. What is already done"),
         table([["Item", "Status"],
                ["Routing engine (shortest and heat-budget)", "Done and tested"], ["Browser prototype with all scenario controls", "Done"],
                ["JSON backend with errors and warnings", "Done and tested"], ["Charts, formulas, ML demo", "Done"], ["Ten PDFs", "Done"]],
               [CW * .7, CW * .3]),
         H1("2. Plan for the remaining hackathon hours"),
         table([["When", "Task", "Owner", "Output"],
                ["Hours 0 to 4", "Run the prototype, read files 01, 06, 07. Agree the story and who speaks", "Whole team", "Shared understanding"],
                ["Hours 4 to 10", "Rehearse the demo and the 5-minute script; fix any wording", "Presenter", "Smooth demo"],
                ["Hours 10 to 18", "Optional upgrade: load a real few-block area of Jaipur with OSMnx and show it as a second map", "Developer", "Real-data screenshot"],
                ["Hours 18 to 24", "Optional upgrade: fetch live temperature from Open-Meteo and scale the sun factor", "Developer", "Weather-aware heat"],
                ["Hours 24 to 30", "Practise Q&A with the file 09 questions; time the pitch", "Whole team", "Confident answers"],
                ["Hours 30 to 36", "Freeze the build. Backup screenshots. Print files. Sleep", "Whole team", "Ready to present"]],
               [CW * .15, CW * .45, CW * .15, CW * .25]),
         H1("3. Roadmap after the hackathon"),
         table([["Step", "What", "Success looks like"],
                ["1", "Real Jaipur street graph from OpenStreetMap", "Routes on real streets"],
                ["2", "Tree and building shade from open data, trained shade model", "Shade error measured against field checks"],
                ["3", "Live weather and sun position (pvlib)", "Heat score follows the actual day"],
                ["4", "Walk test with students on campus", "People prefer CoolRoute; model matches how it felt"],
                ["5", "Exact budget method and contraction hierarchies", "Optimal routes, fast on a whole city"],
                ["6", "Audio and large-text accessibility", "Usable by people with low vision"],
                ["7", "Pilot with a city office", "A paid licence"]],
               [CW * .08, CW * .52, CW * .4]),
         H1("4. Files in the project folder"),
         code("""
coolroute.html        interactive prototype (open in any browser)
core.py / core.js     routing engine in Python and JavaScript (same maths)
api_server.py         JSON backend
test_core.py          13 engine tests
test_api.py           12 backend tests
verify.js             JavaScript versus Python check
make_figs.py          charts and experiments
pdfs/                 these ten PDF files
"""),
         H1("5. Setup in one minute"),
         bullets(["<b>Prototype:</b> open <font face='DVM'>coolroute.html</font>.", "<b>Engine tests:</b> <font face='DVM'>python3 test_core.py</font>.",
                  "<b>Backend:</b> <font face='DVM'>python3 -m uvicorn api_server:app --port 8765</font>, then call /api/v1/health.",
                  "Python needs numpy, matplotlib, scikit-learn and reportlab only for the charts and PDFs, not for the engine or backend."]),
         H1("6. Risks for the next hours"),
         table([["Risk", "Plan"],
                ["Venue internet is slow", "The prototype runs with no internet. Fonts fall back to system fonts"],
                ["A judge asks for real-city results", "Say plainly the prototype is synthetic; show the real-data plan; if time allows, add the OSMnx map"],
                ["Demo laptop fails", "Open the prototype link on a phone; keep screenshots"],
                ["Time runs short in the pitch", "Skip the maths slide; keep demo, proof and one-line business model"]],
               [CW * .35, CW * .65])]
    build(OUT + "10_Roadmap_and_Team_Plan.pdf", "Roadmap and Team Plan", "What is done, the plan for the remaining hours, and what comes next", s, "10 Roadmap")


for f in (doc01, doc02, doc03, doc04, doc05, doc06, doc07, doc08, doc09, doc10):
    f()
    print("built", f.__name__)
