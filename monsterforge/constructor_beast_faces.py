"""Landmark-authored predator heads with orbital, nasal and mandibular planes."""
import copy,math
import numpy as np
from tools.creature_workshop.original_constructor import OriginalSculpt,mesh_command
from tools.creature_workshop.animal_anatomy import indexed,sweep,side_surface
from tools.creature_workshop.predator_heads import mouth
from tools.creature_workshop.family_faces import orient_faces

DESCRIPTIONS={
 'wolf':'Волк: клиновидный череп с височными плоскостями, длинная переносица без резкого стопа, углублённые косые глаза, объёмный нос с ноздрями, собранные губы, закрытая челюсть с видимыми боковыми клыками; шерсть растёт назад из общего меша щёк.',
 'bear':'Медведь: широкий объёмный лоб, углубление между лбом и носом, тяжёлые скуловые дуги, широкая мясистая морда, округлые уши с чашей, небольшие глубоко посаженные глаза, мощная нижняя челюсть и видимые клыки.'}

def sculpt(b,kind,variant):
 wolf=kind=='wolf';hy=1.185 if wolf else 1.15;hz=.78 if wolf else .76
 hx=([.245,.270,.262] if wolf else [.340,.325,.365])[variant]
 tip=([1.165,1.140,1.190] if wolf else [1.075,1.135,1.055])[variant]
 # Each section specifies width, dorsal ridge, lateral cheek and lower bite,
 # rather than sampling a scaled ellipse. Orbital stations pinch into the
 # brow; adjacent zygomatic and nasal planes remain full.
 if wolf:
  rows=[(.40,.16,1.37,1.21,1.02),(.51,hx*.94,1.415,1.225,1.035),(.63,hx,1.420,1.225,1.055),(.735,hx*.91,1.400,1.225,1.070),(.815,hx*.74,1.365,1.232,1.083),(.91,hx*.56,1.325,1.185,1.095),(tip-.115,hx*.48,1.280,1.165,1.106),(tip-.035,hx*.43,1.258,1.156,1.115),(tip,hx*.39,1.246,1.154,1.118)]
 else:
  rows=[(.385,hx*.60,1.465,1.22,.99),(.49,hx*.90,1.530,1.265,1.00),(.605,hx,1.545,1.28,1.02),(.715,hx*.94,1.485,1.275,1.037),(.80,hx*.76,1.370,1.23,1.047),(.875,hx*.65,1.320,1.185,1.060),(tip-.11,hx*.61,1.323,1.19,1.078),(tip-.035,hx*.57,1.312,1.178,1.083),(tip,hx*.53,1.295,1.168,1.091)]
 if variant==1:
  for k,row in enumerate(rows):
   z,w,t,c,d=row;rows[k]=(z,w,t+(.014 if wolf else -.025),c,d)
 # Sixteen anatomical lanes: sagittal ridge, forehead, orbital ledge,
 # zygomatic arch, masseter, bite plane, then mirrored lanes.
 verts=[];faces=[];tips=[]
 for k,(z,w,top,cheek,bottom) in enumerate(rows):
  half=[(0,top),(.43*w,top-.008),(.77*w,top-(top-cheek)*.35),(.94*w,cheek+.033),(w,cheek),(.78*w,bottom+.039),(.59*w,bottom+.008),(.36*w,bottom),(0,bottom-.005)]
  loop=half+[(-x,y) for x,y in half[-2:0:-1]]
  for lane,(x,y) in enumerate(loop):
   p=np.array([x,y,z])
   if k in (1,2,3) and lane in (3,4,5,11,12,13):
    # Shared fur blades are the cheek contour itself, swept toward the nape.
    p[0]+=np.sign(x)*(.035 if wolf else .018)*(1 if k==2 else .65)
    p[2]-=.035 if wolf else .018
    tips.append({'vertex':len(verts),'growth_direction':[0,-.24,-.97]})
   if k in (3,4) and lane in (3,13):p[0]-=np.sign(x)*(.018 if wolf else .023)
   verts.append(p)
  if k:
   for lane in range(16):
    a=(k-1)*16+lane;c=(k-1)*16+(lane+1)%16;d=k*16+lane;e=k*16+(lane+1)%16
    faces.extend([[a,c,e],[a,e,d]] if (lane+k)%2 else [[a,c,d],[c,e,d]])
 for k in (0,len(rows)-1):
  idx=len(verts);verts.append(np.mean(verts[k*16:(k+1)*16],axis=0))
  faces.extend([[idx,k*16+j,k*16+(j+1)%16] for j in range(16)])
 face=indexed(b,kind+'_cranial_cheek_muzzle','skin',verts,faces);skull=b.commands[-1]
 centres=face[0][face[1]].mean(1)
 skull['face_materials']=['cream' if p[2]>.87 and p[1]<(1.19 if wolf else 1.30) else 'skin' for p in centres]
 skull['anatomical_lanes']=['sagittal','forehead','orbital','zygomatic','masseter','bite']
 skull['integrated_fur']={'schema_version':1,'method':'shared cheek-contour blades; no attached tufts','tips':tips}
 # Almond lids are fitted around an actual globe. Broad skin rim bounds a
 # narrow dark opening; iris normal points forward from the oblique cheek.
 ey=1.275 if wolf else 1.295;ez=.807 if wolf else .785
 for sign in (-1,1):
  centre=np.array([side_surface(*face,ey,ez,sign),ey,ez])
  slope=(side_surface(*face,ey,ez+.002,sign)-side_surface(*face,ey,ez-.002,sign))/.004
  normal=np.array([sign,0,-sign*slope]);normal/=np.linalg.norm(normal)
  tangent=np.cross(normal,[0,1,0]);tangent/=np.linalg.norm(tangent)
  # The lateral eye margin follows the actual skin, its inside lid is tucked.
  for name,mat,width,height,depth in [('orbital_lid','skin',.059,.027,.006),('eye_socket','dark',.046,.016,.009)]:
   v=[];f=[]
   for offset in (-.008,.009):
    for j in range(12):
     a=j*2*math.pi/12;zz=ez+width*math.cos(a);yy=ey+height*math.sin(a)-.12*width*math.cos(a)
     xx=side_surface(*face,yy,zz,sign);v.append([xx+sign*(depth+offset),yy,zz])
   for j in range(1,11):f.extend([[0,j,j+1],[12,12+j+1,12+j]])
   for j in range(12):n=(j+1)%12;f.extend([[j,n,n+12],[j,n+12,j+12]])
   indexed(b,name,mat,v,f)
  for name,mat,depth,rad in [('visible_iris','iris',.023,[.014,.009,.021]),('visible_pupil','pupil',.030,[.004,.007,.010]),('eye_glint','sclera',.035,[.0025,.0025,.003])]:
   p=centre+normal*depth
   if name=='eye_glint':p+=np.array([0,.005,0])
   b.oval(name,mat,p.tolist(),rad,sides=10);v,f=mesh_command(b.commands[-1]);basis=np.column_stack([normal,[0,1,0],tangent]);v=(v-p)@basis.T+p;b.commands[-1].update(op='indexed_mesh',vertices=v.tolist(),faces=orient_faces(v,f).tolist())
  # Ears have a broad attached root, an outer rim and recessed inner bowl.
  if wolf:
   outline=[(-.066,-.055),(-.059,.018),(-.018,.165),(.023,.186),(.068,.030),(.054,-.053)]
   root=np.array([sign*hx*.76,1.407,.56]);depth=.055
  else:
   outline=[(-.068,-.035),(-.074,.015),(-.049,.063),(0,.078),(.052,.062),(.076,.011),(.064,-.035),(0,-.057)]
   root=np.array([sign*hx*.80,1.472,.50]);depth=.052
  n=len(outline);v=[]
  for scale,z in [(1,-depth*.5),(1,depth*.4),(.65,depth*.42),(.56,0)]:
   v.extend((root+np.array([x*scale,y*scale,z])).tolist() for x,y in outline)
  f=[]
  for k in range(3):
   for j in range(n):a=k*n+j;c=k*n+(j+1)%n;d=a+n;e=c+n;f.extend([[a,c,e],[a,e,d]])
  for k in (0,3):
   idx=len(v);v.append((root+np.array([0,0,-depth*.5 if k==0 else 0])).tolist());f.extend([[idx,k*n+j,k*n+(j+1)%n] for j in range(n)])
  indexed(b,kind+'_cupped_ear','skin',v,f);b.commands[-1]['face_materials']=['skin']*(n*4)+['shadow']*(len(f)-n*4)
 # Shaped nasal cartilage, with two visible inset nostrils and central groove.
 nose_y=rows[-1][3]+.025;nw=hx*(.39 if wolf else .52)
 stations=[([0,nose_y,tip-.020],nw*.94,.048),([0,nose_y+.005,tip+.018],nw,.047),([0,nose_y-.008,tip+.032],nw*.76,.032)]
 sweep(b,'nasal_cartilage','dark',stations,sides=12)
 b.palette['nose_highlight']='464749';b.palette['nostril_dark']='121519'
 for sign in (-1,1):
  b.oval('nostril','nostril_dark',[sign*nw*.55,nose_y+.002,tip+.034],[nw*.23,.014,.006],sides=8)
  b.tube('nasal_alar_rim','nose_highlight',[[sign*nw*.82,nose_y+.022,tip+.018],[sign*nw*.55,nose_y+.023,tip+.030],[sign*nw*.31,nose_y+.016,tip+.034]],[.004]*3,sides=6)
 b.tube('nasal_philtrum','dark',[[0,nose_y-.030,tip+.021],[0,rows[-1][4]+.005,tip+.002]],[.003,.002],sides=5)
 mouth(b,kind,hy,hz,tip,hx,variant,face,sweep)
 return b

def apply(recipe,settings,slot):
 if slot!='head' or settings['race'] not in {'beast-wolf','beast-bear'}:return
 kind=recipe['animal_design']['anatomy'];variant=recipe['animal_design']['variant']
 b=OriginalSculpt({**recipe['animal_design'],'palette':copy.deepcopy(recipe['palette'])});b.slot='head';b.stage=2
 sculpt(b,kind,variant)
 for j,c in enumerate(b.commands):
  v,f=mesh_command(c);c.update(op='indexed_mesh',vertices=v.tolist(),faces=orient_faces(v,f).tolist(),id=f'beast-face-{kind}-{j}',native_anatomy=settings['race'],ai_description_ru=DESCRIPTIONS[kind])
 recipe['commands']=b.commands;recipe['palette'].update(b.palette)
 recipe['face_revision']={'schema_version':1,'id':'beast-face-v1','landmarks':['occiput','temporal_arch','orbital_rim','zygomatic','nasal_bridge','nasal_cartilage','mandible'],'description_ru':DESCRIPTIONS[kind]}
 recipe['animal_design']['description_ru']=DESCRIPTIONS[kind]
