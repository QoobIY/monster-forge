"""Race-owned frog, slime and satyr anatomy and immutable constructor exports."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from itertools import pairwise
from pathlib import Path

import numpy as np

from monster_forge_sdk.characters import body_rig, load_skeleton
from tools.creature_workshop.geometry import compile_recipe, export_glb, render_png
from tools.creature_workshop.original_constructor import OriginalSculpt

from .paths import ROOT, STYLE_PATH

SOURCE = ROOT / 'media/constructor/marsh_forest/v1'
RACES = {
    'frog': {'label': 'Лягушки', 'neutral': True, 'rig': 'quadruped_v1',
             'gait': 'hop', 'description': 'Четвероногие земноводные с широким ртом, выпуклыми глазами, складными задними ногами и перепонками.'},
    'slime': {'label': 'Жижи', 'neutral': True, 'rig': 'ghost_v1',
              'gait': 'walk', 'description': 'Бесформенные кислотные существа: студенистое ядро, верхняя масса и две боковые лопасти, без человеческих конечностей.'},
    'satyr': {'label': 'Сатиры', 'neutral': True, 'rig': 'humanoid_v1',
              'gait': 'walk', 'description': 'Рогатые лесные существа с заострёнными ушами, шерстяными ногами, скакательными суставами и раздвоенными копытами.'},
}
NAMES = {'frog': ('Болотная лягушка', 'Бородавчатая жаба', 'Королевская лягушка'),
         'slime': ('Кислотная жижа', 'Болотный слизень', 'Жижа с минеральным ядром'),
         'satyr': ('Лесной сатир', 'Проклятый сатир', 'Король сатиров')}
DESIGNS = [{'id': f'native-{race}-{i + 1:02d}', 'label': label, 'race': race,
            'gender': 'male', 'variant': i, 'hair': 'cropped', 'own_body': True,
            'contract': RACES[race]['rig'], 'description_ru': RACES[race]['description']}
           for race, labels in NAMES.items() for i, label in enumerate(labels)]
IDS = {d['id'] for d in DESIGNS}


def encoded(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def immutable(path: Path, blob: bytes) -> None:
    if path.exists():
        if path.read_bytes() != blob:
            raise ValueError(f'Нужна новая ревизия конструктора: {path}')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob)


def options(race: str, gender: str = 'male') -> list[dict]:
    return [d for d in DESIGNS if d['race'] == race and d['gender'] == gender]


class Anatomy(OriginalSculpt):
    """Each authored volume belongs to an explicit permitted bone, never autorig."""

    def __init__(self, design: dict, slot: str, bone: str):
        palette = {'skin': ('638747', '426b38', '628342')[design['variant']],
                   'hair': '48372e', 'eyes': 'dec35f', 'cloth': '4c3c54',
                   'secondary': 'c1c88a', 'accent': 'c2a05c', 'metal': '85715b',
                   'leather': '573e32'}
        if design['race'] == 'slime':
            palette.update(skin=('73a943', '427b53', '588b65')[design['variant']],
                           secondary='c4df77', eyes='e9ef8b', accent='9dd3ae')
        elif design['race'] == 'satyr':
            palette.update(skin=('99734e', '70604e', '78523f')[design['variant']],
                           secondary='403434', eyes='d4b65b', accent='a3bd66')
        super().__init__({'id': design['id'] + '.' + slot, 'palette': palette})
        self.slot, self.stage, self.bone = slot, 2, bone

    def add(self, op, part, material, purpose, **parameters):
        super().add(op, part, material, purpose, **parameters)
        self.commands[-1]['skin_bone'] = self.bone


def frog(b: Anatomy, variant: int) -> None:
    if b.slot == 'torso':
        b.oval('frog_body', 'skin', [0, .65, -.13], [.64, .43, .83], sides=12)
        b.oval('frog_belly', 'secondary', [0, .39, .14], [.51, .20, .59], sides=10)
        for side in (-1, 1):
            for i in range(3 + variant):
                b.oval('frog_wart', 'shadow', [side * .38, .99 - .03 * (i % 2), -.57 + i * .22],
                       [.07 + .015 * variant, .045, .085])
    elif b.slot == 'head':
        b.oval('frog_broad_head', 'skin', [0, .76, .80], [.71, .29, .57], sides=12)
        b.oval('frog_lower_jaw', 'secondary', [0, .55, 1.03], [.60, .12, .37], sides=12)
        b.oval('frog_mouth', 'dark', [0, .64, 1.29], [.59, .022, .08], sides=12)
        for side in (-1, 1):
            x = side * .46
            b.oval('frog_eye_socket', 'skin', [x, 1.0, .86], [.20, .22, .21], sides=10)
            b.oval('frog_eye', 'eyes', [x, 1.02, 1.03], [.14, .15, .055], sides=10)
            b.oval('frog_pupil', 'pupil', [x, 1.02, 1.08], [.036, .105, .016])
            b.oval('frog_nostril', 'dark', [side * .17, .88, 1.31], [.025, .02, .017])
        if variant == 2:
            b.loft('frog_crown_band', 'metal', [[1.04, 0, .54, .28, .19], [1.16, 0, .54, .29, .20]])
            for x in (-.22, 0, .22):
                b.tube('frog_crown_tip', 'accent', [[x, 1.13, .56], [x, 1.43 if x == 0 else 1.34, .56]], [.07, .004])
    elif b.slot == 'tail':
        # The quadruped contract owns a tail slot. Its tiny volume stays inside
        # the rump; an adult frog has no visible tail.
        b.oval('frog_internal_tail_root', 'skin', [0, .68, -.51], [.015] * 3)
    else:
        side = -1 if 'left' in b.slot else 1
        front = b.slot.startswith('front')
        prefix = ('front_' if front else 'hind_') + ('left' if side < 0 else 'right')
        hip = [side * .48, .64, .64 if front else -.48]
        knee = [side * (.73 if front else .87), .32, .80 if front else -.74]
        foot = [side * .66, .09, 1.07 if front else -.05]
        b.bone = prefix
        if not front:
            b.oval('frog_folded_thigh', 'skin', [side * .69, .43, -.54], [.28, .25, .39], sides=10)
        b.tube('frog_upper_limb', 'skin', [hip, knee], [.12 if front else .18, .09 if front else .12])
        b.bone = prefix + '_knee'
        b.tube('frog_lower_limb', 'skin', [knee, foot], [.09, .06])
        b.bone = prefix + '_foot'
        b.oval('frog_palm', 'skin', foot, [.16, .065, .21])
        toes = [[foot[0] + (i - 1.5) * .10, .025, foot[2] + .32 + (.07 if i in (1, 2) else 0)]
                for i in range(4)]
        for a, c in pairwise(toes):
            top = [foot, a, c]
            vertices = top + [[p[0], p[1] - .01, p[2]] for p in top]
            b.solid('frog_webbing', 'secondary', vertices,
                    [[0, 1, 2], [5, 4, 3], [0, 3, 1], [1, 3, 4],
                     [1, 4, 2], [2, 4, 5], [2, 5, 0], [0, 5, 3]],
                    'Перепонка между соседними пальцами')
        for toe in toes:
            b.tube('frog_toe', 'skin', [foot, toe], [.028, .018])
            b.oval('frog_toe_pad', 'secondary', toe, [.045, .025, .05])


def slime(b: Anatomy, variant: int) -> None:
    if b.slot == 'torso':
        b.loft('slime_body', 'skin', [[0, 0, 0, .64, .55], [.13, 0, 0, .76, .64],
                                   [.47, -.05, -.06, .62, .53], [.80, .06, -.04, .37, .31],
                                   [1.02, .10, -.04, .11, .10]], sides=12)
        for i, (x, y, z) in enumerate(((-.25, .42, .38), (.22, .25, .49), (0, .65, .24))):
            b.oval('slime_surface_bubble', 'secondary', [x, y, z], [.09 + .02 * variant] * 3)
            if variant == 2:
                b.tube('slime_mineral', 'accent', [[x, y, z], [x, y + .22, z]], [.08, .005])
    elif b.slot == 'head':
        b.oval('slime_upper_lobe', 'skin', [0, .78, .20], [.38, .24, .34], sides=10)
        for side in (-1, 1):
            b.oval('slime_eye', 'eyes', [side * .16, .81, .51], [.09, .075, .035])
            b.oval('slime_pupil', 'pupil', [side * .16, .81, .54], [.028, .05, .015])
        b.oval('slime_mouth', 'dark', [0, .64, .49], [.10, .035, .035])
    else:
        side = -1 if b.slot.startswith('left') else 1
        b.oval('slime_pseudopod', 'skin', [side * .59, .19, .08], [.37, .19, .43], sides=10)
        b.oval('slime_outer_lobe', 'secondary', [side * .80, .12, .20], [.17, .12, .21])


def satyr(b: Anatomy, variant: int) -> None:
    if b.slot == 'torso':
        b.bone = 'pelvis'
        b.oval('satyr_fur_hips', 'secondary', [0, 1.01, 0], [.28, .21, .20])
        b.bone = 'chest'
        b.loft('satyr_chest', 'skin', [[1.1, 0, .01, .23, .17], [1.47, 0, .03, .34, .21],
                                    [1.73, 0, .05, .31, .18]], sides=10)
        b.oval('satyr_breast_fur', 'secondary', [0, 1.58, .20], [.22, .18, .055])
        b.bone = 'neck'
        b.tube('satyr_neck', 'skin', [[0, 1.72, .08], [0, 2.0, .09]], [.13, .12])
        b.bone = 'pelvis'
        b.loft('satyr_belt', 'leather', [[1.05, 0, 0, .28, .21], [1.15, 0, 0, .27, .20]])
        b.box('satyr_buckle', 'metal', [0, 1.10, .22], [.09, .07, .025])
    elif b.slot == 'head':
        b.oval('satyr_skull', 'skin', [0, 2.20, .10], [.22, .27, .21], sides=10)
        b.oval('satyr_goat_muzzle', 'skin', [0, 2.09, .29], [.14, .12, .17])
        for side in (-1, 1):
            b.tube('satyr_pointed_ear', 'skin', [[side * .18, 2.23, .07], [side * .38, 2.34, .03]], [.075, .005])
            b.oval('satyr_eye', 'eyes', [side * .10, 2.26, .28], [.052, .034, .023])
            b.oval('satyr_pupil', 'pupil', [side * .10, 2.26, .30], [.014, .024, .009])
            height = (.27, .39, .50)[variant]
            b.tube('satyr_horn', 'bone', [[side * .15, 2.39, .02], [side * .27, 2.53, -.10],
                   [side * .30, 2.44 + height, -.23], [side * .19, 2.45 + height, -.30]], [.075, .06, .035, .003], sides=9)
        b.tube('satyr_goatee', 'secondary', [[0, 2.04, .34], [0, 1.88, .28]], [.07, .003])
        if variant == 2:
            b.loft('satyr_crown', 'metal', [[2.39, 0, .08, .22, .18], [2.46, 0, .08, .23, .18]])
            for x in (-.13, 0, .13):
                b.tube('satyr_crown_thorn', 'accent', [[x, 2.44, .24], [x, 2.59, .22]], [.035, .002])
    elif b.slot.endswith('_arm'):
        side = -1 if b.slot.startswith('left') else 1
        prefix = 'left' if side < 0 else 'right'
        b.bone = prefix + '_shoulder'
        b.tube('satyr_upper_arm', 'skin', [[side * .36, 1.8, .04], [side * .72, 1.36, .02]], [.13, .10])
        b.bone = prefix + '_elbow'
        b.tube('satyr_forearm', 'skin', [[side * .72, 1.36, .02], [side * .82, .96, .08]], [.10, .065])
        b.bone = prefix + '_hand'
        b.oval('satyr_hand', 'skin', [side * .82, .93, .10], [.09, .12, .07])
        for i in range(3):
            x = side * .82 + (i - 1) * .045
            b.tube('satyr_claw', 'bone', [[x, .89, .15], [x, .78, .20]], [.019, .003])
    else:
        side = -1 if b.slot.startswith('left') else 1
        prefix = 'left' if side < 0 else 'right'
        b.bone = prefix + '_hip'
        b.tube('satyr_furred_thigh', 'secondary', [[side * .22, .95, 0], [side * .28, .50, .02]], [.17, .12])
        b.bone = prefix + '_knee'
        b.tube('satyr_hock', 'secondary', [[side * .28, .50, .02], [side * .32, .22, -.09],
               [side * .32, .12, .16]], [.105, .075, .065])
        b.bone = prefix + '_foot'
        for toe in (-1, 1):
            b.box('satyr_split_hoof', 'dark', [side * .32 + toe * .049, .075, .20], [.088, .15, .23])


def publish_sources() -> None:
    """Freeze new selectable parts; repeated runs verify, never overwrite sources."""
    for design in DESIGNS:
        spec = RACES[design['race']]
        rig = body_rig(spec['rig'], root=ROOT)
        folder = SOURCE / design['id']
        parts = {}
        arrays = []
        for slot in rig['slots']:
            b = Anatomy(design, slot['id'], slot['bones'][0])
            {'frog': frog, 'slime': slime, 'satyr': satyr}[design['race']](b, design['variant'])
            recipe = b.recipe()
            recipe.update(assembly_reference=spec['rig'], bind_profile='canonical',
                          constructor_anatomy=design, team_materials=['cloth'])
            recipe['commands'].sort(key=lambda c: c['stage'])
            array = compile_recipe(recipe)
            arrays.append(array)
            model = folder / 'parts' / (slot['id'] + '.glb')
            model.parent.mkdir(parents=True, exist_ok=True)
            if model.exists():
                from .workshop_constructor import _glb_arrays
                if any(not np.array_equal(a, c) for a, c in zip(_glb_arrays(model.read_bytes()), array[:3], strict=True)):
                    raise ValueError('Нужна ревизия исходной анатомии')
            else:
                export_glb(model, array, recipe)
            immutable(model.with_suffix('.recipe.json'), encoded(recipe))
            parts[slot['id']] = {'model': f'parts/{slot["id"]}.glb',
                                 'recipe': f'parts/{slot["id"]}.recipe.json',
                                 'sha256': digest(model.read_bytes())}
        immutable(folder / 'parts.json', encoded({'schema_version': 1,
                  'coordinates': 'metres; Y up; +Z forward; floor Y=0',
                  'rig_reference': spec['rig'], 'parts': parts}))
        immutable(folder / 'record.json', encoded({'schema_version': 1, **design, 'rig': spec['rig']}))
        for category, slots in {'face': ['head'], 'outfit': [s['id'] for s in rig['slots']],
                                'arms': [s['id'] for s in rig['slots'] if '_arm' in s['id'] or s['id'].startswith('front') or s['id'] == 'left_wisp'],
                                'legs': [s['id'] for s in rig['slots'] if s['id'].endswith('_leg') or s['id'].startswith('hind') or s['id'] == 'right_wisp']}.items():
            selected = [array for slot, array in zip(rig['slots'], arrays, strict=True) if slot['id'] in slots]
            merged = tuple(np.concatenate([a[i] for a in selected]) for i in range(3)) + ([],)
            card = folder / (category + '.png')
            render_png(card, merged, size=256)


def validate(settings: dict) -> dict:
    from .workshop_constructor import default_settings
    defaults = default_settings()
    if set(settings) != set(defaults) or settings['schema_version'] != 5 or type(settings['schema_version']) is not int:
        raise ValueError('Нужны полные настройки schema_version=5')
    donors = {d['id'] for d in options(settings['race'])}
    if any(not isinstance(settings[k], str) or settings[k] not in donors for k in ('face', 'outfit', 'arms', 'legs')):
        raise ValueError('Детали должны принадлежать выбранному виду')
    fixed = ('gender', 'hair', 'form', 'back', 'eye_size', 'eye_shape', 'decor', 'features', 'reference_parts')
    if isinstance(settings['eye_size'], bool) or any(settings[k] != defaults[k] for k in fixed):
        raise ValueError('Выбирайте собственные детали вида; humanoid-настройки несовместимы')
    colors = settings['colors']
    if not isinstance(colors, dict) or set(colors) != set(defaults['colors']):
        raise ValueError('Неполный набор цветов')
    for value in colors.values():
        if value is not None and (not isinstance(value, str) or re.fullmatch(r'#[0-9a-fA-F]{6}', value) is None):
            raise ValueError('Цвет должен быть #RRGGBB или null')
    return copy.deepcopy(settings)


def build(settings: dict, target: Path, *, weights: bool = False) -> dict:
    from .workshop_constructor import _load
    spec = RACES[settings['race']]
    rig = body_rig(spec['rig'], root=ROOT)
    skeleton = load_skeleton('canonical', root=ROOT) if spec['rig'] == 'humanoid_v1' else rig
    skeleton_hash = digest(encoded(skeleton))
    target.mkdir(parents=True, exist_ok=True)
    (target / 'skeleton.json').write_bytes(encoded(skeleton))
    names = [b['id'] for b in skeleton['bones']]
    parts, arrays = {}, []
    for slot in rig['slots']:
        key = slot['id']
        field = ('face' if key == 'head' else 'arms' if key.endswith('_arm') or key.startswith('front') or key == 'left_wisp'
                 else 'legs' if key.endswith('_leg') or key.startswith('hind') or key == 'right_wisp' else 'outfit')
        donor = settings[field]
        recipe, source = _load(donor, key)
        from .constructor_satyr import apply as refine_satyr
        refine_satyr(recipe,key)
        from .constructor_hand_orientation import apply as orient_hand
        orient_hand(recipe,key)
        for material, color in settings['colors'].items():
            if color and material in recipe['palette']:
                recipe['palette'][material] = color.lstrip('#')
        recipe['constructor'] = {'schema_version': 1, 'slot': key, 'settings': settings,
                                 'sources': [{k: v for k, v in source.items() if k not in {'recipe', 'record'}}],
                                 'style_sha256': digest(STYLE_PATH.read_bytes())}
        recipe['id'] = 'constructor.' + digest(encoded(recipe)) + '.' + key
        array = compile_recipe(recipe)
        arrays.append(array)
        folder = target / 'parts' / key
        folder.mkdir(parents=True, exist_ok=True)
        model = folder / 'model.glb'
        export_glb(model, array, recipe)
        (folder / 'recipe.json').write_bytes(encoded(recipe))
        (folder / 'sources.json').write_bytes(encoded(source))
        info = {'revision_id': digest(encoded(recipe)), 'slot': key, 'model': f'parts/{key}/model.glb',
                'model_sha256': digest(model.read_bytes()), 'triangles': len(array[0]) // 3,
                'bounds_metres': [array[0].min(0).tolist(), array[0].max(0).tolist()]}
        if weights:
            indices, begin = [], 0
            for command, end in zip(recipe['commands'], array[3], strict=True):
                bone = command['skin_bone']
                if bone not in slot['bones']:
                    raise ValueError(f'Кость {bone} несовместима со слотом {key}')
                indices.extend([[names.index(bone), 0, 0, 0] for _ in range(end - begin)])
                begin = end
            sidecar = {'schema_version': 1, 'skeleton_id': spec['rig'], 'bind_profile': 'canonical',
                       'gait': spec['gait'], 'slot': key, 'bone_palette': names,
                       'allowed_bones': slot['bones'], 'model_sha256': info['model_sha256'],
                       'vertex_count': len(array[0]), 'skin_indices': indices,
                       'skin_weights': [[1., 0., 0., 0.] for _ in indices]}
            (folder / 'weights.json').write_bytes(encoded(sidecar))
            info.update(weights=f'parts/{key}/weights.json', weights_sha256=digest(encoded(sidecar)))
        parts[key] = info
    selection = {'schema_version': 1, 'skeleton_id': spec['rig'], 'bind_profile': 'canonical',
                 'skeleton_sha256': skeleton_hash,
                 'parts': {k: {'revision_id': p['revision_id'], 'model_sha256': p['model_sha256']} for k, p in parts.items()}}
    selection['id'] = digest(encoded(selection))
    (target / 'assembly.json').write_bytes(encoded(selection))
    manifest = {'schema_version': 1, 'id': selection['id'], 'contract': spec['rig'],
                'bind_profile': 'canonical', 'skeleton': 'skeleton.json', 'skeleton_sha256': skeleton_hash,
                'bind_bones': [], 'parts': parts, 'triangles': sum(p['triangles'] for p in parts.values()),
                'status': 'authoring_draft', 'warnings': [],
                'checks': {'finite_geometry': all(np.isfinite(a[0]).all().item() for a in arrays),
                           'source_hashes': True, 'weight_sidecars': weights}}
    (target / 'manifest.json').write_bytes(encoded(manifest))
    if weights:
        merged = tuple(np.concatenate([a[i] for a in arrays]) for i in range(3)) + ([],)
        render_png(target / 'preview.png', merged, size=512)
    (target / 'integrity.json').write_bytes(encoded({'schema_version': 1, 'files': {
        str(p.relative_to(target)): digest(p.read_bytes()) for p in sorted(target.rglob('*')) if p.is_file() and p.name != 'integrity.json'}}))
    return manifest
