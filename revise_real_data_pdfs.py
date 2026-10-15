"""Regenerate the CoolRoute real-data handoff PDFs."""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
                                Preformatted, ListFlowable, ListItem)

W, H = A4
M = 18 * mm
COOL = colors.HexColor("#0b7f86")
INK = colors.HexColor("#12262e")
MUTED = colors.HexColor("#546a73")
SOFT = colors.HexColor("#e8f1f3")
LINE = colors.HexColor("#c9d8dd")
ST = {
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9.4, leading=13.5, textColor=INK, spaceAfter=5),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=8, leading=11, textColor=MUTED),
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=COOL, spaceBefore=10, spaceAfter=5),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8.1, leading=10.6, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=8.1, leading=10.6, textColor=colors.white),
    "code": ParagraphStyle("code", fontName="Courier", fontSize=7.2, leading=9.5, textColor=INK),
    "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=9.1, leading=13, textColor=INK),
    "call": ParagraphStyle("call", fontName="Helvetica", fontSize=9, leading=12.5, textColor=INK),
}

def P(text, style="body"):
    return Paragraph(text, ST[style])

def H1(text):
    return P(text, "h1")

def bullets(items):
    return ListFlowable([ListItem(Paragraph(item, ST["bullet"]), leftIndent=12, bulletColor=COOL) for item in items],
                        bulletType="bullet", leftIndent=12, bulletFontSize=8)

def table(rows, widths):
    data = [[Paragraph(str(c), ST["cellb"] if ri == 0 else ST["cell"]) for c in row] for ri, row in enumerate(rows)]
    out = Table(data, colWidths=widths, repeatRows=1)
    style = [("VALIGN", (0,0),(-1,-1),"TOP"),("LINEBELOW",(0,0),(-1,-1),.4,LINE),
             ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
             ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
             ("BACKGROUND",(0,0),(-1,0),COOL)]
    for i in range(2,len(rows),2): style.append(("BACKGROUND",(0,i),(-1,i),SOFT))
    out.setStyle(TableStyle(style))
    return out

def callout(text):
    out=Table([[Paragraph(text,ST["call"])]],colWidths=[W-2*M])
    out.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),SOFT),("LINEBEFORE",(0,0),(0,-1),3,COOL),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
    return out

def code(text):
    out=Table([[Preformatted(text.strip("\n"),ST["code"])]],colWidths=[W-2*M])
    out.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#f1f5f6")),
        ("BOX",(0,0),(-1,-1),.4,LINE),("LEFTPADDING",(0,0),(-1,-1),8),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]))
    return out

def build(filename,title,subtitle,story,tag):
    def footer(c,d):
        c.saveState(); c.setFont("Helvetica",7.5); c.setFillColor(MUTED)
        c.drawString(M,10*mm,"CoolRoute  |  Real-data local demo")
        c.drawRightString(W-M,10*mm,f"{tag}  |  Page {d.page}")
        c.setStrokeColor(LINE); c.line(M,14*mm,W-M,14*mm); c.restoreState()
    def first(c,d):
        c.saveState(); c.setFillColor(INK); c.rect(0,H-48*mm,W,48*mm,stroke=0,fill=1)
        c.setFillColor(COOL); c.rect(0,H-48*mm,8*mm,48*mm,stroke=0,fill=1)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold",20); c.drawString(M+4*mm,H-26*mm,title)
        c.setFont("Helvetica",10); c.setFillColor(colors.HexColor("#b9d4da")); c.drawString(M+4*mm,H-35*mm,subtitle)
        c.restoreState(); footer(c,d)
    doc=BaseDocTemplate(filename,pagesize=A4,leftMargin=M,rightMargin=M,topMargin=M,bottomMargin=20*mm,
                        title=f"CoolRoute: {title}",author="CoolRoute")
    first_frame=Frame(M,20*mm,W-2*M,H-20*mm-56*mm,id="f1",leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
    later_frame=Frame(M,20*mm,W-2*M,H-20*mm-M,id="f2",leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="first",frames=[first_frame],onPage=first,autoNextPageTemplate="later"),
                          PageTemplate(id="later",frames=[later_frame],onPage=footer)])
    doc.build(story)

OUT = ""
CW = W - 2 * M
LINK = "<font color='#0b7f86'><link href='{url}'>{label}</link></font>"


def doc04():
    story = [callout("<b>Current build:</b> the browser now uses a local Starlette backend. The backend fetches bounded OpenStreetMap data and hourly weather, builds a pedestrian graph, and computes both routes locally. Shade is a documented proxy from nearby mapped trees and buildings."),
        H1("1. Request flow"),
        code("""
Browser (Leaflet map + route controls)
  -> GET /api/v1/real/area?bbox=...
     -> Overpass API -> OSM walking streets, trees and building footprints
     -> local graph + 15 minute in-memory area cache
  -> GET /api/v1/real/weather?lat=...&lon=...&hour=...
     -> Open-Meteo hourly forecast
  -> POST /api/v1/real/route
     -> snap map clicks to nearest graph nodes
     -> shortest distance + heat-budget route (local Dijkstra search)
     -> JSON metrics, route geometry, confidence and caveats
"""),
        H1("2. Implemented services"),
        table([["Layer", "What it does now", "Files"],
               ["Web UI", "Leaflet map, route controls, time/budget sliders, street closure mode, responsive light/dark styling", "index.html, styles.css, frontend.js"],
               ["HTTP API", "Serves the app and exposes real and retained synthetic routes", "api_server.py"],
               ["Street data", "Bounded Overpass query for walkable ways, mapped trees and buildings; cached for 15 minutes", "real_data.py"],
               ["Weather", "Open-Meteo hourly temperature, humidity, cloud and shortwave radiation", "real_data.py"],
               ["Routing", "Dijkstra baseline and heat-budget search, with step-free as a hard filter", "core.py"]], [CW*.17,CW*.59,CW*.24]),
        H1("3. Edge data and scoring"),
        table([["Field", "Meaning in this version"],
               ["length", "Street-segment length in metres from lat/lon geometry"],
               ["shade", "Proxy: nearby mapped tree and/or nearby building footprint; not a measured shadow"],
               ["confidence", "Higher where mapped trees/buildings support the estimate; still requires field validation"],
               ["step_free", "Excludes mapped steps and wheelchair=no ways; missing tags remain uncertain"],
               ["closed", "User-selected segments omitted from the route graph"],
               ["heat", "length x (1 - shade) x normalized shortwave radiation; relative route comparison only"]], [CW*.23,CW*.77]),
        H1("4. Run locally"),
        code("""
py -3 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn api_server:app --host 127.0.0.1 --port 8765
Open http://127.0.0.1:8765
""")]
    build("04_Backend_and_Architecture.pdf", "Backend and Architecture", "Real street data, weather inputs, local routing, and honest shade estimates", story, "04 Architecture")


def doc05():
    story = [callout("<b>No API keys in this build.</b> These public services are appropriate for a low-volume, non-commercial demo when their current policies are followed. They are best-effort services, not production SLAs."),
        H1("1. External services"),
        table([["Service", "Use", "Policy / operating note"],
               ["OpenStreetMap tiles", "Map display in Leaflet", "Visible attribution is on the map. Standard tile servers have no SLA; obey caching and no-prefetch rules."],
               ["Overpass API", "Nearby walkable street geometry, trees and building footprints", "Small bounding box only; requests cached 15 minutes. Shared public instances can be busy or rate-limited."],
               ["Open-Meteo", "Hourly temperature, humidity, clouds and shortwave radiation", "Free API is limited and non-commercial; CC BY 4.0 attribution applies."],
               ["Local routing", "Shortest and heat-aware walk on downloaded OSM street graph", "No paid route provider and no external routing quota; quality depends on OSM pedestrian tags."]], [CW*.19,CW*.34,CW*.47]),
        H1("2. Shade estimate and limits"),
        P("Open street data does not give a dependable, time-specific shade percentage for every footpath. This implementation checks for mapped trees near a segment and nearby building footprints, then assigns a clearly labeled proxy value. It does not calculate the direction and length of each building shadow, tree canopy size, seasonal foliage, or the user's side of the street. Treat the result as a route-comparison hint and validate it on foot before relying on it."),
        H1("3. CoolRoute API"),
        table([["Endpoint", "Request / response"],
               ["GET /api/v1/health", "Local service status and data mode"],
               ["GET /api/v1/real/area?bbox=s,w,n,e", "Street graph, street geometry, mapped trees, source and attribution. Window capped to a few kilometres."],
               ["GET /api/v1/real/weather?lat=...&lon=...&hour=...", "Hourly forecast values and source/licence metadata."],
               ["POST /api/v1/real/route", "origin/destination lat/lon, bbox, hour, heat_budget_pct, step_free, shade_available, closed_edge_ids; returns both routes, metrics, weather and warnings."],
               ["GET /api/v1/graph, /sun; POST /api/v1/route", "Retained synthetic demo endpoints for reproducible offline engine examples."]], [CW*.31,CW*.69]),
        H1("4. Important public-service policies"),
        bullets([
            LINK.format(url="https://operations.osmfoundation.org/policies/tiles/", label="OSMF tile policy") + ": visible attribution; respect cache headers; no bulk tile download or prefetch.",
            LINK.format(url="https://operations.osmfoundation.org/policies/nominatim/", label="Nominatim policy") + ": public Nominatim is deliberately not included as a generic search box; use map clicks or browser location in this demo.",
            LINK.format(url="https://open-meteo.com/en/terms", label="Open-Meteo terms") + ": free API is non-commercial, rate-limited and licensed with CC BY 4.0; commercial integrations need an appropriate subscription.",
            LINK.format(url="https://dev.overpass-api.de/overpass-doc/en/preface/commons.html", label="Overpass commons guidance") + ": shared public endpoints have capacity limits; keep queries small and cache results.",
            LINK.format(url="https://www.openstreetmap.org/copyright", label="OSM copyright and licence") + ": retain clear OpenStreetMap contributor attribution."])]
    build("05_API_and_Data_Sources.pdf", "API and Data Sources", "Free open-data integrations, endpoint contracts, usage limits and shade caveats", story, "05 Data")


def doc10():
    story = [H1("1. What is implemented now"),
        table([["Capability", "Status"],
               ["Real map and street geometry", "OpenStreetMap tiles and bounded Overpass street graph"],
               ["Live hourly weather", "Open-Meteo temperature, humidity, cloud cover and shortwave radiation"],
               ["Route comparison", "Local shortest and heat-budget routing on mapped street segments"],
               ["Shade estimate", "Nearby mapped tree/building proxy, visibly labeled as approximate"],
               ["Local run and handoff", "README, Windows start script, requirements, .gitignore and IBM BOB brief"]], [CW*.31,CW*.69]),
        H1("2. Recommended build sequence"),
        table([["Phase", "Work", "Done when"],
               ["1. Local demo", "Run from the Project folder; plan a route in Jaipur and a second area; confirm the browser map attribution and live-service errors are clear.", "A new developer can launch it using README steps."],
               ["2. Routing quality", "Validate OSM footway topology, one-way/steps/accessibility tags, snapped points and closed-edge behavior on field-selected trips.", "Observed trips follow walkable paths and bad tag coverage is surfaced."],
               ["3. Shade quality", "Collect shade observations by street side and time; add canopy width, building height and solar position where licensed data permits.", "Estimate error is measured against field observations."],
               ["4. Resilience", "Add explicit request timeouts, provider status, persistent cache, retry/backoff and configurable provider URLs.", "Provider outage leaves useful errors and does not hang the UI."],
               ["5. Publish", "Select commercial-capable tile, weather and data hosting terms; add privacy notice and deploy backend plus static UI.", "Usage complies with each provider's terms and has operational monitoring."]], [CW*.16,CW*.52,CW*.32]),
        H1("3. GitHub and IBM BOB handoff"),
        bullets(["Open this Project folder as the repository root in IBM BOB.", "Use BOB_IMPLEMENTATION_BRIEF.md as the short continuation prompt; README.md is the source of truth for setup.", "Commit the source files and PDFs. Do not commit .venv, generated caches or secrets.", "The public free services are not commercial production guarantees. Choose licensed or self-hosted providers before monetizing the app.", "Use the new implementation plan PDF to review the architecture and acceptance criteria."]),
        H1("4. Known limitations"),
        bullets(["Shade is inferred from mapped nearby features and has not been calibrated against measured street shadows.", "Step-free routing filters OSM tags but cannot prove curb cuts or accessibility conditions that were never mapped.", "A small-area graph and nearest-node snapping are suitable for a local demo, not a complete city routing service.", "Weather radiation and a relative heat score do not represent personal health risk or individual heat exposure."])]
    build("10_Roadmap_and_Team_Plan.pdf", "Roadmap and Team Plan", "Current real-data build, practical milestones, and the IBM BOB/GitHub handoff", story, "10 Roadmap")


def doc11():
    story = [callout("<b>Implementation target:</b> a professional local-first app that uses real open street/weather data, provides both the shortest and cooler route, and reports where its shade information is weak."),
        H1("1. Product acceptance checklist"),
        bullets(["Map view uses real OpenStreetMap map tiles with visible contributor credit.", "Users can set start and destination by map click or browser location; map clicks snap to the nearest street node.", "The UI shows distance, estimated walk time, shade share, heat comparison, budget status, and data warnings for both routes.", "Time, heat budget, step-free, shade use, street closure, swap, reset, recenter and theme controls work.", "Mobile and desktop layouts retain legible type, keyboard focus, large controls and consistent action colors.", "Every estimate is labeled accurately; estimated shade is not presented as measured shade, and heat is not presented as medical guidance."]),
        H1("2. Data-to-route design"),
        table([["Stage", "Implementation"],
               ["Load", "Overpass returns a bounded set of walkable OSM ways, trees and building footprints."],
               ["Prepare", "Split ways into graph edges, measure segment lengths and infer a low-confidence shade proxy from nearby mapped objects."],
               ["Weather", "Request the selected hour from Open-Meteo and use shortwave radiation to scale the relative sun component."],
               ["Route", "Run shortest-path and heat-budget searches locally; apply closures and step-free filters before search."],
               ["Explain", "Return route coordinates, distance, walk time, shaded share, confidence, warnings and provider metadata."],
               ["Render", "Draw the routes on a Leaflet map and show plain-language trade-offs with the limits beside the result."]], [CW*.18,CW*.82]),
        H1("3. API and operational rules"),
        bullets(["No key is embedded in the browser; the local backend calls external services.", "Keep the map window small, cache street responses, use request timeouts, and show useful errors when a provider is down.", "Follow OSM tile caching and attribution rules; do not bulk download or prefetch tiles.", "Use Open-Meteo's free API only for non-commercial use; buy a suitable plan or replace the provider before commercial use.", "Public Overpass and tile servers have no uptime commitment. Production requires a service plan or self-hosting.", "Avoid public Nominatim generic geocoding in this vibe-coded app. Map click and browser location avoid that dependency."]),
        H1("4. Local setup for IBM BOB"),
        code("""
Open Project/ as the workspace root
py -3 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn api_server:app --host 127.0.0.1 --port 8765
Browse to http://127.0.0.1:8765
"""),
        H1("5. Future accuracy work"),
        table([["Priority", "Upgrade", "Evidence needed"],
               ["1", "Validate OSM graph connectivity and tag handling in a few real neighborhoods.", "Route walk-through notes and snapped-point error."],
               ["2", "Replace tree/building proximity with solar geometry, canopy/building height and dated imagery where licensed.", "Shade percent observations by time and street side."],
               ["3", "Add persistent cache, retries, circuit-breaker status and configurable providers.", "Outage and rate-limit behavior."],
               ["4", "Select commercial data, map and weather providers or self-host the needed services.", "Provider terms, costs and usage forecasts."],
               ["5", "Add accessibility field checks and a privacy review before deployment.", "Curb and crossing audit plus data-flow review."]], [CW*.1,CW*.52,CW*.38])]
    build("11_Real_Data_Implementation_Plan.pdf", "Real Data Implementation Plan", "IBM BOB build brief for a real-data, local-run CoolRoute app", story, "11 Build Plan")


for build_doc in (doc04, doc05, doc10, doc11):
    build_doc()
    print("built", build_doc.__name__)
