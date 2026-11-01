import copy
import unittest
import numpy as np
from monsterforge import workshop_constructor as e
from monsterforge.constructor_naga_costumes import apply
from monsterforge.constructor_face_fit import front_depth
from tools.creature_workshop.geometry import mesh,compile_recipe
from tests.creature_workshop.helpers import clean_settings

class NagaCostumeTests(unittest.TestCase):
 def test_all_costumes_replace_land_clothing_and_fit_approved_anatomy(self):
  for d in [d for d in e.SPECIES_DESIGNS if d['race']=='naga']:
   s=clean_settings('naga',d['id']);s['gender']=d['gender']
   for slot in ('torso','left_arm','right_arm'):
    r,_=e._load(d['id'],slot);source=copy.deepcopy(r);apply(r,s,slot)
    self.assertEqual(r['contract_anchors'],source['contract_anchors'])
    self.assertTrue(np.isfinite(compile_recipe(r)[0]).all())
    self.assertFalse(any(any(k in c['part'] for k in ('coat','tabard','belt','sleeve')) for c in r['commands']))
    base=[c for c in r['commands'] if c['part']=='naga_upper_anatomy' or c['part']=='naga_exposed_arm' or c['part'].endswith(('neck','palm'))]
    self.assertTrue(base)
    for c in r['commands']:
     if c['part'] in {'reef_overlapping_scale','scallop_radial_shell','abyss_segmented_carapace','abyss_keel_ridge','kelp_woven_lamella','kelp_horizontal_binding','tidal_royal_shell','tidal_radial_inlay','marine_pelvic_shell','marine_articulated_vambrace'}:
      v,_=mesh(c);clearance=v[:,2]-front_depth(base,v[:,:2]);self.assertTrue(np.isfinite(clearance).all());n=len(c.get('authored_outline_metres',[]));self.assertTrue(np.all(clearance[:2*n]>0));
      self.assertLessEqual(float(clearance.max()),.025001);self.assertGreaterEqual(float(clearance.min()),-.004001)
    for suffix in ('neck','palm'):
     old=[c for c in source['commands'] if c['part'].endswith(suffix)]
     new=[c for c in r['commands'] if c['part'].endswith(suffix)]
     for a,b in zip(old,new):np.testing.assert_array_equal(mesh(a)[0],mesh(b)[0])
    again,_=e._load(d['id'],slot);self.assertEqual(again,source)
 def test_marine_materials_support_constructor_palette(self):
  s=clean_settings('naga','expansion-naga-female-04');s['colors'].update(cloth='#123456',accent='#abcdef',secondary='#334455')
  r,_=e._load(s['outfit'],'torso');apply(r,s,'torso')
  self.assertEqual(r['palette']['marine_shell'],'123456');self.assertEqual(r['palette']['marine_ridge'],'abcdef');self.assertEqual(r['palette']['marine_fin'],'334455')
if __name__=='__main__':unittest.main()
