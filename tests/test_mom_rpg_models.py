"""Existing RPG presets and race templates remain available for editing."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from monster_forge_sdk import AssetStore
from monster_forge_sdk.characters import read_character_model
from monsterforge import create_app
from monsterforge.constructor_marsh_forest import RACES
from monsterforge.mom_rpg_presets import presets
from monsterforge.workshop_constructor import catalog, validate_settings
from tests import test_character_runtime
from tools.assets.bake_character_models import publish
from tools.assets.publish_character_runtime import file_ref, publish_runtime


class RpgModelTests(unittest.TestCase):
    def test_catalog_preserves_existing_races_and_preset_settings(self):
        app = create_app()
        app.config['TESTING'] = True
        client = app.test_client()
        response = client.get('/creature-workshop/constructor/catalog')
        self.assertEqual(response.status_code, 200)
        active = response.get_json()
        self.assertEqual(active['supported_contracts'], ['humanoid_v1'])
        self.assertEqual({race['id'] for race in active['races']},
                         {race['id'] for race in catalog(include_legacy=True)['races']})
        self.assertTrue(all(race['editable'] for race in active['races']))
        self.assertTrue(all(race['contract'] == 'humanoid_v1'
                            for race in catalog(include_legacy=False)['races']))
        editable_races = {race['id'] for race in active['races']}
        available = {p.get('id'): p for p in active['presets']}
        historical = {p['id']: p for p in catalog(include_legacy=True)['presets']}
        for preset in presets():
            expected = validate_settings(preset['settings'])
            self.assertEqual(historical[preset['id']]['settings'], expected)
            if preset['settings']['race'] in editable_races:
                self.assertEqual(available[preset['id']]['settings'], expected)
            else:
                self.assertNotIn(preset['id'], available)

    def test_new_assembly_archives_removed_slots_as_well_as_replaced_slots(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            media = root / 'media'
            media.mkdir()
            model = media / 'source.glb'
            # Publishing without team colours keeps arbitrary source bytes intact.
            model.write_bytes(test_character_runtime.CharacterRuntimeTests().model_blob())
            rows = [{'id': 'character.mom_rpg.' + version + '.unit.parts.' + slot,
                     'kind': 'character', 'title': 'Unit', 'tags': [],
                     'files': {'model': file_ref(media, model, 'model/gltf-binary')}}
                    for version, slot in [('v1', 'tail'), ('v1', 'head'), ('v2', 'head')]]
            result = publish_runtime(root, {'assets': rows})
            identities = {e['id'] for e in result['assets']}
            self.assertIn('character.maps.mom_rpg.unit.parts.head', identities)
            self.assertIn('character.maps.mom_rpg.unit.parts.head.archived', identities)
            self.assertIn('character.maps.mom_rpg.unit.parts.tail.archived', identities)
            self.assertNotIn('character.maps.mom_rpg.unit.parts.tail', identities)

    def test_rebuild_does_not_resurrect_removed_canonical_limbs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            media = root / 'media'
            media.mkdir()
            prefix = 'character.maps.mom_rpg.fixture.parts.'
            ref = {'path': 'fixture.glb', 'sha256': 'a' * 64,
                   'size_bytes': 1, 'media_type': 'model/gltf-binary'}
            def entry(key):
                return {'id': prefix + key, 'kind': 'character', 'title': key,
                        'revision': 1, 'files': {'model': ref}}
            (media / 'catalog.json').write_text(json.dumps({'schema_version': 1,
                                                          'assets': [entry('tail')]}))
            current = {'schema_version': 1, 'assets': [entry('head'), entry('tail.archived')]}
            with patch('tools.assets.bake_character_models.AssetStore') as store:
                store.return_value.list.return_value = []
                publish(root, current)
            result = json.loads((media / 'catalog.json').read_text())
            self.assertNotIn(prefix + 'tail', {e['id'] for e in result['assets']})
            self.assertEqual(result['aliases'][prefix + 'tail'], prefix + 'tail.archived')

    def test_published_bodies_use_the_selected_constructor_sources(self):
        root = Path(__file__).resolve().parents[1]
        store = AssetStore(root)
        for preset in presets():
            category, name = preset['id'].split('/')
            identity = 'character.maps.mom_rpg.' + category + '.' + name
            model = read_character_model(store.read(identity + '.body'))
            self.assertEqual(model['metadata']['skeleton_id'],
                             RACES.get(preset['settings']['race'], {}).get('rig', 'humanoid_v1'))
            instruction = json.loads(store.read(identity + '.body', 'assembly'))
            self.assertEqual(instruction['schema_version'], 2)
            self.assertEqual(instruction['constructor_settings'], preset['settings'])
            self.assertEqual(instruction['model']['sha256'], store.get(identity + '.body').files['model'].sha256)
            for slot, original in model['metadata']['source_parts'].items():
                component = instruction['parts'][slot]
                if 'revision_id' in component:
                    self.assertRegex(component['revision_id'], r'^[0-9a-f]{64}$')
                    self.assertEqual(component['source_model_sha256'], original['model'])
                else:
                    self.assertEqual(component['model'], original['model'])
                    self.assertEqual(component['weights'], original['weights'])
                    recipe = component['recipe']
                    self.assertEqual(hashlib.sha256((root / 'media' / recipe['path']).read_bytes()).hexdigest(), recipe['sha256'])
            if name == 'viking':
                # Current compact publications pin the derived part hash;
                # their reproducible per-part files belong in /tmp.
                from monsterforge.workshop_constructor import build
                with tempfile.TemporaryDirectory(prefix='forge-viking-source-') as temporary:
                    stage = Path(temporary)
                    manifest = build(preset['settings'], stage)
                    self.assertEqual(manifest['parts']['head']['model_sha256'],
                                     instruction['parts']['head']['source_model_sha256'])
                    head = json.loads((stage/'parts/head/recipe.json').read_text())
                parts = [c['part'] for c in head['commands']]
                self.assertTrue(any('helmet_horn' in p for p in parts))
                self.assertTrue(any('braid' in p for p in parts))


if __name__ == '__main__':
    unittest.main()
