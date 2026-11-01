"""Publish genuine six-faced badge dice; GLB geometry belongs to BHM."""

import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]


def publish(root=ROOT):
    media = root / "media"
    path = media / "imported_catalog.json"
    data = json.loads(path.read_text())
    known = {entry["id"]: entry for entry in data["assets"]}
    pips = {
        1: [(0, 0)],
        2: [(-0.45, -0.45), (0.45, 0.45)],
        3: [(-0.45, -0.45), (0, 0), (0.45, 0.45)],
        4: [(-0.45, -0.45), (0.45, -0.45), (-0.45, 0.45), (0.45, 0.45)],
        5: [(-0.45, -0.45), (0.45, -0.45), (-0.45, 0.45), (0.45, 0.45), (0, 0)],
        6: [(x, y) for x in (-0.45, 0.45) for y in (-0.5, 0, 0.5)],
    }
    normals = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    # Opposite faces sum to seven.
    numbers = [1, 6, 2, 5, 3, 4]
    for key, title, gold in [
        ("dice", "Вращающаяся игральная кость", False),
    ]:
        folder = media / "ui/icons/cosmetics/badges" / (key + ("_v3" if gold else "_v4"))
        folder.mkdir(parents=True, exist_ok=True)
        points, faces, colors = [], [], []
        for normal, number in zip(normals, numbers, strict=True):
            n = np.array(normal, dtype=float)
            u = np.cross(n, (0, 1, 0) if abs(n[1]) < 0.5 else (0, 0, 1))
            v = np.cross(n, u)
            # Differently shaded, bevelled faces keep the solid readable without scene lights.
            base = np.array([255, 204, 63] if gold else [40, 44, 52])
            shade = [0.88, 0.58, 0.78, 0.65, 1.0, 0.52][number - 1]
            rgba = [*np.round(base * shade).astype(int), 255]
            start = len(points)
            square = [
                n + u * x + v * y
                for x, y in [(-0.90, -0.90), (0.90, -0.90), (0.90, 0.90), (-0.90, 0.90)]
            ]
            points.extend(square)
            colors.extend([rgba] * 4)
            faces.extend([[start, start + 1, start + 2], [start, start + 2, start + 3]])
            for j in range(4):
                a, b = square[j], square[(j + 1) % 4]
                # The cube corners at ±1 produce narrow jewel-like bevels.
                outer_a = n + u * (-1 if j in (0, 3) else 1) + v * (-1 if j in (0, 1) else 1)
                outer_b = (
                    n
                    + u * (-1 if (j + 1) % 4 in (0, 3) else 1)
                    + v * (-1 if (j + 1) % 4 in (0, 1) else 1)
                )
                first = len(points)
                points.extend([a, b, outer_b, outer_a])
                colors.extend([[25, 28, 34, 255] if gold else [146, 20, 37, 255]] * 4)
                faces.extend([[first, first + 1, first + 2], [first, first + 2, first + 3]])
            for x, y in pips[number]:
                centre = n * 1.003 + u * x + v * y
                first = len(points)
                points.append(centre)
                colors.append([210, 21, 42, 255] if gold else [240, 35, 54, 255])
                for step in range(16):
                    angle = step * np.pi / 8
                    points.append(centre + 0.13 * (u * np.cos(angle) + v * np.sin(angle)))
                    colors.append([210, 21, 42, 255] if gold else [240, 35, 54, 255])
                for step in range(16):
                    faces.append([first, first + 1 + step, first + 1 + (step + 1) % 16])
        mesh = trimesh.Trimesh(
            vertices=points,
            faces=faces,
            vertex_colors=np.array(colors, dtype=np.uint8),
            process=False,
        )
        encoded = mesh.export(file_type="glb")
        model = folder / "model.glb"
        if model.exists() and model.read_bytes() != encoded:
            raise ValueError("Immutable die model differs")
        model.write_bytes(encoded)
        import cairosvg
        from build_cosmetic_icons import dice

        source = dice(gold=gold)
        if gold:
            source = source.replace("#633909", "#d2152a").replace("#192236", "#191c22")
        else:
            source = (
                source.replace("#f7fafb", "#282c34")
                .replace("#c6d4e5", "#202329")
                .replace("#8195b6", "#171b22")
                .replace("#223452", "#f02336")
                .replace("#192236", "#921425")
            )
        files = {}
        for role, filename, payload, mime in (
            (
                "image",
                "image.png",
                cairosvg.svg2png(bytestring=source.encode(), output_width=512, output_height=512),
                "image/png",
            ),
            ("source", "image.svg", source.encode(), "image/svg+xml"),
        ):
            file = folder / filename
            if file.exists() and file.read_bytes() != payload:
                raise ValueError("Immutable die thumbnail differs")
            file.write_bytes(payload)
            files[role] = {
                "path": file.relative_to(media).as_posix(),
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "media_type": mime,
            }
        files["model"] = {
            "path": model.relative_to(media).as_posix(),
            "size_bytes": len(encoded),
            "sha256": hashlib.sha256(encoded).hexdigest(),
            "media_type": "model/gltf-binary",
        }
        record = {
            "id": "icon.cosmetics.badges." + key + ("_v3" if gold else "_v4"),
            "kind": "icon",
            "title": title,
            "group": "Косметика · Объёмные значки",
            "revision": 2,
            "tags": [
                "cosmetics",
                "badges",
                "dice",
                "gold" if gold else "black-red",
                "3d",
                "animated",
            ],
            "files": files,
        }
        if record["id"] in known and known[record["id"]] != record:
            raise ValueError("Immutable die catalog differs")
        known[record["id"]] = record
    data["assets"] = list(known.values())
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    from build_catalog import build_catalog

    build_catalog(root)


if __name__ == "__main__":
    publish()
