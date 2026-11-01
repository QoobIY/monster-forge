"""Bake jaw edits and facial attachments into the selected head revision."""
import numpy as np
from tools.creature_workshop.geometry import mesh

FACE_NAMES=('face_large_planes','traced_reference_face','facial_topology')

def surfaces(recipe):
    if 'own_body_design' in recipe:
        return [c for c in recipe['commands'] if c['part'] in {'animal_cranium','stone_cranium'}]
    if 'racial_anatomy_revision' in recipe:
        return [c for c in recipe['commands'] if c['part'] in {'bovine_cranium','orc_cranium','goblin_cranium','rounded_cranium','forehead','maxilla','mandible_chin'}]
    return [c for c in recipe['commands'] if any(c['part'].endswith(n) for n in FACE_NAMES)]

def front_depth(commands,xy):
    """Exact +Z intersections with the selected piecewise planar face."""
    triangles=np.concatenate([mesh(c)[0][mesh(c)[1]] for c in commands])
    a,b,c=triangles[:,0],triangles[:,1],triangles[:,2]
    u=b[:,:2]-a[:,:2];v=c[:,:2]-a[:,:2]
    det=u[:,0]*v[:,1]-u[:,1]*v[:,0];valid=np.abs(det)>1e-12
    a,u,v,det=a[valid],u[valid],v[valid],det[valid]
    dz1=(triangles[valid,1]-a)[:,2];dz2=(triangles[valid,2]-a)[:,2]
    result=[]
    for p in xy:
        d=p-a[:,:2]
        s=(d[:,0]*v[:,1]-d[:,1]*v[:,0])/det
        t=(u[:,0]*d[:,1]-u[:,1]*d[:,0])/det
        hit=(s>=-1e-8)&(t>=-1e-8)&(s+t<=1+1e-8)
        if not hit.any():result.append(np.nan);continue
        z=a[:,2]+s*dz1+t*dz2;result.append(z[hit].max())
    return np.asarray(result)

def jaw(recipe,number):
    # The jaw is a lower-face deformation, never another whole portrait.
    widths=(1.18,.82,1.07,.71,1.22,.88,1.12,.93,.78,1.04)
    chin=(1.09,.89,1.05,.78,1.17,.92,1.04,.96,.82,1.02)
    for command in surfaces(recipe):
        v,f=mesh(command);v=v.copy();weight=np.clip((2.255-v[:,1])/.18,0,1)
        v[:,0]*=1+(widths[number-1]-1)*weight
        v[:,1]-=(chin[number-1]-1)*.055*weight
        command.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist())
        command.pop('vertex_normals',None)
        command['jaw_revision']={'schema_version':1,'variant':number,'region':'Y below 2.255; upper face unchanged','width_factor':widths[number-1],'chin_factor':chin[number-1]}
    recipe['jaw_reference_choice']=number

def split_edges(vertices,faces):
    """One conforming refinement so a wide lip follows cheek-plane breaks."""
    vertices=vertices.tolist();cache={};out=[]
    def middle(a,b):
        key=tuple(sorted((int(a),int(b))))
        if key not in cache:
            cache[key]=len(vertices);vertices.append(((np.asarray(vertices[a])+vertices[b])*.5).tolist())
        return cache[key]
    for a,b,c in faces:
        ab,bc,ca=middle(a,b),middle(b,c),middle(c,a)
        out.extend([[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]])
    return np.asarray(vertices),np.asarray(out)

def attach_ears(recipe,face):
    for command in recipe['commands']:
        primitive=command.get('authored_primitive',command)
        anchor=primitive.get('ear_attachment')
        if not anchor:continue
        saved=command.get('ear_fit_template')
        if saved is None:
            v,f=mesh(command);saved={'schema_version':1,'vertices':v.tolist(),'faces':f.tolist(),'anchor':anchor}
        command['ear_fit_template']=saved
        root=np.asarray(saved['anchor']['root']);side=saved['anchor']['side']
        support=[]
        for skin in face:
            v,f=mesh(skin);support.append({'op':'indexed_mesh','vertices':(v[:,[2,1,0]]*[1,1,side]).tolist(),'faces':f.tolist()})
        depth=front_depth(support,np.array([[root[2],root[1]]]))[0]
        if not np.isfinite(depth):continue
        shift=side*(depth-.008)-root[0]
        v=np.asarray(saved['vertices']).copy();v[:,0]+=shift
        command.update(op='indexed_mesh',vertices=v.tolist(),faces=saved['faces'])
        command.pop('vertex_normals',None)
        command['ear_skin_attachment']={'schema_version':1,'method':'baked exact side intersection','root':(root+[shift,0,0]).tolist(),'penetration_metres':.008}

def attach(recipe):
    face=surfaces(recipe)
    if not face:return
    attach_ears(recipe,face)
    landmarks=face[0].get('authored_landmarks',face[0].get('authored_primitive',{}).get('authored_landmarks',{}))
    for command in recipe['commands']:
        part=command['part']
        if command in face:continue
        kind=next((k for k,words in (('pupil',('pupil',)),('iris',('iris',)),('eyes',('eye_aperture','eyelid','eye_socket')),('mouth',('mouth','lip')),('brows',('brow',)),('nose_detail',('nostril',)),('nose',('nose_large_planes','nose_bridge','animal_nose','broad_nose_plate'))) if any(w in part for w in words)),None)
        if kind is None:continue
        saved=command.get('face_fit_template',command.get('authored_primitive',{}).get('face_fit_template'))
        if saved is None:
            vertices,faces=mesh(command)
            saved={'schema_version':1,'vertices':vertices.tolist(),'faces':faces.tolist(),'frame':dict(command.get('face_feature_frame',command.get('authored_primitive',{}).get('face_feature_frame',{}))),'refined':bool(command.get('surface_fit_topology',command.get('authored_primitive',{}).get('surface_fit_topology')))}
        command['face_fit_template']=saved
        relief=command.get('mouth_surface_relief',command.get('authored_primitive',{}).get('mouth_surface_relief'))
        v=np.asarray(saved['vertices']).copy();f=np.asarray(saved['faces'])
        target=landmarks.get('eye_y' if kind in ('eyes','iris','pupil') else 'mouth_y' if kind=='mouth' else 'brow_y' if kind=='brows' else '')
        if target is not None:
            group='eyes' if kind in ('eyes','iris','pupil') else kind
            frame=saved['frame']
            origin=frame.get(group,{'eyes':2.329,'mouth':2.125,'brows':2.395}.get(group,target))
            v[:,1]+=target-origin;command['face_feature_frame']={**frame,group:target}
        if kind in ('mouth','brows','eyes') and not saved['refined'] and not relief:
            v,f=split_edges(v,f);command['surface_fit_topology']=1
        support=face
        if kind in ('mouth','nose','nose_detail'):
            support=face+[c for c in recipe['commands'] if c is not command and any(t in c['part'] for t in ('muzzle','porcine_muzzle'))]
        if kind=='nose_detail':
            support=face+[c for c in recipe['commands'] if c is not command and any(t in c['part'] for t in ('nose_large_planes','nose_bridge','animal_nose','broad_nose_plate'))]
        z=front_depth(support,v[:,:2]);valid=np.isfinite(z)
        if not valid.all():continue
        offset={'eyes':.005,'iris':.008,'pupil':.011,'mouth':.007,'brows':.009,'nose':.025,'nose_detail':.001}[kind]
        # Preserve thickness/shape. The foremost vertices sit on the surface
        # plus a small relief; the rear penetrates the skin instead of floating.
        component_front=front_depth([{'op':'indexed_mesh','vertices':v.tolist(),'faces':f.tolist()}],v[:,:2])
        local=v[:,2]-component_front
        if kind=='mouth' and relief:
            # Preserve the authored Cupid's bow, lip roll and bevelled crowns.
            # Their shared root plane sinks into the selected facial surface.
            local=v[:,2]-relief['anchor_z']
            offset=0
        if kind=='nose':
            # Keep the cross-section of a separately chosen nose. Projecting
            # each front vertex independently collapses its curved end cap
            # when the supporting skin is planar.
            local=v[:,2]-v[:,2].max()
            offset=max(offset,float(np.ptp(v[:,2]))*.75)
        v[:,2]=z+local+offset
        from tools.creature_workshop.family_faces import orient_faces
        f=orient_faces(v,f)
        command.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist())
        command.pop('vertex_normals',None)
        command['face_attachment']={'schema_version':1,'method':'baked exact triangle intersection along +Z','surface_parts':[c['part'] for c in support],'relief_metres':offset,'max_front_gap_metres':float(np.max(v[:,2]-z))}
