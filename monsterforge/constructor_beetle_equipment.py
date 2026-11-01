"""Optional insect armor, fitted to each selected shell rather than mount tack."""
import math
import numpy as np
from tools.creature_workshop.geometry import mesh
from tools.creature_workshop.original_constructor import OriginalSculpt,mesh_command
from tools.creature_workshop.family_faces import orient_faces
OPTIONS={
 'headwear':{'none':'Без шлема','insect_brow_guard':'Налобный щит','insect_war_helm':'Боевой шлем'},
 'shoulders':{'none':'Без грудной брони','insect_thorax_guard':'Грудной панцирь','insect_thorax_lamellar':'Сегментная грудная броня'},
 'belt':{'none':'Без брони надкрыльев','insect_elytra_guard':'Парные щиты надкрыльев','insect_elytra_lamellar':'Сегментная броня надкрыльев'},
 'emblem':{'none':'Без знака','sun':'Солнечный знак','skull':'Череп'},
}

def apply(recipe,settings,slot):
 if slot not in {'head','torso','abdomen'}:return
 category={'head':'headwear','torso':'shoulders','abdomen':'belt'}[slot];choice=settings['decor'][category];emblem=settings['decor']['emblem'] if slot=='torso' else 'none'
 if choice=='none' and emblem=='none':return
 from .constructor_mounts import Surface
 names={'head':('nerubian_shield_cephalon','arthropod_cephalon'),'torso':('segmented_thoracic_shell',),'abdomen':('separate_elytron',)}[slot]
 carriers=[c for c in recipe['commands'] if c['part'] in names]
 if not carriers:raise ValueError('Insect armor requires an actual shell surface')
 b=OriginalSculpt({'id':'insect-equipment-v1','palette':{'skin':recipe['palette']['skin'],'hair':recipe['palette']['hair'],'cloth':'354952','accent':'c5a567','metal':'6b8491','secondary':'9bb1b9','leather':'463b35'}});b.slot=slot;b.stage=4;contacts=[]
 def plate(surface,name,zs,angles,offset=.007,thickness=.014):
  grid=np.array([[surface.radial(float(z),float(a),offset) for a in angles] for z in zs]);m,n=len(zs),len(angles);count=m*n
  direction=np.array([[math.sin(a),math.cos(a),0] for a in angles]);back=grid.reshape(-1,3);outer=(grid+direction*thickness).reshape(-1,3);v=np.concatenate([back,outer]);f=[]
  for i in range(m-1):
   for j in range(n-1):
    q=i*n+j;f.extend([[q,q+n,q+n+1],[q,q+n+1,q+1],[q+count,q+n+1+count,q+n+count],[q+count,q+1+count,q+n+1+count]])
  perimeter=list(range(n))+[i*n+n-1 for i in range(1,m)]+list(range(count-2,count-n-1,-1))+[i*n for i in range(m-2,0,-1)]
  for q,r in zip(perimeter,perimeter[1:]+perimeter[:1]):f.extend([[q,r,r+count],[q,r+count,q+count]])
  b.commands.append(dict(id=name,op='indexed_mesh',vertices=v.tolist(),faces=f,part=name,slot=slot,material='metal',stage=4,purpose='Insect armor fitted against actual shell triangles with bounded outward clearance'))
  top=outer.reshape(m,n,3)
  for edge in (top[0],top[-1],top[:,0],top[:,-1]):b.tube(name+'_rolled_trim','accent',edge.tolist(),[.0045]*len(edge),sides=6)
  for i,j in ((1,1),(m-2,1),(1,n-2),(m-2,n-2)):
   point=top[i,j]+direction[j]*.003;b.oval(name+'_rivet','accent',point.tolist(),[.006]*3,sides=6)
  contacts.append(dict(part=name,carrier=surface.name,points=back.tolist(),clearance=offset,thickness=thickness))
  return top
 for ci,c in enumerate(carriers):
  surface=Surface(c);surface.name=c['id'];lo,hi=surface.bounds;length=hi[2]-lo[2]
  if choice!='none':
   segments=3 if choice.endswith('lamellar') else 1
   for j in range(segments):
    z0=lo[2]+length*(.12+j*.76/segments);z1=lo[2]+length*(.12+(j+1)*.76/segments-.018)
    half=.83 if slot=='head' else 1.23 if slot=='torso' else 1.45
    plate(surface,f'insect_{slot}_guard_{ci}_{j}',np.linspace(z0,z1,6),np.linspace(-half,half,13),offset=.006+j*.001)
   if choice=='insect_war_helm':
    points=[surface.radial(z,0,.033) for z in np.linspace(lo[2]+length*.2,lo[2]+length*.75,6)]
    b.tube('insect_helmet_swept_crest','secondary',np.asarray(points).tolist(),[.014,.026,.036,.040,.028,.006],sides=8)
  if emblem!='none':
   z=lo[2]+length*.63
   plate(surface,'insect_heraldic_base',np.linspace(z-.050,z+.050,5),np.linspace(-.36,.36,9),offset=.024,thickness=.011)
   def point(dx,dz):
    zz=z+dz;centre=surface.centre(zz);r=surface.radial(zz,0);radius=r[1]-centre[1];angle=math.asin(max(-.95,min(.95,dx/radius)));return surface.radial(zz,angle,.042).tolist()
   if emblem=='sun':
    ring=[point(math.cos(t)*.029,math.sin(t)*.029) for t in np.linspace(0,math.tau,17)];b.tube('insect_sun_ring','accent',ring,[.004]*len(ring),sides=6)
    for j in range(8):
     t=math.tau*j/8;b.tube('insect_sun_ray','accent',[point(math.cos(t)*.035,math.sin(t)*.035),point(math.cos(t)*.045,math.sin(t)*.045)],[.0035,.002],sides=5)
   else:
    ring=[point(math.cos(t)*.027,math.sin(t)*.023+.008) for t in np.linspace(0,math.tau,13)];b.tube('insect_skull_outline','accent',ring,[.005]*len(ring),sides=6)
    for sign in (-1,1):b.oval('insect_skull_eye','leather',point(sign*.011,.010),[.006]*3,sides=6)
    b.tube('insect_skull_jaw','accent',[point(-.017,-.012),point(-.013,-.030),point(.013,-.030),point(.017,-.012)],[.004]*4,sides=6)
 for i,c in enumerate(b.commands):
  v,f=mesh_command(c);c.update(op='indexed_mesh',vertices=v.tolist(),faces=orient_faces(v,f).tolist(),id=f'insect_gear_{slot}_{i}',material='insect_'+c['material'],insect_equipment=True,ai_description_ru='Съёмная экипировка жука: '+c['part']+'. Посадка по поверхности выбранного панциря, жвалы, глаза и суставы открыты.');recipe['commands'].append(c)
 recipe['palette'].update({'insect_'+k:v for k,v in b.palette.items()});recipe['commands'].sort(key=lambda c:c['stage']);recipe['insect_equipment']=dict(schema_version=1,choice=choice,emblem=emblem,contact=contacts)
