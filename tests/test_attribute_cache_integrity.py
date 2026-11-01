"""A cold source-only checkout verifies rebuilt attribute GLBs by their pinned hashes."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from monsterforge import constructor_atlas as atlas
from monsterforge import constructor_cache as cache
from monsterforge.paths import ROOT


class AttributeCacheIntegrityTests(unittest.TestCase):
    def test_attribute_integrity_rebuilds_missing_models_and_rejects_changed_expected_hashes(self):
        original = atlas.part_folder("male_clothes", 1)
        integrity = json.loads((original / "integrity.json").read_text())
        specs = cache.artifact_index()
        with tempfile.TemporaryDirectory(prefix="forge-attribute-cache-") as temporary:
            root = Path(temporary)
            folder = root / original.relative_to(ROOT)
            folder.mkdir(parents=True)
            for name in ("recipe.json", "integrity.json"):
                shutil.copyfile(original / name, folder / name)
            selected = {}
            for name in integrity["files"]:
                if not name.endswith(".glb"):
                    continue
                logical = (original / name).relative_to(ROOT).as_posix()
                selected[logical] = specs[logical]
                for reference in specs[logical]["recipes"]:
                    target = root / reference["path"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / reference["path"], target)
            source = root / "media/constructor/attribute_references/v1"
            reference_image = source / "male_clothes/front.png"
            reference_image.parent.mkdir(parents=True)
            shutil.copyfile(atlas.SOURCE / "male_clothes/front.png", reference_image)
            index = root / "config/constructor_artifacts_v1.json"
            index.parent.mkdir(parents=True)
            index.write_text(json.dumps({"schema_version": 1, "artifacts": selected}))
            products = root / "disposable-cache"
            atlas.load.cache_clear()
            self.addCleanup(atlas.load.cache_clear)
            with (
                patch.object(atlas, "part_folder", return_value=folder),
                patch.object(atlas, "SOURCE", source),
                patch.object(cache, "ROOT", root),
                patch.object(cache, "INDEX", index),
                patch.object(cache, "CACHE", products),
            ):
                recipe = atlas.load("male_clothes", 1)
                self.assertEqual(recipe["attribute_reference"]["source_files"], integrity["files"])
                self.assertTrue(selected)
                for logical in selected:
                    model = root / logical
                    self.assertFalse(model.exists())
                    rebuilt = cache.resolve(model)
                    self.assertTrue(rebuilt.is_relative_to(products))
                    self.assertEqual(
                        hashlib.sha256(rebuilt.read_bytes()).hexdigest(),
                        integrity["files"][model.name],
                    )
                first = next(name for name in integrity["files"] if name.endswith(".glb"))
                integrity["files"][first] = "0" * 64
                (folder / "integrity.json").write_text(json.dumps(integrity))
                atlas.load.cache_clear()
                with self.assertRaisesRegex(ValueError, "Immutable attribute mesh changed"):
                    atlas.load("male_clothes", 1)
