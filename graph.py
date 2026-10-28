from typing import TypedDict, Any
from langgraph.graph import StateGraph, END

from agents.extract import extract
from agents.kpi import kpi
from agents.detect import detect
from agents.analyse import analyse
from agents.write import write
from agents.validate import validate
from agents.report import report


class State(TypedDict, total=False):
    pbix_path: str
    tables: Any; mesures_dax: Any; kpi: Any; alertes: list; faits: list
    faits_groupes: list; textes: list; synthese: str
    ok: bool; essais: int; validation: list; report: dict
    groq_unavailable: bool; groq_fallback_used: bool


g = StateGraph(State)
g.add_node("extract", extract)
g.add_node("kpi", kpi)
g.add_node("detect", detect)
g.add_node("analyse", analyse)
g.add_node("write", write)
g.add_node("validate", validate)
g.add_node("report", report)

g.set_entry_point("extract")
g.add_edge("extract", "kpi")
g.add_edge("kpi", "detect")
g.add_edge("detect", "analyse")
g.add_edge("analyse", "write")
g.add_edge("write", "validate")
g.add_conditional_edges(
    "validate",
    lambda s: "report" if s["ok"] else "write",
    {"report": "report", "write": "write"},
)
g.add_edge("report", END)

app = g.compile()
