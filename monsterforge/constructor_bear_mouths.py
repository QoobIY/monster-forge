"""Independent animal mouth expressions, fitted to the selected bear muzzle."""
import copy
import numpy as np
from tools.creature_workshop.original_constructor import OriginalSculpt,mesh_command
from tools.creature_workshop.family_faces import orient_faces
from tools.creature_workshop.owned_surface_revision import front_surface

RACES={'beorn','panda'}
LABELS={'profile':'Рот выбранной морды','small':'Нейтральный','stern':'Недовольный','teeth':'Приоткрытая пасть','fangs':'Оскал'}
DEFAULTS=('small','stern','fangs','teeth')
DESCRIPTIONS={'small':'Закрытый нейтральный рот с прямой линией губ без улыбки.','stern':'Закрытый рот с опущенными уголками и тяжёлой нижней губой.','teeth':'Приоткрытая медвежья пасть с тёмной полостью, нижней губой и небольшими резцами.','fangs':'Оскал с приподнятой верхней губой, парными верхними и нижними клыками, отдельными резцами.'}

def apply(recipe,settings):
 if recipe.get('species_design',{}).get('anatomy') in {'ape','owl'}:return recipe
 race=settings['race']
 if race not in RACES:return recipe
 kind=settings['features']['mouth'];variant=recipe['own_body_design']['variant']
 if kind in ('profile','original'):kind=DEFAULTS[variant]
 recipe['commands']=[c for c in recipe['commands'] if c['part'] not in ('bear_mouth','philtrum') and not c['part'].startswith('bear_expression_')]
 surface=[c for c in recipe['commands'] if c['part']=='bear_muzzle']
 # Older anatomy treated 'bear_muzzle' as an ear due to the substring 'ear'.
 # Undo that accidental vertical ear adjustment only on the muzzle.
 for c in surface:
  if not c.get('bear_muzzle_fit_revision'):
   v,f=mesh_command(c);shift=(0,.025,-.025,-.032)[variant];factor=c['anatomical_profile'][-1]
   center=v[:,1].mean()-shift;v[:,1]=(v[:,1]-shift-center)/factor+center
   c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist(),bear_muzzle_fit_revision=1)

 verts=np.concatenate([mesh_command(c)[0] for c in surface]);width=float(np.ptp(verts[:,0]))*.30
 mouth_width=min(.105,max(.066,width));cy=2.187
 def z(x,y):
  value=front_surface(surface,x,y)
  if value is None:raise ValueError('Медвежий рот вышел за поверхность морды')
  return value
 palette=copy.deepcopy(recipe['palette']);palette.update(bear_mouth_dark='29231f',bear_teeth='d5cdb5',bear_gum='755349')
 b=OriginalSculpt({'id':'bear-expressions-v1','palette':palette});b.slot='head';b.stage=2
 def line(name,xy,mat='bear_mouth_dark',r=.004,depth=.002):
  b.tube('bear_expression_'+name,mat,[[x,y,z(x,y)+depth] for x,y in xy],[r]*len(xy),sides=6)
 if kind in ('small','stern'):
  edge=cy-.019 if kind=='stern' else cy
  path=[[-mouth_width,edge],[-mouth_width*.5,cy-.002],[0,cy+.002 if kind=='stern' else cy],[mouth_width*.5,cy-.002],[mouth_width,edge]]
  line('closed_line',path,r=.0045)
  line('lower_lip',[[x,y-.011] for x,y in path[1:-1]],'muzzle',r=.009,depth=.001)
 else:
  halfheight=.038 if kind=='fangs' else .026
  # A recessed dark pocket with a shaped perimeter and closed backing.
  points=[]
  for a in np.linspace(0,2*np.pi,12,endpoint=False):
   x=mouth_width*np.cos(a);y=cy+halfheight*np.sin(a);points.append([x,y,z(x,y)+.002])
  b.panel3('bear_expression_cavity','bear_mouth_dark',points,.016)
  line('upper_lip',[[-mouth_width,cy],[-mouth_width*.55,cy+halfheight*.86],[0,cy+halfheight],[mouth_width*.55,cy+halfheight*.86],[mouth_width,cy]],'muzzle',r=.008)
  line('lower_lip',[[-mouth_width,cy],[-mouth_width*.55,cy-halfheight*.86],[0,cy-halfheight],[mouth_width*.55,cy-halfheight*.86],[mouth_width,cy]],'muzzle',r=.011)
  # Teeth enter their gum roots; each narrows along a short curved axis.
  for j in range(4):
   x=(j-1.5)*mouth_width*.21;y=cy+halfheight*.75
   b.tube('bear_expression_incisor','bear_teeth',[[x,y,z(x,y)+.004],[x,y-.009,z(x,y-.009)+.006]],[.007,.005],sides=7)
  if kind=='fangs':
   for sign in (-1,1):
    x=sign*mouth_width*.64;y=cy+halfheight*.72
    b.tube('bear_expression_upper_canine','bear_teeth',[[x,y,z(x,y)+.004],[x-sign*.005,cy+.001,z(x-sign*.005,cy+.001)+.007],[x-sign*.013,cy-.012,z(x-sign*.013,cy-.012)+.006]],[.010,.007,.0018],sides=8)
    x=sign*mouth_width*.47;y=cy-halfheight*.70
    b.tube('bear_expression_lower_canine','bear_teeth',[[x,y,z(x,y)+.004],[x+sign*.004,cy-.007,z(x+sign*.004,cy-.007)+.006]],[.008,.0018],sides=7)
 line('philtrum',[[0,2.229],[0,cy+.043 if kind=='fangs' else cy+.029 if kind=='teeth' else cy+.006]],r=.0035)
 for j,c in enumerate(b.commands):
  v,f=mesh_command(c);recipe['commands'].append({**c,'id':f'bear-expression-{j}','op':'indexed_mesh','vertices':v.tolist(),'faces':orient_faces(v,f).tolist(),'native_anatomy':race,'bear_mouth_revision':1,'mouth_expression':kind})
 recipe['palette'].update(b.palette);recipe['commands'].sort(key=lambda c:c['stage'])
 recipe['bear_mouth']={'schema_version':1,'expression':kind,'description_ru':DESCRIPTIONS[kind],'fit':'selected bear_muzzle triangle surface','source_face':recipe['own_body_design']['id']}
 return recipe
