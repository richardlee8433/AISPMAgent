import json
from pathlib import Path
from datetime import datetime, UTC
from rapidfuzz import fuzz
import re
from typing import Iterable

INDEX_PATH = Path("data") / "lti_index.json"
DOCS_DIR = Path("lti_docs")
RUNS_DIR = Path("runs")

# -------------------------
# Helpers: IO
# -------------------------

def load_index():
    if not INDEX_PATH.exists():
        return []
    try:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"Index JSON is invalid: {INDEX_PATH}")
        return []


def _extract_frontmatter_id(text: str) -> str | None:
    """
    Parse a minimal YAML-frontmatter id field.
    Expected shape:
    ---
    id: LTI-6.1
    ---
    """
    if not text.startswith("---"):
        return None

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    for line in lines[1:]:
        if line.strip() == "---":
            return None
        m = re.match(r"^id\s*:\s*(.+)$", line.strip(), flags=re.IGNORECASE)
        if m:
            return m.group(1).strip().strip("\"'")
    return None


def _path_candidates_from_index(item: dict) -> Iterable[Path]:
    doc_path = (item.get("doc_path") or "").strip()
    if doc_path:
        p = Path(doc_path)
        yield p if p.is_absolute() else DOCS_DIR / p

    for alias in item.get("aliases") or []:
        alias = (alias or "").strip()
        if not alias:
            continue
        p = Path(alias)
        yield p if p.is_absolute() else DOCS_DIR / p


def _find_doc_path_by_frontmatter_id(lti_id: str) -> Path | None:
    if not DOCS_DIR.exists():
        return None

    for path in sorted(DOCS_DIR.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if (_extract_frontmatter_id(text) or "").strip() == lti_id:
            return path
    return None

def read_doc_text(lti_id: str, item: dict | None = None) -> str | None:
    """
    ID-first doc resolution (not filename-locked):
    1) index mapped path: item.doc_path / item.aliases
    2) exact: lti_docs/<id>.md
    3) tolerant: any file starting with "<id>" (e.g., "LTI-6.1 — title.md")
    4) frontmatter fallback: find file with YAML id: <id>
    """
    if not DOCS_DIR.exists():
        return None

    for p in _path_candidates_from_index(item or {}):
        if p.exists():
            return p.read_text(encoding="utf-8", errors="ignore")

    exact = DOCS_DIR / f"{lti_id}.md"
    if exact.exists():
        return exact.read_text(encoding="utf-8", errors="ignore")

    candidates = sorted(DOCS_DIR.glob(f"{lti_id}*.md"))
    if candidates:
        return candidates[0].read_text(encoding="utf-8", errors="ignore")

    fm_match = _find_doc_path_by_frontmatter_id(lti_id)
    if fm_match:
        return fm_match.read_text(encoding="utf-8", errors="ignore")

    return None

def ensure_dirs():
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

def run_id_now() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

def persist_run(run_id: str, payload: dict, draft_raw: str):
    """
    runs/<run_id>/
      - input_draft.md
      - result.json (verdict + top matches + config)
    """
    ensure_dirs()
    out_dir = RUNS_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "input_draft.md").write_text(draft_raw, encoding="utf-8")
    (out_dir / "result.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\n💾 Persisted run artifacts to: {out_dir.resolve()}")

# -------------------------
# Helpers: scoring
# -------------------------

def normalize_input(text: str) -> str:
    return " ".join(text.split())

def meta_text(item: dict) -> str:
    title = item.get("title", "")
    summary = item.get("summary", "")
    tags = " ".join(item.get("tags", []))
    series = item.get("series", "")
    return "\n".join([title, summary, tags, series]).strip()

def score_full(draft: str, fulltext: str) -> float:
    return float(fuzz.token_set_ratio(draft, fulltext)) / 100.0

def score_meta(draft: str, item: dict) -> float:
    return float(fuzz.token_set_ratio(draft, meta_text(item))) / 100.0

def score_title_hit(draft: str, title: str) -> float:
    title = (title or "").strip()
    if not title:
        return 0.0
    return float(fuzz.token_set_ratio(draft, title)) / 100.0

def combined_score(full_score: float | None, meta_score: float, title_hit: float) -> float:
    if full_score is not None:
        return 0.65 * full_score + 0.20 * meta_score + 0.15 * title_hit
    return 0.75 * meta_score + 0.25 * title_hit

def classify(best_score: float, best_title_hit: float) -> str:
    # Hard rule: near-exact title hit => DUPLICATE
    if best_title_hit >= 0.92:
        return "DUPLICATE"
    if best_score >= 0.82:
        return "DUPLICATE"
    if best_score >= 0.62:
        return "OVERLAP"
    return "NEW"

# -------------------------
# Helpers: next ID suggestion
# -------------------------

_ID_RE = re.compile(r"^LTI-(\d+)(?:\.(\d+))?(?:\.(\d+))?$")

def parse_lti_id(lti_id: str):
    m = _ID_RE.match((lti_id or "").strip())
    if not m:
        return None
    major = int(m.group(1))
    minor = int(m.group(2)) if m.group(2) is not None else None
    patch = int(m.group(3)) if m.group(3) is not None else None
    return major, minor, patch


def next_id_for_series(index: list[dict], series: str) -> str:
    """
    Suggest next id within a series, based on max minor for that major.
    If series is LTI-6.x / ..., we infer major=6.
    We avoid collisions with existing IDs.

    NOTE:
    - Supports ids like LTI-5.4.1 (patch) by parsing 3 parts.
    - Patch is ignored for "next minor" suggestion, because this function
      only proposes new nodes (major.minor). Patch IDs are handled elsewhere.
    """
    # infer major from series string like "LTI-6.x / ..."
    major = None
    m = re.search(r"LTI-(\d+)\.x", series or "")
    if m:
        major = int(m.group(1))

    existing = set((it.get("id") or "").strip() for it in index)

    # If major inferred, find max minor within that major
    if major is not None:
        max_minor = 0
        for it in index:
            pid = parse_lti_id(it.get("id", ""))
            if not pid:
                continue
            maj, minor, patch = pid
            if maj == major and minor is not None:
                max_minor = max(max_minor, minor)

        # propose next minor
        cand_minor = max_minor + 1
        cand = f"LTI-{major}.{cand_minor}"
        while cand in existing:
            cand_minor += 1
            cand = f"LTI-{major}.{cand_minor}"
        return cand

    # fallback: if cannot infer major, propose next overall major.minor by scanning
    # (not perfect, but safe)
    max_major = 0
    max_minor_for_max_major = 0
    for it in index:
        pid = parse_lti_id(it.get("id", ""))
        if not pid:
            continue
        maj, minor, patch = pid
        if maj > max_major:
            max_major = maj
            max_minor_for_max_major = minor or 0
        elif maj == max_major and minor is not None:
            max_minor_for_max_major = max(max_minor_for_max_major, minor)

    # propose within max_major
    cand = f"LTI-{max_major}.{max_minor_for_max_major + 1}"
    i = 1
    while cand in existing:
        i += 1
        cand = f"LTI-{max_major}.{max_minor_for_max_major + i}"
    return cand


# -------------------------
# Main
# -------------------------

def main():
    index = load_index()
    if not index:
        print("Index is empty. Add entries to data/lti_index.json first.")
        return

    print("Paste your new LTI draft. End with a single line: /end\n")
    lines = []
    while True:
        line = input()
        if line.strip() == "/end":
            break
        lines.append(line)
    draft_raw = "\n".join(lines).strip()
    if not draft_raw:
        print("No input.")
        return

    run_id = run_id_now()
    draft = normalize_input(draft_raw)

    scored = []
    for item in index:
        lti_id = (item.get("id") or "").strip()
        title = item.get("title", "")

        full = read_doc_text(lti_id, item)
        f_score = score_full(draft, normalize_input(full)) if full else None
        m_score = score_meta(draft, item)
        t_hit = score_title_hit(draft, title)
        c_score = combined_score(f_score, m_score, t_hit)

        scored.append({
            "id": lti_id,
            "title": title,
            "series": item.get("series", ""),
            "status": item.get("status", ""),
            "published_at": item.get("published_at", ""),
            "combined": c_score,
            "full_score": f_score,
            "meta_score": m_score,
            "title_hit": t_hit,
            "has_fulltext": bool(full),
        })

    scored.sort(key=lambda x: x["combined"], reverse=True)
    top = scored[:5]
    best = top[0] if top else {"combined": 0.0, "title_hit": 0.0}

    verdict = classify(best["combined"], best["title_hit"])

    print("\n=== LTI Index Similarity Check (Full-text Mode A | v0.2) ===")
    print(f"Verdict: {verdict}  |  best_score={best['combined']:.2f}  |  title_hit={best['title_hit']:.2f}\n")

    for x in top:
        fs = "N/A" if x["full_score"] is None else f"{x['full_score']:.2f}"
        ms = f"{x['meta_score']:.2f}"
        th = f"{x['title_hit']:.2f}"
        ft = "yes" if x["has_fulltext"] else "no"
        print(f"- {x['id']} | {x['title']} | combined={x['combined']:.2f} | full={fs} | meta={ms} | title_hit={th} | fulltext={ft}")

    suggestion = ""
    next_id = None
    if verdict == "DUPLICATE":
        suggestion = "Treat as DUPLICATE. Merge/update the existing entry (or store as revision in COS)."
    elif verdict == "OVERLAP":
        suggestion = "OVERLAP. Either sharpen differentiator to create a new node, or attach as a sub-entry to the closest node."
    else:
        series = best.get("series") or "LTI-6.x / Judgement-as-a-Service"
        next_id = next_id_for_series(index, series)
        suggestion = f"NEW. Create a new LTI entry (suggested id: {next_id}) and append to the index."

    print(f"\nSuggestion: {suggestion}")
    print("\nTip: Prefer index doc_path / aliases or frontmatter id: LTI-x.y. Filename is now only a fallback.")

    payload = {
        "run_id": run_id,
        "verdict": verdict,
        "best_score": round(float(best["combined"]), 4),
        "best_title_hit": round(float(best["title_hit"]), 4),
        "best_match": {
            "id": best.get("id"),
            "title": best.get("title"),
            "series": best.get("series"),
        },
        "top_matches": [
            {
                "id": x["id"],
                "title": x["title"],
                "combined": round(float(x["combined"]), 4),
                "full_score": None if x["full_score"] is None else round(float(x["full_score"]), 4),
                "meta_score": round(float(x["meta_score"]), 4),
                "title_hit": round(float(x["title_hit"]), 4),
                "fulltext": x["has_fulltext"],
            }
            for x in top
        ],
        "suggested_new_id": next_id,
        "config": {
            "mode": "Full-text Mode A",
            "index_path": str(INDEX_PATH),
            "docs_dir": str(DOCS_DIR),
            "thresholds": {
                "duplicate_title_hit": 0.92,
                "duplicate_score": 0.82,
                "overlap_score": 0.62
            }
        }
    }

    persist_run(run_id, payload, draft_raw)

if __name__ == "__main__":
    main()
