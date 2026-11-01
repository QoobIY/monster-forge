"""Removed scenery cannot erase shared live files or return on a catalog rebuild."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.assets.asset_policy import REPLACEMENTS, canonical_entry, retired_model
from tools.assets.clean_retired_models import clean


class ModelCleanupTests(unittest.TestCase):
    def test_cleanup_preserves_shared_files_and_is_idempotent(self):
        old, current = next(iter(REPLACEMENTS.items()))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            media = root / 'media'
            media.mkdir()
            (media / 'shared.glb').write_bytes(b'live')
            (media / 'old.png').write_bytes(b'old')
            rows = [
                {'id': old, 'kind': 'decoration', 'files': {
                    'model': {'path': 'shared.glb'}, 'preview': {'path': 'old.png'}}},
                {'id': current, 'kind': 'decoration', 'files': {'model': {'path': 'shared.glb'}}},
            ]
            original = json.dumps({'schema_version': 1, 'assets': rows})
            for name in ('catalog.json', 'imported_catalog.json'):
                (media / name).write_text(original)
            plan = clean(root)
            self.assertEqual((media / 'catalog.json').read_text(), original)
            self.assertEqual(plan['deleted_files'], ['old.png'])
            clean(root, apply=True)
            self.assertEqual((media / 'shared.glb').read_bytes(), b'live')
            self.assertFalse((media / 'old.png').exists())
            self.assertEqual(clean(root, apply=True)['deleted_files'], [])

    def test_old_equipment_is_retired_and_shared_library_is_kept(self):
        for scope, kinds in (("angel_arena_nova", ("hammer", "blade", "staff", "bow", "axe", "relic")),
                             ("hearthvale", ("sword", "axe", "staff", "bow", "greatsword", "shield"))):
            for kind in kinds:
                self.assertTrue(retired_model({"id": f"decoration.{scope}.equipment.{kind}"}))
        self.assertFalse(retired_model({"id": "equipment.shared.skeletal.sword"}))

    def test_groups_follow_content_and_equipment_is_shared(self):
        for identity, group in [('decoration.hearthvale.props.lamp', 'MOM RPG'),
                                ('decoration.angel_arena_nova.architecture.shop', 'Nova'),
                                ('character.maps.angel_arena_nova.god.body', 'Nova'),
                                ('character.maps.mom_rpg.witcher.body', 'MOM RPG'),
                                ('decoration.angel_arena_nova.equipment.bow', 'Снаряжение'),
                                ('equipment.shared.swamp.sword', 'Снаряжение')]:
            row = {'id': identity, 'kind': 'decoration', 'group': 'old'}
            normalized = canonical_entry(row)
            self.assertEqual(normalized['group'], group)
            self.assertEqual(row['group'], 'old')
            self.assertEqual(canonical_entry(normalized), normalized)
        self.assertTrue(retired_model({'id': next(iter(REPLACEMENTS))}))
        self.assertFalse(retired_model({'id': 'decoration.woodland.oak'}))
