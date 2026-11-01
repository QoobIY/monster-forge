"""Publish a low-poly open hero pavilion with an interior fountain to BHM."""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import trimesh
from monster_forge_sdk import AssetStore

ROOT = Path(__file__).resolve().parents[2]


def single_node(tree):
    tree["nodes"] = [{"name": "hero_altar", "mesh": 0}]
    tree["scenes"] = [{"nodes": [0]}]


def build(root=ROOT):
    store = AssetStore(root)
    donor = next(
        asset
        for asset in store.list("decoration")
        if any(
            ref.sha256.startswith("cabb8262087689bc423f5336")
            for ref in asset.files.values()
        )
    )
    meshes = []
    stone = (173, 181, 176, 255)
    dark = (57, 92, 83, 255)
    gold = (216, 177, 92, 255)

    def add(mesh, color):
        mesh.visual.vertex_colors = np.tile(
            np.array(color, dtype=np.uint8), (len(mesh.vertices), 1)
        )
        meshes.append(mesh)

    def box(size, point, color):
        mesh = trimesh.creation.box(size)
        mesh.apply_translation(point)
        add(mesh, color)

    def cylinder(radius, height, point, color, sections=12):
        mesh = trimesh.creation.cylinder(radius, height, sections=sections)
        mesh.apply_transform(
            trimesh.transformations.rotation_matrix(math.pi / 2, (1, 0, 0))
        )
        mesh.apply_translation(point)
        add(mesh, color)

    box((7.5, 0.22, 5.8), (0, 0.11, 0), stone)
    box((6.9, 0.16, 5.3), (0, 0.30, 0), (130, 146, 139, 255))
    box((3.8, 0.17, 1.2), (0, 0.16, 3.1), stone)
    box((4.3, 0.12, 0.65), (0, 0.06, 3.7), stone)
    for x in (-3, 3):
        for z in (-2.15, 2.15):
            box((0.9, 0.35, 0.9), (x, 0.54, z), dark)
            box((0.56, 2.1, 0.56), (x, 1.76, z), stone)
            box((0.76, 0.16, 0.76), (x, 2.86, z), gold)
            box((0.85, 0.22, 0.85), (x, 3.03, z), dark)
        box((0.42, 0.28, 4.8), (x, 3.22, 0), dark)
        box((0.48, 0.08, 4.9), (x, 3.43, 0), gold)
    # Two vaults leave the roof and front open so the fountain remains visible.
    for z in (-2.15, 2.15):
        for i in range(12):
            a, b = i * math.pi / 12, (i + 1) * math.pi / 12
            vertices = []
            for depth in (-0.22, 0.22):
                for radius, angle in ((2.56, a), (2.9, a), (2.9, b), (2.56, b)):
                    vertices.append(
                        (
                            radius * math.cos(angle),
                            2.65 + radius * 0.42 * math.sin(angle),
                            z + depth,
                        )
                    )
            faces = [
                [0, 1, 2],
                [0, 2, 3],
                [4, 6, 5],
                [4, 7, 6],
                [0, 4, 5],
                [0, 5, 1],
                [1, 5, 6],
                [1, 6, 2],
                [2, 6, 7],
                [2, 7, 3],
                [3, 7, 4],
                [3, 4, 0],
            ]
            add(
                trimesh.Trimesh(vertices=vertices, faces=faces, process=False),
                stone if i % 3 else gold,
            )
    fountain = trimesh.load(store.path(donor.id), force="mesh", process=False)
    fountain.visual = fountain.visual.to_color()
    fountain.apply_scale(1.42)
    fountain.apply_translation((0, 0.38 - fountain.bounds[0, 1], -0.25))
    meshes.append(fountain)
    cylinder(0.78, 0.035, (0, 0.75, -0.25), (52, 187, 205, 255))
    # A faceted blue core over the basin, with small golden votive stands.
    gem = trimesh.creation.icosphere(subdivisions=0, radius=0.30)
    gem.apply_scale((0.7, 1.4, 0.7))
    gem.apply_translation((0, 1.68, -0.25))
    add(gem, (78, 209, 215, 255))
    for x in (-1.9, 1.9):
        cylinder(0.28, 0.4, (x, 0.58, -1.25), dark, 8)
        cylinder(0.38, 0.10, (x, 0.85, -1.25), gold, 8)
        flame = trimesh.creation.icosphere(subdivisions=0, radius=0.22)
        flame.apply_scale((0.65, 1.65, 0.65))
        flame.apply_translation((x, 1.15, -1.25))
        add(flame, (244, 185, 75, 255))
    mesh = trimesh.util.concatenate(meshes)
    folder = root / "media/decorations/mom_rpg/v3/hero_altar"
    folder.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": 1,
        "style": "Unified low-poly project style",
        "id": "hero_altar",
        "source_fountain": donor.id,
        "layout": "open stone pavilion, two vaults, interior fountain, blue core, gold votives",
        "coordinates": "Y-up",
        "bounds": mesh.bounds.tolist(),
    }
    files = {}
    for role, name, payload, mime in [
        (
            "model",
            "model.glb",
            mesh.export(file_type="glb", tree_postprocessor=single_node),
            "model/gltf-binary",
        ),
        (
            "recipe",
            "recipe.json",
            (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode(),
            "application/json",
        ),
    ]:
        path = folder / name
        if path.exists() and path.read_bytes() != payload:
            raise ValueError("Immutable altar changed")
        path.write_bytes(payload)
        files[role] = {
            "path": path.relative_to(root / "media").as_posix(),
            "size_bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "media_type": mime,
        }
    catalog = root / "media/imported_catalog.json"
    data = json.loads(catalog.read_text())
    entry = {
        "id": "decoration.mom_rpg.hero_altar.v3",
        "kind": "decoration",
        "title": "Дом героев · Алтарь с фонтаном",
        "revision": 1,
        "group": "MOM RPG",
        "tags": [
            "city",
            "building",
            "heroes",
            "altar",
            "fountain",
            "mom_rpg",
            "low-poly",
        ],
        "files": files,
    }
    old = next((asset for asset in data["assets"] if asset["id"] == entry["id"]), None)
    if old and old != entry:
        raise ValueError("Immutable altar catalog changed")
    if not old:
        data["assets"].append(entry)
    catalog.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    from build_catalog import build_catalog

    build_catalog(root)
    print("Published hero altar:", len(mesh.faces), "triangles")


if __name__ == "__main__":
    build()
