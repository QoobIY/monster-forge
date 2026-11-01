"""Slot recipe transformations used by the build pipeline and legacy adapters."""

from __future__ import annotations

import copy

import numpy as np

from tools.creature_workshop.geometry import compile_recipe, mesh

from .registry import ConstructorRegistry, default_registry
from .sources import load_part


def _is_hair(c: dict) -> bool:
    part = c["part"].lower()
    return (
        "hair" in part
        or "braid" in part
        or "topknot" in part
        or ("quiff" in part)
        or ("beard" in part)
        or ("mane" in part)
    ) and (not any(x in part for x in ("ear", "horn")))


def _is_headwear(c: dict) -> bool:
    if ("hair_" in c["part"] or "scalp" in c["part"]) and "hair_flower" not in c["part"]:
        return False
    return any(
        x in c["part"].lower() for x in ("helmet", "hood", "hat", "cap", "crown", "hair_flower")
    )


def _transform(c: dict, scale: np.ndarray, offset: np.ndarray, source: str) -> dict:
    """Bake into part geometry, never into assembly placement or runtime formulas."""
    vertices, faces = mesh(c)
    if np.array_equal(scale, [1, 1, 1]) and np.array_equal(offset, [0, 0, 0]):
        return c
    if c["op"] != "indexed_mesh":
        from tools.creature_workshop.family_faces import orient_faces

        faces = orient_faces(vertices, faces)
    changed = {
        key: copy.deepcopy(value)
        for key, value in c.items()
        if key
        not in {
            "center",
            "radii",
            "stations",
            "path",
            "points",
            "offset",
            "size",
            "sides",
            "rings",
            "vertex_normals",
        }
    }
    changed.update(
        op="indexed_mesh", vertices=(vertices * scale + offset).tolist(), faces=faces.tolist()
    )
    if "vertex_normals" in c:
        normals = np.asarray(c["vertex_normals"]) / scale
        normals /= np.linalg.norm(normals, axis=1)[:, None]
        changed["vertex_normals"] = normals.tolist()
    history = copy.deepcopy(c.get("constructor_transforms", []))
    history.append({"source": source, "scale": scale.tolist(), "offset": offset.tolist()})
    changed["constructor_transforms"] = history
    return changed


def _tint(recipe: dict, colors: dict, *, race: str | None = None) -> None:
    palette = recipe["palette"]
    old_skin = palette.get("portrait_skin", palette.get("reuse_portrait_skin", palette.get("skin")))
    if colors["skin"] and old_skin:
        old = np.array(list(bytes.fromhex(old_skin.lstrip("#"))), dtype=float)
        new = np.array(list(bytes.fromhex(colors["skin"].lstrip("#"))), dtype=float)
        for name, value in list(palette.items()):
            if name.lower().endswith(("_shadow", "_lip", "_nostril")) or name in {"shadow", "lip"}:
                rgb = np.array(list(bytes.fromhex(value.lstrip("#"))), dtype=float)
                palette[name] = "".join(
                    f"{v:02x}"
                    for v in np.clip(np.round(rgb / np.maximum(old, 1) * new), 0, 255).astype(int)
                )
    for name in list(recipe["palette"]):
        low = name.lower()
        group = (
            "skin"
            if race == "skeleton" and low in {"bone", "skull_bone"}
            else "skin"
            if low in {"skin", "head_skin"} or low.endswith("_skin")
            else "eyes"
            if "iris" in low or low == "v10_eye"
            else "cloth"
            if low in {"primary", "cloth"} or low.endswith("_cloth")
            else "accent"
            if low == "accent" or low.endswith("_accent")
            else next(
                (k for k in ("metal", "leather", "secondary") if low == k or low.endswith("_" + k)),
                None,
            )
        )
        if group and colors[group]:
            recipe["palette"][name] = colors[group].lstrip("#")
    if colors["hair"]:
        rgb = np.array(list(bytes.fromhex(colors["hair"].lstrip("#"))))
        recipe["palette"]["constructor_hair_color"] = colors["hair"].lstrip("#")
        recipe["palette"]["constructor_hair_highlight"] = "".join(
            f"{v:02x}" for v in np.minimum(np.round(rgb * 1.1), 255).astype(int)
        )
        for c in recipe["commands"]:
            if _is_hair(c) and "flower" not in c["part"] or "brow" in c["part"]:
                c["material"] = (
                    "constructor_hair_highlight"
                    if "light" in c["material"]
                    else "constructor_hair_color"
                )
                c.pop("face_materials", None)
    if recipe["commands"][0].get("slot") == "head":
        has_iris = any(
            c["part"] in {"visible_iris", "iris", "lateral_eye", "animal_eye", "soul_eye"}
            for c in recipe["commands"]
        )
        for c in recipe["commands"]:
            if colors["eyes"] and (
                c["part"]
                in {"lateral_eye", "visible_iris", "eye_iris", "animal_eye", "soul_eye", "iris"}
                or (not has_iris and c["part"] in {"eye_aperture", "eye_opening"})
            ):
                c["material"] = "constructor_eye_color"
                c.pop("face_materials", None)
                recipe["palette"]["constructor_eye_color"] = colors["eyes"].lstrip("#")


def _head(
    recipe: dict,
    settings: dict,
    sources: list[dict],
    *,
    registry: ConstructorRegistry | None = None,
    source_loader=load_part,
) -> dict:
    registry = registry or default_registry()
    if settings["race"] == "ghost":
        from ..constructor_ghosts import prepare_hair

        return prepare_hair(recipe, settings)
    if settings["race"] in registry.owned_races:
        from ..constructor_bear_mouths import apply as bear_mouth

        return bear_mouth(recipe, settings)
    from ..constructor_portraits import anatomy, procedural_hair

    if "reference_base_head" in recipe and (
        not all(v == "original" for v in settings["features"].values())
    ):
        base = recipe["reference_base_head"]
        recipe["commands"] = copy.deepcopy(base["commands"])
        recipe["palette"].update(base["palette"])
    if "reference_design" in recipe:
        recipe["commands"] = [
            c for c in recipe["commands"] if not c["part"].startswith("ornament_")
        ]
    if not all(v == "original" for v in settings["features"].values()):
        from ..constructor_head_topology import upgrade

        upgrade(recipe)
    if settings["race"] != "goblin":
        recipe = anatomy(recipe, settings)
    commands = recipe["commands"]
    if settings["decor"]["beard"] != "original":
        commands = [c for c in commands if "beard" not in c["part"]]
    if settings["decor"]["mustache"] != "original":
        commands = [
            c for c in commands if not any(key in c["part"] for key in ("mustache", "moustache"))
        ]
    if (
        settings["race"] == "skeleton"
        and (not any(c["part"] == "soul_eye" for c in commands))
        and (
            settings["colors"]["eyes"]
            or settings["eye_size"] != 1
            or settings["eye_shape"] != "original"
        )
    ):
        eye_recipe, provenance = source_loader("evil-necromancer", "head")
        sources.append(provenance)
        recipe["palette"]["constructor_soul_eye"] = eye_recipe["palette"]["v10_eye"]
        for original in eye_recipe["commands"]:
            if original["part"] == "soul_eye":
                eye = copy.deepcopy(original)
                eye["id"] = "constructor_soul_" + eye["id"]
                eye["material"] = "constructor_soul_eye"
                commands.append(eye)
    if settings["race"] == "wolf" and settings["face"] not in registry.original_ids:
        commands = [
            _transform(
                c, np.array([0.74, 0.74, 0.74]), np.array([0, 0.98, -0.65]), settings["face"]
            )
            for c in commands
        ]
    commands = sorted(commands, key=lambda c: c["stage"])
    if settings["hair"] != "original":
        commands = [c for c in commands if not _is_hair(c) and (not _is_headwear(c))]
        if settings["hair"] in registry.procedural_hair:
            hair, palette = procedural_hair(
                {**recipe, "commands": commands}, registry.procedural_hair[settings["hair"]][1]
            )
            commands.extend(hair)
            recipe["palette"].update(palette)
        elif settings["hair"] != "bald":
            donor = registry.hair_donors[settings["hair"]]
            hair_recipe, provenance = source_loader(donor, "head")
            sources.append(provenance)
            hair = [
                copy.deepcopy(c)
                for c in hair_recipe["commands"]
                if (
                    _is_hair(c)
                    or (settings["hair"] == "original-ink-archivist" and _is_headwear(c))
                )
                and ("beard" not in c["part"] or settings["hair"] == "original-ember-forger")
            ]
            target = compile_recipe({**recipe, "commands": commands})[0]
            source_face = [
                c
                for c in hair_recipe["commands"]
                if c["part"] in {"traced_reference_face", "rounded_cranium"}
            ]
            donor_face = compile_recipe({**hair_recipe, "commands": source_face})[0]
            target_face_cmds = [
                c
                for c in commands
                if c["part"] in {"traced_reference_face", "reference_face", "canine_cranium"}
            ]
            if target_face_cmds:
                target = compile_recipe({**recipe, "commands": target_face_cmds})[0]
            width = min(
                1.5, max(0.6, float(np.ptp(target[:, 0]) / max(np.ptp(donor_face[:, 0]), 1e-06)))
            )
            scale = np.array([width, 1, width])
            offset = np.array([0, float(target[:, 1].max() - donor_face[:, 1].max()), 0])
            materials = {name: "constructor_hair_" + name for name in hair_recipe["palette"]}
            recipe["palette"].update({materials[k]: v for k, v in hair_recipe["palette"].items()})
            for c in hair:
                c["material"] = materials[c["material"]]
                if "face_materials" in c:
                    c["face_materials"] = [materials[m] for m in c["face_materials"]]
                c = _transform(c, scale, offset, donor)
                c["id"] = "constructor_hair_" + c["id"]
                commands.append(c)
    if (
        settings["gender"] == "female"
        and settings["face"] not in registry.female_heads
        and (settings["race"] != "skeleton")
    ):
        changed = []
        for c in commands:
            is_face = c["part"] in {
                "traced_reference_face",
                "reference_face",
                "nasal_tip",
                "closed_mouth",
                "bull_lower_lip",
                "canine_cranium",
                "long_canine_muzzle",
                "canine_lower_jaw",
                "observed_boar_head",
                "observed_elephant_skull",
            }
            if is_face:
                revised = _transform(c, np.array([0.94, 1, 1]), np.zeros(3), settings["face"])
                vertices = np.asarray(revised["vertices"])
                lo, hi = (vertices[:, 1].min(), vertices[:, 1].max())
                t = np.clip((vertices[:, 1] - lo) / max(hi - lo, 1e-06), 0, 1)
                jaw = 0.9 + 0.1 * np.minimum(t / 0.6, 1)
                vertices[:, 0] *= jaw
                revised["vertices"] = vertices.tolist()
                revised.pop("vertex_normals", None)
                revised["constructor_transforms"].append(
                    {"kind": "feminine_jaw", "min_width": 0.9, "cheek_fraction": 0.6}
                )
                changed.append(revised)
            elif "brow" in c["part"]:
                center = mesh(c)[0].mean(0)
                scale = np.array([0.92, 0.7, 1])
                changed.append(_transform(c, scale, center * (1 - scale), settings["face"]))
            else:
                changed.append(c)
        commands = changed
    if settings["eye_size"] != 1 or settings["eye_shape"] != "original":
        eyes = [
            c
            for c in commands
            if any(t in c["part"] for t in ("eye", "iris", "pupil")) and "brow" not in c["part"]
        ]
        for side in (-1, 1):
            group = [c for c in eyes if float(mesh(c)[0][:, 0].mean()) * side > 0]
            if not group:
                continue
            centers = [
                mesh(c)[0].mean(0)
                for c in group
                if "socket" in c["part"] or "aperture" in c["part"]
            ]
            center = np.mean(centers or [mesh(c)[0].mean(0) for c in group], axis=0)
            proportions = registry.eye_proportions[settings["eye_shape"]]
            scale = np.array(
                [settings["eye_size"] * proportions[0], settings["eye_size"] * proportions[1], 1]
            )
            changed = {
                id(c): _transform(c, scale, center * (1 - scale), settings["face"]) for c in group
            }
            commands = [changed.get(id(c), c) for c in commands]
    recipe["commands"] = sorted(commands, key=lambda c: c["stage"])
    return recipe
