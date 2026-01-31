# lti_graph.py
# LangGraph pipeline for LTI ingestion with:
# 1) SYNC_INDEX        (docs -> index projection, auto-fill missing metadata)
# 2) DEDUPE            (full-text + meta matching, persists runs/<run_id>/ evidence pack)
# 3) ROLE_CLASSIFIER   (OpenAI API: classify mainline + semantic slot + patch intent)
# 4) RTI-3.4 Gate      (human decision)
# 5) APPEND / COS      (actions)
#
# Run: python lti_graph.py

from langgraph.graph import StateGraph, END
from lti_state import LTIState

from nodes.lti_sync_node import lti_sync_node
from nodes.lti_dedupe_node import lti_dedupe_node
from nodes.lti_role_classifier_node import lti_role_classifier_node
from nodes.lti_gate_node import lti_gate_node
from nodes.lti_append_node import lti_append_node
from nodes.lti_cos_node import lti_cos_node
from nodes.lti_editor_node import lti_editor_node
from nodes.lti_id_mapper_node import lti_id_mapper_node


def route_after_gate(state: LTIState) -> str:
    if state.decision == "append":
        return "APPEND"
    if state.decision in ("archive", "merge"):
        return "COS"
    return "END"


graph = StateGraph(LTIState)

# Nodes
graph.add_node("SYNC_INDEX", lti_sync_node)
graph.add_node("DEDUPE", lti_dedupe_node)
graph.add_node("ROLE_CLASSIFIER", lti_role_classifier_node)
graph.add_node("EDITOR", lti_editor_node)
graph.add_node("ID_MAPPER", lti_id_mapper_node)
graph.add_node("GATE", lti_gate_node)
graph.add_node("APPEND", lti_append_node)
graph.add_node("COS", lti_cos_node)



# Wiring
graph.set_entry_point("SYNC_INDEX")
graph.add_edge("SYNC_INDEX", "DEDUPE")
graph.add_edge("DEDUPE", "ROLE_CLASSIFIER")
graph.add_edge("ROLE_CLASSIFIER", "EDITOR")
graph.add_edge("EDITOR", "ID_MAPPER")
graph.add_edge("ID_MAPPER", "GATE")

graph.add_conditional_edges(
    "GATE",
    route_after_gate,
    {
        "APPEND": "APPEND",
        "COS": "COS",
        "END": END,
    },
)

graph.add_edge("APPEND", END)
graph.add_edge("COS", END)

app = graph.compile()


if __name__ == "__main__":
    print("Paste your new LTI draft. End with a single line: /end\n")
    lines = []
    while True:
        line = input()
        if line.strip() == "/end":
            break
        lines.append(line)
    draft = "\n".join(lines).strip()

    # IMPORTANT:
    # Do NOT hardcode series_hint here; let canonical logic (ROLE_CLASSIFIER + Gate) decide.
    state = LTIState(draft_raw=draft, series_hint=None)

    # LangGraph invoke best practice: pass dict, receive dict, validate back
    result = app.invoke(state.model_dump())
    final_state = LTIState.model_validate(result)

    print("\n✅ Done.")
    print("Run id:", final_state.run_id)
    print("Verdict:", (final_state.dedupe_payload or {}).get("verdict"))
    print("Role classification:", getattr(final_state, "role_classification", None))
    print("Decision:", final_state.decision)
    print("Sync added:", (final_state.action_result or {}).get("sync_added_count", 0))
    print("Action result:", final_state.action_result)
