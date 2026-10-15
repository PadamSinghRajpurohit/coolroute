(function () {
  const $ = (id) => document.getElementById(id);
  const NS = "http://www.w3.org/2000/svg";
  const G = GRAPH;
  const state = { start: 0, end: 63, hour: 13, budget: 60, stepFree: false, shade: true, mode: "start" };
  const SPAN = (G.n - 1) * G.spacing;

  function el(tag, attrs, parent) {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }

  // ------------------------------------------------------------ build map
  const svg = $("map");
  const gEdges = el("g", {}, svg), gMissing = el("g", {}, svg), gBase = el("g", {}, svg),
        gCool = el("g", {}, svg), gCross = el("g", {}, svg), gNodes = el("g", {}, svg),
        gHit = el("g", {}, svg), gLabels = el("g", {}, svg);
  const nodeXY = (i) => G.nodes[i];
  const edgeEls = [], hitEls = [];

  G.edges.forEach((e, k) => {
    const a = nodeXY(e.a), b = nodeXY(e.b);
    const l = el("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y, class: "edge" }, gEdges);
    edgeEls.push(l);
    if (e.confidence < 0.3) {
      el("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y, class: "missing" }, gMissing);
    }
    if (e.wait > 0) {
      el("rect", { x: (a.x + b.x) / 2 - 4, y: (a.y + b.y) / 2 - 4, width: 8, height: 8, rx: 1.5, class: "cross" }, gCross);
    }
    const h = el("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y, class: "hit" }, gHit);
    h.addEventListener("click", () => {
      if (state.mode === "close") { e.closed = !e.closed; render(); }
    });
    hitEls.push(h);
  });

  const nodeEls = G.nodes.map((nd, i) => {
    const c = el("circle", { cx: nd.x, cy: nd.y, r: 3.5, class: "node" }, gNodes);
    const h = el("circle", { cx: nd.x, cy: nd.y, r: 13, class: "hit" }, gHit);
    h.addEventListener("click", () => {
      if (state.mode === "start") { if (i !== state.end) state.start = i; setMode("end"); }
      else if (state.mode === "end") { if (i !== state.start) state.end = i; }
      render();
    });
    return c;
  });

  const pin = (cls) => {
    const g = el("g", { class: "pin " + cls }, gLabels);
    el("circle", { r: 11 }, g);
    const t = el("text", { "text-anchor": "middle", dy: "4.5" }, g);
    t.textContent = cls === "pin-a" ? "A" : "B";
    return g;
  };
  const pinA = pin("pin-a"), pinB = pin("pin-b");

  function pathD(nodes) {
    return nodes.map((n, i) => (i ? "L" : "M") + nodeXY(n).x + " " + nodeXY(n).y).join(" ");
  }

  // ---------------------------------------------------------------- UI
  function setMode(m) {
    state.mode = m;
    document.querySelectorAll('input[name="mode"]').forEach((r) => (r.checked = r.value === m));
  }
  function fmtTime(h) {
    const hh = Math.floor(h), mm = Math.round((h - hh) * 60);
    const ap = hh >= 12 ? "pm" : "am";
    const h12 = hh % 12 === 0 ? 12 : hh % 12;
    return h12 + ":" + String(mm).padStart(2, "0") + " " + ap;
  }
  const f0 = (x) => Math.round(x).toLocaleString("en-IN");
  const f1 = (x) => x.toFixed(1);
  const pct = (x) => Math.round(x * 100) + "%";
  const sign = (x) => (x > 0 ? "+" : x < 0 ? "−" : "");

  function bindControls() {
    $("hour").addEventListener("input", (e) => { state.hour = +e.target.value; render(); });
    $("budget").addEventListener("input", (e) => { state.budget = +e.target.value; render(); });
    $("stepfree").addEventListener("change", (e) => { state.stepFree = e.target.checked; render(); });
    $("shade").addEventListener("change", (e) => { state.shade = e.target.checked; render(); });
    document.querySelectorAll('input[name="mode"]').forEach((r) =>
      r.addEventListener("change", (e) => { state.mode = e.target.value; render(); }));
    $("reopen").addEventListener("click", () => { G.edges.forEach((e) => (e.closed = false)); render(); });
    $("swap").addEventListener("click", () => { const t = state.start; state.start = state.end; state.end = t; render(); });
    $("preset-noon").addEventListener("click", () => { state.hour = 13; state.budget = 60; $("hour").value = 13; $("budget").value = 60; render(); });
    $("preset-eve").addEventListener("click", () => { state.hour = 17.5; $("hour").value = 17.5; render(); });
  }

  // ------------------------------------------------------------- charts
  function drawSun() {
    const s = $("sunchart");
    s.innerHTML = "";
    const W = 320, H = 110, L = 8, R = 8, T = 10, B = 24;
    const x = (h) => L + ((h - 5) / 14) * (W - L - R);
    const y = (v) => T + (1 - v) * (H - T - B);
    el("line", { x1: L, y1: y(0), x2: W - R, y2: y(0), class: "ax" }, s);
    let d = "";
    for (let h = 5; h <= 19.001; h += 0.25) d += (d ? "L" : "M") + x(h).toFixed(1) + " " + y(sunFactor(h)).toFixed(1);
    const area = d + `L${x(19)} ${y(0)} L${x(5)} ${y(0)} Z`;
    el("path", { d: area, class: "sunfill" }, s);
    el("path", { d, class: "sunline" }, s);
    [6, 9, 12, 15, 18].forEach((h) => {
      const t = el("text", { x: x(h), y: H - 6, "text-anchor": "middle", class: "tick" }, s);
      t.textContent = h === 12 ? "12 pm" : h > 12 ? h - 12 + " pm" : h + " am";
    });
    const sv = sunFactor(state.hour);
    el("line", { x1: x(state.hour), y1: y(0), x2: x(state.hour), y2: y(sv), class: "mark" }, s);
    el("circle", { cx: x(state.hour), cy: y(sv), r: 4.5, class: "markdot" }, s);
  }

  // --------------------------------------------------------------- render
  function render() {
    $("hourlabel").textContent = fmtTime(state.hour);
    $("budgetlabel").textContent = state.budget + "% of shortest-route heat";
    const sunNow = sunFactor(state.hour);
    $("sunlabel").textContent = "Sun strength " + Math.round(sunNow * 100) + "%";

    G.edges.forEach((e, k) => {
      const shaded = state.shade && e.shade >= 0.5;
      let c = "edge " + (shaded ? "e-shade" : "e-sun");
      if (e.closed) c = "edge e-closed";
      else if (state.stepFree && !e.step_free) c = "edge e-steps";
      edgeEls[k].setAttribute("class", c);
    });
    pinA.setAttribute("transform", `translate(${nodeXY(state.start).x} ${nodeXY(state.start).y})`);
    pinB.setAttribute("transform", `translate(${nodeXY(state.end).x} ${nodeXY(state.end).y})`);

    gBase.innerHTML = ""; gCool.innerHTML = "";
    const out = $("results"), warn = $("warnings"), verdict = $("verdict");
    warn.innerHTML = "";
    const r = plan(G, state.start, state.end, state.hour, state.budget, state.stepFree, state.shade);

    if (r.error) {
      out.hidden = true;
      verdict.textContent = "No route found. The closed footpaths" + (state.stepFree ? " and the step-free rule" : "") +
        " leave no connection between A and B. Reopen a footpath or turn off step-free to continue.";
      verdict.className = "verdict bad";
      drawSun();
      return;
    }
    out.hidden = false;
    el("path", { d: pathD(r.baseline.nodes), class: "route-base" }, gBase);
    el("path", { d: pathD(r.cool.nodes), class: "route-cool" }, gCool);

    const B = r.baseline.m, C = r.cool.m;
    const rows = [
      ["Distance", f0(B.dist) + " m", f0(C.dist) + " m", C.dist - B.dist, " m", 0],
      ["Walk time", f1(B.time / 60) + " min", f1(C.time / 60) + " min", (C.time - B.time) / 60, " min", 1],
      ["Heat exposure", f0(B.heat), f0(C.heat), C.heat - B.heat, "", 0],
      ["Shaded share", pct(B.shaded_share), pct(C.shaded_share), (C.shaded_share - B.shaded_share) * 100, " pts", 0],
      ["Effort", f0(B.effort), f0(C.effort), C.effort - B.effort, "", 0],
      ["Data confidence", pct(B.data_confidence), pct(C.data_confidence), (C.data_confidence - B.data_confidence) * 100, " pts", 0],
    ];
    const tb = $("rows");
    tb.innerHTML = "";
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      const dv = row[3];
      const good = row[0] === "Shaded share" || row[0] === "Data confidence" ? dv > 0.5 : dv < -0.5;
      const bad = row[0] === "Shaded share" || row[0] === "Data confidence" ? dv < -0.5 : dv > 0.5;
      const dtxt = Math.abs(dv) < 0.05 ? "0" : sign(dv) + (row[5] ? Math.abs(dv).toFixed(1) : Math.round(Math.abs(dv))) + row[4];
      [row[0], row[1], row[2]].forEach((t, i) => {
        const td = document.createElement(i ? "td" : "th");
        td.textContent = t; if (i === 0) td.scope = "row"; tr.appendChild(td);
      });
      const td = document.createElement("td");
      td.textContent = dtxt;
      td.className = "delta " + (good ? "good" : bad ? "bad" : "");
      tr.appendChild(td);
      tb.appendChild(tr);
    });

    // verdict in plain words
    const same = r.baseline.edges.join() === r.cool.edges.join();
    const heatCut = B.heat > 0 ? 1 - C.heat / B.heat : 0;
    const extra = C.dist / B.dist - 1;
    let text, cls = "verdict";
    if (sunNow === 0) {
      text = "There is no sun at this hour, so heat exposure is zero and both routes are the same.";
    } else if (same) {
      text = "The shortest route already fits your heat budget, so CoolRoute keeps it.";
    } else {
      text = `CoolRoute is ${f0(C.dist - B.dist)} m longer (${sign(extra)}${Math.abs(extra * 100).toFixed(1)}%) and takes ` +
        `${Math.abs((C.time - B.time) / 60).toFixed(1)} min ${C.time >= B.time ? "more" : "less"}, ` +
        `but cuts heat exposure by ${Math.round(heatCut * 100)}% by keeping to shaded streets` +
        `${B.shaded_share < C.shaded_share ? " (shaded share " + pct(B.shaded_share) + " to " + pct(C.shaded_share) + ")" : ""}.`;
    }
    verdict.textContent = text;
    verdict.className = cls;

    const addWarn = (t, kind) => {
      const li = document.createElement("li"); li.textContent = t; li.className = kind; warn.appendChild(li);
    };
    if (!r.budget_met) addWarn(`A ${state.budget}% budget cannot be met on this map. This is the coolest route available (${Math.round(heatCut * 100)}% lower heat). Raise the budget or move the points.`, "w-bad");
    if (extra > 0.2) addWarn("Large detour: the cooler route adds more than 20% distance. Consider a higher heat budget.", "w-warn");
    if (C.missing_edges > 0) addWarn(`${C.missing_edges} of ${C.n_edges} segments on the CoolRoute have missing shade data (dashed on the map). Their shade is estimated, so the heat value is approximate.`, "w-warn");
    if (B.missing_edges > 0 && !same) addWarn(`${B.missing_edges} segments on the shortest route have missing shade data.`, "w-info");
    if (state.stepFree) addWarn("Step-free is a hard rule: routes only use step-free segments, even if that makes them hotter.", "w-info");
    const closed = G.edges.filter((e) => e.closed).length;
    if (closed) addWarn(`${closed} closed footpath${closed > 1 ? "s" : ""} avoided.`, "w-info");

    drawSun();
  }

  bindControls();
  render();
})();
