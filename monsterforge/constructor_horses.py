"""Horse-specific mane and regional body choices, on fixed quadruped joins."""
import copy,math
import numpy as np
from tools.creature_workshop.geometry import mesh
from tools.creature_workshop.original_constructor import OriginalSculpt,mesh_command
from tools.creature_workshop.family_faces import orient_faces

MANES={'mane_short':'Короткая стоячая','mane_long':'Длинная густая','mane_waves':'Волнистая','mane_braid':'Плетёная','mane_wild':'Дикая грива'}
FORMS={'horse_athletic':'Боевой жеребец','horse_heavy':'Массивный конь','horse_draft':'Богатырский тяжеловоз'}

def crest(recipe,y,front=False):
 faces=[]
 for c in recipe['commands']:
  if c['part'] in {'horse_neck_withers','horse_cranial_cheek_muzzle'}:
   v,f=mesh(c);faces.extend(v[f])
 hits=[]
 for tri in faces:
  xy=tri[:,:2];m=np.column_stack((xy[1]-xy[0],xy[2]-xy[0]))
  if abs(np.linalg.det(m))<1e-10:continue
  uv=np.linalg.solve(m,np.array([0.,y])-xy[0])
  if min(uv)>=-1e-7 and sum(uv)<=1+1e-7:hits.append(float(tri[0,2]+uv@(tri[1:,2]-tri[0,2])))
 if not hits:raise ValueError('Mane crest has no neck/head surface')
 return max(hits) if front else min(hits)

def side_x(recipe,y,z):
 hits=[]
 for c in recipe['commands']:
  if c['part'] not in {'horse_chest_waist_rump','horse_neck_withers','horse_cranial_cheek_muzzle'}:continue
  v,f=mesh(c)
  for tri in v[f]:
   yz=tri[:,1:];m=np.column_stack((yz[1]-yz[0],yz[2]-yz[0]))
   if abs(np.linalg.det(m))<1e-10:continue
   uv=np.linalg.solve(m,np.array([y,z])-yz[0])
   if min(uv)>=-1e-7 and sum(uv)<=1+1e-7:hits.append(float(tri[0,0]+uv@(tri[1:,0]-tri[0,0])))
 return min(hits) if hits else -.22

BARREL_EXTENSION=.24

def lengthen_barrel(recipe,slot):
 # Keep the shoulder and neck fixed. Relocate the croup as a rigid anatomical
 # mass, then author two extra barrel stations between it and the rib cage.
 for key,p in recipe['contract_anchors'].items():
  if key.startswith('hind_') or key=='tail':p[2]-=BARREL_EXTENSION
 for key,landmarks in recipe.get('joint_landmarks',{}).items():
  if key.startswith('hind_'):
   for p in landmarks.values():p[2]-=BARREL_EXTENSION
 if slot.startswith('hind_') or slot=='tail':
  for c in recipe['commands']:
   v,f=mesh(c);v=v.copy();v[:,2]-=BARREL_EXTENSION
   c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist())
  # Translation retains limb proportions, surface normals and the hoof plane.
 elif slot=='torso':
  for c in recipe['commands']:
   if c['part']!='horse_chest_waist_rump':continue
   v,_=mesh(c);rings=v[:-2].reshape(-1,12,3).copy()
   if len(rings)!=11:raise ValueError('Unsupported equine barrel source topology')
   rings[:4,:,2]-=BARREL_EXTENSION;rings[4,:,2]-=.14;rings[5,:,2]-=.045
   middle=(rings[3]+rings[4])*.5;middle[:,2]=-.50
   # The ventral rib plane is deeper here; the narrower waist rises toward it.
   middle[:,1]-=.012*(1-np.abs(middle[:,0])/.44)
   waist=(rings[4]+rings[5])*.5;waist[:,2]=-.155;waist[:,0]*=.985
   rings=np.concatenate([rings[:4],middle[None],rings[4:5],waist[None],rings[5:]])
   verts=rings.reshape(-1,3).tolist();faces=[];count=12
   for k in range(len(rings)-1):
    for j in range(count):
     a=k*count+j;b=k*count+(j+1)%count;d=a+count;e=b+count
     faces.extend([[a,b,d],[b,e,d]] if (k+j)%2 else [[a,b,e],[a,e,d]])
   for k in (0,len(rings)-1):
    centre=len(verts);verts.append(rings[k].mean(0).tolist())
    faces.extend([[centre,k*count+j,k*count+(j+1)%count] for j in range(count)])
   verts=np.asarray(verts);c.update(op='indexed_mesh',vertices=verts.tolist(),faces=orient_faces(verts,np.asarray(faces)).tolist())
   c['equine_landmarks'].update(croup=[0,float(rings[2,:,1].max()),float(rings[2,0,2])],saddle_hollow=[0,float(rings[7,:,1].max()),float(rings[7,0,2])],sections=[[float(r[0,2]),float(r[:,1].max()),float(r[:,1].min()),float(np.abs(r[:,0]).max())] for r in rings])
 recipe['horse_barrel_revision']={'schema_version':1,'id':'horse-barrel-v1','extension_metres':BARREL_EXTENSION,'method':'two authored rib/waist stations; rigid rear-quarter, hind-limb and tail relocation; head and limb lengths unchanged'}


def trim_chest(recipe):
 # Shorten the anterior barrel and low neck in the horse's anatomical +Z
 # direction. A positive depth derivative keeps the existing mesh ordered;
 # this reshapes the surface instead of flattening several rings onto a plane.
 for c in recipe['commands']:
  if c['part'] not in {'horse_chest_waist_rump','horse_neck_withers'}:continue
  v,f=mesh(c);v=v.copy();forward=np.maximum(v[:,2]-.43,0)
  factor=np.clip(.26+.48*(v[:,1]-1.3),.20,.65)
  blend=np.ones(len(v)) if c['part']=='horse_chest_waist_rump' else np.clip((1.90-v[:,1])/.30,0,1)
  v[:,2]-=forward*(1-factor)*blend
  c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist());c.pop('vertex_normals',None)
 recipe['horse_chest_revision']={'schema_version':1,'id':'horse-chest-v1','method':'shorter oblique breast and low neck; posterior barrel and fixed limb joins preserved'}


def muzzle_points(points):
 """Reshape the nasal bridge beyond the orbital plane, preserving the skull."""
 v=np.array(points,dtype=float,copy=True);depth=np.maximum(v[:,2]-.90,0)
 blend=np.clip(depth/.465,0,1)
 v[:,2]-=.20*depth
 v[:,1]+=.028*blend*blend
 v[:,0]*=1+.055*blend
 return v

def refine_muzzle(recipe):
 # Nostril openings and their rims move together as rigid assemblies so that
 # shortening the bridge cannot crush the opening or detach its dark inset.
 pivots={}
 for c in recipe['commands']:
  if c['part']=='horse_nostril_rim':
   centre=mesh(c)[0].mean(0);pivots[int(np.sign(centre[0]))]=centre
 for c in recipe['commands']:
  name=c['part']
  if name not in {'horse_cranial_cheek_muzzle','horse_upper_lip','horse_lower_lip','horse_nostril_rim','nostril','closed_mouth_line'}:continue
  v,f=mesh(c)
  if name in {'horse_nostril_rim','nostril'}:
   p=pivots[int(np.sign(v[:,0].mean()))];v=v+(muzzle_points(p[None])[0]-p)
  else:v=muzzle_points(v)
  c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist());c.pop('vertex_normals',None)
 recipe['horse_muzzle_revision']={'schema_version':1,'id':'horse-muzzle-v1','method':'shorter nasal bridge, fuller slightly lifted muzzle; fixed orbital plane, ears and posterior skull; paired rigid nostril relocation'}

def apply(recipe,settings,slot):
 if settings['race']!='beast-horse':return
 lengthen_barrel(recipe,slot)
 if slot=='torso':trim_chest(recipe)
 if slot=='head':refine_muzzle(recipe)
 form=settings['form'];strength={'regular':0,'horse_athletic':.09,'horse_heavy':.22,'horse_draft':.37}[form]
 if strength:
  anchor=np.asarray(recipe['contract_anchors'][slot])
  for c in recipe['commands']:
   v,f=mesh(c);v=v.copy()
   if slot=='torso':
    region=np.interp(v[:,2],[-.84,-.4,0,.4,.84],[.66,.85,.7,1.,.70]);v[:,0]*=1+strength*region
    centre=1.38;v[:,1]=centre+(v[:,1]-centre)*(1+strength*.46*region)
   elif slot.endswith('_leg'):
    bulk=1+strength*np.interp(v[:,1],[0,.16,.5,1.3],[.68,.68,.88,1.12]);v[:,0]=anchor[0]+(v[:,0]-anchor[0])*bulk
    # Preserve knee/hock centres and the shared ground exactly.
   elif slot=='head':v[:,0]*=1+strength*.10
   c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist());c.pop('vertex_normals',None)
  recipe['horse_silhouette']={'schema_version':1,'choice':form,'method':'regional chest/shoulder/barrel/limb masses; revised horse joins and fixed floor'}
 if slot not in {'head','torso'}:return
 choice=settings['hair']
 if choice=='original':choice=('mane_long','mane_braid','mane_waves')[recipe['animal_design']['variant']]
 if choice not in MANES and choice!='bald':choice='mane_long'
 recipe['commands']=[c for c in recipe['commands'] if c['part'] not in {'neck_mane_lock','forelock_mane'} and not c.get('horse_mane')]
 if choice=='bald':return
 d={**recipe['animal_design'],'palette':copy.deepcopy(recipe['palette'])};b=OriginalSculpt(d);b.slot=slot;b.stage=3
 surface=next(c for c in recipe['commands'] if c['part']==('horse_neck_withers' if slot=='torso' else 'horse_cranial_cheek_muzzle'))
 top=float(mesh(surface)[0][:,1].max())-.02
 ys=np.linspace(1.52,min(2.02,top),17) if slot=='torso' else np.linspace(2.03,min(2.25,top),8)
 for j,y in enumerate(ys):
  z=crest(recipe,float(y));root=[0,float(y),z+.007]
  if choice=='mane_braid':
   zz=max(z+.10,.44);xx=side_x(recipe,y-.025,zz)-.012
   b.tube('mane_braid_spine','hair',[[xx,y+.025,zz],[xx,y-.045,zz]],[.072,.069],sides=8)
   for sign in (-1,1):b.oval('mane_braid_lock','hair_light' if (j+(sign==1))%2 else 'hair',[xx+sign*.035,y-.015,zz+sign*.015],[.059,.050,.060],sides=7)
   if j==len(ys)-1:b.tube('mane_braid_root','hair',[root,[xx,y-.025,zz]],[.051,.048],sides=7)
  elif choice=='mane_short':
   b.tube('mane_roached_lock','hair',[root,[0,y+.07,z-.10],[.01,y+.11,z-.16]],[.065,.055,.005],sides=6)
  else:
   length=.30 if slot=='head' else .62 if choice=='mane_long' else .54 if choice=='mane_waves' else .44
   bend=.052*math.sin(j*1.1) if choice=='mane_waves' else .024*math.sin(j*2)
   zz=max(z+.13,.45);midy=y-length*.52;tipy=y-length
   xxmid=side_x(recipe,midy,zz)-.017;xxend=side_x(recipe,tipy,zz+.015)-.02
   b.tube('mane_curtain_lock','hair_light' if j%4==0 else 'hair',[root,[-.06,y-.035,z-.025],[xxmid+bend,midy,zz],[xxend+bend,tipy,zz+.015]],[.064,.063,.057,.005],sides=7)
 if slot=='head' and choice!='mane_short':
  for j in range(7):
   path=[]
   for x,y,depth in [(-.10+j*.033,2.29,-.008),(-.11+j*.030,2.18,.021),(-.09+j*.025,2.04+abs(j-3)*.035+.012*math.sin(j*2),.023)]:
    path.append([x,y,crest(recipe,y,front=True)+depth])
   b.tube('mane_forelock','hair',path,[.048,.044,.005],sides=6)
 for c in b.commands:
  v,f=mesh_command(c);c.update(op='indexed_mesh',vertices=v.tolist(),faces=orient_faces(v,f).tolist(),id=f'horse-{slot}-{len(recipe["commands"])}',native_anatomy='beast-horse',horse_mane=choice)
  recipe['commands'].append(c)
 recipe['commands'].sort(key=lambda c:c['stage'])
 recipe['palette'].update(b.palette);recipe['horse_mane']={'schema_version':1,'choice':choice,'method':'roots projected onto posterior surface of selected neck/head'}
