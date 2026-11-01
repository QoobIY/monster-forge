"""Assembly schema v2: an instruction and one self-contained skinned GLB."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import struct
import tempfile
from pathlib import Path

import numpy as np

from monster_forge_sdk import AssetStore
from monster_forge_sdk.characters import read_character_model

from .serialization import encoded


def geometry(blob):
    """Display the actual baked artifact, including its embedded texture."""
    model = read_character_model(blob)
    indices = np.asarray(model["triangles"])
    attrs = model["attributes"]
    result = {
        key: np.asarray(attrs[attribute])[indices, :width].reshape(-1).tolist()
        for key, attribute, width in (
            ("positions", "POSITION", 3),
            ("normals", "NORMAL", 3),
            ("colors", "COLOR_0", 3),
        )
    }
    result["uvs"] = (
        np.asarray(attrs["TEXCOORD_0"])[indices].reshape(-1).tolist()
        if "TEXCOORD_0" in attrs
        else [0.002] * (len(indices) * 2)
    )
    size = struct.unpack_from("<I", blob, 12)[0]
    doc = json.loads(blob[20 : 20 + size])
    binary = blob[28 + size :]
    pbr = doc["materials"][0]["pbrMetallicRoughness"]
    if "baseColorTexture" in pbr:
        texture = doc["textures"][pbr["baseColorTexture"]["index"]]
        image = doc["images"][texture["source"]]
        view = doc["bufferViews"][image["bufferView"]]
        start = view.get("byteOffset", 0)
        result["texture"] = base64.b64encode(binary[start : start + view["byteLength"]]).decode()
    return model["metadata"], result


def preview_payload(blob):
    from .static_assembly import is_static
    from .static_assembly import preview_payload as static_preview

    if is_static(blob):
        return static_preview(blob)
    metadata, data = geometry(blob)
    from .runtime import bind_positions

    skeleton = metadata["skeleton"]
    world = bind_positions(skeleton)
    return {
        "schema_version": 2,
        "contract": metadata["skeleton_id"],
        "bind_bones": [
            {"id": bone["id"], "parent": bone["parent"], "position": world[bone["id"]]}
            for bone in skeleton["bones"]
        ],
        "triangles": len(data["positions"]) // 9,
        "warnings": [],
        "parts": {"whole": {"model_sha256": hashlib.sha256(blob).hexdigest(), "geometry": data}},
    }


def preview_image(blob):
    from .static_assembly import is_static
    from .static_assembly import preview_image as static_preview_image

    if is_static(blob):
        return static_preview_image(blob)
    from tools.creature_workshop.geometry import render_png

    from .constructor_cache import CACHE

    target = CACHE / ("body-" + hashlib.sha256(blob).hexdigest() + ".png")
    if not target.exists():
        _, data = geometry(blob)
        arrays = tuple(
            np.asarray(data[key], dtype="<f4").reshape(-1, 3)
            for key in ("positions", "normals", "colors")
        ) + ([],)
        CACHE.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=CACHE) as temporary:
            path = Path(temporary) / "preview.png"
            render_png(path, arrays, size=256)
            os.replace(path, target)
    return target.read_bytes()


def bake_build(root: Path, manifest: dict):
    """Use disposable compiler parts to produce the single saved GLB."""
    weighted = [bool(part.get("weights")) for part in manifest["parts"].values()]
    if not all(weighted):
        if any(weighted) or manifest.get("checks", {}).get("weight_sidecars") is not False:
            raise ValueError("Incomplete character weights cannot be exported as a static draft")
        from .static_assembly import bake_static

        return bake_static(root, manifest)
    from tools.assets.bake_character_models import bake

    from .paths import ROOT

    entries = []
    for slot, info in manifest["parts"].items():
        refs = {}
        for role, path, mime in (
            ("model", root / info["model"], "model/gltf-binary"),
            ("weights", root / info["weights"], "application/json"),
        ):
            blob = path.read_bytes()
            refs[role] = {
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(blob).hexdigest(),
                "size_bytes": len(blob),
                "media_type": mime,
            }
        entries.append(
            {
                "id": "character.saved.parts." + slot,
                "kind": "character",
                "title": slot,
                "revision": 1,
                "files": refs,
            }
        )
    store = AssetStore(ROOT, catalog=encoded({"schema_version": 1, "assets": entries}))
    store.media_root = root.resolve()
    return bake(store, "character.saved", allow_optional_parts=True)


def instruction(settings, manifest, blob):
    static = not any(part.get("weights") for part in manifest["parts"].values())
    result = {
        "schema_version": 2,
        "kind": "constructor_assembly",
        "constructor_settings": settings,
        "skeleton_id": manifest["contract"],
        "bind_profile": manifest.get("bind_profile") if static else manifest["bind_profile"],
        "source_assembly": manifest["id"],
        "parts": {
            slot: {"revision_id": info["revision_id"], "source_model_sha256": info["model_sha256"]}
            for slot, info in manifest["parts"].items()
        },
        "model": {
            "path": "model.glb",
            "sha256": hashlib.sha256(blob).hexdigest(),
            "size_bytes": len(blob),
        },
        "compiler": "monster-forge-constructor-v2",
    }
    if static:
        result.update(
            rigging="none",
            runtime_support=False,
            status="authoring_draft",
            compiler="monster-forge-static-assembly-v1",
        )
    return result
