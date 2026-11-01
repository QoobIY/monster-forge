"""The same running web app must serve the newly published catalog and model."""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import trimesh

from monster_forge_sdk import AssetStore
from monsterforge import create_app
from monsterforge.asset_geometry import geometry
from monsterforge.asset_library import store


class LibraryRefreshTests(unittest.TestCase):
    def test_catalog_geometry_and_files_follow_publication_without_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            media = root/'media'
            media.mkdir()
            def publish(size, group):
                payload = trimesh.creation.box(extents=(size, 1, 1)).export(file_type='glb')
                checksum = hashlib.sha256(payload).hexdigest()
                name = checksum+'.glb'
                (media/name).write_bytes(payload)
                catalog = {'schema_version': 1, 'assets': [{
                    'id': 'decoration.test', 'kind': 'decoration', 'title': 'Test',
                    'revision': 1, 'group': group, 'files': {'model': {
                        'path': name, 'sha256': checksum, 'size_bytes': len(payload),
                        'media_type': 'model/gltf-binary'}}}]}
                (media/'catalog.json').write_text(json.dumps(catalog))
                return checksum
            with patch.dict(os.environ, {'MONSTER_FORGE_ASSET_ROOT': str(root)}):
                first_hash = publish(1, 'Old group')
                app = create_app()
                client = app.test_client()
                self.assertEqual(client.get('/api/assets/v1/catalog?kind=decoration').json['assets'][0]['group'], 'Old group')
                before = client.get('/api/assets/v1/geometry?id=decoration.test')
                self.assertEqual(before.status_code, 200)
                self.assertEqual(before.json['source_sha256'], first_hash)
                with app.app_context():
                    original = store()
                    self.assertIs(store(), original)
                second_hash = publish(2, 'MOM RPG')
                response = client.get('/api/assets/v1/catalog?kind=decoration')
                self.assertEqual(response.json['assets'][0]['group'], 'MOM RPG')
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                model = client.get('/api/assets/v1/geometry?id=decoration.test')
                self.assertEqual(model.status_code, 200)
                self.assertEqual(model.json['source_sha256'], second_hash)
                self.assertEqual(client.get('/health').json['asset_release'], AssetStore(root).release_id)
                with app.app_context():
                    self.assertIsNot(store(), original)
                    with patch('monsterforge.asset_library.AssetStore', side_effect=AssertionError('Unchanged catalog decoded again')):
                        store()
                path = response.json['assets'][0]['files']['model']['path']
                binary = client.get('/media/'+path)
                self.assertEqual(hashlib.sha256(binary.data).hexdigest(), second_hash)
                binary.close()
        geometry.cache_clear()
