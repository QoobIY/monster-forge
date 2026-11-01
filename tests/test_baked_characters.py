"""Whole-body export preserves deformation inputs and the public glTF bind."""
import hashlib
import io
import json
import struct
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

import numpy as np
from PIL import Image

from monster_forge_sdk import AssetStore
from monster_forge_sdk.characters import body_rig, read_character_model
from tools.assets.bake_character_models import (
    bake,
    bone_matrices,
    publish,
    unpack,
)
from tools.assets.publish_character_runtime import file_ref


def triangle_part(offset):
    """Known source streams exercise remapping, texture UVs, and triangle order."""
    streams = {
        'POSITION': np.array([[offset, 0, 0], [offset + .5, 0, 0], [offset, 1, 0]], '<f4'),
        'NORMAL': np.array([[0, 0, 1]] * 3, '<f4'),
        'COLOR_0': np.array([[.2, .6, .3, 1]] * 3, '<f4'),
        'TEXCOORD_0': np.array([[-.2, .3], [1.4, .5], [.7, 1.2]], '<f4'),
        '_TEAM_MASK': np.array([[0], [.5], [1]], '<f4'),
    }
    doc = {'asset': {'version': '2.0'}, 'buffers': [{}], 'bufferViews': [], 'accessors': []}
    binary = bytearray()
    attributes = {}
    for name, values in streams.items():
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': values.nbytes})
        doc['accessors'].append({'bufferView': len(doc['bufferViews']) - 1,
                                 'componentType': 5126, 'count': len(values),
                                 'type': {1: 'SCALAR', 2: 'VEC2', 3: 'VEC3', 4: 'VEC4'}[values.shape[1]]})
        attributes[name] = len(doc['accessors']) - 1
        binary.extend(values.tobytes())
    indices = np.array([[2], [0], [1]], '<u4')
    doc['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': indices.nbytes})
    doc['accessors'].append({'bufferView': len(doc['bufferViews']) - 1,
                             'componentType': 5125, 'count': 3, 'type': 'SCALAR'})
    binary.extend(indices.tobytes())
    image = io.BytesIO()
    Image.new('RGBA', (2, 2), '#abcdef').save(image, format='PNG')
    doc['images'] = [{'bufferView': len(doc['bufferViews']), 'mimeType': 'image/png'}]
    doc['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(image.getvalue())})
    binary.extend(image.getvalue())
    doc['textures'] = [{'source': 0, 'sampler': 0}]
    doc['samplers'] = [{'wrapS': 10497, 'wrapT': 10497, 'magFilter': 9729, 'minFilter': 9729}]
    doc['materials'] = [{'pbrMetallicRoughness': {'baseColorTexture': {'index': 0}}}]
    doc['meshes'] = [{'primitives': [{'attributes': attributes,
                                     'indices': len(doc['accessors']) - 1, 'material': 0}]}]
    binary.extend(b'\0' * (-len(binary) % 4))
    doc['buffers'][0]['byteLength'] = len(binary)
    header = json.dumps(doc).encode()
    header += b' ' * (-len(header) % 4)
    blob = struct.pack('<4sII', b'glTF', 2, 28 + len(header) + len(binary))
    blob += struct.pack('<I4s', len(header), b'JSON') + header
    blob += struct.pack('<I4s', len(binary), b'BIN\0') + binary
    return blob, streams


@contextmanager
def source_fixture(root):
    """Compiler inputs belong in a temporary store, outside the runtime catalog."""
    with tempfile.TemporaryDirectory(prefix='forge-bake-') as temporary:
        media = Path(temporary)
        entries, sources = [], {}
        for number, slot in enumerate(body_rig('humanoid_v1', root=root)['slots']):
            name = slot['id']
            model, streams = triangle_part(number * .3)
            palette = list(reversed(slot['bones']))
            skin = {'skeleton_id': 'humanoid_v1', 'bind_profile': 'canonical', 'slot': name,
                    'model_sha256': hashlib.sha256(model).hexdigest(), 'bone_palette': palette,
                    'skin_indices': [[0, 1, 0, 0]] * 3, 'skin_weights': [[.75, .25, 0, 0]] * 3}
            model_path, weights_path = media / (name + '.glb'), media / (name + '.weights.json')
            model_path.write_bytes(model)
            weights_path.write_text(json.dumps(skin))
            entries.append({'id': 'character.fixture.parts.' + name, 'kind': 'character',
                            'title': name, 'revision': 1, 'files': {
                                'model': file_ref(media, model_path, 'model/gltf-binary'),
                                'weights': file_ref(media, weights_path, 'application/json')}})
            sources[name] = streams, skin
        store = AssetStore(root, catalog=json.dumps({'schema_version': 1, 'assets': entries}).encode())
        store.media_root = media
        yield store, sources


class BakedCharacterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = AssetStore(Path(__file__).resolve().parents[1])

    def check_model(self, identity):
        blob = self.store.read(identity + '.body')
        result = read_character_model(blob)
        doc, binary = unpack(blob)
        metadata = result['metadata']
        instruction = json.loads(self.store.read(identity + '.body', 'assembly'))
        self.assertEqual(instruction['schema_version'], 2)
        self.assertEqual(instruction['kind'], 'constructor_assembly')
        self.assertEqual(instruction['model']['sha256'], hashlib.sha256(blob).hexdigest())
        self.assertEqual(instruction['model']['size_bytes'], len(blob))
        self.assertEqual(instruction['skeleton_id'], metadata['skeleton_id'])
        self.assertEqual(instruction['bind_profile'], metadata['bind_profile'])
        required = {slot['id'] for slot in body_rig(metadata['skeleton_id'])['slots']}
        self.assertEqual(set(metadata['source_parts']), required)
        self.assertEqual(set(instruction['parts']), required)
        for slot, source in metadata['source_parts'].items():
            part = instruction['parts'][slot]
            self.assertEqual(source['model'], part.get('model', part.get('source_model_sha256')))
            for role in ('model', 'weights'):
                self.assertRegex(source[role], r'^[0-9a-f]{64}$')
                if role in part:
                    self.assertEqual(source[role], part[role])
        matrices = bone_matrices(metadata['skeleton'])
        inverses = [np.array(value).reshape(4, 4).T for value in result['inverse_bind_matrices']]
        skin_matrices = np.array([world @ inverse for world, inverse in zip(matrices, inverses, strict=True)])
        np.testing.assert_allclose(skin_matrices, np.broadcast_to(np.eye(4), skin_matrices.shape), atol=1.e-5)
        attributes = result['attributes']
        positions = np.asarray(attributes['POSITION'])
        weights = np.asarray(attributes['WEIGHTS_0'])
        joints = np.asarray(attributes['JOINTS_0'])
        np.testing.assert_allclose(weights.sum(axis=1), 1, atol=1.e-6)
        self.assertTrue(np.all((weights >= 0) & (weights <= 1)))
        self.assertTrue(np.all((joints >= 0) & (joints < len(matrices))))
        homogeneous = np.column_stack((positions, np.ones(len(positions))))
        deformed = np.zeros_like(homogeneous)
        for column in range(4):
            deformed += np.einsum('vab,vb->va', skin_matrices[joints[:, column]], homogeneous) * weights[:, column, None]
        np.testing.assert_allclose(deformed, homogeneous, atol=2.e-5)
        self.assertEqual(len(positions), metadata['vertex_count'])
        self.assertTrue({value[0] for value in attributes['_MOM_LBS']} <= {0, 1})
        self.assertNotIn('animations', doc)
        self.assertEqual(len(doc['meshes'][0]['primitives']), 1)
        self.assertEqual(len(result['triangles']) % 3, 0)
        return result, doc, binary

    def test_nova_geometry_weights_and_mixed_skinning_are_preserved(self):
        result, _, _ = self.check_model('character.maps.angel_arena_nova.furlord')
        self.assertEqual(set(result['metadata']['socket_points']), {'left_arm', 'right_arm'})

    def test_imported_character_keeps_texture_and_virtual_hand_anchors(self):
        result, doc, _ = self.check_model('character.maps.act_one.garhold')
        self.assertTrue(doc['images'])
        self.assertEqual(set(result['metadata']['socket_points']), {'left_arm', 'right_arm'})

    def test_existing_quadruped_keeps_repeat_uv_and_skeleton(self):
        result, doc, _ = self.check_model('character.shared.mom_skins.tiger_rider')
        self.assertEqual(result['metadata']['skeleton_id'], 'quadruped_v1')
        self.assertGreater(np.array(result['attributes']['TEXCOORD_0']).max(), 1)
        self.assertEqual(doc['samplers'][0]['wrapS'], 10497)
        self.assertEqual(doc['samplers'][0]['minFilter'], 9729)

    def test_publication_is_deterministic_and_arbitrary_part_selection_is_checked(self):
        with source_fixture(self.store.root) as (store, sources):
            blob = bake(store, 'character.fixture')
            self.assertEqual(bake(store, 'character.fixture'), blob)
            selection = {slot: 'character.fixture.parts.' + slot for slot in sources}
            self.assertEqual(bake(store, 'character.fixture', selection), blob)
            result = read_character_model(blob)
            names = result['metadata']['bone_palette']
            for number, (slot, (streams, skin)) in enumerate(sources.items()):
                section = slice(number * 3, number * 3 + 3)
                for key, values in streams.items():
                    np.testing.assert_array_equal(result['attributes'][key][section], values)
                remapped = np.array([names.index(name) for name in skin['bone_palette']])[skin['skin_indices']]
                np.testing.assert_array_equal(result['attributes']['JOINTS_0'][section], remapped)
                np.testing.assert_array_equal(result['attributes']['WEIGHTS_0'][section], skin['skin_weights'])
                np.testing.assert_array_equal(result['attributes']['_MOM_LBS'][section],
                                              np.full((3, 1), slot.endswith('_arm')))
                self.assertEqual(result['triangles'][section], [number * 3 + 2, number * 3, number * 3 + 1])
            selection['head'] = selection['torso']
            with self.assertRaisesRegex(ValueError, 'duplicate character slots'):
                bake(store, 'character.fixture', selection)

    def test_rebuild_preserves_published_assets_and_aliases(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            media = root/'media'
            media.mkdir()
            entry = {
                'id': 'legacy.asset', 'kind': 'character', 'title': 'Legacy',
                'revision': 1, 'files': {}}
            original = {'schema_version': 1, 'assets': [entry],
                        'aliases': {'old.asset': 'legacy.asset'}}
            (media/'catalog.json').write_text(json.dumps(original))
            publish(root, {'schema_version': 1, 'assets': [], 'aliases': {}})
            result = json.loads((media/'catalog.json').read_text())
            self.assertEqual(result['assets'], [entry])
            self.assertEqual(result['aliases'], original['aliases'])

    def test_canonical_selection_excludes_readable_archived_source(self):
        with source_fixture(self.store.root) as (store, _):
            original = bake(store, 'character.fixture')
            catalog = store.catalog()
            old = dict(next(entry for entry in catalog['assets'] if entry['id'].endswith('.torso')))
            old['id'] += '.archived_fixture.archived'
            catalog['assets'].append(old)
            staged = AssetStore(self.store.root, catalog=json.dumps(catalog).encode())
            staged.media_root = store.media_root
            self.assertEqual(bake(staged, 'character.fixture'), original)
            self.assertTrue(staged.read(old['id']))

    def test_malformed_skin_and_truncated_glb_are_rejected(self):
        blob = self.store.read('character.maps.angel_arena_nova.furlord.body')
        with self.assertRaises(ValueError):
            read_character_model(blob[:-1])
        doc, binary = unpack(blob)
        key = doc['meshes'][0]['primitives'][0]['attributes']['WEIGHTS_0']
        spec = doc['accessors'][key]
        offset = doc['bufferViews'][spec['bufferView']]['byteOffset']
        broken = bytearray(binary)
        broken[offset:offset+4] = b'\0\0\xc0\x7f'
        size = int.from_bytes(blob[12:16], 'little')
        with self.assertRaises(ValueError):
            read_character_model(blob[:28+size]+broken)


if __name__ == '__main__':
    unittest.main()
