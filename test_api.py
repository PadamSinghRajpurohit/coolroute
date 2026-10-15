import json, urllib.request, urllib.error
BASE = "http://127.0.0.1:8765/api/v1"
def call(path, body=None):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
res, samples = [], {}
def check(name, ok, detail=""):
    res.append({"name": name, "pass": bool(ok), "detail": detail}); print(("PASS " if ok else "FAIL "), name, detail)

s, d = call("/health"); check("GET /health returns ok", s == 200 and d["status"] == "ok"); samples["health"] = d
s, d = call("/sun?hour=13"); check("GET /sun at 13:00 is about 0.77", s == 200 and abs(d["sun_strength"] - 0.7739) < 1e-3); samples["sun"] = d
s, d = call("/sun?hour=99"); check("GET /sun rejects hour 99 with 400", s == 400)
req = {"origin": {"node": 0}, "destination": {"node": 63}, "hour": 13, "heat_budget_pct": 60, "step_free": False, "shade_available": True, "closed_edge_ids": []}
s, d = call("/route", req); check("POST /route returns two routes", s == 200 and d["budget_met"] and d["coolroute"]["heat_exposure"] < d["baseline"]["heat_exposure"], d.get("explanation", ""))
samples["route_request"] = req; samples["route_response"] = d
s2, d2 = call("/route", {**req, "origin": {"x": 5, "y": 3}, "destination": {"x": 555, "y": 560}}); check("Coordinates snap to nearest nodes", s2 == 200 and d2["coolroute"]["nodes"] == d["coolroute"]["nodes"])
s, d3 = call("/route", {**req, "step_free": True}); check("step_free request works or says NO_ROUTE", s in (200, 404)); samples["stepfree"] = d3
s, d4 = call("/route", {**req, "heat_budget_pct": 10}); check("Impossible budget returns warning BUDGET_NOT_MET", s == 200 and any(w["code"] == "BUDGET_NOT_MET" for w in d4["warnings"])); samples["budget_fail"] = d4
s, d5 = call("/route", {**req, "hour": 22}); check("Night time: no sun, equal routes", s == 200 and d5["baseline"]["heat_exposure"] == 0)
s, d6 = call("/route", {**req, "origin": {"node": 999}}); check("Bad node id returns 400", s == 400); samples["bad_input"] = d6
s, d7 = call("/route", {**req, "closed_edge_ids": [10**6]}); check("Bad closed edge id returns 400", s == 400)
s, d8 = call("/route", {"origin": {"node": 0}}); check("Missing destination returns 400", s == 400)
# closing every edge around node 0 -> 404 NO_ROUTE
g = call("/graph")[1]
around = [e["id"] for e in g["edges"] if e["a"] == 0 or e["b"] == 0]
s, d9 = call("/route", {**req, "closed_edge_ids": around}); check("All exits closed returns 404 NO_ROUTE", s == 404 and d9["error"]["code"] == "NO_ROUTE"); samples["no_route"] = d9
json.dump(res, open("api_test_results.json", "w"), indent=1); json.dump(samples, open("api_samples.json", "w"), indent=1)
print(sum(r["pass"] for r in res), "/", len(res), "API checks passed")
