"""Human skull shape, attachment placement, and immutable source boundaries."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from monsterforge import workshop_constructor as editor
from monsterforge.constructor_human_heads import apply, deform, FORWARD_SHIFT
from tools.creature_workshop.geometry import compile_recipe, mesh


class HumanHeadTests(unittest.TestCase):
    def test_rounding_keeps_facial_planes_and_does_not_fold_depth(self):
        z = np.linspace(-.35, .35, 301)
        for x in (0, .08, .16, .22, .30):
            vertices = np.column_stack([np.full(len(z), x), np.full(len(z), 2.3), z])
            result = deform(vertices, .21)
            np.testing.assert_array_equal(result[:, :2], vertices[:, :2])
            self.assertTrue(np.all(np.diff(result[:, 2]) > 0))
            front = z >= .06
            np.testing.assert_allclose(result[front, 2] - z[front], FORWARD_SHIFT)
        rear = np.array([[0, 2.36, -.17], [.175, 2.36, -.17], [-.175, 2.36, -.17]])
        result = deform(rear, .21)
        self.assertAlmostEqual(result[0, 2] - rear[0, 2], FORWARD_SHIFT)
        # Rear lateral corners recede towards the rounded central occiput.
        self.assertGreater(result[1, 2] - result[0, 2], .045)
        self.assertAlmostEqual(result[1, 2], result[2, 2])

    def test_assembled_variants_preserve_features_and_move_all_attachments_together(self):
        cases = [editor.default_settings()]
        for gender in ('male', 'female'):
            value = editor.default_settings()
            value['gender'] = gender
            value['reference_parts'][gender + '_faces'] = 1
            value['reference_parts']['hair'] = 1
            cases.append(value)
        bald = copy.deepcopy(cases[1])
        bald['hair'] = 'bald'
        bald['reference_parts']['hair'] = 0
        cases.append(bald)
        for settings in cases:
            with self.subTest(gender=settings['gender'], hair=settings['hair'], helmet=settings['decor']['headwear']), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                with patch('monsterforge.constructor_human_heads.apply'), patch('monsterforge.constructor_human_heads.reshape'):
                    editor.build(settings, root / 'before')
                editor.build(settings, root / 'after')
                before = json.loads((root / 'before/parts/head/recipe.json').read_text())
                after = json.loads((root / 'after/parts/head/recipe.json').read_text())
                width = after['human_head_revision']['half_width_metres']
                self.assertEqual(len(before['commands']), len(after['commands']))
                for old, new in zip(before['commands'], after['commands'], strict=True):
                    original, faces = mesh(old)
                    actual, actual_faces = mesh(new)
                    # Neck shortening commutes with the correction along Z.
                    expected = deform(original, width)
                    np.testing.assert_allclose(actual, expected, atol=1e-8)
                    np.testing.assert_array_equal(faces, actual_faces)
                compile_recipe(after)  # Closed volumes, valid winding and finite normals.
                once = copy.deepcopy(after)
                apply(after, settings, 'head')
                self.assertEqual(after, once)
                for slot in ('torso', 'left_arm', 'right_arm', 'left_leg', 'right_leg'):
                    self.assertEqual((root / 'before/parts' / slot / 'recipe.json').read_bytes(),
                                     (root / 'after/parts' / slot / 'recipe.json').read_bytes())

    def test_other_races_and_nonhead_parts_are_unchanged(self):
        recipe = {'commands': [], 'custom_metadata': {'keep': True}}
        before = copy.deepcopy(recipe)
        for race, slot in (('randomium', 'head'), ('orc', 'head'), ('human', 'torso')):
            apply(recipe, {'race': race}, slot)
            self.assertEqual(recipe, before)


if __name__ == '__main__':
    unittest.main()
