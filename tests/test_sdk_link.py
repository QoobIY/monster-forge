"""Import the SDK through consumer symlinks with no server or installation."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.link_sdk import ROOT, link_project


class SdkLinkTests(unittest.TestCase):
    def test_linked_consumer_imports_and_reads_assets_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            consumer = Path(tmp)
            links = link_project(consumer)
            self.assertEqual(link_project(consumer), links)
            self.assertTrue(all(p.is_symlink() for p in links))
            env = os.environ.copy()
            env.pop("MONSTER_FORGE_ASSET_ROOT", None)
            env.pop("PYTHONPATH", None)
            result = subprocess.run(
                [
                    sys.executable,
                    "-E",
                    "-c",
                    """
import socket, sys
socket.socket = lambda *a, **k: (_ for _ in ()).throw(AssertionError("Network used"))
from monster_forge_sdk import AssetStore
assets = AssetStore()
for kind in ("character", "icon", "decoration"):
    item = assets.list(kind)[0]
    assert assets.read(item.id)
    assert assets.path(item.id).is_relative_to(assets.root)
assert assets.icon_style()["prompt"]
assert "flask" not in sys.modules
assert "machine_of_monsters" not in sys.modules
print(assets.root)
""",
                ],
                cwd=consumer,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(result.stdout.strip(), str(ROOT))

    def test_conflicting_destination_is_preserved_without_partial_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            consumer = Path(tmp)
            (consumer / "monster_forge_sdk").mkdir()
            with self.assertRaises(FileExistsError):
                link_project(consumer)
            self.assertFalse((consumer / "vendor").exists())
            self.assertTrue((consumer / "monster_forge_sdk").is_dir())


if __name__ == "__main__":
    unittest.main()
