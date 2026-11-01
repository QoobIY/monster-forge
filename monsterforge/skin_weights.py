from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

from .contracts import file_sha256, load_humanoid_contract

SCHEMA_VERSION = 1


def _linear_chain(position: float, centers: list[float]) -> list[float]:
    position = min(1.0, max(0.0, float(position)))
    weights = [0.0] * len(centers)
    if position <= centers[0]:
        weights[0] = 1.0
        return weights
    if position >= centers[-1]:
        weights[-1] = 1.0
        return weights
    for index, (left, right) in enumerate(zip(centers, centers[1:], strict=True)):
        if left <= position <= right:
            alpha = (position - left) / max(right - left, 1e-9)
            alpha = alpha * alpha * (3.0 - 2.0 * alpha)
            weights[index], weights[index + 1] = 1.0 - alpha, alpha
            return weights
    raise AssertionError("chain interval was not found")


def _slot_influences(slot: str, vertices: np.ndarray) -> tuple[list[str], np.ndarray]:
    lower, upper = vertices.min(axis=0), vertices.max(axis=0)
    height = max(float(upper[1] - lower[1]), 1e-9)
    bottom_to_top = np.clip((vertices[:, 1] - lower[1]) / height, 0.0, 1.0)
    top_to_bottom = 1.0 - bottom_to_top
    if slot == "head":
        names, centers, coordinate = ["neck", "head"], [0.0, 0.28], bottom_to_top
    elif slot in {"left_arm", "right_arm"}:
        side = slot.removesuffix("_arm")
        names = [f"{side}_shoulder", f"{side}_elbow", f"{side}_hand"]
        centers, coordinate = [0.0, 0.54, 1.0], top_to_bottom
    elif slot in {"left_leg", "right_leg"}:
        side = slot.removesuffix("_leg")
        names = [f"{side}_hip", f"{side}_knee", f"{side}_foot"]
        centers, coordinate = [0.0, 0.53, 1.0], top_to_bottom
    elif slot == "torso":
        names, centers, coordinate = ["pelvis", "spine", "chest", "neck"], [0.0, 0.34, 0.72, 1.0], bottom_to_top
    elif slot == "back_attachment":
        names, centers, coordinate = ["chest"], [0.0], bottom_to_top
    else:
        raise ValueError(f"unsupported humanoid slot: {slot}")
    weights = np.asarray([_linear_chain(value, centers) if len(centers) > 1 else [1.0] for value in coordinate], dtype=np.float32)
    return names, weights


def build_weight_sidecar(model_path: Path, slot: str, *, bind_profile: str = 'canonical') -> dict[str, Any]:
    contract_slot = next((item for item in load_humanoid_contract().slots if item.id == slot), None)
    if contract_slot is None:
        raise ValueError(f"unknown humanoid slot: {slot}")
    loaded = trimesh.load(model_path, force="scene", process=False)
    scene = loaded if isinstance(loaded, trimesh.Scene) else trimesh.Scene(loaded)
    geometries = [scene.geometry[name] for name in sorted(scene.geometry)]
    if len(geometries) != 1 or not isinstance(geometries[0], trimesh.Trimesh):
        raise ValueError("runtime skinning currently requires one exported mesh primitive per body part")
    vertices = np.asarray(geometries[0].vertices, dtype=np.float64)
    names, dense = _slot_influences(slot, vertices)
    bind_metadata = {}
    if bind_profile != 'canonical':
        from .constructor_knees import BIND_PROFILE, skeleton_snapshot, world_bind
        if bind_profile != BIND_PROFILE:
            raise ValueError('Unsupported constructor bind profile')
        _, digest = skeleton_snapshot()
        bind_metadata = {'bind_profile': bind_profile, 'skeleton_sha256': digest}
        if slot in {'left_leg', 'right_leg'}:
            side = slot.removesuffix('_leg')
            bind = world_bind()
            centers = [-bind[side+'_'+joint][1] for joint in ('hip', 'knee', 'foot')]
            dense = np.asarray([_linear_chain(float(np.interp(-v[1], centers, [0, .5, 1])), [0, .5, 1])
                                for v in vertices], dtype=np.float32)
    if set(names) - set(contract_slot.allowed_bones):
        raise ValueError(f"generated weights leave allowed bone set for {slot}")
    palette = tuple(
        dict.fromkeys(
            bone
            for slot_definition in load_humanoid_contract().slots
            for bone in slot_definition.allowed_bones
        )
    )
    bone_indices = {bone: index for index, bone in enumerate(palette)}
    skin_indices = np.zeros((len(vertices), 4), dtype=np.uint16)
    skin_weights = np.zeros((len(vertices), 4), dtype=np.float32)
    for vertex_index, row in enumerate(dense):
        active = sorted(((float(weight), names[index]) for index, weight in enumerate(row) if weight > 1e-7), reverse=True)[:4]
        total = sum(weight for weight, _ in active)
        for influence_index, (weight, bone) in enumerate(active):
            skin_indices[vertex_index, influence_index] = bone_indices[bone]
            skin_weights[vertex_index, influence_index] = weight / total
    sums = skin_weights.sum(axis=1)
    if len(vertices) == 0 or not np.allclose(sums, 1.0, atol=1e-6):
        raise ValueError("skin weights are not normalized")
    return {
        **bind_metadata,
        "schema_version": SCHEMA_VERSION,
        "slot": slot,
        "skeleton_id": "humanoid_v1",
        "model_sha256": file_sha256(model_path),
        "vertex_count": len(vertices),
        "bone_palette": list(palette),
        "allowed_bones": list(contract_slot.allowed_bones),
        "skin_indices": skin_indices.tolist(),
        "skin_weights": np.round(skin_weights, 7).tolist(),
        "method": "slot_axis_piecewise_smooth_v1",
    }


def write_weight_sidecar(model_path: Path, slot: str, target: Path | None = None) -> dict[str, Any]:
    target = target or model_path.with_name("weights.json")
    payload = build_weight_sidecar(model_path, slot)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.replace(target)
    return payload
