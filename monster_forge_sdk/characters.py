"""BHM-owned bind contracts and portable binary animation weights."""
from __future__ import annotations

import json
import math
import os
import struct
from importlib.resources import files
from pathlib import Path

from ._paths import asset_root

SKIN_MAGIC = b'MOMSKIN1'
SKIN_HEADER = struct.Struct('<8sII')
SKIN_ROW = struct.Struct('<4H4f')


def _contract_bytes(name: str, root: str | Path | None) -> bytes:
    """Explicit releases take precedence; installed SDK defaults are self-contained."""
    if root is not None or os.environ.get('MONSTER_FORGE_ASSET_ROOT') is not None:
        return (asset_root(root) / 'media/rigs' / name).read_bytes()
    resource = files('monster_forge_sdk').joinpath('_contracts', name)
    if resource.is_file():
        return resource.read_bytes()
    # Editable/source checkouts keep a single immutable copy, mapped by setuptools.
    return (asset_root() / 'media/rigs' / name).read_bytes()


def load_skeleton(profile: str = 'canonical', *, root: str | Path | None = None) -> dict:
    if profile not in {'canonical', 'workshop_knees_v1'}:
        raise ValueError(f'Unsupported humanoid bind profile: {profile}')
    data = json.loads(_contract_bytes('humanoid/' + profile + '.json', root))
    if data.get('schema_version') != 2:
        raise ValueError('Unsupported BHM skeleton contract')
    seen = set()
    for bone in data['bones']:
        if bone['id'] in seen or (bone['parent'] is not None and bone['parent'] not in seen):
            raise ValueError('Invalid BHM bone order')
        values = (*bone['bind_translation'], *bone['bind_rotation'])
        if len(values) != 7 or not all(math.isfinite(v) for v in values):
            raise ValueError('Invalid BHM bind transform')
        seen.add(bone['id'])
    return data


def _skin_components(payload: dict, *, metadata_only: bool = False) -> tuple:
    """Use the same admission rules for binary and preserved JSON weights."""
    if not isinstance(payload, dict):
        raise ValueError('Invalid skin payload')  # noqa: TRY004 -- invalid serialized data
    palette = payload.get('bone_palette')
    if not isinstance(palette, (list, tuple)) or not 0 < len(palette) <= 64:
        raise ValueError('Invalid skin bone palette')
    metadata = {k: v for k, v in payload.items() if k not in {'skin_indices', 'skin_weights'}}
    json.dumps(metadata, allow_nan=False)
    if metadata_only:
        return palette, None, None
    indices, weights = payload.get('skin_indices'), payload.get('skin_weights')
    if (not isinstance(indices, (list, tuple)) or not isinstance(weights, (list, tuple))
            or len(indices) != len(weights) or not 0 < len(indices) <= 100000):
        raise ValueError('Invalid skin dimensions')
    for ids, values in zip(indices, weights, strict=True):
        try:
            valid = (len(ids) == 4 and len(values) == 4
                     and all(type(i) is int and 0 <= i < len(palette) for i in ids)
                     and all(math.isfinite(w) and 0 <= w <= 1 for w in values)
                     and abs(sum(values) - 1) <= .001)
        except (TypeError, ValueError):
            valid = False
        if not valid:
            raise ValueError('Invalid skin influence')
    return palette, indices, weights


def encode_skin(payload: dict) -> bytes:
    _, indices, weights = _skin_components(payload)
    metadata = {k: v for k, v in payload.items() if k not in {'skin_indices', 'skin_weights'}}
    header = json.dumps(metadata, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    if not 0 < len(header) <= 65536:
        raise ValueError('Invalid binary weights metadata size')
    rows = bytearray()
    for ids, values in zip(indices, weights, strict=True):
        rows.extend(SKIN_ROW.pack(*ids, *values))
    return SKIN_HEADER.pack(SKIN_MAGIC, len(header), len(indices)) + header + rows


def decode_skin(blob: bytes, *, metadata_only: bool = False) -> dict:
    if not blob.startswith(SKIN_MAGIC):
        payload = json.loads(blob)
        _skin_components(payload)
        if metadata_only:
            return {k: v for k, v in payload.items() if k not in {'skin_indices', 'skin_weights'}}
        return payload
    if len(blob) < SKIN_HEADER.size:
        raise ValueError('Truncated binary weights')
    _, size, count = SKIN_HEADER.unpack_from(blob)
    if not 0 < count <= 100000 or not 0 < size <= 65536 or len(blob) != SKIN_HEADER.size + size + count * SKIN_ROW.size:
        raise ValueError('Invalid binary weights dimensions')
    payload = json.loads(blob[SKIN_HEADER.size:SKIN_HEADER.size + size])
    _skin_components(payload, metadata_only=True)
    if not metadata_only:
        rows = list(SKIN_ROW.iter_unpack(blob[SKIN_HEADER.size + size:]))
        payload['skin_indices'] = [list(row[:4]) for row in rows]
        payload['skin_weights'] = [list(row[4:]) for row in rows]
        _skin_components(payload)
    return payload


def body_rig(identity: str, *, root: str | Path | None = None) -> dict:
    data = json.loads(_contract_bytes('body_rigs.json', root))
    if data.get('schema_version') != 1:
        raise ValueError('Unsupported BHM body rig registry')
    try:
        return data['rigs'][identity]
    except KeyError as error:
        raise ValueError(f'Unsupported body rig: {identity}') from error


def read_character_model(blob: bytes, *, metadata_only: bool = False) -> dict:
    """Read a BHM baked GLB without importing the constructor or animation solver."""
    if len(blob) < 28 or struct.unpack_from('<4sII', blob) != (b'glTF', 2, len(blob)):
        raise ValueError('Invalid baked character GLB')
    size, kind = struct.unpack_from('<I4s', blob, 12)
    if kind != b'JSON' or size > len(blob)-28:
        raise ValueError('Invalid baked character JSON chunk')
    length, kind = struct.unpack_from('<I4s', blob, 20+size)
    if kind != b'BIN\0' or length != len(blob)-28-size:
        raise ValueError('Invalid baked character binary chunk')
    doc = json.loads(blob[20:20+size])
    binary = memoryview(blob)[28+size:]
    metadata = doc['extras']['mom_character']
    if metadata['schema_version'] != 1:
        raise ValueError('Unsupported baked character version')
    palette = metadata['bone_palette']
    bones = metadata['skeleton']['bones']
    if not 0 < len(palette) <= 64 or len(set(palette)) != len(palette) or [b['id'] for b in bones] != palette:
        raise ValueError('Invalid baked character bones')
    if len(doc['skins']) != 1 or doc['skins'][0]['joints'] != list(range(1, len(palette)+1)):
        raise ValueError('Invalid baked character skin')
    if metadata['bind_profile'] not in {'canonical', 'workshop_knees_v1'}:
        raise ValueError('Invalid baked character bind profile')
    if len(doc['nodes']) != len(palette)+1 or len(doc['meshes']) != 1:
        raise ValueError('Invalid baked character mesh')
    for i, bone in enumerate(bones, 1):
        node = doc['nodes'][i]
        if node['name'] != bone['id'] or node['translation'] != bone['bind_translation'] or node['rotation'] != bone['bind_rotation']:
            raise ValueError('Baked character bind differs from GLB joints')
    if doc.get('animations'):
        raise ValueError('Baked characters must not include animations')

    def read(index: int) -> list[list[float | int]]:
        spec = doc['accessors'][index]
        view = doc['bufferViews'][spec['bufferView']]
        width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[spec['type']]
        char = {5123: 'H', 5125: 'I', 5126: 'f'}[spec['componentType']]
        row = struct.Struct('<'+char*width)
        offset = view.get('byteOffset', 0) + spec.get('byteOffset', 0)
        stride = view.get('byteStride', row.size)
        count = spec['count']
        if not 0 < count <= 3000000 or stride < row.size or view.get('buffer', 0) or offset < 0 or offset+(count-1)*stride+row.size > len(binary):
            raise ValueError('Baked character accessor outside buffer')
        values = [list(row.unpack_from(binary, offset+i*stride)) for i in range(count)]
        if not all(math.isfinite(v) for value in values for v in value):
            raise ValueError('Nonfinite baked character attribute')
        return values

    primitive = doc['meshes'][0]['primitives'][0]
    if len(doc['meshes'][0]['primitives']) != 1 or primitive.get('mode', 4) != 4:
        raise ValueError('Baked character requires one triangle mesh')
    attrs = primitive['attributes']
    count = doc['accessors'][attrs['POSITION']]['count']
    if not 0 < count <= 100000:
        raise ValueError('Baked character vertex budget exceeded')
    metadata['vertex_count'] = count
    if metadata_only:
        return metadata
    attributes = {key: read(index) for key, index in attrs.items()}
    if any(len(values) != count for values in attributes.values()):
        raise ValueError('Baked character attribute count mismatch')
    weights = attributes['WEIGHTS_0']
    joints = attributes['JOINTS_0']
    for ids, values in zip(joints, weights, strict=True):
        if len(ids) != 4 or len(values) != 4 or any(not 0 <= i < len(palette) for i in ids) or any(not 0 <= w <= 1 for w in values) or abs(sum(values)-1) > .001:
            raise ValueError('Invalid baked character influence')
    triangles = [v[0] for v in read(primitive['indices'])]
    if len(triangles) % 3 or any(not 0 <= i < count for i in triangles):
        raise ValueError('Invalid baked character triangles')
    return {'metadata': metadata, 'attributes': attributes, 'triangles': triangles,
            'inverse_bind_matrices': read(doc['skins'][0]['inverseBindMatrices'])}
