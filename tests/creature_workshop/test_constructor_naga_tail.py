import json,tempfile,unittest
from pathlib import Path
import numpy as np
import trimesh
from monsterforge import workshop_constructor as e
from monsterforge.constructor_face_fit import front_depth
from tools.creature_workshop.geometry import mesh,compile_recipe
from tests.creature_workshop.helpers import clean_settings

class NagaTailTests(unittest.TestCase):
 def test_all_ten_naga_tails_are_straight_backwards_grounded_and_have_fitted_plates(self):
  designs=[d for d in e.SPECIES_DESIGNS if d['race']=='naga'];self.assertEqual(len(designs),10)
  for d in designs:
   s=clean_settings('naga',d['id']);s['gender']=d['gender']
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);result=e.build(s,root);r=json.loads((root/'parts/tail/recipe.json').read_text());profile=np.array(r['naga_tail_revision']['path']);self.assertTrue(np.all(profile[:,0]==0));self.assertTrue(np.all(np.diff(profile[:,2])<0));self.assertLess(profile[-1,2],-2.4)
    vertices=compile_recipe(r)[0];self.assertTrue(np.isfinite(vertices).all());self.assertAlmostEqual(float(vertices[:,1].min()),0,places=6)
    self.assertEqual(len(result['parts']),5);self.assertFalse(any(c['part']=='serpentine_muscular_coiled_tail' for c in r['commands']))
    shell=next(c for c in r['commands'] if c['part']=='straight_rearward_serpent_tail');self.assertEqual(sum(c['part']=='ventral_serpent_scute' for c in r['commands']),8)
    for c in r['commands']:
     v,f=mesh(c);self.assertTrue(trimesh.Trimesh(v,f,process=False).is_watertight)
     if c['part']=='ventral_serpent_scute':
      clearance=v[:,2]-front_depth([shell],v[:,:2]);self.assertTrue(np.isfinite(clearance).all());self.assertGreaterEqual(float(clearance.min()),-.00301);self.assertLess(float(clearance.max()),.02)
    for slot in ('head',):
     built=json.loads((root/'parts'/slot/'recipe.json').read_text());original,_=e._load(d['id'],slot);np.testing.assert_array_equal(compile_recipe(built)[0],compile_recipe(original)[0])

 def test_tail_selection_remains_a_separate_modular_choice(self):
  s=clean_settings('naga','expansion-naga-female-04');s.update(gender='female',legs='expansion-naga-female-02')
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);e.build(s,root);r=json.loads((root/'parts/tail/recipe.json').read_text());self.assertEqual(r['species_design']['id'],s['legs']);self.assertEqual(r['naga_tail_revision']['direction'],'-Z (backwards)')
if __name__=='__main__':unittest.main()
