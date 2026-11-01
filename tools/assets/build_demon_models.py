"""Original demonic hound, self-crowned Azanus and colored breakable obelisks."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from monster_forge_sdk.characters import body_rig
from tools.assets.build_catalog import build_catalog
from tools.assets.build_mom_skins import bounded_weights
from tools.assets.build_rpg_locations import single_node
from tools.assets.build_swamp_models import SLOTS, Shape, write_json

ROOT = Path(__file__).resolve().parents[2]
RED = (129, 43, 43, 255)
IRON = (43, 37, 48, 255)
BONE = (213, 181, 129, 255)
GOLD = (192, 133, 49, 255)
EMBER = (247, 103, 28, 255)


def hound(slot):
    p = Shape()
    if slot == 'torso':
        p.ellipsoid((0, .95, -.1), (.43, .43, .83), RED, 2)
        p.ellipsoid((0, 1.08, .40), (.48, .48, .45), IRON, 1)
        for i in range(6):
            z = -.65 + i * .23
            p.cone(.12, .27 + .1 * (i % 2), (0, 1.34, z), BONE, 5)
            for s in (-1, 1):
                p.branch((s*.36, 1.12, z), (s*.4, .83, z+.06), .025, EMBER, 5)
    elif slot == 'head':
        p.ellipsoid((0, 1.25, .92), (.37, .35, .43), RED, 1)
        p.ellipsoid((0, 1.1, 1.31), (.24, .19, .35), IRON, 1)
        p.ellipsoid((0, .91, 1.3), (.22, .07, .31), RED, 1)
        p.ellipsoid((0, 1.16, 1.6), (.19, .1, .07), IRON, 0)
        for s in (-1, 1):
            p.ellipsoid((s*.28, 1.36, 1.19), (.07, .055, .04), EMBER, 0)
            p.branch((s*.26, 1.45, .8), (s*.42, 1.74, .60), .12, BONE)
            p.branch((s*.42, 1.74, .60), (s*.34, 1.9, .45), .06, BONE)
            for z in (1.23, 1.43):
                p.cone(.055, .19, (s*.21, .95, z), BONE, 5)
    elif slot == 'tail':
        points = [(0, 1.02, -.85), (.08, 1.1, -1.18), (.21, 1.38, -1.48), (.29, 1.65, -1.5)]
        for i in range(3):
            p.branch(points[i], points[i+1], .09-i*.025, RED)
        p.ellipsoid(points[-1], (.10, .18, .08), EMBER, 0)
    else:
        s = -1 if 'left' in slot else 1
        front = slot.startswith('front')
        hip = (s*.35, 1.04 if front else .92, .49 if front else -.56)
        knee = (s*.43, .49, .51 if front else -.89)
        ankle = (s*.41, .17, .64 if front else -.48)
        p.ellipsoid(hip, (.24, .32, .25), RED, 1)
        p.branch(hip, knee, .15, RED)
        p.branch(knee, ankle, .09, IRON)
        p.ellipsoid((ankle[0], .11, ankle[2]+.08), (.16, .10, .24), RED, 1)
        for i in range(3):
            x = ankle[0]+(i-1)*.10
            p.branch((x, .11, ankle[2]+.19), (x, .065, ankle[2]+.38), .035, BONE, 5)
    return p.finish()


def azanus(slot):
    p = Shape()
    if slot == 'head':
        p.ellipsoid((0, 2.12, .03), (.28, .32, .24), RED, 1)
        p.ellipsoid((0, 1.98, .20), (.21, .14, .17), IRON, 1)
        for s in (-1, 1):
            p.ellipsoid((s*.12, 2.18, .24), (.085, .036, .025), EMBER, 0)
            pts=[(s*.22, 2.32, 0), (s*.44, 2.52, -.10), (s*.48, 2.77, -.15), (s*.31, 2.99, -.08)]
            for i in range(3):
                p.branch(pts[i], pts[i+1], .13-i*.04, BONE)
            p.cone(.035, .14, (s*.10, 1.99, .34), BONE, 5)
        p.cylinder(.31, .1, (0, 2.42, .03), GOLD)
        for i in range(5):
            a=i*math.tau/5
            p.cone(.07, .28 if i else .42, (.28*math.cos(a), 2.48, .03+.28*math.sin(a)), GOLD, 4)
    elif slot == 'torso':
        p.ellipsoid((0, 1.43, 0), (.49, .51, .30), RED, 1)
        p.ellipsoid((0, 1.51, .22), (.43, .31, .12), IRON, 1)
        p.branch((-.38, 1.73, .28), (.34, 1.18, .28), .048, GOLD)
        p.cylinder(.36, .13, (0, 1.02, 0), IRON)
        p.ellipsoid((0, 1.05, .36), (.13, .12, .05), EMBER, 0)
        for s in (-1, 1):
            p.ellipsoid((s*.43, 1.76, 0), (.28, .18, .3), IRON, 0)
            p.branch((s*.47, 1.82, 0), (s*.66, 2.10, -.08), .095, BONE)
            # Small, deliberately inadequate wings on a self-appointed king.
            p.branch((s*.30, 1.66, -.22), (s*.78, 1.97, -.54), .06, BONE)
            p.ellipsoid((s*.58, 1.63, -.41), (.25, .34, .035), RED, 0)
    else:
        s = -1 if slot.startswith('left') else 1
        if slot.endswith('arm'):
            p.branch((s*.38, 1.75, 0), (s*.65, 1.36, 0), .19, RED)
            p.branch((s*.65, 1.36, 0), (s*.83, 1.02, .04), .14, IRON)
            p.cylinder(.17, .12, (s*.79, 1.10, .03), GOLD)
            p.ellipsoid((s*.84, .96, .06), (.15, .15, .14), RED, 1)
            for i in range(3):
                p.branch((s*.86, .92, -.03+i*.09), (s*.94, .76, -.03+i*.09), .04, BONE)
        else:
            p.branch((s*.23, 1, 0), (s*.31, .56, -.12), .22, RED)
            p.branch((s*.31, .56, -.12), (s*.31, .20, .10), .13, IRON)
            for x in (s*.31-.09,s*.31+.09):
                p.ellipsoid((x, .12, .22), (.10, .12, .20), IRON, 0)
    return p.finish()


def build():
    source=Path(__file__).read_bytes()
    digest=hashlib.sha256(source).hexdigest()
    snapshot=ROOT/'media/recipes/builders'/(digest+'.txt')
    snapshot.parent.mkdir(parents=True,exist_ok=True)
    snapshot.write_bytes(source)
    for name, rig_id, make in [('demon_hound','quadruped_v1',hound),('azanus','humanoid_v1',azanus)]:
        rig=body_rig(rig_id, root=ROOT)
        names=[b['id'] for b in rig['bones']]
        points={}
        for b in rig['bones']:
            point=np.array(b['bind_translation'],float)
            points[b['id']]=point if b['parent'] is None else points[b['parent']]+point
        slots=[s['id'] for s in rig['slots']] if rig_id=='quadruped_v1' else SLOTS
        folder=ROOT/'media/constructor/mom_rpg/v1/demons'/name
        (folder/'parts').mkdir(parents=True,exist_ok=True)
        for key in slots:
            mesh=make(key)
            target=folder/'parts'/(key+'.glb')
            blob=mesh.export(file_type='glb',tree_postprocessor=single_node)
            if target.exists() and target.read_bytes()!=blob:
                raise ValueError('Immutable model changed: '+str(target))
            target.write_bytes(blob)
            if rig_id=='humanoid_v1':
                weights=bounded_weights(target,key,'canonical')
            else:
                allowed=next(s['bones'] for s in rig['slots'] if s['id']==key)
                nearest=np.stack([np.linalg.norm(mesh.vertices-points[b],axis=1) for b in allowed],axis=1).argmin(axis=1)
                indices=[[names.index(allowed[i]),0,0,0] for i in nearest]
                weights={'schema_version':1,'skeleton_id':rig_id,'gait':'walk','bind_profile':'canonical','slot':key,'bone_palette':names,'model_sha256':hashlib.sha256(blob).hexdigest(),'skin_indices':indices,'skin_weights':[[1.,0.,0.,0.] for _ in indices]}
            write_json(target.with_suffix('.weights.json'),weights)
            if not target.with_suffix('.recipe.json').exists():
                write_json(target.with_suffix('.recipe.json'),{'schema_version':1,'builder_sha256':digest,'triangles':len(mesh.faces),'anatomy':'four-legged horned canine, elongated muzzle and claws' if name=='demon_hound' else 'self-crowned lower demon, huge horns, small wings'})
        record={'schema_version':1,'id':name,'label':'Демоническая собака' if name=='demon_hound' else 'Король Азанус','race':'demon','rig':rig_id,'bind_profile':'canonical','parts':{s:{'model':'parts/'+s+'.glb'} for s in slots},'tags':['mom_rpg','demons',name]}
        if rig_id=='quadruped_v1':
            record['gait']='walk'
        write_json(folder/'record.json',record)
    catalog_path=ROOT/'media/imported_catalog.json'
    catalog=json.loads(catalog_path.read_text())
    for key,color,label in [('haste',(64,192,190,255),'Обелиск скорости'),('fury',(223,72,39,255),'Обелиск ярости'),('armor',(114,92,216,255),'Обелиск брони'),('basalt',(75,64,78,255),'Базальтовая колонна')]:
        p=Shape()
        p.cylinder(.72,.20,(0,.10,0),IRON,6)
        p.cylinder(.58,.16,(0,.28,0),GOLD if key!='basalt' else IRON,6)
        p.cone(.5,2.2,(0,.36,0),IRON,6)
        for s in (-1,1):
            p.branch((s*.25,.7,.35),(s*.12,1.8,.15),.05,color,5)
            p.branch((s*.12,1.8,.15),(s*.33,2.1,.15),.035,color,5)
        p.ellipsoid((0,2.25,0),(.25,.46,.25),color,0)
        if key!='basalt':
            for s in (-1,1):
                p.branch((s*.12,1.7,0),(s*.58,2.20,0),.08,BONE)
        mesh=p.finish()
        revision=1 if key=='basalt' else 2
        folder=ROOT/'media/decorations/mom_rpg/demons'/key/('v'+str(revision))
        folder.mkdir(parents=True,exist_ok=True)
        files={}
        for role,name,payload,mime in [('model','model.glb',mesh.export(file_type='glb',tree_postprocessor=single_node),'model/gltf-binary'),('recipe','recipe.json',(json.dumps({'schema_version':1,'builder_sha256':digest,'triangles':len(mesh.faces),'style':'faceted basalt and demonic iron'},indent=2)+'\n').encode(),'application/json')]:
            target=folder/name
            if role=='recipe' and target.exists():
                payload=target.read_bytes()
            if target.exists() and target.read_bytes()!=payload:
                raise ValueError('Immutable prop changed')
            target.write_bytes(payload)
            files[role]={'path':target.relative_to(ROOT/'media').as_posix(),'sha256':hashlib.sha256(payload).hexdigest(),'size_bytes':len(payload),'media_type':mime}
        identity='decoration.mom_rpg.demons.'+key
        entry={'id':identity,'kind':'decoration','title':label,'revision':revision,'group':'MOM RPG','tags':['mom_rpg','demons'],'files':files}
        previous=next((a for a in catalog['assets'] if a['id']==identity),None)
        if previous and previous['revision']<revision:
            catalog['assets'][catalog['assets'].index(previous)]=entry
        elif previous and previous!=entry:
            raise ValueError('Immutable prop catalog changed')
        elif not previous:
            catalog['assets'].append(entry)
    write_json(catalog_path,catalog)
    build_catalog(ROOT)
    print('Published demon models and obelisks',flush=True)


if __name__=='__main__':
    build()
