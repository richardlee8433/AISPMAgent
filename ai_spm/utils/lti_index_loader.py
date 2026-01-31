from pathlib import Path
import re
from typing import Tuple

INDEX_DIR = Path(r"G:\My Drive\AI Native PM\AI Native PM\00_Index")
INDEX_RE = re.compile(r"LTI Index v(\d+)\.(\d+)\.(\d+)\.md")

def find_latest_lti_index() -> Tuple[Path, str]:
    """
    Returns:
      (path_to_latest_index_md, version_string)
    Raises:
      FileNotFoundError if no index is found
    """
    candidates = []

    for p in INDEX_DIR.glob("LTI Index v*.md"):
        m = INDEX_RE.match(p.name)
        if not m:
            continue
        version = tuple(int(x) for x in m.groups())
        candidates.append((version, p))

    if not candidates:
        raise FileNotFoundError(f"No LTI Index md found in {INDEX_DIR}")

    candidates.sort(key=lambda x: x[0], reverse=True)
    latest_version, latest_path = candidates[0]

    version_str = ".".join(str(x) for x in latest_version)
    return latest_path, version_str
