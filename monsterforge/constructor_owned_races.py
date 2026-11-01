"""Race-owned modular anatomy. Human garment/body donors are incompatible."""
from .paths import ROOT
RACES={
 'ghost':{'label':'Призраки','neutral':True,'description':'Бестелесные гуманоидные духи с индивидуальными погребальными облачениями; голова, торс, руки и ноги отдельные.'},
 'golem':{'label':'Големы','neutral':True,'description':'Каменные сегменты, массивные сочленения, отдельные кисти из камня и широкие стопы.'},
 'panda':{'label':'Панды','neutral':False,'description':'Медвежий корпус с округлым животом, чёрные лапы, белый мех, маска вокруг глаз и круглые уши.'},
 'beorn':{'label':'Беорны','neutral':False,'description':'Мощный медвежий торс с горбом, тяжёлая шея, выступающая морда, длинные когти и широкие лапы.'},
 'kobold':{'label':'Кобольды','neutral':False,'description':'Лёгкий рептильный торс, длинная морда, гребень, трёхпалые кисти и стопы, хвост как отдельная деталь спины.'},
 'quillboar':{'label':'Иглогривы','neutral':False,'description':'Коренастое кабанье тело, широкая морда с пятачком и клыками, парнокопытные стопы и игольчатая грива вдоль спины.'},
}
SOURCE=ROOT/'media/constructor/owned_races/v9'
NAMES={'golem':['Лавовый голем','Ледяной голем','Голем пустоши','Голем ветров','Древний голем'],
 'panda':['Хранитель бамбука','Горный монах','Путник','Старейшина'],
 'beorn':['Лесной страж','Северный охотник','Бурый воитель','Медовый хранитель'],
 'kobold':['Пещерный разведчик','Красный шаман','Болотный следопыт','Песчаный страж'],
 'quillboar':['Степной иглогрив','Каменный дозорный','Рыжий берсерк','Лесной охотник']}
from .constructor_ghosts import NAMES as GHOST_NAMES, FACES as GHOST_FACES, COSTUMES as GHOST_COSTUMES
NAMES['ghost']=GHOST_NAMES
DESIGNS=[{'id':f'native-{race}-{gender}-{i+1:02d}','race':race,'gender':gender,'variant':i,'label':NAMES[race][i]+(' · женщина' if gender=='female' else ''),'hair':'cropped','own_body':True,'description_ru':spec['description']+' '+NAMES[race][i]+'.'}
 for race,spec in RACES.items() for gender in (['male'] if spec['neutral'] else ['male','female']) for i in range(len(NAMES[race]))]
IDS={d['id'] for d in DESIGNS}
for d in DESIGNS:
 if d['race']=='ghost':d['description_ru']=GHOST_FACES[d['variant']]+' '+GHOST_COSTUMES[d['variant']]
def options(race,gender):return [d for d in DESIGNS if d['race']==race and d['gender']==gender and d.get('public',True)]

from .constructor_expansion import OWNED_SPECS, HUMANOIDS, DESIGNS as EXP_DESIGNS
RACES.update(OWNED_SPECS)
RACES['beorn']['label']='Человекозвери'
DESIGNS.extend([*HUMANOIDS,*[d for d in EXP_DESIGNS if d['race']=='naga']])
IDS.update(d['id'] for d in DESIGNS)

from .constructor_randomiums import RACES as RANDOMIUM_RACES, DESIGNS as RANDOMIUM_DESIGNS
RACES.update(RANDOMIUM_RACES)
DESIGNS.extend(RANDOMIUM_DESIGNS)
IDS.update(d['id'] for d in RANDOMIUM_DESIGNS)
