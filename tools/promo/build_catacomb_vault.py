"""Author a masonry barrel vault for the reusable catacomb environment."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import trimesh

from monsterforge.paths import ROOT
from tools.assets.bake_character_models import unpack
from tools.materials.build_viking_material_lab import blob_glb


def build():
    blocks = []
    for bay in range(11):
        for band in range(16):
            a = band * math.pi / 16 + 0.003
            b = (band + 1) * math.pi / 16 - 0.003
            x0, x1 = -12.3 * math.cos(a), -12.3 * math.cos(b)
            h0, h1 = 8 + 7 * math.sin(a), 8 + 7 * math.sin(b)
            y0, y1 = -44 + bay * 8 + 0.025, -44 + (bay + 1) * 8 - 0.025
            vertices = [[x0, h0, -y0], [x1, h1, -y0], [x0, h0, -y1], [x1, h1, -y1]]
            mesh = trimesh.Trimesh(vertices=vertices, faces=[[0, 2, 1], [1, 2, 3]], process=False)
            tint = 0.82 + 0.035 * ((band + bay * 3) % 5)
            mesh.visual.vertex_colors = np.tile(
                np.uint8(np.array([106, 116, 129, 255]) * [tint, tint, tint, 1]), (4, 1)
            )
            blocks.append(mesh)
    mesh = trimesh.util.concatenate(blocks)
    doc, binary = unpack(mesh.export(file_type="glb"))
    doc["materials"] = [
        {
            "name": "stone",
            "doubleSided": True,
            "pbrMetallicRoughness": {"metallicFactor": 0, "roughnessFactor": 0.93},
        }
    ]
    for m in doc["meshes"]:
        for p in m["primitives"]:
            p["material"] = 0
    raw = blob_glb(doc, binary)
    identity = "decoration.shared.landscapes.catacomb_vault"
    folder = ROOT / "media/decorations/shared/landscapes/catacomb_vault"
    folder.mkdir(parents=True, exist_ok=True)
    layout = {
        "schema_version": 1,
        "coordinates": "Y-up; metres",
        "builder": "tools/promo/build_catacomb_vault.py",
        "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "props": [],
        "triangles": len(mesh.faces),
    }
    files = {}
    for role, payload, suffix, mime in [
        ("model", raw, ".glb", "model/gltf-binary"),
        ("layout", (json.dumps(layout, indent=2) + "\n").encode(), ".json", "application/json"),
    ]:
        digest = hashlib.sha256(payload).hexdigest()
        p = folder / (role + "." + digest[:24] + suffix)
        if p.exists() and p.read_bytes() != payload:
            raise ValueError("Immutable vault collision")
        p.write_bytes(payload)
        files[role] = {
            "path": p.relative_to(ROOT / "media").as_posix(),
            "sha256": digest,
            "size_bytes": len(payload),
            "media_type": mime,
        }
    path = ROOT / "media/catalog.json"
    c = json.loads(path.read_text())
    old = next((e for e in c["assets"] if e["id"] == identity), None)
    entry = {
        "id": identity,
        "kind": "decoration",
        "title": "Каменный свод катакомб",
        "group": "Общие декорации",
        "revision": 1
        if old is None
        else old["revision"] + int(old["files"]["model"] != files["model"]),
        "tags": ["shared", "crypt", "architecture"],
        "files": {**(old["files"] if old else {}), **files},
    }
    c["assets"] = [e for e in c["assets"] if e["id"] != identity] + [entry]
    pending = path.with_suffix(".next")
    pending.write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n")
    pending.replace(path)
    print(identity, len(mesh.faces), "triangles")


if __name__ == "__main__":
    build()
