"""The existing active authoring catalog and an explicit humanoid extension view."""

from __future__ import annotations

import json

from .registry import SUPPORTED_CONTRACTS, ConstructorRegistry, default_registry
from .settings import default_settings


def reference_presets():
    from ..constructor_presets import load_presets

    return load_presets("reference")


def presets():
    from ..constructor_presets import load_presets

    return load_presets("library", "mom_rpg")


def catalog(*, registry: ConstructorRegistry | None = None, include_legacy=True) -> dict:
    from . import _inventory

    registry = registry or default_registry()
    visible_races = registry.active_races if include_legacy else registry.supported_races
    back = []
    for donor in registry.outfits:
        m = json.loads((registry.source_folder(donor) / "parts.json").read_text())
        if "back_attachment" in m["parts"] or "left_wing" in m["parts"]:
            back.append(
                {"id": donor, "label": registry.outfits[donor], "contract": m["rig_reference"]}
            )
    back.extend(_inventory.back_options())
    back.extend(
        {"id": d["id"], "label": d["label"] + " · хвост", "contract": d["contract"]}
        for d in registry.exp_designs
        if d["race"] == "scorpion" and d.get("public", True)
    )
    back.extend(
        {"id": d["id"], "label": d["label"] + " · хвост", "contract": d["contract"]}
        for d in registry.animal_designs
    )
    active_contracts = {
        "humanoid_v1",
        *(registry.species[r][1] for r in visible_races if r in registry.species),
    }
    donor_races = {
        d["id"]: d["race"]
        for d in [
            *registry.original_designs,
            *registry.library_designs,
            *registry.reference_designs,
        ]
    }
    back = [
        item
        for item in back
        if item["contract"] in active_contracts
        and (item["id"] not in donor_races or donor_races[item["id"]] in visible_races)
    ]
    from ..constructor_knees import BIND_PROFILE
    from ..runtime import bind_bones

    bones = bind_bones(BIND_PROFILE)
    from ..constructor_atlas import HAIR_LABELS
    from ..constructor_atlas import available as atlas_available
    from ..constructor_atlas import catalog as atlas_catalog
    from ..constructor_atlas import presets as attribute_presets
    from ..constructor_cloth_motifs import LABELS as motif_labels
    from ..constructor_decor import OPTIONS, colorways
    from ..constructor_head_accessories import LABELS as HEAD_ACCESSORY_LABELS
    from ..constructor_mounts import options as mount_options
    from ..constructor_palette_previews import options as palette_options
    from ..constructor_part_descriptions import summaries as part_summaries

    return {
        "supported_contracts": list(SUPPORTED_CONTRACTS),
        "include_legacy": include_legacy,
        "schema_version": registry.version,
        "settings_version": registry.settings_version,
        "decor": OPTIONS,
        "features": registry.features,
        "cards_version": 28,
        "attribute_library": [spec for spec in atlas_catalog() if spec["id"] != "back"],
        "attribute_presets": attribute_presets(),
        "reference_presets": [
            p for p in reference_presets() if p["settings"]["race"] in visible_races
        ],
        "colorways": colorways(),
        "palette_options": palette_options(),
        "motif_labels": list(motif_labels),
        "attribute_hair_labels": HAIR_LABELS,
        "attribute_headwear_labels": list(HEAD_ACCESSORY_LABELS),
        "attribute_descriptions": part_summaries(),
        "part_descriptions_url": "/creature-workshop/constructor/part-descriptions",
        "contract": "humanoid_v1",
        "defaults": default_settings(registry=registry),
        "active_defaults": attribute_presets()[0]["settings"],
        "bind_bones": bones,
        "archived_race_labels": {
            key: race[0] for key, race in registry.races.items() if key not in visible_races
        },
        "races": [
            {
                "id": key,
                "label": label,
                "faces": [
                    f
                    for f in faces
                    if next(
                        (d.get("public", True) for d in registry.library_designs if d["id"] == f),
                        True,
                    )
                ],
                "female_face": female,
                "owned_body": key in registry.owned_races,
                "hidden_parts": registry.randomium_hidden_parts if key == "randomium" else [],
                "decor_options": {"emblem": registry.randomium_emblems}
                if key == "randomium"
                else {},
                "emblem_defaults": {
                    d["id"]: "randomium-red-dragon" if d["variant"] == 1 else "randomium-diamond"
                    for d in registry.owned_designs
                    if d["race"] == "randomium"
                }
                if key == "randomium"
                else {},
                "anatomy_only": key in registry.rpg_races,
                "human_upper": key == "centaur",
                "animal_body": key in registry.animal_species,
                "flying_body": key in registry.flyer_species,
                "tail_options": key == "scorpion",
                "mount_options": mount_options(key),
                "mane_options": registry.horse_manes if key == "beast-horse" else {},
                "form_options": registry.ghost_forms
                if key == "ghost"
                else {"regular": "Исходный силуэт", **registry.horse_forms}
                if key == "beast-horse"
                else {},
                "body_variants": {
                    g: [
                        d
                        for d in registry.exp_designs
                        if d["race"] == key and d["gender"] == g and d.get("public", True)
                    ]
                    if key in registry.exp_species
                    else [d for d in registry.animal_designs if d["race"] == key and g == "male"]
                    if key in registry.animal_species
                    else [
                        d
                        for d in registry.owned_designs
                        if d["race"] == key and d["gender"] == g and d.get("public", True)
                    ]
                    for g in ("male", "female")
                },
                "editable": key in registry.active_races,
                "contract": registry.rpg_races[key]["rig"]
                if key in registry.rpg_races
                else registry.species[key][1]
                if key in registry.species
                else "humanoid_v1",
                "animation_support": "authoring_only" if key in registry.species else "static_bind",
                "attribute_options": {
                    gender: {
                        e["id"]: atlas_available(e["id"], key, gender)
                        for e in atlas_catalog()
                        if e["id"] != "back"
                    }
                    for gender in ("male", "female")
                },
                "feature_labels": {"mouth": registry.bear_mouth_labels}
                if key in {"beorn", "panda"}
                else {},
                "feature_options": {
                    k: list(registry.bear_mouth_labels)
                    if key in {"beorn", "panda"} and k == "mouth"
                    else []
                    if key in registry.owned_races
                    or (key in registry.species and key != "centaur")
                    or (key == "skeleton" and k == "ears")
                    else list(v)
                    for k, v in registry.features.items()
                },
                "arm_label": "Левая лопасть"
                if key == "slime"
                else "Передние лапы"
                if key == "frog"
                else "Ветви"
                if key == "tree"
                else "Руки"
                if key in {"naga", "centaur"}
                else "Клешни"
                if key in {"scorpion", "crab"}
                else "Левые ноги"
                if key == "spider"
                else "Крылья"
                if key in {"sky-bird", "sky-bat", "sky-eagle"}
                else "Передние ноги"
                if key in registry.species
                else "Руки",
                "leg_label": "Правая лопасть"
                if key == "slime"
                else "Задние лапы"
                if key == "frog"
                else "Копыта и ноги"
                if key == "satyr"
                else "Корни"
                if key == "tree"
                else "Средние и задние ноги"
                if key == "beetle"
                else "Хвост"
                if key == "naga"
                else "Ноги коня"
                if key == "centaur"
                else "Правые ноги"
                if key == "spider"
                else "Ноги"
                if key in {"crab", "scorpion", "sky-bird", "sky-bat", "sky-eagle"}
                else "Задние ноги"
                if key in registry.species
                else "Ноги",
                "reference_faces": [
                    d["id"]
                    for d in registry.reference_designs
                    if d["race"] == key and d.get("public", True)
                ],
                "reference_hair": [
                    d["id"]
                    for d in registry.reference_designs
                    if d["race"] == key and d.get("public", True)
                ],
                "reference_outfits": [
                    d["id"]
                    for d in registry.reference_designs
                    if d["race"] == key and d.get("public", True)
                ],
                "goblin_glove_labels": registry.goblin_gloves if key == "goblin" else [],
                "goblin_boot_labels": registry.goblin_boots if key == "goblin" else [],
                "anatomies": {g: _inventory.racial_choices(key, g) for g in ("male", "female")},
                "library_faces": [
                    *[v["id"] for v in _inventory.racial_choices(key, "male")],
                    *[
                        d["id"]
                        for d in registry.library_designs
                        if d["race"] == key and d.get("public", True)
                    ],
                ],
                "library_hair": []
                if key == "ghost" or key in registry.rpg_races
                else [
                    *[
                        d["id"]
                        for d in registry.library_designs
                        if d["race"] == key and d.get("public", True)
                    ],
                    *[
                        identifier
                        for identifier, (race, _) in registry.procedural_hair.items()
                        if race == key
                    ],
                ],
                "library_outfits": list(registry.goblin_costumes)
                if key == "goblin"
                else [
                    d["id"]
                    for d in registry.library_designs
                    if d["race"] == key and d.get("public", True)
                ],
                "gender_mode": "neutral"
                if key in registry.owned_races
                and registry.owned_races[key]["neutral"]
                or key == "skeleton"
                or (key in registry.species and key not in {"naga", "centaur"})
                else "authored"
                if female
                else "derived",
                "default_back": next(
                    (
                        d["id"]
                        for d in registry.owned_designs
                        if d["race"] == key and d["gender"] == "male"
                    ),
                    None,
                )
                if key == "kobold"
                else "angel-guard-blue"
                if key == "angel"
                else None,
            }
            for key in visible_races
            for label, faces, female in [registry.races[key]]
        ],
        "outfits": [
            {
                "id": key,
                "label": label,
                "original": key in registry.original_ids,
                "race": next((d["race"] for d in registry.library_designs if d["id"] == key), None),
            }
            for key, label in registry.outfits.items()
            if donor_races.get(key) in {*visible_races, None}
        ],
        "face_labels": {
            d["id"]: d["label"]
            for d in [
                *registry.original_designs,
                *registry.library_designs,
                *registry.reference_designs,
            ]
            if d["race"] in visible_races
        },
        "hair": {
            key: value
            for key, value in registry.hair.items()
            if key not in registry.procedural_hair
            or registry.procedural_hair[key][0] in visible_races
        },
        "forms": {
            k: v
            for k, v in registry.forms.items()
            if k not in registry.horse_forms and k != "ghost_spirit"
        },
        "eyes": registry.eyes,
        "back": back,
        "colors": registry.default_colors,
        "status": "authoring_draft",
        "presets": [p for p in presets() if p["settings"]["race"] in visible_races],
    }
