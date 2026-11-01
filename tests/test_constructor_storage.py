"""Disposable products must rebuild without restoring files inside the project."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from monster_forge_sdk import AssetStore
from monsterforge import constructor_cache as cache
from monsterforge.paths import ROOT


class ConstructorStorageTests(unittest.TestCase):
    def test_empty_or_corrupt_cache_rebuilds_original_glb_outside_project(self):
        logical, spec = next((ROOT / key, value) for key, value in cache.artifact_index().items()
                             if value['kind'] == 'glb' and not (ROOT / key).exists())
        with (tempfile.TemporaryDirectory(dir='/tmp', prefix='forge-test-cache-') as directory,
              patch.object(cache, 'CACHE', Path(directory))):
            target = cache.resolve(logical)
            self.assertTrue(target.is_relative_to(directory))
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), spec['sha256'])
            target.write_bytes(b'corrupted cache')
            rebuilt = cache.resolve(logical)
            self.assertEqual(hashlib.sha256(rebuilt.read_bytes()).hexdigest(), spec['sha256'])
            self.assertFalse(logical.exists())

    def test_changed_recipe_cannot_silently_change_a_pinned_artifact(self):
        logical, original = next((ROOT / key, value) for key, value in cache.artifact_index().items()
                                 if value['kind'] == 'glb' and not (ROOT / key).exists())
        spec = json.loads(json.dumps(original))
        spec['recipes'][0]['sha256'] = '0' * 64
        with (tempfile.TemporaryDirectory(dir='/tmp', prefix='forge-test-cache-') as directory,
              patch.object(cache, 'CACHE', Path(directory)),
              patch.object(cache, 'artifact_index', return_value={logical.relative_to(ROOT).as_posix(): spec}),
              self.assertRaisesRegex(ValueError, 'recipe changed')):
            cache.resolve(logical)

    def test_runtime_catalog_contains_finished_characters_and_existing_files(self):
        catalog = json.loads((ROOT / 'media/catalog.json').read_text())
        self.assertEqual(catalog['constructor_storage_version'], 2)
        store = AssetStore(ROOT)
        identities = {asset.id for asset in store.list()}
        self.assertTrue(set(catalog['aliases'].values()) <= identities)
        for asset in store.list():
            if asset.kind == 'character':
                self.assertTrue(asset.id.endswith('.body'), asset.id)
                if 'assembly' in asset.files:
                    assembly = json.loads(store.read(asset.id, 'assembly'))
                    self.assertEqual(assembly['schema_version'], 2)
                    self.assertEqual(assembly['model']['sha256'], asset.files['model'].sha256)
                else:
                    # Material studies preserve a published character's geometry;
                    # their pinned surface record describes that derivative.
                    self.assertIn('surface', asset.files)
                    self.assertTrue({'experimental', 'materials'} <= set(asset.tags))
                    surface = json.loads(store.read(asset.id, 'surface'))
                    self.assertEqual(surface['schema_version'], 1)
                    self.assertEqual(surface['model_sha256'], asset.files['model'].sha256)
                    source = store.get(surface['source'])
                    self.assertIn('assembly', source.files)
                    source_models = {ref.sha256 for role, ref in source.files.items()
                                     if role == 'model' or role.startswith('revision_')}
                    self.assertIn(surface['source_sha256'], source_models)
                    source_assemblies = [json.loads(store.read(source.id, role))
                                         for role in source.files if role == 'assembly' or role.startswith('assembly_')]
                    self.assertTrue(any(record['model']['sha256'] == surface['source_sha256']
                                        for record in source_assemblies))
                self.assertNotIn('weights', asset.files)
                self.assertNotIn('preview', asset.files)
            for role in asset.files:
                self.assertTrue(store.path(asset.id, role).is_file(), (asset.id, role))


if __name__ == '__main__':
    unittest.main()
