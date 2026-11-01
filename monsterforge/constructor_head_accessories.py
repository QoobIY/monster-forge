"""Refined numeric head ornaments authored on the selected skull and hair."""
import math
import numpy as np
from .paths import ROOT
from .constructor_decor import sculpt
from .constructor_portraits import freeze
from .constructor_face_fit import surfaces,front_depth
from .constructor_headwear_fit import hair_support
from .constructor_surface_fit import triangles,radial_hit
from .constructor_armor_details import loop
from tools.creature_workshop.geometry import mesh
from tools.creature_workshop.family_faces import orient_faces
SOURCE=ROOT/'media/constructor/head_accessories/v2'
LABELS=('Обруч с оправой','Зубчатая корона','Ажурная диадема','Очки механика','Серьги с подвесками','Обруч с перьями','Налобный амулет','Роговой обруч','Лавровый венок','Полумаска стража')
DETAILS=(
 'Обруч с толщиной и двумя окантовками, центральная полая оправа, гранёный камень и боковые застёжки.',
 'Замкнутая корона с широким ободом, семь отдельных листовидных зубцов, оправы и гранёные вставки.',
 'Диадема с тонким ободом, тремя ажурными дугами, центральной подвеской и камнями в оправах.',
 'Защитные очки: объёмные полые оправы, мягкие прилегающие наглазники, выпуклые линзы, перемычка, шарниры и затылочный ремень.',
 'Серьги крепятся к мочкам выбранных ушей; замкнутые кольца, соединительные звенья, оправы и каплевидные подвески.',
 'Кожаный обруч с крепёжной розеткой на виске и тремя изогнутыми объёмными перьями, направленными вверх и назад.',
 'Налобный амулет на тонком обруче: вертикальная подвеска, многослойная полая оправа, гранёный камень и лапки крепления.',
 'Парные изогнутые декоративные рога на обруче; металлические гнёзда у оснований и обхватывающие накладки.',
 'Венок с парными ветвями и шестнадцатью объёмными листьями с поднятым центральным ребром, направленными вдоль обруча.',
 'Полумаска с настоящими открытыми глазницами, прилегающими к лицу скуловыми краями, носовой перемычкой и затылочным ремешком.')

def solid(b,name,v,f,mat):
 v=np.asarray(v);b.commands.append(dict(id=name+'-'+str(len(b.commands)),part='refined_headwear_'+name,slot='head',stage=4,material=mat,op='indexed_mesh',vertices=v.tolist(),faces=orient_faces(v,np.asarray(f)).tolist()))

def apply(recipe,settings):
 number=settings['reference_parts']['headwear']
 if not number:return
 skin=surfaces(recipe)
 if not skin:
  skin=[c for c in recipe['commands'] if c['material'].endswith('skull_bone') and not any(t in c['part'] for t in ('tooth','teeth','cervical','hair'))]
 if not skin:return
 recipe['commands']=[c for c in recipe['commands'] if not c['part'].startswith('atlas_headwear_')]
 vskin=np.concatenate([mesh(c)[0] for c in skin]);low,high=vskin.min(0),vskin.max(0);cz=(low[2]+high[2])*.5
 irises=[mesh(c)[0].mean(0) for c in recipe['commands'] if ('iris' in c['part'] or c['part']=='soul_eye') and 'hair' not in c['part']]
 eye=float(np.mean([p[1] for p in irises])) if irises else low[1]+(high[1]-low[1])*.57
 hair=hair_support(recipe);support=triangles(skin+hair);width=max(.16,float(np.abs(vskin[:,0]).max()));depth=max(.14,float((high[2]-low[2])*.5))
 b=sculpt(settings);b.slot='head';b.stage=4;b.palette.update(bone='d2c4a5',glass='608b96')
 if number==9 and not settings['colors']['secondary']:b.palette['secondary']='70845c'
 yband=min(eye+.155,high[1]-.10)
 def point(a,y,clear=.012):
  d=np.array([math.sin(a),0,math.cos(a)]);origin=np.array([0,y,cz]);r=radial_hit(support,origin,d)
  if r is None:r=1/math.sqrt((d[0]/width)**2+(d[2]/depth)**2)
  return origin+d*(r+clear)
 def band(y,height=.033,mat='metal',open_back=False):
  angles=np.linspace(.96,2*math.pi-.96,21) if open_back else np.linspace(0,2*math.pi,24,endpoint=False)
  count=len(angles);v=[];f=[]
  for off in (.004,.020):
   for dy in (-height/2,height/2):
    for a in angles:v.append(point(a,y+dy,off))
  end=count-1 if open_back else count
  for j in range(end):
   k=(j+1)%count
   for row,other in ((0,count),(2*count,3*count),(0,2*count),(count,3*count)):
    a=row+j;c=row+k;d=other+j;e=other+k;f.extend([[a,c,e],[a,e,d]])
  if open_back:
   for j in (0,count-1):
    a=j;c=count+j;d=2*count+j;e=3*count+j;f.extend([[a,c,e],[a,e,d]])
  solid(b,'band',v,f,mat)
  return angles
 def front_assembly(a,y,fn):
  start=len(b.commands);p=point(a,y,.025);rotation=np.array([[math.cos(a),0,math.sin(a)],[0,1,0],[-math.sin(a),0,math.cos(a)]])
  fn()
  for c in b.commands[start:]:
   v,f=mesh(c);v=v@rotation.T+p;c.update(op='indexed_mesh',vertices=v.tolist(),faces=orient_faces(v,f).tolist(),attachment_point_metres=p.tolist())
 def gem(rx=.032,ry=.042):
  loop(b,'refined_headwear_setting','accent',[0,0,.012],rx+ .008,ry+.008,.006)
  # Flattened octahedral stone with a broad crown and a faceted raised centre.
  v=[[0,ry,.018],[rx,0,.018],[0,-ry,.018],[-rx,0,.018],[0,0,.048],[0,0,.005]]
  f=[]
  for j in range(4):f.extend([[j,(j+1)%4,4],[j,5,(j+1)%4]])
  solid(b,'gem',v,f,'secondary')
  for x in (-rx,rx):b.tube('refined_headwear_gem_claw','metal',[[x,0,.011],[x*.87,0,.026]],[.004,.003],sides=5)
 def trim(y):
  p=[point(a,y,.023).tolist() for a in np.linspace(0,2*math.pi,25)];b.tube('refined_headwear_band_edge','accent',p,[.0035]*len(p),sides=5)
 def on_skin(xy,clear=.007):
  z=front_depth(skin,np.asarray(xy));out=[]
  for p,zz in zip(xy,z):
   if not np.isfinite(zz):zz=vskin[np.argmin(np.linalg.norm(vskin[:,:2]-p,axis=1)),2]
   out.append([*p,zz+clear])
  return np.asarray(out)
 def eye_ring(cx,cy,outer,inner,mat,front=None):
  v=[];f=[];N=12
  for back in (False,True):
   for rx,ry in (outer,inner):
    xy=np.asarray([[cx+rx*math.cos(a),cy+ry*math.sin(a)] for a in np.linspace(0,2*math.pi,N,endpoint=False)])
    q=on_skin(xy,.006 if back else .020)
    if front is not None and not back:q[:,2]=front
    v.extend(q)
  for j in range(N):
   k=(j+1)%N
   for a,c in ((0,N),(2*N,3*N),(0,2*N),(N,3*N)):f.extend([[a+j,a+k,c+k],[a+j,c+k,c+j]])
  solid(b,'eye_pad' if front is not None else 'mask_eye_frame',v,f,mat)
 if number in (1,2,3,6,7,8,9):band(yband,.057 if number==2 else .015 if number==9 else .029,'leather' if number==6 else 'accent' if number==9 else 'metal')
 if number in (1,2):
  trim(yband+.020 if number==2 else yband+.012);trim(yband-.020 if number==2 else yband-.012)
 if number==1:
  front_assembly(0,yband,lambda:gem(.026,.030))
  for a in (-.65,.65):front_assembly(a,yband,lambda:b.box('refined_headwear_clasp','accent',[0,0,.009],[.025,.035,.012]))
 elif number==2:
  for a in np.linspace(0,2*math.pi,7,endpoint=False):
   length=.125 if abs(math.atan2(math.sin(a),math.cos(a)))<.6 else .080
   p=point(a,yband+.022,.021);left=point(a-.15,yband+.024,.021);right=point(a+.15,yband+.024,.021)
   outline=np.array([left,p+[0,length*.72,0],p+[0,length,.012],right,p+[0,-.007,0]])
   b.panel3('refined_headwear_crown_leaf','metal',outline.tolist(),.016)
   front_assembly(a,yband+.031,lambda:gem(.014,.019))
 elif number==3:
  for a,widtha,height in ((0,.72,.10),(-.52,.40,.062),(.52,.40,.062)):
   path=[point(a+t,yband+height*math.sin(math.pi*(t+widtha)/(2*widtha)),.027).tolist() for t in np.linspace(-widtha,widtha,9)]
   b.tube('refined_headwear_tiara_arch','accent',path,[.006]*len(path),sides=6)
  front_assembly(0,yband+.045,lambda:gem(.024,.034))
 elif number==4:
  band(eye+.005,.035,'leather',open_back=True)
  centres=[]
  for sign in (-1,1):
   ps=[p for p in irises if p[0]*sign>0];p=np.mean(ps,axis=0) if ps else np.array([sign*width*.44,eye,high[2]])
   cx,cy=p[:2];xy=np.array([[cx+x,cy+y] for x in (-.075,.075) for y in (-.047,.047)]);z=max(on_skin(xy)[:,2].max(),p[2])+.026
   eye_ring(cx,cy,(.075,.049),(.050,.030),'leather',front=z)
   loop(b,'refined_headwear_goggle_rim','metal',[cx,cy,z+.007],.058,.038,.008)
   b.oval('refined_headwear_goggle_lens','glass',[cx,cy,z+.011],[.049,.029,.009],sides=12)
   b.tube('refined_headwear_lens_glint','accent',[[cx-.017,cy+.014,z+.020],[cx+.012,cy+.014,z+.020]],[.0025,.0025],sides=4)
   hinge=np.array([cx+sign*.068,cy,z]);end=point(sign*.96,eye+.005,.025)
   b.tube('refined_headwear_goggle_arm','metal',[hinge.tolist(),end.tolist()],[.011,.011],sides=6);b.oval('refined_headwear_goggle_hinge','accent',hinge.tolist(),[.010,.013,.009],sides=7);centres.append([cx,cy,z])
  a,c=np.asarray(centres);b.tube('refined_headwear_goggle_bridge','metal',[(a+[.040,.009,0]).tolist(),[0,eye+.034,max(a[2],c[2])],(c+[-.040,.009,0]).tolist()],[.007]*3,sides=6)
 elif number==5:
  ears=[mesh(c)[0] for c in recipe['commands'] if 'ear' in c['part'] and not any(t in c['part'] for t in ('hair','beard','headwear'))]
  for sign in (-1,1):
   side=[v for v in ears if v[:,0].mean()*sign>0]
   if side:
    v=np.concatenate(side);lobe=v[np.abs(v[:,1]-v[:,1].min())<.025].mean(0);lobe[2]+=.012
   else:lobe=np.array([sign*(width+.020),eye-.045,cz+.022])
   b.oval('refined_headwear_earring_stud','accent',lobe.tolist(),[.009,.010,.008],sides=7)
   loop(b,'refined_headwear_earring_link','metal',(lobe+[0,-.017,0]).tolist(),.009,.014,.0035)
   centre=lobe+[0,-.078,0];loop(b,'refined_headwear_earring_hoop','accent',centre.tolist(),.032,.048,.005)
   start=len(b.commands);gem(.020,.029)
   for c in b.commands[start:]:
    v,f=mesh(c);c.update(op='indexed_mesh',vertices=(v+centre+[0,-.056,0]).tolist(),faces=f.tolist())
 elif number==6:
  from tools.creature_workshop.feather_wings import feather
  p=point(-.92,yband+.01,.026);b.oval('refined_headwear_plume_mount','accent',p.tolist(),[.025,.032,.016],sides=8)
  for j in range(3):
   root=p+[0,j*.008,-j*.012];tip=root+[-.06-j*.025,.26+j*.046,-.04-j*.045]
   feather(b,'refined_headwear_plume','secondary' if j%2 else 'accent',root,tip,.080-j*.01,bend=-.015)
 elif number==7:
  def amulet():
   b.tube('refined_headwear_pendant_link','accent',[[0,.017,.010],[0,-.034,.015]],[.006,.006],sides=6)
   start=len(b.commands);gem(.031,.049)
   for c in b.commands[start:]:
    v,f=mesh(c);c.update(op='indexed_mesh',vertices=(v+[0,-.080,0]).tolist(),faces=f.tolist())
  front_assembly(0,yband,amulet)
 elif number==8:
  for sign in (-1,1):
   p=point(sign*.95,yband+.019,.025);path=np.array([p,p+[sign*.040,.07,-.025],p+[sign*.072,.13,-.080],p+[sign*.085,.17,-.135],p+[sign*.079,.19,-.17]])
   b.tube('refined_headwear_swept_horn','bone',path.tolist(),[.044,.037,.026,.014,.001],sides=8)
   for j in (0,1):b.tube('refined_headwear_horn_cuff','metal',path[j:j+2].tolist(),[.048-j*.009,.041-j*.009],sides=8)
 elif number==9:
  from tools.creature_workshop.feather_wings import feather
  for sign in (-1,1):
   stem=[point(sign*a,yband+.030,.027).tolist() for a in np.linspace(.12,2.0,13)];b.tube('refined_headwear_laurel_branch','accent',stem,[.006]*len(stem),sides=5)
   for j,a in enumerate(np.linspace(.25,1.95,8)):
    p=point(sign*a,yband+.026,.030);q=point(sign*(a-.22),yband+.046+(.021 if j%2 else -.008),.035)
    feather(b,'refined_headwear_laurel_leaf','secondary',p,q,.042,bend=sign*.004)
 elif number==10:
  band(eye+.033,.020,'leather',open_back=True)
  for sign in (-1,1):
   ps=[p for p in irises if p[0]*sign>0];p=np.mean(ps,axis=0) if ps else np.array([sign*width*.44,eye,high[2]])
   eye_ring(p[0],p[1],(.092,.076),(.052*settings['eye_size'],.032*settings['eye_size']),'metal')
  # Segmented bridge follows the real nose/forehead planes, retaining thickness.
  xy=np.asarray([[-width*.22,eye+.05],[0,eye+.075],[width*.22,eye+.05],[width*.22,eye+.019],[0,eye+.013],[-width*.22,eye+.019]])
  q=on_skin(xy,.020);back=on_skin(xy,.006);vv=np.concatenate([q,back]);ff=[[0,1,4],[0,4,5],[1,2,3],[1,3,4],[6,10,7],[6,11,10],[7,9,8],[7,10,9]]
  for j in range(6):k=(j+1)%6;ff.extend([[j,k,6+k],[j,6+k,6+j]])
  solid(b,'mask_bridge',vv,ff,'metal')
 commands,palette=freeze(b,'head_accessory');recipe['palette'].update(palette)
 for c in commands:c.update(slot='head',purpose=DETAILS[number-1],head_accessory_revision={'schema_version':1,'variant':number,'label_ru':LABELS[number-1]})
 recipe['commands'].extend(commands);recipe['commands'].sort(key=lambda c:c['stage'])
 recipe['head_accessory_revision']={'schema_version':1,'variant':number,'label_ru':LABELS[number-1],'description_ru':DETAILS[number-1],'method':'authored solid ornament on selected skull, eyes, ears and hair surfaces'}
