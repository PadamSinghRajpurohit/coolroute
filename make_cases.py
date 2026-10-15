import json, random, copy
from core import build_neighbourhood, plan
g0 = build_neighbourhood()
rnd = random.Random(1)
cases = []
for _ in range(60):
    src, dst = rnd.sample(range(64), 2)
    c = {"src": src, "dst": dst, "hour": rnd.choice([7, 10, 13, 15.5, 17.5, 22]),
         "budget": rnd.choice([30, 50, 60, 80, 100]), "stepfree": rnd.random() < 0.3,
         "shade": rnd.random() < 0.8, "closed": rnd.sample(range(len(g0["edges"])), rnd.choice([0, 0, 3, 8]))}
    g = copy.deepcopy(g0)
    for k in c["closed"]:
        g["edges"][k]["closed"] = True
    r = plan(g, src, dst, c["hour"], c["budget"], c["stepfree"], c["shade"])
    if "error" in r:
        c["err"] = True
    else:
        c["cool_edges"] = r["cool"]["edges"]; c["base_edges"] = r["baseline"]["edges"]; c["cool_heat"] = r["cool"]["m"]["heat"]
    cases.append(c)
json.dump(cases, open("py_cases.json", "w"))
print(len(cases), "cases,", sum(1 for c in cases if c.get("err")), "no-route")
