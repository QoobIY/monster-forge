"""Publish a constructor instruction and its single finished model."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile

from monsterforge.paths import ROOT
from monsterforge.character_assembly import encoded
from monsterforge.workshop_constructor import _compact_assembly


def publish(identity: str, label: str, settings: dict):
    if not identity.startswith('character.') or identity.endswith('.body') or '/' in identity or '..' in identity:
        raise ValueError('Invalid character assembly identity')
    with tempfile.TemporaryDirectory(prefix='forge-publish-') as temporary:
        instruction, model = _compact_assembly(settings, Path(temporary))
    return publish_model(identity, label, instruction, model)


def publish_model(identity: str, label: str, instruction: dict, model: bytes):
    if not identity.startswith('character.') or identity.endswith('.body') or '/' in identity or '..' in identity:
        raise ValueError('Invalid character assembly identity')
    digest = hashlib.sha256(model).hexdigest()
    directory = ROOT / 'media/assemblies' / hashlib.sha256(identity.encode()).hexdigest()[:16]
    directory.mkdir(parents=True, exist_ok=True)
    model_path = directory / ('body.' + digest[:24] + '.glb')
    instruction.update(asset_id=identity + '.body', label=label)
    instruction['model']['path'] = model_path.relative_to(ROOT / 'media').as_posix()
    instruction.pop('id', None)
    recipe_path = directory / (digest + '.json')
    for path, blob in ((model_path, model), (recipe_path, encoded(instruction))):
        if path.exists() and path.read_bytes() != blob:
            raise ValueError('Immutable finished assembly changed')
        path.write_bytes(blob)
    catalog_path = ROOT / 'media/catalog.json'
    catalog = json.loads(catalog_path.read_text())
    previous = next((a for a in catalog['assets'] if a['id'] == identity + '.body'), None)
    files = dict(previous['files']) if previous else {}
    if previous and previous['files']['model']['sha256'] != digest:
        old = previous['files']['model']
        files['revision_' + old['sha256'][:24]] = old
        if 'assembly' in files:
            files['assembly_' + old['sha256'][:24]] = files['assembly']
    for role, path, mime in (('model', model_path, 'model/gltf-binary'), ('assembly', recipe_path, 'application/json')):
        blob = path.read_bytes()
        files[role] = {'path': path.relative_to(ROOT / 'media').as_posix(), 'sha256': hashlib.sha256(blob).hexdigest(),
                       'size_bytes': len(blob), 'media_type': mime}
    entry = {'id': identity + '.body', 'kind': 'character', 'title': label,
             'revision': (previous['revision'] + int(previous['files']['model']['sha256'] != digest)) if previous else 1,
             'group': 'Constructor assemblies', 'tags': ['baked', 'rigged'], 'files': files}
    catalog['constructor_storage_version'] = 2
    catalog['assets'] = [a for a in catalog['assets'] if a['id'] != entry['id']] + [entry]
    pending = catalog_path.with_suffix('.next')
    pending.write_bytes(encoded(catalog))
    pending.replace(catalog_path)
    return entry
