AISPMAgent: The AI-SPM Development Pipeline 🤖
An automated, governance-first workflow for building and evaluating AI product features.

🎯 The "System-for-AI-Products" Mission
Building AI products is not about writing a single prompt; it's about managing a probabilistic lifecycle. AISPMAgent is a technical implementation of an automated PM pipeline. It ensures that no AI feature is shipped without passing through a rigorous Evaluation and Governance gate.

It demonstrates a core AI PM capability: Engineering the product's decision-making logic.

🧠 The Core Engine (Based on main.py)
This project uses a LangGraph-powered State Machine to manage the transition from "Idea" to "Knowledge."

State-Based Workflow Nodes:
MF Execute (Implementation): The core execution node where the AI feature or task is built.

EVAL (Evaluation): A dedicated node that runs LLM-based evaluation against predefined rubrics.

GATE (Governance): A critical decision-making node. It doesn't just pass data; it judges it based on evaluation scores.

LTI (Learning, Trust, Iteration): The "Success" path. Only items that pass the Gate are published and integrated into the long-term knowledge base.

COS (Archive): The "Risk-Mitigation" path. Failed iterations are archived for analysis, preventing faulty logic from reaching production.

🛠 Technical Implementation
LangGraph StateGraph: Unlike linear scripts, this project uses a graph-based architecture to handle complex loops and conditional routing.

Conditional Routing (route): Implements the logic approve -> LTI vs reject -> COS, showcasing how to automate Risk-Tiered Release Criteria.

UniverseState Management: Maintains a consistent state across different stages of the AI product lifecycle.

📊 The "Strategic Portfolio" Connection
This project is the Integration Layer of my AI PM ecosystem:

MentorFlow: The specialized RAG & Evaluation technology.

AISPMAgent: The Automated Pipeline that orchestrates development (using the logic in main.py).

AIPMO: The Organizational Framework and Natural Language Command Engine.

🚀 Usage
Bash
# Clone the AI PM Pipeline
git clone https://github.com/richardlee8433/AISPMAgent.git

# Run the Graph-based workflow
# This will invoke the state machine from MF -> EVAL -> GATE -> LTI/COS
python main.py


### LTI Authoring (Obsidian-backed)

Configure local vault path before running `ai_spm/lti_graph.py`:

- Copy `ai_spm/config/local_paths.sample.json` -> `ai_spm/config/local_paths.json`
- Set `obsidian_vault_root` to your real vault root

The graph now uses a two-step gate:
- **Post action (LPL)**: `publish_now|schedule|do_not_publish|hold`
- **Canonical action (LTI)**: `merge_now|create_now|update_later|no_change`

If post action is `publish_now` or `schedule`, the agent writes:
- `11_LPL/YYYY/MM/LPL-YYYYMMDDTHHMMSSZ-NNN.md`
- `90_AgentData/lpl_index.jsonl` (append-only SSOT)

If canonical action is `merge_now` or `create_now`, the agent writes canonical updates and refreshes `ai_spm/data/lti_index.json`.
