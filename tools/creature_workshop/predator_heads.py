"""Geometry helpers retained for current constructor customization."""
import numpy as np
from .geometry import mesh
from .family_faces import orient_faces

def vertical_surface(v,f,x,z,upper=True):
 hits=[]
 for tri in v[f]:
  plane=tri[:,[0,2]];m=np.column_stack((plane[1]-plane[0],plane[2]-plane[0]))
  if abs(np.linalg.det(m))<1e-10:continue
  uv=np.linalg.solve(m,np.array([x,z])-plane[0])
  if min(uv)>=-1e-7 and sum(uv)<=1+1e-7:hits.append(float(tri[0,1]+uv@(tri[1:,1]-tri[0,1])))
 if not hits:raise ValueError('Tooth root outside jaw')
 return max(hits) if upper else min(hits)

def mouth(b,kind,hy,hz,tip,hx,variant,face,sweep):
 gap=([.020,.018,.025] if kind=='wolf' else [.024,.021,.027])[variant]
 def upper(z):return hy-.105+.045*np.clip((z-hz)/(tip-hz),0,1)
 def bite(z):return upper(z)-gap
 rows=[([0,hy-.153,hz-.065],hx*(.72 if kind=='wolf' else .80),.030 if kind=='wolf' else .045),([0,bite(hz+.09)-.040,hz+.09],hx*(.52 if kind=='wolf' else .69),.040 if kind=='wolf' else .055),([0,bite(tip-.10)-.033,tip-.10],hx*(.42 if kind=='wolf' else .61),.033),([0,bite(tip-.025)-.025,tip-.025],hx*(.36 if kind=='wolf' else .56),.025)]
 jaw=sweep(b,kind+'_articulated_lower_jaw','cream' if kind=='wolf' else 'skin',rows,sides=10,tone=.08)
 jawcommand=b.commands[-1];jv,jf=jaw;jv=jv.copy()
 # Follow the actual upper underside across the whole dental arcade. Merely
 # lifting a narrow jaw leaves an open side wedge under the sloping muzzle.
 for k,(_,_,depth) in enumerate(rows):
  for j in range(10):
   idx=k*10+j;p=jv[idx]
   ceiling=vertical_surface(*face,p[0],p[2],upper=False)
   p[1]=ceiling-gap-depth*(1-np.cos(j*2*np.pi/10))
 for k in (0,len(rows)-1):jv[len(rows)*10+(0 if k==0 else 1)]=jv[k*10:(k+1)*10].mean(0)
 jawcommand.update(vertices=jv.tolist(),faces=orient_faces(jv,jf).tolist());jaw=(jv,jf)
 jawcommand['predator_mouth']={'schema_version':1,'gap':gap,'bite_type':('closed alert bite','closed guarded bite','closed fierce bite')[variant],'fit':'lower-jaw contour follows true upper underside; narrow tooth opening'}
 # Recessed flat internal lining, not a rounded dark cylinder between the jaws.
 lining=[];lf=[]
 for z,w in [(hz+.045,hx*.50),(tip-.14,hx*(.44 if kind=='wolf' else .59)),(tip-.027,hx*(.35 if kind=='wolf' else .49))]:
  cy=vertical_surface(*face,0,z,upper=False)-gap*.5;half=gap*.15;w*=.42
  lining.extend([[-w,cy+half,z],[w,cy+half,z],[w,cy-half,z],[-w,cy-half,z]])
 b.palette['mouth_dark']='211b1c'
 for k in range(2):
  for j in range(4):
   a=k*4+j;c=k*4+(j+1)%4;d=a+4;e=c+4;lf.extend([[a,c,e],[a,e,d]])
 lf.extend([[0,2,1],[0,3,2],[8,9,10],[8,10,11]])
 from .animal_anatomy import indexed
 indexed(b,'recessed_oral_lining','mouth_dark',lining,lf)
 from .animal_anatomy import side_surface
 def jaw_width(z):return float(np.interp(z,[p[0][2] for p in rows],[p[1] for p in rows]))
 for sign in (-1,1):
  lip=[]
  for z in np.linspace(hz+.08,tip-.035,7):
   x=sign*jaw_width(z)*.85;y=vertical_surface(*face,x,float(z),upper=False);lip.append([x,y-.001,float(z)])
  b.tube('upper_lip_border','dark',lip,[.003]*len(lip),sides=5)
  lip=[]
  for z in np.linspace(hz+.12,tip-.032,6):
   x=sign*jaw_width(z)*.85;y=vertical_surface(*jaw,x,float(z),upper=True);lip.append([x,y+.001,float(z)])
  b.tube('lower_lip_border','dark',lip,[.003]*len(lip),sides=5)
 # Teeth are planted on the actual upper/lower jaw triangles, not a floating row.
 roots=[]
 for top in (True,False):
  v,f=face if top else jaw
  zfront=tip-.039
  frontwidth=hx*(.24 if kind=='wolf' else .34)
  for k,x in enumerate(np.linspace(-frontwidth,frontwidth,6)):
   y=vertical_surface(v,f,float(x),zfront,upper=not top);direction=-1 if top else 1
   root=[float(x),y-direction*.006,zfront]
   length=gap*.36
   b.tube('upper_incisor' if top else 'lower_incisor','enamel',[root,[float(x),y+direction*length,zfront+.004]],[.010 if kind=='wolf' else .012,.004],sides=5)
   roots.append({'part':b.commands[-1]['part'],'root':root,'jaw':'upper' if top else 'lower'})
  for sign in (-1,1):
   z=tip-((.135 if top else .095) if kind=='wolf' else (.095 if top else .060));canine_z=z;x=sign*hx*((.43 if kind=='wolf' else .57) if top else (.28 if kind=='wolf' else .39))
   y=vertical_surface(v,f,x,z,upper=not top);direction=-1 if top else 1;length=(.072 if kind=='wolf' else .085) if top else gap*.44
   root=[x,y-direction*.008,z]
   b.tube('upper_canine' if top else 'lower_canine','enamel',[root,[x+sign*.013,y+direction*length*.57,z+.010],[x+sign*.012,y+direction*length,z+.022]],[.016 if kind=='wolf' else .022,.010,.0015],sides=7)
   roots.append({'part':b.commands[-1]['part'],'root':root,'jaw':'upper' if top else 'lower'})
   for j in range(3):
    z=float(np.linspace(hz+.025,canine_z-.045,3)[j]);x=sign*hx*((.40 if kind=='wolf' else .51) if top else (.29 if kind=='wolf' else .40))
    try:y=vertical_surface(v,f,x,z,upper=not top)
    except ValueError:continue
    root=[x,y-direction*.006,z]
    b.tube('upper_premolar' if top else 'lower_premolar','enamel',[root,[x,y+direction*gap*.32,z+.004]],[.010,.003],sides=5)
    roots.append({'part':b.commands[-1]['part'],'root':root,'jaw':'upper' if top else 'lower'})
 jawcommand['predator_mouth']['tooth_roots']=roots
 return jaw
