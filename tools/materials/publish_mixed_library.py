"""Apply reusable mixed surface profiles to current BHM models, preserving geometry.

Run from BHM with the authoring extra. Existing albedo/alpha/emission survive;
secondary UVs address shared, small detail textures independently of albedo UVs.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

from monster_forge_sdk import AssetStore
from monsterforge.paths import ROOT
from tools.assets.bake_character_models import accessor, unpack
from tools.materials.build_viking_material_lab import blob_glb

VERSION = 1
PROFILES = {
    "cloth": (0.0, 0.84),
    "fur": (0.0, 0.96),
    "skin": (0.0, 0.56),
    "eyes": (0.0, 0.19),
    "hair": (0.0, 0.42),
    "metal": (0.92, 0.30),
    "trim": (0.78, 0.32),
    "leather": (0.0, 0.58),
    "bone": (0.0, 0.67),
    "wood": (0.0, 0.82),
    "stone": (0.0, 0.93),
    "foliage": (0.0, 0.88),
    "crystal": (0.12, 0.22),
    "ceramic": (0.0, 0.42),
    "matte": (0.0, 0.90),
    "water": (0.0, 0.16),
}
FOLDER = ROOT / "media/materials/mixed"


def semantic(name, default="skin"):
    name = name.lower()
    groups = [
        ("water", ("water",)),
        ("eyes", ("sclera", "iris", "pupil", "eye")),
        ("hair", ("hair", "beard", "mustache")),
        ("bone", ("bone", "horn", "tooth", "teeth", "skull", "skeleton")),
        ("fur", ("fur", "pelt")),
        ("leather", ("leather", "belt", "strap", "boot", "glove")),
        ("metal", ("metal", "steel", "iron", "blade", "chain", "armor")),
        ("trim", ("accent", "gold", "brass", "bronze", "copper", "trim")),
        ("wood", ("wood", "bark", "timber", "branch", "root")),
        ("stone", ("stone", "rock", "slate", "plaster", "crypt", "masonry", "sand")),
        ("foliage", ("leaf", "leaves", "foliage", "moss", "grass")),
        ("crystal", ("crystal", "gem", "glass")),
        ("cloth", ("cloth", "fabric", "secondary", "robe", "cape")),
        ("skin", ("skin", "lip", "anatomy", "shadow", "mouth")),
    ]
    for role, words in groups:
        if any(w in name for w in words):
            return role
    return default


def reference(path):
    raw = path.read_bytes()
    return {
        "path": "materials/mixed/" + path.name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "media_type": {
            ".glb": "model/gltf-binary",
            ".png": "image/png",
            ".json": "application/json",
        }[path.suffix],
    }


def publish_bytes(payload, role, suffix):
    digest = hashlib.sha256(payload).hexdigest()
    path = FOLDER / f"{role}.{digest[:24]}{suffix}"
    if path.exists() and path.read_bytes() != payload:
        raise ValueError("Immutable material asset collision")
    if not path.exists():
        path.write_bytes(payload)
    return reference(path)


def detail_images(role):
    y, x = np.mgrid[0:128, 0:128] / 128 * 2 * np.pi
    strength = {
        "cloth": 0.065,
        "fur": 0.08,
        "leather": 0.035,
        "hair": 0.07,
        "metal": 0.02,
        "trim": 0.015,
        "wood": 0.045,
        "stone": 0.025,
        "bone": 0.015,
    }.get(role, 0.0)
    nx = np.cos(x * 7) * np.sin(y * 9) * strength
    ny = np.sin(x * 7) * np.cos(y * 9) * strength
    if role in ("hair", "wood"):
        nx = np.cos(x * 12 + np.sin(y)) * strength
        ny *= 0.1
    normal = np.stack([nx, ny, np.ones_like(nx)], -1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    rough = 0.80 + 0.20 * np.sin(x * 5 + np.sin(y * 3)) * np.cos(y * 7)
    mr = np.stack([np.ones_like(x), rough, np.ones_like(x)], -1)
    out = {}
    for name, data in [("normal", normal * 0.5 + 0.5), ("rough", mr)]:
        stream = io.BytesIO()
        Image.fromarray(np.uint8(np.clip(data, 0, 1) * 255 + 0.5)).save(stream, format="PNG")
        out[name] = stream.getvalue()
    return out


def palette_for(entry, store):
    """Use stored constructor palettes, including historical assembly recipes."""
    values = []
    files = entry["files"]
    assembly = {}
    if "assembly" in files:
        assembly = json.loads(store.path(entry["id"], "assembly").read_text())
    paths = []
    recipes = []
    for part in assembly.get("parts", {}).values():
        if isinstance(part.get("recipe"), dict):
            if "path" in part["recipe"]:
                paths.append(ROOT / "media" / part["recipe"]["path"])
            else:
                recipes.append(part["recipe"])
    settings = assembly.get("constructor_settings") or {}
    for key in ("face", "arms", "legs", "outfit"):
        identity = settings.get(key)
        if identity:
            paths.extend(
                (ROOT / "media/constructor/library/v1" / identity / "parts").glob("*.recipe.json")
            )
    if "recipe" in files:
        paths.append(store.path(entry["id"], "recipe"))
    for path in sorted(set(paths)):
        if not path.exists():
            continue
        recipes.append(json.loads(path.read_text()))
    for recipe in recipes:
        palette = recipe.get("palette", {})
        if not isinstance(palette, dict):
            continue
        for name, color in palette.items():
            if isinstance(color, str) and len(color.lstrip("#")) == 6:
                values.append(
                    (np.array(list(bytes.fromhex(color.lstrip("#")))) / 255, semantic(name))
                )
    for name, color in settings.get("colors", {}).items():
        if color:
            values.append((np.array(list(bytes.fromhex(color.lstrip("#")))) / 255, semantic(name)))
    return values


def choose_roles(entry, colors, palette):
    identity = entry["id"].lower()
    if entry["kind"] == "character":
        default = "bone" if "skeleton" in identity else "skin"
        roles = np.full(len(colors), default, dtype="U10")
        if palette:
            rgb = np.array([p[0] for p in palette])
            names = np.array([p[1] for p in palette])
            for start in range(0, len(colors), 512):
                c = colors[start : start + 512]
                dist = np.sum((c[:, None, :] - rgb[None, :, :]) ** 2, axis=-1)
                roles[start : start + len(c)] = names[np.argmin(dist, axis=1)]
        return roles
    default = semantic(identity, "stone")
    if identity.startswith("equipment."):
        default = "wood" if any(n in identity for n in (".bow", ".staff", ".book")) else "metal"
    roles = np.full(len(colors), default, dtype="U10")
    r, g, b = colors.T
    # Unlabelled legacy props retain their authored palette. Conservative broad
    # surface inference; explicit source material names take precedence below.
    brown = (r > g * 1.18) & (g > b * 1.13) & (r < 0.65)
    green = (g > r * 1.25) & (g > b * 1.12)
    gold = (r > 0.55) & (g > r * 0.76) & (g < r * 0.94) & (b < g * 0.72)
    roles[brown] = (
        "leather"
        if identity.startswith("equipment.") and not any(x in identity for x in (".bow", ".staff"))
        else "wood"
    )
    roles[green] = "foliage"
    roles[gold] = "trim"
    if any(n in identity for n in ("crystal", "gem")):
        roles[(b > r * 1.15) | (g > r * 1.25)] = "crystal"
    return roles


def process(entry, store):
    source_ref = entry["files"]["model"]
    if "surface" in entry["files"] and "surface_model" in entry["files"]:
        previous = json.loads(store.path(entry["id"], "surface").read_text())
        if (
            previous.get("profile_version") == VERSION
            and previous.get("source_sha256") == source_ref["sha256"]
        ):
            # Unchanged sources keep their exact approved material version.
            # Bump VERSION deliberately when changing the material recipe.
            for ref in entry["files"].values():
                if ref["path"].startswith("materials/mixed/"):
                    target = FOLDER / Path(ref["path"]).name
                    if not target.exists():
                        shutil.copyfile(ROOT / "media" / ref["path"], target)
            return copy.deepcopy(entry)
    # Keep the game-compatible one-primitive model role until its loader supports
    # multiple materials. The movie explicitly consumes surface_model.
    if source_ref["sha256"] == "8c5631b561e8fe680e87edb056605879efa7151c9f8c96664db6b58a73aa6a12":
        experiment = next(
            a
            for a in json.loads((ROOT / "media/catalog.json").read_text())["assets"]
            if a["id"] == "character.experiments.viking_materials.10.body"
        )
        result = copy.deepcopy(entry)
        result["files"].update({k: v for k, v in experiment["files"].items() if k != "model"})
        result["files"]["surface_model"] = experiment["files"]["model"]
        result["revision"] += int(
            entry["files"].get("surface_model") != experiment["files"]["model"]
        )
        return result
    source = (ROOT / "media" / source_ref["path"]).read_bytes()
    doc, binary = unpack(source)
    d = copy.deepcopy(doc)
    data = bytearray(binary)
    new_materials = []
    slots = []
    texture_roles = {}
    files = {}
    palette = palette_for(entry, store)

    def append(values, shape):
        values = np.asarray(values, dtype="<f4")
        data.extend(b"\0" * (-len(data) % 4))
        offset = len(data)
        data.extend(values.tobytes())
        view = len(d["bufferViews"])
        d["bufferViews"].append({"buffer": 0, "byteOffset": offset, "byteLength": values.nbytes})
        d["accessors"].append(
            {"bufferView": view, "componentType": 5126, "count": len(values), "type": shape}
        )
        return len(d["accessors"]) - 1

    textures = {}

    def texture(role, kind):
        key = role + "_" + kind
        if key in textures:
            return {"index": textures[key], "texCoord": 1}
        payload = detail_images(role)[kind]
        file = publish_bytes(payload, key, ".png")
        files[key] = file
        data.extend(b"\0" * (-len(data) % 4))
        offset = len(data)
        data.extend(payload)
        view = len(d["bufferViews"])
        d["bufferViews"].append({"buffer": 0, "byteOffset": offset, "byteLength": len(payload)})
        image = len(d.setdefault("images", []))
        d["images"].append({"bufferView": view, "mimeType": "image/png"})
        sampler = len(d.setdefault("samplers", []))
        d["samplers"].append({"wrapS": 10497, "wrapT": 10497, "magFilter": 9729, "minFilter": 9987})
        index = len(d.setdefault("textures", []))
        d["textures"].append({"source": image, "sampler": sampler})
        textures[key] = index
        texture_roles[str(index)] = key
        return {"index": index, "texCoord": 1}

    for mesh in d["meshes"]:
        primitives = []
        for primitive in mesh["primitives"]:
            if primitive.get("mode", 4) != 4:
                raise ValueError("Unsupported non-triangle model")
            attrs = copy.deepcopy(primitive["attributes"])
            positions = accessor(doc, binary, attrs["POSITION"])
            count = len(positions)
            faces = (
                accessor(doc, binary, primitive["indices"]).reshape(-1, 3).astype(int)
                if "indices" in primitive
                else np.arange(count).reshape(-1, 3)
            )
            old = copy.deepcopy(doc.get("materials", [{}])[primitive.get("material", 0)])
            colors = (
                accessor(doc, binary, attrs["COLOR_0"])
                if "COLOR_0" in attrs
                else np.ones((count, 4))
            )
            old_pbr = old.get("pbrMetallicRoughness", {})
            if not old_pbr.get("baseColorTexture"):
                linear = colors.copy()
                linear[:, :3] = np.where(
                    colors[:, :3] <= 0.04045,
                    colors[:, :3] / 12.92,
                    ((colors[:, :3] + 0.055) / 1.055) ** 2.4,
                )
                attrs["COLOR_0"] = append(linear, "VEC4" if linear.shape[1] == 4 else "VEC3")
            face_normals = np.cross(
                positions[faces[:, 1]] - positions[faces[:, 0]],
                positions[faces[:, 2]] - positions[faces[:, 0]],
            )
            face_normals /= np.maximum(np.linalg.norm(face_normals, axis=1, keepdims=True), 1e-10)
            if "NORMAL" not in attrs:
                normals = np.zeros_like(positions)
                np.add.at(normals, faces.ravel(), np.repeat(face_normals, 3, axis=0))
                normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-10)
                attrs["NORMAL"] = append(normals, "VEC3")
            else:
                normals = accessor(doc, binary, attrs["NORMAL"])
            # Per-vertex secondary planar coordinates leave albedo UV0 untouched.
            # Full face streams get per-face dominant-plane charts; indexed props
            # use a continuous asset-wide projection and omit singular relief.
            stream = np.array_equal(faces.ravel(), np.arange(count))
            if stream:
                axis = np.repeat(np.argmax(np.abs(face_normals), axis=1), 3)
                uv = np.zeros((count, 2))
                for normal_axis, axes in enumerate(((1, 2), (2, 0), (0, 1))):
                    mask = axis == normal_axis
                    uv[mask] = positions[mask][:, axes] * 6
            else:
                spans = np.ptp(positions, axis=0)
                axes = np.argsort(spans)[-2:]
                uv = positions[:, axes] * 6
            attrs["TEXCOORD_1"] = append(uv, "VEC2")
            role_names = choose_roles(entry, colors[faces, :3].mean(axis=1), palette)
            material_name = old.get("name", "")
            explicit = semantic(material_name, "")
            if explicit:
                role_names[:] = explicit
            for role in sorted(set(role_names)):
                mat = copy.deepcopy(old)
                metal, rough = PROFILES[role]
                mat["name"] = "mixed/" + role
                pbr = mat.setdefault("pbrMetallicRoughness", {})
                pbr.update(metallicFactor=metal, roughnessFactor=rough)
                pbr["metallicRoughnessTexture"] = texture(role, "rough")
                if stream and role not in ("eyes", "skin", "crystal", "foliage", "matte"):
                    mat["normalTexture"] = {**texture(role, "normal"), "scale": 0.5}
                ext = mat.setdefault("extensions", {})
                if role in ("cloth", "fur"):
                    ext["KHR_materials_sheen"] = {
                        "sheenColorFactor": [0.12, 0.08, 0.16],
                        "sheenRoughnessFactor": 0.7,
                    }
                if role in ("hair", "metal") and stream:
                    ext["KHR_materials_anisotropy"] = {
                        "anisotropyStrength": 0.55 if role == "hair" else 0.30,
                        "anisotropyRotation": 0.0,
                    }
                if role in ("metal", "trim", "ceramic", "water"):
                    ext["KHR_materials_clearcoat"] = {
                        "clearcoatFactor": 0.5,
                        "clearcoatRoughnessFactor": 0.18,
                    }
                mat.setdefault("extras", {})["bhm_surface"] = {
                    "profile": role,
                    "version": VERSION,
                    "mapping": "detail-uv1",
                    "classification": "constructor-palette" if palette else "legacy-palette",
                    "flat_normals": "NORMAL" not in primitive["attributes"],
                }
                index = len(new_materials)
                new_materials.append(mat)
                slots.append(index)
                selected = faces[role_names == role].ravel().astype("<u4")
                data.extend(b"\0" * (-len(data) % 4))
                offset = len(data)
                data.extend(selected.tobytes())
                view = len(d["bufferViews"])
                d["bufferViews"].append(
                    {"buffer": 0, "byteOffset": offset, "byteLength": selected.nbytes}
                )
                ia = len(d["accessors"])
                d["accessors"].append(
                    {
                        "bufferView": view,
                        "componentType": 5125,
                        "count": len(selected),
                        "type": "SCALAR",
                    }
                )
                primitives.append(
                    {**primitive, "attributes": attrs, "indices": ia, "material": index}
                )
            # Preserve geometry and every source simulation attribute byte-for-byte.
            for name, index in primitive["attributes"].items():
                if name == "COLOR_0":
                    continue
                assert np.array_equal(accessor(d, data, attrs[name]), accessor(doc, binary, index))
            merged = np.concatenate(
                [
                    accessor(d, data, p["indices"]).reshape(-1, 3)
                    for p in primitives[-len(set(role_names)) :]
                ]
            )
            assert sorted(map(tuple, merged)) == sorted(map(tuple, faces))
        mesh["primitives"] = primitives
    d["materials"] = new_materials
    d["extensionsUsed"] = sorted(
        set(d.get("extensionsUsed", []))
        | {k for m in new_materials for k in m.get("extensions", {})}
    )
    d.setdefault("extras", {})["bhm_mixed_materials"] = {
        "version": VERSION,
        "source_sha256": source_ref["sha256"],
    }
    assert d.get("nodes") == doc.get("nodes") and d.get("skins") == doc.get("skins")
    # Also export existing embedded albedo/emission maps for renderers using SDK roles.
    for i, tex in enumerate(d.get("textures", [])):
        if str(i) in texture_roles:
            continue
        image = d["images"][tex["source"]]
        if "bufferView" not in image:
            raise ValueError("External image requires import")
        view = d["bufferViews"][image["bufferView"]]
        offset = view.get("byteOffset", 0)
        payload = bytes(data[offset : offset + view["byteLength"]])
        decoded = Image.open(io.BytesIO(payload)).convert("RGBA")
        buf = io.BytesIO()
        decoded.save(buf, format="PNG")
        role = "albedo_" + str(i)
        files[role] = publish_bytes(buf.getvalue(), role, ".png")
        texture_roles[str(i)] = role
    output = blob_glb(d, data)
    files["surface_model"] = publish_bytes(output, "model", ".glb")
    surface = {
        "schema_version": 1,
        "code": "mixed",
        "title": entry["title"],
        "source": entry["id"],
        "source_sha256": source_ref["sha256"],
        "model_sha256": files["surface_model"]["sha256"],
        "materials": new_materials,
        "slots": slots,
        "texture_roles": texture_roles,
        "profile_version": VERSION,
    }
    files["surface"] = publish_bytes(
        (json.dumps(surface, ensure_ascii=False, indent=2) + "\n").encode(), "surface", ".json"
    )
    result = copy.deepcopy(entry)
    result["files"].update(files)
    result["revision"] += int(
        result["files"].get("surface_model") != entry["files"].get("surface_model")
    )
    return result


def publish_stage(stage):
    pending_data = json.loads((stage / "publication.json").read_text())
    catalog_path = ROOT / "media/catalog.json"
    catalog = json.loads(catalog_path.read_text())
    by_id = {e["id"]: e for e in catalog["assets"]}
    results = {e["id"]: e for e in pending_data["entries"]}
    for identity, new in results.items():
        current = by_id[identity]
        if current["files"]["model"] != new["files"]["model"]:
            raise ValueError("Source changed after dry run: " + identity)
        for ref in new["files"].values():
            target = ROOT / "media" / ref["path"]
            candidate = (
                stage / target.name if ref["path"].startswith("materials/mixed/") else target
            )
            if (
                not candidate.is_file()
                or hashlib.sha256(candidate.read_bytes()).hexdigest() != ref["sha256"]
            ):
                raise ValueError("Staged file failed integrity check: " + str(candidate))
    # All source identities, staged files and geometry have been checked first.
    destination = ROOT / "media/materials/mixed"
    destination.mkdir(parents=True, exist_ok=True)
    for new in results.values():
        for ref in new["files"].values():
            if not ref["path"].startswith("materials/mixed/"):
                continue
            target = ROOT / "media" / ref["path"]
            candidate = stage / target.name
            if target.exists():
                if target.read_bytes() != candidate.read_bytes():
                    raise ValueError("Immutable collision")
            else:
                shutil.copyfile(candidate, target)
    merged = []
    for old in catalog["assets"]:
        if old["id"] in results:
            new = results[old["id"]]
            files = {**old["files"], **new["files"]}
            old = {**old, "files": files, "revision": max(old["revision"], new["revision"])}
        merged.append(old)
    catalog["assets"] = merged
    temporary = catalog_path.with_suffix(".next")
    temporary.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(catalog_path)
    (destination / "publication.json").write_text(
        json.dumps(
            {
                "profile_version": VERSION,
                "models": sum(
                    "surface_model" in e["files"] and "experiments." not in e["id"]
                    for e in catalog["assets"]
                ),
                "updated_in_batch": len(results),
                "geometry_unchanged": True,
                "legacy_model_role_preserved": True,
            },
            indent=2,
        )
        + "\n"
    )
    print("Published checked material versions:", len(results))


def main():
    global FOLDER
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, default=Path("/tmp/bhm-mixed-staging"))
    parser.add_argument(
        "--publish", action="store_true", help="Publish an already verified complete dry run"
    )
    parser.add_argument(
        "--asset", action="append", default=[], help="Process only this asset ID; repeatable"
    )
    args = parser.parse_args()
    FOLDER = args.stage.resolve()
    if args.publish:
        publish_stage(FOLDER)
        return
    FOLDER.mkdir(parents=True, exist_ok=True)
    store = AssetStore(ROOT)
    catalog = json.loads((ROOT / "media/catalog.json").read_text())
    results = []
    for e in catalog["assets"]:
        if (
            e["kind"] not in ("character", "decoration")
            or "model" not in e["files"]
            or "experiments." in e["id"]
        ):
            continue
        if args.asset and e["id"] not in args.asset:
            continue
        result = process(e, store)
        results.append(result)
        print(len(results), e["id"], flush=True)
    missing = set(args.asset) - {e["id"] for e in results}
    if missing:
        raise ValueError("Unknown/unprocessable material assets: " + str(sorted(missing)))
    (FOLDER / "publication.json").write_text(
        json.dumps({"version": VERSION, "entries": results}, ensure_ascii=False, indent=2) + "\n"
    )
    print("Dry run verified", len(results), "models; catalog unchanged")


if __name__ == "__main__":
    main()
