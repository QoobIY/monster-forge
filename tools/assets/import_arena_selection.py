"""Publish reviewed Arena humanoids in BHM without rebuilding their appearance."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import struct
import zlib
from pathlib import Path

import numpy as np
import trimesh
from tools.assets.build_catalog import build_catalog

from machine_of_monsters.animation.core import HUMANOID_SLOT_BONES, load_skeleton

ROOT = Path(__file__).resolve().parents[2]
SLOTS = ('head', 'torso', 'left_arm', 'right_arm', 'left_leg', 'right_leg')


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))+'\n').encode()


def immutable(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f'Published asset changed: {path}')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def decode_skin(source, part):
    data = json.loads((source/part['skin']).read_text())
    indices = np.frombuffer(zlib.decompress(base64.b64decode(data['indices'])), dtype=np.uint8).reshape(-1, 4)
    weights = np.frombuffer(zlib.decompress(base64.b64decode(data['weights'])), dtype='<u2').reshape(-1, 4).astype(float)/65535
    assert len(indices) == data['vertex_count']
    weights /= weights.sum(axis=1, keepdims=True)
    return data['bone_palette'], indices, weights


def publish(source, entry, component):
    output = ROOT/'media/constructor/angel_arena/v2'/entry['id']
    skeleton_digest = hashlib.sha256(encode(load_skeleton(component['bind_profile'])).rstrip()).hexdigest()
    for slot in SLOTS:
        part = component['parts'][slot]
        original = source/part['model']
        model_bytes = original.read_bytes()
        palette, indices, weights = decode_skin(source, part)
        if slot == 'torso' and 'back_attachment' in component['parts']:
            back = component['parts']['back_attachment']
            # Both primitives keep their original unmerged vertices and COLOR_0.
            meshes = [trimesh.load(source/p['model'], force='mesh', process=False) for p in (part, back)]
            joined = trimesh.util.concatenate(meshes)
            np.testing.assert_array_equal(joined.vertices, np.concatenate([m.vertices for m in meshes]))
            model_bytes = joined.export(file_type='glb')
            length = struct.unpack_from('<I', model_bytes, 12)[0]
            document = json.loads(model_bytes[20:20+length])
            document['nodes'] = [{'mesh': 0}]
            document['scenes'] = [{'nodes': [0]}]
            document['scene'] = 0
            payload = encode(document).rstrip()
            payload += b' '*(-len(payload) % 4)
            binary_chunk = model_bytes[20+length:]
            model_bytes = (struct.pack('<III', 0x46546C67, 2, 20+len(payload)+len(binary_chunk))
                           +struct.pack('<II', len(payload), 0x4E4F534A)+payload+binary_chunk)
            back_palette, back_indices, back_weights = decode_skin(source, back)
            # The live humanoid contract has a rigid chest attachment; wing
            # authoring bones retain their bind geometry until that rig is supported.
            back_palette = ['chest' if b.startswith('attachment_wing_') else b for b in back_palette]
            union = list(dict.fromkeys([*palette, *back_palette]))
            indices = np.concatenate([np.asarray([union.index(b) for b in palette])[indices],
                                      np.asarray([union.index(b) for b in back_palette])[back_indices]])
            weights = np.concatenate([weights, back_weights])
            palette = union
        allowed = HUMANOID_SLOT_BONES[slot]
        used = {palette[int(index)] for index in indices[weights > 0]}
        if not used <= allowed:
            raise ValueError(f'{entry["id"]}:{slot} leaves its bone contract: {used-allowed}')
        pruned = [bone for bone in palette if bone in used]
        remap = np.asarray([pruned.index(b) if b in pruned else 0 for b in palette])
        metadata = {'schema_version': 1, 'skeleton_id': 'humanoid_v1', 'slot': slot,
                    'bind_profile': component['bind_profile'], 'skeleton_sha256': skeleton_digest,
                    'model_sha256': hashlib.sha256(model_bytes).hexdigest(), 'vertex_count': len(indices),
                    'bone_palette': pruned, 'allowed_bones': sorted(allowed),
                    'skin_indices': remap[indices].tolist(), 'skin_weights': weights.tolist(),
                    'method': 'reviewed_constructor_weights_v11'}
        immutable(output/'parts'/f'{slot}.glb', model_bytes)
        immutable(output/'parts'/f'{slot}.weights.json', encode(metadata))
    immutable(output/'record.json', encode({'schema_version': 1, 'label': entry['label'],
              'race': component['race'], 'rig': 'humanoid_v1', 'constructor_settings': component['settings'],
              'review_id': entry['id'], 'review_revision': 11, 'source_assembly': component['assembly_id'],
              'source_role': component['role'], 'mount_pending': component['role'] == 'rider'}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.source/'manifest.json').read_text())
    integrity = json.loads((args.source/'integrity.json').read_text())['files']
    published, pending = [], []
    for entry in manifest['entries']:
        components = [json.loads((args.source/path).read_text()) for path in entry['components']]
        humanoid = next((c for c in components if c['contract'] == 'humanoid_v1'), None)
        if humanoid is None:
            pending.append(entry['id'])
            continue
        for part in humanoid['parts'].values():
            for field in ('model', 'skin'):
                path = part[field]
                if hashlib.sha256((args.source/path).read_bytes()).hexdigest() != integrity[path]:
                    raise ValueError(f'Review asset hash mismatch: {path}')
        publish(args.source, entry, humanoid)
        published.append(entry['id'])
        print('Published', entry['id'], flush=True)
    build_catalog(ROOT)
    print(json.dumps({'published': published, 'pending_nonhumanoid_contracts': pending}), flush=True)


if __name__ == '__main__':
    main()
