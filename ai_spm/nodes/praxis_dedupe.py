"""
PRAXIS concept-layer dedup (Step 2 of upgraded dedup pipeline).

Matches a draft against 06_Concepts/ knowledge graph, identifies which
Key Insights are addressed, then checks LPL coverage per insight.

Returns:
  {
    "concept_match": ["concept name", ...],
    "insight_coverage": [
      {
        "concept": str,
        "insight": str,
        "draft_addresses": bool,
        "status": "COVERED|PARTIAL|NEW",
        "matched_lpl": {"lpl_id": ..., "title": ...} | null,
        "coverage_reason": str
      }
    ],
    "verdict": "NEW|PATCH|COVERED",
    "reason": str,
    "praxis_available": bool
  }
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# How well a concept name/alias must fuzzy-match the draft to be considered relevant.
# partial_ratio on a short term vs long text — 55 is intentionally loose; the LLM
# does the precise filtering in step 2.
_CONCEPT_MATCH_THRESHOLD = 55


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _get_paths() -> dict:
    _here = Path(__file__).parent           # nodes/
    _ai_spm_root = _here.parent             # ai_spm/
    _pmos_root = _ai_spm_root / "pmos"

    lpl_index = _pmos_root / "data" / "lpl_index.jsonl"
    concepts_dir: Optional[Path] = None

    config_path = _ai_spm_root / "config" / "local_paths.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            vault_root = config.get("obsidian_vault_root", "")
            if vault_root:
                concepts_dir = Path(vault_root) / "06_Concepts"
                # Prefer AgentData lpl_index if it exists
                agent_data = config.get("vault_paths", {}).get("agent_data_dir", "")
                if agent_data:
                    candidate = Path(vault_root) / agent_data / "lpl_index.jsonl"
                    if candidate.exists():
                        lpl_index = candidate
        except Exception:
            pass

    return {"concepts_dir": concepts_dir, "lpl_index": lpl_index}


# ---------------------------------------------------------------------------
# Concept page parsing
# ---------------------------------------------------------------------------

def _parse_concept_page(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None

    result: dict = {"concept": None, "aliases": [], "insights": [], "file": path.name}

    # Frontmatter
    if text.startswith("---"):
        lines = text.splitlines()
        end = None
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                end = i
                break
        if end:
            for line in lines[1:end]:
                m = re.match(r"^concept:\s*(.+)$", line.strip())
                if m:
                    result["concept"] = m.group(1).strip()
                m = re.match(r"^aliases:\s*\[(.+)\]$", line.strip())
                if m:
                    result["aliases"] = [
                        a.strip().strip("\"'") for a in m.group(1).split(",") if a.strip()
                    ]

    # Key Insights section
    in_insights = False
    for line in text.splitlines():
        if "### Key Insights" in line:
            in_insights = True
            continue
        if in_insights:
            if line.strip().startswith("###"):
                break
            stripped = line.strip()
            if stripped.startswith("- "):
                # Strip [[wiki-link]] references
                insight = re.sub(r"\s*—\s*\[\[.*?\]\]", "", stripped[2:]).strip()
                if insight:
                    result["insights"].append(insight)

    if not result["concept"]:
        return None
    return result


def _load_concepts(concepts_dir: Path) -> list[dict]:
    if not concepts_dir or not concepts_dir.exists():
        return []
    concepts = []
    for p in sorted(concepts_dir.glob("*.md")):
        if p.stem.startswith("_"):
            continue
        c = _parse_concept_page(p)
        if c:
            concepts.append(c)
    return concepts


# ---------------------------------------------------------------------------
# Concept matching (fuzzy, terminology layer)
# ---------------------------------------------------------------------------

def _match_concepts(draft: str, concepts: list[dict]) -> list[dict]:
    """
    Return concepts whose name or any alias has a fuzzy partial match in the draft.
    Uses partial_ratio so short terms can match inside the longer draft text.
    """
    matched = []
    draft_lower = draft.lower()
    for c in concepts:
        terms = ([c["concept"]] + c["aliases"])
        best = max(
            (fuzz.partial_ratio(draft_lower, t.lower()) for t in terms if t),
            default=0,
        )
        if best >= _CONCEPT_MATCH_THRESHOLD:
            matched.append({**c, "_match_score": best})
    matched.sort(key=lambda x: x["_match_score"], reverse=True)
    return matched


# ---------------------------------------------------------------------------
# LPL index loader
# ---------------------------------------------------------------------------

def _load_lpl_posts(lpl_index: Path) -> list[dict]:
    posts = []
    if not lpl_index.exists():
        return posts
    with open(lpl_index, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    post = json.loads(line)
                    if post.get("status") == "published":
                        posts.append(post)
                except json.JSONDecodeError:
                    continue
    return posts


# ---------------------------------------------------------------------------
# LLM prompt
# ---------------------------------------------------------------------------

_PRAXIS_PROMPT = """\
You are analyzing a LinkedIn article draft against a PRAXIS knowledge graph.

## Task
1. For each matched concept below, identify which Key Insights the draft actually addresses.
2. For each addressed insight, check whether an existing LPL post already covers it.
3. Return a structured JSON verdict.

## Draft
{draft}

## Matched Concepts (up to 3)
{concepts_block}

## Published LPL Posts (title + hook)
{lpl_block}

## Output (JSON only, no markdown wrapper)
{{
  "concept_match": ["concept name 1", ...],
  "insight_coverage": [
    {{
      "concept": "concept name",
      "insight": "verbatim insight text",
      "draft_addresses": true,
      "status": "COVERED|PARTIAL|NEW",
      "matched_lpl": {{"lpl_id": "...", "title": "..."}} or null,
      "coverage_reason": "one sentence"
    }}
  ],
  "verdict": "NEW|PATCH|COVERED",
  "reason": "one sentence explaining why"
}}

## Rules
- Include ONLY insights the draft actually addresses (draft_addresses must be true).
- COVERED: an LPL post makes the same core argument.
- PARTIAL: an LPL post touches this insight but from a narrower angle.
- NEW: no LPL post covers this insight.
- Overall COVERED: the draft's main argument is already covered by existing posts.
- Overall PATCH: the draft adds a new angle on an argument that's partly covered.
- Overall NEW: at least one core insight has no LPL coverage.
- If the draft doesn't clearly address any insight, verdict = "NEW".
"""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_praxis_dedupe(
    draft: str,
    concepts_dir: Optional[Path] = None,
    lpl_index: Optional[Path] = None,
) -> dict:
    """
    Run PRAXIS concept-layer dedup on a draft string.

    Auto-resolves paths from config/local_paths.json if not provided.
    Returns a dict with keys: concept_match, insight_coverage, verdict, reason,
    praxis_available.  Never raises — falls back gracefully.
    """
    paths = _get_paths()
    if concepts_dir is None:
        concepts_dir = paths["concepts_dir"]
    if lpl_index is None:
        lpl_index = paths["lpl_index"]

    # Step 1: match concepts
    concepts = _load_concepts(concepts_dir)
    matched = _match_concepts(draft, concepts)

    if not matched:
        return {
            "concept_match": [],
            "insight_coverage": [],
            "verdict": "NEW",
            "reason": "No PRAXIS concept matched this draft.",
            "praxis_available": True,
        }

    # Step 2: build LLM inputs
    lpl_posts = _load_lpl_posts(lpl_index)

    concepts_block = "\n\n".join(
        f"### {c['concept']}\n"
        f"Aliases: {', '.join(c['aliases']) or 'none'}\n"
        "Key Insights:\n"
        + "\n".join(f"  - {ins}" for ins in c["insights"])
        for c in matched[:3]
    )

    lpl_block = "\n".join(
        f"- [{p.get('lpl_id', 'N/A')}] \"{p.get('title', 'N/A')}\" "
        f"— Hook: {p.get('hook', 'N/A')}"
        for p in lpl_posts
    ) or "(no published posts yet)"

    prompt = _PRAXIS_PROMPT.format(
        draft=draft,
        concepts_block=concepts_block,
        lpl_block=lpl_block,
    )

    # Step 3: LLM call
    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        result["praxis_available"] = True
        return result
    except Exception as exc:
        # Return a safe fallback so the pipeline never breaks
        return {
            "concept_match": [c["concept"] for c in matched],
            "insight_coverage": [],
            "verdict": "NEW",
            "reason": f"PRAXIS LLM step unavailable ({exc}). Concept matches: "
                      + ", ".join(c["concept"] for c in matched),
            "praxis_available": False,
        }
