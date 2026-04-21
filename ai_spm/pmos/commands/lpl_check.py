import os
import json
import sys
import re
from openai import OpenAI
from dotenv import load_dotenv
from rapidfuzz import fuzz

load_dotenv()

def get_data_paths():
    # Fallback
    base_data_dir = os.path.join("pmos", "data")
    obsidian_root = None
    
    config_path = os.path.join("config", "local_paths.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                vault_paths = config.get("vault_paths", {})
                agent_data_dir = vault_paths.get("agent_data_dir")
                obsidian_root = config.get("obsidian_vault_root")
                if agent_data_dir and obsidian_root:
                    potential_path = os.path.join(obsidian_root, agent_data_dir)
                    if os.path.exists(potential_path):
                        base_data_dir = potential_path
        except Exception:
            pass
            
    return {
        "brand_context": os.path.join("pmos", "data", "brand_context.json"),
        "lpl_index": os.path.join(base_data_dir, "lpl_index.jsonl"),
        "prompt_template": os.path.join("pmos", "prompts", "lpl_check.txt"),
        "obsidian_root": obsidian_root
    }

def strip_frontmatter(text):
    # Strip everything between the first --- and second ---
    # This regex looks for --- at the start of the file or after a newline,
    # then everything until the next ---
    return re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, flags=re.DOTALL | re.MULTILINE).strip()

def main():
    print("Paste your draft. End with a single line: /end")
    draft_lines = []
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        if line.strip() == "/end":
            break
        draft_lines.append(line)
    draft = "".join(draft_lines).strip()
    
    if not draft:
        print("Empty draft. Exiting.")
        return

    paths = get_data_paths()
    
    # Pre-check step
    if os.path.exists(paths["lpl_index"]):
        with open(paths["lpl_index"], "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("path") and paths["obsidian_root"]:
                        full_path = os.path.join(paths["obsidian_root"], entry["path"])
                        if os.path.exists(full_path):
                            with open(full_path, "r", encoding="utf-8") as pf:
                                file_text = strip_frontmatter(pf.read())
                                score = fuzz.token_set_ratio(draft, file_text)
                                if score >= 85:
                                    print("\nDUPLICATE DETECTED (no API call needed)")
                                    print(f"\nSimilarity: {score:.1f}%")
                                    print(f"Matched post: {entry.get('lpl_id')}")
                                    print(f"Title: {entry.get('title')}")
                                    print(f"Hook: {entry.get('hook')}")
                                    print("\nDecision: DUPLICATE — this draft is substantially identical to an existing post.")
                                    return
                except Exception:
                    continue

    if not os.path.exists(paths["brand_context"]):
        print(f"Error: Brand context not found at {paths['brand_context']}")
        return
        
    with open(paths["brand_context"], "r", encoding="utf-8") as f:
        brand_context = json.load(f)
        
    posts = []
    if os.path.exists(paths["lpl_index"]):
        with open(paths["lpl_index"], "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        post = json.loads(line)
                        if post.get("status") == "published":
                            posts.append(post)
                    except json.JSONDecodeError:
                        continue
    
    if not os.path.exists(paths["prompt_template"]):
        print(f"Error: Prompt template not found at {paths['prompt_template']}")
        return
        
    with open(paths["prompt_template"], "r", encoding="utf-8") as f:
        template = f.read()
        
    post_list = "\n".join([f"- [{p.get('lpl_id', 'N/A')}] \"{p.get('title', 'N/A')}\" — Hook: {p.get('hook', 'N/A')}" for p in posts])
    
    try:
        prompt = template.format(
            positioning=brand_context["positioning"],
            cluster_A=brand_context["clusters"]["A"],
            cluster_B=brand_context["clusters"]["B"],
            cluster_C=brand_context["clusters"]["C"],
            cluster_D=brand_context["clusters"]["D"],
            post_count=len(posts),
            post_list=post_list,
            draft=draft
        )
    except KeyError as e:
        print(f"Error formatting prompt: Missing key {e}")
        return
    
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    print("\n" + response.choices[0].message.content)

if __name__ == "__main__":
    main()
