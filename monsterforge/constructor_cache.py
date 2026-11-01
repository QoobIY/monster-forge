"""Disposable constructor artifacts. The only persistent inputs are recipes."""
from __future__ import annotations

import base64
import fcntl
import hashlib
import json
import os
import re
import struct
import tempfile
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path, PurePosixPath
from threading import RLock

from .paths import ROOT, cache_directory

INDEX = ROOT / 'config/constructor_artifacts_v1.json'
CACHE = cache_directory(root=ROOT)
_INDEX_LOCK = RLock()


def artifact_index():
    try:
        info = INDEX.stat()
    except FileNotFoundError:
        return {}
    stamp = (info.st_mtime_ns, info.st_ctime_ns, info.st_size, info.st_ino)
    return _read_index(INDEX.resolve(), stamp)


@lru_cache(maxsize=1)
def _read_index(index: Path, stamp: tuple):
    return _load_index(index)['artifacts']


def _load_index(index: Path) -> dict:
    data = json.loads(index.read_text(encoding='utf-8'))
    _validate_index(data)
    return data


def _validate_index(data: dict) -> None:
    if not isinstance(data, dict) or type(data.get('schema_version')) is not int or data['schema_version'] != 1:
        raise ValueError('Unsupported constructor artifact schema; migrate the index explicitly')
    artifacts = data.get('artifacts')
    if not isinstance(artifacts, dict):
        raise ValueError('Constructor artifact index must contain an artifacts object')  # noqa: TRY004
    for key, spec in artifacts.items():
        path = PurePosixPath(key)
        if (not key or path.is_absolute() or '..' in path.parts or '\\' in key
                or key != path.as_posix() or not key.startswith('media/constructor/')):
            raise ValueError('Invalid constructor artifact path: ' + key)
        if not isinstance(spec, dict) or spec.get('kind') not in ('glb', 'preview', 'card'):
            raise ValueError('Unknown constructor artifact kind: ' + key)
        if spec['kind'] == 'glb' and not re.fullmatch(r'[0-9a-f]{64}', str(spec.get('sha256', ''))):
            raise ValueError('Invalid constructor artifact sha256: ' + key)
        if 'slot_filter' in spec and (spec['kind'] != 'glb' or not isinstance(spec['slot_filter'], str) or spec['slot_filter'] not in {'head', 'torso', 'left_arm', 'right_arm', 'left_leg', 'right_leg', 'back_attachment'}):
            raise ValueError('Invalid constructor artifact slot filter: ' + key)


@contextmanager
def _index_transaction():
    # A lock outside the source tree covers the complete read/modify/replace,
    # including independent publishing processes. Readers see atomic snapshots.
    CACHE.mkdir(parents=True, exist_ok=True)
    lock_id = hashlib.sha256(str(INDEX.resolve()).encode()).hexdigest()
    with _INDEX_LOCK, (CACHE / ('index-' + lock_id + '.lock')).open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def register(path, spec):
    """Atomically register a disposable product without changing pinned sources."""
    key = Path(path).resolve().relative_to(ROOT.resolve()).as_posix()
    _validate_index({'schema_version': 1, 'artifacts': {key: spec}})
    with _index_transaction():
        data = _load_index(INDEX) if INDEX.exists() else {'schema_version': 1, 'artifacts': {}}
        previous = data['artifacts'].get(key)
        if previous and (previous['kind'] == 'glb' or spec.get('kind') == 'glb') and previous != spec:
            raise ValueError('Immutable source needs a new recipe revision: ' + key)
        data['artifacts'][key] = spec
        _validate_index(data)
        INDEX.parent.mkdir(parents=True, exist_ok=True)
        pending = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=INDEX.parent,
                                             prefix='.' + INDEX.name + '-', delete=False) as output:
                pending = Path(output.name)
                json.dump(data, output, ensure_ascii=False, sort_keys=True, indent=2)
                output.write('\n')
                output.flush()
                os.fsync(output.fileno())
            os.replace(pending, INDEX)
            _read_index.cache_clear()
        finally:
            if pending is not None:
                pending.unlink(missing_ok=True)


def reference(path):
    return {'path': Path(path).relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def resolve(path: Path) -> Path:
    path = path.resolve()
    if path.is_file():
        return path
    if not path.is_relative_to(ROOT):
        return path
    key = path.relative_to(ROOT).as_posix()
    spec = artifact_index().get(key)
    generated_card = (path.is_relative_to(ROOT / 'media/constructor')
                      and not path.is_relative_to(ROOT / 'media/constructor/attribute_references')
                      and path.name not in {'reference.png', 'reference_parts.png', 'mask.png'})
    if spec is None and path.suffix == '.png' and generated_card:
        from .constructor_thumbnails import selector
        spec = selector(path)
    if spec is None:
        return path
    if spec['kind'] == 'card' and path.is_relative_to(ROOT / 'media/constructor/species_anatomy/v1/cards'):
        # Old selectors lost filename categories and the chosen upper-body gender.
        # Repair disposable portraits without rewriting their persistent index.
        from .constructor_thumbnails import selector
        current = selector(path)
        if current is None:
            raise ValueError('Unknown constructor card selector: ' + key)
        spec = {**current, 'selector_revision': 'category-gender-v2'}
    # UI portraits follow current derived geometry; immutable source previews
    # and GLBs retain their exact pinned recipes and hashes.
    if path.suffix == '.png' and any(folder in path.parts for folder in ('hair_review', 'attribute_portraits', 'component_cards')):
        category = path.parent.name
        if category in {'hair', 'beards', 'mustaches', 'boots'} and path.stem.isdigit():
            spec = {'kind':'card', 'category':category, 'identifier':str(int(path.stem)),
                    'gender':'female' if 'female' in path.parts else 'male', 'assembled':True}
    if spec['kind'] == 'card':
        spec = {**spec, 'geometry_revision':'component-fit-v2'}
    identity = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    target = CACHE / (identity + path.suffix)
    if target.is_file():
        if spec['kind'] != 'glb' or hashlib.sha256(target.read_bytes()).hexdigest() == spec['sha256']:
            return target
        target.unlink()
    CACHE.mkdir(parents=True, exist_ok=True)
    from tools.creature_workshop.geometry import compile_recipe, export_glb, render_png
    recipes = []
    for reference in spec.get('recipes', []):
        source = (ROOT / reference['path']).resolve()
        if not source.is_relative_to(ROOT) or hashlib.sha256(source.read_bytes()).hexdigest() != reference['sha256']:
            raise ValueError('Constructor recipe changed: ' + reference['path'])
        recipes.append(json.loads(source.read_text()))
    with tempfile.TemporaryDirectory(prefix='build-', dir=CACHE) as temporary:
        output = Path(temporary) / path.name
        if spec['kind'] == 'glb':
            recipe = recipes[0]
            if 'slot_filter' in spec:
                recipe = {**recipe, 'commands': [command for command in recipe['commands']
                                               if command['slot'] == spec['slot_filter']]}
                if not recipe['commands']:
                    raise ValueError('Constructor artifact slot is missing from its source recipe: ' + key)
            export_glb(output, compile_recipe(recipe), recipe)
            if 'header' in spec:
                blob = output.read_bytes()
                size = struct.unpack_from('<I', blob, 12)[0]
                binary = blob[28 + size:][:spec['binary_size']]
                header = base64.b64decode(spec['header'])
                output.write_bytes(struct.pack('<4sII', b'glTF', 2, 28 + len(header) + len(binary))
                                   + struct.pack('<I4s', len(header), b'JSON') + header
                                   + struct.pack('<I4s', len(binary), b'BIN\0') + binary)
            if hashlib.sha256(output.read_bytes()).hexdigest() != spec['sha256']:
                raise ValueError('Rebuilt constructor GLB differs from its source hash: ' + key)
        elif spec['kind'] == 'preview':
            import numpy as np
            arrays = [compile_recipe(r) for r in recipes]
            merged = tuple(np.concatenate([a[i] for a in arrays]) for i in range(3)) + ([],)
            render_png(output, merged, size=spec.get('size', 256), yaw=spec.get('yaw', .65), pitch=spec.get('pitch', .18))
        elif spec['kind'] == 'card':
            from .constructor_thumbnails import arrays
            render_png(output, arrays(spec), size=256)
        else:
            raise ValueError('Unknown constructor artifact kind')
        os.replace(output, target)
    return target
