"""Compatibility imports for existing Monster Forge tools.

New integrations use monsterforge.constructor. This adapter preserves established
functions and the small set of monkeypatch ports used by historical authoring
commands. Constructor policies, geometry and storage live behind explicit APIs.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

from tools.creature_workshop.geometry import render_png

from .assembly_repository import AssemblyRepository
from .constructor import ConstructorService, _inventory
from .constructor.catalog import presets, reference_presets
from .constructor.geometry import _head as _prepare_head
from .constructor.geometry import _is_hair, _is_headwear, _tint, _transform
from .constructor.registry import _FIELDS, DEFAULT_REGISTRY
from .constructor.settings import default_settings as _defaults
from .constructor.settings import validate_settings as _validate
from .constructor.sources import glb_arrays as _glb_arrays
from .constructor.sources import load_part
from .constructor_back import author as author_back
from .constructor_back import tint as tint_back
from .paths import DATA_DIR, ROOT, STYLE_PATH
from .serialization import encoded as _encoded

globals().update({name: value for name, value in vars(_inventory).items() if name.isupper()})
globals().update({name: getattr(DEFAULT_REGISTRY, field) for name, field in _FIELDS.items()})
STORE = DATA_DIR / "character_constructor"


def _registry():
    # Preserve explicit source-directory overrides used by old publishing tools.
    return replace(
        DEFAULT_REGISTRY,
        **{
            field: globals()[name]
            for name, field in _FIELDS.items()
            if name.endswith("_SOURCE") and globals()[name] != getattr(DEFAULT_REGISTRY, field)
        },
    )


def _service(*, build_operation=None):
    return ConstructorService(
        _registry(),
        repository=AssemblyRepository(STORE),
        renderer=render_png,
        source_loader=_load,
        build_operation=build_operation,
    )


def _hash(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _folder(donor: str) -> Path:
    return _registry().source_folder(donor)


def _load(donor: str, slot: str) -> tuple[dict, dict]:
    return load_part(donor, slot, registry=_registry(), folder_resolver=_folder)


def _head(recipe: dict, settings: dict, sources: list[dict]) -> dict:
    return _prepare_head(recipe, settings, sources, registry=_registry(), source_loader=_load)


def default_settings() -> dict:
    return _defaults(registry=_registry())


def validate_settings(payload: dict) -> dict:
    return _validate(payload, registry=_registry())


def catalog(*, include_legacy: bool = True) -> dict:
    return _service().catalog(include_legacy=include_legacy)


def build(payload: dict, target: Path, *, weights: bool = False) -> dict:
    return _service().build(payload, target, weights=weights)


def preview(payload: dict) -> dict:
    return _service(build_operation=build).preview(payload)


def _compact_assembly(payload: dict, root: Path) -> tuple[dict, bytes]:
    return _service(build_operation=build).compact_assembly(payload, root)


def export_bundle(payload: dict) -> bytes:
    return _service(build_operation=build).export_bundle(payload)


def save(payload: dict) -> dict:
    return _service(build_operation=build).save(payload)


def saved_manifest(identifier: str) -> dict:
    return _service().saved_manifest(identifier)


def saved_bundle(identifier: str) -> bytes:
    return _service().saved_bundle(identifier)


def saved_model(identifier: str) -> bytes:
    return _service().saved_model(identifier)


def saved_directory(identifier: str) -> Path:
    return _service().saved_directory(identifier)


def list_saved() -> list[dict]:
    return _service().list_saved()


__all__ = [
    "ROOT",
    "STORE",
    "STYLE_PATH",
    "ConstructorService",
    "_encoded",
    "_glb_arrays",
    "_is_hair",
    "_is_headwear",
    "_tint",
    "_transform",
    "author_back",
    "build",
    "catalog",
    "default_settings",
    "export_bundle",
    "list_saved",
    "presets",
    "preview",
    "reference_presets",
    "render_png",
    "save",
    "saved_bundle",
    "saved_manifest",
    "tint_back",
    "validate_settings",
]
