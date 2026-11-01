"""Publish original modular swamp monsters and scenery on the humanoid bind contract."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import trimesh

from tools.assets.build_catalog import build_catalog
from tools.assets.build_mom_skins import bounded_weights
from tools.assets.build_rpg_locations import Prop, single_node

ROOT = Path(__file__).resolve().parents[2]
GREEN = (91, 119, 46, 255)
DARK = (39, 60, 35, 255)
PALE = (183, 181, 108, 255)
GOLD = (192, 151, 57, 255)
BLACK = (18, 27, 21, 255)
TEAL = (54, 132, 119, 255)
SLIME = (111, 156, 51, 255)
SLOTS = ("head", "torso", "left_arm", "right_arm", "left_leg", "right_leg")


class Shape(Prop):
    def ellipsoid(self, point, scale, color, detail=1):
        mesh = trimesh.creation.icosphere(subdivisions=detail, radius=1)
        mesh.apply_scale(scale)
        self.add(mesh, color, point)

    def branch(self, start, end, radius, color, sections=7):
        start, end = np.array(start, float), np.array(end, float)
        mesh = trimesh.creation.cylinder(radius, np.linalg.norm(end - start), sections=sections)
        mesh.apply_transform(trimesh.geometry.align_vectors((0, 0, 1), end - start))
        self.add(mesh, color, (start + end) / 2)

    def finish(self):
        mesh = trimesh.util.concatenate(self.meshes)
        mesh.fix_normals()
        mesh.unmerge_vertices()
        if not np.isfinite(mesh.vertices).all() or len(mesh.faces) > 7000:
            raise ValueError("swamp mesh budget")
        return mesh


def monster(kind, slot):
    shape = Shape()
    king = kind == "frog_king"
    goo = kind == "acid_slime"
    skin = SLIME if goo else GREEN
    if slot == "head":
        if goo:
            shape.ellipsoid((0, 1.95, 0.1), (0.37, 0.23, 0.32), skin)
            for x in (-0.16, 0.16):
                shape.ellipsoid((x, 2.02, 0.36), (0.085, 0.095, 0.04), BLACK)
            shape.ellipsoid((0, 1.87, 0.39), (0.15, 0.055, 0.07), DARK)
        else:
            shape.ellipsoid((0, 2.20, 0.17), (0.58 if king else 0.51, 0.31, 0.42), skin)
            shape.ellipsoid((0, 2.04, 0.32), (0.45, 0.12, 0.32), PALE)
            for sign in (-1, 1):
                x = sign * 0.36
                shape.ellipsoid((x, 2.45, 0.25), (0.19, 0.20, 0.18), DARK)
                shape.ellipsoid((x, 2.46, 0.38), (0.135, 0.13, 0.055), GOLD)
                shape.ellipsoid((x, 2.46, 0.429), (0.038, 0.11, 0.018), BLACK)
                shape.branch((sign * 0.08, 2.10, 0.628), (sign * 0.40, 2.12, 0.54), 0.021, DARK)
            if king:
                shape.cylinder(0.41, 0.12, (0, 2.57, 0.10), GOLD)
                for i in range(7):
                    a = i * math.tau / 7
                    shape.cone(
                        0.085, 0.31, (0.34 * math.cos(a), 2.63, 0.10 + 0.34 * math.sin(a)), GOLD, 4
                    )
                shape.ellipsoid((0, 2.58, 0.51), (0.12, 0.13, 0.05), TEAL, 0)
    elif slot == "torso":
        if goo:
            shape.ellipsoid((0, 1.03, 0.05), (0.73, 1.03, 0.63), skin)
            shape.ellipsoid((-0.35, 0.32, 0.20), (0.56, 0.31, 0.48), skin)
            shape.ellipsoid((0.32, 0.32, 0.12), (0.53, 0.31, 0.49), skin)
            for x, y, z, r in (
                (-0.35, 1.47, 0.44, 0.17),
                (0.2, 1.35, 0.52, 0.20),
                (0.38, 0.74, 0.50, 0.13),
            ):
                shape.ellipsoid((x, y, z), (r, r, r * 0.4), (162, 184, 64, 255), 0)
        else:
            width = 0.61 if king else 0.47
            shape.ellipsoid((0, 1.36, 0.03), (width, 0.59, 0.41), skin)
            shape.ellipsoid((0, 1.34, 0.34), (width * 0.8, 0.49, 0.105), PALE)
            shape.ellipsoid((0, 1.91, 0.08), (0.24, 0.17, 0.23), skin)
            for x in (-0.32, 0, 0.32):
                shape.ellipsoid((x, 1.48, -0.35), (0.10, 0.14, 0.09), DARK, 0)
            if king:
                shape.branch((-0.48, 1.58, 0.33), (0.42, 1.05, 0.35), 0.065, GOLD)
    else:
        side, limb = slot.split("_")
        sign = -1 if side == "left" else 1
        if limb == "arm":
            shape.branch(
                (sign * 0.36, 1.79, 0.04), (sign * 0.72, 1.36, 0.02), 0.19 if king else 0.15, skin
            )
            shape.ellipsoid((sign * 0.72, 1.36, 0.02), (0.18, 0.16, 0.16), skin)
            shape.branch((sign * 0.72, 1.36, 0.02), (sign * 0.82, 0.96, 0.08), 0.12, skin)
            shape.ellipsoid((sign * 0.82, 0.94, 0.12), (0.20, 0.12, 0.18), skin)
            for i in range(3):
                z = -0.02 + i * 0.14
                shape.branch((sign * 0.82, 0.93, z), (sign * 1.03, 0.84, z + 0.03), 0.046, skin, 5)
                shape.ellipsoid(
                    (sign * 1.04, 0.84, z + 0.03),
                    (0.065, 0.045, 0.065),
                    PALE if not goo else SLIME,
                    0,
                )
        else:
            shape.branch(
                (sign * 0.22, 0.96, 0), (sign * 0.28, 0.48, 0.02), 0.25 if not goo else 0.11, skin
            )
            shape.ellipsoid((sign * 0.28, 0.48, 0.02), (0.20, 0.17, 0.18), skin)
            shape.branch((sign * 0.28, 0.48, 0.02), (sign * 0.32, 0.10, 0.18), 0.13, skin)
            shape.ellipsoid((sign * 0.32, 0.09, 0.30), (0.24, 0.09, 0.38), skin)
            for i in range(3):
                x = sign * 0.32 + (i - 1) * 0.15
                shape.branch((sign * 0.32, 0.09, 0.32), (x, 0.06, 0.64), 0.06, skin, 5)
    return shape.finish()


def prop(name):
    p = Shape()
    if name == "bubble":
        # Hollow geometric shell and sharp highlights remain readable over wet terrain.
        for axis in range(3):
            for i in range(20):
                a, b = i * math.tau / 20, (i + 1) * math.tau / 20

                def point(t, axis=axis):
                    v = [0.55 * math.cos(t), 0.55 * math.sin(t), 0]
                    if axis == 0:
                        v[1], v[2] = v[2], v[1]
                    elif axis == 1:
                        v[0], v[2] = v[2], v[0]
                    return (v[0], v[1] + 0.85, v[2])

                p.branch(point(a), point(b), 0.026, (124, 188, 150, 255), 5)
        p.ellipsoid((-0.22, 1.12, 0.32), (0.08, 0.16, 0.025), (221, 236, 180, 255), 0)
    elif name == "reeds":
        for i in range(9):
            a = i * 2.39996
            x, z = math.cos(a) * (0.1 + i * 0.045), math.sin(a) * (0.1 + i * 0.045)
            top = 0.7 + (i % 4) * 0.27
            p.branch((x, 0, z), (x + 0.1, top, z + 0.08), 0.025, GREEN, 5)
            p.branch((x + 0.1, top * 0.75, z + 0.08), (x + 0.1, top, z + 0.08), 0.07, DARK, 6)
            p.branch((x, 0.22, z), (x + 0.35, top * 0.62, z + 0.17), 0.035, GREEN, 4)
    elif name == "lily":
        p.cylinder(0.65, 0.035, (0, 0.025, 0), (67, 112, 53, 255), 9)
        for i in range(6):
            a = i * math.tau / 6
            p.ellipsoid(
                (0.14 * math.cos(a), 0.14, 0.14 * math.sin(a)),
                (0.15, 0.08, 0.12),
                (172, 169, 93, 255),
                0,
            )
        p.ellipsoid((0, 0.17, 0), (0.09, 0.12, 0.09), GOLD, 0)
    elif name == "pool":
        p.cylinder(1, 0.035, (0, 0, 0), (47, 91, 76, 255), 18)
        p.ellipsoid((-0.2, 0.03, 0.2), (0.42, 0.012, 0.23), (66, 116, 92, 255), 1)
    elif name == "willow":
        wood = (77, 72, 43, 255)
        p.branch((0, 0, 0), (0.15, 2.7, 0.1), 0.25, wood)
        for sign in (-1, 1):
            p.branch((0.12, 1.6, 0.05), (sign * 1.15, 3.15, 0.2), 0.12, wood)
            p.branch((sign * 1.15, 3.15, 0.2), (sign * 1.65, 2.75, 0.55), 0.075, wood)
            for i in range(4):
                x = sign * (1.0 + 0.2 * i)
                p.branch((x, 3.0 - i * 0.09, 0.25), (x, 1.1 + i * 0.13, 0.42), 0.05, GREEN, 5)
        p.ellipsoid((0.12, 3.0, 0.1), (1.5, 0.48, 0.9), DARK, 1)
    elif name == "boardwalk":
        for i in range(7):
            p.box((2.1, 0.14, 0.40), (0, 0.12, i * 0.46 - 1.4), (106 + i % 2 * 13, 91, 57, 255))
        for x in (-0.83, 0.83):
            p.box((0.16, 0.17, 3.2), (x, 0.02, 0), DARK)
    elif name == "spear":
        p.branch((0, -0.78, 0), (0, 1.82, 0), 0.055, (89, 75, 46, 255))
        p.cone(0.19, 0.62, (0, 1.82, 0), (88, 162, 112, 255), 4)
        for y in (-0.12, 0.12, 0.36):
            p.cylinder(0.073, 0.12, (0, y, 0), DARK, 6)
    else:
        raise ValueError(name)
    return p.finish()


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def build(root=ROOT):
    builder = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    labels = {
        "acid_slime": "Болотная тварь",
    }
    for name, label in labels.items():
        folder = root / "media/constructor/mom_rpg/v1/swamp" / name
        (folder / "parts").mkdir(parents=True, exist_ok=True)
        parts = {}
        for slot in SLOTS:
            model = folder / "parts" / (slot + ".glb")
            mesh = monster(name, slot)
            blob = mesh.export(file_type="glb", tree_postprocessor=single_node)
            if model.exists() and model.read_bytes() != blob:
                raise ValueError("Immutable swamp part changed: " + str(model))
            model.write_bytes(blob)
            write_json(
                model.with_suffix(".recipe.json"),
                {
                    "schema_version": 1,
                    "id": name + "." + slot,
                    "kind": "procedural_swamp_anatomy",
                    "bind_profile": "canonical",
                    "builder_sha256": builder,
                    "triangles": len(mesh.faces),
                    "bounds": mesh.bounds.tolist(),
                },
            )
            write_json(
                model.with_suffix(".weights.json"), bounded_weights(model, slot, "canonical")
            )
            parts[slot] = {"model": "parts/" + slot + ".glb"}
        write_json(
            folder / "record.json",
            {
                "schema_version": 1,
                "id": name,
                "label": label,
                "race": "slime" if name == "acid_slime" else "frog",
                "rig": "humanoid_v1",
                "bind_profile": "canonical",
                "parts": parts,
                "tags": ["mom_rpg", "swamp", "mutant"],
                "design_note": "Original faceted swamp anatomy; shared humanoid bind, no human garment donors",
            },
        )
        print("Constructor:", name, flush=True)
    catalog_path = root / "media/imported_catalog.json"
    catalog = json.loads(catalog_path.read_text())
    for name in ("bubble", "reeds", "lily", "pool", "willow", "boardwalk", "spear"):
        folder = root / "media/decorations/mom_rpg/swamp" / name / "v1"
        folder.mkdir(parents=True, exist_ok=True)
        mesh = prop(name)
        identity = "decoration.mom_rpg.swamp." + name
        files = {}
        for role, file, blob, mime in [
            (
                "model",
                "model.glb",
                mesh.export(file_type="glb", tree_postprocessor=single_node),
                "model/gltf-binary",
            ),
            (
                "recipe",
                "recipe.json",
                (
                    json.dumps(
                        {
                            "schema_version": 1,
                            "id": identity,
                            "builder_sha256": builder,
                            "triangles": len(mesh.faces),
                            "coordinates": "metres, Y up",
                            "style": "BHM faceted matte swamp",
                        },
                        indent=2,
                    )
                    + "\n"
                ).encode(),
                "application/json",
            ),
        ]:
            path = folder / file
            if path.exists() and path.read_bytes() != blob:
                raise ValueError("Immutable swamp prop changed")
            path.write_bytes(blob)
            files[role] = {
                "path": path.relative_to(root / "media").as_posix(),
                "sha256": hashlib.sha256(blob).hexdigest(),
                "size_bytes": len(blob),
                "media_type": mime,
            }
        row = {
            "id": identity,
            "kind": "decoration",
            "title": "Болото · " + name,
            "revision": 1,
            "group": "MOM RPG",
            "tags": ["mom_rpg", "swamp", "procedural"],
            "files": files,
        }
        if not any(a["id"] == identity for a in catalog["assets"]):
            catalog["assets"].append(row)
    write_json(catalog_path, catalog)
    from tools.assets.build_swamp_frogs import publish

    publish(root, catalog=False)
    build_catalog(root)
    print("Published baked swamp bodies and scenery", flush=True)


if __name__ == "__main__":
    build()
