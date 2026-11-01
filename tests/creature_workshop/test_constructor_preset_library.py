"""The editor and publishers must consume the same complete file instructions."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from monsterforge import constructor_presets as library
from monsterforge import create_app
from monsterforge.constructor_atlas import presets as attribute_presets
from monsterforge.mom_rpg_presets import presets as rpg_presets
from monsterforge.workshop_constructor import presets, reference_presets


class PresetLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='forge-preset-library-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)/'presets'
        shutil.copytree(library.DIRECTORY, self.root)
        self.scope = patch.object(library, 'DIRECTORY', self.root)
        self.scope.start()
        self.addCleanup(self.scope.stop)

    def read(self, path):
        return json.loads((self.root/path).read_text())

    def write(self, path, value):
        (self.root/path).write_text(json.dumps(value, ensure_ascii=False))

    def test_all_public_entry_points_read_the_library_and_return_independent_settings(self):
        self.assertEqual(presets(), library.load_presets('library', 'mom_rpg'))
        self.assertEqual(rpg_presets(), library.load_presets('mom_rpg'))
        self.assertEqual(reference_presets(), library.load_presets('reference'))
        self.assertEqual(attribute_presets(), library.load_presets('attribute'))
        mage = next(p for p in rpg_presets() if p['id']=='classes/mage')
        mage['settings']['colors']['cloth'] = '#abcdef'
        self.assertNotEqual(next(p for p in rpg_presets() if p['id']=='classes/mage')['settings'], mage['settings'])

    def test_file_edit_reaches_both_browser_catalog_and_publisher_without_python_changes(self):
        from tools.assets import build_mom_rpg_models
        filename = 'mom_rpg/classes/mage.json'
        record = self.read(filename)
        record['settings']['reference_parts']['hair'] = 12
        record['settings']['colors']['cloth'] = '#192b47'
        self.write(filename, record)
        before = {p.relative_to(self.root):p.read_bytes() for p in self.root.rglob('*.json')}
        response = create_app().test_client().get('/creature-workshop/constructor/catalog')
        self.assertEqual(response.status_code, 200)
        mage = next(p for p in response.get_json()['presets'] if p['id']=='classes/mage')
        self.assertEqual(mage['settings'], record['settings'])
        with patch('tools.assets.publish_assembly.publish') as publish:
            build_mom_rpg_models.build()
        call = next(c for c in publish.call_args_list if c.args[0]=='character.maps.mom_rpg.classes.mage')
        self.assertEqual(call.args[2], record['settings'])
        self.assertEqual(before, {p.relative_to(self.root):p.read_bytes() for p in self.root.rglob('*.json')})

    def test_other_skin_publisher_also_reads_the_shared_files(self):
        from tools.assets import build_mom_skins
        record = self.read('mom_skins/knight.json')
        record['settings']['colors']['cloth'] = '#254967'
        self.write('mom_skins/knight.json', record)
        with patch.object(build_mom_skins, 'publish_humanoid') as humanoid, patch.object(build_mom_skins, 'publish_quadruped'), patch.object(build_mom_skins, 'build_catalog'):
            build_mom_skins.main()
        call = next(c for c in humanoid.call_args_list if c.args[0]=='knight')
        self.assertEqual(call.args[2], record['settings'])

    def test_existing_settings_migrations_are_explicit_and_do_not_rewrite_source(self):
        name = 'mom_rpg/classes/mage.json'
        record = self.read(name)
        record['settings']['schema_version'] = 4
        record['settings'].pop('reference_parts')
        self.write(name, record)
        before = (self.root/name).read_bytes()
        mage = next(p for p in rpg_presets() if p['id']=='classes/mage')
        self.assertEqual(mage['settings']['schema_version'], 5)
        self.assertIn('reference_parts', mage['settings'])
        self.assertEqual((self.root/name).read_bytes(), before)

    def test_bad_schema_settings_missing_files_and_unindexed_files_fail_loudly(self):
        filename = 'mom_rpg/classes/mage.json'
        original = self.read(filename)
        bad = [dict(original, schema_version=99), dict(original, schema_version=True),
               dict(original, unknown='not part of the schema')]
        invalid = copy.deepcopy(original)
        invalid['settings']['face'] = 'missing-head'
        bad.append(invalid)
        for record in bad:
            with self.subTest(record=record.get('schema_version')):
                self.write(filename, record)
                with self.assertRaisesRegex(ValueError, filename):
                    rpg_presets()
        self.write(filename, original)
        (self.root/filename).unlink()
        with self.assertRaisesRegex(ValueError, 'mage.json'):
            rpg_presets()
        self.write(filename, original)
        self.write('extra.json', original)
        with self.assertRaisesRegex(ValueError, 'differ from index'):
            rpg_presets()

    def test_index_rejects_duplicate_paths_and_escaping_the_library(self):
        original = self.read('index.json')
        for entry in ({'group':'mom_rpg','path':'../outside.json'}, original['presets'][0]):
            index = copy.deepcopy(original)
            index['presets'].append(entry)
            self.write('index.json', index)
            with self.assertRaisesRegex(ValueError, 'preset path'):
                rpg_presets()


if __name__ == '__main__':
    unittest.main()
