"""Published shared equipment has complete, portable geometry and grip contracts."""
import json
import struct
import unittest

import numpy as np
import trimesh
from scipy.spatial.transform import Rotation

from monster_forge_sdk import AssetStore
from tools.assets.build_shared_weapons import THEMES, TYPES, attachment


class SharedWeaponsTests(unittest.TestCase):
    def test_all_themes_and_types_publish_real_models_and_sockets(self):
        store = AssetStore()
        hashes = set()
        for theme in THEMES:
            for kind in TYPES:
                with self.subTest(theme=theme, kind=kind):
                    asset = store.get(f'equipment.shared.{theme}.{kind}')
                    self.assertEqual(asset.group, 'Снаряжение')
                    payload = store.read(asset.id, 'model')
                    length = struct.unpack_from('<I', payload, 12)[0]
                    gltf = json.loads(payload[20:20+length])
                    self.assertFalse(any('uri' in image for image in gltf.get('images', [])))
                    contract = json.loads(store.read(asset.id, 'attachment'))
                    nodes = {node['name']: node for node in gltf['nodes']}
                    for name, socket in contract['sockets'].items():
                        self.assertEqual(nodes[name]['translation'], socket['position'])
                    self.assertEqual(contract['grip']['position'], [0, 0, 0])
                    if kind in ('greatsword', 'scythe', 'staff'):
                        self.assertIn('grip_secondary', nodes)
                    if kind == 'bow':
                        self.assertIn('string_nock', nodes)
                        self.assertIn('projectile_socket', nodes)
                    mesh = trimesh.load(store.path(asset.id, 'model'), force='mesh', process=False)
                    self.assertTrue(np.isfinite(mesh.vertices).all())
                    self.assertTrue(mesh.is_winding_consistent)
                    self.assertTrue(np.all(mesh.area_faces > 1e-12))
                    self.assertLessEqual(len(mesh.faces), 6000)
                    self.assertLess(np.linalg.norm(mesh.vertices, axis=1).min(), .2)
                    hashes.add(asset.files['model'].sha256)
        self.assertEqual(len(hashes), 90)

    def test_melee_blade_frame_and_staff_pose_contract_are_distinct(self):
        store = AssetStore()
        for theme in THEMES:
            for kind in TYPES:
                identity = f'equipment.shared.{theme}.{kind}'
                frame = json.loads(store.read(identity, 'attachment'))
                expected = attachment(kind, {name: data['position'] for name, data in frame['sockets'].items()})
                self.assertEqual(frame, expected, identity)
                if kind in {'sword', 'greatsword', 'mace', 'axe', 'scythe'}:
                    basis = Rotation.from_quat(frame['grip']['rotation']).inv()
                    np.testing.assert_allclose(basis.apply([0, 1, 0]), [0, 0, 1], atol=1e-8)
                    np.testing.assert_allclose(basis.apply([1, 0, 0]), [0, -1 if kind == "axe" else 1, 0], atol=1e-8)
                    np.testing.assert_allclose(basis.apply([0, 0, 1]), [-1 if kind == "axe" else 1, 0, 0], atol=1e-8)
                else:
                    self.assertEqual(frame['grip']['rotation'], [0, 0, 0, 1])
