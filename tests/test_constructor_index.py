"""The recipe index admits supported data and preserves concurrent publications."""
from __future__ import annotations

import json
import multiprocessing
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from monsterforge import constructor_cache as cache


def _publish_cards(directory: str, number: int, barrier) -> None:
    root = Path(directory)
    with (patch.object(cache, 'ROOT', root),
          patch.object(cache, 'INDEX', root / 'config/index.json'),
          patch.object(cache, 'CACHE', root / 'cache')):
        barrier.wait(timeout=20)
        for suffix in ('front', 'face'):
            cache.register(root / f'media/constructor/{number}/{suffix}.png',
                           {'kind': 'card', 'category': suffix,
                            'identifier': str(number), 'gender': 'male'})


class ConstructorIndexTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='forge-index-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.index = self.root / 'config/index.json'
        self.index.parent.mkdir()
        for name, value in (('ROOT', self.root), ('INDEX', self.index),
                            ('CACHE', self.root / 'cache')):
            patcher = patch.object(cache, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(cache._read_index.cache_clear)
        self.path = self.root / 'media/constructor/test/model.glb'
        self.spec = {'kind': 'glb', 'sha256': 'a' * 64,
                     'recipes': [{'path': 'media/constructor/test/model.recipe.json',
                                  'sha256': 'b' * 64}]}

    def test_unknown_or_malformed_schema_is_rejected_without_rewriting_source(self):
        for data in ({'schema_version': 99, 'artifacts': {}},
                     {'schema_version': True, 'artifacts': {}},
                     {'schema_version': 1, 'artifacts': []},
                     {'schema_version': 1, 'artifacts': {'media/constructor/test.png':
                                                       {'kind': 'unknown'}}},
                     {'schema_version': 1, 'artifacts': {'../outside.glb': self.spec}}):
            with self.subTest(data=data):
                self.index.write_text(json.dumps(data))
                original = self.index.read_bytes()
                with self.assertRaises(ValueError):
                    cache.artifact_index()
                with self.assertRaises(ValueError):
                    cache.register(self.path, self.spec)
                self.assertEqual(self.index.read_bytes(), original)

    def test_pinned_geometry_and_provenance_require_a_new_revision(self):
        cache.register(self.path, self.spec)
        original = self.index.read_bytes()
        cache.register(self.path, self.spec)
        self.assertEqual(self.index.read_bytes(), original)
        for changed in ({**self.spec, 'sha256': 'c' * 64},
                        {**self.spec, 'recipes': []},
                        {'kind': 'card', 'category': 'outfit', 'identifier': 'test'}):
            with self.subTest(spec=changed), self.assertRaisesRegex(ValueError, 'Immutable'):
                cache.register(self.path, changed)
            self.assertEqual(self.index.read_bytes(), original)
        cache.register(self.path.with_name('model-v2.glb'), {**self.spec, 'sha256': 'c' * 64})
        self.assertEqual(len(cache.artifact_index()), 2)

    def test_atomic_replacement_refreshes_cached_index_even_with_same_mtime(self):
        cache.register(self.path, self.spec)
        self.assertEqual(len(cache.artifact_index()), 1)
        data = json.loads(self.index.read_text())
        data['artifacts']['media/constructor/test/card.png'] = {'kind': 'card'}
        replacement = self.index.with_name('replacement.json')
        replacement.write_text(json.dumps(data))
        os.utime(replacement, ns=(self.index.stat().st_atime_ns, self.index.stat().st_mtime_ns))
        replacement.replace(self.index)
        self.assertEqual(len(cache.artifact_index()), 2)

    @unittest.skipUnless('fork' in multiprocessing.get_all_start_methods(), 'POSIX publisher locks')
    def test_independent_publishers_preserve_all_entries_and_migration_metadata(self):
        initial = {f'media/constructor/base/{i}.png': {'kind': 'card'} for i in range(100)}
        migration = {'removed': {'historical.glb': 'preserved'}, 'revision': 1}
        self.index.write_text(json.dumps({'schema_version': 1, 'artifacts': initial,
                                         'migration': migration}))
        context = multiprocessing.get_context('fork')
        count = 8
        barrier = context.Barrier(count + 1)
        publishers = [context.Process(target=_publish_cards,
                                      args=(str(self.root), number, barrier))
                      for number in range(count)]
        try:
            for publisher in publishers:
                publisher.start()
            barrier.wait(timeout=20)
            for publisher in publishers:
                publisher.join(timeout=20)
                self.assertEqual(publisher.exitcode, 0)
        finally:
            for publisher in publishers:
                if publisher.is_alive():
                    publisher.terminate()
                    publisher.join(timeout=5)
        data = json.loads(self.index.read_text())
        self.assertEqual(len(data['artifacts']), len(initial) + count * 2)
        self.assertEqual(data['migration'], migration)
        self.assertTrue(all(data['artifacts'][key] == value for key, value in initial.items()))
        self.assertEqual({path.name for path in self.index.parent.iterdir()}, {'index.json'})
