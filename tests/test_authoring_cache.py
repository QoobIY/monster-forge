"""Draft builds use isolated /tmp workspaces while source releases stay intact."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from monsterforge.paths import cache_directory
from tools.assets import build_mom_rpg_architecture as architecture


class AuthoringCacheTests(unittest.TestCase):
    def test_namespaces_are_stable_and_separate_independent_checkouts(self):
        first = cache_directory('preview', root=Path('/tmp/source-one'))
        self.assertEqual(first, cache_directory('preview', root=Path('/tmp/source-one/.')))
        self.assertTrue(first.is_relative_to('/tmp/monster-forge'))
        self.assertNotEqual(first, cache_directory('preview', root=Path('/tmp/source-two')))
        self.assertNotEqual(first, cache_directory('draft', root=Path('/tmp/source-one')))
        for namespace in ('/outside', '../outside', 'draft/../../outside'):
            with self.subTest(namespace=namespace), self.assertRaises(ValueError):
                cache_directory(namespace)

    def test_architecture_draft_keeps_catalogs_outside_the_source_checkout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            media = root / 'media'
            media.mkdir()
            original = b'{"schema_version": 1, "assets": []}\n'
            for name in ('catalog.json', 'imported_catalog.json'):
                (media / name).write_bytes(original)
            sources, pairs = root / 'sources.json', root / 'pairs.json'
            sources.write_text('[]')
            draft = cache_directory('architecture-review/sdk', root=root)
            self.addCleanup(shutil.rmtree, draft.parent, True)
            with patch.object(architecture, 'ROOT', root):
                architecture.build(sources, pairs, draft=True)
            self.assertFalse((root / 'artifacts').exists())
            self.assertTrue((draft / 'media/catalog.json').is_file())
            self.assertEqual(json.loads(pairs.read_text()), [])
            for name in ('catalog.json', 'imported_catalog.json'):
                self.assertEqual((media / name).read_bytes(), original)
                self.assertEqual(json.loads((draft / 'media' / name).read_text())['assets'], [])
