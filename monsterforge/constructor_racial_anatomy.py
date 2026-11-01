"""Explicit racial volumes, baked into derived humanoid_v1 parts; sources stay frozen."""
import numpy as np
from tools.creature_workshop.geometry import mesh
from .constructor_portraits import builder, freeze

VARIANTS={}
SKIN_COLORS={'minotaur':'827054','orc':'66815b','goblin':'809450','skeleton':'cfc6ad'}
for race,names in {
 'skeleton':['Человеческий череп','Вытянутый череп','Тяжёлый череп','Орочий скелет','Бычий скелет','Волчий скелет'],
 'minotaur':['Степной','Горный','Лесной','Древний','Речной','Северный','Саванновый','Каньонный','Лунный','Венценосный'],
 'goblin':['Ловкач','Разведчик','Алхимик','Задира','Старейшина','Механик','Болотный','Купец','Ночной','Вождь'],
 'orc':['Воин','Следопыт','Шаман','Ветеран','Вождь','Молодой','Старейшина','Охотник','Кузнец','Провидец'],
}.items():
 for gender in (['male'] if race=='skeleton' else ['male','female']):
  for i,name in enumerate(names):
   key=f'anatomy-{race}-{gender}-{i+1:02d}'
   VARIANTS[key]={'id':key,'race':race,'gender':gender,'index':i,'label':name+(' · женщина' if gender=='female' else ''),'source':'library-human-01' if race=='goblin' else f'library-{race}-01',
     'description_ru':name+('. Гоблин: крупные длинные уши с углублённой чашей, выраженные скулы, узкая челюсть, длинный выступающий нос, маленькие клыки; человеческое тело и экипировка с собственными перчатками и обувью. ' if race=='goblin' else '. ')+ 'Самостоятельная расовая форма черепа, челюсти и пропорций тела; отдельные части на humanoid_v1.'}

def choices(race,gender):return [v for v in VARIANTS.values() if v['race']==race and v['gender']==gender]

def apply(recipe,settings,slot):
 spec=VARIANTS.get(settings['face'])
 if not spec:return
 race=spec['race'];i=spec['index'];female=spec['gender']=='female'
 recipe['racial_anatomy_revision']={'schema_version':1,**spec}
 if race=='goblin' and slot!='head':return
 if slot!='head':
  # Keep the SDK joint locations, floor and length: vary mass about segment axes.
  from .constructor_knees import world_bind
  bind=world_bind();bulk=[1.13,1.32,1.06,1.22][i%4] if race=='minotaur' else [1.13,1.02,1.07,1.24][i%4] if race=='orc' else [1,.90,1.17,1.22,1.30,.95][i]
  if female:bulk=1+(bulk-1)*.70
  for c in recipe['commands']:
   v,f=mesh(c);v=v.copy()
   if slot=='torso':
    fac=np.interp(v[:,1],[1.0,1.24,1.65,1.92],[1,1+(bulk-1)*.45,bulk,1]);v[:,0]*=fac;v[:,2]*=1+(fac-1)*.65
   elif slot.endswith(('_arm','_leg')):
    side=slot.split('_')[0];keys=('shoulder','elbow','hand') if slot.endswith('_arm') else ('hip','knee','foot')
    pts=[np.asarray(bind[side+'_'+k]) for k in keys];centres=[]
    for a,b in zip(pts,pts[1:]):
     d=b-a;t=np.clip((v-a)@d/(d@d),0,1);centres.append(a+t[:,None]*d)
    cs=np.stack(centres);idx=np.linalg.norm(cs-v,axis=2).argmin(0);centre=cs[idx,np.arange(len(v))];v=centre+(v-centre)*bulk
    if slot.endswith('_leg'):v[:,1]=mesh(c)[0][:,1]
   c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist());c.pop('vertex_normals',None)
  return
 # Replace head anatomy, retaining independently selected hairstyles/headwear.
 kept=[c for c in recipe['commands'] if (race=='goblin' and c['part'].startswith(('ornament_','decor_'))) or any(w in c['part'] for w in ('hair','beard','mustache','moustache','headwear','helmet','hood'))]
 from .constructor_racial_heads import flesh, skull
 b=builder(recipe)
 b.palette['skin']=(settings['colors']['skin'] or '#'+SKIN_COLORS[race]).lstrip('#')
 if race=='minotaur':
  skin=np.asarray(list(bytes.fromhex(b.palette['skin'])));b.palette['lip']=''.join(f'{x:02x}' for x in np.round(skin*.84).astype(int));b.palette['sclera']='d3c8a8'
 b.palette['shadow']='38382d';
 if race!='minotaur':b.palette['lip']='4e4b38'
 b.palette['iris']=(settings['colors']['eyes'] or '#c89c4e').lstrip('#')
 if race=='goblin':
  from .constructor_goblins import head
  b.palette.update(bone='d3c7a4',sclera='dfd6a6',pupil='20271c',shadow='30382a',lip='5a683e')
  p=head(b,spec['gender'],i)
 elif race=='skeleton':
  p=skull(b,i,horns)
 else:
  p=flesh(b,race,spec['gender'],i,horns)
 if race!='skeleton':
  # Keep selected locks, but adapt their roots to the authored cranial volume.
  for c in kept:
   if 'hair' in c['part']:
    v,f=mesh(c);v=v.copy();v[:,0]*=p['crown']/.18;v[:,1]+=.028
    c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist());c.pop('vertex_normals',None)
 cmds,pal=freeze(b,'racial');recipe['palette'].update(pal)
 recipe['commands']=cmds+(kept if race!='skeleton' else [])
 recipe['racial_anatomy_revision'].update(geometry_revision=5,anatomical_landmarks=p,method='independent regional landmarks and authored bone structures')
 for j,c in enumerate(recipe['commands']):c['id']=f'racial-{slot}-{j}'

def horns(b,i,w,female):
 for sign in (-1,1):
  styles=[[(w*.8,2.48,-.07),(w+.10,2.50,-.09),(w+.19,2.59,-.06),(w+.15,2.70,.015)],[(w*.8,2.48,-.07),(w+.09,2.56,-.13),(w+.10,2.73,-.14),(w+.02,2.84,-.07)],[(w*.8,2.48,-.07),(w+.14,2.47,-.10),(w+.22,2.53,-.13),(w+.26,2.62,-.09)],[(w*.8,2.48,-.07),(w+.13,2.53,-.10),(w+.17,2.69,-.04),(w+.08,2.79,.06)]]
  styles.extend([
   [(w*.8,2.48,-.07),(w+.12,2.50,-.06),(w+.25,2.54,-.03),(w+.29,2.62,.02)],
   [(w*.8,2.48,-.07),(w+.07,2.55,-.10),(w+.08,2.65,-.07),(w+.04,2.72,.01)],
   [(w*.8,2.48,-.07),(w+.17,2.48,-.12),(w+.32,2.51,-.15),(w+.36,2.59,-.09)],
   [(w*.8,2.48,-.07),(w+.09,2.54,-.14),(w+.15,2.63,-.17),(w+.24,2.67,-.10)],
   [(w*.8,2.48,-.07),(w+.09,2.52,-.12),(w+.11,2.63,-.12),(w+.05,2.69,-.04)],
   [(w*.8,2.48,-.07),(w+.11,2.55,-.08),(w+.09,2.72,-.06),(w-.01,2.82,.01)]])
  path=styles[i];path=[[sign*x,2.48+(y-2.48)*(.82 if female else 1),z] for x,y,z in path]
  b.tube('racial_bull_horn','bone',path,[.054,.042,.022,.002],sides=8)
