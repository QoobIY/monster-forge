"""Existing unrigged authoring parts retain geometry, materials and provenance."""

import base64
import copy
import hashlib
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from monsterforge.static_assembly import bake_static, is_static, preview_payload


def pack(document, binary):
    header = json.dumps(document, separators=(",", ":")).encode()
    header += b" " * (-len(header) % 4)
    binary += b"\0" * (-len(binary) % 4)
    return (struct.pack("<4sII", b"glTF", 2, 28 + len(header) + len(binary))
            + struct.pack("<I4s", len(header), b"JSON") + header
            + struct.pack("<I4s", len(binary), b"BIN\0") + binary)


def unpack(blob):
    size = struct.unpack_from("<I", blob, 12)[0]
    return json.loads(blob[20:20 + size]), blob[28 + size:]


def png(color):
    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\0" + bytes(color))) + chunk(b"IEND", b""))


def source_model(slot, height):
    blocks = (
        struct.pack("<9f", 0, height, 0, 1, height, 0, 0, height + 1, 0),
        struct.pack("<9f", *([0, 0, 1] * 3)),
        bytes([255, 128, 64, 255] * 3),
        struct.pack("<6f", 0, 0, 1, 0, 0, 1),
        struct.pack("<3f", 1, 0, 1),
        struct.pack("<3H", 2, 0, 1),
        png((30 if slot == "head" else 90, 60, 120)),
    )
    binary = bytearray()
    views = []
    for block in blocks:
        views.append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(block)})
        binary.extend(block)
        binary.extend(b"\0" * (-len(binary) % 4))
    attributes = {"POSITION": 0, "NORMAL": 1, "COLOR_0": 2, "TEXCOORD_0": 3, "_TEAM_MASK": 4}
    document = {
        "asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "authored-" + slot, "extras": {"source_note": slot}}],
        "meshes": [{"name": slot, "primitives": [{"attributes": attributes, "indices": 5, "material": 0}],
                    "extras": {"command_ids": [slot + "-command"], "command_ends": [3], "recipe_schema": 1}}],
        "materials": [{"name": slot + "-material", "doubleSided": True,
                       "pbrMetallicRoughness": {"baseColorTexture": {"index": 0}, "baseColorFactor": [.8, .6, .4, 1],
                                                 "metallicFactor": 0, "roughnessFactor": .7},
                       "normalTexture": {"index": 0, "scale": .5}}],
        "images": [{"bufferView": 6, "mimeType": "image/png"}],
        "samplers": [{"minFilter": 9729, "magFilter": 9729, "wrapS": 10497, "wrapT": 10497}],
        "textures": [{"source": 0, "sampler": 0}],
        "bufferViews": views, "buffers": [{"byteLength": len(binary)}],
        "accessors": [{"bufferView": i, "componentType": component, "count": 3, "type": kind}
                      for i, (component, kind) in enumerate(((5126, "VEC3"), (5126, "VEC3"),
                                                           (5121, "VEC4"), (5126, "VEC2"),
                                                           (5126, "SCALAR"), (5123, "SCALAR")))],
    }
    document["accessors"][2]["normalized"] = True
    return pack(document, bytes(binary))


class StaticAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.manifest = {"id": "source-assembly", "contract": "centaur_authoring_v1", "bind_profile": None, "parts": {}}
        self.sources = {}
        for slot, height in (("head", 2), ("torso", 0)):
            blob = source_model(slot, height)
            path = self.root / "parts" / slot / "model.glb"
            path.parent.mkdir(parents=True)
            path.write_bytes(blob)
            self.sources[slot] = blob
            self.manifest["parts"][slot] = {"model": path.relative_to(self.root).as_posix(),
                                            "model_sha256": hashlib.sha256(blob).hexdigest(),
                                            "revision_id": slot + "-revision"}

    def replace_source(self, slot, document, binary):
        blob = pack(document, binary)
        (self.root / self.manifest["parts"][slot]["model"]).write_bytes(blob)
        self.manifest["parts"][slot]["model_sha256"] = hashlib.sha256(blob).hexdigest()

    def test_merge_preserves_each_buffer_view_material_texture_uv_mask_and_command_extras(self):
        original_manifest = copy.deepcopy(self.manifest)
        blob = bake_static(self.root, self.manifest)
        document, binary = unpack(blob)
        self.assertTrue(is_static(blob))
        self.assertEqual(self.manifest, original_manifest)
        self.assertEqual(len(document["meshes"]), 2)
        self.assertEqual(len(document["nodes"]), 2)
        self.assertNotIn("skins", document)
        self.assertNotIn("animations", document)
        previous_views = 0
        for number, slot in enumerate(sorted(self.sources)):
            source, payload = unpack(self.sources[slot])
            for view_number, original in enumerate(source["bufferViews"]):
                merged = document["bufferViews"][previous_views + view_number]
                a, b = original["byteOffset"], merged["byteOffset"]
                self.assertEqual(binary[b:b + merged["byteLength"]], payload[a:a + original["byteLength"]])
            self.assertEqual(document["meshes"][number]["extras"], source["meshes"][0]["extras"])
            self.assertIn("_TEAM_MASK", document["meshes"][number]["primitives"][0]["attributes"])
            expected = copy.deepcopy(source["materials"][0])
            expected["pbrMetallicRoughness"]["baseColorTexture"]["index"] = number
            expected["normalTexture"]["index"] = number
            self.assertEqual(document["materials"][number], expected)
            self.assertEqual(document["textures"][number], {"source": number, "sampler": number})
            self.assertEqual(document["nodes"][number]["extras"]["source_note"], slot)
            self.assertEqual((self.root / self.manifest["parts"][slot]["model"]).read_bytes(), self.sources[slot])
            previous_views += len(source["bufferViews"])
        metadata = document["extras"]["monster_forge_static_assembly"]
        self.assertEqual(metadata["skeleton_id"], self.manifest["contract"])
        self.assertEqual(metadata["rigging"], "none")
        self.assertFalse(metadata["runtime_support"])
        self.assertEqual(metadata["status"], "authoring_draft")
        for slot, info in self.manifest["parts"].items():
            self.assertEqual(metadata["parts"][slot]["source_model_sha256"], info["model_sha256"])
            self.assertEqual(metadata["parts"][slot]["revision_id"], info["revision_id"])
        self.assertEqual(blob, bake_static(self.root, self.manifest))

    def test_preview_uses_saved_indexed_geometry_uv_color_factors_and_embedded_texture(self):
        payload = preview_payload(bake_static(self.root, self.manifest))
        self.assertEqual(payload["triangles"], 2)
        self.assertEqual(payload["bind_bones"], [])
        self.assertFalse(payload["runtime_support"])
        self.assertEqual(payload["rigging"], "none")
        for slot, height in (("head", 2), ("torso", 0)):
            data = payload["parts"][slot]["geometry"]
            self.assertEqual(data["positions"], [0, height + 1, 0, 0, height, 0, 1, height, 0])
            self.assertEqual(data["uvs"], [0, 1, 0, 0, 1, 0])
            self.assertEqual(data["normals"], [0, 0, 1] * 3)
            self.assertAlmostEqual(data["colors"][0], .8)
            self.assertAlmostEqual(data["colors"][1], 128 / 255 * .6)
            self.assertIs(data["texture_flip_y"], False)
            source, binary = unpack(self.sources[slot])
            view = source["bufferViews"][source["images"][0]["bufferView"]]
            start = view["byteOffset"]
            self.assertEqual(base64.b64decode(data["texture"]), binary[start:start + view["byteLength"]])

    def test_external_data_nonfinite_attributes_skin_and_unbaked_transforms_are_rejected(self):
        original, binary = unpack(self.sources["head"])
        variants = []
        external_buffer = copy.deepcopy(original)
        external_buffer["buffers"][0]["uri"] = "part.bin"
        variants.append((external_buffer, binary))
        external_image = copy.deepcopy(original)
        external_image["images"][0]["uri"] = "texture.png"
        variants.append((external_image, binary))
        unbaked = copy.deepcopy(original)
        unbaked["nodes"][0]["translation"] = [.1, 0, 0]
        variants.append((unbaked, binary))
        skinned = copy.deepcopy(original)
        skinned["meshes"][0]["primitives"][0]["attributes"]["JOINTS_0"] = 2
        variants.append((skinned, binary))
        nonfinite = bytearray(binary)
        struct.pack_into("<f", nonfinite, 0, float("nan"))
        variants.append((original, bytes(nonfinite)))
        for document, payload in variants:
            with self.subTest(document=document["nodes"]):
                self.replace_source("head", document, payload)
                with self.assertRaises(ValueError):
                    bake_static(self.root, self.manifest)

    def test_missing_or_changed_source_hash_never_compiles_a_different_draft(self):
        info = self.manifest["parts"]["head"]
        (self.root / info["model"]).write_bytes(self.sources["torso"])
        with self.assertRaisesRegex(ValueError, "hash"):
            bake_static(self.root, self.manifest)


if __name__ == "__main__":
    unittest.main()
