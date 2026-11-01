"""Versioned donor inventory and the supported humanoid source extension API.

Registry instances describe immutable source bundles. with_source() returns a new
inventory; it never rewrites a bundle or modifies a published assembly.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass, field, fields, replace
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any

from ..paths import ROOT

SUPPORTED_CONTRACTS = ("humanoid_v1",)


@dataclass(frozen=True)
class SourceBundle:
    """A reviewed six-part Front source under an asset store's media/constructor.

    The caller supplies the approved manifest SHA-256, so an edited source cannot
    be silently admitted as the same extension. GLB/recipe equivalence is checked
    by sources.load_part when building each selected slot.
    """

    id: str
    label: str
    race: str
    gender: str
    directory: Path
    manifest_sha256: str
    contract: str = "humanoid_v1"
    evidence: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class ConstructorRegistry:
    """Explicit build inventory retaining the existing active contracts.

    Extension code calls with_source rather than mutating module globals. Existing
    schema migrations and build policies use the same registry as the catalog.
    """

    asset_root: Path
    source_bundles: dict[str, SourceBundle] = field(default_factory=dict)
    active_races: tuple[str, ...] = ("human",)
    animal_designs: list[dict[str, Any]] = field(default_factory=list)
    animal_ids: set[str] = field(default_factory=set)
    animal_source: Path = field(default_factory=Path)
    animal_species: dict[str, tuple[str, str, str]] = field(default_factory=dict)
    back_colors: dict[str, str] = field(default_factory=dict)
    back_ids: dict[str, str] = field(default_factory=dict)
    bear_mouth_labels: dict[str, str] = field(default_factory=dict)
    costumes: dict[str, str] = field(default_factory=dict)
    default_colors: dict[str, str] = field(default_factory=dict)
    exp_designs: list[dict[str, Any]] = field(default_factory=list)
    exp_ids: set[str] = field(default_factory=set)
    exp_species: dict[str, tuple[str, str, str]] = field(default_factory=dict)
    eyes: dict[str, str] = field(default_factory=dict)
    eye_proportions: dict[str, tuple[float, float]] = field(default_factory=dict)
    features: dict[str, dict[str, Any]] = field(default_factory=dict)
    female_heads: set[str] = field(default_factory=set)
    flyer_designs: list[dict[str, Any]] = field(default_factory=list)
    flyer_ids: set[str] = field(default_factory=set)
    flyer_source: Path = field(default_factory=Path)
    flyer_species: dict[str, tuple[str, str, str]] = field(default_factory=dict)
    forms: dict[str, str] = field(default_factory=dict)
    form_widths: dict[str, float] = field(default_factory=dict)
    ghost_forms: dict[str, str] = field(default_factory=dict)
    goblin_boots: list[str] = field(default_factory=list)
    goblin_costumes: dict[str, str] = field(default_factory=dict)
    goblin_gloves: list[str] = field(default_factory=list)
    hair: dict[str, str] = field(default_factory=dict)
    hair_donors: dict[str, str] = field(default_factory=dict)
    horse_forms: dict[str, str] = field(default_factory=dict)
    horse_manes: dict[str, str] = field(default_factory=dict)
    library_designs: list[dict[str, Any]] = field(default_factory=list)
    library_ids: set[str] = field(default_factory=set)
    library_source: Path = field(default_factory=Path)
    original_designs: list[dict[str, Any]] = field(default_factory=list)
    original_ids: set[str] = field(default_factory=set)
    outfits: dict[str, str] = field(default_factory=dict)
    owned_designs: list[dict[str, Any]] = field(default_factory=list)
    owned_ids: set[str] = field(default_factory=set)
    owned_races: dict[str, dict[str, Any]] = field(default_factory=dict)
    owned_source: Path = field(default_factory=Path)
    physiques: dict[str, dict[str, Any]] = field(default_factory=dict)
    procedural_hair: dict[str, tuple[str, str]] = field(default_factory=dict)
    races: dict[str, tuple[str, list[str], str | None]] = field(
        default_factory=lambda: {"human": ("Humans", [], None)}
    )
    racial_anatomies: dict[str, dict[str, Any]] = field(default_factory=dict)
    randomium_emblems: dict[str, str] = field(default_factory=dict)
    randomium_hidden_parts: list[str] = field(default_factory=list)
    randomium_ids: set[str] = field(default_factory=set)
    randomium_source: Path = field(default_factory=Path)
    reference_designs: list[dict[str, Any]] = field(default_factory=list)
    reference_ids: set[str] = field(default_factory=set)
    reference_source: Path = field(default_factory=Path)
    rpg_designs: list[dict[str, Any]] = field(default_factory=list)
    rpg_ids: set[str] = field(default_factory=set)
    rpg_races: dict[str, dict[str, Any]] = field(default_factory=dict)
    rpg_source: Path = field(default_factory=Path)
    settings_version: int = 5
    slots: tuple[str, ...] = ("head", "torso", "left_arm", "right_arm", "left_leg", "right_leg")
    species: dict[str, tuple[str, str, str]] = field(default_factory=dict)
    species_designs: list[dict[str, Any]] = field(default_factory=list)
    species_ids: set[str] = field(default_factory=set)
    species_source: Path = field(default_factory=Path)
    version: int = 1
    legacy_species_designs: list[dict[str, Any]] = field(default_factory=list)

    def contract_for_race(self, race: str) -> str:
        if race not in self.races:
            raise ValueError("Unknown constructor race: " + race)
        if race in self.rpg_races:
            return self.rpg_races[race]["rig"]
        return self.species[race][1] if race in self.species else "humanoid_v1"

    @property
    def supported_races(self) -> tuple[str, ...]:
        return tuple(
            race
            for race in self.active_races
            if self.contract_for_race(race) in SUPPORTED_CONTRACTS
        )

    def is_editable(self, settings: dict) -> bool:
        return isinstance(settings, dict) and settings.get("race") in self.active_races

    def source_folder(self, donor: str) -> Path:
        bundle = self.source_bundles.get(donor)
        if bundle is not None:
            return bundle.directory
        return _source_folder(donor, registry=self)

    def back_options(self) -> list[dict]:
        from ..constructor_back import options

        return options()

    def with_source(self, source: SourceBundle) -> ConstructorRegistry:
        """Admit a new immutable humanoid donor for an existing supported race.

        New rig types, autorig code and ad-hoc style overrides are intentionally
        outside this boundary. Source evidence stays inside media/constructor.
        """
        if (
            not re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", source.id)
            or source.id in self.library_ids
            or source.id in self.reference_ids
            or source.id in self.source_bundles
            or source.id in self.original_ids
        ):
            raise ValueError("Duplicate or invalid constructor source identity")
        if source.contract not in SUPPORTED_CONTRACTS or source.race not in self.supported_races:
            raise ValueError("New sources must use the supported humanoid_v1 contract")
        if source.gender not in {"male", "female"} or not source.label.strip():
            raise ValueError("Source needs an explicit gender and label")
        directory = source.directory.resolve()
        if not directory.is_relative_to((self.asset_root / "media/constructor").resolve()):
            raise ValueError("Source bundle must belong to media/constructor")
        manifest_blob = (directory / "parts.json").read_bytes()
        if (
            not re.fullmatch(r"[0-9a-f]{64}", source.manifest_sha256)
            or hashlib.sha256(manifest_blob).hexdigest() != source.manifest_sha256
        ):
            raise ValueError("Immutable source manifest changed")
        manifest = json.loads(manifest_blob)
        if (
            not isinstance(manifest, dict)
            or type(manifest.get("schema_version")) is not int
            or manifest["schema_version"] != self.version
            or manifest.get("rig_reference") != source.contract
            or manifest.get("coordinates") != "metres; Y up; +Z forward; floor Y=0"
            or not isinstance(manifest.get("parts"), dict)
            or not set(self.slots) <= manifest["parts"].keys()
            or set(manifest["parts"]) - {*self.slots, "back_attachment"}
        ):
            raise ValueError("Incompatible humanoid source manifest")
        evidence_paths = {"record.json"}
        for part in manifest["parts"].values():
            if not isinstance(part, dict) or not {"model", "recipe", "sha256"} <= part.keys():
                raise ValueError("Incomplete immutable source part")
            if not isinstance(part["sha256"], str) or not re.fullmatch(
                r"[0-9a-f]{64}", part["sha256"]
            ):
                raise ValueError("Invalid immutable source model hash")
            for role in ("model", "recipe"):
                if not isinstance(part[role], str):
                    raise ValueError("Invalid immutable source path")
                relative = PurePosixPath(part[role])
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or "\\" in part[role]
                    or relative.as_posix() != part[role]
                ):
                    raise ValueError("Source part escapes its bundle")
                path = (directory / part[role]).resolve()
                if not path.is_relative_to(directory):
                    raise ValueError("Source part escapes its bundle")
            evidence_paths.add(part["recipe"])
        if not (directory / "record.json").is_file():
            raise ValueError("Source bundle needs its immutable provenance record")
        record = json.loads((directory / "record.json").read_bytes())
        if (
            not isinstance(record, dict)
            or type(record.get("schema_version")) is not int
            or record["schema_version"] != 1
        ):
            raise ValueError("Unsupported source provenance schema")
        reference = record.get("reference_image")
        if reference is not None:
            if not isinstance(reference, str) or not (
                directory / reference
            ).resolve().is_relative_to(directory):
                raise ValueError("Source reference escapes its bundle")
            evidence_paths.add(reference)
        evidence = tuple(
            (name, hashlib.sha256((directory / name).read_bytes()).hexdigest())
            for name in sorted(evidence_paths)
        )
        if source.evidence and source.evidence != evidence:
            raise ValueError("Immutable source evidence changed")
        design = {
            "id": source.id,
            "label": source.label,
            "race": source.race,
            "gender": source.gender,
            "contract": source.contract,
            "hair": "cropped",
        }
        values = {field.name: copy.deepcopy(getattr(self, field.name)) for field in fields(self)}
        values["source_bundles"][source.id] = replace(
            source, directory=directory, evidence=evidence
        )
        values["library_designs"].append(design)
        values["library_ids"].add(source.id)
        values["original_ids"].add(source.id)
        values["outfits"][source.id] = source.label
        values["hair"][source.id] = "Source bundle · " + source.label
        values["hair_donors"][source.id] = source.id
        label, faces, female = values["races"][source.race]
        values["races"][source.race] = (
            label,
            [*faces, source.id],
            source.id if source.gender == "female" else female,
        )
        if source.gender == "female":
            values["female_heads"].add(source.id)
        if source.race in values["owned_races"]:
            values["owned_designs"].append(design)
            values["owned_ids"].add(source.id)
        return ConstructorRegistry(**values)


def _source_folder(donor: str, *, registry: ConstructorRegistry) -> Path:
    if donor in registry.randomium_ids:
        return registry.randomium_source / donor
    if donor in registry.rpg_ids:
        return registry.rpg_source / donor
    if donor in registry.exp_ids:
        from ..constructor_expansion import source_folder

        return source_folder(donor)
    if donor in registry.owned_ids and donor.startswith("native-ghost-"):
        from ..constructor_ghosts import SOURCE as GHOST_SOURCE

        return GHOST_SOURCE / donor
    if donor in registry.flyer_ids:
        return registry.flyer_source / donor
    if donor in registry.animal_ids:
        return registry.animal_source / donor
    if donor in registry.owned_ids:
        return registry.owned_source / donor
    if donor in registry.racial_anatomies:
        donor = registry.racial_anatomies[donor]["source"]
    if donor in {*registry.costumes, *registry.goblin_costumes}:
        return registry.library_source / "library-human-01"
    if donor in registry.reference_ids:
        return registry.reference_source / donor
    if donor in registry.species_ids:
        return registry.species_source / donor
    if donor in registry.library_ids:
        return registry.library_source / donor
    raise ValueError(f"Unknown current constructor source: {donor}")


@lru_cache(maxsize=1)
def default_registry() -> ConstructorRegistry:
    """Load bundled metadata only when authoring is requested."""
    from . import _inventory

    return ConstructorRegistry(
        asset_root=ROOT,
        source_bundles={},
        **{
            field: copy.deepcopy(getattr(_inventory, original))
            for original, field in _FIELDS.items()
        },
    )


_FIELDS = {
    "ACTIVE_RACES": "active_races",
    "ANIMAL_DESIGNS": "animal_designs",
    "ANIMAL_IDS": "animal_ids",
    "ANIMAL_SOURCE": "animal_source",
    "ANIMAL_SPECIES": "animal_species",
    "BACK_COLORS": "back_colors",
    "BACK_IDS": "back_ids",
    "BEAR_MOUTH_LABELS": "bear_mouth_labels",
    "COSTUMES": "costumes",
    "DEFAULT_COLORS": "default_colors",
    "EXP_DESIGNS": "exp_designs",
    "EXP_IDS": "exp_ids",
    "EXP_SPECIES": "exp_species",
    "EYES": "eyes",
    "EYE_PROPORTIONS": "eye_proportions",
    "FEATURES": "features",
    "FEMALE_HEADS": "female_heads",
    "FLYER_DESIGNS": "flyer_designs",
    "FLYER_IDS": "flyer_ids",
    "FLYER_SOURCE": "flyer_source",
    "FLYER_SPECIES": "flyer_species",
    "FORMS": "forms",
    "FORM_WIDTHS": "form_widths",
    "GHOST_FORMS": "ghost_forms",
    "GOBLIN_BOOTS": "goblin_boots",
    "GOBLIN_COSTUMES": "goblin_costumes",
    "GOBLIN_GLOVES": "goblin_gloves",
    "HAIR": "hair",
    "HAIR_DONORS": "hair_donors",
    "HORSE_FORMS": "horse_forms",
    "HORSE_MANES": "horse_manes",
    "LIBRARY_DESIGNS": "library_designs",
    "LIBRARY_IDS": "library_ids",
    "LIBRARY_SOURCE": "library_source",
    "ORIGINAL_DESIGNS": "original_designs",
    "ORIGINAL_IDS": "original_ids",
    "OUTFITS": "outfits",
    "OWNED_DESIGNS": "owned_designs",
    "OWNED_IDS": "owned_ids",
    "OWNED_RACES": "owned_races",
    "OWNED_SOURCE": "owned_source",
    "PHYSIQUES": "physiques",
    "PROCEDURAL_HAIR": "procedural_hair",
    "RACES": "races",
    "RACIAL_ANATOMIES": "racial_anatomies",
    "RANDOMIUM_EMBLEMS": "randomium_emblems",
    "RANDOMIUM_HIDDEN_PARTS": "randomium_hidden_parts",
    "RANDOMIUM_IDS": "randomium_ids",
    "RANDOMIUM_SOURCE": "randomium_source",
    "REFERENCE_DESIGNS": "reference_designs",
    "REFERENCE_IDS": "reference_ids",
    "REFERENCE_SOURCE": "reference_source",
    "RPG_DESIGNS": "rpg_designs",
    "RPG_IDS": "rpg_ids",
    "RPG_RACES": "rpg_races",
    "RPG_SOURCE": "rpg_source",
    "SETTINGS_VERSION": "settings_version",
    "SLOTS": "slots",
    "SPECIES": "species",
    "SPECIES_DESIGNS": "species_designs",
    "SPECIES_IDS": "species_ids",
    "SPECIES_SOURCE": "species_source",
    "VERSION": "version",
    "_LEGACY_SPECIES_DESIGNS": "legacy_species_designs",
}


def __getattr__(name: str):
    if name == "DEFAULT_REGISTRY":
        return default_registry()
    raise AttributeError(name)
