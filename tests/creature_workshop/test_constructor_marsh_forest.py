"""New constructor species cross UI, immutable sources and game export boundaries."""
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import numpy as np

from monster_forge_sdk.characters import body_rig, read_character_model
from monsterforge import create_app
from monsterforge import workshop_constructor as constructor
from monsterforge.constructor_marsh_forest import DESIGNS, RACES


def settings(race):
    value = constructor.default_settings()
    donor = f'native-{race}-01'
    value.update(race=race, face=donor, outfit=donor, arms=donor, legs=donor)
    return value


class MarshForestConstructorTests(unittest.TestCase):
    def test_catalog_cards_preview_and_export_are_available(self):
        client = create_app().test_client()
        catalog = client.get('/creature-workshop/constructor/catalog').get_json()
        races = {r['id']: r for r in catalog['races']}
        historical = {r['id']: r for r in constructor.catalog(include_legacy=True)['races']}
        for race, spec in RACES.items():
            self.assertIn(race, races)
            self.assertEqual(historical[race]['contract'], spec['rig'])
            self.assertTrue(historical[race]['editable'])
            self.assertEqual(len(historical[race]['body_variants']['male']), 3)
            for category in ('face', 'hair', 'outfit', 'arms', 'legs'):
                card = client.get(f'/creature-workshop/constructor/cards/v28/{category}/native-{race}-01.png')
                self.assertEqual(card.status_code, 200)
                self.assertEqual(card.mimetype, 'image/png')
                card.close()
            preview = client.post('/creature-workshop/constructor/preview', json=settings(race))
            self.assertEqual(preview.status_code, 200)
            self.assertEqual(preview.get_json()['contract'], spec['rig'])
            sources = {}
            original_build = constructor.build

            def capture_build(payload, target, *, _build=original_build, _sources=sources, **kwargs):
                manifest = _build(payload, target, **kwargs)
                for slot, info in manifest['parts'].items():
                    _sources[slot] = {
                        'skin': json.loads((target / info['weights']).read_text()),
                        'positions': constructor._glb_arrays((target / info['model']).read_bytes())[0],
                        'model_sha256': info['model_sha256'],
                    }
                return manifest

            with patch.object(constructor, 'build', side_effect=capture_build):
                response = client.post('/creature-workshop/constructor/export', json=settings(race))
                self.assertEqual(response.status_code, 200)
                payload = response.data
            with zipfile.ZipFile(io.BytesIO(payload)) as bundle:
                self.assertEqual(set(bundle.namelist()), {'assembly.json', 'model.glb'})
                assembly = json.loads(bundle.read('assembly.json'))
                self.assertEqual(assembly['schema_version'], 2)
                self.assertEqual(assembly['skeleton_id'], spec['rig'])
                self.assertEqual(set(assembly['parts']), {s['id'] for s in body_rig(spec['rig'])['slots']})
                model = bundle.read('model.glb')
                self.assertEqual(assembly['model']['sha256'], hashlib.sha256(model).hexdigest())
                self.assertEqual(assembly['model']['size_bytes'], len(model))
                baked = read_character_model(model)
                palette = baked['metadata']['bone_palette']
                attributes = baked['attributes']
                offset = 0
                for slot in body_rig(spec['rig'])['slots']:
                    name = slot['id']
                    source = sources[name]
                    skin = source['skin']
                    count = len(skin['skin_weights'])
                    section = slice(offset, offset + count)
                    np.testing.assert_array_equal(attributes['POSITION'][section], source['positions'])
                    np.testing.assert_allclose(attributes['WEIGHTS_0'][section], skin['skin_weights'], atol=1.e-7)
                    remapped = np.array([palette.index(bone) for bone in skin['bone_palette']])[skin['skin_indices']]
                    np.testing.assert_array_equal(attributes['JOINTS_0'][section], remapped)
                    positive = np.asarray(attributes['WEIGHTS_0'][section]) > 0
                    used = {palette[index] for index in remapped[positive]}
                    self.assertLessEqual(used, set(slot['bones']))
                    self.assertEqual(assembly['parts'][name]['source_model_sha256'], source['model_sha256'])
                    offset += count
                self.assertEqual(offset, baked['metadata']['vertex_count'])
                np.testing.assert_allclose(np.sum(attributes['WEIGHTS_0'], axis=1), 1, atol=1.e-6)

    def test_each_anatomy_has_grounded_limbs_and_explicit_permitted_weights(self):
        for design in DESIGNS:
            value = settings(design['race'])
            value.update(face=design['id'], outfit=design['id'], arms=design['id'], legs=design['id'])
            with self.subTest(design=design['id']), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                manifest = constructor.build(value, root, weights=True)
                for slot, info in manifest['parts'].items():
                    arrays = constructor._glb_arrays((root / info['model']).read_bytes())
                    self.assertTrue(all(np.isfinite(a).all() for a in arrays))
                    self.assertGreater(len(arrays[0]), 0)
                    skin = json.loads((root / info['weights']).read_text())
                    self.assertEqual(len(skin['skin_weights']), len(arrays[0]))
                    np.testing.assert_allclose(np.sum(skin['skin_weights'], axis=1), 1)
                    used = {skin['bone_palette'][row[0]] for row in skin['skin_indices']}
                    self.assertLessEqual(used, set(skin['allowed_bones']))
                    if slot.endswith('_leg') or design['race'] == 'slime' and slot == 'torso':
                        self.assertAlmostEqual(float(arrays[0][:, 1].min()), 0, places=5)

    def test_selected_donors_are_independent_and_recolouring_survives_export(self):
        for race in RACES:
            value = settings(race)
            value.update(arms=f'native-{race}-02', legs=f'native-{race}-03')
            value['colors']['skin'] = '#216a98'
            with self.subTest(race=race), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                manifest = constructor.build(value, root, weights=True)
                for slot in manifest['parts']:
                    recipe = json.loads((root / 'parts' / slot / 'recipe.json').read_text())
                    donor = recipe['constructor']['sources'][0]['donor']
                    field = ('face' if slot == 'head' else 'arms' if slot.endswith('_arm') or slot.startswith('front') or slot == 'left_wisp'
                             else 'legs' if slot.endswith('_leg') or slot.startswith('hind') or slot == 'right_wisp' else 'outfit')
                    self.assertEqual(donor, value[field])
                    self.assertEqual(recipe['palette']['skin'], '216a98')

    def test_invalid_or_cross_species_choices_are_rejected(self):
        for mutation in ({'arms': 'native-frog-01'}, {'face': 'library-human-01'},
                         {'back': 'back-royal'}, {'eye_size': True}, {'form': 'heavy'},
                         {'placement': [0, 0, 0]}):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                constructor.validate_settings({**settings('satyr'), **mutation})
        bad = settings('slime')
        bad['colors']['skin'] = '#oops'
        with self.assertRaises(ValueError):
            constructor.validate_settings(bad)

    def test_save_is_immutable_and_supports_all_three_contracts(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(constructor, 'STORE', Path(temporary)):
            for race in RACES:
                first = constructor.save(settings(race))
                self.assertEqual(first, constructor.save(settings(race)))
                self.assertTrue(constructor.saved_bundle(first['id']))


if __name__ == '__main__':
    unittest.main()
