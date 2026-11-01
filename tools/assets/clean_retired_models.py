"""Remove explicitly replaced scenery only after consumers migrate; default is a dry run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.assets.asset_policy import canonical_entry, retired_model

ROOT = Path(__file__).resolve().parents[2]


def clean(root: Path = ROOT, *, apply: bool = False, report: Path | None = None) -> dict:
    media = root / "media"
    documents = {
        name: json.loads((media / name).read_text())
        for name in ("catalog.json", "imported_catalog.json")
    }
    retired = {
        row["id"]: row for doc in documents.values() for row in doc["assets"] if retired_model(row)
    }
    kept = [row for doc in documents.values() for row in doc["assets"] if row["id"] not in retired]
    live = {ref["path"] for row in kept for ref in row["files"].values()}
    candidates = {ref["path"] for row in retired.values() for ref in row["files"].values()}
    # Old revisions of a replaced architecture publication are owned derivatives.
    # Do not traverse source libraries or shared files belonging to retained rows.
    for row in kept:
        path = row.get("files", {}).get("model", {}).get("path", "")
        if path.startswith("decorations/mom_rpg/architecture/"):
            folder = media / Path(*Path(path).parts[:5])
            candidates.update(
                p.relative_to(media).as_posix()
                for p in folder.rglob("*")
                if p.is_file() and p.name in {"model.glb", "recipe.json", "preview.png"}
            )
    for row in kept:
        path = row.get("files", {}).get("model", {}).get("path", "")
        if row["id"].startswith("equipment.shared.") and path.startswith("equipment/shared/"):
            folder = media / Path(*Path(path).parts[:4])
            candidates.update(
                p.relative_to(media).as_posix()
                for p in folder.rglob("*")
                if p.is_file()
                and p.name in {"model.glb", "attachment.json", "recipe.json", "preview.png"}
            )
    for row in retired.values():
        if row["id"].startswith("decoration.202608"):
            folder = media / "decorations" / row["id"]
            candidates.update(
                p.relative_to(media).as_posix() for p in folder.rglob("*") if p.is_file()
            )
    deleted = sorted(candidates - live)
    for relative in deleted:
        path = media / relative
        if path.is_symlink() or not path.resolve().is_relative_to(media.resolve()):
            raise ValueError("Retired file escapes media: " + relative)
    result = {
        "removed_ids": sorted(retired),
        "deleted_files": deleted,
        "shared_files_preserved": sorted(candidates & live),
        "bytes_removed": sum((media / p).stat().st_size for p in deleted if (media / p).is_file()),
    }
    if apply:
        for name, doc in documents.items():
            doc["assets"] = [
                canonical_entry(row) for row in doc["assets"] if row["id"] not in retired
            ]
            doc["aliases"] = {
                key: value
                for key, value in doc.get("aliases", {}).items()
                if key not in retired and value not in retired
            }
            (media / name).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
        for relative in deleted:
            (media / relative).unlink(missing_ok=True)
        parents = {
            p
            for name in deleted
            for p in (media / name).parents
            if p != media and p.is_relative_to(media)
        }
        for folder in sorted(parents, key=lambda p: len(p.parts), reverse=True):
            if folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()
    if report:
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        f"{'Removed' if apply else 'Planned'} {len(retired)} models, {len(deleted)} files, "
        f"{result['bytes_removed']} bytes"
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    clean(apply=args.apply, report=args.report)
