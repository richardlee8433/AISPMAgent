from __future__ import annotations

from typing import Dict, Any
import lti_dedupe as d2  # your existing script (safe to import)

def lti_dedupe_node(state: "LTIState") -> "LTIState":
    """
    Runs full-text dedupe using your lti_dedupe_v0_2 logic,
    and stores the resulting payload back into state.
    Also persists to runs/<run_id>/ via d2.persist_run().
    """
    index = d2.load_index()
    if not index:
        raise RuntimeError("Index is empty. Add entries to data/lti_index.json first.")

    draft_raw = (state.draft_raw or "").strip()
    if not draft_raw:
        raise RuntimeError("No draft_raw provided.")

    draft = d2.normalize_input(draft_raw)

    scored = []
    for item in index:
        lti_id = (item.get("id") or "").strip()
        title = item.get("title", "")

        full = d2.read_doc_text(lti_id, item)  # ID-first match via index map, then filename fallback
        f_score = d2.score_full(draft, d2.normalize_input(full)) if full else None
        m_score = d2.score_meta(draft, item)
        t_hit = d2.score_title_hit(draft, title)
        c_score = d2.combined_score(f_score, m_score, t_hit)

        scored.append({
            "id": lti_id,
            "title": title,
            "series": item.get("series", ""),
            "combined": c_score,
            "full_score": f_score,
            "meta_score": m_score,
            "title_hit": t_hit,
            "has_fulltext": bool(full),
        })

    scored.sort(key=lambda x: x["combined"], reverse=True)
    top = scored[:5]
    best = top[0] if top else {"combined": 0.0, "title_hit": 0.0, "id": None, "title": None, "series": None}

    verdict = d2.classify(best["combined"], best["title_hit"])

    suggested_new_id = None
    if verdict == "NEW":
        series = state.series_hint or best.get("series") or "LTI-6.x / Judgement-as-a-Service"
        suggested_new_id = d2.next_id_for_series(index, series)

    payload: Dict[str, Any] = {
        "run_id": state.run_id,
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
        "suggested_new_id": suggested_new_id,
        "config": {
            "mode": "Full-text Mode A | LangGraph Node",
            "docs_dir": str(d2.DOCS_DIR),
            "index_path": str(d2.INDEX_PATH),
            "thresholds": {
                "duplicate_title_hit": 0.92,
                "duplicate_score": 0.82,
                "overlap_score": 0.62
            }
        }
    }

    # Persist as evidence pack
    d2.persist_run(state.run_id, payload, draft_raw)

    # Store in state for downstream Gate/Actions
    payload["index_ids"] = [it.get("id") for it in index if it.get("id")]
    state.dedupe_payload = payload
    return state

