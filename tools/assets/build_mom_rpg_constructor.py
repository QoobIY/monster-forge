"""Publish RPG constructor classes and the Sovereign's grave in BHM."""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import trimesh
from monsterforge.paths import ROOT
from tools.assets import build_mom_skins as skins
from tools.assets.build_catalog import build_catalog
from tools.assets.build_rpg_locations import BONE, CRYPT, DARK, GREEN, Prop, single_node


def build() -> None:
    skins.DESTINATION = ROOT / 'media/constructor/mom_rpg_classes/v1'
    from monsterforge.constructor_presets import load_presets
    with tempfile.TemporaryDirectory(prefix='bhm-rpg-classes-') as temp:
        for preset in load_presets('mom_rpg'):
            category, name = preset['id'].split('/')
            if category == 'classes':
                skins.publish_humanoid(name, preset['label'], preset['settings'], Path(temp) / name)

    grave = Prop()
    grave.box((1.8, .18, 2.8), (0, .09, 0), DARK)
    grave.box((1.55, .16, 2.5), (0, .25, 0), CRYPT)
    grave.box((1.25, 1.65, .3), (0, .98, -1.05), CRYPT)
    grave.gem(.7, (0, 1.65, -1.05), CRYPT, (1, .65, .22))
    grave.box((1.35, .16, .36), (0, .36, -1.05), DARK)
    # Bone crown, inset skull and a restrained soul rune identify the skeleton boss.
    for x in (-.43, 0, .43):
        grave.cone(.14, .38, (x, 1.96, -1.05), BONE, 4)
    grave.gem(.22, (0, 1.34, -.84), BONE, (1, 1.15, .4))
    for x in (-.08, .08):
        grave.box((.07, .07, .035), (x, 1.37, -.75), DARK)
    grave.box((.07, .38, .035), (0, .83, -.88), GREEN)
    grave.box((.35, .07, .035), (0, .85, -.88), GREEN)
    model = trimesh.util.concatenate(grave.meshes)
    identity = 'decoration.mom_rpg.hollow_crypt.sovereign_grave.v1'
    folder = ROOT / 'media/decorations/mom_rpg/v1/hollow_crypt/sovereign_grave'
    folder.mkdir(parents=True, exist_ok=True)
    recipe = {'schema_version': 1, 'id': identity, 'authoring': 'build_mom_rpg_constructor.py',
              'coordinates': 'metres; Y-up; ground Y=0', 'style': 'BHM RPG crypt low-poly',
              'bounds': model.bounds.tolist(), 'triangles': len(model.faces)}
    payloads = [('model', 'model.glb', model.export(file_type='glb', tree_postprocessor=single_node), 'model/gltf-binary'),
                ('recipe', 'recipe.json', (json.dumps(recipe, ensure_ascii=False, indent=2) + '\n').encode(), 'application/json')]
    files = {}
    for role, name, payload, mime in payloads:
        path = folder / name
        if path.exists() and path.read_bytes() != payload:
            raise ValueError('Immutable grave changed')
        path.write_bytes(payload)
        files[role] = {'path': path.relative_to(ROOT / 'media').as_posix(),
                       'sha256': hashlib.sha256(payload).hexdigest(),
                       'size_bytes': len(payload), 'media_type': mime}
    catalog_path = ROOT / 'media/imported_catalog.json'
    catalog = json.loads(catalog_path.read_text())
    entry = {'id': identity, 'kind': 'decoration', 'title': 'Могила Скелетного Суверена',
             'revision': 1, 'group': 'MOM RPG',
             'tags': ['mom_rpg', 'hollow_crypt', 'low-poly', 'grave'], 'files': files}
    previous = next((a for a in catalog['assets'] if a['id'] == identity), None)
    if previous and previous != entry:
        raise ValueError('Immutable grave catalog changed')
    if not previous:
        catalog['assets'].append(entry)
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    build_catalog(ROOT)
    print('Published grave and three constructor class assemblies')


if __name__ == '__main__':
    build()
