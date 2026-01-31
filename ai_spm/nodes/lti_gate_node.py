# nodes/lti_gate_node.py
# RTI-3.4 Governance Gate (human-in-the-loop)
#
# Shows evidence from:
# - DEDUPE (verdict, best match, numeric suggested id fallback)
# - ROLE_CLASSIFIER (mainline/slot/patch intent)
# - LTI_EDITOR (publish / revision / do_not_publish)
# - ID_MAPPER (canonical_action + canonical_suggested_id)  <-- preferred
#
# Then asks the user to decide:
#   [a] append to index (only meaningful if verdict=NEW and canonical_action=new_canonical)
#   [c] archive to COS (store as draft/revision)
#   [m] merge (treat as revision of existing canonical)
#   [h] hold (do nothing)

from __future__ import annotations

from typing import Optional, Set

from lti_state import LTIState


def _prompt_choice(prompt: str, valid: Set[str], default: Optional[str] = None) -> str:
    while True:
        s = input(prompt).strip().lower()
        if not s and default:
            return default
        if s in valid:
            return s
        print(f"Invalid choice. Choose one of: {', '.join(sorted(valid))}")


def lti_gate_node(state: LTIState) -> LTIState:
    dedupe = state.dedupe_payload or {}
    verdict = dedupe.get("verdict", "UNKNOWN")
    best = dedupe.get("best_match") or {}
    numeric_suggested_id = dedupe.get("suggested_new_id") or dedupe.get("numeric_suggested_id")

    # Role classifier
    role = state.role_classification or {}
    mainline = role.get("primary_mainline")
    slot = role.get("semantic_slot")
    is_patch = role.get("is_patch")
    patch_target = role.get("patch_target")
    role_conf = role.get("confidence")
    role_rationale = role.get("rationale")

    # Editor feedback
    editor = state.editor_feedback or {}

    # Canonical mapping (ID_MAPPER)
    canonical_id = getattr(state, "canonical_suggested_id", None)
    canonical_action = getattr(state, "canonical_action", None)

    print("\n🛑 RTI-3.4 LTI Gate")
    print(f"Verdict: {verdict}")
    if best:
        print(f"Best match: {best.get('id')} | {best.get('title')}")
    else:
        print("Best match: (none)")

    # Numeric fallback (deprecated after ID_MAPPER)
    if numeric_suggested_id:
        print(f"Numeric suggested id (fallback): {numeric_suggested_id}")

    # ROLE_CLASSIFIER block
    if role:
        print("\n🧠 Role Classification")
        if mainline:
            print(f"- mainline: {mainline}")
        if slot:
            print(f"- slot: {slot}")
        print(f"- patch_intent: {bool(is_patch)} → {patch_target}")
        if role_conf is not None:
            try:
                print(f"- confidence: {float(role_conf):.2f}")
            except Exception:
                print(f"- confidence: {role_conf}")
        if role_rationale:
            print(f"- rationale: {role_rationale}")

    # EDITOR block
    if editor:
        print("\n✍️ Editor Recommendation")
        print(f"- recommendation: {editor.get('recommendation')}")
        econf = editor.get("confidence")
        if econf is not None:
            try:
                print(f"- confidence: {float(econf):.2f}")
            except Exception:
                print(f"- confidence: {econf}")

        vf = editor.get("voice_fit", {}) or {}
        iv = editor.get("incremental_value", {}) or {}
        rr = editor.get("redundancy_risk", {}) or {}

        if vf:
            print(f"- voice_fit: {vf.get('score')}/5 | {vf.get('notes')}")
        if iv:
            print(f"- incremental_value: {iv.get('score')}/5 | {iv.get('notes')}")
        if rr:
            print(f"- redundancy_risk: {rr.get('score')}/5 | {rr.get('notes')}")

        one_liner = editor.get("best_one_liner")
        if one_liner:
            print(f"- one_liner: {one_liner}")

        actions = editor.get("editor_actions") or []
        if actions:
            print("- actions:")
            for a in actions[:6]:
                print(f"  - {a}")

    # ID_MAPPER block (preferred)
    if canonical_id or canonical_action:
        print("\n🧭 Canonical Mapping")
        print(f"- canonical_suggested_id: {canonical_id}")
        print(f"- canonical_action: {canonical_action}")
        if canonical_action == "merge_to_existing":
            print("  → Slot already has a canonical article. Recommended: [m] merge (or [c] archive for later merge).")
        elif canonical_action == "new_canonical":
            print("  → No canonical exists for this slot. Recommended: [a] append (after revision if needed).")
        elif canonical_action == "archive_only":
            print("  → Not recommended as canonical. Recommended: [c] archive.")

    print("\nDecisions:")
    print("  [a] append to index (only meaningful if verdict=NEW and canonical_action=new_canonical)")
    print("  [c] archive to COS (store as draft/revision)")
    print("  [m] merge (treat as revision of best match / canonical)")
    print("  [h] hold (do nothing)\n")

    choice = _prompt_choice("Decision: ", {"a", "c", "m", "h"})

    if choice == "a":
        state.decision = "append"
    elif choice == "c":
        state.decision = "archive"
    elif choice == "m":
        state.decision = "merge"
    else:
        state.decision = "hold"

    reason = input("Reason (short): ").strip()
    state.decision_reason = reason

    print(f"\nDecision: {state.decision}")
    if reason:
        print(f"Reason: {reason}")

    return state
