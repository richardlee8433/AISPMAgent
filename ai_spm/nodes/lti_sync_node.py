import json
import re
from pathlib import Path
from datetime import datetime, UTC

INDEX_PATH = Path("data") / "lti_index.json"
DOCS_DIR = Path("lti_docs")

ID_RE = re.compile(r"(LTI-\d+(?:\.\d+){0,2})")

def backup_index():
    if not INDEX_PATH.exists():
        return
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup = INDEX_PATH.parent / f"lti_index.backup.{ts}.json"
    backup.write_text(INDEX_PATH.read_text(encoding="utf-8"), encoding="utf-8")

def load_index():
    if not INDEX_PATH.exists():
        return []
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))

def save_index(index):
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")

def infer_series_from_id(lti_id: str) -> str:
    # LTI-6.1 -> "LTI-6.x / (Unclassified)"
    m = re.match(r"^LTI-(\d+)", lti_id)
    if not m:
        return "LTI-?.x / (Unclassified)"
    return f"LTI-{m.group(1)}.x / (Unclassified)"

def extract_title_and_body(text: str):
    """
    Heuristic:
    - If first non-empty line starts with '#', treat as title
    - else use first sentence as title
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return "(Untitled)", ""

    first = lines[0]
    if first.startswith("#"):
        title = first.lstrip("#").strip()
        body = "\n".join(lines[1:]).strip()
        return title or "(Untitled)", body

    # no markdown title
    body = "\n".join(lines).strip()
    # title = first ~ 120 chars
    title = first[:120]
    return title, body

def naive_summary(body: str, max_sentences: int = 2) -> str:
    """
    Very simple: take first 2 sentences-ish.
    Good enough for dedupe; later you can upgrade to LLM summarizer under RTI gate.
    """
    if not body:
        return ""
    # split on ., !, ? (rough)
    parts = re.split(r"(?<=[.!?])\s+", body)
    parts = [p.strip() for p in parts if p.strip()]
    return " ".join(parts[:max_sentences])[:500]

def rule_tags(text: str):
    t = (text or "").lower()
    tags = []
    def add(tag, *keys):
        if any(k in t for k in keys):
            tags.append(tag)

    add("Accountability", "accountable", "accountability")
    add("Governance", "governance", "audit", "trace", "rollback")
    add("Evaluation", "eval", "evaluation", "regression", "benchmark")
    add("Risk Tiering", "risk", "tier", "tiered")
    add("AI PM", "product", "pm", "shipping", "release")

    # de-dup keep order
    seen = set()
    out = []
    for x in tags:
        if x not in seen:
            out.append(x); seen.add(x)
    return out

def lti_sync_node(state):
    """
    Sync index with docs:
    - For each md in lti_docs, infer id from filename
    - If missing in index, auto-create minimal metadata entry from doc
    """
    if not DOCS_DIR.exists():
        # nothing to sync; keep going
        return state

    index = load_index()
    existing_ids = { (it.get("id") or "").strip() for it in index }

    new_entries = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        m = ID_RE.search(path.name)
        if not m:
            continue
        lti_id = m.group(1).strip()
        if lti_id in existing_ids:
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        title, body = extract_title_and_body(text)
        summary = naive_summary(body, max_sentences=2)
        series = infer_series_from_id(lti_id)
        tags = rule_tags(text)

        entry = {
            "id": lti_id,
            "title": title,
            "series": series,
            "status": "active",
            "published_at": "",
            "tags": tags,
            "summary": summary,
            "doc_path": path.name,
            "aliases": [path.name],
        }
        new_entries.append(entry)
        existing_ids.add(lti_id)

    if new_entries:
        backup_index()
        index.extend(new_entries)
        # stable sort by id (rough)
        def key_fn(it):
            pid = it.get("id","")
            nums = re.findall(r"\d+", pid)
            return [int(x) for x in nums] if nums else [9999]
        index.sort(key=key_fn)
        save_index(index)

    # record what happened in state (optional)
    state.action_result = state.action_result or {}
    state.action_result["sync_added"] = [e["id"] for e in new_entries]
    state.action_result["sync_added_count"] = len(new_entries)

    if new_entries:
        print(f"\n🔄 SYNC_INDEX: added {len(new_entries)} missing entries to data/lti_index.json")
    else:
        print("\n🔄 SYNC_INDEX: index already aligned with docs")

    return state
