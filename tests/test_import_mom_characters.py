"""Legacy source preservation and SDK publication integration."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from monster_forge_sdk import AssetStore
from monster_forge_sdk.characters import decode_skin
from tests import test_character_runtime
from tools.assets.import_mom_characters import import_characters


class CharacterImportTest(unittest.TestCase):
    def test_import_preserves_sources_and_publishes_idempotently(self):
        fixture = test_character_runtime.CharacterRuntimeTests()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, destination = root / 'mom', root / 'bhm'
            base = source / 'media/characters/character.fixture/revisions/0001'
            base.mkdir(parents=True)
            model = base / 'torso.glb'
            model.write_bytes(fixture.model_blob())
            weights = base / 'weights.json'
            payload = fixture.payload()
            payload['model_sha256'] = hashlib.sha256(model.read_bytes()).hexdigest()
            weights.write_text(json.dumps(payload))

            def reference(path):
                return {'uri': '/media/' + path.relative_to(source / 'media').as_posix(),
                        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

            (base / 'record.json').write_text(json.dumps({
                'title': 'Fixture', 'composition': {'parts': [
                    {'slot': 'torso', 'file': reference(model),
                     'weight_sidecar': reference(weights)}]}}))
            (destination / 'media').mkdir(parents=True)
            catalog = destination / 'media/imported_catalog.json'
            catalog.write_text('{"schema_version":1,"assets":[]}')
            with patch('tools.assets.import_mom_characters.CHARACTERS',
                       {'character.fixture': 'fixture'}):
                import_characters(source, destination)
                published = (destination / 'media/catalog.json').read_bytes()
                import_characters(source, destination)
                self.assertEqual(published, (destination / 'media/catalog.json').read_bytes())
                for path in base.iterdir():
                    archived = destination / 'media/imported_mom/characters' / path.relative_to(
                        source / 'media/characters')
                    self.assertEqual(path.read_bytes(), archived.read_bytes())
                store = AssetStore(destination)
                identity = 'character.maps.act_one.fixture.parts.torso'
                self.assertEqual(store.read(identity, 'model'), model.read_bytes())
                self.assertEqual(decode_skin(store.read(identity, 'weights')), payload)
                model.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'Immutable source conflict'):
                    import_characters(source, destination)
