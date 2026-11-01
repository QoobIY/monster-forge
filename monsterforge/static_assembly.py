"""Lossless static drafts for existing authoring contracts without a bind rig.

The inputs are the constructor's embedded, identity-node triangle GLBs. This is
not an importer or autorigger: geometry and materials retain their source bytes,
and the resulting artifact explicitly has no runtime skin or animation support.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
import os
import re
import struct
import tempfile
from pathlib import Path

from .serialization import encoded

_MARKER = "monster_forge_static_assembly"
_COMPONENTS = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2),
               5125: ("I", 4), 5126: ("f", 4)}
_WIDTHS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
_ARRAYS = ("bufferViews", "accessors", "images", "samplers", "textures", "materials", "meshes", "nodes")


def _finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Nonfinite static GLB metadata")
    if isinstance(value, dict):
        for child in value.values():
            _finite(child)
    elif isinstance(value, list):
        for child in value:
            _finite(child)


def _unpack(blob):
    if len(blob) < 28 or struct.unpack_from("<4sII", blob) != (b"glTF", 2, len(blob)):
        raise ValueError("Invalid static GLB header")
    size, kind = struct.unpack_from("<I4s", blob, 12)
    if kind != b"JSON" or size % 4 or size > len(blob) - 28:
        raise ValueError("Invalid static GLB JSON chunk")
    length, kind = struct.unpack_from("<I4s", blob, 20 + size)
    if kind != b"BIN\0" or length != len(blob) - 28 - size or length % 4:
        raise ValueError("Invalid static GLB binary chunk")
    try:
        document = json.loads(blob[20:20 + size])
    except (ValueError, UnicodeError) as error:
        raise ValueError("Invalid static GLB document") from error
    _finite(document)
    if not isinstance(document, dict) or document.get("asset", {}).get("version") != "2.0":
        raise ValueError("Unsupported static GLB version")
    buffers = document.get("buffers", [])
    if (len(buffers) != 1 or "uri" in buffers[0]
            or type(buffers[0].get("byteLength")) is not int
            or not 0 <= length - buffers[0]["byteLength"] <= 3):
        raise ValueError("Static GLB must contain one embedded buffer")
    return document, blob[28 + size:]


def _index(items, value):
    if type(value) is not int or not 0 <= value < len(items):
        raise ValueError("Static GLB reference is outside its document")
    return items[value]


def _view(document, binary, index):
    view = _index(document.get("bufferViews", []), index)
    start, length = view.get("byteOffset", 0), view.get("byteLength")
    if (view.get("extensions") or view.get("buffer", 0) != 0 or type(start) is not int or type(length) is not int
            or start < 0 or length < 0 or start + length > document["buffers"][0]["byteLength"]
            or start + length > len(binary)):
        raise ValueError("Static GLB buffer view is outside its buffer")
    return view, start, length


def _accessor(document, binary, index):
    accessor = _index(document.get("accessors", []), index)
    if "sparse" in accessor or accessor.get("componentType") not in _COMPONENTS or accessor.get("type") not in _WIDTHS:
        raise ValueError("Unsupported static GLB accessor")
    view, start, length = _view(document, binary, accessor.get("bufferView"))
    component, _ = _COMPONENTS[accessor["componentType"]]
    width = _WIDTHS[accessor["type"]]
    row = struct.Struct("<" + component * width)
    offset, count, stride = accessor.get("byteOffset", 0), accessor.get("count"), view.get("byteStride", row.size)
    if (type(offset) is not int or offset < 0 or type(count) is not int or not 0 < count <= 3_000_000
            or type(stride) is not int or stride < row.size
            or offset + (count - 1) * stride + row.size > length):
        raise ValueError("Static GLB accessor is outside its buffer view")
    values = [list(row.unpack_from(binary, start + offset + i * stride)) for i in range(count)]
    if not all(math.isfinite(value) for value in values for value in value):
        raise ValueError("Nonfinite static GLB geometry")
    if accessor.get("normalized") and accessor["componentType"] != 5126:
        bits = _COMPONENTS[accessor["componentType"]][1] * 8
        signed = component.islower()
        divisor = (1 << (bits - int(signed))) - 1
        values = [[max(-1, value / divisor) if signed else value / divisor for value in row] for row in values]
    return values


def _identity(node):
    defaults = {"translation": [0, 0, 0], "rotation": [0, 0, 0, 1], "scale": [1, 1, 1],
                "matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]}
    if any(key in node and node[key] != value for key, value in defaults.items()):
        raise ValueError("Constructor source GLBs require baked identity-node geometry")
    if node.get("children") or "skin" in node or "camera" in node or node.get("weights") or node.get("extensions"):
        raise ValueError("Unsupported constructor source GLB node")


def _validate(document, binary, *, source=False):
    if document.get("skins") or document.get("animations") or document.get("cameras") or document.get("extensions"):
        raise ValueError("Static authoring drafts cannot contain skins, animation or external scene features")
    if (set(document.get("extensionsUsed", [])) | set(document.get("extensionsRequired", []))) - {"KHR_materials_unlit"}:
        raise ValueError("Unsupported constructor GLB extension")
    nodes, meshes = document.get("nodes", []), document.get("meshes", [])
    if not nodes or len(nodes) != len(meshes) or (source and len(nodes) != 1):
        raise ValueError("Unsupported constructor GLB scene layout")
    scene = _index(document.get("scenes", []), document.get("scene", 0))
    if scene.get("nodes") != list(range(len(nodes))):
        raise ValueError("Static authoring scene must preserve all source nodes")
    for index in range(len(document.get("bufferViews", []))):
        _view(document, binary, index)
    for index in range(len(document.get("accessors", []))):
        _accessor(document, binary, index)
    for image in document.get("images", []):
        if "uri" in image or image.get("extensions") or image.get("mimeType") != "image/png":
            raise ValueError("Constructor textures must be embedded PNGs")
        _view(document, binary, image.get("bufferView"))
    for texture in document.get("textures", []):
        if texture.get("extensions"):
            raise ValueError("Unsupported constructor texture extension")
        _index(document.get("images", []), texture.get("source"))
        if "sampler" in texture:
            _index(document.get("samplers", []), texture["sampler"])
    for material in document.get("materials", []):
        if set(material.get("extensions", {})) - {"KHR_materials_unlit"}:
            raise ValueError("Unsupported constructor material extension")
        for info in _texture_infos(material):
            _index(document.get("textures", []), info.get("index"))
    for node in nodes:
        _identity(node)
        mesh = _index(meshes, node.get("mesh"))
        if mesh.get("weights") or len(mesh.get("primitives", [])) != 1:
            raise ValueError("Constructor source meshes require one static primitive")
        primitive = mesh["primitives"][0]
        attributes = primitive.get("attributes", {})
        if (primitive.get("mode", 4) != 4 or primitive.get("targets") or primitive.get("extensions")
                or not {"POSITION", "NORMAL", "COLOR_0"} <= attributes.keys()
                or any(name.startswith(("JOINTS_", "WEIGHTS_")) for name in attributes)):
            raise ValueError("Constructor source meshes require unskinned colored triangles")
        position = _index(document["accessors"], attributes["POSITION"])
        if position["type"] != "VEC3" or position["componentType"] != 5126:
            raise ValueError("Unsupported constructor position format")
        for name, allowed in (("NORMAL", {"VEC3"}), ("COLOR_0", {"VEC3", "VEC4"}),
                              ("TEXCOORD_0", {"VEC2"}), ("_TEAM_MASK", {"SCALAR"})):
            if name in attributes and _index(document["accessors"], attributes[name])["type"] not in allowed:
                raise ValueError("Invalid constructor attribute dimensions: " + name)
        count = position["count"]
        if any(_index(document["accessors"], value)["count"] != count for value in attributes.values()):
            raise ValueError("Constructor source attribute counts differ")
        if "indices" in primitive:
            indices = _index(document["accessors"], primitive["indices"])
            if indices["type"] != "SCALAR" or indices["componentType"] not in {5121, 5123, 5125}:
                raise ValueError("Unsupported constructor triangle indices")
            values = [row[0] for row in _accessor(document, binary, primitive["indices"])]
            if len(values) % 3 or any(type(i) is not int or not 0 <= i < count for i in values):
                raise ValueError("Invalid constructor triangle indices")
        elif count % 3:
            raise ValueError("Invalid constructor triangle count")
        if "material" in primitive:
            _index(document.get("materials", []), primitive["material"])


def _texture_infos(material):
    pbr = material.get("pbrMetallicRoughness", {})
    return [owner[key] for owner, keys in ((pbr, ("baseColorTexture", "metallicRoughnessTexture")),
                                          (material, ("normalTexture", "occlusionTexture", "emissiveTexture")))
            for key in keys if key in owner]


def _pack(document, binary):
    header = encoded(document).rstrip(b"\n")
    header += b" " * (-len(header) % 4)
    binary += b"\0" * (-len(binary) % 4)
    return (struct.pack("<4sII", b"glTF", 2, 28 + len(header) + len(binary))
            + struct.pack("<I4s", len(header), b"JSON") + header
            + struct.pack("<I4s", len(binary), b"BIN\0") + binary)


def bake_static(root: Path, manifest: dict) -> bytes:
    """Merge compiled parts losslessly without inventing a bind rig or weights."""
    root = Path(root).resolve()
    metadata = {
        "schema_version": 1, "kind": "constructor_static_draft", "status": "authoring_draft",
        "skeleton_id": manifest["contract"], "bind_profile": manifest.get("bind_profile"),
        "source_assembly": manifest["id"], "rigging": "none", "runtime_support": False,
        "parts": {slot: {"revision_id": info["revision_id"], "source_model_sha256": info["model_sha256"]}
                  for slot, info in manifest["parts"].items()},
    }
    document = {"asset": {"version": "2.0", "generator": "Monster Forge static authoring assembly v1"},
                "scene": 0, "scenes": [{"nodes": []}], "buffers": [{"byteLength": 0}],
                "extras": {_MARKER: metadata}, **{key: [] for key in _ARRAYS}}
    binary = bytearray()
    for slot, info in sorted(manifest["parts"].items()):
        path = (root / info["model"]).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("Static part model escapes its build directory")
        blob = path.read_bytes()
        if hashlib.sha256(blob).hexdigest() != info["model_sha256"]:
            raise ValueError("Static source model hash differs from its build manifest")
        source, payload = _unpack(blob)
        _validate(source, payload, source=True)
        offsets = {key: len(document[key]) for key in _ARRAYS}
        start = len(binary)
        binary.extend(payload)
        binary.extend(b"\0" * (-len(binary) % 4))
        for key in _ARRAYS:
            document[key].extend(copy.deepcopy(source.get(key, [])))
        for view in document["bufferViews"][offsets["bufferViews"]:]:
            view["buffer"] = 0
            view["byteOffset"] = start + view.get("byteOffset", 0)
        for accessor in document["accessors"][offsets["accessors"]:]:
            accessor["bufferView"] += offsets["bufferViews"]
        for image in document["images"][offsets["images"]:]:
            image["bufferView"] += offsets["bufferViews"]
        for texture in document["textures"][offsets["textures"]:]:
            texture["source"] += offsets["images"]
            if "sampler" in texture:
                texture["sampler"] += offsets["samplers"]
        for material in document["materials"][offsets["materials"]:]:
            for texture_info in _texture_infos(material):
                texture_info["index"] += offsets["textures"]
        for mesh in document["meshes"][offsets["meshes"]:]:
            for primitive in mesh["primitives"]:
                primitive["attributes"] = {name: index + offsets["accessors"] for name, index in primitive["attributes"].items()}
                if "indices" in primitive:
                    primitive["indices"] += offsets["accessors"]
                if "material" in primitive:
                    primitive["material"] += offsets["materials"]
        for node in document["nodes"][offsets["nodes"]:]:
            node["mesh"] += offsets["meshes"]
            node.setdefault("name", slot)
            node.setdefault("extras", {})["monster_forge_slot"] = slot
        document["scenes"][0]["nodes"].extend(range(offsets["nodes"], len(document["nodes"])))
        used = set(document.get("extensionsUsed", [])) | set(source.get("extensionsUsed", []))
        required = set(document.get("extensionsRequired", [])) | set(source.get("extensionsRequired", []))
        if used:
            document["extensionsUsed"] = sorted(used)
        if required:
            document["extensionsRequired"] = sorted(required)
    document["buffers"][0]["byteLength"] = len(binary)
    if not metadata["parts"]:
        raise ValueError("Static assembly requires source parts")
    return _pack(document, bytes(binary))


def is_static(blob: bytes) -> bool:
    document, _ = _unpack(blob)
    return _MARKER in document.get("extras", {})


def _read_static(blob):
    document, binary = _unpack(blob)
    metadata = document.get("extras", {}).get(_MARKER)
    if (not isinstance(metadata, dict) or type(metadata.get("schema_version")) is not int
            or metadata["schema_version"] != 1
            or metadata.get("kind") != "constructor_static_draft" or metadata.get("rigging") != "none"
            or metadata.get("status") != "authoring_draft" or metadata.get("runtime_support") is not False
            or not isinstance(metadata.get("skeleton_id"), str) or not metadata["skeleton_id"]
            or not isinstance(metadata.get("parts"), dict) or not metadata["parts"]):
        raise ValueError("Unsupported static assembly metadata")
    _validate(document, binary)
    for info in metadata["parts"].values():
        if (not isinstance(info, dict) or not isinstance(info.get("revision_id"), str)
                or not info["revision_id"] or re.fullmatch(r"[0-9a-f]{64}", str(info.get("source_model_sha256", ""))) is None):
            raise ValueError("Invalid static assembly part provenance")
    if (len(document["nodes"]) != len(metadata["parts"])
            or {node.get("extras", {}).get("monster_forge_slot") for node in document["nodes"]} != metadata["parts"].keys()):
        raise ValueError("Static assembly source slots differ from its geometry")
    return metadata, document, binary


def preview_payload(blob: bytes) -> dict:
    """Decode the saved static artifact into the existing per-part viewer protocol."""
    metadata, document, binary = _read_static(blob)
    parts = {}
    triangles = 0
    for node in document["nodes"]:
        slot = node["extras"]["monster_forge_slot"]
        primitive = document["meshes"][node["mesh"]]["primitives"][0]
        attrs = {name: _accessor(document, binary, index) for name, index in primitive["attributes"].items()}
        indices = ([row[0] for row in _accessor(document, binary, primitive["indices"])]
                   if "indices" in primitive else range(len(attrs["POSITION"])))
        material = document["materials"][primitive["material"]] if "material" in primitive else {}
        pbr = material.get("pbrMetallicRoughness", {})
        factor = pbr.get("baseColorFactor", [1, 1, 1, 1])
        data = {"positions": [value for index in indices for value in attrs["POSITION"][index]],
                "normals": [value for index in indices for value in attrs["NORMAL"][index]],
                "colors": [value * factor[axis] for index in indices for axis, value in enumerate(attrs["COLOR_0"][index][:3])],
                "uvs": [value for index in indices for value in attrs["TEXCOORD_0"][index]]
                if "TEXCOORD_0" in attrs else [.002] * (len(indices) * 2)}
        if "baseColorTexture" in pbr:
            texture = document["textures"][pbr["baseColorTexture"]["index"]]
            image = document["images"][texture["source"]]
            _, start, length = _view(document, binary, image["bufferView"])
            data["texture"] = base64.b64encode(binary[start:start + length]).decode()
            data["texture_flip_y"] = False
        triangles += len(indices) // 3
        parts[slot] = {"model_sha256": metadata["parts"][slot]["source_model_sha256"], "geometry": data}
    return {"schema_version": 2, "contract": metadata["skeleton_id"], "rigging": "none",
            "runtime_support": False, "status": "authoring_draft", "bind_bones": [],
            "triangles": triangles, "parts": parts,
            "warnings": ["Статическая сборка: скелет и анимации для этого типа не заданы."]}


def preview_image(blob: bytes) -> bytes:
    """Rebuild a disposable display card from this exact saved static draft."""
    import numpy as np

    from tools.creature_workshop.geometry import render_png

    from .constructor_cache import CACHE
    target = CACHE / ("static-assembly-" + hashlib.sha256(blob).hexdigest() + ".png")
    if not target.exists():
        payload = preview_payload(blob)
        arrays = tuple(np.concatenate([np.asarray(part["geometry"][key], dtype="<f4").reshape(-1, 3)
                                       for part in payload["parts"].values()])
                       for key in ("positions", "normals", "colors")) + ([],)
        CACHE.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=CACHE) as temporary:
            path = Path(temporary) / "preview.png"
            render_png(path, arrays, size=256)
            os.replace(path, target)
    return target.read_bytes()
