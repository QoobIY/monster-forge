"""Migrate redundant constructor products to disposable /tmp artifacts.

Published GLBs and authoring recipes are retained. Every removed library GLB
must first reproduce its original hash from its recipe, including its header.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import shutil
import struct
import tempfile

from monster_forge_sdk import AssetStore
from monster_forge_sdk.characters import read_character_model
from monsterforge.constructor_cache import CACHE
from monsterforge.paths import ROOT
from tools.creature_workshop.geometry import compile_recipe, export_glb


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finish_integrity():
    index = ROOT / 'config/constructor_artifacts_v1.json'
    if not index.exists():
        return
    removed = json.loads(index.read_text()).get('migration', {}).get('removed', {})
    paths = {(ROOT / key).resolve() for key in removed}
    for path in (ROOT / 'media/constructor').rglob('integrity.json'):
        data = json.loads(path.read_text())
        retired = {key: value for key, value in data.get('files', {}).items() if (path.parent / key).resolve() in paths}
        if retired:
            data['schema_version'] = 2
            data['files'] = {key: value for key, value in data['files'].items() if key not in retired}
            data.setdefault('derived_files', {}).update(retired)
            pending = path.with_suffix('.next')
            pending.write_bytes(encoded(data))
            pending.replace(path)


def repair_thumbnail_sources(apply=False):
    """Repair previews incorrectly inferred as clothing during the v1 migration."""
    from monsterforge.constructor_thumbnails import selector
    index = ROOT / 'config/constructor_artifacts_v1.json'
    if not index.exists():
        return 0
    snapshot = index.read_bytes()
    data = json.loads(snapshot)
    if data.get('schema_version') != 1:
        raise ValueError('Unsupported constructor artifact schema')
    changed = 0
    for key, spec in data['artifacts'].items():
        path = ROOT / key
        if path.suffix != '.png' or spec['kind'] not in {'preview', 'card'}:
            continue
        if not any(p.is_file() for p in (path.with_suffix('.recipe.json'), path.parent / 'recipe.json')):
            continue
        expected = selector(path)
        if spec.get('recipes') == expected['recipes'] and spec['kind'] == 'preview':
            continue
        data['artifacts'][key] = {**expected, **{k: spec[k] for k in ('size', 'yaw', 'pitch') if k in spec}}
        changed += 1
    if changed and apply:
        if index.read_bytes() != snapshot:
            raise ValueError('Artifact index changed during thumbnail repair; retry')
        data.setdefault('migration', {})['thumbnail_sources_revision'] = 1
        pending = index.with_suffix('.next')
        pending.write_bytes(encoded(data))
        pending.replace(index)
    print('Thumbnail source repairs:', changed, flush=True)
    return changed


def migrate(apply=False):
    catalog_path = ROOT / 'media/catalog.json'
    catalog = json.loads(catalog_path.read_text())
    if catalog.get('constructor_storage_version') == 2:
        repair_thumbnail_sources(apply)
        if apply:
            finish_integrity()
        print('Storage v2 is already active')
        return
    store = AssetStore(ROOT)
    artifacts, obsolete, assemblies = {}, set(), []
    refs = {ref.sha256: (asset, role, ref) for asset in store.list() for role, ref in asset.files.items()}
    bodies = [asset for asset in store.list('character') if asset.id.endswith('.body')]
    instructions = {}
    published_files = set()
    active_library = set()
    from monsterforge import workshop_constructor as editor
    for donor in editor.LIBRARY_IDS | editor.SPECIES_IDS | editor.REFERENCE_IDS:
        try:
            folder = editor._folder(donor)
            manifest = json.loads((folder / 'parts.json').read_text())
            active_library.update((folder / p['model']).resolve() for p in manifest['parts'].values())
        except (ValueError, FileNotFoundError, KeyError):
            continue
    # Register current and historical finished models before retiring part files.
    for body in bodies:
        updated = json.loads(json.dumps(next(row for row in catalog['assets'] if row['id'] == body.id)))
        for role, reference in body.files.items():
            if not reference.path.endswith('.glb'):
                continue
            blob = store.read(body.id, role)
            try:
                metadata = read_character_model(blob, metadata_only=True)
            except (ValueError, KeyError):
                continue
            settings, label = None, body.title
            components = {}
            for slot, original in metadata['source_parts'].items():
                component = dict(original)
                matched = refs.get(original['model'])
                if matched:
                    asset, _, _ = matched
                    source = asset.files.get('source_model')
                    if source is not None and slot == 'torso':
                        record_path = (store.media_root / source.path).parent.parent / 'record.json'
                        if record_path.exists():
                            record = json.loads(record_path.read_text())
                            settings = record.get('constructor_settings')
                            label = record.get('label', label)
                            component['authoring_record'] = {'path': record_path.relative_to(store.media_root).as_posix(),
                                                             'sha256': digest(record_path)}
                    if 'recipe' in asset.files:
                        ref = asset.files['recipe']
                        component['recipe'] = {'path': ref.path, 'sha256': ref.sha256}
                        recipe_path = store.media_root / ref.path
                        recipe = json.loads(recipe_path.read_text())
                        if slot == 'torso':
                            settings = recipe.get('constructor', {}).get('settings')
                            record_path = recipe_path.parent.parent / 'record.json'
                            if record_path.exists():
                                record = json.loads(record_path.read_text())
                                label = record.get('label', label)
                    for name, ref in asset.files.items():
                        path = (store.media_root / ref.path).resolve()
                        if path.suffix in {'.glb', '.momskin'} or 'weights' in name:
                            if path.is_relative_to(ROOT / 'media') and not path.is_relative_to(ROOT / 'media/imported_mom'):
                                published_files.add(path)
                components[slot] = component
            data = {'schema_version': 2, 'kind': 'constructor_assembly', 'asset_id': body.id,
                    'label': label, 'constructor_settings': settings,
                    'skeleton_id': metadata['skeleton_id'], 'bind_profile': metadata['bind_profile'],
                    'parts': components,
                'model': {'path': reference.path, 'sha256': reference.sha256, 'size_bytes': reference.size_bytes},
                    'migration': {'from': 1, 'preserved_baked_model_sha256': reference.sha256}}
            relative = Path('assemblies') / hashlib.sha256(body.id.encode()).hexdigest()[:16] / (reference.sha256 + '.json')
            instructions[ROOT / 'media' / relative] = encoded(data)
            if role == 'model':
                updated['files']['assembly'] = {'path': relative.as_posix(), 'sha256': hashlib.sha256(encoded(data)).hexdigest(),
                                                 'size_bytes': len(encoded(data)), 'media_type': 'application/json'}
            else:
                updated['files']['assembly_' + reference.sha256[:24]] = {
                    'path': relative.as_posix(), 'sha256': hashlib.sha256(encoded(data)).hexdigest(),
                    'size_bytes': len(encoded(data)), 'media_type': 'application/json'}
        updated['files'] = {key: ref for key, ref in updated['files'].items() if key != 'preview'}
        assemblies.append(updated)
    print('Preserved baked characters:', len(bodies), 'finished revisions:', len(instructions), flush=True)
    # Only recipe-backed, byte-identical GLBs become rebuildable artifacts.
    with tempfile.TemporaryDirectory(prefix='forge-storage-audit-') as temporary:
        output = Path(temporary) / 'model.glb'
        candidates = sorted((ROOT / 'media/constructor').rglob('*.glb'))
        for number, path in enumerate(candidates):
            recipe_path = path.with_suffix('.recipe.json')
            if not recipe_path.exists():
                recipe_path = path.parent / 'recipe.json'
            if not recipe_path.exists():
                continue
            try:
                recipe = json.loads(recipe_path.read_text())
                export_glb(output, compile_recipe(recipe), recipe)
                original, rebuilt = path.read_bytes(), output.read_bytes()
                spec = {'kind': 'glb', 'sha256': hashlib.sha256(original).hexdigest(),
                        'recipes': [{'path': recipe_path.relative_to(ROOT).as_posix(), 'sha256': digest(recipe_path)}]}
                if rebuilt != original:
                    size = struct.unpack_from('<I', original, 12)[0]
                    new_size = struct.unpack_from('<I', rebuilt, 12)[0]
                    length = len(original) - 28 - size
                    if original[28 + size:] != rebuilt[28 + new_size:][:length]:
                        continue
                    spec.update(header=base64.b64encode(original[20:20 + size]).decode(), binary_size=length)
                artifacts[path.relative_to(ROOT).as_posix()] = spec
                obsolete.add(path)
            except (ValueError, KeyError, TypeError, IndexError):
                continue
            if number % 250 == 0:
                print('Audited library GLBs:', number + 1, '/', len(candidates), flush=True)
    # Published part copies are represented by the frozen finished GLB. Preserve
    # an active library source unless it was proven exactly reproducible above.
    obsolete.update(path for path in published_files if path.is_file() and path not in active_library)
    # Protect source images and masks mentioned by authoring provenance, even
    # when their filenames happen to resemble generated front thumbnails.
    protected_images, protected_hashes = set(), set()
    def references(value, parent, field=''):
        if isinstance(value, dict):
            for key, child in value.items():
                references(child, parent, key)
        elif isinstance(value, list):
            for child in value:
                references(child, parent, field)
        elif isinstance(value, str):
            if field in {'image_sha256', 'reference_sha256', 'mask_sha256'}:
                protected_hashes.add(value)
            if value.lower().endswith('.png') and field in {'image', 'reference_image', 'image_path', 'reference', 'mask', 'mask_path'}:
                for candidate in (parent / value, ROOT / value):
                    if candidate.exists():
                        protected_images.add(candidate.resolve())
    for path in (ROOT / 'media/constructor').rglob('*.json'):
        try:
            references(json.loads(path.read_text()), path.parent)
        except ValueError:
            continue
    # PNGs with a direct geometry recipe are derived thumbnails, not references.
    for path in (ROOT / 'media/constructor').rglob('*.png'):
        if path.name == 'reference.png' or 'reference' in str(path.parent):
            continue
        if path.resolve() in protected_images or digest(path) in protected_hashes:
            continue
        recipes = []
        same = path.with_suffix('.recipe.json')
        if same.exists():
            recipes = [same]
        elif (path.parent / 'recipe.json').exists():
            recipes = [path.parent / 'recipe.json']
        elif (path.parent / 'parts').is_dir():
            recipes = sorted((path.parent / 'parts').glob('*.recipe.json'))
            if path.stem in {'face', 'hair', 'head-front'}:
                recipes = [p for p in recipes if p.name == 'head.recipe.json']
            elif path.stem.startswith('arms'):
                recipes = [p for p in recipes if '_arm.' in p.name]
            elif path.stem.startswith('legs'):
                recipes = [p for p in recipes if '_leg.' in p.name]
        if recipes:
            spec = {'kind': 'preview', 'size': 256,
                    'recipes': [{'path': p.relative_to(ROOT).as_posix(), 'sha256': digest(p)} for p in recipes]}
        else:
            from monsterforge.constructor_thumbnails import selector
            spec = selector(path)
            if spec is None:
                continue
        artifacts[path.relative_to(ROOT).as_posix()] = spec
        obsolete.add(path)
    print('Rebuildable artifacts:', len(artifacts), 'obsolete published part files:', len(published_files), flush=True)
    print('Removing files:', len(obsolete), 'bytes:', sum(p.stat().st_size for p in obsolete), flush=True)
    report = {'schema_version': 1, 'artifacts': artifacts,
              'migration': {'from_storage_version': 1, 'to_storage_version': 2,
                            'removed': {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(obsolete)}}}
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / 'storage-migration-plan.json').write_bytes(encoded(report))
    if not apply:
        return
    backup = CACHE / 'migration-v1'
    backup.mkdir(exist_ok=True)
    for path in (catalog_path, ROOT / 'media/imported_catalog.json'):
        shutil.copy2(path, backup / path.name)
    for path, content in instructions.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() != content:
            raise ValueError('Assembly instruction collision')
        path.write_bytes(content)
    # Every removal remains recoverable during migration, solely under /tmp.
    for path in sorted(obsolete):
        destination = backup / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(path, destination)
    (ROOT / 'config/constructor_artifacts_v1.json').write_bytes(encoded(report))
    replacements = {row['id']: row for row in assemblies}
    for path in (catalog_path, ROOT / 'media/imported_catalog.json'):
        data = json.loads(path.read_text())
        data['constructor_storage_version'] = 2
        data['assets'] = [replacements.get(row['id'], row) for row in data['assets']
                          if row['kind'] != 'character' or row['id'].endswith('.body')]
        if path == catalog_path:
            present = {row['id'] for row in data['assets']}
            data['assets'].extend(row for key, row in replacements.items() if key not in present)
        present = {row['id'] for row in data['assets']}
        data['aliases'] = {key: value for key, value in data.get('aliases', {}).items()
                           if value in present}
        path.write_bytes(encoded(data))
    finish_integrity()
    repair_thumbnail_sources(apply=True)
    print('Storage v2 activated; cache and migration backup:', CACHE, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    migrate(parser.parse_args().apply)
