"""Publish immutable generated terrain images without changing their pixels."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from PIL import Image

from tools.assets.build_catalog import build_catalog

ROOT = Path(__file__).resolve().parents[2]
TITLES = {'crypt_slate': 'Плиты древней крипты', 'crypt_cracked': 'Треснувшая кладка',
          'crypt_moss': 'Сырые замшелые плиты', 'crypt_rock': 'Расколотый скальный берег',
          'meadow': 'Луговая трава HD', 'earth': 'Утоптанная земля HD',
          'paving': 'Городское мощение HD', 'sand': 'Песчаная дорога HD',
          'moss': 'Мох и камень HD', 'celestial': 'Небесный мрамор HD',
          'ash': 'Вулканический пепел HD', 'basalt': 'Базальтовые плиты HD',
          'cinder': 'Остывшие угли HD', 'redstone': 'Красный камень HD',
          'arcane': 'Магический камень HD', 'rock': 'Светлые скалы HD',
          'rock_dark': 'Тёмные скалы HD'}


def publish(manifest: Path, *, version: str = "v2") -> None:
    if not re.fullmatch(r"v[1-9][0-9]*", version):
        raise ValueError("Invalid terrain version")
    catalog = ROOT / 'media/imported_catalog.json'
    data = json.loads(catalog.read_text())
    for row in json.loads(manifest.read_text()):
        name = row['id']
        if name not in TITLES:
            raise ValueError('Unknown terrain material')
        payload = Path(row['path']).read_bytes()
        with Image.open(row['path']) as image:
            width, height = image.size
            if image.format != 'PNG' or width != height or not 1024 <= width <= 2048:
                raise ValueError('Terrain source must be a square HD PNG')
        cliff = name in {'crypt_rock', 'rock', 'rock_dark'}
        folder = ROOT / 'media/terrain' / version / name
        recipe = {'schema_version': 1, 'generator': 'image_gen_builtin',
                  'prompt': row['prompt'], 'source_sha256': hashlib.sha256(payload).hexdigest(),
                  'source_resolution': [width, height], 'seamless': True,
                  'recommended_world_size': 4 if cliff else 3.6,
                  'projection': 'triplanar' if cliff else 'world_xy'}
        if row.get('reference'):
            recipe['reference_sha256'] = hashlib.sha256(Path(row['reference']).read_bytes()).hexdigest()
        if row.get('style_profile_sha256'):
            recipe['style_profile_sha256'] = row['style_profile_sha256']
        files = {}
        for role, name_on_disk, content, mime in (
            ('image', 'tile.png', payload, 'image/png'),
            ('recipe', 'recipe.json', (json.dumps(recipe, ensure_ascii=False, indent=2)+'\n').encode(), 'application/json'),
        ):
            path = folder / name_on_disk
            if path.exists() and path.read_bytes() != content:
                raise ValueError('Published terrain revision is immutable')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            files[role] = {'path': path.relative_to(ROOT/'media').as_posix(),
                           'sha256': hashlib.sha256(content).hexdigest(),
                           'size_bytes': len(content), 'media_type': mime}
        entry = {'id': 'terrain.'+version+'.'+name, 'kind': 'terrain',
                 'title': row.get('title', TITLES[name]),
                 'revision': 1, 'group': 'Ландшафт · '+('Клифы' if cliff else 'Тайлы · Мощение'),
                 'tags': ['terrain', 'seamless', 'cliff' if cliff else 'tile', 'matte', 'painted', 'mom_rpg', 'hd'] + ([] if name.startswith('crypt_') else ['angel_arena_nova']),
                 'files': files}
        existing = next((asset for asset in data['assets'] if asset['id'] == entry['id']), None)
        if existing and existing != entry:
            raise ValueError('Published terrain entry is immutable')
        if existing is None:
            data['assets'].append(entry)
    catalog.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    build_catalog(ROOT)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--version', default='v2')
    args = parser.parse_args()
    publish(args.manifest, version=args.version)
