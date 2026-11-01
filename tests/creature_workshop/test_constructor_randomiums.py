"""Randomium die, joint emblems and the constructor/export contract."""
import hashlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from collections import Counter
from itertools import pairwise
from pathlib import Path

import numpy as np

from monsterforge import create_app
from monsterforge import workshop_constructor as editor
from monsterforge.constructor_face_fit import front_depth
from monsterforge.constructor_knees import world_bind
from monsterforge.constructor_randomiums import (
    DESIGNS,
    DIE_FACES,
    EMBLEMS,
    HIDDEN_PARTS,
    JOINT_SYMBOLS,
    MAHJONG_SYMBOLS,
    PART_GAP,
    SOURCE,
    recipe,
)
from tools.creature_workshop.geometry import compile_recipe, mesh


def settings(design=0):
    value = editor.default_settings()
    donor = DESIGNS[design]['id']
    value.update(race='randomium', face=donor, outfit=donor, arms=donor, legs=donor)
    return value


class RandomiumTests(unittest.TestCase):
    def test_original_colours_are_required_for_both_gods(self):
        for design in range(2):
            self.assertEqual(editor.validate_settings(settings(design)), settings(design))
            for key in editor.DEFAULT_COLORS:
                with self.subTest(design=design, colour=key):
                    value = settings(design)
                    value['colors'][key] = '#123456'
                    with self.assertRaisesRegex(ValueError, 'исходную расцветку'):
                        editor.validate_settings(value)
            value = settings(design)
            value['reference_parts']['colorways'] = 1
            with self.assertRaises(ValueError):
                editor.validate_settings(value)
        for preset in editor.presets():
            if preset['settings']['race'] == 'randomium':
                value = editor.validate_settings(preset['settings'])
                self.assertTrue(all(c is None for c in value['colors'].values()))
        human = editor.default_settings()
        human['colors']['cloth'] = '#123456'
        self.assertEqual(editor.validate_settings(human)['colors']['cloth'], '#123456')

    def test_hands_have_separate_digits_relaxed_joints_and_mirrored_geometry(self):
        hands = [recipe(slot) for slot in ('left_arm', 'right_arm')]
        for r in hands:
            compile_recipe(r)
            segments = {}
            for c in r['commands']:
                anatomy = c.get('hand_anatomy', {})
                if anatomy.get('digit'):
                    segments.setdefault(anatomy['digit'], []).append(c)
            self.assertEqual({d: len(v) for d, v in segments.items()},
                             {'index': 3, 'middle': 3, 'ring': 3, 'little': 3, 'thumb': 2})
            lengths, bounds = {}, {}
            for digit, commands in segments.items():
                joints = [np.asarray(commands[0]['hand_anatomy']['joint_start'])]
                joints += [np.asarray(c['hand_anatomy']['joint_end']) for c in commands]
                lengths[digit] = sum(np.linalg.norm(c - a) for a, c in pairwise(joints))
                self.assertLess(joints[-1][2], joints[0][2] - .04)
                vertices = np.concatenate([mesh(c)[0] for c in commands])
                inward = 1 if r['commands'][0]['slot'] == 'left_arm' else -1
                bounds[digit] = ((vertices[:, 0] * inward).min(), (vertices[:, 0] * inward).max())
            self.assertGreater(lengths['middle'], lengths['ring'])
            self.assertGreater(lengths['ring'], lengths['index'])
            self.assertGreater(lengths['index'], lengths['little'])
            for a, c in zip(('little', 'ring', 'middle'), ('ring', 'middle', 'index'), strict=True):
                self.assertGreater(bounds[c][0] - bounds[a][1], .001)
            self.assertTrue(all(c['hand_anatomy']['opposed'] for c in segments['thumb']))
            # The opposed thumb starts separately in front of the metacarpus.
            thumb_root = segments['thumb'][0]['hand_anatomy']['joint_start']
            index_root = segments['index'][0]['hand_anatomy']['joint_start']
            self.assertLess(thumb_root[2] - index_root[2], -.02)
        # Badge triangulations follow each arm surface; their contacts are
        # checked separately rather than comparing internal mesh vertices.
        left = {c['part']: c for c in hands[0]['commands'] if c['part'] != 'randomium_joint_plate' and not c['part'].startswith('randomium_symbol_')}
        right = {c['part']: c for c in hands[1]['commands'] if c['part'] != 'randomium_joint_plate' and not c['part'].startswith('randomium_symbol_')}
        self.assertEqual(left.keys(), right.keys())
        for name, command in left.items():
            # Compare the complete surface, independent of triangle winding.
            a = np.round(mesh(command)[0] * [-1, 1, 1], 6)
            c = np.round(mesh(right[name])[0], 6)
            np.testing.assert_array_equal(a[np.lexsort(a.T)], c[np.lexsort(c.T)])

    def test_separation_preserves_hands_joints_torso_and_soles(self):
        previous = SOURCE.parent / 'v6'
        for design in DESIGNS:
            for slot in editor.SLOTS:
                old = json.loads((previous / design['id'] / 'parts' / (slot + '.recipe.json')).read_text())
                new = recipe(slot, design)
                for a, c in zip(old['commands'], new['commands'], strict=True):
                    if slot == 'head':
                        before, after = mesh(a)[0], mesh(c)[0]
                        np.testing.assert_allclose(after[:, (0, 2)], before[:, (0, 2)])
                        np.testing.assert_allclose(after[:, 1] - before[:, 1], new['part_separation_revision']['head_lift_metres'])
                    elif a['part'] not in {'randomium_upper_arm', 'randomium_thigh'} and not (slot.endswith('_arm') and (a['part']=='randomium_joint_plate' or a['part'].startswith('randomium_symbol_'))):
                        np.testing.assert_array_equal(mesh(a)[0], mesh(c)[0])

    def test_final_assembly_has_small_measured_gaps_for_both_head_sizes(self):
        for i in range(2):
            with self.subTest(design=i), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                manifest = editor.build(settings(i), root, weights=True)
                bounds = {slot: np.asarray(info['bounds_metres']) for slot, info in manifest['parts'].items()}
                torso = bounds['torso']
                self.assertAlmostEqual(bounds['head'][0, 1] - torso[1, 1], PART_GAP, places=6)
                self.assertAlmostEqual(torso[0, 0] - bounds['left_arm'][1, 0], PART_GAP, places=6)
                self.assertAlmostEqual(bounds['right_arm'][0, 0] - torso[1, 0], PART_GAP, places=6)
                for slot in ('left_leg', 'right_leg'):
                    self.assertAlmostEqual(torso[0, 1] - bounds[slot][1, 1], PART_GAP, places=6)
                    self.assertAlmostEqual(bounds[slot][0, 1], 0, places=6)
                assembly = json.loads((root / 'assembly.json').read_text())
                self.assertNotIn('placement', assembly)
                self.assertNotIn('calibration', assembly)
        self.assertGreater(recipe('head', DESIGNS[1])['part_separation_revision']['head_lift_metres'],
                           recipe('head', DESIGNS[0])['part_separation_revision']['head_lift_metres'])

    def test_die_counts_opposite_faces_colours_and_surface_contacts(self):
        head = recipe('head')
        compile_recipe(head)  # Closed manifolds, positive volume and nondegenerate triangles.
        pips = [c for c in head['commands'] if 'die_face' in c]
        self.assertEqual(Counter(c['die_face'] for c in pips), {i: i for i in range(1, 7)})
        faces = {tuple(normal): number for number, normal in DIE_FACES}
        for normal, number in faces.items():
            self.assertEqual(number + faces[tuple(-n for n in normal)], 7)
        center = mesh(next(c for c in head['commands'] if c['part'] == 'randomium_die_head'))[0].mean(0)
        for pip in pips:
            self.assertEqual(pip['material'], 'red' if pip['die_face'] in {1, 4} else 'ink')
            vertices, _ = mesh(pip)
            projection = (vertices - center) @ np.asarray(pip['face_normal'])
            self.assertAlmostEqual(projection.min(), .285, places=6)
            self.assertAlmostEqual(projection.max(), .289, places=6)

    def test_symbols_belong_to_the_four_joint_plates(self):
        for design, symbols in zip(DESIGNS, (JOINT_SYMBOLS, MAHJONG_SYMBOLS), strict=True):
            for slot, kind in symbols.items():
                with self.subTest(design=design['id'], slot=slot):
                    r = recipe(slot, design)
                    compile_recipe(r)
                    self.assertEqual(r['randomium_revision']['joint_symbol'], kind)
                    arm = slot.endswith('_arm')
                    joint = np.asarray(world_bind('canonical')[slot.split('_')[0] + ('_elbow' if arm else '_knee')])
                    sign = -1 if slot.startswith('left') else 1
                    normal = np.array([sign, 0, 0] if arm else [0, 0, 1])
                    plate = next(c for c in r['commands'] if c['part'] == 'randomium_joint_plate')
                    plate_vertices, _ = mesh(plate)
                    projection = (plate_vertices - joint) @ normal
                    # Elbow plates must sit laterally, away from the torso;
                    # knee plates must sit in front of their knee pivot.
                    self.assertGreater(projection.min(), .025 if arm else .08)
                    self.assertLess(projection.max(), .20 if arm else .16)
                    if arm:
                        self.assertEqual(plate['joint_attachment']['normal'], normal.tolist())
                        self.assertEqual(plate['joint_attachment']['surface'], 'lateral_elbow')
                    symbols = [c for c in r['commands'] if c['part'].startswith('randomium_symbol_')]
                    self.assertTrue(symbols)
                    for c in symbols:
                        vertices, _ = mesh(c)
                        tangent_axes = [1, 2] if arm else [0, 1]
                        self.assertTrue(np.all(vertices[:, tangent_axes] >= plate_vertices.min(0)[tangent_axes] - 1e-6))
                        self.assertTrue(np.all(vertices[:, tangent_axes] <= plate_vertices.max(0)[tangent_axes] + 1e-6))
                        self.assertGreater(((vertices - joint) @ normal).min(), .025 if arm else .10)

    def test_arm_reliefs_follow_the_plate_without_buried_or_floating_components(self):
        for design in range(2):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                editor.build(settings(design), root)
                for slot in ('left_arm', 'right_arm'):
                    sign = -1 if slot.startswith('left') else 1
                    def front_frame(command, sign=sign):
                        vertices, faces = mesh(command)
                        vertices = np.column_stack([-sign * vertices[:, 2], vertices[:, 1], sign * vertices[:, 0]])
                        return dict(command, op='indexed_mesh', vertices=vertices.tolist(), faces=faces.tolist())
                    built = json.loads((root / 'parts' / slot / 'recipe.json').read_text())
                    for r in (recipe(slot, DESIGNS[design]), built):
                        original = next(c for c in r['commands'] if c['part'] == 'randomium_joint_plate')
                        plate = front_frame(original)
                        # Check the back of the plate against the actual arm,
                        # including face interiors, not just emblem-to-plate fit.
                        support = [front_frame(c) for c in r['commands'] if c['part'] in
                                   {'randomium_elbow', 'randomium_upper_arm', 'randomium_forearm'}]
                        vertices, faces = mesh(plate)
                        template = original['surface_contact_template']
                        rear = np.isclose(np.asarray(template['vertices'])[:, 2], template['base_z'], atol=1e-9)
                        rear_faces = faces[rear[faces].all(axis=1)]
                        probes = np.concatenate([vertices[rear], vertices[rear_faces].mean(axis=1)])
                        contact = probes[:, 2] - front_depth(support, probes[:, :2])
                        self.assertTrue(np.isfinite(contact).all())
                        # The hidden rear surface seats inside the arm. No
                        # part of it should float outside the support.
                        self.assertGreaterEqual(float(contact.min()), -.012)
                        self.assertLessEqual(float(contact.max()), .0005)
                        front = np.asarray(template['vertices'])[:, 2] >= template['base_z'] + .024
                        front_faces = faces[front[faces].all(axis=1)]
                        visible = np.concatenate([vertices[front], vertices[front_faces].mean(axis=1)])
                        clearance = visible[:, 2] - front_depth(support, visible[:, :2])
                        self.assertTrue(np.isfinite(clearance).all())
                        self.assertGreater(float(clearance.min()), .001)
                        for command in r['commands']:
                            if not command['part'].startswith('randomium_symbol_'):
                                continue
                            vertices, _ = mesh(front_frame(command))
                            gap = vertices[:, 2] - front_depth([plate], vertices[:, :2])
                            self.assertTrue(np.isfinite(gap).all())
                            # Every component touches the support with only a
                            # half millimetre overlap; no glyph disappears in it.
                            self.assertAlmostEqual(float(gap.min()), -.0005, places=6)
                            self.assertLess(float(gap.max()), .025)

    def test_mahjong_head_and_shared_body_geometry(self):
        head = recipe('head', DESIGNS[1])
        positions, _, _, _ = compile_recipe(head)
        bounds = np.ptp(positions, axis=0)
        self.assertGreater(bounds[1], bounds[0])
        self.assertGreater(bounds[0], bounds[2])
        back = next(c for c in head['commands'] if c['part'] == 'randomium_mahjong_back')
        self.assertEqual(back['material'], 'jade')
        self.assertTrue(any(c['part'] == 'randomium_symbol_red-dragon' and c['material'] == 'red' for c in head['commands']))
        for slot in editor.SLOTS:
            if slot == 'head':
                continue
            bodies = []
            for design in DESIGNS:
                r = recipe(slot, design)
                r['commands'] = [c for c in r['commands'] if not c['part'].startswith('randomium_symbol_')]
                bodies.append(compile_recipe(r))
            for a, b in zip(bodies[0][:3], bodies[1][:3], strict=True):
                np.testing.assert_array_equal(a, b)

    def test_catalog_cards_preview_export_and_normalized_slot_weights(self):
        client = create_app().test_client()
        race = next(r for r in editor.catalog()['races'] if r['id'] == 'randomium')
        self.assertEqual(race['label'], 'Рандомиумы')
        self.assertEqual(race['contract'], 'humanoid_v1')
        self.assertEqual(race['gender_mode'], 'neutral')
        self.assertEqual([d['label'] for d in race['body_variants']['male']], ['Бог рандома', 'Бог маджонга'])
        self.assertEqual(race['hidden_parts'], ['belt', 'headwear', 'back', 'appearance', 'palette'])
        self.assertEqual(race['decor_options']['emblem'], EMBLEMS)
        for design in DESIGNS:
            for category in ('face', 'hair', 'outfit', 'arms', 'legs'):
                with client.get(f'/creature-workshop/constructor/cards/v28/{category}/{design["id"]}.png') as response:
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.mimetype, 'image/png')
        for i in range(2):
            with client.post('/creature-workshop/constructor/preview', json=settings(i)) as response:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(set(response.get_json()['parts']), set(editor.SLOTS))
        with zipfile.ZipFile(io.BytesIO(editor.export_bundle(settings(1)))) as bundle:
            from monster_forge_sdk.characters import read_character_model
            self.assertEqual(set(bundle.namelist()), {'assembly.json', 'model.glb'})
            assembly = json.loads(bundle.read('assembly.json'))
            self.assertEqual(assembly['skeleton_id'], 'humanoid_v1')
            self.assertEqual(set(assembly['parts']), set(editor.SLOTS))
            blob = bundle.read('model.glb')
            self.assertEqual(hashlib.sha256(blob).hexdigest(), assembly['model']['sha256'])
            model = read_character_model(blob)
            points = np.asarray(model['attributes']['POSITION'])
            weights = np.asarray(model['attributes']['WEIGHTS_0'])
            joints = np.asarray(model['attributes']['JOINTS_0'])
            self.assertTrue(np.isfinite(points).all())
            np.testing.assert_allclose(weights.sum(1), 1, atol=1e-6)
            for side, sign in (('left', -1), ('right', 1)):
                hand = (points[:,0]*sign > .65) & (points[:,1] < .90)
                self.assertTrue(hand.any())
                bone = model['metadata']['bone_palette'].index(side+'_hand')
                strength = np.sum(weights[hand]*(joints[hand]==bone), axis=1)
                np.testing.assert_allclose(strength, 1, atol=1e-6)

    def test_emblems_replace_each_other_and_contact_the_chest(self):
        client = create_app().test_client()
        for choice in EMBLEMS:
            value = settings(1)
            value['decor']['emblem'] = choice
            if choice.startswith('randomium-'):
                with client.get(f'/creature-workshop/constructor/cards/v28/emblem/{choice}.png') as response:
                    self.assertEqual(response.status_code, 200)
            with self.subTest(choice=choice), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                editor.build(value, root)
                r = json.loads((root / 'parts/torso/recipe.json').read_text())
                emblems = [c for c in r['commands'] if c.get('randomium_chest_emblem')]
                if choice == 'none':
                    self.assertFalse(emblems)
                    continue
                self.assertTrue(emblems)
                expected = 'red-dragon' if choice == 'original' else choice.removeprefix('randomium-')
                self.assertEqual({c['randomium_chest_emblem']['symbol'] for c in emblems}, {expected})
                chest = [c for c in r['commands'] if c['part'] == 'randomium_chest']
                distances = []
                for c in emblems:
                    v, _ = mesh(c)
                    distances.extend(v[:, 2] - front_depth(chest, v[:, :2]))
                self.assertTrue(np.isfinite(distances).all())
                self.assertAlmostEqual(min(distances), -.001, places=6)
                self.assertLess(max(distances), .04)

    def test_unsupported_equipment_and_other_races_emblems_are_rejected(self):
        for field, value in (('belt', 'gems'), ('headwear', 'crown'), ('emblem', 'sun')):
            s = settings()
            s['decor'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                editor.validate_settings(s)
        with self.assertRaises(ValueError):
            editor.validate_settings({**settings(), 'back': 'back-quiver'})
        human = editor.default_settings()
        human['decor']['emblem'] = 'randomium-bamboo'
        with self.assertRaises(ValueError):
            editor.validate_settings(human)

    @unittest.skipUnless(shutil.which('node'), 'Node is required to exercise the part picker')
    def test_hidden_tabs_and_emblem_availability_survive_race_switches(self):
        picker = f"import {{createPicker}} from '{Path('static/characters/constructor-picker.js').resolve().as_uri()}';"
        script = """
const assert=require('node:assert/strict');
let current={id:'randomium',owned_body:true,contract:'humanoid_v1',hidden_parts:%s};
const settings={get race(){return current.id;},form:'regular',face:'native-randomium-mahjong-god-01'};
const section={querySelectorAll:()=>[{}]};
%s
const {partAvailable}=createPicker({settings,get catalog(){return {races:[current]};}});
for(const key of ['belt','headwear','back','appearance','palette'])assert.equal(partAvailable(key,section),false);
for(const key of ['face','outfit','arms','legs','emblem'])assert.equal(partAvailable(key,section),true);
current={id:'human',contract:'humanoid_v1',hidden_parts:[]};
for(const key of ['belt','headwear','back','emblem','appearance','palette'])assert.equal(partAvailable(key,section),true);
""" % (json.dumps(HIDDEN_PARTS), picker)  # noqa: UP031 — Preserve literal JavaScript braces and $ helpers.
        subprocess.run(['node', '--input-type=module', '-e', "import {createRequire} from 'node:module';const require=createRequire(import.meta.url);\n" + script], check=True, capture_output=True, text=True)

    def test_own_body_validation_and_original_reference_provenance(self):
        for field in ('face', 'outfit', 'arms', 'legs'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                editor.validate_settings({**settings(), field: 'library-human-01'})
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in SOURCE.rglob('*') if p.is_file()}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            editor.build(settings(), root, weights=True)
            sources = json.loads((root / 'parts/head/sources.json').read_text())['sources']
            self.assertEqual(sources[0]['record']['source_character_revision'], 4)
            reference = sources[0]['reference_files'][0]
            self.assertEqual(hashlib.sha256((root / 'parts/head/reference-0-0.png').read_bytes()).hexdigest(), reference['sha256'])
        self.assertEqual(before, {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in SOURCE.rglob('*') if p.is_file()})
