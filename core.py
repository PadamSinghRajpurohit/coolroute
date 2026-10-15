"""CoolRoute core: heat-exposure-aware pedestrian routing.

Edge model
----------
Every street segment (edge) carries:
  length (m), shade (0..1), slope (%), step_free (bool), confidence (0..1)

Heat exposure of an edge  =  length * (1 - shade) * sun(t)        [sun-metres]
Effort of an edge         =  length * (1 + 0.05 * slope%)         [effort-metres]
Crossings add a waiting time that also accrues heat if unshaded.

Two routes
----------
1. Baseline  : minimise distance only (classic Dijkstra, λ=0).
2. CoolRoute : minimise distance subject to heat ≤ budget.
   Solved with Lagrangian relaxation:  cost = distance + λ * heat
   λ found by bisection (40 iterations, fast and explainable).
"""
import heapq
import json
import math
import random

# Defaults — overridden at runtime for real-data routes
DEFAULT_LAT = 26.9      # Jaipur latitude
WALK_SPEED  = 1.3       # m/s  (~4.7 km/h average pedestrian)


# ──────────────────────────────────────────── sun model ──
def sun_factor(hour: float, lat: float = DEFAULT_LAT, day_of_year: int = 288) -> float:
    """Fractional sun strength 0..1 for a clock hour (solar time).

    Uses standard astronomical formula:
      sin(elevation) = sin(φ)·sin(δ) + cos(φ)·cos(δ)·cos(h)
    where φ = latitude, δ = solar declination, h = hour angle.
    Returns 0 when the sun is below the horizon.
    """
    dec = math.radians(23.45 * math.sin(math.radians(360 / 365 * (day_of_year - 81))))
    phi = math.radians(lat)
    h   = math.radians(15.0 * (hour - 12.0))
    elev = math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(h)
    return max(0.0, elev)


# ──────────────────────────────────────── synthetic grid ──
def build_neighbourhood(n: int = 8, spacing: int = 80, seed: int = 7) -> dict:
    """Synthetic n×n street grid for offline demos.  Node id = row*n + col."""
    rnd = random.Random(seed)
    nodes = [{"id": r * n + c, "x": c * spacing, "y": r * spacing}
             for r in range(n) for c in range(n)]
    edges = []

    def add(a: int, b: int, kind: str) -> None:
        length = spacing * rnd.uniform(0.95, 1.1)
        ra, ca = divmod(a, n)
        rb, cb = divmod(b, n)
        shaded_line = (ca == cb == 2) or (ra == rb == 5)   # tree-lined
        shade  = rnd.uniform(0.65, 0.9) if shaded_line else rnd.uniform(0.0, 0.3)
        slope  = rnd.choice([0, 0, 0, 1, 2, 3, 6])
        step_free   = rnd.random() > 0.12
        crossing    = kind == "cross"
        wait        = rnd.choice([10, 20, 35, 50]) if crossing else 0
        cross_shade = round(rnd.uniform(0.0, 0.5), 2) if crossing else 0
        confidence  = round(rnd.uniform(0.35, 1.0), 2)
        if rnd.random() < 0.1:
            confidence = round(rnd.uniform(0.0, 0.25), 2)   # missing-data simulation
        edges.append({
            "a": a, "b": b, "length": round(length, 1), "shade": round(shade, 2),
            "slope": float(slope), "step_free": step_free,
            "wait": wait, "crossing_shade": cross_shade,
            "confidence": confidence, "closed": False,
        })

    for r in range(n):
        for c in range(n):
            i = r * n + c
            if c + 1 < n:
                add(i, i + 1, "cross" if (r % 3 == 0 and c % 2 == 0) else "street")
            if r + 1 < n:
                add(i, i + n, "cross" if (c % 3 == 0 and r % 2 == 0) else "street")
    return {"n": n, "spacing": spacing, "nodes": nodes, "edges": edges}


# ────────────────────────────────────────── edge costs ──
def edge_metrics(e: dict, sun: float, shade_on: bool = True) -> dict:
    """Compute per-edge cost metrics given current sun strength."""
    shade  = e["shade"]          if shade_on else 0.0
    cshade = e["crossing_shade"] if shade_on else 0.0
    walk_heat = e["length"] * (1.0 - shade)  * sun
    wait_heat = e["wait"]   * WALK_SPEED * (1.0 - cshade) * sun
    heat   = walk_heat + wait_heat
    effort = e["length"] * (1.0 + 0.05 * e.get("slope", 0))
    time_s = e["length"] / WALK_SPEED + e["wait"]
    return {"dist": e["length"], "heat": round(heat, 4),
            "effort": round(effort, 4), "time": round(time_s, 4)}


def make_adj(g: dict, sun: float,
             step_free_only: bool = False,
             shade_on: bool = True) -> dict:
    """Build adjacency list from graph, respecting closed edges and accessibility."""
    adj: dict = {nd["id"]: [] for nd in g["nodes"]}
    for k, e in enumerate(g["edges"]):
        if e.get("closed"):
            continue
        if step_free_only and not e.get("step_free", True):
            continue
        m = edge_metrics(e, sun, shade_on)
        adj[e["a"]].append((e["b"], k, m))
        adj[e["b"]].append((e["a"], k, m))
    return adj


# ──────────────────────────────────── Dijkstra search ──
def dijkstra(adj: dict, src: int, dst: int, lam: float):
    """Minimise dist + lam*heat via Dijkstra.

    Returns (path_nodes, path_edges) or None if unreachable.
    """
    best = {src: 0.0}
    prev: dict = {}
    pq = [(0.0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == dst:
            break
        if d > best.get(u, 1e18):
            continue
        for v, k, m in adj.get(u, []):
            nd = d + m["dist"] + lam * m["heat"]
            if nd < best.get(v, 1e18):
                best[v] = nd
                prev[v] = (u, k)
                heapq.heappush(pq, (nd, v))
    if dst not in prev and dst != src:
        return None
    nodes, eds = [dst], []
    cur = dst
    while cur != src:
        if cur not in prev:
            return None
        u, k = prev[cur]
        eds.append(k)
        nodes.append(u)
        cur = u
    return nodes[::-1], eds[::-1]


# ─────────────────────────────────────── summarise ──
def summarise(g: dict, adj_edges: list, sun: float,
              shade_on: bool = True) -> dict:
    """Aggregate metrics across a route's edge list."""
    tot = {"dist": 0.0, "heat": 0.0, "effort": 0.0, "time": 0.0}
    low_conf = 0
    shade_len = 0.0
    for k in adj_edges:
        e = g["edges"][k]
        m = edge_metrics(e, sun, shade_on)
        for key in tot:
            tot[key] += m[key]
        if e.get("confidence", 1.0) < 0.3:
            low_conf += 1
        shade_len += e["length"] * (e["shade"] if shade_on else 0.0)
    total_len = tot["dist"] or 1.0
    tot["shaded_share"]    = round(shade_len / total_len, 4)
    tot["missing_edges"]   = low_conf
    tot["n_edges"]         = len(adj_edges)
    tot["data_confidence"] = round(
        sum(g["edges"][k].get("confidence", 1.0) for k in adj_edges) /
        max(1, len(adj_edges)), 4
    )
    return tot


# ────────────────────────────────────────────── plan ──
def plan(g: dict, src: int, dst: int, hour: float,
         budget_pct: float = 60.0,
         step_free_only: bool = False,
         shade_on: bool = True,
         sun_override: float | None = None) -> dict:
    """Return baseline and CoolRoute.

    budget_pct: allowed heat as % of baseline heat (100 = no constraint).
    sun_override: bypass the astronomical model (0..1 fraction).
    """
    sun = (sun_factor(hour) if sun_override is None
           else max(0.0, min(1.0, float(sun_override))))
    adj = make_adj(g, sun, step_free_only, shade_on)

    base_r = dijkstra(adj, src, dst, 0.0)
    if base_r is None:
        return {"error": "no_route", "sun": round(sun, 4)}

    base_s = summarise(g, base_r[1], sun, shade_on)
    budget = base_s["heat"] * budget_pct / 100.0

    # Already within budget?
    if base_s["heat"] <= budget + 1e-9:
        return {
            "sun": round(sun, 4), "budget": round(budget, 4), "budget_met": True,
            "baseline": {"nodes": base_r[0], "edges": base_r[1], "m": base_s},
            "cool":     {"nodes": base_r[0], "edges": base_r[1], "m": base_s},
        }

    # Lagrangian bisection
    lo, hi = 0.0, 100.0
    best_r, best_s, feasible = base_r, base_s, False
    for _ in range(40):
        mid = (lo + hi) / 2.0
        r   = dijkstra(adj, src, dst, mid)
        if r is None:
            break
        s = summarise(g, r[1], sun, shade_on)
        if s["heat"] <= budget + 1e-9:
            best_r, best_s, feasible = r, s, True
            hi = mid
        else:
            lo = mid

    if not feasible:
        # Return coolest possible even if budget not met
        r = dijkstra(adj, src, dst, hi)
        if r:
            best_r, best_s = r, summarise(g, r[1], sun, shade_on)

    return {
        "sun": round(sun, 4), "budget": round(budget, 4),
        "budget_met": best_s["heat"] <= budget + 1e-9,
        "baseline": {"nodes": base_r[0], "edges": base_r[1], "m": base_s},
        "cool":     {"nodes": best_r[0], "edges": best_r[1], "m": best_s},
    }


# ─────────────────────────────── standalone smoke test ──
if __name__ == "__main__":
    g = build_neighbourhood()
    with open("graph.json", "w") as f:
        json.dump(g, f)
    r = plan(g, 0, 63, 13.0, 60)
    print(json.dumps({k: v for k, v in r.items() if k in ("sun", "budget", "budget_met")}))
    for key in ("baseline", "cool"):
        m = r[key]["m"]
        print(key, {k: round(v, 3) if isinstance(v, float) else v for k, v in m.items()})
