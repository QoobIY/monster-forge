"""Source export includes new code while preserving inputs and excluding secrets."""

import base64
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.check_release import (
    CODE_CONTRACTS,
    CONSTRUCTOR_RESOURCES_FILE,
    DOCUMENTATION_IMAGES,
    TOOL_CONFIG_FILES,
)
from tools.prepare_release import prepare

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC"
)


class SourceReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "checkout"
        self.root.mkdir()
        self.output = self.base / "release"
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, capture_output=True)
        self.write(".gitignore", ".env\n__pycache__/\n")
        self.write("pyproject.toml", '[project]\nname="fixture"\n')
        self.write("tracked.py", "answer = 42\n")
        self.write("media/image.png", "third party fixture image")
        self.write("tools/imported_mom/source.py.txt", "third party fixture source")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True, capture_output=True)
        self.write("untracked_new.py", "new_feature = True\n")
        self.write(".env", "credential-content-must-not-be-read")
        self.write("private.key", "private-key-fixture")
        self.write(".serena/project.yml", "local configuration")

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_draft_includes_untracked_code_and_excludes_secrets_history_and_imports(self):
        original_read = Path.read_bytes
        snapshots = {
            name: hashlib.sha256(original_read(self.root / name)).hexdigest()
            for name in ("tracked.py", "untracked_new.py", "media/image.png")
        }

        def protected_read(path):
            if path.name in {".env", "private.key"}:
                raise AssertionError("Credential content was read")
            return original_read(path)

        with patch.object(Path, "read_bytes", protected_read):
            manifest = prepare(self.root, self.output, draft=True)
        self.assertTrue(manifest["draft"])
        self.assertEqual(manifest["schema_version"], 2)
        self.assertFalse(manifest["publication_approved"])
        self.assertFalse(manifest["git_history_included"])
        self.assertFalse(manifest["license_assigned_by_exporter"])
        self.assertEqual(manifest["release_status"], "blocked")
        names = {row["path"] for row in manifest["files"]}
        self.assertTrue({"tracked.py", "untracked_new.py"} <= names)
        for name in (".git", ".env", "private.key", "media", "tools/imported_mom", ".serena"):
            self.assertFalse((self.output / name).exists(), name)
        for row in manifest["files"]:
            content = (self.output / row["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), row["sha256"])
            self.assertEqual(len(content), row["size_bytes"])
        self.assertEqual(json.loads((self.output / "release-manifest.json").read_bytes()), manifest)
        for name, digest in snapshots.items():
            self.assertEqual(hashlib.sha256((self.root / name).read_bytes()).hexdigest(), digest)
        self.assertTrue((self.root / ".git/index").is_file())
        self.assertFalse((self.root / "LICENSE").exists())

    def test_normal_export_refuses_blockers_without_leaving_output(self):
        with self.assertRaisesRegex(ValueError, "blockers"):
            prepare(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_existing_nonempty_output_is_preserved(self):
        self.output.mkdir()
        sentinel = self.output / "user-file.txt"
        sentinel.write_text("keep me")
        with self.assertRaisesRegex(ValueError, "not an empty"):
            prepare(self.root, self.output, draft=True)
        self.assertEqual(sentinel.read_text(), "keep me")

    def test_credential_symlink_is_not_materialized_under_an_innocent_name(self):
        (self.root / "alias.py").symlink_to(".env")
        with self.assertRaisesRegex(ValueError, "Unsafe source file"):
            prepare(self.root, self.output, draft=True)
        self.assertFalse(self.output.exists())

    def test_normal_export_after_explicit_fixture_license_keeps_assets_excluded(self):
        (self.root / "private.key").unlink()
        self.write("LICENSE", "Fixture license declaration")
        self.write("pyproject.toml", '[project]\nname="fixture"\nlicense="LicenseRef-Test"\n')
        self.output.mkdir()
        manifest = prepare(self.root, self.output)
        self.assertFalse(manifest["draft"])
        self.assertEqual(manifest["release_status"], "checks_passed")
        self.assertFalse(manifest["publication_approved"])
        self.assertFalse((self.output / "media").exists())
        self.assertEqual((self.output / "LICENSE").read_text(), "Fixture license declaration")

    def test_only_exact_code_owned_bind_contracts_are_exported_from_media(self):
        self.write("media/rigs/humanoid/canonical.json", "fixture contract")
        self.write("media/rigs/other.json", "unreviewed fixture")
        manifest = prepare(self.root, self.output, draft=True)
        self.assertEqual(
            manifest["included_code_contracts"], ["media/rigs/humanoid/canonical.json"]
        )
        self.assertEqual(
            (self.output / "media/rigs/humanoid/canonical.json").read_text(), "fixture contract"
        )
        self.assertFalse((self.output / "media/rigs/other.json").exists())
        self.assertFalse((self.output / "media/image.png").exists())

    def test_tools_only_export_omits_collection_presets_indices_and_unknown_config_data(self):
        private = (
            "config/constructor_presets/v1/library/character.json",
            "config/constructor_artifacts_v1.json",
            "config/constructor_reference_kits_v1.json",
            "config/future_asset_data.json",
            "tools/assetforge_generator/FACET_Forge_2_2.html",
        )
        for name in private:
            self.write(name, "project-specific fixture data")
        self.write("config/style_profile.json", "tool defaults")
        self.write("config/humanoid_v1.json", "slot contract")
        manifest = prepare(self.root, self.output, draft=True)
        self.assertEqual(manifest["distribution"], "tools-only")
        self.assertEqual(
            set(manifest["tool_config_files"]),
            {"config/style_profile.json", "config/humanoid_v1.json"},
        )
        for name in private:
            self.assertFalse((self.output / name).exists(), name)
            self.assertTrue((self.root / name).is_file(), name)
        self.assertEqual((self.output / "config/style_profile.json").read_text(), "tool defaults")

    def test_schema_two_reports_only_aggregate_exclusions_without_private_inventory(self):
        private_paths = (
            "media/private-character-example.png",
            "config/constructor_presets/v1/private-character-example.json",
        )
        for name in private_paths:
            self.write(name, "private fixture collection data")
        manifest = prepare(self.root, self.output, draft=True)
        self.assertEqual(manifest["schema_version"], 2)
        self.assertFalse(manifest["excluded_paths_included"])
        self.assertNotIn("exclusions", manifest)
        self.assertEqual(
            sum(item["file_count"] for item in manifest["exclusion_summary"]),
            manifest["excluded_file_count"],
        )
        for filename in ("release-manifest.json", "release-report.json"):
            serialized = (self.output / filename).read_text()
            self.assertNotIn("private-character-example", serialized)
        reasons = {item["reason"] for item in manifest["exclusion_summary"]}
        self.assertTrue({"excluded_scope:media", "project_asset_data"} <= reasons)

    def test_tracked_root_media_model_text_and_dependency_cache_do_not_enter_tools_export(self):
        private = (
            "root-image.png",
            "models/character.glb",
            "models/scene.gltf",
            "models/cube.obj",
            "models/cube.mtl",
            "audio.wav",
            "font.ttf",
            "reference.pdf",
            "archive.zip",
            "vendor/node_modules/package/index.js",
        )
        for name in private:
            self.write(name, "unpublished fixture")
        subprocess.run(
            ["git", "-C", str(self.root), "add", *private], check=True, capture_output=True
        )
        manifest = prepare(self.root, self.output, draft=True)
        for name in private:
            self.assertFalse((self.output / name).exists(), name)
            self.assertTrue((self.root / name).is_file(), name)
        reasons = {item["reason"] for item in manifest["exclusion_summary"]}
        self.assertTrue({"artifact_file_type", "local_cache"} <= reasons)

    def documentation_fixture(self, *, policy_version=2):
        (self.root / "private.key").unlink()
        self.write("LICENSE", "Fixture Apache scope declaration")
        self.write("pyproject.toml", '[project]\nlicense="Apache-2.0"\n')
        for name in DOCUMENTATION_IMAGES:
            self.write(name, "").write_bytes(PNG)
        policy = {
            "schema_version": policy_version,
            "distribution": "tools-only",
            "code_license": "Apache-2.0",
            "license_files": ["LICENSE"],
            "asset_library_included": False,
            "git_history_included": False,
            "included_code_contracts": list(CODE_CONTRACTS),
            "tool_config_files": list(TOOL_CONFIG_FILES),
        }
        if policy_version == 2:
            policy["documentation_images"] = list(DOCUMENTATION_IMAGES)
        self.write("config/release_policy.json", json.dumps(policy))
        self.write(
            "config/release_rights.json",
            json.dumps(
                {
                    "schema_version": 1,
                    "scopes": [
                        {
                            "id": "documentation-images",
                            "paths": list(DOCUMENTATION_IMAGES),
                            "origin": "Owned synthetic fixture",
                            "license": "Apache-2.0",
                            "redistribution": "approved",
                            "evidence": ["LICENSE"],
                        }
                    ],
                }
            ),
        )

    def test_exact_owned_documentation_screenshots_are_exported_byte_for_byte(self):
        self.documentation_fixture()
        excluded = (
            "docs/images/private.png",
            "docs/images/sdk-guide.pdf",
            "docs/reference.pdf",
            "other.png",
        )
        for name in excluded:
            self.write(name, "excluded fixture")
        manifest = prepare(self.root, self.output)
        self.assertEqual(manifest["documentation_images"], list(DOCUMENTATION_IMAGES))
        self.assertEqual(manifest["policy_schema_version"], 2)
        self.assertEqual(manifest["policy_source_schema_version"], 2)
        self.assertEqual(manifest["release_status"], "checks_passed")
        files = {item["path"]: item for item in manifest["files"]}
        for name in DOCUMENTATION_IMAGES:
            self.assertEqual((self.output / name).read_bytes(), PNG)
            self.assertEqual((self.root / name).read_bytes(), PNG)
            self.assertEqual(files[name]["sha256"], hashlib.sha256(PNG).hexdigest())
        for name in excluded:
            self.assertFalse((self.output / name).exists(), name)
        self.assertFalse((self.output / "media/image.png").exists())

    def test_legacy_policy_or_renamed_binary_cannot_publish_documentation_images(self):
        self.documentation_fixture(policy_version=1)
        with self.assertRaisesRegex(ValueError, "blockers"):
            prepare(self.root, self.output)
        self.assertFalse(self.output.exists())
        (self.root / DOCUMENTATION_IMAGES[0]).write_bytes(b"%PDF-1.4\nRenamed binary fixture")
        with self.assertRaisesRegex(ValueError, "must be a PNG"):
            prepare(self.root, self.output, draft=True)
        self.assertFalse(self.output.exists())

    def resource_fixture(self, *, policy_version=3):
        self.documentation_fixture()
        entries = {}
        for name, content, classification in (
            ("config/constructor_library_v1.json", b'{"designs": []}\n', "configuration"),
            (
                "media/constructor/library/v1/example/parts/head.recipe.json",
                b'{"commands": []}\n',
                "recipe",
            ),
            (
                "media/constructor/attribute_references/v1/hair/front.png",
                PNG,
                "reference_input",
            ),
        ):
            self.write(name, "").write_bytes(content)
            entries[name] = {
                "sha256": hashlib.sha256(content).hexdigest(),
                "size_bytes": len(content),
                "classification": classification,
            }
        self.write(
            CONSTRUCTOR_RESOURCES_FILE,
            json.dumps({"schema_version": 1, "resources": entries}),
        )
        if policy_version == 3:
            policy = json.loads((self.root / "config/release_policy.json").read_bytes())
            policy.update(schema_version=3, constructor_resources=CONSTRUCTOR_RESOURCES_FILE)
            self.write("config/release_policy.json", json.dumps(policy))
        return entries

    def test_v3_exports_pinned_constructor_inputs_and_keeps_unlisted_neighbors_excluded(self):
        entries = self.resource_fixture()
        neighbors = (
            "config/constructor_future.json",
            "config/constructor_resources_v2.json",
            "media/constructor/attribute_references/v1/hair/private.png",
            "media/constructor/library/v1/example/parts/model.glb",
        )
        for name in neighbors:
            self.write(name, "excluded fixture")
        manifest = prepare(self.root, self.output)
        self.assertEqual(manifest["release_status"], "checks_passed")
        self.assertEqual(manifest["policy_source_schema_version"], 3)
        self.assertEqual(
            manifest["constructor_resources"],
            {"inventory": CONSTRUCTOR_RESOURCES_FILE, "file_count": 3, "paths": sorted(entries)},
        )
        self.assertEqual(
            (self.output / CONSTRUCTOR_RESOURCES_FILE).read_bytes(),
            (self.root / CONSTRUCTOR_RESOURCES_FILE).read_bytes(),
        )
        files = {row["path"]: row for row in manifest["files"]}
        for name, spec in entries.items():
            self.assertEqual((self.output / name).read_bytes(), (self.root / name).read_bytes())
            self.assertEqual(files[name]["sha256"], spec["sha256"])
            self.assertEqual(files[name]["size_bytes"], spec["size_bytes"])
        for name in neighbors:
            self.assertFalse((self.output / name).exists(), name)
        self.assertFalse((self.output / "media/image.png").exists())

    def test_v2_export_does_not_read_or_admit_the_new_resource_inventory(self):
        entries = self.resource_fixture(policy_version=2)
        inventory = self.root / CONSTRUCTOR_RESOURCES_FILE
        inventory.write_text("invalid excluded inventory")
        original = Path.read_bytes

        def guarded(path):
            if path == inventory:
                raise AssertionError("Older export opened an excluded inventory")
            return original(path)

        with patch.object(Path, "read_bytes", guarded):
            manifest = prepare(self.root, self.output)
        self.assertEqual(manifest["constructor_resources"]["file_count"], 0)
        for name in {CONSTRUCTOR_RESOURCES_FILE, *entries}:
            self.assertFalse((self.output / name).exists(), name)

    def test_missing_or_tampered_resources_do_not_leave_even_a_draft_output(self):
        entries = self.resource_fixture()
        name = next(name for name in entries if name.endswith(".recipe.json"))
        path = self.root / name
        original = path.read_bytes()
        for content in (original.replace(b"commands", b"modified"), None):
            if content is None:
                path.unlink()
            else:
                path.write_bytes(content)
            for draft in (False, True):
                with self.subTest(content=content, draft=draft), self.assertRaises(ValueError):
                    prepare(self.root, self.output, draft=draft)
                self.assertFalse(self.output.exists())
            path.write_bytes(original)

    def test_resource_symlinks_are_rejected_without_opening_credentials(self):
        entries = self.resource_fixture()
        name = next(name for name in entries if name.endswith(".recipe.json"))
        path = self.root / name
        path.unlink()
        secret = self.root / ".env"
        path.symlink_to(secret)
        original = Path.open

        def guarded(candidate, *args, **kwargs):
            if candidate.resolve() == secret:
                raise AssertionError("Credential resource bytes were opened")
            return original(candidate, *args, **kwargs)

        with patch.object(Path, "open", guarded), self.assertRaises(ValueError):
            prepare(self.root, self.output, draft=True)
        self.assertFalse(self.output.exists())

    def test_resource_bytes_changed_after_audit_are_rejected_during_copy(self):
        entries = self.resource_fixture()
        name = next(name for name in entries if name.endswith(".recipe.json"))
        path = self.root / name
        original_bytes = path.read_bytes()
        original_read = Path.read_bytes

        def changed_during_copy(candidate):
            if candidate == path:
                return original_bytes.replace(b"commands", b"modified")
            return original_read(candidate)

        with patch.object(Path, "read_bytes", changed_during_copy), self.assertRaisesRegex(
            ValueError, "changed during export"
        ):
            prepare(self.root, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(path.read_bytes(), original_bytes)

    def test_invalid_v3_inventory_and_policy_never_create_output(self):
        self.resource_fixture()
        inventory = self.root / CONSTRUCTOR_RESOURCES_FILE
        inventory.write_text('{"schema_version": 99, "resources": {}}')
        with self.assertRaises(ValueError):
            prepare(self.root, self.output)
        self.assertFalse(self.output.exists())
        policy_path = self.root / "config/release_policy.json"
        policy = json.loads(policy_path.read_bytes())
        policy["constructor_resources"] = "config/any-future-inventory.json"
        policy_path.write_text(json.dumps(policy))
        with self.assertRaises(ValueError):
            prepare(self.root, self.output, draft=True)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
