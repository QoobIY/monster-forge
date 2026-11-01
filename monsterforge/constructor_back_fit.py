"""Bake a rigid back attachment onto the selected torso's actual rear surface."""
import numpy as np
from tools.creature_workshop.geometry import mesh
from .constructor_face_fit import front_depth
from .constructor_surface_fit import torso_support


def rear_support(torso):
    result=[]
    for c in torso_support(torso):
        if 'neck' in c['part']:continue
        v,f=mesh(c);v=v.copy();v[:,2]*=-1
        result.append({**c,'op':'indexed_mesh','vertices':v.tolist(),'faces':f.tolist()})
    return result


def contact_samples(recipe,torso):
    # Use the common physical mounting area, not a wing tip, cape hem, arrow
    # tip or an ornament at the far end of a backpack.
    support=rear_support(torso)
    if not support:return np.empty((0,2)),np.empty(0),np.empty(0)
    xy=np.asarray([[x,y] for x in np.linspace(-.24,.24,17) for y in np.linspace(1.40,1.87,20)])
    body=-front_depth(support,xy)
    item=front_depth(recipe['commands'],xy)
    valid=np.isfinite(body)&np.isfinite(item)
    return xy[valid],body[valid],item[valid]


def apply(recipe,torso):
    if recipe.get('back_surface_attachment'):return
    xy,body,item=contact_samples(recipe,torso)
    if not len(xy):
        raise ValueError('Нет общей области крепления аксессуара к спине')
    # First contact stops the rigid object from passing through the torso.
    # Embed its nearest mounting point by 2 mm, retaining all relative offsets.
    gap=body-item;index=int(np.argmin(gap));shift=float(gap[index]+.002)
    for c in recipe['commands']:
        v,f=mesh(c);v=v.copy();v[:,2]+=shift
        c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist())
    quiver=recipe.get('quiver_arrow_revision')
    if quiver:
        offset=np.array([0,0,shift])
        for key in ('bottom','opening'):quiver[key]=(np.asarray(quiver[key])+offset).tolist()
        for arrow in quiver['arrows']:
            for key in ('start','tip'):arrow[key]=(np.asarray(arrow[key])+offset).tolist()
    recipe['back_surface_attachment']={'schema_version':1,'method':'rigid contact with selected torso rear triangles',
        'offset_metres':[0,0,shift],'contact_xy_metres':xy[index].tolist(),
        'penetration_metres':.002,'samples':len(xy)}
