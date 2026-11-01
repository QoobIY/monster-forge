"""A rounded human occiput and forward head placement in derived parts."""
from __future__ import annotations

import numpy as np

from tools.creature_workshop.geometry import mesh

REVISION = 1
FORWARD_SHIFT = .035
REAR_CORNER_TUCK = .075
REAR_START = .06
REAR_END = -.18


def deform(vertices, half_width):
    """Round rear corners without changing facial planes or mesh topology.

    The depth derivative stays positive: the correction cannot fold a closed
    volume inside out. The same continuous field keeps skin and hair together.
    """
    result = np.asarray(vertices, dtype=float).copy()
    rear = np.clip((REAR_START - result[:, 2]) / (REAR_START - REAR_END), 0, 1)
    rear = rear * rear * (3 - 2 * rear)
    lateral = np.minimum((result[:, 0] / half_width) ** 2, 1)
    result[:, 2] += FORWARD_SHIFT + REAR_CORNER_TUCK * lateral * rear
    return result


def reshape(recipe, settings, slot):
    if slot != 'head' or settings['race'] != 'human':
        return
    previous = recipe.get('human_head_shape_revision')
    if previous:
        if previous['schema_version'] != REVISION:
            raise ValueError('Unsupported human head shape revision')
        return
    from .constructor_face_fit import surfaces
    skin = surfaces(recipe)
    if not skin:
        raise ValueError('Human head has no cranial surface')
    half_width = max(float(np.abs(mesh(c)[0][:, 0]).max()) for c in skin)
    if half_width <= 0:
        raise ValueError('Human head has no width')
    for command in recipe['commands']:
        vertices, faces = mesh(command)
        vertices = deform(vertices, half_width)
        vertices[:, 2] -= FORWARD_SHIFT
        command.update(op='indexed_mesh', vertices=vertices.tolist(), faces=faces.tolist())
        command.pop('vertex_normals', None)
    recipe['human_head_shape_revision'] = {
        'schema_version': REVISION,
        'rear_corner_tuck_metres': REAR_CORNER_TUCK, 'half_width_metres': half_width,
        'method': 'rounded posterior corners before fitting helmets and head accessories',
        'sdk_bind_unchanged': True,
    }


def apply(recipe, settings, slot):
    """Move the finished head and fitted gear together, leaving bind bones alone."""
    if slot != 'head' or settings['race'] != 'human':
        return
    previous = recipe.get('human_head_revision')
    if previous:
        if previous['schema_version'] != REVISION:
            raise ValueError('Unsupported human head placement revision')
        return
    reshape(recipe, settings, slot)
    for command in recipe['commands']:
        vertices, faces = mesh(command)
        vertices = vertices.copy()
        vertices[:, 2] += FORWARD_SHIFT
        command.update(op='indexed_mesh', vertices=vertices.tolist(), faces=faces.tolist())
    recipe['human_head_revision'] = {
        **recipe['human_head_shape_revision'], 'forward_shift_metres': FORWARD_SHIFT,
        'method': 'rounded posterior corners; finished head and fitted attachments shifted along +Z',
    }
