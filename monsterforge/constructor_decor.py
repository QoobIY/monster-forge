"""Authored modular ornaments, baked into immutable body-part revisions."""
from __future__ import annotations
import copy
import math
import numpy as np
from tools.creature_workshop.original_constructor import OriginalSculpt, mesh_command
from tools.creature_workshop.family_faces import orient_faces

EMBLEMS=dict(none='Без эмблемы',lion='Лев',sun='Солнце',moon='Полумесяц',star='Звезда',skull='Череп',leaf='Лист',bolt='Молния',wings='Крылья',diamond='Кристалл',serpent='Змея')
EMBLEMS.update(lionheart='Львиное сердце',key='Ключ',bear='Медведь',wolf='Волк',mage='Маг',crown='Корона',pirate='Пиратский знак')
SHOULDERS=dict(none='Без наплечников',plates='Гранёные пластины',layered='Чешуйчатые',horns='Рога',spikes='Шипы',feathers='Перья',fur='Мех',gems='Кристаллы',scrolls='Свитки',wings='Крылатые',asymmetric='Один наплечник')
BELTS=dict(none='Исходный пояс',pouches='Подсумки',tools='Инструменты',chain='Цепь',gems='Камни',sash='Кушак',double='Двойной ремень',flasks='Колбы',scrolls='Свитки',book='Книга',medallion='Медальон')
HEADWEAR=dict(none='Без украшения',circlet='Обруч',crown='Корона',tiara='Диадема',goggles='Очки',earrings='Серьги',feather='Перо',gem='Камень',horncaps='Роговые накладки',laurel='Лавровый венок',mask='Полумаска')
HEADWEAR['horned_helmet']='Рогатый шлем викинга'
HEADWEAR.update(cloth_hood='Тканевый капюшон',deep_hood='Глубокий капюшон с отворотом',wizard_hat='Колпак мага',winged_helmet='Крылатый шлем',halo='Нимб',closed_helmet='Шлем-котелок · Т-образная прорезь',crested_helmet='Шлем с гребнем',barbute='Барбют · Т-образный вырез')
from .constructor_horns import LABELS as HORN_LABELS
HEADWEAR.update(HORN_LABELS)
# Labels avoid importing the geometry module during this module's initialization.
HEADWEAR.update(faceless_tendrils='Безликий · четыре щупальца',faceless_crown='Безликий · шесть щупалец',faceless_abyss='Безликий · глубоководный',horned_mask='Рогатая полумаска')
from .constructor_goblins import HEADWEAR as GOBLIN_HEADWEAR
HEADWEAR.update(GOBLIN_HEADWEAR)
PATTERNS=dict(none='Однотонный',split='Два цвета',quartered='Четверти',stripes='Полосы',checks='Клетка',chevron='Шеврон',rays='Лучи',runes='Руны',diamonds='Ромбы',edged='Кант',scales='Чешуя')
PATTERNS.update(ancient_runes='Древние руны',elven_runes='Эльфийские руны',demonic_runes='Демонические руны')
from .constructor_elemental_runes import ELEMENTS
PATTERNS.update({k:e['label'] for k,e in ELEMENTS.items()})
from .constructor_portraits import BEARDS, MUSTACHES, facial_hair
from .constructor_wild_clothes import SHOULDERS as WILD_SHOULDERS, BELTS as WILD_BELTS
SHOULDERS.update(WILD_SHOULDERS);BELTS.update(WILD_BELTS)
OPTIONS={'beard':BEARDS,'mustache':MUSTACHES,'emblem':EMBLEMS,'shoulders':SHOULDERS,'belt':BELTS,'headwear':HEADWEAR,'pattern':PATTERNS}
PALETTES=[
 ('forest','Лесной дозор',['#4e6858','#c2b886','#7b8980','#604737','#91a174']),
 ('crimson','Багряный орден',['#773b49','#d7ae65','#acb2b9','#442e34','#b55c51']),
 ('azure','Лазурная стража',['#315c85','#c1d5db','#849eaf','#434751','#5fa4b2']),
 ('ivory','Слоновая кость',['#d3cbb5','#c8a65e','#adab9d','#85674e','#809ba3']),
 ('obsidian','Обсидиан',['#30383f','#b88358','#565f6c','#392e30','#715180']),
 ('violet','Аметист',['#66507e','#d2b58a','#9692b0','#463a4f','#ac799c']),
 ('copper','Медный закат',['#a6653f','#ddb67b','#b88257','#654237','#51838a']),
 ('frost','Зимний поход',['#8bafbf','#ede3c7','#b4c8d1','#596877','#50748e']),
 ('jade','Нефрит',['#31746d','#d3c29b','#77a99d','#3c524c','#9cba64']),
 ('royal','Королевский',['#363c75','#d3b058','#a8a6ba','#46384b','#8c4567']),
 ('sand','Пустынный',['#b99b6b','#ede0ad','#a08d73','#7b553a','#937446']),
 ('rose','Розовый кварц',['#a76980','#e0c4b0','#c4a6b0','#634756','#665985']),
]

def colorways():
    return [{'id':i,'label':label,'colors':dict(zip(('cloth','accent','metal','leather','secondary'),colors))} for i,label,colors in PALETTES]

def sculpt(settings):
    palette={'skin':'bda080','hair':'544136','iris':'659198','cloth':'667b83','accent':'d0b67a','metal':'919ba1','leather':'624c3d','secondary':'976356'}
    for k,v in settings['colors'].items():
        if v:palette[k]=v.lstrip('#')
    b=OriginalSculpt({'id':'constructor-ornaments-v1','palette':palette})
    b.stage=4
    return b

def badge(b,kind):
    b.slot='torso';cx=0;cy=1.52;z=.325
    def panel(name,points,mat='accent'):
        b.panel3('ornament_'+name,mat,[[cx+x,cy+y,z] for x,y in points],.025)
    if kind=='none':return
    from .constructor_emblems import authored_badge
    if authored_badge(b,kind,cy,z):return
    if kind in ('sun','star','diamond','moon'):
        if kind=='moon':
            panel('moon',[(-.05,.11),(-.105,.04),(-.09,-.065),(-.01,-.12),(.075,-.08),(.025,-.09),(-.04,-.035),(-.045,.045),(.005,.095)])
        else:
            count=24 if kind=='sun' else 10 if kind=='star' else 4
            points=[]
            for i in range(count):
                a=math.pi/2+i*2*math.pi/count;r=.12 if count==4 or i%2==0 else .05
                points.append((math.cos(a)*r,math.sin(a)*r))
            panel(kind,points)
            if kind=='sun':b.oval('ornament_sun_core','secondary',[0,cy,z+.015],[.042,.042,.018],sides=8)
    elif kind=='lion':
        panel('lion_mane',[(-.10,.09),(-.04,.13),(.04,.13),(.10,.09),(.12,-.025),(.07,-.10),(0,-.14),(-.07,-.10),(-.12,-.025)])
        b.oval('ornament_lion_face','metal',[0,cy,z+.025],[.063,.071,.035],sides=6)
        b.oval('ornament_lion_nose','leather',[0,cy-.025,z+.06],[.018,.012,.012],sides=5)
    elif kind=='skull':
        b.oval('ornament_skull','accent',[0,cy+.025,z],[.077,.078,.03],sides=8)
        b.box('ornament_jaw','accent',[0,cy-.055,z],[.095,.055,.045])
        for sign in (-1,1):b.oval('ornament_eye','leather',[sign*.032,cy+.02,z+.03],[.021,.022,.012],sides=6)
    elif kind=='leaf':panel('leaf',[(0,.15),(.08,.07),(.09,-.02),(0,-.12),(-.07,-.04),(-.08,.07)])
    elif kind=='bolt':panel('bolt',[(.015,.15),(-.095,-.015),(-.015,-.015),(-.025,-.15),(.09,.04),(.02,.04)])
    elif kind=='wings':
        for sign in (-1,1):panel('wing',[(sign*.015,.06),(sign*.15,.11),(sign*.10,-.02),(sign*.02,-.075)])
    elif kind=='serpent':
        path=[[.045*math.sin(i*.9),cy+.12-i*.03,z] for i in range(9)]
        b.tube('ornament_serpent','accent',path,[.018]*8+[.003],sides=5)
    if kind=='lion':
        for sign in (-1,1):
            b.oval('ornament_lion_eye','leather',[sign*.025,cy+.019,z+.058],[.008,.009,.006],sides=5)
            b.oval('ornament_lion_muzzle','accent',[sign*.025,cy-.039,z+.052],[.023,.024,.014],sides=5)
    elif kind=='leaf':
        b.tube('ornament_leaf_vein','metal',[[0,cy-.105,z+.013],[0,cy+.125,z+.013]],[.004,.002],sides=4)
        for sign in (-1,1):
            for y in (-.04,.02,.07):b.tube('ornament_leaf_branch','metal',[[0,cy+y-.016,z+.013],[sign*.05,cy+y+.019,z+.013]],[.002,.001],sides=4)
    elif kind=='wings':
        for sign in (-1,1):
            for i in range(4):b.tube('ornament_wing_feather','metal',[[sign*(.028+i*.025),cy+.059,z+.01],[sign*(.032+i*.019),cy-.034-i*.01,z+.01]],[.004,.002],sides=4)
    elif kind in ('diamond','star'):
        b.panel3('ornament_inset_facet','secondary',[[0,cy+.073,z+.012],[.042,cy,z+.018],[0,cy-.061,z+.012],[-.042,cy,z+.018]],.009)


def ornaments(settings,slot):
    b=sculpt(settings);b.slot=slot;d=settings['decor']
    if slot=='torso':
        badge(b,d['emblem']);b.slot=slot;k=d['belt']
        if k=='pouches':
            for sign in (-1,1):b.box('ornament_pouch','leather',[sign*.245,1.08,.25],[.14,.18,.10]);b.box('ornament_pouch_clasp','metal',[sign*.245,1.11,.31],[.035,.04,.01])
        elif k=='tools':
            for i in range(3):b.box('ornament_tool_handle','leather',[-.21+i*.06,1.14,.285],[.026,.18,.027]);b.box('ornament_tool_tip','metal',[-.21+i*.06,1.22,.285],[.045,.06,.025])
        elif k=='chain':
            for i in range(9):b.oval('ornament_chain_link','metal',[-.24+i*.06,1.03-.055*math.sin(i*math.pi/8),.26],[.035,.025,.012],sides=6)
        elif k=='gems':
            for x in (-.17,0,.17):b.oval('ornament_belt_gem','secondary',[x,1.1,.255],[.032,.047,.024],sides=5)
        elif k in ('sash','double'):
            for y in ([1.03,1.16] if k=='double' else [1.06,1.12,1.18]):b.loft('ornament_waist_band','secondary' if k=='sash' else 'leather',[[y,0,0,.27,.227],[y+.033,0,0,.27,.227]],sides=10)
            if k=='sash':b.panel3('ornament_sash_tail','secondary',[[.14,1.1,.27],[.24,1.1,.27],[.2,.63,.25],[.11,.69,.25]],.025)
        elif k=='flasks':
            for x in (-.24,.24):b.oval('ornament_flask','secondary',[x,1.04,.26],[.05,.09,.042],sides=6);b.box('ornament_cork','leather',[x,1.13,.26],[.038,.035,.038])
        elif k=='scrolls':
            for x in (-.22,.22):b.tube('ornament_scroll','accent',[[x,.96,.25],[x,1.19,.25]],[.035,.035],sides=6)
        elif k=='book':b.box('ornament_book_cover','leather',[-.27,1.04,.25],[.16,.22,.06]);b.box('ornament_book_pages','accent',[-.27,1.04,.289],[.135,.18,.018])
        elif k=='medallion':b.oval('ornament_medallion','metal',[0,1.11,.278],[.063,.063,.02],sides=10)
    elif slot.endswith('_arm'):
        k=d['shoulders'];sign=-1 if slot=='left_arm' else 1
        if k=='asymmetric' and sign==1:k='none'
        if k in ('plates','asymmetric','layered'):
            for i in range(3 if k=='layered' else 1):b.oval('ornament_shoulder_plate','metal',[sign*(.405+i*.025),1.84-i*.06,.045],[.185,.13,.19],sides=6)
        elif k in ('horns','spikes','feathers','gems','scrolls','fur','wings'):
            b.oval('ornament_shoulder_base','leather',[sign*.415,1.83,.015],[.165,.10,.165],sides=6)
            for i in range(3):
                x=sign*(.34+i*.065);y=1.91-i*.015
                if k in ('horns','spikes'):b.tube('ornament_shoulder_'+k,'metal' if k=='spikes' else 'accent',[[x,y,.04],[x+sign*.04,y+.13,.025],[x+sign*.09,y+.18,.06]],[.043,.025,.002],sides=5)
                elif k in ('feathers','wings'):b.panel3('ornament_shoulder_feather','secondary',[[x,y,.16],[x+sign*.06,y+.02,.17],[x+sign*.15,y-.23,.18],[x+sign*.1,y-.25,.18]],.02)
                elif k=='gems':b.oval('ornament_shoulder_crystal','secondary',[x,y+.035,.085],[.045,.085,.045],sides=5)
                elif k=='scrolls':b.tube('ornament_shoulder_scroll','accent',[[x,y-.10,.14],[x,y+.04,.14]],[.025,.025],sides=6)
                elif k=='fur':b.oval('ornament_fur_tuft','secondary',[x,y-.03,.11],[.07,.11,.08],sides=5)
    elif slot=='head':
        k=d['headwear']
        if k in ('circlet','crown','tiara','laurel'):
            b.loft('ornament_circlet','metal',[[2.47,0,-.025,.229,.213],[2.5,0,-.025,.229,.213]],sides=12)
            for i in range(5 if k=='crown' else 3 if k in ('tiara','laurel') else 1):
                x=(i-(2 if k=='crown' else 1 if k in ('tiara','laurel') else 0))*.065
                if k=='crown':b.panel3('ornament_crown_point','metal',[[x-.029,2.50,.198],[x+.029,2.50,.198],[x,2.59+(i%2)*.035,.19]],.022)
                elif k=='laurel':b.oval('ornament_laurel_leaf','secondary',[x,2.51,.19],[.04,.018,.018],sides=5)
                else:b.oval('ornament_circlet_gem','secondary',[x,2.505,.20],[.025,.034,.018],sides=5)
        elif k=='goggles':
            for sign in (-1,1):b.oval('ornament_goggle_rim','metal',[sign*.103,2.33,.279],[.058,.047,.02],sides=8);b.oval('ornament_goggle_lens','secondary',[sign*.103,2.33,.299],[.041,.032,.007],sides=8)
            b.box('ornament_goggle_bridge','metal',[0,2.33,.28],[.11,.015,.017])
        elif k=='earrings':
            for sign in (-1,1):b.oval('ornament_earring','metal',[sign*.235,2.235,.02],[.025,.055,.021],sides=8)
        elif k=='feather':b.panel3('ornament_head_feather','secondary',[[.19,2.51,.025],[.30,2.75,0],[.36,2.68,.01],[.235,2.5,.045]],.025)
        elif k=='gem':b.oval('ornament_forehead_gem','secondary',[0,2.445,.21],[.034,.052,.016],sides=5)
        elif k=='horncaps':
            for sign in (-1,1):b.tube('ornament_horn_cap','metal',[[sign*.17,2.49,-.03],[sign*.25,2.61,-.02]],[.052,.007],sides=5)
        elif k=='mask':b.panel3('ornament_half_mask','metal',[[-.18,2.36,.265],[.18,2.36,.265],[.14,2.29,.275],[0,2.30,.30],[-.14,2.29,.275]],.016)
    from tools.creature_workshop.accessory_details import belt as detail_belt, headwear as detail_headwear
    if slot=='torso':detail_belt(b,d['belt'])
    if slot=='head':
        detail_headwear(b,d['headwear'])
        facial_hair(b,settings)
    if settings['colors']['hair']:
        b.palette['hair']=settings['colors']['hair'][1:]
        rgb=np.array(list(bytes.fromhex(b.palette['hair'])))
        b.palette['hair_light']=''.join(f'{v:02x}' for v in np.minimum(np.round(rgb*1.16),255).astype(int))
    result=[]
    for i,c in enumerate(b.commands):
        v,f=mesh_command(c);f=orient_faces(v,f)
        result.append(dict(id=f'decor_{slot}_{i}',stage=4,slot=slot,part=c['part'],material='decor_'+c['material'],op='indexed_mesh',vertices=v.tolist(),faces=f.tolist(),authored_primitive=copy.deepcopy(c),purpose='User-selected ornament; immutable body part revision'))
    return result,{'decor_'+k:v for k,v in b.palette.items()}


def apply(recipe,settings,slot):
    effective=copy.deepcopy(settings)
    if settings['race']=='randomium':
        effective['decor']['emblem']='none'
    if slot=='head' and not effective['colors']['hair']:
        candidates=[c for c in recipe['commands'] if any(key in c['part'] for key in ('hair','braid','mane')) and 'brow' not in c['part']]
        name=candidates[0]['material'] if candidates else 'hair'
        effective['colors']['hair']='#'+recipe['palette'].get(name,recipe['palette'].get('hair','544136')).lstrip('#')
    commands,palette=ornaments(effective,slot)
    recipe['palette'].update(palette);recipe['commands'].extend(commands)
    pattern=settings['decor']['pattern']
    secondary=settings['colors']['secondary'] or '#976356'
    recipe['palette']['pattern_secondary']=secondary.lstrip('#')
    if pattern not in {'none','ancient_runes','elven_runes','demonic_runes',*ELEMENTS} and slot!='head' and slot!='back_attachment':
        for c in recipe['commands']:
            if c['material'] not in {'cloth','primary'}:continue
            v,f=mesh_command(c);centers=v[f].mean(axis=1)
            x,y,z=centers.T
            mask={'split':x>0,'quartered':(x>0)^(y>1.45),'stripes':(np.floor(y*18).astype(int)%2)==0,
                  'checks':((np.floor(x*14)+np.floor(y*14)).astype(int)%2)==0,
                  'chevron':(np.floor((y+np.abs(x)*.6)*14).astype(int)%2)==0,
                  'rays':(np.floor(np.arctan2(x,y-1.5)*5).astype(int)%2)==0,
                  'runes':((np.floor(x*20).astype(int)%3)==0)&((np.floor(y*20).astype(int)%3)==0),
                  'diamonds':(np.floor((x+y)*12).astype(int)%2)==(np.floor((y-x)*12).astype(int)%2),
                  'edged':np.abs(x)>np.quantile(np.abs(x),.75),
                  'scales':((np.floor(y*17)+np.floor(x*16+(np.floor(y*17)%2)*.5)).astype(int)%3)==0}[pattern]
            c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist(),face_materials=['pattern_secondary' if on else c['material'] for on in mask])
    from .constructor_wild_clothes import apply as apply_wild
    apply_wild(recipe,settings,slot)
    recipe['decor_revision']=1
