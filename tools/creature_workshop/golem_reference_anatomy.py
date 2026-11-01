"""Geometry helpers retained for current constructor customization."""
import math
import numpy as np
from monsterforge.constructor_knees import world_bind
from .family_faces import orient_faces

def solid(b,name,outline,z,depth,mat='skin',inset=.83,crown=.035,face_offsets=None):
    """Beveled authored XY outline; large planar face, full depth and closed back."""
    xy=np.asarray(outline,float);mid=xy.mean(0);n=len(xy)
    face=mid+(xy-mid)*inset
    v=np.concatenate([np.column_stack([xy,np.full(n,z-depth*.32)]),
                      np.column_stack([xy,np.full(n,z+depth*.28)]),
                      np.column_stack([face,np.full(n,z+depth*.5)]),
                      [[*mid,z-depth*.5],[*mid,z+depth*.5+crown]]])
    if face_offsets is not None:v[2*n:3*n,2]+=np.asarray(face_offsets)
    f=[]
    for i in range(n):
        j=(i+1)%n
        f.extend([[3*n,j,i],[i,j,n+j],[i,n+j,n+i],
                  [n+i,n+j,2*n+j],[n+i,2*n+j,2*n+i],
                  [3*n+1,2*n+i,2*n+j]])
    if face_offsets is not None:
        # Two deliberately offset ridge vertices break the radial fan into large
        # quarry planes. The ridge follows the stone's longest contour axis.
        axis=int(np.argmax(np.ptp(face,axis=0)));extent=np.ptp(face,axis=0)[axis]
        a=mid.copy();a[axis]-=extent*.18
        c=mid.copy();c[axis]+=extent*.14
        v=np.concatenate([v[:-1],[[*a,z+depth*.5+crown],[*c,z+depth*.5+crown*.35]]])
        f=[t for t in f if 3*n+1 not in t]
        caps=[]
        for k in range(n):
            j=(k+1)%n;cap=3*n+1+int((face[k,axis]+face[j,axis])*.5>=mid[axis]);caps.append(cap)
            f.append([cap,2*n+k,2*n+j])
        for k in range(n):
            if caps[k]!=caps[k-1]:f.append([caps[k-1],2*n+k,caps[k]])
    b.commands.append({'id':name,'part':name,'op':'indexed_mesh','vertices':v.tolist(),'faces':orient_faces(v,np.array(f)).tolist(),'material':mat,'slot':b.slot,'stage':b.stage,'purpose':'Авторский контур с фасками, крупными плоскостями и глубиной; форма по Front-референсу големов v1.'})

def slab(b,name,x,y,w,h,z=.03,depth=.22,mat='skin',cut=.20):
    solid(b,name,[(x-w*.72,y-h),(x+w*.60,y-h),(x+w,y-h*.55),
                  (x+w,y+h*.55),(x+w*(1-cut),y+h),(x-w*.68,y+h),
                  (x-w,y+h*.48),(x-w,y-h*.45)],z,depth,mat)

def ribbon(b,name,path,widths,z=.015,depth=.15,mat='skin'):
    p=np.asarray(path,float);v=[];f=[]
    for i,q in enumerate(p):
        t=p[min(i+1,len(p)-1)]-p[max(i-1,0)];normal=np.array([-t[1],t[0]]);normal/=np.linalg.norm(normal)
        for dz in (-depth*.5,depth*.23):
            for sign in (-1,1):v.append([*(q+normal*widths[i]*sign),z+dz])
        v.append([*q,z+depth*.65])
        if i:
            a=(i-1)*5;c=i*5
            for j,k in ((0,1),(1,3),(3,4),(4,2),(2,0)):f.extend([[a+j,c+j,c+k],[a+j,c+k,a+k]])
    f.extend([[0,2,4],[0,4,3],[0,3,1]]);a=(len(p)-1)*5;f.extend([[a,a+4,a+2],[a,a+3,a+4],[a,a+1,a+3]])
    b.commands.append({'id':name,'part':name,'op':'indexed_mesh','vertices':v,'faces':orient_faces(np.asarray(v),np.asarray(f)).tolist(),'material':mat,'slot':b.slot,'stage':b.stage,'purpose':'Широкая изогнутая каменная лопасть; цельный замкнутый меш с открытым пространством вокруг.'})

def diamond(b,name,x,y,w,h,z,depth,mat='bone'):
    solid(b,name,[(x,y-h),(x+w,y-h*.12),(x+w*.66,y+h*.55),(x,y+h),(x-w*.66,y+h*.55),(x-w,y-h*.12)],z,depth,mat,inset=.60,crown=.024)

def face(b,i):
    b.slot='head';b.stage=2
    if i==0:
        slab(b,'stone_cranium',0,2.275,.198,.19,.015,.28)
        slab(b,'volcanic_mandible',0,2.10,.146,.062,.10,.15)
        for s in (-1,1):solid(b,'basalt_face_plane',[(s*.025,2.38),(s*.16,2.36),(s*.19,2.27),(s*.14,2.20),(s*.035,2.22)],.153,.055,'skin')
    elif i==1:
        diamond(b,'stone_cranium',0,2.30,.17,.30,0,.25)
        for s in (-1,1):
            solid(b,'ice_face_blade',[(s*.018,2.43),(s*.151,2.39),(s*.105,2.12),(s*.035,2.04)],.12,.06,'secondary')
            solid(b,'ice_crown_prong',[(s*.10,2.48),(s*.15,2.72),(s*.18,2.47)],-.05,.075,'bone')
    elif i==2:
        slab(b,'stone_cranium',0,2.29,.205,.20,.02,.24)
        slab(b,'weathered_brow',0,2.48,.245,.059,.037,.29,'bone')
        slab(b,'sandstone_nose_keystone',0,2.26,.037,.092,.17,.09)
        for s in (-1,1):slab(b,'eroded_cheek',s*.122,2.24,.045,.13,.13,.10)
    elif i==3:
        for s in (-1,1):
            ribbon(b,'stone_cranium',[(s*.025,2.09),(s*.14,2.31),(s*.14,2.47),(s*.075,2.54)],[.025,.055,.045,.022],-.03,.12)
            solid(b,'wind_face_visor',[(s*.01,2.12),(s*.095,2.33),(s*.06,2.44),(s*.008,2.36)],.12,.055,'bone')
    else:
        slab(b,'stone_cranium',0,2.30,.185,.224,.005,.255)
        slab(b,'ancient_forehead_lintel',0,2.53,.245,.063,.025,.30,'bone')
        slab(b,'ancient_nose_keystone',0,2.28,.040,.11,.176,.10)
        for s in (-1,1):
            slab(b,'ancient_cheek_column',s*.129,2.25,.045,.141,.12,.13)
            slab(b,'ancient_stone_beard',s*.070,2.08,.043,.081,.13,.085)
    # A dark cut beneath heavy brow planes, with short elemental eye inserts.
    for s in (-1,1):
        if i!=3:
            solid(b,'stone_eye_recess',[(s*.035,2.355),(s*.135,2.365),(s*.122,2.322),(s*.04,2.325)],.169,.035,'dark',crown=0)
        b.tube('elemental_eye','iris',[[s*.044,2.343,.192],[s*.108,2.351,.183]],[.008,.007],sides=5)
    if i in (2,4):b.tube('stone_mouth_fissure','dark',[[-.061,2.16,.16],[0,2.147,.175],[.061,2.16,.16]],[.005]*3,sides=5)
