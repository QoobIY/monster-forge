"""Publish map-scoped references, team masks and compact weights from BHM sources."""
from __future__ import annotations

import copy
import hashlib
import json
import re
import struct
from pathlib import Path

from monster_forge_sdk.characters import encode_skin


def character_identity(identity: str) -> tuple[str, str]:
    parts = identity.split('.')[1:]
    parts = [v for v in parts if not re.fullmatch(r'v\d+', v)]
    category = parts.pop(0)
    if category == 'angel_arena':
        scope = 'maps/angel_arena_nova'
    elif category == 'act_one':
        scope = 'maps/act_one'
    elif category in {'mom_rpg', 'mom_rpg_classes'}:
        scope = 'maps/mom_rpg'
        if category == 'mom_rpg_classes':
            parts.insert(0, 'classes')
    else:
        scope = 'shared/' + ('extra' if category == 'species_extra' else category)
    return 'character.' + scope.replace('/', '.') + '.' + '.'.join(parts), scope


def file_ref(media: Path, path: Path, mime: str) -> dict:
    blob = path.read_bytes()
    return {'path': path.relative_to(media).as_posix(), 'sha256': hashlib.sha256(blob).hexdigest(),
            'size_bytes': len(blob), 'media_type': mime}


def immutable_write(path: Path, blob: bytes) -> None:
    if path.exists():
        if path.read_bytes() != blob:
            raise ValueError(f'Published artifact changed: {path}')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob)


def team_mask_glb(blob: bytes, team_colors: tuple[str, ...] = ()) -> bytes:
    """Convert explicitly authored palette colours into an independent vertex mask.

    A colour is selected only when the record declares it for team cloth and
    does not assign the same colour to another material. No hue guessing.
    New constructor exports carry the mask directly and take precedence.
    """
    size = struct.unpack_from('<I', blob, 12)[0]
    doc = json.loads(blob[20:20 + size])
    primitives = [p for m in doc.get('meshes', []) for p in m.get('primitives', [])]
    if len(primitives) != 1:
        return blob
    attrs = primitives[0]['attributes']
    if '_TEAM_MASK' in attrs or not team_colors or 'COLOR_0' not in attrs:
        return blob
    colors = doc['accessors'][attrs['COLOR_0']]
    component = colors['componentType']
    if component not in {5121, 5123, 5126} or colors['type'] not in {'VEC3', 'VEC4'} or (component != 5126 and not colors.get('normalized')):
        return blob
    binary = bytearray(blob[28 + size:])
    view = doc['bufferViews'][colors['bufferView']]
    components = 3 if colors['type'] == 'VEC3' else 4
    offset = view.get('byteOffset', 0) + colors.get('byteOffset', 0)
    width = {5121: 1, 5123: 2, 5126: 4}[component]
    stride = view.get('byteStride', components * width)
    targets = [tuple(v / 255 for v in bytes.fromhex(c.lstrip('#'))) for c in team_colors]
    mask = []
    for row in range(colors['count']):
        color = struct.unpack_from({5121: '<3B', 5123: '<3H', 5126: '<3f'}[component], binary, offset + row * stride)
        if component != 5126:
            color = tuple(v / (255 if component == 5121 else 65535) for v in color)
        mask.append(float(any(max(abs(a-b) for a, b in zip(color, target, strict=True)) < 1.e-5 for target in targets)))
    if not any(mask):
        return blob
    start = len(binary)
    binary.extend(struct.pack('<' + 'f' * len(mask), *mask))
    doc['bufferViews'].append({'buffer': 0, 'byteOffset': start, 'byteLength': 4 * len(mask), 'target': 34962})
    attrs['_TEAM_MASK'] = len(doc['accessors'])
    doc['accessors'].append({'bufferView': len(doc['bufferViews']) - 1, 'componentType': 5126, 'count': len(mask), 'type': 'SCALAR'})
    doc['buffers'][0]['byteLength'] = len(binary)
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    return struct.pack('<4sII', b'glTF', 2, 28 + len(encoded) + len(binary)) + struct.pack('<I4s', len(encoded), b'JSON') + encoded + struct.pack('<I4s', len(binary), b'BIN\0') + binary


def publish_runtime(root: Path, data: dict) -> dict:
    media = root / 'media'
    result = copy.deepcopy(data)
    aliases = {}
    occupied = set()
    # Newest published revision gets the stable name; older geometry remains addressable.
    rows = sorted(result['assets'], key=lambda row: tuple(int(v) for v in re.findall(r'\.v(\d+)(?:\.|$)', row['id'])), reverse=True)
    assemblies = {}
    for row in rows:
        if row['kind'] == 'character' and '.parts.' in row['id']:
            source = row['id'].split('.parts.', 1)[0]
            canonical, _ = character_identity(source)
            assemblies.setdefault(canonical, source)
    for entry in rows:
        if entry['kind'] != 'character':
            continue
        old_id = entry['id']
        identity, scope = character_identity(old_id)
        source = old_id.split('.parts.', 1)[0]
        assembly, _ = character_identity(source)
        older_assembly = '.parts.' in old_id and assemblies[assembly] != source
        if older_assembly or identity in occupied:
            identity += '.archived'
        if identity in occupied:
            identity = identity.removesuffix('.archived') + '.revision_' + hashlib.sha256(old_id.encode()).hexdigest()[:12] + '.archived'
        if identity in occupied:
            raise ValueError(f'Ambiguous character migration: {old_id}')
        occupied.add(identity)
        aliases[old_id] = identity
        entry['id'] = identity
        entry['group'] = ('Карты · ' + scope.split('/')[1] if scope.startswith('maps/') else 'Общие части · ' + scope.split('/')[1])
        entry['tags'] = list(dict.fromkeys([*entry.get('tags', []), scope]))
        files = entry['files']
        model = files['model']
        source = media / model['path']
        record_path = source.parent.parent / 'record.json'
        record = json.loads(record_path.read_text()) if record_path.exists() else {}
        colors = record.get('constructor_settings', {}).get('colors', {})
        selected = colors.get('cloth')
        conflicts = {v for k, v in colors.items() if k != 'cloth' and v is not None}
        team_colors = (selected,) if selected and selected not in conflicts else ()
        blob = team_mask_glb(source.read_bytes(), team_colors)
        relative_id = identity.removeprefix('character.' + scope.replace('/', '.') + '.')
        components = relative_id.split('.')
        if 'parts' in components:
            components.remove('parts')
        directory = media / scope / 'characters' / Path(*components[:-1])
        digest = hashlib.sha256(blob).hexdigest()
        target = directory / (components[-1] + '.' + digest[:24] + '.glb')
        immutable_write(target, blob)
        files['source_model'] = model
        files['model'] = file_ref(media, target, 'model/gltf-binary')
        if 'weights' in files:
            original = files['weights']
            payload = json.loads((media / original['path']).read_bytes())
            payload['model_sha256'] = digest
            packed = encode_skin(payload)
            skin = directory / (components[-1] + '.' + hashlib.sha256(packed).hexdigest()[:24] + '.momskin')
            immutable_write(skin, packed)
            files['source_weights'] = original
            files['weights'] = file_ref(media, skin, 'application/vnd.mom.skin')
        # Published map/checkpoint hashes remain resolvable after a new revision.
        current = {ref['path'] for ref in files.values()}
        for previous in sorted(directory.glob(components[-1] + '.*')):
            if previous.suffix not in {'.glb', '.momskin'} or previous.relative_to(media).as_posix() in current:
                continue
            mime = 'model/gltf-binary' if previous.suffix == '.glb' else 'application/vnd.mom.skin'
            ref = file_ref(media, previous, mime)
            files['revision_' + ref['sha256'][:24] + previous.suffix.replace('.', '_')] = ref

    result['aliases'] = aliases
    return result
