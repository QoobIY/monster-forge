"""Round existing limb end caps in-place as explicit, replayable part revisions."""
import math
import numpy as np
from tools.creature_workshop.geometry import mesh
from tools.creature_workshop.family_faces import orient_faces

PARTS={'fitted_sleeve','sleeve','sleeve_core','leg','trousers','humerus','femur','animal_leg','segmented_leg'}

def round_roots(recipe,slot):
    if slot not in {'left_arm','right_arm','left_leg','right_leg'} and not slot.endswith('_leg') and '_leg_' not in slot:return recipe
    changed=[]
    for c in recipe['commands']:
        primitive=c.get('authored_primitive',c)
        if c['slot']!=slot or c['part'] not in PARTS or 'rounded_root' in c:continue
        vertices,faces=mesh(c)
        if 'ring_topology' in primitive:
            topology=primitive['ring_topology'];sides=topology['sides'];sections=topology['sections'];kind='sweep'
        elif primitive.get('op') not in {'sweep','loft'}:
            # Older frozen sources retain only indexed rings. Recognize their
            # exact topology rather than assuming arbitrary meshes are tubes.
            candidates=[]
            for n in range(3,13):
                if len(vertices)%n or not 2<=len(vertices)//n<=12:continue
                levels=faces//n
                if np.any(levels.max(1)-levels.min(1)>1):continue
                if np.sum(np.all(faces<n,axis=1))!=n-2 or np.sum(np.all(faces>=len(vertices)-n,axis=1))!=n-2:continue
                candidates.append(n)
            if len(candidates)!=1:continue
            sides=candidates[0];sections=len(vertices)//sides;kind='loft'
        else:
            sides=primitive.get('sides',8);sections=len(primitive.get('path',primitive.get('stations',[])));kind=primitive['op']
        if len(vertices)!=sections*sides or sections<2:continue
        # Sweeps are authored from the attachment toward the hand/foot. Loft
        # roots use their upper section. Work on actual vertices, preserving
        # all previous authoring transforms and the remainder of the mesh.
        index=0 if kind=='sweep' else int(np.argmax([vertices[i*sides:(i+1)*sides,1].mean() for i in range(sections)]))
        if index not in {0,sections-1}:continue
        root_indices=np.arange(index*sides,(index+1)*sides);ring=vertices[root_indices].copy();center=ring.mean(0)
        neighbor=1 if index==0 else sections-2
        inner=vertices[neighbor*sides:(neighbor+1)*sides].mean(0)-center
        distance=float(np.linalg.norm(inner));direction=inner/max(distance,1e-12)
        radius=float(np.linalg.norm(ring-center,axis=1).mean())
        depth=min(radius*.68,distance*.24)
        if depth<1e-6:continue
        cap=np.all(np.isin(faces,root_indices),axis=1)
        if not cap.any():continue
        new_vertices=vertices.copy();new_vertices[root_indices]=ring+direction*depth
        new_faces=faces[~cap].tolist();materials=None
        if 'face_materials' in c:
            materials=[m for m,remove in zip(c['face_materials'],cap,strict=True) if not remove]
            cap_material=next(m for m,remove in zip(c['face_materials'],cap,strict=True) if remove)
        previous=root_indices.tolist()
        # Three bevel rings and one pole form a faceted ellipsoidal dome. Its
        # pole stays on the old cap plane: no added extension or hidden collar.
        for angle in (math.pi*3/8,math.pi/4,math.pi/8):
            section=center+direction*depth*(1-math.cos(angle))+(ring-center)*math.sin(angle)
            start=len(new_vertices);new_vertices=np.concatenate([new_vertices,section]);current=list(range(start,start+sides))
            for i in range(sides):
                j=(i+1)%sides;new_faces.extend([[previous[i],previous[j],current[i]],[previous[j],current[j],current[i]]])
                if materials is not None:materials.extend([cap_material]*2)
            previous=current
        pole=len(new_vertices);new_vertices=np.concatenate([new_vertices,center[None,:]])
        for i in range(sides):
            new_faces.append([previous[i],previous[(i+1)%sides],pole])
            if materials is not None:materials.append(cap_material)
        new_faces=orient_faces(new_vertices,np.asarray(new_faces))
        c.update(op='indexed_mesh',vertices=new_vertices.tolist(),faces=new_faces.tolist())
        c.pop('vertex_normals',None)
        if materials is not None:c['face_materials']=materials
        c['rounded_root']={'schema_version':1,'method':'inset_faceted_dome','center':center.tolist(),'inward_axis':direction.tolist(),'depth_metres':depth,'radius_metres':radius,'rings':3,'original_root_section':index}
        changed.append(c['id'])
    if changed:recipe['limb_root_revision']={'schema_version':1,'commands':changed,'preserve_distal_geometry':True}
    return recipe
