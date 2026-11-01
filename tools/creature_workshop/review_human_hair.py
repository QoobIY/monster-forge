"""Numerical human hair audit and Front picker thumbnails from derived heads."""
import hashlib
import json

import numpy as np

from monsterforge import workshop_constructor as editor
from monsterforge.constructor_atlas import apply as atlas, available
from monsterforge.constructor_face_fit import surfaces
from monsterforge.constructor_surface_fit import apply as fit, triangles, radial_hit
from tools.creature_workshop.geometry import compile_recipe, mesh, render_png

OUTPUT=editor.ROOT/'media/constructor/hair_review/v1'


def head(settings):
    recipe,source=editor._load(settings['face'],'head')
    sources=[source]
    recipe=editor._head(recipe,settings,sources)
    atlas(recipe,settings,'head')
    fit(recipe,'head')
    recipe['commands'].sort(key=lambda c:c['stage'])
    return recipe


def audit(recipe):
    arrays=compile_recipe(recipe)
    caps=[c for c in recipe['commands'] if c['part'].endswith(('hair_crown','hair_cap','scalp'))]
    if len(caps)>1:raise ValueError('A braid was replaced by duplicate scalp shells')
    face=surfaces(recipe);samples=0;clearances=[]
    if face and caps:
        top=max(mesh(c)[0][:,1].max() for c in face)
        skin_tri,cap_tri=triangles(face),triangles(caps)
        for drop in (.14,.23,.32,.37):
            for angle in (-.5,0,.5):
                origin=np.array([0,top-drop,.005]);direction=np.array([np.sin(angle),0,-np.cos(angle)])
                skin=radial_hit(skin_tri,origin,direction)
                if skin is None:continue
                hair=radial_hit(cap_tri,origin,direction)
                if hair is None or hair-skin<.003:
                    raise ValueError(f'Uncovered occiput at drop={drop}, angle={angle}')
                clearances.append(hair-skin);samples+=1
    return {'triangles':len(arrays[0])//3,'rear_samples':samples,
            'minimum_cap_clearance':min(clearances) if clearances else None,
            'cap_count':len(caps),
            'coverage_scope':'posterior scalp' if caps else 'open/shaved hairstyle; topology only',
            'rear_curtain':any(c['part']=='hair_back_curtain' for c in recipe['commands']),
            'recipe_sha256':editor._hash(editor._encoded(recipe))}


def run():
    cases=[];files={}
    catalog=editor.catalog();human=next(r for r in catalog['races'] if r['id']=='human')
    for gender in ('male','female'):
        for face in range(1,11):
            for number in available('hair','human',gender):
                s=editor.default_settings();s['gender']=gender
                s['reference_parts'].update({gender+'_faces':face,'hair':number})
                recipe=head(s)
                cases.append({'gender':gender,'face':face,'hair':number,**audit(recipe)})
                if face==1:
                    path=OUTPUT/gender/'hair'/f'{number:02d}.png';path.parent.mkdir(parents=True,exist_ok=True)
                    render_png(path,compile_recipe(recipe),yaw=0,pitch=0,size=256,recipe=recipe)
                    files[str(path.relative_to(OUTPUT))]=hashlib.sha256(path.read_bytes()).hexdigest()
            print(gender,'face',face,flush=True)
        for donor in [*human['library_hair'],*human['reference_hair']]:
            s=editor.default_settings();s.update(gender=gender,hair=donor)
            recipe=head(s)
            cases.append({'gender':gender,'face':'native','hair':donor,**audit(recipe)})
            path=OUTPUT/gender/'native'/f'{donor}.png';path.parent.mkdir(parents=True,exist_ok=True)
            render_png(path,compile_recipe(recipe),yaw=0,pitch=0,size=256,recipe=recipe)
            files[str(path.relative_to(OUTPUT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    record={'schema_version':1,'revision':1,'cases':cases,'files':files,
            'scope':'Numerical topology and posterior scalp coverage; not an artistic quality verdict.'}
    (OUTPUT/'audit.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print('Audited',len(cases),'heads;',sum(c['rear_samples'] for c in cases),'rear rays',flush=True)


if __name__=='__main__':run()
