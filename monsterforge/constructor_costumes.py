"""Additional modular costumes authored on approved clothing proportions."""
import copy
from .constructor_decor import sculpt
from .constructor_portraits import freeze
from .constructor_goblins import COSTUMES as GOBLIN_COSTUMES

COSTUMES={'costume-druid':'Костюм друида','costume-angel':'Костюм ангела','costume-demon':'Демонические доспехи'}
COSTUMES.update(GOBLIN_COSTUMES)
from .constructor_sea_costumes import LABELS as SEA_COSTUMES, DESCRIPTIONS as SEA_DESCRIPTIONS, BASE as SEA_BASE
COSTUMES.update(SEA_COSTUMES)
DESCRIPTIONS={'costume-druid':'Лесное длинное одеяние: зелёная ткань, перекрывающиеся листья, кожаные перевязи и деревянные застёжки.',
 'costume-angel':'Светлые рыцарские доспехи с золотым кантом, веерными панелями и белым табардом.',
 'costume-demon':'Тёмные демонические доспехи: заострённые нагрудные пластины, бордовые панели и костяные шипы на наручах и поножах.'}

DESCRIPTIONS.update(SEA_DESCRIPTIONS)

def atlas_settings(settings,slot):
    field='outfit' if slot=='torso' else 'arms' if slot.endswith('_arm') else 'legs' if slot.endswith('_leg') else None
    if field is None or settings[field] not in COSTUMES:return settings
    s=copy.deepcopy(settings);k=settings[field];gender=s['gender']
    if k in SEA_COSTUMES:
        s['reference_parts'][gender+'_clothes']=SEA_BASE[k][gender=='female']
        s['reference_parts'][('female' if gender=='male' else 'male')+'_clothes']=0
        return s
    if k in GOBLIN_COSTUMES:
        index=list(GOBLIN_COSTUMES).index(k)
        s['reference_parts'][gender+'_clothes']=[5,6,1][index] if gender=='male' else [5,6,1][index]
        s['reference_parts'][('female' if gender=='male' else 'male')+'_clothes']=0
        return s
    s['reference_parts'][gender+'_clothes']=3 if k=='costume-druid' and gender=='male' else 2 if k=='costume-druid' else 1 if k=='costume-angel' else 2 if gender=='male' else 1
    s['reference_parts'][('female' if gender=='male' else 'male')+'_clothes']=0
    return s

def apply(recipe,settings,slot):
    field='outfit' if slot=='torso' else 'arms' if slot.endswith('_arm') else 'legs' if slot.endswith('_leg') else None
    if field is None or settings[field] not in COSTUMES:return
    if settings[field] in SEA_COSTUMES:
        from .constructor_sea_costumes import apply as sea_costume
        return sea_costume(recipe,settings,slot,settings[field])
    if settings[field] in GOBLIN_COSTUMES:
        from .constructor_goblins import costume
        return costume(recipe,settings,slot)
    k=settings[field];b=sculpt(settings);b.slot=slot;b.stage=3
    palette={'costume-druid':dict(cloth='456447',secondary='758651',metal='88794b',accent='c3ad70',leather='574332'),
        'costume-angel':dict(cloth='e1dfcf',secondary='c6cfc9',metal='c3cbd0',accent='c8a754',leather='8c7960'),
        'costume-demon':dict(cloth='492b35',secondary='833e46',metal='363741',accent='b3a18a',leather='34232c')}[k]
    for name in recipe['palette']:
        for channel,value in palette.items():
            if name==channel or name.endswith('_'+channel):recipe['palette'][name]=(settings['colors'].get(channel) or value).lstrip('#')
    b.palette.update(palette)
    for channel in palette:
        if settings['colors'].get(channel):b.palette[channel]=settings['colors'][channel].lstrip('#')
    def panel(name,pts,mat):b.panel3('costume_'+name,mat,pts,.016)
    if slot=='torso':
        if k=='costume-druid':
            for sign in (-1,1):
                for i in range(5):
                    x=sign*(.08+i*.031);y=1.77-i*.095
                    panel('leaf_lapel',[[x,y+.055,.29],[x+sign*.09,y,.29],[x+sign*.025,y-.12,.30],[x-sign*.017,y-.027,.30]],'secondary')
                    b.tube('costume_leaf_vein','accent',[[x,y+.03,.307],[x+sign*.024,y-.092,.307]],[.003,.001],sides=4)
            for y in (1.57,1.38,1.19):b.oval('costume_wood_clasp','leather',[0,y,.32],[.023,.025,.012],sides=8)
        else:
            for sign in (-1,1):
                for i in range(3):
                    x=sign*(.055+i*.065);y=1.78-i*.045
                    panel('breastplate_feather' if k=='costume-angel' else 'breastplate_fang',[[x-sign*.027,y,.30],[x+sign*.057,y-.02,.30],[x+sign*.035,y-.23-(.03*i),.31],[x-sign*.01,y-.15,.31]],'metal')
                    b.tube('costume_plate_trim','accent',[[x,y-.01,.328],[x+sign*.026,y-.19-.03*i,.328]],[.005,.003],sides=5)
            for sign in (-1,1):panel('waist_tasset',[[sign*.03,1.13,.27],[sign*.24,1.11,.26],[sign*.20,.88,.26],[sign*.08,.80,.27]],'secondary')
    elif slot.endswith('_arm'):
        sign=-1 if slot.startswith('left') else 1
        for i in range(3):
            x=sign*(.57+i*.038);y=1.40-i*.083
            panel('bracer_scale',[[x-.052,y+.035,.15],[x+.052,y+.035,.15],[x+.040,y-.065,.16],[x,y-.09,.16],[x-.040,y-.065,.16]],'secondary' if k=='costume-druid' else 'metal')
            if k=='costume-demon':b.tube('costume_bracer_spike','accent',[[x,y,.17],[x+sign*.07,y+.06,.20],[x+sign*.11,y+.04,.22]],[.022,.013,.002],sides=5)
    else:
        sign=-1 if slot.startswith('left') else 1;x=sign*.21
        for i in range(3):
            y=.38-i*.073
            panel('greave_scale',[[x-.075,y+.05,.18],[x+.075,y+.05,.18],[x+.060,y-.045,.20],[x,y-.073,.20],[x-.060,y-.045,.20]],'secondary' if k=='costume-druid' else 'metal')
    commands,pal=freeze(b,'new_costume')
    for c in commands:c['slot']=slot
    recipe['palette'].update(pal);recipe['commands'].extend(commands)
    recipe['costume_revision']={'schema_version':1,'id':k,'description_ru':DESCRIPTIONS[k]}

def fit(recipe):
    from .constructor_surface_fit import mount_front
    detail=[c for c in recipe['commands'] if c['part'].startswith('new_costume_')]
    support=[c for c in recipe['commands'] if c not in detail and not any(t in c['part'] for t in ('ornament_','atlas_emblems_','cloth_motif_'))]
    if detail:
        mount_front(detail,support,relief=-.002)
        # Re-seat badges and embroidery against the final fitted armour layers.
        from .constructor_surface_fit import fit_ornaments
        from .constructor_cloth_motifs import refit
        slot=detail[0]['slot']
        if slot=='torso':fit_ornaments(recipe)
        refit(recipe,slot)
