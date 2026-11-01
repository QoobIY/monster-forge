"""Publish MoM cosmetic assemblies from BHM constructor settings and source parts."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np
import trimesh
from machine_of_monsters.animation import forward_kinematics, load_skeleton
from machine_of_monsters.animation.rigs import body_rig

from monsterforge.paths import ROOT
from monsterforge.skin_weights import build_weight_sidecar
from monsterforge.workshop_constructor import build, default_settings
from tools.assets.build_catalog import build_catalog
from tools.creature_workshop.geometry import compile_recipe, export_glb

DESTINATION = ROOT / 'media/constructor/mom_skins/v1'
SLOTS = ('head','torso','left_arm','right_arm','left_leg','right_leg')

def write(path, data):
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
    if path.exists() and path.read_text() != encoded:
        raise ValueError(f'Immutable published assembly changed: {path}')
    if not path.exists(): path.write_text(encoded)

def settings(donor='library-human-01', **changes):
    value=default_settings()
    value.update(face=donor,outfit=donor,arms=donor,legs=donor)
    for key, change in changes.items():
        if isinstance(change,dict): value[key].update(change)
        else: value[key]=change
    return value

def bounded_weights(model, slot, profile):
    data=build_weight_sidecar(model,slot,bind_profile=profile)
    old=data['bone_palette'];palette=[b for b in old if b in data['allowed_bones']]
    remap={i:palette.index(b) for i,b in enumerate(old) if b in palette}
    data['skin_indices']=[[remap[i] if w>0 else 0 for i,w in zip(row,ws,strict=True)] for row,ws in zip(data['skin_indices'],data['skin_weights'],strict=True)]
    data['bone_palette']=palette;data['bind_profile']=profile
    return data

def merge(base, attachment, prefix, *, scale=1., offset=(0,0,0)):
    base=copy.deepcopy(base);attachment=copy.deepcopy(attachment)
    for key, value in attachment['palette'].items(): base['palette'][prefix+key]=value
    for command in attachment['commands']:
        from monsterforge.workshop_constructor import _transform
        command=_transform(command,np.array([scale]*3),np.array(offset),prefix)
        command['material']=prefix+command['material'];command['id']=prefix+command['id']
        command['slot']=base['commands'][0]['slot'];command['part']=prefix+command['part']
        base['commands'].append(command)
    base.setdefault('assembly_sources',[]).append({'recipe':attachment['id'],'transform':{'scale':scale,'offset':offset}})
    base['commands'].sort(key=lambda command: command['stage'])
    return base

def publish_humanoid(name, label, choices, stage):
    catalog = json.loads((ROOT / 'media/catalog.json').read_text())
    if catalog.get('constructor_storage_version') == 2:
        from tools.assets.publish_assembly import publish
        from tools.assets.publish_character_runtime import character_identity
        scope = DESTINATION.relative_to(ROOT / 'media/constructor').as_posix().replace('/', '.')
        identity, _ = character_identity('character.' + scope + '.' + name)
        return publish(identity, label, choices)
    manifest=build(choices,stage,weights=False)
    recipes={slot:json.loads((stage/'parts'/slot/'recipe.json').read_text()) for slot in SLOTS}
    if 'back_attachment' in manifest['parts']:
        back=json.loads((stage/'parts/back_attachment/recipe.json').read_text())
        recipes['head']=merge(recipes['head'],back,'back_')
    output=DESTINATION/name; (output/'parts').mkdir(parents=True,exist_ok=True)
    for slot,recipe in recipes.items():
        model=output/'parts'/f'{slot}.glb'; arrays=compile_recipe(recipe)
        if not model.exists(): export_glb(model,arrays,recipe)
        write(model.with_suffix('.recipe.json'),recipe)
        weights=bounded_weights(model,slot,manifest['bind_profile'])
        if slot=='head' and 'back_attachment' in manifest['parts']:
            # Back belongs to the head slot, rigid at the neck; feathers never bend into the face.
            ends=arrays[3];begin=0;neck=weights['bone_palette'].index('neck')
            for command,end in zip(recipe['commands'],ends,strict=True):
                if command['part'].startswith('back_'):
                    for i in range(begin,end): weights['skin_indices'][i]=[neck,0,0,0];weights['skin_weights'][i]=[1,0,0,0]
                begin=end
        write(model.with_suffix('.weights.json'),weights)
    write(output/'record.json',{'schema_version':1,'id':name,'label':label,'race':choices['race'],'rig':'humanoid_v1','bind_profile':manifest['bind_profile'],'constructor_settings':choices,'parts':{s:{'model':f'parts/{s}.glb'} for s in SLOTS},'source_assembly':json.loads((stage/'assembly.json').read_text())})
    print('Published',name,flush=True)

def seated_rider(stage, rider_settings=None, *, seat=None):
    build(rider_settings or settings('library-human-04',decor={'headwear':'circlet'},colors={'cloth':'#256568','accent':'#d2b671'}),stage,weights=False)
    skeleton=load_skeleton('workshop_knees_v1');rotations={b['id']:np.array(b['bind_rotation']) for b in skeleton['bones']}
    bind=forward_kinematics(skeleton,np.zeros(3),rotations)
    from scipy.optimize import least_squares
    from scipy.spatial.transform import Rotation
    if seat is None:
        raise ValueError('Mounted pose requires the selected animal seat surface')
    scale = seat['scale']
    offset = np.array(seat['offset'])
    origin = np.array(seat['contact'])
    def solve(start, middle, end, middle_target, end_target):
        def apply(values):
            rotations[start] = Rotation.from_rotvec(values[:3]).as_quat()
            rotations[middle] = Rotation.from_rotvec(values[3:]).as_quat()
            return forward_kinematics(skeleton, np.zeros(3), rotations)
        def residual(values):
            pose = apply(values)
            return np.concatenate((pose[middle][0] - middle_target,
                                   pose[end][0] - end_target))
        result = least_squares(residual, np.array([-.45, 0, 0, .8, 0, 0]),
                               max_nfev=150, ftol=1e-10, xtol=1e-10, gtol=1e-10)
        pose = apply(result.x)
        # Boots stay level instead of following the shin rotation.
        rotations[end] = Rotation.from_quat(pose[middle][1]).inv().as_quat()
    for side, sign in (('left', -1), ('right', 1)):
        width = seat['half_width']
        knee = origin + [sign * (width + .09), -.22, .16]
        foot = origin + [sign * (width + .13), -.59, .10]
        solve(side+'_hip', side+'_knee', side+'_foot',
              (knee-offset)/scale, (foot-offset)/scale)
        elbow = origin + [sign*.34, .45, .15]
        hand = origin + [sign*.25, .32, .43]
        solve(side+'_shoulder', side+'_elbow', side+'_hand',
              (elbow-offset)/scale, (hand-offset)/scale)
    posed=forward_kinematics(skeleton,np.zeros(3),rotations)
    def _transform(position, quaternion):
        matrix = np.eye(4)
        matrix[:3,:3] = Rotation.from_quat(quaternion).as_matrix()
        matrix[:3,3] = position
        return matrix
    parts=[]
    for slot in SLOTS:
        recipe=json.loads((stage/'parts'/slot/'recipe.json').read_text())
        arrays=compile_recipe(recipe);points=arrays[0];weights=bounded_weights(stage/'parts'/slot/'model.glb',slot,'workshop_knees_v1')
        matrices=[_transform(*posed[b]) @ np.linalg.inv(_transform(*bind[b])) for b in weights['bone_palette']]
        homogeneous=np.column_stack((points,np.ones(len(points))));deformed=np.zeros((len(points),3))
        for col in range(4):
            indices=np.array(weights['skin_indices'])[:,col];strength=np.array(weights['skin_weights'])[:,col]
            transformed=np.einsum('nij,nj->ni',np.array(matrices)[indices],homogeneous)[:,:3]
            deformed+=transformed*strength[:,None]
        # Retain each original surface and material as one indexed mesh command.
        commands=[];begin=0
        for command,end in zip(recipe['commands'],arrays[3],strict=True):
            vertices=deformed[begin:end]
            if any(token in command['part'] for token in ('rivet', 'buckle')):
                # Small metal fasteners follow one bone; blended twist can invert them.
                dense=np.zeros(len(matrices))
                for ids, strengths in zip(weights['skin_indices'][begin:end], weights['skin_weights'][begin:end], strict=True):
                    for bone, strength in zip(ids, strengths, strict=True):
                        dense[bone] += strength
                vertices=(homogeneous[begin:end] @ matrices[int(dense.argmax())].T)[:,:3]
            surface=trimesh.Trimesh(vertices=vertices,faces=np.arange(len(vertices)).reshape(-1,3),process=True)
            assert surface.is_watertight, command['part']
            commands.append({'purpose':command.get('purpose','Seated rider surface'),'id':command['id'],'part':'rider_'+command['part'],'slot':'torso','stage':command['stage'],'material':command['material'],'op':'indexed_mesh','vertices':surface.vertices.tolist(),'faces':surface.faces.tolist()})
            begin=end
        recipe['commands']=commands;parts.append(recipe)
    rider=parts[0]
    for index,part in enumerate(parts[1:]): rider=merge(rider,part,'rider_'+str(index)+'_')
    return rider

def publish_quadruped(name,label,animal,stage,rider_stage=None,rider_settings=None,mount_settings=None,identity=None):
    compact = json.loads((ROOT / 'media/catalog.json').read_text()).get('constructor_storage_version') == 2
    choices=copy.deepcopy(mount_settings) if mount_settings is not None else settings('library-animal-'+animal+'-01',race='beast-'+animal)
    if rider_stage is not None:
        choices['decor'].update(belt='mount_war', headwear='mount_bridle')
    if animal=='sheep': choices['back']='back-angel-large';choices['colors'].update(back_primary='#eee6c8',back_secondary='#b9d9ef')
    build(choices,stage,weights=False)
    rig=body_rig('quadruped_v1');slots=rig.slot_ids
    recipes={slot:json.loads((stage/'parts'/slot/'recipe.json').read_text()) for slot in slots}
    if animal=='sheep': recipes['torso']=merge(recipes['torso'],json.loads((stage/'parts/back_attachment/recipe.json').read_text()),'wings_')
    if rider_stage is not None:
        from monsterforge.constructor_mounts import Surface
        carrier = next(command for command in recipes['torso']['commands']
                       if 'chest_waist_rump' in command['part'] or 'ribcage_waist_croup' in command['part'])
        surface = Surface(carrier)
        lo, hi = surface.bounds
        z = float(lo[2] + (hi[2]-lo[2])*.49)
        # Match the constructor saddle's contact surface, excluding the neck/mane.
        contact = surface.radial(z, 0, .091)
        side = surface.radial(z+.16, 1.25, 0)
        scale = .8
        seat = {'schema_version': 1, 'contact': contact.tolist(),
                'half_width': float(abs(side[0])), 'scale': scale,
                'offset': (contact - [0, scale*.90, 0]).tolist()}
        rider=seated_rider(rider_stage,rider_settings,seat=seat)
        recipes['torso']=merge(recipes['torso'],rider,'mounted_',scale=scale,offset=seat['offset'])
    output = stage / 'baked-input' if compact else DESTINATION / name
    (output/'parts').mkdir(parents=True,exist_ok=True)
    for slot,recipe in recipes.items():
        model=output/'parts'/f'{slot}.glb';arrays=compile_recipe(recipe)
        if not model.exists():export_glb(model,arrays,recipe)
        write(model.with_suffix('.recipe.json'),recipe)
        points=np.asarray(trimesh.load(model,force='mesh',process=False).vertices)
        if slot.endswith('_leg'):
            base=slot.removesuffix('_leg');palette=[base,base+'_knee',base+'_foot']
            # Preserve the author's floor and joint height; blend around the middle joint.
            t=np.clip((points[:,1]-points[:,1].min())/max(1e-6,np.ptp(points[:,1])),0,1)
            dense=np.column_stack((np.maximum(0,2*t-1),1-np.abs(2*t-1),np.maximum(0,1-2*t)))
        else:
            palette=['body'] if slot=='torso' else ['head'] if slot=='head' else ['tail'];dense=np.ones((len(points),1))
        allowed=rig.allowed_bones(slot);assert set(palette)<=allowed
        indices=np.zeros((len(points),4),dtype=int);weights=np.zeros((len(points),4))
        for index in range(len(palette)):indices[:,index]=index;weights[:,index]=dense[:,index]
        write(model.with_suffix('.weights.json'),{'schema_version':1,'slot':slot,'skeleton_id':rig.id,'model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),'vertex_count':len(points),'bone_palette':palette,'allowed_bones':sorted(allowed),'skin_indices':indices.tolist(),'skin_weights':weights.tolist(),'bind_profile':'canonical','method':'quadruped_slot_chain_v1'})
    if compact:
        from monsterforge.character_assembly import bake_build, encoded, instruction
        from tools.assets.publish_assembly import publish_model
        from tools.assets.publish_character_runtime import character_identity
        parts = {slot: {'model': f'parts/{slot}.glb', 'weights': f'parts/{slot}.weights.json',
                        'revision_id': hashlib.sha256(encoded(recipes[slot])).hexdigest(),
                        'model_sha256': hashlib.sha256((output / 'parts' / (slot + '.glb')).read_bytes()).hexdigest()}
                 for slot in slots}
        manifest = {'contract': rig.id, 'bind_profile': 'canonical', 'parts': parts,
                    'id': hashlib.sha256(encoded(parts)).hexdigest()}
        model = bake_build(output, manifest)
        data = instruction(choices, manifest, model)
        # The mounted rider and attachment transforms are authoring inputs.
        for slot in slots:
            data['parts'][slot]['recipe'] = recipes[slot]
        data['mounted_rider'] = rider_stage is not None
        if rider_stage is not None:
            data['mounted_seat'] = seat
            data['mounted_rider_settings'] = rider_settings or settings('library-human-04',decor={'headwear':'circlet'},colors={'cloth':'#256568','accent':'#d2b671'})
        scope = DESTINATION.relative_to(ROOT / 'media/constructor').as_posix().replace('/', '.')
        if identity is None:
            identity, _ = character_identity('character.' + scope + '.' + name)
        return publish_model(identity, label, data, model)
    write(output/'record.json',{'schema_version':1,'id':name,'label':label,'race':'beast-'+animal,'rig':rig.id,'constructor_settings':choices,'parts':{s:{'model':f'parts/{s}.glb'} for s in slots},'mounted_rider':rider_stage is not None})
    print('Published',name,flush=True)

def main():
    from monsterforge.constructor_presets import load_presets
    with tempfile.TemporaryDirectory(prefix='bhm-mom-skins-') as temp:
        stage=Path(temp)
        for preset in load_presets('mom_skins'):
            publish_humanoid(preset['id'], preset['label'], preset['settings'], stage/preset['id'])
        publish_quadruped('winged_sheep','Барашек с крыльями','sheep',stage/'sheep')
        publish_quadruped('tiger_rider','Наездник на тигре','tiger',stage/'tiger',stage/'rider')
    build_catalog()

if __name__=='__main__':main()
