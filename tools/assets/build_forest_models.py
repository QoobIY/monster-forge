"""Original horned satyrs and thornwood traps for the cursed forest."""

import hashlib
import json
import math
from pathlib import Path

from tools.assets.build_catalog import build_catalog
from tools.assets.build_mom_skins import bounded_weights
from tools.assets.build_rpg_locations import single_node
from tools.assets.build_swamp_models import SLOTS, Shape, write_json

ROOT = Path(__file__).resolve().parents[2]
SKIN = (112, 90, 88, 255)
FUR = (60, 46, 51, 255)
HORN = (179, 163, 123, 255)
EYE = (166, 211, 69, 255)
DARK = (31, 28, 34, 255)
BARK = (69, 58, 43, 255)


def anatomy(slot, king):
    p = Shape()
    accent = (112, 65, 117, 255) if king else (83, 104, 54, 255)
    if slot == "head":
        p.ellipsoid((0, 2.13, 0.04), (0.25, 0.31, 0.23), SKIN)
        p.ellipsoid((0, 2.0, 0.22), (0.14, 0.15, 0.14), FUR)
        p.cone(0.12, 0.3, (0, 1.82, 0.14), FUR, 5)
        for s in [-1, 1]:
            p.ellipsoid((s * 0.29, 2.17, 0), (0.19, 0.08, 0.11), SKIN, 0)
            p.ellipsoid((s * 0.105, 2.2, 0.245), (0.065, 0.036, 0.025), EYE, 0)
            points = [
                (s * 0.19, 2.34, 0),
                (s * 0.31, 2.49, -0.12),
                (s * 0.34, 2.64, -0.25),
                (s * 0.25, 2.78, -0.34),
                (s * 0.12, 2.76, -0.31),
            ]
            if king:
                points = [(x * 1.25, y + 0.08, z * 1.3) for x, y, z in points]
            for i in range(len(points) - 1):
                p.branch(points[i], points[i + 1], 0.105 * (1 - i * 0.23), HORN)
    elif slot == "torso":
        p.ellipsoid((0, 1.41, 0), (0.35, 0.46, 0.21), SKIN)
        p.ellipsoid((0, 1.03, 0), (0.29, 0.17, 0.22), FUR)
        p.branch((-0.28, 1.68, 0.2), (0.25, 1.13, 0.21), 0.06, accent)
        p.cylinder(0.31, 0.12, (0, 1.08, 0), accent, 8)
        if king:
            for s in [-1, 1]:
                p.ellipsoid((s * 0.35, 1.73, 0), (0.24, 0.17, 0.28), BARK, 0)
                for j in range(3):
                    p.branch(
                        (s * 0.35, 1.79, -0.13 + j * 0.14),
                        (s * (0.4 + 0.1 * j), 2.1, -0.2 + j * 0.14),
                        0.045,
                        HORN,
                        5,
                    )
    else:
        s = -1 if slot.startswith("left") else 1
        if slot.endswith("arm"):
            p.branch((s * 0.35, 1.74, 0), (s * 0.65, 1.36, 0), 0.145, SKIN)
            p.branch((s * 0.65, 1.36, 0), (s * 0.82, 1.01, 0.04), 0.1, SKIN)
            p.ellipsoid((s * 0.83, 0.97, 0.07), (0.12, 0.13, 0.12), FUR)
            p.cylinder(0.13, 0.16, (s * 0.78, 1.13, 0.02), accent, 6)
            for j in range(3):
                p.branch(
                    (s * 0.84, 0.95, -0.01 + j * 0.07),
                    (s * 0.91, 0.84, -0.01 + j * 0.07),
                    0.033,
                    HORN,
                    5,
                )
        else:
            p.branch((s * 0.22, 1.0, 0), (s * 0.31, 0.56, -0.13), 0.21, FUR)
            p.branch((s * 0.31, 0.56, -0.13), (s * 0.30, 0.20, 0.12), 0.10, FUR)
            for x in [s * 0.3 - 0.065, s * 0.3 + 0.065]:
                p.ellipsoid((x, 0.115, 0.23), (0.07, 0.12, 0.19), DARK, 0)
    return p.finish()


def build():
    digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    for name, king in [("satyr", False), ("satyr_king", True)]:
        folder = ROOT / "media/constructor/mom_rpg/v1/forest" / name
        (folder / "parts").mkdir(parents=True, exist_ok=True)
        for slot in SLOTS:
            target = folder / "parts" / (slot + ".glb")
            mesh = anatomy(slot, king)
            payload = mesh.export(file_type="glb", tree_postprocessor=single_node)
            if target.exists() and target.read_bytes() != payload:
                raise ValueError("Immutable forest anatomy changed")
            target.write_bytes(payload)
            write_json(
                target.with_suffix(".recipe.json"),
                {
                    "schema_version": 1,
                    "builder_sha256": digest,
                    "kind": "procedural_satyr_anatomy",
                    "triangles": len(mesh.faces),
                    "anatomy": "curved horns, goat muzzle, furred reverse-joint legs and split hooves; no human boots",
                },
            )
            write_json(
                target.with_suffix(".weights.json"), bounded_weights(target, slot, "canonical")
            )
        write_json(
            folder / "record.json",
            {
                "schema_version": 1,
                "id": name,
                "label": "Король сатиров" if king else "Сатир-ловчий",
                "race": "satyr",
                "rig": "humanoid_v1",
                "bind_profile": "canonical",
                "parts": {s: {"model": "parts/" + s + ".glb"} for s in SLOTS},
                "tags": ["mom_rpg", "forest", "satyr"],
            },
        )
    p = Shape()
    for i in range(7):
        a = i * math.tau / 7
        x, z = math.cos(a), math.sin(a)
        p.branch((x * 0.75, 0, z * 0.75), (x * 0.38, 0.42, z * 0.38), 0.10, BARK)
        p.branch((x * 0.38, 0.42, z * 0.38), (x * 0.18, 0.75, z * 0.18), 0.065, HORN)
    mesh = p.finish()
    folder = ROOT / "media/decorations/mom_rpg/forest/thorn_trap/v1"
    folder.mkdir(parents=True, exist_ok=True)
    catalog_path = ROOT / "media/imported_catalog.json"
    catalog = json.loads(catalog_path.read_text())
    files = {}
    for role, name, blob, mime in [
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
                        "style": "BHM faceted thornwood",
                        "triangles": len(mesh.faces),
                    },
                    indent=2,
                )
                + "\n"
            ).encode(),
            "application/json",
        ),
    ]:
        target = folder / name
        if target.exists() and target.read_bytes() != blob:
            raise ValueError("Immutable forest trap changed")
        target.write_bytes(blob)
        files[role] = {
            "path": target.relative_to(ROOT / "media").as_posix(),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "size_bytes": len(blob),
            "media_type": mime,
        }
    identity = "decoration.mom_rpg.forest.thorn_trap"
    if not any(a["id"] == identity for a in catalog["assets"]):
        catalog["assets"].append(
            {
                "id": identity,
                "kind": "decoration",
                "title": "Ловушка из проклятых корней",
                "revision": 1,
                "group": "MOM RPG",
                "tags": ["mom_rpg", "forest"],
                "files": files,
            }
        )
    write_json(catalog_path, catalog)
    build_catalog(ROOT)
    print("Published forest models", flush=True)


if __name__ == "__main__":
    build()
