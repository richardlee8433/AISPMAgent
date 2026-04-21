# AISPMAgent

A personal AI PM operating system for building in public — with governance.

## What this is

AISPMAgent started as a LangGraph-based evaluation and governance pipeline for AI features. It has evolved into a practical toolset for an AI-native PM who publishes on LinkedIn and manages knowledge across systems.

## Current active tooling: pmos

`pmos` is a lightweight CLI for managing LinkedIn posts with brand consistency.

### pmos lpl check

Run before publishing a LinkedIn post. Checks the draft against all published posts and brand positioning.

```bash
python -m pmos.commands.lpl_check
```

What it does:
- Paste your draft, end with /end
- Runs rapidfuzz similarity check against all published .md files in your LPL Library
- If similarity >= 85%: returns DUPLICATE immediately, no API call
- If similarity < 85%: calls GPT-4.1-mini for semantic judgment
- Returns: Core Claim, Most Similar Posts, Similarity Level, Positioning Fit, Decision (GO / REVISE / DUPLICATE)

### pmos lpl add

Run after publishing. Adds the new post to lpl_index.jsonl.

```bash
python -m pmos.commands.lpl_add
```

## Brand context

Richard's positioning: AI native PM who keeps humans in the judgment seat.
Core belief: AI accelerates capability, but accountability stays with the person.

Posts are organized into four clusters:
- A: AI removes bottlenecks but widens the judgment gap
- B: PM's job is to define boundaries in ambiguity
- C: Build-in-public — VIVERSE creator onboarding series
- D: Tool evaluations and AI as infrastructure

## Legacy: LangGraph pipeline

The original LangGraph pipeline (lti_graph.py) handled LTI knowledge management with nodes for deduplication, role classification, editorial review, and canonical mapping. This is currently frozen while the simpler pmos tooling is the active workflow.

## Setup

1. Copy config/local_paths.sample.json to config/local_paths.json
2. Set obsidian_vault_root to your local vault path
3. Set OPENAI_API_KEY in your .env file
4. pip install openai python-dotenv pyyaml rapidfuzz

## Structure
ai_spm/
pmos/
commands/
lpl_check.py      # pre-publish brand check
lpl_add.py        # post-publish index update
data/
brand_context.json
lpl_index.jsonl   # append-only post index
prompts/
lpl_check.txt     # prompt template
config/
local_paths.sample.json
lti_graph.py          # legacy LangGraph pipeline (frozen)
