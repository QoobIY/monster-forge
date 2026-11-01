"""Application service joining constructor policies, build ports and storage."""

from __future__ import annotations

import base64
import hashlib
import json
import tempfile
from pathlib import Path

from tools.creature_workshop.geometry import render_png

from ..assembly_repository import AssemblyRepository, assembly_files, bundle
from ..paths import DATA_DIR
from ..serialization import encoded
from . import builder
from .catalog import catalog
from .registry import ConstructorRegistry, SourceBundle, default_registry
from .settings import default_settings, validate_settings
from .sources import load_part


class ConstructorService:
    """Use one explicit registry and repository throughout an authoring request.

    renderer/source_loader are injectable adapters, useful for tools and numerical
    checks. Extensions fork the inventory; source bytes and global state stay put.
    """

    def __init__(
        self,
        registry: ConstructorRegistry | None = None,
        *,
        repository: AssemblyRepository | None = None,
        renderer=render_png,
        source_loader=None,
        build_operation=None,
    ):
        self.registry = registry or default_registry()
        self.repository = repository or AssemblyRepository(DATA_DIR / "character_constructor")
        self.renderer = renderer
        self.source_loader = source_loader or (
            lambda donor, slot: load_part(donor, slot, registry=self.registry)
        )
        self.build_operation = build_operation

    def with_source(self, source: SourceBundle) -> ConstructorService:
        return ConstructorService(
            self.registry.with_source(source), repository=self.repository, renderer=self.renderer
        )

    def default_settings(self) -> dict:
        return default_settings(registry=self.registry)

    def validate_settings(self, payload: dict) -> dict:
        return validate_settings(payload, registry=self.registry)

    def catalog(self, *, include_legacy: bool = True) -> dict:
        return catalog(registry=self.registry, include_legacy=include_legacy)

    def source_card(self, category: str, identifier: str) -> Path:
        from .cards import source_card

        return source_card(self, category, identifier)

    def build(self, payload: dict, target: Path, *, weights: bool = False) -> dict:
        if self.build_operation is not None:
            return self.build_operation(payload, target, weights=weights)
        return builder.build(
            payload,
            target,
            weights=weights,
            registry=self.registry,
            source_loader=self.source_loader,
            renderer=self.renderer,
        )

    def preview(self, payload: dict) -> dict:
        with tempfile.TemporaryDirectory(prefix="forge-constructor-") as temporary:
            root = Path(temporary)
            manifest = self.build(payload, root)
            for part in manifest["parts"].values():
                part["glb"] = base64.b64encode((root / part["model"]).read_bytes()).decode()
            return manifest

    def compact_assembly(self, payload: dict, root: Path) -> tuple[dict, bytes]:
        from ..character_assembly import bake_build, instruction

        manifest = self.build(payload, root, weights=True)
        blob = bake_build(root, manifest)
        data = instruction(self.validate_settings(payload), manifest, blob)
        data["id"] = hashlib.sha256(encoded(data)).hexdigest()
        return data, blob

    def export_bundle(self, payload: dict) -> bytes:
        with tempfile.TemporaryDirectory(prefix="forge-constructor-export-") as temporary:
            data, blob = self.compact_assembly(payload, Path(temporary))
            return bundle(assembly_files(data, blob))

    def save(self, payload: dict) -> dict:
        with tempfile.TemporaryDirectory(prefix="forge-constructor-save-") as temporary:
            data, blob = self.compact_assembly(payload, Path(temporary))
            self.repository.save(data, blob)
        return {
            "schema_version": 2,
            "id": data["id"],
            "status": "saved_local",
            "parts": len(data["parts"]),
        }

    def saved_manifest(self, identifier: str) -> dict:
        return self.repository.manifest(identifier)

    def saved_bundle(self, identifier: str) -> bytes:
        return self.repository.download(identifier)

    def saved_model(self, identifier: str) -> bytes:
        return self.repository.model(identifier)

    def saved_directory(self, identifier: str) -> Path:
        return self.repository.directory(identifier)

    def list_saved(self) -> list[dict]:
        result = []
        if not self.repository.root.is_dir():
            return result
        for folder in sorted(
            self.repository.root.iterdir(), key=lambda path: path.stat().st_mtime, reverse=True
        ):
            if not folder.is_dir() or folder.name.startswith(".pending-"):
                continue
            try:
                manifest = self.saved_manifest(folder.name)
                if manifest["schema_version"] == 2:
                    settings = self.validate_settings(manifest["constructor_settings"])
                else:
                    recipe = json.loads((folder / "parts/head/recipe.json").read_text())
                    settings = self.validate_settings(recipe["constructor"]["settings"])
                editable = self.registry.is_editable(settings)
                item = {
                    "id": folder.name,
                    "settings": settings,
                    "parts": len(manifest["parts"]),
                    "editable": editable,
                    "preview": f"/creature-workshop/constructor/revisions/{folder.name}/preview",
                }
                if not editable:
                    item["edit_error"] = (
                        "This saved race is absent from the active constructor catalog"
                    )
                result.append(item)
            except (ValueError, FileNotFoundError, KeyError) as error:
                result.append({"id": folder.name, "error": str(error)})
        return result
