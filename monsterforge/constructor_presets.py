"""Load the shared, versioned constructor preset library without code defaults."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

from .paths import CONFIG_DIR

DIRECTORY = CONFIG_DIR / 'constructor_presets/v1'
GROUPS = ('library', 'mom_rpg', 'reference', 'attribute', 'mom_skins')


def _read(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise ValueError(f'Cannot read constructor preset {path}: {error}') from error


def load_presets(*groups: str) -> list[dict]:
    """Read complete settings; preserve file order and apply settings migrations.

    Published assemblies hold immutable snapshots. This library is the sole
    editable source for shipped presets, shared by the UI and build commands.
    """
    from .constructor.settings import validate_settings

    selected = set(groups or GROUPS)
    if not selected <= set(GROUPS):
        raise ValueError('Unknown constructor preset group')
    root = DIRECTORY.resolve()
    index = _read(root / 'index.json')
    if (not isinstance(index, dict) or set(index) != {'schema_version', 'presets'} or
            type(index['schema_version']) is not int or index['schema_version'] != 1 or
            not isinstance(index['presets'], list)):
        raise ValueError('Unsupported constructor preset index schema')
    result, paths, identities = [], set(), set()
    for entry in index['presets']:
        if not isinstance(entry, dict) or set(entry) != {'group', 'path'}:
            raise ValueError('Invalid constructor preset index entry')
        group, relative = entry['group'], entry['path']
        if group not in GROUPS or not isinstance(relative, str):
            raise ValueError('Invalid constructor preset group or path')
        path = (root / relative).resolve()
        if (not path.is_relative_to(root) or path.suffix != '.json' or
                PurePosixPath(relative).parts[0] != group or relative in paths):
            raise ValueError(f'Invalid or duplicate constructor preset path: {relative}')
        paths.add(relative)
        if group not in selected:
            continue
        record = _read(path)
        if (not isinstance(record, dict) or
                not {'schema_version', 'id', 'label', 'settings'} <= set(record) or
                set(record) - {'schema_version', 'id', 'label', 'settings', 'reference_image'} or
                type(record['schema_version']) is not int or record['schema_version'] != 1):
            raise ValueError(f'Unsupported constructor preset schema: {relative}')
        identity = record['id']
        if (not isinstance(identity, str) or relative != f'{group}/{identity}.json' or
                (group, identity) in identities or
                not isinstance(record['label'], str) or not record['label'].strip() or
                'reference_image' in record and not isinstance(record['reference_image'], str)):
            raise ValueError(f'Invalid constructor preset identity: {relative}')
        identities.add((group, identity))
        try:
            settings = validate_settings(record['settings'])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f'Invalid constructor preset settings {relative}: {error}') from error
        result.append({k: v for k, v in record.items() if k != 'schema_version'} | {'settings': settings})
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*.json')}
    if actual != paths | {'index.json'}:
        raise ValueError('Constructor preset files differ from index: ' +
                         ', '.join(sorted(actual ^ (paths | {'index.json'}))))
    return result
