"""Shorter visible neck baked into humanoid parts, retaining SDK bind bones."""
import numpy as np
from tools.creature_workshop.geometry import mesh

SHOULDER_LINE=1.85
HEAD_DROP=.0875

def apply(recipe,slot):
    for c in recipe['commands']:
        if c.get('short_neck_revision'):continue
        if slot!='head' and not (slot=='torso' and c['part'].endswith('neck')):continue
        v,f=mesh(c);v=v.copy()
        if slot=='head':v[:,1]-=HEAD_DROP
        else:
            top=float(v[:,1].max())
            length=max(top-SHOULDER_LINE,0)
            if length<=HEAD_DROP:continue
            upper=v[:,1]>SHOULDER_LINE
            v[upper,1]=SHOULDER_LINE+(v[upper,1]-SHOULDER_LINE)*(length-HEAD_DROP)/length
        c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist(),
                 short_neck_revision={'schema_version':1,'head_drop_metres':HEAD_DROP,'shoulder_line_metres':SHOULDER_LINE,'sdk_bind_unchanged':True})
        c.pop('vertex_normals',None)
    return recipe
