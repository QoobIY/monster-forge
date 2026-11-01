"""Audio is a first-class SDK file, including HTTP filtering and integrity."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from monster_forge_sdk import AssetIntegrityError, AssetStore
from monsterforge import create_app


class AudioSdkTests(unittest.TestCase):
    def test_audio_default_role_and_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            media = root / 'media'
            media.mkdir()
            payload = b'RIFF-original-audio'
            sound = media / 'score.wav'
            sound.write_bytes(payload)
            reference = {'path': 'score.wav', 'size_bytes': len(payload),
                         'sha256': hashlib.sha256(payload).hexdigest(), 'media_type': 'audio/wav'}
            (media / 'catalog.json').write_text(json.dumps({'schema_version': 1, 'assets': [
                {'id': 'audio.test', 'kind': 'audio', 'title': 'Score', 'revision': 1,
                 'files': {'audio': reference}}]}))
            store = AssetStore(root)
            self.assertEqual(store.path('audio.test'), sound)
            self.assertEqual(store.read('audio.test'), payload)
            self.assertEqual(store.resolve_uri('/media/score.wav'), sound)
            sound.write_bytes(b'RIFF-modified-audio')
            with self.assertRaises(AssetIntegrityError):
                store.read('audio.test')

    def test_http_audio_catalog_uses_the_same_release(self):
        with create_app().test_client() as client:
            response = client.get('/api/assets/v1/catalog?kind=audio')
            self.assertEqual(response.status_code, 200)
            rows = response.get_json()['assets']
            self.assertTrue(rows)
            self.assertTrue(all(row['kind'] == 'audio' for row in rows))
            self.assertTrue(all('audio' in row['files'] for row in rows))
