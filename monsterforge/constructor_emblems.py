"""Authored heraldic reliefs, mounted with the common garment contact pass."""
import math

KINDS={'sun','lionheart','key','skull','bear','wolf','serpent','mage','crown','pirate'}
DESCRIPTIONS={
 'sun':'Солнце: двенадцать отдельных лучей, двойной диск и центральный рельеф.',
 'lionheart':'Сердце в обрамлении львиной гривы, с мордой, ушами и парными глазами.',
 'key':'Старинный ключ с ажурным кольцом, длинным стержнем и тремя зубцами.',
 'skull':'Анатомический череп: скулы, впалые глазницы, носовая полость и отдельные зубы.',
 'bear':'Медвежья голова с круглыми ушами, широкой мордой и носом.',
 'wolf':'Волчья голова с острыми ушами, вытянутой мордой и светлыми щеками.',
 'serpent':'Изогнутая змея с расширенной головой, глазами, раздвоенным языком и сегментами брюха.',
 'mage':'Колпак мага со звездой над раскрытой книгой.',
 'crown':'Золотая корона с пятью зубцами, ободом и тремя камнями.',
 'pirate':'Пиратский череп с повязкой и перекрещенными костями.'}

def authored_badge(b,kind,cy,z):
    if kind not in KINDS:return False
    def panel(name,pts,mat='accent',depth=0):
        b.panel3('ornament_badge_'+name,mat,[[x,cy+y,z+depth] for x,y in pts],.012)
    def oval(name,x,y,rx,ry,mat='accent',depth=.012):
        b.oval('ornament_badge_'+name,mat,[x,cy+y,z+depth],[rx,ry,.012],sides=10)
    def line(name,pts,r=.007,mat='accent',depth=.018):
        b.tube('ornament_badge_'+name,mat,[[x,cy+y,z+depth] for x,y in pts],[r]*len(pts),sides=5)
    if kind=='sun':
        for i in range(12):
            a=i*math.pi/6;d=(math.cos(a),math.sin(a));n=(-d[1],d[0])
            panel('sun_ray',[(d[0]*.067+n[0]*.018,d[1]*.067+n[1]*.018),(d[0]*.132,d[1]*.132),(d[0]*.067-n[0]*.018,d[1]*.067-n[1]*.018)])
        oval('sun_disc',0,0,.065,.065);oval('sun_inset',0,0,.048,.048,'secondary',.026)
    elif kind=='key':
        line('key_ring',[(.0+math.cos(a)*.052,.072+math.sin(a)*.045) for a in [i*math.pi/8 for i in range(17)]],.010)
        line('key_stem',[(0,.025),(0,-.13)],.011)
        for y in (-.065,-.095,-.125):line('key_tooth',[(0,y),(.048,y)],.009)
    elif kind in {'skull','pirate'}:
        if kind=='pirate':
            for sign in (-1,1):
                line('pirate_bone',[(sign*-.11,-.10),(sign*.11,.10)],.009,'secondary',-.012)
                for x,y in ((sign*-.11,-.10),(sign*.11,.10)):oval('pirate_bone_end',x,y,.018,.015,'secondary',-.012)
        panel('skull_cranium',[(-.075,.025),(-.072,.084),(-.040,.12),(.040,.12),(.072,.084),(.075,.025),(.055,-.045),(.033,-.055),(-.033,-.055),(-.055,-.045)])
        for sign in (-1,1):
            oval('skull_cheek',sign*.058,-.019,.021,.022)
            panel('skull_socket',[(sign*.012,.050),(sign*.057,.057),(sign*.051,.013),(sign*.014,.017)],'leather',.024)
        panel('skull_nose',[(-.014,-.018),(0,.009),(.014,-.018),(0,-.029)],'leather',.025)
        line('skull_jaw',[(-.046,-.049),(-.034,-.091),(0,-.10),(.034,-.091),(.046,-.049)],.011)
        for x in (-.027,-.009,.009,.027):
            b.box('ornament_badge_skull_tooth','accent',[x,cy-.065,z+.027],[.013,.026,.013])
        if kind=='pirate':line('pirate_band',[(-.068,.075),(0,.089),(.067,.075)],.013,'secondary',.027)
    elif kind in {'bear','wolf','lionheart'}:
        if kind=='lionheart':
            panel('lionheart_heart',[(-.10,.025),(-.11,.078),(-.070,.11),(-.02,.094),(0,.065),(.02,.094),(.07,.11),(.11,.078),(.10,.025),(0,-.13)],'secondary')
            for i in range(12):
                a=i*math.pi/6;oval('lionheart_mane',math.cos(a)*.066,math.sin(a)*.074,.028,.031,depth=.014)
        oval(kind+'_face',0,0,.060,.073,depth=.025)
        for sign in (-1,1):
            if kind=='wolf':panel('wolf_ear',[(sign*.027,.047),(sign*.065,.126),(sign*.082,.032)],depth=.01)
            else:oval(kind+'_ear',sign*.057,.064,.027,.027,depth=.014)
            oval(kind+'_eye',sign*.029,.018,.009,.007,'leather',.045)
            oval(kind+'_muzzle',sign*.020,-.031,.027,.026,'secondary',.043)
        oval(kind+'_nose',0,-.015,.019,.013,'leather',.057)
        line(kind+'_mouth',[(-.025,-.051),(0,-.059),(.025,-.051)],.003,'leather',.056)
    elif kind=='serpent':
        path=[(.057*math.sin(i*.65),.088-i*.024) for i in range(9)]
        line('serpent_body',path,.016)
        panel('serpent_head',[(-.023,.084),(-.029,.117),(0,.139),(.029,.117),(.023,.084)],depth=.020)
        for sign in (-1,1):oval('serpent_eye',sign*.012,.115,.005,.005,'leather',.04)
        line('serpent_tongue',[(0,.137),(0,.151),(-.012,.16)],.002,'secondary')
        line('serpent_tongue',[(0,.151),(.012,.16)],.002,'secondary')
        for x,y in path[1:-1]:line('serpent_belly',[(x-.008,y),(x+.008,y)],.002,'secondary',.036)
    elif kind=='mage':
        panel('mage_book',[(-.115,-.056),(-.055,-.041),(0,-.059),(.055,-.041),(.115,-.056),(.10,-.115),(0,-.098),(-.10,-.115)],'secondary')
        panel('mage_hat',[(-.069,-.023),(-.029,.083),(.018,.137),(.050,.125),(.027,.113),(.075,-.023)])
        line('mage_brim',[(-.099,-.028),(.098,-.028)],.012)
        panel('mage_star',[(0,.067),(.008,.042),(.035,.04),(.014,.026),(.020,0),(0,.015),(-.020,0),(-.014,.026),(-.035,.04),(-.008,.042)],'secondary',.02)
    elif kind=='crown':
        panel('crown_points',[(-.105,-.055),(-.12,.076),(-.063,.025),(-.054,.112),(0,.043),(.054,.112),(.063,.025),(.12,.076),(.105,-.055)])
        line('crown_band',[(-.102,-.052),(0,-.067),(.102,-.052)],.012)
        for x in (-.066,0,.066):oval('crown_gem',x,-.025,.011,.016,'secondary',.025)
    return True


def refine_reference(recipe,settings,slot):
    """Old symbol selections retain lineage and receive the current derived relief."""
    kind={2:'sun',5:'skull',10:'serpent'}.get(settings['reference_parts']['emblems'])
    if slot!='torso' or kind is None:return
    from .constructor_decor import sculpt
    from .constructor_portraits import freeze
    recipe['commands'][:]=[c for c in recipe['commands'] if not c['part'].startswith('atlas_emblems_')]
    b=sculpt(settings);b.slot=slot;authored_badge(b,kind,1.52,.325)
    commands,palette=freeze(b,'atlas_emblems_refined')
    for c in commands:c['slot']=slot
    recipe['commands'].extend(commands);recipe['palette'].update(palette)
    recipe['emblem_revision']={'schema_version':1,'kind':kind,'derived_from_reference_variant':settings['reference_parts']['emblems'],'description_ru':DESCRIPTIONS[kind]}


def apply_native(recipe,settings,slot):
    kind=settings['decor']['emblem']
    if slot!='torso' or kind not in KINDS or settings['reference_parts']['emblems']:return
    from .constructor_decor import sculpt
    from .constructor_portraits import freeze
    # Clothing replaces torso geometry. Add the independent selected badge after it.
    recipe['commands'][:]=[c for c in recipe['commands'] if not c['part'].startswith('ornament_badge_')]
    b=sculpt(settings);b.slot=slot;authored_badge(b,kind,1.52,.325)
    commands,palette=freeze(b,'ornament_badge')
    for c in commands:c['slot']=slot
    recipe['commands'].extend(commands);recipe['palette'].update(palette)
    recipe['emblem_revision']={'schema_version':1,'kind':kind,'description_ru':DESCRIPTIONS[kind]}
