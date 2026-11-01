"""Derived satyr anatomy on the existing explicit humanoid bone assignments."""
import copy

import numpy as np

REVISION = 2
LABELS = ('Лесной сатир · козлиные рога и косматая шерсть',
          'Проклятый сатир · витые бараньи рога и спинные шипы',
          'Король сатиров · ветвистые рога, грива и нагрудная перевязь')


def fur(b, name, roots, length=.12, radius=.045):
    for i, root in enumerate(roots):
        p=np.asarray(root,float)
        end=p+[np.sign(p[0])*.025,-length*(.85+.1*(i%3)), -.025]
        b.tube(name,'secondary',[p.tolist(),((p+end)*.5+[0,0,.014]).tolist(),end.tolist()],
               [radius,radius*.72,.002],sides=5)


def author(b, variant):
    v=variant
    if b.slot=='head':
        b.bone='head'
        b.loft('satyr_faceted_cranium','skin',[[1.99,0,.12,.105,.11],
               [2.08,0,.10,.17,.17],[2.25,0,.075,.225,.205],
               [2.39,0,.045,.20,.16],[2.46,0,.035,.13,.10]],sides=12)
        b.loft('satyr_tapered_goat_muzzle','skin',[[2.025,0,.28,.085,.075],
               [2.09,0,.29,.14,.14],[2.17,0,.22,.13,.11]],sides=10)
        b.oval('satyr_split_nose','dark',[0,2.12,.414],[.079,.042,.025])
        b.tube('satyr_muzzle_cleft','lip',[[0,2.11,.433],[0,2.055,.403]],[.008,.006])
        for side in (-1,1):
            b.oval('satyr_cheek_plane','skin',[side*.16,2.17,.215],[.088,.10,.064])
            b.oval('satyr_eye_socket','shadow',[side*.105,2.276,.255],[.070,.052,.034])
            b.oval('satyr_amber_eye','eyes',[side*.105,2.276,.282],[.048,.031,.015])
            b.oval('satyr_horizontal_goat_pupil','pupil',[side*.105,2.276,.296],[.031,.008,.006])
            b.tube('satyr_heavy_brow','skin',[[side*.045,2.323,.261],[side*.12,2.34,.256],[side*.19,2.30,.224]],[.032,.042,.018])
            b.panel3('satyr_leaf_shaped_ear','skin',[[side*.17,2.25,.07],[side*.40,2.39,.015],
                     [side*.36,2.23,.06],[side*.21,2.18,.10]],.045)
            b.panel3('satyr_ear_inner_plane','shadow',[[side*.22,2.25,.085],[side*.365,2.355,.042],
                     [side*.32,2.245,.081]],.010)
            if v==0:
                path=[[side*.14,2.40,.02],[side*.20,2.59,-.06],[side*.18,2.76,-.19],[side*.11,2.78,-.26]]
            elif v==1:
                path=[[side*.15,2.39,.03],[side*.30,2.53,-.03],[side*.39,2.43,-.17],
                      [side*.37,2.25,-.20],[side*.27,2.20,-.12],[side*.24,2.29,-.055]]
            else:
                path=[[side*.14,2.40,.01],[side*.22,2.62,-.08],[side*.31,2.82,-.14],[side*.28,3.00,-.20]]
            radii=np.linspace(.08 if v!=1 else .105,.004,len(path))
            b.tube('satyr_anatomical_horn','bone',path,radii.tolist(),sides=9)
            if v==2:
                for j in (1,2):
                    p=np.array(path[j]);end=p+[side*.17,.15,.04]
                    b.tube('satyr_royal_horn_tine','bone',[p.tolist(),(p+[side*.12,.07,.04]).tolist(),end.tolist()],[.046,.027,.002])
            # Horn ridges follow the horn rather than floating around the skull.
            for j in range(1,len(path)-1):
                p=np.array(path[j]);b.oval('satyr_horn_growth_ridge','bone',p.tolist(),[float(radii[j]*1.10),float(radii[j]*.60),float(radii[j]*1.10)])
        fur(b,'satyr_pointed_goatee',[[x,2.025,.325-abs(x)*.15] for x in (-.06,-.025,.025,.06)],.20,.04)
        fur(b,'satyr_occipital_mane',[[x,y,-.115] for y in (2.37,2.24,2.10) for x in (-.12,0,.12)],.14 if v!=2 else .21,.055)
        if v==1:
            b.panel3('satyr_cursed_scar','lip',[[.04,2.34,.272],[.056,2.35,.274],[.14,2.23,.29],[.126,2.22,.291]],.007)
        if v==2:
            b.oval('satyr_royal_forehead_stone','accent',[0,2.38,.204],[.042,.060,.026],sides=6)
    elif b.slot=='torso':
        b.bone='pelvis'
        b.loft('satyr_furred_pelvis','secondary',[[.88,0,0,.20,.15],[1.04,0,0,.28,.20],[1.16,0,.01,.24,.17]],sides=10)
        fur(b,'satyr_hip_fur',[[s*x,y,z] for s in (-1,1) for x,y,z in ((.24,1.09,.10),(.22,1.04,-.12),(.25,.98,.03))],.14,.07)
        b.bone='chest'
        width=(.32,.35,.36)[v]
        b.loft('satyr_contoured_trunk','skin',[[1.08,0,.015,.22,.16],[1.27,0,.02,.245,.18],
               [1.48,0,.035,width,.205],[1.68,0,.04,.32,.18],[1.78,0,.05,.23,.145]],sides=12)
        for s in (-1,1):
            b.oval('satyr_pectoral_plane','skin',[s*.14,1.58,.194],[.145,.11,.055],sides=10)
            fur(b,'satyr_chest_fur',[[s*x,1.64-x*.35,.23] for x in (.025,.075,.12)],.15,.036)
        fur(b,'satyr_dorsal_mane',[[x,y,-.145] for y in (1.74,1.60,1.44) for x in (-.08,0,.08)],.13 if v!=2 else .22,.052)
        if v==1:
            for y in (1.70,1.55,1.40):
                b.tube('satyr_cursed_dorsal_spine','bone',[[0,y,-.15],[0,y+.09,-.36]],[.06,.003])
        if v==2:
            b.panel3('satyr_royal_crossbody_leather','leather',[[-.29,1.70,.16],[-.22,1.75,.20],[.24,1.18,.20],[.17,1.14,.22]],.028)
            for x,y in ((-.17,1.59),(0,1.40),(.16,1.22)):
                b.oval('satyr_royal_harness_stud','metal',[x,y,.249],[.021,.021,.013],sides=6)
        b.bone='neck'
        b.loft('satyr_anatomical_neck','skin',[[1.73,0,.075,.135,.12],[1.87,0,.085,.115,.10],[2.04,0,.10,.12,.105]],sides=10)
    elif b.slot.endswith('_arm'):
        s=-1 if b.slot.startswith('left') else 1;prefix='left' if s<0 else 'right'
        b.bone=prefix+'_shoulder'
        b.tube('satyr_deltoid_biceps','skin',[[s*.36,1.80,.04],[s*.49,1.66,.035],[s*.62,1.49,.025],[s*.72,1.36,.02]],
               [.135,.15 if v!=0 else .125,.115,.09],sides=10)
        fur(b,'satyr_shoulder_fur',[[s*x,y,-.025] for x,y in ((.37,1.83),(.45,1.75),(.52,1.65))],.15,.07)
        b.bone=prefix+'_elbow'
        b.tube('satyr_tapered_forearm','skin',[[s*.72,1.36,.02],[s*.77,1.21,.045],[s*.82,1.02,.08]], [.09,.11,.06],sides=10)
        fur(b,'satyr_elbow_tuft',[[s*.72,1.33,-.04],[s*.76,1.20,-.025]],.11,.045)
        b.bone=prefix+'_hand'
        b.oval('satyr_fingered_palm','skin',[s*.82,.94,.10],[.079,.105,.055])
        for i in range(4):
            x=s*.82+(i-1.5)*.034;drop=(.115,.15,.145,.105)[i]
            path=[[x,.91,.115],[x,.84,.145],[x,.91-drop,.18]]
            b.tube('satyr_articulated_finger','skin',path,[.021,.019,.013])
            b.tube('satyr_finger_claw','bone',[path[-1],[x,.89-drop,.215]],[.014,.002])
        b.tube('satyr_opposed_thumb','skin',[[s*.77,.98,.10],[s*.72,.93,.16],[s*.74,.87,.18]],[.029,.025,.013])
    else:
        s=-1 if b.slot.startswith('left') else 1;prefix='left' if s<0 else 'right'
        b.bone=prefix+'_hip'
        b.tube('satyr_contoured_goat_thigh','secondary',[[s*.22,.95,0],[s*.25,.78,.04],[s*.28,.50,.02]], [.17,.175 if v!=0 else .15,.105],sides=10)
        fur(b,'satyr_thigh_shag',[[s*x,y,z] for x,y,z in ((.34,.85,.07),(.36,.72,.03),(.30,.80,.16),(.20,.65,-.08))],.15,.055)
        b.bone=prefix+'_knee'
        b.tube('satyr_digitigrade_shank','secondary',[[s*.28,.50,.02],[s*.30,.36,-.055],[s*.32,.23,-.09],[s*.32,.14,.12]], [.105,.085,.065,.060],sides=9)
        fur(b,'satyr_hock_shag',[[s*.34,.39,-.08],[s*.30,.32,-.105]],.10,.038)
        b.bone=prefix+'_foot'
        for toe in (-1,1):
            # Individual convex hoof halves share Y=0, with a real cloven gap.
            x=s*.32+toe*.053
            b.loft('satyr_cloven_hoof','dark',[[0,x,.20,.047,.14],[.045,x,.20,.049,.142],
                   [.13,x,.18,.044,.105],[.18,x,.14,.033,.060]],sides=8)
            b.loft('satyr_hoof_growth_band','bone',[[.125,x,.18,.0445,.1055],[.143,x,.17,.041,.093]],sides=8)
        for sign in (-1,1):
            b.tube('satyr_rear_dewclaw','bone',[[s*.32+sign*.045,.19,-.025],[s*.32+sign*.05,.12,-.06]],[.025,.004])


def apply(recipe, slot):
    design=recipe.get('constructor_anatomy',{})
    if design.get('race')!='satyr':return
    from .constructor_marsh_forest import Anatomy
    source=copy.deepcopy(recipe['commands'])
    b=Anatomy(design,slot,'head')
    b.palette=copy.deepcopy(recipe['palette'])
    author(b,design['variant'])
    recipe['commands']=b.commands;recipe['palette'].update(b.palette)
    recipe['satyr_anatomy_revision']={'schema_version':1,'revision':REVISION,
        'label':LABELS[design['variant']],'source_commands':[c['id'] for c in source],
        'method':'anatomical derived modules; original source and bone contract unchanged'}
