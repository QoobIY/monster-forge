"""Satyr derivatives retain source records, common floor and bone restrictions."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from monsterforge import workshop_constructor as editor
from monsterforge.constructor_satyr import apply
from tests.creature_workshop.test_constructor_marsh_forest import settings
from tools.creature_workshop.geometry import mesh, compile_recipe


class SatyrRevisionTests(unittest.TestCase):
    def test_horns_have_three_anatomical_silhouettes_and_original_source_is_unchanged(self):
        bounds=[]
        for i in range(1,4):
            donor=f'native-satyr-{i:02d}'
            recipe,_=editor._load(donor,'head');before=copy.deepcopy(recipe)
            apply(recipe,'head');compile_recipe(recipe)
            horns=[c for c in recipe['commands'] if c['part']=='satyr_anatomical_horn']
            self.assertEqual(len(horns),2)
            np.testing.assert_allclose(np.asarray(horns[0]['path'])*[-1,1,1],horns[1]['path'],atol=1e-12)
            np.testing.assert_allclose(horns[0]['radii'],horns[1]['radii'])
            v=np.concatenate([mesh(c)[0] for c in horns]);bounds.append(np.ptp(v,axis=0))
            self.assertEqual(editor._load(donor,'head')[0],before)
            self.assertEqual(sum(c['part']=='satyr_horizontal_goat_pupil' for c in recipe['commands']),2)
            self.assertEqual(sum(c['part']=='satyr_royal_horn_tine' for c in recipe['commands']),4 if i==3 else 0)
        self.assertGreater(bounds[1][0],bounds[0][0]*1.25)
        self.assertGreater(bounds[2][1],bounds[0][1]+.15)

    def test_mixed_donors_preserve_floor_cloven_hooves_and_explicit_weights(self):
        s=settings('satyr');s.update(outfit='native-satyr-02',arms='native-satyr-03',legs='native-satyr-02')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manifest=editor.build(s,root,weights=True)
            for slot,info in manifest['parts'].items():
                recipe=json.loads((root/'parts'/slot/'recipe.json').read_text())
                sidecar=json.loads((root/info['weights']).read_text())
                self.assertEqual(recipe['satyr_anatomy_revision']['revision'],2)
                self.assertTrue(all(c['skin_bone'] in sidecar['allowed_bones'] for c in recipe['commands']))
                donor=s['face' if slot=='head' else 'arms' if slot.endswith('_arm') else 'legs' if slot.endswith('_leg') else 'outfit']
                self.assertEqual(recipe['constructor']['sources'][0]['donor'],donor)
                if slot.endswith('_leg'):
                    self.assertAlmostEqual(compile_recipe(recipe)[0][:,1].min(),0,places=9)
                    hooves=[mesh(c)[0] for c in recipe['commands'] if c['part']=='satyr_cloven_hoof']
                    self.assertEqual(len(hooves),2)
                    self.assertLess(hooves[0][:,0].max(),hooves[1][:,0].min())
                if slot.endswith('_arm'):
                    self.assertEqual(sum(c['part']=='satyr_articulated_finger' for c in recipe['commands']),4)


if __name__=='__main__':unittest.main()
