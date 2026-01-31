# nodes/lti_id_mapper_node.py
from __future__ import annotations
from typing import Optional
from lti_state import LTIState

def lti_id_mapper_node(state: LTIState) -> LTIState:
    """
    Canonical ID Mapper
    Policy: One ID, One Canonical Article.

    Maps semantic_slot -> canonical_action + canonical_suggested_id
    """

    role = state.role_classification or {}
    slot: Optional[str] = role.get("semantic_slot")
    is_patch = bool(role.get("is_patch"))
    patch_target: Optional[str] = role.get("patch_target")

    editor = state.editor_feedback or {}
    editor_rec = editor.get("recommendation")

    dedupe = state.dedupe_payload or {}
    index_ids = set(dedupe.get("index_ids") or [])
    best = dedupe.get("best_match") or {}

    # defaults
    state.canonical_suggested_id = None
    state.canonical_action = "archive_only"

    # If editor says do_not_publish, never create canonical
    if editor_rec == "do_not_publish":
        state.canonical_action = "archive_only"
        return state

    # If no slot, we cannot map canonically
    if not slot:
        state.canonical_action = "archive_only"
        return state

    # Check existence of the slot as canonical ID
    slot_exists = False
    if index_ids:
        slot_exists = slot in index_ids
    else:
        # fallback inference
        slot_exists = (best.get("id") == slot)

    if slot_exists:
        # Single-canonical policy: must merge/upgrade existing
        state.canonical_suggested_id = slot
        state.canonical_action = "merge_to_existing"
        return state

    # Patch intent also implies merge (even if target exists)
    if is_patch and patch_target:
        state.canonical_suggested_id = patch_target
        state.canonical_action = "merge_to_existing"
        return state

    # Otherwise: create a new canonical occupying the slot itself
    state.canonical_suggested_id = slot
    state.canonical_action = "new_canonical"
    return state
