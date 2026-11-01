"""Revision persistence uses tiny immutable inputs, without running the compiler."""

import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from monsterforge.assembly_repository import AssemblyRepository, assembly_files, bundle
from monsterforge.serialization import encoded


def instruction(blob=b"test model", **changes):
    record = {
        "schema_version": 2,
        "constructor_settings": {"schema_version": 5, "sources": ["original"], "hints": {"head": 1}},
        "parts": {"head": {"revision_id": "original"}},
        "model": {"path": "model.glb", "sha256": hashlib.sha256(blob).hexdigest(), "size_bytes": len(blob)},
    } | changes
    record["id"] = hashlib.sha256(encoded(record)).hexdigest()
    return record


class AssemblyRepositoryTests(unittest.TestCase):
    def test_save_and_export_share_exact_instruction_and_model_bytes(self):
        model = b"test model"
        record = instruction(model)
        with tempfile.TemporaryDirectory() as temporary:
            repository = AssemblyRepository(Path(temporary))
            repository.save(record, model)
            self.assertEqual(repository.manifest(record["id"]), record)
            self.assertEqual(repository.model(record["id"]), model)
            for archive in (repository.download(record["id"]), bundle(assembly_files(record, model))):
                with zipfile.ZipFile(io.BytesIO(archive)) as result:
                    self.assertEqual(set(result.namelist()), {"assembly.json", "model.glb"})
                    self.assertEqual(result.read("assembly.json"), encoded(record))
                    self.assertEqual(result.read("model.glb"), model)

    def test_concurrent_identical_saves_publish_one_complete_revision(self):
        record = instruction()
        with tempfile.TemporaryDirectory() as temporary:
            repository = AssemblyRepository(Path(temporary))
            with ThreadPoolExecutor(max_workers=8) as executor:
                list(executor.map(lambda _: repository.save(record, b"test model"), range(16)))
            self.assertEqual([path.name for path in repository.root.iterdir()], [record["id"]])
            self.assertEqual(repository.model(record["id"]), b"test model")

    def test_conflict_preserves_existing_revision_and_model_corruption_is_detected(self):
        record = instruction()
        with tempfile.TemporaryDirectory() as temporary:
            repository = AssemblyRepository(Path(temporary))
            repository.save(record, b"test model")
            target = repository.directory(record["id"]) / "model.glb"
            target.write_bytes(b"corrupt")
            before = (target.parent / "assembly.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "immutable"):
                repository.save(record, b"test model")
            for action in (repository.model, repository.download):
                with self.assertRaisesRegex(ValueError, "повреждена"):
                    action(record["id"])
            self.assertEqual(target.read_bytes(), b"corrupt")
            self.assertEqual((target.parent / "assembly.json").read_bytes(), before)

    def test_invalid_instruction_or_model_is_rejected_before_publication(self):
        for record in (instruction(schema_version=True), instruction(parts=[]),
                       instruction(model={"path": "model.glb", "sha256": "0" * 64, "size_bytes": 10})):
            with self.subTest(record=record), tempfile.TemporaryDirectory() as temporary:
                repository = AssemblyRepository(Path(temporary))
                with self.assertRaises(ValueError):
                    repository.save(record, b"test model")
                self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_unknown_schema_is_not_hidden_by_a_legacy_manifest(self):
        identifier = "a" * 64
        with tempfile.TemporaryDirectory() as temporary:
            repository = AssemblyRepository(Path(temporary))
            root = repository.directory(identifier)
            root.mkdir()
            (root / "manifest.json").write_bytes(encoded({"id": identifier, "schema_version": 1, "parts": {}}))
            for version in (True, 99, None):
                with self.subTest(version=version):
                    (root / "assembly.json").write_bytes(encoded({"schema_version": version}))
                    with self.assertRaisesRegex(ValueError, "Несовместимая"):
                        repository.manifest(identifier)

    def test_download_checks_the_instruction_bytes_that_will_be_exported(self):
        record = instruction()
        with tempfile.TemporaryDirectory() as temporary:
            repository = AssemblyRepository(Path(temporary))
            repository.save(record, b"test model")
            read_manifest = repository.manifest

            def change_after_admission(identifier):
                original = read_manifest(identifier)
                changed = {**original, "constructor_settings": {"schema_version": 99}}
                (repository.directory(identifier) / "assembly.json").write_bytes(encoded(changed))
                return original

            with (patch.object(repository, "manifest", side_effect=change_after_admission),
                  self.assertRaisesRegex(ValueError, "изменилась")):
                repository.download(record["id"])

    def test_legacy_download_verifies_all_exported_files_and_preserves_evidence(self):
        identifier = "a" * 64
        with tempfile.TemporaryDirectory() as temporary:
            repository = AssemblyRepository(Path(temporary))
            root = repository.directory(identifier)
            root.mkdir()
            manifest = {"id": identifier, "schema_version": 1, "parts": {
                "head": {"model": "parts/head/model.glb", "weights": "parts/head/weights.json"},
            }}
            files = {
                "assembly.json": encoded({"schema_version": 1, "id": identifier}),
                "manifest.json": encoded(manifest),
                "parts/head/recipe.json": encoded({"commands": []}),
                "parts/head/model.glb": b"old model",
                "parts/head/weights.json": encoded({"weights": [1]}),
                "parts/head/sources.json": encoded({"immutable_evidence": True}),
            }
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            integrity = {"schema_version": 1, "files": {
                name: hashlib.sha256(content).hexdigest() for name, content in files.items()
            }}
            (root / "integrity.json").write_bytes(encoded(integrity))
            with zipfile.ZipFile(io.BytesIO(repository.download(identifier))) as archive:
                self.assertNotIn("parts/head/sources.json", archive.namelist())
                self.assertEqual(archive.read("parts/head/model.glb"), b"old model")
            self.assertEqual((root / "parts/head/sources.json").read_bytes(), files["parts/head/sources.json"])
            del integrity["files"]["parts/head/model.glb"]
            (root / "integrity.json").write_bytes(encoded(integrity))
            with self.assertRaisesRegex(ValueError, "неполная проверка"):
                repository.download(identifier)

    def test_json_arrays_and_revision_path_escape_have_explicit_errors(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = AssemblyRepository(Path(temporary))
            root = repository.directory("a" * 64)
            root.mkdir()
            (root / "assembly.json").write_text(json.dumps([]))
            with self.assertRaisesRegex(ValueError, "объект"):
                repository.manifest(root.name)
            for identifier in ("../outside", None, [], "a" * 63):
                with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                    repository.manifest(identifier)


if __name__ == "__main__":
    unittest.main()
