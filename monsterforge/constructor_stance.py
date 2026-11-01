"""Compact leg columns baked into parts; the shared SDK remains unchanged."""
import numpy as np
from tools.creature_workshop.geometry import mesh


def apply(recipe):
    for c in recipe['commands']:
        if c['slot'] not in ('left_leg', 'right_leg'):
            continue
        source=c.get('authored_primitive',c)
        previous=c.get('thigh_stance_revision',source.get('thigh_stance_revision'))
        if previous and previous.get('schema_version',1)>=2:
            continue
        v,f=mesh(c);v=v.copy()
        seam=1.16 if source.get('body_silhouette_revision') else .95
        weight=np.clip((v[:,1]-.48)/(seam-.48),0,1)
        sign=1 if c['slot']=='left_leg' else -1
        # Source revisions already contain the old 3 cm thigh-root adjustment.
        # Move the entire column inward, keeping that authored bend intact.
        medial=0 if previous else .03
        v[:,0]+=sign*(.045+medial*weight)
        c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist())
        c.pop('vertex_normals',None)
        c['thigh_stance_revision']={'schema_version':2,'medial_shift_metres':.03,
                                    'column_shift_metres':.045,
                                    'knee_y_metres':.48,'upper_seam_y_metres':seam,
                                    'sdk_bind_unchanged':True}
    return recipe
