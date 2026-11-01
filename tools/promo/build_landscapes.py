"""Author reusable rolling landscapes and organic set dressing in BHM."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image
from trimesh.visual.material import PBRMaterial

from monster_forge_sdk import AssetStore
from monsterforge.paths import ROOT
from tools.assets.bake_character_models import unpack
from tools.materials.build_viking_material_lab import blob_glb


def height(x, y, town):
    distance = max(abs(x) - 20, abs(y - 7) - 29, 0) if town else max(math.hypot(x, y - 1) - 12, 0)
    blend = min(1, distance / 22)
    hills = (
        2.8
        + 2.1 * math.sin(x * 0.055 + 0.4) * math.cos(y * 0.047)
        + 1.3 * math.sin(y * 0.081 + x * 0.027)
    )
    far = min(1, max(0, distance - 65) / 85) if town else 0
    return max(0, hills) * blend * blend + far * (19 + 7 * math.sin(x * 0.017 + y * 0.021))


def road(x, y, town):
    if town:
        # The south cart track follows the valley, then forks beyond the houses.
        center = 3.8 * math.sin(min(0, y + 17) * 0.058)
        south = abs(x - center) if y < -16 else 1000
        east = abs(y - 10 - 4.2 * math.sin((x - 17) * 0.07)) if x > 16 else 1000
        north = abs(x - 1.5 * math.sin(y * 0.08)) if y > 28 else 1000
        return min(south, east, north)
    return abs(x - 2.5 * math.sin((y + 9) * 0.11)) if y < 1 else 1000


def layout(town):
    rng = np.random.default_rng(4817 if town else 8183)
    result = []
    # Rejection sampling makes irregular groves with clearings and cart tracks.
    centers = (
        [(-35, -20), (-34, 12), (-26, 46), (5, 55), (36, 35), (35, 5), (26, -44), (-12, -51)]
        if town
        else [(-21, -7), (-20, 16), (0, 29), (20, 20), (23, -5)]
    )
    for index in range(140 if town else 85):
        x, y = np.array(centers[index % len(centers)]) + rng.normal(0, 8 if town else 6, 2)
        if town and abs(x) < 22 and -23 < y < 39:
            continue
        if not town and (math.hypot(x, y - 1) < 14 or y < -6 and abs(x) < 7):
            continue
        if road(x, y, town) < 4.8:
            continue
        # Preserve the establishing camera's line into town, not a foreground hedge.
        if town and x > 10 and y < -16 and math.hypot(x - 22, y + 28) < 12:
            continue
        pine = rng.random() < 0.34
        result.append(
            {
                "asset": "decoration.woodland.pine" if pine else "decoration.woodland.oak",
                "position": [float(x), float(y), height(x, y, town)],
                "height": float(rng.uniform(7, 13) if town else rng.uniform(6, 11)),
                "heading": float(rng.uniform(-180, 180)),
            }
        )
        if rng.random() < 0.62:
            bx, by = x + rng.uniform(-2, 2), y + rng.uniform(-2, 2)
            result.append(
                {
                    "asset": "decoration.woodland.fern",
                    "position": [float(bx), float(by), height(bx, by, town)],
                    "height": float(rng.uniform(0.6, 1.3)),
                    "heading": float(rng.uniform(0, 360)),
                }
            )
    for _ in range(24 if town else 17):
        x, y = rng.uniform(-60 if town else -24, 60 if town else 24, 2)
        if town and abs(x) < 20 and -19 < y < 36 or not town and abs(x) < 6 and -12 < y < 11:
            continue
        result.append(
            {
                "asset": "decoration.woodland.boulder",
                "position": [float(x), float(y), height(x, y, town) - 0.15],
                "height": float(rng.uniform(0.7, 2.8)),
                "heading": float(rng.uniform(0, 360)),
            }
        )
    if not town:
        for x, y, h, angle in [
            (-8, 6, 4, 24),
            (9, 8, 3.3, -31),
            (-11, 1, 2.8, 50),
            (12, 0, 2.4, -25),
        ]:
            result.append(
                {
                    "asset": "decoration.mom_rpg.hollow_crypt.broken_arch",
                    "position": [x, y, height(x, y, False)],
                    "height": h,
                    "heading": angle,
                }
            )
        for side in (-1, 1):
            for y in (-3, 6, 12):
                x = side * (8.3 + math.sin(y) * 1.1)
                result.append(
                    {
                        "asset": "decoration.mom_rpg.hollow_crypt.rune_stone.v4",
                        "position": [x, y, height(x, y, False)],
                        "height": 1.8 if y < 10 else 2.5,
                        "heading": side * 18,
                    }
                )
    return result


def build(town):
    name = "town_valley" if town else "forest_portal"
    store = AssetStore(ROOT)
    radius, step = (130, 3) if town else (66, 2)
    axis = np.arange(-radius, radius + 0.01, step)
    if town:
        axis = np.unique(np.concatenate((np.arange(-364, -130, 9), axis, np.arange(131, 365, 9))))
        radius = 364
    vertices = np.array([[x, height(x, y, town), -y] for y in axis for x in axis])
    groups = [[], [], []]
    width = len(axis)
    for row in range(width - 1):
        for col in range(width - 1):
            a = row * width + col
            for face in ([a, a + 1, a + width], [a + 1, a + width + 1, a + width]):
                groups[0].append(face)
    # Continuous narrow ribbons follow the relief; terrain cells never decide
    # road coverage, so the track has no checkerboard gaps or triangular corners.
    points = vertices.tolist()
    routes = (
        [("south", -radius, -16), ("north", 28, radius), ("east", 16, radius)]
        if town
        else [("portal", -radius, 1)]
    )
    for route, start, end in routes:
        samples = np.arange(start, end + 0.1, 0.7)
        first = len(points)
        for t in samples:
            width_scale = 1 + 0.11 * math.sin(t * 0.21)
            for offset in (-2.05, -1.45, 1.45, 2.05):
                o = offset * width_scale
                if route == "east":
                    x, y = t, 10 + 4.2 * math.sin((t - 17) * 0.07) + o
                else:
                    center = (
                        3.8 * math.sin(min(0, t + 17) * 0.058)
                        if route == "south"
                        else 1.5 * math.sin(t * 0.08)
                        if route == "north"
                        else 2.5 * math.sin((t + 9) * 0.11)
                    )
                    x, y = center + o, t
                points.append([x, height(x, y, town) + 0.035, -y])
        for row in range(len(samples) - 1):
            for col in range(3):
                a = first + row * 4 + col
                role = 1 if col == 1 else 2
                groups[role].extend(([a, a + 4, a + 1], [a + 1, a + 4, a + 5]))
    vertices = np.array(points)
    scene = trimesh.Scene()
    for i, (label, terrain) in enumerate(
        [("foliage", "meadow" if town else "moss"), ("earth", "earth"), ("road_verge", "moss")]
    ):
        mesh = trimesh.Trimesh(vertices=vertices.copy(), faces=groups[i], process=False)
        mesh.remove_unreferenced_vertices()
        downward = mesh.face_normals[:, 1] < 0
        mesh.faces[downward] = mesh.faces[downward][:, ::-1]
        texture = Image.open(store.path("terrain.v3." + terrain, "image")).convert("RGB")
        uv = mesh.vertices[:, [0, 2]] / 8
        mesh.visual = trimesh.visual.TextureVisuals(
            uv=uv,
            material=PBRMaterial(
                name=label,
                baseColorTexture=texture,
                baseColorFactor=[184, 168, 133, 255] if i == 1 else [255, 255, 255, 255],
                roughnessFactor=0.94,
            ),
        )
        scene.add_geometry(mesh, geom_name=label, node_name=label)
    doc, binary = unpack(scene.export(file_type="glb"))
    doc["meshes"] = [
        {"name": name, "primitives": [p for m in doc["meshes"] for p in m["primitives"]]}
    ]
    doc["nodes"] = [{"mesh": 0, "name": name}]
    doc["scenes"] = [{"nodes": [0]}]
    doc["scene"] = 0
    raw = blob_glb(doc, binary)
    identity = "decoration.shared.landscapes." + name
    folder = ROOT / "media/decorations/shared/landscapes" / name
    folder.mkdir(parents=True, exist_ok=True)
    files = {}
    recipe = {
        "schema_version": 1,
        "builder": "tools/promo/build_landscapes.py",
        "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "coordinates": "Y-up; metres; scene layout Z-up",
        "radius": radius,
        "height_range": [float(vertices[:, 1].min()), float(vertices[:, 1].max())],
        "triangles": sum(len(g) for g in groups),
        "props": layout(town),
    }
    for role, payload, suffix, mime in [
        ("model", raw, ".glb", "model/gltf-binary"),
        (
            "layout",
            (json.dumps(recipe, ensure_ascii=False, indent=2) + "\n").encode(),
            ".json",
            "application/json",
        ),
    ]:
        digest = hashlib.sha256(payload).hexdigest()
        path = folder / (role + "." + digest[:24] + suffix)
        if path.exists() and path.read_bytes() != payload:
            raise ValueError("Immutable landscape collision")
        path.write_bytes(payload)
        files[role] = {
            "path": path.relative_to(ROOT / "media").as_posix(),
            "sha256": digest,
            "size_bytes": len(payload),
            "media_type": mime,
        }
    path = ROOT / "media/catalog.json"
    catalog = json.loads(path.read_text())
    old = next((e for e in catalog["assets"] if e["id"] == identity), None)
    entry = {
        "id": identity,
        "kind": "decoration",
        "group": "Общие декорации",
        "title": "Городская долина" if town else "Лесное святилище портала",
        "revision": 1
        if old is None
        else old["revision"]
        + int(old["files"]["model"] != files["model"] or old["files"]["layout"] != files["layout"]),
        "tags": ["landscape", "shared", "forest"],
        "files": {**(old["files"] if old else {}), **files},
    }
    catalog["assets"] = [e for e in catalog["assets"] if e["id"] != identity] + [entry]
    pending = path.with_suffix(".next")
    pending.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    pending.replace(path)
    print(identity, len(recipe["props"]), "props", recipe["triangles"], "triangles", flush=True)


if __name__ == "__main__":
    build(True)
    build(False)
