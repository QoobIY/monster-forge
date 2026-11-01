"""Authored shoulder shells and waist assemblies fitted to actual selected clothing."""
import hashlib,math
from pathlib import Path
import numpy as np
from .paths import ROOT
from .constructor_decor import sculpt
from .constructor_portraits import freeze
from .constructor_surface_fit import triangles,radial_hit,torso_support
from tools.creature_workshop.geometry import mesh
from tools.creature_workshop.family_faces import orient_faces
from tools.creature_workshop.accessory_details import frame

SOURCE=ROOT/'media/constructor/armor_details/v2'
SHOULDERS=('plates','layered','horns','spikes','feathers','fur','gems','scrolls','wings','asymmetric')
BELTS=('plain','pouches','tools','chain','gems','sash','double','flasks','scrolls','book')
SHOULDER_DESCRIPTIONS={
 'plates':'Кованый наплечник: выпуклый полый купол с фасками, толстая окантовка, шарнирная нижняя пластина и заклёпки.',
 'layered':'Составной наплечник из трёх перекрывающихся подвижных пластин с отдельными ободами и боковыми заклёпками.',
 'horns':'Наплечник с костяными рогами: кованый купол, металлические гнёзда у оснований и изогнутые рога.',
 'spikes':'Шипованный наплечник: металлический купол, усиленные гнёзда и разной длины наклонённые шипы.',
 'feathers':'Пернатый наплечник: кожаная чашка и два ряда перекрывающихся объёмных перьев с рёбрами.',
 'fur':'Меховой наплечник: цельная шкурная чашка с заострённым краем по росту меха, ремень и застёжка.',
 'gems':'Наплечник с кристаллами: полый металлический купол, оправы и гранёные кристаллы разного размера.',
 'scrolls':'Наплечник писца: кожаная чашка, два закреплённых свитка, полые торцы, ремешки и застёжки.',
 'wings':'Крылатый наплечник: металлическое основание, веер длинных перьев и отдельный ряд кроющих перьев.',
 'asymmetric':'Один кованый наплечник с шарнирной нижней пластиной на левой руке; правая рука свободна.',
}
BELT_DESCRIPTIONS={
 'plain':'Кожаный пояс: реальная толщина ремня, полая пряжка с язычком, продетый хвост, отверстия и держатели.',
 'pouches':'Пояс с объёмными подсумками: выпуклые боковины, загнутые клапаны, отдельные петли, замки и усиленные края.',
 'tools':'Рабочий пояс: кожаные петли, молоток с головкой, клещи с раскрытым концом, нож в ножнах и заклёпки креплений.',
 'chain':'Пояс с подвесной цепью: настоящие полые звенья в чередующихся плоскостях и металлические крепёжные кольца.',
 'gems':'Пояс с камнями: гранёные вставки в полых оправах, металлические лапки и широкий кожаный ремень.',
 'sash':'Тканевый кушак: объёмная широкая лента, перекрывающаяся складка, узел и два свисающих конца с окантовкой.',
 'double':'Двойной пояс: два независимых ремня по талии, две полые пряжки и вертикальные кожаные соединения.',
 'flasks':'Пояс алхимика: флаконы с плечиками, узкими горлышками, пробками и отдельными кожаными креплениями.',
 'scrolls':'Пояс со свитками: объёмная бумажная намотка, открытые торцы, кожаные петли и печати.',
 'book':'Пояс с книгой: две обложки, отдельный блок страниц и корешок, оборачивающий ремень, замок и подвес.',
 'medallion':'Парадный пояс: полая пряжка, медальон с многослойным ободом, центральным рельефом и боковыми цепочками.'}


def solid(b,name,v,f,mat,purpose='Объёмная авторская деталь с толщиной, фасками и читаемым креплением.'):
 b.commands.append(dict(id=name+'-'+str(len(b.commands)),part=name,slot=b.slot,stage=4,material=mat,op='indexed_mesh',vertices=np.asarray(v).tolist(),faces=orient_faces(np.asarray(v),np.asarray(f)).tolist(),purpose=purpose))


def loop(b,name,mat,centre,rx,ry,tube=.007,rotation=0):
 # Actual hollow link, closed along both parametric directions; no filled oval.
 centre=np.asarray(centre);v=[];f=[];N=12;K=5
 rot=np.array([[math.cos(rotation),0,math.sin(rotation)],[0,1,0],[-math.sin(rotation),0,math.cos(rotation)]])
 for j,a in enumerate(np.linspace(0,2*math.pi,N,endpoint=False)):
  p=np.array([math.cos(a)*rx,math.sin(a)*ry,0]);normal=np.array([math.cos(a),math.sin(a),0])
  for q in np.linspace(0,2*math.pi,K,endpoint=False):v.append(centre+rot@(p+normal*math.cos(q)*tube+np.array([0,0,math.sin(q)*tube])))
 for j in range(N):
  for k in range(K):
   a=j*K+k;c=j*K+(k+1)%K;d=((j+1)%N)*K+k;e=((j+1)%N)*K+(k+1)%K;f.extend([[a,c,d],[c,e,d]])
 solid(b,name,v,f,mat,'Полый замкнутый обод/звено, сохраняющий просвет.')


def pipe(b,name,mat,start,end,outer=.034,inner=.020):
 start=np.asarray(start);end=np.asarray(end);axis=end-start;axis/=np.linalg.norm(axis)
 ref=np.array([0.,0.,1.]) if abs(axis[2])<.85 else np.array([0.,1.,0.]);u=np.cross(axis,ref);u/=np.linalg.norm(u);w=np.cross(axis,u)
 N=10;v=[];f=[]
 for point,r in ((start,outer),(end,outer),(start,inner),(end,inner)):
  for a in np.linspace(0,2*math.pi,N,endpoint=False):v.append(point+r*(u*math.cos(a)+w*math.sin(a)))
 for k in range(N):
  j=(k+1)%N
  for a,c in ((0,N),(2*N,3*N),(0,2*N),(N,3*N)):f.extend([[a+k,a+j,c+j],[a+k,c+j,c+k]])
 solid(b,name,v,f,mat,'Настоящая полая намотка свитка с открытыми торцами и толщиной бумаги.')


def shoulder(b,kind,slot,support):
 s=-1 if slot=='left_arm' else 1
 if kind=='asymmetric' and s==1:return
 from .constructor_knees import world_bind
 bind=world_bind();origin=np.array(bind[slot.split('_')[0]+'_shoulder']);axis=np.array(bind[slot.split('_')[0]+'_elbow'])-origin;axis/=np.linalg.norm(axis)
 front=np.array([0.,0.,1.]);front-=axis*np.dot(front,axis);front/=np.linalg.norm(front)
 lateral=np.cross(front,axis);lateral*=s
 tri=triangles(support)
 def location(t,a,extra=.025,fallback=.145):
  o=origin+axis*t;direction=front*math.cos(a)+lateral*math.sin(a);r=radial_hit(tri,o,direction)
  return o+direction*((r if r is not None else fallback)+extra)
 def shell(name,start,end,metal='metal',scallop=False):
  cols=12;v=[];rowt=[start,start+.035,(start+end)*.55,end]
  for inset in (False,True):
   for j,t in enumerate(rowt):
    for k,a in enumerate(np.linspace(0,2*math.pi,cols,endpoint=False)):
     # A rigid raised ridge flows down into the articulated hem.
     fallback=[.055,.105,.160,.145][j]
     off=.004 if inset else .023+(.012 if j in (1,2) else 0)+.015*max(math.sin(a),0)
     q=location(t,a,off,fallback)
     if scallop and j==3:q+=axis*(.018 if k%2 else -.010)
     v.append(q)
  v=np.asarray(v);n=4*cols;f=[]
  for row in range(3):
   for k in range(cols):
    a=row*cols+k;c=row*cols+(k+1)%cols;d=a+cols;e=c+cols
    f.extend([[a,c,d],[c,e,d],[n+a,n+d,n+c],[n+c,n+d,n+e]])
  for row in (3,):
   for k in range(cols):
    a=row*cols+k;c=row*cols+(k+1)%cols;f.extend([[a,n+a,n+c],[a,n+c,c]])
  if 'cup' in name or name.endswith('hide'):
   top=len(v);v=np.concatenate([v,[origin+axis*(start-.075),origin+axis*(start-.055)]])
   for k in range(cols):
    j=(k+1)%cols;f.extend([[top,k,j],[top+1,n+j,n+k]])
  else:
   for k in range(cols):
    j=(k+1)%cols;f.extend([[k,n+k,n+j],[k,n+j,j]])
  solid(b,name,v,f,metal,'Замкнутый полый кованый купол с внутренней стенкой и толщиной; посажен на объём выбранного рукава.')
  rim=[location(end,a,.034) for a in np.linspace(0,2*math.pi,cols+1)]
  b.tube('armor_shoulder_rolled_rim','accent',[q.tolist() for q in rim],[.0045]*len(rim),sides=5)
  for a in (-.62,.62,2.40,3.88):
   p=location((start+end)*.6,a,.045);b.oval('armor_shoulder_rivet','accent',p.tolist(),[.012,.012,.009],sides=7)
 if kind=='fur':
  shell('armor_shoulder_hide',-.085,.245,'secondary',scallop=True)
  # The growth-direction silhouette belongs to the hide itself, not blobs on it.
  for c in b.commands:
   if c['part']=='armor_shoulder_hide':
    v=np.asarray(c['vertices']);n=48
    for offset in (0,n):
     for k in range(12):v[offset+36+k]+=axis*(.05 if k%2 else -.025)
    c['vertices']=v.tolist()
 elif kind in ('feathers','wings','scrolls'):
  shell('armor_shoulder_leather_cup',-.07,.16,'leather')
 else:
  shell('armor_shoulder_forged_cup',-.095,.165)
  if kind in ('plates','asymmetric','layered'):
   shell('armor_shoulder_articulated_lame',.14,.215)
   if kind=='layered':shell('armor_shoulder_lower_lame',.205,.27)
 for a in (-.65,.65):
  p=location(.15,a,.038);q=location(.245 if kind=='layered' else .21,a,.040)
  b.tube('armor_shoulder_hinge_strap','leather',[p.tolist(),q.tolist()],[.014,.014],sides=6)
  b.oval('armor_shoulder_hinge_pin','metal',p.tolist(),[.014,.014,.010],sides=7)
 if kind in ('horns','spikes'):
  for j in range(3):
   a=.65+j*.47;p=location(.025,a,.04);direction=(front*math.cos(a)+lateral*math.sin(a));tip=p+direction*(.10+j*.025)-axis*.065
   b.tube('armor_shoulder_spike_socket','metal',[p.tolist(),(p+direction*.022).tolist()],[.033,.026],sides=8)
   b.tube('armor_shoulder_horn' if kind=='horns' else 'armor_shoulder_spike','secondary' if kind=='horns' else 'metal',[p.tolist(),(p+direction*.07-axis*.035).tolist(),tip.tolist(),(tip+axis*.025+direction*.024).tolist()],[.026,.020,.010,.001],sides=7)
 elif kind in ('feathers','wings'):
  from tools.creature_workshop.feather_wings import feather
  for row in (0,1):
   for j in range(4):
    p=location(.025+row*.05,-.5+j*.36,.046+row*.023)
    tip=p+axis*(.21+(j%2)*.035 if kind=='feathers' else .30+j*.03)+lateral*(.025+j*.010)
    feather(b,'armor_shoulder_feather','secondary' if row==0 else 'accent',p,tip,.082 if row==0 else .060,bend=s*.013)
 elif kind=='gems':
  for j in range(3):
   a=.4+j*.6;p=location(.015,a,.035);d=front*math.cos(a)+lateral*math.sin(a)
   b.tube('armor_shoulder_crystal_setting','accent',[p.tolist(),(p+d*.027).tolist()],[.039,.039],sides=8)
   b.tube('armor_shoulder_crystal','secondary',[p.tolist(),(p+d*(.07+j*.024)).tolist(),(p+d*(.14+j*.035)-axis*.025).tolist()],[.031,.037,.001],sides=5)
 elif kind=='scrolls':
  for j in range(2):
   p=location(.05,-.50+j*.75,.056);q=p+axis*.16
   pipe(b,'armor_shoulder_scroll','accent',p,q)
   for t in (.3,.72):
    c=p+(q-p)*t;b.tube('armor_shoulder_scroll_tie','leather',[(c-axis*.013).tolist(),(c+axis*.013).tolist()],[.038,.038],sides=8)


def belt(b,kind,support):
 tri=triangles(support);vertices=np.concatenate([mesh(c)[0] for c in support])
 structural=[c for c in support if c['part'].endswith(('tailored_body','tunic_body','torso_body'))]
 if structural:vertices=triangles(structural).reshape(-1,3)
 def p(a,y=1.115,clear=.0):
  d=np.array([math.sin(a),0,math.cos(a)]);o=np.array([0.,y,0.]);r=radial_hit(tri,o,d)
  if r is None:
   nearby=vertices[np.abs(vertices[:,1]-y)<.085]
   if len(nearby)<4:nearby=vertices[np.argsort(abs(vertices[:,1]-y))[:16]]
   rx=max(.13,float(np.abs(nearby[:,0]).max()));rz=max(.12,float(np.abs(nearby[:,2]).max()))
   r=1/math.sqrt((d[0]/rx)**2+(d[2]/rz)**2)
  return o+d*(r+clear)
 def band(y,height,mat='leather'):
  cols=20;v=[];f=[]
  for clear in (-.001,.014):
   for yy in (y-height*.5,y+height*.5):
    for a in np.linspace(0,2*math.pi,cols,endpoint=False):v.append(p(a,yy,clear))
  for k in range(cols):
   j=(k+1)%cols
   for a,c in ((0,cols),(2*cols,3*cols),(0,2*cols),(cols,3*cols)):f.extend([[a+k,a+j,c+j],[a+k,c+j,c+k]])
  solid(b,'armor_belt_strap',v,f,mat,'Ремень с настоящей толщиной: внутренний и внешний контуры рассчитаны по выбранной одежде.')
 def place(a,y,name,fn):
  start=len(b.commands);anchor=p(a,y,.016);fn()
  rotation=np.array([[math.cos(a),0,math.sin(a)],[0,1,0],[-math.sin(a),0,math.cos(a)]])
  for c in b.commands[start:]:
   v,f=mesh(c);soliddata=(v@rotation.T+anchor);c.update(op='indexed_mesh',vertices=soliddata.tolist(),faces=orient_faces(soliddata,f).tolist(),attachment_point_metres=anchor.tolist(),attachment_method='Rigid local assembly attached to belt surface; depth ordering retained')
 def buckle():
  frame(b,'armor_belt_buckle','metal',[0,0,.020],.108,.081,.013,.018)
  b.tube('armor_belt_buckle_prong','metal',[[-.037,0,.033],[.040,0,.033]],[.005]*2,sides=6)
  b.box('armor_belt_threaded_tail','leather',[.057,0,.012],[.115,.056,.015])
  for x in (.054,.082,.11):b.oval('armor_belt_punched_hole','dark',[x,0,.021],[.005,.005,.002],sides=6)
  b.box('armor_belt_keeper','metal',[.112,0,.026],[.015,.069,.015])
 band(1.115,.067 if kind not in ('sash','gems') else .105,'secondary' if kind=='sash' else 'leather')
 place(0,1.115,'buckle',buckle)
 if kind=='double':
  band(1.005,.057);place(-.18,1.005,'second-buckle',buckle)
  for a in (-.8,.8,2.2,4.0):
   start=p(a,1.01,.026);end=p(a,1.13,.025);b.tube('armor_belt_vertical_connector','leather',[start.tolist(),end.tolist()],[.013,.013],sides=6)
 # Stitch rows and keepers wrap around the fitted waist rather than float in front.
 for a in (-1.0,-.65,.60,1.,2.25,3.8):
  def keeper():b.box('armor_belt_keeper','leather',[0,0,.020],[.018,.09,.013]);b.oval('armor_belt_keeper_rivet','metal',[0,.020,.030],[.005,.006,.004],sides=6)
  place(a,1.115,'keeper',keeper)
 def pouch():
  b.loft('armor_belt_pouch','leather',[[-.20,0,.056,.051,.035],[-.165,0,.056,.077,.053],[-.04,0,.050,.073,.045],[.020,0,.036,.060,.035]],sides=8)
  b.panel3('armor_belt_pouch_flap','secondary',[[-.073,.020,.081],[.073,.020,.081],[.071,-.055,.106],[.035,-.096,.114],[-.035,-.096,.114],[-.071,-.055,.106]],.018)
  frame(b,'armor_belt_pouch_clasp','metal',[0,-.066,.127],.036,.038,.006,.012)
  for x in (-.049,.049):b.tube('armor_belt_pouch_suspension','leather',[[x,.04,.016],[x,-.015,.050],[x,-.059,.102]],[.009]*3,sides=6)
  b.tube('armor_belt_pouch_seam','accent',[[-.062,-.055,.107],[-.064,-.15,.108],[0,-.182,.114],[.064,-.15,.108],[.062,-.055,.107]],[.0035]*5,sides=5)
 if kind=='pouches':
  for a in (-.72,.72):place(a,1.085,'pouch',pouch)
 elif kind=='tools':
  def tools():
   for x in (-.073,0,.075):
    frame(b,'armor_belt_tool_loop','leather',[x,-.025,.047],.050,.06,.008,.023)
    b.tube('armor_belt_tool_handle','leather',[[x,.050,.061],[x,-.180,.061]],[.013,.013],sides=7)
   b.box('armor_belt_hammer_head','metal',[-.073,.068,.061],[.11,.055,.055])
   for s in (-1,1):b.tube('armor_belt_plier_jaw','metal',[[0,.065,.061],[s*.025,.105,.061],[s*.018,.14,.061]],[.010,.007,.005],sides=6)
   b.loft('armor_belt_knife_sheath','leather',[[-.24,.075,.065,.014,.020],[-.09,.075,.065,.030,.023],[-.045,.075,.065,.026,.022]],sides=6)
  place(-.85,1.115,'tools',tools);place(.9,1.08,'pouch',pouch)
 elif kind in ('chain','medallion'):
  for j in range(17):
   a=-.82+j*.1025;y=1.095-.082*math.sin(j*math.pi/16);q=p(a,y,.035);loop(b,'armor_belt_chain_link','metal',q,.026,.018,.0055,rotation=math.pi/4 if j%2 else -math.pi/4)
  for a in (-.82,.82):loop(b,'armor_belt_chain_anchor','metal',p(a,1.10,.026),.020,.023,.006)
  if kind=='medallion':
   def medallion():
    loop(b,'armor_belt_medallion_rim','metal',[0,-.06,.043],.060,.068,.010)
    b.oval('armor_belt_medallion_inset','secondary',[0,-.060,.035],[.05,.057,.018],sides=10)
    b.panel3('armor_belt_medallion_relief','accent',[[0,-.018,.061],[.028,-.060,.065],[0,-.103,.061],[-.028,-.060,.065]],.012)
   place(0,1.105,'medallion',medallion)
 elif kind=='gems':
  for a in (-.60,.60):
   def gem():
    frame(b,'armor_belt_gem_setting','metal',[0,0,.031],.082,.096,.009,.024)
    b.oval('armor_belt_gem','secondary',[0,0,.043],[.031,.038,.029],sides=6)
    for x in (-.029,.029):b.box('armor_belt_gem_claw','accent',[x,0,.064],[.010,.020,.025])
   place(a,1.115,'gem',gem)
 elif kind=='sash':
  def sash():
   b.loft('armor_belt_sash_knot','secondary',[[-.046,0,.035,.040,.025],[0,0,.044,.055,.038],[.045,0,.035,.035,.025]],sides=8)
   for s in (-1,1):
    pts=[[s*.024,-.005,.029],[s*.089,-.044,.032],[s*.109,-.27-(.09 if s==1 else 0),.074],[s*.060,-.33-(.09 if s==1 else 0),.078],[s*.023,-.17,.055]]
    b.panel3('armor_belt_sash_tail','secondary',pts,.026);b.tube('armor_belt_sash_border','accent',pts[1:4],[.004]*3,sides=5)
   b.tube('armor_belt_sash_fold','cloth',[[-.025,.02,.073],[0,.008,.087],[.03,-.02,.073]],[.008]*3,sides=6)
  place(.58,1.115,'sash',sash)
 elif kind=='flasks':
  for a in (-.75,.75):
   def flask():
    b.loft('armor_belt_flask','secondary',[[-.20,0,.055,.028,.028],[-.18,0,.055,.052,.043],[-.08,0,.055,.051,.044],[-.04,0,.055,.025,.025],[.011,0,.055,.022,.022]],sides=10)
    b.tube('armor_belt_flask_cork','leather',[[0,.004,.055],[0,.042,.055]],[.024,.025],sides=8)
    frame(b,'armor_belt_flask_holder','leather',[0,-.065,.101],.10,.066,.010,.020)
    for x in (-.035,.035):b.tube('armor_belt_flask_sling','leather',[[x,.03,.019],[x,-.11,.109],[x,-.19,.080]],[.007]*3,sides=5)
   place(a,1.1,'flask',flask)
 elif kind=='scrolls':
  for a in (-.73,.73):
   def scroll():
    pipe(b,'armor_belt_scroll','accent',[0,-.20,.060],[0,.035,.060])
    for y in (-.045,-.125):b.tube('armor_belt_scroll_binding','leather',[[0,y-.013,.06],[0,y+.013,.06]],[.040,.040],sides=10)
    b.oval('armor_belt_scroll_seal','secondary',[0,-.050,.105],[.020,.024,.010],sides=8)
   place(a,1.10,'scroll',scroll)
 elif kind=='book':
  def book():
   b.box('armor_belt_book_pages','accent',[0,-.085,.059],[.14,.195,.045])
   for z in (.028,.091):b.box('armor_belt_book_cover','leather',[0,-.085,z],[.166,.225,.014])
   b.box('armor_belt_book_spine','leather',[-.078,-.085,.06],[.022,.226,.072])
   b.box('armor_belt_book_binding','secondary',[0,-.080,.106],[.033,.23,.021]);frame(b,'armor_belt_book_clasp','metal',[0,-.059,.122],.047,.043,.007,.012)
   for y in (-.13,-.07):b.tube('armor_belt_book_page_edge','secondary',[[.072,y,.037],[.072,y,.080]],[.0025]*2,sides=4)
   b.tube('armor_belt_book_suspension','leather',[[-.04,.075,.02],[-.04,.026,.05],[-.04,-.045,.098]],[.011]*3,sides=6)
  place(-.90,1.105,'book',book)


def apply(recipe,settings,slot):
 category='belts' if slot=='torso' else 'shoulders' if slot.endswith('_arm') else None
 if category is None:return
 n=settings['reference_parts'][category]
 key=settings['decor']['belt' if category=='belts' else 'shoulders']
 kind=(BELTS if category=='belts' else SHOULDERS)[n-1] if n else key
 if kind not in (BELTS if category=='belts' else SHOULDERS) and kind not in {'medallion'}:return
 if kind=='none':return
 if category=='shoulders':
  recipe['commands']=[c for c in recipe['commands'] if not c['part'].startswith('atlas_shoulders_') and not any(t in c['part'] for t in ('ornament_shoulder_','ornament_fur_tuft','pauldron','epaulet')) and not c['part'].endswith(('shoulder_plate','shoulder_lower_plate','shoulder_guard'))]
  support=[c for c in recipe['commands'] if c['slot']==slot and not c['part'].startswith(('ornament_','atlas_emblems_'))]
 else:
  recipe['commands']=[c for c in recipe['commands'] if not c['part'].startswith(('atlas_belts_','armor_belt_')) and not
    (c['part'].startswith('ornament_') and any(t in c['part'] for t in ('buckle','pouch','waist_band','leather_keeper','belt_stitch','belt_gem','flask','cork','scroll','book','medallion','tool','tab_','attachment_tab','gem_setting','chain','ornament_belt'))) and not c['part'].endswith(('waist_belt','belt_buckle'))]
  support=torso_support(recipe)
 if not support:return
 b=sculpt(settings);b.slot=slot;b.stage=4;b.palette.update(dark='302e2a',bone='d4c6a8')
 if category=='shoulders':shoulder(b,kind,slot,support)
 else:belt(b,kind,support)
 cc,pal=freeze(b,'decor_refined_armor');recipe['palette'].update(pal)
 for c in cc:c.update(slot=slot,armor_surface_revision={'schema_version':1,'category':category,'variant':kind,'method':'authored solid assemblies on actual selected clothing surfaces'})
 recipe['commands'].extend(cc);recipe['commands'].sort(key=lambda c:c['stage'])
 recipe['armor_detail_revision']={'schema_version':1,'category':category,'variant':kind,'description_ru':(SHOULDER_DESCRIPTIONS if category=='shoulders' else BELT_DESCRIPTIONS)[kind],'author_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
