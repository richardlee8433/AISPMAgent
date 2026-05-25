import os
import json
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Cluster suggestion ────────────────────────────────────────────────────────

def load_brand_context() -> dict:
    _here = Path(__file__).resolve().parent
    path = _here.parent / "data" / "brand_context.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}

def suggest_cluster(draft: str) -> str | None:
    """Call OpenAI to suggest a cluster. Returns A/B/C/D or None if unavailable."""
    try:
        from openai import OpenAI
        brand = load_brand_context()
        clusters = brand.get("clusters", {})
        if not clusters:
            return None

        cluster_desc = "\n".join(f"  {k}: {v}" for k, v in clusters.items())
        prompt = (
            f"You are classifying a LinkedIn post into one of four content clusters.\n\n"
            f"Clusters:\n{cluster_desc}\n\n"
            f"Post:\n\"\"\"\n{draft[:2000]}\n\"\"\"\n\n"
            f"Reply with exactly one letter: A, B, C, or D."
        )

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5,
            temperature=0,
        )
        answer = resp.choices[0].message.content.strip().upper()
        return answer if answer in {"A", "B", "C", "D"} else None
    except Exception:
        return None


# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    _here = Path(__file__).resolve().parent
    config_path = _here.parent.parent / "config" / "local_paths.json"
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    return {}

def get_vault_root(cfg: dict) -> Path | None:
    root = cfg.get("obsidian_vault_root")
    return Path(root) if root else None

def get_lpl_dir(cfg: dict) -> str:
    return cfg.get("vault_paths", {}).get("lpl_dir", "08_LPL_Library")

def get_index_path(cfg: dict) -> Path:
    root = get_vault_root(cfg)
    agent_dir = cfg.get("vault_paths", {}).get("agent_data_dir", "90_AgentData")
    if root:
        return root / agent_dir / "lpl_index.jsonl"
    _here = Path(__file__).resolve().parent
    return _here.parent / "data" / "lpl_index.jsonl"


# ── Helpers ───────────────────────────────────────────────────────────────────

def generate_lpl_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"LPL-{ts}-001"

def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def extract_title(draft: str) -> str:
    """Use first non-empty line as title fallback (max 120 chars)."""
    for line in draft.splitlines():
        line = line.strip()
        if line:
            return line[:120]
    return "(Untitled)"

def read_draft_stdin() -> str:
    print("Paste your draft. End with a single line: /end\n")
    lines = []
    for line in sys.stdin:
        if line.strip() == "/end":
            break
        lines.append(line)
    return "".join(lines).strip()

def build_frontmatter(lpl_id: str, title: str, hook: str, cluster: str,
                      post_url: str, rel_path: str) -> str:
    now = iso_now()
    lines = [
        "---",
        "type: lpl_post",
        f"lpl_id: {lpl_id}",
        f'date_created: "{now}"',
        f'date_published: "{now}"',
        "status: published",
        "channel: linkedin",
        "language: en",
        f'title: "{title}"',
        f'hook: "{hook}"',
        f"cluster: {cluster}",
        "canonical_lti_targets: []",
        f"path: {rel_path}",
    ]
    if post_url:
        lines.append("links:")
        lines.append(f'  url: "{post_url}"')
    lines.append("---")
    return "\n".join(lines)


# ── Core ──────────────────────────────────────────────────────────────────────

def write_md(cfg: dict, lpl_id: str, title: str, hook: str, cluster: str,
             post_url: str, draft: str) -> Path:
    root = get_vault_root(cfg)
    lpl_dir = get_lpl_dir(cfg)
    yyyy = lpl_id[4:8]
    mm   = lpl_id[8:10]

    rel_path = f"{lpl_dir}/{yyyy}/{mm}/{lpl_id}.md"

    if root:
        abs_path = root / lpl_dir / yyyy / mm / f"{lpl_id}.md"
    else:
        _here = Path(__file__).resolve().parent
        abs_path = _here.parent.parent / lpl_dir / yyyy / mm / f"{lpl_id}.md"

    abs_path.parent.mkdir(parents=True, exist_ok=True)

    fm = build_frontmatter(lpl_id, title, hook, cluster, post_url, rel_path)
    content = fm + "\n\n" + draft + "\n"
    abs_path.write_text(content, encoding="utf-8")
    return abs_path

def append_index(cfg: dict, lpl_id: str, title: str, hook: str,
                 cluster: str, rel_path: str) -> None:
    idx = get_index_path(cfg)
    idx.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "lpl_id": lpl_id,
        "date_created": iso_now(),
        "date_published": iso_now(),
        "status": "published",
        "title": title,
        "hook": hook,
        "cluster": cluster,
        "canonical_lti_targets": [],
        "language": "en",
        "path": rel_path,
    }
    with idx.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Add an LPL post — writes .md to vault and updates index.")
    parser.add_argument("--title",    help="Post title (auto-extracted from first line if omitted)")
    parser.add_argument("--hook",     help="One-liner hook sentence")
    parser.add_argument("--cluster",  help="Cluster A / B / C / D")
    parser.add_argument("--post-url", default="", help="Published LinkedIn URL (optional)")
    parser.add_argument("--id",       help="LPL ID (auto-generated if omitted)")
    args = parser.parse_args()

    cfg = load_config()
    interactive = sys.stdin.isatty()

    # Draft
    draft = read_draft_stdin()
    if not draft:
        print("Empty draft. Exiting.")
        return

    # ── Metadata ──────────────────────────────────────────────────────────────
    # Pipe mode (stdin not a tty): rely entirely on flags, no input() calls.
    # Interactive mode: prompt for any missing field.

    if interactive:
        title    = args.title    or input(f"Title [{extract_title(draft)}]: ").strip() or extract_title(draft)
        hook     = args.hook     or input("Hook: ").strip()
        post_url = args.post_url or input("LinkedIn URL (optional, Enter to skip): ").strip()
    else:
        title    = args.title    or extract_title(draft)
        hook     = args.hook     or ""
        post_url = args.post_url or ""

    if args.cluster:
        cluster = args.cluster.upper()
    else:
        brand = load_brand_context()
        cluster_desc = brand.get("clusters", {})
        print("\nSuggesting cluster...", end=" ", flush=True)
        suggestion = suggest_cluster(draft)
        if suggestion:
            desc = cluster_desc.get(suggestion, "")
            print(f"{suggestion}  ({desc})")
            if interactive:
                confirm = input(f"Cluster [{suggestion}]: ").strip().upper()
                cluster = confirm if confirm in {"A", "B", "C", "D"} else suggestion
            else:
                cluster = suggestion
                print(f"→ auto-accepted: {cluster}")
        else:
            print("(no suggestion)")
            if interactive:
                for k, v in cluster_desc.items():
                    print(f"  {k}: {v}")
                cluster = input("Cluster [A/B/C/D]: ").strip().upper()
            else:
                cluster = "D"  # safe default when no suggestion and no tty
                print(f"→ fallback default: {cluster}")

    if cluster not in {"A", "B", "C", "D"}:
        print(f"Invalid cluster '{cluster}'. Must be A, B, C or D.")
        return

    lpl_id = args.id or generate_lpl_id()
    lpl_dir = get_lpl_dir(cfg)
    yyyy, mm = lpl_id[4:8], lpl_id[8:10]
    rel_path = f"{lpl_dir}/{yyyy}/{mm}/{lpl_id}.md"

    abs_path = write_md(cfg, lpl_id, title, hook, cluster, post_url, draft)
    append_index(cfg, lpl_id, title, hook, cluster, rel_path)

    print(f"\n✅ {lpl_id}")
    print(f"   .md  → {abs_path}")
    print(f"   idx  → {get_index_path(cfg)}")


if __name__ == "__main__":
    main()
