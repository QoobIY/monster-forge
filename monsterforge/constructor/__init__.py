"""Supported constructor API, importable without asset data or the MoM solver."""

from .registry import SUPPORTED_CONTRACTS, ConstructorRegistry, SourceBundle, default_registry
from .service import ConstructorService


def __getattr__(name: str):
    if name == "DEFAULT_REGISTRY":
        return default_registry()
    raise AttributeError(name)


__all__ = [
    "ConstructorRegistry",
    "ConstructorService",
    "SourceBundle",
    "default_registry",
    "SUPPORTED_CONTRACTS",
]
