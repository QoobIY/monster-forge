"""Portable character readers share release locations and skin admission rules."""

import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from monster_forge_sdk import AssetStore
from monster_forge_sdk.characters import body_rig, decode_skin, encode_skin, load_skeleton

CONTRACT_HASHES = {
    "body_rigs.json": "b2556755ec4ba7f62a950c1287d3a8ed818f8646e7dca05d366fd5693d71dcd8",
    "humanoid/canonical.json": "037753438d7c06f6817902fbd008609ac66bd1f6878cc5843dbfbd10318c9e99",
    "humanoid/workshop_knees_v1.json": "c87da3ae98adcc6e8781b37b33d829c540a1a26d02b8d98eed9c82f32a84386b",
}


class SkinAdmissionTests(unittest.TestCase):
    def payload(self):
        return {
            "bind_profile": "canonical",
            "bone_palette": ["root"],
            "skin_indices": [[0, 0, 0, 0]],
            "skin_weights": [[1, 0, 0, 0]],
            "hand_socket": [0.1, 0.2, 0.3],
        }

    def test_legacy_and_binary_weights_return_the_same_metadata(self):
        payload = self.payload()
        legacy = json.dumps(payload).encode()
        binary = encode_skin(payload)
        self.assertEqual(decode_skin(legacy), decode_skin(binary))
        self.assertEqual(
            decode_skin(legacy, metadata_only=True),
            decode_skin(binary, metadata_only=True),
        )
        self.assertNotIn("skin_weights", decode_skin(legacy, metadata_only=True))

    def test_legacy_weights_cannot_bypass_influence_validation(self):
        for field, value in (
            ("skin_weights", [[0.5, 0, 0, 0]]),
            ("skin_weights", [[float("nan"), 0, 0, 0]]),
            ("skin_indices", [[1, 0, 0, 0]]),
            ("skin_indices", [[0, 0, 0, 0], [0, 0, 0, 0]]),
            ("bone_palette", []),
        ):
            payload = {**self.payload(), field: value}
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    decode_skin(json.dumps(payload).encode())
                with self.assertRaises(ValueError):
                    decode_skin(json.dumps(payload).encode(), metadata_only=True)

    def test_encoder_rejects_metadata_that_the_binary_reader_cannot_read(self):
        payload = {**self.payload(), "note": "x" * 65536}
        with self.assertRaisesRegex(ValueError, "metadata size"):
            encode_skin(payload)

    def test_metadata_only_binary_read_validates_the_palette(self):
        header = json.dumps({"bone_palette": []}).encode()
        blob = struct.pack("<8sII", b"MOMSKIN1", len(header), 1)
        blob += header + struct.pack("<4H4f", 0, 0, 0, 0, 1, 0, 0, 0)
        with self.assertRaisesRegex(ValueError, "bone palette"):
            decode_skin(blob, metadata_only=True)


class ReleaseLocationTests(unittest.TestCase):
    def test_store_and_character_readers_share_explicit_and_environment_roots(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rigs = root / "media/rigs"
            (rigs / "humanoid").mkdir(parents=True)
            (root / "media/catalog.json").write_text('{"schema_version":1,"assets":[]}')
            skeleton = {"schema_version": 2, "bones": [{
                "id": "root", "parent": None, "bind_translation": [0, 0, 0],
                "bind_rotation": [0, 0, 0, 1],
            }]}
            (rigs / "humanoid/canonical.json").write_text(json.dumps(skeleton))
            rig = {"slots": [{"id": "head"}]}
            (rigs / "body_rigs.json").write_text(json.dumps({
                "schema_version": 1, "rigs": {"humanoid_v1": rig},
            }))
            with patch.dict("os.environ", {"MONSTER_FORGE_ASSET_ROOT": str(root)}):
                self.assertEqual(AssetStore().root, root.resolve())
                self.assertEqual(load_skeleton(), skeleton)
                self.assertEqual(body_rig("humanoid_v1"), rig)
            with patch.dict("os.environ", {"MONSTER_FORGE_ASSET_ROOT": str(root / "missing")}):
                for value in (root, str(root)):
                    self.assertEqual(AssetStore(value).root, root.resolve())
                    self.assertEqual(load_skeleton(root=value), skeleton)
                    self.assertEqual(body_rig("humanoid_v1", root=value), rig)

    def test_missing_explicit_release_never_falls_back_to_sdk_defaults(self):
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing"
            with patch.dict("os.environ", {"MONSTER_FORGE_ASSET_ROOT": str(missing)}):
                for read in (load_skeleton, lambda: body_rig("humanoid_v1")):
                    with self.assertRaises(FileNotFoundError):
                        read()
            with self.assertRaises(FileNotFoundError):
                load_skeleton(root=missing)
            with self.assertRaises(FileNotFoundError):
                body_rig("humanoid_v1", root=missing)


class BindResourceTests(unittest.TestCase):
    def test_default_contracts_and_packaging_preserve_the_single_immutable_source(self):
        from tools.check_release import CODE_CONTRACTS

        root = Path(__file__).resolve().parents[1]
        config = tomllib.loads((root / "pyproject.toml").read_text())
        packaging = config["tool"]["setuptools"]
        self.assertEqual(packaging["package-dir"]["monster_forge_sdk._contracts"], "media/rigs")
        self.assertEqual(set(packaging["package-data"]["monster_forge_sdk._contracts"]), set(CONTRACT_HASHES))
        self.assertEqual(set(CODE_CONTRACTS), {"media/rigs/" + name for name in CONTRACT_HASHES})
        for name, digest in CONTRACT_HASHES.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((root / "media/rigs" / name).read_bytes()).hexdigest(), digest)
        with patch.dict("os.environ", {}, clear=True):
            for profile in ("canonical", "workshop_knees_v1"):
                expected = json.loads((root / "media/rigs/humanoid" / (profile + ".json")).read_bytes())
                self.assertEqual(load_skeleton(profile), expected)
            registry = json.loads((root / "media/rigs/body_rigs.json").read_bytes())
            self.assertEqual(body_rig("humanoid_v1"), registry["rigs"]["humanoid_v1"])

    @unittest.skipUnless(os.environ.get("MONSTER_FORGE_TEST_WHEEL"),
                         "Build a wheel and set MONSTER_FORGE_TEST_WHEEL for the isolated installation check")
    def test_installed_wheel_has_exact_contract_bytes_and_needs_no_asset_release(self):
        wheel = Path(os.environ["MONSTER_FORGE_TEST_WHEEL"])
        with tempfile.TemporaryDirectory(prefix="forge-sdk-wheel-") as temporary:
            root = Path(temporary)
            installed = root / "installed"
            with zipfile.ZipFile(wheel) as archive:
                for name, digest in CONTRACT_HASHES.items():
                    content = archive.read("monster_forge_sdk/_contracts/" + name)
                    self.assertEqual(hashlib.sha256(content).hexdigest(), digest)
                archive.extractall(installed)
            environment = os.environ.copy()
            environment.pop("MONSTER_FORGE_ASSET_ROOT", None)
            script = """
import json, os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from monster_forge_sdk.characters import body_rig, load_skeleton
canonical = load_skeleton()
workshop = load_skeleton('workshop_knees_v1')
assert canonical['schema_version'] == workshop['schema_version'] == 2
assert canonical != workshop
assert body_rig('humanoid_v1')['id'] == 'humanoid_v1'
canonical['bones'].clear()
assert load_skeleton()['bones']
assert not (Path(sys.argv[1]) / 'media').exists()
release = Path.cwd() / 'explicit-release'
(release / 'media/rigs/humanoid').mkdir(parents=True)
(release / 'media/rigs/humanoid/canonical.json').write_text(json.dumps({'schema_version': 2, 'bones': []}))
(release / 'media/rigs/body_rigs.json').write_text(json.dumps({'schema_version': 1, 'rigs': {'humanoid_v1': {'id': 'explicit'}}}))
os.environ['MONSTER_FORGE_ASSET_ROOT'] = str(release)
assert load_skeleton()['bones'] == []
assert body_rig('humanoid_v1')['id'] == 'explicit'
os.environ['MONSTER_FORGE_ASSET_ROOT'] = str(release / 'missing')
assert load_skeleton(root=release)['bones'] == []
assert body_rig('humanoid_v1', root=release)['id'] == 'explicit'
for read in (load_skeleton, lambda: body_rig('humanoid_v1')):
    try:
        read()
    except FileNotFoundError:
        pass
    else:
        raise AssertionError('Explicit missing release fell back to bundled data')
assert all(name not in sys.modules for name in ('flask', 'numpy', 'machine_of_monsters'))
print('isolated wheel bind resources OK')
"""
            result = subprocess.run([sys.executable, "-I", "-S", "-c", script, str(installed)],
                                    cwd=root, env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "isolated wheel bind resources OK")
