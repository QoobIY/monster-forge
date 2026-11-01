"""Continuous matte pelts: shared contour tips instead of overlaid locks/stripes."""
import numpy as np
from tools.creature_workshop.geometry import mesh
from tools.creature_workshop.family_faces import orient_faces
from monsterforge.constructor_face_fit import split_edges
from tools.creature_workshop.owned_surface_revision import normals
RACES={'beorn','panda','quillboar'}
PARTS={'racial_torso','bear_withers','animal_cranium','racial_upper_arm','racial_forearm','racial_thigh','racial_shin','panda_dark_shoulder_band','boar_bristle_mantle'}
DESCRIPTIONS={
 'beorn':'Густая медвежья шкура: широкие пряди на загривке, щеках и плечах, более короткая шерсть рук и голеней; выступы являются общими вершинами замкнутого меша и направлены вниз/назад. Без накладных бугорков и полосатой текстуры.',
 'panda':'Короткая плотная шкура панды с сохранёнными белым корпусом, чёрными плечами и лапами, маской глаз. Мягкий зубчатый контур щёк и плеч, компактные пряди конечностей из общей сетки; без накладных прядей и тёмной штриховки.',
 'quillboar':'Жёсткая короткая щетина: направленные назад выступы щёк, вниз вдоль корпуса и конечностей. Щетина формирует общий меш шкуры; отдельные длинные спинные и головные иглы сохранены. Без приклеенных чешуек и полосатой текстуры.'}

def coarse_skin(c):
 v,f=mesh(c)
 if c.get('pelt_surface_revision')==2:
  # The frozen v9 surface was refined once with split_edges. Recover its
  # original triangle corners; the three edge midpoints occur three times.
  if len(f)%4:raise ValueError('Unknown frozen pelt topology')
  base=[]
  for block in f.reshape(-1,4,3):
   indices,counts=np.unique(block,return_counts=True);corners=indices[counts==1]
   if len(corners)!=3:raise ValueError('Cannot recover original pelt triangle')
   base.append(corners)
  f=orient_faces(v,np.array(base));used=np.unique(f);remap=np.full(len(v),-1);remap[used]=np.arange(len(used));v=v[used].copy();f=remap[f]
 return v,f

def coat(c,race,slot):
 base,faces=coarse_skin(c);v,f=split_edges(base,faces);n=normals(v,f)
 lo=base.min(0);hi=base.max(0);centre=(lo+hi)*.5;span=hi-lo
 growth=np.array([0.,-1.,-.13])
 if slot=='head':growth=np.array([0.,-.48,-.88])
 elif slot.endswith('_arm'):growth=np.array([-.44 if slot.startswith('left') else .44,-.90,.035])
 elif slot.endswith('_leg'):growth=np.array([0.,-1.,.06])
 growth/=np.linalg.norm(growth)
 # Shared edge midpoints are shifted along the coat flow. Roots and original
 # anatomical vertices stay fixed, preserving the face, limb joins and floor.
 edges={}
 for face in faces:
  for a,b in zip(face,np.roll(face,-1)):
   key=tuple(sorted((int(a),int(b))));edges.setdefault(key,len(base)+len(edges))
 tips=[];amplitude={'beorn':.030,'panda':.023,'quillboar':.017}[race]
 for (a,b),index in edges.items():
  p=v[index].copy();normal=n[index];direction=growth-normal*(normal@growth)
  length=np.linalg.norm(direction)
  if length<.3:continue
  direction/=length;edge=base[b]-base[a];edge_length=np.linalg.norm(edge)
  if abs(edge@growth)>edge_length*.68:continue
  if p[1]<lo[1]+.035 or p[1]>hi[1]-.035:continue
  # Keep facial landmarks and their carrier untouched. Fur only reaches the
  # lateral cheeks and nape, never the eyes, nose or mouth surfaces.
  if slot=='head' and (p[2]>.035 or abs(p[0]-centre[0])<span[0]*.28):continue
  if (a*7+b*11)%5==0:continue
  strength=1.
  if c['part']=='racial_torso':
   strength=.65 if p[1]<1.58 else 1.15
   if normal[2]>.55 and p[1]<1.55:strength*=.5
  if slot.endswith(('_arm','_leg')):strength*=.70
  amount=min(amplitude*strength,edge_length*.18)
  if amount<.002:continue
  delta=normal*amount+direction*amount*1.35
  v[index]+=delta
  tips.append({'vertex':index,'base':p.tolist(),'growth_direction':direction.tolist(),'outward_direction':normal.tolist(),'displacement':delta.tolist()})
 c.update(op='indexed_mesh',vertices=v.tolist(),faces=orient_faces(v,f).tolist(),integrated_fur={'schema_version':1,'race':race,'method':'shared edge-tip vertices swept along regional growth; fixed anatomical roots','original_vertices':len(base),'tips':tips},ai_description_ru=DESCRIPTIONS[race])
 for key in ('fur_uv','fur_texture','vertex_color_factors','vertex_normals','face_materials','pelt_surface_revision'):c.pop(key,None)
 c['pelt_surface_revision']=3


def apply(recipe,settings,slot):
 race=settings['race']
 if race not in RACES:return
 recipe['commands']=[c for c in recipe['commands'] if c['part']!='surface_fur_lock']
 for c in recipe['commands']:
  if c['part'] in PARTS:coat(c,race,slot)
 recipe['pelt_revision']={'schema_version':1,'id':'owned-pelt-v3','description_ru':DESCRIPTIONS[race],'method':'regional integrated contour fur; removed detached locks and striped albedo'}
