"""Bake immutable, self-contained character GLBs; source parts stay editable."""
from __future__ import annotations

import hashlib
import io
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image

from monster_forge_sdk import AssetStore
from monster_forge_sdk.characters import body_rig, decode_skin, load_skeleton
from tools.assets.publish_character_runtime import file_ref, immutable_write


def unpack(blob: bytes) -> tuple[dict, bytes]:
    if len(blob) < 28 or struct.unpack_from('<4sII', blob) != (b'glTF', 2, len(blob)):
        raise ValueError('Invalid source GLB')
    size, kind = struct.unpack_from('<I4s', blob, 12)
    if kind != b'JSON' or blob[24 + size:28 + size] != b'BIN\0':
        raise ValueError('Invalid source GLB chunks')
    return json.loads(blob[20:20 + size]), blob[28 + size:]


def accessor(doc: dict, binary: bytes, index: int) -> np.ndarray:
    spec = doc['accessors'][index]
    view = doc['bufferViews'][spec['bufferView']]
    dtype = {5121: '<u1', 5123: '<u2', 5125: '<u4', 5126: '<f4'}[spec['componentType']]
    width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[spec['type']]
    offset = view.get('byteOffset', 0) + spec.get('byteOffset', 0)
    unit = np.dtype(dtype).itemsize
    values = np.ndarray((spec['count'], width), dtype, buffer=binary, offset=offset,
                        strides=(view.get('byteStride', width * unit), unit)).copy()
    if spec.get('normalized'):
        values = values.astype(np.float32) / np.iinfo(dtype).max
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite source attribute')
    return values


def bone_matrices(skeleton: dict) -> list[np.ndarray]:
    matrices, names = [], {}
    for bone in skeleton['bones']:
        x, y, z, w = bone['bind_rotation']
        rotation = np.array([
            [1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
            [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
            [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
        matrix = np.eye(4)
        matrix[:3, :3] = rotation
        matrix[:3, 3] = bone['bind_translation']
        if bone['parent'] is not None:
            matrix = matrices[names[bone['parent']]] @ matrix
        names[bone['id']] = len(matrices)
        matrices.append(matrix)
    return matrices


def bake(store: AssetStore, identity: str, selection: dict[str, str] | None = None, *, allow_optional_parts: bool = False) -> bytes:
    parts = ([store.get(key) for key in selection.values()] if selection is not None else
             [entry for entry in store.list() if entry.id.startswith(identity + '.parts.')
              and not entry.id.endswith('.archived') and 'weights' in entry.files])
    if not parts:
        raise ValueError('No character parts: ' + identity)
    payloads = [(entry, decode_skin(store.read(entry.id, 'weights'))) for entry in parts]
    profiles = {p.get('bind_profile', 'canonical') for _, p in payloads}
    rigs = {p['skeleton_id'] for _, p in payloads}
    if len(profiles) != 1 or len(rigs) != 1:
        raise ValueError('Mixed character bind profiles: ' + identity)
    profile, rig = profiles.pop(), rigs.pop()
    gaits = {payload.get('gait', 'walk') for _, payload in payloads}
    if len(gaits) != 1:
        raise ValueError('Mixed body locomotion profiles')
    gait = gaits.pop()
    if gait not in {'walk', 'hop'} or (gait == 'hop' and rig != 'quadruped_v1'):
        raise ValueError('Unsupported body locomotion profile')

    contract = body_rig(rig, root=store.root)
    slots = [slot['id'] for slot in contract['slots']]
    selected = {p['slot']: (entry, p) for entry, p in payloads}
    if allow_optional_parts and 'back_attachment' in selected and 'back_attachment' not in slots:
        slots.append('back_attachment')
    if (set(selected) != set(slots) or len(selected) != len(parts)
            or (selection is not None and any(selected[slot][0].id != key for slot, key in selection.items()))):
        raise ValueError('Incomplete or duplicate character slots: ' + identity)
    skeleton = load_skeleton(profile, root=store.root) if rig == 'humanoid_v1' else contract
    names = [bone['id'] for bone in skeleton['bones']]
    geometry, images, provenance, palms, sockets, samplers = [], {}, {}, {}, {}, {}
    for slot in slots:
        entry, skin = selected[slot]
        model = store.read(entry.id, 'model')
        if skin['model_sha256'] != hashlib.sha256(model).hexdigest():
            raise ValueError('Weights differ from source model: ' + entry.id)
        doc, binary = unpack(model)
        primitive = doc['meshes'][0]['primitives'][0]
        attributes = {name: accessor(doc, binary, value)
                      for name, value in primitive['attributes'].items()}
        positions = attributes['POSITION']
        count = len(positions)
        if len(skin['skin_weights']) != count:
            raise ValueError('Source weights count mismatch')
        palette = np.array([names.index(name) for name in skin['bone_palette']], dtype=np.uint16)
        joints = palette[np.asarray(skin['skin_indices'], dtype=np.uint16)]
        weights = np.asarray(skin['skin_weights'], dtype=np.float32)
        indices = (accessor(doc, binary, primitive['indices']).reshape(-1).astype(np.uint32)
                   if 'indices' in primitive else np.arange(count, dtype=np.uint32))
        normals = attributes.get('NORMAL')
        if normals is None:
            normals = np.zeros((count, 3), dtype=np.float32)
            for triangle in indices.reshape(-1, 3):
                a, b, c = positions[triangle]
                normal = np.cross(b-a, c-a)
                length = np.linalg.norm(normal)
                if length:
                    normal /= length
                normals[triangle] += normal
            normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1.e-12)
        colors = attributes.get('COLOR_0', np.ones((count, 4), dtype=np.float32))
        if colors.shape[1] == 3:
            colors = np.column_stack((colors, np.ones(count)))
        material = doc.get('materials', [{}])[primitive.get('material', 0)]
        pbr = material.get('pbrMetallicRoughness', {})
        colors = colors * np.asarray(pbr.get('baseColorFactor', [1, 1, 1, 1]))
        uv = attributes.get('TEXCOORD_0', np.zeros((count, 2), dtype=np.float32))
        texture = None
        if 'baseColorTexture' in pbr:
            texture_spec = doc['textures'][pbr['baseColorTexture']['index']]
            image = doc['images'][texture_spec['source']]
            view = doc['bufferViews'][image['bufferView']]
            offset = view.get('byteOffset', 0)
            raw = binary[offset:offset + view['byteLength']]
            texture = hashlib.sha256(raw).hexdigest()
            images.setdefault(texture, Image.open(io.BytesIO(raw)).convert('RGBA'))
            sampler = doc.get('samplers', [{}])[texture_spec.get('sampler', 0)]
            values = {key: sampler.get(key, default) for key, default in (('wrapS', 10497), ('wrapT', 10497), ('magFilter', 9729), ('minFilter', 9987))}
            if texture in samplers and samplers[texture] != values:
                raise ValueError('Conflicting sampler settings: '+entry.id)
            samplers[texture] = values
            if (uv < -64).any() or (uv > 64).any():
                raise ValueError('Source UV budget exceeded: '+entry.id)
        if slot.endswith('_arm'):
            hand = slot.removesuffix('_arm')
            if skin.get('hand_socket') is not None:
                palms[hand] = skin['hand_socket']
            if hand + '_hand' in names:
                bone = names.index(hand + '_hand')
                influence = np.sum(weights * (joints == bone), axis=1)
                anchor = np.where(influence >= .65, influence, 0)
                if not anchor.sum() and influence.max() > 1.e-8:
                    anchor[influence.argmax()] = 1
                if anchor.sum():
                    anchor /= anchor.sum()
                    points = np.zeros((len(names), 4))
                    homogeneous = np.column_stack((positions, np.ones(count)))
                    for j in range(4):
                        np.add.at(points, joints[:, j], homogeneous * (anchor * weights[:, j])[:, None])
                    sockets[slot] = points.tolist()
        geometry.append((positions, normals, colors, uv, texture, joints, weights,
                         attributes.get('_TEAM_MASK', np.zeros((count, 1))), slot, indices))
        provenance[slot] = {'asset': entry.id, 'model': entry.files['model'].sha256,
                            'weights': entry.files['weights'].sha256}
    direct_texture = len(images) == 1 and all(item[4] is not None for item in geometry)
    atlas, boxes = None, {}
    if direct_texture:
        atlas = next(iter(images.values()))
    if images and not direct_texture:
        images['white'] = Image.new('RGBA', (1, 1), 'white')
        # Shelf packing with edge padding preserves the original texel resolution.
        x = y = row_height = 0
        for key, image in sorted(images.items()):
            width, height = image.size
            if width + 4 > 2048 or height + 4 > 2048:
                raise ValueError('Source image exceeds atlas budget')
            if x + width + 4 > 2048:
                x, y, row_height = 0, y + row_height, 0
            boxes[key] = (x + 2, y + 2, width, height)
            x += width + 4
            row_height = max(row_height, height + 4)
        height = y + row_height
        if height > 2048:
            raise ValueError('Character atlas exceeds 2048px')
        atlas = Image.new('RGBA', (2048, height))
        for key, image in images.items():
            x, y, width, height = boxes[key]
            atlas.paste(image, (x, y))
            atlas.paste(image.crop((0, 0, 1, height)).resize((2, height)), (x-2, y))
            atlas.paste(image.crop((width-1, 0, width, height)).resize((2, height)), (x+width, y))
            atlas.paste(image.crop((0, 0, width, 1)).resize((width, 2)), (x, y-2))
            atlas.paste(image.crop((0, height-1, width, height)).resize((width, 2)), (x, y+height))
    doc = {'asset': {'version': '2.0', 'generator': 'BHM character bake v1'},
           'buffers': [{}], 'bufferViews': [], 'accessors': [], 'meshes': [], 'nodes': [],
           'scene': 0, 'scenes': [], 'extras': {'mom_character': {
               'schema_version': 1, 'skeleton_id': rig, 'bind_profile': profile,
               'bone_palette': names, 'skeleton': skeleton, 'hand_sockets': palms,
               'socket_points': sockets, 'source_parts': provenance}}}
    if gait != 'walk':
        doc['extras']['mom_character']['gait'] = gait
    binary = bytearray()

    def append(values, component, shape, *, bounds=False):
        nonlocal binary
        values = np.asarray(values, dtype={5126: '<f4', 5123: '<u2', 5125: '<u4'}[component])
        binary.extend(b'\0' * (-len(binary) % 4))
        start = len(binary)
        binary.extend(values.tobytes())
        view = len(doc['bufferViews'])
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': start, 'byteLength': values.nbytes})
        spec = {'bufferView': view, 'componentType': component, 'count': len(values), 'type': shape}
        if bounds:
            spec.update(min=values.min(axis=0).tolist(), max=values.max(axis=0).tolist())
        doc['accessors'].append(spec)
        return len(doc['accessors']) - 1
    streams = {name: [] for name in ('POSITION', 'NORMAL', 'COLOR_0', 'JOINTS_0',
                                     'WEIGHTS_0', '_TEAM_MASK', '_MOM_LBS', 'TEXCOORD_0')}
    triangles, offset = [], 0
    for positions, normals, colors, uv, texture, joints, weights, mask, slot, indices in geometry:
        for name, values in (('POSITION', positions), ('NORMAL', normals), ('COLOR_0', colors),
                             ('JOINTS_0', joints), ('WEIGHTS_0', weights), ('_TEAM_MASK', mask),
                             ('_MOM_LBS', np.full((len(positions), 1), float(slot.endswith('_arm'))))):
            streams[name].append(values)
        if atlas and not direct_texture:
            if (uv < 0).any() or (uv > 1).any():
                raise ValueError("Multi-image repeating UVs need a dedicated atlas: "+identity)
            x, y, width, height = boxes[texture or 'white']
            uv = uv.copy() if texture else np.full((len(positions), 2), .5)
            uv[:, 0] = (x + uv[:, 0] * width) / atlas.width
            uv[:, 1] = (y + uv[:, 1] * height) / atlas.height
        if atlas:
            streams['TEXCOORD_0'].append(uv)
        triangles.append(indices + offset)
        offset += len(positions)
    attrs = {}
    for name, values in streams.items():
        if values:
            values = np.concatenate(values)
            attrs[name] = append(values, 5123 if name == 'JOINTS_0' else 5126,
                                 {1: 'SCALAR', 2: 'VEC2', 3: 'VEC3', 4: 'VEC4'}[values.shape[1]],
                                 bounds=name == 'POSITION')
    primitive = {'attributes': attrs, 'indices': append(np.concatenate(triangles), 5125, 'SCALAR'), 'mode': 4, 'material': 0}
    doc['materials'] = [{'pbrMetallicRoughness': {'baseColorFactor': [1, 1, 1, 1],
                                               'metallicFactor': 0, 'roughnessFactor': 1}, 'doubleSided': False}]
    if atlas:
        stream = io.BytesIO()
        atlas.save(stream, format='PNG')
        binary.extend(b'\0' * (-len(binary) % 4))
        doc['images'] = [{'bufferView': len(doc['bufferViews']), 'mimeType': 'image/png'}]
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(stream.getvalue())})
        binary.extend(stream.getvalue())
        doc['textures'] = [{'source': 0, 'sampler': 0}]
        if direct_texture:
            doc['samplers'] = [next(iter(samplers.values()))]
        else:
            filters = {(v['magFilter'], v['minFilter']) for v in samplers.values()}
            if len(filters) != 1:
                raise ValueError('Mixed atlas filtering needs separate materials: '+identity)
            mag, minimum = filters.pop()
            doc['samplers'] = [{'wrapS': 33071, 'wrapT': 33071, 'magFilter': mag, 'minFilter': minimum}]
        doc['materials'][0]['pbrMetallicRoughness']['baseColorTexture'] = {'index': 0}
    doc['meshes'] = [{'name': identity, 'primitives': [primitive]}]
    doc['nodes'] = [{'name': identity, 'mesh': 0, 'skin': 0}]
    roots = [0]
    for index, bone in enumerate(skeleton['bones']):
        doc['nodes'].append({'name': bone['id'], 'translation': bone['bind_translation'],
                             'rotation': bone['bind_rotation']})
        if bone['parent'] is None:
            roots.append(index+1)
        else:
            doc['nodes'][names.index(bone['parent'])+1].setdefault('children', []).append(index+1)
    matrices = np.array([np.linalg.inv(matrix).T.reshape(16) for matrix in bone_matrices(skeleton)])
    doc['skins'] = [{'joints': list(range(1, len(names)+1)), 'inverseBindMatrices': append(matrices, 5126, 'MAT4')}]
    doc['scenes'] = [{'nodes': roots}]
    binary.extend(b'\0' * (-len(binary) % 4))
    doc['buffers'][0]['byteLength'] = len(binary)
    raw = json.dumps(doc, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    raw += b' ' * (-len(raw) % 4)
    return struct.pack('<4sII', b'glTF', 2, 28+len(raw)+len(binary)) + struct.pack('<I4s', len(raw), b'JSON') + raw + struct.pack('<I4s', len(binary), b'BIN\0') + binary


def publish(root: Path, data: dict | None = None) -> dict:
    path = root/'media/catalog.json'
    previous = json.loads(path.read_text()) if path.exists() else {'assets': []}
    catalog = {**previous, **(data or {})}
    catalog['aliases'] = {**previous.get('aliases', {}), **catalog.get('aliases', {})}
    entries = {entry['id']: entry for entry in catalog['assets']}
    # Published immutable assets remain addressable after a source catalog rebuild.
    assemblies = {key.split('.parts.', 1)[0] for key in entries if '.parts.' in key}
    for entry in previous['assets']:
        key = entry['id']
        # A newer complete assembly owns its slot set, including removed slots.
        # Re-adding old canonical limbs here can combine incompatible skeletons.
        if '.parts.' in key and key.split('.parts.', 1)[0] in assemblies and key not in entries:
            replacement = next((row['id'] for row in entries.values()
                                if row['id'].startswith(key.split('.parts.', 1)[0] + '.parts.')
                                and row['id'].endswith('.archived')
                                and row['files']['model']['sha256'] == entry['files']['model']['sha256']), None)
            if replacement:
                catalog['aliases'].setdefault(key, replacement)
            continue
        entries.setdefault(key, entry)
    catalog['assets'] = list(entries.values())
    store = AssetStore(root, catalog=json.dumps(catalog).encode())
    identities = sorted({entry.id.rsplit('.parts.', 1)[0] for entry in store.list()
                         if '.parts.' in entry.id and 'weights' in entry.files
                         and not entry.id.endswith('.archived')})
    published = 0
    for identity in identities:
        parts = [entry for entry in store.list()
                 if entry.id.startswith(identity+'.parts.') and 'weights' in entry.files
                 and not entry.id.endswith('.archived')]
        rig = decode_skin(store.read(parts[0].id, 'weights')).get('skeleton_id')
        # Catalogs may publish individual legacy parts without a complete assembly.
        if rig is None:
            continue
        required = {slot['id'] for slot in body_rig(rig, root=root)['slots']}
        if not required.issubset({entry.id.rsplit('.', 1)[1] for entry in parts}):
            continue
        blob = bake(store, identity)
        digest = hashlib.sha256(blob).hexdigest()
        relative = identity.removeprefix('character.').split('.')
        target = root/'media'/Path(*relative[:2])/'characters'/Path(*relative[2:])/('body.'+digest[:24]+'.glb')
        immutable_write(target, blob)
        key = identity+'.body'
        previous = entries.get(key)
        files = dict(previous['files']) if previous else {}
        if previous and previous['files']['model']['sha256'] != digest:
            old = previous['files']['model']
            files['revision_'+old['sha256'][:24]] = old
        files['model'] = file_ref(root/'media', target, 'model/gltf-binary')
        preview = store.get(identity+'.parts.torso').files.get('preview')
        if preview is not None:
            files['preview'] = {'path': preview.path, 'sha256': preview.sha256,
                                'size_bytes': preview.size_bytes, 'media_type': preview.media_type}
        entries[key] = {'id': key, 'kind': 'character', 'title': identity+' (baked)',
                        'revision': (previous['revision'] + (previous['files']['model']['sha256'] != digest)) if previous else 1,
                        'group': 'Runtime characters', 'tags': ['baked', 'rigged', 'no-animation'], 'files': files}
        published += 1
    catalog['assets'] = list(entries.values())
    temporary = root/'media/catalog.json.next'
    temporary.write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+'\n')
    temporary.replace(root/'media/catalog.json')
    return {'characters': published}


if __name__ == '__main__':
    print(publish(Path(__file__).resolve().parents[2]))
