"""Publish promo cast using existing constructor parts, never custom meshes."""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path

from monsterforge import constructor_randomiums, workshop_constructor
from monsterforge.constructor_presets import load_presets
from tools.assets.publish_assembly import publish


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--randomium-source", type=Path, default=constructor_randomiums.SOURCE)
    args = parser.parse_args()
    source = args.randomium_source.resolve(strict=True)
    constructor_randomiums.SOURCE = source
    workshop_constructor.RANDOMIUM_SOURCE = source
    heroes = {p["id"]: p for p in load_presets("mom_rpg")}
    for name in ("witcher", "viking", "mage"):
        recipe = heroes["classes/" + name]
        publish(
            "character.shared.promo." + name,
            recipe["label"] + " · проморолик",
            recipe["settings"],
        )
    presets = workshop_constructor.presets()
    god = next(
        p["settings"] for p in presets if p["settings"]["face"] == "native-randomium-random-god-01"
    )
    publish("character.shared.promo.random_god", "Бог Рандома", god)
    for number in range(1, 6):
        face = f"library-skeleton-{number:02d}"
        preset = next(p for p in presets if p["settings"]["face"] == face)
        publish(
            f"character.shared.promo.sentry-{number:02d}",
            preset["label"] + " · страж крипты",
            preset["settings"],
        )
    king = deepcopy(next(p["settings"] for p in presets if p["settings"]["face"] == "library-skeleton-01"))
    king["decor"].update(headwear="crown", shoulders="spikes")
    king["colors"].update(
        skin="#c9c3ad", cloth="#392a53", accent="#b8994f", metal="#a99468", eyes="#60c2ff"
    )
    publish("character.shared.promo.skeleton_sovereign", "Скелетный Суверен · проморолик", king)


if __name__ == "__main__":
    main()
