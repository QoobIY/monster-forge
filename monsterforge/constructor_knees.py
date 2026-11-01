"""Bake the SDK knee bind revision into immutable constructor leg surfaces."""
import copy
import hashlib
import json

import numpy as np
from tools.creature_workshop.geometry import mesh

BIND_PROFILE = 'workshop_knees_v1'


def skeleton_snapshot():
    from .runtime import load_bind_skeleton
    skeleton = copy.deepcopy(load_bind_skeleton(BIND_PROFILE))
    digest = hashlib.sha256(json.dumps(skeleton, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return skeleton, digest


def world_bind(profile=BIND_PROFILE):
    from .runtime import bind_positions, load_bind_skeleton
    return bind_positions(load_bind_skeleton(profile))


def bind_bones():
    from .runtime import bind_bones as static_bind_bones
    return static_bind_bones(BIND_PROFILE)


def apply(recipe):
    """Move the actual knee region forward, keeping the sole and hip seam fixed.

    This is authored surface deformation, not an animation solver. The new
    joint position and all runtime poses come from the shared MOM SDK.
    """
    old, new = world_bind('canonical'), world_bind()
    _, digest = skeleton_snapshot()
    for command in recipe['commands']:
        slot = command['slot']
        if slot not in ('left_leg', 'right_leg'):
            continue
        source = command.get('authored_primitive', command)
        revision = command.get('knee_bind_revision', source.get('knee_bind_revision'))
        if revision:
            if revision['profile'] != BIND_PROFILE or revision['skeleton_sha256'] != digest:
                raise ValueError('Incompatible immutable knee bind revision')
            continue
        side = slot.split('_')[0]
        knee = new[side + '_knee']
        offset = knee[2] - old[side + '_knee'][2]
        vertices, faces = mesh(command)
        vertices = vertices.copy()
        # The authored thigh seam is at 1.16, above the SDK hip pivot.
        seam_y = 1.16 if source.get('body_silhouette_revision') else old[side + '_hip'][1]
        blend = np.interp(vertices[:, 1], [.085, knee[1], seam_y], [0, 1, 0])
        vertices[:, 2] += offset * blend
        command.update(op='indexed_mesh', vertices=vertices.tolist(), faces=faces.tolist())
        command.pop('vertex_normals', None)
        command['knee_bind_revision'] = {
            'schema_version': 1, 'profile': BIND_PROFILE, 'skeleton_sha256': digest,
            'knee_forward_metres': offset, 'knee_world_metres': knee,
            'surface_anchors_y_metres': [.085, knee[1], seam_y],
        }
        meta = command.get('limb_proportions')
        if meta and meta.get('region') == 'leg':
            meta['knee'] = knee
            meta['bind_profile'] = BIND_PROFILE
    return recipe
