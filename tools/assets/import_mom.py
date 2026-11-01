"""Import current MOM icons, scenery and their preserved style provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from tools.assets.asset_policy import RETIRED_DECORATION_ROOTS, canonical_entry
from tools.assets.icon_policy import RETIRED_GROUPS, RETIRED_UI_FOLDERS

ROOT = Path(__file__).resolve().parents[2]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def import_assets(source: Path, destination: Path = ROOT) -> dict:
    source = source.resolve()
    destination = destination.resolve()
    media = source / "media"
    entries = []
    copied = {}

    def file_ref(path: Path, *, expected: str | None = None) -> dict:
        relative = path.relative_to(media)
        target = destination / "media" / relative
        checksum = digest(path)
        if expected is not None and checksum != expected:
            raise ValueError(f"MOM source integrity mismatch: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and digest(target) != checksum:
            raise ValueError(f"Existing asset would change: {relative}")
        if not target.exists():
            shutil.copyfile(path, target)
        copied[str(relative)] = checksum
        return {
            "path": relative.as_posix(),
            "sha256": checksum,
            "size_bytes": target.stat().st_size,
            "media_type": {
                ".png": "image/png",
                ".svg": "image/svg+xml",
                ".glb": "model/gltf-binary",
                ".json": "application/json",
                ".zip": "application/zip",
            }.get(path.suffix, "application/octet-stream"),
        }

    def referenced(ref: dict) -> dict:
        uri = ref["uri"]
        if not uri.startswith("/media/"):
            raise ValueError(f"Unsupported source URI: {uri}")
        p = (media / uri[7:]).resolve()
        if not p.is_relative_to(media.resolve()):
            raise ValueError("Source escapes media root")
        return file_ref(p, expected=ref["sha256"])

    latest = {}
    for record in (media / "icons").rglob("record.json"):
        data = json.loads(record.read_text())
        identity = data["id"]
        if identity not in latest or data["revision"] > latest[identity][1]["revision"]:
            latest[identity] = (record, data)
    for identity, (record, data) in sorted(latest.items()):
        if data['kind'] != 'item_icon_collection' or data.get('name') in RETIRED_GROUPS:
            continue
        record_ref = file_ref(record)
        if data["kind"] == "item_icon_collection":
            references = {
                "record": record_ref,
                "manifest": referenced(data["manifest"]),
                "archive": referenced(data["archive"]),
            }
            for icon in data["icons"]:
                entries.append(
                    {
                        "id": f"icon.collection.{identity}.{icon['id']}",
                        "kind": "icon",
                        "title": icon["id"].replace("_", " ").title(),
                        "group": data["name"],
                        "revision": data["revision"],
                        "tags": [
                            "equipment",
                            icon.get("weapon_type") or icon.get("item_type"),
                        ],
                        "files": {"image": referenced(icon["file"]), **references},
                        "source_id": icon["id"],
                        "source_uri": icon["file"]["uri"],
                    }
                )
        else:
            entries.append(
                {
                    "id": f"icon.{identity}",
                    "kind": "icon",
                    "title": identity.replace(".", " · ").replace("_", " "),
                    "group": "Способности и эффекты",
                    "revision": data["revision"],
                    "tags": [data["purpose"]],
                    "files": {"image": referenced(data["file"]), "record": record_ref},
                    "source_id": identity,
                    "source_uri": data["file"]["uri"],
                }
            )
    # Separate UI icons are runtime assets, not historical generator output.
    for p in sorted((media / "ui/icons").rglob("*")):
        if p.suffix.lower() not in {".png", ".svg"}:
            continue
        relative = p.relative_to(media / "ui/icons")
        if relative.parts[0] in RETIRED_UI_FOLDERS:
            continue
        entries.append(
            {
                "id": "icon.ui." + relative.as_posix().replace("/", "."),
                "kind": "icon",
                "title": p.stem.replace("_", " ").replace("-", " "),
                "group": "Интерфейс · "
                + (
                    relative.parent.as_posix()
                    if relative.parent.as_posix() != "."
                    else "общие"
                ),
                "revision": 1,
                "tags": ["ui"],
                "files": {"image": file_ref(p)},
                "source_uri": "/media/" + p.relative_to(media).as_posix(),
            }
        )
    # Reusable runtime icons from map assets; no map/gameplay data is imported.
    for p in sorted((media / "maps").rglob("*")):
        if "icons" not in p.parts or p.suffix.lower() not in {".png", ".svg"}:
            continue
        if p.parent.name == "icons":
            continue
        relative = p.relative_to(media / "maps")
        destination_path = destination / "media/icons/maps" / relative
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        if destination_path.exists() and digest(destination_path) != digest(p):
            raise ValueError("Immutable map icon changed")
        shutil.copyfile(p, destination_path)
        ref = {
            "path": destination_path.relative_to(destination / "media").as_posix(),
            "sha256": digest(p),
            "size_bytes": p.stat().st_size,
            "media_type": "image/svg+xml" if p.suffix == ".svg" else "image/png",
        }
        copied[ref["path"]] = ref["sha256"]
        entries.append(
            {
                "id": "icon.map." + relative.as_posix().replace("/", "."),
                "kind": "icon",
                "title": p.stem.replace("_", " "),
                "group": "Игровые иконки · " + p.parent.name,
                "revision": 1,
                "tags": ["game", p.parent.name],
                "files": {"image": ref},
                "source_uri": "/media/maps/" + relative.as_posix(),
            }
        )
    for record in sorted((media / "decorations").rglob("record.json")):
        if any(part in RETIRED_DECORATION_ROOTS for part in record.parts):
            continue
        data = json.loads(record.read_text())
        files = {"record": file_ref(record)}
        for part in data["composition"]["parts"]:
            key = (
                "model"
                if len(data["composition"]["parts"]) == 1
                else "model." + part["id"]
            )
            files[key] = referenced(part["file"])
        # Actual model thumbnails are generated separately; preserve producer refs.
        for preview in record.parent.rglob("*.png"):
            files["source_preview"] = file_ref(preview)
        entries.append(
            {
                "id": data["id"],
                "kind": "decoration",
                "title": data["title"],
                "description": data.get("description", ""),
                "group": "Окружение",
                "revision": data["revision"],
                "tags": data.get("tags", []),
                "files": files,
                "composition": data["composition"],
                "metadata": data.get("metadata", {}),
            }
        )
    entries = [canonical_entry(a) for a in entries]
    # Preserve the exact complete prompt snapshots and the explicit MOM override.
    style_source = source / "artifacts/imagegen/nova"
    style_root = destination / "styles/icons"
    style_root.mkdir(parents=True, exist_ok=True)
    for name in ("prompts-mom.json", "prompts.json", "mom-style-reference.jpg"):
        shutil.copyfile(style_source / name, style_root / name)
    prompts = json.loads((style_root / "prompts-mom.json").read_text())
    prompt = next(iter(prompts["atlases"].values()))["prompt"]
    override = prompt.split("\\nUse case:", 1)[0].split("\nUse case:", 1)[0]
    profile = {
        "schema_version": 1,
        "id": "mom-icons-v1",
        "name": "MOM · гранёные игровые иконки",
        "prompt": override,
        "source": "prompts-mom.json",
        "source_sha256": digest(style_root / "prompts-mom.json"),
        "reference": "mom-style-reference.jpg",
        "reference_sha256": digest(style_root / "mom-style-reference.jpg"),
    }
    (style_root / "profile.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n"
    )
    (style_root / "style.txt").write_text(override + "\n")
    # Re-importing unchanged sources retains verified, derived model thumbnails.
    previous_path = destination / "media/imported_catalog.json"
    if previous_path.is_file():
        previous = json.loads(previous_path.read_text())
        if previous.get("schema_version") != 1:
            raise ValueError("Unsupported previous import catalog schema")
        previous_assets = {row["id"]: row for row in previous["assets"]}
        for row in entries:
            old = previous_assets.get(row["id"], {})
            preview = old.get("files", {}).get("preview")
            model = row["files"].get("model")
            if preview and model == old.get("files", {}).get("model"):
                path = (destination / "media" / preview["path"]).resolve()
                if not path.is_relative_to((destination / "media").resolve()):
                    raise ValueError("Previous preview escapes media root")
                if path.is_file() and digest(path) == preview["sha256"]:
                    row["files"]["preview"] = preview
    result = {
        "schema_version": 1,
        "source": "Machine of Monsters current runtime media",
        "assets": entries,
        "imported_files": copied,
    }
    (destination / "media/imported_catalog.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    result = import_assets(parser.parse_args().source)
    print(
        f"Imported {len(result['assets'])} assets / {len(result['imported_files'])} verified files"
    )
