"""Picker images must depict their category, even with an empty thumbnail cache."""
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from monsterforge import constructor_cache as cache
from monsterforge import create_app
from monsterforge.constructor_atlas import load, part_folder
from monsterforge.constructor_racial_anatomy import VARIANTS
from monsterforge.constructor_thumbnails import arrays, selector
from monsterforge.paths import ROOT
from tools.assets import migrate_constructor_storage as migration
from tools.creature_workshop.geometry import compile_recipe


class ThumbnailTests(unittest.TestCase):
    def test_anatomy_portraits_keep_their_exact_race_gender_and_head_selection(self):
        captured = []
        head = np.array([[0., 2., 0.], [1., 2., 0.], [0., 3., 0.]])

        def build(settings, root):
            captured.append(settings)
            (root / 'head.glb').write_bytes(b'head')
            (root / 'torso.glb').write_bytes(b'torso')
            return {'parts': {'head': {'model': 'head.glb'}, 'torso': {'model': 'torso.glb'}}}

        def glb_arrays(blob):
            self.assertEqual(blob, b'head', 'Portraits must not frame a whole body')
            return head, np.ones_like(head), np.ones_like(head)

        with patch('monsterforge.workshop_constructor.build', side_effect=build), patch('monsterforge.workshop_constructor._glb_arrays', side_effect=glb_arrays):
            for identifier, anatomy in VARIANTS.items():
                for category in ('face', 'hair'):
                    with self.subTest(identifier=identifier, category=category):
                        logical = ROOT / 'media/constructor/cards/v28' / category / (identifier + '.png')
                        spec = selector(logical)
                        self.assertEqual(spec['category'], category)
                        self.assertEqual(spec['gender'], anatomy['gender'])
                        result = arrays(spec)
                        np.testing.assert_array_equal(result[0], head)
                        self.assertEqual(captured[-1]['race'], anatomy['race'])
                        self.assertEqual(captured[-1]['gender'], anatomy['gender'])
                        self.assertEqual(captured[-1]['face'], identifier)
                        self.assertEqual(captured[-1]['hair'], 'bald')
                        for slot in ('outfit', 'arms', 'legs'):
                            self.assertEqual(captured[-1][slot], anatomy['source'])
                self.assertIsNone(selector(ROOT / 'media/constructor/cards/v28/outfit' / (identifier + '.png')))

    def test_anatomy_routes_rebuild_missing_portraits_in_the_disposable_cache(self):
        client = create_app().test_client()
        original_is_file = Path.is_file
        original_index = cache.INDEX.read_bytes()
        portraits = {
            ROOT / ('media/constructor/goblins/v1/face/' if anatomy['race'] == 'goblin'
                    else 'media/constructor/racial_anatomy/v5/face/') / (identifier + '.png')
            for identifier, anatomy in VARIANTS.items()
        }
        captured = []

        def render(path, geometry, **kwargs):
            self.assertTrue(np.isfinite(geometry[0]).all())
            self.assertGreater(len(geometry[0]), 0)
            self.assertGreater(geometry[0][:, 1].min(), 1.8)
            captured.append(geometry)
            path.write_bytes(b'test-anatomy-thumbnail')

        with tempfile.TemporaryDirectory(dir='/tmp', prefix='forge-anatomy-card-') as temporary, patch.object(cache, 'CACHE', Path(temporary)), patch.object(Path, 'is_file', lambda path: False if path in portraits else original_is_file(path)), patch('tools.creature_workshop.geometry.render_png', side_effect=render):
            for race, gender, category in (('skeleton', 'male', 'face'), ('minotaur', 'male', 'face'), ('orc', 'male', 'face'), ('goblin', 'male', 'face'), ('orc', 'female', 'hair')):
                identifier = f'anatomy-{race}-{gender}-01'
                with self.subTest(identifier=identifier, category=category):
                    with client.get(f'/creature-workshop/constructor/cards/v28/{category}/{identifier}.png') as response:
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.mimetype, 'image/png')
                        self.assertEqual(response.data, b'test-anatomy-thumbnail')
            self.assertEqual(len(captured), 5)
            self.assertEqual(len(list(Path(temporary).glob('*.png'))), 5)
        self.assertEqual(cache.INDEX.read_bytes(), original_index)

    def test_unregistered_native_preview_is_rebuilt_in_tmp_without_publishing_files(self):
        logical = ROOT / 'media/constructor/cards/v28/face/library-human-01.png'
        entries = dict(cache.artifact_index())
        entries.pop(logical.relative_to(ROOT).as_posix(), None)
        original_index = cache.INDEX.read_bytes()
        with tempfile.TemporaryDirectory(dir='/tmp', prefix='forge-native-card-') as temporary:
            with patch.object(cache, 'CACHE', Path(temporary)), patch.object(cache, 'artifact_index', return_value=entries):
                image = cache.resolve(logical)
                self.assertTrue(image.is_relative_to(temporary))
                self.assertTrue(image.read_bytes().startswith(b'\x89PNG\r\n'))
                self.assertFalse(logical.exists())
        self.assertEqual(cache.INDEX.read_bytes(), original_index)
        reference = ROOT / 'media/constructor/missing-source/reference.png'
        with patch('monsterforge.constructor_thumbnails.selector', side_effect=AssertionError('Do not invent references')):
            self.assertEqual(cache.resolve(reference), reference)

    def test_all_recipe_previews_pin_their_own_category_and_revision(self):
        count = 0
        for key, spec in cache.artifact_index().items():
            path = ROOT / key
            if path.suffix != '.png' or spec['kind'] not in {'preview', 'card'}:
                continue
            candidates = (path.with_suffix('.recipe.json'), path.parent / 'recipe.json')
            recipe = next((p for p in candidates if p.is_file()), None)
            if recipe is None:
                continue
            with self.subTest(path=key):
                self.assertEqual(spec['recipes'], [{'path': recipe.relative_to(ROOT).as_posix(),
                                                   'sha256': hashlib.sha256(recipe.read_bytes()).hexdigest()}])
            count += 1
        self.assertGreater(count, 200)

    def test_cold_head_and_feature_routes_render_the_selected_recipe(self):
        client = create_app().test_client()
        with tempfile.TemporaryDirectory(dir='/tmp', prefix='forge-card-test-') as temporary, patch.object(cache, 'CACHE', Path(temporary)):
            for category in ('male_faces', 'female_faces', 'noses', 'jaws', 'mouths', 'race_heads'):
                for number in (1, 3):
                    expected = compile_recipe(load(category, number))
                    captured = []
                    def render(path, arrays, captured=captured, **kwargs):
                        captured.append(arrays)
                        path.write_bytes(b'test-thumbnail')
                    with self.subTest(category=category, number=number), patch('tools.creature_workshop.geometry.render_png', side_effect=render):
                        with client.get(f'/creature-workshop/constructor/attribute-parts/{category}/{number}.png') as response:
                            self.assertEqual(response.status_code, 200)
                        self.assertEqual(len(captured), 1)
                        np.testing.assert_array_equal(captured[0][0], expected[0])
                        self.assertEqual({c['slot'] for c in load(category, number)['commands']}, {'head'})
                        self.assertFalse((part_folder(category, number) / 'front.png').exists())

    def test_selector_uses_explicit_attributes_and_rejects_unknown_numbers(self):
        for category in ('male_faces', 'female_faces', 'female_clothes', 'noses', 'jaws', 'mouths', 'body_forms', 'accessories'):
            with self.subTest(category=category):
                path = ROOT / 'media/constructor/cards/v28' / category / '01.png'
                spec = selector(path)
                expected = part_folder(category, 1) / 'recipe.json'
                self.assertEqual(spec['recipes'][0]['path'], expected.relative_to(ROOT).as_posix())
        self.assertIsNone(selector(ROOT / 'media/constructor/unknown_cards/01.png'))

    def test_repair_replaces_wrong_clothing_refs_and_is_repeatable(self):
        with tempfile.TemporaryDirectory(dir='/tmp', prefix='forge-card-migrate-') as temporary:
            root = Path(temporary)
            recipe = root / 'media/constructor/attribute_sculpts/v26/male_faces/01/recipe.json'
            recipe.parent.mkdir(parents=True)
            recipe.write_text('{"category":"male_faces"}')
            key = recipe.with_name('front.png').relative_to(root).as_posix()
            index = root / 'config/constructor_artifacts_v1.json'
            index.parent.mkdir()
            index.write_text(json.dumps({'schema_version': 1, 'artifacts': {key: {
                'kind': 'preview', 'yaw': 0, 'recipes': [{'path': 'wrong/male_clothes/01/recipe.json', 'sha256': '0' * 64}]}}}))
            with patch.object(migration, 'ROOT', root), patch.object(cache, 'ROOT', root), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(migration.repair_thumbnail_sources(apply=True), 1)
                self.assertEqual(migration.repair_thumbnail_sources(apply=True), 0)
            spec = json.loads(index.read_text())['artifacts'][key]
            self.assertEqual(spec['recipes'][0]['path'], recipe.relative_to(root).as_posix())
            self.assertEqual(spec['yaw'], 0)
            self.assertFalse(recipe.with_name('front.png').exists())

    def test_changed_component_portraits_use_current_assembly_in_disposable_cache(self):
        captured = []
        def arrays(spec):
            captured.append(spec)
            return (np.zeros((3,3)), np.zeros((3,3)), np.zeros((3,3)), [])
        def render(path, *args, **kwargs):
            path.write_bytes(b'current-component-thumbnail')
        original_index = cache.INDEX.read_bytes()
        with tempfile.TemporaryDirectory(dir='/tmp', prefix='forge-component-card-') as temporary, patch.object(cache, 'CACHE', Path(temporary)), patch('monsterforge.constructor_thumbnails.arrays', side_effect=arrays), patch('tools.creature_workshop.geometry.render_png', side_effect=render):
            client = create_app().test_client()
            for category, number, gender in (('hair',18,'female'), ('beards',1,'male'), ('boots',2,'male')):
                with client.get(f'/creature-workshop/constructor/attribute-parts/{category}/{number}.png?gender={gender}') as response:
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.data, b'current-component-thumbnail')
                self.assertEqual(captured[-1]['category'], category)
                self.assertEqual(captured[-1]['gender'], gender)
                self.assertTrue(captured[-1]['assembled'])
                self.assertEqual(captured[-1]['geometry_revision'], 'component-fit-v2')
        self.assertEqual(cache.INDEX.read_bytes(), original_index)

    def test_current_numbered_facial_hair_cards_frame_only_the_head(self):
        from monsterforge.constructor_thumbnails import arrays
        with patch('monsterforge.workshop_constructor.render_png'):
            for category in ('beards', 'mustaches'):
                result = arrays({'category':category, 'identifier':'1', 'gender':'male', 'assembled':True})
                self.assertGreater(result[0][:,1].min(), 1.9)
                self.assertGreater(result[0][:,1].max(), 2.4)


if __name__ == '__main__':
    unittest.main()
