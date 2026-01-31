from pathlib import Path

def lti_cos_node(state):
    """
    Minimal COS: put draft into cos_drafts/ as a record.
    - archive: store as standalone draft
    - merge: store as revision for best_match id
    """
    cos_dir = Path("cos_drafts")
    cos_dir.mkdir(parents=True, exist_ok=True)

    p = state.dedupe_payload or {}
    best = (p.get("best_match") or {})
    best_id = best.get("id") or "UNKNOWN"

    if state.decision == "merge":
        out = cos_dir / f"{best_id}__revision__{state.run_id}.md"
        out.write_text(state.draft_raw, encoding="utf-8")
        state.action_result = {"ok": True, "merged_as_revision": True, "path": str(out)}
        return state

    if state.decision == "archive":
        out = cos_dir / f"draft__{state.run_id}.md"
        out.write_text(state.draft_raw, encoding="utf-8")
        state.action_result = {"ok": True, "archived": True, "path": str(out)}
        return state

    state.action_result = {"ok": True, "skipped": True, "reason": "decision_not_archive_or_merge"}
    return state
