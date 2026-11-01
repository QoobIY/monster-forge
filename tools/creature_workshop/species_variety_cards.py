"""Build Front picker cards from the same derived recipes as the constructor.

Run with python -m tools.creature_workshop.species_variety_cards.
These are UI thumbnails, not a geometry quality check or new source assets.
"""
import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np

from monsterforge import workshop_constructor as editor
from monsterforge.constructor_species_variety import RACES
from tools.creature_workshop.geometry import compile_recipe, render_png

OUTPUT = editor.ROOT/'media/constructor/species_anatomy/v1/cards'


def build_cards():
    for design in editor.SPECIES_DESIGNS:
        race, donor = design['race'], design['id']
        if race not in {*RACES, 'centaur'}:
            continue
        for gender in (('male', 'female') if race=='centaur' else ('male',)):
            folder=OUTPUT/donor/gender
            folder.mkdir(parents=True,exist_ok=True)
            settings=editor.default_settings()
            settings.update(race=race,gender=gender,face=donor,outfit=donor,arms=donor,legs=donor)
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);manifest=editor.build(settings,root)
                recipes={slot:json.loads((root/'parts'/slot/'recipe.json').read_text()) for slot in manifest['parts']}
                for category in ('face','outfit','arms','legs'):
                    slots=(['head'] if category=='face' else list(recipes) if category=='outfit' else
                           [s for s in recipes if s.endswith(('_arm','_claw')) or s.startswith('front_') or s.endswith('_leg_1')] if category=='arms' else
                           [s for s in recipes if '_leg' in s])
                    arrays=[compile_recipe(recipes[s]) for s in slots]
                    merged=tuple(np.concatenate([a[i] for a in arrays]) for i in range(3))+([],)
                    render_png(folder/(category+'.png'),merged,yaw=0,pitch=0,size=256,
                               recipe={'commands':[c for s in slots for c in recipes[s]['commands']]})
                metadata={'schema_version':1,'assembly_id':manifest['id'],'settings':settings,
                          'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.glob('*.png'))}}
                (folder/'record.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
            print(donor,gender,flush=True)


if __name__=='__main__':
    build_cards()
