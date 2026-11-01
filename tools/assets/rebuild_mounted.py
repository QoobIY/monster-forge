"""Rebuild mounted constructor publications from their saved mount/rider choices."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from monsterforge.paths import ROOT
from tools.assets import build_mom_skins as skins


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asset', action='append', default=[])
    args = parser.parse_args()
    catalog = json.loads((ROOT / 'media/catalog.json').read_text())
    selected = []
    for asset in catalog['assets']:
        if 'assembly' not in asset['files']:
            continue
        record = json.loads((ROOT / 'media' / asset['files']['assembly']['path']).read_text())
        if record.get('mounted_rider') and (not args.asset or asset['id'] in args.asset):
            selected.append((asset, record))
    if args.asset and set(args.asset) != {asset['id'] for asset, _ in selected}:
        raise ValueError('Requested asset is not a mounted constructor publication')
    for asset, record in selected:
        identity = asset['id'].removeprefix('character.').removesuffix('.body')
        scope, name = identity.rsplit('.', 1)
        skins.DESTINATION = ROOT / 'media/constructor' / scope.replace('.', '/')
        choices = record['constructor_settings']
        animal = choices['race'].removeprefix('beast-')
        with tempfile.TemporaryDirectory(prefix='bhm-mounted-') as temporary:
            stage = Path(temporary)
            result = skins.publish_quadruped(
                name, asset['title'], animal, stage/'mount', stage/'rider',
                rider_settings=record['mounted_rider_settings'], mount_settings=choices,
                identity=asset['id'].removesuffix('.body'))
        print(result['id'], flush=True)


if __name__ == '__main__':
    main()
