"""Thumbnail publication preserves geometry and updates both SDK manifests."""
import base64
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from monster_forge_sdk import AssetStore
from monsterforge.paths import cache_directory
from tools.assets.build_previews import build_previews, missing_previews, publish_previews

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC')


class SceneryPreviewTests(unittest.TestCase):
    def fixture(self, root):
        media = root/'media'
        media.mkdir()
        model = b'untouched model bytes'
        (media/'model.glb').write_bytes(model)
        row = {'id': 'decoration.fixture', 'kind': 'decoration', 'title': 'Fixture',
               'revision': 7, 'group': 'MOM RPG', 'metadata': {'preserved': True},
               'files': {'model': {'path': 'model.glb', 'sha256': hashlib.sha256(model).hexdigest(),
                                   'size_bytes': len(model), 'media_type': 'model/gltf-binary'}}}
        payload = json.dumps({'schema_version': 1, 'assets': [row]})
        for name in ('catalog.json', 'imported_catalog.json'):
            (media/name).write_text(payload)
        return row

    def test_publish_both_catalogs_and_skip_unchanged_previews(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = self.fixture(root)
            store = AssetStore(root)
            image = root/'render.png'
            image.write_bytes(PNG)
            self.assertEqual(len(missing_previews(store)), 1)
            self.assertEqual(publish_previews(root, {original['id']: image}, store.release_id), 1)
            for name in ('catalog.json', 'imported_catalog.json'):
                row = json.loads((root/'media'/name).read_text())['assets'][0]
                self.assertEqual(row['files']['model'], original['files']['model'])
                self.assertEqual(row['metadata'], original['metadata'])
                self.assertEqual(row['revision'], 7)
                self.assertIn('preview', row['files'])
            updated = AssetStore(root)
            self.assertEqual(updated.read(original['id'], 'preview'), PNG)
            self.assertEqual(build_previews(root), 0)
            updated.path(original['id'], 'preview').write_bytes(b'corrupt')
            self.assertEqual(len(missing_previews(AssetStore(root))), 1)

    def test_publication_rejects_a_concurrent_catalog_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            row = self.fixture(root)
            release = AssetStore(root).release_id
            manifest = root/'media/catalog.json'
            manifest.write_text(manifest.read_text()+'\n')
            original = manifest.read_bytes()
            with self.assertRaisesRegex(ValueError, 'Catalog changed'):
                publish_previews(root, {row['id']: root/'absent.png'}, release)
            self.assertEqual(manifest.read_bytes(), original)

    def test_render_work_stays_in_tmp_and_publication_preserves_the_source_model(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = self.fixture(root)
            renderer = root / 'test-renderer'
            renderer.touch()
            work = cache_directory('library-previews', root=root)
            self.addCleanup(shutil.rmtree, work, True)

            def render(arguments, *, check):
                self.assertTrue(check)
                manifest, output = Path(arguments[-2]), Path(arguments[-1])
                self.assertTrue(output.is_relative_to(work))
                self.assertFalse(output.is_relative_to(root))
                for row in json.loads(manifest.read_text()):
                    (output / (row['key'] + '-after.png')).write_bytes(PNG)

            with patch('tools.assets.build_previews.subprocess.run', side_effect=render):
                self.assertEqual(build_previews(root, renderer=renderer), 1)
            self.assertFalse((root / 'artifacts').exists())
            published = AssetStore(root)
            self.assertEqual(published.file(original['id'], 'model').sha256,
                             original['files']['model']['sha256'])
            self.assertEqual(published.read(original['id'], 'preview'), PNG)
