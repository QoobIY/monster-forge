"""Publish a minimap from the authored forest grid and scenery positions."""

import hashlib
import io
import json
import struct
from pathlib import Path

from PIL import Image, ImageDraw

from tools.assets.build_catalog import build_catalog

ROOT = Path(__file__).resolve().parents[2]


def publish(root=ROOT):
    stage = root.parent / "machine-of-monsters/media/maps/mom_rpg/stages/rpg_forest"
    grid = (stage / "assets/terrain/terrain.momterrain").read_bytes()
    _, width, height, _ = struct.unpack_from("<8sHHB3x", grid)
    heights = struct.unpack_from("<" + str(width * height) + "h", grid, 16)
    materials = grid[16 + width * height * 2 :]
    colors = [(112, 87, 56), (47, 64, 41), (63, 77, 43), (45, 60, 40)]
    image = Image.new("RGB", (width, height))
    for y in range(height):
        for x in range(width):
            i = y * width + x
            color = colors[materials[i]]
            shade = heights[i] * 2
            image.putpixel((x, height - 1 - y), tuple(max(0, min(255, c + shade)) for c in color))
    image = image.resize((340, 364), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(image)
    scenery = (stage / "world/decorations.json").read_bytes()
    for row in json.loads(scenery).values():
        if row["model"] not in ["forest_oak", "forest_pine"]:
            continue
        x = (row["point"][0] + 42) / 84 * 339
        y = (50 - row["point"][1]) / 90 * 363
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(30, 46, 32), outline=(56, 73, 42))
    output = io.BytesIO()
    image.save(output, format="PNG")
    payload = output.getvalue()
    folder = root / "media/maps/mom_rpg/forest/minimap/v1"
    folder.mkdir(parents=True, exist_ok=True)
    recipe = {
        "schema_version": 1,
        "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "grid_sha256": hashlib.sha256(grid).hexdigest(),
        "scenery_sha256": hashlib.sha256(scenery).hexdigest(),
        "bounds": [-42, 42, -40, 50],
        "north": "top",
        "style": "terrain-derived map diagram",
    }
    files = {}
    for role, name, data, mime in [
        ("image", "image.png", payload, "image/png"),
        (
            "recipe",
            "recipe.json",
            (json.dumps(recipe, indent=2) + "\n").encode(),
            "application/json",
        ),
    ]:
        path = folder / name
        if path.exists() and path.read_bytes() != data:
            raise ValueError("Immutable forest minimap changed")
        path.write_bytes(data)
        files[role] = {
            "path": path.relative_to(root / "media").as_posix(),
            "sha256": hashlib.sha256(data).hexdigest(),
            "size_bytes": len(data),
            "media_type": mime,
        }
    p = root / "media/imported_catalog.json"
    catalog = json.loads(p.read_text())
    identity = "map.mom_rpg.forest.minimap"
    if not any(row["id"] == identity for row in catalog["assets"]):
        catalog["assets"].append(
            {
                "id": identity,
                "kind": "terrain",
                "title": "Проклятый лес · Миникарта",
                "revision": 1,
                "group": "MOM RPG",
                "tags": ["mom_rpg", "forest", "minimap"],
                "files": files,
            }
        )
    p.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    build_catalog(root)
    print("Published terrain-derived forest minimap", flush=True)


if __name__ == "__main__":
    publish()
