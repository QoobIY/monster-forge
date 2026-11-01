"""Thin embroidered motifs baked onto the selected garment's actual surface."""
import numpy as np
from .constructor_surface_fit import mount_front
from tools.creature_workshop.geometry import mesh

LABELS=('Кант с ромбами','Рунная цепь','Солнечные знаки','Переплетение','Ветви и листья',
        'Двойной шеврон','Созвездия','Вертикальные руны','Алхимические печати','Чешуйчатый орнамент')


def garment_support(recipe,slot):
    groups=recipe.get('atlas_material_groups',{})
    return [c for c in recipe['commands'] if c['slot']==slot and
            not any(t in c['part'] for t in ('cloth_motif','ornament_','atlas_emblems_','atlas_belts_','atlas_accessories_',
                'neck','palm','finger','thumb','foot','boot','shoe','toe')) and
            groups.get(c['material'],c['material'].rsplit('_',1)[-1]) not in {'skin','bone','fixed','hair','eyes'}]


def refit(recipe,slot):
    commands=[c for c in recipe['commands'] if 'cloth_motif_stroke' in c['part'] and c['slot']==slot]
    support=garment_support(recipe,slot)
    for c in commands:
        template=c.get('motif_footprint_template')
        if template is None:
            v,_=mesh(c);template={'vertices':v.tolist()};c['motif_footprint_template']=template
        conform_stroke(c,np.asarray(template['vertices']),support)
    recipe['commands'][:]=[c for c in recipe['commands'] if not c.get('motif_outside_garment')]


def clip_polygon(polygon,triangle):
    """Intersect a stroke footprint with an existing garment triangle in XY."""
    cross=lambda a,b:a[0]*b[1]-a[1]*b[0]
    if cross(triangle[1]-triangle[0],triangle[2]-triangle[0])<0:triangle=triangle[::-1]
    out=list(polygon)
    for a,b in zip(triangle,np.roll(triangle,-1,axis=0)):
        incoming=out;out=[]
        if not incoming:break
        for p,q in zip(incoming,incoming[1:]+incoming[:1]):
            hp=cross(b-a,p-a);hq=cross(b-a,q-a)
            if hp>=-1e-10:out.append(p)
            if (hp>=0)!=(hq>=0):out.append(p+(q-p)*hp/(hp-hq))
    if len(out)<3:return None
    unique=[]
    for p in out:
        # Ignore sub-micrometre clipping slivers: their ribbon side walls
        # otherwise collapse into degenerate triangles after export.
        if not unique or np.linalg.norm(p-unique[-1])>1e-6:unique.append(p)
    if len(unique)>1 and np.linalg.norm(unique[0]-unique[-1])<1e-6:unique.pop()
    changed=True
    while changed and len(unique)>3:
        changed=False
        for i in range(len(unique)):
            if abs(cross(unique[i]-unique[i-1],unique[(i+1)%len(unique)]-unique[i]))<1e-9:
                del unique[i];changed=True;break
    if len(unique)<3:return None
    area=sum(cross(p,q) for p,q in zip(unique,unique[1:]+unique[:1]))*.5
    if abs(area)<1e-9:return None
    return np.asarray(unique if area>0 else unique[::-1])


def conform_stroke(command,prototype,support):
    """Thin closed ribbons follow every actual face and stop at garment edges.

    Endpoint-only projection let long tube faces bridge folds and empty seams.
    Clipping to the existing triangles also keeps all intermediate points seated.
    """
    from .constructor_surface_fit import triangles
    from tools.creature_workshop.family_faces import orient_faces
    primitive=command.get('authored_primitive',{})
    sides=int(primitive.get('sides',4));count=len(prototype)//sides
    if not support or count<2:command['motif_outside_garment']=True;return
    tri=triangles(support)
    normals=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    tri=tri[normals[:,2]>1e-10]
    vertices=[];faces=[]
    for i in range(count-1):
        first=prototype[i*sides:(i+1)*sides,:2];second=prototype[(i+1)*sides:(i+2)*sides,:2]
        # Four-sided sweep has two lateral vertices and front/back vertices
        # sharing the centre line. Choose the widest pair in each section.
        a,b=np.unravel_index(np.argmax(((first[:,None]-first[None,:])**2).sum(2)),(sides,sides))
        c,d=np.unravel_index(np.argmax(((second[:,None]-second[None,:])**2).sum(2)),(sides,sides))
        if np.dot(first[b]-first[a],second[d]-second[c])<0:c,d=d,c
        points=sorted({tuple(p) for p in (first[a],first[b],second[d],second[c])})
        cross=lambda o,a,b:(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
        lower=[];upper=[]
        for p in points:
            while len(lower)>=2 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
            lower.append(p)
        for p in reversed(points):
            while len(upper)>=2 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
            upper.append(p)
        footprint=np.asarray(lower[:-1]+upper[:-1])
        if len(footprint)<3:continue
        low,high=footprint.min(0),footprint.max(0)
        candidates=tri[((tri[:,:,:2].max(1)>=low)&(tri[:,:,:2].min(1)<=high)).all(1)]
        for surface in candidates:
            polygon=clip_polygon(footprint,surface[:,:2])
            if polygon is None:continue
            basis=np.column_stack([surface[1,:2]-surface[0,:2],surface[2,:2]-surface[0,:2]])
            bary=np.linalg.solve(basis,(polygon-surface[0,:2]).T).T
            depth=surface[0,2]+bary@(surface[1:,2]-surface[0,2])
            start=len(vertices);n=len(polygon)
            vertices.extend(np.column_stack([polygon,depth+.0012]).tolist())
            vertices.extend(np.column_stack([polygon,depth-.0008]).tolist())
            for j in range(1,n-1):faces.extend([[start,start+j,start+j+1],[start+n,start+n+j+1,start+n+j]])
            for j in range(n):
                k=(j+1)%n;faces.extend([[start+j,start+n+j,start+n+k],[start+j,start+n+k,start+k]])
    if not vertices:command['motif_outside_garment']=True;return
    v=np.asarray(vertices);f=orient_faces(v,np.asarray(faces))
    command.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist(),
        surface_contact_revision={'schema_version':2,'method':'stroke footprints clipped to garment triangles',
            'clearance_metres':.0012,'recess_metres':.0008})
    command.pop('vertex_normals',None)
    command.pop('motif_outside_garment',None)


def apply(recipe,number,slot='torso'):
    if not number:return recipe
    if recipe.get('cloth_motif_revision')==number:return recipe
    support=garment_support(recipe,slot)
    if not support:return recipe
    from .constructor_decor import sculpt
    from .workshop_constructor import default_settings
    from .constructor_portraits import freeze
    b=sculpt(default_settings());b.slot=slot;b.stage=4
    angle=0
    from .constructor_elemental_runes import PATHS as ELEMENTAL_PATHS, ELEMENTS
    def line(points,r=.012):
        b.tube('cloth_motif_stroke','secondary',[[x,y,.30] for x,y in points],[r]*len(points),sides=4)
    def glyph(x,y,kind,scale=1):
        paths={
            **ELEMENTAL_PATHS,
            0:[[[-.018,0],[0,.025],[.018,0],[0,-.025],[-.018,0]]],
            1:[[[0,-.026],[0,.028]],[[0,.018],[.019,.006],[0,-.006]]],
            2:[[[-.022,0],[.022,0]],[[0,-.022],[0,.022]],
               [[-.014,-.014],[.014,.014]],[[.014,-.014],[-.014,.014]]],
            3:[[[-.020,-.02],[.020,.02],[.020,-.02],[-.020,.02],[-.020,-.02]]],
            4:[[[0,-.025],[0,.027]],[[-.018,-.006],[0,.007],[.017,.014]]],
            5:[[[-.025,.014],[0,-.008],[.025,.014]],[[-.025,-.005],[0,-.027],[.025,-.005]]],
            6:[[[-.024,-.012],[-.006,.015],[.02,.007],[.027,-.019]]],
            7:[[[0,-.029],[0,.030]],[[-.018,.015],[0,.004],[.018,.015]],[[0,-.012],[.017,-.026]]],
            8:[[[-.024,-.015],[0,.027],[.024,-.015],[-.024,-.015]],[[-.018,.006],[.018,.006]]],
            9:[[[-.022,.012],[-.014,-.010],[0,-.020],[.014,-.010],[.022,.012]]],
            10:[[[0,-.036],[0,.036]],[[-.022,.024],[0,.009],[.022,.024]],
                [[-.021,-.023],[0,-.009],[.021,-.023]],[[-.028,.036],[-.028,-.036]],[[.028,.036],[.028,-.036]]],
            11:[[[0,-.035],[-.009,-.012],[.007,.012],[0,.035]],
                [[0,.029],[.025,.017],[.017,.006],[.002,.005]],
                [[0,-.029],[-.025,-.017],[-.017,-.006],[-.002,-.005]],
                [[-.025,.029],[-.032,.015],[-.027,.002]],[[.025,-.029],[.032,-.015],[.027,-.002]]],
            12:[[[-.031,.033],[-.021,.004],[0,-.036],[.021,.004],[.031,.033]],
                [[-.029,.013],[0,.023],[.029,.013]],[[0,-.036],[0,.041]],
                [[-.024,-.026],[-.035,-.016],[-.024,-.006]],[[.024,-.026],[.035,-.016],[.024,-.006]]],
        }[kind]
        for p in paths:line([(x+(xx*np.cos(angle)-yy*np.sin(angle))*scale,
                                y+(xx*np.sin(angle)+yy*np.cos(angle))*scale) for xx,yy in p])
    kind=number-1
    if slot=='torso':
        # One large, readable chest sign replaces the tiny repeated tile grid.
        glyph(0,1.57,kind,5.2)
        for c in support:
            if not any(c['part'].endswith(n) for n in ('split_coat_panel','central_tabard','smith_apron','tunic_hem')):continue
            v,_=mesh(c);low,high=v[:,:2].min(0),v[:,:2].max(0)
            if high[1]-low[1]<.18:continue
            x,y=(low+high)/2
            scale=min(4.0,(high[0]-low[0])/.06*.65,(high[1]-low[1])/.06*.70)
            glyph(float(x),float(y),kind,scale)
    elif slot.endswith('_arm') or slot.endswith('_leg'):
        vertices=np.concatenate([mesh(c)[0] for c in support])
        arm=slot.endswith('_arm')
        for y,scale in ((1.55,2.8),(1.23,2.5)) if arm else ((.83,3.3),(.29,2.9)):
            near=vertices[np.abs(vertices[:,1]-y)<.045]
            if not len(near):continue
            x=float((near[:,0].min()+near[:,0].max())*.5)
            if arm:
                high=vertices[np.abs(vertices[:,1]-(y+.07))<.045]
                low=vertices[np.abs(vertices[:,1]-(y-.07))<.045]
                dx=float(high[:,0].mean()-low[:,0].mean()) if len(high) and len(low) else 0
                angle=-np.arctan2(dx,.14)
            glyph(x,y,kind,scale)
    commands,palette=freeze(b,'cloth_motif');recipe['palette'].update(palette)
    for c in commands:c['slot']=slot
    mount_front(commands,support,relief=-.002,group_base=.30)
    commands=[c for c in commands if 'surface_contact_revision' in c]
    recipe['commands'].extend(commands);recipe['commands'].sort(key=lambda c:c['stage'])
    recipe['atlas_material_groups']=dict(recipe.get('atlas_material_groups',{}),**{k:'secondary' for k in palette if k.endswith('_secondary')})
    # The same colour channel serves native and reference costumes.
    secondary=recipe.get('selected_pattern_color')
    if secondary:
        for k in palette:
            if k.endswith('_secondary'):recipe['palette'][k]=secondary.lstrip('#')
    recipe['cloth_motif_revision']=number
    if number>=11:
        recipe['cloth_motif_description']={11:'Крупные древние руны: угловатые резные знаки, парные боковые штрихи и центральный стержень.',
            12:'Крупные эльфийские руны: плавно изогнутые ветвящиеся знаки с парными листовидными петлями.',
            13:'Крупные демонические руны: рогатый сигил, острые крюки и нисходящий клин.',
            **{e['number']:e['description'] for e in ELEMENTS.values()}}[number]
    return recipe
