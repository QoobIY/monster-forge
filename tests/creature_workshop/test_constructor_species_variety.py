"""Anatomy, mixed donors and human-upper contract regression checks."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import trimesh

from monsterforge import constructor_cache as cache
from monsterforge import create_app
from monsterforge import workshop_constructor as editor
from monsterforge.constructor_species_variety import apply
from tests.creature_workshop.helpers import clean_settings
from tools.creature_workshop.geometry import compile_recipe, mesh


class SpeciesVarietyTests(unittest.TestCase):
    def revised(self, race, number, slot):
        donor = [d for d in editor.SPECIES_DESIGNS if d['race']==race][number]['id']
        recipe, _ = editor._load(donor, slot)
        frozen = copy.deepcopy(recipe)
        apply(recipe, clean_settings(race, donor), slot)
        recipe['commands'].sort(key=lambda c:c['stage'])
        self.assertTrue(np.isfinite(compile_recipe(recipe)[0]).all())
        for c in recipe['commands']:
            if c['id'] in {x['id'] for x in frozen['commands']}:
                continue
            v, f = mesh(c)
            self.assertTrue(trimesh.Trimesh(v, f, process=False).is_watertight, c['part'])
            self.assertTrue((trimesh.triangles.area(v[f]) > 1e-12).all(), c['part'])
        self.assertEqual(editor._load(donor, slot)[0], frozen)
        return recipe

    def test_elephant_ears_tusks_and_wool_have_distinct_anatomy(self):
        heads = [self.revised('beast-elephant', i, 'head') for i in range(3)]
        def vertices(r, part):
            return np.concatenate([mesh(c)[0] for c in r['commands'] if c['part']==part])
        widths = [np.ptp(vertices(r,'anatomical_elephant_ear')[:,0]) for r in heads]
        self.assertGreater(widths[1], widths[0]*1.5)
        self.assertLess(widths[2], widths[0])
        tusks = [vertices(r,'anatomical_ivory_tusk') for r in heads]
        self.assertGreater(tusks[2][:,1].max(), tusks[0][:,1].max()+.30)
        self.assertTrue(any(c['part']=='mammoth_hanging_wool' for c in heads[2]['commands']))
        self.revised('beast-elephant',2,'torso')

    def test_crab_claw_asymmetry_and_scorpion_tail_paths(self):
        claws = [self.revised('crab', 0, side+'_claw') for side in ('left','right')]
        sizes = [np.ptp(compile_recipe(r)[0],axis=0) for r in claws]
        self.assertGreater(sizes[0][1],sizes[1][1]*1.5)
        tail_bounds=[]
        for i in range(3):
            for race in ('crab','scorpion'):
                self.revised(race,i,'torso')
                self.revised(race,i,'left_claw')
            r=self.revised('scorpion',i,'tail')
            root=np.array(r['contract_anchors']['tail'])
            segment=next(c for c in r['commands'] if c['part']=='articulated_tail_segment')
            np.testing.assert_allclose(segment['path'][0],root)
            v=compile_recipe(r)[0];tail_bounds.append((v[:,1].max(),v[:,2].min()))
        self.assertGreater(tail_bounds[0][0],tail_bounds[1][0]+.4)
        self.assertLess(tail_bounds[2][1],tail_bounds[0][1]-.5)

    def test_beetle_shells_keep_ventral_attachments_and_have_distinct_dorsal_profiles(self):
        heights=[]
        for i in range(3):
            r=self.revised('beetle',i,'torso')
            source,_=editor._load([d for d in editor.SPECIES_DESIGNS if d['race']=='beetle'][i]['id'],'torso')
            c=next(c for c in r['commands'] if c['part']=='segmented_thoracic_shell')
            old=mesh(source['commands'][0])[0];new=mesh(c)[0]
            np.testing.assert_allclose(new[old[:,1]<=.56],old[old[:,1]<=.56])
            heights.append(new[:,1].max())
            self.revised('beetle',i,'head');self.revised('beetle',i,'abdomen')
        self.assertGreater(heights[1],heights[0]+.12)

    def test_centaur_human_controls_preserve_carrier_and_all_four_leg_donors(self):
        donor='expansion-centaur-male-01'
        for gender in ('male','female'):
            s=clean_settings('centaur',donor);s.update(gender=gender,arms='expansion-centaur-male-02',legs='expansion-centaur-male-03')
            s['reference_parts'].update({gender+'_faces':4,gender+'_clothes':7,'hair':3,'gloves':2,'body_forms':3})
            s['features']['nose']='broad';s['decor']['headwear']='crown'
            s['decor']['shoulders']='spikes'
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);manifest=editor.build(s,root)
                for slot in manifest['parts']:
                    r=json.loads((root/'parts'/slot/'recipe.json').read_text())
                    if slot.startswith(('front_','hind_')):
                        self.assertEqual(r['constructor']['sources'][0]['donor'],s['legs'])
                        source,_=editor._load(s['legs'],slot)
                        np.testing.assert_allclose(compile_recipe(r)[0],compile_recipe(source)[0])
                        self.assertAlmostEqual(compile_recipe(r)[0][:,1].min(),0)
                    if slot in {'head','torso','left_arm','right_arm'}:
                        self.assertEqual(r['centaur_upper']['gender'],gender)
                        self.assertTrue(r['attribute_references'])
                        self.assertEqual(r['constructor']['sources'][1]['donor'],'library-human-01')
                    if slot=='head':
                        self.assertTrue(any(c['part']=='ornament_crown_point' for c in r['commands']))
                    if slot.endswith('_arm'):
                        self.assertTrue(any(c['part']=='ornament_shoulder_spikes' for c in r['commands']))
                    if slot=='torso':
                        source,_=editor._load(donor,slot)
                        a=next(c for c in source['commands'] if c['part']=='horse_chest_waist_rump')
                        b=next(c for c in r['commands'] if c['part']==a['part'])
                        np.testing.assert_allclose(mesh(a)[0],mesh(b)[0])
                        self.assertFalse(any('mane' in c['part'] or 'horse_neck' in c['part'] or 'naga_' in c['part'] for c in r['commands']))
                        self.assertTrue(any('tailored_body' in c['part'] for c in r['commands']))
                assembly=json.loads((root/'assembly.json').read_text())
                self.assertTrue(all(set(v)=={'revision_id','model_sha256'} for v in assembly['parts'].values()))

    def test_centaur_catalog_and_validation_expose_only_compatible_human_attributes(self):
        race=next(r for r in editor.catalog(include_legacy=True)['races'] if r['id']=='centaur')
        self.assertTrue(race['human_upper']);self.assertNotEqual(race['gender_mode'],'neutral')
        for gender in ('male','female'):
            options=race['attribute_options'][gender]
            self.assertTrue(options[gender+'_faces']);self.assertTrue(options[gender+'_clothes'])
            self.assertTrue(options['hair']);self.assertTrue(options['gloves'])
            self.assertTrue(options['body_forms'])
            self.assertFalse(options['boots']);self.assertFalse(options['legs'])
        s=clean_settings('centaur','expansion-centaur-male-01')
        s['reference_parts']['boots']=1
        with self.assertRaises(ValueError):editor.validate_settings(s)

    def test_picker_serves_revised_cards_including_female_centaur(self):
        client=create_app().test_client()
        version=editor.catalog()['cards_version']
        captured=[]
        def arrays(spec):
            captured.append(spec)
            return (np.zeros((3,3)),np.zeros((3,3)),np.zeros((3,3)),[])
        def render(path,*args,**kwargs):
            path.write_bytes(b'\x89PNG\r\n')
        original_index=cache.INDEX.read_bytes()
        with tempfile.TemporaryDirectory() as temporary, patch.object(cache,'CACHE',Path(temporary)), patch('monsterforge.constructor_thumbnails.arrays',side_effect=arrays), patch('tools.creature_workshop.geometry.render_png',side_effect=render):
            for race in ('centaur','beast-elephant','crab','beetle','scorpion'):
                donor=next(d['id'] for d in editor.SPECIES_DESIGNS if d['race']==race)
                for gender in (('male','female') if race=='centaur' else ('male',)):
                    for category in ('face','hair','outfit','arms','legs'):
                        with self.subTest(race=race,gender=gender,category=category):
                            with client.get(f'/creature-workshop/constructor/cards/v{version}/{category}/{donor}.png?gender={gender}') as response:
                                self.assertEqual(response.status_code,200)
                                self.assertEqual(response.mimetype,'image/png')
                            expected='face' if category=='hair' else category
                            self.assertEqual(captured[-1]['category'],expected)
                            self.assertEqual(captured[-1]['gender'],gender)
                            self.assertEqual(captured[-1]['identifier'],donor)
        self.assertEqual(cache.INDEX.read_bytes(),original_index)

    def test_centaur_portrait_builder_receives_the_selected_gender_and_category(self):
        from monsterforge.constructor_thumbnails import arrays, selector
        donor='expansion-centaur-male-01'
        captured=[]
        def build(settings,root):
            captured.append(copy.deepcopy(settings))
            for slot in ('head','torso'):
                (root/(slot+'.glb')).write_bytes(b'derived-geometry')
            return {'parts':{slot:{'model':slot+'.glb'} for slot in ('head','torso')}}
        geometry=(np.zeros((3,3)),np.zeros((3,3)),np.zeros((3,3)),[])
        with patch.object(editor,'build',side_effect=build), patch.object(editor,'_glb_arrays',return_value=geometry):
            for gender in ('male','female'):
                for category in ('face','outfit'):
                    path=editor.ROOT/'media/constructor/species_anatomy/v1/cards'/donor/gender/(category+'.png')
                    spec=selector(path)
                    self.assertEqual(spec['category'],category)
                    result=arrays(spec)
                    self.assertEqual(captured[-1]['gender'],gender)
                    self.assertEqual(captured[-1]['face'],donor)
                    self.assertEqual(result[0].shape,(3 if category=='face' else 6,3))


if __name__=='__main__':
    unittest.main()
