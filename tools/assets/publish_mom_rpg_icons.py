"""Publish imagegen bone equipment icons with Nova style provenance in BHM."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

from PIL import Image
from tools.assets.build_catalog import ROOT, build_catalog


def build(jobs_path: Path) -> None:
    media = ROOT / 'media'
    catalog_path = media / 'imported_catalog.json'
    catalog = json.loads(catalog_path.read_text())
    references = ['icons/maps/angel_arena_nova/assets/icons/painted/item_classic_boots_of_speed.png',
                  'icons/maps/angel_arena_nova/assets/icons/painted/item_mid_runebound_staff.png']
    for job in json.loads(jobs_path.read_text()):
        identity = 'icon.item.mom_rpg.v1.' + job['key']
        folder = media / 'icons/mom_rpg/v1' / job['key']
        folder.mkdir(parents=True, exist_ok=True)
        source = Path(job['path']).read_bytes()
        image = Image.open(io.BytesIO(source))
        if image.width != image.height or image.width < 256:
            raise ValueError('Expected square icon original')
        preview = image.convert('RGB').resize((256, 256), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        preview.save(buffer, format='PNG')
        recipe = {'schema_version': 1, 'tool': 'imagegen', 'label': job['label'],
                  'style': 'angel_arena_nova', 'prompt': job['prompt'],
                  'source_sha256': hashlib.sha256(source).hexdigest(),
                  'references': [{'path': p, 'sha256': hashlib.sha256((media / p).read_bytes()).hexdigest()} for p in references],
                  'ui_export': {'size': [256, 256], 'filter': 'lanczos', 'background': 'opaque'}}
        files = {}
        for role, name, payload, mime in [('image', 'icon.png', buffer.getvalue(), 'image/png'),
                                         ('source', 'source.png', source, 'image/png'),
                                         ('recipe', 'recipe.json', (json.dumps(recipe, ensure_ascii=False, indent=2) + '\n').encode(), 'application/json')]:
            path = folder / name
            if path.exists() and path.read_bytes() != payload:
                raise ValueError('Immutable icon changed: ' + identity)
            path.write_bytes(payload)
            files[role] = {'path': path.relative_to(media).as_posix(),
                           'sha256': hashlib.sha256(payload).hexdigest(),
                           'size_bytes': len(payload), 'media_type': mime}
        entry = {'id': identity, 'kind': 'icon', 'title': job['label'], 'revision': 1,
                 'group': 'MOM RPG',
                 'tags': ['mom_rpg', 'equipment', 'imagegen', 'angel_arena_nova_style'], 'files': files}
        previous = next((a for a in catalog['assets'] if a['id'] == identity), None)
        if previous and previous != entry:
            raise ValueError('Immutable icon catalog changed')
        if not previous:
            catalog['assets'].append(entry)
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    build_catalog(ROOT)
    print('Published RPG item icons with Nova references')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('jobs', type=Path)
    build(parser.parse_args().jobs)
