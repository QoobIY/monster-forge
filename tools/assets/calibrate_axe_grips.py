"""Turn axe cutting edges around their shaft without moving the grip or mesh."""
from __future__ import annotations

import copy
import json

from tools.assets.build_shared_weapons import ROOT, attachment
from tools.assets.calibrate_sword_grips import immutable


def build():
    for name in ('imported_catalog.json', 'catalog.json'):
        path = ROOT / 'media' / name
        catalog = json.loads(path.read_text())
        changed = 0
        for entry in catalog['assets']:
            identity = entry['id']
            if not identity.startswith('equipment.shared.') or not identity.endswith('.axe'):
                continue
            frame = json.loads((ROOT / 'media' / entry['files']['attachment']['path']).read_text())
            expected = attachment('axe', {k: v['position'] for k, v in frame['sockets'].items()})
            if frame == expected:
                continue
            if frame['grip']['rotation'] != [-.5, -.5, -.5, .5]:
                raise ValueError('Unexpected axe grip: ' + identity)
            old = copy.deepcopy(entry)
            folder = ROOT / 'media/equipment/shared' / identity.split('.')[2] / 'axe/cutting_edge_grip_v1'
            entry['files']['attachment'] = immutable(folder / 'attachment.json', expected)
            entry['files']['calibration'] = immutable(folder / ('calibration.' + old['files']['attachment']['sha256'][:24] + '.json'), {
                'schema_version': 1, 'asset': identity,
                'source_model': old['files']['model'],
                'source_attachment': old['files']['attachment'],
                'grip_before': frame['grip'], 'grip_after': expected['grip'],
                'model_basis_in_hand': {'shaft': [0, 0, 1], 'cutting_edge': [0, -1, 0]},
            })
            entry['metadata'] = expected
            entry['revision'] += 1
            assert entry['files']['model'] == old['files']['model']
            assert expected['grip']['position'] == frame['grip']['position']
            assert expected['grip']['scale'] == frame['grip']['scale']
            changed += 1
        if changed:
            pending = path.with_suffix('.next')
            pending.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
            pending.replace(path)
        print(name, 'corrected axe grips:', changed)


if __name__ == '__main__':
    build()
