"""Ten modular spirits; independent face and garment choices on humanoid_v1."""
from .paths import ROOT

SOURCE = ROOT/'media/constructor/ghosts/v2'
FORM_CARDS = ROOT/'media/constructor/ghost_forms/v3'
BODY_CARDS = ROOT/'media/constructor/ghost_refinements/v2'
ARM_DONORS = ROOT/'media/constructor/ghost_arm_donors/v1'
FORMS = {'regular':'С ногами', 'ghost_spirit':'Дух без ног'}
SPIRIT_DESCRIPTION = 'Вместо ног и обуви — единый сужающийся призрачный шлейф с изгибом назад. Две составные половины имеют общий контур, без коленей и ступней.'
NAMES = ['Тихий дух', 'Плачущая душа', 'Погребённый', 'Падший рыцарь',
         'Призрачный маг', 'Узник', 'Утопленник', 'Погребальный жрец',
         'Древний предок', 'Безликий']
FACES = [
 'Узкое спокойное мужское лицо, впалые щёки, светящиеся пустые глаза и седой пробор.',
 'Женское лицо с высокими скулами, скорбным ртом, тёмными слёзными дорожками и длинными белыми волосами.',
 'Иссохшее мужское лицо, выраженная челюсть, закрытый рот и погребальные повязки на темени.',
 'Широкое мужское лицо воина, тяжёлые надбровья, переломанный шрам и короткие серебряные волосы.',
 'Вытянутое женское лицо с острым подбородком, светлыми глазами и длинными височными прядями.',
 'Худое лысое мужское лицо с запавшими висками, сомкнутыми губами и меткой заточения на лбу.',
 'Мужское лицо с широким носом, тяжёлым подбородком, мокрыми прядями и потемневшими губами.',
 'Женское лицо с высоким лбом, строгими глазами и ритуальной диадемой.',
 'Старое мужское лицо с выраженными скулами, седыми волосами, длинными усами и бородой.',
 'Гладкая вытянутая погребальная маска без носа и рта, две глубокие узкие глазницы и вертикальный знак на лбу.'
]
COSTUMES = [
 'Узкий саван с диагональным запахом, ступенчатым рваным подолом и тканевыми обмотками предплечий.',
 'Приталенное погребальное платье с широкими свисающими рукавами, поясом-шнуром и длинными раздельными полами.',
 'Многослойные погребальные ленты поверх туники, обмотанные предплечья и ноги, асимметричные концы ткани.',
 'Старинная кираса с четырьмя изогнутыми нагрудными пластинами, наплечными лепестками, латными перчатками и поножами.',
 'Длинная мантия с двойным воротом, раскрытыми рукавами, гравированными вертикальными лентами и тройным поясом.',
 'Рваная рубаха с открытыми предплечьями, широким кожаным поясом, железными браслетами и повреждёнными штанами.',
 'Двубортный морской сюртук с отворотами, косым перевязем, застёжками и высокими сапогами.',
 'Широкое жреческое облачение, длинная стола с костяными орнаментами, ступенчатые рукава и церемониальный пояс.',
 'Мантия предка с тяжёлой наплечной накидкой, несколькими перекрывающимися полами и узорными манжетами.',
 'Тёмное узкое облачение с рассечёнными продольными полотнами, острыми манжетами и светлыми швами.'
]

def settings(variant=0):
    from .workshop_constructor import default_settings
    s = default_settings()
    donor = f'native-ghost-male-{variant+1:02d}'
    s.update(race='ghost', face=donor, outfit=donor, arms=donor, legs=donor)
    return s

def prepare_hair(recipe,selected):
    """Keep the approved face; share the exact existing human hairstyle library."""
    number=selected['reference_parts']['hair']
    if not number and selected['hair']!='bald':return recipe
    import numpy as np
    from tools.creature_workshop.geometry import mesh
    from .constructor_neck import HEAD_DROP
    def scalp(c):
        p=c['part'].lower()
        return any(w in p for w in ('hair','braid','mane','topknot','quiff','scalp')) and not any(w in p for w in ('beard','mustache','moustache','brow'))
    recipe['commands']=[c for c in recipe['commands'] if not scalp(c)]
    if number:
        # The ghost faces are already at their short-neck height. Put the whole
        # head back into the common atlas frame for fitting, then the standard
        # final neck pass lowers every feature and the new hair together once.
        for c in recipe['commands']:
            if not c.get('short_neck_revision'):continue
            v,f=mesh(c);v=v.copy();v[:,1]+=HEAD_DROP
            c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist())
            c.pop('short_neck_revision',None)
    return recipe

def apply_spirit(recipe, selected, slot):
    """Bake a continuous two-piece spirit silhouette, keeping the SDK contract."""
    if selected['race']!='ghost' or selected['form']!='ghost_spirit' or not slot.endswith('_leg'):
        return recipe
    import math
    import numpy as np
    from tools.creature_workshop.family_faces import orient_faces
    from .constructor_knees import BIND_PROFILE, skeleton_snapshot
    sign=-1 if slot=='left_leg' else 1
    # Both halves share exactly the same two boundary curves and terminal point.
    # These are authored sections of the whole spirit, not stretched leg meshes.
    stations=[(.10,.055,-.39,.025,.022),(.28,.030,-.24,.095,.065),
              (.50,-.015,-.10,.165,.118),(.74,0,-.025,.224,.15),
              (1.02,0,.015,.265,.17)]
    sides=9;vertices=[[.06,0,-.44]];faces=[]
    for y,x,z,rx,rz in stations:
        for angle in np.linspace(-math.pi/2,math.pi/2,sides):
            vertices.append([x+sign*rx*math.cos(angle),y,z+rz*math.sin(angle)])
    for j in range(sides-1):faces.append([0,1+j,2+j])
    faces.append([0,sides,1])
    for ring in range(len(stations)-1):
        a=1+ring*sides;b=a+sides
        for j in range(sides-1):faces.extend([[a+j,b+j,a+j+1],[a+j+1,b+j,b+j+1]])
        # Closed internal seam; both sides use identical diagonal subdivision.
        faces.extend([[a,a+sides-1,b+sides-1],[a,b+sides-1,b]])
    a=1+(len(stations)-1)*sides
    for j in range(1,sides-1):faces.append([a,a+j,a+j+1])
    v=np.asarray(vertices);f=orient_faces(v,np.asarray(faces))
    recipe['commands']=[{'id':'ghost-spirit-'+slot,'op':'indexed_mesh',
        'part':'ghost_spirit_shroud','slot':slot,'stage':1,'material':'cloth',
        'vertices':v.tolist(),'faces':f.tolist(),'native_anatomy':'ghost',
        'purpose':SPIRIT_DESCRIPTION,'spirit_form_revision':2,
        'knee_bind_revision':{'profile':BIND_PROFILE,'skeleton_sha256':skeleton_snapshot()[1],
                              'method':'new spirit silhouette; SDK skeleton retained'},
        'thigh_stance_revision':{'schema_version':2,'authored_shared_spirit_seam':True}}]
    recipe['spirit_form']={'schema_version':1,'revision':2,'id':'ghost_spirit','description_ru':SPIRIT_DESCRIPTION,
                           'shared_tip_metres':[.06,0,-.44],'stations':stations,'forward_axis':'+Z'}
    return recipe

def refine_arms(recipe, selected, slot):
    if selected['race']!='ghost' or not slot.endswith('_arm'):return recipe
    import copy
    import hashlib
    import json
    from .constructor_knees import BIND_PROFILE, skeleton_snapshot
    variant=int(selected['arms'].rsplit('-',1)[1])-1
    female=variant in (1,4,7)
    gender='female' if female else 'male'
    path=ARM_DONORS/(gender+'-'+slot+'.recipe.json')
    blob=path.read_bytes()
    expected=json.loads((ARM_DONORS/'integrity.json').read_text())['files'][path.name]
    if hashlib.sha256(blob).hexdigest()!=expected:raise ValueError('Изменился immutable-источник человеческих рук; нужна новая ревизия')
    donor=json.loads(blob)
    # Copy the finished approved human mesh, including its actual shoulder cap.
    # No section generation, reshaping or scaling occurs here.
    commands=copy.deepcopy(donor['commands'])
    removed={'ghost_sleeve','ghost_hand','ghost_finger','ghost_thumb'}
    recipe['commands']=[c for c in recipe['commands'] if c['part'] not in removed]
    for j,c in enumerate(commands):
        primitive=c.get('authored_primitive',c)
        c['limb_proportions']=copy.deepcopy(primitive['limb_proportions'])
        if primitive.get('rounded_root'):c['rounded_root']=copy.deepcopy(primitive['rounded_root'])
        c['part']='palm' if c['limb_proportions']['region']=='hand' else 'fitted_sleeve'
        c['material']='metal' if c['part']=='palm' and variant==3 else 'skin' if c['part']=='palm' else 'cloth'
        c.update(id=f'ghost-arm-v2-{slot}-{j}',native_anatomy='ghost',
            human_arm_source={'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(blob).hexdigest(),
                              'method':'unmodified finished human mesh; material substitution only'},
            knee_bind_revision={'profile':BIND_PROFILE,'skeleton_sha256':skeleton_snapshot()[1],
                                'method':'approved human anatomical arm and hand; SDK bind unchanged'})
    recipe['commands'].extend(commands)
    recipe['ghost_arm_revision']={'schema_version':1,'revision':2,
        'method':'direct unchanged geometry copy from finished approved human arms; existing shoulder cap and connected hand',
        'human_donor':str(path.relative_to(ROOT)),'human_donor_sha256':hashlib.sha256(blob).hexdigest(),
        'variant':variant,'preserved_costume_details':True}
    return recipe
