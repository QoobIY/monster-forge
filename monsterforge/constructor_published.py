"""Read immutable character publications from an optional asset release."""
from __future__ import annotations

import hashlib
import json
import re

from monster_forge_sdk import AssetNotFound, AssetStore

from .paths import ROOT


def _entries(store=None):
    if store is None:
        if not (ROOT / 'media/catalog.json').is_file():
            return
        store = AssetStore(ROOT)
    for body in store.list('character'):
        if not body.id.endswith('.body'):
            continue
        if 'assembly' in body.files:
            record = json.loads(store.read(body.id, 'assembly'))
            if record.get('schema_version') != 2:
                raise ValueError('Неизвестная версия инструкции сборки')
            if record.get('constructor_settings') is not None:
                identifier = hashlib.sha256(body.id.encode()).hexdigest()
                yield store, body, None, record, identifier
            continue
        try:
            torso = store.get(body.id.removesuffix('.body') + '.parts.torso')
        except AssetNotFound:
            continue
        if 'recipe' not in torso.files:
            continue
        folder = (store.media_root / torso.files['recipe'].path).resolve().parent.parent
        if not folder.is_relative_to((store.media_root / 'constructor').resolve()):
            continue
        record_path = folder / 'record.json'
        if not record_path.is_file():
            continue
        record = json.loads(record_path.read_text())
        if 'constructor_settings' not in record:
            continue
        identifier = hashlib.sha256(body.id.encode()).hexdigest()
        yield store, body, torso, record, identifier


def list_published(*, store=None):
    from .constructor import DEFAULT_REGISTRY
    from .constructor.settings import validate_settings
    result = []
    for publication_store, body, torso, record, identifier in _entries(store):
        item = {'id': identifier, 'source': 'mom', 'asset_id': body.id,
                'label': record.get('label', body.title), 'revision': body.revision,
                'preview': f'/creature-workshop/constructor/published/{identifier}/preview',
                'model_url': f'/creature-workshop/constructor/published/{identifier}/model',
                'download': f'/creature-workshop/constructor/published/{identifier}/download',
                'model_sha256': body.files['model'].sha256, 'editable': False}
        try:
            if record.get('schema_version') not in {1,2}:
                raise ValueError('Неизвестная версия опубликованного персонажа')
            # The catalog pins the recipe hash. Editable settings come from that
            # recipe rather than a similarly named preset or an older revision.
            if record['schema_version'] == 2:
                item['settings'] = validate_settings(record['constructor_settings'])
            else:
                recipe = json.loads(publication_store.read(torso.id, 'recipe'))
                item['settings'] = validate_settings(recipe['constructor']['settings'])
            item['editable'] = DEFAULT_REGISTRY.is_editable(item['settings'])
            if not item['editable']:
                item['edit_error'] = 'Эта раса отсутствует в активном каталоге конструктора'
        except (ValueError, KeyError) as error:
            item['edit_error'] = str(error)
        result.append(item)
    return sorted(result, key=lambda item: (not item['asset_id'].startswith('character.maps.mom_rpg.'), item['label']))


def _selected(identifier, *, store=None):
    if re.fullmatch(r'[0-9a-f]{64}', identifier) is None:
        raise ValueError('Некорректный ID опубликованного персонажа')
    for entry in _entries(store):
        if entry[-1] == identifier:
            return entry
    raise FileNotFoundError(identifier)


def model_blob(identifier, *, store=None):
    store, body, _, _, _ = _selected(identifier, store=store)
    return store.read(body.id, 'model')


def published_model(identifier, *, store=None):
    from .character_assembly import preview_payload
    return preview_payload(model_blob(identifier, store=store))


def preview_blob(identifier, *, store=None):
    from .character_assembly import preview_image
    return preview_image(model_blob(identifier, store=store))
