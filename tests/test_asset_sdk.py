"""Consumer-visible asset contract: files, integrity, aliases, and web integration."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from monster_forge_sdk import AssetIntegrityError, AssetNotFound, AssetStore
from monsterforge import create_app


class AssetSdkTests(unittest.TestCase):
    def test_sdk_resolves_migrated_files_and_legacy_mom_uris(self):
        store = AssetStore()
        decorations = store.list("decoration")
        self.assertEqual(len([a for a in decorations if a.id.startswith("equipment.shared.")]), 90)
        for asset in decorations:
            self.assertNotIn(".equipment.", asset.id)
            store.path(asset.id)
            if 'preview' in asset.files:
                store.path(asset.id, 'preview')
            else:
                with self.assertRaises(AssetNotFound):
                    store.path(asset.id, 'preview')
            if asset.id.startswith("equipment.shared."):
                self.assertEqual(asset.group, "Снаряжение")
            elif {"angel_arena_nova", "hearthvale"}.intersection(asset.tags):
                self.assertIn(asset.group, {"Nova", "MOM RPG"})
        self.assertTrue(store.list("icon"))
        for name in ('skull', 'ring', 'sun', 'lion', 'gladiator', 'rabbit', 'troll', 'angel', 'demon'):
            icon = store.get('icon.cosmetics.badges.' + name)
            self.assertEqual(icon.group, 'Косметика · Значки')
            self.assertEqual(store.path(icon.id).suffix, '.png')
            self.assertEqual(store.path(icon.id, 'source').suffix, '.svg')
        for row in store.catalog()["assets"]:
            for role in row["files"]:
                ref = store.file(row["id"], role)
                path = store.path(row["id"], role)
                self.assertTrue(path.is_relative_to(store.media_root))
                self.assertEqual(store.resolve_uri(ref.uri), path)
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(), ref.sha256
                )
            if row.get("source_uri"):
                self.assertEqual(
                    store.resolve_uri(row["source_uri"]), store.path(row["id"])
                )

    def test_corruption_and_escape_are_rejected_before_consumption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "media").mkdir()
            (root / "media/icon.png").write_bytes(b"original")
            ref = {
                "path": "icon.png",
                "sha256": hashlib.sha256(b"original").hexdigest(),
                "size_bytes": 8,
                "media_type": "image/png",
            }
            row = {
                "id": "test",
                "kind": "icon",
                "title": "Test",
                "revision": 1,
                "files": {"image": ref},
            }
            manifest = root / "media/catalog.json"
            manifest.write_text(json.dumps({"schema_version": 1, "assets": [row]}))
            store = AssetStore(root)
            self.assertEqual(store.read("test"), b"original")
            (root / "media/icon.png").write_bytes(b"modified")
            with self.assertRaises(AssetIntegrityError):
                store.read("test")
            with self.assertRaises(AssetIntegrityError):
                store.path("test")
            for invalid in (
                "/media/../.env",
                "/media/unknown.png",
                "/media/../../local_archive/secret.png",
            ):
                with self.assertRaises(AssetNotFound):
                    store.resolve_uri(invalid)
            ref["path"] = "../.env"
            manifest.write_text(json.dumps({"schema_version": 1, "assets": [row]}))
            with self.assertRaises(AssetIntegrityError):
                AssetStore(root)
            ref["path"] = "icon.png"
            manifest.write_text(json.dumps({"schema_version": 99, "assets": [row]}))
            with self.assertRaises(AssetIntegrityError):
                AssetStore(root)

    def test_sdk_can_be_loaded_from_explicit_asset_volume(self):
        store = AssetStore()
        with patch.dict("os.environ", {"MONSTER_FORGE_ASSET_ROOT": str(store.root)}):
            self.assertEqual(AssetStore().release_id, store.release_id)

    def test_style_preserves_exact_override_and_original_generation_prompts(self):
        store = AssetStore()
        profile = store.icon_style()
        source = json.loads((store.root / "styles/icons/prompts-mom.json").read_text())
        for atlas in source["atlases"].values():
            self.assertTrue(atlas["prompt"].startswith(profile["prompt"]))
        self.assertEqual(
            (store.root / "styles/icons/style.txt").read_text().rstrip(),
            profile["prompt"],
        )

    def test_shared_sections_http_catalog_and_actual_scene_geometry(self):
        app = create_app()
        client = app.test_client()
        for route, active in (
            ("/characters/", "characters"),
            ("/icons/", "icons"),
            ("/decorations/", "decorations"),
        ):
            response = client.get(route)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"MONSTER FORGE", response.data)
            self.assertNotIn(b"CHARACTER ATELIER", response.data)
            self.assertIn(b'aria-current="page"', response.data)
        self.assertEqual(client.get("/sdk/").status_code, 200)
        self.assertEqual(
            client.get("/api/assets/v1/catalog?kind=unknown").status_code, 400
        )
        data = client.get("/api/assets/v1/catalog?kind=decoration").json
        self.assertEqual(len(data["assets"]), len(AssetStore().list("decoration")))
        for row in data["assets"]:
            response = client.get("/media/" + row["files"]["model"]["path"])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                hashlib.sha256(response.data).hexdigest(),
                row["files"]["model"]["sha256"],
            )
            response.close()
            if 'preview' in row['files']:
                response = client.get('/media/' + row['files']['preview']['path'])
                self.assertEqual(response.status_code, 200)
                self.assertEqual(hashlib.sha256(response.data).hexdigest(),
                                 row['files']['preview']['sha256'])
                response.close()
            else:
                response = client.get('/api/assets/v1/geometry', query_string={'id': row['id']})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json['source_sha256'], row['files']['model']['sha256'])
                self.assertGreater(response.json['triangles'], 0)
        response = client.get("/api/assets/v1/geometry?id=decoration.woodland.oak")
        self.assertEqual(response.status_code, 200)
        model = response.json
        self.assertGreater(model["triangles"], 0)
        self.assertEqual(
            model["source_sha256"],
            app.extensions["asset_store"].file("decoration.woodland.oak").sha256,
        )
        for part in model["parts"].values():
            g = part["geometry"]
            self.assertEqual(len(g["positions"]), len(g["normals"]))
            self.assertEqual(len(g["positions"]), len(g["colors"]))
            self.assertEqual(len(g["uvs"]) * 3, len(g["positions"]) * 2)
        self.assertEqual(
            client.get("/media/ui/fonts/NotoSans-Regular.ttf").status_code, 404
        )
        self.assertEqual(client.get("/media/../../.env").status_code, 404)
        self.assertEqual(client.get("/styles/icons/../../.env").status_code, 404)
        self.assertEqual(client.get("/api/assets/v1/icon-style").status_code, 200)
        self.assertEqual(client.get("/creature-workshop/constructor/").status_code, 200)


if __name__ == "__main__":
    unittest.main()
