"""Long hairstyles must cover the nape; helmet shells must clear scalp hair."""
import hashlib
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import numpy as np

from monsterforge.constructor_face_fit import surfaces
from monsterforge.constructor_headwear_fit import hair_support
from monsterforge.constructor_portraits import procedural_hair
from monsterforge.constructor_surface_fit import radial_hit, triangles
from monsterforge.mom_rpg_presets import presets
from monsterforge.workshop_constructor import _load, build, default_settings
from tools.creature_workshop.geometry import compile_recipe, mesh


class HairFitTests(unittest.TestCase):
    def test_female_orc_hairline_through_skull_vertices_has_a_closed_fitted_scalp(self):
        settings = default_settings()
        settings.update(race='orc', gender='female', face='anatomy-orc-female-01',
                        outfit='library-orc-01', arms='library-orc-01', legs='library-orc-01')
        for race, hair in (('orc', 'original'), ('orc', 'hair-orc-long-straight'),
                           ('human', 'hair-human-long-straight')):
            choices = settings if race == 'orc' else default_settings()
            with self.subTest(race=race, hair=hair), tempfile.TemporaryDirectory(prefix='forge-orc-hair-') as temporary:
                root = Path(temporary)
                build({**choices, 'hair': hair}, root)
                recipe = json.loads((root / 'parts/head/recipe.json').read_text())
                skull = surfaces(recipe)
                top = max(mesh(command)[0][:, 1].max() for command in skull)
                origin = np.array([0, top - .215, .005])
                cap = next(command for command in recipe['commands']
                           if command['part'] == 'hair_crown')
                vertices, faces = mesh(cap)
                self.assertTrue(np.isfinite(vertices).all())
                edge_directions = {}
                for face in faces:
                    self.assertEqual(len(set(face)), 3)
                    for a, b in zip(face, np.roll(face, -1), strict=True):
                        edge_directions.setdefault(tuple(sorted((int(a), int(b)))), []).append((a, b))
                for directions in edge_directions.values():
                    self.assertEqual(len(directions), 2)
                    self.assertEqual(directions[0], directions[1][::-1])
                tri = vertices[faces]
                normals = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
                self.assertTrue((np.linalg.norm(normals, axis=1) > 1e-12).all())
                self.assertGreater(np.einsum('ij,ij->i', tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum(), 0)
                half = len(vertices) // 2
                radial_normals = np.sum(normals * (tri.mean(axis=1) - origin), axis=1)
                self.assertTrue((radial_normals[np.all(faces < half, axis=1)] > 0).all())
                self.assertTrue((radial_normals[np.all(faces >= half, axis=1)] < 0).all())
                if race == 'human':
                    # Exact scalar mesh captured from the unmodified helper.
                    self.assertEqual(hashlib.sha256(vertices.astype('<f8').tobytes()
                                                   + faces.astype('<u4').tobytes()).hexdigest(),
                                     'c6f2f98c169c7a9c96be4748cd27007b1716a6d3ef2d288f791c6d36ba4b2f7f')
                    continue
                directions = vertices[:half] - origin
                directions /= np.linalg.norm(directions, axis=1)[:, None]
                skull_tri = triangles(skull)
                skin_distance = np.asarray([radial_hit(skull_tri, origin, d) for d in directions])
                np.testing.assert_allclose(np.linalg.norm(vertices[:half] - origin, axis=1) - skin_distance,
                                           .020, atol=1e-10, rtol=0)
                np.testing.assert_allclose(np.linalg.norm(vertices[half:] - origin, axis=1) - skin_distance,
                                           -.004, atol=1e-10, rtol=0)

    def test_all_long_styles_have_closed_back_curtains_with_matching_hems(self):
        for donor in ('library-human-01', 'library-human-04', 'library-orc-01'):
            recipe, _ = _load(donor, 'head')
            for style in ('long-straight', 'long-waves', 'pageboy'):
                with self.subTest(donor=donor, style=style):
                    commands, palette = procedural_hair(recipe, style)
                    rear = next(c for c in commands if c['part'] == 'hair_back_curtain')
                    vertices, faces = mesh(rear)
                    edges = Counter(tuple(sorted((int(a), int(b)))) for f in faces
                                    for a, b in zip(f, np.roll(f, -1), strict=True))
                    self.assertTrue(all(count == 2 for count in edges.values()))
                    self.assertLess(float(vertices[:, 2].min()), -.24)
                    arrays = compile_recipe({**recipe, 'palette': palette, 'commands': commands})
                    self.assertTrue(all(np.isfinite(a).all() for a in arrays[:3]))
                    for side in (-1, 1):
                        rear_side = vertices[vertices[:, 0] * side > .05]
                        self.assertGreater(len(rear_side), 0)
                        if style != 'long-waves':
                            lock = next(c for c in commands if c['part'] == 'hair_long_panel'
                                        and mesh(c)[0][:, 0].mean() * side > 0)
                            self.assertAlmostEqual(float(rear_side[:, 1].min()),
                                                   float(mesh(lock)[0][:, 1].min()))

    def test_helmet_variants_clear_scalp_and_preserve_hanging_braids(self):
        choices = next(p['settings'] for p in presets() if p['id'] == 'classes/viking')
        for kind in ('horned_helmet', 'winged_helmet', 'crested_helmet', 'barbute', 'closed_helmet'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                settings = {**choices, 'decor': {**choices['decor'], 'headwear': kind}}
                build(settings, root)
                recipe = json.loads((root / 'parts/head/recipe.json').read_text())
                scalp = [c for c in hair_support(recipe) if c['part'] == 'hair_crown']
                shell = [c for c in recipe['commands'] if c['part'] == 'equipment_helmet_shell']
                self.assertTrue(scalp and shell)
                skull_tri, shell_tri = triangles(scalp), triangles(shell)
                base = float(np.concatenate([mesh(c)[0] for c in shell])[:, 1].min())
                top = float(np.concatenate([mesh(c)[0] for c in scalp])[:, 1].max())
                for y in np.linspace(base + .04, top - .01, 6):
                    for angle in np.linspace(-np.pi, np.pi, 16, endpoint=False):
                        direction = np.array([np.sin(angle), 0, np.cos(angle)])
                        point = np.array([0, y, .0095])
                        hair = radial_hit(skull_tri, point, direction)
                        metal = radial_hit(shell_tri, point, direction)
                        if hair is not None:
                            self.assertIsNotNone(metal)
                            self.assertGreater(metal - hair, .003)
                open_settings = {**choices, 'decor': {**choices['decor'], 'headwear': 'none'}}
                build(open_settings, root / 'open')
                before = json.loads((root / 'open/parts/head/recipe.json').read_text())
                braids = lambda r: [mesh(c)[0] for c in r['commands'] if c['part'] == 'braid_lobe']
                self.assertEqual(len(braids(recipe)), len(braids(before)))
                for a, b in zip(braids(recipe), braids(before), strict=True):
                    if float(b[:, 1].min()) < base - .02:
                        np.testing.assert_array_equal(a, b)


if __name__ == '__main__':
    unittest.main()
