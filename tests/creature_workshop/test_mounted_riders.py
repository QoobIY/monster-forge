"""Published riders straddle their mounts rather than sitting above the neck."""
import json
import unittest

import numpy as np

from monsterforge.paths import ROOT
from tools.creature_workshop.geometry import compile_recipe, mesh


class MountedRiderTests(unittest.TestCase):
    def test_published_seats_and_legs_fit_each_animal(self):
        catalog = json.loads((ROOT/'media/catalog.json').read_text())
        mounted = []
        for asset in catalog['assets']:
            if 'assembly' not in asset['files']:
                continue
            record = json.loads((ROOT/'media'/asset['files']['assembly']['path']).read_text())
            if record.get('mounted_rider'):
                mounted.append((asset['id'], record))
        self.assertGreaterEqual(len(mounted), 2)
        for identity, record in mounted:
            with self.subTest(asset=identity):
                self.assertIn('mounted_rider_settings', record)
                recipe = record['parts']['torso']['recipe']
                compile_recipe(recipe)  # Includes consistent winding and positive volumes.
                seat = np.asarray(record['mounted_seat']['contact'])
                groups = {}
                for command in recipe['commands']:
                    if not command['part'].startswith('mounted_'):
                        continue
                    points, _ = mesh(command)
                    groups.setdefault(command['slot'], []).extend(points)
                self.assertTrue(groups)
                def vertices(token, recipe=recipe):
                    return np.concatenate([mesh(c)[0] for c in recipe['commands']
                                           if c['part'].startswith('mounted_') and token in c['part']])
                # Actual boot vertices: below the seat, at opposite flanks, level soles.
                boots = vertices('boot')
                for sign in (-1, 1):
                    foot = boots[boots[:, 0]*sign > .15]
                    self.assertGreater(len(foot), 0)
                    self.assertLess(foot[:, 1].max(), seat[1]-.15)
                    self.assertGreater(foot[:, 1].min(), seat[1]-.9)
                    self.assertLess(abs(np.median(foot[:, 2])-seat[2]), .35)
                # Rider is centred over the saddle, behind the animal's neck.
                head = vertices('helmet') if 'cavalry_guard' in identity else vertices('traced_reference_face')
                self.assertLess(abs((head[:, 0].max()+head[:, 0].min())*.5), .12)
                self.assertLess(abs(np.median(head[:, 2])-seat[2]), .35)
