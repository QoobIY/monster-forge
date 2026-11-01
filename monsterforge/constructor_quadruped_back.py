"""Rigid, uniformly scaled mounting of existing human artifacts on animal spines."""
import copy,math
import numpy as np
from tools.creature_workshop.geometry import mesh
from .constructor_mounts import Surface

def author(settings,body_recipe):
 from . import workshop_constructor as e
 recipe,source=e._load('library-human-01','back_attachment')
 recipe=e.author_back(recipe,settings['back'],'back_attachment')
 carriers=[c for c in body_recipe['commands'] if any(n in c['part'] for n in ('chest_waist_rump','ribcage_waist_croup'))]
 if not carriers:raise ValueError('Нет поверхности спины для крепления выбранного артефакта')
 carrier=max(carriers,key=lambda c:np.prod(np.ptp(mesh(c)[0],axis=0)))
 surface=Surface(carrier);lo,hi=surface.bounds;z=float(lo[2]+(hi[2]-lo[2])*.55)
 attachment=surface.radial(z,0,offset=-.008)
 origin=np.array([0,1.77,-.27])
 # Human vertical artifact becomes a dorsal artifact with its long axis aft.
 wing=any(name in settings['back'] for name in ('angel','demon','feather','raven','membrane','dragon','crystal','mechanical','fan'))
 angle=math.radians(35 if wing else 90)
 rotation=np.array([[1.,0,0],[0,math.cos(angle),-math.sin(angle)],[0,math.sin(angle),math.cos(angle)]])
 scale=float(np.clip((hi[0]-lo[0])/.68,.65,1.65))
 recipe['commands']=[e._transform(c,np.ones(3)*scale,-origin*scale,settings['back']) for c in recipe['commands']]
 for c in recipe['commands']:
  v,f=mesh(c);c.update(vertices=(v@rotation.T+attachment).tolist(),faces=f.tolist());c.pop('vertex_normals',None)
 from .constructor_face_fit import front_depth
 # Compare the lower artifact surface with the dorsal carrier in the mounting area.
 xy=np.array([[x,z+dz] for x in np.linspace(-.20,.20,9)*scale for dz in np.linspace(-.15,.15,9)*scale])
 def projected(commands,sign):
  result=[]
  for command in commands:
   v,f=mesh(command);result.append({**command,'op':'indexed_mesh','vertices':np.column_stack([v[:,0],v[:,2],sign*v[:,1]]).tolist(),'faces':f.tolist()})
  return result
 top=front_depth(projected([carrier],1),xy);bottom=-front_depth(projected(recipe['commands'],-1),xy)
 valid=np.isfinite(top)&np.isfinite(bottom)
 shift=0.
 if valid.any():
  shift=float(np.max(top[valid]-bottom[valid])-.002)
  for c in recipe['commands']:
   v,f=mesh(c);v[:,1]+=shift;c.update(vertices=v.tolist(),faces=f.tolist())
  attachment[1]+=shift
 recipe['contract_anchors']={'back_attachment':attachment.tolist()}
 recipe['assembly_reference']='quadruped_authoring_v1'
 recipe['quadruped_attachment']={'schema_version':1,'artifact':settings['back'],'source_contract':'humanoid_v1','target_contract':'quadruped_authoring_v1','uniform_scale':scale,'rotation':rotation.tolist(),'source_anchor':origin.tolist(),'target_anchor':attachment.tolist(),'carrier_part':carrier['part'],'surface_clearance_metres':-.002,'dorsal_contact_adjustment_metres':shift,'method':'rigid artifact placement at exact dorsal triangle intersection'}
 return recipe,source
