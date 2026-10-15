import copy
import json
from core import build_neighbourhood, plan, sun_factor

g = build_neighbourhood()
results = []


def check(name, ok, detail=""):
    results.append({"name": name, "pass": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name, detail)


# 1 sun model: zero at night, peak near noon
check("Sun is zero at midnight", sun_factor(0) == 0)
check("Sun peaks near noon", sun_factor(12) > sun_factor(9) > sun_factor(7))

# 2 baseline is the shortest distance
r = plan(g, 0, 63, 13, 60)
check("Cool route heat <= budget", r["budget_met"],
      f"heat {r['cool']['m']['heat']:.0f} <= {r['budget']:.0f}")
check("Cool route is cooler than baseline", r["cool"]["m"]["heat"] < r["baseline"]["m"]["heat"])
check("Baseline is the shortest", r["baseline"]["m"]["dist"] <= r["cool"]["m"]["dist"] + 1e-6)

# 3 time of day: evening sun makes the heat gap shrink / vanish
r_night = plan(g, 0, 63, 22, 60)
check("At night heat is zero and routes match",
      r_night["baseline"]["m"]["heat"] == 0 and r_night["baseline"]["edges"] == r_night["cool"]["edges"])

# 4 shade availability off (e.g. trees removed / noon summer): less saving
r_noshade = plan(g, 0, 63, 13, 60, shade_on=False)
check("Without shade the baseline heat is higher",
      r_noshade["baseline"]["m"]["heat"] > r["baseline"]["m"]["heat"])

# 5 closed footpath: route must avoid it
g2 = copy.deepcopy(g)
for k in r["cool"]["edges"][:1]:
    g2["edges"][k]["closed"] = True
closed_edge = r["cool"]["edges"][0]
r2 = plan(g2, 0, 63, 13, 60)
check("Closed footpath is never used",
      closed_edge not in r2["cool"]["edges"] and closed_edge not in r2["baseline"]["edges"])

# 6 step-free hard constraint
r3 = plan(g, 0, 63, 13, 60, step_free_only=True)
if "error" in r3:
    check("Step-free: honest 'no route' answer", True, "no step-free route")
else:
    ok = all(g["edges"][k]["step_free"] for k in r3["cool"]["edges"] + r3["baseline"]["edges"])
    check("Step-free route uses only step-free edges", ok)

# 7 impossible step-free: block everything -> clear error, not a wrong route
g3 = copy.deepcopy(g)
for e in g3["edges"]:
    e["step_free"] = False
r4 = plan(g3, 0, 63, 13, 60, step_free_only=True)
check("No step-free route -> error returned", r4.get("error") == "no_route")

# 8 impossible budget (5%) -> coolest route returned and flagged
r5 = plan(g, 0, 63, 13, 5)
check("Impossible budget is flagged (budget_met False)", r5["budget_met"] is False)

# 9 missing data is reported
low = sum(1 for e in g["edges"] if e["confidence"] < 0.3)
check("Missing-data edges exist in the map and are counted", low > 0, f"{low} low-confidence edges")

# 10 budget 100% gives the baseline
r6 = plan(g, 0, 63, 13, 100)
check("Budget 100% returns the baseline route", r6["baseline"]["edges"] == r6["cool"]["edges"])

json.dump(results, open("test_results.json", "w"), indent=1)
print(f"\n{sum(x['pass'] for x in results)}/{len(results)} tests passed")
