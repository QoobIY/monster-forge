"""Authored helmet topology fitted to the final selected skull, before neck drop."""
import math
import numpy as np
from .constructor_face_fit import surfaces
from .constructor_headwear_fit import hair_support
from .constructor_surface_fit import triangles, radial_hit
from .constructor_decor import sculpt
from .constructor_portraits import freeze
from tools.creature_workshop.geometry import mesh
from tools.creature_workshop.family_faces import orient_faces

DESCRIPTIONS = {
    'horned_helmet': 'Открытый стальной шлем викинга: гранёный купол, усиленный обод, переносица и два крупных изогнутых костяных рога. Под шлемом сохраняются косы.',
    'wizard_hat': 'Колпак мага: широкий отогнутый обод, высокая изогнутая коническая тулья, кожаный пояс с пряжкой и золотые звёзды.',
    'winged_helmet': 'Открытый гранёный шлем с парными белыми ангельскими крыльями: изогнутый веер маховых перьев и два перекрывающихся ряда кроющих перьев, ободом и переносицей.',
    'halo': 'Приподнятый золотой нимб: объёмное кольцо над всей причёской, восемь лучей и внутренний обод.',
    'closed_helmet': 'Шлем-котелок с округлым куполом и ровными боковыми стенками. Узкая горизонтальная прорезь для глаз соединяется с вертикальным центральным вырезом до нижнего края; щёки закрыты.',
    'crested_helmet': 'Открытый шлем с защитой щёк, длинным продольным гребнем, цветным плюмажем и окантовкой.',
    'barbute': 'Барбют с Т-образным вырезом для глаз и носа, вытянутой защитой щёк и центральным ребром.',
}

from .constructor_hoods import DESCRIPTIONS as HOODS
DESCRIPTIONS.update(HOODS)
from .constructor_horns import DESCRIPTIONS as HORNS
DESCRIPTIONS.update(HORNS)

def apply(recipe, settings):
    kind = settings['decor']['headwear']
    if kind not in DESCRIPTIONS or settings['reference_parts']['headwear']:
        return
    face = surfaces(recipe)
    if not face:
        # Native creature heads use their original skin/muzzle volumes.
        face = [c for c in recipe['commands'] if c['slot']=='head' and
                not any(t in c['part'] for t in ('hair','eye','iris','pupil','ornament','beard','mustache'))]
    if not face:return
    v = np.concatenate([mesh(c)[0] for c in face]);low, high = v.min(0), v.max(0)
    top = float(high[1]);chin = float(low[1]);height = top-chin
    iris = [c for c in recipe['commands'] if any(t in c['part'] for t in ('visible_iris','visible_pupil'))]
    eye = float(np.concatenate([mesh(c)[0] for c in iris])[:,1].mean()) if iris else chin+height*.57
    b = sculpt(settings);b.slot='head';b.stage=4
    b.palette['metal']=settings['colors']['metal'].lstrip('#') if settings['colors']['metal'] else 'a3adb5'
    hair = hair_support(recipe)
    # A scalp cap can extend below the rim as one connected mesh. It must
    # participate in fitting even when hanging braids are retained unchanged.
    scalp = [c for c in hair if any(t in c['part'] for t in ('crown','cap','scalp'))
             and not any(t in c['part'] for t in ('braid','tail','bun'))]
    panels=[]
    if kind in HORNS:
        from .constructor_horns import author as horns
        horns(b,kind,face,v,settings)
    elif kind in HOODS:
        from .constructor_hoods import author as hood
        hood(b,kind,v,eye,hair)
    elif kind=='halo':
        hair_top=max([top]+[float(mesh(c)[0][:,1].max()) for c in hair])
        y=hair_top+.095;r=max(.29,float(np.max(np.abs(v[:,0])))+.06)
        path=[[math.sin(a)*r,y,.005+math.cos(a)*r] for a in np.linspace(0,2*math.pi,25)]
        b.tube('equipment_halo_ring','accent',path,[.019]*25,sides=6)
        inner=[[p[0]*.90,p[1],.005+(p[2]-.005)*.90] for p in path]
        b.tube('equipment_halo_inner','metal',inner,[.006]*25,sides=4)
        for a in np.linspace(0,2*math.pi,8,endpoint=False):
            p=np.array([math.sin(a)*r,y,.005+math.cos(a)*r])
            q=p+np.array([math.sin(a)*.07,.02,math.cos(a)*.07])
            b.tube('equipment_halo_ray','accent',[p.tolist(),q.tolist()],[.011,.002],sides=5)
    elif kind=='wizard_hat':
        y=eye+.11;radius=max(.25,float(np.abs(v[:,0]).max())+.065)
        b.loft('equipment_wizard_brim','secondary',[[y,0,-.025,radius*1.65,radius*1.45],[y+.025,0,-.025,radius*1.65,radius*1.45]],sides=20)
        b.loft('equipment_wizard_cone','cloth',[[y+.02,0,-.025,radius,radius],[top+.12,0,-.04,radius*.75,radius*.75],[top+.36,.035,-.075,radius*.40,radius*.40],[top+.55,.11,-.11,.055,.055],[top+.59,.19,-.13,.005,.005]],sides=16)
        b.loft('equipment_wizard_band','leather',[[y+.032,0,-.025,radius+.009,radius+.009],[y+.088,0,-.028,radius*.94+.009,radius*.94+.009]],sides=20)
        b.box('equipment_wizard_buckle','accent',[0,y+.062,radius-.018],[.065,.047,.016])
        for x,dy in ((-.055,.15),(.06,.25),(0,.36)):
            z=-.04+radius*(1-dy/.62)
            points=[[x+math.cos(a)*(.028 if i%2==0 else .012),top+dy+math.sin(a)*(.028 if i%2==0 else .012),z] for i,a in enumerate(np.linspace(math.pi/2,math.pi/2+2*math.pi,10,endpoint=False))]
            b.panel3('equipment_wizard_star','accent',points,.008)
    else:
        # Rounded rear corners need room between angular helmet stations,
        # including the interiors of their broad, flat side panels.
        clearance = .040 if recipe.get('human_head_shape_revision') else .028
        if scalp:
            top=max(top,max(float(mesh(c)[0][:,1].max()) for c in scalp))
        tri=triangles(face+scalp);center_z=float((low[2]+high[2])*.5)
        halfwidth=max(.14,float(np.max(np.abs(v[:,0]))))
        halfdepth=max(.16,float((high[2]-low[2])*.5))
        base=chin+.025 if kind in {'closed_helmet','barbute','crested_helmet'} else eye+.04
        stations=[base,eye-.030,eye+.031,top-.09,top-.015,top+.055]
        if kind=='closed_helmet':
            base=chin-.005
            stations=[base,eye-.016,eye+.016,top-.025,top+.025,top+.075,top+.115,top+.14]
        stations=sorted(set(y for y in stations if y>=base))
        count=24;angles=np.linspace(-math.pi,math.pi,count+1)
        if kind=='closed_helmet':angles=np.asarray(sorted(set([*angles,-.14,.14])))
        def point(y,a):
            if kind=='closed_helmet':
                dome=np.interp(y,[top-.025,top+.025,top+.075,top+.115,top+.14],[1,.96,.80,.51,.10])
                depth=max(halfdepth+.065,float(v[:,2].max()-center_z)+.065)
                d=np.array([np.sin(a),0,np.cos(a)]);origin=np.array([0,min(y,top-.001),center_z])
                hit=radial_hit(tri,origin,d) if y<top else None
                radius=1/math.sqrt((d[0]/(halfwidth+.065))**2+(d[2]/depth)**2)*dome
                radius=max(radius,hit+.045) if hit is not None else radius
                return origin+np.array([d[0]*radius,y-origin[1],d[2]*radius])
            origin=np.array([0,min(y,top-.006),center_z]);d=np.array([math.sin(a),0,math.cos(a)])
            hit=radial_hit(tri,origin,d)
            fallback=1/math.sqrt((d[0]/halfwidth)**2+(d[2]/halfdepth)**2)
            radius=(hit if hit is not None else fallback)+clearance
            # Hold the rim broad at the temples; taper only the upper dome.
            if y>top-.09:
                dome=np.interp(y,[top-.09,top-.015,top+.055],[1,.79,.16])
                radius=max((fallback+clearance)*dome,hit+clearance) if hit is not None else (fallback+clearance)*dome
            p=np.array([d[0]*radius,y,center_z+d[2]*radius])
            if abs(a)<.82 and y<=top-.09:
                anatomy=[c for c in recipe['commands'] if c['slot']=='head' and
                    any(t in c['part'] for t in ('nose','brow','mouth','lip')) and
                    not any(t in c['part'] for t in ('beard','mustache'))]
                if anatomy:
                    from .constructor_face_fit import front_depth
                    depth=front_depth(face+anatomy,np.asarray([[p[0],y]]))[0]
                    if np.isfinite(depth):p[2]=max(p[2],depth+.034)
                if kind=='closed_helmet' and y<eye-.025:
                    p[2]=max(p[2],float(v[:,2].max())+.035)
            return p
        panels=[]
        def panel(name,points):
            pts=np.asarray(points);inside=pts.copy()
            for p in inside:
                if name=='equipment_helmet_crown':
                    p[1]-=.016
                    continue
                d=np.array([p[0],0,p[2]-center_z]);norm=np.linalg.norm(d)
                if norm:p-=d/norm*.016
            verts=np.concatenate([pts,inside]);n=len(pts)
            faces=[[0,i,i+1] for i in range(1,n-1)]+[[n,n+i+1,n+i] for i in range(1,n-1)]
            for i in range(n):
                j=(i+1)%n;faces.extend([[i,n+i,n+j],[i,n+j,j]])
            faces=np.asarray(orient_faces(verts,np.asarray(faces)))
            panels.append({'id':f'helmet-{len(panels)}','slot':'head','stage':4,'part':name,
                'material':'equipment_metal','op':'indexed_mesh','vertices':verts.tolist(),'faces':faces.tolist(),
                'purpose':DESCRIPTIONS[kind]})
        for y0,y1 in zip(stations,stations[1:]):
            for a0,a1 in zip(angles,angles[1:]):
                mid=(a0+a1)*.5;front=abs(mid)<.82
                slit=y0>=eye-.031 and y1<=eye+.032
                opening=(front and slit) if kind=='closed_helmet' else (
                    front and y1<=eye+.032)
                if kind=='closed_helmet':
                    slit=y0>=eye-.017 and y1<=eye+.017
                    opening=front and slit or abs(mid)<.14 and y1<=eye-.015
                if kind=='barbute':opening=front and slit or abs(mid)<.16 and y1<=eye-.029
                if opening:continue
                panel('equipment_helmet_shell',[point(y0,a0),point(y0,a1),point(y1,a1),point(y1,a0)])
        panel('equipment_helmet_crown',[point(stations[-1],a) for a in angles[:-1]])
        rim=[point(base,a).tolist() for a in angles]
        # Open-face variants stop the lower trim before the face opening.
        if kind!='closed_helmet':rim=[p for a,p in zip(angles,rim) if abs(a)>=.82]
        # Separate arcs avoid drawing a band across the open face.
        for side in (-1,1):
            arc=[point(base,a).tolist() for a in angles if side*a>=.82]
            if len(arc)>1:b.tube('equipment_helmet_rim','accent',arc,[.011]*len(arc),sides=5)
        if kind=='closed_helmet':
            # Riveted reinforcing arcs follow the shell rather than float above it.
            for y in (eye+.045,top-.025):
                arc=[point(y,a).tolist() for a in angles if abs(a)>=.85]
                b.tube('equipment_helmet_reinforcement','accent',arc,[.006]*len(arc),sides=5)
            for a in (-2.5,-1.6,-.95,.95,1.6,2.5):
                p=point(eye+.045,a)
                b.oval('equipment_helmet_rivet','accent',p.tolist(),[.009,.009,.009],sides=6)
            for sign in (-1,1):
                edge=[point(base,sign*.14),point(eye-.016,sign*.14)]
                b.tube('equipment_helmet_opening_edge','metal',[p.tolist() for p in edge],[.005,.005],sides=5)
            for sign in (-1,1):
                for i in range(3):
                    p=point(chin+.085+i*.025,sign*.43);p[2]+=.009
                    b.oval('equipment_helmet_vent','leather',p.tolist(),[.006,.009,.004],sides=5)
        if kind=='horned_helmet':
            b.palette['horn_bone']='e0d5b4'
            for sign in (-1,1):
                anchor=point(top-.11,sign*math.pi/2)
                path=[anchor.tolist(), (anchor+[sign*.11,.04,0]).tolist(),
                      (anchor+[sign*.24,.13,-.015]).tolist(),
                      (anchor+[sign*.29,.27,-.04]).tolist(),
                      (anchor+[sign*.25,.37,-.065]).tolist()]
                b.oval('equipment_helmet_horn_mount','accent',anchor.tolist(),[.072,.073,.069],sides=10)
                b.tube('equipment_helmet_horn','horn_bone',path,[.065,.061,.043,.023,.002],sides=9)
            b.tube('equipment_helmet_nasal','accent',
                   [point(top-.08,0).tolist(),point(eye+.04,0).tolist(),
                    (point(eye+.04,0)+[0,-.12,.015]).tolist()],
                   [.019,.018,.012],sides=6)
        if kind=='winged_helmet':
            for sign in (-1,1):
                anchor=point(top-.095,sign*math.pi/2)
                b.oval('equipment_helmet_wing_mount','accent',anchor.tolist(),[.026,.055,.045],sides=8)
                from tools.creature_workshop.feather_wings import helmet_wings
                helmet_wings(b,anchor,sign)
        if kind in {'crested_helmet','barbute'}:
            b.tube('equipment_helmet_spine','accent',[[0,top+.033,center_z-.17],[0,top+.08,center_z],
                [0,top+.033,center_z+.16]],[.018,.019,.013],sides=6)
        if kind=='crested_helmet':
            for i in range(9):
                z=center_z-.20+i*.05;rise=.17+.05*math.sin(i*math.pi/8)
                b.oval('equipment_helmet_plume','secondary',[0,top+.08+rise*.5,z],[.032,rise*.5,.04],sides=6)
        # Covered hair is tucked inside the helmet. Hanging braids/tails below
        # the rim retain their authored geometry; selecting a helmet keeps hair.
        covered=hair
        if kind=='closed_helmet':covered=hair+[c for c in recipe['commands'] if any(t in c['part'] for t in ('beard','mustache'))]
        for c in covered:
            h,f=mesh(c);h=h.copy()
            # Each authored lock remains a solid volume. Per-vertex radial
            # clamping flattened both sides of thin braid lobes into one face.
            # Hanging locks remain outside; covered locks use a positive affine
            # transform inside the skull, preserving their topology and volume.
            if any(c is cap for cap in scalp) or float(h[:,1].min())<base-.02:continue
            radial=np.linalg.norm(h[:,[0,2]]-[0,center_z],axis=1)
            factor=min(.72,halfwidth*.62/max(float(radial.max()),1e-9))
            h[:,0]*=factor;h[:,2]=center_z+(h[:,2]-center_z)*factor
            centre_y=eye+.05
            vertical=min(.72,(top-.065-centre_y)/max(float(h[:,1].max()-centre_y),1e-9))
            vertical=max(.08,vertical)
            h[:,1]=centre_y+(h[:,1]-centre_y)*vertical
            c.update(op='indexed_mesh',vertices=h.tolist(),faces=f.tolist())
            c['helmet_hair_revision']={'schema_version':1,'method':'covered hair tucked inside helmet; hanging hair retained'}
    commands,palette=freeze(b,'equipment');recipe['palette'].update(palette)
    if kind!='halo':
        recipe['palette']['equipment_metal']=b.palette['metal'];commands+=panels
    for c in commands:
        c['slot']='head';c['helmet_revision']={'schema_version':1,'variant':kind,'description_ru':DESCRIPTIONS[kind]}
        if kind in {'horned_helmet','winged_helmet','crested_helmet','barbute'}:
            c['helmet_revision']['scalp_clearance_metres'] = clearance
    recipe['commands'].extend(commands);recipe['commands'].sort(key=lambda c:c['stage'])
