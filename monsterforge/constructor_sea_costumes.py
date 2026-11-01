"""Three modular upper garments usable by humans and draft naga sources."""
import math
from .constructor_decor import sculpt
from .constructor_portraits import freeze
LABELS={'costume-sea-guard':'Доспех морского стража','costume-tidal-mage':'Облачение приливного мага','costume-reef-hunter':'Костюм рифового охотника'}
DESCRIPTIONS={'costume-sea-guard':'Морской нагрудник из перекрывающихся ребристых пластин, бронзовый кант, пояс с раковинами и бирюзовый табард.', 'costume-tidal-mage':'Длинное бирюзовое облачение, волнообразные отвороты, серебряные застёжки, рукава с крупным приливным орнаментом.', 'costume-reef-hunter':'Короткий кожаный жилет с косой перевязью, коралловые защитные пластины и крепления для снаряжения.'}
BASE={'costume-sea-guard':(2,1),'costume-tidal-mage':(3,2),'costume-reef-hunter':(5,4)}
def apply(recipe,settings,slot,kind):
 b=sculpt(settings);b.slot=slot;b.stage=3
 palette=dict(cloth='366a76',secondary='599f9a',metal='96afb2',accent='d2bd81',leather='5c4940')
 for name in recipe['palette']:
  for channel,value in palette.items():
   if name==channel or name.endswith('_'+channel):recipe['palette'][name]=(settings['colors'].get(channel) or value).lstrip('#')
 b.palette.update({k:(settings['colors'].get(k) or v).lstrip('#') for k,v in palette.items()})
 def panel(name,pts,mat='metal'):b.panel3('sea_'+name,mat,pts,.022)
 if slot=='torso':
  for sign in (-1,1):
   for i in range(4):
    x=sign*(.04+i*.047);y=1.77-i*.045
    if kind=='costume-tidal-mage':
     path=[[x,y,.28],[x+sign*.045,y-.09,.29],[x+sign*.024,y-.18,.28]];b.tube('sea_wave_lapel','secondary',path,[.029,.037,.011],sides=7)
    else:
     panel('ribbed_plate',[[x-sign*.026,y,.29],[x+sign*.040,y-.023,.30],[x+sign*.047,y-.18,.32],[x,y-.22,.31],[x-sign*.022,y-.09,.29]],'secondary' if kind=='costume-reef-hunter' else 'metal')
     b.tube('sea_plate_ridge','accent',[[x,y-.012,.317],[x+sign*.022,y-.15,.339]],[.005,.003],sides=5)
  for sign in (-1,1):
   x=sign*.14;y=1.16;b.oval('sea_shell_clasp','accent',[x,y,.31],[.045,.034,.014],sides=9)
   for a in (-.55,0,.55):b.tube('sea_shell_rib','metal',[[x,y-.018,.324],[x+math.sin(a)*.035,y+.026,.324]],[.003,.002],sides=5)
 elif slot.endswith('_arm'):
  sign=-1 if slot.startswith('left') else 1
  for i in range(3):
   x=sign*(.57+i*.028);y=1.41-i*.075
   panel('bracer',[[x-.045,y+.045,.15],[x+.047,y+.028,.15],[x+.043,y-.066,.17],[x,y-.09,.17],[x-.040,y-.052,.15]],'secondary' if kind=='costume-tidal-mage' else 'metal')
 elif slot.endswith('_leg'):
  sign=-1 if slot.startswith('left') else 1;x=sign*.21
  for i in range(3):
   y=.42-i*.084;panel('greave',[[x-.063,y+.05,.17],[x+.063,y+.05,.17],[x+.053,y-.050,.19],[x,y-.070,.19],[x-.054,y-.05,.19]])
 commands,pal=freeze(b,'new_costume');recipe['commands'].extend(commands);recipe['palette'].update(pal);recipe['costume_revision']={'schema_version':1,'id':kind,'description_ru':DESCRIPTIONS[kind]}
