import json
t = open("template.html").read()
core = open("core.js").read()
app = open("app.js").read()
graph = open("graph.json").read()
t = t.replace("/*CORE*/", core).replace("/*GRAPH*/", graph).replace("/*APP*/", app)
open("coolroute.html", "w").write(t)
print("built", len(t), "bytes")
