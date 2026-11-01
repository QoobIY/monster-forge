"""Refine the approved boar wedge: nasal cartilage, masseter, tusks and bristles."""
import copy,math
import numpy as np
from tools.creature_workshop.geometry import mesh
from tools.creature_workshop.original_constructor import OriginalSculpt,mesh_command
from tools.creature_workshop.family_faces import orient_faces
from tools.creature_workshop.animal_anatomy import indexed,side_surface
from tools.creature_workshop.owned_surface_revision import front_surface
DESCRIPTION='Кабан: сохранён длинный клиновидный череп; тяжёлые нижние щёки, щетинистый контур затылка из общего меша, цельные прилегающие надбровья, кожистый объёмный пятачок с овальными углублёнными ноздрями, изогнутые нижние клыки и короткие верхние клыки у уголков закрытой пасти.'

def apply(recipe,settings,slot):
 if slot!='head' or settings['race']!='beast-boar':return
 skull=next(c for c in recipe['commands'] if c['part']=='boar_cranial_cheek_muzzle')
 v,f=mesh(skull);rings=v[:-2].reshape(-1,12,3).copy();variant=recipe['animal_design']['variant']
 # Preserve the nasal bridge, forehead and orbital carriers; add cheek muscle
 # below the eye plane. Posterior serrations share edges with the skin itself.
 tip=float(rings[-1,:,2].mean());hy=float(rings[0,:,1].mean()-.06)
 for ring in rings[:3]:
  below=np.clip((hy+.025-ring[:,1])/.15,0,1);ring[:,0]*=1+.10*below
 rear=(rings[0]+rings[1])*.5;fur_vertices=[]
 for j in (2,4,8,10):
  p=rear[j];p[0]+=np.sign(p[0])*.028;p[2]-=.023;p[1]-=.008;fur_vertices.append(12+j)
 crown=(rings[0]+rear)*.5
 for j in (0,1,11):crown[j,1]+=.031;crown[j,2]-=.013
 rings=np.concatenate([rings[:1],rear[None],crown[None],rings[1:]])
 # Sort the inserted sections by anatomical depth to keep the skull manifold.
 rings=rings[np.argsort(rings[:,:,2].mean(1))]
 verts=rings.reshape(-1,3).tolist();faces=[]
 for k in range(len(rings)-1):
  for j in range(12):
   a=k*12+j;c=k*12+(j+1)%12;d=a+12;e=c+12;faces.extend([[a,c,e],[a,e,d]] if (j+k)%2 else [[a,c,d],[c,e,d]])
 for k in (0,len(rings)-1):
  idx=len(verts);verts.append(rings[k].mean(0).tolist());faces.extend([[idx,k*12+j,k*12+(j+1)%12] for j in range(12)])
 v=np.array(verts);f=orient_faces(v,np.array(faces));skull.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist(),integrated_fur={'schema_version':1,'method':'two shared nape contours with backward swept bristle points; no attached bumps'})
 skull.pop('vertex_color_factors',None);skull['vertex_color_factors']=(1+.09*(v[:,1]-v[:,1].mean())/np.ptp(v[:,1])).tolist()
 face=(v,f)
 # Remove only the early placeholder ornaments, retaining eyes, ears and mouth.
 obsolete={'pig_snout_disc','nostril','curved_tusk','sculpted_orbital_ridge'}
 original=[c for c in recipe['commands'] if c['part'] not in obsolete]
 for c in original:
  if c['part'] in {'visible_iris','visible_pupil'}:
   vv,ff=mesh(c);vv=vv.copy();cy=vv[:,1].mean();vv[:,1]=cy+(vv[:,1]-cy)*.76;c.update(vertices=vv.tolist(),faces=ff.tolist())
 b=OriginalSculpt({**recipe['animal_design'],'palette':copy.deepcopy(recipe['palette'])});b.palette.update(recipe['palette']);b.slot='head';b.stage=2
 b.palette.update(boar_nasal='6d5d50' if variant!=1 else '57514d',boar_nostril='171a18',boar_nasal_rim='807163' if variant!=1 else '6d6862')
 nosey=float(rings[-1,:,1].mean())+.005;width=float(np.max(np.abs(rings[-1,:,0])))*.97
 # An authored cartilage outline with dorsal notch, lateral lobes and lower
 # septum; bevel and real depth replace a flat generic pink oval.
 outline=[(-.36,.93),(.36,.93),(.80,.61),(1,.16),(.90,-.47),(.48,-.84),(0,-.94),(-.48,-.84),(-.90,-.47),(-1,.16),(-.80,.61)]
 n=len(outline);nv=[];nf=[]
 for scale,z in [(1,tip-.012),(1,tip+.018),(.84,tip+.035)]:
  nv.extend([[x*width*scale,nosey+y*.062*scale,z] for x,y in outline])
 for k in range(2):
  for j in range(n):a=k*n+j;c=k*n+(j+1)%n;d=a+n;e=c+n;nf.extend([[a,c,e],[a,e,d]])
 for k,z in [(0,tip-.018),(2,tip+.038)]:
  idx=len(nv);nv.append([0,nosey,z]);nf.extend([[idx,k*n+j,k*n+(j+1)%n] for j in range(n)])
 indexed(b,'boar_nasal_cartilage','boar_nasal',nv,nf);carrier=b.commands[-1]
 for sign in (-1,1):
  xx=sign*width*.44;yy=nosey+.002;zz=front_surface([carrier],xx,yy)
  b.oval('nostril','boar_nostril',[xx,yy,zz+.001],[width*.18,.012,.005],sides=10)
  arc=[]
  for a in np.linspace(.05,math.pi*.98,6):
   x=xx+width*.20*math.cos(a);y=yy+.015*math.sin(a);z=front_surface([carrier],x,y);arc.append([x,y,z+.001])
  b.tube('nasal_cartilage_fold','boar_nasal_rim',arc,[.003]*len(arc),sides=5)
 b.tube('nasal_septum','boar_nasal_rim',[[0,nosey+.02,tip+.039],[0,nosey-.014,tip+.039]],[.003,.0025],sides=5)
 # Long lower canines grow out of the jaw, curl upward and sweep back. Short
 # upper whetters oppose them, rather than duplicating another huge tusk.
 for sign in (-1,1):
  z=tip-.155;y=hy-.102;x=side_surface(*face,y,z,sign)
  root=np.array([x-sign*.009,y,z]);height=[.147,.125,.175][variant]
  offsets=[[0,0,0],[sign*.028,.012,.026],[sign*.067,.052,.042],[sign*.076,height*.73,.028],[sign*.049,height,.006]]
  path=[(root+o).tolist() for o in offsets]
  b.tube('curved_tusk','enamel',path,[.030,.028,.022,.012,.0015],sides=9);b.commands[-1]['tusk_root']=root.tolist()
  yy=hy-.045;zz=tip-.139;xx=side_surface(*face,yy,zz,sign)
  b.tube('upper_whetter_tusk','enamel',[[xx-sign*.009,yy,zz],[xx+sign*.022,yy+.013,zz+.016],[xx+sign*.035,yy+.042,zz+.003]],[.021,.014,.0015],sides=8)
  # A single planar brow follows the eye margin, replacing four bead shapes.
  eye=next(c for c in original if c['part']=='visible_iris' and np.sign(mesh(c)[0][:,0].mean())==sign);ey,ez=mesh(eye)[0].mean(0)[1:]
  outline=[(-.065,.046),(-.016,.040),(.043,.013),(.046,-.001),(-.022,.021),(-.068,.028)];bv=[];bf=[];n=len(outline)
  for depth in (-.009,.015):
   for dz,dy in outline:
    yy=ey+dy;zz=ez+dz;xx=side_surface(*face,yy,zz,sign);bv.append([xx+sign*depth,yy,zz])
  for k in range(1,n-1):bf.extend([[0,k,k+1],[n,n+k+1,n+k]])
  for k in range(n):a=(k+1)%n;bf.extend([[k,a,a+n],[k,a+n,k+n]])
  indexed(b,'boar_fitted_brow','skin',bv,bf)
 for j,c in enumerate(b.commands):
  vv,ff=mesh_command(c);c.update(op='indexed_mesh',vertices=vv.tolist(),faces=orient_faces(vv,ff).tolist(),id=f'boar-face-{j}',native_anatomy='beast-boar',ai_description_ru=DESCRIPTION)
 recipe['commands']=sorted(original+b.commands,key=lambda c:c['stage']);recipe['palette'].update(b.palette)
 recipe['face_revision']={'schema_version':1,'id':'boar-face-v1','description_ru':DESCRIPTION,'method':'preserved wedge skull; authored nasal cartilage, native nape bristles, fitted brows and rooted curved canines'}
 recipe['animal_design']['description_ru']=DESCRIPTION
