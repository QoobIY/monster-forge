"""Bake ornament and scalp contact into part geometry, without changing rigging."""
import numpy as np
from tools.creature_workshop.geometry import mesh
from .constructor_face_fit import surfaces, front_depth


def triangles(commands):
    return np.concatenate([mesh(c)[0][mesh(c)[1]] for c in commands])


def radial_hit(tri, point, direction):
    a=tri[:,0];e1=tri[:,1]-a;e2=tri[:,2]-a
    h=np.cross(np.broadcast_to(direction,e2.shape),e2);det=np.sum(e1*h,axis=1)
    valid=np.abs(det)>1e-10;inv=np.zeros_like(det);inv[valid]=1/det[valid]
    tvec=point-a;u=np.sum(tvec*h,axis=1)*inv;q=np.cross(tvec,e1)
    v=np.sum(direction*q,axis=1)*inv;t=np.sum(e2*q,axis=1)*inv
    hit=valid&(u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)&(t>=0)
    return float(t[hit].max()) if hit.any() else None


def scalp_shell(face,top):
    """Reuse the selected skull's planes, with a front/temple/nape hairline."""
    vertices=[];indices={};faces=[]
    def index(p):
        key=tuple(np.round(p,10))
        if key not in indices:indices[key]=len(vertices);vertices.append(p)
        return indices[key]
    def height(p):
        line=(top-.185+.065*np.clip(p[2]/.17,0,1)
              -.255*np.clip(-p[2]/.17,0,1)
              -.055*np.clip(abs(p[0])/.22,0,1))
        return p[1]-line
    for triangle in triangles(face):
        polygon=[]
        for a,b in zip(triangle,np.roll(triangle,-1,axis=0)):
            ha,hb=height(a),height(b)
            if ha>=0:polygon.append(a)
            if (ha>=0)!=(hb>=0):polygon.append(a+(b-a)*ha/(ha-hb))
        if len(polygon)<3:continue
        # A hairline passing through a skull vertex can emit that endpoint
        # both as a retained vertex and as an intersection. The existing weld
        # identifies them; triangulate each endpoint only once, so a clipped
        # point or edge cannot become a zero-area face or a self-edge.
        ids=list(dict.fromkeys(index(p) for p in polygon))
        for i in range(1,len(ids)-1):faces.append([ids[0],ids[i],ids[i+1]])
    v=np.asarray(vertices);f=np.asarray(faces);n=len(v)
    origin=np.array([0,top-.215,.005]);direction=v-origin
    direction/=np.linalg.norm(direction,axis=1)[:,None]
    v=np.concatenate([v+direction*.020,v-direction*.004])
    edges={}
    for tri in f:
        for a,b in zip(tri,np.roll(tri,-1)):
            key=tuple(sorted((int(a),int(b))))
            if key in edges:del edges[key]
            else:edges[key]=(int(a),int(b))
    closed=f.tolist()+(f[:,::-1]+n).tolist()
    for a,b in edges.values():closed.extend([[a,a+n,b+n],[a,b+n,b]])
    from tools.creature_workshop.family_faces import orient_faces
    return v,orient_faces(v,np.asarray(closed))


def round_nape(recipe):
    for c in surfaces(recipe):
        if c.get('nape_volume_revision',{}).get('schema_version')==3:continue
        source=c.get('authored_primitive',c);topology=source.get('head_topology',c.get('head_topology',{}))
        names=topology.get('landmarks')
        if not names:continue
        v,f=mesh(c);v=v.copy();start=max(names.values())+1
        length=topology['parameters'].get('length',1)
        y=2.335+(v[start:,1]-2.335)/length
        # Authored sagittal outline: a full occiput, then a short inward turn
        # at the nape. The previous outline ran diagonally all the way to chin.
        profile_y=[2.025,2.08,2.135,2.17,2.28,2.37,2.43,2.48,2.555,2.585]
        profile_z=[.015,-.085,-.135,-.155,-.168,-.180,-.174,-.140,-.080,-.030]
        rear=v[start:];target=np.interp(y,profile_y,profile_z)
        rear[:,2]=np.minimum(rear[:,2],target)
        rear[:,0]*=1+.09*np.clip((2.30-y)/.16,0,1)
        c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist(),
                 nape_volume_revision={'schema_version':3,'profile_y':profile_y,'profile_z':profile_z,'front_vertex_count':start})
        c.pop('vertex_normals',None)


def fit_scalp(recipe):
    face=surfaces(recipe)
    if not face:return
    tri=triangles(face);head_vertices=np.concatenate([mesh(c)[0] for c in face]);top=head_vertices[:,1].max()
    for c in recipe['commands']:
        part=c['part'];source=c.get('authored_primitive',c)
        if not any(word in part for word in ('hair_','hair_cap','scalp')) or any(w in part for w in ('brow','beard','mustache')):continue
        if 'hair_tie' in part:continue
        saved=c.get('scalp_contact_template')
        if saved is None:
            v,f=mesh(c);saved={'vertices':v.tolist(),'faces':f.tolist()}
        c['scalp_contact_template']=saved;v=np.asarray(saved['vertices']).copy();f=np.asarray(saved['faces'])
        # A crown braid is a strand, not a scalp cap. Substring matching used
        # to replace every braid bead with another complete skull shell.
        shell=part.endswith(('hair_crown','hair_cap','scalp'))
        if shell:
            v,f=scalp_shell(face,top)
        elif source.get('path') and source.get('sides'):
            count=int(source['sides']);root=v[:count].mean(axis=0)
            origin=np.array([0,top-.215,.005]);d=root-origin;norm=np.linalg.norm(d)
            if norm>1e-9:
                d/=norm;distance=radial_hit(tri,origin,d)
                if distance is not None:
                    radius=source.get('radii',[.04])[0]
                    target=origin+d*(distance+radius*.30)
                    delta=target-root
                    c['scalp_root_delta']=delta.tolist()
                    # Move complete locks coherently: settling only the first
                    # ring previously stretched the hair into detached spikes.
                    v+=delta
        elif 'hair_mohawk' in part and source.get('stations'):
            count=int(source['sides']);low=float(v[:,1].min())
            # The crest attaches at its lowest ring, never at its high tips.
            high=float(v[:,1].max())
            v[:,1]=top-.115+(v[:,1]-low)/(high-low)*.235
            for p in v[:count]:
                origin=np.array([0,p[1],.005]);d=np.array([p[0],0,p[2]-.005]);norm=np.linalg.norm(d)
                if norm<1e-9:continue
                d/=norm;distance=radial_hit(tri,origin,d)
                if distance is not None and np.linalg.norm(p-origin)>distance:p[:]=origin+d*(distance-.004)
        elif source.get('op')=='ellipsoid' and 'center' in source:
            # Curls/afro lobes are volumes. Move their attachment as a whole;
            # flattening the upper vertices would destroy the hairstyle.
            center=np.asarray(source['center'],float);radius=np.asarray(source['radii'],float)
            if 'braid_lobe' in part and center[1]<top-.20:
                # Hanging braid segments follow the braid core, not the scalp.
                # Pulling every bead toward the head bunches the entire braid.
                c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist())
                continue
            origin=np.array([0,top-.215,.005]);d=center-origin;norm=np.linalg.norm(d)
            if norm>1e-9:
                d/=norm;distance=radial_hit(tri,origin,d)
                if distance is not None:
                    target=origin+d*(distance+min(radius[0],radius[2])*.52)
                    v+=target-center
        else:
            # Fringe panels and long side sheets retain their hanging shape.
            # Their upper attachment follows the actual scalp instead of a box.
            high=float(v[:,1].max());mask=v[:,1]>=high-.055
            if high<top-.10:continue
            root=v[mask].mean(axis=0);origin=np.array([0,top-.215,.005])
            d=root-origin;norm=np.linalg.norm(d)
            if norm>1e-9:
                d/=norm;distance=radial_hit(tri,origin,d)
                if distance is not None:
                    target=origin+d*(distance+.012)
                    delta=target-root
                    c['scalp_root_delta']=delta.tolist()
                    v+=delta
        c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist(),
                 scalp_contact_revision={'schema_version':3,'method':'anatomical nape hairline and rigid strand attachment','shell_clearance_metres':.020})
        c.pop('vertex_normals',None)
    ponytail=next((c for c in recipe['commands'] if 'ponytail' in c['part'] and 'scalp_root_delta' in c),None)
    if ponytail:
        for c in recipe['commands']:
            if 'hair_tie' not in c['part']:continue
            saved=c.get('scalp_contact_template')
            if saved is None:
                v,f=mesh(c);saved={'vertices':v.tolist(),'faces':f.tolist()}
            c['scalp_contact_template']=saved
            c.update(op='indexed_mesh',vertices=(np.asarray(saved['vertices'])+ponytail['scalp_root_delta']).tolist(),faces=saved['faces'])
    # Braids are authored as cores plus overlapping lobes. Every lobe follows
    # its own core, including the hanging ends and the crown braid segments.
    for c in recipe['commands']:
        if 'braid' not in c['part'] or 'lobe' not in c['part']:continue
        base=c['part'].removesuffix('_lobe')
        cores=[x for x in recipe['commands'] if x['part'] in {base,base+'_core'} and 'scalp_root_delta' in x]
        if not cores:continue
        saved=c.get('scalp_contact_template')
        if saved is None:continue
        center=np.mean(saved['vertices'],axis=0)
        core=min(cores,key=lambda x:np.linalg.norm(np.mean(x['scalp_contact_template']['vertices'],axis=0)-center))
        c.update(op='indexed_mesh',vertices=(np.asarray(saved['vertices'])+core['scalp_root_delta']).tolist(),faces=saved['faces'])
    from .constructor_hair_shape import complete_back
    complete_back(recipe,face,top)


def torso_support(recipe):
    return [c for c in recipe['commands'] if c['slot']=='torso' and not any(w in c['part'] for w in
            ('ornament_','atlas_emblems_','atlas_belts_','atlas_accessories_','cloth_motif_','cloth_rune_',
             'badge','fastener','buckle','pouch','hanging_book','pendant','gem'))]


def fit_costume_details(recipe,slot):
    """Seat authored clothing layers before mounting separate decorations."""
    layers=(('broad_breastplate',),
            ('coat_lapel','standing_coat_lapel','ranger_diagonal_strap','apron_strap',
             'shoulder_plate','shoulder_lower_plate','knee_plate','shin_plate'),
            ('chest_emblem','chest_tabard_trim','coat_edge','tabard_border',
             'belt_diamond','belt_buckle','apron_pocket','tunic_fastener'))
    details=[c for c in recipe['commands'] if c['slot']==slot and 'ornament_shoulder_' not in c['part'] and
             any(c['part'].endswith(name) for layer in layers for name in layer)]
    support=[c for c in recipe['commands'] if c['slot']==slot and c not in details
             and not any(t in c['part'] for t in ('ornament_','atlas_emblems_',
                 'atlas_belts_','atlas_accessories_','cloth_motif_'))]
    for names in layers:
        for c in details:
            if not any(c['part'].endswith(name) for name in names):continue
            v,_=mesh(c)
            # Thin tube trims have their centre line on the supporting cloth;
            # solid panels embed their rear face by two millimetres.
            tube=any(c['part'].endswith(n) for n in ('coat_edge','tabard_border','chest_tabard_trim','ranger_diagonal_strap','apron_strap'))
            base=float((v[:,2].min()+v[:,2].max())*.5 if tube else v[:,2].min())
            mount_front([c],support,group_base=base,relief=.002,nearest_bounds=True)
            if c.get('surface_contact_revision'):support.append(c)


def mount_front(commands,support, *, relief=.002, group_base=None, rigid=False,nearest_bounds=False):
    if not commands or not support:return
    base=min(float(mesh(c)[0][:,2].min()) for c in commands) if group_base is None else group_base
    rigid_depth=None
    if rigid:
        points=np.concatenate([mesh(c)[0] for c in commands]);x=float(points[:,0].mean());y=float(points[:,1].mean())
        for factor in (1,.9,.75,.5,0):
            candidate=front_depth(support,np.asarray([[x*factor,y]]))[0]
            if np.isfinite(candidate):rigid_depth=float(candidate);break
    for c in commands:
        saved=c.get('surface_contact_template')
        if saved is None:
            v,f=mesh(c);saved={'vertices':v.tolist(),'faces':f.tolist(),'base_z':base}
        c['surface_contact_template']=saved;v=np.asarray(saved['vertices']).copy();f=np.asarray(saved['faces'])
        depth=np.full(len(v),rigid_depth) if rigid_depth is not None else front_depth(support,v[:,:2]);valid=np.isfinite(depth)
        if not valid.any():
            if not nearest_bounds:continue
            skin=np.concatenate([mesh(s)[0] for s in support])
            distance=np.sum((v[:,None,:2]-skin[None,:,:2])**2,axis=2)
            depth=skin[distance.argmin(axis=1),2];valid=np.isfinite(depth)
        # Minor border overhangs use the nearest valid contact on the same component.
        if not valid.all():
            distance=np.sum((v[~valid,:2,None]-v[valid,:2].T[None,:,:])**2,axis=1)
            depth[~valid]=depth[valid][distance.argmin(axis=1)]
        v[:,2]=depth+(v[:,2]-saved['base_z'])-relief
        from tools.creature_workshop.family_faces import orient_faces
        f=orient_faces(v,f)
        c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist(),
                 surface_contact_revision={'schema_version':1,'method':'baked front surface intersection','root_penetration_metres':relief})
        c.pop('vertex_normals',None)


def fit_ornaments(recipe):
    support=torso_support(recipe)
    badges=[c for c in recipe['commands'] if c['part'].startswith('atlas_emblems_') or
            (c['part'].startswith('ornament_') and any(w in c['part'] for w in
             ('badge','lion','sun','moon','star','skull','jaw','eye','leaf','bolt','wing','diamond','serpent')) and c['slot']=='torso')]
    mount_front(badges,support)


def fit_belts(recipe):
    support=torso_support(recipe)
    if not support:return
    parts=[c for c in recipe['commands'] if c['part'].startswith(('atlas_belts_','atlas_accessories_')) or
           (c['slot']=='torso' and c['part'].startswith('ornament_') and any(w in c['part'] for w in
            ('buckle','pouch','waist_band','leather_keeper','belt_stitch','belt_gem','flask','cork','scroll','book','medallion','tool','tab_','attachment_tab','gem_setting','chain')))]
    bands=[c for c in parts if c['part'].endswith('ornament_belt') or 'waist_band' in c['part']]
    tri=triangles(support)
    for c in bands:
        saved=c.get('waist_contact_template')
        if saved is None:
            v,f=mesh(c);saved={'vertices':v.tolist(),'faces':f.tolist()}
        c['waist_contact_template']=saved;v=np.asarray(saved['vertices']).copy();f=np.asarray(saved['faces'])
        for p in v:
            origin=np.array([0,p[1],0]);d=np.array([p[0],0,p[2]]);norm=np.linalg.norm(d)
            if norm<1e-9:continue
            d/=norm;distance=radial_hit(tri,origin,d)
            if distance is not None:p[[0,2]]=(origin+d*(distance+.007))[[0,2]]
        c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist(),waist_contact_revision={'schema_version':1,'clearance_metres':.007})
    buckle=[c for c in parts if 'buckle' in c['part']]
    mount_front(buckle,support,relief=-.007)
    rest=[c for c in parts if c not in bands and c not in buckle]
    # Left/right hanging assemblies keep the depth order of flap, clasp and body.
    for sign in (-1,1):
        group=[c for c in rest if (mesh(c)[0][:,0].mean()<0)==(sign<0)]
        mount_front(group,support,relief=-.004,rigid=True)


def fit_headwear(recipe):
    face=surfaces(recipe)
    if not face:return
    source=face[0].get('authored_primitive',face[0]);topology=source.get('head_topology',face[0].get('head_topology',{}))
    params=topology.get('parameters',{});width=params.get('width',.21)/.21;length=params.get('length',1)
    parts=[c for c in recipe['commands'] if c['part'].startswith('atlas_headwear_') or
           (c['slot']=='head' and c['part'].startswith('ornament_'))]
    for c in parts:
        saved=c.get('headwear_fit_template')
        if saved is None:
            v,f=mesh(c);saved={'vertices':v.tolist(),'faces':f.tolist()}
        c['headwear_fit_template']=saved;v=np.asarray(saved['vertices']).copy();f=np.asarray(saved['faces'])
        v[:,0]*=width;v[:,1]=2.335+(v[:,1]-2.335)*length
        c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist())
        c['headwear_contact_revision']={'schema_version':1,'head_width_factor':width,'head_length_factor':length}
    bands=[c for c in parts if any(w in c['part'] for w in ('ornament_circlet','goggle_strap')) and 'gem' not in c['part']]
    tri=triangles(face);top=tri[:,:,1].max()
    for c in bands:
        v,f=mesh(c);v=v.copy()
        primitive=c.get('authored_primitive',c)
        if primitive.get('path') and primitive.get('sides'):
            count=int(primitive['sides'])
            for start in range(0,len(primitive['path'])*count,count):
                center=v[start:start+count].mean(axis=0);origin=np.array([0,min(center[1],top-.005),.005])
                d=np.array([center[0],0,center[2]-.005]);norm=np.linalg.norm(d)
                if norm<1e-9:continue
                d/=norm;distance=radial_hit(tri,origin,d)
                if distance is not None:v[start:start+count]+=origin+d*(distance+.021)-center
            c['vertices']=v.tolist();continue
        for p in v:
            origin=np.array([0,min(p[1],top-.005),.005]);d=np.array([p[0],0,p[2]-.005]);norm=np.linalg.norm(d)
            if norm<1e-9:continue
            d/=norm;distance=radial_hit(tri,origin,d)
            if distance is not None:p[[0,2]]=(origin+d*(distance+.018))[[0,2]]
        c['vertices']=v.tolist()
    front=[c for c in parts if c not in bands and not any(w in c['part'] for w in ('earring','horn_cap','cap_engraving','head_feather','feather_shaft','feather_barb','laurel'))]
    circlet=any('circlet' in c['part'] or 'crown_point' in c['part'] or 'tiara_arch' in c['part'] for c in parts)
    mount_front(front,face,relief=.001,group_base=.18 if circlet else None)
    from .constructor_headwear_fit import apply as fit_over_hair
    fit_over_hair(recipe,parts,bands)


def apply(recipe,slot):
    if slot=='head':round_nape(recipe);fit_scalp(recipe);fit_headwear(recipe)
    if slot!='head' and slot!='back_attachment':fit_costume_details(recipe,slot)
    if slot=='torso':fit_ornaments(recipe);fit_belts(recipe)
    if slot in {'torso','left_arm','right_arm','left_leg','right_leg'}:
        from .constructor_cloth_motifs import refit
        refit(recipe,slot)
    return recipe
