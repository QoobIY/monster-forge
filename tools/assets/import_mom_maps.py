"""Publish categorized immutable map props; landscape remains map-owned."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
from pathlib import Path

from tools.assets.asset_policy import REPLACEMENTS, canonical_entry, retired_model
from tools.assets.build_catalog import build_catalog

ROOT = Path(__file__).resolve().parents[2]
WEAPONS = {'hammer', 'blade', 'staff', 'bow', 'axe', 'relic', 'sword', 'greatsword', 'shield'}
GROUPS = {'equipment': 'Снаряжение', 'collision': 'Препятствия', 'sanctuary': 'Святилища',
          'nature': 'Природа', 'architecture': 'Архитектура', 'props': 'Реквизит'}


def category(name: str) -> str:
    if name in WEAPONS:
        return 'equipment'
    if name.startswith('pathing_'):
        return 'collision'
    if name.startswith('sanctuary_'):
        return 'sanctuary'
    if name in {'tree', 'flowerbed'}:
        return 'nature'
    if name in {'house_blue', 'house_warm', 'crypt_arch', 'wall', 'pillar', 'portal', 'sealed_portal', 'shop'}:
        return 'architecture'
    return 'props'


def import_maps(source: Path, destination: Path = ROOT) -> dict[str, str]:
    index = destination / 'media/imported_catalog.json'
    catalog = json.loads(index.read_text())
    by_id = {row['id']: row for row in catalog['assets']}
    by_hash = {row['files']['model']['sha256']: row['files']['model']
               for row in catalog['assets'] if 'model' in row['files']}
    bindings = {}
    roots = [source / 'media/maps/angel_arena_nova',
             *sorted((source / 'media/maps/hearthvale/stages').iterdir())]
    for root in roots:
        scope = 'angel_arena_nova' if root.name == 'angel_arena_nova' else 'hearthvale'
        assets = (json.loads((root / 'entities/assets.json').read_text()) if scope == 'angel_arena_nova'
                  else [{'id': key, **value} for key, value in json.loads((root / 'map.json').read_text())['assets'].items()])
        for asset in assets:
            if asset['kind'] != 'model' or asset.get('slot') or asset['path'].startswith('assets/forge/'):
                continue
            name = asset['id'].removeprefix('model_')
            if name.startswith('landscape_'):
                continue
            path = root / asset['path']
            payload = path.read_bytes()
            # Reject machine-local/external texture links before publishing a portable file.
            length = struct.unpack_from('<I', payload, 12)[0]
            doc = json.loads(payload[20:20 + length])
            if any('uri' in image and not image['uri'].startswith('data:') for image in doc.get('images', [])):
                raise ValueError(f'External model texture: {path}')
            checksum = hashlib.sha256(payload).hexdigest()
            group = category(name)
            identity = f'decoration.{scope}.{group}.{name}'
            if identity in REPLACEMENTS:
                bindings[path.relative_to(source / 'media/maps').as_posix()] = REPLACEMENTS[identity]
                continue
            if retired_model({'id': identity}):
                continue
            if checksum in by_hash:
                ref = by_hash[checksum]
            else:
                target = destination / 'media/decorations/maps' / scope / group / (name + '.glb')
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != checksum:
                    raise ValueError(f'Immutable model conflict: {target}')
                if not target.exists():
                    shutil.copyfile(path, target)
                ref = {'path': target.relative_to(destination / 'media').as_posix(), 'sha256': checksum,
                       'size_bytes': len(payload), 'media_type': 'model/gltf-binary'}
                by_hash[checksum] = ref
            row = {'id': identity, 'kind': 'decoration', 'title': name.replace('_', ' '),
                   'group': ('Angel Arena Nova' if scope == 'angel_arena_nova' else 'Hearthvale') + ' · ' + GROUPS[group],
                   'revision': 1, 'tags': [scope, group], 'files': {'model': ref},
                   'source_file': path.relative_to(source / 'media').as_posix(),
                   'metadata': {'category': group, 'coordinates': 'unchanged_runtime_glb', 'source_sha256': checksum}}
            previous = by_id.get(identity)
            if previous and previous['files']['model'] != ref:
                raise ValueError(f'Published asset changed: {identity}')
            if previous:
                row['files'].update({k: v for k, v in previous['files'].items() if k != 'model'})
            by_id[identity] = canonical_entry(row)
            bindings[path.relative_to(source / 'media/maps').as_posix()] = identity
    catalog['assets'] = list(by_id.values())
    index.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    build_catalog(destination)
    return bindings


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--bindings', type=Path, required=True)
    args = parser.parse_args()
    result = import_maps(args.source.resolve())
    args.bindings.write_text(json.dumps(result, indent=2) + '\n')
    print(f'Published {len(result)} map dependencies with categories and immutable geometry')
