"""License metadata and archive boundaries without building or publishing packages.

Fixtures exercise the audit in every portable run. Release jobs can additionally
set MONSTER_FORGE_TEST_WHEEL and MONSTER_FORGE_TEST_SDIST to audit real archives.
No test downloads dependencies or imports the private authoring asset library.
"""

from __future__ import annotations

import hashlib
import io
import os
import tarfile
import tempfile
import tomllib
import unittest
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath

from tools.check_release import CODE_CONTRACTS, CONTENT_ROOTS, sensitive_name, within

ROOT = Path(__file__).resolve().parents[1]
LICENSE_FILES = ("LICENSE", "NOTICE", "LICENSE_SCOPE.md")
WHEEL_CONTRACTS = {
    "monster_forge_sdk/_contracts/body_rigs.json",
    "monster_forge_sdk/_contracts/humanoid/canonical.json",
    "monster_forge_sdk/_contracts/humanoid/workshop_knees_v1.json",
}


def _metadata() -> bytes:
    return (
        "Metadata-Version: 2.4\nName: monster-forge-sdk\nVersion: 1.0\n"
        "License-Expression: Apache-2.0\n"
        + "".join(f"License-File: {name}\n" for name in LICENSE_FILES)
        + "\nFixture metadata\n"
    ).encode()


class DistributionLicenseTests(unittest.TestCase):
    def _assert_metadata(self, payload: bytes):
        metadata = BytesParser().parsebytes(payload)
        self.assertEqual(metadata["License-Expression"], "Apache-2.0")
        self.assertGreaterEqual(
            tuple(int(part) for part in metadata["Metadata-Version"].split(".")), (2, 4)
        )
        self.assertEqual(set(metadata.get_all("License-File", [])), set(LICENSE_FILES))

    def _assert_paths(self, names: list[str]):
        self.assertEqual(len(names), len(set(names)), "Archive contains duplicate entries")
        for name in names:
            path = PurePosixPath(name)
            self.assertFalse(path.is_absolute(), name)
            self.assertNotIn("..", path.parts, name)
            self.assertNotIn("\\", name)
            self.assertEqual(path.as_posix(), name, name)
            self.assertFalse(sensitive_name(name), name)
            self.assertNotIn(".git", path.parts, name)

    def _assert_wheel(self, path: Path, expected: dict[str, bytes]):
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            self._assert_paths(names)
            metadata = [name for name in names if name.endswith(".dist-info/METADATA")]
            self.assertEqual(len(metadata), 1)
            self._assert_metadata(archive.read(metadata[0]))
            dist_info = metadata[0].removesuffix("/METADATA")
            for name, payload in expected.items():
                self.assertEqual(archive.read(f"{dist_info}/licenses/{name}"), payload)
            json_files = {name for name in names if name.endswith(".json")}
            self.assertEqual(json_files, WHEEL_CONTRACTS)
            for name in names:
                if name.startswith(dist_info + "/"):
                    continue
                self.assertTrue(name.startswith("monster_forge_sdk/"), name)
                self.assertTrue(
                    name in WHEEL_CONTRACTS or name.endswith((".py", ".pyi", "/py.typed")), name
                )

    def _assert_sdist(self, path: Path, expected: dict[str, bytes]):
        with tarfile.open(path, "r:gz") as archive:
            members = archive.getmembers()
            self._assert_paths([member.name.rstrip("/") for member in members])
            self.assertTrue(
                all(member.isfile() or member.isdir() for member in members),
                "Source distributions must not materialize symlinks",
            )
            files = {member.name: member for member in members if member.isfile()}
            roots = {PurePosixPath(name).parts[0] for name in files}
            self.assertEqual(len(roots), 1)
            prefix = roots.pop() + "/"
            relative = {name.removeprefix(prefix): member for name, member in files.items()}
            for name, payload in expected.items():
                self.assertEqual(archive.extractfile(relative[name]).read(), payload)
            metadata = [
                member
                for name, member in relative.items()
                if name == "PKG-INFO" or name.endswith(".egg-info/PKG-INFO")
            ]
            self.assertTrue(metadata)
            for member in metadata:
                self._assert_metadata(archive.extractfile(member).read())
            for name in relative:
                if name in CODE_CONTRACTS:
                    continue
                self.assertFalse(any(within(name, root) for root in CONTENT_ROOTS), name)

    def _license_fixture(self):
        # These are test markers, not a substitute for the project's legal files.
        return {name: ("Fixture legal document: " + name + "\n").encode() for name in LICENSE_FILES}

    def _wheel_fixture(self, path: Path, documents: dict[str, bytes], *, extra=None):
        prefix = "monster_forge_sdk-1.0.dist-info"
        files = {"monster_forge_sdk/__init__.py": b"", f"{prefix}/METADATA": _metadata()}
        files.update({name: b"{}" for name in WHEEL_CONTRACTS})
        files.update({f"{prefix}/licenses/{name}": payload for name, payload in documents.items()})
        files.update(extra or {})
        with zipfile.ZipFile(path, "w") as archive:
            for name, payload in files.items():
                archive.writestr(name, payload)

    def _sdist_fixture(self, path: Path, documents: dict[str, bytes], *, extra=None):
        files = {**documents, "PKG-INFO": _metadata(), "monster_forge_sdk/__init__.py": b""}
        files.update({name: b"{}" for name in CODE_CONTRACTS})
        files.update(extra or {})
        with tarfile.open(path, "w:gz") as archive:
            for name, payload in files.items():
                member = tarfile.TarInfo("monster_forge_sdk-1.0/" + name)
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))

    def test_fixture_archives_preserve_license_notice_and_scope_bytes(self):
        expected = self._license_fixture()
        with tempfile.TemporaryDirectory(prefix="forge-license-fixture-") as temporary:
            root = Path(temporary)
            wheel, sdist = root / "fixture.whl", root / "fixture.tar.gz"
            self._wheel_fixture(wheel, expected)
            self._sdist_fixture(sdist, expected)
            self._assert_wheel(wheel, expected)
            self._assert_sdist(sdist, expected)

    def test_fixture_audit_rejects_missing_notice_and_asset_leakage(self):
        expected = self._license_fixture()
        with tempfile.TemporaryDirectory(prefix="forge-license-rejection-") as temporary:
            root = Path(temporary)
            wheel, sdist = root / "fixture.whl", root / "fixture.tar.gz"
            self._wheel_fixture(
                wheel, {name: payload for name, payload in expected.items() if name != "NOTICE"}
            )
            with self.assertRaises((AssertionError, KeyError)):
                self._assert_wheel(wheel, expected)
            self._sdist_fixture(
                sdist, expected, extra={"media/reference.png": b"unlicensed fixture"}
            )
            with self.assertRaises(AssertionError):
                self._assert_sdist(sdist, expected)
            self._wheel_fixture(
                wheel, expected, extra={"monster_forge_sdk/model.glb": b"asset fixture"}
            )
            with self.assertRaises(AssertionError):
                self._assert_wheel(wheel, expected)

    def test_project_declares_the_selected_license_and_all_three_legal_documents(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
        self.assertEqual(project.get("license"), "Apache-2.0")
        self.assertEqual(set(project.get("license-files", [])), set(LICENSE_FILES))
        for name in LICENSE_FILES:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_root_license_keeps_the_unmodified_official_apache_text(self):
        # Official https://www.apache.org/licenses/LICENSE-2.0.txt, checked when
        # adopting the license. Scope/attribution belong in separate documents.
        payload = (ROOT / "LICENSE").read_bytes()
        self.assertEqual(len(payload), 11358)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30",
        )

    @unittest.skipUnless(
        os.environ.get("MONSTER_FORGE_TEST_WHEEL"),
        "Set MONSTER_FORGE_TEST_WHEEL to audit a built wheel",
    )
    def test_built_wheel_contains_exact_legal_documents_and_only_sdk_code_contracts(self):
        expected = {name: (ROOT / name).read_bytes() for name in LICENSE_FILES}
        self._assert_wheel(Path(os.environ["MONSTER_FORGE_TEST_WHEEL"]), expected)

    @unittest.skipUnless(
        os.environ.get("MONSTER_FORGE_TEST_SDIST"),
        "Set MONSTER_FORGE_TEST_SDIST to audit a built source distribution",
    )
    def test_built_source_distribution_contains_exact_legal_documents_without_asset_libraries(self):
        expected = {name: (ROOT / name).read_bytes() for name in LICENSE_FILES}
        self._assert_sdist(Path(os.environ["MONSTER_FORGE_TEST_SDIST"]), expected)
