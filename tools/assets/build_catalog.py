"""Build the shared file catalog without importing the character application."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.assets.asset_policy import canonical_entry, retired_model
from tools.assets.icon_policy import retired_icon

ROOT = Path(__file__).resolve().parents[2]


def build_catalog(root: Path = ROOT) -> dict:
    media = root / "media"
    imported = json.loads((media / "imported_catalog.json").read_text())["assets"]
    current_path = media / 'catalog.json'
    if current_path.exists():
        current = json.loads(current_path.read_text())
        if current.get('constructor_storage_version') == 2:
            # Runtime releases contain complete characters, never compiler parts.
            entries = {row['id']: row for row in current['assets']}
            for row in imported:
                if row['kind'] != 'character' and not retired_icon(row) and not retired_model(row):
                    row = canonical_entry(row)
                    entries[row['id']] = row
            current['assets'] = list(entries.values())
            current_path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + '\n')
            return current
    entries = [canonical_entry(a) for a in imported if not retired_icon(a) and not retired_model(a)]
    for p in sorted((media / "constructor").rglob("*.glb")):
        relative = p.relative_to(media)
        scope = p.relative_to(media / "constructor")
        ref = {
            "path": relative.as_posix(),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "size_bytes": p.stat().st_size,
            "media_type": "model/gltf-binary",
        }
        parent = p.parent
        files = {"model": ref}
        if (parent / "recipe.json").is_file():
            recipe = parent / "recipe.json"
        else:
            recipe = p.with_suffix(".recipe.json")
        if recipe.exists():
            files["recipe"] = {
                "path": recipe.relative_to(media).as_posix(),
                "sha256": hashlib.sha256(recipe.read_bytes()).hexdigest(),
                "size_bytes": recipe.stat().st_size,
                "media_type": "application/json",
            }
        weights = p.with_suffix(".weights.json")
        if weights.is_file():
            files["weights"] = {
                "path": weights.relative_to(media).as_posix(),
                "sha256": hashlib.sha256(weights.read_bytes()).hexdigest(),
                "size_bytes": weights.stat().st_size,
                "media_type": "application/json",
            }
        preview = p.parent.parent / "preview.png"
        if preview.is_file():
            files["preview"] = {
                "path": preview.relative_to(media).as_posix(),
                "sha256": hashlib.sha256(preview.read_bytes()).hexdigest(),
                "size_bytes": preview.stat().st_size,
                "media_type": "image/png",
            }
        record_path = p.parent.parent / "record.json"
        record = json.loads(record_path.read_text()) if record_path.is_file() else {}
        design = record.get("design", record.get("spec", record))
        race = record.get("race", design.get("race", ""))
        label = record.get("label", design.get("label", ""))
        races = {"human": "Люди", "orc": "Орки", "minotaur": "Минотавры", "skeleton": "Скелеты", "goblin": "Гоблины", "tree": "Тренты", "golem": "Големы", "panda": "Панды", "beorn": "Медвежьи", "quillboar": "Иглогривы", "ghost": "Призраки", "beast-sheep": "Овцы", "beast-tiger": "Тигры"}
        category = races.get(race)
        tags = ["modular", "part", p.stem]
        cosmetic = scope.parts[0] == "mom_skins"
        arena = scope.parts[0] == "angel_arena"
        if arena:
            tags.extend(["angel_arena", "reviewed_constructor"])
        if cosmetic:
            tags.extend(["cosmetic", "skin"])
        if race:
            tags.append(race)
        if record.get("rig"):
            tags.append(record["rig"])
        entries.append(
            {
                "id": "character." + scope.with_suffix("").as_posix().replace("/", "."),
                "kind": "character",
                "title": (label + " · " + p.stem.replace("_", " ")).strip(" ·"),
                "group": ("Персонажи · Angel Arena · " + (category or race)) if arena else ("Облики · " + (category or race)) if cosmetic else "Персонажи · " + category if category else scope.parts[0],
                "revision": 1,
                "tags": tags,
                "files": files,
            }
        )
    from tools.assets.bake_character_models import publish
    from tools.assets.publish_character_runtime import publish_runtime

    data = publish_runtime(root, {"schema_version": 1, "assets": entries})
    publish(root, data)
    published = json.loads((media / "catalog.json").read_text())
    published["assets"] = [canonical_entry(a) for a in published["assets"]
                           if not retired_model(a)]
    (media / "catalog.json").write_text(json.dumps(published, ensure_ascii=False, indent=2) + "\n")
    return published


if __name__ == "__main__":
    data = build_catalog()
    print("Indexed", len(data["assets"]), "assets")
