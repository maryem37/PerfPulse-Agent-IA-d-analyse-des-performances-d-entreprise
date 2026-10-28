from agents.kpi import kpi
g.add_node("kpi", kpi)
g.add_edge("extract", "kpi")