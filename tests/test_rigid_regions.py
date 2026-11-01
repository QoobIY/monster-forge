"""Constructor binding contracts for rigid anatomy and surface ornaments."""
import unittest

from monsterforge.constructor_rigid_regions import apply_weights, mark_dice_head


class RigidRegionTests(unittest.TestCase):
    def test_head_and_markings_share_one_transform(self):
        recipe = {'commands': [{'part': 'randomium_die_head'},
                               {'part': 'randomium_die_pip'}, {'part': 'neck'}]}
        mark_dice_head(recipe, 'head')
        weights = {'allowed_bones': ['neck', 'head'], 'bone_palette': ['neck', 'head'],
                   'skin_indices': [[0, 1, 0, 0] for _ in range(3)],
                   'skin_weights': [[.25, .75, 0, 0] for _ in range(3)]}
        apply_weights(weights, recipe, [1, 2, 3])
        self.assertEqual(weights['skin_weights'][:2], [[1., 0., 0., 0.]] * 2)
        self.assertEqual(weights['skin_indices'][:2], [[1, 0, 0, 0]] * 2)
        self.assertEqual(weights['skin_weights'][2], [.25, .75, 0, 0])

    def test_rigid_region_cannot_cross_slot_bone_contract(self):
        recipe = {'rigid_regions_revision': 1,
                  'commands': [{'skin_bone': 'right_hand'}]}
        with self.assertRaisesRegex(ValueError, 'outside its slot'):
            apply_weights({'allowed_bones': ['head']}, recipe, [1])

    def test_existing_unmarked_character_keeps_its_weights(self):
        recipe = {'commands': [{'part': 'human_face'}]}
        mark_dice_head(recipe, 'head')
        self.assertNotIn('rigid_regions_revision', recipe)
        weights = {'untouched': True}
        apply_weights(weights, recipe, [])
        self.assertEqual(weights, {'untouched': True})
