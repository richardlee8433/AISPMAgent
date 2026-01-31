import json
from pathlib import Path

INDEX_PATH = Path("data") / "lti_index.json"

def lti_append_node(state):
    p = state.dedupe_payload or {}
    verdict = p.get("verdict")
    new_id = p.get("suggested_new_id")

    if state.decision != "append":
        state.action_result = {"ok": True, "skipped": True, "reason": "decision_not_append"}
        return state

    if verdict != "NEW":
        state.action_result = {"ok": False, "error": f"Cannot append when verdict={verdict}. Use merge/archive instead."}
        return state

    if not new_id:
        state.action_result = {"ok": False, "error": "No suggested_new_id. Provide series_hint or ensure index has series."}
        return state

    index = json.loads(INDEX_PATH.read_text(encoding="utf-8")) if INDEX_PATH.exists() else []
    existing_ids = {it.get("id") for it in index}
    if new_id in existing_ids:
        state.action_result = {"ok": False, "error": f"ID already exists: {new_id}"}
        return state

    # Minimal entry template; you can refine later
    entry = {
        "id": new_id,
        "title": "(TBD from draft)",
        "series": (state.series_hint or (p.get("best_match") or {}).get("series") or "LTI-6.x / Judgement-as-a-Service"),
        "status": "active",
        "published_at": "",
        "tags": [],
        "summary": ""
    }

    index.append(entry)
    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")

    state.action_result = {"ok": True, "appended": True, "id": new_id}
    return state
