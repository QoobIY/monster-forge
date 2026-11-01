"""Closed rear curtains join long side locks to the selected hairstyle crown."""
import math

import numpy as np


def long_back(builder, width: float, top: float, length: float, *, waves: bool) -> None:
    angles = np.linspace(0, math.pi, 13)
    stations = [(top - length, 1.03, .24), (top - .30, 1.07, .25),
                (top - .08, .96, .22)]
    vertices = []
    for inner in (False, True):
        for row, (y, scale, depth) in enumerate(stations):
            for angle in angles:
                ripple = .012 * math.cos(angle * 6 + row * .8) if waves else 0
                inset = .028 if inner else 0
                vertices.append([-(width * scale + ripple - inset) * math.cos(angle),
                                 y, -.045 - (depth + ripple - inset) * math.sin(angle)])
    columns, rows = len(angles), len(stations)
    count = columns * rows
    faces = []
    for row in range(rows - 1):
        for col in range(columns - 1):
            a = row * columns + col
            b, c, d = a + 1, a + columns, a + columns + 1
            faces.extend([[a, c, b], [b, c, d],
                          [a + count, b + count, c + count],
                          [b + count, d + count, c + count]])
    boundary = [*range(columns), *[r * columns + columns - 1 for r in range(1, rows)],
                *range(count - 2, count - columns - 1, -1),
                *[r * columns for r in range(rows - 2, 0, -1)]]
    for a, b in zip(boundary, [*boundary[1:], boundary[0]], strict=True):
        faces.extend([[a, b, b + count], [a, b + count, a + count]])
    builder.solid('hair_back_curtain', 'hair', vertices, faces,
                  'Цельная затылочная часть с тем же нижним краем, что у боковых прядей')


def complete_back(recipe, face, top):
    """Close loose hairstyles behind the skull; keep braids and shaved cuts open."""
    from tools.creature_workshop.geometry import mesh
    from tools.creature_workshop.original_constructor import OriginalSculpt
    from .constructor_surface_fit import radial_hit, triangles
    from tools.creature_workshop.family_faces import orient_faces

    loose_names=('hair_long_straight','hair_long_waves','hair_long_panel',
                 'hair_warrior_long','hair_wavy_bob','hair_bob_curved_side',
                 'hair_shag_side')
    loose=[c for c in recipe['commands'] if c['part'].endswith(loose_names)]
    existing=[c for c in recipe['commands'] if c['part']=='hair_back_curtain']
    if not loose and not existing:return
    support=loose or existing
    points=np.concatenate([mesh(c)[0] for c in support])
    hem=float(points[:,1].min());width=float(np.max(np.abs(points[:,0])))
    if hem>top-.28:return
    b=OriginalSculpt({'id':'hair-rear-v1','palette':recipe['palette']});b.slot='head';b.stage=3
    long_back(b,width*.94,top,max(.32,top-hem),waves=any('wav' in c['part'] for c in loose))
    c=b.commands[-1];v,f=mesh(c);columns=13;rows=3;count=columns*rows
    tri=triangles(face)
    # The upper edge joins the actual cap rather than a floating fixed ellipse.
    # The lower edge retains the selected side locks' haircut length.
    ys=[hem, max(hem+.025,top-.32), top-.12]
    for layer in (0,1):
        for row,y in enumerate(ys):
            for col,angle in enumerate(np.linspace(0,math.pi,columns)):
                index=layer*count+row*columns+col
                direction=np.array([-math.cos(angle),0,-math.sin(angle)])
                origin=np.array([0,y,.005])
                distance=radial_hit(tri,origin,direction)
                if row==2:
                    radius=(distance if distance is not None else .17)+.019
                    v[index]=origin+direction*(radius-layer*.024)
                elif distance is not None:
                    radius=max(float(np.linalg.norm(v[index,[0,2]]-origin[[0,2]])),distance+.019-layer*.024)
                    v[index]=origin+direction*radius
                v[index,1]=y
    c.update(op='indexed_mesh',vertices=v.tolist(),faces=orient_faces(v,f).tolist(),
             material=support[0]['material'],
             hair_rear_revision={'schema_version':1,'hem_y':hem,'method':'loose haircut rear volume with skull-fitted upper edge'})
    recipe['commands']=[x for x in recipe['commands'] if x['part']!='hair_back_curtain']+[c]


def refine_braids(recipe):
    """Long hanging braids use three interwoven strands and tapered loose tips."""
    if recipe.get('hanging_braid_revision'):
        return
    from tools.creature_workshop.geometry import mesh
    from tools.creature_workshop.original_constructor import OriginalSculpt
    from .constructor_portraits import freeze
    groups = {}
    for c in recipe['commands']:
        part = c['part']
        if 'braid' not in part or any(t in part for t in ('crown', 'bun', 'beard', 'mustache', 'fringe', 'sweep', 'face')):
            continue
        v, _ = mesh(c)
        if v[:, 1].min() > 2.45:
            continue
        sign = -1 if v[:, 0].mean() < 0 else 1
        groups.setdefault(sign, []).append(c)
    removed, added = [], []
    for sign, commands in groups.items():
        points = np.concatenate([mesh(c)[0] for c in commands])
        low, top = float(points[:, 1].min()), float(points[:, 1].max())
        if top-low < .23:
            continue
        length = min(.95, max(.72, (top-low)*1.35))
        root = np.mean(points[points[:, 1] > top-.075], axis=0)
        root[1] = top-.025
        b = OriginalSculpt({'id': 'hanging-braid-v1', 'palette': {'skin':'bc9170', 'hair':'544136', **recipe['palette']}})
        b.slot, b.stage = 'head', 3
        material = commands[0]['material']
        # Broad interlacing, kept within the project's low-poly detail budget.
        for strand in range(3):
            path, radii = [], []
            for t in np.linspace(0, 1, 25):
                centre = root + [sign*.035*t, -length*t, (.33-root[2])*t*t]
                angle = t*math.pi*8 + strand*math.tau/3
                radius = .021*(1-.6*t)
                path.append((centre + [math.cos(angle)*radius, 0, math.sin(angle)*radius]).tolist())
                radii.append(.017*(1-.65*t))
            b.tube('braid_woven_strand', material, path, radii, sides=5)
        end = root + [sign*.035, -length, .33-root[2]]
        b.tube('braid_loose_tip', material, [end.tolist(), (end+[sign*.015,-.075,.008]).tolist()], [.025,.003], sides=6)
        tie_material = next((k for k in recipe['palette'] if k.endswith('leather')), material)
        b.tube('braid_end_tie', tie_material, [(end+[0,.012,0]).tolist(), (end+[0,-.008,0]).tolist()], [.027,.026], sides=8)
        new, _ = freeze(b, 'woven_braid_'+str(sign))
        # freeze prefixes palette names; these materials already belong to the
        # selected hair source and must retain their authored color semantics.
        for c, original in zip(new, b.commands, strict=True):
            c['material'] = original['material']
        removed.extend(commands)
        added.extend(new)
    if added:
        recipe['commands'] = [c for c in recipe['commands'] if c not in removed] + added
        recipe['hanging_braid_revision'] = {'schema_version': 1,
            'method': 'three interwoven tapered strands; extended hanging length',
            'removed_source_parts': [c['part'] for c in removed]}
