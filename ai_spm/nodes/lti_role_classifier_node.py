# nodes/lti_role_classifier_node.py

import os
import json
from typing import Dict, Any

from openai import OpenAI
from lti_state import LTIState

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You are an AI classification agent for the AI-SPM (AI Systems Product Management) universe.

Your job is NOT to create content.
Your job is to CLASSIFY a draft article into the canonical LTI thought universe.

GOVERNANCE:
- LTI IDs are semantic coordinates, NOT time-based.
- Classification must follow the Canonical LTI Logic strictly.
- If uncertain, choose the closest semantic role and lower confidence.

Canonical LTI Mainlines:
- LTI-1.x — Identity / Foundations (mostly historical, rarely extended)
- LTI-2.x — Industry / Trend Interpretation (event-driven)
- LTI-3.x — Build-in-Public / Product Evolution (low frequency)
- LTI-4.x — Reference / Knowledge (tool-like)
- LTI-5.x — Evaluation → Governance (CLOSED; reference-only)
- LTI-6.x — Judgement-as-a-Service (ACTIVE primary line)

LTI-6.x Semantic Slots:
- LTI-6.0 — Define judgement framework
- LTI-6.1 — Reframe accountability narrative
- LTI-6.2 — Extract judgement principles
- LTI-6.3 — Legitimize responsibility source
- LTI-6.4 — Define NO-GO threshold
- LTI-6.5 — Discuss quality / consequence cost
- LTI-6.6 — Evidence overturns judgement
- LTI-6.7 — Intentional negative decisions
- LTI-6.8 — Scale judgement capability
- LTI-6.9 — Identity lock-in / closure

Patch Rules:
- If the draft refines / operationalizes / corrects an existing judgement WITHOUT redefining it, it is a PATCH.
- Otherwise treat as a new node in its semantic slot.

OUTPUT: Return STRICT JSON ONLY (no markdown).
Schema:
{
  "primary_mainline": "LTI-1.x|LTI-2.x|LTI-3.x|LTI-4.x|LTI-5.x|LTI-6.x",
  "semantic_slot": "LTI-6.4" | null,
  "is_patch": true|false,
  "patch_target": "LTI-5.4" | null,
  "confidence": 0.0-1.0,
  "rationale": "short"
}
"""

def _safe_json_load(s: str) -> Dict[str, Any] | None:
    try:
        return json.loads(s)
    except Exception:
        return None

def lti_role_classifier_node(state: LTIState) -> LTIState:
    draft = (state.draft_raw or "").strip()
    if len(draft) < 50:
        state.role_classification = {"error": "Draft too short for semantic classification"}
        return state

    if not os.getenv("OPENAI_API_KEY"):
        state.role_classification = {"status": "skipped", "reason": "OPENAI_API_KEY not set"}
        print("\n🧠 ROLE_CLASSIFIER: skipped (no OPENAI_API_KEY)")
        return state

    best_match = (state.dedupe_payload or {}).get("best_match") or {}
    context = ""
    if best_match:
        # best_match may not have summary; keep safe
        context = f"\nClosest existing LTI:\n{best_match.get('id')} — {best_match.get('title')}\n"

    user_prompt = f"""
Draft content:
\"\"\"
{draft}
\"\"\"
{context}
"""

    try:
        # Use Chat Completions for broad SDK compatibility
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content or ""
        obj = _safe_json_load(content)

        if not obj:
            state.role_classification = {
                "error": "Model output is not valid JSON",
                "raw": content[:1000],
            }
            print("\n⚠️ ROLE_CLASSIFIER: invalid JSON output")
            return state

        # Minimal validation / normalization
        allowed_mainlines = {"LTI-1.x","LTI-2.x","LTI-3.x","LTI-4.x","LTI-5.x","LTI-6.x"}
        if obj.get("primary_mainline") not in allowed_mainlines:
            obj["primary_mainline"] = "LTI-6.x"  # conservative default
            obj["confidence"] = min(float(obj.get("confidence", 0.3)), 0.5)
            obj["rationale"] = (obj.get("rationale") or "") + " | normalized mainline"

        # Ensure keys exist
        obj.setdefault("semantic_slot", None)
        obj.setdefault("is_patch", False)
        obj.setdefault("patch_target", None)
        obj.setdefault("confidence", 0.5)
        obj.setdefault("rationale", "")

        state.role_classification = obj

        print("\n🧠 ROLE_CLASSIFIER:")
        print(f"  Mainline: {obj.get('primary_mainline')}")
        print(f"  Slot: {obj.get('semantic_slot')}")
        print(f"  Patch: {obj.get('is_patch')} → {obj.get('patch_target')}")
        try:
            print(f"  Confidence: {float(obj.get('confidence')):.2f}")
        except Exception:
            pass

        return state

    except Exception as e:
        state.role_classification = {"error": str(e)}
        print("\n⚠️ ROLE_CLASSIFIER failed:", e)
        return state
