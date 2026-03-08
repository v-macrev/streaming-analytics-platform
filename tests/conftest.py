from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PRODUCER_SRC = REPO_ROOT / "producer" / "src"
STREAMING_SRC = REPO_ROOT / "streaming" / "src"

for path in (REPO_ROOT, PRODUCER_SRC, STREAMING_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)