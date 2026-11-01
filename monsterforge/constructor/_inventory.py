"""Bundled authoring inventory, including preserved historical contracts.

This module only loads source metadata. New integrations use ConstructorRegistry;
legacy species definitions remain here so immutable publications stay readable.
"""

import json

from tools.creature_workshop.constructor_species import CONFIG as SPECIES_CONFIG
from tools.creature_workshop.constructor_species import CONTRACTS as SPECIES_CONTRACTS
from tools.creature_workshop.constructor_species import OUTPUT as SPECIES_SOURCE
from tools.creature_workshop.constructor_species import SPECIES

from ..constructor_animals import DESIGNS as ANIMAL_DESIGNS
from ..constructor_animals import IDS as ANIMAL_IDS
from ..constructor_animals import SOURCE as ANIMAL_SOURCE
from ..constructor_animals import SPECIES as ANIMAL_SPECIES
from ..constructor_animals import options as animal_options
from ..constructor_back import COLORS as BACK_COLORS
from ..constructor_back import IDS as BACK_IDS
from ..constructor_back import options as back_options
from ..constructor_bear_mouths import LABELS as BEAR_MOUTH_LABELS
from ..constructor_costumes import COSTUMES
from ..constructor_expansion import CONTRACTS as EXP_CONTRACTS
from ..constructor_expansion import DESIGNS as EXP_DESIGNS
from ..constructor_expansion import FLYERS as EXP_FLYERS
from ..constructor_expansion import IDS as EXP_IDS
from ..constructor_expansion import SPECIES as EXP_SPECIES
from ..constructor_expansion import source_folder as expansion_folder
from ..constructor_flyers import CONTRACTS as FLYER_CONTRACTS
from ..constructor_flyers import DESIGNS as FLYER_DESIGNS
from ..constructor_flyers import IDS as FLYER_IDS
from ..constructor_flyers import SOURCE as FLYER_SOURCE
from ..constructor_flyers import SPECIES as FLYER_SPECIES
from ..constructor_ghosts import FORMS as GHOST_FORMS
from ..constructor_goblins import BOOTS as GOBLIN_BOOTS
from ..constructor_goblins import COSTUMES as GOBLIN_COSTUMES
from ..constructor_goblins import GLOVES as GOBLIN_GLOVES
from ..constructor_horses import FORMS as HORSE_FORMS
from ..constructor_horses import MANES as HORSE_MANES
from ..constructor_marsh_forest import DESIGNS as RPG_DESIGNS
from ..constructor_marsh_forest import IDS as RPG_IDS
from ..constructor_marsh_forest import RACES as RPG_RACES
from ..constructor_marsh_forest import SOURCE as RPG_SOURCE
from ..constructor_naga_costumes import LABELS as NAGA_COSTUME_LABELS
from ..constructor_owned_races import DESIGNS as OWNED_DESIGNS
from ..constructor_owned_races import IDS as OWNED_IDS
from ..constructor_owned_races import RACES as OWNED_RACES
from ..constructor_owned_races import SOURCE as OWNED_SOURCE
from ..constructor_owned_races import options as owned_options
from ..constructor_physiques import PROFILES as PHYSIQUES
from ..constructor_portraits import FEATURES, NEW_HAIR
from ..constructor_racial_anatomy import VARIANTS as RACIAL_ANATOMIES
from ..constructor_racial_anatomy import choices as racial_choices
from ..constructor_randomiums import EMBLEMS as RANDOMIUM_EMBLEMS
from ..constructor_randomiums import HIDDEN_PARTS as RANDOMIUM_HIDDEN_PARTS
from ..constructor_randomiums import IDS as RANDOMIUM_IDS
from ..constructor_randomiums import SOURCE as RANDOMIUM_SOURCE
from ..paths import ROOT

SLOTS = ("head", "torso", "left_arm", "right_arm", "left_leg", "right_leg")

VERSION = 1

SETTINGS_VERSION = 5

ACTIVE_RACES = (
    "human",
    "skeleton",
    "minotaur",
    "orc",
    "goblin",
    "ghost",
    "golem",
    "panda",
    "beorn",
    "kobold",
    "quillboar",
    "spider",
    "beast-sheep",
    "beast-wolf",
    "beast-bear",
    "beast-boar",
    "beast-dog",
    "beast-tiger",
    "beast-horse",
    "sky-dragon",
    "sky-bone-dragon",
    "sky-eagle",
    "naga",
    "centaur",
    "beast-elephant",
    "crab",
    "beetle",
    "scorpion",
    "tree",
)

RACES = {
    "human": ("Люди", [], None),
    "goblin": ("Гоблины", [], None),
    "orc": ("Орки", [], None),
    "minotaur": ("Минотавры", [], None),
    "skeleton": ("Скелеты", [], None),
}

OUTFITS = {}

HAIR = {"original": "Причёска комплекта", "bald": "Без волос"}

HAIR_DONORS = {}

FORMS = {"regular": "Обычное", "slender": "Стройное", "stocky": "Крепкое"}

EYES = {"original": "Исходная форма", "round": "Округлые", "narrow": "Узкие"}

DEFAULT_COLORS = {
    "hair": "#725139",
    "eyes": "#54808e",
    "skin": "#c7a27e",
    "cloth": "#536b85",
    "accent": "#c7ab73",
    "metal": "#919ba1",
    "leather": "#624c3d",
    "secondary": "#976356",
}

DEFAULT_COLORS.update(BACK_COLORS)

FEMALE_HEADS = set()

ORIGINAL_DESIGNS = []

ORIGINAL_IDS = set()

HAIR_LABELS = {
    "swept": "Зачёс набок",
    "bob": "Асимметричное каре",
    "knot": "Узел и короткая борода",
    "twin-braids": "Две косы",
    "mane": "Бычья грива",
    "forelock": "Короткий чуб",
    "braided-bun": "Плетёный пучок",
    "cap": "Шапочка архивариуса",
    "slick": "Гладкий зачёс",
    "wrapped-braid": "Коса с повязкой",
}

LIBRARY_SOURCE = ROOT / "media/constructor/library/v1"

LIBRARY_DESIGNS = [
    d
    for d in json.loads((ROOT / "config/constructor_library_v1.json").read_text())["designs"]
    if d["race"] in RACES
]

LIBRARY_IDS = {d["id"] for d in LIBRARY_DESIGNS}

PROCEDURAL_HAIR = {f"hair-{race}-{style}": (race, style) for race in RACES for style in NEW_HAIR}

HAIR.update({key: NEW_HAIR[style] for key, (_, style) in PROCEDURAL_HAIR.items()})

ORIGINAL_IDS |= LIBRARY_IDS

FORMS.update(
    lean="Поджарое",
    athletic="Атлетическое",
    broad="Широкоплечее",
    heavy="Массивное",
    petite="Миниатюрное",
    wiry="Жилистое",
    powerful="Мощное",
)

FORM_WIDTHS = {
    "regular": 1,
    "slender": 0.94,
    "stocky": 1.06,
    "lean": 0.9,
    "athletic": 1.03,
    "broad": 1.1,
    "heavy": 1.14,
    "petite": 0.86,
    "wiry": 0.97,
    "powerful": 1.18,
}

FORMS.update({key: p["label"] for key, p in PHYSIQUES.items()})

FORM_WIDTHS.update({key: 1.0 for key in PHYSIQUES})

FORMS["ghost_spirit"] = GHOST_FORMS["ghost_spirit"]

FORM_WIDTHS["ghost_spirit"] = 1.0

EYES.update(
    almond="Миндалевидные",
    wide="Широкие",
    deep="Глубокие",
    small="Маленькие",
    large="Крупные",
    slanted="Раскосые",
    soft="Мягкий овал",
)

EYE_PROPORTIONS = {
    "original": (1, 1),
    "round": (1, 1.12),
    "narrow": (1.06, 0.84),
    "almond": (1.1, 0.94),
    "wide": (1.14, 1.02),
    "deep": (0.94, 0.9),
    "small": (0.86, 0.86),
    "large": (1.13, 1.13),
    "slanted": (1.07, 0.9),
    "soft": (0.96, 1.07),
}

HAIR_LABELS["cropped"] = "Короткая стрижка"

OUTFITS = {**{d["id"]: d["label"] for d in LIBRARY_DESIGNS}, **OUTFITS}

for _race_key, (_label, _faces, _female) in list(RACES.items()):
    _specs = [d for d in LIBRARY_DESIGNS if d["race"] == _race_key]
    RACES[_race_key] = (
        _label,
        [*[d["id"] for d in _specs], *_faces],
        next((d["id"] for d in _specs if d["gender"] == "female"), _female),
    )

for _d in LIBRARY_DESIGNS:
    HAIR[_d["id"]] = HAIR_LABELS[_d["hair"]]
    HAIR_DONORS[_d["id"]] = _d["id"]
    if _d["gender"] == "female":
        FEMALE_HEADS.add(_d["id"])

FLYER_DESIGNS = [*FLYER_DESIGNS, *EXP_FLYERS]

ANIMAL_SPECIES = {**ANIMAL_SPECIES, "beast-elephant": EXP_SPECIES["beast-elephant"]}

HAIR.update(HORSE_MANES)

FORMS.update(HORSE_FORMS)

FORM_WIDTHS.update({k: 1.0 for k in HORSE_FORMS})

SPECIES = {**SPECIES, **ANIMAL_SPECIES, **FLYER_SPECIES, **EXP_SPECIES}

SPECIES_CONTRACTS = {**SPECIES_CONTRACTS, **FLYER_CONTRACTS, **EXP_CONTRACTS}

_LEGACY_SPECIES_DESIGNS = [
    d for d in json.loads(SPECIES_CONFIG.read_text())["designs"] if d["race"] == "spider"
]

SPECIES_DESIGNS = (
    [
        d
        for d in _LEGACY_SPECIES_DESIGNS
        if d["race"] not in {*ANIMAL_SPECIES, *FLYER_SPECIES, *EXP_SPECIES}
    ]
    + ANIMAL_DESIGNS
    + FLYER_DESIGNS
    + EXP_DESIGNS
)

SPECIES_IDS = {
    d["id"] for d in [*_LEGACY_SPECIES_DESIGNS, *ANIMAL_DESIGNS, *FLYER_DESIGNS, *EXP_DESIGNS]
}

LIBRARY_DESIGNS = [*LIBRARY_DESIGNS, *SPECIES_DESIGNS]

LIBRARY_IDS |= SPECIES_IDS

ORIGINAL_IDS |= SPECIES_IDS

OUTFITS.update({d["id"]: d["label"] for d in SPECIES_DESIGNS})

OUTFITS.update(
    {d["id"]: NAGA_COSTUME_LABELS[d["variant"] % 5] for d in EXP_DESIGNS if d["race"] == "naga"}
)

for _race, (_label, _contract, _kind) in SPECIES.items():
    _ids = [d["id"] for d in SPECIES_DESIGNS if d["race"] == _race]
    RACES[_race] = (_label, _ids, None)
    for i, _id in enumerate(_ids):
        HAIR[_id] = (
            (
                "Гребень"
                if _race.startswith("sky-")
                else "Грива"
                if _race.startswith("beast-")
                else "Головной панцирь"
            )
            + " "
            + str(i + 1).zfill(2)
        )
        HAIR_DONORS[_id] = _id

REFERENCE_SOURCE = ROOT / "media/constructor/reference_kits/v2"

REFERENCE_DESIGNS = [
    d
    for d in json.loads((ROOT / "config/constructor_reference_kits_v1.json").read_text())["designs"]
    if d["race"] in RACES and d.get("public", True)
]

REFERENCE_IDS = {d["id"] for d in REFERENCE_DESIGNS}

ORIGINAL_IDS |= REFERENCE_IDS

OUTFITS.update({d["id"]: d["label"] for d in REFERENCE_DESIGNS})

for d in REFERENCE_DESIGNS:
    label, faces, female = RACES[d["race"]]
    RACES[d["race"]] = (label, [*faces, d["id"]], female)
    HAIR[d["id"]] = "По референсу · " + d["label"]
    HAIR_DONORS[d["id"]] = d["id"]
    if d["gender"] == "female":
        FEMALE_HEADS.add(d["id"])

LIBRARY_DESIGNS = [*LIBRARY_DESIGNS, *[d for d in OWNED_DESIGNS if d["id"] not in LIBRARY_IDS]]

LIBRARY_IDS |= OWNED_IDS

ORIGINAL_IDS |= OWNED_IDS

OUTFITS.update({d["id"]: d["label"] for d in OWNED_DESIGNS})

for _race, _spec in OWNED_RACES.items():
    _designs = [d for d in OWNED_DESIGNS if d["race"] == _race]
    RACES[_race] = (
        _spec["label"],
        [d["id"] for d in _designs],
        next((d["id"] for d in _designs if d["gender"] == "female"), None),
    )
    for _d in _designs:
        HAIR[_d["id"]] = "Расовая анатомия головы"
        HAIR_DONORS[_d["id"]] = _d["id"]
        if _d["gender"] == "female":
            FEMALE_HEADS.add(_d["id"])

for _key, _spec in RACIAL_ANATOMIES.items():
    _label, _faces, _female = RACES[_spec["race"]]
    RACES[_spec["race"]] = (
        _label,
        [_key, *_faces],
        _key if _spec["gender"] == "female" else _female,
    )
    if _spec["gender"] == "female":
        FEMALE_HEADS.add(_key)

OUTFITS.update(COSTUMES)

OUTFITS.update(GOBLIN_COSTUMES)

ACTIVE_RACES = (*ACTIVE_RACES, "randomium", *RPG_RACES)

OWNED_RACES.update(RPG_RACES)

OWNED_DESIGNS.extend(RPG_DESIGNS)

OWNED_IDS.update(RPG_IDS)

LIBRARY_DESIGNS.extend(RPG_DESIGNS)

LIBRARY_IDS.update(RPG_IDS)

ORIGINAL_IDS.update(RPG_IDS)

for _race, _spec in RPG_RACES.items():
    _designs = [d for d in RPG_DESIGNS if d["race"] == _race]
    RACES[_race] = (_spec["label"], [d["id"] for d in _designs], None)
    for _design in _designs:
        OUTFITS[_design["id"]] = _design["label"]
        HAIR[_design["id"]] = "Расовая анатомия головы"
        HAIR_DONORS[_design["id"]] = _design["id"]

__all__ = [
    "ACTIVE_RACES",
    "ANIMAL_DESIGNS",
    "ANIMAL_IDS",
    "ANIMAL_SOURCE",
    "ANIMAL_SPECIES",
    "BACK_COLORS",
    "BACK_IDS",
    "BEAR_MOUTH_LABELS",
    "COSTUMES",
    "DEFAULT_COLORS",
    "EXP_DESIGNS",
    "EXP_IDS",
    "EXP_SPECIES",
    "EYES",
    "EYE_PROPORTIONS",
    "FEATURES",
    "FEMALE_HEADS",
    "FLYER_DESIGNS",
    "FLYER_IDS",
    "FLYER_SOURCE",
    "FLYER_SPECIES",
    "FORMS",
    "FORM_WIDTHS",
    "GHOST_FORMS",
    "GOBLIN_BOOTS",
    "GOBLIN_COSTUMES",
    "GOBLIN_GLOVES",
    "HAIR",
    "HAIR_DONORS",
    "HORSE_FORMS",
    "HORSE_MANES",
    "LIBRARY_DESIGNS",
    "LIBRARY_IDS",
    "LIBRARY_SOURCE",
    "ORIGINAL_DESIGNS",
    "ORIGINAL_IDS",
    "OUTFITS",
    "OWNED_DESIGNS",
    "OWNED_IDS",
    "OWNED_RACES",
    "OWNED_SOURCE",
    "PHYSIQUES",
    "PROCEDURAL_HAIR",
    "RACES",
    "RACIAL_ANATOMIES",
    "RANDOMIUM_EMBLEMS",
    "RANDOMIUM_HIDDEN_PARTS",
    "RANDOMIUM_IDS",
    "RANDOMIUM_SOURCE",
    "REFERENCE_DESIGNS",
    "REFERENCE_IDS",
    "REFERENCE_SOURCE",
    "RPG_DESIGNS",
    "RPG_IDS",
    "RPG_RACES",
    "RPG_SOURCE",
    "SETTINGS_VERSION",
    "SLOTS",
    "SPECIES",
    "SPECIES_DESIGNS",
    "SPECIES_IDS",
    "SPECIES_SOURCE",
    "VERSION",
    "_LEGACY_SPECIES_DESIGNS",
    "animal_options",
    "back_options",
    "expansion_folder",
    "owned_options",
    "racial_choices",
]
