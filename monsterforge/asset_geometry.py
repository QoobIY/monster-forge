"""Convert source GLB scene geometry for the shared browser viewer, preserving scale."""

from __future__ import annotations

import base64
import io
from functools import lru_cache

import numpy as np
import trimesh

from monster_forge_sdk import AssetStore


@lru_cache(maxsize=24)
def geometry(asset_id: str, release_id: str, *, root=None) -> dict:
    store = AssetStore(root)
    if store.release_id != release_id:
        raise ValueError("Asset release changed; reload the catalog")
    asset = store.get(asset_id)
    if asset.kind != "decoration":
        raise ValueError("Scene preview requires a decoration")
    scene = trimesh.load(store.path(asset_id), force="scene", process=False)
    parts = {}
    bounds = []
    count = 0
    for index, node in enumerate(scene.graph.nodes_geometry):
        transform, name = scene.graph[node]
        mesh = scene.geometry[name]
        if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces):
            continue
        indices = mesh.faces.reshape(-1)
        vertices = trimesh.transform_points(mesh.vertices, transform)[indices]
        normals = mesh.vertex_normals @ np.linalg.inv(transform[:3, :3])
        normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
        normals = normals[indices]
        texture = None
        uv = np.zeros((len(vertices), 2))
        visual = mesh.visual
        if visual.kind == "texture":
            material = visual.material
            factor = getattr(material, "baseColorFactor", None)
            factor = (
                np.ones(3)
                if factor is None
                else np.asarray(factor)[:3].astype(float) / 255
            )
            colors = np.tile(factor, (len(vertices), 1))
            if visual.uv is not None:
                uv = np.asarray(visual.uv)[indices]
            image = getattr(material, "baseColorTexture", None)
            if image is None:
                image = getattr(material, "image", None)
            if image is not None:
                with io.BytesIO() as buffer:
                    image.convert("RGB").save(buffer, format="PNG")
                    texture = base64.b64encode(buffer.getvalue()).decode("ascii")
        elif visual.kind == "vertex":
            colors = np.asarray(visual.vertex_colors)[indices, :3] / 255
        else:
            colors = np.asarray(visual.face_colors)[:, :3].repeat(3, axis=0) / 255
        part = {
            "positions": vertices.astype("float32").reshape(-1).tolist(),
            "normals": normals.astype("float32").reshape(-1).tolist(),
            "colors": colors.astype("float32").reshape(-1).tolist(),
            "uvs": uv.astype("float32").reshape(-1).tolist(),
            "texture": texture,
        }
        parts[str(index)] = {"geometry": part}
        bounds.extend((vertices.min(0), vertices.max(0)))
        count += len(mesh.faces)
    if not parts:
        raise ValueError("Source model contains no triangle meshes")
    b = np.asarray(bounds)
    return {
        "schema_version": 1,
        "source_sha256": store.file(asset_id).sha256,
        "parts": parts,
        "triangles": count,
        "bounds_metres": [b.min(0).tolist(), b.max(0).tolist()],
    }
