"""Preserve legacy MoM character sources and publish act-one parts through BHM."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from tools.assets.build_catalog import build_catalog
from tools.assets.publish_character_runtime import file_ref

CHARACTERS = {
    'character.20260827t113857z-c96af2c3': 'garhold',
    'character.20260827t113039z-21ca1ba7': 'veyr',
    'character.20260827t113923z-6f9b1250': 'malgar',
    'character.20260827t114839z-d88a4419': 'kharon',
    'character.20260827t214936z-822b1b35': 'morven',
    'character.20260827t115630z-5c4a8b6b': 'skeleton-king',
    'character.20260829t193906z-121a9f7f': 'training-dummy',
}


def import_characters(source: Path, destination: Path) -> None:
    media = destination / 'media'
    archive = media / 'imported_mom/characters'
    for path in sorted((source / 'media/characters').rglob('*')):
        if not path.is_file():
            continue
        target = archive / path.relative_to(source / 'media/characters')
        blob = path.read_bytes()
        if target.exists() and target.read_bytes() != blob:
            raise ValueError(f'Immutable source conflict: {target}')
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copyfile(path, target)
    catalog_path = media / 'imported_catalog.json'
    catalog = json.loads(catalog_path.read_text())
    entries = {entry['id']: entry for entry in catalog['assets']}
    for legacy, name in CHARACTERS.items():
        record_path = archive / legacy / 'revisions/0001/record.json'
        record = json.loads(record_path.read_text())
        for part in record['composition']['parts']:
            files = {'record': file_ref(media, record_path, 'application/json')}
            for field, role, mime in (('file', 'model', 'model/gltf-binary'),
                                      ('weight_sidecar', 'weights', 'application/json')):
                ref = part[field]
                path = archive / ref['uri'].removeprefix('/media/characters/')
                result = file_ref(media, path, mime)
                if result['sha256'] != ref['sha256']:
                    raise ValueError(f'Corrupt source: {path}')
                files[role] = result
            identity = f'character.act_one.{name}.parts.{part["slot"]}'
            entry = {'id': identity, 'kind': 'character', 'title': record['title'],
                     'group': 'Акт 1', 'revision': 1, 'tags': ['humanoid_v1', 'imported'],
                     'files': files}
            if identity in entries and entries[identity] != entry:
                raise ValueError(f'Conflicting catalog entry: {identity}')
            entries[identity] = entry
    catalog['assets'] = list(entries.values())
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    build_catalog(destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--destination', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    import_characters(args.source, args.destination)
