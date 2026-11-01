"""Add slot-bounded animation weights to existing immutable humanoid parts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from monsterforge.skin_weights import build_weight_sidecar
from tools.assets.build_catalog import build_catalog

SLOTS = ('head', 'torso', 'left_arm', 'right_arm', 'left_leg', 'right_leg')


def prepare_set(folder: Path) -> int:
    folder = folder.resolve()
    if not folder.is_relative_to((ROOT / 'media/constructor').resolve()):
        raise ValueError('Humanoid sets must belong to the BHM constructor library')
    record = json.loads((folder / 'record.json').read_bytes())
    if record.get('rig') != 'humanoid_v1':
        raise ValueError('Only existing humanoid_v1 sets are supported')
    prepared = []
    for slot in SLOTS:
        model = folder / record['parts'][slot]['model']
        recipe = json.loads(model.with_suffix('.recipe.json').read_bytes())
        profiles = {c['knee_bind_revision']['profile'] for c in recipe.get('commands', [])
                    if 'knee_bind_revision' in c}
        profile = recipe.get('bind_profile') or (next(iter(profiles)) if profiles else 'canonical')
        if profiles and profiles != {profile}:
            raise ValueError('Mixed bind contracts require an explicit asset migration')
        payload = build_weight_sidecar(model, slot, bind_profile=profile)
        if profile != 'canonical':
            raise ValueError('This release needs canonical game bind coordinates')
        original = payload['bone_palette']
        palette = [bone for bone in original if bone in payload['allowed_bones']]
        remap = {index: palette.index(bone) for index, bone in enumerate(original) if bone in palette}
        payload['skin_indices'] = [[remap[index] if weight > 0 else 0
                                    for index, weight in zip(row, weights, strict=True)]
                                   for row, weights in zip(payload['skin_indices'], payload['skin_weights'], strict=True)]
        payload['bone_palette'] = palette
        payload['bind_profile'] = profile
        payload['publication'] = 'existing_bhm_geometry_mom_runtime_v1'
        prepared.append((model.with_suffix('.weights.json'), payload))
    # All six parts must be compatible before any sidecar is published.
    for path, payload in prepared:
        encoded = json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n'
        if path.exists() and path.read_text() != encoded:
            raise ValueError(f'Published weights changed: {path}; create an explicit new revision')
    for path, payload in prepared:
        if not path.exists():
            path.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n')
    return len(prepared)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sets', nargs='+', type=Path)
    args = parser.parse_args()
    total = sum(prepare_set(folder) for folder in args.sets)
    build_catalog()
    print(f'Prepared {total} existing humanoid part weights; catalog updated')
