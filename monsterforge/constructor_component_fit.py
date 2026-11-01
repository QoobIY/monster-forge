"""Contact corrections baked into derived humanoid parts, never assembly offsets."""
from __future__ import annotations

import numpy as np

from tools.creature_workshop.geometry import mesh
from .constructor_face_fit import surfaces, front_depth

REVISION = 1


def clothing(recipe, slot):
    """Keep separately selectable heraldry and shoulder gear out of base clothes."""
    if recipe.get('original_design', {}).get('spec', {}).get('race') != 'human':
        return
    removed = []
    for c in recipe['commands']:
        if (slot == 'torso' and c['part'] == 'chest_rank_mark' or
                slot.endswith('_arm') and c['part'] in {
                    'pauldron', 'pauldron_facet', 'leather_shoulder'}):
            removed.append(c)
    if removed:
        recipe['commands'] = [c for c in recipe['commands'] if c not in removed]
        recipe['modular_clothing_revision'] = {
            'schema_version': REVISION, 'removed_parts': [c['part'] for c in removed],
            'method': 'emblem and shoulder geometry belongs to independent controls'}


def _write(command, vertices, faces, key, detail):
    command.update(op='indexed_mesh', vertices=vertices.tolist(), faces=faces.tolist())
    command.pop('vertex_normals', None)
    command[key] = {'schema_version': REVISION, **detail}


def _depth(face, xy):
    """Use the lower face at the chin for hair that hangs below the jaw."""
    skin = np.concatenate([mesh(c)[0] for c in face])
    xy = np.asarray(xy).copy()
    xy[:, 1] = np.clip(xy[:, 1], skin[:, 1].min() + .018, skin[:, 1].max() - .01)
    result = front_depth(face, xy)
    # Sideburn roots can fall just outside a narrower head's projected outline.
    for _ in range(12):
        missing = ~np.isfinite(result)
        if not missing.any():
            break
        xy[missing, 0] *= .8
        result[missing] = front_depth(face, xy[missing])
    if not np.isfinite(result).all():
        raise ValueError('Facial hair has no facial support')
    return result


def _stubble(face, bottom, top):
    """Clip the actual front facial planes and close a thin shell over them."""
    points, faces, lookup = [], [], {}
    def index(p):
        key = tuple(np.round(p, 10))
        if key not in lookup:
            lookup[key] = len(points)
            points.append(p)
        return lookup[key]
    for skin in face:
        vertices, triangles = mesh(skin)
        for triangle in vertices[triangles]:
            normal = np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
            if normal[2] <= 1e-10 or triangle[:, 2].mean() < .025:
                continue
            polygon = list(triangle)
            for axis, bound, sign in ((1, bottom, 1), (1, top, -1)):
                clipped = []
                for a, b in zip(polygon, polygon[1:] + polygon[:1]):
                    da, db = sign * (a[axis] - bound), sign * (b[axis] - bound)
                    if da >= 0:
                        clipped.append(a)
                    if (da >= 0) != (db >= 0):
                        clipped.append(a + (b-a)*da/(da-db))
                polygon = clipped
            ids = [index(p) for p in polygon]
            for i in range(1, len(ids)-1):
                faces.append([ids[0], ids[i], ids[i+1]])
    v, f = np.asarray(points), np.asarray(faces, dtype=int)
    if not len(f):
        raise ValueError('No lower face surface for stubble')
    edges = {}
    for triangle in f:
        for a, b in zip(triangle, np.roll(triangle, -1)):
            key = tuple(sorted((int(a), int(b))))
            if key in edges:
                del edges[key]
            else:
                edges[key] = (int(a), int(b))
    n = len(v)
    closed = f.tolist() + (f[:, ::-1] + n).tolist()
    for a, b in edges.values():
        closed.extend([[a, a+n, b+n], [a, b+n, b]])
    from tools.creature_workshop.family_faces import orient_faces
    vertices = np.concatenate([v + [0, 0, .002], v - [0, 0, .001]])
    return vertices, orient_faces(vertices, np.asarray(closed))


def facial_hair(recipe, settings):
    face = surfaces(recipe)
    if not face:
        return
    commands = [c for c in recipe['commands'] if 'beard' in c['part'] or
                any(t in c['part'] for t in ('mustache', 'moustache'))]
    if not commands or recipe.get('facial_hair_contact_revision'):
        return
    skin = np.concatenate([mesh(c)[0] for c in face])
    lips = [mesh(c)[0] for c in recipe['commands'] if 'lip' in c['part']]
    mouth_y = float(np.concatenate(lips)[:, 1].mean()) if lips else 2.125
    chin = float(skin[:, 1].min())
    stubble = (settings['reference_parts'].get('beards') == 1 or
               not settings['reference_parts'].get('beards') and settings['decor']['beard'] == 'stubble')
    if stubble:
        beard = [c for c in commands if 'beard' in c['part']]
        if beard:
            vertices, triangles = _stubble(face, chin + .005, mouth_y - .012)
            c = beard[0]
            _write(c, vertices, triangles, 'facial_hair_contact',
                   {'method': 'thin closed shell from selected lower facial planes', 'relief_metres': .002})
            recipe['commands'] = [c for c in recipe['commands'] if c not in beard[1:]]
            commands = [c for c in commands if c not in beard]
    scale = np.clip(np.ptp(skin[:, 0])/.416, .7, 1.5)
    for command in commands:
        v, f = mesh(command)
        if 'beard_volume' in command['part']:
            from .constructor_face_fit import split_edges
            v, f = split_edges(v, f)
            if 'face_materials' in command:
                command['face_materials'] = [m for m in command['face_materials'] for _ in range(4)]
        v = v.copy()
        v[:, 0] *= scale
        v[:, 1] += mouth_y - 2.125
        z = _depth(face, v[:, :2])
        # Preserve the authored relief and free hanging ends; seat the roots
        # against this face instead of using the donor's fixed Z plane.
        lift = np.zeros(len(v))
        if 'beard_volume' in command['part']:
            front = front_depth([{'op':'indexed_mesh', 'vertices':v.tolist(), 'faces':f.tolist()}], v[:, :2])
            # Seat the visible tapered envelope as well as its root plane.
            # The rear remains embedded; the free hanging tip keeps its shape.
            root = np.clip((v[:, 1]-chin+.03)/.03, 0, 1)
            lift = np.maximum(.006-(front-.23), 0)*root
        v[:, 2] += z - .23 + lift
        _write(command, v, f, 'facial_hair_contact',
               {'method': 'selected lower facial surface with preserved hanging relief',
                'mouth_y_metres': mouth_y, 'width_factor': float(scale),
                'front_clearance_metres': .006})
    recipe['facial_hair_contact_revision'] = {'schema_version': REVISION, 'front_envelope_revision': 2}


def nose_clearance(recipe):
    """Retain a long nose's character while leaving the upper lip uncovered."""
    face = surfaces(recipe)
    noses = [c for c in recipe['commands'] if any(t in c['part'] for t in (
        'nose_bridge', 'nose_large_planes'))]
    lips = [mesh(c)[0] for c in recipe['commands'] if 'upper_lip' in c['part']]
    if not face or not noses or not lips or recipe.get('nose_clearance_revision'):
        return
    nose = np.concatenate([mesh(c)[0] for c in noses])
    low, high = nose[:, 1].min(), nose[:, 1].max()
    target = min(float(np.concatenate(lips)[:, 1].max()) + .018, high - .025)
    for c in recipe['commands']:
        if c not in noses and 'nostril' not in c['part']:
            continue
        v, f = mesh(c)
        v = v.copy()
        if low < target:
            v[:, 1] = high - (high-v[:, 1])*(high-target)/(high-low)
        z = _depth(face, v[:, :2])
        protrusion = np.maximum(v[:, 2]-z, 0)
        maximum = max(float(protrusion.max()), .075)
        v[:, 2] -= protrusion*(1-.075/maximum)
        _write(c, v, f, 'nose_clearance', {'upper_lip_gap_metres': .018,
                                          'max_projection_metres': .075})
    recipe['nose_clearance_revision'] = {'schema_version': REVISION}


def _section(commands, y):
    hits = []
    for c in commands:
        v, f = mesh(c)
        for t in v[f]:
            for a, b in zip(t, np.roll(t, -1, axis=0)):
                if abs(a[1]-y) < 1e-8:
                    hits.append(a)
                if (a[1] < y) != (b[1] < y):
                    hits.append(a + (b-a)*(y-a[1])/(b[1]-a[1]))
    return np.asarray(hits)


def _split_height(vertices, faces, y):
    """Conforming horizontal edge cuts retain a closed boot's shared topology."""
    points = vertices.tolist()
    lookup = {tuple(np.round(p, 10)): i for i, p in enumerate(vertices)}
    def index(point):
        key = tuple(np.round(point, 10))
        if key not in lookup:
            lookup[key] = len(points)
            points.append(point.tolist())
        return lookup[key]
    result, parents = [], []
    for parent, face in enumerate(faces):
        triangle = vertices[face]
        if triangle[:,1].min() >= y-1e-9 or triangle[:,1].max() <= y+1e-9:
            result.append(face.tolist())
            parents.append(parent)
            continue
        for sign in (-1, 1):
            polygon = []
            for a, b in zip(triangle, np.roll(triangle, -1, axis=0)):
                da, db = sign*(a[1]-y), sign*(b[1]-y)
                if da >= 0:
                    polygon.append(a)
                if (da >= 0) != (db >= 0):
                    polygon.append(a+(b-a)*da/(da-db))
            ids = list(dict.fromkeys(index(p) for p in polygon))
            for i in range(1, len(ids)-1):
                result.append([ids[0], ids[i], ids[i+1]])
                parents.append(parent)
    return np.asarray(points), np.asarray(result), parents


def footwear(recipe, slot):
    if (not slot.endswith('_leg') or recipe.get('footwear_contact_revision') or
            any(ref.get('category') == 'boots' and ref.get('variant', 0) >= 8
                for ref in recipe.get('attribute_references', []))):
        return
    boots = [c for c in recipe['commands'] if 'hoof' not in c['part'] and any(t in c['part'] for t in ('flat_boot', 'boot_shaft', 'boot_cuff', 'shoe_upper'))]
    trousers = [c for c in recipe['commands'] if any(t in c['part'] for t in ('trousers', 'pants', 'lower_leg', 'shin_skin'))]
    if not boots or not trousers:
        return
    from .constructor_surface_fit import triangles, radial_hit
    for c in boots:
        v, f = mesh(c)
        for y in (.18, .22, .26):
            v, f, parents = _split_height(v, f, y)
            if 'face_materials' in c:
                c['face_materials'] = [c['face_materials'][i] for i in parents]
        c.update(op='indexed_mesh', vertices=v.tolist(), faces=f.tolist())
    support = triangles(trousers)
    # Sections are computed from the unmodified source, so paired boot layers
    # receive a coherent correction rather than expanding one another.
    import copy
    boot_source = copy.deepcopy(boots)
    sections = {}
    for c in boots:
        for y in mesh(c)[0][:, 1]:
            key = round(float(y), 9)
            if key in sections or y < .09:
                continue
            pants = _section(trousers, y)
            boot = _section(boot_source, y)
            if len(pants) and len(boot):
                sections[key] = ((boot.min(0)+boot.max(0))*.5,
                                 (pants.min(0)+pants.max(0))*.5)
    for c in recipe['commands']:
        if c not in boots and not any(t in c['part'] for t in ('boot_strap', 'boot_buckle')):
            continue
        v, f = mesh(c)
        v = v.copy()
        for i, p in enumerate(v):
            y = float(p[1])
            key = round(y, 9)
            if key not in sections:
                pants, boot = _section(trousers, y), _section(boot_source, y)
                if y < .09 or not len(pants) or not len(boot):
                    continue
                sections[key] = ((boot.min(0)+boot.max(0))*.5, (pants.min(0)+pants.max(0))*.5)
            old_center, center = sections[key]
            direction = p-old_center
            direction[1] = 0
            radius = np.linalg.norm(direction)
            if radius < 1e-9:
                continue
            direction /= radius
            blend = np.clip((y-.09)/.14, 0, 1)
            shifted = old_center + (center-old_center)*blend
            shifted[1] = y
            hit = radial_hit(support, shifted, direction)
            if hit is not None:
                radius = max(radius, hit+.014)
            v[i] = shifted + direction*radius
        _write(c, v, f, 'footwear_contact',
               {'method': 'boot shaft follows selected trouser cross section',
                'clearance_metres': .014, 'sole_unchanged_below_y': .09})
    recipe['footwear_contact_revision'] = {'schema_version': REVISION}
