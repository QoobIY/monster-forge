"""Race-specific facial anatomy and independently authored hair silhouettes.

These are geometry edits baked into a new head revision. Frozen source meshes,
rigs and previously saved revisions are never overwritten.
"""
from __future__ import annotations
import copy
import json
import math
import numpy as np
from pathlib import Path
from .paths import ROOT
from tools.creature_workshop.original_constructor import OriginalSculpt,mesh_command
from tools.creature_workshop.family_faces import orient_faces

FEATURES={
 'nose':dict(profile='Характер лица',button='Кнопка',aquiline='Орлиный',broad='Широкий',flat='Плоский',hooked='С горбинкой',upturned='Курносый',long='Длинный',broken='Сломанный',angular='Гранёный',round='Круглый'),
 'ears':dict(profile='Характер лица',small='Маленькие',large='Большие',round='Округлые',long='Длинные',pointed='Острые',swept='Отведённые',drooping='Опущенные',notched='С надрезом',wide='Широкие',asymmetric='Разные'),
 'jaw':dict(profile='Характер лица',soft='Мягкая',square='Квадратная',tapered='Заострённая',broad='Широкая',long='Длинная',short='Короткая',cleft='С ямкой',heavy='Массивная',gaunt='Впалая',asymmetric='Асимметричная'),
 'brows':dict(profile='Характер лица',straight='Прямые',arched='Дугой',thick='Густые',thin='Тонкие',angled='Угловатые',low='Низкие',high='Высокие',split='С разрывом',wild='Кустистые',uneven='Неровные'),
 'mouth':dict(profile='Характер лица',small='Маленький',wide='Широкий',full='Полные губы',thin='Тонкие губы',smile='Улыбка',stern='Суровый',crooked='Кривой',scarred='Со шрамом',fangs='Клыки',teeth='Видимые зубы'),
}
NEW_HAIR={
 'mohawk':'Ирокез','undercut':'Андеркат','curly':'Кудри','afro':'Афро','dreadlocks':'Дреды',
 'ponytail':'Высокий хвост','low-tail':'Низкий хвост','double-buns':'Два пучка','pageboy':'Паж',
 'long-waves':'Длинные волны','side-shave':'Выбритый бок','spiky':'Колючие пряди','pompadour':'Помпадур',
 'pixie':'Пикси','side-braid':'Боковая коса','braid-crown':'Венок из кос','messy':'Растрёпанные',
 'long-straight':'Длинные прямые','fringe':'Густая чёлка','crest':'Высокий гребень',
}
BEARDS=dict(none='Без бороды',stubble='Щетина',short='Короткая',full='Окладистая',long='Длинная',pointed='Клином',forked='Раздвоенная',braided='Плетёная',goatee='Эспаньолка',mutton='Бакенбарды',sideburns='Виски')
MUSTACHES=dict(none='Без усов',pencil='Тонкие',thick='Густые',handlebar='Закрученные',horseshoe='Подковой',walrus='Моржовые',split='Разделённые',braided='Плетёные',twirl='Спиральные',straight='Прямые',short='Короткие')
BEARDS['original']='Исходная борода'
MUSTACHES['original']='Исходные усы'
# Actual racial anatomy differs before the ten within-race character profiles.
RACE_SHAPES={
 'human':(1,1,1,'human'),'elf':(.85,1.07,.96,'elf'),'orc':(1.28,.94,1.12,'orc'),
 'minotaur':(1.38,1.03,1.25,'bull'),'wolf':(1.02,1.02,1.16,'canine'),
 'angel':(.94,1.05,1.02,'angel'),'demon':(.95,1.10,1.10,'demon'),
 'skeleton':(1,1,1,'skull'),'boarfolk':(1.25,.92,1.15,'boar'),
 'elephantfolk':(1.35,1.12,1.12,'elephant'),'mutant':(1.15,1.03,1.12,'mutant'),
 'undead':(.91,1.09,.91,'undead'),'gargoyle':(1.17,.98,1.16,'stone'),
 'tentaclefolk':(1.12,1.14,1.10,'cephalopod')}
PROFILES=[{'nose':n,'ears':e,'jaw':j,'brows':b,'mouth':m} for n,e,j,b,m in zip(
 list(FEATURES['nose'])[1:],list(FEATURES['ears'])[1:],list(FEATURES['jaw'])[1:],
 ['straight','arched','thick','thin','angled','low','high','split','wild','uneven'],
 ['small','smile','full','thin','stern','wide','crooked','scarred','fangs','teeth'])]
CONFIG=ROOT/'config/constructor_portraits_v1.json'

def config_snapshot():
    return {'schema_version':1,'id':'constructor_portraits_v1','contract':'humanoid_v1','features':FEATURES,'profiles':PROFILES,'race_shapes':RACE_SHAPES,'hair':NEW_HAIR,'beards':{k:v for k,v in BEARDS.items() if k!='original'},'mustaches':{k:v for k,v in MUSTACHES.items() if k!='original'}}

def ensure_config():
    encoded=json.dumps(config_snapshot(),ensure_ascii=False,indent=2)+'\n'
    if CONFIG.exists() and json.loads(CONFIG.read_text())!=json.loads(encoded):raise ValueError('Immutable portrait design config conflict')
    if not CONFIG.exists():CONFIG.write_text(encoded)

def defaults(original=False):return {key:'original' if original else 'profile' for key in FEATURES}

def profile(settings):
    if settings['face'].startswith('reference-'):
        config=json.loads((ROOT/'config/constructor_reference_kits_v1.json').read_text())
        spec=next(d for d in config['designs'] if d['id']==settings['face'])
        return 0,spec['features']
    face=settings['face'];number=int(face.rsplit('-',1)[-1])-1 if face.startswith('library-') else 0
    return number%10,PROFILES[number%10]

def builder(recipe):
    palette={k:recipe['palette'].get(k,v) for k,v in {'skin':'bda080','hair':'544136','iris':'659198','cloth':'667b83','accent':'d0b67a','metal':'919ba1','leather':'624c3d','secondary':'976356'}.items()}
    b=OriginalSculpt({'id':'portrait-anatomy-v1','palette':palette});b.slot='head';b.stage=2
    return b

def freeze(b,prefix):
    commands=[]
    for i,c in enumerate(b.commands):
        v,f=mesh_command(c);f=orient_faces(v,f)
        commands.append(dict(id=f'{prefix}_{i}',stage=c['stage'],slot='head',part=c['part'],material=prefix+'_'+c['material'],op='indexed_mesh',vertices=v.tolist(),faces=f.tolist(),authored_primitive=copy.deepcopy(c),purpose='Authored race anatomy or independent hairstyle'))
    return commands,{prefix+'_'+k:v for k,v in b.palette.items()}

def ear(b,kind,race,width,number):
    for sign in (-1,1):
        scale=.68 if kind=='small' else 1.38 if kind in ('large','wide') else 1
        length=1.40 if kind in ('long','pointed') else .75 if kind=='round' else 1
        if kind=='asymmetric' and sign==1:scale*=.55
        y=2.33;root=width*.90;spread=.10*scale;tipy=y+.06*length
        if race in ('elf','demon','gargoyle'):spread*=1.6;tipy+=.06*length
        if race in ('wolf','boarfolk','minotaur'):
            root=width*.62;y=2.48;spread=.085*scale;tipy=y+.18*length
        if race=='elephantfolk':spread=.21*scale;y=2.32;tipy=y+.17*length
        if race=='tentaclefolk':spread*=1.2;tipy=y+.085
        if kind=='wide':spread*=1.35;tipy=y+.025
        if kind=='drooping':tipy=y-.15*length
        if kind=='swept':tipy+=.075;spread*=1.25
        if kind in ('round','long') or race=='elephantfolk':
            points=[[sign*root,y+.06,0],[sign*(root+spread*.7),tipy,.005],[sign*(root+spread),y-.005,-.01],[sign*(root+spread*.8),y-.11,.01],[sign*root,y-.07,.04]]
        else:
            points=[[sign*root,y+.045,0],[sign*(root+spread),tipy,-.025],[sign*(root+spread*.75),y-.07,.018],[sign*root,y-.075,.045]]
        if kind=='notched':points.insert(2,[sign*(root+spread*.54),y+.018,.015])
        b.panel3('anatomy_ear','skin',points,.035)
        if race not in ('skeleton','gargoyle'):
            center=np.mean(points,axis=0);inner=(np.asarray(points)-center)*.58+center;inner[:,2]+=.018
            b.panel3('anatomy_ear_inner','lip',inner.tolist(),.008)
        if race=='tentaclefolk':
            for i in range(3):b.tube('anatomy_sensory_frill','skin',[[sign*(root+spread*.55),y+i*.035,.02],[sign*(root+spread+.02+i*.01),y+.01+i*.042,.04]],[.018,.002],sides=5)

def nose(b,kind,race,number):
    if race in ('minotaur','wolf','boarfolk'):
        broad=.20 if race=='minotaur' else .115 if race=='wolf' else .145
        length=.22 if race=='wolf' else .18 if race=='minotaur' else .125
        broad*= {'broad':1.25,'flat':1.16,'angular':.9,'long':.87,'round':1.10,'button':.78}.get(kind,1)
        length*= {'long':1.35,'hooked':1.12,'flat':.75,'button':.8,'aquiline':1.2}.get(kind,1)
        z=.18+length
        b.loft('anatomy_muzzle','skin',[[2.085,0,.14,broad*.62,.10],[2.15,0,.20,broad,.12],[2.235,0,.20,broad*.82,length*.75]],sides=8)
        b.oval('anatomy_animal_nose','lip' if race=='boarfolk' else 'dark',[.012 if kind=='broken' else 0,2.215,z],[broad*.53,.043 if kind!='flat' else .026,.025],sides=6)
        for sign in (-1,1):b.oval('anatomy_nostril','dark',[sign*broad*.26,2.22,z+.02],[.013,.010,.007],sides=5)
        return
    if race=='elephantfolk':
        length=.28+number*.013
        curve=-.10 if kind in ('hooked','broken') else .08 if kind in ('upturned','round') else .035
        b.tube('anatomy_trunk','skin',[[0,2.36,.26],[0,2.24,.36],[0,2.12,.40],[curve*.5,2.25-length,.43],[curve,2.23-length,.48]],[.073,.066,.054,.035,.022],sides=8)
        return
    if race=='tentaclefolk':
        b.oval('anatomy_nasal_ridge','skin',[0,2.315,.26],[.035 if kind!='broad' else .06,.06,.035],sides=6)
        return
    specs={'button':(.037,.032,.035),'aquiline':(.026,.09,.065),'broad':(.070,.047,.045),'flat':(.065,.022,.025),'hooked':(.028,.078,.095),'upturned':(.042,.030,.060),'long':(.030,.105,.085),'broken':(.038,.068,.064),'angular':(.042,.065,.075),'round':(.053,.042,.060)}
    w,h,z=specs[kind];w*=.85 if race=='elf' else 1.30 if race=='orc' else 1
    x=.018 if kind=='broken' else 0
    b.loft('anatomy_nose_bridge','skin',[[2.25-h,x,.218,w,.017],[2.25,x,.235,w,z],[2.25+h*.7,0,.218,w*.60,.023]],sides=6)
    for sign in (-1,1):b.oval('anatomy_nostril','shadow',[x+sign*w*.52,2.232-h*.25,.25+z*.45],[w*.19,.007,.007],sides=5)

def eyebrows(b,kind,number):
    thick=.019 if kind in ('thick','wild') else .006 if kind=='thin' else .011
    y=2.395+(.035 if kind=='high' else -.025 if kind=='low' else 0)
    for sign in (-1,1):
        if kind=='uneven':y+=sign*.018
        path=[[sign*.055,y,.245],[sign*.105,y+(.023 if kind=='arched' else 0),.249],[sign*.16,y+(.025 if kind=='angled' else -.012),.226]]
        if kind=='split':
            for p in (path[:2],[[sign*.128,y,.24],path[-1]]):b.tube('anatomy_brow','hair',p,[thick,thick*.8],sides=4)
        else:b.tube('anatomy_brow','hair',path,[thick,thick,thick*.7],sides=4)
        if kind=='wild':
            for i in range(3):b.tube('anatomy_wild_brow','hair',[[sign*(.07+i*.028),y,.25],[sign*(.065+i*.035),y+.028,.245]],[.008,.002],sides=4)

def mouth(b,kind,race,number):
    if race != 'tentaclefolk':
        from tools.creature_workshop.mouth_sculpt import mouth as sculpt_mouth
        sculpt_mouth(b,kind,race,number)
        return
    z=.23;y=2.125;w=.045 if kind=='small' else .095 if kind=='wide' else .07
    if race in ('minotaur','wolf','boarfolk'):z=.345;y=2.11;w*=1.30
    if race=='elephantfolk':w=.095;z=.29
    if race=='tentaclefolk':
        for i in range(4+number%3):
            x=(i-(3+number%3)/2)*.047
            b.tube('anatomy_face_tentacle','skin',[[x,2.20,.255],[x*1.25,2.095,.31],[x*1.35,1.96+(i%2)*.06,.32],[x*1.60,2.01,.37]],[.032,.026,.017,.002],sides=6)
            b.oval('anatomy_tentacle_sucker','lip',[x*1.3,2.065,.339],[.01,.018,.006],sides=5)
        return

def anatomy(recipe,settings):
    if all(v=='original' for v in settings['features'].values()):return recipe
    number,p=profile(settings);race=settings['race'];resolved={k:p[k] if v in ('profile','original') else v for k,v in settings['features'].items()}
    width,height,depth,kind=RACE_SHAPES[race];jaw=resolved['jaw']
    kept=[]
    remove=('ear','nostril','muzzle','nose_plate','nasal_tip','brow','closed_mouth','lower_lip','fang','facial_tentacle','cranial_growth','asymmetric_cheek','gaunt_cheek','articulated_trunk','elephant_tusk','boar_tusk','bull_horn','curved_horn','stone_horn','sensory')
    for original in recipe['commands']:
        part=original['part'].lower()
        if any(token in part for token in remove) and not ('beard' in part and settings['decor']['beard']=='original'):continue
        c=copy.deepcopy(original)
        if any(t in part for t in ('traced_reference_face','rounded_cranium','canine_cranium','skull','orbital','mandible','teeth','visible_iris','visible_pupil','eye_aperture','eye_socket','skull_cheek')):
            v,f=mesh_command(c);v=v.copy();center=np.array([0,2.28,.045]);v=(v-center)*[width,height,depth]+center
            lower=np.clip((2.25-v[:,1])/.22,0,1)
            if jaw in ('square','heavy','broad'):v[:,0]*=1+lower*.12
            if jaw in ('tapered','gaunt'):v[:,0]*=1-lower*.20
            if jaw=='asymmetric':v[:,0]+=lower*.035
            if jaw=='long':v[:,1]-=lower*.055
            if jaw=='short':v[:,1]+=lower*.040
            if jaw=='cleft':v[:,2]-=lower*.018*(np.abs(v[:,0])<.04)
            if race!='skeleton':
                mask=(np.abs(v[:,0])<.052)&(v[:,1]>2.20)&(v[:,1]<2.40)&(v[:,2]>.22)
                if part=='traced_reference_face' and not c.get('head_topology'):v[mask,2]=.22
            if race=='skeleton':
                # Orbital asymmetry, broad zygoma, jaw angle and tooth damage are
                # independent topology edits, not uniform scaling alone.
                if 'eye' in part or 'orbital' in part:v[:,1]+=(.014*(number%3-1))*(v[:,0]>0)
                if 'tooth' in part or 'teeth' in part:
                    v[:,1]+=np.sin(v[:,0]*70+number)*(.004+number*.001)
                v[:,2]+=np.sin(v[:,0]*17+number)*.008*(v[:,1]<2.32)
            if c.get('head_topology') and 'authored_landmarks' in c:
                c['authored_landmarks']={k:2.28+(y-2.28)*height for k,y in c['authored_landmarks'].items()}
            c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist());c.pop('vertex_normals',None)
        kept.append(c)
    recipe['commands']=kept;b=builder(recipe);face_width=.22*width
    if race!='skeleton':
        ear(b,resolved['ears'],race,face_width,number);nose(b,resolved['nose'],race,number);eyebrows(b,resolved['brows'],number);mouth(b,resolved['mouth'],race,number)
    else:
        # Ten genuinely different orbital/brow/jaw details in a bone face.
        b.palette['skin']=recipe['palette'].get('skull_bone','c5bea6')
        b.palette['hair']=b.palette['skin'];eyebrows(b,resolved['brows'],number)
        for c in b.commands:c['part']='anatomy_orbital_ridge';c['material']='skin'
        nk=list(FEATURES['nose']).index(resolved['nose'])
        b.panel3('anatomy_nasal_bone','skin',[[-.016-nk*.001,2.34,.215],[.016+nk*.001,2.34,.215],[.008,2.24-nk*.003,.22+nk*.004],[-.008,2.24-nk*.003,.22+nk*.004]],.013)
        mk=list(FEATURES['mouth']).index(resolved['mouth']);count=3+mk%5
        for j in range(count):b.box('anatomy_jaw_tooth','skin',[(j-(count-1)/2)*.031,2.095+(mk%3)*.005,.222],[.022,.026+(mk%4)*.007,.015])
    if race in ('minotaur','demon','gargoyle'):
        for sign in (-1,1):
            sweep=.06*(number%3-1);root=.20 if race=='minotaur' else .15
            b.tube('anatomy_racial_horn','bone' if race=='minotaur' else 'skin' if race=='gargoyle' else 'metal',[[sign*root,2.47,-.035],[sign*(root+.10),2.55,-.065],[sign*(root+.17+sweep),2.65+number*.006,-.035],[sign*(root+.10+sweep),2.75+number*.009,.045]],[.075 if race=='minotaur' else .052,.05,.025,.002],sides=6)
    if race in ('boarfolk','elephantfolk'):
        for sign in (-1,1):b.tube('anatomy_tusk','bone',[[sign*.12,2.14,.265],[sign*(.17+number*.002),2.17,.34],[sign*.18,2.25+number*.008,.365]],[.03,.022,.002],sides=6)
    if race=='mutant':
        b.oval('anatomy_asymmetric_cheek','skin',[.20,2.22,.20],[.09,.10,.065],sides=5)
        if number%2==0:
            b.oval('anatomy_third_eye','iris',[0,2.46,.215],[.036,.025,.014],sides=6)
        for i in range(1+number%3):b.tube('anatomy_cranial_growth','skin',[[.06+i*.055,2.48,-.03],[.075+i*.065,2.61+i*.035,-.01]],[.027,.002],sides=5)
    if race in ('undead','gargoyle'):
        for sign in (-1,1):b.panel3('anatomy_hollow_cheek','shadow',[[sign*.09,2.28,.23],[sign*.18,2.25,.205],[sign*.14,2.14,.20]],.012)
        if race=='undead':b.tube('anatomy_suture','leather',[[-.17,2.40,.21],[-.075,2.365,.255]],[.006,.006],sides=4)
    commands,palette=freeze(b,'anatomy');recipe['commands'].extend(commands);recipe['palette'].update(palette)
    recipe['portrait_revision']={'schema_version':1,'race':race,'profile':number+1,'resolved':resolved,'config':config_snapshot()}
    return recipe


def procedural_hair(recipe,style):
    b=builder(recipe);b.stage=3
    cmds=[c for c in recipe['commands'] if c['part']=='traced_reference_face' or c['part']=='rounded_cranium']
    if cmds:
        vertices=np.concatenate([mesh_command(c)[0] for c in cmds]);w=float(np.ptp(vertices[:,0]))*.5;top=float(vertices[:,1].max())
    else:w=.22;top=2.55
    w=min(.34,max(.17,w));top=min(2.64,max(2.52,top))
    crown=[[top-.15,0,-.07,w*.96,.145],[top-.02,0,-.045,w*1.03,.20],[top+.045,0,-.04,w*.80,.13]]
    if style not in ('mohawk','crest','afro'):b.loft('hair_crown','hair',crown,sides=10)
    def locks(x,y,z,count,length,dx=0):
        for i in range(count):
            yy=y-i*length/count;xx=x+dx*i
            b.oval('hair_lock','hair_light' if i%2 else 'hair',[xx,yy,z+.015*(i%2)],[.045,.065,.05],sides=6)
    if style in ('mohawk','crest'):
        for i in range(3 if style=='crest' else 5):b.panel3('hair_crest','hair',[[ -.035,top-.10,-.16+i*.075],[.035,top-.10,-.16+i*.075],[.025,top+(.23 if style=='crest' else .13)+(i%2)*.035,-.13+i*.075],[-.02,top+(.24 if style=='crest' else .16),-.13+i*.075]],.028)
    elif style in ('curly','afro'):
        for layer in range(3 if style=='afro' else 2):
            for i in range(9):
                a=i*math.pi*2/9;r=w*(1.05 if style=='afro' else .92)
                b.oval('hair_curl','hair_light' if (i+layer)%3==0 else 'hair',[r*math.cos(a),top-.12+layer*.08,.15*math.sin(a)-.045],[.07,.066,.064],sides=7)
    elif style=='dreadlocks':
        for sign in (-1,1):
            for i in range(3):locks(sign*(w+.015+i*.015),top-.10-i*.02,-.08+i*.055,6,.55)
    elif style in ('ponytail','low-tail'):
        y=top+.035 if style=='ponytail' else top-.22
        b.box('hair_tail_tie','accent',[0,y,-.205],[.10,.035,.055]);b.tube('hair_tail','hair',[[0,y,-.20],[.055,y-.13,-.28],[.11,y-.40,-.27],[.12,y-.48,-.22]],[.072,.07,.052,.015],sides=7)
    elif style=='double-buns':
        for sign in (-1,1):b.oval('hair_bun','hair',[sign*w*.90,top+.04,-.02],[.09,.086,.085],sides=8)
    elif style in ('long-waves','long-straight','pageboy'):
        length=.46 if style=='pageboy' else .70
        from .constructor_hair_shape import long_back
        long_back(b,w,top,length,waves=style=='long-waves')
        for sign in (-1,1):
            if style=='long-waves':locks(sign*(w+.005),top-.14,-.01,7,length,sign*.007)
            else:
                b.loft('hair_long_panel','hair',[[top-length,sign*w*.94,.22,.027,.045],[top-length+.10,sign*w*1.08,.15,.050,.065],[top-.34,sign*w*1.10,.045,.064,.095],[top-.17,sign*w*1.02,-.015,.065,.10],[top-.08,sign*w*.90,-.04,.055,.095]],sides=8)
                if style=='long-straight':
                    for strand in range(3):
                        x=sign*(w*.82+strand*.027)
                        b.tube('hair_straight_lock','hair_light' if strand==1 else 'hair',[[x,top-.06,.10],[x*1.12,top-.20,.135],[x*1.15,top-.39,.19],[x*1.05,top-length+.06+strand*.018,.28]],[.025,.028,.021,.004],sides=5)
        if style=='long-straight':
            for sign in (-1,1):
                b.tube('hair_parted_sweep','hair',[[sign*.018,top+.014,.10],[sign*w*.42,top+.025,.15],[sign*w*.80,top-.04,.17],[sign*w*.98,top-.17,.14]],[.030,.045,.038,.012],sides=6)
        else:b.panel3('hair_fringe','hair_light',[[-w*.75,top+.006,.17],[w*.65,top+.006,.17],[w*.7,top-.16,.205],[-w*.82,top-.12,.20]],.025)
    elif style in ('undercut','side-shave','pixie'):
        side=1 if style=='side-shave' else -1
        b.panel3('hair_side_sweep','hair_light',[[side*w,top+.055,.07],[-side*w*.55,top+.09,.11],[-side*w,top-.15,.19],[side*.045,top-.11,.22]],.06)
        if style=='pixie':b.tube('hair_pixie_tuft','hair',[[0,top+.02,.07],[.06,top+.12,.055]],[.055,.009],sides=6)
    elif style in ('spiky','messy'):
        for i in range(7):
            x=(i-3)*.052
            b.tube('hair_spike','hair_light' if i%2 else 'hair',[[x,top-.015,.02],[x+(i%3-1)*(.095 if style=='messy' else .055),top+(.07 if style=='messy' else .13)+(i%2)*.04,.09 if style=='messy' else .045]],[.055,.003],sides=5)
    elif style=='pompadour':
        b.loft('hair_pompadour','hair',[[top-.10,0,.08,w*.92,.105],[top+.02,.03,.10,w*.88,.135],[top+.12,.04,.075,w*.72,.085]],sides=8)
    elif style in ('side-braid','braid-crown'):
        if style=='side-braid':b.tube('hair_side_braid_core','hair',[[-w,top-.10,.02],[-w*1.05,top-.40,.16],[-w,top-.82,.30]],[.052,.044,.020],sides=6)
        else:
            for i in range(9):
                a=i*math.pi/8
                b.oval('hair_crown_braid','hair_light' if i%2 else 'hair',[math.cos(a)*w,top+.03+math.sin(a)*.015,.155],[.044,.037,.04],sides=6)
    elif style=='fringe':
        for i in range(5):b.panel3('hair_heavy_fringe','hair',[[ -.18+i*.072,top+.02,.14],[-.12+i*.072,top+.02,.14],[-.13+i*.072,top-.17+(i%2)*.025,.23],[-.19+i*.072,top-.15,.22]],.035)
    commands,palette=freeze(b,'hairbank');return commands,palette


def facial_hair(b,settings):
    race=settings['race'];kind=settings['decor']['beard'];mustache=settings['decor']['mustache'];b.slot='head';b.stage=4
    z=.23 if race not in ('minotaur','wolf','boarfolk') else .39;y=2.115
    material='hair'
    if kind not in {'none','original'}:
        if kind in ('full','long'):
            from tools.creature_workshop.beard_sculpt import sculpt as sculpt_beard
            sculpt_beard(b,kind,z)
        elif kind in ('stubble','short','pointed','goatee','forked','braided'):
            width=.06 if kind in ('goatee','braided') else .14 if kind in ('full','long') else .10
            length=.04 if kind=='stubble' else .09 if kind=='short' else .35 if kind in ('long','braided') else .20
            if kind=='braided':
                for i in range(5):b.oval('beard_braid','hair_light' if i%2 else material,[0,y-.06-i*.055,z+.005],[.045,.05,.03],sides=6)
                b.box('beard_braid_clasp','metal',[0,y-.29,z],[.052,.03,.04])
            elif kind=='forked':
                for sign in (-1,1):b.tube('beard_fork',material,[[sign*.045,y-.01,z],[sign*.06,y-.10,z+.01],[sign*.055,y-.24,z-.01]],[.055,.047,.005],sides=6)
            else:b.loft('beard_volume',material,[[y-length,0,z-.015,.018 if kind in ('pointed','goatee','long') else width*.45,.025],[y-.07,0,z,width,.055],[y,0,z-.01,width*.94,.033]],sides=7)
        if kind in ('mutton','sideburns'):
            from tools.creature_workshop.beard_sculpt import sideburns
            sideburns(b,kind,z)
    if mustache not in {'none','original'}:
        for sign in (-1,1):
            w=.053 if mustache=='short' else .095 if mustache in ('walrus','handlebar','horseshoe') else .075
            thick=.005 if mustache=='pencil' else .023 if mustache in ('thick','walrus') else .014
            path=[[sign*.009,y+.045,z+.015],[sign*w*.65,y+.047,z+.025],[sign*w,y+.04,z+.015]]
            if mustache in ('handlebar','twirl'):path.extend([[sign*(w+.022),y+.08,z+.023],[sign*w,y+.095,z+.025]])
            if mustache in ('horseshoe','walrus','braided'):path.append([sign*w,y-.055 if mustache=='horseshoe' else y-.025,z+.025])
            if mustache=='split':path[0][0]=sign*.025
            b.tube('mustache_'+mustache,material,path,[thick]*len(path),sides=5)
