"""Seat arrows in the selected, final quiver geometry without editing sources."""
import numpy as np
from .constructor_portraits import builder, freeze
from tools.creature_workshop.geometry import mesh


def fit(recipe):
    cases=[c for c in recipe['commands'] if 'quiver_case' in c['part']]
    shafts=[c for c in recipe['commands'] if 'arrow_shaft' in c['part']]
    feathers=[c for c in recipe['commands'] if 'arrow_fletch' in c['part']]
    if len(cases)!=1 or not shafts or not feathers:return recipe
    v,_=mesh(cases[0])
    # Case sweeps contain two equal rings. Read the final transformed centres,
    # including the selected body width, rather than the old source path.
    bottom,opening=np.array_split(v,2)
    bottom=bottom.mean(0);opening=opening.mean(0)
    axis=opening-bottom;length=np.linalg.norm(axis);axis/=length
    if axis[1]<0:bottom,opening=opening,bottom;axis=-axis
    lateral=np.cross(axis,[0,0,1]);lateral/=np.linalg.norm(lateral)
    depth=np.cross(axis,lateral)
    b=builder(recipe);b.slot=cases[0]['slot'];b.stage=3
    # Two staggered rows keep shafts and feathers separate inside the mouth.
    offsets=((-1,-.5),(0,.5),(1,-.5),(-.5,1.5),(.5,-1.5))
    records=[]
    for i in range(len(shafts)):
        x,z=offsets[i%len(offsets)]
        offset=lateral*x*.049+depth*z*.032
        start=bottom+axis*.055+offset
        tip=opening+axis*(.26+(i%3)*.027)+offset
        b.tube('arrow_shaft','metal',[start.tolist(),tip.tolist()],[.012,.012],sides=5)
        # Two feather vanes share the shaft frame; both finish below its nock.
        for direction in (lateral,depth):
            points=[tip-axis*.135,tip-axis*.10+direction*.034,
                    tip-axis*.025+direction*.034,tip-axis*.009]
            normal=np.cross(axis,direction);normal/=np.linalg.norm(normal)
            verts=np.concatenate([np.asarray(points)+normal*.004,np.asarray(points)-normal*.004])
            faces=[[0,1,2],[0,2,3],[4,6,5],[4,7,6]]
            for j in range(4):
                k=(j+1)%4;faces.extend([[j,j+4,k+4],[j,k+4,k]])
            b.commands.append({'id':f'quiver-feather-{i}-{len(b.commands)}','slot':b.slot,
                'stage':b.stage,'part':'arrow_fletching','material':'secondary','op':'indexed_mesh',
                'vertices':verts.tolist(),'faces':faces,'purpose':'Feather vane aligned to its arrow shaft'})
        records.append({'start':start.tolist(),'tip':tip.tolist()})
    commands,palette=freeze(b,'quiver_arrows')
    # Preserve the chosen source's material colours and back colour channels.
    palette['quiver_arrows_metal']=recipe['palette'][shafts[0]['material']]
    palette['quiver_arrows_secondary']=recipe['palette'][feathers[0]['material']]
    old={id(c) for c in shafts+feathers}
    recipe['commands'][:]=[c for c in recipe['commands'] if id(c) not in old]
    for c in commands:c['slot']=cases[0]['slot']
    recipe['commands'].extend(commands);recipe['commands'].sort(key=lambda c:c['stage'])
    recipe['palette'].update({k:v for k,v in palette.items() if any(c['material']==k for c in commands)})
    recipe['quiver_arrow_revision']={'schema_version':1,'bottom':bottom.tolist(),
        'opening':opening.tolist(),'axis':axis.tolist(),'arrows':records}
    return recipe
