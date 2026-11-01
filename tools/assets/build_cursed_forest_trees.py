"""Publish original dead thornwood scenery and cursed treants for MOM RPG."""

import hashlib
import json
import math
from pathlib import Path

from tools.assets.build_catalog import build_catalog
from tools.assets.build_mom_skins import bounded_weights
from tools.assets.build_rpg_locations import single_node
from tools.assets.build_swamp_models import SLOTS, Shape, write_json

ROOT = Path(__file__).resolve().parents[2]
BARK = (48, 39, 43, 255)
LIGHT = (73, 58, 62, 255)
CUT = (101, 80, 66, 255)
DARK = (17, 13, 22, 255)
CURSE = (139, 65, 180, 255)
HOT = (208, 153, 222, 255)
LEAF = (71, 52, 70, 255)


def limb(p, points, radius, color=BARK):
    for i in range(len(points) - 1):
        r = radius * (1 - i / (len(points) + 0.3) * 0.78)
        p.branch(points[i], points[i + 1], r, color, 7)
        if i:
            p.ellipsoid(points[i], (r * 1.1,) * 3, color, 0)


def face(p, y, width):
    for s in [-1, 1]:
        p.ellipsoid((s * width * 0.35, y, 0.285), (0.14, 0.095, 0.05), DARK, 0)
        p.ellipsoid((s * width * 0.35, y + 0.008, 0.328), (0.085, 0.026, 0.025), CURSE, 0)
        p.ellipsoid((s * width * 0.35, y + 0.012, 0.348), (0.027, 0.018, 0.01), HOT, 0)
    p.ellipsoid((0, y - 0.23, 0.28), (0.13, 0.16, 0.055), DARK, 0)
    for s in [-1, 1]:
        limb(
            p,
            [(s * 0.06, y - 0.31, 0.34), (s * 0.13, y - 0.2, 0.33), (s * 0.07, y - 0.1, 0.32)],
            0.022,
            CUT,
        )


def monster(slot, ancient):
    p = Shape()
    width = 0.46 if ancient else 0.35
    if slot == "torso":
        limb(p, [(0, 0.75, 0), (-0.055, 1.15, -0.02), (0.035, 1.62, 0), (0, 1.94, 0)], width)
        for i in range(7):
            a = i * math.tau / 7
            limb(
                p,
                [
                    (math.cos(a) * width * 0.7, 0.8, math.sin(a) * width * 0.7),
                    (math.cos(a) * width, 1.28, math.sin(a) * width),
                    (math.cos(a + 0.12) * width * 0.72, 1.8, math.sin(a + 0.12) * width * 0.72),
                ],
                0.065,
                LIGHT if i % 2 else BARK,
            )
        limb(
            p,
            [
                (-0.09, 1.0, width + 0.012),
                (0.04, 1.25, width + 0.012),
                (-0.07, 1.5, width + 0.012),
                (0.03, 1.67, width + 0.012),
            ],
            0.018,
            CURSE,
        )
    elif slot == "head":
        p.ellipsoid((0, 2.13, 0.0), (0.34 if ancient else 0.29, 0.32, 0.29), BARK)
        face(p, 2.2, 0.34)
        for s in [-1, 1]:
            limb(
                p,
                [
                    (s * 0.15, 2.33, -0.06),
                    (s * 0.33, 2.65, -0.08),
                    (s * 0.54, 2.76, -0.03),
                    (s * 0.50, 3.0, 0.02),
                ],
                0.095,
                LIGHT,
            )
            limb(
                p,
                [(s * 0.33, 2.65, -0.08), (s * 0.19, 2.81, -0.2), (s * 0.28, 2.99, -0.26)],
                0.048,
                CUT,
            )
        if ancient:
            limb(p, [(0, 2.35, -0.1), (0.06, 2.68, -0.21), (-0.12, 2.93, -0.24)], 0.09)
    else:
        s = -1 if slot.startswith("left") else 1
        if slot.endswith("arm"):
            limb(
                p,
                [
                    (s * 0.34, 1.76, 0),
                    (s * 0.48, 1.63, -0.1),
                    (s * 0.65, 1.35, 0),
                    (s * 0.82, 1.00, 0.06),
                ],
                0.18 if ancient else 0.14,
            )
            limb(
                p,
                [(s * 0.49, 1.61, -0.09), (s * 0.71, 1.88, -0.15), (s * 0.86, 1.96, -0.03)],
                0.065,
                CUT,
            )
            for j in range(3):
                z = -0.08 + j * 0.14
                limb(
                    p,
                    [
                        (s * 0.81, 1.02, z),
                        (s * (1.01 + j * 0.04), 0.79, z + 0.08),
                        (s * (0.94 + j * 0.045), 0.67, z + 0.22),
                    ],
                    0.065,
                    LIGHT,
                )
        else:
            limb(
                p,
                [(s * 0.2, 1, 0), (s * 0.30, 0.56, -0.06), (s * 0.30, 0.12, 0.06)],
                0.21 if ancient else 0.17,
            )
            for j in range(3):
                a = j * 1.8
                end = (s * 0.3 + math.cos(a) * 0.38, 0.025, 0.16 + math.sin(a) * 0.37)
                limb(
                    p,
                    [(s * 0.3, 0.18, 0.06), ((end[0] + s * 0.3) / 2, 0.07, end[2] * 0.7), end],
                    0.09,
                    LIGHT,
                )
    return p.finish()


def scenery(variant):
    p = Shape()
    height = 4.8 if variant == 0 else 5.6
    points = [
        (0, 0, 0),
        (0.14, 1.0, -0.04),
        (-0.23, 2.1, 0.09),
        (0.13, 3.0, 0.0),
        (-0.2, height - 0.7, 0.12),
        (-0.05, height, 0),
    ]
    limb(p, points, 0.43 if variant == 0 else 0.32)
    for i in range(7):
        a = i * math.tau / 7 + variant * 0.3
        c, s = math.cos(a), math.sin(a)
        limb(p, [(0, 0.28, 0), (c * 0.6, 0.08, s * 0.6), (c * 1.2, 0.015, s * 1.2)], 0.15, LIGHT)
    for i in range(7):
        a = i * math.tau / 7
        c, s = math.cos(a), math.sin(a)
        y = 2.0 + i * 0.23
        tip = (c * (1.7 if variant == 0 else 1.2), y + 1.1, s * 1.6)
        middle = (c * 0.8, y + 0.4, s * 0.7)
        limb(
            p,
            [(0, y, 0), middle, tip, (tip[0] * 1.14, tip[1] + 0.45, tip[2] * 1.15)],
            0.16 if variant == 0 else 0.12,
        )
        fork = (middle[0] + s * 0.6, middle[1] + 0.7, middle[2] - c * 0.6)
        limb(p, [middle, fork, (fork[0] * 1.15, fork[1] + 0.4, fork[2] * 1.1)], 0.07, LIGHT)
        if i % 3 == 0:
            p.ellipsoid((tip[0], tip[1] - 0.12, tip[2]), (0.22, 0.12, 0.21), LEAF, 0)
    for s in [-1, 1]:
        limb(
            p,
            [
                (s * 0.16, 0.9, 0.32),
                (s * 0.07, 1.3, 0.34),
                (s * 0.17, 1.55, 0.27),
                (s * 0.08, 1.87, 0.26),
            ],
            0.025,
            DARK,
        )
        limb(
            p,
            [
                (s * 0.16, 0.9, 0.343),
                (s * 0.07, 1.3, 0.36),
                (s * 0.17, 1.55, 0.293),
                (s * 0.08, 1.87, 0.28),
            ],
            0.012,
            CURSE,
        )
    return p.finish()


def publish():
    digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    for name, ancient in [("cursed_tree", False), ("ancient_tree", True)]:
        directory = ROOT / "media/constructor/mom_rpg/v1/forest" / name
        (directory / "parts").mkdir(parents=True, exist_ok=True)
        for slot in SLOTS:
            path = directory / "parts" / (slot + ".glb")
            mesh = monster(slot, ancient)
            blob = mesh.export(file_type="glb", tree_postprocessor=single_node)
            if path.exists() and path.read_bytes() != blob:
                raise ValueError("Immutable cursed treant changed")
            path.write_bytes(blob)
            write_json(path.with_suffix(".weights.json"), bounded_weights(path, slot, "canonical"))
            write_json(
                path.with_suffix(".recipe.json"),
                {
                    "schema_version": 1,
                    "builder_sha256": digest,
                    "triangles": len(mesh.faces),
                    "design": "twisted trunk, root feet, thorn branch fingers, hollow glowing curse eyes; no green foliage",
                },
            )
        write_json(
            directory / "record.json",
            {
                "schema_version": 1,
                "id": name,
                "label": "Древнее проклятое дерево" if ancient else "Проклятое дерево",
                "race": "tree",
                "rig": "humanoid_v1",
                "bind_profile": "canonical",
                "parts": {s: {"model": "parts/" + s + ".glb"} for s in SLOTS},
                "tags": ["mom_rpg", "forest", "cursed"],
            },
        )
    catalog_path = ROOT / "media/imported_catalog.json"
    catalog = json.loads(catalog_path.read_text())
    for variant, name in enumerate(["crooked_elm", "dead_pine"]):
        directory = ROOT / "media/decorations/mom_rpg/forest" / name / "v1"
        directory.mkdir(parents=True, exist_ok=True)
        mesh = scenery(variant)
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
                            "builder_sha256": digest,
                            "triangles": len(mesh.faces),
                            "design": "dead twisted thornwood, charcoal bark, violet curse cracks, sparse withered leaves",
                        },
                        indent=2,
                    )
                    + "\n"
                ).encode(),
                "application/json",
            ),
        ]:
            path = directory / file
            if path.exists() and path.read_bytes() != blob:
                raise ValueError("Immutable cursed scenery changed")
            path.write_bytes(blob)
            files[role] = {
                "path": path.relative_to(ROOT / "media").as_posix(),
                "sha256": hashlib.sha256(blob).hexdigest(),
                "size_bytes": len(blob),
                "media_type": mime,
            }
        identity = "decoration.mom_rpg.forest." + name
        if not any(a["id"] == identity for a in catalog["assets"]):
            catalog["assets"].append(
                {
                    "id": identity,
                    "kind": "decoration",
                    "title": "Проклятый лес · "
                    + ("Скрученный вяз" if variant == 0 else "Мёртвая сосна"),
                    "group": "MOM RPG",
                    "revision": 1,
                    "tags": ["mom_rpg", "forest", "cursed"],
                    "files": files,
                }
            )
    write_json(catalog_path, catalog)
    build_catalog(ROOT)
    print("Published cursed forest trees", flush=True)


if __name__ == "__main__":
    publish()
