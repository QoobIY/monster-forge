"""Disposable source cards, built from verified approved slot geometry."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image

from tools.creature_workshop import geometry

from ..paths import cache_directory
from ..serialization import encoded

if TYPE_CHECKING:
    from .service import ConstructorService


def source_card(service: ConstructorService, category: str, identifier: str) -> Path:
    registry = service.registry
    if identifier not in registry.source_bundles:
        raise ValueError("Unknown registered source bundle")
    slots = {
        "face": ("head",),
        "head": ("head",),
        "hair": ("head",),
        "arms": ("left_arm", "right_arm"),
        "legs": ("left_leg", "right_leg"),
        "outfit": registry.slots,
        "back": ("back_attachment",),
    }.get(category)
    if slots is None:
        raise ValueError("Unsupported source card category")
    arrays, sources = [], []
    for slot in slots:
        recipe, provenance = service.source_loader(identifier, slot)
        # A warm PNG cache never bypasses approved source evidence or GLB/recipe
        # equivalence. Source reads and admission happen on every request.
        arrays.append(geometry.compile_recipe(recipe))
        sources.append(
            {
                key: provenance[key]
                for key in (
                    "donor",
                    "slot",
                    "model_sha256",
                    "recipe_sha256",
                    "manifest_sha256",
                    "record_sha256",
                    "reference_files",
                )
            }
        )
    identity = hashlib.sha256(
        encoded(
            {
                "schema_version": 1,
                "category": category,
                "sources": sources,
                "renderer_sha256": hashlib.sha256(Path(geometry.__file__).read_bytes()).hexdigest(),
                "background": 255,
                "size": 256,
            }
        )
    ).hexdigest()
    cache = cache_directory("source-cards", root=registry.asset_root)
    target = cache / (identity + ".png")
    try:
        with Image.open(target) as image:
            image.verify()
        return target
    except (OSError, ValueError, SyntaxError):
        pass
    cache.mkdir(parents=True, exist_ok=True)
    merged = tuple(np.concatenate([part[index] for part in arrays]) for index in range(3)) + ([],)
    with tempfile.TemporaryDirectory(prefix="source-card-", dir=cache) as temporary:
        output = Path(temporary) / "preview.png"
        service.renderer(output, merged, size=256, background=255)
        with Image.open(output) as image:
            if image.format != "PNG":
                raise ValueError("Source card renderer must produce PNG")
            image.verify()
        os.replace(output, target)
    return target
