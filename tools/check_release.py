"""Audit release metadata and checkout paths without reading credential files.

Run ``python -m tools.check_release --scope repository`` for the complete current
working tree, or ``--scope code`` for a source-only distribution that excludes
media, styles, imported authoring source and historical artifacts. JSON goes to
stdout; exit status 1 means release blockers remain. No files are changed.
Three BHM-owned bind JSON contracts are required to build the self-contained SDK.
Policy v3 also admits exact, hash-pinned inputs of the existing constructor;
unlisted neighboring files and derivative model caches remain excluded.
Two exact documentation screenshots may additionally be distributed with a v2
policy and scoped rights approval; this never admits neighboring image files.

This is a metadata check, not a credential scanner or a grant of legal rights.
It does not inspect Git history. A code-scope pass does not approve publishing
the original Git repository, whose content and history are still present.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tomllib
from collections import Counter
from pathlib import Path, PurePosixPath

CONTENT_ROOTS = (
    "media",
    "styles",
    "artifacts",
    "tools/imported_mom",
    "tools/assetforge_generator",
    "assets",
    "config",
)
# These are BHM-owned code contracts, not art. Keep their single source for SDK packaging.
CODE_CONTRACTS = (
    "media/rigs/body_rigs.json",
    "media/rigs/humanoid/canonical.json",
    "media/rigs/humanoid/workshop_knees_v1.json",
)
TOOL_CONFIG_FILES = (
    "config/style_profile.json",
    "config/humanoid_v1.json",
    "config/release_rights.json",
    "config/release_policy.json",
)
DOCUMENTATION_IMAGES = (
    "docs/images/constructor.png",
    "docs/images/sdk-guide.png",
)
CONSTRUCTOR_RESOURCES_FILE = "config/constructor_resources_v1.json"
LOCAL_ROOTS = (".serena", ".codex", ".agents", ".aws", ".git")
CACHE_PARTS = {"__pycache__", ".venv", "venv", ".ruff_cache", "build", "dist", "node_modules"}
ARTIFACT_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".bmp",
    ".tga",
    ".tif",
    ".tiff",
    ".avif",
    ".heic",
    ".exr",
    ".hdr",
    ".dds",
    ".ktx",
    ".ktx2",
    ".psd",
    ".ai",
    ".ico",
    ".glb",
    ".gltf",
    ".obj",
    ".mtl",
    ".fbx",
    ".blend",
    ".usd",
    ".usdz",
    ".abc",
    ".ply",
    ".stl",
    ".bin",
    ".wav",
    ".mp3",
    ".ogg",
    ".flac",
    ".aac",
    ".m4a",
    ".mid",
    ".midi",
    ".sf2",
    ".sfz",
    ".mp4",
    ".mkv",
    ".mov",
    ".avi",
    ".webm",
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
    ".eot",
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    ".tgz",
    ".whl",
    ".egg",
    ".momskin",
    ".w3x",
    ".w3m",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
}
LICENSE_NAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "LICENCE.md", "COPYING")
TEXT_SUFFIXES = {
    ".py",
    ".js",
    ".css",
    ".html",
    ".json",
    ".toml",
    ".md",
    ".txt",
    ".lock",
    ".yml",
    ".yaml",
}
USER_PATH = re.compile(r"/(?:home|Users)/[A-Za-z0-9_.-]+/|[A-Za-z]:\\Users\\[A-Za-z0-9_.-]+\\")
CREDENTIAL_URL = re.compile(r"https?://[^\s/@:]+:[^\s/@]+@")


def within(name: str, prefix: str) -> bool:
    return name == prefix or name.startswith(prefix + "/")


def sensitive_name(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        (
            path.name.startswith(".env")
            and path.name not in {".env.example", ".env.sample", ".env.template"}
        )
        or path.name in {".netrc", "credentials", "id_rsa", "id_ed25519"}
        or any(part in {".aws", ".ssh"} for part in path.parts)
        or path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}
    )


def _relative(name: object) -> bool:
    if not isinstance(name, str) or not name:
        return False
    path = PurePosixPath(name)
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and name == path.as_posix()
        and "\\" not in name
    )


def exclusion_reason(
    name: str, scope: str = "code", *, resources: frozenset[str] = frozenset()
) -> str | None:
    if scope not in {"code", "repository"}:
        raise ValueError("Unknown release scope")
    if scope == "repository":
        return None
    if sensitive_name(name):
        return "credential_filename"
    parts = PurePosixPath(name).parts
    if ".git" in parts:
        return "git_metadata"
    if any(part in CACHE_PARTS for part in parts) or PurePosixPath(name).suffix in {".pyc", ".pyo"}:
        return "local_cache"
    if (
        name in CODE_CONTRACTS
        or name in TOOL_CONFIG_FILES
        or name in DOCUMENTATION_IMAGES
        or name in resources
    ):
        return None
    if within(name, "config"):
        return "project_asset_data"
    for prefix in (*CONTENT_ROOTS, *LOCAL_ROOTS):
        if within(name, prefix):
            return "excluded_scope:" + prefix
    if PurePosixPath(name).suffix.lower() in ARTIFACT_SUFFIXES:
        return "artifact_file_type"
    return None


def select_paths(
    paths: list[str], scope: str = "code", *, root: Path | None = None
) -> list[str]:
    """Share the exact source-only scope between audit and export."""
    if scope not in {"code", "repository"}:
        raise ValueError("Unknown release scope")
    if not all(_relative(name) for name in paths):
        raise ValueError("Expected normalized relative checkout paths")
    policy = _release_policy(Path(root).resolve()) if root is not None else None
    resources = _constructor_resources(Path(root).resolve(), policy) if root is not None else {}
    admitted = _resource_paths(policy, resources)
    return [
        name
        for name in sorted(set(paths))
        if exclusion_reason(name, scope, resources=admitted) is None
    ]


def working_tree_paths(root: Path) -> list[str]:
    """Include new, non-ignored source files; never inspect history or ignored files."""
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        check=True,
        capture_output=True,
    )
    return sorted({name for name in result.stdout.decode("utf-8").split("\0") if name})


def _release_policy(root: Path) -> dict | None:
    path = root / "config/release_policy.json"
    if not path.exists() and not path.is_symlink():
        return None
    if not path.resolve().is_relative_to(root) or sensitive_name(
        path.resolve().relative_to(root).as_posix()
    ):
        raise ValueError("Unsafe release policy path")
    data = json.loads(path.read_bytes())
    if (
        not isinstance(data, dict)
        or type(data.get("schema_version")) is not int
        or data["schema_version"] not in {1, 2, 3}
        or data.get("distribution") != "tools-only"
        or data.get("code_license") != "Apache-2.0"
        or data.get("asset_library_included") is not False
        or data.get("git_history_included") is not False
        or not isinstance(data.get("license_files"), list)
        or not data["license_files"]
        or not all(_relative(name) for name in data["license_files"])
        or not isinstance(data.get("included_code_contracts"), list)
        or len(data["included_code_contracts"]) != len(CODE_CONTRACTS)
        or set(data["included_code_contracts"]) != set(CODE_CONTRACTS)
        or not isinstance(data.get("tool_config_files"), list)
        or len(data["tool_config_files"]) != len(TOOL_CONFIG_FILES)
        or set(data["tool_config_files"]) != set(TOOL_CONFIG_FILES)
    ):
        raise ValueError("Unsupported or inconsistent tools-only release policy")
    version = data["schema_version"]
    fields = {
        "schema_version",
        "distribution",
        "code_license",
        "license_files",
        "asset_library_included",
        "git_history_included",
        "included_code_contracts",
        "tool_config_files",
    }
    if version >= 2:
        fields.add("documentation_images")
        images = data.get("documentation_images")
        if (
            not isinstance(images, list)
            or len(images) != len(DOCUMENTATION_IMAGES)
            or not all(isinstance(name, str) for name in images)
            or set(images) != set(DOCUMENTATION_IMAGES)
        ):
            raise ValueError("Policy must declare only the approved documentation screenshots")
    if version == 3:
        fields.add("constructor_resources")
        if data.get("constructor_resources") != CONSTRUCTOR_RESOURCES_FILE:
            raise ValueError("Policy v3 must use the exact constructor resource inventory")
    if set(data) != fields:
        raise ValueError("Unknown release policy fields; use an explicit schema migration")
    # Reading v1 never widens its scope or rewrites the source policy. Its
    # migrated view explicitly has no documentation-image authorization.
    normalized = {**data, "schema_version": max(2, version), "source_schema_version": version}
    if version == 1:
        normalized["documentation_images"] = []
    return normalized


def _resource_file(root: Path, name: str) -> Path:
    """Resource admission never follows symlinks, including parent directories."""
    if not _relative(name) or name == "." or sensitive_name(name):
        raise ValueError("Unsafe constructor resource path")
    path = root
    for part in PurePosixPath(name).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("Constructor resources must not use symlinks: " + name)
    if not path.resolve().is_relative_to(root) or not path.is_file():
        raise ValueError("Missing or non-regular constructor resource: " + name)
    return path


def _constructor_resources(root: Path, policy: dict | None) -> dict:
    """Older policies cannot admit inventory files or widen their fixed scope."""
    if policy is None or policy["source_schema_version"] != 3:
        return {}
    _resource_file(root, CONSTRUCTOR_RESOURCES_FILE)
    # The top-level package and resource loader are standard-library only.
    # Importing monsterforge.constructor here would load optional geometry code.
    from monsterforge.resources import load_resources

    return load_resources(root)


def _resource_paths(policy: dict | None, resources: dict) -> frozenset[str]:
    if policy is not None and policy["source_schema_version"] == 3:
        return frozenset({CONSTRUCTOR_RESOURCES_FILE, *resources})
    return frozenset()


def _verify_constructor_resource(root: Path, name: str, spec: dict) -> None:
    path = _resource_file(root, name)
    if path.stat().st_size != spec["size_bytes"]:
        raise ValueError("Constructor resource size mismatch: " + name)
    with path.open("rb") as source:
        checksum = hashlib.file_digest(source, "sha256").hexdigest()
    if checksum != spec["sha256"]:
        raise ValueError("Constructor resource hash mismatch: " + name)


def _documentation_png(root: Path, name: str) -> bool:
    path = root / name
    resolved = path.resolve()
    if (
        path.is_symlink()
        or not resolved.is_relative_to(root)
        or sensitive_name(resolved.relative_to(root).as_posix())
        or not path.is_file()
    ):
        return False
    # Standard-library format admission only; no asset-generation dependencies
    # and no claims about the screenshot's artistic or visual quality.
    with path.open("rb") as stream:
        header = stream.read(33)
        if (
            len(header) != 33
            or header[:8] != b"\x89PNG\r\n\x1a\n"
            or header[8:16] != b"\0\0\0\rIHDR"
            or not 0 < int.from_bytes(header[16:20], "big") <= 32768
            or not 0 < int.from_bytes(header[20:24], "big") <= 32768
        ):
            return False
        stream.seek(-12, 2)
        return stream.read(12) == b"\0\0\0\0IEND\xaeB`\x82"


def _project_content(name: str, *, resources: frozenset[str] = frozenset()) -> bool:
    return name not in {*CODE_CONTRACTS, *TOOL_CONFIG_FILES, *resources} and (
        PurePosixPath(name).suffix.lower() in ARTIFACT_SUFFIXES
        or any(within(name, prefix) for prefix in CONTENT_ROOTS)
    )


def _rights(root: Path) -> list[dict]:
    path = root / "config/release_rights.json"
    if not path.resolve().is_relative_to(root) or sensitive_name(
        path.resolve().relative_to(root).as_posix()
    ):
        raise ValueError("Unsafe rights inventory path")
    data = json.loads(path.read_bytes())
    if (
        not isinstance(data, dict)
        or type(data.get("schema_version")) is not int
        or data["schema_version"] != 1
        or not isinstance(data.get("scopes"), list)
    ):
        raise ValueError("Unsupported release rights schema")
    seen, prefixes = set(), set()
    for item in data["scopes"]:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("id"), str)
            or not item["id"]
            or item["id"] in seen
            or not isinstance(item.get("paths"), list)
            or not item["paths"]
            or not all(_relative(name) and name != "." for name in item["paths"])
            or not isinstance(item.get("origin"), str)
            or not item["origin"]
            or item.get("redistribution") not in {"approved", "pending", "blocked"}
            or not isinstance(item.get("evidence"), list)
            or not all(_relative(name) for name in item["evidence"])
        ):
            raise ValueError("Invalid release rights scope")
        seen.add(item["id"])
        if any(prefix in prefixes for prefix in item["paths"]):
            raise ValueError("Duplicate release rights path")
        prefixes.update(item["paths"])
        if item["redistribution"] == "approved" and (
            not isinstance(item.get("license"), str)
            or not item["license"]
            or not item["evidence"]
            or not all((root / name).is_file() for name in item["evidence"])
        ):
            raise ValueError("Approved scope requires a license and existing evidence")
    return data["scopes"]


def _metadata(root: Path, name: str) -> dict:
    path = root / name
    if not path.resolve().is_relative_to(root) or sensitive_name(
        path.resolve().relative_to(root).as_posix()
    ):
        raise ValueError("Unsafe package metadata path")
    return tomllib.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def audit(root: Path, tracked: list[str], *, scope: str = "repository") -> dict:
    """Return facts and blockers; explicit path inputs make admission testable."""
    if scope not in {"code", "repository"}:
        raise ValueError("Unknown release scope")
    root = Path(root).resolve()
    tracked = sorted(set(tracked))
    if not all(_relative(name) for name in tracked):
        raise ValueError("Expected normalized relative tracked paths")
    excluded_roots = (*CONTENT_ROOTS, *LOCAL_ROOTS) if scope == "code" else ()
    findings = []

    def finding(identity, severity, message, paths=(), **details):
        findings.append(
            {
                "id": identity,
                "severity": severity,
                "message": message,
                "paths": list(paths),
                **details,
            }
        )

    policy = None
    policy_path = root / "config/release_policy.json"
    try:
        policy = _release_policy(root)
    except (OSError, ValueError, TypeError):
        finding(
            "release_policy_invalid",
            "blocker",
            "The tools-only release policy is unsupported or conflicts with the fixed source scope.",
            ["config/release_policy.json"],
        )
    resources = {}
    try:
        resources = _constructor_resources(root, policy)
    except (OSError, ValueError, TypeError):
        finding(
            "constructor_resources_invalid",
            "blocker",
            "The declared constructor resource inventory is missing, unsafe or invalid.",
            [CONSTRUCTOR_RESOURCES_FILE],
        )
    admitted_resources = _resource_paths(policy, resources)
    selected = [
        name
        for name in tracked
        if exclusion_reason(name, scope, resources=admitted_resources) is None
    ]
    invalid_resources = []
    for name, spec in resources.items():
        try:
            _verify_constructor_resource(root, name, spec)
        except (OSError, ValueError):
            invalid_resources.append(name)
    if invalid_resources:
        finding(
            "constructor_resources_mismatch",
            "blocker",
            "Required constructor resources are missing, unsafe or differ from their pinned bytes.",
            invalid_resources,
        )
    missing_resources = sorted(admitted_resources - set(selected))
    if missing_resources:
        finding(
            "constructor_resources_not_selected",
            "blocker",
            "Required constructor resources must be included in the release candidate paths.",
            missing_resources,
        )
    sensitive = [name for name in tracked if sensitive_name(name)]
    if sensitive:
        finding(
            "sensitive_filenames",
            "blocker",
            "Tracked credential-like files require review; their contents were not read.",
            sensitive,
        )
    licenses = [
        name for name in LICENSE_NAMES if (root / name).is_file() and (root / name).stat().st_size
    ]
    if not licenses:
        finding("code_license_missing", "blocker", "No root source-code license file is present.")
    documentation_images = [name for name in selected if name in DOCUMENTATION_IMAGES]
    if documentation_images:
        authorized = set(policy["documentation_images"]) if policy else set()
        unapproved = [name for name in documentation_images if name not in authorized]
        if unapproved:
            finding(
                "documentation_images_not_authorized",
                "blocker",
                "Documentation screenshots require an explicit tools-only policy.",
                unapproved,
            )
        invalid = []
        for name in documentation_images:
            try:
                valid = _documentation_png(root, name)
            except OSError:
                valid = False
            if not valid:
                invalid.append(name)
        if invalid:
            finding(
                "documentation_images_invalid",
                "blocker",
                "Documentation screenshots must be regular PNG files inside the checkout.",
                invalid,
            )
    try:
        project = _metadata(root, "pyproject.toml")
        lock = _metadata(root, "uv.lock")
        package = project.get("project", {})
        source_table = project.get("tool", {}).get("uv", {}).get("sources", {})
        packages = lock.get("package", [])
        if (
            not isinstance(package, dict)
            or not isinstance(source_table, dict)
            or not isinstance(packages, list)
            or not all(isinstance(row, dict) for row in packages)
        ):
            raise ValueError("Invalid package metadata shape")
    except (OSError, ValueError, AttributeError, TypeError):
        finding(
            "package_metadata_invalid",
            "blocker",
            "Package metadata cannot be parsed.",
            ["pyproject.toml", "uv.lock"],
        )
        package, source_table, packages = {}, {}, []
    if not package.get("license"):
        finding(
            "package_license_missing",
            "blocker",
            "Python package metadata does not declare a source-code license.",
            ["pyproject.toml"],
        )
    if policy:
        missing = [
            name
            for name in policy["license_files"]
            if not (root / name).is_file() or not (root / name).stat().st_size
        ]
        if missing:
            finding(
                "policy_license_files_missing",
                "blocker",
                "The release policy's license or scope notices are missing.",
                missing,
            )
        if package.get("license") != policy["code_license"]:
            finding(
                "policy_license_mismatch",
                "blocker",
                "Package license metadata conflicts with the release policy.",
                ["pyproject.toml", "config/release_policy.json"],
            )
    sources = [
        ("pyproject.toml", str(name), value)
        for name, variants in source_table.items()
        for value in (variants if isinstance(variants, list) else [variants])
    ]
    sources += [("uv.lock", row.get("name", "unknown"), row.get("source", {})) for row in packages]
    local_dependencies = []
    for name, dependency, value in sources:
        if not isinstance(value, dict):
            continue
        location = value.get("path", value.get("editable"))
        if isinstance(location, str) and (
            Path(location).is_absolute() or not (root / location).resolve().is_relative_to(root)
        ):
            local_dependencies.append({"file": name, "dependency": dependency})
    if local_dependencies:
        finding(
            "external_local_dependencies",
            "blocker",
            "Dependency resolution requires a path outside a clean checkout.",
            sorted({row["file"] for row in local_dependencies}),
            dependencies=local_dependencies,
        )
    sizes, user_paths, credential_urls, unreadable = [], [], [], []
    for name in selected:
        if name in invalid_resources:
            continue
        path = root / name
        if not path.resolve().is_relative_to(root):
            finding(
                "external_symlink",
                "blocker",
                "A tracked symlink resolves outside the checkout.",
                [name],
            )
            continue
        if not path.is_file():
            finding(
                "tracked_file_missing",
                "blocker",
                "Tracked file is missing from this working tree.",
                [name],
            )
            continue
        size = path.stat().st_size
        sizes.append((size, name))
        if (
            sensitive_name(name)
            or sensitive_name(path.resolve().relative_to(root).as_posix())
            or path.suffix.lower() not in TEXT_SUFFIXES
            or size > 5_000_000
        ):
            continue
        try:
            for line, text in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if USER_PATH.search(text):
                    user_paths.append({"path": name, "line": line})
                if CREDENTIAL_URL.search(text):
                    credential_urls.append({"path": name, "line": line})
        except (OSError, UnicodeError):
            unreadable.append(name)
    if user_paths:
        finding(
            "absolute_user_paths",
            "warning",
            "Preserved text contains machine-specific user paths; only locations are reported.",
            sorted({row["path"] for row in user_paths}),
            locations=user_paths,
        )
    if credential_urls:
        finding(
            "credential_urls",
            "blocker",
            "Text contains URLs with embedded credentials; values are not reported.",
            sorted({row["path"] for row in credential_urls}),
            locations=credential_urls,
        )
    if unreadable:
        finding(
            "unreadable_text", "warning", "Some candidate text files were not scanned.", unreadable
        )
    large = [
        {"path": name, "size_bytes": size}
        for size, name in sorted(sizes, reverse=True)
        if size > 10 * 1024 * 1024
    ]
    if large:
        finding(
            "large_files",
            "warning",
            "Files exceed the audit's 10 MiB reporting threshold; plan the distribution size.",
            [row["path"] for row in large],
            files=large,
        )
    generated = [
        name
        for name in selected
        if any(part in CACHE_PARTS for part in PurePosixPath(name).parts)
        or PurePosixPath(name).suffix in {".pyc", ".pyo"}
        or any(within(name, prefix) for prefix in (*LOCAL_ROOTS, "artifacts"))
    ]
    if generated:
        finding(
            "local_or_review_files",
            "warning",
            "Tracked local tool configuration or historical build/review files need an explicit distribution decision.",
            generated,
        )
    content = [
        name for name in selected if _project_content(name, resources=admitted_resources)
    ]
    policy_exclusions = (
        [
            name
            for name in selected
            if exclusion_reason(name, "code", resources=admitted_resources)
        ]
        if policy
        else []
    )
    if policy_exclusions:
        finding(
            "policy_excludes_project_content",
            "blocker",
            "The tools-only distribution policy excludes this checkout's project content and archived source.",
            policy_exclusions[:30],
            file_count=len(policy_exclusions),
        )
    rights_counts = Counter()
    if content:
        try:
            rights = _rights(root)
            unresolved = []
            documentation_license_mismatches = []
            for name in content:
                matches = [
                    (len(prefix), item)
                    for item in rights
                    for prefix in item["paths"]
                    if within(name, prefix)
                ]
                item = max(matches, key=lambda pair: pair[0])[1] if matches else None
                status = item["redistribution"] if item else "uncovered"
                rights_counts[status] += 1
                if status != "approved":
                    unresolved.append(name)
                elif name in DOCUMENTATION_IMAGES and item["license"] != "Apache-2.0":
                    documentation_license_mismatches.append(name)
            if unresolved:
                finding(
                    "content_rights_unresolved",
                    "blocker",
                    "Non-code content or imported source lacks an approved scoped redistribution decision.",
                    unresolved[:30],
                    file_count=len(unresolved),
                    status_counts=dict(rights_counts),
                )
            if documentation_license_mismatches:
                finding(
                    "documentation_image_license_mismatch",
                    "blocker",
                    "The approved project documentation screenshots must use Apache-2.0.",
                    documentation_license_mismatches,
                )
        except (OSError, ValueError, TypeError):
            finding(
                "content_rights_invalid",
                "blocker",
                "The scoped rights inventory is missing or invalid.",
                ["config/release_rights.json"],
            )
    blockers = sum(row["severity"] == "blocker" for row in findings)
    return {
        "schema_version": 1,
        "scope": scope,
        "distribution": policy["distribution"]
        if policy
        else ("tools-only" if scope == "code" else "repository"),
        "policy_file": "config/release_policy.json" if policy_path.exists() else None,
        "policy_schema_version": policy["schema_version"] if policy else None,
        "policy_source_schema_version": policy["source_schema_version"] if policy else None,
        "status": "blocked" if blockers else "checks_passed",
        "publication_approved": False,
        "blocker_count": blockers,
        "inventory": {
            "candidate_files": len(tracked),
            "selected_files": len(selected),
            "selected_bytes": sum(size for size, _ in sizes),
            "excluded_prefixes": list(excluded_roots),
            "included_code_contracts": [name for name in selected if name in CODE_CONTRACTS],
            "tool_config_files": [name for name in selected if name in TOOL_CONFIG_FILES],
            "documentation_images": documentation_images,
            "constructor_resources": {
                "inventory": CONSTRUCTOR_RESOURCES_FILE
                if policy and policy["source_schema_version"] == 3
                else None,
                "file_count": len(resources),
                "selected_file_count": sum(name in resources for name in selected),
                "verified_file_count": len(resources) - len(invalid_resources),
            },
            "excluded_files": len(tracked) - len(selected),
            "largest_files": [
                {"path": name, "size_bytes": size}
                for size, name in sorted(sizes, reverse=True)[:10]
            ],
            "rights_status_counts": dict(rights_counts),
        },
        "findings": findings,
        "limitations": [
            "Current checkout paths, including non-ignored untracked files; Git history was not inspected.",
            "Credential file contents are never read; this is not a complete secret scan.",
            "License declarations and rights inventory entries require owner review; checks do not establish ownership or grant rights.",
            "Code scope applies only to a distribution that actually excludes the listed prefixes; it does not approve publishing the complete Git repository.",
            "Package installation and application behavior require separate build and runtime checks.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("code", "repository"), default="repository")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        tracked = working_tree_paths(args.root)
        report = audit(args.root, tracked, scope=args.scope)
    except (OSError, ValueError, subprocess.SubprocessError):
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "audit_failed",
                    "error": "Could not inspect the checkout.",
                }
            )
        )
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["blocker_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
