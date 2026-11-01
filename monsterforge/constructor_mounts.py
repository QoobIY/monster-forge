"""Fitted, optional mount tack; derived meshes never modify animal source parts."""
import math
import numpy as np
from tools.creature_workshop.geometry import mesh
from tools.creature_workshop.original_constructor import OriginalSculpt,mesh_command
from tools.creature_workshop.family_faces import orient_faces

RACES={'beast-horse','beast-tiger','beast-wolf','beast-bear','beast-elephant','sky-dragon'}
SADDLES={'none':'Без седла','mount_travel':'Походное седло','mount_war':'Боевое седло','mount_royal':'Парадное седло'}
ARMOR={'none':'Без защиты','mount_leather':'Кожаная защита','mount_plate':'Пластинчатая броня','mount_scale':'Чешуйчатая броня'}
BRIDLES={'none':'Без сбруи','mount_bridle':'Ременная сбруя','mount_chamfron':'Сбруя с налобной защитой'}
EMBLEMS={'none':'Без эмблемы','sun':'Солнце','lionheart':'Львиное сердце','key':'Ключ','skull':'Череп','bear':'Медведь','wolf':'Волк','serpent':'Змея','mage':'Маг','crown':'Корона','pirate':'Пиратский знак'}
OPTIONS={'belt':SADDLES,'shoulders':ARMOR,'headwear':BRIDLES,'emblem':EMBLEMS}

def options(race):
    if race=='beetle':
        from .constructor_beetle_equipment import OPTIONS as insect_options
        return insect_options
    return OPTIONS if race in RACES else {}

class Surface:
    def __init__(self,command):
        self.v,f=mesh(command);self.tri=self.v[f];self.bounds=(self.v.min(0),self.v.max(0));self.sections={}
    def centre(self,z):
        # Use intersections with the actual section plane, rather than a bounding sphere.
        if z in self.sections:return self.sections[z]
        points=[]
        for tri in self.tri:
            for a,b in ((tri[0],tri[1]),(tri[1],tri[2]),(tri[2],tri[0])):
                if abs(b[2]-a[2])>1e-9 and min(a[2],b[2])<=z<=max(a[2],b[2]):points.append(a+(b-a)*(z-a[2])/(b[2]-a[2]))
        if not points:raise ValueError('Tack section outside animal surface')
        p=np.asarray(points);self.sections[z]=np.array([(p[:,0].min()+p[:,0].max())*.5,(p[:,1].min()+p[:,1].max())*.5,z]);return self.sections[z]
    def hit(self,origin,direction):
        o=np.asarray(origin);d=np.asarray(direction);t=self.tri
        e1=t[:,1]-t[:,0];e2=t[:,2]-t[:,0];p=np.cross(d,e2);det=np.einsum('ij,ij->i',e1,p)
        safe=np.where(abs(det)>1e-9,det,1);tv=o-t[:,0];u=np.einsum('ij,ij->i',tv,p)/safe;q=np.cross(tv,e1);v=q@d/safe;dist=np.einsum('ij,ij->i',e2,q)/safe
        valid=(abs(det)>1e-9)&(u>=-1e-6)&(v>=-1e-6)&(u+v<=1+1e-6)&(dist>1e-8)
        if not valid.any():raise ValueError('Tack cannot contact selected anatomy')
        return o+d*float(dist[valid].max())
    def radial(self,z,a,offset=.018):
        direction=np.array([math.sin(a),math.cos(a),0]);return self.hit(self.centre(z),direction)+direction*offset

def apply(recipe,settings,slot,_carrier=None):
    if settings['race']=='beetle':
        from .constructor_beetle_equipment import apply as insect_apply
        return insect_apply(recipe,settings,slot)
    if settings['race'] not in RACES:return
    decor=settings['decor'];saddle=decor['belt'];armor=decor['shoulders'];bridle=decor['headwear'];emblem=decor['emblem']
    if slot not in {'head','torso'}:return
    if slot=='head' and bridle=='none' or slot=='torso' and saddle==armor==emblem=='none':return
    candidates=[c for c in recipe['commands'] if any(t in c['part'] for t in (('chest_waist_rump','ribcage_waist_croup') if slot=='torso' else ('cranial_cheek_muzzle','occiput_forehead_cheeks','eagle_cranium','cranial_orbit','neck_occiput_brow')))]
    multihead=slot=='head' and len(candidates)>1
    if not candidates:candidates=[c for c in recipe['commands'] if not any(t in c['part'] for t in ('eye','tooth','horn','feather','talon','mane','iris','nostril'))]
    if multihead and _carrier is None:
        placements=[]
        for carrier in candidates:
            apply(recipe,settings,slot,_carrier=carrier);placements.append(dict(recipe['mount_equipment']))
        recipe['mount_heads']={'schema_version':1,'count':len(placements),'placements':placements}
        return
    part=_carrier if _carrier is not None else max(candidates,key=lambda c:float(np.prod(np.ptp(mesh(c)[0],axis=0))))
    surface=Surface(part);lo,hi=surface.bounds;length=hi[2]-lo[2];b=OriginalSculpt({'id':'mount-equipment-v2','palette':{'skin':recipe['palette']['skin'],'hair':recipe['palette']['hair'],'cloth':'315877','accent':'d8ba73','metal':'969fa5','leather':'50382c','secondary':'743b43'}});b.slot=slot;b.stage=4
    contact=[]
    def wrap(name,mat,zs,angles,offset=.018,thickness=.014):
        grid=np.array([[surface.radial(float(z),float(a),offset) for a in angles] for z in zs]);vertices=[]
        for layer in (0,1):
            for row in grid:
                for j,p in enumerate(row):vertices.append((p+np.array([math.sin(angles[j]),math.cos(angles[j]),0])*thickness*layer).tolist())
        n=len(angles);m=len(zs);count=m*n;faces=[]
        for i in range(m-1):
            for j in range(n-1):
                q=i*n+j
                faces.extend([[q,q+n,q+n+1],[q,q+n+1,q+1],[count+q,count+q+n+1,count+q+n],[count+q,count+q+1,count+q+n+1]])
        perimeter=list(range(n))+[i*n+n-1 for i in range(1,m)]+list(range((m-1)*n+n-2,(m-1)*n-1,-1))+[i*n for i in range(m-2,0,-1)]
        for q,r in zip(perimeter,perimeter[1:]+perimeter[:1]):faces.extend([[q,r,r+count],[q,r+count,q+count]])
        b.commands.append({'id':name,'op':'indexed_mesh','vertices':vertices,'faces':faces,'part':name,'material':mat,'slot':slot,'stage':4,'purpose':'Fitted tack with constant outward clearance from selected animal mesh'})
        contact.append({'part':name,'points':grid.reshape(-1,3).tolist(),'clearance':offset})
        return grid
    def panel(name,mat,outline,offset=.035,thickness=.024,trim=True):
        # Authored outline in longitudinal/angular coordinates; a fitted solid with
        # a recessed perimeter and an inset, raised face, rather than a box strip.
        uv=np.asarray(outline,float);centre=uv.mean(0);n=len(uv)
        inset=centre+(uv-centre)*.82
        back=np.array([surface.radial(z,a,offset) for z,a in uv])
        edge=np.array([surface.radial(z,a,offset+thickness*.40) for z,a in uv])
        face=np.array([surface.radial(z,a,offset+thickness) for z,a in inset])
        cb=surface.radial(*centre,offset);cf=surface.radial(*centre,offset+thickness+.014)
        vertices=np.concatenate([back,edge,face,[cb,cf]]);faces=[]
        for i in range(n):
            j=(i+1)%n
            faces.extend([[3*n,j,i],[i,j,n+j],[i,n+j,n+i],
                          [n+i,n+j,2*n+j],[n+i,2*n+j,2*n+i],
                          [3*n+1,2*n+i,2*n+j]])
        b.commands.append({'id':name,'op':'indexed_mesh','vertices':vertices.tolist(),'faces':faces,'part':name,'material':mat,'slot':slot,'stage':4,'purpose':'Contoured fitted plate with bevel, raised face and embedded fastening edge'})
        contact.append({'part':name,'points':back.tolist(),'clearance':offset})
        if trim:
            # A narrow rolled edge follows the actual bevel, including pointed tips.
            b.tube(name+'_rolled_edge','accent',np.concatenate([edge,[edge[0]]]).tolist(),[.006]*(n+1),sides=5)
        return edge
    def rivet(z,a,offset=.080):
        origin=surface.centre(float(z));direction=np.array([math.sin(a),math.cos(a),0])
        carriers=[]
        for c in b.commands:
            if c['op']=='indexed_mesh' and c.get('purpose','').startswith('Contoured fitted plate'):
                try:carriers.append((Surface(c).hit(origin,direction),c['part']))
                except ValueError:pass
        if not carriers:return
        skin,name=max(carriers,key=lambda item:np.linalg.norm(item[0]-origin))
        b.oval('mount_peened_rivet','accent',(skin+direction*.004).tolist(),[.009,.009,.009],sides=6)
        b.commands[-1]['fastening']={'carrier':name,'surface_point':skin.tolist(),'centre_clearance':.004}
    if slot=='torso':
        zc=lo[2]+length*.49;half=length*.22;zs=np.linspace(zc-half,zc+half,7);angles=np.linspace(-2.10,2.10,17)
        if saddle!='none' or emblem!='none':
            grid=wrap('mount_saddlecloth','cloth',zs,angles)
            for edge in (grid[0],grid[-1],grid[:,0],grid[:,-1]):b.tube('mount_blanket_piping','accent',edge.tolist(),[.009]*len(edge),sides=5)
            for z in (zc-half*.86,zc+half*.86):wrap('mount_girth_strap','leather',[z-.022,z+.022],np.linspace(-math.pi,math.pi,33),offset=.035)
        if saddle!='none':
            seat=wrap('mount_saddle_seat','leather',np.linspace(zc-half*.68,zc+half*.68,6),np.linspace(-.62,.62,9),offset=.055,thickness=.036)
            for i,z in enumerate((zc-half*.72,zc+half*.72)):
                points=[surface.radial(z,a,.080+(.072 if i==0 else .048)*math.cos(a)) for a in np.linspace(-.63,.63,9)]
                b.tube('mount_cantle' if i==0 else 'mount_pommel','leather',np.asarray(points).tolist(),[.028]*9,sides=8)
                b.tube('mount_seat_trim','accent',(np.asarray(points)+[0,.025,0]).tolist(),[.009]*9,sides=6)
            for sign in (-1,1):
                start=surface.radial(zc+half*.24,sign*.88,.070);end=surface.radial(zc+half*.24,sign*1.9,.050)
                b.tube('mount_stirrup_leather','leather',[start.tolist(),end.tolist()],[.020,.016],sides=6)
                x,y,z=end;loop=[[x+sign*.015,y+.015,z-.045],[x+sign*.035,y-.085,z-.065],[x+sign*.035,y-.115,z+.065],[x+sign*.015,y+.015,z+.045],[x+sign*.015,y+.015,z-.045]]
                b.tube('mount_stirrup_iron','metal',loop,[.012]*5,sides=6)
                if saddle=='mount_travel':
                    p=surface.radial(zc-half*.62,sign*1.30,.085);b.oval('mount_saddlebag','leather',p.tolist(),[.075,.105,.12],sides=8)
                    b.box('mount_bag_buckle','accent',(p+[sign*.075,0,0]).tolist(),[.018,.033,.037])
                if saddle=='mount_royal':
                    for z in np.linspace(zc-half*.75,zc+half*.75,6):
                        p=surface.radial(float(z),sign*2.08,.03);b.tube('mount_royal_tassel','accent',[p.tolist(),(p+[0,-.10,0]).tolist()],[.013,.007],sides=5)
        if armor!='none':
            def shape(points,sign=1):return [(lo[2]+length*z,sign*a) for z,a in points]
            metal='leather' if armor=='mount_leather' else 'metal'
            # Split the breast protection into a dorsal yoke and left/right bibs.
            # This leaves the foreleg articulation clear instead of wrapping it in a barrel.
            panel('mount_chest_guard',metal,shape([(.79,-.56),(.88,-.65),(.95,-.30),(.97,0),(.95,.30),(.88,.65),(.79,.56),(.76,0)]),thickness=.035)
            for sign in (-1,1):
                panel('mount_breast_bib',metal,shape([(.82,.68),(.93,.65),(.96,1.04),(.91,1.65),(.86,2.22),(.78,2.04),(.75,1.31)],sign),thickness=.032)
                for z,a in ((.86,.78),(.91,1.20),(.80,1.79)):rivet(lo[2]+length*z,sign*a,.073)
                if armor=='mount_leather':
                    # Light barding: two shaped, padded guards, carried by diagonal
                    # straps. Exposed fur and a lower scalloped edge distinguish it.
                    for name,outline in (
                        ('mount_padded_shoulder',[(.66,.82),(.77,.75),(.82,1.10),(.78,1.73),(.73,1.92),(.67,1.74),(.63,1.26)]),
                        ('mount_padded_haunch',[(.17,.83),(.29,.69),(.35,1.00),(.33,1.58),(.26,1.89),(.18,1.66),(.14,1.18)])):
                        panel(name,'leather',shape(outline,sign),offset=.038,thickness=.036)
                        uv=np.asarray(shape(outline,sign));mid=uv.mean(0)
                        stitch=mid+(uv-mid)*.89
                        for z,a in stitch:rivet(z,a,.078)
                    for z0,z1 in ((.29,.39),(.63,.76)):
                        path=[surface.radial(lo[2]+length*(z0+(z1-z0)*t),sign*(.30+1.36*t),.087).tolist() for t in np.linspace(0,1,9)]
                        b.tube('mount_guard_suspension','leather',path,[.020]*9,sides=6)
                        z=lo[2]+length*(z0+(z1-z0)*.62);a=sign*(.30+1.36*.62)
                        uv=[(z-length*.023,a-.08),(z+length*.023,a-.08),(z+length*.023,a+.08),(z-length*.023,a+.08)]
                        frame=[surface.radial(q,t,.108).tolist() for q,t in uv];frame.append(frame[0])
                        b.tube('mount_harness_buckle','accent',frame,[.009]*5,sides=6)
                        b.tube('mount_buckle_tongue','accent',[surface.radial(z,a-.08,.110).tolist(),surface.radial(z,a+.025,.110).tolist()],[.006,.006],sides=5)
                elif armor=='mount_plate':
                    # Overlapping shoulder lames descend outwards; the hindquarter
                    # has its own flared shield. The middle remains a heraldic cloth.
                    broad=settings['race']=='beast-bear'
                    for row in range(3):
                        a=.63+row*.36;z=.755-row*.018;w=.095 if broad else .083
                        panel('mount_articulated_pauldron','metal',shape([(z-w,a+.08),(z-.02,a-.055),(z+w,a+.015),(z+w+.025,a+.27),(z+.035,a+.47),(z-w,a+.36)],sign),offset=.060+row*.008,thickness=.030)
                        for q in (z-w*.60,z+w*.60):rivet(lo[2]+length*q,sign*(a+.15),.102+row*.008)
                    panel('mount_croup_shield','metal',shape([(.13,.79),(.23,.58),(.34,.75),(.38,1.18),(.32,1.69),(.23,1.93),(.15,1.55),(.11,1.07)],sign),offset=.049,thickness=.034)
                    panel('mount_croup_lower_lame','metal',shape([(.16,1.58),(.27,1.64),(.31,1.82),(.27,2.10),(.20,2.23),(.14,1.99)],sign),offset=.067,thickness=.026)
                    for z,a in ((.18,.92),(.30,.92),(.21,1.75)):rivet(lo[2]+length*z,sign*a,.095)
                else:
                    panel('mount_scale_leather_backing','leather',shape([(.18,.74),(.64,.72),(.77,1.03),(.73,1.76),(.61,2.02),(.27,2.09),(.17,1.69)],sign),offset=.043,thickness=.016,trim=False)
                    # Broad pointed scales are individually fitted, overlap in the
                    # direction of articulation, and reveal the leather foundation.
                    for row in range(3):
                        a=.82+row*.36
                        for col in range(5):
                            z=.235+col*.095+(row%2)*.026
                            panel('mount_pointed_scale','metal',shape([(z-.052,a+.04),(z-.040,a-.035),(z+.041,a-.035),(z+.056,a+.045),(z+.047,a+.27),(z,a+.43),(z-.048,a+.27)],sign),offset=.072+row*.009,thickness=.018,trim=False)
                            rivet(lo[2]+length*z,sign*(a+.085),.099+row*.009)
        if emblem!='none':
            from .constructor_emblems import authored_badge
            for sign in (-1,1):
                if armor!='none':wrap('mount_heraldic_field','cloth',np.linspace(zc-.16,zc+.16,7),np.linspace(sign*1.13,sign*2.02,9),offset=.133,thickness=.014)
                support=Surface(next(c for c in reversed(b.commands) if c['part']==('mount_heraldic_field' if armor!='none' else 'mount_saddlecloth')))
                start=len(b.commands);authored_badge(b,emblem,0,0)
                centre=surface.centre(zc);ey=centre[1]+(hi[1]-lo[1])*.03
                for c in b.commands[start:]:
                    v,f=mesh_command(c);v=v.copy();local=v.copy();v[:,1]=ey+local[:,1];v[:,2]=zc+local[:,0]
                    for i,p in enumerate(v):v[i,0]=support.hit([0,p[1],p[2]],[sign,0,0])[0]+sign*(.013+local[i,2])
                    c.update(op='indexed_mesh',vertices=v.tolist(),faces=orient_faces(v,f).tolist())
    else:
        for frac in (.43,.78):
            z=lo[2]+length*frac;wrap('mount_bridle_noseband' if frac>.5 else 'mount_bridle_headband','leather',[z-.018,z+.018],np.linspace(-math.pi,math.pi,33),offset=.015)
        for sign in (-1,1):
            points=[]
            for z in np.linspace(lo[2]+length*.43,lo[2]+length*.78,8):points.append(surface.radial(float(z),sign*1.45,.028).tolist())
            b.tube('mount_bridle_cheekstrap','leather',points,[.016]*len(points),sides=6)
            for p in (points[0],points[-1]):b.oval('mount_bridle_ring','accent',p,[.015,.023,.023],sides=8)
        if bridle=='mount_chamfron':
            # A tapered nasal shield and two brow wings, leaving eyes and jaws open.
            panel('mount_chamfron_plate','metal',[(lo[2]+length*z,a) for z,a in ((.36,-.25),(.44,-.47),(.58,-.35),(.75,-.15),(.80,0),(.75,.15),(.58,.35),(.44,.47),(.36,.25))],thickness=.027)
            for sign in (-1,1):
                panel('mount_chamfron_brow_wing','metal',[(lo[2]+length*z,sign*a) for z,a in ((.32,.30),(.39,.29),(.45,.47),(.44,.70),(.37,.83),(.31,.63))],offset=.030,thickness=.020)
                for z in (.44,.65):rivet(lo[2]+length*z,sign*.17,.073)
    for c in b.commands:
        v,f=mesh_command(c) if c['op']!='indexed_mesh' else mesh(c)
        c.update(op='indexed_mesh',vertices=v.tolist(),faces=orient_faces(v,f).tolist(),id='mount_'+slot+'_'+str(len(recipe['commands'])),mount_equipment=True,material='mount_'+c['material'],ai_description_ru='Экипировка боевого животного: '+c['part']+'. Посадка рассчитана по поверхности выбранной анатомии; независимый выбор седла, защиты, сбруи и герба.')
        recipe['commands'].append(c)
    recipe['palette'].update({'mount_'+k:v for k,v in b.palette.items()});recipe['commands'].sort(key=lambda c:c['stage'])
    recipe['mount_equipment']={'schema_version':1,'design_revision':2,'saddle':saddle,'armor':armor,'bridle':bridle,'emblem':emblem,'contact':contact,'source_part':part['id']}
