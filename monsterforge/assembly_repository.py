"""Immutable local assemblies, independent of geometry compilation and HTTP.

New revisions contain only assembly.json (schema 2) and model.glb. Historical
schema 1 directories remain readable without rewriting their source evidence.
"""

from __future__ import annotations

import errno
import hashlib
import io
import json
import re
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from .serialization import encoded


def bundle(files: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return stream.getvalue()


def assembly_files(instruction: dict, model: bytes) -> dict[str, bytes]:
    """Use the same representation for immediate exports and saved downloads."""
    return {"assembly.json": encoded(instruction), "model.glb": model}


def _read_record(path: Path) -> dict:
    try:
        record = json.loads(path.read_bytes())
    except ValueError as error:
        raise ValueError(f"Повреждён JSON сборки: {path.name}") from error
    if not isinstance(record, dict):
        raise ValueError(f"Ожидается объект сборки: {path.name}")  # noqa: TRY004 - schema error
    return record


def _validate_instruction(data: dict, identifier: str) -> None:
    identity = {key: value for key, value in data.items() if key != "id"}
    if data.get("id") != identifier or hashlib.sha256(encoded(identity)).hexdigest() != identifier:
        raise ValueError("Сохранённая инструкция повреждена")
    model = data.get("model")
    if (type(data.get("schema_version")) is not int or data["schema_version"] != 2
            or not isinstance(model, dict) or model.get("path") != "model.glb"
            or not isinstance(model.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", model["sha256"]) is None
            or type(model.get("size_bytes")) is not int or model["size_bytes"] < 0
            or not isinstance(data.get("parts"), dict)
            or not isinstance(data.get("constructor_settings"), dict)):
        raise ValueError("Сохранённая инструкция повреждена: неполные данные")


class AssemblyRepository:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def directory(self, identifier: str) -> Path:
        if not isinstance(identifier, str) or re.fullmatch(r"[0-9a-f]{64}", identifier) is None:
            raise ValueError("Некорректный ID ревизии")
        path = self.root / identifier
        if not path.resolve().is_relative_to(self.root):
            raise ValueError("Некорректный путь ревизии")
        return path

    def manifest(self, identifier: str) -> dict:
        root = self.directory(identifier)
        compact = root / "assembly.json"
        if compact.is_file():
            data = _read_record(compact)
            version = data.get("schema_version")
            if type(version) is not int or version not in {1, 2}:
                raise ValueError("Несовместимая сохранённая ревизия")
            if version == 2:
                _validate_instruction(data, identifier)
                return data
        manifest = _read_record(root / "manifest.json")
        if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
            raise ValueError("Несовместимая сохранённая ревизия")
        if manifest.get("id") != identifier:
            raise ValueError("ID сохранённой ревизии не совпадает")
        if not isinstance(manifest.get("parts"), dict):
            raise ValueError("Сохранённая ревизия повреждена: нет списка частей")  # noqa: TRY004 - schema error
        return manifest

    def save(self, instruction: dict, model: bytes) -> None:
        """Stage complete revisions; concurrent identical saves are idempotent."""
        target = self.directory(instruction["id"])
        _validate_instruction(instruction, instruction["id"])
        if (hashlib.sha256(model).hexdigest() != instruction["model"]["sha256"]
                or len(model) != instruction["model"]["size_bytes"]):
            raise ValueError("Сохранённая ревизия повреждена")
        expected = assembly_files(instruction, model)
        self.root.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with tempfile.TemporaryDirectory(prefix=".pending-", dir=self.root) as temporary:
                staging = Path(temporary) / "revision"
                staging.mkdir()
                for name, content in expected.items():
                    (staging / name).write_bytes(content)
                try:
                    staging.rename(target)
                except OSError as error:
                    if error.errno not in {errno.EEXIST, errno.ENOTEMPTY}:
                        raise
        actual = {
            path.relative_to(target).as_posix(): self._read_file(target, path.relative_to(target).as_posix())
            for path in target.rglob("*") if path.is_file()
        }
        if actual != expected:
            raise ValueError("Конфликт immutable-ревизии; существующие данные не изменены")

    def model(self, identifier: str) -> bytes:
        manifest = self.manifest(identifier)
        if manifest["schema_version"] != 2:
            raise ValueError("Единый model.glb требует сборку schema_version=2")
        return self._compact_files(identifier, manifest)["model.glb"]

    def download(self, identifier: str) -> bytes:
        manifest = self.manifest(identifier)
        if manifest["schema_version"] == 2:
            return bundle(self._compact_files(identifier, manifest))
        return self._legacy_bundle(identifier, manifest)

    def _compact_files(self, identifier: str, manifest: dict) -> dict[str, bytes]:
        root = self.directory(identifier)
        names = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
        if names != {"assembly.json", "model.glb"}:
            raise ValueError("Сохранённая ревизия повреждена: неполный или лишний набор файлов")
        files = {name: self._read_file(root, name) for name in ("assembly.json", "model.glb")}
        # Check the exact snapshot that will be served, including changes made
        # outside the application between manifest admission and file reads.
        if json.loads(files["assembly.json"]) != manifest:
            raise ValueError("Сохранённая инструкция повреждена: изменилась во время чтения")
        model = files["model.glb"]
        if (hashlib.sha256(model).hexdigest() != manifest["model"]["sha256"]
                or len(model) != manifest["model"]["size_bytes"]):
            raise ValueError("Сохранённая ревизия повреждена")
        return files

    @staticmethod
    def _read_file(root: Path, name: str) -> bytes:
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name or relative.as_posix() != name:
            raise ValueError("Некорректный путь файла модели")
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Некорректный путь файла модели")
        return path.read_bytes()

    def _legacy_bundle(self, identifier: str, manifest: dict) -> bytes:
        root = self.directory(identifier)
        integrity = _read_record(root / "integrity.json")
        if type(integrity.get("schema_version")) is not int or integrity["schema_version"] != 1:
            raise ValueError("Несовместимая версия проверки целостности")
        if not isinstance(integrity.get("files"), dict):
            raise ValueError("Сохранённая ревизия повреждена: нет списка файлов")  # noqa: TRY004 - schema error
        names = {"manifest.json", "assembly.json"}
        names.update(name for name in ("skeleton.json", "contract.json") if (root / name).is_file())
        for slot, part in manifest["parts"].items():
            names.update((f"parts/{slot}/recipe.json", part["model"]))
            if part.get("weights"):
                names.add(part["weights"])
        # Every exported file must have been verified, not only whatever a
        # damaged integrity record happens to enumerate.
        if not names <= integrity["files"].keys():
            raise ValueError("Сохранённая ревизия повреждена: неполная проверка целостности")
        files = {}
        for name, digest in integrity["files"].items():
            blob = self._read_file(root, name)
            if hashlib.sha256(blob).hexdigest() != digest:
                raise ValueError("Сохранённая ревизия повреждена")
            if name in names:
                files[name] = blob
        if json.loads(files["manifest.json"]) != manifest:
            raise ValueError("Сохранённая инструкция повреждена: изменилась во время чтения")
        files = {name: files[name] for name in sorted(files)}
        files["integrity.json"] = encoded({
            "schema_version": 1,
            "files": {name: hashlib.sha256(blob).hexdigest() for name, blob in files.items()},
        })
        return bundle(files)
