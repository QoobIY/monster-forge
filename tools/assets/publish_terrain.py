"""Immutable seamless matte terrain tiles and cliffs for the shared SDK."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MATERIALS = {
    'meadow': ('Луговая трава', (111,139,105), 'Земля'),
    'earth': ('Утоптанная земля', (143,127,103), 'Земля'),
    'sand': ('Светлый песчаник', (190,183,154), 'Земля'),
    'paving': ('Старая брусчатка', (153,151,137), 'Мощение'),
    'crypt': ('Камень древней крипты', (91,99,111), 'Мощение'),
    'moss': ('Замшелый камень', (100,119,104), 'Мощение'),
    'ash': ('Пепельная земля', (113,104,112), 'Земля'),
    'cinder': ('Обожжённый камень', (139,107,96), 'Земля'),
    'basalt': ('Тёмный базальт', (90,85,98), 'Земля'),
    'celestial': ('Камень небесного двора', (170,184,182), 'Мощение'),
    'arcane': ('Камень магического двора', (154,151,177), 'Мощение'),
    'redstone': ('Камень огненного двора', (137,97,104), 'Мощение'),
    'rock': ('Выветренная скала', (125,129,121), 'Клифы'),
    'rock_dark': ('Базальтовый клиф', (85,81,92), 'Клифы'),
    'rock_sand': ('Клиф из песчаника', (153,140,116), 'Клифы'),
}


def tile(name, base, cliff, seed):
    n = 256
    y, x = np.mgrid[0:n, 0:n] / n
    rng = np.random.default_rng(seed)
    tone = np.zeros((n, n))
    for frequency, amount in [(1, 2.2), (2, 1.8), (4, 1.3), (8, .6), (16, .25)]:
        for _ in range(3):
            kx, ky = rng.integers(0, frequency + 1, 2)
            phase = rng.uniform(0, 2*np.pi)
            tone += amount*np.cos(2*np.pi*(kx*x+ky*y)+phase)
    # Periodic irregular polygon cells. No rectangular tile outlines or edge frame.
    count = 24 if cliff else 38
    points = rng.random((count, 2))
    dx = np.abs(x[..., None]-points[:, 0]); dx = np.minimum(dx, 1-dx)
    dy = np.abs(y[..., None]-points[:, 1]); dy = np.minimum(dy, 1-dy)
    dist = dx*dx + dy*dy*(3 if cliff else 1)
    order = np.argsort(dist, axis=2)
    labels = order[:, :, 0]
    tone += rng.uniform(-5, 5, count)[labels]
    if name in {'paving','crypt','celestial','arcane','redstone'} or cliff:
        nearest = np.take_along_axis(dist, order[:, :, :2], axis=2)
        edge = np.exp(-(nearest[:, :, 1]-nearest[:, :, 0])/0.0007)
        tone -= edge*(9 if cliff else 5)
    rgb = np.clip(np.array(base)[None, None, :] + tone[..., None], 0, 255).astype('uint8')
    return Image.fromarray(rgb)


def build():
    media = ROOT/'media'
    catalog = media/'imported_catalog.json'
    data = json.loads(catalog.read_text())
    for seed, (name, (title, color, group)) in enumerate(MATERIALS.items()):
        folder = media/'terrain/v1'/name
        folder.mkdir(parents=True, exist_ok=True)
        image = folder/'tile.png'
        import io
        buffer = io.BytesIO()
        tile(name, color, group == 'Клифы', seed+920).save(buffer, format='PNG')
        payload = buffer.getvalue()
        recipe = (json.dumps({'schema_version':1, 'generator':'periodic_facets_v1', 'seed':seed+920, 'base_color':color, 'seamless':True, 'recommended_world_size':6, 'projection':'triplanar' if group=='Клифы' else 'world_xy'}, ensure_ascii=False, indent=2)+'\n').encode()
        files = {}
        for role, path, content, mime in [('image',image,payload,'image/png'), ('recipe',folder/'recipe.json',recipe,'application/json')]:
            if path.exists() and path.read_bytes() != content:
                raise ValueError('Immutable terrain asset changed: '+name)
            path.write_bytes(content)
            files[role] = {'path':path.relative_to(media).as_posix(), 'sha256':hashlib.sha256(content).hexdigest(), 'size_bytes':len(content), 'media_type':mime}
        entry = {'id':'terrain.v1.'+name, 'kind':'terrain', 'title':title, 'revision':1, 'group':'Ландшафт · '+('Клифы' if group=='Клифы' else 'Тайлы · '+group), 'tags':['terrain','seamless','cliff' if group=='Клифы' else 'tile','matte','low-poly'], 'files':files}
        old = next((row for row in data['assets'] if row['id']==entry['id']), None)
        if old and old != entry:
            raise ValueError('Immutable catalog entry changed')
        if not old:
            data['assets'].append(entry)
    catalog.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    from tools.assets.build_catalog import build_catalog
    build_catalog(ROOT)
    print('Published',len(MATERIALS),'categorized terrain assets')


if __name__=='__main__':
    build()
