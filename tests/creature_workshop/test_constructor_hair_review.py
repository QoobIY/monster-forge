"""Posterior scalp coverage and preservation of authored braid/lock geometry."""
import copy
import unittest

import numpy as np

from monsterforge import workshop_constructor as editor
from monsterforge.constructor_atlas import available, load
from monsterforge.constructor_face_fit import surfaces
from monsterforge.constructor_surface_fit import fit_scalp, triangles, radial_hit
from tools.creature_workshop.geometry import mesh, compile_recipe
from tools.creature_workshop.review_human_hair import head


class HumanHairReviewTests(unittest.TestCase):
    def settings(self, gender, number, face=1):
        s=editor.default_settings();s['gender']=gender
        s['reference_parts'].update({gender+'_faces':face,'hair':number})
        return s

    def test_every_selectable_hair_has_rear_scalp_coverage_on_different_heads(self):
        for gender in ('male','female'):
            for face in (1,10):
                for number in available('hair','human',gender):
                    with self.subTest(gender=gender,face=face,hair=number):
                        recipe=head(self.settings(gender,number,face))
                        caps=[c for c in recipe['commands'] if c['part'].endswith(('hair_crown','hair_cap','scalp'))]
                        # The mohawk intentionally leaves the sides shaved.
                        if number==6:
                            self.assertFalse(caps);continue
                        self.assertEqual(len(caps),1)
                        face_parts=surfaces(recipe);skin_tri=triangles(face_parts);hair_tri=triangles(caps)
                        top=max(mesh(c)[0][:,1].max() for c in face_parts)
                        for y in (top-.20,top-.31,top-.36):
                            for angle in (-.45,-.2,0,.2,.45):
                                p=np.array([0,y,.005]);d=np.array([np.sin(angle),0,-np.cos(angle)])
                                skin=radial_hit(skin_tri,p,d);hair=radial_hit(hair_tri,p,d)
                                if skin is None:continue
                                self.assertIsNotNone(hair)
                                self.assertGreater(hair-skin,.003)

    def test_crown_braid_lobes_stay_small_and_strands_move_rigidly(self):
        source=copy.deepcopy(load('hair',9))
        r=head(self.settings('male',9))
        lobes=[c for c in r['commands'] if 'crown_braid_lobe' in c['part']]
        self.assertGreater(len(lobes),5)
        for c in lobes:
            before=np.asarray(c['scalp_contact_template']['vertices']);after=mesh(c)[0]
            self.assertEqual(len(after),len(before))
            np.testing.assert_allclose(after-after.mean(0),before-before.mean(0),atol=1e-12)
            self.assertLess(np.ptp(after[:,1]),.12)
        self.assertEqual(source,load('hair',9))

    def test_loose_styles_have_closed_rear_volume_and_repeatable_fit(self):
        for number in (2,8,17,24,25,26,29):
            gender='female' if number in (17,26,29) else 'male'
            with self.subTest(hair=number):
                r=head(self.settings(gender,number))
                rear=next(c for c in r['commands'] if c['part']=='hair_back_curtain')
                v,f=mesh(rear);skin=surfaces(r);top=max(mesh(c)[0][:,1].max() for c in skin)
                tri=triangles([rear])
                for y in np.linspace(v[:,1].min()+.04,top-.16,8):
                    hit=radial_hit(tri,np.array([0,y,.005]),np.array([0,0,-1]))
                    self.assertIsNotNone(hit)
                    self.assertGreater(hit,.10)
                before={c['id']:mesh(c)[0].copy() for c in r['commands']}
                fit_scalp(r);r['commands'].sort(key=lambda c:c['stage']);compile_recipe(r)
                for c in r['commands']:
                    np.testing.assert_allclose(mesh(c)[0],before[c['id']],atol=1e-12)


if __name__=='__main__':unittest.main()
