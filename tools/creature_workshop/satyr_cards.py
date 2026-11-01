"""Front cards of derived satyr modules; frozen v1 source assets stay intact."""
import json
import tempfile
from pathlib import Path

import numpy as np

from monsterforge import workshop_constructor as editor
from monsterforge.constructor_marsh_forest import DESIGNS
from tools.creature_workshop.geometry import compile_recipe, render_png

OUTPUT=editor.ROOT/'media/constructor/satyr/v2/cards'


def run():
    for design in DESIGNS:
        if design['race']!='satyr':continue
        s=editor.default_settings();s.update(race='satyr',**{k:design['id'] for k in ('face','outfit','arms','legs')})
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manifest=editor.build(s,root)
            recipes={slot:json.loads((root/'parts'/slot/'recipe.json').read_text()) for slot in manifest['parts']}
            folder=OUTPUT/design['id'];folder.mkdir(parents=True,exist_ok=True)
            for category in ('face','outfit','arms','legs'):
                slots=['head'] if category=='face' else list(recipes) if category=='outfit' else [s for s in recipes if s.endswith('_arm' if category=='arms' else '_leg')]
                arrays=[compile_recipe(recipes[s]) for s in slots]
                merged=tuple(np.concatenate([a[i] for a in arrays]) for i in range(3))+([],)
                render_png(folder/(category+'.png'),merged,yaw=0,pitch=0,size=256,recipe={'commands':[c for s in slots for c in recipes[s]['commands']]})
            (folder/'record.json').write_bytes(editor._encoded({'schema_version':1,'assembly_id':manifest['id'],
                'files':{p.name:editor._hash(p.read_bytes()) for p in folder.glob('*.png')}}))
        print(design['id'],flush=True)


if __name__=='__main__':run()
