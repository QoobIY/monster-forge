"""Retirement removes files, preserves shared artwork and stays idempotent."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.assets.clean_retired_icons import clean
from tools.assets.icon_policy import canonical_entry, retired_icon


class IconCleanupTests(unittest.TestCase):
    def test_shared_files_survive_and_dry_run_is_read_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            media = root/'media'
            orphan = media/'icons/singles/old/revisions/0001/unused.png'
            orphan.parent.mkdir(parents=True)
            orphan.write_bytes(b'orphan')
            (media/'shared.png').write_bytes(b'canonical')
            old = media/'icons/singles/old/icon.png'
            old.write_bytes(b'old')
            entries = [
                {'id': 'old-stats', 'kind': 'icon', 'group': 'Интерфейс · stats',
                 'files': {'image': {'path': 'shared.png'}}},
                {'id': 'old-ability', 'kind': 'icon', 'group': 'Способности и эффекты',
                 'files': {'image': {'path': 'icons/singles/old/icon.png'}}},
                {'id': 'canonical', 'kind': 'icon', 'group': 'Old Nova subdivision',
                 'tags': ['nova'], 'files': {'image': {'path': 'shared.png'}}},
            ]
            original = json.dumps({'schema_version': 1, 'assets': entries})
            for name in ('catalog.json', 'imported_catalog.json'):
                (media/name).write_text(original)
            plan = clean(root)
            self.assertEqual((media/'catalog.json').read_text(), original)
            self.assertTrue(old.exists())
            self.assertIn('shared.png', plan['shared_files_preserved'])
            clean(root, apply=True)
            self.assertFalse(old.exists())
            self.assertFalse(orphan.exists())
            self.assertEqual((media/'shared.png').read_bytes(), b'canonical')
            kept = json.loads((media/'catalog.json').read_text())['assets']
            self.assertEqual([a['id'] for a in kept], ['canonical'])
            self.assertEqual(kept[0]['group'], 'Nova')
            self.assertEqual(clean(root, apply=True)['deleted_files'], [])

    def test_sources_retire_with_their_category_and_nova_art_is_preserved(self):
        self.assertTrue(retired_icon({'kind': 'icon', 'group': 'Интерфейс · stats/sources'}))
        self.assertFalse(retired_icon({'kind': 'icon', 'group': 'Игровые иконки · painted'}))
        icon = {'kind': 'icon', 'group': 'Separate', 'files': {
            'image': {'path': 'icons/maps/angel_arena_nova/assets/icons/painted/item.png'}}}
        self.assertEqual(canonical_entry(icon)['group'], 'Nova')
        self.assertEqual(icon['group'], 'Separate')

    def test_published_canonical_icons_resolve_through_sdk(self):
        from monster_forge_sdk import AssetStore
        store = AssetStore()
        nova = [a for a in store.list('icon') if a.group == 'Nova']
        self.assertTrue(nova)
        self.assertFalse(any(retired_icon(a) for a in store.catalog()['assets']))
        self.assertFalse(any(a.group.startswith('Иконки · Nova') for a in store.list('icon')))
        for asset in nova:
            store.read(asset.id, 'image')


if __name__ == '__main__':
    unittest.main()
