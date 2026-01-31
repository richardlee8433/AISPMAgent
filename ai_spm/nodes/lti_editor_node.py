# nodes/lti_editor_node.py
import os
import json
from typing import Dict, Any

from openai import OpenAI
from lti_state import LTIState

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You are the LTI Series Editor for the AI-SPM universe.

You DO NOT decide IDs, and you DO NOT dedupe.
You provide editorial judgement on:
1) Voice/style fit with the LTI canon
2) Incremental value (does it add a quotable judgement?)
3) Whether it should be published as an LTI post now
4) If not, whether it should be revised or archived to COS

You must be strict and practical. Prefer fewer, stronger LTI posts.

Return STRICT JSON only.

Output schema:
{
  "recommendation": "publish" | "publish_with_revision" | "do_not_publish",
  "confidence": 0.0-1.0,
  "voice_fit": { "score": 0-5, "notes": "short" },
  "incremental_value": { "score": 0-5, "notes": "short" },
  "redundancy_risk": { "score": 0-5, "notes": "short" },
  "editor_actions": [
    "actionable bullet 1",
    "actionable bullet 2",
    "..."
  ],
  "best_one_liner": "the one sentence a recruiter would remember (or empty if none)"
}

Guidance:
- Voice fit: LTI should feel like judgement, not tutorial documentation.
- Incremental value: must add a new lens, a sharper threshold, or a governance insight.
- Redundancy risk: consider proximity to best match and slot (if provided).
- If it's good but too long/soft, recommend publish_with_revision with specific edits.
"""

def _safe_json_load(s: str) -> Dict[str, Any] | None:
    try:
        return json.loads(s)
    except Exception:
        return None

def lti_editor_node(state: LTIState) -> LTIState:
    draft = (state.draft_raw or "").strip()
    if len(draft) < 80:
        state.editor_feedback = {"error": "Draft too short for editorial review"}
        return state

    if not os.getenv("OPENAI_API_KEY"):
        state.editor_feedback = {"status": "skipped", "reason": "OPENAI_API_KEY not set"}
        print("\n✍️ LTI_EDITOR: skipped (no OPENAI_API_KEY)")
        return state

    dedupe = state.dedupe_payload or {}
    best = dedupe.get("best_match") or {}
    verdict = dedupe.get("verdict")

    role = state.role_classification or {}
    mainline = role.get("primary_mainline")
    slot = role.get("semantic_slot")
    is_patch = role.get("is_patch")
    patch_target = role.get("patch_target")

    # Provide just enough context for editorial judgement (not too long)
    context = f"""
Context:
- Dedupe verdict: {verdict}
- Best match: {best.get('id')} | {best.get('title')}
- Classified mainline: {mainline}
- Classified slot: {slot}
- Patch intent: {is_patch} -> {patch_target}
"""

    user_prompt = f"""
{context}

Draft:
\"\"\"
{draft}
\"\"\"
"""

    try:
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
            state.editor_feedback = {"error": "Model output is not valid JSON", "raw": content[:1200]}
            print("\n⚠️ LTI_EDITOR: invalid JSON output")
            return state

        # Minimal normalization
        obj.setdefault("recommendation", "publish_with_revision")
        obj.setdefault("confidence", 0.5)
        obj.setdefault("voice_fit", {"score": 3, "notes": ""})
        obj.setdefault("incremental_value", {"score": 3, "notes": ""})
        obj.setdefault("redundancy_risk", {"score": 3, "notes": ""})
        obj.setdefault("editor_actions", [])
        obj.setdefault("best_one_liner", "")

        state.editor_feedback = obj

        print("\n✍️ LTI_EDITOR:")
        print(f"  Recommendation: {obj.get('recommendation')} (conf={float(obj.get('confidence',0.0)):.2f})")
        print(f"  Voice fit: {obj.get('voice_fit',{}).get('score')}/5 | Incremental: {obj.get('incremental_value',{}).get('score')}/5 | Redundancy: {obj.get('redundancy_risk',{}).get('score')}/5")
        if obj.get("best_one_liner"):
            print(f"  One-liner: {obj.get('best_one_liner')}")

        return state

    except Exception as e:
        state.editor_feedback = {"error": str(e)}
        print("\n⚠️ LTI_EDITOR failed:", e)
        return state
