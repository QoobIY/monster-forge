"""Geometry helpers retained for current constructor customization."""
import hashlib,math
import numpy as np
from scipy.spatial import ConvexHull
from .original_constructor import mesh_command
from .family_faces import orient_faces

def normals(v,f):
 n=np.zeros_like(v);cross=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
 for k in range(3):np.add.at(n,f[:,k],cross)
 return n/np.maximum(np.linalg.norm(n,axis=1),1e-12)[:,None]

def front_surface(commands,x,y):
 # Barycentric projection onto the actual front-facing rock facets.
 values=[]
 for c in commands:
  v,f=mesh_command(c)
  for tri in v[f]:
   xy=tri[:,:2];m=np.column_stack([xy[1]-xy[0],xy[2]-xy[0]])
   try:u,w=np.linalg.solve(m,np.array([x,y])-xy[0])
   except np.linalg.LinAlgError:continue
   if u>=-1e-6 and w>=-1e-6 and u+w<=1+1e-6:values.append(float(tri[0,2]+u*(tri[1,2]-tri[0,2])+w*(tri[2,2]-tri[0,2])))
 return max(values) if values else None
