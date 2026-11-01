import json,tempfile,unittest
from pathlib import Path
import numpy as np
import trimesh
from monsterforge import workshop_constructor as e
from monsterforge.constructor_mounts import Surface
from tools.creature_workshop.geometry import mesh,compile_recipe
from tests.creature_workshop.helpers import clean_settings

class BeetleLegTests(unittest.TestCase):
 def test_all_beetles_have_six_grounded_articulated_legs_with_separated_supports(self):
  for d in [d for d in e.SPECIES_DESIGNS if d['race']=='beetle']:
   s=clean_settings('beetle',d['id'])
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);result=e.build(s,root);feet={}
    for slot in result['parts']:
     if '_leg_' not in slot:continue
     r=json.loads((root/'parts'/slot/'recipe.json').read_text());meta=r['beetle_leg_anatomy'];profile=meta['profile'];feet[slot]=profile['tip'];a=compile_recipe(r)[0];self.assertAlmostEqual(float(a[:,1].min()),0,places=7);self.assertTrue(np.isfinite(a).all())
     self.assertLess(profile['root'][1],.55);self.assertLess(profile['knee'][1],.58)
     for c in r['commands']:
      v,f=mesh(c);self.assertTrue(trimesh.Trimesh(v,f,process=False).is_watertight,c['part'])
     self.assertTrue(any(c['part']=='beetle_contoured_femur' for c in r['commands']));self.assertEqual(sum(c['part']=='beetle_grounded_claw' for c in r['commands']),2)
     # Roots sit inside the actual shell at this section, rather than floating.
     body_slot='abdomen' if meta['pair']==3 else 'torso';body=json.loads((root/'parts'/body_slot/'recipe.json').read_text());sg=-1 if meta['side']=='left' else 1
     carriers=[c for c in body['commands'] if c['part'] in {'separate_elytron','segmented_thoracic_shell'} and (body_slot!='abdomen' or np.sign(mesh(c)[0][:,0].mean())==sg)]
     surface=Surface(carriers[0]);p=np.array(profile['root']);centre=surface.centre(p[2]);origin=[centre[0],p[1],p[2]];hit=surface.hit(origin,[sg,0,0]);self.assertLessEqual(sg*p[0],sg*hit[0]+.003)
    self.assertEqual(len(feet),6)
    for side in ('left','right'):
     self.assertGreater(feet[side+'_leg_1'][2],.70);self.assertLess(abs(feet[side+'_leg_2'][2]),.1);self.assertLess(feet[side+'_leg_3'][2],-.90)
    for i in (1,2,3):np.testing.assert_allclose(np.array(feet[f'left_leg_{i}'])*[-1,1,1],feet[f'right_leg_{i}'],atol=1e-12)

 def test_front_and_rear_donors_are_independent_and_equipment_is_retained(self):
  s=clean_settings('beetle','expansion-nerubian-male-01');s.update(arms='expansion-beetle-male-01',legs='expansion-beetle-male-02');s['decor'].update(headwear='insect_war_helm',shoulders='insect_thorax_lamellar',belt='insect_elytra_guard')
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);e.build(s,root)
   for slot in ('head','torso','abdomen'):self.assertTrue(json.loads((root/'parts'/slot/'recipe.json').read_text()).get('insect_equipment'))
   for i in (1,2,3):
    r=json.loads((root/'parts'/f'left_leg_{i}'/'recipe.json').read_text());expected=e._load(s['arms'] if i==1 else s['legs'],f'left_leg_{i}')[1]
    self.assertEqual(r['constructor']['sources'][0]['model_sha256'],expected['model_sha256'])
if __name__=='__main__':unittest.main()
