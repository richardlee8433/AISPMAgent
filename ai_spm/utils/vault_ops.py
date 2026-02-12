from __future__ import annotations

import json
import re
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

DEFAULT_PATHS = {
    "index_dir": "00_Index",
    "lti_dir": "10_LTI",
    "lpl_dir": "11_LPL",
    "cos_dir": "12_COS",
    "agent_data_dir": "90_AgentData",
}


class VaultConfigError(RuntimeError):
    pass


def iso_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_id_now() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def load_local_paths(config_dir: Path | None = None) -> dict[str, Any]:
    config_dir = config_dir or Path("config")
    config_path = config_dir / "local_paths.json"
    sample_path = config_dir / "local_paths.sample.json"

    if config_path.exists():
        data = json.loads(config_path.read_text(encoding="utf-8"))
    elif sample_path.exists():
        data = json.loads(sample_path.read_text(encoding="utf-8"))
    else:
        raise VaultConfigError(
            "Missing config/local_paths.json (or sample). Please create it with obsidian_vault_root and vault_paths."
        )

    root = (data.get("obsidian_vault_root") or "").strip()
    if not root:
        raise VaultConfigError("obsidian_vault_root is required in local paths config.")

    vault_paths = dict(DEFAULT_PATHS)
    vault_paths.update(data.get("vault_paths") or {})

    return {"obsidian_vault_root": root, "vault_paths": vault_paths}


def ensure_vault_root_exists(cfg: dict[str, Any]) -> Path:
    root = Path(cfg["obsidian_vault_root"])
    if not root.exists():
        raise VaultConfigError(f"Obsidian vault root does not exist: {root}")
    return root


def vault_abs_path(cfg: dict[str, Any], *parts: str) -> Path:
    root = ensure_vault_root_exists(cfg)
    out = root
    for p in parts:
        out = out / p
    return out


def lpl_index_jsonl_path(cfg: dict[str, Any]) -> Path:
    return vault_abs_path(cfg, cfg["vault_paths"]["agent_data_dir"], "lpl_index.jsonl")


def _lpl_prefix(today_yyyymmdd: str) -> str:
    return f"LPL-{today_yyyymmdd}T"


def next_lpl_id(cfg: dict[str, Any], now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    today = now.strftime("%Y%m%d")
    ts = now.strftime("%Y%m%dT%H%M%SZ")
    prefix = _lpl_prefix(today)
    re_id = re.compile(rf"^{re.escape(prefix)}\d{{6}}Z-(\d{{3}})$")

    index_path = lpl_index_jsonl_path(cfg)
    max_n = 0
    if index_path.exists():
        for line in index_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            lpl_id = (row.get("lpl_id") or "").strip()
            m = re_id.match(lpl_id)
            if m:
                max_n = max(max_n, int(m.group(1)))

    return f"LPL-{ts}-{max_n + 1:03d}"


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text

    lines = text.splitlines()
    try:
        end_idx = lines[1:].index("---") + 1
    except ValueError:
        return {}, text

    fm_lines = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1 :]).lstrip("\n")
    fm: dict[str, Any] = {}
    for ln in fm_lines:
        if not ln.strip() or ":" not in ln:
            continue
        k, v = ln.split(":", 1)
        fm[k.strip()] = v.strip().strip('"')
    return fm, body


def dump_frontmatter(data: dict[str, Any]) -> str:
    def fmt(v: Any, indent: int = 0) -> str:
        pad = " " * indent
        if isinstance(v, dict):
            rows = []
            for kk, vv in v.items():
                if isinstance(vv, (dict, list)):
                    rows.append(f"{pad}{kk}:")
                    rows.append(fmt(vv, indent + 2))
                else:
                    rows.append(f"{pad}{kk}: {scalar(vv)}")
            return "\n".join(rows)
        if isinstance(v, list):
            if not v:
                return f"{pad}[]"
            rows = []
            for item in v:
                if isinstance(item, (dict, list)):
                    rows.append(f"{pad}-")
                    rows.append(fmt(item, indent + 2))
                else:
                    rows.append(f"{pad}- {scalar(item)}")
            return "\n".join(rows)
        return f"{pad}{scalar(v)}"

    def scalar(v: Any) -> str:
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return str(v)
        s = str(v)
        if s == "" or any(ch in s for ch in [":", "#", "\n", "\"", "[", "]", "{"]):
            return json.dumps(s, ensure_ascii=False)
        return s

    return "---\n" + fmt(data) + "\n---\n"


def extract_title_from_draft(draft: str) -> str:
    lines = [ln.strip() for ln in draft.splitlines() if ln.strip()]
    if not lines:
        return "(Untitled)"
    first = lines[0]
    return first.lstrip("#").strip()[:140] if first.startswith("#") else first[:140]


def bump_patch_version(version: str | None, lti_id: str) -> str:
    if version:
        nums = [int(x) for x in re.findall(r"\d+", version)]
        if nums:
            nums[-1] += 1
            return ".".join(str(x) for x in nums)

    m = re.match(r"^LTI-(\d+)\.(\d+)", lti_id)
    if m:
        return f"{m.group(1)}.{m.group(2)}.1"
    return "0.0.1"
