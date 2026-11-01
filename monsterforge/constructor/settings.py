"""Settings schema admission and migrations, independent of geometry and HTTP."""

from __future__ import annotations

import copy
import json
import math
import re

from ..constructor_atlas import defaults as atlas_defaults
from ..constructor_portraits import defaults as feature_defaults
from .registry import ConstructorRegistry, default_registry


def default_settings(*, registry: ConstructorRegistry | None = None) -> dict:
    registry = registry or default_registry()
    return {
        "schema_version": registry.settings_version,
        "race": "human",
        "gender": "male",
        "face": "library-human-01",
        "hair": "original",
        "form": "regular",
        "outfit": "library-human-01",
        "arms": "library-human-01",
        "legs": "library-human-01",
        "back": None,
        "eye_size": 1.0,
        "eye_shape": "original",
        "colors": {key: None for key in registry.default_colors},
        "decor": {
            key: "none"
            for key in ("emblem", "shoulders", "belt", "headwear", "pattern", "beard", "mustache")
        },
        "features": feature_defaults(),
        "reference_parts": atlas_defaults(),
    }


def validate_settings(payload: dict, *, registry: ConstructorRegistry | None = None) -> dict:
    registry = registry or default_registry()
    if (
        isinstance(payload, dict)
        and isinstance(payload.get("race"), str)
        and (payload["race"] in registry.rpg_races)
    ):
        from ..constructor_marsh_forest import validate

        return validate(payload)
    if (
        not isinstance(payload, dict)
        or type(payload.get("schema_version")) is not int
        or payload.get("schema_version") not in {1, 2, 3, 4, registry.settings_version}
    ):
        raise ValueError(
            "Поддерживается schema_version=1–5 с явной миграцией; несовместимые версии не игнорируются"
        )
    payload = copy.deepcopy(payload)
    if payload["schema_version"] == 1:
        if (
            set(payload)
            != set(default_settings(registry=registry)) - {"decor", "features", "reference_parts"}
            or not isinstance(payload.get("colors"), dict)
            or set(payload["colors"]) != {"hair", "eyes", "skin", "cloth", "accent"}
        ):
            raise ValueError("Неполная или несовместимая schema_version=1")
        payload["schema_version"] = 2
        payload["decor"] = {
            key: "none" for key in ("emblem", "shoulders", "belt", "headwear", "pattern")
        }
        payload["colors"].update(metal=None, leather=None, secondary=None)
    if payload["schema_version"] == 2:
        if (
            set(payload)
            != set(default_settings(registry=registry)) - {"features", "reference_parts"}
            or not isinstance(payload.get("decor"), dict)
            or set(payload.get("decor")) != {"emblem", "shoulders", "belt", "headwear", "pattern"}
            or (not isinstance(payload.get("colors"), dict))
            or (set(payload["colors"]) != set(registry.default_colors) - set(registry.back_colors))
        ):
            raise ValueError("Неполная или несовместимая schema_version=2")
        payload["schema_version"] = 3
        payload["decor"].update(beard="original", mustache="original")
        payload["features"] = feature_defaults(original=True)
    if payload["schema_version"] == 3:
        if not isinstance(payload.get("colors"), dict) or set(payload["colors"]) != set(
            registry.default_colors
        ) - set(registry.back_colors):
            raise ValueError("Неполная или несовместимая schema_version=3")
        payload["colors"].update({key: None for key in registry.back_colors})
        payload["schema_version"] = 4
    if payload["schema_version"] == 4:
        from ..constructor_atlas import defaults as atlas_defaults

        if "reference_parts" in payload:
            raise ValueError("reference_parts requires schema_version=5")
        payload["reference_parts"] = atlas_defaults()
        payload["schema_version"] = 5
    allowed = set(default_settings(registry=registry))
    if set(payload) != allowed:
        raise ValueError("Неполный набор настроек или неизвестные поля")
    s = copy.deepcopy(payload)
    for field, options in [
        ("race", registry.races),
        ("gender", ("male", "female")),
        ("hair", registry.hair),
        ("form", registry.forms),
        ("eye_shape", registry.eyes),
        ("outfit", registry.outfits),
        ("arms", registry.outfits),
        ("legs", registry.outfits),
    ]:
        if not isinstance(s[field], str) or s[field] not in options:
            raise ValueError(f"Недопустимое значение {field}")
    if s["form"] in registry.horse_forms and s["race"] != "beast-horse":
        raise ValueError("Этот силуэт предназначен для лошади")
    if s["form"] == "ghost_spirit" and s["race"] != "ghost":
        raise ValueError("Этот силуэт предназначен для призраков")
    if s["race"] != "beast-horse" and s["hair"] in registry.horse_manes:
        raise ValueError("Эта грива предназначена для лошади")
    if s["race"] in registry.species and s["form"] in registry.physiques:
        raise ValueError("Эти телосложения предназначены для humanoid_v1")
    race = registry.races[s["race"]]
    from ..constructor_atlas import available as atlas_available
    from ..constructor_atlas import defaults as atlas_defaults

    if not isinstance(s["reference_parts"], dict) or set(s["reference_parts"]) != set(
        atlas_defaults()
    ):
        raise ValueError("Неполный набор вариантов по референсам")
    for category, number in s["reference_parts"].items():
        if type(number) is not int or number not in {
            0,
            *atlas_available(category, s["race"], s["gender"]),
        }:
            raise ValueError("Этот вариант референса не подходит выбранной расе и полу")
    allowed_faces = {*race[1], *([race[2]] if race[2] else [])}
    if not isinstance(s["face"], str) or s["face"] not in allowed_faces:
        raise ValueError("Лицо не принадлежит выбранной расе")
    if s["race"] == "skeleton" and s["gender"] != "male":
        raise ValueError("У исходных скелетов нет достоверных половых вариантов")
    if (
        s["race"] == "beorn"
        and s["face"].startswith(("expansion-ape-", "expansion-owl-"))
        and isinstance(s["features"], dict)
        and (s["features"].get("mouth") not in {"profile", "original"})
    ):
        raise ValueError("Выражение выбранного расового лица задаётся выбранной анатомией головы")
    if s["race"] in registry.owned_races:
        owned_ids = {d["id"] for d in registry.owned_designs if d["race"] == s["race"]}
        if any(s[key] not in owned_ids for key in ("outfit", "arms", "legs")):
            raise ValueError(
                "Эта раса использует собственное тело; человеческие комплекты несовместимы"
            )
        if s["form"] not in ({"regular", "ghost_spirit"} if s["race"] == "ghost" else {"regular"}):
            raise ValueError("Телосложение этой расы выбирается собственными деталями тела")
        if not isinstance(s["features"], dict) or any(
            (
                v
                not in (
                    {"profile", "original", "small", "stern", "teeth", "fangs"}
                    if k == "mouth" and s["race"] in {"beorn", "panda"}
                    else {"profile", "original"}
                )
                for k, v in s["features"].items()
            )
        ):
            raise ValueError("Черты лица этой расы задаются её анатомией головы")
        if s["eye_shape"] != "original" or s["eye_size"] != 1:
            raise ValueError("Глаза этой расы задаются её анатомией головы")
        if (
            not isinstance(s["decor"], dict)
            or not {"beard", "mustache", "pattern"} <= set(s["decor"])
            or any(s["decor"][k] != "none" for k in ("beard", "mustache", "pattern"))
        ):
            raise ValueError("Эти дополнения не поддерживают расовую анатомию")
        if registry.owned_races[s["race"]]["neutral"] and s["gender"] != "male":
            raise ValueError("Пол этой расы не выражен")
        if s["hair"] not in {"original", "bald", *owned_ids}:
            raise ValueError("Внешность головы задаётся расовой анатомией")
    if s["race"] in registry.species:
        allowed_parts = {d["id"] for d in registry.species_designs if d["race"] == s["race"]}
        if any(s[key] not in allowed_parts for key in ("outfit", "arms", "legs")):
            raise ValueError("Части нового типа должны принадлежать выбранной расе")
        if (
            s["race"] in {*registry.animal_species, *registry.flyer_species}
            and s["face"] not in allowed_parts
        ):
            raise ValueError("Голова животного должна принадлежать его виду")
        if s["race"] in {*registry.animal_species, *registry.flyer_species} and s["form"] not in (
            {"regular", *registry.horse_forms} if s["race"] == "beast-horse" else {"regular"}
        ):
            raise ValueError("Телосложение животного задаётся выбранной анатомией")
        if s["race"] in {*registry.animal_species, *registry.flyer_species} and (
            s["eye_shape"] != "original" or s["eye_size"] != 1
        ):
            raise ValueError("Глаза животного задаются выбранной анатомией")
        allowed_hair = {"original", "bald", *allowed_parts}
        if s["race"] == "beast-horse":
            allowed_hair.update(registry.horse_manes)
        if s["hair"] not in allowed_hair:
            raise ValueError("Этот тип использует собственные гривы или гребни")
        if s["gender"] != "male" and s["race"] not in {"naga", "centaur"}:
            raise ValueError("Пол этого авторского типа не выражен")
    if s["back"] is not None:
        if (
            not isinstance(s["back"], str)
            or s["back"] not in {*registry.outfits, *registry.back_ids}
            or (
                s["back"] not in registry.back_ids
                and (
                    not (
                        {"back_attachment", "left_wing", "tail"}
                        if s["race"] in {*registry.animal_species, "scorpion"}
                        else {"back_attachment", "left_wing"}
                    )
                    & set(
                        json.loads((registry.source_folder(s["back"]) / "parts.json").read_text())[
                            "parts"
                        ]
                    )
                )
            )
        ):
            raise ValueError("Неизвестная спина / крылья")
        contract = (
            registry.species[s["race"]][1] if s["race"] in registry.species else "humanoid_v1"
        )
        back_contract = (
            next(x["contract"] for x in registry.back_options() if x["id"] == s["back"])
            if s["back"] in registry.back_ids
            else json.loads((registry.source_folder(s["back"]) / "parts.json").read_text())[
                "rig_reference"
            ]
        )
        if s["race"] in registry.flyer_species and s["back"] not in {
            d["id"] for d in registry.flyer_designs if d["race"] == s["race"]
        }:
            raise ValueError("Крылья должны принадлежать выбранной летающей расе")
        if back_contract != contract and (
            not (
                s["race"] in registry.animal_species
                and s["back"] in registry.back_ids
                and (back_contract == "humanoid_v1")
            )
        ):
            raise ValueError("Спина несовместима с контрактом выбранного существа")
    if (
        isinstance(s["eye_size"], bool)
        or not isinstance(s["eye_size"], (int, float))
        or (not math.isfinite(s["eye_size"]))
        or (not 0.85 <= s["eye_size"] <= 1.15)
    ):
        raise ValueError("Размер глаз должен быть от 0.85 до 1.15")
    if not isinstance(s["colors"], dict) or set(s["colors"]) != set(registry.default_colors):
        raise ValueError("Нужны цвета волос, глаз, кожи, костюма и отделки")
    for value in s["colors"].values():
        if value is not None and (
            not isinstance(value, str) or re.fullmatch("#[0-9a-fA-F]{6}", value) is None
        ):
            raise ValueError("Цвет должен быть #RRGGBB или null для исходного цвета")
    from ..constructor_decor import OPTIONS
    from ..constructor_mounts import options as mount_options

    decor_options = {**OPTIONS, **mount_options(s["race"])}
    if s["race"] == "randomium":
        if (
            any(value is not None for value in s["colors"].values())
            or s["reference_parts"]["colorways"]
        ):
            raise ValueError("Рандомиумы используют исходную расцветку; менять цвета нельзя")
        decor_options["emblem"] = registry.randomium_emblems
        if s["back"] is not None or any(s["decor"].get(k) != "none" for k in ("belt", "headwear")):
            raise ValueError("Рандомиумам недоступны пояс, головной убор, спина и крылья")
    if not isinstance(s["decor"], dict) or set(s["decor"]) != set(OPTIONS):
        raise ValueError("Неполный набор украшений")
    for key, value in s["decor"].items():
        if not isinstance(value, str) or value not in decor_options[key]:
            raise ValueError("Неизвестное украшение " + key)
    if not isinstance(s["features"], dict) or set(s["features"]) != set(registry.features):
        raise ValueError("Неполный набор черт лица")
    for key, value in s["features"].items():
        if not isinstance(value, str) or value not in {*registry.features[key], "original"}:
            raise ValueError("Неизвестная черта лица " + key)
    if s["hair"] in registry.procedural_hair and registry.procedural_hair[s["hair"]][0] != (
        "human" if s["race"] == "centaur" else s["race"]
    ):
        raise ValueError("Причёска не принадлежит расе")
    if s["race"] in registry.species and s["race"] != "centaur":
        if any(
            (
                v != "none"
                for k, v in s["decor"].items()
                if k not in mount_options(s["race"]) and k != "pattern"
            )
        ):
            raise ValueError("Humanoid-украшения несовместимы с этим типом")
        if any(v not in {"original", "profile"} for v in s["features"].values()):
            raise ValueError("Человеческие черты несовместимы с этим типом")
        if s["back"] is not None and s["back"] not in {*allowed_parts, *registry.back_ids}:
            raise ValueError("Крылья должны принадлежать выбранной расе")
    return s
