"""Contour and surface primitives used by current animal customization."""
import math
import numpy as np
from .family_faces import orient_faces

def indexed(b,name,material,v,f):
 v=np.asarray(v,float);f=orient_faces(v,np.asarray(f,int))
 b.commands.append({'id':f'animal-{len(b.commands)}','op':'indexed_mesh','slot':b.slot,'part':name,'material':material,'stage':b.stage,'purpose':name.replace('_',' '),'vertices':v.tolist(),'faces':f.tolist()})
 return v,f

def sweep(b,name,material,stations,sides=12,axis='z',tone=None,fur=None):
 """Contour rings track chest/waist/rump or cranial landmarks. Closed end caps."""
 original_stations=stations
 if fur:
  expanded=[]
  for row,(left,right) in enumerate(zip(stations,stations[1:])):
   expanded.append((left,False,row))
   if 'cranial' not in name or row<2:
    t=.50;expanded.append((((np.asarray(left[0])*(1-t)+np.asarray(right[0])*t).tolist(),left[1]*(1-t)+right[1]*t,left[2]*(1-t)+right[2]*t),True,row))
  expanded.append((stations[-1],False,len(stations)-1))
  stations=[x[0] for x in expanded]
 else:expanded=[(st,False,row) for row,st in enumerate(stations)]
 v=[];base=[];tips=[];f=[]
 for k,(p,w,h) in enumerate(stations):
  for j in range(sides):
   a=j*2*math.pi/sides
   if axis=='z':q=np.asarray(p)+[w*math.sin(a),h*math.cos(a),0]
   else:
    prev=np.asarray(stations[max(0,k-1)][0]);nxt=np.asarray(stations[min(len(stations)-1,k+1)][0]);t=nxt-prev;t/=np.linalg.norm(t)
    e=np.array([1.,0,0]);normal=np.cross(t,e);normal/=np.linalg.norm(normal)
    q=np.asarray(p)+e*w*math.sin(a)+normal*h*math.cos(a)
   base.append(q.copy())
   if fur and expanded[k][1] and (j+expanded[k][2])%2==0:
    # The tip is a shared contour vertex: its adjacent faces belong to the skin itself.
    if axis=='z':out=np.array([math.sin(a),math.cos(a),0.]);flow=np.array([0.,-.22,-1.])
    else:out=e*math.sin(a)+normal*math.cos(a);flow=t if name in {'foreleg_muscle_joint','hindleg_thigh_hock'} else -t
    flow-=out*(flow@out);flow/=np.linalg.norm(flow)
    mask=1. if 'cranial' not in name else .95 if abs(math.sin(a))>.6 else .15
    leg=name in {'foreleg_muscle_joint','hindleg_thigh_hock'}
    amplitude=(.012 if leg else .067 if fur=='wolf' else .046)*mask*(.85+.15*math.sin(j*1.7+k))
    travel=(.016 if leg else .052 if fur=='wolf' else .042)*mask
    spacing=np.linalg.norm(np.asarray(stations[min(k+1,len(stations)-1)][0])-np.asarray(stations[max(k-1,0)][0]));travel=min(travel,spacing*.32)
    delta=out*amplitude+flow*travel;q=q+delta
    tips.append({'vertex':len(v),'growth_direction':flow.tolist(),'outward_direction':out.tolist(),'displacement':delta.tolist()})
   v.append(q)
  if k:
   for j in range(sides):
    a=(k-1)*sides+j;c=(k-1)*sides+(j+1)%sides;d=k*sides+j;e=k*sides+(j+1)%sides
    f.extend([[a,c,e],[a,e,d]] if (j+k)%2 else [[a,c,d],[c,e,d]])
 for k in (0,len(stations)-1):
  idx=len(v);v.append(stations[k][0]);base.append(np.asarray(stations[k][0]))
  f.extend([[idx,k*sides+j,k*sides+(j+1)%sides] for j in range(sides)])
 arrays=indexed(b,name,material,v,f)
 if fur:b.commands[-1]['integrated_fur']={'schema_version':1,'species':fur,'method':'shared serrated contour vertices tilted along hair growth; connected skin topology','base_vertices':np.asarray(base).tolist(),'tips':tips}
 if tone:
  c=b.commands[-1];p=np.asarray(v);c['vertex_color_factors']=(1+tone*(p[:,1]-p[:,1].mean())/max(np.ptp(p[:,1]),.01)).tolist()
 return arrays

def side_surface(v,f,y,z,sign):
 hits=[]
 for tri in v[f]:
  yz=tri[:,1:];mat=np.column_stack((yz[1]-yz[0],yz[2]-yz[0]));det=np.linalg.det(mat)
  if abs(det)<1e-10:continue
  uv=np.linalg.solve(mat,np.array([y,z])-yz[0])
  if min(uv)>=-1e-8 and sum(uv)<=1+1e-8:hits.append(float(tri[0,0]+uv@(tri[1:,0]-tri[0,0])))
 if not hits:raise ValueError(('No face contact',y,z))
 return max(hits) if sign==1 else min(hits)
