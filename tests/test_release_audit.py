"""Release admission reports facts without opening secrets or approving assets."""

import base64
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.check_release import (
    CODE_CONTRACTS,
    CONSTRUCTOR_RESOURCES_FILE,
    DOCUMENTATION_IMAGES,
    TOOL_CONFIG_FILES,
    _release_policy,
    audit,
    select_paths,
)

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC"
)


class ReleaseAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.tracked = []
        # A fixture declaration is enough to test admission; it grants no project license.
        self.write("LICENSE", "Fixture license declaration")
        self.write("pyproject.toml", '[project]\nname="fixture"\nlicense="LicenseRef-Test"\n')
        self.write("example.py", "answer = 42\n")

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        self.tracked.append(name)
        return path

    def rights(self, scopes, *, version=1):
        self.write(
            "config/release_rights.json", json.dumps({"schema_version": version, "scopes": scopes})
        )

    def scope(self, prefix="media", *, status="pending", license=None, evidence=None):
        return {
            "id": prefix,
            "paths": [prefix],
            "origin": "Fixture origin",
            "license": license,
            "redistribution": status,
            "evidence": evidence or [],
        }

    def report(self, scope="repository"):
        return audit(self.root, self.tracked, scope=scope)

    def ids(self, report):
        return {row["id"] for row in report["findings"]}

    def release_policy(self, **changes):
        return {
            "schema_version": 1,
            "distribution": "tools-only",
            "code_license": "Apache-2.0",
            "license_files": ["LICENSE"],
            "asset_library_included": False,
            "git_history_included": False,
            "included_code_contracts": list(CODE_CONTRACTS),
            "tool_config_files": list(TOOL_CONFIG_FILES),
        } | changes

    def test_code_scope_excludes_content_and_never_approves_full_repository(self):
        self.write("media/image.png", "fixture")
        self.write("tools/imported_mom/upstream.py.txt", "historical source")
        self.rights([self.scope(), self.scope("tools/imported_mom")])
        code = self.report("code")
        self.assertEqual(code["status"], "checks_passed")
        self.assertFalse(code["publication_approved"])
        self.assertEqual(code["inventory"]["excluded_files"], 2)
        repository = self.report()
        self.assertIn("content_rights_unresolved", self.ids(repository))
        self.assertEqual(repository["inventory"]["rights_status_counts"], {"pending": 2})

    def test_only_exact_bhm_bind_sources_are_code_owned_media_exceptions(self):
        self.write("media/rigs/humanoid/canonical.json", "fixture contract")
        self.write("media/rigs/unreviewed.json", "unreviewed fixture")
        report = self.report("code")
        self.assertEqual(report["status"], "checks_passed")
        self.assertEqual(
            report["inventory"]["included_code_contracts"], ["media/rigs/humanoid/canonical.json"]
        )
        self.assertEqual(report["inventory"]["excluded_files"], 1)

    def test_collection_configs_and_future_configs_are_excluded_while_tool_defaults_remain(self):
        for name in (
            "config/constructor_presets/v1/example.json",
            "config/constructor_artifacts_v1.json",
            "config/constructor_reference_kits_v1.json",
            "config/future_collection.json",
        ):
            self.write(name, "unpublished asset metadata")
        self.write("config/style_profile.json", "tool defaults")
        self.write("config/humanoid_v1.json", "slot contract")
        report = self.report("code")
        self.assertEqual(report["status"], "checks_passed")
        self.assertEqual(
            set(report["inventory"]["tool_config_files"]),
            {"config/style_profile.json", "config/humanoid_v1.json"},
        )
        self.assertEqual(report["inventory"]["excluded_files"], 4)
        self.assertIn("content_rights_invalid", self.ids(self.report()))

    def test_media_and_model_files_outside_content_roots_and_dependency_caches_are_excluded(self):
        for name in (
            "image.png",
            "model.glb",
            "scene.gltf",
            "shapes/cube.obj",
            "shapes/cube.mtl",
            "sound.wav",
            "font.ttf",
            "reference.pdf",
            "bundle.zip",
            "vendor/node_modules/package/index.js",
        ):
            self.write(name, "unpublished fixture")
        report = self.report("code")
        self.assertEqual(report["status"], "checks_passed")
        self.assertEqual(report["inventory"]["selected_files"], 3)
        self.assertEqual(report["inventory"]["excluded_files"], 10)

    def test_policy_is_reported_and_cannot_widen_the_fixed_source_scope(self):
        self.write("pyproject.toml", '[project]\nlicense="Apache-2.0"\n')
        self.write("config/release_policy.json", json.dumps(self.release_policy()))
        self.assertEqual(self.report("code")["distribution"], "tools-only")
        self.assertEqual(self.report("code")["status"], "checks_passed")
        for changes in (
            {"schema_version": 99},
            {"asset_library_included": True},
            {"included_code_contracts": [*CODE_CONTRACTS, "media/private.png"]},
            {"tool_config_files": [*TOOL_CONFIG_FILES, "config/constructor_presets"]},
        ):
            with self.subTest(changes=changes):
                self.write("config/release_policy.json", json.dumps(self.release_policy(**changes)))
                self.assertIn("release_policy_invalid", self.ids(self.report("code")))

    def test_policy_license_mismatch_and_complete_repository_content_are_blocked(self):
        self.write("config/release_policy.json", json.dumps(self.release_policy()))
        self.assertIn("policy_license_mismatch", self.ids(self.report("code")))
        self.write("pyproject.toml", '[project]\nlicense="Apache-2.0"\n')
        self.write("config/constructor_presets/v1/character.json", "private character settings")
        self.assertEqual(self.report("code")["status"], "checks_passed")
        self.assertIn("policy_excludes_project_content", self.ids(self.report()))

    def test_credential_files_and_links_are_reported_without_reading_values(self):
        secret = "secret-value-that-must-not-be-read"
        self.write(".env", secret)
        self.write(".aws/credentials", secret)
        (self.root / "linked.py").symlink_to(".env")
        self.tracked.append("linked.py")
        original = Path.read_text

        def protected_read(path, *args, **kwargs):
            if path.resolve().name in {".env", "credentials"}:
                raise AssertionError("Credential content was read")
            return original(path, *args, **kwargs)

        with patch.object(Path, "read_text", protected_read):
            report = self.report()
        self.assertIn("sensitive_filenames", self.ids(report))
        self.assertNotIn(secret, json.dumps(report))

    def test_external_local_dependencies_block_clean_checkout(self):
        self.write(
            "pyproject.toml",
            '[project]\nlicense="LicenseRef-Test"\n'
            '[tool.uv.sources]\nsolver={path="../private-solver", editable=true}\n',
        )
        self.write("uv.lock", '[[package]]\nname="solver"\nsource={editable="../private-solver"}\n')
        report = self.report("code")
        row = next(row for row in report["findings"] if row["id"] == "external_local_dependencies")
        self.assertEqual(row["paths"], ["pyproject.toml", "uv.lock"])
        self.assertEqual(report["status"], "blocked")

    def test_specific_rights_decision_does_not_approve_neighboring_assets(self):
        self.write("media/approved.png", "a")
        self.write("media/pending.png", "b")
        self.rights(
            [
                self.scope(),
                self.scope(
                    "media/approved.png",
                    status="approved",
                    license="LicenseRef-Test",
                    evidence=["LICENSE"],
                ),
            ]
        )
        report = self.report()
        self.assertEqual(report["inventory"]["rights_status_counts"], {"approved": 1, "pending": 1})
        unresolved = next(
            row for row in report["findings"] if row["id"] == "content_rights_unresolved"
        )
        self.assertEqual(unresolved["paths"], ["media/pending.png"])

    def test_unsupported_or_unsubstantiated_rights_are_explicit_blockers(self):
        self.write("media/image.png", "fixture")
        for scopes, version in (
            ([self.scope()], 99),
            ([self.scope(status="approved")], 1),
            ([self.scope(), self.scope()], 1),
        ):
            with self.subTest(version=version, scopes=scopes):
                self.rights(scopes, version=version)
                self.assertIn("content_rights_invalid", self.ids(self.report()))

    def test_location_findings_never_copy_credentials_or_private_path_values(self):
        private_path = "/ho" + "me/private-person/project/file.py"
        credential = "https://" + "account:password-value@" + "example.invalid/repository"
        self.write("historical.json", json.dumps({"path": private_path, "url": credential}))
        report = self.report()
        self.assertIn("absolute_user_paths", self.ids(report))
        self.assertIn("credential_urls", self.ids(report))
        serialized = json.dumps(report)
        self.assertNotIn(private_path, serialized)
        self.assertNotIn(credential, serialized)
        self.assertNotIn("password-value", serialized)

    def test_missing_license_metadata_does_not_become_an_implicit_license(self):
        (self.root / "LICENSE").unlink()
        self.tracked.remove("LICENSE")
        self.write("pyproject.toml", '[project]\nname="fixture"\n')
        report = self.report("code")
        self.assertTrue({"code_license_missing", "package_license_missing"} <= self.ids(report))

    def test_invalid_package_metadata_shape_is_an_explicit_blocker(self):
        self.write("pyproject.toml", 'project="invalid table"\n')
        self.assertIn("package_metadata_invalid", self.ids(self.report("code")))

    def test_large_files_are_inventory_and_external_symlinks_are_blocked(self):
        image = self.write("large.bin", "")
        with image.open("r+b") as stream:
            stream.truncate(11 * 1024 * 1024)
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "unread.txt"
            target.write_text("outside data")
            (self.root / "external.txt").symlink_to(target)
            self.tracked.append("external.txt")
            report = self.report()
        self.assertTrue({"large_files", "external_symlink"} <= self.ids(report))
        self.assertEqual(report["inventory"]["largest_files"][0]["size_bytes"], 11 * 1024 * 1024)

    def documentation_fixture(
        self, *, policy_version=2, rights_status="approved", license="Apache-2.0"
    ):
        self.write("pyproject.toml", '[project]\nlicense="Apache-2.0"\n')
        for name in DOCUMENTATION_IMAGES:
            self.write(name, "").write_bytes(PNG)
        policy = self.release_policy(schema_version=policy_version)
        if policy_version == 2:
            policy["documentation_images"] = list(DOCUMENTATION_IMAGES)
        self.write("config/release_policy.json", json.dumps(policy))
        self.rights(
            [
                self.scope(name, status=rights_status, license=license, evidence=["LICENSE"])
                for name in DOCUMENTATION_IMAGES
            ]
        )
        return policy

    def test_only_two_documentation_pngs_are_policy_v2_exceptions_with_scoped_rights(self):
        self.documentation_fixture()
        neighbors = (
            "docs/images/private.png",
            "docs/images/sdk-guide.jpg",
            "docs/images/sdk-guide.pdf",
            "docs/images/library-demo.PNG",
            "docs/elsewhere/library-demo.png",
            "reference.pdf",
        )
        for name in neighbors:
            self.write(name, "excluded fixture")
        self.assertEqual(
            set(select_paths([*DOCUMENTATION_IMAGES, *neighbors])), set(DOCUMENTATION_IMAGES)
        )
        report = self.report("code")
        self.assertEqual(report["status"], "checks_passed")
        self.assertEqual(report["policy_schema_version"], 2)
        self.assertEqual(report["policy_source_schema_version"], 2)
        self.assertEqual(report["inventory"]["documentation_images"], list(DOCUMENTATION_IMAGES))
        self.assertEqual(report["inventory"]["rights_status_counts"], {"approved": 2})
        self.assertEqual(report["inventory"]["excluded_files"], len(neighbors))

    def test_v1_migration_preserves_policy_bytes_and_does_not_authorize_screenshots(self):
        self.documentation_fixture(policy_version=1)
        policy_path = self.root / "config/release_policy.json"
        original = policy_path.read_bytes()
        migrated = _release_policy(self.root)
        self.assertEqual(migrated["schema_version"], 2)
        self.assertEqual(migrated["source_schema_version"], 1)
        self.assertEqual(migrated["documentation_images"], [])
        self.assertEqual(policy_path.read_bytes(), original)
        report = self.report("code")
        self.assertIn("documentation_images_not_authorized", self.ids(report))
        self.assertEqual(report["policy_source_schema_version"], 1)
        self.write(
            "config/release_policy.json", json.dumps(self.release_policy(documentation_images=[]))
        )
        self.assertIn("release_policy_invalid", self.ids(self.report("code")))

    def test_documentation_policy_cannot_widen_paths_or_skip_rights_admission(self):
        policy = self.documentation_fixture()
        for paths in (
            [*DOCUMENTATION_IMAGES, "docs/images/private.png"],
            ["docs/images/*.png"],
            [DOCUMENTATION_IMAGES[0]],
        ):
            with self.subTest(paths=paths):
                self.write(
                    "config/release_policy.json",
                    json.dumps({**policy, "documentation_images": paths}),
                )
                self.assertIn("release_policy_invalid", self.ids(self.report("code")))
        self.write("config/release_policy.json", json.dumps(policy))
        self.rights([self.scope(name) for name in DOCUMENTATION_IMAGES])
        self.assertIn("content_rights_unresolved", self.ids(self.report("code")))
        self.rights(
            [
                self.scope(name, status="approved", license="MIT", evidence=["LICENSE"])
                for name in DOCUMENTATION_IMAGES
            ]
        )
        self.assertIn("documentation_image_license_mismatch", self.ids(self.report("code")))

    def test_documentation_png_admission_rejects_renamed_documents_and_never_opens_credentials(
        self,
    ):
        self.documentation_fixture()
        image = self.root / DOCUMENTATION_IMAGES[0]
        image.write_bytes(b"%PDF-1.4\nRenamed fixture document")
        self.assertIn("documentation_images_invalid", self.ids(self.report("code")))
        credential = self.write(".env", "credential-content-must-not-be-opened")
        image.unlink()
        image.symlink_to(credential)
        original_open = Path.open

        def protected_open(path, *args, **kwargs):
            if path.resolve() == credential:
                raise AssertionError("Credential content was opened")
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", protected_open):
            report = self.report("code")
        self.assertIn("documentation_images_invalid", self.ids(report))

    def resource_fixture(self, *, policy_version=3):
        policy = self.documentation_fixture()
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
            policy.update(schema_version=3, constructor_resources=CONSTRUCTOR_RESOURCES_FILE)
        self.write("config/release_policy.json", json.dumps(policy))
        return policy, entries

    def test_v3_admits_only_exact_pinned_constructor_inputs_without_approving_neighbors(self):
        _, entries = self.resource_fixture()
        neighbors = (
            "config/constructor_future.json",
            "config/constructor_resources_v2.json",
            "media/constructor/attribute_references/v1/hair/private.png",
            "media/constructor/library/v1/example/parts/model.glb",
        )
        for name in neighbors:
            self.write(name, "excluded fixture")
        selected = set(select_paths(self.tracked, root=self.root))
        self.assertTrue({CONSTRUCTOR_RESOURCES_FILE, *entries} <= selected)
        self.assertTrue(selected.isdisjoint(neighbors))
        self.assertNotIn(CONSTRUCTOR_RESOURCES_FILE, select_paths(self.tracked))
        report = self.report("code")
        self.assertEqual(report["status"], "checks_passed")
        self.assertEqual(report["policy_schema_version"], 3)
        self.assertEqual(report["policy_source_schema_version"], 3)
        self.assertEqual(report["inventory"]["rights_status_counts"], {"approved": 2})
        self.assertEqual(
            report["inventory"]["constructor_resources"],
            {
                "inventory": CONSTRUCTOR_RESOURCES_FILE,
                "file_count": 3,
                "selected_file_count": 3,
                "verified_file_count": 3,
            },
        )

    def test_v2_does_not_read_or_admit_a_new_resource_inventory(self):
        _, entries = self.resource_fixture(policy_version=2)
        inventory = self.root / CONSTRUCTOR_RESOURCES_FILE
        inventory.write_text("not a valid resource inventory")
        original = Path.read_bytes

        def guarded(path):
            if path == inventory:
                raise AssertionError("An older policy opened an excluded inventory")
            return original(path)

        with patch.object(Path, "read_bytes", guarded):
            selected = set(select_paths(self.tracked, root=self.root))
            report = self.report("code")
        self.assertTrue(selected.isdisjoint({CONSTRUCTOR_RESOURCES_FILE, *entries}))
        self.assertEqual(report["status"], "checks_passed")
        self.assertEqual(report["inventory"]["constructor_resources"]["file_count"], 0)

    def test_v3_policy_cannot_redirect_or_broaden_resource_admission(self):
        policy, _ = self.resource_fixture()
        for change in (
            {"constructor_resources": "config/future.json"},
            {"constructor_resources": [CONSTRUCTOR_RESOURCES_FILE]},
            {"constructor_resources": "../private.json"},
            {"tool_config_files": [*TOOL_CONFIG_FILES, CONSTRUCTOR_RESOURCES_FILE]},
            {"extra_resources": ["media/private.png"]},
        ):
            with self.subTest(change=change):
                self.write("config/release_policy.json", json.dumps(policy | change))
                self.assertIn("release_policy_invalid", self.ids(self.report("code")))
                with self.assertRaises(ValueError):
                    select_paths(self.tracked, root=self.root)

    def test_invalid_resource_metadata_and_unrelated_paths_fail_closed(self):
        _, entries = self.resource_fixture()
        name, spec = next(iter(entries.items()))
        variants = (
            {"schema_version": 99, "resources": entries},
            {"schema_version": 1, "resources": []},
            {"schema_version": 1, "resources": {name: spec | {"sha256": "bad"}}},
            {"schema_version": 1, "resources": {name: spec | {"size_bytes": True}}},
            {"schema_version": 1, "resources": {name: spec | {"classification": "recipe"}}},
            {"schema_version": 1, "resources": {"../private.json": spec}},
            {"schema_version": 1, "resources": {"README.md": spec}},
            {"schema_version": 1, "resources": {"media/constructor/private.png": spec}},
        )
        for data in variants:
            with self.subTest(data=data):
                self.write(CONSTRUCTOR_RESOURCES_FILE, json.dumps(data))
                self.assertIn("constructor_resources_invalid", self.ids(self.report("code")))
                with self.assertRaises(ValueError):
                    select_paths(self.tracked, root=self.root)

    def test_missing_size_and_same_size_hash_changes_are_explicit_blockers(self):
        _, entries = self.resource_fixture()
        name = next(name for name in entries if name.endswith(".recipe.json"))
        path = self.root / name
        original = path.read_bytes()
        for content in (b"", original.replace(b"commands", b"modified"), None):
            with self.subTest(content=content):
                if content is None:
                    path.unlink()
                else:
                    path.write_bytes(content)
                report = self.report("code")
                self.assertIn("constructor_resources_mismatch", self.ids(report))
                row = next(row for row in report["findings"] if row["id"] == "constructor_resources_mismatch")
                self.assertEqual(row["paths"], [name])
                path.write_bytes(original)

    def test_required_resource_cannot_be_silently_omitted_from_candidate_paths(self):
        _, entries = self.resource_fixture()
        name = next(iter(entries))
        self.tracked.remove(name)
        report = self.report("code")
        self.assertIn("constructor_resources_not_selected", self.ids(report))

    def test_resource_symlink_never_opens_credential_bytes(self):
        _, entries = self.resource_fixture()
        name = next(name for name in entries if name.endswith(".recipe.json"))
        path = self.root / name
        secret = self.root / ".env"
        secret.write_text("credential-bytes-must-not-be-read")
        path.unlink()
        path.symlink_to(secret)
        original = Path.open

        def guarded(candidate, *args, **kwargs):
            if candidate.resolve() == secret:
                raise AssertionError("Credential resource bytes were opened")
            return original(candidate, *args, **kwargs)

        with patch.object(Path, "open", guarded):
            report = self.report("code")
        self.assertIn("constructor_resources_mismatch", self.ids(report))
        self.assertNotIn(secret.read_text(), json.dumps(report))

    def test_resource_parent_symlink_is_rejected_even_when_it_stays_inside_checkout(self):
        _, entries = self.resource_fixture()
        name = next(name for name in entries if name.endswith(".recipe.json"))
        directory = (self.root / name).parent
        real_directory = directory.with_name("real-parts")
        directory.rename(real_directory)
        directory.symlink_to(real_directory, target_is_directory=True)
        self.assertIn("constructor_resources_mismatch", self.ids(self.report("code")))

    def test_v3_audit_runs_with_only_the_standard_library(self):
        self.resource_fixture()
        script = (
            "import json,sys; from pathlib import Path; from tools.check_release import audit; "
            "report=audit(Path(sys.argv[1]),json.loads(sys.argv[2]),scope='code'); "
            "assert not {'numpy','flask','machine_of_monsters'} & sys.modules.keys(); "
            "print(json.dumps({'status':report['status']}))"
        )
        result = subprocess.run(
            [sys.executable, "-S", "-c", script, str(self.root), json.dumps(self.tracked)],
            check=True, capture_output=True, text=True,
        )
        self.assertEqual(json.loads(result.stdout)["status"], "checks_passed")


if __name__ == "__main__":
    unittest.main()
