"""Humanoid randomiums: shared body, individual game heads and joint emblems."""
from __future__ import annotations

import hashlib
import copy
import itertools
import json
import tempfile
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull

from tools.creature_workshop.family_faces import orient_faces
from tools.creature_workshop.geometry import compile_recipe, export_glb, render_png, mesh
from tools.creature_workshop.original_constructor import OriginalSculpt
from .constructor_knees import world_bind
from .constructor_marsh_forest import encoded, immutable
from .paths import ROOT, STYLE_PATH

SOURCE = ROOT / 'media/constructor/randomiums/v10'
PART_GAP = .025
RACES = {'randomium': {'label': 'Рандомиумы', 'neutral': True,
                      'description': 'Гуманоиды с игровыми предметами вместо головы; общее гранёное тело, индивидуальные символы на локтях и коленях.'}}
DESIGNS = [{'id': 'native-randomium-random-god-01', 'race': 'randomium',
            'gender': 'male', 'variant': 0, 'label': 'Бог рандома', 'hair': 'cropped',
            'own_body': True, 'contract': 'humanoid_v1',
            'description_ru': 'Голова — игральная кость с гранями 1–6, противоположные дают 7; 1 и 4 красные. Тело цвета слоновой кости с графитовыми сочленениями. На внешней боковой стороне локтей бубны и черви, на коленях пики и трефы.'},
           {'id': 'native-randomium-mahjong-god-01', 'race': 'randomium',
            'gender': 'male', 'variant': 1, 'label': 'Бог маджонга', 'hair': 'cropped',
            'own_body': True, 'contract': 'humanoid_v1',
            'description_ru': 'Голова — вертикальная костяшка маджонга цвета слоновой кости с зелёной обратной стороной и красным знаком 中. Общее тело рандомиумов. На внешней боковой стороне локтей бамбук и круги, на коленях 萬 и восточный ветер 東.'}]
IDS = {d['id'] for d in DESIGNS}
SLOTS = ('head', 'torso', 'left_arm', 'right_arm', 'left_leg', 'right_leg')
REFERENCE = (ROOT / 'media/imported_mom/characters/character.20260827t113124z-72c73d54/revisions/0001/preview/asset/026a9c4b35154ca87308f7bc207a04f162d281d023cce23d2be359a5a6dda2b9--output.png')
PIPS = {1: [(0, 0)], 2: [(-1, 1), (1, -1)],
        3: [(-1, 1), (0, 0), (1, -1)],
        4: [(-1, -1), (-1, 1), (1, -1), (1, 1)],
        5: [(-1, -1), (-1, 1), (0, 0), (1, -1), (1, 1)],
        6: [(x, y) for x in (-1, 1) for y in (-1, 0, 1)]}
DIE_FACES = ((5, (0, 0, 1)), (2, (0, 0, -1)),
             (1, (0, 1, 0)), (6, (0, -1, 0)),
             (3, (1, 0, 0)), (4, (-1, 0, 0)))
JOINT_SYMBOLS = {'left_arm': 'diamond', 'right_arm': 'heart',
                 'left_leg': 'spade', 'right_leg': 'club'}
MAHJONG_SYMBOLS = {'left_arm': 'bamboo', 'right_arm': 'circles',
                   'left_leg': 'wan', 'right_leg': 'wind'}
EMBLEMS = {'original': 'Эмблема комплекта', 'none': 'Без эмблемы',
           'randomium-diamond': 'Бубны', 'randomium-heart': 'Черви',
           'randomium-spade': 'Пики', 'randomium-club': 'Трефы',
           'randomium-bamboo': 'Бамбук', 'randomium-circles': 'Круги',
           'randomium-wan': 'Десятки · 萬', 'randomium-wind': 'Восточный ветер · 東',
           'randomium-red-dragon': 'Красный дракон · 中'}
HIDDEN_PARTS = ['belt', 'headwear', 'back', 'appearance', 'palette']


def glyph(b, kind, center, size, material):
    """Authored stroke reliefs; glyphs are geometry, never a font dependency."""
    x, y, z = center
    paths = {
        'red-dragon': [[(0, -1), (0, 1)], [(-.7, -.5), (-.7, .5), (.7, .5), (.7, -.5), (-.7, -.5)]],
        'wind': [[(-.9, .7), (.9, .7)], [(0, 1), (0, -.95)],
                 [(-.62, .4), (.62, .4), (.62, -.25), (-.62, -.25), (-.62, .4)],
                 [(-.62, .08), (.62, .08)], [(0, -.25), (-.85, -.88)], [(0, -.25), (.85, -.88)]],
        'wan': [[(-.9, .8), (.9, .8)], [(-.35, 1), (-.35, .57)], [(.35, 1), (.35, .57)],
                [(-.57, .48), (.57, .48), (.57, -.12), (-.57, -.12), (-.57, .48)],
                [(-.57, .18), (.57, .18)], [(0, .48), (0, -.48)],
                [(-.8, -.38), (.8, -.38), (.8, -.95), (.54, -.95)],
                [(-.8, -.38), (-.8, -.98)], [(0, -.38), (0, -.8)], [(-.45, -.8), (.43, -.8)]]}
    for path in paths[kind]:
        for a, c in zip(path, path[1:]):
            b.tube('randomium_symbol_' + kind, material,
                   [[x + a[0] * size, y + a[1] * size, z],
                    [x + c[0] * size, y + c[1] * size, z]], [.065 * size] * 2, sides=6)


def circle(b, center, radius):
    x, y, z = center
    vertices = [[x + r * np.cos(a), y + r * np.sin(a), zz]
                for zz in (z - .004, z + .004) for r in (radius, radius * .57)
                for a in np.arange(12) * (np.pi / 6)]
    faces = []
    for i in range(12):
        j = (i + 1) % 12
        for a, c, d, e in ((i, j, j + 12, i + 12), (i + 24, i + 36, j + 36, j + 24),
                           (i, i + 24, j + 24, j), (i + 12, j + 12, j + 36, i + 36)):
            faces.extend([[a, c, d], [a, d, e]])
    vertices = np.asarray(vertices)
    b.solid('randomium_symbol_circles', 'jade', vertices,
            orient_faces(vertices, np.asarray(faces)), 'Объёмное кольцо масти кругов с открытой серединой.')


def emblem(b, kind, center, size):
    """Closed reliefs on the joint's front plate, in the part's coordinates."""
    x, y, z = center
    if kind in {'red-dragon', 'wan', 'wind'}:
        glyph(b, kind, center, size, 'red' if kind != 'wind' else 'ink')
        return
    if kind == 'circles':
        for dx, dy in ((-.45, -.38), (.45, -.38), (0, .45)):
            circle(b, [x + dx * size, y + dy * size, z + .005], size * .37)
        return
    if kind == 'bamboo':
        for dx in (-.48, .48):
            b.tube('randomium_symbol_bamboo', 'jade',
                   [[x + dx * size, y - .85 * size, z], [x + dx * size, y + .85 * size, z]],
                   [.12 * size] * 2, sides=6)
            for dy in (-.45, .4):
                b.box('randomium_symbol_bamboo_node', 'jade',
                      [x + dx * size, y + dy * size, z], [.38 * size, .13 * size, .014])
        return
    mat = 'red' if kind in {'heart', 'diamond'} else 'ink'
    def panel(name, points):
        b.panel3('randomium_symbol_' + name, mat,
                 [[x + a * size, y + c * size, z] for a, c in points], .008)
    if kind == 'diamond':
        panel(kind, [(0, -1), ( .70, 0), (0, 1), (-.70, 0)])
    elif kind in {'heart', 'spade'}:
        points = [(0, -.95), (.78, -.10), (.94, .42), (.66, .83),
                  (.28, .85), (0, .50), (-.28, .85), (-.66, .83),
                  (-.94, .42), (-.78, -.10)]
        if kind == 'spade':
            points = [(a, -c * .78 + .15) for a, c in points]
        panel(kind, points)
    else:
        for i, (dx, dy) in enumerate(((0, .48), (-.49, 0), (.49, 0))):
            b.oval('randomium_symbol_club_lobe_' + str(i), mat,
                   [x + dx * size, y + dy * size, z - .002],
                   [.50 * size, .50 * size, .008], sides=10)
    if kind in {'spade', 'club'}:
        panel(kind + '_stem', [(-.38, -.95), (.38, -.95), (.13, -.38), (-.13, -.38)])


def dice_head(b):
    center, half, bevel = np.array([0, 2.25, .08]), .285, .024
    vertices = []
    for signs in itertools.product((-1, 1), repeat=3):
        for axis in range(3):
            p = np.array(signs, dtype=float) * (half - bevel)
            p[axis] = signs[axis] * half
            vertices.append(p + center)
    vertices = np.asarray(vertices)
    faces = orient_faces(vertices, ConvexHull(vertices).simplices)
    b.solid('randomium_die_head', 'ivory', vertices, faces,
            'Цельная кубическая голова с небольшими фасками; без человеческого лица.')
    for number, direction in DIE_FACES:
        normal = np.array(direction, dtype=float)
        u = np.array([1., 0, 0]) if normal[0] == 0 else np.array([0., 0, 1.])
        v = np.cross(normal, u)
        for a, c in PIPS[number]:
            point = center + normal * half + .14 * (a * u + c * v)
            b.tube('randomium_die_pip', 'red' if number in {1, 4} else 'ink',
                   [point.tolist(), (point + normal * .004).tolist()], [.042] * 2, sides=12)
            b.commands[-1]['die_face'] = number
            b.commands[-1]['face_normal'] = list(direction)


def mahjong_head(b):
    # The common neck/head attachment stays on humanoid_v1.
    for name, center, half, mat in (
            ('back', [0, 2.25, -.035], [.235, .335, .115], 'jade'),
            ('face', [0, 2.25, .065], [.235, .335, .075], 'ivory')):
        vertices = []
        for signs in itertools.product((-1, 1), repeat=3):
            for axis in range(3):
                p = np.array(signs) * (np.array(half) - .018)
                p[axis] = signs[axis] * half[axis]
                vertices.append(p + center)
        vertices = np.asarray(vertices)
        b.solid('randomium_mahjong_' + name, mat, vertices,
                orient_faces(vertices, ConvexHull(vertices).simplices),
                'Вертикальная костяшка маджонга с фасками; зелёная спинка и лицевая сторона из слоновой кости.')
    glyph(b, 'red-dragon', [0, 2.25, .144], .20, 'red')


def faceted_volume(b, name, material, centers, widths, depths, lateral, front, **metadata):
    """Closed chamfered sections with broad planes and an authored silhouette."""
    outline = np.array([[-.65, -1], [.65, -1], [1, -.60], [1, .60],
                        [.65, 1], [-.65, 1], [-1, .60], [-1, -.60]])
    lateral, front = np.asarray(lateral), np.asarray(front)
    vertices = np.concatenate([np.asarray(center) + outline[:, :1] * width * lateral
                               + outline[:, 1:] * depth * front
                               for center, width, depth in zip(centers, widths, depths, strict=True)])
    faces = []
    for row in range(len(centers) - 1):
        for i in range(8):
            a, c = row * 8 + i, row * 8 + (i + 1) % 8
            faces.extend([[a, c, c + 8], [a, c + 8, a + 8]])
    for start in (0, (len(centers) - 1) * 8):
        faces.extend([[start, start + i, start + i + 1] for i in range(1, 7)])
    b.solid(name, material, vertices, orient_faces(vertices, np.asarray(faces)),
            'Авторский гранёный объём с меняющимся сечением и фасками.', **metadata)


def articulated_hand(b, wrist, sign):
    """Five relaxed digits, a metacarpal arch and an opposed two-joint thumb.

    This is authored bind geometry. All digits remain on the existing hand bone.
    Local U points towards the thumb; D down the palm; F towards its inner face.
    """
    u, d, f = np.array([-sign, 0., 0.]), np.array([0., -1., 0.]), np.array([0., 0., 1.])
    wrist = np.asarray(wrist)
    def point(x, y, z):
        return wrist + u * x + d * y + f * z
    centers = [point(0, -.012, 0), point(.004, .035, .004), point(.003, .084, .008),
               point(-.004, .132, .010), point(-.007, .156, .012)]
    faceted_volume(b, 'randomium_palm', 'ivory', centers,
                   [.044, .063, .079, .083, .072], [.030, .039, .043, .035, .025], u, f,
                   hand_anatomy={'schema_version': 1, 'region': 'metacarpus', 'wrist': wrist.tolist()})
    # Thenar eminence joins the palm and thumb base instead of a side-mounted rod.
    faceted_volume(b, 'randomium_thenar', 'ivory',
                   [point(.040, .035, .018), point(.068, .067, .029), point(.077, .099, .041)],
                   [.026, .037, .023], [.025, .032, .022], u, f)

    def phalanges(digit, path, width, thumb=False):
        # A continuous dark articular core supports the separated ivory phalanges.
        faceted_volume(b, 'randomium_digit_core_' + digit, 'graphite', path,
                       [width * .62 * (1 - .16 * i if i < len(path) - 1 else .40) for i in range(len(path))],
                       [width * .50 * (1 - .16 * i if i < len(path) - 1 else .40) for i in range(len(path))], u, f)
        for i, (a, c) in enumerate(zip(path, path[1:])):
            a, c = np.asarray(a), np.asarray(c)
            axis = c - a
            length = float(np.linalg.norm(axis))
            direction = axis / length
            # Leave a readable joint recess, while the core keeps the finger connected.
            start = a + direction * (.002 if i else -.004)
            end = c - direction * (.002 if i < len(path) - 2 else 0)
            w = width * (1 - .16 * i)
            faceted_volume(b, 'randomium_phalanx_' + digit + '_' + str(i + 1), 'ivory',
                           [start, start + (end - start) * .24, start + (end - start) * .84, end],
                           [w * .78, w, w * .88, w * .62],
                           [w * .65, w * .83, w * .74, w * .47], u, f,
                           hand_anatomy={'schema_version': 1, 'digit': digit, 'phalanx': i + 1,
                                         'joint_start': a.tolist(), 'joint_end': c.tolist(),
                                         'opposed': thumb})
    # Knuckles form an arch; unequal lengths and gentle flexion give a relaxed hand.
    for digit, x, base, length, width, spread in (
            ('index', .061, .145, .132, .020, .009),
            ('middle', .019, .156, .150, .0205, 0),
            ('ring', -.024, .151, .140, .019, -.004),
            ('little', -.064, .133, .108, .0165, -.010)):
        path = [point(x + spread * t, base + length * t, .011 + .018 * t + .045 * t * t)
                for t in (0, .46, .77, 1)]
        phalanges(digit, path, width)
    # Thumb root sits forward of the palm; two phalanges turn towards the fingers.
    phalanges('thumb', [point(.073, .077, .035), point(.112, .127, .074),
                       point(.098, .184, .121)], .025, thumb=True)


def sculpted_arm(b, shoulder, elbow, wrist, sign):
    """Shared SDK attachment pivots; faceted deltoid, upper arm and forearm."""
    front = np.array([0., 0., 1.])
    axis = elbow - shoulder
    lateral = np.array([axis[1], -axis[0], 0.])
    lateral /= np.linalg.norm(lateral)
    faceted_volume(b, 'randomium_upper_arm', 'ivory',
                   [shoulder + axis * t + front * offset for t, offset in
                    ((-.045, 0), (.14, -.005), (.35, .010), (.61, .013), (.83, .002), (1., 0))],
                   [.105, .150, .153, .132, .103, .086],
                   [.092, .139, .136, .124, .091, .077], lateral, front,
                   arm_anatomy={'schema_version': 1, 'region': 'upper_arm',
                                'proximal': shoulder.tolist(), 'distal': elbow.tolist()})
    b.oval('randomium_elbow', 'graphite', elbow.tolist(), [.107, .104, .105], sides=8)
    axis = wrist - elbow
    lateral = np.array([axis[1], -axis[0], 0.])
    lateral /= np.linalg.norm(lateral)
    faceted_volume(b, 'randomium_forearm', 'graphite',
                   [elbow + axis * t + front * offset for t, offset in
                    ((0, 0), (.16, .005), (.37, .009), (.64, .006), (.88, 0), (1.015, 0))],
                   [.087, .110, .103, .080, .057, .046],
                   [.079, .094, .091, .068, .046, .033], lateral, front,
                   arm_anatomy={'schema_version': 1, 'region': 'forearm',
                                'proximal': elbow.tolist(), 'distal': wrist.tolist()})
    articulated_hand(b, wrist, sign)


def shared_body(b, slot):
    bind = world_bind('canonical')
    if slot == 'torso':
        b.loft('randomium_core', 'graphite', [[.91, 0, 0, .24, .16],
               [1.17, 0, 0, .27, .19], [1.43, 0, .01, .25, .18]], sides=8)
        b.loft('randomium_chest', 'ivory', [[1.18, 0, .01, .25, .18],
               [1.55, 0, .03, .36, .23], [1.78, 0, .04, .32, .21],
               [1.88, 0, .05, .14, .12]], sides=8)
        b.tube('randomium_neck', 'ivory', [[0, 1.84, .07], [0, 1.99, .08]], [.11, .10])
        emblem(b, 'diamond', [0, 1.04, .17], .075)
        return
    side = slot.split('_')[0]
    sign = -1 if side == 'left' else 1
    arm = slot.endswith('_arm')
    a, joint, end = [np.asarray(bind[side + '_' + key]) for key in
                     (('shoulder', 'elbow', 'hand') if arm else ('hip', 'knee', 'foot'))]
    if arm:
        sculpted_arm(b, a, joint, end, sign)
        width, height, z = .125, .135, joint[2] + .12
    else:
        b.tube('randomium_thigh', 'ivory', [a.tolist(), joint.tolist()], [.165, .115], sides=6)
        b.oval('randomium_knee', 'graphite', joint.tolist(), [.12, .12, .115], sides=8)
        ankle = [end[0], .16, .04]
        b.tube('randomium_shin', 'graphite', [joint.tolist(), ankle], [.115, .095], sides=6)
        b.loft('randomium_foot', 'ivory', [[0, end[0], .12, .135, .23],
                   [.10, end[0], .12, .135, .23], [.22, end[0], .04, .095, .115]], sides=8)
        width, height, z = .13, .14, joint[2] + .13
    x, y = joint[:2]
    b.panel3('randomium_joint_plate', 'ivory',
             [[x - width, y - height * .6, z], [x, y - height, z],
              [x + width, y - height * .6, z], [x + width, y + height * .6, z],
              [x, y + height, z], [x - width, y + height * .6, z]], .025)


def separate_parts(source_recipe, slot, design):
    """Bake small open seams into parts while retaining SDK pivots and soles."""
    # Measure the torso after the existing neck revision, as it appears in the
    # constructor. All randomiums share these exact body surfaces.
    torso = OriginalSculpt({'id': 'randomium-seam-reference', 'palette': source_recipe['palette']})
    torso.slot, torso.stage = 'torso', 2
    shared_body(torso, 'torso')
    from .constructor_neck import apply as shorten_neck
    reference = torso.recipe()
    shorten_neck(reference, 'torso')
    body = np.concatenate([mesh(c)[0] for c in reference['commands']])
    info = {'schema_version': 1, 'gap_metres': PART_GAP, 'skeleton_unchanged': True}
    if slot == 'head':
        final_head = copy.deepcopy(source_recipe)
        shorten_neck(final_head, 'head')
        bottom = min(float(mesh(c)[0][:, 1].min()) for c in final_head['commands'])
        lift = float(body[:, 1].max()) + PART_GAP - bottom
        for c in source_recipe['commands']:
            vertices, faces = mesh(c)
            vertices[:, 1] += lift
            c.update(op='indexed_mesh', vertices=vertices.tolist(), faces=faces.tolist())
        info.update(method='head surface clearance from actual bounds', head_lift_metres=lift,
                    head_design=design['id'])
    elif slot.endswith('_arm'):
        side = slot.split('_')[0]
        sign = -1 if side == 'left' else 1
        bind = world_bind('canonical')
        shoulder, elbow = np.asarray(bind[side + '_shoulder']), np.asarray(bind[side + '_elbow'])
        axis = elbow - shoulder
        target = float(np.abs(body[:, 0]).max()) + PART_GAP
        command = next(c for c in source_recipe['commands'] if c['part'] == 'randomium_upper_arm')
        vertices, faces = mesh(command)
        t = (vertices - shoulder) @ axis / (axis @ axis)
        blend = np.clip((.55 - t) / .40, 0, 1)
        needed = target - sign * vertices[:, 0]
        if np.any((blend < 1e-8) & (needed > 0)):
            raise ValueError('Нельзя получить плечевой зазор без смещения локтя')
        shift = max(0., float(np.max(needed[blend > 1e-8] / blend[blend > 1e-8])))
        vertices[:, 0] += sign * shift * blend
        command.update(op='indexed_mesh', vertices=vertices.tolist(), faces=faces.tolist())
        info.update(method='proximal shoulder surface separation', root_shift_metres=shift,
                    elbow_and_hand_unchanged=True)
    elif slot.endswith('_leg'):
        # Trim the convex thigh at its upper seam; preserve knee, shin and sole.
        top = float(body[:, 1].min()) - PART_GAP
        command = next(c for c in source_recipe['commands'] if c['part'] == 'randomium_thigh')
        vertices, faces = mesh(command)
        points = vertices[vertices[:, 1] <= top].tolist()
        edges = {tuple(sorted((int(a), int(c)))) for face in faces for a, c in zip(face, np.roll(face, -1))}
        for a, c in edges:
            p, q = vertices[a], vertices[c]
            if (p[1] < top < q[1]) or (q[1] < top < p[1]):
                points.append((p + (q - p) * ((top - p[1]) / (q[1] - p[1]))).tolist())
        points = np.unique(np.round(points, 10), axis=0)
        hull = ConvexHull(points)
        command.update(op='indexed_mesh', vertices=points.tolist(),
                       faces=orient_faces(points, hull.simplices).tolist())
        info.update(method='capped upper thigh seam', upper_seam_y_metres=top,
                    knee_and_sole_unchanged=True)
    else:
        return
    source_recipe['part_separation_revision'] = info


def fit_elbow_badge(b, joint, sign):
    """Seat the complete badge on the arm, then seat its relief on the badge."""
    from .constructor_face_fit import split_edges
    from .constructor_surface_fit import mount_front
    pivot = np.asarray(joint)
    support = []
    for command in b.commands:
        if command['part'] not in {'randomium_upper_arm', 'randomium_elbow', 'randomium_forearm'}:
            continue
        vertices, faces = mesh(command)
        local = vertices - pivot
        vertices = pivot + np.column_stack([-sign * local[:, 2], local[:, 1], sign * local[:, 0]])
        support.append(dict(command, op='indexed_mesh', vertices=vertices.tolist(), faces=faces.tolist()))
    plate = next(c for c in b.commands if c['part'] == 'randomium_joint_plate')
    symbols = [c for c in b.commands if c['part'].startswith('randomium_symbol_')]
    for command in [plate, *symbols]:
        vertices, faces = mesh(command)
        # The previous footprint extended past the elbow silhouette. Keep the
        # whole hexagon inside the joint before projecting onto its surface.
        vertices[:, :2] = pivot[:2] + (vertices[:, :2] - pivot[:2]) * .55
        for _ in range(2 if command is plate else 1):
            vertices, faces = split_edges(vertices, faces)
        command.update(op='indexed_mesh', vertices=vertices.tolist(), faces=faces.tolist())
    mount_front([plate], support, relief=.004)
    plate['elbow_surface_attachment'] = {'schema_version': 1, 'footprint_scale': .55,
                                         'root_penetration_metres': .004}
    for command in symbols:
        mount_front([command], [plate], relief=.0005)
    for command in [plate, *symbols]:
        vertices, faces = mesh(command)
        local = vertices - pivot
        vertices = pivot + np.column_stack([sign * local[:, 2], local[:, 1], -sign * local[:, 0]])
        command.update(op='indexed_mesh', vertices=vertices.tolist(), faces=faces.tolist(),
                       joint_attachment={'schema_version': 2, 'bone': b.slot.split('_')[0] + '_elbow',
                                         'normal': [sign, 0, 0], 'surface': 'lateral_elbow'})


def recipe(slot, design=None):
    design = design or DESIGNS[0]
    b = OriginalSculpt({'id': design['id'] + '.' + slot,
                       'palette': {'skin': 'ded7be', 'hair': '303b40', 'ivory': 'ded7be',
                                   'graphite': '303b40', 'red': 'af3e37', 'ink': '22282b', 'jade': '2b7550'}})
    b.slot, b.stage = slot, 2
    if slot == 'head':
        (mahjong_head if design['variant'] == 1 else dice_head)(b)
    else:
        shared_body(b, slot)
        if slot in JOINT_SYMBOLS:
            joint = world_bind('canonical')[slot.split('_')[0] + ('_elbow' if slot.endswith('_arm') else '_knee')]
            symbols = MAHJONG_SYMBOLS if design['variant'] == 1 else JOINT_SYMBOLS
            emblem(b, symbols[slot], [joint[0], joint[1], joint[2] + (.131 if slot.endswith('_arm') else .141)], .087)
            if slot.endswith('_arm'):
                fit_elbow_badge(b, joint, -1 if slot.startswith('left') else 1)
    result = b.recipe()
    separate_parts(result, slot, design)
    from .constructor_hand_orientation import apply as orient_hand
    orient_hand(result,slot)
    # Freeze consistently oriented closed surfaces before the common constructor
    # applies its bind/stance revisions to the authored primitives.
    for command in result['commands']:
        vertices, faces = mesh(command)
        command.update(op='indexed_mesh', vertices=vertices.tolist(),
                       faces=orient_faces(vertices, faces).tolist())
    result.update(assembly_reference='humanoid_v1', own_body_design=design,
                  randomium_revision={'schema_version': 10, 'shared_body': 'randomium-body-v10',
                                      'joint_symbol': (MAHJONG_SYMBOLS if design['variant'] == 1 else JOINT_SYMBOLS).get(slot)},
                  style_profile=json.loads(STYLE_PATH.read_text()))
    return result


def apply_chest_emblem(source_recipe, settings, slot):
    """Replace the chest emblem, fitted to the actual common chest surface."""
    if slot != 'torso' or settings['race'] != 'randomium':
        return
    choice = settings['decor']['emblem']
    source_recipe['commands'][:] = [c for c in source_recipe['commands'] if not c.get('randomium_chest_emblem')]
    if choice == 'none':
        return
    design = next(d for d in DESIGNS if d['id'] == settings['outfit'])
    kind = ('red-dragon' if design['variant'] == 1 else 'diamond') if choice == 'original' else choice.removeprefix('randomium-')
    b = OriginalSculpt({'id': 'randomium-chest-emblem', 'palette': source_recipe['palette']})
    b.slot, b.stage = 'torso', 4
    emblem(b, kind, [0, 1.53, 0], .14)
    commands = b.commands
    for i, command in enumerate(commands):
        vertices, faces = mesh(command)
        command.update(id=f'randomium_chest_emblem_{i}', op='indexed_mesh',
                       vertices=vertices.tolist(), faces=orient_faces(vertices, faces).tolist(),
                       randomium_chest_emblem={'schema_version': 1, 'choice': choice, 'symbol': kind})
    from .constructor_surface_fit import mount_front
    support = [c for c in source_recipe['commands'] if c['part'] == 'randomium_chest']
    if not support:
        raise ValueError('У рандомиума нет поверхности груди для эмблемы')
    mount_front(commands, support, relief=.001)
    source_recipe['commands'].extend(commands)


def publish_sources(root: Path = SOURCE):
    """Publish new immutable source parts without changing the imported god."""
    for design in DESIGNS:
        folder = root / design['id']
        parts, arrays = {}, {}
        for slot in SLOTS:
            source_recipe = recipe(slot, design)
            array = compile_recipe(source_recipe)
            arrays[slot] = array
            model = folder / 'parts' / (slot + '.glb')
            model.parent.mkdir(parents=True, exist_ok=True)
            immutable(model.with_suffix('.recipe.json'), encoded(source_recipe))
            from .constructor_cache import register, reference, resolve
            with tempfile.TemporaryDirectory(prefix='randomium-source-') as temporary:
                output = Path(temporary) / 'model.glb'
                export_glb(output, array, source_recipe)
                model_hash = hashlib.sha256(output.read_bytes()).hexdigest()
            register(model, {'kind': 'glb', 'sha256': model_hash,
                             'recipes': [reference(model.with_suffix('.recipe.json'))]})
            parts[slot] = {'model': f'parts/{slot}.glb', 'recipe': f'parts/{slot}.recipe.json', 'sha256': model_hash}
        immutable(folder / 'parts.json', encoded({'schema_version': 1, 'rig_reference': 'humanoid_v1',
                  'coordinates': 'metres; Y up; +Z forward; floor Y=0', 'parts': parts}))
        immutable(folder / 'reference.png', REFERENCE.read_bytes())
        immutable(folder / 'record.json', encoded({'schema_version': 1, **design,
                  'reference_image': 'reference.png', 'source_character_revision': 4,
                  'source_character_id': 'character.20260827t113124z-72c73d54',
                  'reference_sha256': hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
                  'reference_scope': 'shared body and original random god; mahjong head and symbols are authored geometry',
                  'previous_source_revision': 'media/constructor/randomiums/v9',
                  'style_sha256': hashlib.sha256(STYLE_PATH.read_bytes()).hexdigest(),
                  'authoring': 'procedural geometry; original visual reference; no image generation'}))
        for category, slots in {'face': ['head'], 'outfit': SLOTS, 'arms': ['left_arm', 'right_arm'],
                                'legs': ['left_leg', 'right_leg']}.items():
            from .constructor_cache import register, reference
            register(folder / (category + '.png'), {'kind': 'preview', 'size': 256, 'yaw': 0, 'pitch': 0,
                     'recipes': [reference(folder / 'parts' / (slot + '.recipe.json')) for slot in slots]})
    # Cards use the same symbol geometry as exported chest emblems.
    for choice in EMBLEMS:
        if not choice.startswith('randomium-'):
            continue
        b = OriginalSculpt({'id': choice, 'palette': recipe('torso')['palette']})
        b.slot, b.stage = 'torso', 4
        emblem(b, choice.removeprefix('randomium-'), [0, 1.53, 0], .14)
        card_recipe = b.recipe()
        for c in card_recipe['commands']:
            vertices, faces = mesh(c)
            c.update(op='indexed_mesh', vertices=vertices.tolist(), faces=orient_faces(vertices, faces).tolist())
        array = compile_recipe(card_recipe)
        immutable(root / 'emblems' / (choice + '.recipe.json'), encoded(card_recipe))
        from .constructor_cache import register, reference
        register(root / 'emblems' / (choice + '.png'), {'kind': 'preview', 'size': 256, 'yaw': 0, 'pitch': 0,
                 'recipes': [reference(root / 'emblems' / (choice + '.recipe.json'))]})


if __name__ == '__main__':
    publish_sources()
