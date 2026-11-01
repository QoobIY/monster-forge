"""Publish melee grip orientations in BHM while preserving mesh and pivot."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from tools.assets.asset_policy import canonical_entry
from tools.assets.calibrate_sword_grips import ROTATION, immutable

ROOT = Path(__file__).resolve().parents[2]
KINDS = {'sword', 'greatsword', 'axe', 'mace', 'scythe'}


def build():
    catalogs = {name: json.loads((ROOT / 'media' / name).read_text())
                for name in ('imported_catalog.json', 'catalog.json')}
    count = 0
    for old in list(catalogs['imported_catalog.json']['assets']):
        identity = old['id']
        if not identity.startswith('equipment.shared.') or identity.rsplit('.', 1)[1] not in KINDS:
            continue
        frame = json.loads((ROOT / 'media' / old['files']['attachment']['path']).read_text())
        if frame['grip']['rotation'] == ROTATION:
            continue
        if frame['grip']['rotation'] != [0, 0, 0, 1] or frame['grip_frame'] != 'hand':
            raise ValueError('Review nonstandard grip before calibration: ' + identity)
        revised = copy.deepcopy(frame)
        revised['grip']['rotation'] = list(ROTATION)
        revised['sockets']['grip_primary']['rotation'] = list(ROTATION)
        revision = old['revision'] + 1
        folder = ROOT / 'media/equipment/shared' / identity.split('.')[2] / identity.split('.')[3] / f'grip_revision_{revision}'
        files = copy.deepcopy(old['files'])
        files['attachment'] = immutable(folder / 'attachment.json', revised)
        files['calibration'] = immutable(folder / 'calibration.json', {
            'schema_version': 1, 'asset': identity, 'source_revision': old['revision'],
            'source_model': old['files']['model'], 'source_attachment': old['files']['attachment'],
            'grip_before': frame['grip'], 'grip_after': revised['grip'],
            'model_basis_in_hand': {'longitudinal': [0, 0, 1], 'blade_width': [0, 1, 0], 'flat_normal': [1, 0, 0]},
        })
        for name, catalog in catalogs.items():
            index = next(i for i, row in enumerate(catalog['assets']) if row['id'] == identity)
            row = catalog['assets'][index]
            if row['revision'] != old['revision'] or row['files']['model'] != old['files']['model']:
                raise ValueError('Catalogs disagree: ' + name + ': ' + identity)
            catalog['assets'][index] = canonical_entry({**row, 'revision': revision,
                                                       'files': files, 'metadata': revised})
        assert revised['grip']['position'] == frame['grip']['position']
        assert revised['grip']['scale'] == frame['grip']['scale']
        assert files['model'] == old['files']['model']
        count += 1
    for name, catalog in catalogs.items():
        path = ROOT / 'media' / name
        payload = json.dumps(catalog, ensure_ascii=False, indent=2) + '\n'
        if path.read_text() != payload:
            path.write_text(payload)
    print('Calibrated melee grips:', count)


if __name__ == '__main__':
    build()
