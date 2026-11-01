"""Publish reusable faceted bone projectile meshes through the BHM catalog."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from tools.assets.build_catalog import build_catalog
from tools.assets.build_rpg_locations import single_node

ROOT=Path(__file__).resolve().parents[2]
IVORY=(206,196,160,255)
LIGHT=(236,224,185,255)
SHADOW=(129,119,93,255)

class Bones:
    def __init__(self):self.meshes=[]
    def add(self,mesh,color):
        mesh.visual.vertex_colors=np.tile(np.asarray(color,dtype=np.uint8),(len(mesh.vertices),1))
        self.meshes.append(mesh)
    def segment(self,start,end,radius,color=IVORY,tip=None):
        start,end=np.asarray(start,float),np.asarray(end,float)
        mesh=trimesh.creation.cone(radius,np.linalg.norm(end-start),sections=7) if tip else trimesh.creation.cylinder(radius,np.linalg.norm(end-start),sections=7)
        if tip:
            mesh.apply_transform(trimesh.geometry.align_vectors((0,0,1),end-start));mesh.apply_translation(start)
        else:
            mesh.apply_transform(trimesh.geometry.align_vectors((0,0,1),end-start));mesh.apply_translation((start+end)/2)
        self.add(mesh,color)
    def joint(self,point,scale):
        mesh=trimesh.creation.icosphere(subdivisions=0,radius=1)
        mesh.apply_scale(scale);mesh.apply_translation(point);self.add(mesh,LIGHT)
    def plate(self,points,color):
        mesh=trimesh.Trimesh(vertices=points,faces=[(0,1,2),(0,2,3),(0,3,1),(1,3,2)],process=False)
        mesh.fix_normals();self.add(mesh,color)
    def finish(self):
        mesh=trimesh.util.concatenate(self.meshes);mesh.fix_normals();mesh.unmerge_vertices()
        if not np.isfinite(mesh.vertices).all() or len(mesh.faces)>700:raise ValueError('Bone mesh budget')
        return mesh

def arrow():
    bone=Bones()
    bone.segment((0,.24,0),(0,1.55,0),.072)
    bone.joint((0,.42,0),(.13,.12,.105));bone.joint((0,1.46,0),(.11,.10,.09))
    # Two hooked osseous barbs read as a broadhead, not a generic light streak.
    bone.plate([(0,0,0),(-.26,.41,0),(-.08,.31,.08),(.02,.35,-.06)],LIGHT)
    bone.plate([(0,0,0),(.26,.41,0),(.08,.31,-.08),(-.02,.35,.06)],IVORY)
    for angle in (0,2.0943951024,4.1887902048):
        c,s=np.cos(angle),np.sin(angle)
        bone.plate([(0,1.27,0),(.24*c,1.7,.24*s),(0,1.82,0),(.035*s,1.5,-.035*c)],SHADOW)
    return bone.finish()

def spike():
    bone=Bones()
    bone.joint((0,.12,0),(.29,.26,.25))
    bone.segment((0,.05,0),(.10,.75,0),.21)
    bone.joint((.10,.72,0),(.22,.20,.19))
    bone.segment((.10,.70,0),(.18,1.46,.03),.145)
    bone.segment((.18,1.40,.03),(-.03,2.24,.02),.15,LIGHT,tip=True)
    bone.segment((.06,.70,0),(-.45,1.28,.05),.12)
    bone.segment((-.45,1.22,.05),(-.59,1.65,.03),.125,IVORY,tip=True)
    return bone.finish()

def build(root=ROOT):
    catalog_path=root/'media/imported_catalog.json'
    catalog=json.loads(catalog_path.read_text())
    for name,mesh in (('bone_arrow',arrow()),('bone_spike',spike())):
        identity='decoration.shared.vfx.'+name
        folder=root/'media/decorations/shared/vfx'/name/'v1'
        folder.mkdir(parents=True,exist_ok=True)
        recipe={'schema_version':1,'id':identity,'coordinates':'metres, Y up; arrow tip at Y=0, bone root at ground',
                'style_profile_sha256':hashlib.sha256((root/'config/style_profile.json').read_bytes()).hexdigest(),
                'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'triangles':len(mesh.faces),'bounds':mesh.bounds.tolist(),
                'design':'Faceted ivory bone, broad osseous shapes, matte colors; reusable projectile and erupting rib'}
        files={}
        for role,filename,payload,mime in (
            ('model','model.glb',mesh.export(file_type='glb',tree_postprocessor=single_node),'model/gltf-binary'),
            ('recipe','recipe.json',(json.dumps(recipe,indent=2)+'\n').encode(),'application/json')):
            path=folder/filename
            if path.exists() and path.read_bytes()!=payload:raise ValueError('Immutable bone revision already exists')
            path.write_bytes(payload)
            files[role]={'path':path.relative_to(root/'media').as_posix(),'sha256':hashlib.sha256(payload).hexdigest(),'size_bytes':len(payload),'media_type':mime}
        entry={'id':identity,'kind':'decoration','revision':1,
               'title':'Костяная стрела' if name=='bone_arrow' else 'Костяной шип',
               'group':'MOM RPG','tags':['shared','vfx','projectile','bone','low-poly'],'files':files}
        previous=next((row for row in catalog['assets'] if row['id']==identity),None)
        if previous and previous!=entry:raise ValueError('Immutable bone asset already exists')
        if not previous:catalog['assets'].append(entry)
        print(identity,len(mesh.faces),'triangles')
    catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    build_catalog(root)

if __name__=='__main__':build()
