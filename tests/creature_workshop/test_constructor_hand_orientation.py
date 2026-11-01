"""Handedness revisions preserve immutable sources and leave arm pivots fixed."""
import copy
import unittest

import numpy as np

from monsterforge import workshop_constructor as editor
from monsterforge.constructor_hand_orientation import apply, is_hand
from monsterforge.constructor_knees import world_bind
from tools.creature_workshop.geometry import compile_recipe, mesh


class HandOrientationTests(unittest.TestCase):
    def test_humanoid_hands_reflect_about_the_wrist_once_and_preserve_sources(self):
        for donor in ('library-human-01', 'native-golem-male-01', 'native-ghost-male-01'):
            for slot in ('left_arm', 'right_arm'):
                with self.subTest(donor=donor, slot=slot):
                    source, _ = editor._load(donor, slot)
                    original = copy.deepcopy(source)
                    derived = copy.deepcopy(source)
                    wrist = np.asarray(world_bind('canonical')[slot.split('_')[0] + '_hand'])
                    apply(derived, slot)
                    self.assertTrue(any(c.get('hand_orientation_revision') for c in derived['commands']))
                    for before, after in zip(source['commands'], derived['commands'], strict=True):
                        old = mesh(before)[0]
                        new = mesh(after)[0]
                        if is_hand(before):
                            np.testing.assert_allclose(new[:, :2], old[:, :2])
                            np.testing.assert_allclose(new[:, 2], 2 * wrist[2] - old[:, 2])
                        else:
                            np.testing.assert_array_equal(new, old)
                    once = copy.deepcopy(derived)
                    apply(derived, slot)
                    self.assertEqual(derived, once)
                    self.assertEqual(source, original)
                    positions, normals, _, _ = compile_recipe(derived)
                    self.assertTrue(np.isfinite(positions).all())
                    np.testing.assert_allclose(np.linalg.norm(normals, axis=1), 1, atol=1e-5)

    def test_nonhand_slots_and_elbow_symbols_are_untouched(self):
        from monsterforge.constructor_randomiums import recipe
        for slot in ('head', 'torso', 'left_leg', 'right_leg'):
            r = recipe(slot)
            before = copy.deepcopy(r)
            apply(r, slot)
            self.assertEqual(r, before)
        for slot in ('left_arm', 'right_arm'):
            r = recipe(slot)
            for c in r['commands']:
                if c['part'] == 'randomium_joint_plate' or c['part'].startswith('randomium_symbol_'):
                    self.assertNotIn('hand_orientation_revision', c)
                    v, _ = mesh(c)
                    joint = np.asarray(world_bind('canonical')[slot.split('_')[0] + '_elbow'])
                    sign = -1 if slot.startswith('left') else 1
                    self.assertGreater(np.min((v[:, 0] - joint[0]) * sign), .025)
