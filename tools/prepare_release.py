"""Prepare a reviewable source-only directory without publishing or editing inputs.

``python -m tools.prepare_release --draft`` writes a draft under /tmp. A normal
export requires passing code-scope release checks. Both modes exclude the same
content roots, credential filenames, caches and Git metadata as check_release.
New non-ignored source files are included. An existing nonempty output is never
replaced; no Git history is copied or rewritten and no license is assigned.
Three BHM-owned bind JSON source files are included from media/rigs for SDK
packaging. Policy v3 additionally includes the existing constructor's exact
hash-pinned source inputs, without admitting neighboring art or derived GLBs.

Manifest schema 2 records excluded content only as aggregate counts. Schema 1
drafts are not rewritten; regenerate them to remove their historical per-file
exclusion inventory before sharing a tools-only artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from tools.check_release import (
    CODE_CONTRACTS,
    CONSTRUCTOR_RESOURCES_FILE,
    CONTENT_ROOTS,
    DOCUMENTATION_IMAGES,
    LOCAL_ROOTS,
    TOOL_CONFIG_FILES,
    _constructor_resources,
    _documentation_png,
    _release_policy,
    _resource_file,
    _resource_paths,
    audit,
    exclusion_reason,
    select_paths,
    sensitive_name,
    working_tree_paths,
)


def _source_file(root: Path, name: str, *, resources: frozenset[str] = frozenset()) -> Path:
    if name in resources:
        return _resource_file(root, name)
    path = root / name
    resolved = path.resolve()
    if not resolved.is_relative_to(root) or sensitive_name(resolved.relative_to(root).as_posix()):
        raise ValueError("Unsafe source file: " + name)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Source export requires regular files: " + name)
    if name in DOCUMENTATION_IMAGES and not _documentation_png(root, name):
        raise ValueError("Documentation screenshot must be a PNG: " + name)
    return path


def prepare(root: Path, output: Path, *, draft: bool = False) -> dict:
    root = Path(root).resolve()
    output = Path(output)
    if output.is_symlink():
        raise ValueError("Output must not be a symlink")
    output = output.resolve()
    if root.is_relative_to(output):
        raise ValueError("Output must not contain or replace the source checkout")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Output already exists and is not an empty directory")
    candidates = working_tree_paths(root)
    # An explicitly chosen in-workspace destination must not copy itself.
    if output.is_relative_to(root):
        prefix = output.relative_to(root).as_posix() + "/"
        candidates = [name for name in candidates if not name.startswith(prefix)]
    policy = _release_policy(root)
    resources = _constructor_resources(root, policy)
    resource_names = _resource_paths(policy, resources)
    selected = select_paths(candidates, "code", root=root)
    if any(name in {"release-manifest.json", "release-report.json"} for name in selected):
        raise ValueError("Source checkout contains reserved release metadata names")
    report = audit(root, candidates, scope="code")
    if report["blocker_count"] and not draft:
        raise ValueError(
            "Code release checks have blockers; inspect check_release or prepare an explicit --draft"
        )
    for name in selected:
        _source_file(root, name, resources=resource_names)
    selected_set = set(selected)
    exclusion_counts = Counter(
        exclusion_reason(name, "code", resources=resource_names)
        for name in candidates
        if name not in selected_set
    )
    exclusion_summary = []
    for reason, count in sorted(exclusion_counts.items()):
        entry = {"reason": reason, "file_count": count}
        if reason.startswith("excluded_scope:"):
            entry["prefix"] = reason.removeprefix("excluded_scope:")
        elif reason == "project_asset_data":
            entry["prefix"] = "config"
        exclusion_summary.append(entry)
    manifest = {
        "schema_version": 2,
        "kind": "monster_forge_source_export",
        "distribution": report["distribution"],
        "policy_file": report["policy_file"],
        "policy_schema_version": report["policy_schema_version"],
        "policy_source_schema_version": report["policy_source_schema_version"],
        "draft": draft,
        "publication_approved": False,
        "input_basis": "working_tree_including_non_ignored_untracked_files",
        "git_history_included": False,
        "license_assigned_by_exporter": False,
        "release_status": report["status"],
        "blockers": [row for row in report["findings"] if row["severity"] == "blocker"],
        "excluded_prefixes": [*CONTENT_ROOTS, *LOCAL_ROOTS],
        "included_code_contracts": [name for name in selected if name in CODE_CONTRACTS],
        "tool_config_files": [name for name in selected if name in TOOL_CONFIG_FILES],
        "documentation_images": [name for name in selected if name in DOCUMENTATION_IMAGES],
        "constructor_resources": {
            "inventory": CONSTRUCTOR_RESOURCES_FILE
            if CONSTRUCTOR_RESOURCES_FILE in resource_names
            else None,
            "file_count": len(resources),
            "paths": sorted(resources),
        },
        "additional_exclusions": [
            "credential filenames",
            "Python/build/dependency caches",
            "all Git metadata",
            "media and artifact file types except approved screenshots and pinned constructor resources",
        ],
        "excluded_paths_included": False,
        "excluded_file_count": sum(exclusion_counts.values()),
        "exclusion_summary": exclusion_summary,
        "files": [],
        "generated_metadata": ["release-manifest.json", "release-report.json"],
        "limitations": report["limitations"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".forge-release-", dir=output.parent) as temporary:
        staging = Path(temporary) / "source"
        staging.mkdir()
        for name in selected:
            source = _source_file(root, name, resources=resource_names)
            content = source.read_bytes()
            checksum = hashlib.sha256(content).hexdigest()
            if name in resources and (
                len(content) != resources[name]["size_bytes"]
                or checksum != resources[name]["sha256"]
            ):
                raise ValueError("Constructor resource changed during export: " + name)
            destination = staging / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            destination.chmod(source.stat().st_mode & 0o777)
            manifest["files"].append(
                {
                    "path": name,
                    "sha256": checksum,
                    "size_bytes": len(content),
                }
            )
        if CONSTRUCTOR_RESOURCES_FILE in resource_names and (
            _constructor_resources(staging, policy) != resources
            or not set(resources) <= selected_set
        ):
            raise ValueError("Constructor resource inventory changed or is incomplete during export")
        (staging / "release-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (staging / "release-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if output.exists():
            output.rmdir()  # Fails safely if another process filled the empty destination.
        staging.rename(output)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--output", type=Path, default=Path(tempfile.gettempdir()) / "monster-forge-source"
    )
    parser.add_argument("--draft", action="store_true")
    args = parser.parse_args()
    try:
        manifest = prepare(args.root, args.output, draft=args.draft)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(json.dumps({"schema_version": 2, "status": "export_failed", "error": str(error)}))
        return 1
    print(
        json.dumps(
            {
                "schema_version": 2,
                "status": "draft_created" if args.draft else "source_export_created",
                "output": str(args.output.resolve()),
                "source_files": len(manifest["files"]),
                "release_status": manifest["release_status"],
                "publication_approved": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
