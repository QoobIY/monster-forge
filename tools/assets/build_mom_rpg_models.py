"""Publish constructor presets as immutable, map-scoped model revisions."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np

from monsterforge.constructor_marsh_forest import RACES, encoded, immutable, publish_sources
from monsterforge.constructor_presets import load_presets
from monsterforge.paths import ROOT
from monsterforge.workshop_constructor import build as assemble
from tools.assets import build_mom_skins as skins
from tools.assets.build_catalog import build_catalog
from tools.creature_workshop.geometry import compile_recipe, render_png


def publish_owned(name: str, preset: dict, stage: Path, output: Path) -> None:
    manifest = assemble(preset['settings'], stage, weights=True)
    for slot, info in manifest['parts'].items():
        model = output / 'parts' / (slot + '.glb')
        immutable(model, (stage / info['model']).read_bytes())
        immutable(model.with_suffix('.recipe.json'), (stage / 'parts' / slot / 'recipe.json').read_bytes())
        immutable(model.with_suffix('.weights.json'), (stage / info['weights']).read_bytes())
    immutable(output / 'record.json', encoded({
        'schema_version': 1, 'id': name, 'label': preset['label'],
        'race': preset['settings']['race'], 'rig': manifest['contract'],
        'bind_profile': manifest['bind_profile'], 'constructor_settings': preset['settings'],
        'parts': {slot: {'model': f'parts/{slot}.glb'} for slot in manifest['parts']},
        'source_assembly': json.loads((stage / 'assembly.json').read_text())}))
    immutable(output / 'preview.png', (stage / 'preview.png').read_bytes())


def build() -> None:
    catalog = json.loads((ROOT / 'media/catalog.json').read_text())
    if catalog.get('constructor_storage_version') == 2:
        from tools.assets.publish_assembly import publish
        for preset in load_presets('mom_rpg'):
            publish('character.maps.mom_rpg.' + preset['id'].replace('/', '.'), preset['label'], preset['settings'])
        return
    publish_sources()
    previous = skins.DESTINATION
    try:
        with tempfile.TemporaryDirectory(prefix='bhm-rpg-models-') as temporary:
            for preset in load_presets('mom_rpg'):
                category, name = preset['id'].split('/')
                skins.DESTINATION = (ROOT / 'media/constructor/mom_rpg_classes/v3'
                                     if category == 'classes' else
                                     ROOT / 'media/constructor/mom_rpg/v2' / category)
                stage = Path(temporary) / category / name
                if preset['settings']['race'] in RACES:
                    publish_owned(name, preset, stage, skins.DESTINATION / name)
                else:
                    skins.publish_humanoid(name, preset['label'], preset['settings'], stage)
                preview = skins.DESTINATION / name / 'preview.png'
                if not preview.exists():
                    recipes = [json.loads(p.read_text()) for p in sorted(
                        (skins.DESTINATION / name / 'parts').glob('*.recipe.json'))]
                    arrays = [compile_recipe(recipe) for recipe in recipes]
                    merged = tuple(np.concatenate([a[i] for a in arrays])
                                   for i in range(3)) + ([],)
                    render_png(preview, merged, size=512)
    finally:
        skins.DESTINATION = previous
    build_catalog()


if __name__ == '__main__':
    build()
