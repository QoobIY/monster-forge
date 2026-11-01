"""Publish curved branching roots for immobilization VFX."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from tools.assets.build_catalog import build_catalog
from tools.assets.build_rpg_locations import single_node
from tools.assets.build_swamp_models import Shape

ROOT = Path(__file__).resolve().parents[2]


def publish(root: Path = ROOT) -> None:
    shape = Shape()
    for strand in range(7):
        angle = strand * math.tau / 7
        points = []
        for step in range(7):
            fraction = step / 6
            radius = 1.05 - 0.6 * fraction
            theta = angle + fraction * 1.7
            points.append((radius * math.cos(theta), fraction * 1.45, radius * math.sin(theta)))
        for step in range(6):
            color = (93 + step * 7, 65 + step * 5, 35 + step * 3, 255)
            shape.branch(points[step], points[step + 1], 0.13 - step * 0.014, color)
            if step < 4:
                shape.ellipsoid(points[step], (0.13 - step * 0.014,) * 3, color, 0)
        root_origin = points[0]
        for fork in [-1, 1]:
            tip = (
                (1.4 + strand % 2 * 0.13) * math.cos(angle + fork * 0.25),
                0.025,
                (1.4 + strand % 2 * 0.13) * math.sin(angle + fork * 0.25),
            )
            shape.branch(root_origin, tip, 0.065, (76, 53, 29, 255), sections=6)
    mesh = shape.finish()
    directory = root / "media/decorations/mom_rpg/forest/root_cage/v1"
    directory.mkdir(parents=True, exist_ok=True)
    files = {}
    recipe = {
        "schema_version": 1,
        "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "coordinates": "Y up; seven curved tapered roots around a clear 0.45m central cylinder",
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
    identity = "decoration.mom_rpg.forest.root_cage"
    catalog["assets"] = [row for row in catalog["assets"] if row["id"] != identity]
    catalog["assets"].append(
        {
            "id": identity,
            "kind": "decoration",
            "title": "Опутывающие проклятые корни",
            "revision": 1,
            "group": "MOM RPG",
            "tags": ["forest", "vfx", "roots"],
            "files": files,
        }
    )
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    build_catalog(root)
    print("Published curved forest root cage", flush=True)


if __name__ == "__main__":
    publish()
