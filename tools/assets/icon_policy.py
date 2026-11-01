"""Canonical library categories; retired icon families cannot be republished."""

from __future__ import annotations

RETIRED_GROUPS = frozenset({
    'Акт 1. Скелеты', 'Способности и эффекты', 'Интерфейс · items',
    'Интерфейс · placeholders', 'Интерфейс · pvp', 'Интерфейс · stats',
    'Игровые иконки · icons', 'Косметика · Архив',
})
RETIRED_UI_FOLDERS = frozenset({'items', 'placeholders', 'pvp', 'stats'})


def retired_icon(entry: dict) -> bool:
    group = entry.get('group', '')
    return entry.get('kind') == 'icon' and any(
        group == old or group.startswith(old+'/') for old in RETIRED_GROUPS)


def canonical_entry(entry: dict) -> dict:
    if entry.get('kind') != 'icon':
        return entry
    path = entry.get('files', {}).get('image', {}).get('path', '')
    if path.startswith('icons/maps/angel_arena_nova/') or 'nova' in entry.get('tags', []):
        return {**entry, 'group': 'Nova'}
    return entry
