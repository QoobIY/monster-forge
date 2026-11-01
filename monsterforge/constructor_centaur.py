"""Human upper modules on the fixed centaur authoring layout.

All placement is baked into derived parts. Horse legs retain their source scale.
"""
import copy

import numpy as np

from tools.creature_workshop.geometry import mesh
from tools.creature_workshop.original_constructor import OriginalSculpt

REVISION = 1
UPPER_SLOTS = {'head', 'torso', 'left_arm', 'right_arm'}
ATTRIBUTES = {'male_faces', 'female_faces', 'hair', 'brows', 'eyes', 'noses',
              'ears', 'jaws', 'mouths', 'beards', 'mustaches', 'headwear',
              'male_clothes', 'female_clothes', 'arms', 'gloves', 'shoulders',
              'emblems', 'patterns', 'colorways', 'body_forms'}
SCALE = np.array([.88, .88, .88])
OFFSET = np.array([0., .45, -.10])


def apply(recipe, settings, slot, sources):
    if settings['race'] != 'centaur' or slot not in UPPER_SLOTS:
        return
    from . import workshop_constructor as e
    from .constructor_atlas import apply as atlas
    from .constructor_decor import apply as decorate

    original = copy.deepcopy(recipe['commands'])
    coat = recipe['palette'].get('skin', '705039')
    if slot == 'torso':
        for c in original:
            if c['part'] == 'horse_chest_waist_rump':
                name = c['material']
                recipe['palette']['centaur_coat'] = recipe['palette'][name]
                c['material'] = 'centaur_coat'
    upper, provenance = e._load('library-human-01', slot)
    sources.append(provenance)
    human = copy.deepcopy(settings)
    human.update(race='human', face='library-human-01')
    selected = human['reference_parts']
    # Defaults use the same human library as the ordinary constructor; explicit
    # selections override them without ever replacing the horse carrier.
    variant = recipe['species_design']['variant'] % 3
    if human['hair'].startswith('expansion-centaur-'):
        human['hair'] = 'original'
    if slot == 'head' and not any(selected[k] for k in ('male_faces', 'female_faces')):
        selected[settings['gender'] + '_faces'] = (1, 3, 6)[variant]
    if slot == 'head' and human['hair']=='original' and not selected['hair']:
        selected['hair'] = (2, 6, 9)[variant] if settings['gender']=='female' else (1, 3, 6)[variant]
    if slot != 'head' and not any(selected[k] for k in ('male_clothes', 'female_clothes')):
        selected[settings['gender'] + '_clothes'] = (5, 6, 8)[variant]
    if slot == 'head':
        upper = e._head(upper, human, sources)
    atlas(upper, human, slot)
    ornaments = copy.deepcopy(human)
    for category, field in (('headwear','headwear'), ('beards','beard'),
                            ('mustaches','mustache'), ('shoulders','shoulders'),
                            ('emblems','emblem')):
        if selected[category]:
            ornaments['decor'][field] = 'none'
    # Face/garment selection replaces whole modules, so native accessories must
    # be authored afterwards or a new face silently erases the selected crown.
    decorate(upper, ornaments, slot)
    if slot == 'head':
        from .constructor_helmets import apply as helmet
        from .constructor_head_accessories import apply as headwear
        from .constructor_faceless import apply as faceless
        helmet(upper, human)
        headwear(upper, human)
        faceless(upper, human)
    if slot == 'torso':
        # Remove skirts, hanging trousers and pouches below the human waist.
        # Keep closed volumes; no clipping through triangles or open cut caps.
        upper['commands'] = [c for c in upper['commands']
                             if mesh(c)[0][:, 1].min() >= 1.08 or mesh(c)[0][:, 1].max() >= 1.65]
        for c in upper['commands']:
            v, f = mesh(c)
            v = v.copy()
            lo, hi = v[:, 1].min(), v[:, 1].max()
            if lo < 1.12:
                v[:, 1] = 1.12 + (v[:, 1]-lo) * (hi-1.12)/(hi-lo)
            c.update(op='indexed_mesh', vertices=v.tolist(), faces=f.tolist())
            c.pop('vertex_normals', None)
    commands = [e._transform(c, SCALE, OFFSET, 'centaur-human-upper-v1')
                for c in upper['commands']]
    recipe['palette'].update(upper['palette'])
    if slot == 'torso':
        commands.extend(c for c in original if c['part'] == 'horse_chest_waist_rump')
        # A horse's tall neck and mane are inappropriate beneath a human torso.
        # Short anatomical withers connect the forechest to the human waist.
        b = OriginalSculpt({'id': 'centaur-withers-v1', 'palette': recipe['palette']})
        b.slot = slot
        b.stage = 1
        b.palette['centaur_coat'] = coat
        b.oval('centaur_forechest_withers', 'centaur_coat', [0, 1.43, -.27], [.34, .34, .36], sides=10)
        commands.extend(b.commands)
        recipe['palette'].update(b.palette)
    recipe['commands'] = commands
    for key in ('attribute_references', 'atlas_material_groups'):
        if key in upper:
            recipe[key] = upper[key]
    recipe['centaur_upper'] = {
        'schema_version': 1, 'revision': REVISION,
        'gender': settings['gender'], 'source_commands': [c['id'] for c in original],
        'scale': SCALE.tolist(), 'offset': OFFSET.tolist(),
        'reference_parts': copy.deepcopy(selected),
        'horse_carrier_preserved': slot == 'torso',
    }
    if slot == 'head':
        recipe['contract_anchors'][slot] = (np.array([0, 2.04, .08]) * SCALE + OFFSET).tolist()
    elif slot.endswith('_arm'):
        sign = -1 if slot.startswith('left') else 1
        widths = (.88,1.03,1.10,1.20,.94,.86,.98,1.12,.80,1.18)
        width = widths[selected['body_forms']-1] if selected['body_forms'] else 1
        recipe['contract_anchors'][slot] = (np.array([sign * .36 * width, 1.92, .04]) * SCALE + OFFSET).tolist()
