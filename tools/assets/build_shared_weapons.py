"""Publish shared, metre-scale weapons with authored grip and projectile sockets.

Each theme changes construction and silhouette as well as its palette. Sources
are deterministic BHM geometry, never runtime meshes or map-specific branches.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

import numpy as np
import trimesh

from tools.assets.asset_policy import canonical_entry
from tools.assets.build_mom_rpg_architecture import Architecture

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Theme:
    label: str
    surface: tuple
    edge: tuple
    shaft: tuple
    accent: tuple
    flare: float
    bend: float


THEMES = {
    "skeletal": Theme(
        "Скелеты",
        (181, 174, 144, 255),
        (224, 215, 177, 255),
        (82, 72, 59, 255),
        (63, 130, 111, 255),
        0.13,
        -0.035,
    ),
    "swamp": Theme(
        "Болото",
        (91, 115, 75, 255),
        (157, 163, 107, 255),
        (66, 58, 39, 255),
        (156, 175, 73, 255),
        0.11,
        0.10,
    ),
    "cursed": Theme(
        "Проклятые земли",
        (86, 84, 91, 255),
        (149, 146, 143, 255),
        (67, 50, 48, 255),
        (159, 81, 115, 255),
        0.07,
        -0.11,
    ),
    "demonic": Theme(
        "Демоны",
        (67, 52, 59, 255),
        (139, 106, 96, 255),
        (49, 37, 41, 255),
        (204, 77, 43, 255),
        0.18,
        0.10,
    ),
    "spectral": Theme(
        "Призраки",
        (88, 145, 143, 255),
        (164, 210, 193, 255),
        (46, 76, 88, 255),
        (111, 190, 184, 255),
        0.08,
        -0.12,
    ),
    "fire": Theme(
        "Огонь",
        (81, 62, 54, 255),
        (158, 124, 89, 255),
        (48, 42, 40, 255),
        (232, 121, 44, 255),
        0.15,
        0.06,
    ),
    "woodland": Theme(
        "Живое дерево",
        (123, 98, 57, 255),
        (184, 159, 99, 255),
        (74, 63, 41, 255),
        (97, 142, 72, 255),
        0.12,
        0.12,
    ),
    "crystal": Theme(
        "Кристаллы",
        (79, 122, 163, 255),
        (150, 196, 214, 255),
        (53, 67, 89, 255),
        (164, 138, 197, 255),
        0.19,
        -0.025,
    ),
    "dark": Theme(
        "Тьма",
        (55, 54, 72, 255),
        (124, 121, 149, 255),
        (39, 36, 49, 255),
        (131, 92, 167, 255),
        0.055,
        -0.17,
    ),
    "gladiator": Theme(
        "Гладиаторы",
        (145, 131, 98, 255),
        (208, 183, 122, 255),
        (87, 45, 42, 255),
        (165, 62, 48, 255),
        0.05,
        0.025,
    ),
}
TYPES = {
    "sword": "Одноручный меч",
    "greatsword": "Двуручный меч",
    "bow": "Лук",
    "mace": "Булава",
    "axe": "Топор",
    "scythe": "Коса",
    "staff": "Посох",
    "claws": "Когти",
    "book": "Книга",
}


def color_scale(color, value):
    return tuple(min(255, round(c * value)) for c in color[:3]) + (255,)


class Weapon(Architecture):
    def __init__(self, theme: str):
        super().__init__()
        self.theme = theme
        self.t = THEMES[theme]
        self.sockets = {"grip_primary": [0.0, 0.0, 0.0]}

    def rod(self, start, end, radius, color, sections=8):
        a, b = np.asarray(start, float), np.asarray(end, float)
        direction = b - a
        mesh = trimesh.creation.cylinder(radius, np.linalg.norm(direction), sections=sections)
        mesh.apply_transform(trimesh.geometry.align_vectors((0, 0, 1), direction))
        self.add(mesh, color, (a + b) / 2)

    def prism(self, points, depth, color, ridge=0.025, z=0):
        # Concave outlines (guards, hooks, teeth) need actual triangulation.
        # A centroid fan folds across indentations and destroys the silhouette.
        points = np.asarray(points, float)
        center = points.mean(axis=0)
        inner = center + (points - center) * 0.88
        n = len(points)

        def cross(a, b, c):
            u, v = b - a, c - a
            return u[0] * v[1] - u[1] * v[0]

        signed = sum(cross(np.zeros(2), points[i], points[(i + 1) % n]) for i in range(n))
        order = list(range(n)) if signed > 0 else list(reversed(range(n)))
        triangles = []
        while len(order) > 3:
            found = False
            for i, current in enumerate(order):
                previous, following = order[i - 1], order[(i + 1) % len(order)]
                a, b, c = points[[previous, current, following]]
                if cross(a, b, c) <= 1e-10:
                    continue
                if any(
                    cross(a, b, points[k]) >= -1e-10
                    and cross(b, c, points[k]) >= -1e-10
                    and cross(c, a, points[k]) >= -1e-10
                    for k in order
                    if k not in (previous, current, following)
                ):
                    continue
                triangles.append((previous, current, following))
                order.pop(i)
                found = True
                break
            if not found:
                raise ValueError("Weapon outline is self-intersecting")
        triangles.append(tuple(order))
        vertices = [(x, y, 0) for x, y in points]
        vertices += [(x, y, depth / 2 + ridge * 0.35) for x, y in inner]
        vertices += [(x, y, -depth / 2 - ridge * 0.35) for x, y in inner]
        faces = []
        for i in range(n):
            j = (i + 1) % n
            faces += [
                (i, j, n + j),
                (i, n + j, n + i),
                (j, i, 2 * n + i),
                (j, 2 * n + i, 2 * n + j),
            ]
        bevel_faces = len(faces)
        for a, b, c in triangles:
            faces += [(n + a, n + b, n + c), (2 * n + c, 2 * n + b, 2 * n + a)]
        mesh = trimesh.Trimesh(vertices, faces, process=False)
        mesh.fix_normals()
        self.add(mesh, color, (0, 0, z))
        face_colors = np.tile(np.asarray(color, dtype=np.uint8), (len(faces), 1))
        face_colors[:bevel_faces] = color_scale(color, 1.16)
        mesh.visual.face_colors = face_colors

    def shard(self, position, length, radius, color=None, tilt=0):
        mesh = trimesh.creation.cone(radius, length, sections=5)
        mesh.apply_translation((0, 0, -length * 0.24))
        mesh.apply_transform(trimesh.transformations.rotation_matrix(-math.pi / 2, (1, 0, 0)))
        mesh.apply_transform(trimesh.transformations.rotation_matrix(tilt, (0, 0, 1)))
        self.add(mesh, color or self.t.edge, position)

    def skull(self, position, scale=0.16):
        x, y, z = position
        self.gem(scale, (x, y, z), self.t.edge, (1.0, 1.14, 0.7))
        self.block(
            (scale * 1.2, scale * 0.7, scale * 0.8),
            (x, y - scale * 0.9, z),
            self.t.surface,
            bevel=scale * 0.1,
        )
        # Broad inset-looking eyes, rather than noisy teeth/face meshes.
        for sign in (-1, 1):
            self.gem(
                scale * 0.29,
                (x + sign * scale * 0.4, y + scale * 0.05, z + scale * 0.62),
                self.t.shaft,
                (1, 0.7, 0.35),
            )

    def motif(self, position, size=0.13):
        x, y, z = position

        def plate(points, depth, color, ridge=0.025):
            self.prism(points, depth, color, ridge, z=z + size * 0.45)

        if self.theme == "skeletal":
            self.skull(position, size)
        elif self.theme in ("swamp", "woodland"):
            for sign in (-1, 1):
                self.rod(
                    (x, y - size * 0.5, z),
                    (x + sign * size * 1.1, y + size, z),
                    size * 0.15,
                    self.t.shaft,
                    6,
                )
                self.gem(
                    size,
                    (x + sign * size, y + size * 0.5, z + 0.02),
                    self.t.accent,
                    (0.45, 1.4, 0.25),
                )
            self.gem(size * 0.65, (x, y, z), self.t.edge, (0.55, 1.1, 0.6))
        elif self.theme == "demonic":
            for sign in (-1, 1):
                self.rod(
                    (x + sign * size * 0.5, y, z),
                    (x + sign * size * 1.2, y + size * 0.6, z),
                    size * 0.32,
                    self.t.shaft,
                    6,
                )
                self.shard(
                    (x + sign * size * 1.2, y + size * 0.6, z),
                    size * 1.9,
                    size * 0.34,
                    tilt=-sign * 0.4,
                )
            self.gem(size * 0.75, position, self.t.accent, (0.8, 1.3, 0.5))
        elif self.theme == "crystal":
            for dx, tilt, length in [(-0.8, 0.55, 1.7), (0, 0, 2.7), (0.7, -0.6, 1.9)]:
                self.shard(
                    (x + dx * size, y, z),
                    size * length,
                    size * 0.44,
                    self.t.accent if dx else self.t.edge,
                    tilt,
                )
        elif self.theme == "fire":
            self.gem(size, position, self.t.shaft, (1, 1.3, 0.5))
            for dx, tilt in [(-0.55, -0.15), (0, 0.2), (0.5, -0.4)]:
                plate(
                    [
                        (x + dx * size - size * 0.25, y - size * 0.5),
                        (x + dx * size + size * 0.3, y - size * 0.2),
                        (x + dx * size + size * 0.15, y + size * (1.5 + tilt)),
                        (x + dx * size - size * 0.25, y + size * 0.5),
                    ],
                    size * 0.55,
                    self.t.accent,
                    0,
                )
        elif self.theme in ("dark", "spectral"):
            self.gem(size * 1.25, position, self.t.shaft, (1.15, 1.4, 0.3))
            self.gem(size * 0.8, (x, y, z + size * 0.4), self.t.accent, (0.6, 1.1, 0.3))
            for sign in (-1, 1):
                plate(
                    [
                        (x + sign * size * 0.7, y - size),
                        (x + sign * size * 1.5, y + size * 0.2),
                        (x + sign * size * 0.65, y + size * 1.2),
                    ],
                    size * 0.4,
                    self.t.edge,
                    0,
                )
        elif self.theme == "cursed":
            self.block(
                (size * 1.3, size * 1.7, size * 0.7), position, self.t.shaft, bevel=size * 0.1
            )
            plate(
                [
                    (x - size * 0.5, y - size * 0.5),
                    (x, y),
                    (x - size * 0.2, y + size * 0.7),
                    (x + size * 0.4, y + size * 0.25),
                    (x + size * 0.2, y - size * 0.8),
                ],
                size * 0.85,
                self.t.accent,
                0,
            )
        else:
            self.gem(size, position, self.t.edge, (1.2, 1.4, 0.5))
            for sign in (-1, 1):
                plate(
                    [
                        (x + sign * size * 0.6, y - size * 0.3),
                        (x + sign * size * 1.4, y + size),
                        (x + sign * size * 0.6, y + size * 0.7),
                    ],
                    size * 0.4,
                    self.t.accent,
                    0,
                )

    def handle(self, low, high, radius=0.055):
        # Metre-scale grip length is independent of the weapon's head geometry.
        self.cylinder(radius, high - low, (0, (low + high) / 2, 0), self.t.shaft, 8)
        for y in np.linspace(low + 0.025, high - 0.025, max(2, round((high - low) / 0.09))):
            self.cylinder(radius * 1.07, 0.018, (0, y, 0), color_scale(self.t.shaft, 1.3), 8)
        for y in (low, high):
            self.cylinder(radius * 1.28, 0.045, (0, y, 0), self.t.edge, 8)

    def shaft(self, low, high, radius=0.045):
        if self.theme in ("woodland", "swamp", "skeletal"):
            n = 7
            points = [
                (
                    math.sin(i * 1.7) * (0.024 if self.theme == "skeletal" else 0.045),
                    low + (high - low) * i / n,
                    0,
                )
                for i in range(n + 1)
            ]
            for a, b in pairwise(points):
                self.rod(
                    a, b, radius, self.t.surface if self.theme == "skeletal" else self.t.shaft, 7
                )
            for i in (2, 4, 6):
                x, y, z = points[i]
                if self.theme == "skeletal":
                    self.gem(radius * 1.5, (x, y, z), self.t.edge, (1.2, 0.8, 1.1))
                else:
                    self.rod((x, y, 0), (x + 0.13, y + 0.19, 0), radius * 0.5, self.t.shaft, 6)
                    self.gem(0.09, (x + 0.13, y + 0.2, 0), self.t.accent, (0.5, 1.4, 0.25))
        else:
            self.cylinder(radius, high - low, (0, (high + low) / 2, 0), self.t.shaft, 8)
            for y in (low, high, (low + high) / 2):
                self.cylinder(radius * 1.35, 0.055, (0, y, 0), self.t.edge, 8)

    def guard(self, y, width):
        t = self.t
        shape = [
            (-width * 0.55, y + 0.12 + t.flare),
            (-width * 0.48, y - 0.06),
            (-0.11, y - 0.04),
            (0, y - 0.11),
            (0.11, y - 0.04),
            (width * 0.48, y - 0.06),
            (width * 0.55, y + 0.12 + t.flare),
            (width * 0.37, y + 0.065),
            (0.10, y + 0.06),
            (-0.10, y + 0.06),
            (-width * 0.37, y + 0.065),
        ]
        if self.theme == "gladiator":
            shape = [
                (-width * 0.5, y + 0.04),
                (-width * 0.5, y - 0.07),
                (width * 0.5, y - 0.07),
                (width * 0.5, y + 0.04),
            ]
        self.prism(shape, 0.10, t.surface)
        self.motif((0, y + 0.04, 0.075), 0.075)

    def blade(self, low, length, width):
        # Main silhouette families: bone teeth, livewood curve, obsidian barbs,
        # broken-edged cursed iron and broad faceted crystal all differ in mesh.
        t = self.t
        bend = t.bend * length
        left = [(-width * 0.48, low), (-width * 0.52, low + length * 0.20)]
        right = [(width * 0.48, low), (width * 0.52, low + length * 0.20)]
        if self.theme in ("skeletal", "demonic", "cursed", "fire"):
            for f in (0.34, 0.52, 0.70):
                barb = (0.22 if self.theme == "demonic" else 0.14) * width
                left += [
                    (-width * 0.45 + bend * f, low + length * f),
                    (-width * 0.45 - barb + bend * f, low + length * (f + 0.035)),
                    (-width * 0.4 + bend * f, low + length * (f + 0.10)),
                ]
                right += [
                    (width * 0.45 + bend * f, low + length * f),
                    (width * 0.45 + barb + bend * f, low + length * (f + 0.035)),
                    (width * 0.4 + bend * f, low + length * (f + 0.10)),
                ]
        elif self.theme in ("swamp", "woodland", "dark", "spectral"):
            left += [
                (-width * 0.46 + bend * 0.5, low + length * 0.5),
                (-width * 0.29 + bend * 0.8, low + length * 0.82),
            ]
            right += [
                (width * 0.48 + bend * 0.6, low + length * 0.53),
                (width * 0.26 + bend * 0.8, low + length * 0.84),
            ]
        else:
            left += [
                (
                    -width * (0.63 if self.theme == "crystal" else 0.44) + bend * 0.6,
                    low + length * 0.65,
                ),
                (-width * 0.27 + bend * 0.8, low + length * 0.84),
            ]
            right += [
                (
                    width * (0.63 if self.theme == "crystal" else 0.44) + bend * 0.6,
                    low + length * 0.65,
                ),
                (width * 0.27 + bend * 0.8, low + length * 0.84),
            ]
        self.prism(
            left + [(bend, low + length)] + list(reversed(right)),
            0.07 if self.theme != "crystal" else 0.13,
            t.surface,
        )
        if self.theme in ("fire", "cursed", "dark", "spectral"):
            self.prism(
                [
                    (-0.025, low + 0.05),
                    (0.027, low + 0.05),
                    (bend * 0.52 + 0.026, low + length * 0.50),
                    (bend * 0.79, low + length * 0.83),
                    (bend * 0.52 - 0.025, low + length * 0.48),
                ],
                0.12,
                t.accent,
                0,
            )
        elif self.theme in ("woodland", "swamp", "skeletal"):
            for sign in (-1, 1):
                self.rod(
                    (0, low + length * 0.2, 0.05),
                    (sign * width * 0.27 + bend * 0.5, low + length * 0.57, 0.05),
                    0.015,
                    t.edge,
                    5,
                )

    def sword(self, two=False):
        self.handle(-0.16, 0.25 if two else 0.13)
        self.guard(0.29 if two else 0.17, 0.65 if two else 0.49)
        self.blade(0.33 if two else 0.21, 1.32 if two else 0.93, 0.245 if two else 0.19)
        self.motif((0, -0.22, 0), 0.085)
        if two:
            self.sockets["grip_secondary"] = [0.0, 0.20, 0.0]

    def axe(self):
        self.shaft(-0.18, 0.96, 0.048)
        self.handle(-0.14, 0.12)
        t = self.t
        for sign in (-1, 1) if self.theme in ("demonic", "gladiator", "crystal") else (1,):
            points = [
                (0.02, 0.69),
                (0.25, 0.70),
                (0.40, 0.56),
                (0.53, 0.69),
                (0.51, 1.02),
                (0.37, 1.14),
                (0.24, 0.97),
                (0.025, 0.97),
            ]
            if self.theme in ("woodland", "swamp"):
                points = [
                    (0.01, 0.72),
                    (0.22, 0.66),
                    (0.40, 0.73),
                    (0.46, 0.96),
                    (0.30, 1.09),
                    (0.13, 0.93),
                    (0.01, 0.94),
                ]
            self.prism([(sign * x, y) for x, y in points], 0.12, t.surface)
            if self.theme in ("fire", "cursed", "spectral", "dark"):
                self.rod((sign * 0.18, 0.77, 0.09), (sign * 0.35, 0.91, 0.09), 0.018, t.accent, 6)
        self.cylinder(0.083, 0.25, (0, 0.84, 0), t.edge, 8)
        self.motif((0, 1.01, 0.09), 0.10)

    def mace(self):
        t = self.t
        self.shaft(-0.16, 0.66)
        self.handle(-0.14, 0.12)
        self.cylinder(0.11, 0.42, (0, 0.84, 0), t.surface, 8)
        for i in range(6):
            angle = i * math.pi / 3
            if self.theme == "crystal":
                mesh = trimesh.creation.cone(0.095, 0.43, sections=5)
                mesh.apply_transform(
                    trimesh.geometry.align_vectors(
                        (0, 0, 1), (math.cos(angle), 0.45, math.sin(angle))
                    )
                )
                self.add(mesh, t.edge, (math.cos(angle) * 0.12, 0.85, math.sin(angle) * 0.12))
            else:
                points = [(0.08, 0.64), (0.20, 0.67), (0.28, 0.82), (0.22, 1.06), (0.08, 1.09)]
                # Radial flanges give the mace a distinct physical striking head.
                before = len(self.meshes)
                self.prism(points, 0.065, t.surface)
                for mesh in self.meshes[before:]:
                    mesh.apply_transform(trimesh.transformations.rotation_matrix(angle, (0, 1, 0)))
        for y in (0.66, 1.045):
            self.cylinder(0.15, 0.055, (0, y, 0), t.edge, 10)
        self.motif((0, 1.16, 0), 0.10)
        if self.theme == "skeletal":
            self.skull((0, 0.89, 0.16), 0.14)

    def scythe(self):
        t = self.t
        self.shaft(-0.48, 1.28, 0.048)
        self.handle(-0.13, 0.13)
        self.sockets["grip_secondary"] = [0.0, 0.43, 0.0]
        self.rod((0, 0.35, 0), (-0.19, 0.30, 0.04), 0.05, t.shaft)
        self.prism(
            [
                (-0.075, 1.15),
                (0.18, 1.18),
                (0.47, 1.12),
                (0.74, 0.99),
                (0.94, 0.74),
                (0.80, 1.15),
                (0.54, 1.37),
                (0.20, 1.44),
                (-0.08, 1.34),
            ],
            0.085,
            t.surface,
        )
        self.prism(
            [(0.16, 1.23), (0.42, 1.18), (0.71, 1.04), (0.50, 1.30), (0.18, 1.37)], 0.12, t.edge, 0
        )
        if self.theme in ("fire", "cursed", "dark", "spectral"):
            self.rod((0.20, 1.30, 0.075), (0.50, 1.21, 0.075), 0.02, t.accent, 6)
        self.motif((-0.015, 1.36, 0.05), 0.13)

    def staff(self):
        t = self.t
        self.shaft(-0.65, 1.05, 0.046)
        self.handle(-0.13, 0.13)
        self.sockets["grip_secondary"] = [0.0, 0.36, 0.0]
        for sign in (-1, 1):
            self.prism(
                [
                    (sign * 0.04, 0.91),
                    (sign * 0.22, 1.05),
                    (sign * 0.27, 1.38),
                    (sign * 0.13, 1.24),
                    (sign * 0.10, 1.04),
                ],
                0.08,
                t.surface,
            )
        if self.theme == "skeletal":
            self.skull((0, 1.27, 0), 0.19)
        elif self.theme in ("woodland", "swamp"):
            self.motif((0, 1.20, 0), 0.23)
        else:
            self.motif((0, 1.27, 0), 0.18)
        self.gem(0.10, (0, -0.70, 0), t.edge, (0.6, 1.3, 0.6))
        self.sockets["projectile_socket"] = [0.0, 1.34, 0.0]

    def bow(self):
        t = self.t
        self.handle(-0.12, 0.12, 0.05)
        for sign in (-1, 1):
            points = [
                (0, sign * 0.12, 0),
                (0.09, sign * 0.29, 0),
                (0.22, sign * 0.52, 0),
                (0.23, sign * 0.72, 0),
                (0.11, sign * 0.91, 0),
                (-0.03, sign * 1.02, 0),
            ]
            for i, (a, b) in enumerate(pairwise(points)):
                self.rod(a, b, 0.060 - i * 0.007, t.surface, 8)
            self.rod((-0.03, sign * 1.02, 0), (-0.10, 0, 0), 0.007, t.edge, 5)
            if self.theme in ("skeletal", "demonic", "cursed", "fire", "crystal"):
                for y in (0.42, 0.70):
                    self.shard((0.24, sign * y, 0), 0.16, 0.047, t.edge, -sign * 1.1)
            elif self.theme in ("woodland", "swamp"):
                self.gem(0.13, (0.24, sign * 0.55, 0), t.accent, (0.6, 1.6, 0.3))
            else:
                self.prism(
                    [(0.15, sign * 0.44), (0.31, sign * 0.62), (0.18, sign * 0.76)], 0.085, t.edge
                )
        self.motif((0.085, 0, 0.04), 0.09)
        self.sockets["string_nock"] = [-0.10, 0.0, 0.0]
        self.sockets["projectile_socket"] = [-0.10, 0.0, 0.0]

    def claws(self):
        t = self.t
        # Palm bar and wrist cuff stay behind three deliberately curved talons.
        self.rod((-0.15, 0, 0), (0.15, 0, 0), 0.046, t.shaft)
        self.block((0.34, 0.18, 0.10), (0, 0.11, 0), t.surface, 0.025)
        self.block((0.30, 0.10, 0.075), (0, -0.14, 0), t.shaft, 0.015)
        for i, x in enumerate((-0.13, 0, 0.13)):
            length = 0.57 if i == 1 else 0.48
            bend = 0.10 if self.theme not in ("crystal", "gladiator") else 0.035
            points = [
                (x - 0.038, 0.16),
                (x - 0.045, 0.34),
                (x + bend, length + 0.20),
                (x + 0.05, 0.43),
                (x + 0.045, 0.16),
            ]
            self.prism(points, 0.055, t.edge)
        for sign in (-1, 1):
            self.block((0.045, 0.30, 0.06), (sign * 0.145, -0.025, -0.045), t.surface, 0.008)
        self.motif((0, 0.16, 0.08), 0.07)

    def book(self):
        t = self.t
        # Two covers, page blocks, central binding, four large corner fittings.
        for sign in (-1, 1):
            mesh = trimesh.creation.box((0.265, 0.43, 0.045))
            mesh.apply_transform(trimesh.transformations.rotation_matrix(sign * 0.18, (0, 1, 0)))
            self.add(mesh, t.shaft, (sign * 0.14, 0.17, -0.025))
            mesh = trimesh.creation.box((0.235, 0.39, 0.035))
            mesh.apply_transform(trimesh.transformations.rotation_matrix(sign * 0.18, (0, 1, 0)))
            self.add(mesh, (201, 192, 158, 255), (sign * 0.14, 0.17, 0.015))
            for y in (-0.015, 0.355):
                self.block((0.055, 0.05, 0.06), (sign * 0.24, y, -0.005), t.edge, 0.008)
            for y in (0.095, 0.18, 0.265):
                self.rod((sign * 0.04, y, 0.050), (sign * 0.20, y, 0.025), 0.006, t.surface, 4)
        self.cylinder(0.024, 0.45, (0, 0.17, 0), t.edge, 8)
        glyphs = {
            "skeletal": [
                (-0.05, -0.04),
                (-0.05, 0.04),
                (0, 0.07),
                (0.05, 0.04),
                (0.05, -0.04),
                (0, -0.07),
            ],
            "swamp": [(0, -0.07), (-0.045, 0), (0, 0.075), (0.045, 0)],
            "cursed": [
                (-0.04, -0.07),
                (0.015, -0.015),
                (-0.015, 0.06),
                (0.04, 0.01),
                (0.015, -0.07),
            ],
            "demonic": [
                (-0.06, 0.07),
                (-0.025, -0.05),
                (0, -0.075),
                (0.025, -0.05),
                (0.06, 0.07),
                (0, 0.015),
            ],
            "spectral": [(-0.045, -0.045), (0, 0.07), (0.045, -0.045), (0, -0.015)],
            "fire": [
                (-0.04, -0.06),
                (-0.05, 0.01),
                (-0.015, 0.075),
                (0.005, 0.015),
                (0.04, 0.055),
                (0.045, -0.04),
                (0, -0.07),
            ],
            "woodland": [
                (0, -0.075),
                (-0.04, -0.015),
                (-0.015, 0.04),
                (0, 0.075),
                (0.04, 0.02),
                (0.02, -0.02),
            ],
            "crystal": [(0, -0.075), (-0.045, -0.01), (-0.025, 0.06), (0, 0.08), (0.04, 0.015)],
            "dark": [(-0.06, 0), (0, 0.04), (0.06, 0), (0, -0.04)],
            "gladiator": [
                (-0.05, 0.06),
                (0, 0.035),
                (0.05, 0.06),
                (0.04, -0.035),
                (0, -0.075),
                (-0.04, -0.035),
            ],
        }
        self.prism(
            [(x - 0.14, y + 0.19) for x, y in glyphs[self.theme]], 0.004, t.accent, 0, z=0.055
        )
        self.prism(
            [(-0.018, 0.07), (0.018, 0.07), (0.018, -0.12), (0, -0.095), (-0.018, -0.12)],
            0.006,
            t.accent,
            0,
            z=0.05,
        )
        if self.theme in ("skeletal", "demonic", "crystal"):
            for sign in (-1, 1):
                self.shard((sign * 0.25, 0.36, 0), 0.12, 0.04, t.edge, -sign * 0.7)
        self.sockets["projectile_socket"] = [0.0, 0.20, 0.10]


def make_weapon(theme: str, kind: str) -> Weapon:
    weapon = Weapon(theme)
    if kind == "greatsword":
        weapon.sword(two=True)
    else:
        getattr(weapon, kind)()
    return weapon


def mesh_for(weapon: Weapon) -> trimesh.Trimesh:
    mesh = trimesh.util.concatenate(weapon.meshes)
    mesh.unmerge_vertices()
    if not np.isfinite(mesh.vertices).all() or not mesh.is_winding_consistent:
        raise ValueError("Invalid weapon geometry")
    if len(mesh.faces) > 6000 or np.any(mesh.area_faces < 1e-12):
        raise ValueError("Weapon triangle budget or degenerate face")
    return mesh


def attachment(kind: str, sockets: dict) -> dict:
    rotation = [-.5, -.5, -.5, .5] if kind in {"sword", "greatsword", "mace", "axe", "scythe"} else [0, 0, 0, 1]
    # Axe cutting edges point along +X in model space, opposite the idle palm.
    if kind == "axe":
        rotation = [-.5, .5, .5, .5]
    profile = {
        "sword": "one_handed",
        "greatsword": "two_handed",
        "bow": "bow",
        "mace": "one_handed",
        "axe": "one_handed",
        "scythe": "two_handed",
        "staff": "staff",
        "claws": "unarmed",
        "book": "staff",
    }[kind]
    return {
        "schema_version": 1,
        "units": "metres",
        "coordinates": "Y-up; longitudinal axis +Y",
        "grip_frame": "hand",
        "attack_profile": profile,
        "grip": {"position": sockets["grip_primary"], "rotation": list(rotation), "scale": [1, 1, 1]},
        "sockets": {
            key: {"position": value, "rotation": list(rotation) if key == "grip_primary" else [0, 0, 0, 1]} for key, value in sockets.items()
        },
    }


def build(root: Path = ROOT, previews: Path | None = None, revision: int = 3) -> list[dict]:
    catalog_path = root / "media/imported_catalog.json"
    doc = json.loads(catalog_path.read_text())
    runtime_path = root / "media/catalog.json"
    runtime = json.loads(runtime_path.read_text())
    source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    rows = []
    for theme, t in THEMES.items():
        for kind, label in TYPES.items():
            weapon = make_weapon(theme, kind)
            mesh = mesh_for(weapon)
            identity = f"equipment.shared.{theme}.{kind}"
            frame = attachment(kind, weapon.sockets)

            def nodes(tree, identity=identity, weapon=weapon, frame=frame):
                tree["nodes"] = [
                    {
                        "name": identity,
                        "mesh": 0,
                        "children": list(range(1, len(weapon.sockets) + 1)),
                    }
                ]
                tree["nodes"] += [
                    {"name": key, "translation": value} for key, value in weapon.sockets.items()
                ]
                tree["scenes"] = [{"nodes": [0]}]
                tree["extras"] = {"equipment": frame}

            payloads = {
                "model": (
                    "model.glb",
                    mesh.export(file_type="glb", tree_postprocessor=nodes),
                    "model/gltf-binary",
                ),
                "attachment": (
                    "attachment.json",
                    (json.dumps(frame, indent=2) + "\n").encode(),
                    "application/json",
                ),
            }
            recipe = {
                "schema_version": 1,
                "builder_sha256": source_hash,
                "id": identity,
                "theme": theme,
                "type": kind,
                "style_profile": "config/style_profile.json",
                "triangles": len(mesh.faces),
                "bounds": mesh.bounds.tolist(),
                "source": "authored BHM faceted geometry; shared equipment; metre-scale grips",
            }
            payloads["recipe"] = (
                "recipe.json",
                (json.dumps(recipe, indent=2) + "\n").encode(),
                "application/json",
            )
            if previews:
                payloads["preview"] = (
                    "preview.png",
                    (previews / f"{theme}_{kind}-after.png").read_bytes(),
                    "image/png",
                )
            folder = root / "media/equipment/shared" / theme / kind
            if revision > 1:
                folder /= f"revision_{revision}"
            files = {}
            for role, (name, payload, mime) in payloads.items():
                file = folder / name
                if file.exists() and file.read_bytes() != payload:
                    raise ValueError("Published weapon is immutable: " + str(file))
                file.parent.mkdir(parents=True, exist_ok=True)
                if not file.exists():
                    file.write_bytes(payload)
                files[role] = {
                    "path": file.relative_to(root / "media").as_posix(),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                    "media_type": mime,
                }
            entry = canonical_entry(
                {
                    "id": identity,
                    "kind": "decoration",
                    "revision": revision,
                    "title": f"{label} · {t.label}",
                    "group": "Снаряжение",
                    "tags": ["shared", "equipment", theme, kind],
                    "files": files,
                    "metadata": frame,
                }
            )
            for document in (doc, runtime):
                old = next((a for a in document["assets"] if a["id"] == identity), None)
                if old and old["revision"] > revision:
                    raise ValueError("Cannot downgrade equipment: " + identity)
                if old and old["revision"] == revision:
                    # Adding a preview does not change the immutable geometry/attachment.
                    for role, ref in old["files"].items():
                        if role in files and files[role] != ref:
                            raise ValueError(
                                "Published weapon role changed: " + identity + ":" + role
                            )
                    entry = {**entry, "files": {**old["files"], **files}}
                    document["assets"][document["assets"].index(old)] = entry
                elif old:
                    document["assets"][document["assets"].index(old)] = entry
                else:
                    document["assets"].append(entry)
            path = "assets/forge/" + files["model"]["sha256"][:24] + ".glb"
            rows.append(
                {
                    "key": f"{theme}_{kind}",
                    "before_path": path,
                    "after_path": path,
                    "id": identity,
                    "theme": theme,
                    "type": kind,
                    "triangles": len(mesh.faces),
                    "label": entry["title"],
                }
            )
    for file, document in ((catalog_path, doc), (runtime_path, runtime)):
        file.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    print(f"Published {len(rows)} shared weapons")
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--previews", type=Path)
    parser.add_argument("--revision", type=int, default=3)
    parser.add_argument("--review", type=Path)
    args = parser.parse_args()
    review = build(args.root, args.previews, args.revision)
    if args.review:
        args.review.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n")
