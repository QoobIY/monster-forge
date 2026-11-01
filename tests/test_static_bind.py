"""Static authoring uses the existing BHM exporter, without a game runtime."""

from __future__ import annotations

import builtins
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from monsterforge.runtime import bind_bones, bind_positions, load_bind_skeleton
from monsterforge.serialization import encoded
from tools.assets.bake_character_models import bone_matrices


class StaticBindTests(unittest.TestCase):
    def test_constructor_owned_bind_contracts_ignore_a_separate_empty_asset_library(self):
        from monsterforge.constructor_marsh_forest import build
        from monsterforge.workshop_constructor import default_settings

        expected = load_bind_skeleton()
        settings = default_settings()
        settings.update(race="satyr", **dict.fromkeys(("face", "outfit", "arms", "legs"), "native-satyr-01"))
        with tempfile.TemporaryDirectory(prefix="forge-bind-isolation-") as temporary:
            root = Path(temporary)
            library = root / "empty-library"
            library.mkdir()
            target = root / "build"
            with patch.dict(os.environ, {"MONSTER_FORGE_ASSET_ROOT": str(library)}):
                self.assertEqual(load_bind_skeleton(), expected)
                result = build(settings, target)
            self.assertEqual(json.loads((target / "skeleton.json").read_bytes()), expected)
            self.assertTrue(result["parts"])

    def test_source_preflight_checks_inventory_paths_without_reading_all_payloads(self):
        from monsterforge.paths import ROOT
        from monsterforge.resources import load_resources
        from monsterforge.runtime import source_availability

        resources = load_resources(ROOT)
        original_open = Path.open

        def metadata_only(path, *args, **kwargs):
            relative = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else None
            if relative in resources:
                raise AssertionError(
                    "Startup opened a source payload instead of checking its metadata"
                )
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", metadata_only):
            self.assertEqual(source_availability(), (True, None))

    def test_joint_origins_are_the_same_static_transforms_as_the_existing_exporter(self):
        for profile in ("canonical", "workshop_knees_v1"):
            with self.subTest(profile=profile):
                skeleton = load_bind_skeleton(profile)
                before = encoded(skeleton)
                positions = bind_positions(skeleton)
                bones = bind_bones(profile)
                self.assertEqual(
                    [bone["id"] for bone in bones], [bone["id"] for bone in skeleton["bones"]]
                )
                for bone, matrix in zip(bones, bone_matrices(skeleton), strict=True):
                    self.assertEqual(bone["position"], matrix[:3, 3].tolist())
                    self.assertEqual(bone["position"], positions[bone["id"]])
                self.assertEqual(encoded(skeleton), before)

    def test_static_bind_keeps_parent_rotation_and_local_translation(self):
        q = float(np.sqrt(0.5))
        skeleton = {
            "bones": [
                {
                    "id": "root",
                    "parent": None,
                    "bind_translation": [1, 2, 3],
                    "bind_rotation": [0, q, 0, q],
                },
                {
                    "id": "child",
                    "parent": "root",
                    "bind_translation": [1, 0, 0],
                    "bind_rotation": [0, 0, 0, 1],
                },
            ]
        }
        np.testing.assert_allclose(bind_positions(skeleton)["child"], [1, 2, 2], atol=1.0e-12)

    def test_existing_sculpt_and_knee_helpers_work_when_game_import_is_forbidden(self):
        script = """
import importlib.abc
import sys
class NoGame(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, *args):
        if fullname == 'machine_of_monsters' or fullname.startswith('machine_of_monsters.'):
            raise AssertionError('The standalone constructor imported a game runtime')
sys.meta_path.insert(0, NoGame())
from monsterforge.runtime import bind_positions, load_bind_skeleton
from monsterforge.constructor_knees import world_bind, skeleton_snapshot
from tools.creature_workshop.original_constructor import world_bind as sculpture_bind
assert sculpture_bind() == bind_positions(load_bind_skeleton('canonical'))
assert world_bind() == bind_positions(load_bind_skeleton('workshop_knees_v1'))
assert skeleton_snapshot()[1] == '73de9df60fc229702f4b7da5c6a1db4f156347bd0b10d114ecb88e73cb56c6c9'
assert not any(name.startswith('machine_of_monsters') for name in sys.modules)
"""
        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_saved_model_preview_and_compilation_do_not_import_a_game_solver(self):
        from monster_forge_sdk.characters import read_character_model
        from monsterforge.character_assembly import bake_build, preview_payload
        from monsterforge.skin_weights import build_weight_sidecar
        from tools.creature_workshop.geometry import compile_recipe, export_glb

        slots = ("head", "torso", "left_arm", "right_arm", "left_leg", "right_leg")
        original_import = builtins.__import__

        def no_game(name, *args, **kwargs):
            if name == "machine_of_monsters" or name.startswith("machine_of_monsters."):
                raise AssertionError("The standalone compiler imported a game runtime")
            return original_import(name, *args, **kwargs)

        with (
            tempfile.TemporaryDirectory(prefix="forge-static-bind-") as temporary,
            patch("builtins.__import__", no_game),
        ):
            root = Path(temporary)
            parts = {}
            for index, slot in enumerate(slots):
                directory = root / "parts" / slot
                directory.mkdir(parents=True)
                recipe = {
                    "schema_version": 1,
                    "id": "static-fixture." + slot,
                    "palette": {"primary": "8b755d"},
                    "commands": [
                        {
                            "id": slot,
                            "slot": slot,
                            "stage": 1,
                            "op": "box",
                            "part": slot,
                            "material": "primary",
                            "purpose": "Numeric bind/export fixture",
                            "center": [index * 0.1, 0.1, 0],
                            "size": [0.1, 0.2, 0.1],
                        }
                    ],
                }
                model, weights = directory / "model.glb", directory / "weights.json"
                export_glb(model, compile_recipe(recipe), recipe)
                weights.write_bytes(encoded(build_weight_sidecar(model, slot)))
                parts[slot] = {
                    "model": model.relative_to(root).as_posix(),
                    "weights": weights.relative_to(root).as_posix(),
                }
            blob = bake_build(root, {"parts": parts})
            model = read_character_model(blob)
            preview = preview_payload(blob)
        self.assertEqual(preview["contract"], "humanoid_v1")
        self.assertGreater(preview["triangles"], 0)
        self.assertEqual(preview["bind_bones"], bind_bones("canonical"))
        self.assertEqual(
            preview["parts"]["whole"]["model_sha256"], hashlib.sha256(blob).hexdigest()
        )
        np.testing.assert_allclose(np.sum(model["attributes"]["WEIGHTS_0"], axis=1), 1, atol=1.0e-6)
        self.assertFalse(json.loads(encoded(model["metadata"])).get("animations"))
