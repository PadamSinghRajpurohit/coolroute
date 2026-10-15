// CoolRoute core (JavaScript port of core.py). Same maths, same results.
const LAT = 26.9, WALK_SPEED = 1.3;

function sunFactor(hour, doy = 288) {
  const dec = (23.45 * Math.sin(((360 / 365) * (doy - 81) * Math.PI) / 180) * Math.PI) / 180;
  const lat = (LAT * Math.PI) / 180;
  const h = (15 * (hour - 12) * Math.PI) / 180;
  const s = Math.sin(lat) * Math.sin(dec) + Math.cos(lat) * Math.cos(dec) * Math.cos(h);
  return Math.max(0, s);
}

function edgeMetrics(e, sun, shadeOn) {
  const shade = shadeOn ? e.shade : 0;
  const cshade = shadeOn ? e.crossing_shade : 0;
  const walkHeat = e.length * (1 - shade) * sun;
  const waitHeat = e.wait * WALK_SPEED * (1 - cshade) * sun;
  return {
    dist: e.length,
    heat: walkHeat + waitHeat,
    effort: e.length * (1 + 0.05 * e.slope),
    time: e.length / WALK_SPEED + e.wait,
  };
}

function makeAdj(g, sun, stepFreeOnly, shadeOn) {
  const adj = g.nodes.map(() => []);
  g.edges.forEach((e, k) => {
    if (e.closed) return;
    if (stepFreeOnly && !e.step_free) return; // hard constraint
    const m = edgeMetrics(e, sun, shadeOn);
    adj[e.a].push([e.b, k, m]);
    adj[e.b].push([e.a, k, m]);
  });
  return adj;
}

// minimise dist + lam * heat  (small graph: simple O(V^2) Dijkstra)
function dijkstra(adj, src, dst, lam) {
  const N = adj.length;
  const best = new Array(N).fill(Infinity);
  const done = new Array(N).fill(false);
  const prev = new Array(N).fill(null);
  best[src] = 0;
  for (let it = 0; it < N; it++) {
    let u = -1, bu = Infinity;
    for (let i = 0; i < N; i++) if (!done[i] && best[i] < bu) { bu = best[i]; u = i; }
    if (u < 0 || u === dst) break;
    done[u] = true;
    for (const [v, k, m] of adj[u]) {
      const nd = bu + m.dist + lam * m.heat;
      if (nd < best[v]) { best[v] = nd; prev[v] = [u, k]; }
    }
  }
  if (!isFinite(best[dst])) return null;
  const nodes = [dst], eds = [];
  while (nodes[nodes.length - 1] !== src) {
    const [u, k] = prev[nodes[nodes.length - 1]];
    eds.push(k); nodes.push(u);
  }
  return { nodes: nodes.reverse(), edges: eds.reverse() };
}

function summarise(g, edgeIds, sun, shadeOn) {
  const t = { dist: 0, heat: 0, effort: 0, time: 0, shadedLen: 0 };
  let missing = 0, conf = 0;
  for (const k of edgeIds) {
    const e = g.edges[k];
    const m = edgeMetrics(e, sun, shadeOn);
    t.dist += m.dist; t.heat += m.heat; t.effort += m.effort; t.time += m.time;
    t.shadedLen += e.length * (shadeOn ? e.shade : 0);
    if (e.confidence < 0.3) missing++;
    conf += e.confidence;
  }
  t.missing_edges = missing;
  t.n_edges = edgeIds.length;
  t.data_confidence = conf / Math.max(1, edgeIds.length);
  t.shaded_share = t.dist > 0 ? t.shadedLen / t.dist : 0;
  return t;
}

function plan(g, src, dst, hour, budgetPct = 60, stepFreeOnly = false, shadeOn = true) {
  const sun = sunFactor(hour);
  const adj = makeAdj(g, sun, stepFreeOnly, shadeOn);
  const base = dijkstra(adj, src, dst, 0);
  if (!base) return { error: "no_route", sun };
  const baseS = summarise(g, base.edges, sun, shadeOn);
  const budget = (baseS.heat * budgetPct) / 100;
  let lo = 0, hi = 50, best = base, bestS = baseS, feasible = baseS.heat <= budget;
  if (!feasible) {
    for (let i = 0; i < 40; i++) {
      const mid = (lo + hi) / 2;
      const r = dijkstra(adj, src, dst, mid);
      const s = summarise(g, r.edges, sun, shadeOn);
      if (s.heat <= budget) { best = r; bestS = s; feasible = true; hi = mid; } else lo = mid;
    }
    if (!feasible) {
      const r = dijkstra(adj, src, dst, hi);
      best = r; bestS = summarise(g, r.edges, sun, shadeOn);
    }
  }
  return {
    sun, budget, budget_met: bestS.heat <= budget + 1e-9,
    baseline: { nodes: base.nodes, edges: base.edges, m: baseS },
    cool: { nodes: best.nodes, edges: best.edges, m: bestS },
  };
}

if (typeof module !== "undefined") module.exports = { sunFactor, plan, edgeMetrics };
