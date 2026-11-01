"""Numerical export and corruption checks for the game character boundary."""
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path

from monster_forge_sdk import AssetStore
from monster_forge_sdk.characters import decode_skin, encode_skin, load_skeleton
from tools.assets.publish_character_runtime import (
    file_ref,
    publish_runtime,
    team_mask_glb,
)


class CharacterRuntimeTests(unittest.TestCase):
    def payload(self):
        return {'bind_profile': 'canonical', 'bone_palette': ['root'],
                'skin_indices': [[0, 0, 0, 0]], 'skin_weights': [[1, 0, 0, 0]]}

    def test_binary_roundtrip_keeps_metadata_and_weights(self):
        source = self.payload()
        source['hand_socket'] = [.1, .2, .3]
        self.assertEqual(decode_skin(encode_skin(source)), source)
        self.assertNotIn('skin_weights', decode_skin(encode_skin(source), metadata_only=True))

    def test_rejects_truncation_invalid_influences_and_nonfinite_values(self):
        blob = encode_skin(self.payload())
        for invalid in (blob[:-1], blob + b'\0', blob[:8]):
            with self.assertRaises(ValueError):
                decode_skin(invalid)
        for values in ([.5, 0, 0, 0], [float('nan'), 0, 0, 0], [-1, 2, 0, 0]):
            source = self.payload()
            source['skin_weights'] = [values]
            with self.assertRaises(ValueError):
                encode_skin(source)
        broken = bytearray(blob)
        struct.pack_into('<H', broken, len(broken) - 24, 5)
        with self.assertRaises(ValueError):
            decode_skin(bytes(broken))

    def model_blob(self):
        data = struct.pack('<9f', -.5, 0, 0, .5, 0, 0, 0, 1, 0)
        data += struct.pack('<9f', *([.2, .6, .3] * 3))
        doc = {'asset': {'version': '2.0'}, 'buffers': [{'byteLength': len(data)}],
               'bufferViews': [{'buffer': 0, 'byteOffset': 0, 'byteLength': 36},
                               {'buffer': 0, 'byteOffset': 36, 'byteLength': 36}],
               'accessors': [{'bufferView': i, 'componentType': 5126, 'count': 3, 'type': 'VEC3'} for i in range(2)],
               'meshes': [{'primitives': [{'attributes': {'POSITION': 0, 'COLOR_0': 1}}]}]}
        header = json.dumps(doc).encode()
        header += b' ' * (-len(header) % 4)
        return struct.pack('<4sII', b'glTF', 2, 28 + len(header) + len(data)) + struct.pack('<I4s', len(header), b'JSON') + header + struct.pack('<I4s', len(data), b'BIN\0') + data

    def test_mask_keeps_authored_geometry_and_colors(self):
        blob = self.model_blob()
        # Explicit colour from the authoring record; no inference from hue.
        source = bytearray(blob)
        length = struct.unpack_from('<I', source, 12)[0]
        struct.pack_into('<3f', source, 28 + length + 36, 51/255, 153/255, 77/255)
        painted = team_mask_glb(bytes(source), ('#33994d',))
        end = struct.unpack_from('<I', painted, 12)[0]
        self.assertEqual(painted[28 + end:28 + end + 72], source[28 + length:28 + length + 72])
        doc = json.loads(painted[20:20 + end])
        self.assertIn('_TEAM_MASK', doc['meshes'][0]['primitives'][0]['attributes'])
        self.assertEqual(struct.unpack_from('<3f', painted, 28 + end + 72), (1, 0, 0))

    def test_previous_published_weights_stay_resolvable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            media = root / 'media'
            source = media / 'constructor/library/fixture/parts'
            source.mkdir(parents=True)
            model = source / 'torso.glb'
            model.write_bytes(self.model_blob())
            weights = source / 'torso.weights.json'
            weights.write_text(json.dumps(self.payload()))
            entry = {'id': 'character.library.v1.fixture.parts.torso', 'kind': 'character',
                     'title': 'Fixture', 'revision': 1, 'files': {
                         'model': file_ref(media, model, 'model/gltf-binary'),
                         'weights': file_ref(media, weights, 'application/json')}}
            data = {'schema_version': 1, 'assets': [entry]}
            first = publish_runtime(root, data)['assets'][0]['files']['weights']
            updated = self.payload()
            updated['skin_weights'] = [[.5, .5, 0, 0]]
            newer = source / 'torso.next.weights.json'
            newer.write_text(json.dumps(updated))
            entry['files']['weights'] = file_ref(media, newer, 'application/json')
            latest = publish_runtime(root, data)
            self.assertNotEqual(first['sha256'], latest['assets'][0]['files']['weights']['sha256'])
            (media / 'catalog.json').write_text(json.dumps(latest))
            store = AssetStore(root)
            old = store.resolve_uri('/media/' + first['path'])
            self.assertEqual(hashlib.sha256(old.read_bytes()).hexdigest(), first['sha256'])

    def test_bhm_owns_distinct_compatible_bind_profiles(self):
        original = load_skeleton()
        workshop = load_skeleton('workshop_knees_v1')
        self.assertEqual([b['id'] for b in original['bones']], [b['id'] for b in workshop['bones']])
        self.assertNotEqual(original, workshop)
        original['bones'].clear()
        self.assertTrue(load_skeleton()['bones'])


if __name__ == '__main__':
    unittest.main()
