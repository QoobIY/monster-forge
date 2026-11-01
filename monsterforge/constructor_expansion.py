"""Arena-approved anatomy expansion; sources remain experimental and modular."""
from .paths import ROOT
SOURCE=ROOT/'media/constructor/species_extra/v3'
HUMAN=('head','torso','left_arm','right_arm','left_leg','right_leg')
QUAD=('head','torso','front_left_leg','front_right_leg','hind_left_leg','hind_right_leg','tail')
CONTRACTS={
 'naga_authoring_v1':('head','torso','left_arm','right_arm','tail'),
 'centaur_authoring_v1':('head','torso','left_arm','right_arm',*QUAD[2:]),
 'crustacean_authoring_v1':('head','torso','left_claw','right_claw',*[f'{s}_leg_{i}' for s in ('left','right') for i in range(1,5)]),
 'insect_authoring_v1':('head','torso','abdomen',*[f'{s}_leg_{i}' for s in ('left','right') for i in range(1,4)]),
}
SPECIES={'naga':('Наги','naga_authoring_v1','naga'),'centaur':('Кентавры','centaur_authoring_v1','centaur'),'beast-elephant':('Слоны','quadruped_authoring_v1','elephant'),'crab':('Крабы','crustacean_authoring_v1','crab'),'beetle':('Жуки','insect_authoring_v1','beetle'),'scorpion':('Скорпионы','scorpion_authoring_v1','scorpion')}
OWNED_SPECS={'naga':{'label':'Наги','neutral':False,'description':'Человеческий верх, рептильные черты, змеевидный хвост вместо ног.'},'tree':{'label':'Тренты','neutral':True,'description':'Тренты: цельный древесный ствол, разветвлённые сучья вместо рук и кистей, опорные корни вместо ног и стоп; лицо вырезано в верхней части ствола.'}}
NAMES={'naga':['Морской страж','Коралловый воин','Приливный маг','Глубинный охотник','Змеиный жрец'],'centaur':['Степной страж','Лесной хранитель','Тяжёлый воитель'],'elephant':['Боевой слон','Африканский великан','Древний бивненосец'],'crab':['Королевский краб','Рифовый краб','Шипастый краб'],'beetle':['Жук-олень','Жук-носорог','Панцирный мститель'],'scorpion':['Пустынный скорпион','Императорский скорпион','Костяной скорпион'],'tree':['Дубовый хранитель','Ива вод','Хвойный страж','Древний сухостой','Цветущий древ']}
DESIGNS=[]
for race,(label,contract,kind) in SPECIES.items():
 for gender in (('male','female') if race=='naga' else ('male',)):
  for i,name in enumerate(NAMES[kind]):
   DESIGNS.append(dict(id=f'expansion-{kind}-{gender}-{i+1:02d}',race=race,gender=gender,variant=i,label=name+(' · женщина' if gender=='female' else ''),contract=contract,anatomy=kind,hair='cropped',own_body=race=='naga',description_ru=name+'. Собственная модульная анатомия, фиксированные места соединения.'))
HUMANOIDS=[dict(id=f'expansion-tree-male-{i+1:02d}',race='tree',gender='male',variant=i,label=name,contract='humanoid_v1',anatomy='tree',hair='cropped',own_body=True,description_ru=name+'. Ствол, корневые ноги, ветви-руки и индивидуальная крона.') for i,name in enumerate(NAMES['tree'])]
HUMANOIDS += [dict(id='expansion-water-golem-male-01',race='golem',gender='male',variant=5,label='Водяной голем',contract='humanoid_v1',anatomy='water',hair='cropped',own_body=True,description_ru='Водяной голем: текучие объёмы, завитки волн, пенные гребни, водопады вместо каменных плит.')]
HUMANOIDS += [dict(id=f'expansion-ape-{gender}-{i+1:02d}',race='beorn',gender=gender,variant=4+i,label=('Обезьяноподобный исполин','Снежный человек')[i]+(' · женщина' if gender=='female' else ''),contract='humanoid_v1',anatomy='ape',hair='cropped',own_body=True,description_ru='Человекозверь с обезьяноподобным лицом, выступающим надбровьем, широкой носовой площадкой, массивной челюстью и направленным мехом.') for gender in ('male','female') for i in range(2)]
FLYERS=[dict(id=f'expansion-dragon-{n}-head',race='sky-dragon',gender='male',variant=3+n-2,label=('Двуглавый дракон','Трёхглавый дракон')[n-2],contract='dragon_flight_authoring_v1',anatomy='dragon',head_count=n,hair='cropped',description_ru=f'{n} головы на расходящихся отдельных шеях, раскрытые перепончатые крылья, четыре поджатые лапы.') for n in (2,3)]
FLYERS += [dict(id='expansion-hippogriff-male-01',race='sky-dragon',gender='male',variant=5,label='Гипогриф',contract='dragon_flight_authoring_v1',anatomy='hippogriff',hair='cropped',description_ru='Гипогриф: орлиная голова и передние когтистые лапы, конский задний корпус с копытами, перьевые крылья и хвост.')]
FOLLOWUP_SOURCE=ROOT/'media/constructor/species_extra/v4'
FOLLOWUP=[dict(id='expansion-nerubian-male-01',race='beetle',gender='male',variant=3,label='Нерубианский страж',contract='insect_authoring_v1',anatomy='nerubian',hair='cropped',own_body=False,description_ru='Шестиногий жук с вытянутой щитовой головой, боковыми жвалами, парными изогнутыми рогами и раздельными надкрыльями. Съёмный шлем, грудная и брюшная броня выбираются отдельно.')]
FOLLOWUP += [dict(id=f'expansion-owl-{gender}-01',race='beorn',gender=gender,variant=6,label='Совомедведь'+(' · женщина' if gender=='female' else ''),contract='humanoid_v1',anatomy='owl',hair='cropped',own_body=True,description_ru='Совомедведь: меховой гуманоидный корпус, широкая совиная голова, два вогнутых лицевых диска, крупные янтарные глаза, крючковатый клюв, перьевые брови и направленные щёчные перья.') for gender in ('male','female')]
DESIGNS += [d for d in FOLLOWUP if d['race']=='beetle']
HUMANOIDS += [d for d in FOLLOWUP if d['race']=='beorn']
ARENA_ARTHROPOD_SOURCE=ROOT/'media/constructor/species_extra/v5'
ARENA_ARTHROPODS=[]
for kind,names in {'crab':('Краб Arena','Тяжёлый панцирный краб','Шипастый краб Arena'),'scorpion':('Скорпион Arena','Тяжёлый императорский скорпион','Скорпион с отведённым жалом')}.items():
 for i,name in enumerate(names):
  ARENA_ARTHROPODS.append(dict(id=f'expansion-arena-{kind}-{i+1:02d}',race=kind,gender='male',variant=i,label=name,contract=SPECIES[kind][1],anatomy=kind,hair='cropped',own_body=False,source_arena='king-crab' if kind=='crab' else 'scorpion-king',description_ru=name+'. Геометрия исходной модели Arena: панцирь, раскрытые клешни, восемь суставчатых ног, собственная голова'+(', сегментное брюшко и хвост с жалом.' if kind=='scorpion' else ' с глазными стеблями.')))
for d in DESIGNS:
 if d['race'] in {'crab','scorpion'}:d['public']=False
DESIGNS += ARENA_ARTHROPODS
TREANT_SOURCE=ROOT/'media/constructor/species_extra/v6'
TREANTS=[dict(id=f'expansion-treant-{i+1:02d}',race='tree',gender='male',variant=i,label=name,contract='humanoid_v1',anatomy='treant',hair='cropped',own_body=True,description_ru=name+'. Тело — цельный асимметричный ствол без талии, руки — разветвлённые сучья без ладоней, ноги — расходящиеся наземные корни без стоп; древесное лицо продолжает ствол.') for i,name in enumerate(('Дубовый трент','Ивовый трент','Хвойный трент','Трент сухостоя','Цветущий трент'))]
for d in HUMANOIDS:
 if d['race']=='tree':d['public']=False
HUMANOIDS += TREANTS
DRAFT_TREANTS=TREANTS
for d in DRAFT_TREANTS:d['public']=False
ROOTED_TREANT_SOURCE=ROOT/'media/constructor/species_extra/v7'
TREANTS=[{**d,'id':d['id'].replace('treant-','treant-rooted-'),'public':True,'description_ru':d['description_ru']+' Удлинённый ствол, короткие опорные корни у земли.'} for d in DRAFT_TREANTS]
HUMANOIDS += TREANTS

def source_folder(identifier):
 if identifier in {d['id'] for d in TREANTS}:return ROOTED_TREANT_SOURCE/identifier
 if identifier in {d['id'] for d in DRAFT_TREANTS}:return TREANT_SOURCE/identifier
 if identifier in {d['id'] for d in ARENA_ARTHROPODS}:return ARENA_ARTHROPOD_SOURCE/identifier
 return (FOLLOWUP_SOURCE if identifier in {d['id'] for d in FOLLOWUP} else SOURCE)/identifier
DESIGNS=[d for d in DESIGNS if d.get('public',True)]
HUMANOIDS=[d for d in HUMANOIDS if d.get('public',True)]
ALL=[*DESIGNS,*HUMANOIDS,*FLYERS];IDS={d['id'] for d in ALL}
from .constructor_species_variety import LABELS as ANATOMY_LABELS
for d in DESIGNS:
 if d['race'] in ANATOMY_LABELS:
  d['label']=ANATOMY_LABELS[d['race']][d['variant']]
  d['description_ru']=d['label']+'. Собственная анатомическая ревизия; исходная геометрия сохранена.'
