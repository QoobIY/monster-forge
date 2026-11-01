"""Straight rearward naga tails, baked into derived tail-part revisions."""
import copy
import numpy as np
from tools.creature_workshop.original_constructor import OriginalSculpt,mesh_command
from tools.creature_workshop.family_faces import orient_faces
from .constructor_face_fit import front_depth
REVISION=2
PATH=[[0,1.12,.015],[0,.92,-.025],[0,.68,-.12],[0,.43,-.29],[0,.245,-.52],[0,.185,-.78],[0,.160,-1.05],[0,.125,-1.35],[0,.095,-1.65],[0,.068,-1.95],[0,.035,-2.23],[0,.008,-2.43]]
RADII=[.26,.255,.25,.235,.21,.18,.155,.12,.09,.063,.030,.002]

def apply(recipe,settings,slot):
 if settings['race']!='naga' or slot!='tail':return
 b=OriginalSculpt({'id':'naga-straight-tail-v2','palette':copy.deepcopy(recipe['palette'])});b.slot='tail';b.stage=1
 b.tube('straight_rearward_serpent_tail','skin',PATH,RADII,sides=12);c=b.commands[-1];v,f=mesh_command(c);floor=float(v[:,1].min());v[:,1]-=floor;c.update(op='indexed_mesh',vertices=v.tolist(),faces=orient_faces(v,f).tolist())
 shell=copy.deepcopy(c);old=recipe['commands'];commands=[c]
 # Preserve the existing ventral plates, but refit them against the new shell.
 for source in old:
  if source['part']!='ventral_serpent_scute':continue
  q=copy.deepcopy(source);vv,ff=mesh_command(q);depth=front_depth([shell],vv[:,:2]);
  if not np.isfinite(depth).all():raise ValueError('Naga ventral plate outside tail surface')
  # First/second vertex rings are the front/back of the original extruded scute.
  vv[:,2]=depth+np.where(np.arange(len(vv))<len(vv)//2,.014,-.003)
  q.update(op='indexed_mesh',vertices=vv.tolist(),faces=orient_faces(vv,ff).tolist());commands.append(q)
 for i,q in enumerate(commands):q.update(id=f'naga-tail-v{REVISION}-{i}',ai_description_ru='Хвост наги: без боковой спирали, прямая продольная ось X=0; плавный спуск от таза, затем длинный сужающийся хвост назад по −Z.')
 recipe['commands']=commands;recipe['contract_anchors']['tail']=(np.array(recipe['contract_anchors']['tail'])-[0,floor,0]).tolist();recipe['naga_tail_revision']={'schema_version':1,'revision':REVISION,'path':(np.array(PATH)-[0,floor,0]).tolist(),'radii':RADII,'direction':'-Z (backwards)','source_commands':[q['id'] for q in old],'ground_translation_y':-floor}
