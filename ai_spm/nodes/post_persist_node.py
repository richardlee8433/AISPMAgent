from __future__ import annotations

import json
from pathlib import Path

from lti_state import LTIState
from utils.vault_ops import (
    extract_title_from_draft,
    iso_now,
    lpl_index_jsonl_path,
    load_local_paths,
    next_lpl_id,
    vault_abs_path,
    VaultConfigError,
    dump_frontmatter,
)


def _build_lpl_frontmatter(state: LTIState, lpl_id: str, rel_path: str) -> dict:
    role = state.role_classification or {}
    editor = state.editor_feedback or {}

    status = "draft"
    if state.post_action == "publish_now":
        status = "published"
    elif state.post_action == "schedule":
        status = "scheduled"

    fm = {
        "type": "lpl_post",
        "lpl_id": lpl_id,
        "date_created": iso_now(),
        "date_published": None,
        "status": status,
        "channel": "linkedin",
        "language": "en",
        "title": extract_title_from_draft(state.draft_raw or ""),
        "hook": editor.get("best_one_liner") or "",
        "canonical_lti_targets": [getattr(state, "canonical_suggested_id", None)]
        if getattr(state, "canonical_suggested_id", None)
        else [],
        "rti_anchors": [],
        "agent": {
            "role_classification": {
                "primary_mainline": role.get("primary_mainline"),
                "semantic_slot": role.get("semantic_slot"),
                "is_patch": role.get("is_patch"),
                "confidence": role.get("confidence"),
            },
            "editor_recommendation": editor.get("recommendation"),
            "dedupe_verdict": (state.dedupe_payload or {}).get("verdict"),
            "best_match_lti": ((state.dedupe_payload or {}).get("best_match") or {}).get("id"),
        },
        "path": rel_path,
    }

    if state.post_action == "publish_now" and state.post_url:
        fm["date_published"] = iso_now()
        fm["links"] = {"url": state.post_url}

    return fm


def post_persist_node(state: LTIState) -> LTIState:
    if state.post_action not in {"publish_now", "schedule"}:
        state.post_result = {
            "ok": True,
            "skipped": True,
            "reason": "post_action_not_publish_or_schedule",
        }
        return state

    try:
        cfg = load_local_paths()
    except VaultConfigError as e:
        state.post_result = {"ok": False, "error": str(e)}
        return state

    lpl_id = next_lpl_id(cfg)

    yyyy = lpl_id[4:8]
    mm = lpl_id[8:10]
    lpl_dir = cfg["vault_paths"]["lpl_dir"]
    rel_path = f"{lpl_dir}/{yyyy}/{mm}/{lpl_id}.md"
    abs_path = vault_abs_path(cfg, lpl_dir, yyyy, mm, f"{lpl_id}.md")
    abs_path.parent.mkdir(parents=True, exist_ok=True)

    fm = _build_lpl_frontmatter(state, lpl_id, rel_path)
    content = dump_frontmatter(fm) + "\n" + (state.draft_raw or "").strip() + "\n"
    abs_path.write_text(content, encoding="utf-8")

    # append machine index jsonl (SSOT)
    idx_path = lpl_index_jsonl_path(cfg)
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    index_row = {
        "lpl_id": lpl_id,
        "date_created": fm["date_created"],
        "date_published": fm.get("date_published"),
        "status": fm["status"],
        "title": fm["title"],
        "canonical_lti_targets": fm["canonical_lti_targets"],
        "language": fm["language"],
        "path": rel_path,
    }
    with idx_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(index_row, ensure_ascii=False) + "\n")

    state.lpl_id = lpl_id
    state.lpl_path = rel_path
    state.post_result = {"ok": True, "written": True, "lpl_id": lpl_id, "path": str(abs_path)}
    return state
