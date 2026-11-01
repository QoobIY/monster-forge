"""Build disposable part revisions from admitted settings and pinned sources.

The compiler owns geometry transformations. It does not know Flask, catalogs or
local saved revisions. The source loader and preview renderer are explicit ports.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np

from tools.creature_workshop.geometry import compile_recipe, export_glb, mesh, render_png

from ..paths import STYLE_PATH, resolve_asset_path
from ..serialization import encoded as _encoded
from ..skin_weights import build_weight_sidecar
from .geometry import _head, _tint, _transform
from .registry import ConstructorRegistry, default_registry
from .settings import validate_settings
from .sources import load_part


def _hash(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def build(
    payload: dict,
    target: Path,
    *,
    weights: bool = False,
    registry: ConstructorRegistry | None = None,
    source_loader=None,
    renderer=render_png,
) -> dict:
    from ..constructor_back import author as author_back
    from ..constructor_back import tint as tint_back

    registry = registry or default_registry()
    source_loader = source_loader or (lambda donor, slot: load_part(donor, slot, registry=registry))
    settings = validate_settings(payload, registry=registry)
    if settings["race"] in registry.rpg_races:
        from ..constructor_marsh_forest import build as build_owned

        return build_owned(settings, target, weights=weights)
    target.mkdir(parents=True, exist_ok=True)
    if settings["race"] in registry.species:
        from ..constructor_species_runtime import build as build_species

        return build_species(settings, target, weights=weights)
    from ..constructor_knees import BIND_PROFILE, bind_bones, skeleton_snapshot
    from ..constructor_knees import apply as apply_knees

    skeleton, skeleton_hash = skeleton_snapshot()
    (target / "skeleton.json").write_bytes(_encoded(skeleton))
    choices = {
        "head": settings["face"],
        "torso": settings["outfit"],
        "left_arm": settings["arms"],
        "right_arm": settings["arms"],
        "left_leg": settings["legs"],
        "right_leg": settings["legs"],
    }
    if settings["back"]:
        choices["back_attachment"] = settings["back"]
    elif settings["reference_parts"]["back"]:
        choices["back_attachment"] = next(iter(registry.back_ids))
    derived = {}
    preview_arrays = []
    head_recipe, _ = source_loader(settings["face"], "head")
    effective_colors = copy.deepcopy(settings["colors"])
    from ..constructor_atlas import color_overrides

    for key, value in color_overrides(settings).items():
        if effective_colors[key] is None:
            effective_colors[key] = value
    if settings["race"] in {"orc", "minotaur", "goblin"} and effective_colors["skin"] is None:
        from ..constructor_racial_anatomy import SKIN_COLORS

        effective_colors["skin"] = "#" + SKIN_COLORS[settings["race"]]
    if effective_colors["skin"] is None and settings["race"] not in registry.owned_races:
        palette = head_recipe["palette"]
        if settings["race"] == "goblin":
            from ..constructor_goblins import SKIN

            palette = {**palette, "skin": SKIN}
        head_skin = (
            palette["skin"]
            if settings["race"] == "goblin"
            else palette.get(
                "portrait_skin", palette.get("reuse_portrait_skin", palette.get("skin"))
            )
        )
        if settings["race"] == "wolf" and settings["face"] not in registry.original_ids:
            head_skin = palette.get("primary")
        if head_skin:
            effective_colors["skin"] = "#" + head_skin.lstrip("#")
    total_triangles = 0
    width = registry.form_widths[settings["form"]]
    for slot, donor in choices.items():
        recipe, source = source_loader(
            "library-human-01" if donor in registry.back_ids else donor, slot
        )
        if donor in registry.back_ids:
            recipe = author_back(recipe, donor, slot)
        local_sources = [source]
        from ..constructor_ghosts import refine_arms

        refine_arms(recipe, settings, slot)
        if donor in registry.reference_ids and slot != "head":
            recipe["commands"] = [
                c for c in recipe["commands"] if not c["part"].startswith("ornament_")
            ]
        if slot == "head":
            recipe = _head(
                recipe, settings, local_sources, registry=registry, source_loader=source_loader
            )
            from ..constructor_golem_faces import apply as refine_golem_face

            refine_golem_face(recipe, settings, slot)
        from ..constructor_owned_pelts import apply as refine_owned_pelt

        refine_owned_pelt(recipe, settings, slot)
        from ..constructor_component_fit import clothing as separate_clothing

        separate_clothing(recipe, slot)
        from ..constructor_limb_caps import round_roots

        round_roots(recipe, slot)
        _tint(
            recipe, effective_colors, race=settings["race"] if settings["colors"]["skin"] else None
        )
        if slot == "back_attachment":
            tint_back(recipe, settings["colors"])
        from ..constructor_decor import apply as apply_decor

        apply_decor(recipe, settings, slot)
        from ..constructor_atlas import apply as apply_atlas
        from ..constructor_costumes import apply as author_costume
        from ..constructor_costumes import atlas_settings

        apply_atlas(recipe, atlas_settings(settings, slot), slot)
        author_costume(recipe, settings, slot)
        if settings["race"] == "goblin" and slot != "head":
            _tint(recipe, effective_colors, race="goblin")
        from ..constructor_emblems import apply_native, refine_reference

        refine_reference(recipe, settings, slot)
        apply_native(recipe, settings, slot)
        if settings["race"] == "randomium":
            from ..constructor_randomiums import apply_chest_emblem

            apply_chest_emblem(recipe, settings, slot)
        apply_knees(recipe)
        from ..constructor_racial_anatomy import apply as author_racial_anatomy

        author_racial_anatomy(recipe, settings, slot)
        from ..constructor_goblins import extremities
        from ..constructor_goblins import headwear as goblin_headwear

        extremities(recipe, settings, slot)
        if slot == "head":
            goblin_headwear(recipe, settings)
        if settings["face"] in registry.racial_anatomies and slot == "head":
            _tint(recipe, effective_colors, race=settings["race"])
        from ..constructor_physiques import apply as apply_physique

        apply_physique(recipe, settings, slot)
        from ..constructor_stance import apply as apply_stance

        apply_stance(recipe)
        from ..constructor_component_fit import footwear

        footwear(recipe, slot)
        recipe["bind_profile"] = BIND_PROFILE
        recipe["skeleton_sha256"] = skeleton_hash
        if slot == "head":
            from ..constructor_face_fit import attach

            if (
                settings["face"] not in registry.racial_anatomies
                and settings["race"] not in registry.owned_races
            ):
                attach(recipe)
        for ref in recipe.get("attribute_references", []):
            local_sources.append(
                {
                    "donor": f"attribute-{ref['category']}-{ref['variant']:02d}",
                    "slot": slot,
                    "reference_files": [{"path": ref["image"], "sha256": ref["image_sha256"]}],
                    "record": ref,
                    "recipe": {"schema_version": 1, "depth_status": ref["depth_status"]},
                }
            )
        if slot == "head" and settings["race"] == "wolf" and settings["colors"]["skin"]:
            recipe["palette"]["primary"] = settings["colors"]["skin"].lstrip("#")
        if slot != "head" and (
            width != 1
            or (settings["gender"] == "female" and settings["race"] not in registry.owned_races)
        ):
            changed = []
            for c in recipe["commands"]:
                verts, _ = mesh(c)
                y = float(verts[:, 1].mean())
                feminine = (
                    0.96 if settings["gender"] == "female" and slot == "torso" and (y > 1.2) else 1
                )
                factor = width * feminine
                offset = np.zeros(3)
                if slot.endswith("_leg"):
                    from ..constructor_knees import world_bind

                    offset[0] = world_bind()[slot.split("_")[0] + "_knee"][0] * (1 - factor)
                changed.append(_transform(c, np.array([factor, 1, 1]), offset, donor))
            recipe["commands"] = changed
        from ..constructor_surface_fit import apply as fit_surfaces

        fit_surfaces(recipe, slot)
        from ..constructor_component_fit import facial_hair, nose_clearance

        if settings["race"] == "human" and slot == "head":
            nose_clearance(recipe)
            facial_hair(recipe, settings)
        from ..constructor_costumes import fit as fit_costume

        fit_costume(recipe)
        from ..constructor_goblins import fit_costume as fit_goblin_costume

        fit_goblin_costume(recipe)
        from ..constructor_armor_details import apply as refine_armor_details

        refine_armor_details(recipe, settings, slot)
        if slot == "head":
            from ..constructor_hair_shape import refine_braids

            refine_braids(recipe)
            from ..constructor_human_heads import reshape as reshape_human_head

            reshape_human_head(recipe, settings, slot)
            from ..constructor_helmets import apply as fit_helmet

            fit_helmet(recipe, settings)
            from ..constructor_head_accessories import apply as refine_head_accessories

            refine_head_accessories(recipe, settings)
            from ..constructor_faceless import apply as faceless

            faceless(recipe, settings)
        if slot == "back_attachment":
            from ..constructor_quiver import fit as fit_quiver

            fit_quiver(recipe)
            from ..constructor_back_fit import apply as fit_back

            if "own_body_design" in recipe and any(
                c["part"] == "racial_tail" for c in recipe["commands"]
            ):
                recipe["back_surface_attachment"] = {
                    "schema_version": 1,
                    "method": "native pelvic attachment authored in shared SDK bind",
                    "origin_metres": [0, 1.085, -0.11],
                    "source_revision": recipe["own_body_design"]["id"],
                }
            else:
                fit_back(recipe, json.loads((target / "parts/torso/recipe.json").read_text()))
        from ..constructor_human_heads import apply as refine_human_head

        refine_human_head(recipe, settings, slot)
        from ..constructor_neck import apply as shorten_neck

        shorten_neck(recipe, slot)
        from ..constructor_ghosts import apply_spirit

        apply_spirit(recipe, settings, slot)
        if (
            settings["race"] in {"orc", "minotaur", "goblin"}
            or settings["colors"]["skin"] is not None
            or (settings["race"] == "ghost" and slot == "head")
        ):
            _tint(recipe, effective_colors, race=settings["race"])
        from ..constructor_hand_orientation import apply as orient_hand
        from ..constructor_part_descriptions import selected as describe_part

        orient_hand(recipe, slot)
        from ..constructor_rigid_regions import mark_dice_head

        mark_dice_head(recipe, slot)
        recipe["ai_description"] = describe_part(settings, slot)
        recipe.setdefault("team_materials", ["cloth", "banner", "team"])
        recipe["constructor"] = {
            "schema_version": registry.version,
            "slot": slot,
            "settings": settings,
            "sources": [
                {k: v for k, v in x.items() if k not in {"recipe", "record"}} for x in local_sources
            ],
            "style_profile": json.loads(STYLE_PATH.read_text()),
            "style_sha256": _hash(STYLE_PATH.read_bytes()),
        }
        recipe["commands"].sort(key=lambda c: c["stage"])
        identity = _hash(_encoded(recipe))
        recipe["id"] = "constructor." + identity + "." + slot
        arrays = compile_recipe(recipe)
        preview_arrays.append(arrays)
        if not np.isfinite(arrays[0]).all():
            raise ValueError("Неконечные координаты производной детали")
        folder = target / "parts" / slot
        folder.mkdir(parents=True, exist_ok=True)
        export_glb(folder / "model.glb", arrays, recipe)
        (folder / "recipe.json").write_bytes(_encoded(recipe))
        (folder / "sources.json").write_bytes(
            _encoded({"schema_version": registry.version, "sources": local_sources})
        )
        for index, source in enumerate(local_sources):
            for ref_index, ref in enumerate(source["reference_files"] if weights else []):
                blob = resolve_asset_path(ref["path"], root=registry.asset_root).read_bytes()
                if _hash(blob) != ref["sha256"]:
                    raise ValueError("Изменился сохранённый reference")
                (folder / f"reference-{index}-{ref_index}.png").write_bytes(blob)
        blob = (folder / "model.glb").read_bytes()
        info = {
            "revision_id": identity,
            "slot": slot,
            "model": f"parts/{slot}/model.glb",
            "ai_description": recipe["ai_description"],
            "model_sha256": _hash(blob),
            "triangles": len(arrays[0]) // 3,
            "bounds_metres": [arrays[0].min(0).tolist(), arrays[0].max(0).tolist()],
        }
        if weights:
            from ..runtime import load_bind_skeleton

            sidecar = build_weight_sidecar(folder / "model.glb", slot, bind_profile=BIND_PROFILE)
            from ..constructor_hand_orientation import apply_weights as bind_hand

            bind_hand(sidecar, recipe, arrays[3])
            from ..constructor_rigid_regions import apply_weights as bind_rigid

            bind_rigid(sidecar, recipe, arrays[3])
            sdk_allowed = set(load_bind_skeleton()["slot_bindings"][slot]["allowed_bones"])
            if set(sidecar["allowed_bones"]) != sdk_allowed:
                raise ValueError("Контракт весов не совпадает с bind-скелетом BHM")
            (folder / "weights.json").write_bytes(_encoded(sidecar))
            info["weights"] = f"parts/{slot}/weights.json"
            info["weights_sha256"] = _hash((folder / "weights.json").read_bytes())
        derived[slot] = info
        total_triangles += info["triangles"]
    floors = [derived[s]["bounds_metres"][0][1] for s in ("left_leg", "right_leg")]
    if max(abs(y) for y in floors) > 1e-05 or abs(floors[0] - floors[1]) > 1e-05:
        raise ValueError("Ноги не стоят на общей плоскости Y=0; нужна коррекция исходной части")
    selection = {
        "schema_version": registry.version,
        "skeleton_id": "humanoid_v1",
        "bind_profile": BIND_PROFILE,
        "skeleton_sha256": skeleton_hash,
        "parts": {
            slot: {"revision_id": i["revision_id"], "model_sha256": i["model_sha256"]}
            for slot, i in derived.items()
        },
    }
    selection["id"] = _hash(_encoded(selection))
    (target / "assembly.json").write_bytes(_encoded(selection))
    warnings = []
    if settings["gender"] == "female" and settings["face"] not in registry.female_heads:
        warnings.append(
            "Женский вариант этой расы выведен из исходной геометрии, отдельного утверждённого эталона нет."
        )
    if settings["race"] == "wolf" and settings["face"] not in registry.original_ids:
        warnings.append("Волколюдь использует новую humanoid-ревизию головы существующего волка.")
    if settings["race"] == "skeleton" and settings["outfit"] not in {
        "skeletal-archer",
        "evil-necromancer",
        *[d["id"] for d in registry.library_designs if d["race"] == "skeleton"],
    }:
        warnings.append("У костюма остаётся шея донора; проверьте её соответствие скелету.")
    manifest = {
        "schema_version": registry.version,
        "id": selection["id"],
        "contract": "humanoid_v1",
        "bind_profile": BIND_PROFILE,
        "skeleton_sha256": skeleton_hash,
        "skeleton": "skeleton.json",
        "bind_bones": bind_bones(),
        "status": "authoring_draft",
        "parts": derived,
        "triangles": total_triangles,
        "checks": {
            "finite_geometry": True,
            "shared_floor": True,
            "source_hashes": True,
            "weight_sidecars": weights,
        },
        "warnings": warnings,
    }
    (target / "manifest.json").write_bytes(_encoded(manifest))
    if weights:
        merged = tuple(np.concatenate([a[i] for a in preview_arrays]) for i in range(3)) + ([],)
        renderer(target / "preview.png", merged, size=320)
    integrity = {
        str(p.relative_to(target)): _hash(p.read_bytes())
        for p in sorted(target.rglob("*"))
        if p.is_file()
    }
    (target / "integrity.json").write_bytes(
        _encoded({"schema_version": registry.version, "files": integrity})
    )
    return manifest
