"""Publish fantasy badge loops and aura glyphs as verified SDK icon assets.

Run with a Python environment containing cairosvg. SVG sources are retained.
"""

import colorsys
import hashlib
import json
import math
from pathlib import Path

import cairosvg

ROOT = Path(__file__).resolve().parents[2]
DARK = "#192236"


def svg(body):
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">' + body + "</svg>"


def path(d, fill, stroke=DARK, width=12):
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>'


def ellipse(x, y, rx, ry, fill, stroke=DARK, width=10):
    return f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'


def crest(night=False):
    shield = path("M256 34 L464 132 L420 318 L256 478 L92 318 L48 132 Z", "#f2b84a")
    shield += path(
        "M256 61 L433 148 L390 305 L256 438 L122 305 L79 148 Z",
        "#302941" if night else "#ae253b",
        width=8,
    )
    if night:
        shield += ellipse(256, 216, 116, 116, "#827fba", width=0)
        shield += path(
            "M94 207 L147 132 L187 199 L224 201 L237 170 L255 190 L276 170 L289 204 L330 199 L367 131 L421 208 L375 257 L337 255 L312 293 L278 284 L256 334 L233 284 L199 293 L173 256 L137 258 Z",
            "#111827",
            "#efca72",
            7,
        )
        shield += path("M248 218 L239 209 M265 218 L274 209", "none", "#8fe2ff", 7)
    else:
        shield += path(
            "M133 168 L366 168 L327 210 L247 210 L281 248 L375 249 L329 328 L183 328 L139 281 L264 281 L221 240 L135 237 Z",
            "#ffdc64",
            width=8,
        )
        shield += path(
            "M342 93 L353 119 L383 131 L353 143 L342 169 L330 143 L304 131 L330 119 Z",
            "#fff1b0",
            width=4,
        )
    return svg(shield)


def slime(t):
    jump = max(0, math.sin(t * math.tau))
    sx, sy = 1.12 - 0.23 * jump, 0.78 + 0.33 * jump
    body = ellipse(256, 427, 130 - 37 * jump, 18, "#203f43", width=0)
    body += f'<g transform="translate(256 {330 - 160 * jump}) scale({sx} {sy})">'
    body += path(
        "M-150 64 Q-159 -22 -101 -88 Q-55 -138 18 -116 Q134 -94 148 59 Q105 111 46 95 Q3 116 -44 94 Q-112 118 -150 64 Z",
        "#54de86",
        "#174c43",
        12,
    )
    body += path("M-114 12 Q-106 -66 -32 -81", "none", "#b9ffca", 19)
    for x in (-49, 50):
        body += ellipse(x, -4, 18, 26, DARK, width=0) + ellipse(
            x - 5, -12, 6, 8, "#ffffff", width=0
        )
    body += path("M-19 28 Q0 48 20 28", "none", DARK, 9)
    body += ellipse(-83, 26, 20, 9, "#ffafab", width=0) + ellipse(83, 26, 20, 9, "#ffafab", width=0)
    return svg(body + "</g>")


def frog(t):
    sway = math.sin(t * math.tau)
    rgb = colorsys.hsv_to_rgb(t, 0.60, 0.95)
    skin = "#" + "".join(f"{round(c * 255):02x}" for c in rgb)
    body = ellipse(256, 439, 133, 17, "#232937", width=0)
    body += f'<g transform="translate(256 295) rotate({sway * 12})">'
    body += path(
        f"M-65 61 L-118 104 L-170 109 L-163 139 L-66 125 L-27 80 M65 61 L118 {104 - 20 * sway} L170 {109 - 20 * sway} L163 {139 - 20 * sway} L66 125 L27 80",
        skin,
    )
    body += path(
        f"M-96 -20 L-154 {-75 - 28 * sway} L-169 {-123 - 28 * sway} M96 -20 L154 {-75 + 28 * sway} L169 {-123 + 28 * sway}",
        "none",
        DARK,
        30,
    )
    body += path(
        f"M-96 -20 L-154 {-75 - 28 * sway} L-169 {-123 - 28 * sway} M96 -20 L154 {-75 + 28 * sway} L169 {-123 + 28 * sway}",
        "none",
        skin,
        19,
    )
    body += ellipse(0, 13, 102, 111, skin)
    body += ellipse(0, 48, 65, 58, "#f4efa6", width=0)
    body += ellipse(0, -69, 132, 76, skin)
    for x in (-72, 72):
        body += ellipse(x, -124, 43, 44, skin)
        body += ellipse(x, -129, 28, 30, "#fff8d2", width=5)
        body += ellipse(x + sway * 5, -130, 10, 19, DARK, width=0)
    body += path("M-67 -55 Q0 -17 67 -55", "none", DARK, 9)
    return svg(body + "</g>")


def dice(t=0, gold=False):
    wobble = math.sin(t * math.tau)
    palette = ("#ffef9b", "#d49b28", "#a85c13") if gold else ("#f7fafb", "#c6d4e5", "#8195b6")
    body = f'<g transform="rotate({wobble * 18} 256 256)">'
    body += path("M256 57 L432 157 L256 256 L80 157 Z", palette[0])
    body += path("M80 157 L256 256 L256 455 L80 350 Z", palette[1])
    body += path("M256 256 L432 157 L432 350 L256 455 Z", palette[2])
    dots = [
        (225, 135),
        (287, 171),
        (180, 264),
        (146, 281),
        (213, 318),
        (180, 337),
        (329, 265),
        (374, 278),
        (329, 355),
    ]
    if t >= 0.5 and not gold:
        dots = [
            (256, 158),
            (151, 270),
            (206, 332),
            (317, 250),
            (382, 251),
            (349, 309),
            (316, 365),
            (383, 365),
        ]
    for x, y in dots:
        body += ellipse(x, y, 12, 9, "#633909" if gold else "#223452", width=0)
    body += "</g>"
    if gold:
        body += path(
            "M413 46 L425 80 L459 92 L425 104 L413 138 L401 104 L367 92 L401 80 Z",
            "#fff2b2",
            "#b97e22",
            5,
        )
        body += path(
            "M73 371 L80 391 L103 400 L80 409 L73 431 L65 409 L43 400 L65 391 Z",
            "#fff2b2",
            "#b97e22",
            5,
        )
    return svg(body)


def glyph(key):
    if key == "heart":
        d = "M256 450 L77 262 C-12 139 161 -10 256 140 C351 -10 524 139 435 262 Z"
    elif key == "spade":
        d = "M256 44 L423 207 C525 345 331 393 281 313 L281 381 L342 459 L170 459 L231 381 L231 313 C181 393 -13 345 89 207 Z"
    elif key == "diamond":
        d = "M256 40 L428 256 L256 472 L84 256 Z"
    elif key == "club":
        d = "M256 49 C350 49 360 165 312 191 C436 135 518 331 379 354 C321 364 286 327 281 303 L281 381 L340 459 L172 459 L231 381 L231 303 C226 327 191 364 133 354 C-6 331 76 135 200 191 C152 165 162 49 256 49 Z"
    else:
        return svg(
            path(
                "M267 407 C382 467 282 517 241 443 L204 121 C191 19 334 13 303 102 C289 147 156 205 170 303 C181 388 338 389 347 299 C355 225 232 211 218 290 C211 329 255 337 281 312",
                "none",
                "#ffffff",
                30,
            )
        )
    return svg(path(d, "#ff788f" if key in ("heart", "diamond") else "#d1edff", "#281e49", 12))


def publish(root=ROOT):
    media = root / "media"
    catalog_path = media / "imported_catalog.json"
    catalog = json.loads(catalog_path.read_text())
    records = []
    specifications = [
        ("badges", "sun_champion", "Солнечный герой", [crest()], 0),
        ("badges", "night_guard", "Ночной страж", [crest(True)], 0),
        ("badges", "slime", "Прыгающий слайм", [slime(i / 20) for i in range(20)], 20),
        ("badges", "frog", "Танцующая лягушка", [frog(i / 24) for i in range(24)], 12),
        ("badges", "dice", "Игральная кость", [dice(i / 20) for i in range(20)], 15),
        ("badges", "golden_dice", "Золотая кость", [dice(gold=True)], 0),
        *[
            ("aura_glyphs", key, key, [glyph(key)], 0)
            for key in ("heart", "spade", "diamond", "club", "treble_clef")
        ],
    ]
    for category, key, title, frames, fps in specifications:
        folder = media / "ui" / "icons" / "cosmetics" / category / key
        folder.mkdir(parents=True, exist_ok=True)
        files = {}

        def reference(role, filename, data, mime, folder=folder, files=files):
            file = folder / filename
            if file.exists() and file.read_bytes() != data:
                raise ValueError(f"Immutable published asset differs: {file}")
            file.write_bytes(data)
            files[role] = {
                "path": file.relative_to(media).as_posix(),
                "size_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "media_type": mime,
            }

        for i, frame in enumerate(frames):
            role = f"frame_{i:02}" if fps else "image"
            reference(
                role,
                role + ".png",
                cairosvg.svg2png(bytestring=frame.encode(), output_width=512, output_height=512),
                "image/png",
            )
            reference(role + "_source", role + ".svg", frame.encode(), "image/svg+xml")
        if fps:
            files["image"] = files["frame_00"]
            manifest = {
                "schema_version": 1,
                "fps": fps,
                "frame_roles": [f"frame_{i:02}" for i in range(len(frames))],
            }
            reference(
                "animation",
                "animation.json",
                (json.dumps(manifest, indent=2) + "\n").encode(),
                "application/json",
            )
        records.append(
            {
                "id": f"icon.cosmetics.{category}.{key}",
                "kind": "icon",
                "title": title,
                "group": "Косметика · " + ("Значки" if category == "badges" else "Символы аур"),
                "revision": 1,
                "tags": ["cosmetics", category, key, "animated" if fps else "static"],
                "files": files,
            }
        )
    known = {entry["id"]: entry for entry in catalog["assets"]}
    for record in records:
        if record["id"] in known and known[record["id"]] != record:
            raise ValueError(f"Immutable catalog entry differs: {record['id']}")
        known[record["id"]] = record
    catalog["assets"] = list(known.values())
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    from build_catalog import build_catalog

    build_catalog(root)
    print("Published", len(records), "icons with", sum(len(s[3]) for s in specifications), "frames")


if __name__ == "__main__":
    publish()
