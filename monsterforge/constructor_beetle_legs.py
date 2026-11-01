"""Anatomical, longitudinally separated beetle legs; applied as derived revisions."""
import copy
import numpy as np
from tools.creature_workshop.original_constructor import OriginalSculpt,mesh_command
from tools.creature_workshop.family_faces import orient_faces
REVISION=2
# +Z is forwards. Forelegs reach forwards and hindlegs reach backwards.
PROFILE={
 1:dict(root=[.215,.53,.20],hip=[.29,.50,.25],knee=[.48,.54,.43],ankle=[.66,.074,.59],foot=[.72,.027,.68],tip=[.75,.014,.76]),
 2:dict(root=[.23,.53,-.045],hip=[.34,.49,-.065],knee=[.56,.52,-.015],ankle=[.78,.070,.01],foot=[.85,.026,.035],tip=[.91,.014,.055]),
 3:dict(root=[.30,.53,-.40],hip=[.39,.48,-.45],knee=[.58,.50,-.64],ankle=[.75,.069,-.81],foot=[.81,.026,-.89],tip=[.86,.014,-.96]),
}

def apply(recipe,settings,slot):
 if settings['race']!='beetle' or '_leg_' not in slot:return
 side,index=slot.split('_leg_');index=int(index);sign=-1 if side=='left' else 1
 profile=copy.deepcopy(PROFILE[index]);p={k:np.asarray(v)*[sign,1,1] for k,v in profile.items()}
 b=OriginalSculpt({'id':'beetle-leg-anatomy-v2','palette':copy.deepcopy(recipe['palette'])});b.slot=slot;b.stage=1
 root,hip,knee,ankle,foot,tip=(p[k] for k in ('root','hip','knee','ankle','foot','tip'))
 # Coxa, muscular femur and tapering tibia have distinct contours. No decorative
 # balls at joints and no collapsed fore/mid/hind foot positions.
 b.tube('beetle_coxa','skin',[root.tolist(),hip.tolist()],[.039,.041],sides=8)
 femur=[hip,hip+(knee-hip)*.24,hip+(knee-hip)*.56,hip+(knee-hip)*.82,knee]
 b.tube('beetle_contoured_femur','skin',[v.tolist() for v in femur],[.039,.060,.062,.046,.033],sides=10)
 tibia=[knee,knee+(ankle-knee)*.16,knee+(ankle-knee)*.46,knee+(ankle-knee)*.80,ankle]
 b.tube('beetle_tapered_tibia','skin',[v.tolist() for v in tibia],[.033,.042,.032,.022,.016],sides=8)
 tarsus=[ankle,ankle+(foot-ankle)*.50,foot,foot+(tip-foot)*.55,tip]
 b.tube('beetle_articulated_tarsus','skin',[v.tolist() for v in tarsus],[.016,.014,.012,.008,.004],sides=7)
 # Paired terminal claws stay on the common floor plane; they follow the foot
 # rather than standing upright like the earlier tiny cylindrical stumps.
 forward=tip-foot;forward[1]=0;forward/=np.linalg.norm(forward);lateral=np.array([-forward[2],0,forward[0]])
 for sg in (-1,1):
  start=tip+lateral*sg*.004;mid=tip+forward*.025+lateral*sg*.010;end=tip+forward*.042+lateral*sg*.004;mid[1]=.008;end[1]=.003
  b.tube('beetle_grounded_claw','dark' if 'dark' in b.palette else 'skin',[start.tolist(),mid.tolist(),end.tolist()],[.005,.004,.001],sides=6)
 # Uniformly lower the entire slot to its ground contact; no limb stretching.
 commands=[];floor=min(float(mesh_command(c)[0][:,1].min()) for c in b.commands)
 for i,c in enumerate(b.commands):
  v,f=mesh_command(c);v[:,1]-=floor
  commands.append({**c,'id':f'beetle-leg-v{REVISION}-{slot}-{i}','op':'indexed_mesh','vertices':v.tolist(),'faces':orient_faces(v,f).tolist(),'ai_description_ru':('Передняя' if index==1 else 'Средняя' if index==2 else 'Задняя')+' нога жука: короткая тазиковая часть, объёмное бедро, сужающаяся голень, направленная лапка и парные коготки. Передняя пара направлена вперёд, задняя назад.'})
 source_parts=[c['id'] for c in recipe['commands']];recipe['commands']=commands;recipe['palette'].update(b.palette)
 recipe['contract_anchors'][slot]=(root-[0,floor,0]).tolist()
 recipe['beetle_leg_anatomy']={'schema_version':1,'revision':REVISION,'source_commands':source_parts,'pair':index,'side':side,'profile':{k:(v-[0,floor,0]).tolist() for k,v in p.items()},'ground_translation_y':-floor,'geometry_origin':'derived anatomical leg; source part unchanged'}
