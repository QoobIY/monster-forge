"""Pinned inputs of the existing constructor, without application dependencies.

The inventory admits exact source files, never derivative GLBs, weights, cards,
raw image-tool responses or unrelated game assets. Reading it grants no license.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath

MANIFEST = "config/constructor_resources_v1.json"
CONFIG_NAMES = {
    "constructor_artifacts_v1.json", "constructor_human_approval_v1.json",
    "constructor_library_v1.json", "constructor_part_descriptions_v7.json",
    "constructor_portraits_v1.json", "constructor_reference_kits_v1.json", "constructor_species_v2.json",
}
SOURCE_NAMES = {"recipe.json", "record.json", "parts.json", "integrity.json", "source.json", "character.json", "requests.json", "master.json"}
CLASSIFICATIONS = {"recipe", "part_manifest", "provenance", "integrity", "reference_metadata", "reference_input", "preset", "configuration", "artifact_index"}


def resource_classification(name: str) -> str:
    """Restrict the inventory's authority to constructor source inputs."""
    if not isinstance(name, str) or not name:
        raise ValueError("Constructor resource path must be a relative string")
    path = PurePosixPath(name)
    if (path.is_absolute() or ".." in path.parts or "\\" in name or name != path.as_posix()
            or any(part in {".git", ".aws", ".ssh", "node_modules", "__pycache__"} for part in path.parts)):
        raise ValueError("Invalid constructor resource path")
    if name.startswith("config/constructor_presets/v1/") and path.suffix == ".json":
        return "preset"
    if name.startswith("config/") and len(path.parts) == 2 and path.name in CONFIG_NAMES:
        return "artifact_index" if path.name == "constructor_artifacts_v1.json" else "configuration"
    if not name.startswith("media/constructor/"):
        raise ValueError("Constructor resource is outside the source library")
    if path.name == "recipe.json" or path.name.endswith(".recipe.json"):
        return "recipe"
    if path.name in SOURCE_NAMES:
        if path.name == "parts.json":
            return "part_manifest"
        if path.name == "integrity.json":
            return "integrity"
        if path.name in {"requests.json", "master.json"}:
            return "reference_metadata"
        return "provenance"
    parts = path.parts
    front = (len(parts) == 6 and parts[:4] == ("media", "constructor", "attribute_references", "v1")
             and path.name == "front.png" and re.fullmatch(r"[a-z_]+", parts[4]))
    master = name in {
        "media/constructor/attribute_references/v1/attribute_grid_master_v1.png",
        "media/constructor/attribute_references/v1/attribute_grid_mask_v1.png",
    }
    reference = (len(parts) == 6 and parts[:4] == ("media", "constructor", "reference_kits", "v2")
                 and parts[4].startswith("reference-") and path.name == "reference.png")
    if front or master or reference:
        return "reference_input"
    raise ValueError("Unsupported constructor resource type")


def _file(root: Path, name: str) -> Path:
    path = root / name
    current = root
    for component in PurePosixPath(name).parts:
        current /= component
        if current.is_symlink():
            raise ValueError("Constructor resource must not use symlinks: " + name)
    if not path.resolve().is_relative_to(root) or not path.is_file():
        raise ValueError("Missing or unsafe constructor resource: " + name)
    return path


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate constructor resource inventory key")
        result[key] = value
    return result


def load_resources(root: Path | None = None) -> dict[str, dict]:
    """Read only the fixed manifest; resource payloads are not opened here."""
    root = (Path(root) if root is not None else Path(__file__).resolve().parents[1]).resolve()
    try:
        data = json.loads(_file(root, MANIFEST).read_bytes(), object_pairs_hook=_object)
    except (OSError, ValueError) as error:
        raise ValueError("Cannot read constructor resource inventory") from error
    if (not isinstance(data, dict) or set(data) != {"schema_version", "resources"}
            or type(data.get("schema_version")) is not int or data["schema_version"] != 1
            or not isinstance(data.get("resources"), dict) or not data["resources"]):
        raise ValueError("Unsupported constructor resource inventory schema")
    result = {}
    for name, spec in data["resources"].items():
        classification = resource_classification(name)
        if (not isinstance(spec, dict) or set(spec) != {"sha256", "size_bytes", "classification"}
                or not isinstance(spec.get("sha256"), str)
                or re.fullmatch(r"[0-9a-f]{64}", spec["sha256"]) is None
                or type(spec.get("size_bytes")) is not int or spec["size_bytes"] <= 0
                or not isinstance(spec.get("classification"), str)
                or spec["classification"] not in CLASSIFICATIONS
                or spec["classification"] != classification):
            raise ValueError("Invalid constructor resource metadata: " + name)
        result[name] = dict(spec)
    return result


def verify_resources(root: Path | None = None) -> list[str]:
    """Return missing/tampered resource errors; malformed inventories raise ValueError."""
    root = (Path(root) if root is not None else Path(__file__).resolve().parents[1]).resolve()
    errors = []
    for name, spec in load_resources(root).items():
        try:
            path = _file(root, name)
            if path.stat().st_size != spec["size_bytes"]:
                raise ValueError("Constructor resource byte size changed: " + name)
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != spec["sha256"]:
                raise ValueError("Constructor resource hash changed: " + name)
        except (OSError, ValueError) as error:
            errors.append(str(error))
    return errors
