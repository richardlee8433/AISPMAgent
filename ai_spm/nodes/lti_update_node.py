from __future__ import annotations

import json
from pathlib import Path

from lti_state import LTIState
from utils.vault_ops import (
    bump_patch_version,
    dump_frontmatter,
    iso_now,
    load_local_paths,
    parse_frontmatter,
    vault_abs_path,
    VaultConfigError,
)

INDEX_PATH = Path("data") / "lti_index.json"


def _load_index() -> list[dict]:
    if not INDEX_PATH.exists():
        return []
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def _save_index(index: list[dict]) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


def _find_entry(index: list[dict], lti_id: str) -> dict | None:
    for item in index:
        if (item.get("id") or "").strip() == lti_id:
            return item
    return None


def _compose_merge_plan(draft: str, lti_id: str) -> dict:
    lines = [ln.strip() for ln in draft.splitlines() if ln.strip()]
    return {
        "target_lti": lti_id,
        "increments": [
            "Integrate new draft arguments into canonical narrative.",
            "Preserve one-id-one-article policy while refreshing examples.",
            f"Incorporate top lines from incoming draft ({min(len(lines), 5)} key lines scanned).",
        ],
    }


def _build_lti_doc(state: LTIState, lti_id: str, existing_text: str, existing_entry: dict) -> tuple[str, dict, dict]:
    fm_old, body_old = parse_frontmatter(existing_text)
    now = iso_now()
    role = state.role_classification or {}

    old_version = fm_old.get("version") or existing_entry.get("version")
    new_version = bump_patch_version(old_version, lti_id)

    change_item = {
        "ts": now,
        "action": "merge" if state.canonical_decision == "merge_now" else "create",
        "source_run_id": state.run_id,
        "source_lpl": state.lpl_id,
        "notes": "Updated by LTI_UPDATE_NODE full-overwrite workflow.",
    }

    change_log = []
    if isinstance(fm_old.get("governance.change_log"), list):
        change_log = fm_old["governance.change_log"]

    governance = {
        "policy": "one-id-one-article",
        "change_log": [*change_log, change_item],
    }

    linked_posts = []
    if state.lpl_id:
        linked_posts.append(state.lpl_id)

    title = existing_entry.get("title") or (state.dedupe_payload or {}).get("best_match", {}).get("title") or "(Untitled)"
    if state.canonical_decision == "create_now":
        title = title if title != "(TBD from draft)" else (state.draft_raw.splitlines()[0][:140] if state.draft_raw else "(Untitled)")

    fm_new = {
        "type": "lti_canonical",
        "lti_id": lti_id,
        "mainline": role.get("primary_mainline") or existing_entry.get("mainline") or "",
        "slot": role.get("semantic_slot") or existing_entry.get("slot") or "",
        "status": "canonical",
        "title": title,
        "language": "en",
        "version": new_version,
        "last_updated": now,
        "anchors": {
            "rti": existing_entry.get("anchors", []),
            "mf": [],
        },
        "linked_posts": {
            "supporting_lpl": linked_posts,
        },
        "governance": governance,
        "summary": {
            "one_liner": (state.editor_feedback or {}).get("best_one_liner") or "",
            "abstract": "Canonical articulation updated by merge workflow.",
        },
    }

    merge_plan = _compose_merge_plan(state.draft_raw or "", lti_id)
    diff_summary = {
        "changes": [
            f"Version bumped to {new_version}",
            "Canonical markdown fully overwritten using merged content.",
            "Governance change_log appended with run metadata.",
        ]
    }

    body = (state.draft_raw or "").strip() if state.canonical_decision in {"merge_now", "create_now"} else body_old
    updated_markdown = dump_frontmatter(fm_new) + "\n" + body + "\n"
    return updated_markdown, merge_plan, diff_summary


def lti_update_node(state: LTIState) -> LTIState:
    if state.canonical_decision not in {"merge_now", "create_now"}:
        state.canonical_result = {
            "ok": True,
            "skipped": True,
            "reason": "canonical_decision_not_merge_or_create",
        }
        return state

    expected = "merge_to_existing" if state.canonical_decision == "merge_now" else "new_canonical"
    if state.canonical_action != expected:
        state.canonical_result = {
            "ok": False,
            "error": f"Invalid decision/action pair: decision={state.canonical_decision}, canonical_action={state.canonical_action}",
        }
        return state

    lti_id = state.canonical_suggested_id
    if not lti_id:
        state.canonical_result = {"ok": False, "error": "Missing canonical_suggested_id"}
        return state

    index = _load_index()
    entry = _find_entry(index, lti_id) or {
        "id": lti_id,
        "title": "(TBD from draft)",
        "series": (state.role_classification or {}).get("primary_mainline") or "",
        "status": "canonical",
        "summary": "",
        "linked_posts": [],
    }

    try:
        cfg = load_local_paths()
    except VaultConfigError as e:
        state.canonical_result = {"ok": False, "error": str(e)}
        return state

    lti_dir = cfg["vault_paths"]["lti_dir"]
    rel_doc = entry.get("path") or f"{lti_dir}/{lti_id}.md"
    filename = Path(rel_doc).name if rel_doc else f"{lti_id}.md"
    abs_doc = vault_abs_path(cfg, lti_dir, filename)
    abs_doc.parent.mkdir(parents=True, exist_ok=True)

    existing_text = abs_doc.read_text(encoding="utf-8", errors="ignore") if abs_doc.exists() else ""

    updated_markdown, merge_plan, diff_summary = _build_lti_doc(state, lti_id, existing_text, entry)
    abs_doc.write_text(updated_markdown, encoding="utf-8")

    # update machine index
    if not _find_entry(index, lti_id):
        index.append(entry)

    entry_ref = _find_entry(index, lti_id)
    assert entry_ref is not None
    entry_ref["status"] = "canonical"
    entry_ref["path"] = f"{lti_dir}/{filename}"
    entry_ref["version"] = parse_frontmatter(updated_markdown)[0].get("version")
    entry_ref["last_updated"] = parse_frontmatter(updated_markdown)[0].get("last_updated")
    entry_ref["linked_posts"] = list({*(entry_ref.get("linked_posts") or []), *([state.lpl_id] if state.lpl_id else [])})
    entry_ref["summary"] = (state.editor_feedback or {}).get("best_one_liner") or entry_ref.get("summary") or ""

    _save_index(index)

    state.merge_plan = merge_plan
    state.lti_updated_markdown = updated_markdown
    state.diff_summary = diff_summary
    state.canonical_result = {
        "ok": True,
        "updated": True,
        "id": lti_id,
        "path": str(abs_doc),
        "merge_plan": merge_plan,
        "diff_summary": diff_summary,
    }
    return state
