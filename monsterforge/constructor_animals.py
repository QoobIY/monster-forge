"""Independent Arena-inspired quadrupeds, frozen source parts and fixed joins."""
from .paths import ROOT
SOURCE=ROOT/'media/constructor/animals/v15'
NAMES={
 'sheep':('Горный баран','Шерстистая овца','Степной баран'),
 'wolf':('Лесной волк','Северный волк','Матёрый волк'),
 'bear':('Бурый медведь','Белый медведь','Чёрный медведь'),
 'boar':('Лесной кабан','Секач','Щетинистый кабан'),
 'dog':('Овчарка','Мастиф','Гончая'),
 'tiger':('Бенгальский тигр','Белый тигр','Саблезубый тигр'),
 'horse':('Боевой конь','Тяжеловоз','Степная лошадь')}
LABELS={'sheep':'Овцы','wolf':'Волки','bear':'Медведи','boar':'Кабаны','dog':'Собаки','tiger':'Тигры','horse':'Лошади'}
REFERENCES={'sheep':'flying-sheep','wolf':'summoned-beast','bear':'furbolg-pup','boar':'razormane-pup','dog':'summoned-beast','tiger':'beast-archer','horse':'fearsome-crusader'}
SPECIES={f'beast-{kind}':(LABELS[kind],'quadruped_authoring_v1',kind) for kind in NAMES}
DESIGNS=[{'id':f'library-animal-{kind}-{i+1:02d}','race':f'beast-{kind}','gender':'male','variant':i,'label':label,'contract':'quadruped_authoring_v1','anatomy':kind,'hair':'cropped','reference_id':REFERENCES[kind], 'description_ru':label+'. Собственная четвероногая анатомия: голова, корпус, четыре отдельные ноги и хвост. Суставы передних и задних ног различаются; части совместимы внутри вида.'} for kind,names in NAMES.items() for i,label in enumerate(names)]
IDS={d['id'] for d in DESIGNS}
def options(race,gender='male'):return [d for d in DESIGNS if d['race']==race and gender=='male']
