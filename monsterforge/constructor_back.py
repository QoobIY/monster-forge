"""Independent back geometry, baked into immutable part revisions with source lineage."""
import hashlib
import json
from pathlib import Path
import numpy as np
from .constructor_portraits import builder,freeze
from tools.creature_workshop.geometry import mesh

STYLES=dict(short='Короткий плащ',royal='Королевский плащ',split='Раздвоенный плащ',ranger='Плащ следопыта',layered='Многослойная накидка',feather='Пернатые крылья',fan='Веерные крылья',raven='Вороньи крылья',membrane='Перепончатые крылья',dragon='Драконьи крылья',crystal='Кристальные крылья',mechanical='Механические крылья',pack='Походный рюкзак',bedroll='Рюкзак со спальником',quiver='Колчан стрел',books='Книги и свитки',banner='Знамя',twinbanner='Два штандарта',shield='Щит на спине',plates='Броневые пластины',spikes='Шипованный панцирь',alchemy='Алхимический ранец',lantern='Рюкзак с фонарём',trophies='Охотничьи трофеи')
WING_STYLES=dict(swept='Стреловидные',broad='Широкие',long='Длинные',compact='Компактные',fan='Веерные',layered='Многослойные',crystal='Кристальные',mechanical='Бронированные',thorn='С шипами',ornate='С цветными панелями')
IDS={**{f'back-{k}':v for k,v in STYLES.items()},**{f'wing-{race}-{k}':v+' крылья' for race in ('sky-bird','sky-bat','sky-dragon') for k,v in WING_STYLES.items()}}
from tools.creature_workshop.celestial_wings import LABELS as CELESTIAL_WINGS
IDS.update(CELESTIAL_WINGS)
from .constructor_goblins import BACKS as GOBLIN_BACKS
IDS.update(GOBLIN_BACKS)
COLORS={'back_primary':'#6d789b','back_secondary':'#caaa6c','back_frame':'#565b64'}

def options():
    return [{'id':id,'label':label,'contract':'humanoid_v1' if id.startswith('back-') else {'sky-bird':'avian_authoring_v1','sky-bat':'chiropteran_authoring_v1','sky-dragon':'dragon_authoring_v1'}[next(r for r in ('sky-bird','sky-bat','sky-dragon') if id.startswith('wing-'+r+'-'))]} for id,label in IDS.items()]

def tint(recipe,colors):
    # Explicit channels override only this part; old palette remains when unset.
    groups={}
    for name in recipe['palette']:
        low=name.lower()
        key='back_frame' if any(t in low for t in ('frame','metal','leather','bone','shaft')) else 'back_secondary' if any(t in low for t in ('secondary','accent','trim','tip','gold')) else 'back_primary'
        groups[name]=key
        if colors[key]:recipe['palette'][name]=colors[key].lstrip('#')
    recipe['back_color_channels']=groups


def author(recipe,id,slot):
    if id not in IDS:return recipe
    from . import workshop_constructor as e
    snapshot={'schema_version':1,'id':id,'label':IDS[id],'generator':'constructor_back_v1','generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    b=builder(recipe);b.slot=slot;b.stage=3
    if id.startswith('wing-'):
        style=id.rsplit('-',1)[-1];factor={'swept':(1.12,.85),'broad':(1.25,1.05),'long':(1.4,.80),'compact':(.78,.88),'fan':(1.1,1.23),'layered':(1,1),'crystal':(1.06,1),'mechanical':(.96,1.08),'thorn':(1.12,1),'ornate':(1,1)}[style]
        anchor=np.asarray(recipe['contract_anchors'][slot]);scale=np.array([factor[0],factor[1],1])
        recipe['commands']=[e._transform(c,scale,anchor*(1-scale),id) for c in recipe['commands']]
        verts=np.concatenate([mesh(c)[0] for c in recipe['commands']]);lo,hi=verts.min(0),verts.max(0);sign=-1 if slot.startswith('left') else 1
        if style in {'layered','crystal','mechanical','thorn','ornate','fan'}:
            for i in range(7 if style=='layered' else 5):
                p=anchor+(np.array([sign*abs(hi[0]-lo[0])*(i+1)/6,(hi[1]-anchor[1])*(i+1)/6,-.045]))
                if style=='thorn':b.tube('wing_spike','accent',[p.tolist(),(p+[0,.14,-.02]).tolist()],[.045,.003],sides=5)
                elif style=='mechanical':b.box('wing_armor','metal',p.tolist(),[.12,.17,.07])
                elif style=='crystal':b.oval('wing_crystal','secondary',p.tolist(),[.065,.15,.065],sides=5)
                else:b.panel3('wing_colored_panel','secondary',[(p+[-.055,.07,0]).tolist(),(p+[.09,.04,0]).tolist(),(p+[.06,-.12,0]).tolist(),(p+[-.07,-.05,0]).tolist()],.028)
        commands,palette=freeze(b,'back_detail_'+slot);
        for c in commands:c['slot']=slot
        recipe['commands'].extend(commands);recipe['palette'].update(palette)
    else:
        style=id[5:];z=-.27
        if id in GOBLIN_BACKS:
            from .constructor_goblins import back as author_goblin_back
            b.palette['bone']='d3c7a4'
            author_goblin_back(b,id)
        elif id in CELESTIAL_WINGS:
            from tools.creature_workshop.celestial_wings import author as celestial
            celestial(b,style,z)
        elif style in {'short','royal','split','ranger','layered'}:
            bottom={'short':1.13,'royal':.22,'split':.47,'ranger':.68,'layered':.84}[style];w=.36 if style!='royal' else .47
            for side in (-1,1):
                points=[[side*.13,1.90,z],[side*.28,1.76,z-.025],[side*w,bottom,z-.09],[side*(.055 if style=='split' else 0),bottom+.08,z-.11],[0,1.82,z]]
                b.panel3('cape_body','cloth',points,.045)
                b.tube('cape_border','accent',points[1:4],[.025]*3,sides=5)
            if style=='layered':b.panel3('cape_upper_layer','secondary',[[-.34,1.78,z-.07],[.34,1.78,z-.07],[.29,1.27,z-.14],[-.29,1.27,z-.14]],.045)
            if style=='royal':
                for y in (1.48,1.13,.78):b.oval('royal_medallion','metal',[0,y,z-.14],[.055,.065,.022],sides=6)
        elif style=='raven':
            from tools.creature_workshop.feather_wings import raven_wings
            raven_wings(b,z)
        elif style in {'feather','fan','membrane','dragon','crystal','mechanical'}:
            for sign in (-1,1):
                root=[sign*.16,1.78,z];tip=[sign*1.02,2.13,z-.09]
                b.tube('wing_frame','metal',[root,[sign*.52,2.1,z-.05],tip],[.065,.04,.01],sides=6)
                if style in {'membrane','dragon'}:
                    for i in range(4):
                        end=[sign*(.42+i*.16),1.14+i*.15-(.12 if style=='dragon' and i%2==0 else 0),z-.14]
                        b.panel3('wing_membrane','cloth',[root,tip,end],.025)
                        b.tube('wing_rib','metal',[root,end],[.028,.008],sides=5)
                else:
                    for i in range(7):
                        x=.30+i*.105;y=1.80+i*.05;length=(.37+(6-i)*.020 if style=='fan' else .55+(6-i)*.055 if style=='raven' else .46+(6-i)*.035)
                        mat='secondary' if i%3==0 else 'cloth'
                        if style=='crystal':b.oval('wing_crystal',mat,[sign*x,y-.12,z-.08],[.09,length/2,.05],sides=5)
                        else:b.panel3('wing_blade',mat,[[sign*x,y,z],[sign*(x+.15),y+.07,z],[sign*(x+.18),y-length,z-.10],[sign*(x+.045),y-length-.08,z-.09]],.04 if style=='mechanical' else .022)
                if style in {'fan','raven'}:b.panel3('upper_wing_fan','accent',[[sign*.19,1.8,z],[sign*.65,2.27,z],[sign*1.12,2.05,z],[sign*.6,1.8,z]],.025)
        elif style in {'pack','bedroll','books','alchemy','lantern','trophies'}:
            b.loft('backpack_body','cloth',[[1.225,0,z-.13,.185,.115],[1.29,0,z-.13,.218,.135],[1.66,0,z-.13,.22,.138],[1.77,0,z-.13,.193,.115]],sides=8)
            b.panel3('backpack_flap','secondary',[[-.215,1.78,z-.263],[.215,1.78,z-.263],[.20,1.62,z-.279],[0,1.58,z-.293],[-.20,1.62,z-.279]],.025)
            for x in (-.13,.13):b.box('pack_strap','leather',[x,1.50,z-.28],[.045,.52,.025])
            if style=='bedroll':b.tube('rolled_blanket','secondary',[[-.30,1.94,z-.13],[.30,1.94,z-.13]],[.105,.105],sides=8)
            if style=='books':
                for i in range(3):b.box('book_spine','accent' if i%2 else 'secondary',[-.11+i*.11,1.49,z-.31],[.085,.31+i*.02,.06])
            if style=='alchemy':
                for x in (-.30,.30):b.oval('alchemy_flask','secondary',[x,1.50,z-.12],[.09,.14,.09],sides=6);b.box('flask_cap','metal',[x,1.65,z-.12],[.07,.05,.07])
            if style=='lantern':b.box('lantern_glow','accent',[.31,1.32,z-.13],[.14,.19,.12]);b.box('lantern_roof','metal',[.31,1.45,z-.13],[.18,.05,.16])
            if style=='trophies':
                for sign in (-1,1):b.tube('trophy_horn','accent',[[sign*.24,1.5,z-.18],[sign*.35,1.67,z-.16],[sign*.32,1.85,z-.13]],[.055,.036,.003],sides=6)
        elif style=='quiver':
            b.tube('quiver_case','cloth',[[-.14,1.17,z-.12],[.14,1.78,z-.12]],[.10,.13],sides=8)
            for i in range(7 if style=='layered' else 5):
                x=.03+i*.047;b.tube('arrow_shaft','metal',[[x,1.55,z-.10],[x,2.04+i*.025,z-.10]],[.012,.012],sides=5);b.panel3('arrow_fletching','secondary',[[x,1.99,z-.1],[x+.05,2.08,z-.1],[x,2.15,z-.1]],.015)
        elif style in {'banner','twinbanner'}:
            for x in ([.0] if style=='banner' else [-.25,.25]):
                b.tube('standard_pole','metal',[[x,1.2,z],[x,2.67,z]],[.025,.025],sides=6);b.panel3('standard_cloth','cloth',[[x,2.55,z],[x+.38,2.55,z],[x+.35,2.08,z],[x+.19,2.16,z],[x,2.08,z]],.025);b.oval('standard_emblem','accent',[x+.17,2.36,z-.025],[.075,.075,.02],sides=6)
        elif style=='shield':
            b.panel3('back_shield','cloth',[[-.27,1.85,z-.05],[.27,1.85,z-.05],[.28,1.47,z-.11],[0,1.08,z-.14],[-.28,1.47,z-.11]],.085);b.box('shield_cross','accent',[0,1.56,z-.17],[.07,.52,.025]);b.box('shield_cross_bar','accent',[0,1.68,z-.17],[.4,.06,.025])
        else:
            for i in range(4):
                y=1.78-i*.17;w=.34-i*.04;b.panel3('dorsal_armor','cloth',[[-w,y,z],[0,y+.09,z-.1],[w,y,z],[w*.85,y-.14,z],[0,y-.18,z-.11],[-w*.85,y-.14,z]],.065)
                b.oval('armor_stud','accent',[0,y-.04,z-.17],[.038,.038,.02],sides=6)
                if style=='spikes':b.tube('dorsal_spike','metal',[[0,y,z-.11],[0,y+.06,z-.40]],[.065,.003],sides=5)
        from tools.creature_workshop.accessory_details import back as detail_back
        if style!='raven' and id not in CELESTIAL_WINGS:detail_back(b,style,z)
        commands,palette=freeze(b,'back_design')
        for c in commands:c['slot']=slot
        recipe['commands']=commands;recipe['palette']=palette
    recipe['commands'].sort(key=lambda c:c['stage'])
    snapshot['commands_sha256']=hashlib.sha256(json.dumps(recipe['commands'],sort_keys=True).encode()).hexdigest()
    recipe['back_design']=snapshot
    return recipe
