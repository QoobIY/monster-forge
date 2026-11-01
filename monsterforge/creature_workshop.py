"""Current modular character constructor and its asset routes."""

from io import BytesIO
from pathlib import Path

from flask import Blueprint, abort, current_app, jsonify, render_template, request, send_file

from .paths import ROOT

blueprint = Blueprint("creature_workshop", __name__, url_prefix="/creature-workshop")
STATIC = ROOT / "static/characters"


def constructor_service():
    """Use an app-owned extension service, retaining the historical default API."""
    service = current_app.extensions.get("constructor_service")
    if service is None:
        service = current_app.config.get("CONSTRUCTOR_SERVICE")
    if service is not None:
        return service
    from . import workshop_constructor

    return workshop_constructor


def _source_card(category: str, identifier: str):
    service = constructor_service()
    registry = getattr(service, "registry", None)
    if registry is None or identifier not in registry.source_bundles:
        return None
    if request.args.get("gender", "male") not in {"male", "female"}:
        abort(404)
    if category not in {"face", "head", "hair", "outfit", "arms", "legs", "back"}:
        abort(404)
    try:
        response = send_file(
            service.source_card(category, identifier), mimetype="image/png", conditional=True
        )
    except (ValueError, FileNotFoundError) as error:
        return jsonify(error=str(error)), 409
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def _read_file(root: Path, filename: str):
    root = root.resolve()
    path = (root / filename).resolve()
    if not path.is_relative_to(root):
        abort(404)
    from .constructor_cache import resolve

    path = resolve(path)
    if not path.is_file():
        abort(404)
    media = {".glb": "model/gltf-binary", ".jsonl": "application/x-ndjson"}.get(path.suffix)
    response = send_file(path, mimetype=media, conditional=True)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@blueprint.get("/static/<path:filename>")
def static_file(filename: str):
    if filename == "font.ttf":
        return _read_file(ROOT / "media/ui/fonts", "NotoSans-Regular.ttf")
    return _read_file(STATIC, filename)


@blueprint.get("/health")
def health():
    return jsonify(status="ok", read_only=True)


@blueprint.get("/constructor/")
def constructor():
    return render_template("characters.html", active="characters")


@blueprint.get("/constructor/catalog")
def constructor_catalog():
    return jsonify(constructor_service().catalog())


@blueprint.get("/constructor/part-descriptions")
def constructor_part_descriptions():
    from .constructor_part_descriptions import catalogue

    data = catalogue()
    return jsonify({**data, "parts": [p for p in data["parts"] if p["category"] != "back"]})


def _constructor_action(action):
    if request.content_length is not None and request.content_length > 16384:
        return jsonify(error="Настройки персонажа превышают допустимый размер"), 413
    if len(request.get_data(cache=True)) > 16384:
        return jsonify(error="Настройки персонажа превышают допустимый размер"), 413
    if not request.is_json:
        return jsonify(error="Настройки персонажа нужно передать в формате JSON"), 415
    try:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            raise ValueError("Настройки персонажа должны быть JSON-объектом")
        from .constructor import default_registry

        service = constructor_service()
        registry = getattr(service, "registry", None) or default_registry()
        race = payload.get("race")
        if not isinstance(race, str) or race not in registry.active_races:
            raise ValueError("Выберите расу из существующего активного каталога персонажей")
        if action == "preview":
            return jsonify(service.preview(payload))
        if action == "save":
            return jsonify(service.save(payload))
        return send_file(
            BytesIO(service.export_bundle(payload)),
            mimetype="application/zip",
            as_attachment=True,
            download_name="flying-character.zip"
            if race.startswith("sky-")
            else "humanoid-character.zip",
        )
    except ValueError as error:
        return jsonify(error=str(error)), 400


@blueprint.post("/constructor/preview")
def constructor_preview():
    return _constructor_action("preview")


@blueprint.get("/constructor/palette-cards/<identifier>.png")
def constructor_static_palette_card(identifier):
    from .constructor_palette_previews import options

    if identifier not in {"current", *(p["id"] for p in options())}:
        abort(404)
    response = _read_file(ROOT / "media/constructor/static_palettes/v1", identifier + ".png")
    response.headers["Cache-Control"] = "private, max-age=86400"
    return response


@blueprint.post("/constructor/save")
def constructor_save():
    return _constructor_action("save")


@blueprint.get("/constructor/ghost-cards/form/<identifier>.png")
def constructor_ghost_form_card(identifier):
    from .constructor_ghosts import FORM_CARDS, FORMS

    if identifier not in FORMS:
        abort(404)
    return _read_file(FORM_CARDS, identifier + ".png")


@blueprint.post("/constructor/export")
def constructor_export():
    return _constructor_action("export")


@blueprint.get("/constructor/revisions/<identifier>/download")
def constructor_download(identifier: str):
    try:
        return send_file(
            BytesIO(constructor_service().saved_bundle(identifier)),
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"humanoid-{identifier[:12]}.zip",
        )
    except FileNotFoundError:
        abort(404)
    except ValueError as error:
        return jsonify(error=str(error)), 400


@blueprint.get("/constructor/revisions")
def constructor_revisions():
    from .asset_library import store
    from .constructor_published import list_published

    return jsonify(
        schema_version=1, revisions=constructor_service().list_saved(), published=list_published(store=store())
    )


@blueprint.get("/constructor/published/<identifier>/<action>")
def constructor_published(identifier, action):
    from .asset_library import store
    from .constructor_published import model_blob, preview_blob, published_model

    try:
        if action == "preview":
            response = send_file(BytesIO(preview_blob(identifier, store=store())), mimetype="image/png")
        elif action == "model":
            response = jsonify(published_model(identifier, store=store()))
        elif action == "download":
            response = send_file(
                BytesIO(model_blob(identifier, store=store())),
                mimetype="model/gltf-binary",
                as_attachment=True,
                download_name=f"character-{identifier[:12]}.glb",
            )
        else:
            abort(404)
        response.headers["Cache-Control"] = "no-cache"
        return response
    except FileNotFoundError:
        abort(404)
    except (ValueError, KeyError) as error:
        return jsonify(error=str(error)), 400


@blueprint.get("/constructor/revisions/<identifier>/preview")
def constructor_revision_preview(identifier: str):
    service = constructor_service()
    try:
        manifest = service.saved_manifest(identifier)
        if manifest["schema_version"] == 2:
            from .character_assembly import preview_image

            blob = service.saved_model(identifier)
            return send_file(BytesIO(preview_image(blob)), mimetype="image/png")
    except (FileNotFoundError, ValueError):
        abort(404)
    return _read_file(service.saved_directory(identifier), "preview.png")


@blueprint.get("/constructor/mount-cards/<race>/<category>/<identifier>.png")
def constructor_mount_card(race, category, identifier):
    from .constructor_mounts import options

    if identifier != "none" and identifier in options(race).get(category, {}):
        if race in {"sky-dragon", "beast-elephant", "beetle"}:
            return _read_file(
                ROOT / "media/constructor/species_extra/options/v1/mount" / race / category,
                identifier + ".png",
            )
        return _read_file(
            ROOT / "media/constructor/mount_cards/v10" / race / category, identifier + ".png"
        )
    abort(404)


@blueprint.get("/constructor/horse-cards/<category>/<identifier>.png")
def constructor_horse_card(category, identifier):
    from .constructor_horses import FORMS, MANES

    if (
        category == "mane"
        and identifier in MANES
        or category == "form"
        and identifier in {"regular", *FORMS}
    ):
        return _read_file(ROOT / "media/constructor/horse_cards/v6" / category, identifier + ".png")
    abort(404)


@blueprint.get("/constructor/cards/<category>/<identifier>.png")
def constructor_card(category: str, identifier: str):
    card = _source_card(category, identifier)
    if card is not None:
        return card
    from .constructor_decor import OPTIONS
    from .workshop_constructor import LIBRARY_IDS, ROOT

    allowed = (
        identifier in LIBRARY_IDS
        if category in {"face", "hair", "outfit", "arms", "legs", "back"}
        else category in OPTIONS and identifier in OPTIONS[category]
    )
    if not allowed:
        abort(404)
    if (
        category in {"shoulders", "belt"}
        and not identifier.startswith("wild_")
        and identifier != "none"
    ):
        return constructor_versioned_card(28, category, identifier)
    response = _read_file(ROOT / "media/constructor/cards/v28" / category, identifier + ".png")
    response.headers["Cache-Control"] = "private, max-age=3600"
    return response


@blueprint.get("/constructor/cards/v<int:version>/<category>/<identifier>.png")
def constructor_versioned_card(version: int, category: str, identifier: str):
    card = _source_card(category, identifier)
    if card is not None:
        return card
    from .constructor_randomiums import EMBLEMS as RANDOMIUM_EMBLEMS
    from .constructor_randomiums import IDS as RANDOMIUM_IDS
    from .constructor_randomiums import SOURCE as RANDOMIUM_SOURCE

    if (
        category == "emblem"
        and identifier in RANDOMIUM_EMBLEMS
        and identifier.startswith("randomium-")
    ):
        return _read_file(RANDOMIUM_SOURCE / "emblems", identifier + ".png")
    if identifier in RANDOMIUM_IDS and category in {"face", "hair", "outfit", "arms", "legs"}:
        return _read_file(
            RANDOMIUM_SOURCE / identifier, ("face" if category == "hair" else category) + ".png"
        )
    from .constructor_expansion import IDS as EXP_IDS
    from .constructor_expansion import source_folder as expansion_folder
    from .constructor_faceless import LABELS as FACELESS
    from .constructor_sea_costumes import LABELS as SEA
    from .workshop_constructor import (
        BACK_IDS,
        COSTUMES,
        LIBRARY_IDS,
        PROCEDURAL_HAIR,
        RACES,
        REFERENCE_IDS,
    )

    gender = request.args.get("gender", "male")
    if gender not in {"male", "female"}:
        abort(404)
    if category == "hair":
        from .workshop_constructor import LIBRARY_DESIGNS, REFERENCE_DESIGNS

        human_hair = {
            d["id"] for d in [*LIBRARY_DESIGNS, *REFERENCE_DESIGNS] if d["race"] == "human"
        }
        human_hair.update(k for k, v in PROCEDURAL_HAIR.items() if v[0] == "human")
        if identifier in human_hair:
            return _read_file(
                ROOT / "media/constructor/hair_review/v1" / gender / "native", identifier + ".png"
            )
    from .constructor_marsh_forest import IDS as RPG_IDS
    from .constructor_marsh_forest import SOURCE as RPG_SOURCE

    if identifier in RPG_IDS and category in {"face", "hair", "outfit", "arms", "legs"}:
        if identifier.startswith("native-satyr-"):
            return _read_file(
                ROOT / "media/constructor/satyr/v2/cards" / identifier,
                ("face" if category == "hair" else category) + ".png",
            )
        return _read_file(
            RPG_SOURCE / identifier, ("face" if category == "hair" else category) + ".png"
        )
    from .constructor_expansion import DESIGNS as EXP_DESIGNS
    from .constructor_species_variety import RACES as VARIED_SPECIES

    varied = next(
        (
            d
            for d in EXP_DESIGNS
            if d["id"] == identifier and d["race"] in {*VARIED_SPECIES, "centaur"}
        ),
        None,
    )
    if varied and category in {"face", "hair", "outfit", "arms", "legs"}:
        card_gender = gender if varied["race"] == "centaur" else "male"
        return _read_file(
            ROOT / "media/constructor/species_anatomy/v1/cards" / identifier / card_gender,
            ("face" if category == "hair" else category) + ".png",
        )
    if (
        category == "headwear"
        and identifier in FACELESS
        or category in {"outfit", "arms", "legs"}
        and identifier in SEA
    ):
        return _read_file(
            ROOT
            / "media/constructor/species_extra/options/v1"
            / gender
            / ("headwear" if category == "headwear" else "outfit"),
            identifier + ".png",
        )
    if category in {"outfit", "arms", "legs"} and identifier in {
        d["id"] for d in EXP_DESIGNS if d["race"] == "naga"
    }:
        return _read_file(
            ROOT / "media/constructor/naga_costumes/v3" / identifier, category + ".png"
        )
    if category in {"outfit", "arms", "legs"} and identifier in {
        d["id"] for d in EXP_DESIGNS if d["race"] == "beetle"
    }:
        return _read_file(ROOT / "media/constructor/beetle_legs/v2" / identifier, category + ".png")
    if identifier in EXP_IDS and category in {"face", "hair", "outfit", "arms", "legs", "back"}:
        folder = expansion_folder(identifier)
        from .constructor_cache import artifact_index

        candidate = folder / (category + "-front.png")
        available = (
            candidate.is_file() or candidate.relative_to(ROOT).as_posix() in artifact_index()
        )
        filename = (
            "head-front.png"
            if category in {"face", "hair"}
            else category + "-front.png"
            if category in {"arms", "legs", "back"} and available
            else "front.png"
        )
        return _read_file(folder, filename)
    from .constructor_decor import OPTIONS
    from .constructor_owned_races import IDS as OWNED_IDS
    from .constructor_owned_races import SOURCE as OWNED_SOURCE
    from .constructor_portraits import FEATURES
    from .constructor_racial_anatomy import VARIANTS

    if (
        identifier in OWNED_IDS
        and identifier.startswith("native-ghost-")
        and category in {"face", "hair", "outfit", "arms", "legs", "back"}
    ):
        from .constructor_ghosts import BODY_CARDS as GHOST_BODY_CARDS

        return _read_file(GHOST_BODY_CARDS / identifier, "front.png")
    from .constructor_flyers import IDS as FLYER_IDS
    from .constructor_flyers import SOURCE as FLYER_SOURCE

    if identifier in FLYER_IDS and category in {"face", "hair", "outfit", "arms", "legs", "back"}:
        return _read_file(
            FLYER_SOURCE / identifier,
            "head-front.png" if category in {"face", "hair"} else "front.png",
        )
    from .constructor_animals import IDS as ANIMAL_IDS
    from .constructor_animals import SOURCE as ANIMAL_SOURCE
    from .constructor_bear_mouths import LABELS as BEAR_MOUTHS
    from .constructor_bear_mouths import RACES as BEAR_RACES
    from .constructor_goblins import BACKS as GOBLIN_BACKS
    from .constructor_goblins import COSTUMES as GOBLIN_COSTUMES
    from .constructor_goblins import HEADWEAR as GOBLIN_HEADWEAR
    from .constructor_goblins import SOURCE as GOBLIN_SOURCE

    if (
        (identifier in VARIANTS and VARIANTS[identifier]["race"] == "goblin" and category in {"face", "hair"})
        or (identifier in GOBLIN_COSTUMES and category in {"outfit", "arms", "legs"})
        or (identifier in GOBLIN_HEADWEAR and category == "headwear")
        or (identifier in GOBLIN_BACKS and category == "back")
    ):
        card_category = "face" if identifier in VARIANTS else category
        return _read_file(GOBLIN_SOURCE / card_category, identifier + ".png")
    if (
        identifier in OWNED_IDS
        and identifier.startswith(("native-beorn-", "native-panda-", "native-quillboar-"))
        and category in {"face", "hair", "outfit", "arms", "legs", "back"}
    ):
        return _read_file(ROOT / "media/constructor/owned_pelts/v1" / identifier, "front.png")
    if (
        identifier in ANIMAL_IDS
        and identifier.startswith("library-animal-boar-")
        and category in {"face", "hair", "outfit", "arms", "legs", "back"}
    ):
        return _read_file(ROOT / "media/constructor/boar_faces/v1" / identifier, "front.png")
    if category in {"face", "hair", "outfit", "arms", "legs", "back"} and (
        identifier.startswith(("library-animal-wolf-", "library-animal-bear-"))
        and identifier in ANIMAL_IDS
        or identifier in OWNED_IDS
        and identifier.startswith("native-golem-")
    ):
        return _read_file(ROOT / "media/constructor/reviewed_faces/v2" / identifier, "front.png")
    if (
        identifier in ANIMAL_IDS
        and identifier.startswith("library-animal-horse-")
        and category in {"face", "hair", "outfit", "arms", "legs", "back"}
    ):
        return _read_file(
            ROOT / "media/constructor/horse_cards/v6/animals" / identifier, "front.png"
        )
    if (
        identifier in ANIMAL_IDS
        and identifier.startswith("library-animal-wolf-")
        and category in {"face", "hair", "outfit", "arms", "legs", "back"}
    ):
        from .constructor_wolf_limbs import SOURCE as WOLF_SOURCE

        return _read_file(WOLF_SOURCE / identifier, "front.png")
    if identifier in ANIMAL_IDS and category in {"face", "hair", "outfit", "arms", "legs", "back"}:
        return _read_file(ANIMAL_SOURCE / identifier, "front.png")
    if category == "mouth" and "--" in identifier:
        race, mouth = identifier.split("--", 1)
        if race in BEAR_RACES and mouth in BEAR_MOUTHS:
            return _read_file(ROOT / "media/constructor/bear_mouths/v2/mouth", identifier + ".png")
    if (
        identifier in OWNED_IDS
        and identifier.split("-")[1] in BEAR_RACES
        and category in {"face", "hair"}
    ):
        return _read_file(ROOT / "media/constructor/bear_mouths/v2/face", identifier + ".png")
    if identifier in OWNED_IDS and category in {"face", "hair", "outfit", "arms", "legs", "back"}:
        return _read_file(
            OWNED_SOURCE / identifier, ("face" if category == "hair" else category) + ".png"
        )
    from .constructor_wild_clothes import IDS as WILD_IDS

    if identifier in WILD_IDS and category in {"shoulders", "belt"}:
        return _read_file(
            ROOT / "media/constructor/wild_clothes/v2" / category, identifier + ".png"
        )
    from .constructor_armor_details import BELTS, SHOULDERS
    from .constructor_armor_details import SOURCE as ARMOR_SOURCE

    if (
        category == "shoulders"
        and identifier in SHOULDERS
        or category == "belt"
        and identifier in {*BELTS, "medallion"}
    ):
        if identifier == "medallion":
            return _read_file(ARMOR_SOURCE, "medallion.png")
        variants = SHOULDERS if category == "shoulders" else BELTS
        return _read_file(
            ARMOR_SOURCE / "male" / ("shoulders" if category == "shoulders" else "belts"),
            f"{variants.index(identifier) + 1:02d}.png",
        )
    if category == "headwear" and identifier in {"cloth_hood", "deep_hood"}:
        return _read_file(ROOT / "media/constructor/hoods/v3/headwear", identifier + ".png")
    if category in {"face", "hair"} and identifier in VARIANTS:
        return _read_file(ROOT / "media/constructor/racial_anatomy/v5/face", identifier + ".png")
    if version not in {
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
    }:
        abort(404)
    if category == "form":
        from .constructor_physiques import PROFILES

        gender = request.args.get("gender", "male")
        if (
            identifier not in PROFILES
            or gender not in {"male", "female"}
            or version not in {21, 22, 23, 24, 25, 26, 27, 28}
        ):
            abort(404)
        return _read_file(
            ROOT / "media/constructor/cards/v28" / gender / category, identifier + ".png"
        )
    if category == "face" and identifier == "library-spider-01":
        return _read_file(ROOT / "media/constructor/cards/v28/hair", identifier + ".png")
    if category in {"face", "hair", "outfit", "arms", "legs", "back"}:
        allowed = (
            identifier in {*LIBRARY_IDS, *REFERENCE_IDS}
            or category in {"outfit", "arms", "legs"}
            and identifier in COSTUMES
            or category == "back"
            and identifier in BACK_IDS
            or category == "hair"
            and identifier in PROCEDURAL_HAIR
        )
    elif category in FEATURES:
        tokens = identifier.split("--")
        allowed = len(tokens) == 2 and tokens[0] in RACES and tokens[1] in FEATURES[category]
    else:
        allowed = category in OPTIONS and identifier in OPTIONS[category]
    if not allowed:
        abort(404)
    # Older cache URLs serve the consolidated current option.
    card_root = ROOT / "media/constructor/cards/v28" / category
    if category == "back" and identifier == "back-quiver":
        card_root = ROOT / "media/constructor/quiver_cards/v1"
    response = _read_file(card_root, identifier + ".png")
    response.headers["Cache-Control"] = "private, max-age=86400"
    return response


@blueprint.get("/constructor/references/<identifier>.png")
def constructor_reference_image(identifier: str):
    from .workshop_constructor import REFERENCE_IDS, REFERENCE_SOURCE

    if identifier not in REFERENCE_IDS:
        abort(404)
    response = _read_file(REFERENCE_SOURCE / identifier, "reference.png")
    response.headers["Cache-Control"] = "private, max-age=86400"
    return response


@blueprint.get("/constructor/attribute-references/")
def constructor_attribute_references():
    import json

    root = ROOT / "media/constructor/attribute_references/v1"
    specs = json.loads((root / "requests.json").read_text())["entries"]
    manifest = (
        json.loads((root / "manifest.json").read_text())
        if (root / "manifest.json").exists()
        else {"entries": []}
    )
    return render_template(
        "constructor_attribute_references.html", entries=manifest["entries"], total=len(specs)
    )


@blueprint.get("/constructor/attribute-references/images/<identifier>.png")
def constructor_attribute_reference_image(identifier: str):
    import json

    root = ROOT / "media/constructor/attribute_references/v1"
    identifiers = {e["id"] for e in json.loads((root / "requests.json").read_text())["entries"]}
    if identifier not in identifiers:
        abort(404)
    response = _read_file(root / identifier, "front.png")
    response.headers["Cache-Control"] = "private, max-age=86400"
    return response


@blueprint.get("/constructor/attribute-parts/<category>/<int:number>.png")
def constructor_attribute_part_card(category, number):
    from .constructor_atlas import defaults, part_folder

    if category == "back":
        abort(404)
    if request.args.get("race") == "goblin" and category in {"gloves", "boots"}:
        if number not in {1, 2, 3}:
            abort(404)
        from .constructor_goblins import SOURCE as GOBLIN_SOURCE

        return _read_file(GOBLIN_SOURCE / category, f"{number:02d}.png")
    if category not in defaults() or not 1 <= number <= (30 if category == "hair" else 10):
        abort(404)
    if category == "headwear":
        from .constructor_head_accessories import SOURCE as HEAD_ACCESSORY_SOURCE

        gender = request.args.get("gender", "male")
        if gender not in {"male", "female"}:
            abort(404)
        return _read_file(HEAD_ACCESSORY_SOURCE / gender / f"{number:02d}", "front.png")
    if category in {"shoulders", "belts"}:
        from .constructor_armor_details import SOURCE as ARMOR_SOURCE

        gender = request.args.get("gender", "male")
        if gender not in {"male", "female"}:
            abort(404)
        return _read_file(ARMOR_SOURCE / gender / category, f"{number:02d}.png")
    if category == "emblems" and number in {2, 5, 10}:
        return _read_file(
            ROOT / "media/constructor/cards/v28/emblem",
            {2: "sun", 5: "skull", 10: "serpent"}[number] + ".png",
        )
    if category == "body_forms":
        gender = request.args.get("gender", "male")
        if gender not in {"male", "female"}:
            abort(404)
        response = _read_file(
            ROOT / "media/constructor/cards/v28" / gender / category, f"{number:02d}.png"
        )
    elif category in {"hair", "beards", "mustaches"}:
        from .constructor_atlas import available

        gender = request.args.get(
            "gender",
            "female" if category == "hair" and (16 <= number <= 20 or number >= 26) else "male",
        )
        if gender not in {"male", "female"} or number not in available(category, "human", gender):
            abort(404)
        if category == "hair":
            return _read_file(
                ROOT / "media/constructor/hair_review/v1" / gender / "hair", f"{number:02d}.png"
            )
        revision = (
            "v6"
            if category == "hair" and (number == 2 or number >= 21)
            else "v4"
            if category == "beards" and number in {9, 10}
            else "v3"
            if category == "beards" and number in {3, 4}
            else "v1"
        )
        folder = ROOT / f"media/constructor/attribute_portraits/{revision}" / gender / category
        response = _read_file(folder, f"{number:02d}.png")
    elif category == "boots":
        gender = request.args.get("gender", "male")
        if gender not in {"male", "female"}:
            abort(404)
        response = _read_file(
            ROOT / "media/constructor/component_cards/v1" / gender / "boots", f"{number:02d}.png"
        )
    elif category == "patterns":
        response = _read_file(
            ROOT / "media/constructor/clothing_motif_cards/v2", f"{number:02d}.png"
        )
    elif category == "back" and number == 8:
        response = _read_file(ROOT / "media/constructor/quiver_cards/v1", "back-08.png")
    elif category in {"male_clothes", "female_clothes"} and number in {1, 2}:
        response = _read_file(ROOT / "media/constructor/cards/v28" / category, f"{number:02d}.png")
    else:
        response = _read_file(part_folder(category, number), "front.png")
    response.headers["Cache-Control"] = "private, max-age=86400"
    return response
