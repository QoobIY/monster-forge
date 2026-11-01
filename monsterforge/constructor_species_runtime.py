"""Static authoring assembly for explicitly supported non-humanoid layouts."""
import copy

import numpy as np

from tools.creature_workshop.constructor_species import CONTRACTS as LEGACY_CONTRACTS
from tools.creature_workshop.geometry import (
    compile_recipe,
    export_glb,
    mesh,
    render_png,
)

from .constructor_expansion import CONTRACTS as EXP_CONTRACTS
from .constructor_expansion import IDS as EXP_IDS
from .constructor_flyers import CONTRACTS as FLYER_CONTRACTS

CONTRACTS={**LEGACY_CONTRACTS,**FLYER_CONTRACTS,**EXP_CONTRACTS}



def prepare_head(recipe,settings,sources):
    from . import workshop_constructor as e
    if settings['race'] in e.FLYER_SPECIES or settings['face'] in EXP_IDS:return recipe
    if settings['race'] in {'spider','scorpion'}:
        if settings['hair']=='bald':return recipe
        donor=settings['face'] if settings['hair']=='original' else settings['hair']
        number=int(donor.rsplit('-',1)[-1])-1
        from .constructor_portraits import builder, freeze
        b=builder(recipe);b.stage=3
        for i in range(1+number%5):
            x=(i-(number%5)/2)*.055
            if number%3==0:b.tube('hair_carapace_crest','accent',[[x,.77,.44],[x,.90+(i%2)*.03,.42]],[.029,.002],sides=5)
            elif number%3==1:b.oval('hair_carapace_node','accent',[x,.80,.42],[.04,.042,.045],sides=6)
            else:b.panel3('hair_carapace_fin','accent',[[x-.023,.77,.41],[x+.023,.77,.41],[x+.018,.88,.44],[x-.018,.87,.44]],.018)
        commands,palette=freeze(b,'species_crest');recipe['commands'].extend(commands);recipe['palette'].update(palette)
        recipe['crest_revision']={'schema_version':1,'variant':number+1};return recipe
    if settings['hair']!='original':
        recipe['commands']=[c for c in recipe['commands'] if not e._is_hair(c)]
        if settings['hair']!='bald':
            hr,source=e._load(settings['hair'],'head');sources.append(source)
            materials={k:'species_hair_'+k for k in hr['palette']};recipe['palette'].update({materials[k]:v for k,v in hr['palette'].items()})
            for original in hr['commands']:
                if e._is_hair(original):
                    c=copy.deepcopy(original);c['material']=materials[c['material']];c['id']='species_hair_'+c['id'];recipe['commands'].append(c)
    return recipe


def build(settings,target,*,weights=False):
    from . import workshop_constructor as e
    contract=e.SPECIES[settings['race']][1];slots=CONTRACTS[contract]
    choices={slot:settings['outfit'] for slot in slots};choices['head']=settings['face']
    if contract=='quadruped_authoring_v1' or contract in {'dragon_authoring_v1','dragon_flight_authoring_v1'}:
        for slot in slots:
            if slot.startswith('front_'):choices[slot]=settings['arms']
            if slot.startswith('hind_'):choices[slot]=settings['legs']
    elif contract=='centaur_authoring_v1':
        for slot in slots:
            if slot in {'left_arm','right_arm'}:choices[slot]=settings['arms']
            if slot.startswith(('front_','hind_')) or slot=='tail':choices[slot]=settings['legs']
    elif contract=='insect_authoring_v1':
        for slot in slots:
            if '_leg_' in slot:choices[slot]=settings['arms'] if slot.endswith('_leg_1') else settings['legs']
    elif contract=='arachnid_authoring_v1':
        for slot in slots:
            if slot.startswith('left_leg'):choices[slot]=settings['arms']
            if slot.startswith('right_leg'):choices[slot]=settings['legs']
    elif contract in {'scorpion_authoring_v1','crustacean_authoring_v1'}:
        for slot in slots:
            if slot.endswith('_claw'):choices[slot]=settings['arms']
            if '_leg_' in slot:choices[slot]=settings['legs']
    else:
        for slot in slots:
            if slot in {'left_arm','right_arm','left_wing','right_wing'}:choices[slot]=settings['arms']
            if slot in {'left_leg','right_leg','tail'} or '_leg_' in slot:choices[slot]=settings['legs']
            if slot.startswith('front_'):choices[slot]=settings['arms']
            if slot.startswith('hind_'):choices[slot]=settings['legs']
    if settings['race']=='scorpion' and settings['back']:
        choices['tail']=settings['back']
    if settings['race'] in e.ANIMAL_SPECIES and settings['back'] and settings['back'] not in e.BACK_IDS:
        choices['tail']=settings['back']
    if settings['back']:
        for slot in ('left_wing','right_wing'):
            if slot in slots:choices[slot]=settings['back']
    if settings['race'] in e.ANIMAL_SPECIES and settings['back'] in e.BACK_IDS:
        slots=(*slots,'back_attachment');choices['back_attachment']=settings['back']
    derived={};arrays_all=[];recipes_all=[];anchors={};total=0
    for slot,donor in choices.items():
        if slot=='back_attachment' and donor in e.BACK_IDS:
            from .constructor_quadruped_back import author
            recipe,source=author(settings,next(r for r in recipes_all if r['commands'][0]['slot']=='torso'))
            recipe['quadruped_attachment'].update(carrier_revision_id=derived['torso']['revision_id'],carrier_model_sha256=derived['torso']['model_sha256'])
        else:
            recipe,source=e._load(donor,slot)
        sources=[source]
        if settings['race']=='beast-horse':
            from .constructor_horses import apply as horse_choices
            horse_choices(recipe,settings,slot)
        if settings['race']=='beast-wolf':
            from .constructor_wolf_limbs import apply as wolf_limbs
            wolf_limbs(recipe,settings,slot)
        if slot=='head':
            from .constructor_beast_faces import apply as refine_beast_face
            refine_beast_face(recipe,settings,slot)
            from .constructor_boar_faces import apply as refine_boar_face
            refine_boar_face(recipe,settings,slot)
            if settings['race'] not in {'beast-horse','centaur'}:recipe=prepare_head(recipe,settings,sources)
            if settings['eye_size']!=1 or settings['eye_shape']!='original':
                scale=np.array([settings['eye_size']*e.EYE_PROPORTIONS[settings['eye_shape']][0],settings['eye_size']*e.EYE_PROPORTIONS[settings['eye_shape']][1],1])
                recipe['commands']=[e._transform(c,scale,mesh(c)[0].mean(0)*(1-scale),donor) if c['part'] in {'visible_iris','visible_pupil'} else c for c in recipe['commands']]
        from .constructor_limb_caps import round_roots
        if settings['race'] not in {*e.ANIMAL_SPECIES,*e.FLYER_SPECIES,*e.EXP_SPECIES}:round_roots(recipe,slot)
        from .constructor_naga_costumes import apply as naga_costume
        naga_costume(recipe,settings,slot)
        from .constructor_naga_tail import apply as naga_tail
        naga_tail(recipe,settings,slot)
        from .constructor_beetle_legs import apply as beetle_legs
        beetle_legs(recipe,settings,slot)
        from .constructor_species_variety import apply as species_variety
        species_variety(recipe,settings,slot)
        from .constructor_centaur import apply as centaur_upper
        centaur_upper(recipe,settings,slot,sources)
        from .constructor_mounts import apply as mount_equipment
        mount_equipment(recipe,settings,slot)
        e._tint(recipe,settings['colors'])
        if slot in {'left_wing','right_wing','back_attachment'}:e.tint_back(recipe,settings['colors'])
        from .constructor_decor import apply
        # Only cloth pattern is compatible with these new anatomical layouts.
        if settings['decor']['pattern']!='none' and settings['race']!='centaur':apply(recipe,settings,slot)
        factor=e.FORM_WIDTHS[settings['form']]
        recipe['commands'].sort(key=lambda c:c['stage'])
        recipe['commands']=[e._transform(c,np.array([factor,1,1]),np.zeros(3),donor) for c in recipe['commands']]
        anchors[slot]=(np.asarray(recipe['contract_anchors'][slot])*[factor,1,1]).tolist()
        recipe.setdefault('team_materials', ['cloth', 'banner', 'team'])
        recipe['constructor']={'schema_version':3,'settings':settings,'slot':slot,'sources':[{k:v for k,v in p.items() if k not in {'recipe','record'}} for p in sources]}
        from .constructor_hand_orientation import apply as orient_hand
        orient_hand(recipe,slot)
        digest=e._hash(e._encoded(recipe));recipe['id']='constructor.'+digest+'.'+slot
        folder=target/'parts'/slot;folder.mkdir(parents=True)
        a=compile_recipe(recipe);export_glb(folder/'model.glb',a,recipe);(folder/'recipe.json').write_bytes(e._encoded(recipe))
        for i,p in enumerate(sources):
            (folder/f'source-{i}.recipe.json').write_bytes(e._encoded(p['recipe']));(folder/f'source-{i}.record.json').write_bytes(e._encoded(p['record']))
        if not np.isfinite(a[0]).all():raise ValueError('Некорректная геометрия')
        if settings['race'] not in e.FLYER_SPECIES and (slot.endswith('_leg') or '_leg_' in slot) and abs(float(a[0][:,1].min()))>1e-5:
            raise ValueError('Ноги должны оставаться на общей плоскости')
        triangles=len(a[0])//3;total+=triangles;arrays_all.append(a);recipes_all.append(recipe)
        from .constructor_flyers import part_description
        description=recipe['species_design']['description_ru'] if donor in EXP_IDS else part_description(recipe['species_design'],slot) if settings['race'] in e.FLYER_SPECIES else recipe.get('animal_design',recipe.get('species_design',{})).get('description_ru','')
        if recipe.get('species_anatomy_revision'):description=recipe['species_anatomy_revision']['label']
        if recipe.get('centaur_upper'):description='Человеческий верх кентавра: лицо, волосы, черты и одежда из человеческой библиотеки; конский корпус и масштаб ног сохранены.'
        if recipe.get('naga_costume_revision'):
            description=recipe['naga_costume_revision']['label_ru']+'. Морской панцирь, раковины, чешуйчатые пластины и плавниковые наручи; без сухопутной ткани. Сохранены исходные пропорции тела и кисти.'
        if slot=='back_attachment':description=e.BACK_IDS[settings['back']]+'. Точная геометрия человеческого артефакта; единый масштаб и поворот, прикреплено к поверхности спины выбранного животного.'
        derived[slot]={'ai_description':{'schema_version':1,'slot':slot,'race':settings['race'],'contract':contract,'pose':'flight' if settings['race'] in e.FLYER_SPECIES else 'standing','description_ru':description},'revision_id':digest,'model':f'parts/{slot}/model.glb','model_sha256':e._hash((folder/'model.glb').read_bytes()),'triangles':triangles,'anchor':anchors[slot]}
    assembly={'schema_version':2,'contract_id':contract,'parts':{slot:{'revision_id':p['revision_id'],'model_sha256':p['model_sha256']} for slot,p in derived.items()}}
    assembly['id']=e._hash(e._encoded(assembly));(target/'assembly.json').write_bytes(e._encoded(assembly))
    (target/'contract.json').write_bytes(e._encoded({'schema_version':1,'id':contract,'slots':list(slots),'anchors':anchors,'coordinates':'metres; Y up; +Z forward; floor Y=0','contact_mode':'airborne' if settings['race'] in e.FLYER_SPECIES else 'grounded','pose':'flight' if settings['race'] in e.FLYER_SPECIES else 'standing','runtime_skeleton':None,'animation_support':'static_authoring_only'}))
    result={'schema_version':1,'id':assembly['id'],'contract':contract,'status':'authoring_draft','rigging':'none','runtime_support':False,'bind_bones':[],'parts':derived,'triangles':total,'checks':{'finite_geometry':True,'shared_floor':settings['race'] not in e.FLYER_SPECIES,'airborne':settings['race'] in e.FLYER_SPECIES,'source_hashes':True,'weight_sidecars':False},'warnings':['Авторская сборка без скелета и анимаций. Сохранение и экспорт содержат один статический GLB и полные настройки выбора деталей.']}
    (target/'manifest.json').write_bytes(e._encoded(result))
    if weights:
        merged=tuple(np.concatenate([a[i] for a in arrays_all]) for i in range(3))+([],);render_png(target/'preview.png',merged,yaw=0,pitch=0,size=320,recipe={'commands':[c for r in recipes_all for c in r['commands']]})
    integrity={str(p.relative_to(target)):e._hash(p.read_bytes()) for p in sorted(target.rglob('*')) if p.is_file()}
    (target/'integrity.json').write_bytes(e._encoded({'schema_version':1,'files':integrity}));return result
