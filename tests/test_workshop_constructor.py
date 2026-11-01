"""Constructor trust boundaries, immutable derivatives and numerical part contracts."""
import hashlib
import io
import json
import tempfile
import shutil
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import numpy as np

from monsterforge import create_app
from monsterforge import workshop_constructor as editor


class WorkshopConstructorTests(unittest.TestCase):
    def test_settings_reject_incompatible_versions_and_unowned_placement(self):
        base = editor.default_settings()
        mutations = [{'schema_version': 99}, {'schema_version': True}, {'race': '../../.env'}, {'face': 'axemaster'},
                     {'eye_size': float('nan')}, {'eye_size': True}, {'placement': [1, 2, 3]},
                     {'colors': {'skin': '#ffffff'}}, {'back': '../unknown'}]
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                editor.validate_settings({**base, **mutation})

    def test_reference_path_migration_preserves_bytes_and_rejects_escape(self):
        from monsterforge.constructor_atlas import load
        from monsterforge.paths import resolve_asset_path
        ref = load('male_faces', 1)['attribute_reference']
        path = resolve_asset_path(ref['image'])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), ref['image_sha256'])
        for invalid in ('../../.env', 'media/constructor/../../.env',
                        'media/experiments/constructor_../../.env',
                        'local_archive/angel_arena/reference.png'):
            with self.subTest(path=invalid), self.assertRaises(ValueError):
                resolve_asset_path(invalid)

    def test_export_contains_instruction_and_one_skinned_model(self):
        from monster_forge_sdk.characters import read_character_model
        with zipfile.ZipFile(io.BytesIO(editor.export_bundle(editor.default_settings()))) as archive:
            self.assertEqual(set(archive.namelist()), {'assembly.json', 'model.glb'})
            instruction = json.loads(archive.read('assembly.json'))
            self.assertEqual(instruction['schema_version'], 2)
            self.assertEqual(set(instruction['parts']), set(editor.SLOTS))
            self.assertEqual(instruction['constructor_settings'], editor.default_settings())
            blob = archive.read('model.glb')
            self.assertEqual(hashlib.sha256(blob).hexdigest(), instruction['model']['sha256'])
            model = read_character_model(blob)
            self.assertEqual(model['metadata']['skeleton_id'], 'humanoid_v1')
            weights = np.asarray(model['attributes']['WEIGHTS_0'])
            self.assertTrue(np.all(weights >= 0))
            np.testing.assert_allclose(weights.sum(1), 1, atol=1e-6)
            self.assertAlmostEqual(min(v[1] for v in model['attributes']['POSITION']), 0, places=5)

    def test_source_recipe_cannot_drift_from_immutable_model(self):
        donor = 'library-human-01'
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/donor
            shutil.copytree(editor._folder(donor), source)
            from monsterforge.constructor_cache import resolve
            (source/'parts/head.glb').write_bytes(resolve(editor._folder(donor)/'parts/head.glb').read_bytes())
            path = source/'parts/head.recipe.json'
            recipe = json.loads(path.read_text())
            recipe['palette'][recipe['commands'][0]['material']] = 'ff0000'
            path.write_text(json.dumps(recipe))
            with patch.object(editor, '_folder', return_value=source), self.assertRaisesRegex(ValueError, 'рецепт не соответствует'):
                editor._load(donor, 'head')

    def test_all_races_customization_preserves_floor_finite_normals_and_modular_slots(self):
        for race in editor.catalog(include_legacy=True)['races']:
            with self.subTest(race=race['id']), tempfile.TemporaryDirectory() as tmp:
                settings = editor.default_settings()
                variants = race['body_variants']['male']
                donor = variants[0]['id'] if variants else race['library_outfits'][0]
                settings.update(race=race['id'], face=donor, outfit=donor, arms=donor,
                                legs=donor, hair='bald')
                if race.get('anatomy_only'):
                    settings['hair'] = 'original'
                if race['anatomies']['male']:
                    settings['face'] = race['anatomies']['male'][0]['id']
                if race['id'] != 'randomium':
                    settings['colors'].update(eyes='#67905f', cloth='#455a7b')
                manifest = editor.build(settings, Path(tmp))
                from monster_forge_sdk.characters import body_rig
                expected = ([s['id'] for s in body_rig(race['contract'])['slots']] if race.get('anatomy_only') else
                            editor.SPECIES_CONTRACTS[race['contract']] if race['id'] in editor.SPECIES else editor.SLOTS)
                self.assertEqual(set(manifest['parts']), set(expected))
                for slot, part in manifest['parts'].items():
                    positions, normals, colors = editor._glb_arrays((Path(tmp)/part['model']).read_bytes())
                    self.assertTrue(np.isfinite(positions).all())
                    np.testing.assert_allclose(np.linalg.norm(normals, axis=1), 1, atol=1e-5)
                    self.assertTrue(np.all((colors >= 0) & (colors <= 1)))
                    if slot.endswith('_leg') and not race['flying_body']:
                        self.assertAlmostEqual(float(positions[:, 1].min()), 0, places=5)

    def test_body_form_does_not_stretch_legs_vertically(self):
        with tempfile.TemporaryDirectory() as tmp:
            roots = [Path(tmp)/str(i) for i in range(2)]
            settings = editor.default_settings()
            first = editor.build(settings, roots[0])
            settings['form'] = 'stocky'
            second = editor.build(settings, roots[1])
            for slot in ('left_leg', 'right_leg'):
                a = editor._glb_arrays((roots[0]/first['parts'][slot]['model']).read_bytes())[0]
                b = editor._glb_arrays((roots[1]/second['parts'][slot]['model']).read_bytes())[0]
                np.testing.assert_array_equal(a[:, 1:], b[:, 1:])
                self.assertGreater(np.ptp(b[:, 0]), np.ptp(a[:, 0]))



    def test_local_save_is_idempotent_immutable_and_detects_corruption(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(editor, 'STORE', Path(tmp)):
            first = editor.save(editor.default_settings())
            self.assertEqual(editor.save(editor.default_settings()), first)
            self.assertEqual(len(editor.list_saved()), 1)
            self.assertTrue(editor.saved_bundle(first['id']))
            path = Path(tmp)/first['id']/'model.glb'
            path.write_bytes(b'corrupted')
            with self.assertRaisesRegex(ValueError, 'immutable'):
                editor.save(editor.default_settings())
            with self.assertRaisesRegex(ValueError, 'повреждена'):
                editor.saved_bundle(first['id'])

    def test_constructor_routes_are_available_and_legacy_gallery_is_removed(self):
        app = create_app()
        app.config['TESTING'] = True
        with app.test_client() as client:
            for path in ('/creature-workshop/constructor/', '/creature-workshop/constructor/catalog'):
                response = client.get(path)
                self.assertEqual(response.status_code, 200)
                response.close()
            response = client.post('/creature-workshop/constructor/preview', json={**editor.default_settings(), 'schema_version': 99})
            self.assertEqual(response.status_code, 400)
            self.assertIn('schema_version', response.get_json()['error'])
            response.close()
            response = client.post('/creature-workshop/data/index.json', json={})
            self.assertEqual(response.status_code, 404)
            response.close()
            response = client.get('/creature-workshop/constructor/revisions/../../.env/download')
            self.assertEqual(response.status_code, 404)
            response.close()


if __name__ == '__main__':
    unittest.main()
