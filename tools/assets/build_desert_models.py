"""Faceted desert fauna: quillbacks, eight-legged spider, sandstone and healer totem."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import trimesh

from monster_forge_sdk.characters import body_rig
from tools.assets.build_catalog import build_catalog
from tools.assets.build_rpg_locations import single_node
from tools.assets.build_swamp_models import Shape, write_json

ROOT = Path(__file__).resolve().parents[2]
HIDE = (153, 103, 63, 255)
DARK = (64, 49, 45, 255)
IVORY = (230, 208, 154, 255)
BLUE = (55, 159, 198, 255)
GREEN = (88, 181, 119, 255)
SAND = (191, 146, 85, 255)


def spike(p, start, end, radius, color):
    start, end = np.array(start, float), np.array(end, float)
    mesh = trimesh.creation.cone(radius, np.linalg.norm(end-start), sections=5)
    mesh.apply_transform(trimesh.geometry.align_vectors((0,0,1), end-start))
    p.add(mesh, color, start)


def quillback(slot, kind):
    p = Shape()
    mage = kind == 'quillback_mage'
    chief = kind == 'quillback_chief'
    color = (119, 102, 81, 255) if mage else HIDE
    if slot == 'torso':
        p.ellipsoid((0, .94, -.05), (.55, .47, .78), color, 2)
        p.ellipsoid((0, 1.12, -.18), (.50, .31, .58), DARK, 1)
        # Quills lean backwards; silhouette is recognisable from the gameplay camera.
        for row in range(5):
            z = -.58 + row * .23
            for side in (-1, 0, 1):
                start = (side * .30, 1.32 - abs(side)*.08, z)
                end = (side * .50, 1.79 + (.13 if chief else 0) - abs(side)*.16, z-.40)
                spike(p, start, (end[0], end[1]+.15, end[2]-.10), .10, IVORY)
        if mage:
            p.ellipsoid((0, 1.46, -.03), (.23, .18, .25), GREEN, 0)
        if chief:
            for side in (-1, 1):
                p.ellipsoid((side*.5, 1.1, .31), (.13, .30, .28), BLUE, 0)
    elif slot == 'head':
        p.ellipsoid((0, 1.04, .83), (.37, .38, .40), color, 1)
        p.ellipsoid((0, .92, 1.20), (.30, .22, .35), color, 1)
        p.ellipsoid((0, .94, 1.48), (.26, .15, .07), DARK, 0)
        for side in (-1, 1):
            p.ellipsoid((side*.29, 1.21, 1.02), (.05, .045, .06), BLUE if chief else (245, 186, 65, 255), 0)
            p.ellipsoid((side*.32, 1.36, .73), (.13, .20, .08), DARK, 0)
            p.branch((side*.22, .79, 1.25), (side*.35, .94, 1.47), .075, IVORY, 5)
            p.branch((side*.35, .94, 1.47), (side*.30, 1.12, 1.44), .04, IVORY, 5)
        if mage:
            p.ellipsoid((0, 1.47, .88), (.28, .15, .24), GREEN, 0)
            p.branch((0, 1.48, .88), (0, 1.90, .72), .075, IVORY, 5)
        if chief:
            p.cylinder(.32, .12, (0, 1.47, .83), BLUE, 6)
            for i in range(5):
                a = i*math.tau/5
                p.cone(.075, .3, (.28*math.cos(a), 1.53, .83+.28*math.sin(a)), IVORY, 4)
    elif slot == 'tail':
        p.branch((0, .94, -.72), (.12, .99, -1.18), .075, color)
        p.branch((.12, .99, -1.18), (.22, 1.17, -1.27), .045, DARK)
    else:
        side = -1 if 'left' in slot else 1
        front = slot.startswith('front')
        hip = (side*.40, .90, .43 if front else -.50)
        knee = (side*.47, .46, .54 if front else -.67)
        foot = (side*.46, .13, .62 if front else -.55)
        p.ellipsoid(hip, (.23, .31, .25), color, 1)
        p.branch(hip, knee, .15, color)
        p.branch(knee, foot, .09, DARK)
        for dx in (-.07, .07):
            p.ellipsoid((foot[0]+dx, .10, foot[2]+.07), (.075, .10, .18), DARK, 0)
    return p.finish()


def spider(slot, buried=False):
    p = Shape()
    if buried:
        # Same rig/slots, low buried silhouette: abdomen ridge, eyes, tucked legs.
        if slot == 'torso':
            p.ellipsoid((0, .15, -.1), (.68, .16, .82), SAND, 1)
            p.ellipsoid((0, .21, -.2), (.28, .10, .32), DARK, 1)
        elif slot == 'head':
            p.ellipsoid((0, .16, .57), (.23, .11, .22), SAND, 1)
            for x in (-.1, .1):
                p.ellipsoid((x, .20, .76), (.035, .025, .025), BLUE, 0)
        elif slot == 'tail':
            p.ellipsoid((0, .10, -.78), (.06, .04, .06), SAND, 0)
        else:
            s = -1 if 'left' in slot else 1
            z = .30 if slot.startswith('front') else -.30
            p.branch((s*.30, .10, z), (s*.77, .06, z+.1), .045, SAND, 5)
        return p.finish()
    if slot == 'torso':
        p.ellipsoid((0, .74, -.42), (.46, .39, .66), DARK, 1)
        p.ellipsoid((0, .74, .30), (.28, .22, .34), HIDE, 1)
        for side in (-1, 1):
            p.branch((side*.25, .98, -.73), (side*.22, 1.04, -.16), .06, SAND, 5)
    elif slot == 'head':
        p.ellipsoid((0, .73, .60), (.26, .22, .28), HIDE, 1)
        for side in (-1, 1):
            for j in range(2):
                p.ellipsoid((side*(.07+j*.09), .82+j*.025, .81-j*.03), (.045, .04, .04), BLUE, 0)
            p.branch((side*.12, .60, .80), (side*.19, .44, .94), .08, DARK, 5)
            p.branch((side*.19, .44, .94), (side*.06, .41, 1.01), .045, IVORY, 5)
    elif slot == 'tail':
        p.ellipsoid((0, .65, -1.03), (.10, .08, .08), HIDE, 0)
    else:
        side = -1 if 'left' in slot else 1
        front = slot.startswith('front')
        # Two anatomically distinct legs per limb chain: eight legs, no human arms.
        for i in range(2):
            z = (.38+i*.24) if front else (-.16-i*.28)
            reach = (.77+i*.36) if front else (-.45-i*.44)
            hip = (side*.22, .72, z)
            knee = (side*(.85+i*.20), .94-i*.08, reach)
            foot = (side*(1.14+i*.25), .055, reach+.12 if front else reach-.16)
            p.branch(hip, knee, .085, HIDE, 6)
            p.ellipsoid(knee, (.11, .10, .11), DARK, 0)
            p.branch(knee, foot, .055, DARK, 5)
            p.branch(foot, (foot[0]+side*.09, .025, foot[2]), .025, IVORY, 4)
    return p.finish()


def build():
    digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    snapshot = ROOT/'media/recipes/builders'/(digest+'.txt')
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_bytes(Path(__file__).read_bytes())
    rig = body_rig('quadruped_v1', root=ROOT)
    names = [b['id'] for b in rig['bones']]
    points = {}
    for b in rig['bones']:
        point = np.array(b['bind_translation'], float)
        points[b['id']] = point if b['parent'] is None else points[b['parent']]+point
    labels = {'quillback':'Иглогрив', 'quillback_mage':'Иглогрив маг', 'quillback_chief':'Вождь иглогривов', 'desert_spider':'Пустынный паук', 'buried_spider':'Закопавшийся пустынный паук'}
    for name, label in labels.items():
        folder = ROOT/'media/constructor/mom_rpg/v1/desert'/name
        (folder/'parts').mkdir(parents=True, exist_ok=True)
        for slot in rig['slots']:
            key = slot['id']
            mesh = spider(key, name=='buried_spider') if 'spider' in name else quillback(key, name)
            blob = mesh.export(file_type='glb', tree_postprocessor=single_node)
            filename = key+'.v2.glb' if key=='torso' and 'quillback' in name else key+'.glb'
            path = folder/'parts'/filename
            if path.exists() and path.read_bytes()!=blob:
                raise ValueError('Immutable model changed: '+str(path))
            path.write_bytes(blob)
            nearest = np.stack([np.linalg.norm(mesh.vertices-points[b], axis=1) for b in slot['bones']], axis=1).argmin(axis=1)
            weights = {'schema_version':1, 'skeleton_id':'quadruped_v1', 'gait':'walk', 'bind_profile':'canonical', 'slot':key, 'bone_palette':names, 'model_sha256':hashlib.sha256(blob).hexdigest(), 'skin_indices':[[names.index(slot['bones'][i]),0,0,0] for i in nearest], 'skin_weights':[[1.,0.,0.,0.] for _ in nearest]}
            write_json(path.with_suffix('.weights.json'), weights)
            recipe = path.with_suffix('.recipe.json')
            if not recipe.exists():
                write_json(recipe, {'schema_version':1, 'builder_sha256':digest, 'triangles':len(mesh.faces), 'anatomy':'eight-legged arachnid; paired leg chains' if 'spider' in name else 'four-legged boar-like quillback, backward quills, tusks'})
        write_json(folder/'record.json', {'schema_version':1, 'id':name, 'label':label, 'race':'arachnid' if 'spider' in name else 'quillback', 'rig':'quadruped_v1', 'gait':'walk', 'bind_profile':'canonical', 'parts':{s['id']:{'model':'parts/'+s['id']+('.v2.glb' if s['id']=='torso' and 'quillback' in name else '.glb')} for s in rig['slots']}, 'tags':['mom_rpg','desert',name]})
    catalog_path = ROOT/'media/imported_catalog.json'
    catalog = json.loads(catalog_path.read_text())
    for key, label in [('healing_totem','Лечащий тотем иглогривов'), ('sandstone','Выветренный песчаник'), ('storm_orb','Ядро шаровой молнии')]:
        p = Shape()
        if key == 'healing_totem':
            p.cylinder(.42, .16, (0,.08,0), DARK, 6)
            p.branch((0,.16,0), (0,1.55,0), .17, HIDE, 6)
            p.ellipsoid((0,1.62,0), (.36,.35,.28), IVORY, 0)
            for side in (-1,1):
                p.branch((side*.24,1.7,0), (side*.51,2.05,-.12), .065, IVORY, 5)
                p.ellipsoid((side*.14,1.68,.23), (.07,.06,.04), GREEN, 0)
                p.branch((0,.9,0), (side*.60,1.15,0), .09, DARK, 5)
                p.ellipsoid((side*.62,1.13,0), (.11,.20,.10), GREEN, 0)
            p.cylinder(.19,.18,(0,.45,0), GREEN, 6)
        elif key == 'storm_orb':
            p.ellipsoid((0,.85,0), (.23,.23,.23), BLUE, 1)
            p.ellipsoid((0,.85,0), (.12,.33,.12), IVORY, 0)
        else:
            for i in range(3):
                p.ellipsoid(((i-1)*.35,.55+i*.46,0), (.85-i*.20,.55,.65-i*.07), SAND if i%2==0 else HIDE, 0)
        mesh = p.finish()
        folder = ROOT/'media/decorations/mom_rpg/desert'/key/'v1'
        folder.mkdir(parents=True, exist_ok=True)
        files = {}
        for role, filename, blob, mime in [('model','model.glb',mesh.export(file_type='glb',tree_postprocessor=single_node),'model/gltf-binary'), ('recipe','recipe.json',(json.dumps({'schema_version':1,'builder_sha256':digest,'triangles':len(mesh.faces)},indent=2)+'\n').encode(),'application/json')]:
            path=folder/filename
            if role=='recipe' and path.exists():
                blob=path.read_bytes()
            if path.exists() and path.read_bytes()!=blob:
                raise ValueError('Immutable prop changed')
            path.write_bytes(blob)
            files[role]={'path':path.relative_to(ROOT/'media').as_posix(),'sha256':hashlib.sha256(blob).hexdigest(),'size_bytes':len(blob),'media_type':mime}
        identity='decoration.mom_rpg.desert.'+key
        entry={'id':identity,'kind':'decoration','title':label,'revision':1,'group':'MOM RPG','tags':['mom_rpg','desert'],'files':files}
        previous=next((a for a in catalog['assets'] if a['id']==identity),None)
        if previous and previous!=entry:
            raise ValueError('Immutable prop catalog changed')
        if not previous:
            catalog['assets'].append(entry)
    write_json(catalog_path,catalog)
    build_catalog(ROOT)
    print('Published desert fauna and scenery',flush=True)


if __name__=='__main__':
    build()
