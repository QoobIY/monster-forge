"""Contact invariants for independently selected human constructor components."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import trimesh

from monsterforge import workshop_constructor as editor
from monsterforge.constructor_atlas import load
from monsterforge.constructor_component_fit import _section, footwear
from monsterforge.constructor_face_fit import surfaces, front_depth
from monsterforge.constructor_hair_shape import refine_braids
from monsterforge.constructor_surface_fit import triangles, radial_hit
from monsterforge.mom_rpg_presets import presets
from tools.creature_workshop.geometry import mesh, compile_recipe


class ComponentFitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='forge-component-test-')
        cls.root = Path(cls.temporary.name)
        cls.recipes = {}
        for preset in presets()[:3]:
            name = preset['id'].split('/')[-1]
            root = cls.root/name
            editor.build(preset['settings'], root)
            cls.recipes[name] = {p.parent.name: json.loads(p.read_text())
                                 for p in (root/'parts').glob('*/recipe.json')}

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_independent_emblem_and_shoulders_do_not_duplicate_base_clothes(self):
        witcher = self.recipes['witcher']
        self.assertNotIn('chest_rank_mark', [c['part'] for c in witcher['torso']['commands']])
        self.assertTrue(any('ornament_badge_wolf' in c['part'] for c in witcher['torso']['commands']))
        for name in ('viking', 'witcher'):
            for slot in ('left_arm', 'right_arm'):
                parts = [c['part'] for c in self.recipes[name][slot]['commands']]
                self.assertFalse({'pauldron', 'pauldron_facet', 'leather_shoulder'} & set(parts))
                self.assertTrue(any('shoulder' in p for p in parts), 'Selected separate shoulder gear is retained')
        source, _ = editor._load('library-human-01', 'torso')
        self.assertIn('chest_rank_mark', [c['part'] for c in source['commands']])

    def test_stubble_is_closed_and_has_only_two_millimetres_of_relief(self):
        head = self.recipes['witcher']['head']
        beard = next(c for c in head['commands'] if 'beard' in c['part'])
        v, f = mesh(beard)
        self.assertTrue(trimesh.Trimesh(v, f, process=True).is_watertight)
        depth = front_depth(surfaces(head), v[:, :2])
        self.assertTrue(np.isfinite(depth).all())
        np.testing.assert_allclose(np.sort(np.unique(np.round(v[:, 2]-depth, 6))), [-.001, .002])
        self.assertGreater(np.ptp(v[:, 0]), .25, 'Stubble follows the jaw rather than a detached chin block')

    def test_mage_beard_front_stays_outside_the_chin_between_vertices(self):
        head = self.recipes['mage']['head']
        beard = [c for c in head['commands'] if 'beard' in c['part']]
        v = np.concatenate([mesh(c)[0] for c in beard])
        skin = surfaces(head)
        low = max(np.concatenate([mesh(c)[0] for c in skin])[:,1].min()+.001, v[:,1].min())
        xy = np.array([[x,y] for x in np.linspace(v[:,0].min(),v[:,0].max(),41)
                       for y in np.linspace(low,v[:,1].max()-.001,41)])
        face_z, beard_z = front_depth(skin,xy), front_depth(beard,xy)
        overlap = np.isfinite(face_z)&np.isfinite(beard_z)
        self.assertGreater(overlap.sum(), 800)
        self.assertGreater((beard_z[overlap]-face_z[overlap]).min(), .001)
        for c in beard:
            vertices, faces = mesh(c)
            self.assertTrue(trimesh.Trimesh(vertices,faces,process=True).is_watertight)

    def test_mage_has_no_braid_dark_blue_cloth_and_a_clear_upper_lip(self):
        head = self.recipes['mage']['head']
        self.assertFalse(any('braid' in c['part'] for c in head['commands']))
        noses = np.concatenate([mesh(c)[0] for c in head['commands'] if 'nose_bridge' in c['part']])
        lips = np.concatenate([mesh(c)[0] for c in head['commands'] if 'upper_lip' in c['part']])
        self.assertGreaterEqual(noses[:, 1].min()-lips[:, 1].max(), .018-1e-8)
        s = next(p['settings'] for p in presets() if p['id']=='classes/mage')
        self.assertEqual(s['reference_parts']['hair'], 11)
        hair = [mesh(c)[0] for c in head['commands'] if 'hair' in c['part']
                and not c['part'].endswith(('hair_crown','hair_cap','scalp'))]
        self.assertGreater(np.concatenate(hair)[:,1].min(), 2.1)
        r, g, b = bytes.fromhex(s['colors']['cloth'][1:])
        self.assertGreater(b, g)
        self.assertGreater(g, r)
        self.assertLess(b, 100)
        self.assertEqual(self.recipes['mage']['torso']['palette']['cloth'], '182b52')

    def test_boot_shafts_cover_trousers_and_keep_the_floor(self):
        for name, parts in self.recipes.items():
            for slot in ('left_leg', 'right_leg'):
                with self.subTest(name=name, slot=slot):
                    recipe = parts[slot]
                    boots = [c for c in recipe['commands'] if c['part'] in ('flat_boot', 'boot_cuff')]
                    trousers = [c for c in recipe['commands'] if c['part']=='trousers']
                    skin, leather = triangles(trousers), triangles(boots)
                    for y in (.2, .25, .29, .32, .35, .365):
                        section = _section(trousers, y)
                        center = (section.min(0)+section.max(0))*.5
                        for angle in np.linspace(0, np.pi*2, 24, endpoint=False):
                            direction = np.array([np.cos(angle), 0, np.sin(angle)])
                            foot = radial_hit(leather, center, direction)
                            leg = radial_hit(skin, center, direction)
                            self.assertIsNotNone(foot)
                            self.assertGreater(foot-leg, .001)
                    before = copy.deepcopy(recipe)
                    footwear(recipe, slot)
                    self.assertEqual(recipe, before)
                    self.assertEqual(min(mesh(c)[0][:,1].min() for c in boots), 0)

    def test_long_straight_locks_and_interwoven_extended_braids(self):
        head = self.recipes['witcher']['head']
        parts = [c['part'] for c in head['commands']]
        self.assertEqual(parts.count('hair_straight_lock'), 6)
        self.assertEqual(parts.count('hair_parted_sweep'), 2)
        self.assertNotIn('hair_fringe', parts)
        # Frozen native and numbered sources both receive the same derived braid.
        samples = [editor._load('library-human-04','head')[0], copy.deepcopy(load('hair',18)),
                   copy.deepcopy(load('hair',28))]
        from monsterforge.constructor_portraits import procedural_hair
        base, _ = editor._load('library-human-01', 'head')
        commands, palette = procedural_hair(base, 'side-braid')
        samples.append({**base, 'commands':commands, 'palette':palette})
        for recipe in samples:
            before = copy.deepcopy(recipe)
            old = [mesh(c)[0] for c in recipe['commands'] if 'braid' in c['part'] and 'crown' not in c['part']]
            low = min(v[:,1].min() for v in old)
            refine_braids(recipe)
            strands = [c for c in recipe['commands'] if c['part']=='braid_woven_strand']
            self.assertIn(len(strands), (3,6))
            self.assertLess(min(mesh(c)[0][:,1].min() for c in strands), low-.10)
            compile_recipe(recipe)
            once = copy.deepcopy(recipe)
            refine_braids(recipe)
            self.assertEqual(recipe, once)
            for c in strands:
                v, f = mesh(c)
                self.assertTrue(trimesh.Trimesh(v, f, process=True).is_watertight)
            self.assertNotIn('hanging_braid_revision', before)

    def test_numbered_beards_fit_different_heads_without_changing_sources(self):
        from monsterforge.constructor_component_fit import facial_hair
        from tools.creature_workshop.review_human_hair import head
        for face in (1, 10):
            for beard in (1, 2, 3, 4, 9):
                with self.subTest(face=face, beard=beard):
                    settings = editor.default_settings()
                    settings['reference_parts'].update(male_faces=face, beards=beard)
                    source = copy.deepcopy(load('beards', beard))
                    recipe = head(settings)
                    facial_hair(recipe, settings)
                    commands = [c for c in recipe['commands'] if 'beard' in c['part']]
                    self.assertTrue(commands)
                    self.assertTrue(all('facial_hair_contact' in c for c in commands))
                    compile_recipe(recipe)
                    self.assertEqual(source, load('beards', beard))
