"""Persistent SDK cache contract: pinned releases, warm reads and repair."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from monster_forge_sdk import AssetStore, ContentCache


class AssetCacheTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.source = self.root / 'release'
        (self.source / 'media').mkdir(parents=True)
        self.cache = self.root / 'cache'
        self.publish(b'original')

    def tearDown(self):
        self.directory.cleanup()

    def publish(self, payload):
        (self.source / 'media/icon.png').write_bytes(payload)
        self.hash = hashlib.sha256(payload).hexdigest()
        row = {'id': 'test', 'kind': 'icon', 'title': 'Test', 'revision': 1,
               'files': {'image': {'path': 'icon.png', 'sha256': self.hash,
                         'size_bytes': len(payload), 'media_type': 'image/png'}}}
        (self.source / 'media/catalog.json').write_text(json.dumps({'schema_version': 1, 'assets': [row]}))

    def store(self):
        return AssetStore(self.source, cache_dir=self.cache)

    def test_warm_restart_never_opens_source_or_rehashes_unchanged_blob(self):
        first = self.store()
        path = first.path('test')
        self.assertTrue(path.is_relative_to(self.cache))
        second = self.store()
        with patch.object(second, '_path', side_effect=AssertionError('source read')), \
             patch('monster_forge_sdk.cache.hashlib.sha256', side_effect=AssertionError('rehash')):
            self.assertEqual(second.path('test'), path)
            self.assertEqual(second.resolve_uri('/media/icon.png'), path)

    def test_changed_hash_gets_new_file_without_overwriting_pinned_version(self):
        old = self.store().path('test')
        self.publish(b'changed!')
        new = self.store().path('test')
        self.assertNotEqual(old, new)
        self.assertEqual(old.read_bytes(), b'original')
        self.assertEqual(new.read_bytes(), b'changed!')

    def test_same_size_cache_corruption_is_repaired(self):
        first = self.store()
        path = first.path('test')
        path.write_bytes(b'modified')
        self.assertEqual(self.store().path('test').read_bytes(), b'original')

    def test_failed_admission_and_missing_receipt_do_not_trust_bad_bytes(self):
        cache = ContentCache(self.cache)
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            cache.put(self.hash, 8, '.png', [b'modified'])
        self.assertFalse(list(self.cache.rglob('.asset-*')))
        self.assertIsNone(cache.get(self.hash, 8, '.png'))
        path = self.store().path('test')
        path.with_name(path.name + '.verified.json').unlink()
        path.write_bytes(b'modified')
        self.assertEqual(self.store().path('test').read_bytes(), b'original')

    def test_cache_symlinks_cannot_escape(self):
        outside = self.root / 'outside.png'
        outside.write_bytes(b'original')
        path = self.cache / self.hash[:2] / (self.hash + '.png')
        path.parent.mkdir(parents=True)
        path.symlink_to(outside)
        with self.assertRaises(ValueError):
            self.store().path('test')
        self.assertEqual(outside.read_bytes(), b'original')
