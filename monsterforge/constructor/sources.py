"""Read and verify immutable source parts; never generate character revisions."""

from __future__ import annotations

import copy
import hashlib
import json
import struct

import numpy as np

from tools.creature_workshop.geometry import compile_recipe

from .registry import ConstructorRegistry, default_registry


def _hash(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def glb_arrays(blob: bytes) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if len(blob) < 28 or struct.unpack_from("<4sII", blob) != (b"glTF", 2, len(blob)):
        raise ValueError("Повреждённый GLB источника")
    size, kind = struct.unpack_from("<I4s", blob, 12)
    if kind != b"JSON" or 28 + size > len(blob):
        raise ValueError("Повреждённый JSON chunk")
    doc = json.loads(blob[20 : 20 + size])
    binary_size, binary_kind = struct.unpack_from("<I4s", blob, 20 + size)
    if binary_kind != b"BIN\x00" or 28 + size + binary_size != len(blob):
        raise ValueError("Повреждённый binary chunk")
    primitive = doc["meshes"][0]["primitives"][0]
    arrays = []
    for name in ("POSITION", "NORMAL", "COLOR_0"):
        accessor = doc["accessors"][primitive["attributes"][name]]
        view = doc["bufferViews"][accessor["bufferView"]]
        offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        count = accessor["count"]
        if (
            accessor["type"] != "VEC3"
            or accessor["componentType"] != 5126
            or view.get("byteStride", 12) != 12
            or (count <= 0)
            or (offset < 0)
            or (offset + count * 12 > binary_size)
        ):
            raise ValueError("Неподдерживаемые атрибуты GLB")
        arrays.append(
            np.frombuffer(blob, dtype="<f4", count=count * 3, offset=28 + size + offset)
            .reshape(-1, 3)
            .copy()
        )
    if any(a.shape != arrays[0].shape or not np.isfinite(a).all() for a in arrays):
        raise ValueError("Некорректные атрибуты GLB")
    return tuple(arrays)


def load_part(
    donor: str, slot: str, *, registry: ConstructorRegistry | None = None, folder_resolver=None
) -> tuple[dict, dict]:
    registry = registry or default_registry()
    folder = (folder_resolver or registry.source_folder)(donor)
    bundle = registry.source_bundles.get(donor)
    if bundle is not None:
        for name, digest in bundle.evidence:
            path = (folder / name).resolve()
            if not path.is_relative_to(folder.resolve()) or _hash(path.read_bytes()) != digest:
                raise ValueError("Immutable source evidence changed: " + name)
    manifest_bytes = (folder / "parts.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if bundle is not None and _hash(manifest_bytes) != bundle.manifest_sha256:
        raise ValueError("Immutable source manifest changed")
    if (
        not isinstance(manifest, dict)
        or type(manifest.get("schema_version")) is not int
        or manifest["schema_version"] != registry.version
    ):
        raise ValueError("Неизвестная версия исходных частей; нужна явная миграция")
    if manifest.get("coordinates") != "metres; Y up; +Z forward; floor Y=0":
        raise ValueError("Несовместимая система координат")
    if (
        manifest.get("rig_reference") != "humanoid_v1"
        and (
            not (
                donor in registry.rpg_ids
                and manifest.get("rig_reference")
                == next(d["contract"] for d in registry.rpg_designs if d["id"] == donor)
            )
        )
        and (
            not (
                donor in registry.species_ids
                and manifest.get("rig_reference")
                == next(
                    d["contract"]
                    for d in [*registry.species_designs, *registry.legacy_species_designs]
                    if d["id"] == donor
                )
            )
        )
    ):
        raise ValueError(
            "Разрешены только humanoid_v1 и исходные головы для производных волколюдей"
        )
    info = manifest["parts"].get(slot)
    if info is None:
        raise ValueError(f"У {donor} нет детали {slot}")
    blobs = {}
    for field in ("model", "recipe"):
        path = (folder / info[field]).resolve()
        if not path.is_relative_to(folder.resolve()):
            raise ValueError("Исходник выходит за пределы персонажа")
        from ..constructor_cache import resolve

        blobs[field] = resolve(path).read_bytes()
    if _hash(blobs["model"]) != info["sha256"]:
        raise ValueError("Изменился исходный GLB; нужна новая версия источника")
    recipe = json.loads(blobs["recipe"])
    if (
        not isinstance(recipe, dict)
        or type(recipe.get("schema_version")) is not int
        or recipe["schema_version"] != registry.version
        or any(c.get("slot") != slot for c in recipe["commands"])
    ):
        raise ValueError("Несовместимая версия или слот исходного рецепта")
    original = glb_arrays(blobs["model"])
    compiled = compile_recipe(recipe)
    if any((not np.array_equal(a, b) for a, b in zip(original, compiled[:3], strict=True))):
        raise ValueError(
            "Исходный рецепт не соответствует утверждённому GLB; нужна ревизия источника"
        )
    record_bytes = (folder / "record.json").read_bytes()
    record = json.loads(record_bytes)
    provenance = {
        "donor": donor,
        "slot": slot,
        "model_sha256": info["sha256"],
        "recipe_sha256": _hash(blobs["recipe"]),
        "manifest_sha256": _hash(manifest_bytes),
        "record_sha256": _hash(record_bytes),
        "recipe": recipe,
        "record": record,
        "reference_files": [],
    }
    for key in ("reference_image",):
        name = record.get(key)
        if isinstance(name, str):
            p = (folder / name).resolve()
            if p.is_relative_to(folder.resolve()) and p.is_file():
                provenance["reference_files"].append(
                    {
                        "path": str(p.relative_to(registry.asset_root)),
                        "sha256": _hash(p.read_bytes()),
                    }
                )
    return (copy.deepcopy(recipe), provenance)
