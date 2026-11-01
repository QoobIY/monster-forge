"""Publish a fleshy tongue mesh for the Frog King's telegraphed attack."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.assets.build_catalog import build_catalog
from tools.assets.build_rpg_locations import single_node
from tools.assets.build_swamp_models import Shape

ROOT = Path(__file__).resolve().parents[2]


def publish(root: Path = ROOT) -> None:
    shape = Shape()
    shape.branch((0, 0, -0.03), (0, 0, -0.92), 0.22, (160, 48, 70, 255), sections=10)
    shape.ellipsoid((0, 0, -0.92), (0.30, 0.20, 0.14), (190, 67, 84, 255), 2)
    shape.branch((0, 0.18, -0.06), (0, 0.18, -0.90), 0.035, (221, 113, 122, 255), sections=6)
    mesh = shape.finish()
    directory = root / "media/decorations/mom_rpg/swamp/tongue/v1"
    directory.mkdir(parents=True, exist_ok=True)
    files = {}
    recipe = {
        "schema_version": 1,
        "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "coordinates": "Y up; extends along negative Z from mouth, unit length",
        "triangles": len(mesh.faces),
    }
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
            (json.dumps(recipe, indent=2) + "\n").encode(),
            "application/json",
        ),
    ]:
        path = directory / name
        path.write_bytes(blob)
        files[role] = {
            "path": path.relative_to(root / "media").as_posix(),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "size_bytes": len(blob),
            "media_type": mime,
        }
    path = root / "media/imported_catalog.json"
    catalog = json.loads(path.read_text())
    identity = "decoration.mom_rpg.swamp.tongue"
    catalog["assets"] = [row for row in catalog["assets"] if row["id"] != identity]
    catalog["assets"].append(
        {
            "id": identity,
            "kind": "decoration",
            "title": "Язык Короля лягушек",
            "revision": 1,
            "group": "MOM RPG",
            "tags": ["swamp", "vfx", "frog"],
            "files": files,
        }
    )
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    build_catalog(root)
    print("Published Frog King tongue", flush=True)


if __name__ == "__main__":
    publish()
