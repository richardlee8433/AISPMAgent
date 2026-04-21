import os
import json
import sys
import yaml
import argparse
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

def get_data_paths():
    base_data_dir = os.path.join("pmos", "data")
    config_path = os.path.join("ai_spm", "config", "local_paths.json")
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
        "lpl_index": os.path.join(base_data_dir, "lpl_index.jsonl")
    }

def append_to_index(entry):
    paths = get_data_paths()
    os.makedirs(os.path.dirname(paths["lpl_index"]), exist_ok=True)
    with open(paths["lpl_index"], "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"Added [{entry['lpl_id']}] to lpl_index.jsonl")

def main():
    parser = argparse.ArgumentParser(description="Add an LPL post to the index.")
    parser.add_argument("--id", help="LPL ID")
    parser.add_argument("--title", help="Post title")
    parser.add_argument("--hook", help="Post hook")
    parser.add_argument("--cluster", help="Cluster (A/B/C/D)")
    
    # We might be called with no args, or some args.
    # If any manual flag is provided, we assume manual mode for the provided fields.
    # But the spec says "Mode 2 - manual flags: python -m pmos.commands.lpl_add --id ... --title ... --hook ... --cluster A"
    # "Appends directly, no prompts."
    
    args, unknown = parser.parse_known_args()
    
    if args.id and args.title and args.hook and args.cluster:
        # Mode 2: Manual
        entry = {
            "lpl_id": args.id,
            "title": args.title,
            "hook": args.hook,
            "cluster": args.cluster,
            "status": "published",
            "date_added": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        append_to_index(entry)
    else:
        # Mode 1: Interactive
        print("Paste your LPL frontmatter (the --- block). End with /end")
        fm_lines = []
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            if line.strip() == "/end":
                break
            fm_lines.append(line)
        fm_text = "".join(fm_lines).strip()
        
        if not fm_text:
            print("Empty input. Exiting.")
            return

        # Handle optional --- delimiters
        lines = fm_text.splitlines()
        if lines[0].strip() == "---":
            lines = lines[1:]
        if lines and lines[-1].strip() == "---":
            lines = lines[:-1]
        fm_text = "\n".join(lines)
            
        try:
            data = yaml.safe_load(fm_text)
        except Exception as e:
            print(f"Error parsing YAML: {e}")
            return
            
        if not isinstance(data, dict):
            print("Error: Invalid frontmatter format. Expected a YAML mapping.")
            return

        lpl_id = data.get("lpl_id")
        title = data.get("title")
        hook = data.get("hook")
        status = data.get("status", "published")
        
        if not lpl_id or not title:
            print(f"Error: Missing {'lpl_id' if not lpl_id else 'title'} in frontmatter.")
            if not lpl_id:
                print("LPL ID is required.")
            if not title:
                print("Title is required.")
            return
            
        if not hook:
            print("No hook found in frontmatter. Please provide one:")
            hook = sys.stdin.readline().strip()
            
        cluster = input("Cluster? [A/B/C/D]: ").strip().upper()
        
        entry = {
            "lpl_id": lpl_id,
            "title": title,
            "hook": hook,
            "cluster": cluster,
            "status": status,
            "date_added": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        append_to_index(entry)

if __name__ == "__main__":
    main()
