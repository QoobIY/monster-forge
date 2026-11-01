"""Hair-aware placement of headbands and their attached ornaments."""
import numpy as np
from tools.creature_workshop.geometry import mesh
from .constructor_face_fit import surfaces,front_depth


def hair_support(recipe):
    return [c for c in recipe['commands'] if c['slot']=='head' and
            any(t in c['part'] for t in ('hair_','hair_cap','scalp','braid','mane','topknot','dreadlock')) and
            not any(t in c['part'] for t in ('beard','mustache','brow','hair_tie'))]


def primitive(command):
    while 'authored_primitive' in command:command=command['authored_primitive']
    return command


def apply(recipe,parts,bands):
    from .constructor_surface_fit import triangles,radial_hit
    hair=hair_support(recipe);face=surfaces(recipe)
    if not hair or not face:return
    support=face+hair;tri=triangles(support)
    bands=[c for c in bands if 'engraving' not in c['part']]
    band_templates={id(c):mesh(c)[0].copy() for c in bands}
    # Keep the tube section intact when moving an engraved line or strap.
    # Solid circlet sweeps have perimeter vertices and move radially.
    for command in bands:
        v,f=mesh(command);v=v.copy();source=primitive(command)
        sections=[]
        if source.get('path') and source.get('sides'):
            sides=int(source['sides'])
            sections=[np.arange(i*sides,(i+1)*sides) for i in range(len(source['path']))]
        else:sections=[np.asarray([i]) for i in range(len(v))]
        for indices in sections:
            p=v[indices].mean(0);origin=np.array([0,p[1],.005])
            direction=p-origin;direction[1]=0;radius=np.linalg.norm(direction)
            if radius<1e-9:continue
            direction/=radius;distance=radial_hit(tri,origin,direction)
            if distance is not None:
                padding=.020 if len(indices)>1 else .018
                v[indices]+=direction*max(0,distance+padding-radius)
        command.update(vertices=v.tolist(),faces=f.tolist())
        command['headwear_hair_contact']={'schema_version':1,'placement':'outside skull and hairstyle','clearance_metres':.018}
    frame=any(any(t in c['part'] for t in ('circlet','crown_point','tiara_arch','laurel')) for c in parts)
    forehead=[c for c in parts if ('forehead_' in c['part'] or 'head_feather' in c['part'] or 'feather_shaft' in c['part'] or 'feather_barb' in c['part'])]
    decoration=[c for c in parts if c not in bands and
        ((frame and not any(t in c['part'] for t in ('earring','horn_cap','cap_engraving','goggle','mask'))) or c in forehead)]
    # Rigidly move the ornament assembly. Independent per-vertex projection
    # twisted thin arches and frames and changed their closed-mesh volume.
    # Keep the crown points, settings and gems in one coherent frame.
    if not decoration:return
    scale_x=1.0
    if frame and bands:
        before=np.concatenate(list(band_templates.values()))
        after=np.concatenate([mesh(c)[0] for c in bands])
        scale_x=max(1.0,float(np.max(np.abs(after[:,0]))/np.max(np.abs(before[:,0]))))
    vertices=[]
    for command in decoration:
        v,f=mesh(command);v=v.copy()
        # The authored crown is a rigid object, rather than a relief bent over
        # the forehead. Start from its proportion-adjusted original frame.
        saved=command.get('headwear_fit_template')
        if saved is not None:
            v=np.asarray(saved['vertices']).copy()
            proportions=command['headwear_contact_revision']
            v[:,0]*=proportions['head_width_factor']
            v[:,1]=2.335+(v[:,1]-2.335)*proportions['head_length_factor']
        v[:,0]*=scale_x
        vertices.append((command,v,f))
    points=np.concatenate([v for _,v,_ in vertices])
    outer=front_depth(hair,points[:,:2]);valid=np.isfinite(outer)
    shift=max(0.0,float(np.max(outer[valid]+.008-points[valid,2]))) if valid.any() else 0.0
    for command,v,f in vertices:
        v[:,2]+=shift;command.update(vertices=v.tolist(),faces=f.tolist())
        command['headwear_hair_contact']={'schema_version':1,'placement':'rigid ornament frame outside hairstyle',
            'forward_shift_metres':shift,'hair_width_factor':scale_x}
    # The front arc stays with the same ornament frame while the sides/back
    # follow their local hair volume. It does not become a separate floating
    # row of gems in front of an unchanged skull-sized circlet.
    if frame and shift:
        for command in bands:
            v,f=mesh(command);v=v.copy();before=band_templates[id(command)]
            weight=np.clip((before[:,2]-.005)/max(float(before[:,2].max()-.005),1e-9),0,1)
            v[:,2]=np.maximum(v[:,2],before[:,2]+shift*weight)
            command.update(vertices=v.tolist(),faces=f.tolist())
