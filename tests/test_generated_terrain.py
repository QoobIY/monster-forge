"""Versioned terrain publication preserves pixels and prior releases."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from monster_forge_sdk import AssetStore
from tools.assets import publish_generated_terrain as publisher


class GeneratedTerrainTests(unittest.TestCase):
    def test_versioned_pixels_and_immutable_republication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/'media').mkdir()
            (root/'media/imported_catalog.json').write_text('{"schema_version":1,"assets":[]}')
            source=root/'source.png'
            Image.new('RGB',(1024,1024),(80,110,70)).save(source)
            manifest=root/'manifest.json'
            rows=[{'id':'meadow','path':str(source),'prompt':'Crisp broad grass planes'}]
            manifest.write_text(json.dumps(rows))
            with patch.object(publisher,'ROOT',root):
                publisher.publish(manifest)
                old=(root/'media/terrain/v2/meadow/recipe.json').read_bytes()
                publisher.publish(manifest,version='v3')
                store=AssetStore(root)
                self.assertEqual(store.read('terrain.v3.meadow','image'),source.read_bytes())
                self.assertEqual(store.read('terrain.v2.meadow','image'),source.read_bytes())
                self.assertEqual((root/'media/terrain/v2/meadow/recipe.json').read_bytes(),old)
                publisher.publish(manifest,version='v3')
                rows[0]['prompt']='Different recipe'
                manifest.write_text(json.dumps(rows))
                with self.assertRaisesRegex(ValueError,'immutable'):
                    publisher.publish(manifest,version='v3')
                with self.assertRaisesRegex(ValueError,'Invalid terrain version'):
                    publisher.publish(manifest,version='../escape')
