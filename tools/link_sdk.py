"""Link this asset project and its Python SDK into a consumer, without a server."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def link_project(consumer: Path, source: Path = ROOT) -> tuple[Path, Path]:
    source = source.resolve(strict=True)
    consumer = consumer.resolve(strict=True)
    if not consumer.is_dir():
        raise ValueError("Consumer must be an existing project directory")
    if consumer == source or consumer.is_relative_to(source):
        raise ValueError("Consumer must be outside the asset project")
    for required in ("media/catalog.json", "monster_forge_sdk/__init__.py"):
        if not (source / required).is_file():
            raise ValueError(f"Missing asset project file: {required}")
    project = consumer / "vendor/big-head-models"
    sdk = consumer / "monster_forge_sdk"
    links = ((project, source), (sdk, project / "monster_forge_sdk"))
    # Check both destinations before creating anything; never overwrite user files.
    for link, target in links:
        if (link.exists() or link.is_symlink()) and (
            not link.is_symlink() or link.resolve() != target.resolve()
        ):
            raise FileExistsError(f"Conflicting destination: {link}")
    project.parent.mkdir(parents=True, exist_ok=True)
    for link, target in links:
        if not link.is_symlink():
            link.symlink_to(
                os.path.relpath(target, link.parent), target_is_directory=True
            )
    return project, sdk


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "consumer", type=Path, help="Existing consumer project directory"
    )
    args = parser.parse_args()
    for link in link_project(args.consumer):
        print(f"{link} -> {os.readlink(link)}")
    print("Ready: from monster_forge_sdk import AssetStore; assets = AssetStore()")
