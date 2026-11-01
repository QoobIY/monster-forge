"""Portable constructor interfaces: no solver, private media or bundled inventory."""

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

from monsterforge.constructor import ConstructorRegistry, ConstructorService, SourceBundle
from monsterforge.paths import ROOT


class ConstructorBoundaryTests(unittest.TestCase):
    def test_public_api_imports_without_solver_or_asset_reads(self):
        script = """
import importlib.abc
import pathlib
import sys
class NoSolver(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, *args):
        if fullname == 'machine_of_monsters' or fullname.startswith('machine_of_monsters.'):
            raise ModuleNotFoundError('Optional solver deliberately absent', name=fullname)
sys.meta_path.insert(0, NoSolver())
for name in ('read_text', 'read_bytes'):
    original = getattr(pathlib.Path, name)
    def check(path, *args, _original=original, **kwargs):
        if 'media' in path.parts or 'config' in path.parts:
            raise AssertionError('Public API imported private asset data: ' + str(path))
        return _original(path, *args, **kwargs)
    setattr(pathlib.Path, name, check)
from monsterforge.constructor import ConstructorService, ConstructorRegistry, SourceBundle
registry = ConstructorRegistry(asset_root=pathlib.Path('/tmp/empty-forge'))
service = ConstructorService(registry)
assert service.registry.supported_races == ('human',)
try:
    service.validate_settings({'schema_version': 99})
except ValueError:
    pass
else:
    raise AssertionError('Unsupported settings were admitted')
assert 'monsterforge.constructor._inventory' not in sys.modules
assert not any(name.startswith('machine_of_monsters') for name in sys.modules)
"""
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_core_does_not_import_the_legacy_compatibility_adapter(self):
        for path in (ROOT / "monsterforge/constructor").glob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn("workshop_constructor", node.module or "", str(path))
                    self.assertNotIn(
                        "workshop_constructor", [alias.name for alias in node.names], str(path)
                    )

    def fixture(self, root: Path):
        directory = root / "media/constructor/community/human/v1"
        directory.mkdir(parents=True)
        registry = ConstructorRegistry(asset_root=root)
        manifest = {
            "schema_version": 1,
            "rig_reference": "humanoid_v1",
            "coordinates": "metres; Y up; +Z forward; floor Y=0",
            "parts": {
                slot: {"model": f"{slot}.glb", "recipe": f"{slot}.recipe.json", "sha256": "a" * 64}
                for slot in registry.slots
            },
        }
        blob = json.dumps(manifest).encode()
        (directory / "parts.json").write_bytes(blob)
        for slot in registry.slots:
            (directory / f"{slot}.recipe.json").write_text('{"schema_version": 1}')
        (directory / "record.json").write_text('{"schema_version": 1, "approval": "fixture"}')
        source = SourceBundle(
            id="community-human-v1",
            label="Community human",
            race="human",
            gender="male",
            directory=directory,
            manifest_sha256=hashlib.sha256(blob).hexdigest(),
        )
        return registry, source, manifest

    def test_registry_extensions_preserve_the_original_inventory_and_source_evidence(self):
        with tempfile.TemporaryDirectory(prefix="forge-portable-registry-") as temporary:
            registry, source, _ = self.fixture(Path(temporary))
            snapshot = {path.name: path.read_bytes() for path in source.directory.iterdir()}
            service = ConstructorService(registry)
            extended = service.with_source(source)
            self.assertNotIn(source.id, registry.library_ids)
            self.assertIn(source.id, extended.registry.library_ids)
            self.assertEqual(extended.registry.source_folder(source.id), source.directory)
            self.assertEqual(
                {path.name: path.read_bytes() for path in source.directory.iterdir()}, snapshot
            )
            self.assertTrue(extended.registry.is_editable({"race": "human"}))
            self.assertFalse(extended.registry.is_editable({"race": "centaur"}))
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                extended.registry.with_source(source)

    def test_registry_rejects_unsupported_or_incompatible_source_data(self):
        with tempfile.TemporaryDirectory(prefix="forge-portable-admission-") as temporary:
            registry, source, manifest = self.fixture(Path(temporary))
            for invalid in (
                replace(source, contract="quadruped_v1"),
                replace(source, race="centaur"),
                replace(source, directory=Path("/tmp/outside")),
                replace(source, manifest_sha256="0" * 64),
            ):
                with self.subTest(source=invalid), self.assertRaises(ValueError):
                    registry.with_source(invalid)
            cases = [
                {**manifest, "schema_version": 99},
                {**manifest, "parts": {"head": manifest["parts"]["head"]}},
                {
                    **manifest,
                    "parts": {
                        **manifest["parts"],
                        "head": {**manifest["parts"]["head"], "recipe": "../../outside.json"},
                    },
                },
            ]
            for data in cases:
                blob = json.dumps(data).encode()
                (source.directory / "parts.json").write_bytes(blob)
                with self.subTest(manifest=data), self.assertRaises(ValueError):
                    registry.with_source(
                        replace(source, manifest_sha256=hashlib.sha256(blob).hexdigest())
                    )


class ConstructorHttpExtensionTests(unittest.TestCase):
    def setUp(self):
        from flask import Flask

        from monsterforge.creature_workshop import blueprint
        from monsterforge.paths import cache_directory
        from tools.creature_workshop.geometry import compile_recipe, export_glb, render_png

        self.temporary = tempfile.TemporaryDirectory(prefix="forge-http-extension-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.directory = self.root / "media/constructor/community/v1"
        self.directory.mkdir(parents=True)
        registry = ConstructorRegistry(asset_root=self.root)
        parts = {}
        for number, slot in enumerate(registry.slots):
            recipe = {
                "schema_version": 1,
                "id": "fixture." + slot,
                "palette": {"primary": "806040"},
                "commands": [
                    {
                        "id": slot,
                        "slot": slot,
                        "stage": 1,
                        "part": slot,
                        "purpose": "Approved numeric source fixture",
                        "material": "primary",
                        "op": "box",
                        "center": [number * 0.2, 0.5, 0],
                        "size": [0.1, 0.2, 0.1],
                    }
                ],
            }
            model = self.directory / (slot + ".glb")
            export_glb(model, compile_recipe(recipe), recipe)
            (self.directory / (slot + ".recipe.json")).write_text(json.dumps(recipe))
            parts[slot] = {
                "model": model.name,
                "recipe": slot + ".recipe.json",
                "sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
            }
        manifest = json.dumps(
            {
                "schema_version": 1,
                "rig_reference": "humanoid_v1",
                "coordinates": "metres; Y up; +Z forward; floor Y=0",
                "parts": parts,
            }
        ).encode()
        (self.directory / "parts.json").write_bytes(manifest)
        (self.directory / "record.json").write_text('{"schema_version": 1, "approval": "fixture"}')
        self.source = SourceBundle(
            id="community-human-v1",
            label="Community human",
            race="human",
            gender="male",
            directory=self.directory,
            manifest_sha256=hashlib.sha256(manifest).hexdigest(),
        )
        self.captured = []

        def renderer(path, arrays, **options):
            self.captured.append(arrays)
            return render_png(path, arrays, **options)

        self.service = ConstructorService(registry.with_source(self.source), renderer=renderer)
        self.cache = cache_directory("source-cards", root=self.root)
        self.addCleanup(shutil.rmtree, self.cache.parent, True)
        app = Flask(__name__)
        app.config.update(TESTING=True, CONSTRUCTOR_SERVICE=self.service)
        app.register_blueprint(blueprint)
        self.app, self.client = app, app.test_client()

    def test_http_catalog_actions_and_download_use_the_injected_service(self):
        projection = {
            "schema_version": 1,
            "races": [{"id": "human", "contract": "humanoid_v1"}],
            "outfits": [{"id": self.source.id, "label": self.source.label}],
        }
        with patch.object(self.service, "catalog", return_value=projection) as operation:
            response = self.client.get("/creature-workshop/constructor/catalog")
            self.assertEqual(response.json, projection)
            operation.assert_called_once_with()
        settings = {"schema_version": 5, "race": "human", "face": self.source.id}
        with patch.object(
            self.service, "preview", return_value={"source": self.source.id}
        ) as operation:
            response = self.client.post("/creature-workshop/constructor/preview", json=settings)
            self.assertEqual(response.json, {"source": self.source.id})
            operation.assert_called_once_with(settings)
        with patch.object(
            self.service, "saved_bundle", return_value=b"configured archive"
        ) as operation:
            with self.client.get(
                "/creature-workshop/constructor/revisions/" + "a" * 64 + "/download"
            ) as response:
                self.assertEqual(response.data, b"configured archive")
                self.assertEqual(response.mimetype, "application/zip")
            operation.assert_called_once_with("a" * 64)
        self.app.extensions["constructor_service"] = self.service
        self.app.config["CONSTRUCTOR_SERVICE"] = object()
        with patch.object(self.service, "catalog", return_value=projection):
            self.assertEqual(
                self.client.get("/creature-workshop/constructor/catalog").json, projection
            )

    def test_source_cards_use_approved_slot_geometry_and_only_write_disposable_cache(self):
        snapshot = {path.name: path.read_bytes() for path in self.directory.iterdir()}
        for category, count in (
            ("face", 36),
            ("hair", 36),
            ("arms", 72),
            ("legs", 72),
            ("outfit", 216),
        ):
            with self.subTest(category=category):
                response = self.client.get(
                    f"/creature-workshop/constructor/cards/v28/{category}/{self.source.id}.png"
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, "image/png")
                self.assertEqual(response.headers["Cache-Control"], "no-cache")
                self.assertEqual(len(self.captured[-1][0]), count)
                self.assertTrue(response.data.startswith(b"\x89PNG\r\n"))
                response.close()
        rendered = len(self.captured)
        with self.client.get(
            f"/creature-workshop/constructor/cards/face/{self.source.id}.png"
        ) as response:
            self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.captured), rendered)
        self.assertTrue(self.cache.is_relative_to("/tmp/monster-forge"))
        self.assertFalse(self.cache.is_relative_to(self.root))
        self.assertEqual(
            {path.name: path.read_bytes() for path in self.directory.iterdir()}, snapshot
        )

    def test_warm_thumbnail_does_not_hide_changed_source_bytes(self):
        url = f"/creature-workshop/constructor/cards/v28/face/{self.source.id}.png"
        with self.client.get(url) as response:
            self.assertEqual(response.status_code, 200)
        (self.directory / "head.glb").write_bytes(b"changed pinned model")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 409)
        self.assertIn("GLB", response.json["error"])

    def test_changed_source_evidence_is_rejected_and_corrupt_card_cache_is_rebuilt(self):
        url = f"/creature-workshop/constructor/cards/v28/face/{self.source.id}.png"
        with self.client.get(url) as response:
            self.assertEqual(response.status_code, 200)
        target = self.service.source_card("face", self.source.id)
        target.write_bytes(b"corrupt disposable thumbnail")
        with self.client.get(url) as response:
            self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.captured), 2)
        (self.directory / "record.json").write_text('{"schema_version": 1, "approval": "changed"}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 409)
        self.assertIn("evidence changed", response.json["error"])
