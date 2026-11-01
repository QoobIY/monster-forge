"""A public source checkout can run against its own tiny example release."""

import hashlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

from monster_forge_sdk import AssetStore
from monsterforge import create_app
from monsterforge.asset_geometry import geometry
from monsterforge.demo import create_demo
from monsterforge.runtime import bind_bones, load_bind_skeleton


class ApplicationModeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='forge-library-')
        self.addCleanup(self.temporary.cleanup)
        self.addCleanup(geometry.cache_clear)
        self.root = create_demo(Path(self.temporary.name))
        self.app = create_app({'ASSET_ROOT': self.root, 'MODE': 'library', 'TESTING': True})
        self.client = self.app.test_client()

    def test_examples_rebuild_identically_and_verify_through_the_real_sdk(self):
        assets = AssetStore(self.root)
        original = (self.root / 'media/catalog.json').read_bytes()
        create_demo(self.root)
        self.assertEqual((self.root / 'media/catalog.json').read_bytes(), original)
        self.assertEqual({asset.kind for asset in assets.list()}, {'decoration', 'icon', 'terrain'})
        for asset in assets.list():
            ref = assets.file(asset.id)
            self.assertEqual(hashlib.sha256(assets.read(asset.id)).hexdigest(), ref.sha256)
        image = Image.open(io.BytesIO(assets.read('terrain.example.ground')))
        self.assertEqual(image.size, (32, 32))
        self.assertEqual(assets.icon_style()['schema_version'], 1)

    def test_library_and_geometry_work_without_constructor_endpoints(self):
        self.assertEqual(self.client.get('/').location, '/decorations/')
        for path in ('/decorations/', '/icons/', '/terrain/', '/sdk/', '/characters/'):
            with self.subTest(path=path), self.client.get(path) as response:
                self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/capabilities').json['mode'], 'library')
        self.assertEqual(self.client.get('/health').json['mode'], 'library')
        response = self.client.get('/api/assets/v1/geometry?id=decoration.example.block')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['triangles'], 12)
        self.assertEqual(response.json['bounds_metres'], [[-.5, 0, -.5], [.5, 1, .5]])
        normals = np.asarray(response.json['parts']['0']['geometry']['normals']).reshape(-1, 3)
        np.testing.assert_allclose(np.linalg.norm(normals, axis=1), 1)
        for path in ('catalog', 'preview', 'save', 'export'):
            request = self.client.get if path == 'catalog' else self.client.post
            response = request('/creature-workshop/constructor/' + path)
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json['code'], 'constructor_unavailable')
        for path in ('style.txt', 'profile.json', 'mom-style-reference.jpg', 'prompts-mom.json'):
            with self.client.get('/styles/icons/' + path) as response:
                self.assertEqual(response.status_code, 200)

    def test_two_apps_do_not_read_each_others_asset_root_or_cached_geometry(self):
        response = self.client.get('/api/assets/v1/geometry?id=decoration.example.block')
        self.assertEqual(response.status_code, 200)
        with tempfile.TemporaryDirectory() as directory:
            other = create_demo(Path(directory))
            store = AssetStore(other)
            store.path('decoration.example.block').unlink()
            app = create_app({'ASSET_ROOT': other, 'MODE': 'library', 'TESTING': True})
            self.assertEqual(app.test_client().get('/api/assets/v1/geometry?id=decoration.example.block').status_code, 404)
        self.assertEqual(self.client.get('/api/assets/v1/geometry?id=decoration.example.block').status_code, 200)

    def test_auto_mode_reports_missing_sources_and_required_authoring_fails_early(self):
        with patch('monsterforge.web.source_availability', return_value=(False, 'Install constructor sources')):
            auto = create_app({'ASSET_ROOT': self.root, 'MODE': 'auto'})
            self.assertEqual(auto.test_client().get('/api/capabilities').json['constructor']['reason'], 'Install constructor sources')
            with self.assertRaisesRegex(RuntimeError, 'Install constructor sources'):
                create_app({'ASSET_ROOT': self.root, 'MODE': 'authoring'})
        with self.assertRaisesRegex(ValueError, 'MODE'):
            create_app({'ASSET_ROOT': self.root, 'MODE': 'invented'})

    def test_library_import_never_attempts_to_load_the_game_or_constructor(self):
        script = '''
import importlib.abc, sys
from pathlib import Path
class RejectGame(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('machine_of_monsters', 'monsterforge.constructor')):
            raise AssertionError('Library attempted to import ' + fullname)
sys.meta_path.insert(0, RejectGame())
from monsterforge import create_app
app = create_app({'MODE': 'library', 'ASSET_ROOT': Path(sys.argv[1])})
assert app.test_client().get('/health').status_code == 200
assert app.test_client().get('/api/assets/v1/catalog').json['assets']
'''
        result = subprocess.run([sys.executable, '-c', script, str(self.root)],
                                env=dict(os.environ), capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_static_bind_uses_the_bundled_contract(self):
        for profile in ('canonical', 'workshop_knees_v1'):
            skeleton = load_bind_skeleton(profile)
            bones = bind_bones(profile)
            self.assertEqual([bone['id'] for bone in bones],
                             [bone['id'] for bone in skeleton['bones']])
            self.assertTrue(np.isfinite([bone['position'] for bone in bones]).all())

    def test_missing_source_pack_does_not_advertise_working_authoring(self):
        with patch('monsterforge.web.source_availability', return_value=(False, 'Source library is not installed')):
            app = create_app({'ASSET_ROOT': self.root, 'MODE': 'auto'})
            capability = app.test_client().get('/api/capabilities').json['constructor']
            self.assertFalse(capability['available'])
            self.assertIn('Source library', capability['reason'])

    def test_constructor_launches_without_a_published_asset_catalog(self):
        with tempfile.TemporaryDirectory(prefix='forge-no-release-') as directory:
            root = Path(directory)
            with (patch('monsterforge.web.ROOT', root),
                  patch('monsterforge.web.source_availability', return_value=(True, None))):
                app = create_app({'ASSET_ROOT': None, 'MODE': 'auto'})
            client = app.test_client()
            self.assertEqual(client.get('/').location, '/characters/')
            self.assertEqual(client.get('/health').json['mode'], 'authoring')
            self.assertEqual(client.get('/api/assets/v1/catalog').json['assets'], [])
            self.assertFalse((root / 'media/catalog.json').exists())
            # A release published later is picked up by the same app instance.
            create_demo(root)
            self.assertEqual(len(client.get('/api/assets/v1/catalog').json['assets']), 3)


if __name__ == '__main__':
    unittest.main()
