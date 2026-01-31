from langgraph.graph import StateGraph, END
from state import UniverseState
from nodes.mf import mf_execute
from nodes.eval import evaluate
from nodes.gate import governance_gate
from nodes.lti import publish_lti
from nodes.cos import archive_cos

graph = StateGraph(UniverseState)

graph.add_node("MF", mf_execute)
graph.add_node("EVAL", evaluate)
graph.add_node("GATE", governance_gate)
graph.add_node("LTI", publish_lti)
graph.add_node("COS", archive_cos)

graph.set_entry_point("MF")
graph.add_edge("MF", "EVAL")
graph.add_edge("EVAL", "GATE")

def route(state):
    return "LTI" if state.decision == "approve" else "COS"

graph.add_conditional_edges("GATE", route)

graph.add_edge("LTI", END)
graph.add_edge("COS", END)

app = graph.compile()

if __name__ == "__main__":
    state = UniverseState(work_item="Test AI-SPM Root")
    app.invoke(state)
