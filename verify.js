// compare JS core with Python core on several scenarios
const fs = require("fs");
const core = require("./core.js");
const G = JSON.parse(fs.readFileSync("graph.json"));
const cases = JSON.parse(fs.readFileSync("py_cases.json"));
let ok = 0;
for (const c of cases) {
  const g = JSON.parse(JSON.stringify(G));
  (c.closed || []).forEach(k => g.edges[k].closed = true);
  const r = core.plan(g, c.src, c.dst, c.hour, c.budget, c.stepfree, c.shade);
  const same = c.err ? r.error === "no_route" :
    JSON.stringify(r.cool.edges) === JSON.stringify(c.cool_edges) &&
    JSON.stringify(r.baseline.edges) === JSON.stringify(c.base_edges) &&
    Math.abs(r.cool.m.heat - c.cool_heat) < 1e-6;
  if (same) ok++; else console.log("MISMATCH", JSON.stringify(c).slice(0, 120));
}
console.log(ok + "/" + cases.length + " scenarios match Python");
