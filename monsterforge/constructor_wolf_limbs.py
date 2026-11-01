"""Canine shoulder/thigh masses and substantial digitigrade feet on fixed joins."""
import numpy as np
from .paths import ROOT
from tools.creature_workshop.animal_anatomy import sweep
from tools.creature_workshop.original_constructor import OriginalSculpt
from tools.creature_workshop.geometry import mesh

SOURCE=ROOT/'media/constructor/wolf_limbs/v1'
DESCRIPTION='Мощные волчьи конечности: широкое косое плечо, объёмное бедро, выраженные локоть и скакательный сустав, сужающиеся предплечье и голень, крупные пальцевые лапы с четырьмя пальцами и когтями. Шерсть встроена в контур и направлена вниз; суставы и плоскость опоры сохранены.'

def apply(recipe,settings,slot):
 if settings['race']!='beast-wolf' or not slot.endswith('_leg'):return
 front=slot.startswith('front_');sign=-1 if '_left_' in slot else 1
 root=recipe['joint_landmarks'][slot];x,_,z=root['root'];variant=recipe['animal_design']['variant']
 elbow=np.asarray(root['elbow' if front else 'stifle']);joint=np.asarray(root['wrist' if front else 'hock']);ankle=np.asarray(root['ankle'])
 if front:
  stations=[([x-sign*.027,1.06,z-.030],.125,.171),([x-sign*.007,.90,z-.015],.143,.189),
   ([x,.72,z-.031],.111,.148),(elbow.tolist(),.089,.109),
   ([x,.34,(elbow[2]+joint[2])*.5],.058,.072),(joint.tolist(),.068,.075),(ankle.tolist(),.061,.067)]
 else:
  stations=[([x-sign*.025,1.055,z-.035],.139,.184),([x,.88,z-.020],.159,.209),
   ([x,.70,z+.066],.144,.180),(elbow.tolist(),.104,.118),
   ([x,.34,(elbow[2]+joint[2])*.5-.015],.071,.097),(joint.tolist(),.071,.087),(ankle.tolist(),.061,.068)]
 # Northern wolves have deeper upper masses; mature wolves favour the front
 # quarters. The distal bones remain smaller and the joint centres stay fixed.
 for j,(p,w,d) in enumerate(stations):
  strength=(1.16 if j<4 else 1.07) if variant==1 else (1.09 if front and j<3 else 1.045 if not front and j<3 else 1.025) if variant==2 else 1
  stations[j]=(p,w*strength,d*strength)
 name='foreleg_muscle_joint' if front else 'hindleg_thigh_hock'
 b=OriginalSculpt({**recipe['animal_design'],'palette':recipe['palette'].copy()});b.stage=1;b.slot=slot
 sweep(b,name,'skin',stations,axis='path',sides=8,tone=.12,fur='wolf')
 replacement=b.commands[0];replacement.update(native_anatomy='beast-wolf',purpose=DESCRIPTION,ai_description_ru=DESCRIPTION,wolf_limb_revision={'schema_version':1,'variant':variant,'method':'authored shoulder/thigh/forearm/calf stations; fixed joint centres'})
 old=next(c for c in recipe['commands'] if c['part']==name);replacement['id']=old['id'];recipe['commands'][recipe['commands'].index(old)]=replacement
 paw_factor=(1.25,1.35,1.29)[variant]
 for c in recipe['commands']:
  if c['part'] not in {'digitigrade_paw','individual_toe','paw_claw'}:continue
  v,f=mesh(c);v=v.copy();v[:,0]=x+(v[:,0]-x)*paw_factor
  centre=z+.045;v[:,2]=centre+(v[:,2]-centre)*(1+(paw_factor-1)*.65)
  if c['part']=='digitigrade_paw':v[:,1]*=1.23
  c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist());c.pop('vertex_normals',None)
 recipe['wolf_limb_revision']={'schema_version':1,'id':'wolf-limbs-v1','description_ru':DESCRIPTION,'variant':variant,'contract_anchors_unchanged':True}
