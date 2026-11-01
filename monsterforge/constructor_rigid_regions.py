"""Bind explicitly rigid constructor regions without changing their geometry."""

from __future__ import annotations


def mark_dice_head(recipe, slot):
    if slot != "head":
        return
    marked = False
    for command in recipe["commands"]:
        if command["part"] in {"randomium_die_head", "randomium_die_pip"}:
            command["skin_bone"] = "head"
            marked = True
    if marked:
        recipe["rigid_regions_revision"] = 1


def apply_weights(sidecar, recipe, ends):
    if "rigid_regions_revision" not in recipe:
        return
    if recipe["rigid_regions_revision"] != 1:
        raise ValueError("Unknown rigid region revision")
    start = 0
    for command, end in zip(recipe["commands"], ends, strict=True):
        bone = command.get("skin_bone")
        if bone:
            if bone not in sidecar["allowed_bones"]:
                raise ValueError("Rigid region bone is outside its slot contract")
            index = sidecar["bone_palette"].index(bone)
            for vertex in range(start, end):
                sidecar["skin_indices"][vertex] = [index, 0, 0, 0]
                sidecar["skin_weights"][vertex] = [1.0, 0.0, 0.0, 0.0]
        start = end
    sidecar["rigid_regions_revision"] = 1
