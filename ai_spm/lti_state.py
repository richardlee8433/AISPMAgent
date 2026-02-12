from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime, UTC

def _run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

class LTIState(BaseModel):
    # Input
    draft_raw: str
    series_hint: Optional[str] = None

    # Run / evidence
    run_id: str = Field(default_factory=_run_id)
    dedupe_payload: Optional[Dict[str, Any]] = None  # persisted to runs/

    # NEW: role classification (OpenAI)
    role_classification: Optional[Dict[str, Any]] = None
    
    # Canonical mapping (ID_MAPPER)
    canonical_suggested_id: Optional[str] = None
    canonical_action: Optional[str] = None  # "new_canonical" | "merge_to_existing" | "archive_only"

    
    # NEW: editor feedback (Series Editor)
    editor_feedback: Optional[Dict[str, Any]] = None

    # Governance decision (RTI-3.4)
    decision: Optional[Literal["append", "archive", "merge", "hold"]] = None
    decision_reason: Optional[str] = None

    # Two-step gate decisions (LPL / LTI split)
    post_action: Optional[Literal["publish_now", "schedule", "do_not_publish", "hold"]] = None
    canonical_decision: Optional[Literal["merge_now", "create_now", "update_later", "no_change"]] = None
    post_url: Optional[str] = None

    # Outcome
    action_result: Optional[Dict[str, Any]] = None
    post_result: Optional[Dict[str, Any]] = None
    canonical_result: Optional[Dict[str, Any]] = None

    # Generated artifacts
    lpl_id: Optional[str] = None
    lpl_path: Optional[str] = None
    merge_plan: Optional[Dict[str, Any]] = None
    lti_updated_markdown: Optional[str] = None
    diff_summary: Optional[Dict[str, Any]] = None
