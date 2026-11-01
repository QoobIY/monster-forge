"""Publish sword socket rotations without changing meshes or grip positions."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from tools.assets.asset_policy import canonical_entry

ROOT = Path(__file__).resolve().parents[2]
ROTATION = [-0.5, -0.5, -0.5, 0.5]


def immutable(path: Path, document: dict) -> dict:
    payload = (json.dumps(document, ensure_ascii=False, indent=2) + '\n').encode()
    if path.exists() and path.read_bytes() != payload:
        raise ValueError('Published calibration differs: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(payload)
    return {'path': path.relative_to(ROOT / 'media').as_posix(),
            'sha256': hashlib.sha256(payload).hexdigest(),
            'size_bytes': len(payload), 'media_type': 'application/json'}


def build() -> None:
    catalogs = {name: json.loads((ROOT / 'media' / name).read_text())
                for name in ('imported_catalog.json', 'catalog.json')}
    source = catalogs['imported_catalog.json']
    count = 0
    for index in range(len(source['assets'])):
        old = source['assets'][index]
        if not old['id'].startswith('equipment.shared.') or not old['id'].endswith('.sword'):
            continue
        frame = json.loads((ROOT / 'media' / old['files']['attachment']['path']).read_text())
        if frame['grip']['rotation'] == ROTATION:
            continue
        if old['revision'] != 2:
            raise ValueError('Unexpected source sword revision: ' + old['id'])
        updated = copy.deepcopy(frame)
        updated['grip']['rotation'] = list(ROTATION)
        updated['sockets']['grip_primary']['rotation'] = list(ROTATION)
        folder = ROOT / 'media/equipment/shared' / old['id'].split('.')[2] / 'sword/grip_revision_3'
        files = copy.deepcopy(old['files'])
        files['attachment'] = immutable(folder / 'attachment.json', updated)
        files['calibration'] = immutable(folder / 'calibration.json', {
            'schema_version': 1, 'asset': old['id'], 'source_revision': old['revision'],
            'source_attachment': old['files']['attachment'], 'source_model': old['files']['model'],
            'grip_before': frame['grip'], 'grip_after': updated['grip'],
            'model_basis_in_hand': {'blade': [0, 0, 1], 'edge_width': [0, 1, 0], 'flat_normal': [1, 0, 0]},
        })
        assert updated['grip']['position'] == frame['grip']['position']
        assert updated['grip']['scale'] == frame['grip']['scale']
        assert files['model'] == old['files']['model']
        for name, catalog in catalogs.items():
            row = next(i for i, asset in enumerate(catalog['assets']) if asset['id'] == old['id'])
            entry = catalog['assets'][row]
            if entry['revision'] != old['revision'] or entry['files']['model'] != old['files']['model']:
                raise ValueError('Catalogs disagree: ' + name + ': ' + old['id'])
            catalog['assets'][row] = canonical_entry({**entry, 'revision': 3, 'metadata': updated, 'files': files})
        count += 1
    for name, catalog in catalogs.items():
        path = ROOT / 'media' / name
        payload = json.dumps(catalog, ensure_ascii=False, indent=2) + '\n'
        if path.read_text() != payload:
            path.write_text(payload)
    print('Calibrated sword grips:', count)


if __name__ == '__main__':
    build()
