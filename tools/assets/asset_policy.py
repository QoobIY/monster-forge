"""Canonical media groups and explicitly replaced scenery; no implicit latest revision."""

from __future__ import annotations

from tools.assets.icon_policy import canonical_entry as canonical_icon

REPLACEMENTS = {
    "decoration.angel_arena_nova.equipment.hammer": "equipment.shared.crystal.mace",
    "decoration.angel_arena_nova.equipment.blade": "equipment.shared.gladiator.sword",
    "decoration.angel_arena_nova.equipment.staff": "equipment.shared.crystal.staff",
    "decoration.angel_arena_nova.equipment.bow": "equipment.shared.woodland.bow",
    "decoration.angel_arena_nova.equipment.axe": "equipment.shared.gladiator.axe",
    "decoration.angel_arena_nova.equipment.relic": "equipment.shared.crystal.book",
    "decoration.hearthvale.equipment.sword": "equipment.shared.skeletal.sword",
    "decoration.hearthvale.equipment.axe": "equipment.shared.skeletal.axe",
    "decoration.hearthvale.equipment.staff": "equipment.shared.skeletal.staff",
    "decoration.hearthvale.equipment.bow": "equipment.shared.skeletal.bow",
    "decoration.hearthvale.equipment.greatsword": "equipment.shared.skeletal.greatsword",
    "decoration.mom_rpg.sei.cavalry_guard.v4": "decoration.mom_rpg.sei.cavalry_guard.v5",
    "decoration.hearthvale.architecture.crypt_arch": "decoration.mom_rpg.hollow_crypt.entrance_arch",
    "decoration.hearthvale.architecture.house_blue": "decoration.mom_rpg.sei.house_blue",
    "decoration.hearthvale.architecture.house_warm": "decoration.mom_rpg.sei.house_warm",
    "decoration.hearthvale.architecture.pillar": "decoration.mom_rpg.hollow_crypt.pillar_small",
    "decoration.hearthvale.architecture.sealed_portal": "decoration.mom_rpg.sei.sealed_portal",
    "decoration.mom_rpg.architecture.house_blue": "decoration.mom_rpg.sei.house_blue",
    "decoration.mom_rpg.architecture.house_warm": "decoration.mom_rpg.sei.house_warm",
    "decoration.mom_rpg.hollow_crypt.arched_door.v4": "decoration.mom_rpg.hollow_crypt.arched_door",
    "decoration.mom_rpg.hollow_crypt.broken_arch.v4": "decoration.mom_rpg.hollow_crypt.broken_arch",
    "decoration.mom_rpg.hollow_crypt.burial_niche.v4": "decoration.mom_rpg.hollow_crypt.burial_niche",
    "decoration.mom_rpg.hollow_crypt.pillar.v4": "decoration.mom_rpg.hollow_crypt.pillar",
    "decoration.mom_rpg.hollow_crypt.vault_wall.v4": "decoration.mom_rpg.hollow_crypt.vault_wall",
    "decoration.mom_rpg.sei.barracks.v4": "decoration.mom_rpg.sei.barracks",
    "decoration.mom_rpg.sei.barracks.v5": "decoration.mom_rpg.sei.barracks",
    "decoration.mom_rpg.sei.corner_tower.v4": "decoration.mom_rpg.sei.corner_tower",
    "decoration.mom_rpg.sei.curtain_wall.v4": "decoration.mom_rpg.sei.curtain_wall",
    "decoration.mom_rpg.sei.gatehouse.v4": "decoration.mom_rpg.sei.gatehouse",
    "decoration.mom_rpg.sei.gatehouse.v5": "decoration.mom_rpg.sei.gatehouse",
    "decoration.mom_rpg.sei.keep.v4": "decoration.mom_rpg.sei.keep",
    "decoration.mom_rpg.sei.keep.v5": "decoration.mom_rpg.sei.keep",
    "decoration.mom_rpg.sei.smithy.v4": "decoration.mom_rpg.sei.smithy",
    "decoration.mom_rpg.sei.smithy.v5": "decoration.mom_rpg.sei.smithy",
    "decoration.mom_rpg.sei.stable.v4": "decoration.mom_rpg.sei.stable",
    "decoration.mom_rpg.sei.stable.v5": "decoration.mom_rpg.sei.stable",
    "decoration.mom_rpg.sei.watch_platform.v4": "decoration.mom_rpg.sei.watch_platform",
    "decoration.mom_rpg.sei.watch_platform.v5": "decoration.mom_rpg.sei.watch_platform",
    "decoration.mom_rpg.sei.well.v4": "decoration.mom_rpg.sei.well",
    "decoration.mom_rpg.sei.well.v5": "decoration.mom_rpg.sei.well",
}

RETIRED_DECORATIONS = frozenset(
    [
        "decoration.hearthvale.equipment.shield",
        "decoration.20260827t170917z-a9881dfe.decoration_cluster",
        "decoration.20260827t170917z-a9881dfe.landmark",
        "decoration.20260828t110918z-b491a755",
        "decoration.20260829t193939z-0005add9",
        "decoration.20260829t193952z-1937024e",
        "decoration.20260830t092614z-33ebf93a",
        "decoration.20260831t143948z-d02633a4",
        "decoration.20260831t143958z-41932be9",
        "decoration.20260831t144013z-22ebbf95",
        "decoration.20260831t144023z-b266c75e",
    ]
)


RETIRED_DECORATION_ROOTS = frozenset(
    ".".join(identity.split(".")[:2]) for identity in RETIRED_DECORATIONS
    if identity.startswith("decoration.202608")
)


def retired_model(entry: dict) -> bool:
    return entry["id"] in RETIRED_DECORATIONS or entry["id"] in REPLACEMENTS


def canonical_entry(entry: dict) -> dict:
    entry = canonical_icon(entry)
    identity = entry["id"]
    group = entry.get("group", "")
    if entry.get("kind") == "decoration" and (
        ".equipment." in identity
        or identity.startswith("equipment.")
        or "equipment" in entry.get("tags", [])
    ):
        return {**entry, "group": "Снаряжение"}
    if (
        "angel_arena" in identity
        or "nova" in entry.get("tags", [])
        or "Angel Arena" in group
        or "angel_arena_nova" in group
    ):
        return {**entry, "group": "Nova"}
    if (
        "mom_rpg" in identity
        or "hearthvale" in identity
        or "MOM RPG" in group
        or "Hearthvale" in group
    ):
        return {**entry, "group": "MOM RPG"}
    return entry
