"""Locations of current constructor assets and local saved assemblies."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
STYLE_PATH = CONFIG_DIR / "style_profile.json"
HUMANOID_CONTRACT_PATH = CONFIG_DIR / "humanoid_v1.json"


def cache_directory(namespace: str = "", *, root: Path | None = None) -> Path:
    """Locate disposable work outside the checkout, isolated by source root."""
    relative = Path(namespace)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Cache namespace must be relative")
    identity = hashlib.sha256(str((root or ROOT).resolve()).encode()).hexdigest()[:16]
    return Path("/tmp/monster-forge") / identity / relative


def resolve_asset_path(historical_path: str, *, root: Path | None = None) -> Path:
    """Resolve immutable recipe provenance after the constructor store migration."""
    prefix = "media/experiments/constructor_"
    if historical_path.startswith(prefix):
        relative = historical_path[len(prefix) :]
        if relative.startswith("arena_expansion/"):
            relative = "species_extra/" + relative[len("arena_expansion/") :]
        historical_path = "media/constructor/" + relative
    source_root = root or ROOT
    path = (source_root / historical_path).resolve()
    if not path.is_relative_to((source_root / "media/constructor").resolve()):
        raise ValueError("Reference must belong to the current constructor asset store")
    return path
