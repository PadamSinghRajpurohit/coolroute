import json, math, random, copy
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from core import build_neighbourhood, plan, sun_factor, make_adj, dijkstra, summarise

COOL, HEAT, TREE, INK, MUTED, SOFT = "#0b7f86", "#d4501a", "#3f9a52", "#12262e", "#546a73", "#e3edf0"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 200, "font.size": 10})
g = build_neighbourhood()
stats = {}
OUT = "figs/"
import os
os.makedirs(OUT, exist_ok=True)
SRC, DST, HOUR = 0, 63, 13.0


def save(name):
    plt.tight_layout()
    plt.savefig(OUT + name, bbox_inches="tight", facecolor="white")
    plt.close()


# ---------- 1. route map
r = plan(g, SRC, DST, HOUR, 60)
fig, ax = plt.subplots(figsize=(6.2, 6.2))
for e in g["edges"]:
    a, b = g["nodes"][e["a"]], g["nodes"][e["b"]]
    if e["shade"] >= 0.5:
        ax.plot([a["x"], b["x"]], [a["y"], b["y"]], color=TREE, lw=5, alpha=0.5, solid_capstyle="round")
    else:
        ax.plot([a["x"], b["x"]], [a["y"], b["y"]], color="#b9a58a", lw=2, alpha=0.9, solid_capstyle="round")
    if e["confidence"] < 0.3:
        ax.plot([a["x"], b["x"]], [a["y"], b["y"]], color="white", lw=1.4, ls=(0, (3, 3)))
    if e["wait"] > 0:
        ax.plot((a["x"] + b["x"]) / 2, (a["y"] + b["y"]) / 2, "s", color="white", mec=MUTED, ms=5, mew=1)
def path_xy(nodes):
    return [g["nodes"][n]["x"] for n in nodes], [g["nodes"][n]["y"] for n in nodes]
ax.plot(*path_xy(r["baseline"]["nodes"]), color=HEAT, lw=9, alpha=0.4, solid_capstyle="round", label="Shortest route")
ax.plot(*path_xy(r["cool"]["nodes"]), color=COOL, lw=3.5, solid_capstyle="round", label="CoolRoute")
for n, t, c in ((SRC, "A", INK), (DST, "B", COOL)):
    nd = g["nodes"][n]
    ax.scatter([nd["x"]], [nd["y"]], s=260, color=c, zorder=5)
    ax.text(nd["x"], nd["y"], t, color="white", ha="center", va="center", fontweight="bold", zorder=6)
ax.invert_yaxis(); ax.set_aspect("equal"); ax.axis("off")
ax.legend(loc="lower left", frameon=True, fontsize=8)
ax.set_title("Synthetic neighbourhood at 1 pm: two route choices", fontsize=10, color=INK)
save("fig_routes.png")
B, C = r["baseline"]["m"], r["cool"]["m"]
stats["demo"] = {"base_dist": B["dist"], "cool_dist": C["dist"], "base_heat": B["heat"], "cool_heat": C["heat"],
                 "base_time": B["time"], "cool_time": C["time"], "base_shade": B["shaded_share"] if "shaded_share" in B else None}

# shaded share
def shaded_share(edges):
    L = sum(g["edges"][k]["length"] for k in edges)
    return sum(g["edges"][k]["length"] * g["edges"][k]["shade"] for k in edges) / L
stats["demo"]["base_shade"] = shaded_share(r["baseline"]["edges"])
stats["demo"]["cool_shade"] = shaded_share(r["cool"]["edges"])

# ---------- 2. pareto: heat vs distance as budget tightens
bud = list(range(20, 101, 5))
pts = []
for b in bud:
    rr = plan(g, SRC, DST, HOUR, b)
    pts.append((b, rr["cool"]["m"]["dist"], rr["cool"]["m"]["heat"], rr["budget_met"]))
fig, ax = plt.subplots(figsize=(6.2, 3.6))
ax.plot([p[1] for p in pts], [p[2] for p in pts], "-o", color=COOL, ms=4)
for p in pts[::3]:
    ax.annotate(f"{p[0]}%", (p[1], p[2]), textcoords="offset points", xytext=(5, 5), fontsize=8, color=MUTED)
ax.set_xlabel("Walking distance (m)"); ax.set_ylabel("Heat exposure (sun-metres)")
ax.set_title("The trade-off: a tighter heat budget means a longer walk", fontsize=10, color=INK)
ax.grid(alpha=0.25)
save("fig_pareto.png")
stats["pareto"] = pts

# ---------- 3. across the day
hrs = np.arange(6, 18.01, 0.5)
bh, ch, sun = [], [], []
for h in hrs:
    rr = plan(g, SRC, DST, float(h), 60)
    bh.append(rr["baseline"]["m"]["heat"]); ch.append(rr["cool"]["m"]["heat"]); sun.append(sun_factor(h))
fig, ax = plt.subplots(figsize=(6.2, 3.6))
ax.plot(hrs, bh, color=HEAT, lw=2, label="Shortest route")
ax.plot(hrs, ch, color=COOL, lw=2, label="CoolRoute (60% budget)")
ax.fill_between(hrs, ch, bh, color=COOL, alpha=0.12)
ax.set_xlabel("Hour of day"); ax.set_ylabel("Heat exposure (sun-metres)")
ax.set_title("Heat saved is biggest when the sun is strongest", fontsize=10, color=INK)
ax.legend(frameon=False); ax.grid(alpha=0.25)
save("fig_day.png")

# ---------- 4. many random trips
rnd = random.Random(11)
cuts, extras, times = [], [], []
met = 0
N = 300
for _ in range(N):
    s, d = rnd.sample(range(64), 2)
    if abs(s // 8 - d // 8) + abs(s % 8 - d % 8) < 6:
        continue
    rr = plan(g, s, d, HOUR, 60)
    b, c = rr["baseline"]["m"], rr["cool"]["m"]
    if b["heat"] <= 0:
        continue
    cuts.append(100 * (1 - c["heat"] / b["heat"]))
    extras.append(100 * (c["dist"] / b["dist"] - 1))
    times.append((c["time"] - b["time"]) / 60)
    met += rr["budget_met"]
trips = len(cuts)
stats["many"] = {"trips": trips, "median_cut": float(np.median(cuts)), "mean_cut": float(np.mean(cuts)),
                 "median_extra": float(np.median(extras)), "p90_extra": float(np.percentile(extras, 90)),
                 "budget_met_pct": 100 * met / trips, "over20": float(np.mean(np.array(extras) > 20) * 100)}
fig, axs = plt.subplots(1, 2, figsize=(6.6, 3.2))
axs[0].hist(cuts, bins=14, color=COOL, alpha=0.85)
axs[0].set_xlabel("Heat reduction (%)"); axs[0].set_ylabel("Number of trips"); axs[0].set_title("Heat cut", fontsize=10, color=INK)
axs[1].hist(extras, bins=14, color=HEAT, alpha=0.85)
axs[1].set_xlabel("Extra distance (%)"); axs[1].set_title("Price paid in distance", fontsize=10, color=INK)
save("fig_hist.png")

# ---------- 5. lambda sweep (why bisection works)
sun = sun_factor(HOUR)
adj = make_adj(g, sun)
base = dijkstra(adj, SRC, DST, 0.0)
bs = summarise(g, base[1], sun)
budget = bs["heat"] * 0.6
lams = np.linspace(0, 0.4, 401)
hh_, dd_ = [], []
for lm in lams:
    rr = dijkstra(adj, SRC, DST, float(lm))
    sm = summarise(g, rr[1], sun)
    hh_.append(sm["heat"]); dd_.append(sm["dist"])
chosen = next(lm for lm, h in zip(lams, hh_) if h <= budget)
fig, axs = plt.subplots(1, 2, figsize=(6.8, 3.2))
axs[0].step(lams, hh_, where="post", color=COOL, lw=2)
axs[0].axhline(budget, color=HEAT, ls="--", label=f"Heat budget ({budget:.0f})")
axs[0].axvline(chosen, color=MUTED, ls=":", lw=1)
axs[0].set_xlabel("Price of heat, λ"); axs[0].set_ylabel("Heat of the best route")
axs[0].set_title("Heat only goes down as λ rises", fontsize=9, color=INK); axs[0].legend(frameon=False, fontsize=8)
axs[1].step(lams, dd_, where="post", color=HEAT, lw=2)
axs[1].axvline(chosen, color=MUTED, ls=":", lw=1)
axs[1].set_xlabel("Price of heat, λ"); axs[1].set_ylabel("Distance of the best route (m)")
axs[1].set_title("Distance only goes up", fontsize=9, color=INK)
save("fig_lambda.png")
stats["lambda"] = {"chosen": float(chosen), "budget": budget}

# ---------- 6. sun curve + shadow geometry
fig, axs = plt.subplots(1, 2, figsize=(6.8, 3.0), gridspec_kw={"width_ratios": [1.1, 1]})
hh = np.linspace(5, 19, 200)
axs[0].plot(hh, [sun_factor(h) for h in hh], color=HEAT, lw=2)
axs[0].fill_between(hh, [sun_factor(h) for h in hh], color=HEAT, alpha=0.15)
axs[0].set_xlabel("Hour of day"); axs[0].set_ylabel("sun(t)"); axs[0].set_title("Sun strength, Jaipur, mid-October", fontsize=9, color=INK)
ax = axs[1]
ax.set_xlim(0, 10); ax.set_ylim(0, 6); ax.axis("off")
ax.add_patch(plt.Rectangle((0.5, 0), 1.5, 4, color="#9fb3bb"))
ax.plot([0, 10], [0, 0], color=INK, lw=2)
ax.plot([2, 6.2], [4, 0], color=HEAT, lw=1.5)
ax.plot([2, 6.2], [0, 0], color=INK, lw=4, alpha=0.5)
ax.annotate("", xy=(2, 4.6), xytext=(2, 0.1), arrowprops=dict(arrowstyle="<->", color=INK))
ax.text(0.2, 2, "H", fontsize=10, color=INK)
ax.text(3.7, -0.7, "L = H / tan(α)", fontsize=9, color=INK, ha="center")
ax.text(5.6, 1.6, "α", fontsize=11, color=HEAT)
ax.text(5, 5.2, "Building shadow", fontsize=9, color=MUTED, ha="center")
save("fig_sun.png")

# ---------- 7. architecture diagram
def box(ax, x, y, w, h, text, fc, tc="white", fs=8.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec="none"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", color=tc, fontsize=fs, fontweight="bold", linespacing=1.25)
def arrow(ax, x1, y1, x2, y2, c=MUTED):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12, color=c, lw=1.4))

fig, ax = plt.subplots(figsize=(7.2, 4.6))
ax.set_xlim(0, 12); ax.set_ylim(0, 8); ax.axis("off")
ax.text(0.1, 7.6, "1  User", fontsize=8, color=MUTED); ax.text(3.2, 7.6, "2  Frontend", fontsize=8, color=MUTED)
ax.text(6.4, 7.6, "3  Backend", fontsize=8, color=MUTED); ax.text(9.4, 7.6, "4  Data and models", fontsize=8, color=MUTED)
box(ax, 0.1, 5.4, 2.4, 1.6, "Phone or laptop\nbrowser (PWA)", INK)
box(ax, 3.2, 5.9, 2.5, 1.1, "React + MapLibre\nmap and controls", COOL)
box(ax, 3.2, 4.3, 2.5, 1.1, "Charts and\nexplanation panel", COOL)
box(ax, 6.4, 6.2, 2.5, 0.9, "FastAPI gateway\n/route /scenario", "#2a5d7a")
box(ax, 6.4, 4.9, 2.5, 0.9, "Routing engine\nDijkstra + λ search", "#2a5d7a")
box(ax, 6.4, 3.6, 2.5, 0.9, "Heat model\nsun(t) x (1 - shade)", "#2a5d7a")
box(ax, 6.4, 2.3, 2.5, 0.9, "Shade model (ML)\nGradient boosting", "#2a5d7a")
box(ax, 9.4, 6.2, 2.5, 0.9, "OpenStreetMap\nstreets, buildings", TREE)
box(ax, 9.4, 4.9, 2.5, 0.9, "Open-Meteo\nweather, radiation", TREE)
box(ax, 9.4, 3.6, 2.5, 0.9, "Sentinel-2\nNDVI tree cover", TREE)
box(ax, 9.4, 2.3, 2.5, 0.9, "PostGIS database\ngraph and cache", "#6b7f88")
for y in (6.45,):
    arrow(ax, 2.5, 6.4, 3.2, 6.4)
arrow(ax, 5.7, 6.45, 6.4, 6.65); arrow(ax, 7.65, 6.2, 7.65, 5.8); arrow(ax, 7.65, 4.9, 7.65, 4.5)
arrow(ax, 7.65, 3.6, 7.65, 3.2)
arrow(ax, 8.9, 6.65, 9.4, 6.65); arrow(ax, 8.9, 4.0, 9.4, 5.2); arrow(ax, 8.9, 2.75, 9.4, 3.9); arrow(ax, 8.9, 2.6, 9.4, 2.6)
arrow(ax, 6.4, 5.3, 5.7, 4.9, c=COOL)
ax.text(6, 0.9, "Free-tier tools only. Prototype runs fully in the browser with synthetic data.", ha="center", fontsize=8, color=MUTED)
save("fig_arch.png")

# ---------- 8. app flow
fig, ax = plt.subplots(figsize=(7.2, 3.4))
ax.set_xlim(0, 14); ax.set_ylim(0, 6); ax.axis("off")
steps = [("1\nOpen app", INK), ("2\nPick start\nand end", INK), ("3\nSet time and\nheat budget", COOL), ("4\nOptional:\nstep-free, closed\nfootpath, shade", COOL),
         ("5\nCompute\nshortest route", "#2a5d7a"), ("6\nCompute\nCoolRoute", "#2a5d7a"), ("7\nCompare and\nexplain trade-off", TREE)]
x = 0.1
for i, (t, c) in enumerate(steps):
    row = 0 if i < 4 else 1
    xx = 0.2 + (i if i < 4 else i - 4) * 3.4 + (0 if i < 4 else 1.7)
    yy = 3.5 if i < 4 else 0.7
    box(ax, xx, yy, 2.8, 1.9, t, c, fs=8)
    if i < 3: arrow(ax, xx + 2.8, yy + 0.95, xx + 3.4, yy + 0.95)
    if i == 3: arrow(ax, xx + 1.4, yy, 0.2 + 0 * 3.4 + 1.7 + 1.4, 2.6)
    if 4 <= i < 6: arrow(ax, xx + 2.8, yy + 0.95, xx + 3.4, yy + 0.95)
save("fig_flow.png")

# ---------- 9. ML shade model (synthetic demo)
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
rs = np.random.RandomState(5)
n = 6000
H = rs.uniform(0, 30, n)            # building height (m)
W = rs.uniform(6, 30, n)            # street width (m)
theta = rs.uniform(0, 180, n)       # street bearing
ndvi = rs.uniform(0, 0.8, n)        # tree greenness
alt = rs.uniform(10, 85, n)         # sun elevation
az = rs.uniform(60, 300, n)         # sun azimuth
Lsh = H / np.tan(np.radians(alt))
Lperp = Lsh * np.abs(np.sin(np.radians(az - theta)))
bshade = np.clip(Lperp / W, 0, 1)
tshade = np.clip(1.4 * ndvi - 0.1, 0, 0.9)
true = 1 - (1 - bshade) * (1 - tshade)
y = np.clip(true + rs.normal(0, 0.05, n), 0, 1)
X = np.c_[H, W, theta, ndvi, alt, az]
names = ["building height", "street width", "street bearing", "tree greenness (NDVI)", "sun elevation", "sun azimuth"]
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=1)
q = {}
for a in (0.1, 0.5, 0.9):
    m = GradientBoostingRegressor(loss="quantile", alpha=a, n_estimators=200, max_depth=3, learning_rate=0.08, random_state=1)
    m.fit(Xtr, ytr); q[a] = m
p50 = q[0.5].predict(Xte)
lo_, hi_ = q[0.1].predict(Xte), q[0.9].predict(Xte)
cover = float(np.mean((yte >= lo_) & (yte <= hi_)))
mae = mean_absolute_error(yte, p50); r2 = r2_score(yte, p50)
mean_model = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.08, random_state=1).fit(Xtr, ytr)
imp = mean_model.feature_importances_
stats["ml"] = {"mae": mae, "r2": r2, "coverage80": cover, "n": n, "importance": dict(zip(names, imp.tolist()))}
fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.2))
axs[0].scatter(yte[:600], p50[:600], s=6, color=COOL, alpha=0.5)
axs[0].plot([0, 1], [0, 1], color=HEAT, lw=1.2)
axs[0].set_xlabel("Actual shade"); axs[0].set_ylabel("Predicted shade"); axs[0].set_title(f"R² = {r2:.2f}, MAE = {mae:.3f}", fontsize=9, color=INK)
order = np.argsort(imp)
axs[1].barh([names[i] for i in order], imp[order], color=TREE)
axs[1].set_title("What the model relies on", fontsize=9, color=INK); axs[1].tick_params(axis="y", labelsize=7)
save("fig_ml.png")

# ---------- 10. revenue projection (illustrative assumptions)
yrs = ["Year 1", "Year 2", "Year 3"]
city = [1 * 6.0, 3 * 8.0, 8 * 10.0]                 # lakh rupees
api = [0.5e6 * 0.15 / 1e5, 3e6 * 0.15 / 1e5, 12e6 * 0.15 / 1e5]
prem = [500 * 399 / 1e5, 4000 * 399 / 1e5, 20000 * 399 / 1e5]
fig, ax = plt.subplots(figsize=(6.2, 3.5))
ax.bar(yrs, city, color=COOL, label="City licences")
ax.bar(yrs, prem, bottom=city, color=TREE, label="Premium app")
ax.bar(yrs, api, bottom=[c + p for c, p in zip(city, prem)], color=HEAT, label="Route API")
tot = [c + p + a for c, p, a in zip(city, prem, api)]
for i, t in enumerate(tot):
    ax.text(i, t + 3, f"{t:.1f} lakh", ha="center", fontsize=9, color=INK)
ax.set_ylabel("Revenue (Rs lakh per year)"); ax.set_ylim(0, max(tot) * 1.18)
ax.set_title("Illustrative 3-year revenue plan (assumptions, not a forecast)", fontsize=10, color=INK)
ax.legend(frameon=False, loc="upper left")
save("fig_rev.png")
stats["rev"] = {"city": city, "api": api, "prem": prem, "total": tot}

json.dump(stats, open("stats.json", "w"), indent=1, default=float)
print(json.dumps({k: v for k, v in stats.items() if k not in ("pareto", "lambda")}, indent=1, default=float))
