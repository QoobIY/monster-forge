"""Goblin regional landmarks and shared humanoid equipment; no independent rig."""
import math
import numpy as np
from .paths import ROOT
from .constructor_portraits import builder,freeze
from .constructor_knees import world_bind
from tools.creature_workshop.geometry import mesh
from tools.creature_workshop.family_faces import orient_faces

SOURCE=ROOT/'media/constructor/goblins/v1'
SKIN='809450'
NAMES=['Ловкач','Разведчик','Алхимик','Задира','Старейшина','Механик','Болотный','Купец','Ночной','Вождь']
COSTUMES={'costume-goblin-scout':'Гоблинский лазутчик','costume-goblin-tinker':'Гоблинский механик','costume-goblin-chief':'Гоблинский вождь'}
HEADWEAR={'goblin-goggles':'Гоблинские очки механика','goblin-cap':'Кожаный колпак с ушными вырезами','goblin-headdress':'Костяной убор вождя'}
BACKS={'back-goblin-tools':'Гоблинский ранец с инструментами','back-goblin-alchemy':'Гоблинский алхимический ранец','back-goblin-trophies':'Гоблинский штандарт с трофеями'}
GLOVES=['Кожаные перчатки с открытыми пальцами','Перчатки механика с накладками','Перчатки вождя с костяной защитой']
BOOTS=['Загнутые походные башмаки','Укреплённые сапоги механика','Сапоги вождя с костяными накладками']
DESCRIPTIONS={
 **{k:v+'. Самостоятельный гоблинский комплект на человеческом humanoid_v1; раздельные торс, рукава и штанины.' for k,v in COSTUMES.items()},
 **{k:v+'. Объёмный предмет, совместимый с расовыми ушами и человеческим skeleton contract.' for k,v in HEADWEAR.items()},
 **{k:v+'. Отдельный back_attachment, с опорой на спину выбранного человеческого тела.' for k,v in BACKS.items()}}
# Independently chosen regional proportions: cheekbones, jaw, chin, nasal wings,
# nose projection and orbital planes. These are not scaled orc profiles.
ROWS=[
 (.174,.195,.227,.139,.054,.113,.038,.325,.096,2.067,.014),
 (.165,.181,.219,.119,.043,.109,.032,.350,.079,2.043,.018),
 (.180,.204,.236,.150,.058,.120,.058,.320,.106,2.060,.010),
 (.184,.205,.234,.175,.078,.114,.055,.305,.119,2.083,-.008),
 (.171,.195,.245,.134,.050,.122,.044,.359,.098,2.025,.006),
 (.191,.209,.229,.161,.070,.120,.063,.313,.111,2.056,-.005),
 (.168,.202,.248,.144,.061,.128,.050,.343,.109,2.049,.020),
 (.189,.214,.251,.165,.067,.121,.066,.327,.120,2.070,.007),
 (.161,.184,.215,.117,.038,.109,.030,.374,.077,2.021,.023),
 (.198,.221,.260,.177,.079,.131,.061,.333,.128,2.045,-.010)]

def profile(gender,i):
 crown,temple,cheek,jaw,chin,eye,nose,nz,mouth,cy,tilt=ROWS[i]
 if gender=='female':
  crown-=.007;temple-=.008;cheek-=.005;jaw-=.013;chin-=.008;nose-=.005;nz-=.012;mouth-=.009;cy+=.009;tilt+=.004
 return dict(crown=crown,temple=temple,cheek=cheek,jaw=jaw,chin=chin,eye=eye,eye_y=2.385+(i%3-1)*.010,eye_h=.027 if gender=='male' else .032,tilt=tilt,brow=.041 if i in (3,4,9) else .029,nose=nose,nose_z=nz,mouth=mouth,chin_y=cy,forehead_z=.175+(i%3)*.008,cheek_z=.225+(i%4)*.008,jaw_z=.088+(i%3)*.010,chin_z=.235+(i%4)*.010,lip_z=.249+(i%3)*.008,ear=i%5)

def head(b,gender,i):
 from .constructor_racial_heads import flesh_surface,eyes,closed_patch
 p=profile(gender,i);v,names=flesh_surface(b,p,'goblin');b.commands[-1]['part']=b.commands[-1]['id']='goblin_cranium'
 eyes(b,p,v,names)
 for sign in (-1,1):
  shapes=[[(0,-.070),(.10,-.105),(.285,.090),(.130,.070),(.025,.048)],[(0,-.068),(.135,-.084),(.29,.020),(.17,.068),(.025,.048)],[(0,-.076),(.11,-.086),(.252,.145),(.13,.075),(.028,.050)],[(0,-.070),(.12,-.1),(.27,.05),(.215,.09),(.20,.075),(.16,.115),(.026,.053)],[(0,-.08),(.145,-.11),(.32,.055),(.165,.075),(.025,.054)]]
  root=p['temple']*.93;y=p['eye_y']+.037;pts=np.array([[sign*(root+x),y+dy,.055-x*.33] for x,dy in shapes[p['ear']]])
  n=len(pts);centre=pts.mean(0);inner=centre+(pts-centre)*.64;inner[:,2]-=.021;rear=pts.copy();rear[:,2]-=.032
  vv=np.concatenate([pts,inner,rear]);ff=[]
  for k in range(n):
   j=(k+1)%n;ff.extend([[k,j,n+j],[k,n+j,n+k],[k,2*n+k,2*n+j],[k,2*n+j,j]])
  for k in range(1,n-1):ff.extend([[2*n,2*n+k,2*n+k+1],[n,n+k+1,n+k]])
  b.solid('goblin_cupped_ear','skin',vv,orient_faces(vv,np.array(ff)),'Большое самостоятельное гоблинское ухо: длинный край, углублённая чаша, толщина и разный контур.')
  inner[:,2]+=.002;closed_patch(b,'goblin_ear_concha','lip',inner,np.array([[0,k,k+1] for k in range(1,n-1)]),'Углублённая внутренняя раковина гоблина.')
  nw=p['nose'];b.oval('goblin_nostril','shadow',[sign*nw*.69,2.265,p['nose_z']-.022],[nw*.23,.010,.007],sides=8)
 mw=p['mouth'];mz=p['lip_z'];path=[[-mw,2.174,mz-.025],[-mw*.55,2.173,mz],[0,2.170,mz+.006],[mw*.55,2.173,mz],[mw,2.174,mz-.025]]
 b.tube('goblin_mouth_seam','shadow',path,[.003,.004,.004,.004,.003],sides=6)
 for sign in (-1,1):
  x=mw*.76;length=.028+(i%4)*.007
  b.tube('goblin_canine','bone',[[sign*x,2.174,mz-.002],[sign*(x+.003),2.157,mz+.014],[sign*(x+.005),2.174-length,mz+.009]],[.009,.008,.001],sides=7)
 return p

def finish(recipe,b,prefix):
 cc,pal=freeze(b,prefix)
 for c in cc:c['slot']=b.slot
 recipe['palette'].update(pal);recipe['commands'].extend(cc)
 recipe.setdefault('goblin_revision',{'schema_version':1})
 return cc

def extremities(recipe,settings,slot):
 if settings['race']!='goblin' or not slot.endswith(('_arm','_leg')):return
 from .constructor_decor import sculpt
 b=sculpt(settings);b.palette['bone']='d3c7a4';b.palette['skin']=(settings['colors']['skin'] or '#'+SKIN).lstrip('#');b.slot=slot;b.stage=3
 s=-1 if slot.startswith('left') else 1;side=slot.split('_')[0];bind=world_bind()
 if slot.endswith('_arm'):
  n=settings['reference_parts']['gloves'] or 1
  recipe['commands']=[c for c in recipe['commands'] if not any(t in c['part'] for t in ('palm','thumb','finger','hand','glove'))]
  wrist=np.array(bind[side+'_hand']);x=s*abs(wrist[0]);z=wrist[2]
  b.loft('goblin_glove_palm','leather',[[.83,x+s*.017,z,.055,.030],[.895,x+s*.010,z,.076,.041],[.97,x,z,.061,.037]],sides=8)
  for k in range(4):
   fx=x+(k-1.5)*.033;ln=[.105,.121,.112,.091][k]
   b.tube('goblin_glove_finger','leather',[[fx,.864,z+.006],[fx+s*.008,.825,z+.012],[fx+s*.014,.864-ln,z+.032]],[.017,.015,.010],sides=7)
   b.tube('goblin_fingertip','skin',[[fx+s*.014,.864-ln,z+.032],[fx+s*.018,.845-ln,z+.038]],[.011,.008],sides=7)
  b.tube('goblin_glove_thumb','leather',[[x-s*.05,.938,z+.013],[x-s*.093,.900,z+.033],[x-s*.107,.845,z+.058]],[.025,.021,.012],sides=7)
  b.tube('goblin_thumb_tip','skin',[[x-s*.107,.845,z+.058],[x-s*.112,.819,z+.061]],[.013,.009],sides=7)
  b.loft('goblin_glove_cuff','leather',[[.95,x,z,.064,.039],[1.015,x-s*.012,z,.069,.045]],sides=8)
  b.box('goblin_glove_clasp','metal',[x,.990,z+.045],[.044,.034,.015])
  if n>=2:
   b.panel3('goblin_glove_knuckle_guard','metal' if n==2 else 'bone',[[x-.064,.91,z+.047],[x+.064,.91,z+.047],[x+.055,.851,z+.052],[x-.052,.851,z+.052]],.018)
   for k in (-1,0,1):b.oval('goblin_glove_rivet','accent',[x+k*.036,.895,z+.069],[.008,.008,.005],sides=6)
  if n==3:
   for k in (-1,1):b.tube('goblin_glove_bone_spur','bone',[[x+k*.038,.9,z+.06],[x+k*.05,.953,z+.09]],[.012,.001],sides=6)
 else:
  n=settings['reference_parts']['boots'] or 1
  recipe['commands']=[c for c in recipe['commands'] if not any(t in c['part'] for t in ('boot','foot','shoe','greave'))]
  x=bind[side+'_foot'][0];z=bind[side+'_foot'][2]
  b.loft('goblin_boot_shaft','leather',[[.08,x,z-.025,.070,.073],[.16,x,z-.055,.068,.070],[.29,x-s*.005,z-.06,.080,.073]],sides=8)
  b.loft('goblin_boot_sole','leather',[[0,x,z+.04,.081,.16],[.035,x,z+.04,.087,.175],[.095,x,z+.03,.081,.15],[.135,x,z-.025,.065,.084]],sides=8)
  b.tube('goblin_curved_toe','leather',[[x,.065,z+.13],[x,.073,z+.24],[x,.126,z+.31],[x,.158,z+.326]],[.063,.049,.022,.002],sides=8)
  for y in (.16,.25):b.loft('goblin_boot_strap','secondary',[[y-.015,x,z-.05,.079,.077],[y+.015,x,z-.05,.079,.077]],sides=8)
  b.box('goblin_boot_buckle','metal',[x+s*.075,.23,z-.021],[.018,.038,.041])
  if n>=2:b.panel3('goblin_boot_front_guard','metal' if n==2 else 'bone',[[x-.065,.275,z+.02],[x+.065,.275,z+.02],[x+.051,.145,z+.027],[x,.116,z+.047],[x-.051,.145,z+.027]],.023)
  if n==3:
   for k in (-1,1):b.tube('goblin_boot_bone_trim','bone',[[x+k*.049,.16,z+.052],[x+k*.055,.275,z+.036]],[.013,.012],sides=6)
 finish(recipe,b,'goblin_extremity');recipe['goblin_revision'].update(extremities='independent goblin gloves and shoes; shared SDK wrist/foot anchors',variant=n)

def costume(recipe,settings,slot):
 field='outfit' if slot=='torso' else 'arms' if slot.endswith('_arm') else 'legs' if slot.endswith('_leg') else None
 if not field or settings[field] not in COSTUMES:return
 from .constructor_decor import sculpt
 b=sculpt(settings);b.slot=slot;b.stage=3;k=settings[field];kind=list(COSTUMES).index(k)
 palettes=[dict(cloth='536147',leather='574131',metal='828578',accent='a4ad79',secondary='79874b'),dict(cloth='684d39',leather='443529',metal='87948e',accent='c49a53',secondary='985a3c'),dict(cloth='673b42',leather='49352b',metal='6f7772',accent='c8ab66',secondary='b3a47f')]
 pal=palettes[kind]
 for channel,value in pal.items():
  b.palette[channel]=(settings['colors'].get(channel) or '#'+value).lstrip('#')
  for name in recipe['palette']:
   if name==channel or name.endswith('_'+channel):recipe['palette'][name]=b.palette[channel]
 if slot=='torso':
  for s in (-1,1):
   if kind==0:
    b.panel3('goblin_scout_lapel','leather',[[s*.045,1.83,.23],[s*.18,1.81,.22],[s*.22,1.36,.235],[s*.08,1.27,.245]],.028)
    b.panel3('goblin_scout_split_skirt','secondary',[[s*.035,1.13,.18],[s*.21,1.13,.16],[s*.24,.83,.14],[s*.105,.77,.15]],.025)
   elif kind==1:
    b.panel3('goblin_tinker_apron','leather',[[-.18,1.68,.245],[.18,1.68,.245],[.20,.87,.19],[-.20,.87,.19]],.027) if s==1 else None
    for j in range(3):
     x=s*(.055+j*.045);b.box('goblin_apron_tool_loop','secondary',[x,1.27,.232],[.037,.09,.03]);b.tube('goblin_apron_tool','metal',[[x,1.34,.25],[x,1.12,.25]],[.010,.012],sides=6)
   else:
    for j in range(3):
     x=s*(.065+j*.060);y=1.72-j*.025
     b.panel3('goblin_chief_lamella','metal',[[x-s*.03,y+.04,.26],[x+s*.058,y+.015,.25],[x+s*.04,y-.25,.275],[x-s*.024,y-.21,.27]],.028)
    b.panel3('goblin_chief_tasset','secondary',[[s*.035,1.13,.20],[s*.24,1.12,.18],[s*.20,.83,.18],[s*.075,.76,.21]],.029)
  b.tube('goblin_diagonal_harness','leather',[[-.19,1.83,.245],[-.08,1.63,.29],[.10,1.37,.267],[.18,1.17,.24]],[.026]*4,sides=6)
  for x in (-.18,.18):
   b.box('goblin_belt_pouch','leather',[x,1.12,.215],[.105,.135,.075]);b.box('goblin_pouch_flap','secondary',[x,1.17,.258],[.11,.052,.022]);b.oval('goblin_pouch_stud','metal',[x,1.15,.273],[.009,.01,.006],sides=6)
 elif slot.endswith('_arm'):
  s=-1 if slot.startswith('left') else 1
  for j in range(2 if kind==0 else 3):
   x=s*(.65+j*.026);y=1.39-j*.075
   b.panel3('goblin_costume_bracer','leather' if kind==0 else 'metal',[[x-.065,y+.05,.10],[x+.065,y+.05,.10],[x+.054,y-.07,.12],[x-.054,y-.07,.12]],.024)
 else:
  s=-1 if slot.startswith('left') else 1
  b.panel3('goblin_costume_knee_patch','leather' if kind<2 else 'metal',[[s*.28-.065,.54,.18],[s*.28+.065,.54,.18],[s*.28+.055,.425,.21],[s*.28-.055,.425,.21]],.025)
 finish(recipe,b,'goblin_costume');recipe['goblin_revision'].update(costume=k,description_ru=DESCRIPTIONS[k])

def headwear(recipe,settings):
 k=settings['decor']['headwear']
 if k not in HEADWEAR:return
 b=builder(recipe);b.palette['bone']='d3c7a4';b.slot='head';b.stage=4
 if k=='goblin-goggles':
  for s in (-1,1):
   b.oval('goblin_headwear_goggle_rim','metal',[s*.117,2.398,.206],[.060,.050,.022],sides=12)
   b.oval('goblin_headwear_goggle_lens','secondary',[s*.117,2.398,.229],[.046,.037,.008],sides=10)
   b.tube('goblin_headwear_temple_arm','leather',[[s*.165,2.4,.206],[s*.204,2.40,.064],[s*.205,2.4,-.10]],[.012]*3,sides=6)
  b.tube('goblin_headwear_goggle_bridge','metal',[[-.052,2.405,.215],[0,2.428,.255],[.052,2.405,.215]],[.012]*3,sides=6)
 elif k=='goblin-cap':
  b.loft('goblin_headwear_cap','leather',[[2.46,0,-.035,.205,.19],[2.56,0,-.025,.19,.17],[2.67,.065,-.055,.13,.115],[2.69,.135,-.075,.037,.04]],sides=10)
  b.loft('goblin_headwear_cap_band','secondary',[[2.463,0,-.035,.211,.195],[2.50,0,-.035,.211,.195]],sides=10)
  b.oval('goblin_headwear_cap_clasp','metal',[0,2.493,.165],[.034,.029,.011],sides=8)
 else:
  b.loft('goblin_headwear_chief_band','leather',[[2.46,0,-.02,.214,.196],[2.50,0,-.02,.214,.196]],sides=10)
  for s in (-1,1):
   for j in range(3):
    x=s*(.065+j*.055);b.tube('goblin_headwear_bone_crest','bone',[[x,2.49,-.11],[x+s*.017,2.60+j*.027,-.14],[x+s*.012,2.66+j*.030,-.18]],[.023,.014,.001],sides=7)
  b.oval('goblin_headwear_chief_gem','accent',[0,2.50,.18],[.035,.041,.013],sides=6)
 finish(recipe,b,'goblin_headwear')

def back(b,id):
 z=-.28
 if id in ('back-goblin-tools','back-goblin-alchemy'):
  b.loft('goblin_pack_body','leather',[[1.22,0,z-.10,.17,.10],[1.29,0,z-.10,.21,.13],[1.70,0,z-.10,.21,.13],[1.77,0,z-.10,.17,.10]],sides=8)
  b.panel3('goblin_pack_flap','secondary',[[-.205,1.76,z-.24],[.205,1.76,z-.24],[.19,1.61,z-.27],[0,1.57,z-.29],[-.19,1.61,z-.27]],.025)
  for x in (-.12,.12):b.box('goblin_pack_strap','leather',[x,1.48,z-.25],[.04,.46,.023]);b.box('goblin_pack_buckle','metal',[x,1.49,z-.27],[.06,.07,.02])
  if id=='back-goblin-tools':
   for j in range(3):
    x=-.27+j*.26;b.tube('goblin_pack_tool_handle','leather',[[x,1.35,z-.13],[x,1.98-j*.08,z-.13]],[.025,.025],sides=7)
    b.box('goblin_pack_tool_head','metal',[x,1.96-j*.08,z-.13],[.16 if j==1 else .09,.07,.07])
   b.tube('goblin_pack_rope','accent',[[-.27,1.64,z-.20],[-.29,1.44,z-.28],[-.20,1.35,z-.30],[-.11,1.45,z-.28],[-.16,1.62,z-.22]],[.017]*5,sides=6)
  else:
   for x in (-.29,.29):
    b.loft('goblin_alchemy_bottle','secondary',[[1.34,x,z-.09,.047,.047],[1.38,x,z-.09,.069,.064],[1.52,x,z-.09,.06,.058],[1.57,x,z-.09,.024,.024]],sides=8)
    b.box('goblin_alchemy_cork','leather',[x,1.59,z-.09],[.05,.045,.05])
   b.loft('goblin_alchemy_tank','metal',[[1.81,0,z-.11,.092,.09],[1.98,0,z-.11,.092,.09],[2.02,0,z-.11,.055,.06]],sides=10)
   b.tube('goblin_alchemy_pipe','metal',[[.07,1.98,z-.11],[.19,2.06,z-.10],[.28,2.035,z-.10]],[.018]*3,sides=6)
 else:
  b.tube('goblin_banner_staff','leather',[[.13,1.18,z-.05],[.13,2.52,z-.05]],[.025,.024],sides=8)
  b.tube('goblin_banner_crossbar','bone',[[-.24,2.39,z-.05],[.46,2.39,z-.05]],[.025,.019],sides=7)
  b.panel3('goblin_banner_cloth','cloth',[[-.20,2.36,z-.06],[.43,2.36,z-.06],[.39,1.90,z-.09],[.25,1.99,z-.10],[.13,1.87,z-.09],[-.15,1.94,z-.08]],.025)
  for x in (-.21,.43):b.tube('goblin_banner_trophy','bone',[[x,2.35,z-.06],[x,2.16,z-.09],[x+.025,2.10,z-.09]],[.017,.021,.002],sides=7)
  b.panel3('goblin_banner_sign','accent',[[.02,2.26,z-.078],[.18,2.29,z-.078],[.27,2.17,z-.098],[.12,2.03,z-.098],[-.015,2.15,z-.086]],.008)

def fit_costume(recipe):
 from .constructor_surface_fit import mount_front
 detail=[c for c in recipe['commands'] if c['part'].startswith('goblin_') and c['material'].startswith('goblin_costume_')]
 support=[c for c in recipe['commands'] if c not in detail]
 if detail and support:mount_front(detail,support,relief=-.002)
