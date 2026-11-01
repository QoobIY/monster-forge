"""Publish ten material-only studies of one immutable constructor Viking.

Needs the BHM authoring environment and rtree for the optional AO ray cache.
No character geometry is generated, remeshed, smoothed or displaced here.
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
import struct
import tempfile
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

from monster_forge_sdk import AssetStore
from monster_forge_sdk.characters import body_rig
from monsterforge.paths import ROOT
from monsterforge.workshop_constructor import build
from tools.assets.bake_character_models import accessor, unpack
from tools.creature_workshop.geometry import compile_recipe

SOURCE = "character.shared.promo.viking.body"
CELL, COLS = 16, 128
STUDIES = [
    (
        "00",
        "Исходный материал",
        "Один материал: metallic=0, roughness=1. Тот же PBR-свет, что у вариантов.",
    ),
    ("01", "Разделение PBR", "Отдельные свойства стали, золота, ткани, кожи, волос, рогов и лица."),
    (
        "02",
        "Насыщенное альбедо",
        "Более глубокий цвет поверхности; без изменения света и геометрии.",
    ),
    ("03", "Карта шероховатости", "Разная ширина блика на потёртой коже, кованом металле и ткани."),
    (
        "04",
        "Микрорельеф / normal map",
        "Плетение ткани, зерно кожи и лёгкая ковка меняют нормали освещения.",
    ),
    ("05", "Ворсистая ткань / sheen", "Мягкий скользящий блеск ткани и меха, особенно по силуэту."),
    (
        "06",
        "Покрытие металла / clearcoat",
        "Второй узкий отражающий слой на шлеме, цепях и золотой отделке.",
    ),
    (
        "07",
        "Контактное AO",
        "Трассировка лучей в исходную геометрию; затемняет только окружающий свет в щелях.",
    ),
    (
        "08",
        "Износ выпуклых кромок",
        "Высветление и полировка настоящих острых выпуклых рёбер, без сетки треугольников.",
    ),
    (
        "09",
        "Направленные блики",
        "Анизотропия волос и шлифованного металла; направление хранится в карте материала.",
    ),
    (
        "10",
        "Смешанный вариант",
        "Насыщенный цвет, PBR, умеренный рельеф, AO, ткань, металл и аккуратные кромки.",
    ),
]
PRESETS = {
    "cloth": (0.0, 0.84),
    "fur": (0.0, 0.96),
    "skin": (0.0, 0.56),
    "eyes": (0.0, 0.19),
    "hair": (0.0, 0.42),
    "metal": (0.92, 0.3),
    "trim": (0.78, 0.32),
    "leather": (0.0, 0.58),
    "bone": (0.0, 0.67),
}


def role(command):
    m, p = command["material"], command["part"]
    if "fur" in p:
        return "fur"
    if "hair" in m:
        return "hair"
    if m in {"sclera", "iris", "pupil"}:
        return "eyes"
    if "horn" in m or "horn" in p:
        return "bone"
    if "leather" in m or m.endswith("_dark"):
        return "leather"
    if "metal" in m:
        return "metal"
    if "accent" in m:
        return "trim"
    if "cloth" in m or m.endswith("_secondary"):
        return "cloth"
    return "skin"


def regions(store, settings, positions):
    result = np.empty(len(positions), dtype="U8")
    offset = 0
    with tempfile.TemporaryDirectory(prefix="bhm-material-regions-") as temp:
        root = Path(temp)
        build(settings, root, weights=True)
        for slot in [r["id"] for r in body_rig("humanoid_v1", root=ROOT)["slots"]]:
            recipe = json.loads((root / "parts" / slot / "recipe.json").read_text())
            arrays = compile_recipe(recipe)
            if not np.array_equal(positions[offset : offset + len(arrays[0])], arrays[0]):
                raise ValueError(
                    "Constructor changed geometry; refusing to relabel a different model: " + slot
                )
            start = 0
            for command, end in zip(recipe["commands"], arrays[3], strict=True):
                result[offset + start : offset + end] = role(command)
                start = end
            offset += len(arrays[0])
    if offset != len(positions):
        raise ValueError("Incomplete material coverage")
    return result


def ray_ao(vertices, faces, normals, samples=12):
    identity = hashlib.sha256(vertices.tobytes() + faces.tobytes()).hexdigest()
    cache = (
        Path(tempfile.gettempdir()) / "monster-forge/material-lab" / f"ao-{identity}-{samples}.npy"
    )
    if cache.exists():
        return np.load(cache)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    centers = mesh.triangles_center + normals * 0.0007
    seed = np.tile([1.0, 0, 0], (len(normals), 1))
    seed[np.abs(normals[:, 0]) > 0.8] = [0, 0, 1]
    tangent = np.cross(normals, seed)
    tangent /= np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-10)
    bitangent = np.cross(normals, tangent)
    hits = np.zeros(len(faces))
    for k in range(samples):
        u = (k + 0.5) / samples
        a = k * 2.3999632297
        directions = (
            tangent * np.cos(a) * np.sqrt(u)
            + bitangent * np.sin(a) * np.sqrt(u)
            + normals * np.sqrt(1 - u)
        )
        for first in range(0, len(faces), 512):
            end = min(first + 512, len(faces))
            locations, rays, _ = mesh.ray.intersects_location(
                centers[first:end], directions[first:end], multiple_hits=False
            )
            distance = np.linalg.norm(locations - centers[first + rays], axis=1)
            weight = np.maximum(0.0, 1 - distance / 0.22)
            hits[first + rays] += weight
        print("AO rays", k + 1, "/", samples, flush=True)
    ao = np.clip(1 - hits / samples, 0.16, 1)
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.save(cache, ao)
    return ao


def sharp_edges(vertices, faces, normals):
    _, inverse = np.unique(np.round(vertices, 5), axis=0, return_inverse=True)
    edges = {}
    result = np.zeros((len(faces), 3), bool)
    centers = vertices[faces].mean(axis=1)
    for i, face in enumerate(inverse[faces]):
        for opposite in range(3):
            a, b = face[(opposite + 1) % 3], face[(opposite + 2) % 3]
            key = tuple(sorted((int(a), int(b))))
            if key in edges:
                other, edge = edges[key]
                d = centers[other] - centers[i]
                if (
                    np.dot(normals[i], normals[other]) < 0.65
                    and np.dot(d, normals[i]) < -0.00001
                    and np.dot(-d, normals[other]) < -0.00001
                ):
                    result[i, opposite] = result[other, edge] = True
            else:
                edges[key] = (i, opposite)
    return result


def pack_tiles(tiles):
    count = len(tiles)
    rows = (count + COLS - 1) // COLS
    tiles = np.pad(tiles, ((0, rows * COLS - count), (0, 0), (0, 0), (0, 0)), constant_values=1)
    return np.clip(
        tiles.reshape(rows, COLS, CELL, CELL, 3)
        .transpose(0, 2, 1, 3, 4)
        .reshape(rows * CELL, COLS * CELL, 3)
        * 255,
        0,
        255,
    ).astype("uint8")


def maps(vertices, faces, colors, face_roles):
    tri = vertices[faces]
    e1, e2 = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
    n = np.cross(e1, e2)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-10)
    t = e1 / np.maximum(np.linalg.norm(e1, axis=1, keepdims=True), 1e-10)
    b = np.cross(n, t)
    uv = np.empty((len(vertices), 2), np.float32)
    rows = (len(faces) + COLS - 1) // COLS
    for i, face in enumerate(faces):
        x, y = i % COLS * CELL, i // COLS * CELL
        uv[face] = [(x + 2.5, y + 2.5), (x + 13.5, y + 2.5), (x + 2.5, y + 13.5)]
    uv[:, 0] /= COLS * CELL
    # glTF (0,0) is the upper-left image corner. The viewer flips GPU sampling.
    uv[:, 1] /= rows * CELL
    tangents = np.column_stack((t, np.full(len(t), 1.0))).repeat(3, axis=0).astype("<f4")
    ao = ray_ao(vertices, faces, n)
    edges = sharp_edges(vertices, faces, n)
    grid = (np.arange(CELL) - 2) / 11
    u, v = np.meshgrid(grid, grid)
    bary = np.stack((1 - u - v, u, v), axis=-1)
    data = {
        key: np.ones((len(faces), CELL, CELL, 3), np.float32)
        for key in [
            "albedo",
            "wear",
            "combined",
            "normal",
            "rough",
            "rough_wear",
            "ao",
            "anisotropy",
        ]
    }
    for first in range(0, len(faces), 256):
        end = min(first + 256, len(faces))
        sl = slice(first, end)
        p = np.einsum("uvk,nkj->nuvj", bary, tri[sl])
        color = np.clip(np.einsum("uvk,nkj->nuvj", bary, colors[faces[sl], :3]), 0, 1)
        face_t = t[sl]
        face_b = b[sl]
        height_gradient = np.zeros_like(p)
        rough = np.ones(p.shape[:-1], np.float32)
        for name in PRESETS:
            mask = face_roles[sl] == name
            if not mask.any():
                continue
            q = p[mask]
            x, y, z = q[..., 0], q[..., 1], q[..., 2]
            if name in {"cloth", "fur"}:
                grad = np.stack(
                    (
                        0.06 * np.cos(x * 300) * np.sin(y * 360),
                        0.08 * np.sin(x * 300) * np.cos(y * 360),
                        np.zeros_like(x),
                    ),
                    axis=-1,
                )
            elif name == "leather":
                a = 210 * x + 160 * y + 73 * z
                grad = np.cos(a)[..., None] * np.array([0.045, 0.034, 0.015])
            elif name in {"metal", "trim"}:
                grad = np.stack(
                    (
                        0.025 * np.cos(x * 110) * np.sin(y * 125),
                        0.03 * np.sin(x * 110) * np.cos(y * 125),
                        np.zeros_like(x),
                    ),
                    axis=-1,
                )
            elif name == "hair":
                grad = np.cos(x * 320 + z * 230)[..., None] * np.array([0.09, 0, 0.063])
            else:
                grad = np.zeros_like(q)
            height_gradient[mask] = grad
            variation = 0.5 + 0.5 * np.sin(x * 100 + np.sin(z * 67)) * np.cos(y * 120)
            rough[mask] = 0.62 + 0.38 * variation
        nt = np.stack(
            (
                -np.einsum("nuvj,nj->nuv", height_gradient, face_t),
                -np.einsum("nuvj,nj->nuv", height_gradient, face_b),
                np.ones_like(rough),
            ),
            axis=-1,
        )
        nt /= np.linalg.norm(nt, axis=-1, keepdims=True)
        data["normal"][sl] = nt * 0.5 + 0.5
        data["rough"][sl, ..., 1] = rough
        data["albedo"][sl] = color
        data["ao"][sl] = ao[sl, None, None, None]
        # Distance to the true convex edges, in metres; flat triangulation is ignored.
        area2 = np.linalg.norm(np.cross(e1[sl], e2[sl]), axis=1)
        sides = np.stack(
            [np.linalg.norm(tri[sl, (i + 1) % 3] - tri[sl, (i + 2) % 3], axis=1) for i in range(3)],
            axis=1,
        )
        altitude = area2[:, None] / np.maximum(sides, 1e-10)
        dist = np.abs(bary[None, ..., :] * altitude[:, None, None, :])
        edge = np.max(np.exp(-((dist / 0.0025) ** 2)) * edges[sl, None, None, :], axis=-1)
        edge *= np.isin(face_roles[sl], ["metal", "trim", "leather", "bone"])[:, None, None]
        worn = np.clip(color + edge[..., None] * 0.25, 0, 1)
        data["combined"][sl] = np.clip(color + edge[..., None] * 0.10, 0, 1)
        # Preserve the original linear albedo in this isolated edge-wear study.
        data["wear"][sl] = np.where(
            worn <= 0.0031308, worn * 12.92, 1.055 * worn ** (1 / 2.4) - 0.055
        )
        data["rough_wear"][sl, ..., 1] = np.clip(rough - edge * 0.32, 0.25, 1)
        axis = np.tile([0.0, 1, 0], (end - first, 1))
        tx = np.einsum("nj,nj->n", axis, face_t)
        by = np.einsum("nj,nj->n", axis, face_b)
        length = np.maximum(np.hypot(tx, by), 1e-8)
        data["anisotropy"][sl, ..., 0] = (tx / length)[:, None, None] * 0.5 + 0.5
        data["anisotropy"][sl, ..., 1] = (by / length)[:, None, None] * 0.5 + 0.5
    return uv, tangents, {k: pack_tiles(v) for k, v in data.items()}


def blob_glb(doc, binary):
    binary = bytes(binary) + b"\0" * (-len(binary) % 4)
    doc["buffers"][0]["byteLength"] = len(binary)
    raw = json.dumps(doc, separators=(",", ":")).encode()
    raw += b" " * (-len(raw) % 4)
    return (
        struct.pack("<4sII", b"glTF", 2, 28 + len(raw) + len(binary))
        + struct.pack("<I4s", len(raw), b"JSON")
        + raw
        + struct.pack("<I4s", len(binary), b"BIN\0")
        + binary
    )


def main():
    store = AssetStore(ROOT)
    source = store.read(SOURCE)
    doc, binary = unpack(source)
    primitive = doc["meshes"][0]["primitives"][0]
    attrs = primitive["attributes"]
    vertices = accessor(doc, binary, attrs["POSITION"])
    faces = accessor(doc, binary, primitive["indices"]).reshape(-1, 3)
    if "TEXCOORD_0" in attrs or not np.array_equal(faces.ravel(), np.arange(len(vertices))):
        raise ValueError(
            "This controlled study requires the original untextured, unshared face stream"
        )
    assembly = json.loads(store.path(SOURCE, "assembly").read_text())
    labels = regions(store, assembly["constructor_settings"], vertices)
    if not np.all(labels[faces] == labels[faces[:, 0, None]]):
        raise ValueError("A triangle crosses semantic material regions")
    face_roles = labels[faces[:, 0]]
    colors = accessor(doc, binary, attrs["COLOR_0"])
    uv, tangents, images = maps(vertices, faces, colors, face_roles)
    folder = ROOT / "media/material_labs/viking"
    folder.mkdir(parents=True, exist_ok=True)
    shared = {}
    for key, image in images.items():
        buf = io.BytesIO()
        Image.fromarray(image).save(buf, format="PNG")
        shared[key] = buf.getvalue()
    variants = []
    entries = []
    source_hash = hashlib.sha256(source).hexdigest()
    for code, title, description in STUDIES:
        d = copy.deepcopy(doc)
        bin_data = bytearray(binary)
        files = {}
        textures = {}

        def publish(role, payload, suffix, mime, files=files):
            digest = hashlib.sha256(payload).hexdigest()
            path = folder / f"{role}.{digest[:24]}{suffix}"
            if path.exists() and path.read_bytes() != payload:
                raise ValueError("Immutable asset differs")
            path.write_bytes(payload)
            files[role] = {
                "path": path.relative_to(ROOT / "media").as_posix(),
                "sha256": digest,
                "size_bytes": len(payload),
                "media_type": mime,
            }

        def append(values, shape, component=5126, d=d, bin_data=bin_data):
            values = np.asarray(values, dtype="<u4" if component == 5125 else "<f4")
            bin_data.extend(b"\0" * (-len(bin_data) % 4))
            offset = len(bin_data)
            bin_data.extend(values.tobytes())
            view = len(d["bufferViews"])
            d["bufferViews"].append(
                {"buffer": 0, "byteOffset": offset, "byteLength": values.nbytes}
            )
            d["accessors"].append(
                {
                    "bufferView": view,
                    "componentType": component,
                    "count": len(values),
                    "type": shape,
                }
            )
            return len(d["accessors"]) - 1

        def tex(role, textures=textures, d=d, bin_data=bin_data, publish=publish):
            if role in textures:
                return {"index": textures[role]}
            payload = shared[role]
            publish(role, payload, ".png", "image/png")
            bin_data.extend(b"\0" * (-len(bin_data) % 4))
            off = len(bin_data)
            bin_data.extend(payload)
            view = len(d["bufferViews"])
            d["bufferViews"].append({"buffer": 0, "byteOffset": off, "byteLength": len(payload)})
            d.setdefault("images", []).append({"bufferView": view, "mimeType": "image/png"})
            index = len(d.setdefault("textures", []))
            d["textures"].append({"source": len(d["images"]) - 1, "sampler": 0})
            textures[role] = index
            return {"index": index}

        materials = []
        slots = []
        if code != "00":
            a = copy.deepcopy(attrs)
            a["TEXCOORD_0"] = append(uv, "VEC2")
            a["TANGENT"] = append(tangents, "VEC4")
            if code in {"02", "08", "10"}:
                a["COLOR_0"] = append(np.ones_like(colors), "VEC4")
            primitives = []
            extensions = set()
            d["samplers"] = [{"wrapS": 33071, "wrapT": 33071, "minFilter": 9987, "magFilter": 9729}]
            for name in sorted(set(face_roles)):
                metal, rough = PRESETS[name]
                m = {
                    "name": name,
                    "doubleSided": False,
                    "pbrMetallicRoughness": {
                        "baseColorFactor": [1, 1, 1, 1],
                        "metallicFactor": metal,
                        "roughnessFactor": rough,
                    },
                }
                pbr = m["pbrMetallicRoughness"]
                if code in {"02", "08", "10"}:
                    pbr["baseColorTexture"] = tex(
                        {"02": "albedo", "08": "wear", "10": "combined"}[code]
                    )
                if code in {"03", "08", "10"}:
                    pbr["metallicRoughnessTexture"] = tex(
                        "rough_wear" if code in {"08", "10"} else "rough"
                    )
                if code in {"04", "10"}:
                    m["normalTexture"] = {**tex("normal"), "scale": 0.5 if code == "10" else 1.0}
                if code in {"07", "10"}:
                    m["occlusionTexture"] = {**tex("ao"), "strength": 0.8}
                ext = {}
                if code in {"05", "10"} and name in {"cloth", "fur"}:
                    ext["KHR_materials_sheen"] = {
                        "sheenColorFactor": [0.25, 0.12, 0.35]
                        if name == "cloth"
                        else [0.22, 0.16, 0.12],
                        "sheenRoughnessFactor": 0.7,
                    }
                if code in {"06", "10"} and name in {"metal", "trim"}:
                    ext["KHR_materials_clearcoat"] = {
                        "clearcoatFactor": 0.5 if code == "10" else 1.0,
                        "clearcoatRoughnessFactor": 0.18,
                    }
                if code in {"09", "10"} and name in {"hair", "metal"}:
                    ext["KHR_materials_anisotropy"] = {
                        "anisotropyStrength": 0.75 if name == "hair" else 0.55,
                        "anisotropyRotation": 0.0,
                        "anisotropyTexture": tex("anisotropy"),
                    }
                if ext:
                    m["extensions"] = ext
                    extensions.update(ext)
                index = len(materials)
                materials.append(m)
                slots.append(index)
                primitives.append(
                    {
                        "attributes": a,
                        "indices": append(faces[face_roles == name].ravel(), "SCALAR", 5125),
                        "material": index,
                        "mode": 4,
                    }
                )
            d["meshes"][0]["primitives"] = primitives
            d["materials"] = materials
            if extensions:
                d["extensionsUsed"] = sorted(extensions)
            d["extras"]["material_lab"] = {
                "source": SOURCE,
                "sha256": source_hash,
                "study": code,
                "geometry_unchanged": True,
            }
            model = blob_glb(d, bin_data)
        else:
            model = source
            materials = d["materials"]
            slots = [0]
        publish("model", model, ".glb", "model/gltf-binary")
        surface = {
            "schema_version": 1,
            "code": code,
            "title": title,
            "description": description,
            "source": SOURCE,
            "source_sha256": source_hash,
            "model_sha256": files["model"]["sha256"],
            "materials": materials,
            "slots": slots,
            "texture_roles": {str(i): r for r, i in textures.items()},
        }
        publish(
            "surface",
            (json.dumps(surface, ensure_ascii=False, indent=2) + "\n").encode(),
            ".json",
            "application/json",
        )
        identity = "character.experiments.viking_materials." + code + ".body"
        entries.append(
            {
                "id": identity,
                "kind": "character",
                "title": f"Викинг · Материалы {code} · {title}",
                "group": "Material laboratory",
                "tags": ["experimental", "materials", "same-geometry", "viking"],
                "revision": 1,
                "files": files,
            }
        )
        variants.append({"id": identity, "code": code, "title": title, "description": description})
        print("Published material study", code, flush=True)
    catalog_path = ROOT / "media/catalog.json"
    catalog = json.loads(catalog_path.read_text())
    old = {e["id"]: e for e in catalog["assets"]}
    for entry in entries:
        prev = old.get(entry["id"])
        entry["revision"] = (
            prev["revision"]
            + int(prev["files"]["model"]["sha256"] != entry["files"]["model"]["sha256"])
            if prev
            else 1
        )
    ids = {e["id"] for e in entries}
    catalog["assets"] = [e for e in catalog["assets"] if e["id"] not in ids] + entries
    pending = catalog_path.with_suffix(".next")
    pending.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    pending.replace(catalog_path)
    (folder / "studies.json").write_text(
        json.dumps(
            {"source": SOURCE, "source_sha256": source_hash, "variants": variants},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
