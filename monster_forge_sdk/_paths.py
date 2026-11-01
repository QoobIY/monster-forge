"""Asset release location shared by the dependency-free SDK readers."""

from __future__ import annotations

import os
from pathlib import Path


def asset_root(root: str | Path | None = None) -> Path:
    if root is None:
        root = os.environ.get("MONSTER_FORGE_ASSET_ROOT")
    return (Path(root) if root is not None else Path(__file__).resolve().parents[1]).resolve()
