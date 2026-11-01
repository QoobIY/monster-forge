"""Author low, four-legged frogs; no humanoid donor meshes or biped proportions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from monster_forge_sdk.characters import body_rig
from tools.assets.build_catalog import build_catalog
from tools.assets.build_rpg_locations import single_node
from tools.assets.build_swamp_models import BLACK, DARK, GOLD, GREEN, PALE, Shape

ROOT = Path(__file__).resolve().parents[2]


def anatomy(slot: str, king: bool) -> trimesh.Trimesh:
    shape = Shape()
    skin = (76, 105, 43, 255) if king else GREEN
    if slot == "torso":
        shape.ellipsoid((0, 0.62, -0.10), (0.69, 0.43, 0.95), skin, 2)
        shape.ellipsoid((0, 0.37, 0.18), (0.56, 0.20, 0.67), PALE, 2)
        for side in (-1, 1):
            for i in range(4):
                shape.ellipsoid(
                    (side * (0.35 + 0.06 * (i % 2)), 0.99 - i * 0.015, -0.55 + i * 0.25),
                    (0.10, 0.06, 0.12),
                    DARK,
                )
    elif slot == "head":
        shape.ellipsoid((0, 0.75, 0.82), (0.76, 0.30, 0.62), skin, 2)
        shape.ellipsoid((0, 0.55, 1.12), (0.65, 0.12, 0.36), PALE, 2)
        shape.ellipsoid((0, 0.64, 1.34), (0.64, 0.026, 0.07), DARK, 2)
        for side in (-1, 1):
            shape.ellipsoid((side * 0.48, 1.02, 0.84), (0.21, 0.24, 0.22), skin, 2)
            shape.ellipsoid((side * 0.48, 1.04, 1.02), (0.15, 0.16, 0.075), (204, 175, 66, 255), 2)
            shape.ellipsoid((side * 0.48, 1.04, 1.083), (0.042, 0.12, 0.025), BLACK, 2)
            shape.ellipsoid(
                (side * 0.45, 1.095, 1.105), (0.027, 0.032, 0.015), (232, 230, 176, 255)
            )
            shape.ellipsoid((side * 0.19, 0.88, 1.35), (0.035, 0.028, 0.025), DARK)
        if king:
            # The crown sits between the eyes, on an animal head.
            shape.cylinder(0.35, 0.12, (0, 1.08, 0.52), GOLD)
            for x in (-0.26, 0, 0.26):
                shape.cone(0.10, 0.29 if x else 0.42, (x, 1.23, 0.52), GOLD)
    elif slot == "tail":
        # The shared quadruped layout has an unused tail joint; frogs have no visible tail.
        shape.ellipsoid((0, 0.62, -0.2), (0.025, 0.025, 0.025), skin)
    else:
        side = -1 if "left" in slot else 1
        if slot.startswith("front"):
            shoulder = (side * 0.55, 0.60, 0.68)
            elbow = (side * 0.78, 0.30, 0.84)
            palm = (side * 0.70, 0.085, 1.14)
            shape.branch(shoulder, elbow, 0.105, skin)
            shape.branch(elbow, palm, 0.075, skin)
            shape.ellipsoid(palm, (0.15, 0.055, 0.20), skin)
            for i in range(4):
                toe = (palm[0] + (i - 1.5) * 0.085, 0.055, 1.48 + (0.08 if i in (1, 2) else 0))
                shape.branch(palm, toe, 0.033, PALE)
                shape.ellipsoid(toe, (0.055, 0.024, 0.062), skin)
        else:
            hip = (side * 0.48, 0.55, -0.48)
            knee = (side * 0.94, 0.30, -0.77)
            ankle = (side * 0.65, 0.10, -0.12)
            shape.ellipsoid((side * 0.78, 0.42, -0.54), (0.31, 0.26, 0.46), skin, 2)
            shape.branch(hip, knee, 0.18, skin)
            shape.branch(knee, ankle, 0.10, skin)
            shape.ellipsoid(ankle, (0.19, 0.065, 0.24), skin)
            for i in range(5):
                toe = (ankle[0] + (i - 2) * 0.105, 0.055, 0.42 + (0.10 if i in (1, 2, 3) else 0))
                shape.branch(ankle, toe, 0.043, PALE)
                shape.ellipsoid(toe, (0.07, 0.028, 0.09), skin)
    return shape.finish()


def publish(root: Path = ROOT, *, catalog: bool = True) -> None:
    rig = body_rig("quadruped_v1", root=root)
    bones = rig["bones"]
    names = [bone["id"] for bone in bones]
    points = {}
    for bone in bones:
        point = np.array(bone["bind_translation"], float)
        points[bone["id"]] = point if bone["parent"] is None else points[bone["parent"]] + point
    digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    for name in ("frog_mutant", "frog_king"):
        folder = root / "media/constructor/mom_rpg/v1/swamp" / name
        (folder / "parts").mkdir(parents=True, exist_ok=True)
        # Replace only the rejected, newly authored biped frog parts.
        approved_slots = {slot["id"] for slot in rig["slots"]}
        for path in (folder / "parts").iterdir():
            if path.name.split(".")[0] not in approved_slots:
                path.unlink()
        records = {}
        for slot in rig["slots"]:
            key = slot["id"]
            mesh = anatomy(key, name == "frog_king")
            blob = mesh.export(file_type="glb", tree_postprocessor=single_node)
            model = folder / "parts" / (key + ".glb")
            model.write_bytes(blob)
            allowed = list(slot["bones"])
            distance = np.stack(
                [np.linalg.norm(mesh.vertices - points[bone], axis=1) for bone in allowed], axis=1
            )
            nearest = distance.argmin(axis=1)
            indices = [[names.index(allowed[index]), 0, 0, 0] for index in nearest]
            weights = {
                "schema_version": 1,
                "skeleton_id": "quadruped_v1",
                "gait": "hop",
                "bind_profile": "canonical",
                "slot": key,
                "bone_palette": names,
                "model_sha256": hashlib.sha256(blob).hexdigest(),
                "skin_indices": indices,
                "skin_weights": [[1.0, 0.0, 0.0, 0.0] for _ in indices],
            }
            model.with_suffix(".weights.json").write_text(json.dumps(weights, indent=2) + "\n")
            model.with_suffix(".recipe.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "builder_sha256": digest,
                        "anatomy": "horizontal frog, four crouched limbs, webbed toes, no visible tail",
                        "triangles": len(mesh.faces),
                    },
                    indent=2,
                )
                + "\n"
            )
            records[key] = {"model": "parts/" + key + ".glb"}
        (folder / "record.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "id": name,
                    "label": "Король лягушек" if name == "frog_king" else "Лягушка-мутант",
                    "race": "frog",
                    "rig": "quadruped_v1",
                    "gait": "hop",
                    "parts": records,
                    "tags": ["mom_rpg", "swamp", "frog", "quadruped"],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
    if catalog:
        build_catalog(root)
    print("Published quadruped swamp frogs", flush=True)


if __name__ == "__main__":
    publish()
