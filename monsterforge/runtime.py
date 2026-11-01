"""BHM static bind data for the standalone character constructor.

The constructor reads BHM's own SDK contracts and reuses its existing GLB
exporter's bind matrices. It never needs the game's FK/IK or animation runtime.
"""

from __future__ import annotations

from .paths import ROOT


def load_bind_skeleton(profile: str = "canonical") -> dict:
    from monster_forge_sdk.characters import load_skeleton

    return load_skeleton(profile, root=ROOT)


def bind_positions(skeleton: dict) -> dict[str, list[float]]:
    """Expose the same static joint origins used to export inverse bind matrices."""
    from tools.assets.bake_character_models import bone_matrices

    return {
        bone["id"]: matrix[:3, 3].tolist()
        for bone, matrix in zip(skeleton["bones"], bone_matrices(skeleton), strict=True)
    }


def bind_bones(profile: str = "canonical") -> list[dict]:
    skeleton = load_bind_skeleton(profile)
    positions = bind_positions(skeleton)
    return [
        {"id": bone["id"], "parent": bone["parent"], "position": positions[bone["id"]]}
        for bone in skeleton["bones"]
    ]


def source_availability() -> tuple[bool, str | None]:
    """The rich HTTP editor needs its immutable source and preset pack.

    Startup checks the fixed inventory, paths and byte sizes without rereading
    its full payload. Release admission verifies all hashes, and the existing
    source readers retain their per-part hash and recipe-equivalence checks.
    """
    from .resources import load_resources

    try:
        resources = load_resources(ROOT)
        required = {
            "config/constructor_library_v1.json",
            "config/constructor_species_v2.json",
            "config/constructor_reference_kits_v1.json",
            "config/constructor_presets/v1/index.json",
            "config/constructor_artifacts_v1.json",
            "media/constructor/library/v1/library-human-01/parts.json",
            "media/constructor/attribute_references/v1/requests.json",
        }
        if not required <= resources.keys():
            return False, "The constructor resource inventory is incomplete."
        for name, spec in resources.items():
            path = ROOT / name
            current = ROOT
            for component in path.relative_to(ROOT).parts:
                current /= component
                if current.is_symlink():
                    return False, "The constructor source pack contains a symlink: " + name
            if not path.is_file() or path.stat().st_size != spec["size_bytes"]:
                return False, "The constructor source pack is missing or changed: " + name
    except (OSError, ValueError) as error:
        return False, f"The constructor source pack cannot be read: {error}"
    return True, None
