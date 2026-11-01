"""Hand-authored racial landmarks and bone structures, no donor skull scaling.

The flesh topology reuses approved facial edge connectivity; every anatomical
region receives racial landmarks. Skeletal heads are built from separate bone
arches, open orbital tunnels, dental arcades and mandibles.
"""
import math
import numpy as np
from .constructor_head_topology import head
from tools.creature_workshop.family_faces import orient_faces

# Crown, temple, cheekbone, mandibular angle and chin are independent landmarks.
# Entries describe a face, rather than a scale applied to the same cranium.
ORCS={
 'male':[
  dict(crown=.190,temple=.224,cheek=.258,jaw=.230,chin=.122,eye=.119,eye_y=2.370,eye_h=.025,tilt=-.009,brow=.049,nose=.065,nose_z=.257,mouth=.123,chin_y=2.035,forehead_z=.158,cheek_z=.191,jaw_z=.155,chin_z=.242,lip_z=.253,ear='rising'),
  dict(crown=.173,temple=.209,cheek=.240,jaw=.176,chin=.078,eye=.123,eye_y=2.365,eye_h=.029,tilt=.009,brow=.035,nose=.043,nose_z=.285,mouth=.095,chin_y=2.022,forehead_z=.180,cheek_z=.211,jaw_z=.104,chin_z=.213,lip_z=.230,ear='back'),
  dict(crown=.170,temple=.201,cheek=.253,jaw=.182,chin=.081,eye=.123,eye_y=2.385,eye_h=.023,tilt=.013,brow=.062,nose=.052,nose_z=.304,mouth=.087,chin_y=2.052,forehead_z=.140,cheek_z=.216,jaw_z=.112,chin_z=.216,lip_z=.230,ear='long'),
  dict(crown=.207,temple=.252,cheek=.271,jaw=.252,chin=.141,eye=.140,eye_y=2.352,eye_h=.020,tilt=-.006,brow=.065,nose=.081,nose_z=.247,mouth=.148,chin_y=2.028,forehead_z=.146,cheek_z=.192,jaw_z=.171,chin_z=.254,lip_z=.268,ear='notched')],
 'female':[
  dict(crown=.178,temple=.214,cheek=.247,jaw=.192,chin=.085,eye=.124,eye_y=2.378,eye_h=.030,tilt=.007,brow=.036,nose=.054,nose_z=.251,mouth=.112,chin_y=2.037,forehead_z=.177,cheek_z=.205,jaw_z=.123,chin_z=.223,lip_z=.244,ear='rising'),
  dict(crown=.169,temple=.194,cheek=.222,jaw=.157,chin=.061,eye=.112,eye_y=2.372,eye_h=.033,tilt=.012,brow=.027,nose=.038,nose_z=.272,mouth=.088,chin_y=2.024,forehead_z=.188,cheek_z=.219,jaw_z=.112,chin_z=.204,lip_z=.226,ear='back'),
  dict(crown=.176,temple=.205,cheek=.239,jaw=.158,chin=.062,eye=.119,eye_y=2.391,eye_h=.026,tilt=.016,brow=.042,nose=.045,nose_z=.292,mouth=.085,chin_y=2.046,forehead_z=.168,cheek_z=.231,jaw_z=.089,chin_z=.210,lip_z=.227,ear='long'),
  dict(crown=.193,temple=.227,cheek=.259,jaw=.212,chin=.106,eye=.134,eye_y=2.367,eye_h=.025,tilt=-.003,brow=.048,nose=.066,nose_z=.255,mouth=.127,chin_y=2.031,forehead_z=.158,cheek_z=.205,jaw_z=.137,chin_z=.235,lip_z=.253,ear='notched')],
}
BULLS={
 'male':[
  dict(crown=.202,temple=.236,cheek=.270,jaw=.204,chin=.137,eye=.182,eye_y=2.393,eye_h=.024,tilt=.012,brow=.060,nose=.099,nose_z=.363,mouth=.169,chin_y=2.064,forehead_z=.162,cheek_z=.213,jaw_z=.150,chin_z=.303,lip_z=.391,ear='broad'),
  dict(crown=.238,temple=.278,cheek=.298,jaw=.254,chin=.165,eye=.202,eye_y=2.389,eye_h=.021,tilt=-.007,brow=.075,nose=.121,nose_z=.342,mouth=.191,chin_y=2.076,forehead_z=.143,cheek_z=.215,jaw_z=.207,chin_z=.320,lip_z=.380,ear='droop'),
  dict(crown=.185,temple=.214,cheek=.239,jaw=.181,chin=.116,eye=.168,eye_y=2.411,eye_h=.029,tilt=.018,brow=.041,nose=.077,nose_z=.427,mouth=.138,chin_y=2.012,forehead_z=.185,cheek_z=.227,jaw_z=.119,chin_z=.357,lip_z=.440,ear='up'),
  dict(crown=.218,temple=.252,cheek=.283,jaw=.237,chin=.169,eye=.186,eye_y=2.378,eye_h=.025,tilt=-.010,brow=.078,nose=.113,nose_z=.403,mouth=.177,chin_y=2.038,forehead_z=.143,cheek_z=.237,jaw_z=.169,chin_z=.352,lip_z=.421,ear='back')],
 'female':[
  dict(crown=.191,temple=.221,cheek=.253,jaw=.175,chin=.112,eye=.171,eye_y=2.398,eye_h=.030,tilt=.014,brow=.044,nose=.086,nose_z=.354,mouth=.148,chin_y=2.067,forehead_z=.182,cheek_z=.224,jaw_z=.116,chin_z=.275,lip_z=.374,ear='broad'),
  dict(crown=.217,temple=.254,cheek=.275,jaw=.213,chin=.139,eye=.183,eye_y=2.395,eye_h=.028,tilt=.006,brow=.054,nose=.108,nose_z=.337,mouth=.172,chin_y=2.073,forehead_z=.168,cheek_z=.223,jaw_z=.157,chin_z=.292,lip_z=.364,ear='droop'),
  dict(crown=.177,temple=.198,cheek=.229,jaw=.151,chin=.094,eye=.158,eye_y=2.418,eye_h=.031,tilt=.020,brow=.034,nose=.069,nose_z=.401,mouth=.124,chin_y=2.034,forehead_z=.191,cheek_z=.231,jaw_z=.104,chin_z=.326,lip_z=.420,ear='up'),
  dict(crown=.202,temple=.229,cheek=.268,jaw=.196,chin=.128,eye=.175,eye_y=2.390,eye_h=.028,tilt=.009,brow=.060,nose=.092,nose_z=.374,mouth=.156,chin_y=2.051,forehead_z=.171,cheek_z=.238,jaw_z=.133,chin_z=.310,lip_z=.398,ear='back')],
}


# Six further authored identities per sex. Existing approved orc landmarks stay intact.
PROFILE_FIELDS='crown temple cheek jaw chin eye eye_y eye_h tilt brow nose nose_z mouth chin_y forehead_z cheek_z jaw_z chin_z lip_z ear'.split()
MORE_ORCS={
 'male':[
 [.221,.257,.285,.246,.128,.147,2.382,.028,-.004,.061,.067,.270,.153,2.045,.172,.231,.155,.245,.271,'rising'],
 [.170,.198,.216,.172,.088,.104,2.370,.035,.004,.028,.048,.240,.104,2.060,.194,.190,.124,.205,.225,'back'],
 [.176,.220,.266,.181,.092,.118,2.402,.022,.010,.069,.042,.320,.102,2.026,.134,.243,.092,.221,.243,'long'],
 [.197,.213,.242,.198,.095,.127,2.347,.027,-.011,.047,.060,.290,.117,2.021,.175,.218,.144,.220,.254,'notched'],
 [.214,.251,.255,.251,.153,.131,2.366,.026,.003,.056,.087,.262,.158,2.043,.169,.187,.180,.272,.288,'back'],
 [.182,.203,.238,.166,.072,.113,2.394,.032,.013,.040,.052,.285,.094,2.015,.193,.235,.111,.202,.220,'rising']],
 'female':[
 [.201,.239,.273,.217,.107,.138,2.383,.032,.005,.048,.061,.267,.130,2.047,.181,.234,.139,.230,.258,'rising'],
 [.166,.188,.211,.153,.062,.103,2.385,.036,.007,.023,.040,.231,.085,2.061,.203,.202,.115,.196,.217,'back'],
 [.171,.201,.253,.156,.067,.115,2.406,.027,.013,.055,.035,.305,.091,2.030,.159,.247,.095,.203,.230,'long'],
 [.182,.198,.231,.174,.078,.120,2.364,.030,-.004,.034,.049,.274,.106,2.032,.184,.228,.132,.207,.239,'notched'],
 [.195,.228,.249,.215,.121,.127,2.378,.030,.006,.042,.071,.255,.133,2.045,.185,.208,.162,.243,.266,'back'],
 [.174,.191,.228,.146,.052,.108,2.403,.035,.010,.033,.043,.270,.081,2.028,.201,.238,.101,.194,.215,'rising']]
}
MORE_BULLS={
 'male':[
 [.212,.247,.270,.226,.153,.182,2.405,.030,.003,.037,.106,.370,.178,2.055,.182,.242,.190,.309,.357,'broad'],
 [.239,.275,.286,.245,.169,.199,2.388,.031,-.002,.043,.121,.345,.188,2.077,.171,.231,.194,.303,.334,'droop'],
 [.190,.224,.254,.196,.125,.173,2.418,.033,.006,.030,.089,.414,.151,2.043,.198,.247,.147,.341,.391,'up'],
 [.223,.260,.282,.252,.178,.189,2.384,.027,.004,.045,.116,.390,.193,2.062,.164,.219,.185,.330,.368,'back'],
 [.196,.231,.263,.206,.131,.178,2.411,.036,.005,.024,.102,.363,.172,2.051,.203,.254,.163,.296,.347,'broad'],
 [.232,.272,.295,.234,.159,.205,2.400,.029,.001,.043,.109,.404,.181,2.046,.179,.244,.192,.347,.383,'up']],
 'female':[
 [.195,.229,.257,.189,.124,.171,2.410,.034,.006,.028,.094,.357,.154,2.063,.195,.246,.156,.292,.339,'broad'],
 [.218,.251,.267,.215,.144,.180,2.396,.034,.003,.035,.106,.334,.168,2.079,.183,.242,.170,.285,.321,'droop'],
 [.175,.205,.235,.167,.102,.160,2.422,.035,.009,.024,.077,.391,.132,2.051,.209,.251,.132,.319,.369,'up'],
 [.204,.238,.266,.211,.143,.175,2.399,.031,.003,.034,.102,.375,.169,2.066,.185,.237,.165,.311,.351,'back'],
 [.184,.214,.247,.177,.108,.162,2.416,.038,.006,.021,.087,.346,.145,2.063,.213,.254,.148,.276,.330,'broad'],
 [.211,.247,.274,.197,.127,.185,2.409,.034,.004,.032,.095,.382,.156,2.055,.196,.250,.163,.326,.363,'up']]
}
for _sex in ('male','female'):
 ORCS[_sex].extend(dict(zip(PROFILE_FIELDS,row,strict=True)) for row in MORE_ORCS[_sex])
 # Correct the four earlier bovine identities locally: softer brow, shorter chin,
 # broader rounded muzzle and less pinched cheek-to-jaw transition.
 for _index,_p in enumerate(BULLS[_sex]):
  _p['brow']=[.033,.043,.029,.044][_index] if _sex=='male' else [.025,.034,.024,.032][_index]
  _p['tilt']=[.003,-.002,.006,.001][_index]
  _p['eye_h']+=.006
  _p['cheek_z']+=.018
  _p['jaw']=max(_p['jaw'],_p['mouth']*1.18)
  _p['chin_y']=max(_p['chin_y'],2.052)
  _p['lip_z']=_p['nose_z']-.014
  _p['chin_z']=_p['nose_z']-.055
 BULLS[_sex].extend(dict(zip(PROFILE_FIELDS,row,strict=True)) for row in MORE_BULLS[_sex])


def closed_patch(b,name,material,vertices,faces,purpose,depth=.008):
 vertices=np.asarray(vertices);faces=np.asarray(faces);n=len(vertices)
 rear=vertices.copy();rear[:,2]-=depth;vv=np.concatenate((vertices,rear))
 ff=faces.tolist()+[[a+n,c+n,bb+n] for a,bb,c in faces]
 edges={}
 for tri in faces:
  for a,bb in zip(tri,np.roll(tri,-1)):
   key=tuple(sorted((int(a),int(bb))));edges.setdefault(key,[]).append((int(a),int(bb)))
 for es in edges.values():
  if len(es)==1:
   a,bb=es[0];ff.extend([[a,bb,bb+n],[a,bb+n,a+n]])
 b.solid(name,material,vv,orient_faces(vv,np.asarray(ff)),purpose)

def flesh_surface(b,p,race):
 v,f,meta=head();names=meta['landmarks'];regions=meta['face_regions']
 def point(n,xyz):v[names[n]]=xyz
 bovine=race=='minotaur';nz=p['nose_z'];mz=p['lip_z'];cy=p['chin_y'];ey=p['eye_y']
 central={'top':(0,2.59,-.015),'forehead':(0,2.502,p['forehead_z']),'glabella':(0,ey+.069,p['forehead_z']+.040),'bridge':(0,ey-.010,nz-.073),'tip':(0,2.282,nz),'base':(0,2.244,nz-.021),'philtrum':(0,2.212,mz-.011),'mouth':(0,2.174,mz),'lip':(0,2.142,mz+.008),'chin':(0,cy+.026,p['chin_z']),'bottom':(0,cy,p['chin_z']-.045)}
 if bovine:central.update(glabella=(0,ey+.060,p['forehead_z']+.029),bridge=(0,2.338,nz-.095),tip=(0,2.257,nz),base=(0,2.220,nz-.018),philtrum=(0,2.189,mz-.005),mouth=(0,2.160,mz),lip=(0,2.131,mz-.002))
 for n,xyz in central.items():point(n,xyz)
 for side,sg in (('r',1),('l',-1)):
  c=p['cheek'];j=p['jaw'];ch=p['chin'];t=p['temple'];nw=p['nose'];mw=p['mouth'];cz=p['cheek_z']
  pts={'crown':(p['crown']*.67,2.556,.058),'forehead_side':(p['crown'],2.491,p['forehead_z']-.035),'forehead_inner':(p['eye']*.60,2.503,p['forehead_z']+.010),'temple':(t,ey+.071,.090),'cheek_edge':(c,ey-.084,.071),'jaw_edge':(j,2.175,p['jaw_z']),'jaw_angle':(j*.92,cy+.073,p['jaw_z']+.022),'chin_side':(ch,cy,p['chin_z']-.046),'fold':(nw*1.42,2.245,mz-.028),'cheek_plane':(c*.77,ey-.108,cz),'cheek_lower':(j*.76,2.182,cz-.037),'alar':(nw,2.274,nz-.024),'tip_side':(nw*.63,2.291,nz-.004),'nasal_side':(nw*.57,2.323,nz-.060),'mouth_corner':(mw,2.174,mz-.025),'chin_plane':(ch*.88,cy+.037,p['chin_z']-.008),'lip_side':(mw*.82,2.140,mz-.010)}
  if bovine:
   pts.update(cheek_edge=(c,ey-.089,.121),cheek_plane=(c*.79,ey-.119,cz),cheek_lower=(j*.87,2.193,cz-.012),fold=(nw*1.27,2.213,mz-.012),alar=(nw,2.244,nz-.016),tip_side=(nw*.72,2.270,nz-.003),nasal_side=(nw*.78,2.314,nz-.085),mouth_corner=(mw,2.160,mz-.024),lip_side=(mw*.88,2.135,mz-.011),chin_plane=(ch*.94,cy+.039,p['chin_z']+.012))
  for n,(x,y,z) in pts.items():point(side+n,(sg*x,y,z))
  ex=p['eye'];ew=.047 if bovine else .051;eh=p['eye_h'];z=.165 if bovine else .194
  # Eight point eyelid rim: epicanthus, upper lid, canthus, lower lid.
  for k,a in enumerate(np.linspace(math.pi,math.pi-2*math.pi,8,endpoint=False)):
   x=ex+math.cos(a)*ew;dy=math.sin(a)*eh+(x-ex)/ew*p['tilt'];zz=z-abs(math.cos(a))*.009
   point(side+'i'+str(k),(sg*x,ey+dy,zz))
   ox=ex+math.cos(a)*(ew+.027);oy=ey+math.sin(a)*(eh+.031)+(ox-ex)/(ew+.027)*p['tilt']
   oz=z+.009+(p['brow']-.035)*max(math.sin(a),0)-.045*max(math.cos(a),0)
   point(side+'o'+str(k),(sg*ox,oy,oz))
  point(side+'socket',(sg*ex,ey,z-.014))
 # Retain connectivity, but model a broad occiput and nape around racial outline.
 front_count=len(names);backcount=(len(v)-front_count-1)//2
 # Identify matching side/back boundary from original head's authored order.
 boundary=['bottom','rchin_side','rjaw_angle','rjaw_edge','rcheek_edge','ro4','rtemple','rforehead_side','rcrown','top','lcrown','lforehead_side','ltemple','lo4','lcheek_edge','ljaw_edge','ljaw_angle','lchin_side']
 assert backcount==len(boundary)
 for k,n in enumerate(boundary):
  x,y,_=v[names[n]];z=np.interp(y,[cy,cy+.075,2.25,2.38,2.49,2.59],[.037,-.035,-.139,-.187,-.154,-.035]);v[front_count+k]=[x*.91,y+(.03 if y<2.12 else 0),z]
  q=np.array([0,2.365,-.20])+(v[front_count+k]-[0,2.365,-.20])*.55;q[2]=np.interp(q[1],[2.08,2.28,2.40,2.56],[-.085,-.175,-.201,-.077]);v[front_count+backcount+k]=q
 v[-1]=[0,2.365,-.202]
 if race=='orc' and p['ear']=='notched':
  # Old healed asymmetry affects one nasal wing and its own cheek plane.
  v[names['rtip_side'],0]+=.018;v[names['rnasal_side'],2]-=.014;v[names['rcheek_plane'],1]-=.012
 b.solid('bovine_cranium' if bovine else 'orc_cranium','skin',v,orient_faces(v,f),'Расовые лоб, глазничные края, скуловые дуги, носогубные складки и нижняя челюсть.',racial_landmarks={n:v[k].tolist() for n,k in names.items()},facial_regions=regions,anatomical_profile=p)
 return v,names

def cupped_ear(b,p,race,sign):
 root=p['temple']*.91;y=p['eye_y']+.045
 if race=='orc':
  shapes={'rising':[(0,-.055),(.085,-.04),(.152,.095),(.047,.040)],'back':[(0,-.048),(.092,-.046),(.165,.035),(.035,.034)],'long':[(0,-.064),(.092,-.027),(.185,.143),(.040,.045)],'notched':[(0,-.066),(.092,-.045),(.143,.050),(.116,.063),(.147,.094),(.040,.041)]}
 else:
  shapes={'broad':[(0,-.05),(.107,-.063),(.183,-.014),(.121,.046),(.032,.045)],'droop':[(0,-.048),(.089,-.101),(.173,-.111),(.161,-.025),(.057,.038)],'up':[(0,-.045),(.063,-.050),(.137,.067),(.093,.105),(.032,.043)],'back':[(0,-.055),(.118,-.073),(.180,.002),(.105,.068),(.03,.039)]}
 pts=np.array([[sign*(root+x),y+dy,.02-.11*(x/.18)] for x,dy in shapes[p['ear']]])
 center=pts.mean(0);inner=center+(pts-center)*.56;inner[:,2]-=.014;rear=pts.copy();rear[:,2]-=.026
 vv=np.concatenate((pts,inner,rear));ff=[];n=len(pts)
 for k in range(n):
  j=(k+1)%n;ff.extend([[k,j,n+j],[k,n+j,n+k],[k,2*n+k,2*n+j],[k,2*n+j,j]])
 for k in range(1,n-1):ff.extend([[2*n,2*n+k,2*n+k+1],[n,n+k+1,n+k]])
 b.solid('bull_ear' if race=='minotaur' else 'orc_ear','skin',vv,orient_faces(vv,np.asarray(ff)),'Ушная раковина с толщиной, краем и углублённой чашей.')
 concha=inner.copy();concha[:,2]+=.0018
 closed_patch(b,'ear_concha','lip',concha,np.array([[0,k,k+1] for k in range(1,n-1)]),'Внутренняя углублённая раковина.')

def eyes(b,p,v,names):
 for s,sign in (('r',1),('l',-1)):
  rim=np.array([v[names[s+'i'+str(k)]] for k in range(8)]);center=rim.mean(0);depth=center[2]-.002
  vv=np.concatenate((rim,[[sign*p['eye'],p['eye_y'],depth+.010]]));ff=np.array([[8,k,(k+1)%8] for k in range(8)])
  closed_patch(b,'racial_eye_white','sclera',vv,ff,'Миндалевидное глазное яблоко внутри краёв век.')
  b.oval('racial_iris','iris',[sign*p['eye'],p['eye_y'],depth+.010],[.016,.019,.005],sides=8)
  b.oval('racial_pupil','pupil',[sign*p['eye'],p['eye_y'],depth+.015],[.006,.013,.0025],sides=8)
  brow=[v[names[s+'o'+str(k)]]+[0,.004,.005] for k in (0,1,2,3)]
  bovine=p.get('bovine',False)
  if bovine:brow=[q+[0,-.008,-.004] for q in brow]
  b.tube('racial_brow','skin' if bovine else 'hair',[q.tolist() for q in brow],[.009,.012,.010,.004] if bovine else [.009,.016,.014,.005],sides=6)

def flesh(b,race,gender,i,horn_author):
 p=dict((ORCS if race=='orc' else BULLS)[gender][i])
 if race=='minotaur':p['bovine']=True
 v,names=flesh_surface(b,p,race)
 for sign in (-1,1):cupped_ear(b,p,race,sign)
 eyes(b,p,v,names)
 nz=p['nose_z'];mw=p['mouth'];mz=p['lip_z']
 if race=='minotaur':
  # A broad soft nasal pad, rather than a tiny pointed human nose on the muzzle.
  nw=p['nose'];b.oval('bovine_nose_pad','dark',[0,2.256,nz+.002],[nw*1.04,.042,.023],sides=12)
  for sign in (-1,1):
   b.tube('bovine_nostril','shadow',[[sign*nw*.49,2.267,nz+.020],[sign*nw*.71,2.260,nz+.022],[sign*nw*.76,2.248,nz+.016]],[.010,.013,.009],sides=8)
  horn_author(b,i,p['crown']*1.10,gender=='female')
 else:
  for sign in (-1,1):
   nw=p['nose'];b.oval('orc_nostril','shadow',[sign*nw*.68,2.267,nz-.010],[nw*.22,.010,.007],sides=8)
   length=[.085,.050,.118,.078,.105,.041,.093,.067,.072,.055][i] if gender=='male' else [.062,.041,.078,.058,.081,.032,.064,.048,.056,.043][i]
   x=mw*.76
   b.tube('orc_lower_tusk','bone',[[sign*x,2.143,mz-.006],[sign*(x+.014),2.177,mz+.022],[sign*(x+.022),2.150+length,mz+.018],[sign*(x+.025),2.156+length,mz+.008]],[.022,.019,.008,.001],sides=8)
   # Gum collar belongs to the tooth, not a floating cone.
   b.oval('orc_tusk_gum','lip',[sign*x,2.151,mz],[.025,.014,.012],sides=8)
 if race=='minotaur':
  y=2.160
  b.tube('racial_mouth_line','shadow',[[-mw,y,mz-.024],[-mw*.55,y-.001,mz],[0,y-.002,mz+.006],[mw*.55,y-.001,mz],[mw,y,mz-.024]],[.002,.003,.003,.003,.002],sides=6)
  b.panel3('racial_lower_lip','lip',[[-mw*.85,y-.006,mz-.010],[-mw*.4,y-.006,mz+.003],[mw*.4,y-.006,mz+.003],[mw*.85,y-.006,mz-.010],[mw*.56,y-.023,mz-.003],[-mw*.56,y-.023,mz-.003]],.009)
  return p
 # Cupid bow and a separate lower lip follow selected face's own mouth corners.
 points=[[-mw,2.174,mz-.025],[-mw*.45,2.181,mz+.002],[0,2.178,mz+.006],[mw*.45,2.181,mz+.002],[mw,2.174,mz-.025]]
 b.tube('racial_mouth_line','shadow',points,[.0035,.005,.005,.005,.0035],sides=6)
 b.panel3('racial_lower_lip','lip',[[-mw*.92,2.169,mz-.015],[-mw*.38,2.172,mz+.006],[mw*.38,2.172,mz+.006],[mw*.92,2.169,mz-.015],[mw*.59,2.151,mz+.008],[-mw*.59,2.151,mz+.008]],.012)
 return p

# Bone profiles independently specify orbital contour, maxillary arcade,
# zygomatic arch, cranial vault and mandibular angles.
SKULLS=[
 dict(vault=.218,top=2.576,forehead=.158,eye=.112,ey=2.367,orbit='round',ow=.070,oh=.071,cheek=.233,jaw=.174,chin=.099,snout=.184,nose=.037,teeth=8,angle=2.140),
 dict(vault=.199,top=2.634,forehead=.127,eye=.108,ey=2.388,orbit='oval',ow=.058,oh=.082,cheek=.227,jaw=.141,chin=.064,snout=.171,nose=.027,teeth=8,angle=2.110),
 dict(vault=.245,top=2.552,forehead=.169,eye=.128,ey=2.355,orbit='square',ow=.075,oh=.055,cheek=.270,jaw=.232,chin=.144,snout=.220,nose=.046,teeth=10,angle=2.124),
 dict(vault=.228,top=2.555,forehead=.126,eye=.123,ey=2.365,orbit='slant',ow=.073,oh=.055,cheek=.274,jaw=.235,chin=.133,snout=.252,nose=.051,teeth=8,angle=2.128),
 dict(vault=.240,top=2.593,forehead=.149,eye=.178,ey=2.387,orbit='lateral',ow=.059,oh=.069,cheek=.288,jaw=.212,chin=.132,snout=.359,nose=.072,teeth=8,angle=2.157),
 dict(vault=.175,top=2.580,forehead=.143,eye=.119,ey=2.393,orbit='slant',ow=.060,oh=.061,cheek=.222,jaw=.157,chin=.074,snout=.400,nose=.034,teeth=10,angle=2.139),
]

def orbital_tunnel(b,p,sign):
 shape={'round':[(1,0),(.65,.77),(0,1),(-.72,.64),(-1,0),(-.58,-.77),(.14,-1),(.84,-.60)],'oval':[(1,0),(.72,.76),(0,1),(-.68,.76),(-1,0),(-.68,-.75),(0,-1),(.74,-.72)],'square':[(1,.52),(.42,1),(-.55,.92),(-1,.30),(-.94,-.65),(-.23,-1),(.64,-.87),(1,-.35)],'slant':[(1,.5),(.2,.95),(-.64,.62),(-1,.02),(-.80,-.62),(-.18,-1),(.71,-.65),(1,-.04)],'lateral':[(1,0),(.62,.85),(-.16,1),(-.85,.55),(-1,-.1),(-.51,-.87),(.20,-1),(.85,-.6)]}[p['orbit']]
 inner=np.array([[sign*(p['eye']+x*p['ow']),p['ey']+y*p['oh'],.184-.034*max(x,0)] for x,y in shape]);center=inner.mean(0)
 outer=center+(inner-center)*[1.26,1.25,1];outer[:,2]+=.013
 rear=inner.copy();rear[:,2]-=.056;outerrear=outer.copy();outerrear[:,2]-=.073;vv=np.concatenate((outer,inner,rear,outerrear));ff=[]
 for k in range(8):
  j=(k+1)%8;ff.extend([[k,j,8+j],[k,8+j,8+k],[8+k,8+j,16+j],[8+k,16+j,16+k],[16+k,16+j,24+j],[16+k,24+j,24+k],[24+k,24+j,j],[24+k,j,k]])
 b.solid('orbital_rim','skin',vv,orient_faces(vv,np.asarray(ff)),'Настоящая костная глазница: отдельный наружный край, внутренний контур и глубокие стенки.',orbital_profile=p['orbit'])
 closed_patch(b,'recessed_orbit','shadow',rear,np.array([[0,k,k+1] for k in range(1,7)]),'Дно глубокой глазницы за скуловой костью.')
 b.oval('soul_eye','iris',[sign*p['eye'],p['ey'],.140],[.019,.023,.006],sides=8)
 return outer

def skull(b,i,horn_author):
 p=SKULLS[i];b.palette['skin']='cfc6ad';b.palette['shadow']='373932';b.palette['bone']='e1d8bd'
 w=p['vault'];ey=p['ey'];sn=p['snout'];j=p['jaw'];ch=p['chin']
 # Cranial vault is only behind the sockets: it cannot fill the facial cavities.
 b.loft('rounded_cranium','skin',[[2.21,0,-.085,w*.69,.112],[2.37,0,-.106,w,.146],[2.49,0,-.085,w*.91,.135],[p['top']-.024,0,-.049,w*.50,.069],[p['top'],0,-.040,w*.12,.021]],sides=12)
 b.panel3('forehead','skin',[[-w*.91,ey+.058,.119],[-w*.77,2.496,p['forehead']-.010],[-w*.42,p['top']-.027,.041],[0,p['top']-.012,.033],[w*.42,p['top']-.027,.041],[w*.77,2.496,p['forehead']-.010],[w*.91,ey+.058,.119],[p['eye']*.43,ey+.049,.175],[0,ey+.013,.185],[-p['eye']*.43,ey+.049,.175]],.048)
 for sign in (-1,1):
  orbital_tunnel(b,p,sign)
  # Cheek arches have open space underneath; no stretched skin cheek slabs.
  path=[[sign*p['eye']*.55,ey-.072,.191],[sign*(p['eye']+p['ow']*.69),ey-.090,.199],[sign*p['cheek'],ey-.066,.095],[sign*w*.96,ey+.014,-.014]]
  b.tube('zygomatic_arch','skin',path,[.019,.026,.024,.022],sides=6)
  b.tube('mandible_ram','skin',[[sign*w*.83,ey-.028,-.017],[sign*j,p['angle']+.066,.025],[sign*j,p['angle'],.081],[sign*ch,2.066,sn-.014]],[.025,.030,.035,.022],sides=6)
  # Nasal aperture boundary changes with muzzle, not just overall skull width.
  nw=p['nose'];b.panel3('nasal_side','skin',[[sign*nw*.34,ey+.025,.201],[sign*nw,2.270,sn+.012],[sign*nw*1.17,2.225,sn+.004],[sign*nw*.60,2.243,sn-.013]],.022)
  if i in (4,5):b.tube('maxillary_bridge','skin',[[sign*nw*.85,2.300,sn*.58],[sign*nw*1.4,2.266,sn*.80],[sign*nw*1.95,2.218,sn-.02]],[.032,.038,.035],sides=6)
 # Actual triangular/elongated nasal hole is framed by bone rather than a drawn triangle.
 nw=p['nose'];b.panel3('nasal_cavity','shadow',[[-nw*.28,ey-.012,.183],[nw*.28,ey-.012,.183],[nw*.87,2.237,sn-.005],[-nw*.87,2.237,sn-.005]],.010)
 archw=[.112,.094,.151,.141,.161,.110][i]
 upper=[];lower=[]
 for a in np.linspace(math.pi,0,9):
  x=math.cos(a)*archw;z=sn-.045+math.sin(a)*.047
  upper.append([x,2.183,z]);lower.append([x*.97,2.091,z-.006])
 b.tube('maxilla','skin',upper,[.024]*9,sides=6)
 b.tube('mandible_chin','skin',lower,[.026 if i in (2,3) else .021]*9,sides=6)
 # Teeth lie on a curved arcade and taper at the gum; distinct canine/premolar shapes.
 count=p['teeth']
 for row,base_y in [('upper',2.169),('lower',2.110)]:
  for k,a in enumerate(np.linspace(math.pi*.88,math.pi*.12,count)):
   x=math.cos(a)*archw*.94;z=sn-.033+math.sin(a)*.041;edge=min(k,count-1-k);canine=edge==1 and i in (3,5)
   length=.057 if canine else .027 if edge<2 else .023;tw=.018 if i in (4,5) else .021
   direction=-1 if row=='upper' else 1
   b.loft(f'{row}_tooth_{k}','bone',[[base_y, x,z,tw*.58,.014],[base_y+direction*length*.73,x,z+.001,tw*.49,.013],[base_y+direction*length,x,z+.005,tw*(.15 if canine else .44),.010]],sides=6)
 if i==3:
  for sign in (-1,1):b.tube('orc_skeletal_tusk','bone',[[sign*.121,2.09,sn],[sign*.142,2.162,sn+.023],[sign*.155,2.228,sn+.015]],[.023,.016,.0015],sides=8)
 if i==4:horn_author(b,1,w,False)
 if i==5:
  # Sagittal crest and nasal ridge distinguish the canine skull in silhouette.
  b.panel3('sagittal_crest','skin',[[-.009,2.45,.113],[0,2.590,-.020],[.009,2.45,.113],[.009,2.405,.12]],.055)
 return p
