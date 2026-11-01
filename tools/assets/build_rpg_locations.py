"""Publish immutable low-poly Sei and Hollow Crypt props in the BHM catalog."""
from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np
import trimesh
from monster_forge_sdk import AssetStore
from monster_forge_sdk.characters import decode_skin
from tools.assets.asset_policy import canonical_entry, retired_model

ROOT = Path(__file__).resolve().parents[2]
STONE = (150, 159, 170, 255)
DARK = (57, 65, 79, 255)
BLUE = (44, 87, 139, 255)
GOLD = (208, 163, 75, 255)
WOOD = (115, 76, 47, 255)
BONE = (193, 186, 156, 255)
CRYPT = (91, 99, 112, 255)
GREEN = (76, 143, 126, 255)


class Prop:
    def __init__(self) -> None:
        self.meshes: list[trimesh.Trimesh] = []

    def add(self, mesh, color, point=(0, 0, 0)):
        mesh.visual.vertex_colors = np.tile(np.array(color, dtype=np.uint8), (len(mesh.vertices), 1))
        mesh.apply_translation(point)
        self.meshes.append(mesh)

    def box(self, size, point, color=STONE):
        self.add(trimesh.creation.box(size), color, point)

    def cylinder(self, radius, height, point, color=STONE, sections=8):
        mesh = trimesh.creation.cylinder(radius, height, sections=sections)
        mesh.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, (1, 0, 0)))
        self.add(mesh, color, point)

    def cone(self, radius, height, point, color=BLUE, sections=8):
        mesh = trimesh.creation.cone(radius, height, sections=sections)
        mesh.apply_transform(trimesh.transformations.rotation_matrix(-math.pi / 2, (1, 0, 0)))
        self.add(mesh, color, point)

    def gem(self, radius, point, color=GOLD, scale=(1, 1, 1)):
        mesh = trimesh.creation.icosphere(subdivisions=0, radius=radius)
        mesh.apply_scale(scale)
        self.add(mesh, color, point)

    def arch(self, width=5, height=4, depth=.7, color=STONE):
        for x in (-width/2, width/2):
            self.box((.7, height*.65, depth), (x, height*.325, 0), color)
            self.box((1, .3, depth+.25), (x, .15, 0), DARK)
        for i in range(9):
            a = (i+.5)*math.pi/9
            mesh = trimesh.creation.box((width*math.pi/18+.15, .7, depth))
            mesh.apply_transform(trimesh.transformations.rotation_matrix(a-math.pi/2, (0,0,1)))
            self.add(mesh, color if i%3 else DARK, (width/2*math.cos(a), height*.65+width*.3*math.sin(a), 0))

    def roof(self, width, depth, y, color=BLUE):
        for x, angle in ((-width/4, .65), (width/4, -.65)):
            mesh=trimesh.creation.box((width/(2*math.cos(.65))+.05,.22,depth))
            mesh.apply_transform(trimesh.transformations.rotation_matrix(angle,(0,0,1)))
            self.add(mesh,color,(x,y+width/4*math.tan(.65),0))

    def spear(self, x=0, z=0):
        self.cylinder(.055, 2.9, (x,1.45,z), WOOD, 6)
        self.gem(.24,(x,3.05,z),STONE,(.65,1.7,.2))
        self.cylinder(.085,.18,(x,2.8,z),GOLD,6)


def load_colored(path):
    mesh=trimesh.load(path,force='mesh',process=False)
    raw=Path(path).read_bytes();length=struct.unpack_from('<I',raw,12)[0]
    doc=json.loads(raw[20:20+length]);attributes=doc['meshes'][0]['primitives'][0]['attributes']
    spec=doc['accessors'][attributes['COLOR_0']];view=doc['bufferViews'][spec['bufferView']]
    dtype=np.dtype({5121:'u1',5126:'<f4'}[spec['componentType']]);width={'VEC3':3,'VEC4':4}[spec['type']]
    colors=np.ndarray((spec['count'],width),dtype=dtype,buffer=raw,offset=28+length+view.get('byteOffset',0)+spec.get('byteOffset',0),strides=(view.get('byteStride',width*dtype.itemsize),dtype.itemsize))
    assert len(colors)==len(mesh.vertices)
    if dtype.kind=='f':colors=np.rint(np.clip(colors,0,1)*255).astype(np.uint8)
    mesh.visual=trimesh.visual.ColorVisuals(mesh=mesh,vertex_colors=colors)
    return mesh


def city(name):
    p=Prop()
    if name=='curtain_wall':
        p.box((6,3.1,1),(0,1.55,0));p.box((6.2,.3,1.35),(0,3.15,0),DARK)
        for x in (-2.5,-1.5,-.5,.5,1.5,2.5):p.box((.65,.6,1.2),(x,3.6,0))
    elif name=='corner_tower':
        p.cylinder(2,5,(0,2.5,0));p.cylinder(2.15,.4,(0,5,0),DARK)
        for i in range(8):
            a=i*math.pi/4;p.box((.7,.7,.7),(1.7*math.cos(a),5.5,1.7*math.sin(a)))
        p.cone(2.25,1.6,(0,5.55,0));p.box((.3,1.6,.06),(0,3.5,-1.99),DARK)
    elif name=='gatehouse':
        p.arch(6,4.2,1.5)
        for x in (-4.1,4.1):
            p.box((2.2,5,2.8),(x,2.5,0));p.roof(2.8,3.2,5)
            p.box((.3,1.25,.06),(x,3,-1.43),DARK)
        p.box((7.2,.55,1.8),(0,4.7,0),DARK)
        for x in range(-3,4):p.box((.65,.6,1.6),(x,5.25,0))
    elif name in ('keep','barracks','stable','smithy'):
        w,h,d={'keep':(7,5,6),'barracks':(6,2.8,4),'stable':(6,2.5,4),'smithy':(4,2.5,4)}[name]
        p.box((w,h,d),(0,h/2,0),STONE if name!='stable' else WOOD);p.roof(w+1,d+1,h)
        p.box((1.3,1.9,.08),(0,.95,-d/2-.05),DARK)
        for x in (-w*.32,w*.32):p.box((.6,.85,.08),(x,h*.67,-d/2-.05),BLUE)
        if name=='keep':
            for x in (-w/2,w/2):p.cylinder(1,5.8,(x,2.9,0));p.cone(1.25,1.5,(x,5.8,0))
        elif name=='smithy':
            p.box((1,3.5,1),(w/2,1.75,1),DARK);p.box((1.4,.45,.7),(-1,.7,-2.8),DARK)
        elif name=='stable':
            for x in (-2,0,2):p.box((.12,1.1,1.2),(x,.55,-2.4),WOOD)
    elif name=='watch_platform':
        for x in (-1,1):
            for z in (-1,1):p.box((.2,4.6,.2),(x,2.3,z),WOOD)
        p.box((2.6,.25,2.6),(0,2.5,0),WOOD);p.roof(3,3,4.6)
        for y in (.3,.7,1.1,1.5,1.9):p.box((1,.12,.18),(0,y,-1.15),GOLD)
    elif name=='city_banner':
        p.cylinder(.09,4,(0,2,0),DARK);p.box((1.4,2,.06),(.62,2.7,0),BLUE)
        p.box((.2,1.2,.08),(.62,2.7,-.05),GOLD);p.gem(.18,(0,4.15,0))
    elif name=='well':
        p.cylinder(1.1,.75,(0,.375,0));p.cylinder(.8,.05,(0,.76,0),BLUE)
        for x in (-1.2,1.2):p.box((.2,2.5,.2),(x,1.25,0),WOOD)
        p.roof(3,2,2.5)
    elif name=='supply_cart':
        p.box((2,.35,1.2),(0,.8,0),WOOD)
        for x in (-.95,.95):p.box((.15,.65,1.2),(x,1.2,0),WOOD)
        for x in (-1.2,1.2):
            mesh=trimesh.creation.cylinder(.52,.15,sections=10);mesh.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2,(0,1,0)));p.add(mesh,DARK,(x,.52,0))
        p.box((.18,.18,1.8),(.5,.8,1.25),WOOD);p.box((.18,.18,1.8),(-.5,.8,1.25),WOOD)
    elif name=='crate_stack':
        for pos in ((-.6,.5,0),(.6,.5,0),(0,1.5,0)):
            p.box((1,.95,1),pos,WOOD);p.box((1.05,.12,1.05),(pos[0],pos[1]+.3,pos[2]),GOLD)
    elif name=='training_dummy':
        p.cylinder(.12,2,(0,1,0),WOOD);p.box((1.6,.12,.12),(0,1.4,0),WOOD)
        p.gem(.4,(0,1.5,0),BONE,(.8,1.5,.65));p.gem(.27,(0,2.2,0),BONE)
    elif name=='weapon_rack':
        for x in (-.9,.9):p.box((.18,1.7,.3),(x,.85,0),WOOD)
        p.box((2.2,.15,.2),(0,1.3,0),WOOD)
        for x in (-.6,0,.6):p.spear(x,.1)
    elif name=='guard_spear':p.spear()
    elif name=='cavalry_guard':
        store=AssetStore(ROOT)
        for slot in ('torso','head','tail','front_left_leg','front_right_leg','hind_left_leg','hind_right_leg'):
            m=load_colored(store.path('character.animals.v15.library-animal-horse-01.parts.'+slot))
            p.meshes.append(m)
        from scipy.spatial.transform import Rotation

        from machine_of_monsters.animation import forward_kinematics, load_skeleton
        skeleton=load_skeleton('workshop_knees_v1');rots={b['id']:np.array(b['bind_rotation']) for b in skeleton['bones']}
        bind=forward_kinematics(skeleton,np.zeros(3),rots)
        for side in ('left','right'):
            for joint,angle in (('hip',-1.15),('knee',1.25)):rots[side+'_'+joint]=np.array([math.sin(angle/2),0,0,math.cos(angle/2)])
        pose=forward_kinematics(skeleton,np.zeros(3),rots)
        def matrix(pair):
            v,q=pair;m=np.eye(4);m[:3,:3]=Rotation.from_quat(q).as_matrix();m[:3,3]=v;return m
        for slot in ('torso','head','left_arm','right_arm','left_leg','right_leg'):
            key='character.mom_skins.v1.knight.parts.'+slot
            m=load_colored(store.path(key));w=decode_skin(store.read(key,'weights'))
            pts=np.column_stack((m.vertices,np.ones(len(m.vertices))));out=np.zeros_like(m.vertices)
            mats=np.array([matrix(pose[b])@np.linalg.inv(matrix(bind[b])) for b in w['bone_palette']])
            indices=np.array(w['skin_indices']);weights=np.array(w['skin_weights'])
            assert len(indices)==len(pts)
            for i in range(4):out+=np.einsum('nij,nj->ni',mats[indices[:,i]],pts)[:,:3]*weights[:,i,None]
            m.vertices=out*.8+np.array((0,1.1,-.1));p.meshes.append(m)
        p.spear(.55,.25);p.box((.8,.08,1),(0,1.76,-.1),BLUE)
    elif name=='palisade':
        for x in (-1.2,-.6,0,.6,1.2):p.box((.32,1.5,.32),(x,.75,0),WOOD);p.cone(.24,.35,(x,1.5,0),WOOD,4)
        p.box((3,.18,.18),(0,.7,-.15),DARK)
    elif name=='planter':
        p.box((1.6,.45,1.1),(0,.225,0));p.box((1.3,.05,.8),(0,.47,0),WOOD)
        for x in (-.45,0,.45):p.gem(.35,(x,.75,0),GREEN,(1,1.25,1))
    elif name=='bench':
        p.box((2,.16,.7),(0,.6,0),WOOD);p.box((2,.65,.12),(0,1,-.32),WOOD)
        for x in (-.7,.7):p.box((.15,.6,.5),(x,.3,0),DARK)
    elif name=='lamppost':
        p.cylinder(.12,2.7,(0,1.35,0),DARK);p.box((.55,.6,.55),(0,2.9,0),GOLD);p.cone(.45,.35,(0,3.2,0),BLUE,4)
    else:raise ValueError(name)
    return p


def crypt(name):
    p=Prop()
    if name=='vault_wall':
        p.box((6,2.8,1),(0,1.4,0),CRYPT)
        for x in (-2.5,-1.5,-.5,.5,1.5,2.5):p.box((.85,.5,1.05),(x,2.65,0),DARK)
        p.box((6.1,.2,1.15),(0,.15,0),DARK)
    elif name=='pillar':
        p.box((1.4,.25,1.4),(0,.125,0),DARK);p.cylinder(.45,3.3,(0,1.9,0),CRYPT);p.box((1.2,.3,1.2),(0,3.7,0),BONE)
    elif name in ('arched_door','broken_arch'):
        p.arch(4,3,.8,CRYPT)
        if name=='broken_arch':p.meshes=p.meshes[:-3];p.gem(.6,(2,.3,1),CRYPT)
    elif name in ('sarcophagus','coffin'):
        p.box((1.8,.7,3),(0,.35,0),CRYPT if name=='sarcophagus' else WOOD)
        p.box((2,.2,3.2),(0,.8,0),DARK);p.box((.15,.1,1.4),(0,.95,0),BONE);p.box((.8,.1,.15),(0,.95,-.2),BONE)
        if name=='sarcophagus':p.gem(.25,(0,1,1),BONE)
    elif name=='ritual_altar':
        p.box((3,.3,2.2),(0,.15,0),DARK);p.box((2.5,1,1.7),(0,.8,0),CRYPT);p.box((2.8,.2,2),(0,1.4,0),BONE);p.gem(.35,(0,1.8,0),GREEN,(1,1.8,1))
    elif name in ('bone_heap','skull_heap'):
        for i in range(9):
            x=(i%3-1)*.45;z=(i//3-1)*.4
            if name=='bone_heap':
                mesh=trimesh.creation.box((.8,.13,.13));mesh.apply_transform(trimesh.transformations.rotation_matrix(i*.9,(0,1,0)));p.add(mesh,BONE,(x,.1+i%3*.08,z))
            else:p.gem(.24,(x,.2+(i%2)*.1,z),BONE);p.box((.16,.08,.08),(x,.22,z+.2),DARK)
    elif name=='soul_brazier':
        p.cylinder(.38,.8,(0,.4,0),DARK);p.cylinder(.6,.2,(0,.9,0),CRYPT);p.gem(.4,(0,1.25,0),GREEN,(.75,1.8,.75))
    elif name=='hanging_cage':
        p.box((1.5,.15,1.5),(0,.1,0),DARK);p.box((1.5,.15,1.5),(0,2,0),DARK)
        for x in (-.7,0,.7):
            for z in (-.7,.7):p.box((.07,2,.07),(x,1,z),CRYPT)
        p.box((.06,.8,.06),(0,2.45,0),CRYPT)
    elif name=='sovereign_throne':
        p.box((3,.25,2.5),(0,.125,0),DARK);p.box((2,.75,1.5),(0,.7,0),CRYPT);p.box((2.3,3,.35),(0,1.8,-.65),CRYPT)
        for x in (-1.05,1.05):p.box((.3,1.2,1.5),(x,1.1,0),DARK);p.cone(.35,.8,(x,2.8,-.65),BONE,4)
        p.gem(.28,(0,2.6,-.4),GREEN)
    elif name=='rune_stone':
        p.gem(1,(0,1.1,0),CRYPT,(.8,1.5,.5));p.box((.12,1.2,.06),(0,1.3,.51),GREEN);p.box((.65,.12,.06),(0,1.3,.51),GREEN)
    elif name=='steps':
        for i in range(4):p.box((3,(i+1)*.2,.65),(0,(i+1)*.1,(i-1.5)*.6),CRYPT)
    elif name=='collapsed_wall':
        for i in range(7):p.gem(.65,((i%3-1)*.7,.35+(i//3)*.3,(i%2)*.6),CRYPT,(1,.65,1))
    elif name=='burial_urn':
        p.cylinder(.4,.7,(0,.35,0),CRYPT);p.cylinder(.22,.25,(0,.82,0),BONE);p.cone(.35,.2,(0,.95,0),DARK)
    elif name=='candelabrum':
        p.cylinder(.08,1.3,(0,.65,0),DARK);p.box((1.2,.1,.1),(0,1.3,0),DARK)
        for x in (-.5,0,.5):p.cylinder(.07,.3,(x,1.5,0),BONE);p.gem(.11,(x,1.8,0),GOLD,(.6,1.8,.6))
    elif name=='sentinel_statue':
        p.box((1.4,.4,1.4),(0,.2,0),DARK);p.box((.7,1.4,.45),(0,1.1,0),CRYPT);p.gem(.35,(0,2.1,0),CRYPT,(.8,1.1,1));p.box((.18,1.2,.18),(.5,1.1,0),BONE);p.box((.18,1.2,.18),(-.5,1.1,0),BONE)
    elif name=='iron_grille':
        p.box((3.6,.15,.25),(0,.1,0),DARK);p.box((3.6,.15,.25),(0,2.8,0),DARK)
        for x in np.linspace(-1.7,1.7,9):p.box((.08,2.8,.08),(x,1.4,0),CRYPT)
    elif name=='burial_niche':
        p.box((3,2.8,.5),(0,1.4,-.5),DARK)
        for x in (-1.4,1.4):p.box((.25,2.8,1.2),(x,1.4,0),CRYPT)
        for y in (.2,1.4,2.6):p.box((3,.18,1.2),(0,y,0),CRYPT)
        p.gem(.2,(-.4,1.6,0),BONE);p.gem(.2,(.4,.4,0),BONE)
    else:raise ValueError(name)
    return p


CITY = ('curtain_wall','corner_tower','gatehouse','keep','barracks','stable','smithy','watch_platform','city_banner','well','supply_cart','crate_stack','training_dummy','weapon_rack','guard_spear','cavalry_guard','palisade','planter','bench','lamppost')
CRYPT_PROPS = ('vault_wall','pillar','arched_door','broken_arch','sarcophagus','coffin','ritual_altar','bone_heap','skull_heap','soul_brazier','hanging_cage','sovereign_throne','rune_stone','steps','collapsed_wall','burial_urn','candelabrum','sentinel_statue','iron_grille','burial_niche')


def single_node(tree):
    tree['nodes']=[{'name':'rpg_prop','mesh':0}];tree['scenes']=[{'nodes':[0]}]


def build(root=ROOT):
    catalog=root/'media/imported_catalog.json';data=json.loads(catalog.read_text())
    for location, names, maker in [('sei',CITY,city),('hollow_crypt',CRYPT_PROPS,crypt)]:
        for name in names:
            version=5 if location=='sei' and name in ('gatehouse','keep','barracks','stable','smithy','watch_platform','well','cavalry_guard') else 4
            identity=f'decoration.mom_rpg.{location}.{name}.v{version}'
            if retired_model({'id': identity}):
                continue
            prop=maker(name);mesh=trimesh.util.concatenate(prop.meshes)
            folder=root/f'media/decorations/mom_rpg/v{version}'/location/name;folder.mkdir(parents=True,exist_ok=True)
            recipe={'schema_version':1,'id':identity,'coordinates':'metres; Y-up; ground Y=0','style':'Unified low-poly project style','bounds':mesh.bounds.tolist(),'triangles':len(mesh.faces),'source_parts':(['character.animals.v15.library-animal-horse-01','character.mom_skins.v1.knight'] if name=='cavalry_guard' else []),'palette':'matte stone, dark slate, blue cloth, muted gold' if location=='sei' else 'matte crypt slate, bone, verdigris, dark wood'}
            files={}
            for role,filename,payload,mime in [('model','model.glb',mesh.export(file_type='glb',tree_postprocessor=single_node),'model/gltf-binary'),('recipe','recipe.json',(json.dumps(recipe,ensure_ascii=False,indent=2)+'\n').encode(),'application/json')]:
                path=folder/filename
                if path.exists() and path.read_bytes()!=payload:raise ValueError('Immutable prop changed: '+identity)
                path.write_bytes(payload);files[role]={'path':path.relative_to(root/'media').as_posix(),'sha256':hashlib.sha256(payload).hexdigest(),'size_bytes':len(payload),'media_type':mime}
            group=('Декорации · MOM RPG · Сей · '+('Оборона' if name in ('curtain_wall','corner_tower','gatehouse','watch_platform','cavalry_guard','palisade','guard_spear') else 'Город')) if location=='sei' else 'Декорации · MOM RPG · Полая крипта · '+('Архитектура' if name in ('vault_wall','pillar','arched_door','broken_arch','steps','iron_grille','burial_niche') else 'Убранство')
            entry={'id':identity,'kind':'decoration','title':name.replace('_',' ').title(),'revision':1,'group':group,'tags':['mom_rpg',location,'low-poly','architecture' if name.endswith(('wall','tower','house','door')) else 'prop'],'files':files}
            entry=canonical_entry(entry)
            old=next((a for a in data['assets'] if a['id']==identity),None)
            if old and old!=entry:raise ValueError('Immutable catalog entry changed')
            if not old:data['assets'].append(entry)
            print(identity,len(mesh.faces),'triangles',flush=True)
    catalog.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    from tools.assets.build_catalog import build_catalog
    build_catalog(root)


if __name__=='__main__':build()
