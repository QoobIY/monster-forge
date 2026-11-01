"""Five material-specific sculpted masks with integrated orbital recesses."""
import copy,math
import numpy as np
from tools.creature_workshop.original_constructor import OriginalSculpt,mesh_command
from tools.creature_workshop.animal_anatomy import indexed
from tools.creature_workshop.golem_reference_anatomy import solid,ribbon
from tools.creature_workshop.owned_surface_revision import front_surface
from tools.creature_workshop.family_faces import orient_faces

DESCRIPTIONS=[
 'Лавовый голем: расколотый базальтовый череп, асимметричные височные обломки, утопленные огненные глазницы, каменная переносица, сегментированная челюсть и магма в узких трещинах.',
 'Ледяной голем: вытянутая призматическая маска, острые кристаллические надбровья, глубокие узкие глаза, гранёная переносица, расщеплённая ледяная корона и прозрачные светлые плоскости.',
 'Голем пустошей: широкий выветренный песчаниковый череп, асимметричная тяжёлая бровь, впалые глазницы, сколотые скулы, истёртая переносица и горизонтальные пласты осадочной породы.',
 'Голем ветров: открытый венец из изогнутых каменных лопастей, две встречные скуловые дуги, клиновидная центральная маска, открытый затылок, узкие светящиеся глаза.',
 'Древний голем: резная храмовая маска с углублёнными глазами, ступенчатым венцом, мощными скулами, вытянутым носом, резной челюстью, узорами и очагами мха в трещинах.'
]

def mask(b,i):
 # Front lanes follow the brow, socket borders, cheek, nasal ridge and chin.
 # A separate posterior arc closes the cranium without making a flat slab.
 rows=[(2.035,.107,.073),(2.105,.158,.113),(2.195,.192,.138),(2.280,.206,.153),(2.320,.211,.144),(2.355,.212,.178),(2.425,.205,.160),(2.49,.178,.102),(2.525,.118,.058)]
 if i==1:rows=[(y,(w*.77 if y<2.28 else w*.87),z*.87) for y,w,z in rows]
 if i==2:rows=[(y,w*1.09,z*.95) for y,w,z in rows]
 if i==4:rows=[(y,w*.99,z*1.02) for y,w,z in rows]
 v=[];f=[];fronts=[]
 lanes=[-1,-.78,-.62,-.36,0,.36,.62,.78,1]
 for row,(y,w,z) in enumerate(rows):
  for lane in lanes:
   x=w*lane
   depth=z-.075*abs(lane)**2
   # Sculpt eye basins between shared upper/lower and inner/outer rims.
   if row==4 and .35<abs(lane)<.80:depth-=.041
   # Nose, philtrum and mandibular planes are continuous mask geometry.
   if row in (2,3) and abs(lane)<.37:depth+=(.072 if i in (2,4) else .045)*(1-abs(lane))
   if row==1:depth+=.023*(1-abs(lane))
   if i==0:depth+=.013*math.sin(row*1.7+lane*4);x+=.008*math.sin(row*1.2)*(1-abs(lane))
   if i==2:depth+=.009*math.sin(row*2.1+lane*3);y0=y+.008*math.sin(lane*5+row*.7)
   else:y0=y
   v.append([x,y0,depth]);fronts.append(len(v)-1)
  for lane,depth in [( .80,-.07),(.42,-.145),(0,-.175),(-.42,-.145),(-.80,-.07)]:
   v.append([w*lane,y,depth])
  if row:
   for j in range(14):
    a=(row-1)*14+j;c=(row-1)*14+(j+1)%14;d=a+14;e=c+14;f.extend([[a,c,d],[c,e,d]])
 for row in (0,len(rows)-1):
  idx=len(v);v.append(np.mean(v[row*14:(row+1)*14],axis=0));f.extend([[idx,row*14+j,row*14+(j+1)%14] for j in range(14)])
 indexed(b,'sculpted_elemental_mask','skin',v,f)
 b.commands[-1]['front_vertex_indices']=fronts
 b.commands[-1]['facial_lanes']=['temple','orbital_outer','orbital_basin','orbital_inner','nasal_ridge','mandible']
 return b.commands[-1]

def carve(b,carrier,name,mat,xy,width=.004,offset=.002):
 path=[]
 for x,y in xy:
  z=front_surface(carrier,x,y)
  if z is not None:path.append([x,y,z+offset])
 if len(path)>1:b.tube(name,mat,path,[width]*len(path),sides=5)

def sculpt(b,i):
 if i!=3:base=mask(b,i)
 else:
  # Open wind construct: rear arcs and mask are actual separate blades;
  # no solid human-like skull hidden behind the openings.
  for s in (-1,1):
   ribbon(b,'wind_cranial_arc',[(s*.045,2.06),(s*.174,2.245),(s*.20,2.435),(s*.136,2.55),(s*.035,2.54)],[.022,.053,.048,.033,.015],-.035,.13,'skin')
   solid(b,'wind_carved_half_mask',[(s*.008,2.055),(s*.105,2.205),(s*.148,2.365),(s*.065,2.443),(s*.009,2.365)],.092,.093,'bone',inset=.72,crown=.021,face_offsets=[-.014,.014,-.009,.021,-.012])
   solid(b,'wind_cheek_hook',[(s*.086,2.31),(s*.18,2.415),(s*.205,2.32),(s*.153,2.155),(s*.094,2.08)],.042,.12,'skin',face_offsets=[0,.022,-.013,.012,0])
 if i==0:
  for s in (-1,1):
   solid(b,'fractured_basalt_temple',[(s*.12,2.40),(s*.165,2.52),(s*.235,2.50),(s*.263,2.39),(s*.207,2.29)],-.014,.17,'skin',inset=.72,crown=.023,face_offsets=[0,.028,-.024,.014,-.019])
   solid(b,'basalt_jaw_fragment',[(s*.031,2.04),(s*.119,2.025),(s*.189,2.108),(s*.153,2.154),(s*.055,2.138)],.055,.14,'skin',face_offsets=[-.013,0,.019,-.012,.006])
 elif i==1:
  for s in (-1,1):
   solid(b,'ice_crystal_crown',[(s*.067,2.425),(s*.075,2.60),(s*.142,2.72),(s*.153,2.515),(s*.137,2.415)],-.018,.14,'bone',inset=.64,crown=.037,face_offsets=[-.010,.021,-.012,0,.012])
   solid(b,'ice_lateral_prism',[(s*.125,2.23),(s*.195,2.37),(s*.166,2.45),(s*.143,2.30),(s*.092,2.07)],.035,.13,'secondary',inset=.67,crown=.018)
 elif i in (2,4):
  ancient=i==4
  solid(b,'carved_lintel' if ancient else 'eroded_brow_cap',[(-.21,2.43),(-.245,2.49),(-.211,2.56),(.212,2.552),(.26,2.485),(.225,2.422)],.001,.30,'bone',inset=.88,crown=.011,face_offsets=[-.012,.009,-.020,.006,.016,-.011])
  for s in (-1,1):
   solid(b,'temple_cheek_relief' if ancient else 'sandstone_broken_cheek',[(s*.138,2.14),(s*.203,2.20),(s*.224,2.355),(s*.182,2.398),(s*.144,2.30)],.010,.18,'skin',inset=.80,crown=.012,face_offsets=[.012,-.011,.02,-.012,.006])
  if ancient:
   solid(b,'carved_chin_keystone',[(-.063,2.018),(.065,2.018),(.086,2.13),(.043,2.156),(-.059,2.135)],.073,.09,'bone',inset=.84,crown=.01)
 # Carved facial landmarks use independent quarry planes; their roots enter
 # the common mask, while the front ridges project in depth from the cranium.
 if i in (0,1,2,4):
  nose=[(-.025,2.385),(.026,2.385),(.044,2.230),(.029,2.191),(-.045,2.207)]
  if i==1:nose=[(-.016,2.414),(.020,2.414),(.031,2.259),(0,2.132),(-.035,2.264)]
  solid(b,'carved_nasal_keystone',nose,.159,.145,'bone' if i==1 else 'skin',inset=.67,crown=.032,face_offsets=[-.011,.006,.032,-.012,.015])
  for s in (-1,1):
   solid(b,'heavy_orbital_stone',[(s*.038,2.374),(s*.077,2.417),(s*.184,2.421),(s*.179,2.381),(s*.101,2.359)],.107,.128,'bone' if i in (1,4) else 'skin',inset=.78,crown=.008,face_offsets=[0,.015,-.008,.006,-.012])
   if i==0:
    solid(b,'basalt_zygomatic_shard',[(s*.065,2.254),(s*.161,2.316),(s*.191,2.24),(s*.149,2.177),(s*.067,2.184)],.092,.151,'skin',inset=.75,crown=.021,face_offsets=[-.013,.02,0,-.018,.009])
   elif i==4:
    solid(b,'carved_mandibular_column',[(s*.033,2.031),(s*.077,2.019),(s*.108,2.140),(s*.079,2.175),(s*.035,2.13)],.105,.119,'skin',inset=.81,crown=.006,face_offsets=[0,.01,-.016,.013,.006])
 carriers=[c for c in b.commands if c['material'] not in {'iris','dark'}]
 # Recesses are part of the cranium. Thin eyes lie in their floor, below brow.
 for s in (-1,1):
  eye=[(s*.065,2.331),(s*.128,2.340),(s*.121,2.322),(s*.067,2.316)]
  points=[]
  for x,y in eye:
   z=front_surface(carriers,x,y)
   if z is None:raise ValueError('Eye outside golem mask')
   points.append([x,y,z+.007])
  b.panel3('elemental_eye','iris',points,.010)
  if i==3:carve(b,carriers,'carved_orbital_brow','bone',[(s*.037,2.360),(s*.077,2.369),(s*.135,2.379)],.008,offset=.002)
 if i==0:
  for xy in [[(-.10,2.47),(-.059,2.423),(-.077,2.40),(-.052,2.37)],[(.134,2.26),(.089,2.215),(.107,2.18),(.069,2.132)],[(.012,2.50),(-.008,2.451),(.019,2.414)]]:carve(b,carriers,'molten_skull_fissure','iris',xy,.0035)
 elif i==1:
  for s in (-1,1):carve(b,carriers,'crystal_split','secondary',[(s*.054,2.43),(s*.078,2.395),(s*.044,2.26),(s*.063,2.19)],.003)
 elif i==2:
  for yy in (2.405,2.252,2.174):carve(b,carriers,'sedimentary_face_layer','shadow',[(-.17,yy-.005),(-.105,yy),(-.035,yy-.008),(.055,yy+.002),(.16,yy-.014)],.003)
 elif i==4:
  for s in (-1,1):
   carve(b,carriers,'temple_carved_spiral','shadow',[(s*.153,2.39),(s*.173,2.36),(s*.172,2.23),(s*.139,2.205),(s*.127,2.226),(s*.142,2.246)],.004)
   carve(b,carriers,'carved_crown_glyph','shadow',[(s*.053,2.49),(s*.07,2.52),(s*.087,2.49),(s*.07,2.475),(s*.053,2.49)],.003)
  b.palette['moss']='69794b'
  for xy in [[(-.19,2.40),(-.178,2.374),(-.186,2.345)],[(.151,2.135),(.138,2.116),(.129,2.13)]]:carve(b,carriers,'moss_in_mask_crack','moss',xy,.009)
 if i!=3:carve(b,carriers,'stone_mouth_fissure','dark',[(-.084,2.142),(-.043,2.151),(0,2.142),(.045,2.152),(.088,2.139)],.003)

def apply(recipe,settings,slot):
 if recipe.get('species_design',{}).get('anatomy')=='water':return
 if slot!='head' or settings['race']!='golem':return
 variant=int(settings['face'].rsplit('-',1)[-1])-1
 palette=copy.deepcopy(recipe['palette']);palette.setdefault('hair','49433a');palette.setdefault('skin','807365')
 b=OriginalSculpt({'id':'elemental-mask-v1','palette':palette});b.palette.update(palette);b.slot='head';b.stage=2;sculpt(b,variant)
 for j,c in enumerate(b.commands):
  v,f=mesh_command(c);c.update(op='indexed_mesh',vertices=v.tolist(),faces=orient_faces(v,f).tolist(),id=f'golem-face-{variant}-{j}',ai_description_ru=DESCRIPTIONS[variant],native_anatomy='golem')
 recipe['commands']=b.commands;recipe['palette'].update(b.palette)
 recipe['face_revision']={'schema_version':1,'id':'golem-face-v1','variant':variant,'description_ru':DESCRIPTIONS[variant]}
