"""Publish replacement RPG architecture without overwriting any original GLB.

Usage: python -m tools.assets.build_mom_rpg_architecture SOURCES_JSON PAIRS_JSON
The source manifest pins the map keys and immutable SDK assets being replaced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import trimesh

from monster_forge_sdk import AssetNotFound, AssetStore
from monsterforge.paths import cache_directory
from tools.assets.build_rpg_locations import Prop, single_node

ROOT = Path(__file__).resolve().parents[2]
STONE = (147, 151, 145, 255)
LIGHT = (182, 181, 158, 255)
PLASTER = (185, 171, 139, 255)
SLATE = (54, 83, 109, 255)
WOOD = (90, 63, 43, 255)
EDGE = (51, 49, 48, 255)
GOLD = (164, 132, 68, 255)
CRYPT = (85, 98, 102, 255)
BONE = (150, 155, 139, 255)
TEAL = (61, 132, 119, 255)


def tint(color, value):
    return tuple(min(255, round(c * value)) for c in color[:3]) + (255,)


class Architecture(Prop):
    """Large faceted masses, inset openings and sparse construction details."""

    def block(self, size, point, color=STONE, bevel=.045):
        x, y, z = np.asarray(size) / 2
        b = min(bevel, x * .2, y * .2, z * .2)
        if b < .012:
            self.box(size, point, color)
            return
        corners = [(-x+b, -z), (x-b, -z), (x, -z+b), (x, z-b),
                   (x-b, z), (-x+b, z), (-x, z-b), (-x, -z+b)]
        vertices = []
        for h, inset in [(-y, b), (-y+b, 0), (y-b, 0), (y, b)]:
            for a, c in corners:
                vertices.append((a * (x-inset)/x, h, c * (z-inset)/z))
        faces = []
        for ring in range(3):
            for i in range(8):
                a, c = ring*8+i, ring*8+(i+1) % 8
                faces.extend([(a, c, a+8), (c, c+8, a+8)])
        for i in range(1, 7):
            faces.extend([(0, i+1, i), (24, 24+i, 25+i)])
        mesh = trimesh.Trimesh(vertices, faces, process=False)
        mesh.fix_normals()
        self.add(mesh, color, point)

    def beam(self, start, end, width=.14, depth=.16, color=WOOD):
        start, end = np.asarray(start, float), np.asarray(end, float)
        direction = end-start
        mesh = trimesh.creation.box((width, np.linalg.norm(direction), depth))
        mesh.apply_transform(trimesh.geometry.align_vectors((0, 1, 0), direction))
        self.add(mesh, color, (start+end)/2)

    def polygon(self, points, depth, z, color):
        n = len(points)
        vertices = [(x, y, z-depth/2) for x, y in points]
        vertices += [(x, y, z+depth/2) for x, y in points]
        faces = []
        for i in range(1, n-1):
            faces.extend([(0, i+1, i), (n, n+i, n+i+1)])
        for i in range(n):
            j = (i+1) % n
            faces.extend([(i, j, i+n), (j, j+n, i+n)])
        mesh = trimesh.Trimesh(vertices, faces, process=False)
        mesh.fix_normals()
        self.add(mesh, color)

    def banded_tower(self, x, z, radius, height, roof=True):
        self.cylinder(radius*1.12, .3, (x, .15, z), EDGE, 12)
        self.cylinder(radius*.83, height-.3, (x, (height+.3)/2, z), STONE, 12)
        for course in range(5):
            bottom = .32+course*(height-.32)/5
            top = .32+(course+1)*(height-.32)/5-.022
            for section in range(12):
                a = (section+(course % 2)*.5)*math.pi/6
                b = a+math.pi/6
                points = [(x+math.cos(t)*r, z+math.sin(t)*r)
                          for t, r in [(a, radius*.82), (a, radius),
                                       ((a+b)/2, radius), (b, radius),
                                       (b, radius*.82)]]
                count = len(points)
                vertices = [(u, y, v) for y in (bottom, top) for u, v in points]
                faces = []
                for j in range(1, count-1):
                    faces += [(0, j+1, j), (count, count+j, count+j+1)]
                for j in range(count):
                    k = (j+1) % count
                    faces += [(j, k, j+count), (k, k+count, j+count)]
                mesh = trimesh.Trimesh(vertices, faces, process=False)
                mesh.fix_normals()
                self.add(mesh, tint(STONE, [1., .97, 1.03][(section+course) % 3]))
        for y in (.48, height*.47, height-.18):
            self.cylinder(radius*1.045, .16, (x, y, z), LIGHT, 12)
        for side in (-1, 1):
            self.window(x, height*.65, z+side*(radius+.02), .25, .95, stone=True)
        if roof:
            for r, y, h in [(radius*1.23, height+.05, .16),
                            (radius*1.20, height+.13, radius*1.4)]:
                if h < .2:
                    self.cylinder(r, h, (x, y, z), EDGE, 12)
                else:
                    self.cone(r, h, (x, y, z), SLATE, 12)
            self.gem(.13, (x, height+radius*1.65, z), GOLD, (.65, 1.5, .65))

    def window(self, x, y, z, width=.65, height=.9, stone=False):
        # A recessed dark panel bounded by a thick frame and a projecting sill.
        sign = 1 if z >= 0 else -1
        self.box((width, height, .045), (x, y, z), EDGE)
        color = LIGHT if stone else WOOD
        for a in (-1, 1):
            self.block((.10, height+.14, .13), (x+a*(width/2+.045), y, z+sign*.04), color)
        for a in (-1, 1):
            self.block((width+.24, .12, .19 if a < 0 else .13),
                       (x, y+a*(height/2+.04), z+sign*.06), color)
        self.box((.055, height, .06), (x, y, z+sign*.035), color)
        if not stone:
            for a in (-1, 1):
                self.block((width*.24, height*.94, .07),
                           (x+a*width*.38, y, z+sign*.07), tint(SLATE, .85))

    def doorway(self, x, z, height=1.9, width=1.25):
        self.block((width+.3, .14, .5), (x, .07, z-.12), LIGHT)
        self.box((width, height, .07), (x, height/2+.13, z), EDGE)
        for i in range(4):
            self.block((width/4-.025, height-.12, .08),
                       (x+(i-1.5)*width/4, height/2+.13, z-.035), tint(WOOD, .88+i*.035))
        for a in (-1, 1):
            self.block((.19, height+.12, .22), (x+a*(width/2+.09), height/2+.13, z-.08), LIGHT)
        self.block((width+.45, .22, .25), (x, height+.23, z-.08), LIGHT)
        for y in (.5, 1.4):
            self.box((width*.83, .10, .07), (x, y, z-.105), EDGE)

    def foundation(self, width, depth, height=.48, color=STONE):
        self.block((width, height, depth), (0, height/2, 0), color, .09)
        self.block((width+.08, .15, depth+.08), (0, height-.04, 0), LIGHT)

    def roof_panels(self, width, depth, y, rise, color=SLATE, center=(0, 0)):
        cx, cz = center
        self.polygon([(cx-width/2, y-.05), (cx+width/2, y-.05), (cx, y+rise)],
                     depth-.16, cz, tint(PLASTER, .91))
        angle = math.atan2(rise, width/2)
        # Four generous courses, with staggered colors rather than microtiles.
        for side in (-1, 1):
            for course in range(4):
                x = side*(course+.5)*width/8
                height = y+rise*(1-abs(x)/(width/2))
                edges = np.linspace(-depth/2, depth/2, 5)
                edges[1:4] += (course % 2)*depth/12
                for column in range(4):
                    span = edges[column+1]-edges[column]
                    mesh = trimesh.creation.box((width/8/math.cos(angle)+.04, .12, span-.008))
                    mesh.apply_transform(trimesh.transformations.rotation_matrix(-side*angle, (0, 0, 1)))
                    shade = [.96, .99, 1.02, 1.0][course]+[0., .02, -.01, .01][column]
                    self.add(mesh, tint(color, shade), (cx+x, height+.04+(3-course)*.015, cz+(edges[column]+edges[column+1])/2))
        for z in (cz-depth/2-.025, cz+depth/2+.025):
            for side in (-1, 1):
                self.beam((cx+side*width/2, y, z), (cx, y+rise+.08, z), .16, .18)
        for side in (-1, 1):
            self.block((.16, .20, depth+.18), (cx+side*width/2, y-.03, cz), WOOD)
        self.block((.23, .17, depth+.15), (cx, y+rise+.13, cz), tint(color, .72))

    def framed_hall(self, width, height, depth, roof_color=SLATE):
        self.foundation(width+.2, depth+.2)
        self.block((width, height-.45, depth), (0, (height+.45)/2, 0), PLASTER, .06)
        for x in (-width/2-.01, width/2+.01):
            for z in (-depth/2-.01, depth/2+.01):
                self.block((.20, height-.4, .20), (x, (height+.4)/2, z), WOOD)
        for z in (-depth/2-.06, depth/2+.06):
            for y in (.65, height*.58, height-.12):
                self.block((width+.10, .16, .16), (0, y, z), WOOD)
        for side in (-1, 1):
            x = side*width/2
            self.beam((x, .7, -depth*.30), (x, height*.58-.1, depth*.30), .16, .16)
        self.roof_panels(width+.8, depth+.8, height, width*.36, roof_color)

    def stone_arch(self, width=4, spring=2.2, rise=1.5, depth=.8,
                   color=STONE, broken=False, pointed=False, piers=True):
        radius = width/2
        thickness = .48
        for side in (-1, 1) if piers else ():
            x = side*(radius+thickness/2)
            self.block((.95, .25, depth+.35), (x, .125, 0), EDGE)
            for i in range(4):
                self.block((thickness, spring/4-.025, depth),
                           (x, (i+.5)*spring/4+.1, 0), tint(color, [1., .94, 1.04, .98][i]))
            self.block((.78, .18, depth+.2), (x, spring-.02, 0), LIGHT if not pointed else BONE)
        for i in range(11):
            if broken and i in (3, 4, 5):
                continue
            a, b = i*math.pi/11+.012, (i+1)*math.pi/11-.012
            def arc(t, outer):
                extra = thickness if outer else 0
                y = spring+(rise+extra)*math.sin(t)
                if pointed:
                    y += .28*math.sin(t)**5
                return ((radius+extra)*math.cos(t), y)
            self.polygon([arc(a, False), arc(a, True), arc(b, True), arc(b, False)],
                         depth+.12, 0, tint(color, [1.02, .92, 1.06][i % 3]))
        if not broken:
            self.block((.45, .60, depth+.28), (0, spring+rise+.19+(.28 if pointed else 0), 0), LIGHT if not pointed else BONE)
        else:
            for i in range(3):
                self.gem(.30, (radius+.12+(i % 2)*.18, .25, .5+i*.35), tint(color, .9), (1.2, .7, 1.1))


def city(name):
    p = Architecture()
    if name in ('house_blue', 'house_warm', 'barracks'):
        w, h, d = (5, 3.4, 4) if name.startswith('house') else (6, 3, 4)
        roof = SLATE if name != 'house_warm' else (135, 78, 57, 255)
        p.framed_hall(w, h, d, roof)
        p.doorway(-w*.21, -d/2-.12)
        p.window(w*.24, h*.65, -d/2-.08)
        p.window(0, h*.70, d/2+.08)
        for x in (-w*.30, w*.30):
            p.beam((x-.28, .8, -d/2-.10), (x+.28, h*.58-.12, -d/2-.10), .13, .12)
        p.window(0, h+.66, -d/2-.37, .55, .56)
        if name.startswith('house'):
            p.roof_panels(1.9, 1.25, 2.35, .48, roof, (-w*.21, -d/2-.38))
            for x in (-w*.21-.67, -w*.21+.67):
                p.beam((x, 1.83, -d/2-.04), (x, 2.35, -d/2-.72), .12, .12)
        p.block((.63, 2.0, .62), (-w*.34, h+1.2, d*.22), STONE)
        p.block((.83, .23, .8), (-w*.34, h+2.25, d*.22), EDGE)
        if name == 'barracks':
            p.block((1.0, .95, .12), (0, h-.48, -d/2-.22), SLATE)
            p.gem(.27, (0, h-.45, -d/2-.33), GOLD, (.8, 1.2, .2))
            for x in (-w*.40, w*.40):
                p.block((.14, 1.6, .14), (x, 1.2, -d/2-.32), WOOD)
                p.cone(.18, .35, (x, 2.0, -d/2-.32), STONE, 4)
    elif name == 'keep':
        p.foundation(7, 5.6, .65)
        p.block((6.6, 4.5, 5.2), (0, 2.85, 0), STONE)
        for x in (-2.8, 2.8):
            for z in (-2.25, 2.25):
                p.block((.55, 4.7, .6), (x, 2.75, z), LIGHT)
        for y in (1.3, 3.4, 5.05):
            p.block((6.95, .20, 5.55), (0, y, 0), LIGHT)
        p.roof_panels(7.5, 6.1, 5.2, 2.25)
        p.doorway(0, -2.75, 2.5, 1.55)
        for x in (-1.9, 1.9):
            p.window(x, 3.7, -2.68, .62, 1.1, stone=True)
        p.banded_tower(-3.35, .6, 1.0, 5.9)
        p.banded_tower(3.35, .6, .85, 5.3)
        for i in range(3):
            p.block((2.2+i*.35, .18, .55), (0, .45-i*.15, -2.95-i*.43), STONE)
        for x in (-.95, .95):
            p.block((.48, 1.5, .07), (x, 3.55, -2.82), SLATE)
            p.box((.1, 1.08, .09), (x, 3.65, -2.88), GOLD)
    elif name == 'gatehouse':
        p.stone_arch(6.0, 2.4, 1.9, 2.0, piers=False)
        for side in (-1, 1):
            x = side*4.2
            p.banded_tower(x, 0, 1.25, 4.4)
            for z in (-1.10, 1.10):
                p.block((.48, 3.4, .48), (x, 1.9, z), LIGHT)
        p.block((6.5, .38, 2.2), (0, 4.75, 0), LIGHT)
        for x in np.linspace(-2.8, 2.8, 7):
            p.block((.52, .65, 1.9), (x, 5.16, 0), STONE)
        for z in (-1.1, 1.1):
            p.block((1.2, 1.05, .12), (0, 4.4, z), SLATE)
            p.gem(.23, (0, 4.45, z*1.08), GOLD, (1, 1.2, .25))
    elif name == 'curtain_wall':
        p.foundation(6.1, 1.2, .35)
        p.block((6, 2.6, .85), (0, 1.65, 0), STONE)
        for x in (-2.65, 0, 2.65):
            p.block((.60, 2.8, 1.25), (x, 1.72, 0), LIGHT)
            p.block((.78, .19, 1.4), (x, 3.10, 0), EDGE)
        for y in (.85, 1.65, 2.45):
            p.box((6, .045, .91), (0, y, 0), tint(STONE, .76))
        p.block((6.25, .28, 1.35), (0, 3.2, 0), LIGHT)
        for x in np.linspace(-2.65, 2.65, 6):
            p.block((.66, .65, 1.1), (x, 3.64, 0), STONE)
    elif name == 'corner_tower':
        p.banded_tower(0, 0, 1.7, 4.9)
        for a in range(4):
            t = a*math.pi/2
            p.block((.48, 2.5, .48), (math.cos(t)*1.58, 1.4, math.sin(t)*1.58), LIGHT)
        p.doorway(0, -1.73, 1.8, .9)
    elif name == 'stable':
        p.foundation(6.2, 4.7, .30)
        # Open bays, not a solid box with a painted door.
        p.block((6, 2.7, .24), (0, 1.65, 1.9), PLASTER)
        for x in (-2.8, 0, 2.8):
            p.block((.25, 3.3, .25), (x, 1.9, -1.9), WOOD)
            p.block((.20, 2.1, 3.8), (x, 1.35, .05), WOOD)
            p.beam((x, 2.35, -1.8), (x, 3.35, -.8), .16, .16)
        p.block((6.15, .22, .25), (0, 3.35, -1.9), WOOD)
        p.roof_panels(6.8, 5.0, 3.45, 1.55)
        for x in (-1.4, 1.4):
            p.block((2.3, .7, .13), (x, .8, -1.85), WOOD)
            for dx in (-.75, 0, .75):
                p.block((.10, .7, .16), (x+dx, .8, -1.88), tint(WOOD, 1.2))
            p.block((1.4, .45, 1), (x, .55, .95), (147, 130, 76, 255))
        p.block((1.9, .52, .66), (-1.4, .42, -2.35), EDGE)
        p.block((1.6, .10, .44), (-1.4, .69, -2.35), (74, 102, 108, 255))
    elif name == 'smithy':
        p.foundation(4.4, 4.5, .4)
        p.block((4, 2.8, 3.1), (0, 1.8, .55), STONE)
        p.roof_panels(4.8, 4.3, 3.25, 1.4)
        p.window(-1.0, 2, -1.04, .65, .7, stone=True)
        p.doorway(.85, -1.08, 1.85, 1.0)
        # Deep furnace mouth with a masonry hood and a tall square flue.
        p.block((1.4, .45, 1.3), (-1.2, .65, -1.65), EDGE)
        for x in (-1.76, -.64):
            p.block((.26, 1.35, 1.05), (x, 1.45, -1.65), STONE)
        p.block((1.5, .44, 1.2), (-1.2, 2.25, -1.65), STONE)
        p.box((.8, .28, .08), (-1.2, 1.0, -1.13), (178, 89, 43, 255))
        p.block((.8, 3.1, .85), (-1.2, 3.1, -1.65), EDGE)
        p.block((1.04, .20, 1.05), (-1.2, 4.72, -1.65), LIGHT)
        p.block((.74, .06, .76), (-1.2, 4.84, -1.65), EDGE)
        p.block((.55, .65, .65), (.9, .72, -2.15), WOOD)
        p.polygon([(.2, 1.04), (1.5, 1.04), (1.8, 1.23), (.45, 1.35), (.2, 1.28)], .46, -2.15, EDGE)
    elif name == 'watch_platform':
        for x in (-.95, .95):
            for z in (-.95, .95):
                p.block((.4, .3, .4), (x, .15, z), STONE)
                p.block((.20, 4.3, .20), (x, 2.45, z), WOOD)
            p.beam((x, .5, -.95), (x, 2.6, .95), .17, .17)
            p.beam((x, .5, .95), (x, 2.6, -.95), .17, .17)
        for z in (-.95, .95):
            p.beam((-.95, .5, z), (.95, 2.6, z), .17, .17)
        p.block((2.5, .26, 2.5), (0, 2.8, 0), WOOD)
        for side in (-1, 1):
            p.block((.14, .65, 2.3), (side*1.13, 3.25, 0), WOOD)
            p.block((2.3, .65, .14), (0, 3.25, side*1.13), WOOD)
        for x in (-.4, .4):
            p.beam((x, .1, -1.35), (x, 2.85, -.95), .11, .13)
        for i in range(8):
            p.block((.88, .10, .13), (0, .25+i*.34, -1.33+i*.05), tint(WOOD, 1.3))
        p.roof_panels(3, 3, 4.55, .95)
    elif name == 'well':
        # Hollow masonry ring: the water remains below the rim.
        for i in range(10):
            a, b = i*2*math.pi/10, (i+1)*2*math.pi/10
            points = [(math.cos(t)*r, math.sin(t)*r) for t, r in [(a, .78), (a, 1.1), (b, 1.1), (b, .78)]]
            verts = [(x, y, z) for y in (.05, .8) for x, z in points]
            faces = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7)]
            for j in range(4):
                k = (j+1) % 4
                faces += [(j, k, j+4), (k, k+4, j+4)]
            mesh = trimesh.Trimesh(verts, faces, process=False)
            mesh.fix_normals()
            p.add(mesh, tint(STONE, [1, .93, 1.05][i % 3]))
        p.cylinder(.77, .04, (0, .28, 0), (58, 89, 99, 255), 10)
        for x in (-1.18, 1.18):
            p.block((.20, 2.6, .24), (x, 1.3, 0), WOOD)
        p.beam((-1.25, 1.85, 0), (1.25, 1.85, 0), .18, .18)
        p.block((.07, 1.15, .07), (0, 1.24, 0), (133, 117, 86, 255))
        p.roof_panels(3.0, 2.2, 2.65, .85)
    elif name == 'sealed_portal':
        p.stone_arch(3.0, 2.0, 1.3, .8)
        p.polygon([(-1.38, .12), (1.38, .12), (1.38, 2), (.85, 2.9), (0, 3.27), (-.85, 2.9), (-1.38, 2)], .13, .12, EDGE)
        for x in (-.8, 0, .8):
            p.box((.08, 2.5, .05), (x, 1.55, -.02), TEAL)
        p.gem(.36, (0, 2.0, -.12), TEAL, (1, 1.5, .25))
    else:
        raise ValueError(name)
    return p


def crypt(name):
    p = Architecture()
    if name in ('arched_door', 'entrance_arch', 'broken_arch'):
        p.stone_arch(3.2, 2.0, 1.25, .8, CRYPT,
                     broken=name == 'broken_arch', pointed=True)
        for side in (-1, 1):
            p.block((.28, 2.0, .26), (side*2.05, 1.13, -.5), BONE)
    elif name in ('pillar', 'pillar_small'):
        p.block((1.4, .25, 1.4), (0, .125, 0), EDGE)
        p.block((1.12, .24, 1.12), (0, .37, 0), BONE)
        p.cylinder(.44, 2.9, (0, 1.9, 0), CRYPT, 8)
        for y in (.62, 2.7, 3.3):
            p.cylinder(.53, .16, (0, y, 0), BONE, 8)
        for side in (-1, 1):
            p.block((.12, 2.5, .16), (side*.32, 1.9, -.32), tint(CRYPT, 1.15))
        p.block((1.05, .26, 1.05), (0, 3.45, 0), BONE)
        p.block((1.35, .22, 1.35), (0, 3.68, 0), EDGE)
    elif name == 'vault_wall':
        p.foundation(6, 1, .3, EDGE)
        p.block((5.9, 2.5, .48), (0, 1.55, .15), CRYPT)
        for x in (-2.7, -.9, .9, 2.7):
            p.block((.32, 2.65, .85), (x, 1.63, 0), BONE)
            p.block((.52, .25, 1.04), (x, .35, 0), EDGE)
        for x in (-1.8, 0, 1.8):
            p.box((1.35, 1.85, .06), (x, 1.55, -.12), EDGE)
            p.polygon([(x-.67, 1.95), (x, 2.6), (x+.67, 1.95)], .08, -.17, tint(CRYPT, 1.20))
        p.block((6.1, .25, 1.05), (0, 2.97, 0), BONE)
        p.block((6.2, .15, 1.15), (0, 3.14, 0), EDGE)
    elif name == 'burial_niche':
        p.foundation(3.3, 1.4, .25, EDGE)
        p.block((3.05, 2.7, .20), (0, 1.65, .55), CRYPT)
        for x in (-1.48, 0, 1.48):
            p.block((.22, 2.85, 1.25), (x, 1.67, 0), BONE)
        for y in (.35, 1.65, 2.95):
            p.block((3.2, .18, 1.3), (0, y, 0), BONE)
        for x in (-.74, .74):
            for y in (.75, 2.05):
                p.block((1.12, .28, .9), (x, y, .02), tint(CRYPT, .83))
                p.block((1.18, .10, .95), (x, y+.18, .02), BONE)
                p.gem(.15, (x, y+.34, -.12), BONE, (1, .8, .9))
        p.block((3.4, .25, 1.45), (0, 3.15, 0), EDGE)
    else:
        raise ValueError(name)
    return p


NAMES = {'model_house_blue': 'house_blue', 'model_house_warm': 'house_warm',
         'model_sealed_portal': 'sealed_portal', 'model_crypt_arch': 'entrance_arch',
         'model_pillar': 'pillar_small'}


def build(sources: Path, pairs: Path, *, draft=False, previews: Path | None = None, revision=1):
    if revision < 1:
        raise ValueError('Revision must be positive')
    store = AssetStore(ROOT)
    root = cache_directory('architecture-review/sdk', root=ROOT) if draft else ROOT
    catalog_path = root/'media/imported_catalog.json'
    catalog = json.loads((ROOT/'media/imported_catalog.json').read_text())
    runtime = json.loads((ROOT/'media/catalog.json').read_text())
    if draft:
        (root/'media').mkdir(parents=True, exist_ok=True)
    rows = json.loads(sources.read_text())
    source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    output = []
    for row in rows:
        if draft:
            source = store.get(row['before_id']).files['model']
            link = root/'media'/source.path
            link.parent.mkdir(parents=True, exist_ok=True)
            if link.is_symlink():
                link.unlink()
            link.write_bytes(store.read(row['before_id'], 'model'))
        name = NAMES.get(row['key'], row['key'].removeprefix('prop_'))
        location = 'sei' if row['stage'] == 'rpg_city' else 'hollow_crypt'
        prop = (city if location == 'sei' else crypt)(name)
        mesh = trimesh.util.concatenate(prop.meshes)
        # Keep the original ground plane and horizontal footprint. The map's
        # world placements and passage/pathing definitions do not change.
        old_bounds = np.asarray(row['before_bounds'])
        lo, hi = mesh.bounds
        target = old_bounds[1]-old_bounds[0]
        target[1] = old_bounds[1, 1]
        factors = np.ones(3)
        for axis in (0, 2):
            factors[axis] = min(old_bounds[0, axis]/lo[axis],
                                old_bounds[1, axis]/hi[axis])
        mesh.vertices[:, 1] -= lo[1]
        factors[1] = target[1]/(hi[1]-lo[1])
        mesh.vertices *= factors
        mesh.unmerge_vertices()
        colors = mesh.visual.vertex_colors.copy()
        # Large planes retain their base color; low broad shading replaces
        # uniformly bright primitive surfaces, without noisy microtextures.
        factor = .90+.10*np.clip(mesh.vertices[:, 1]/target[1], 0, 1)
        colors[:, :3] = np.rint(colors[:, :3]*factor[:, None]).astype(np.uint8)
        mesh.visual.vertex_colors = colors
        if not mesh.is_winding_consistent or not np.isfinite(mesh.vertices).all():
            raise ValueError(f'Invalid architectural mesh: {name}')
        if len(mesh.faces) > 14000:
            raise ValueError(f'Architecture triangle budget exceeded: {name}')
        identity = f'decoration.mom_rpg.{location}.{name}'
        folder = root/'media/decorations/mom_rpg/architecture'/location/name
        if revision > 1:
            folder /= f'revision_{revision}'
        try:
            source_sha256 = store.get(row['before_id']).files['model'].sha256
        except AssetNotFound:
            previous_recipe = json.loads(store.read(identity, 'recipe'))
            if previous_recipe['source_id'] != row['before_id']:
                raise ValueError('Replacement provenance does not match') from None
            source_sha256 = previous_recipe['source_sha256']
        recipe = {'schema_version': 1, 'id': identity, 'source_id': row['before_id'],
                  'source_sha256': source_sha256,
                  'builder_sha256': source_hash, 'coordinates': 'metres; Y-up; ground Y=0',
                  'style': 'Unified low-poly project style', 'triangles': len(mesh.faces),
                  'bounds': mesh.bounds.tolist(), 'design': 'Faceted masonry, constructed roof planes, recessed openings; no microtexture'}
        payloads = {'model': ('model.glb', mesh.export(file_type='glb', tree_postprocessor=single_node), 'model/gltf-binary'),
                    'recipe': ('recipe.json', (json.dumps(recipe, indent=2)+'\n').encode(), 'application/json')}
        if previews is not None:
            payloads['preview'] = ('preview.png', (previews/(row['key']+'-after.png')).read_bytes(), 'image/png')
        files = {}
        folder.mkdir(parents=True, exist_ok=True)
        for role, (filename, payload, mime) in payloads.items():
            path = folder/filename
            if not draft and path.exists() and path.read_bytes() != payload:
                raise ValueError('Immutable replacement already exists: '+identity)
            if draft or not path.exists():
                path.write_bytes(payload)
            files[role] = {'path': path.relative_to(root/'media').as_posix(),
                           'sha256': hashlib.sha256(payload).hexdigest(),
                           'size_bytes': len(payload), 'media_type': mime}
        entry = {'id': identity, 'kind': 'decoration', 'revision': revision,
                 'title': name.replace('_', ' ').title(),
                 'group': 'MOM RPG',
                 'tags': ['mom_rpg', location, 'architecture', 'low-poly'], 'files': files}
        previous = next((a for a in catalog['assets'] if a['id'] == identity), None)
        if previous and previous['revision'] >= revision and previous != entry:
            raise ValueError('Replacement revision already exists: '+identity)
        if previous:
            catalog['assets'][catalog['assets'].index(previous)] = entry
        else:
            catalog['assets'].append(entry)
        output.append({**row, 'after_id': identity,
                       'after_path': 'assets/forge/'+files['model']['sha256'][:24]+'.glb',
                       'triangles': len(mesh.faces), 'after_bounds': mesh.bounds.tolist()})
        print(identity, len(mesh.faces), 'triangles', flush=True)
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+'\n')
    known = {a['id']: i for i, a in enumerate(runtime['assets'])}
    for entry in catalog['assets']:
        index = known.get(entry['id'])
        if index is None:
            runtime['assets'].append(entry)
        elif entry['revision'] > runtime['assets'][index]['revision']:
            runtime['assets'][index] = entry
    (root/'media/catalog.json').write_text(json.dumps(runtime, ensure_ascii=False, indent=2)+'\n')
    pairs.write_text(json.dumps(output, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sources', type=Path)
    parser.add_argument('pairs', type=Path)
    parser.add_argument('--draft', action='store_true')
    parser.add_argument('--previews', type=Path)
    parser.add_argument('--revision', type=int, default=1)
    args = parser.parse_args()
    build(args.sources, args.pairs, draft=args.draft, previews=args.previews, revision=args.revision)
