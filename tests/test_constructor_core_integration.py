"""Core boundaries, supported projection and isolated source extensions."""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from monsterforge import workshop_constructor as legacy
from monsterforge.constructor import DEFAULT_REGISTRY, ConstructorService, SourceBundle
from monsterforge.constructor.sources import load_part
from monsterforge.paths import ROOT
from monsterforge.runtime import source_availability
from monsterforge.serialization import encoded

HAS_SOURCE_PACK = source_availability()[0]


class ConstructorCoreTests(unittest.TestCase):
    def test_core_imports_and_settings_do_not_load_an_animation_solver(self):
        script = """
import importlib.abc
import sys
class NoSolver(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, *args):
        if fullname == 'machine_of_monsters' or fullname.startswith('machine_of_monsters.'):
            raise ModuleNotFoundError('Optional solver deliberately absent', name=fullname)
sys.meta_path.insert(0, NoSolver())
from monsterforge.constructor import ConstructorService, DEFAULT_REGISTRY
service = ConstructorService()
assert service.validate_settings(service.default_settings())['race'] == 'human'
assert DEFAULT_REGISTRY.supported_races
assert not any(name.startswith('machine_of_monsters') for name in sys.modules)
"""
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_core_has_no_import_dependency_on_its_compatibility_adapter(self):
        for path in (ROOT / "monsterforge/constructor").glob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn("workshop_constructor", node.module or "", str(path))
                    self.assertNotIn(
                        "workshop_constructor", [alias.name for alias in node.names], str(path)
                    )

    @unittest.skipUnless(HAS_SOURCE_PACK, "The constructor source pack is required")
    def test_existing_active_races_and_parts_remain_editable_in_the_default_catalog(self):
        service = ConstructorService()
        complete = service.catalog()
        restricted = service.catalog(include_legacy=False)
        self.assertEqual(
            [race["id"] for race in complete["races"]], list(DEFAULT_REGISTRY.active_races)
        )
        self.assertTrue(all(race["editable"] for race in complete["races"]))
        self.assertEqual(restricted["supported_contracts"], ["humanoid_v1"])
        self.assertTrue(all(race["contract"] == "humanoid_v1" for race in restricted["races"]))
        visible = {race["id"] for race in complete["races"]}
        self.assertTrue(all(item["settings"]["race"] in visible for item in complete["presets"]))
        self.assertTrue(all(item["race"] in {*visible, None} for item in complete["outfits"]))
        centaur = next(race for race in complete["races"] if race["id"] == "centaur")
        self.assertTrue(centaur["editable"])
        self.assertNotIn("centaur", {race["id"] for race in restricted["races"]})
        self.assertIn("centaur", DEFAULT_REGISTRY.races)

    @unittest.skipUnless(
        HAS_SOURCE_PACK, "The constructor source pack is required for immutable byte checks"
    )
    def test_refactor_preserves_the_preexisting_default_assembly_bytes(self):
        # Captured before extraction from workshop_constructor. This catches
        # changes to source selection, recipe order, canonical JSON and skinning.
        with tempfile.TemporaryDirectory(prefix="forge-core-golden-") as temporary:
            instruction, model = ConstructorService().compact_assembly(
                legacy.default_settings(), Path(temporary)
            )
        self.assertEqual(
            hashlib.sha256(model).hexdigest(),
            "8d7082b8f1ef17794757bc5c7fe99445ae3a79c48993cd2e3c8f772937cd3142",
        )
        self.assertEqual(
            hashlib.sha256(encoded(instruction)).hexdigest(),
            "f4be4f76571ab18ae712337e682760b2c62565901f3664c261c188f48cfb49b7",
        )

    def fixture(self, root):
        source = DEFAULT_REGISTRY.source_folder("library-human-01")
        directory = root / "media/constructor/community/human/v1"
        shutil.copytree(source, directory)
        from monsterforge.constructor_cache import resolve

        manifest = json.loads((source / "parts.json").read_text())
        for part in manifest["parts"].values():
            (directory / part["model"]).write_bytes(resolve(source / part["model"]).read_bytes())
        bundle = SourceBundle(
            id="community-human-v1",
            label="Community human",
            race="human",
            gender="male",
            directory=directory,
            manifest_sha256=hashlib.sha256((directory / "parts.json").read_bytes()).hexdigest(),
        )
        registry = replace(DEFAULT_REGISTRY, asset_root=root)
        return registry, bundle

    def test_source_registration_is_isolated_and_pins_the_approved_manifest(self):
        with tempfile.TemporaryDirectory(prefix="forge-core-extension-") as temporary:
            registry, source = self.fixture(Path(temporary))
            extended = registry.with_source(source)
            self.assertNotIn(source.id, registry.library_ids)
            self.assertIn(source.id, extended.library_ids)
            settings = ConstructorService(extended).default_settings()
            settings.update(face=source.id, outfit=source.id, arms=source.id, legs=source.id)
            self.assertEqual(ConstructorService(extended).validate_settings(settings), settings)
            recipe, provenance = load_part(source.id, "head", registry=extended)
            self.assertEqual(provenance["donor"], source.id)
            self.assertTrue(all(command["slot"] == "head" for command in recipe["commands"]))
            original = (source.directory / "parts.json").read_bytes()
            (source.directory / "parts.json").write_bytes(original + b"\n")
            with self.assertRaisesRegex(ValueError, "manifest changed"):
                load_part(source.id, "head", registry=extended)

    def test_source_registration_rejects_collision_new_rigs_and_source_escape(self):
        with tempfile.TemporaryDirectory(prefix="forge-core-admission-") as temporary:
            registry, source = self.fixture(Path(temporary))
            for invalid in (
                replace(source, id="library-human-01"),
                replace(source, contract="quadruped_v1"),
                replace(source, race="centaur"),
                replace(source, directory=Path("/tmp/outside")),
                replace(source, manifest_sha256="0" * 64),
            ):
                with self.subTest(source=invalid), self.assertRaises(ValueError):
                    registry.with_source(invalid)
            data = json.loads((source.directory / "parts.json").read_text())
            data["parts"]["head"]["recipe"] = "../../outside.json"
            blob = encoded(data)
            (source.directory / "parts.json").write_bytes(blob)
            invalid = replace(source, manifest_sha256=hashlib.sha256(blob).hexdigest())
            with self.assertRaisesRegex(ValueError, "escapes"):
                registry.with_source(invalid)

    @unittest.skipUnless(HAS_SOURCE_PACK, "The constructor source pack is required")
    def test_registered_owned_body_is_projected_from_the_same_registry_as_validation(self):
        with tempfile.TemporaryDirectory(prefix="forge-core-owned-extension-") as temporary:
            registry, source = self.fixture(Path(temporary))
            # This verifies registry projection, not artistic race classification.
            extended = registry.with_source(replace(source, race="panda"))
            race = next(
                item
                for item in ConstructorService(extended).catalog()["races"]
                if item["id"] == "panda"
            )
            self.assertIn(source.id, [item["id"] for item in race["body_variants"]["male"]])
            self.assertIn(source.id, race["faces"])

    @unittest.skipUnless(
        HAS_SOURCE_PACK, "The constructor source pack is required for a full source extension build"
    )
    def test_registered_source_builds_one_skinned_assembly_without_rewriting_evidence(self):
        from monster_forge_sdk.characters import read_character_model

        with tempfile.TemporaryDirectory(prefix="forge-core-extension-build-") as temporary:
            root = Path(temporary)
            registry, source = self.fixture(root)
            snapshot = {
                path.relative_to(source.directory).as_posix(): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in source.directory.rglob("*")
                if path.is_file()
            }
            service = ConstructorService(registry.with_source(source))
            settings = service.default_settings()
            settings.update(face=source.id, outfit=source.id, arms=source.id, legs=source.id)
            instruction, blob = service.compact_assembly(settings, root / "build")
            model = read_character_model(blob)
            self.assertEqual(instruction["constructor_settings"], settings)
            self.assertEqual(set(instruction["parts"]), set(registry.slots))
            self.assertEqual(model["metadata"]["skeleton_id"], "humanoid_v1")
            self.assertEqual(hashlib.sha256(blob).hexdigest(), instruction["model"]["sha256"])
            self.assertEqual(
                {
                    path.relative_to(source.directory).as_posix(): hashlib.sha256(
                        path.read_bytes()
                    ).hexdigest()
                    for path in source.directory.rglob("*")
                    if path.is_file()
                },
                snapshot,
            )

    def test_compatibility_facade_keeps_build_and_renderer_ports_in_orchestration(self):
        with patch.object(legacy, "build", side_effect=RuntimeError("legacy build port")):
            with self.assertRaisesRegex(RuntimeError, "legacy build port"):
                legacy.preview(legacy.default_settings())
            with self.assertRaisesRegex(RuntimeError, "legacy build port"):
                legacy.export_bundle(legacy.default_settings())
        renderer = object()
        with patch.object(legacy, "render_png", renderer):
            self.assertIs(legacy._service().renderer, renderer)
