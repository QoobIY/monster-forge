"""Compatibility entry point for the file-backed MOM RPG preset library."""
from .constructor_presets import load_presets


def presets() -> list[dict]:
    return load_presets('mom_rpg')
