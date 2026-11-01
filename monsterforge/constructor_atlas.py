"""Immutable, manually authored low-poly volumes guided by Front references.

This is a geometry authoring library, never an image-to-3D service or a rig.
Every selection is baked into the existing slot recipe and skeleton contract.
"""
import copy
import hashlib
import json
from functools import lru_cache
import numpy as np
from .paths import ROOT

SOURCE=ROOT/'media/constructor/attribute_references/v1'
LIBRARY=ROOT/'media/constructor/attribute_sculpts/v26'
HAIR_EXPANSION=ROOT/'media/constructor/attribute_sculpts/v35'
HAIR_EXTENSIONS=ROOT/'media/constructor/attribute_sculpts/v30'
BEARD_REFINEMENTS=ROOT/'media/constructor/attribute_sculpts/v32'
SIDEBURN_REFINEMENTS=ROOT/'media/constructor/attribute_sculpts/v33'
HAIR_LABELS={11:'Короткий кроп',12:'Боковой пробор',13:'Зачёс назад',14:'Короткие кудри',15:'Низкий пучок',
             16:'Пикси с чёлкой',17:'Волнистое каре',18:'Две косы',19:'Двойной пучок',20:'Коса вокруг головы'}

HAIR_LABELS.update({2:'Каре с мягкой косой чёлкой',21:'Короткая стрижка с фейдом',22:'Объёмный квифф',23:'Шторки с центральным пробором',24:'Небрежная стрижка до ушей',25:'Воин · собранные длинные волосы',26:'Длинные волны с пробором',27:'Высокий хвост с чёлкой',28:'Боковая плетёная коса',29:'Французское каре',30:'Плетёный низкий пучок'})

def part_folder(category,number):
    if category=='hair' and (number==2 or number>=21):return HAIR_EXPANSION/category/f'{number:02d}'
    if category=='beards' and number in {3,4}:return BEARD_REFINEMENTS/category/f'{number:02d}'
    if category=='beards' and number in {9,10}:return SIDEBURN_REFINEMENTS/category/f'{number:02d}'
    root=HAIR_EXTENSIONS if category=='hair' and number>10 else LIBRARY
    return root/category/f'{number:02d}'
RACE_ORDER=('human','elf','orc','minotaur','wolf','skeleton','angel','demon','boarfolk','elephantfolk')
HEAD_CATEGORIES={'male_faces','female_faces','hair','brows','eyes','noses','ears','jaws','mouths','beards','mustaches','race_heads','headwear'}

def defaults():
    return {e['id']:0 for e in json.loads((SOURCE/'requests.json').read_text())['entries']}

def available(category,race,gender):
    if race=='centaur':
        from .constructor_centaur import ATTRIBUTES
        return available(category,'human',gender) if category in ATTRIBUTES else []
    if race=='ghost':return list(range(1,31)) if category=='hair' else []
    if race=='goblin':
        if category in {'gloves','boots'}:return [1,2,3]
        if category in {'ears','race_heads','male_faces','female_faces','jaws','brows','eyes','noses','mouths','beards','mustaches'}:return []
        return available(category,'human',gender)
    if race not in {'human','elf','orc','minotaur','wolf','skeleton','angel','demon','boarfolk','elephantfolk','mutant','undead','gargoyle','tentaclefolk'}:return []
    if category=='race_heads':return [RACE_ORDER.index(race)+1] if race in RACE_ORDER else []
    if category in {'male_faces','female_faces','jaws','brows','eyes','noses','mouths'} and race not in {'human','elf','angel','demon','undead'}:return []
    if category in {'male_faces','male_clothes'} and gender!='male':return []
    if category in {'female_faces','female_clothes'} and gender!='female':return []
    if race=='skeleton' and category in {'hair','ears','beards','mustaches'}:return []
    if category=='hair':return [*range(1,11),*(range(16,21) if gender=='female' else range(11,16)),*(range(26,31) if gender=='female' else range(21,26))]
    return list(range(1,11))

def catalog():
    return [{'id':e['id'],'label':e['label'],'count':30 if e['id']=='hair' else 10} for e in json.loads((SOURCE/'requests.json').read_text())['entries']]

COLORWAYS=(
 ('4b653f','ddd0af','a79b65','705039'),('762f3d','d0a24f','999ca0','49352c'),
 ('304e70','d6c18d','999da2','3a302c'),('b4a07c','e0d5bd','b88059','95724f'),
 ('32373c','b67d5e','939ba0','44322c'),('6a405e','d2bb83','b6b7b9','6c4b36'),
 ('e1d8bd','3b62a2','c3a45e','95714c'),('328d93','d27b69','a67f58','674a32'),
 ('a65b3b','39716e','b97c51','4a342b'),('9cb9ce','e1dfd2','b7bfc7','61646a'))

def color_overrides(settings):
    n=settings.get('reference_parts',{}).get('colorways',0)
    if not n:return {}
    return dict(zip(('cloth','accent','metal','leather'),('#'+c for c in COLORWAYS[n-1])))

def presets():
    from .constructor_presets import load_presets
    return load_presets('attribute')


@lru_cache(maxsize=270)
def load(category,number):
    p=part_folder(category,number)/'recipe.json'
    recipe=json.loads(p.read_text())
    if recipe.get('schema_version')!=1 or recipe.get('coordinate_system')!='metres; Y up; +Z forward; floor Y=0':raise ValueError('Incompatible attribute geometry schema')
    if recipe['attribute_reference']['category']!=category or recipe['attribute_reference']['variant']!=number:raise ValueError('Attribute source identity mismatch')
    integrity_path=p.parent/'integrity.json'
    if integrity_path.exists():
        integrity=json.loads(integrity_path.read_text())
        if integrity.get('schema_version') not in {1,2}:raise ValueError('Incompatible attribute integrity schema')
        for name,digest in integrity['files'].items():
            item=(p.parent/name).resolve()
            if not item.is_relative_to(p.parent.resolve()):raise ValueError('Immutable attribute mesh changed; author a new revision')
            from .constructor_cache import resolve
            if hashlib.sha256(resolve(item).read_bytes()).hexdigest()!=digest:raise ValueError('Immutable attribute mesh changed; author a new revision')
        recipe['attribute_reference']['source_files']=integrity['files']
    ref=SOURCE/category/'front.png'
    if recipe['attribute_reference']['image_sha256']!=hashlib.sha256(ref.read_bytes()).hexdigest():raise ValueError('Attribute reference changed; author a new revision')
    return recipe

def _commands(category,number,slot):
    recipe=load(category,number)
    commands=copy.deepcopy([c for c in recipe['commands'] if c['slot']==slot])
    palette=copy.deepcopy(recipe['palette']);ref=copy.deepcopy(recipe['attribute_reference'])
    # Refine material semantics in the derived revision without altering the
    # frozen observed geometry. Sclera/pupil and bare hands must not be dyed as
    # iris or glove leather.
    for name,color in palette.items():
        if ref.get('method')=='manual_low_poly_volumes':continue
        r,g,b=bytes.fromhex(color);value=(r+g+b)/3;chroma=max(r,g,b)-min(r,g,b)
        group=ref['material_groups'][name]
        if category=='eyes':
            group='fixed' if value<65 or chroma<26 and value>110 else 'skin' if r>g*1.10 and g>b*1.10 and value>125 else 'eyes'
        elif category=='gloves' and number in {1,8,9,10}:
            group='skin' if number in {1,9} or g>r*1.06 else group
        elif category=='boots' and number in {8,9}:
            group='skin' if number==9 and value>130 or number==8 and g>r*1.06 else group
        ref['material_groups'][name]=group
    ref['material_semantics_revision']=2
    return commands,palette,ref

def apply(recipe,settings,slot):
    selected=settings.get('reference_parts',{})
    used=[]
    def append(category,replace=None):
        n=selected.get(category,0)
        if not n:return False
        commands,palette,ref=_commands(category,n,slot)
        if not commands:return False
        previous=[c for c in recipe['commands'] if replace is not None and replace(c)]
        # Placement is baked in this new module revision. The assembly never
        # carries a calibration offset, and sole planes never move vertically.
        if previous and category in {'gloves','boots','shoulders'}:
            from tools.creature_workshop.geometry import mesh
            old=np.concatenate([mesh(c)[0] for c in previous]);new=np.concatenate([mesh(c)[0] for c in commands])
            dx=(old[:,0].min()+old[:,0].max()-new[:,0].min()-new[:,0].max())*.5
            dy=0 if category=='boots' else old[:,1].max()-new[:,1].max()
            if category=='gloves':
                def wrist(items):
                    for c in items:
                        meta=c.get('limb_proportions',c.get('authored_primitive',{}).get('limb_proportions',{}))
                        if meta.get('region')=='hand':return np.asarray(meta['wrist'])
                a,b=wrist(previous),wrist(commands)
                if a is not None and b is not None:dx,dy=(a-b)[:2]
            for c in commands:
                v=np.asarray(c['vertices']);v+=np.array([dx,dy,0]);c['vertices']=v.tolist()
                c['attachment_revision']={'schema_version':1,'method':'baked attachment to selected source part','offset_metres':[float(dx),float(dy),0]}
        if replace is not None:recipe['commands'][:]=[c for c in recipe['commands'] if not replace(c)]
        recipe['commands'].extend(commands);recipe['palette'].update(palette);used.append(ref)
        return True
    if slot=='head':
        replaced=False
        for category in ('race_heads','male_faces','female_faces'):
            preserve_racial=category!='race_heads' and settings['race'] in {'elf','demon'}
            replaced=append(category,lambda c: not(preserve_racial and any(t in c['part'] for t in ('anatomy_ear','racial_horn')))) or replaced
        if replaced:
            # Explicit native feature controls also edit the chosen reference
            # head. Its profile defaults preserve the reference design.
            from .constructor_portraits import ear,nose,eyebrows,mouth,freeze
            from .constructor_decor import sculpt
            from .constructor_face_fit import jaw
            features=settings['features'];b=sculpt(settings);b.slot='head';b.stage=2
            native={'nose':('noses',('nose','nasal','nostril')),'ears':('ears',('ear',)),'brows':('brows',('brow',)),'mouth':('mouths',('mouth','lip','tooth','teeth','fang'))}
            for key,(category,terms) in native.items():
                value=features[key]
                if value in ('profile','original') or selected.get(category):continue
                recipe['commands'][:]=[c for c in recipe['commands'] if not any(t in c['part'] for t in terms)]
                if key=='nose':nose(b,value,settings['race'],0)
                elif key=='ears':ear(b,value,settings['race'],.22,0)
                elif key=='brows':eyebrows(b,value,0)
                else:mouth(b,value,settings['race'],0)
            commands,palette=freeze(b,'reference_native_features');recipe['commands'].extend(commands);recipe['palette'].update(palette)
            native_jaw=features['jaw']
            if native_jaw not in ('profile','original') and not selected.get('jaws'):
                jaw(recipe,{'soft':3,'square':1,'tapered':4,'broad':5,'long':6,'short':7,'cleft':10,'heavy':1,'gaunt':9,'asymmetric':8}[native_jaw])
        if selected.get('jaws'):
            from .constructor_face_fit import jaw
            jaw(recipe,selected['jaws']);used.append(copy.deepcopy(load('jaws',selected['jaws'])['attribute_reference']))
        if selected.get('noses') or (replaced and settings['features']['nose'] not in ('profile','original')):
            from .constructor_head_topology import flatten_nose
            flatten_nose(recipe)
        if replaced and settings['hair']=='bald':recipe['commands'][:]=[c for c in recipe['commands'] if 'hair' not in c['part']]
        for category,terms in [('hair',('hair','braid','mane','topknot','quiff')),('brows',('brow',)),('eyes',('eye','iris','pupil')),('noses',('nose','nasal','nostril')),('ears',('ear',)),('mouths',('mouth','lip','tooth','teeth','fang')),('beards',('beard',)),('mustaches',('mustache',)),('headwear',('headwear','helmet','crown','hat','circlet'))]:
            append(category,lambda c,terms=terms,category=category:
                   any(t in c['part'] for t in terms) and
                   not (category=='headwear' and ('hair_' in c['part'] or 'scalp' in c['part'])))
        if (replaced or selected.get('eyes')) and (settings['eye_size']!=1 or settings['eye_shape']!='original'):
            from .workshop_constructor import EYE_PROPORTIONS
            from tools.creature_workshop.geometry import mesh
            for side in (-1,1):
                eye_commands=[c for c in recipe['commands'] if any(t in c['part'] for t in ('eye','iris','pupil')) and 'brow' not in c['part'] and float(mesh(c)[0][:,0].mean())*side>0]
                openings=[mesh(c)[0].mean(0) for c in eye_commands if 'aperture' in c['part']]
                if not openings:continue
                center=np.mean(openings,axis=0);scale=np.array([settings['eye_size']*EYE_PROPORTIONS[settings['eye_shape']][0],settings['eye_size']*EYE_PROPORTIONS[settings['eye_shape']][1],1])
                for c in eye_commands:
                    v,f=mesh(c);c.update(op='indexed_mesh',vertices=((v-center)*scale+center).tolist(),faces=f.tolist());c.pop('vertex_normals',None)
        if replaced or any(selected.get(k) for k in ('jaws','eyes','mouths','brows','noses')):
            from .constructor_face_fit import attach
            attach(recipe)
    else:
        for category in ('male_clothes','female_clothes'):
            # Clothing sheets contain all five independent body modules.
            append(category,lambda c:True)
        if slot=='torso' and any(selected.get(k) in {1,2} for k in ('male_clothes','female_clothes')):
            recipe['commands'][:]=[c for c in recipe['commands'] if not c['part'].endswith('chest_emblem')]
        if slot.endswith('_arm'):
            append('arms',lambda c:True)
            if settings['race']!='goblin':append('gloves',lambda c:any(t in c['part'] for t in ('palm','thumb','hand','glove')))
            append('shoulders',lambda c:'shoulder' in c['part'])
            if not selected.get('shoulders') and settings['decor']['shoulders']=='none':
                recipe['commands'][:]=[c for c in recipe['commands'] if not
                    (any(t in c['part'] for t in ('pauldron','epaulet','ornament_shoulder_')) or
                     'shoulder' in c['part'] and any(t in c['part'] for t in ('plate','armor','pad','guard')))]
        if slot.endswith('_leg'):
            append('legs',lambda c:True)
            if settings['race']!='goblin':append('boots',lambda c:any(t in c['part'] for t in ('boot','foot','shoe')))
        if slot=='torso':
            append('belts',lambda c:'ornament_belt' in c['part'])
            append('emblems',lambda c:'ornament_badge' in c['part'])
            append('accessories')
        if slot=='back_attachment':append('back',lambda c:True)
    if selected.get('body_forms') and slot!='head':
        # Only transverse proportions change: both sole planes remain Y=0.
        widths=(.88,1.03,1.10,1.20,.94,.86,.98,1.12,.80,1.18)
        factor=widths[selected['body_forms']-1]
        from tools.creature_workshop.geometry import mesh
        for c in recipe['commands']:
            v,f=mesh(c);v=v.copy()
            if slot.endswith('_leg'):
                from .constructor_knees import world_bind
                center=world_bind()[slot.split('_')[0]+'_knee'][0]
                v[:,0]=center+(v[:,0]-center)*factor
            else:v[:,0]*=factor
            c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist());c.pop('vertex_normals',None)
    # Preserve broad tonal variations when using user-selected material colours.
    material_groups=recipe.get('atlas_material_groups',{})
    for ref in used:
        for name,group in ref['material_groups'].items():material_groups[name]=group
    colors={**color_overrides(settings),**{k:v for k,v in settings['colors'].items() if v}}
    for name,group in material_groups.items():
        color=colors.get(group)
        if color and name in recipe['palette']:
            old=np.array(list(bytes.fromhex(recipe['palette'][name])))
            rgb=np.array(list(bytes.fromhex(color.lstrip('#'))))
            manual=any(ref.get('method')=='manual_low_poly_volumes' and name in ref['material_groups'] for ref in used)
            intensity=(.63 if name.endswith('_shadow') else .72 if name.endswith('_lip') else 1.16 if name.endswith('_hair_light') else 1.0) if manual else np.clip(np.mean(old)/150,.50,1.25)
            recipe['palette'][name]=''.join(f'{int(v):02x}' for v in np.clip(rgb*intensity,0,255))
    pattern=selected.get('patterns',0)
    for category in ('body_forms','patterns','colorways'):
        if selected.get(category) and slot!='head':used.append(copy.deepcopy(load(category,selected[category])['attribute_reference']))
    if used:
        recipe['attribute_references']=used
        recipe['atlas_material_groups']=material_groups
    if slot in {'torso','left_arm','right_arm','left_leg','right_leg'}:
        from .constructor_elemental_runes import ELEMENTS
        native={**{k:e['number'] for k,e in ELEMENTS.items()},'runes':8,'edged':1,'chevron':6,'rays':3,'diamonds':1,'scales':10,
                'ancient_runes':11,'elven_runes':12,'demonic_runes':13}.get(settings['decor']['pattern'],0)
        if pattern or native:
            from .constructor_cloth_motifs import apply as apply_motifs
            recipe['selected_pattern_color']=colors.get('secondary') or colors.get('accent') or ELEMENTS.get(settings['decor']['pattern'],{}).get('color','#caa454')
            apply_motifs(recipe,pattern or native,slot)
    recipe['commands'].sort(key=lambda c:c['stage'])
    return recipe
