"""Bake the common humanoid palm convention into derived arm revisions.

Thumbs point medially in the authored relaxed bind. The palm and finger flexion
therefore face -Z, with the dorsum facing +Z. Skeletons and sockets stay fixed.
"""
from __future__ import annotations

import copy

import numpy as np

from tools.creature_workshop.geometry import mesh
from tools.creature_workshop.family_faces import orient_faces
from .constructor_knees import world_bind


def is_hand(command):
    part = command['part'].lower()
    primitive = command.get('authored_primitive', command)
    anatomy = command.get('limb_proportions', primitive.get('limb_proportions', {}))
    return (anatomy.get('region') == 'hand' or bool(command.get('hand_anatomy'))
            or command.get('skin_bone', '').endswith('_hand')
            or any(name in part for name in ('palm', 'finger', 'thumb', 'hand', 'glove',
                                             'thenar', 'phalanx', 'digit_core')))


def apply(recipe, slot):
    if slot not in {'left_arm', 'right_arm'}:
        return
    wrist = np.asarray(world_bind('canonical')[slot.split('_')[0] + '_hand'])
    for command in recipe['commands']:
        if not is_hand(command):
            continue
        previous = command.get('hand_orientation_revision')
        if previous:
            if previous.get('schema_version') != 1:
                raise ValueError('Неизвестная ревизия ориентации кисти')
            continue
        def reflect(points):
            result = np.asarray(points, dtype=float).copy()
            result[..., 2] = 2 * wrist[2] - result[..., 2]
            return result
        vertices, faces = mesh(command)
        command.setdefault('hand_orientation_source', {'vertices': vertices.tolist(), 'faces': faces.tolist()})
        vertices = reflect(vertices)
        command.update(op='indexed_mesh', vertices=vertices.tolist(), faces=orient_faces(vertices, faces[:, ::-1]).tolist())
        if 'vertex_normals' in command:
            normals = np.asarray(command['vertex_normals']).copy()
            normals[:, 2] *= -1
            command['vertex_normals'] = normals.tolist()
        for key in ('path', 'center'):
            if key in command:
                command[key] = reflect(command[key]).tolist()
        if 'stations' in command:
            command['stations'] = [[y, x, 2 * wrist[2] - z, rx, rz] for y, x, z, rx, rz in command['stations']]
        if 'hand_anatomy' in command:
            command['hand_anatomy'] = copy.deepcopy(command['hand_anatomy'])
            for key in ('joint_start', 'joint_end', 'wrist'):
                if key in command['hand_anatomy']:
                    command['hand_anatomy'][key] = reflect(command['hand_anatomy'][key]).tolist()
        command['hand_orientation_revision'] = {
            'schema_version': 1, 'palm_normal': [0, 0, -1], 'dorsum_normal': [0, 0, 1],
            'wrist_plane_z_metres': float(wrist[2]), 'method': 'authored hand reflection; skeleton and sockets unchanged'}


def apply_weights(sidecar, recipe, ends):
    """Rigid hand anatomy belongs to the hand bone, not the elbow blend."""
    slot = sidecar['slot']
    if slot not in {'left_arm', 'right_arm'}:
        return
    bone = slot.split('_')[0] + '_hand'
    if bone not in sidecar['allowed_bones']:
        raise ValueError('Кость кисти несовместима со слотом руки')
    index, start, changed = sidecar['bone_palette'].index(bone), 0, False
    for command, end in zip(recipe['commands'], ends, strict=True):
        if is_hand(command):
            for vertex in range(start, end):
                sidecar['skin_indices'][vertex] = [index, 0, 0, 0]
                sidecar['skin_weights'][vertex] = [1., 0., 0., 0.]
            changed = True
        start = end
    if changed:
        sidecar['hand_binding_revision'] = {'schema_version': 1, 'bone': bone,
                                           'method': 'backend rigid hand regions; existing forearm weights retained'}
