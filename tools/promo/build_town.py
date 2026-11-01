"""Publish current constructor citizens and a reusable stone town fountain in BHM."""

from __future__ import annotations

import hashlib
import json
import math
from itertools import pairwise
from pathlib import Path

import numpy as np
import trimesh

from monsterforge.paths import ROOT
from monsterforge.workshop_constructor import presets
from tools.assets.publish_assembly import publish


def citizens():
    choices = presets()
    for number in range(1, 11):
        face = f"library-human-{number:02d}"
        original = next(p for p in choices if p["settings"]["face"] == face)
        settings = original["settings"]
        # Every resident goes through the current constructor, including its head
        # anatomy/hair correction; no reuse of the old library's baked body.
        entry = publish(
            f"character.shared.promo.citizen-{number:02d}",
            original["label"] + " · житель города",
            settings,
        )
        print(entry["id"], entry["files"]["model"]["sha256"], flush=True)


def fountain():
    meshes = {"stone": [], "trim": [], "water": [], "water_jet": []}
    colors = {
        "stone": (164, 172, 162, 255),
        "trim": (145, 129, 87, 255),
        "water": (49, 107, 123, 255),
        "water_jet": (178, 218, 224, 255),
    }

    def add(mesh, role, position=(0, 0, 0), tint=1.0):
        color = np.array(colors[role], float)
        color[:3] *= tint
        mesh.visual.vertex_colors = np.tile(
            np.uint8(np.clip(color, 0, 255)), (len(mesh.vertices), 1)
        )
        mesh.apply_translation(position)
        meshes[role].append(mesh)

    def cylinder(radius, height, y, role="stone", sections=16):
        m = trimesh.creation.cylinder(radius, height, sections=sections)
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, (1, 0, 0)))
        add(m, role, (0, y, 0))

    def ring(outer, inner, low, high, role="stone", segments=16):
        # Individual voussoirs retain the chunky construction and readable joints.
        for i in range(segments):
            a = (i + 0.025) * 2 * math.pi / segments
            b = (i + 0.975) * 2 * math.pi / segments
            v = [
                [r * math.cos(t), y, r * math.sin(t)]
                for y in (low, high)
                for r in (inner, outer)
                for t in (a, b)
            ]
            triangles = [
                [0, 1, 3],
                [0, 3, 2],
                [4, 6, 7],
                [4, 7, 5],
                [0, 4, 5],
                [0, 5, 1],
                [2, 3, 7],
                [2, 7, 6],
                [0, 2, 6],
                [0, 6, 4],
                [1, 5, 7],
                [1, 7, 3],
            ]
            mesh = trimesh.Trimesh(vertices=v, faces=triangles, process=False)
            trimesh.repair.fix_normals(mesh)
            add(mesh, role, tint=0.96 + (i % 3) * 0.025)

    cylinder(1.9, 0.16, 0.08)
    cylinder(1.77, 0.17, 0.245)
    cylinder(1.61, 0.12, 0.37)
    ring(1.72, 1.42, 0.36, 0.67)
    ring(1.79, 1.39, 0.64, 0.76)
    cylinder(1.39, 0.016, 0.57, "water", 48)
    cylinder(0.38, 0.17, 0.63)
    cylinder(0.24, 0.83, 1.07)
    cylinder(0.34, 0.13, 1.45)
    cylinder(0.68, 0.11, 1.55)
    ring(0.78, 0.64, 1.52, 1.70)
    cylinder(0.64, 0.014, 1.66, "water", 32)
    cylinder(0.13, 0.40, 1.83)
    cylinder(0.19, 0.07, 2.04, "trim")
    cylinder(0.065, 0.07, 2.11, "water")
    for i in range(8):
        angle = i * math.pi / 4

        def arc(start_radius, start_y, end_radius, end_y, lift, width, angle=angle):
            points = []
            for k in range(13):
                t = k / 12
                r = start_radius + (end_radius - start_radius) * t
                points.append(
                    [
                        r * math.cos(angle),
                        start_y + (end_y - start_y) * t + lift * 4 * t * (1 - t),
                        r * math.sin(angle),
                    ]
                )
            for a, b in pairwise(points):
                direction = np.array(b) - a
                mesh = trimesh.creation.cylinder(width, np.linalg.norm(direction), sections=5)
                mesh.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], direction))
                add(mesh, "water_jet", (np.array(a) + b) / 2)

        arc(0.04, 2.13, 0.53, 1.68, 0.14, 0.012)
        arc(0.73, 1.68, 1.10, 0.59, 0.09, 0.016)
    scene = trimesh.Scene()
    for name, parts in meshes.items():
        mesh = trimesh.util.concatenate(parts)
        mesh.metadata["surface_role"] = name
        scene.add_geometry(mesh, geom_name=name, node_name=name)
    raw = scene.export(file_type="glb")
    from tools.assets.bake_character_models import unpack
    from tools.materials.build_viking_material_lab import blob_glb

    doc, binary = unpack(raw)
    doc["materials"] = []
    for mesh in doc["meshes"]:
        name = mesh["name"]
        index = len(doc["materials"])
        doc["materials"].append(
            {
                "name": name,
                "pbrMetallicRoughness": {
                    "baseColorFactor": [
                        1,
                        1,
                        1,
                        0.65 if name == "water_jet" else 0.86 if name == "water" else 1,
                    ],
                    "metallicFactor": 0,
                    "roughnessFactor": 0.16 if name.startswith("water") else 0.88,
                },
                "doubleSided": False,
                "alphaMode": "BLEND" if name.startswith("water") else "OPAQUE",
            }
        )
        for primitive in mesh["primitives"]:
            primitive["material"] = index
    doc["meshes"] = [
        {
            "name": "civic_fountain",
            "primitives": [p for mesh in doc["meshes"] for p in mesh["primitives"]],
        }
    ]
    doc["nodes"] = [{"name": "civic_fountain", "mesh": 0}]
    doc["scenes"] = [{"nodes": [0]}]
    doc["scene"] = 0
    raw = blob_glb(doc, binary)
    folder = ROOT / "media/decorations/shared/town/civic_fountain"
    folder.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(raw).hexdigest()
    path = folder / f"model.{digest[:24]}.glb"
    if path.exists() and path.read_bytes() != raw:
        raise ValueError("Immutable fountain model differs")
    path.write_bytes(raw)
    recipe = {
        "schema_version": 1,
        "builder": "tools/promo/build_town.py",
        "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "coordinates": "Y-up; metres; ground Y=0",
        "design": "16-sided stone basin, central raised cup, shallow blue water, eight cascades",
        "materials": ["stone", "trim", "water"],
        "bounds": scene.bounds.tolist(),
    }
    recipe_bytes = (json.dumps(recipe, indent=2) + "\n").encode()
    recipe_hash = hashlib.sha256(recipe_bytes).hexdigest()
    recipe_path = folder / f"recipe.{recipe_hash[:24]}.json"
    if recipe_path.exists() and recipe_path.read_bytes() != recipe_bytes:
        raise ValueError("Immutable fountain recipe differs")
    recipe_path.write_bytes(recipe_bytes)

    def ref(p, mime):
        blob = p.read_bytes()
        return {
            "path": p.relative_to(ROOT / "media").as_posix(),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "size_bytes": len(blob),
            "media_type": mime,
        }

    identity = "decoration.shared.town.civic_fountain"
    catalog_path = ROOT / "media/catalog.json"
    catalog = json.loads(catalog_path.read_text())
    old = next((e for e in catalog["assets"] if e["id"] == identity), None)
    files = dict(old["files"]) if old and old["files"]["model"]["sha256"] == digest else {}
    files.update(model=ref(path, "model/gltf-binary"), recipe=ref(recipe_path, "application/json"))
    entry = {
        "id": identity,
        "kind": "decoration",
        "group": "Общие декорации",
        "title": "Городской каменный фонтан",
        "revision": old["revision"] + int(old["files"]["model"]["sha256"] != digest) if old else 1,
        "tags": ["shared", "town", "fountain", "stone", "water"],
        "files": files,
    }
    catalog["assets"] = [e for e in catalog["assets"] if e["id"] != identity] + [entry]
    pending = catalog_path.with_suffix(".next")
    pending.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    pending.replace(catalog_path)
    print(identity, digest, flush=True)


def main():
    citizens()
    fountain()


if __name__ == "__main__":
    main()
