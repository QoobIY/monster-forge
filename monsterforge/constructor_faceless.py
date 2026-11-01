"""Face-surface-rooted tentacles and an explicit combined mask/horn accessory."""
import copy,math
import numpy as np
from tools.creature_workshop.geometry import mesh
from .constructor_face_fit import surfaces,front_depth
from .constructor_decor import sculpt
from .constructor_portraits import freeze
LABELS={'faceless_tendrils':'Безликий · четыре щупальца','faceless_crown':'Безликий · шесть щупалец','faceless_abyss':'Безликий · глубоководный','horned_mask':'Рогатая полумаска'}
DESCRIPTIONS={
 'faceless_tendrils':'Четыре мясистых щупальца укоренены в щеках и верхней губе, опускаются ниже подбородка и загибаются наружу; у каждого плавно сужающийся изгиб и кончик.',
 'faceless_crown':'Шесть щупалец расходятся от нижней части лица, длинные боковые отростки загнуты внутрь; отдельные лицевые гребни вокруг глаз.',
 'faceless_abyss':'Восемь разновеликих щупалец: длинные челюстные и короткие височные; парные гребни, отдельные светлые поперечные присоски на нижних сторонах.',
 'horned_mask':'Подогнанная полумаска с прорезями для глаз, металлическими краями и парными длинными демоническими рогами, растущими назад от висков.'}

def apply(recipe,settings):
 kind=settings['decor']['headwear']
 if kind not in LABELS:return
 face=surfaces(recipe)
 if not face:return
 v=np.concatenate([mesh(c)[0] for c in face]);lo,hi=v.min(0),v.max(0)
 if kind=='horned_mask':
  from .constructor_head_accessories import apply as mask
  local=copy.deepcopy(settings);local['reference_parts']['headwear']=10;mask(recipe,local)
  from .constructor_horns import author
  b=sculpt(settings);b.slot='head';b.stage=4;author(b,'demon_swept_horns',face,v,settings)
 else:
  recipe['commands']=[c for c in recipe['commands'] if not any(w in c['part'] for w in ('mouth','lip','nose','nostril','philtrum','tooth','teeth','mustache','beard'))]
  b=sculpt(settings);b.slot='head';b.stage=4
  b.palette['skin']=(settings['colors']['skin'] or '#718092').lstrip('#')
  b.palette['tendril_light']='9ba7aa';b.palette['sucker']='647381'
  eyes=[mesh(c)[0].mean(0) for c in recipe['commands'] if 'iris' in c['part']]
  eye=float(np.mean([p[1] for p in eyes])) if eyes else lo[1]+.59*(hi[1]-lo[1])
  count={'faceless_tendrils':4,'faceless_crown':6,'faceless_abyss':8}[kind];width=float(np.max(np.abs(v[:,0])))
  for i in range(count):
   x=(i-(count-1)/2)*width*1.30/(count-1);y=eye-.125+.04*abs(x)/width
   z=float(front_depth(face,[[x,y]])[0]);root=[x,y,z-.012];sign=-1 if x<0 else 1
   drop=.23+.15*(1-abs(x)/width)+(i%2)*.055;out=.025+.075*abs(x)/width
   path=[root,[x,y-.045,z+.030],[x+sign*out*.55,y-drop*.45,z+.067],[x+sign*out,y-drop*.86,z+.084],[x+sign*out*.8,y-drop,z+.14],[x+sign*out*.20,y-drop+.025,z+.183]]
   radii=[.034 if count<8 else .027,.043 if count<8 else .034,.032,.019,.011,.0025]
   b.tube('faceless_rooted_tendril','skin',path,radii,sides=8)
   if kind=='faceless_abyss':
    for j in range(1,4):
     p=np.asarray(path[j]);p[2]+=radii[j]*.90;b.oval('faceless_sucker','sucker',p.tolist(),[radii[j]*.58,radii[j]*.26,.005],sides=7)
  if kind!='faceless_tendrils':
   for sign in (-1,1):
    x=sign*width*.66;y=eye+.055;z=float(front_depth(face,[[x,y]])[0]);b.tube('faceless_orbital_crest','skin',[[x*.60,y+.04,z-.003],[x,y+.047,z+.02],[x*1.14,y-.015,z+.008]],[.018,.026,.005],sides=7)
 commands,palette=freeze(b,'faceless');recipe['commands'].extend(commands);recipe['palette'].update(palette)
 recipe['faceless_accessory']={'schema_version':1,'id':kind,'description_ru':DESCRIPTIONS[kind],'placement':'root intersections on selected face triangles'}
