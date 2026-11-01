"""Version 1 construction language. No imported game meshes or executable recipes."""
from __future__ import annotations

import json
import math
import struct
import zlib
from pathlib import Path

import numpy as np

VERSION = 1
OPS = {"ellipsoid", "loft", "sweep", "prism", "box", "indexed_mesh"}


def mesh(command: dict) -> tuple[np.ndarray, np.ndarray]:
    """Return vertices/faces in metres, Y up, +Z forward."""
    op = command["op"]
    if op not in OPS:
        raise ValueError(f"Unknown construction operation: {op}")
    vertices, faces = [], []
    if op == "indexed_mesh":
        vertices = np.asarray(command["vertices"], dtype=float)
        indices = np.asarray(command["faces"])
        if (vertices.ndim != 2 or vertices.shape[1] != 3 or len(vertices) < 4
                or indices.ndim != 2 or indices.shape[1] != 3 or len(indices) < 4
                or not np.issubdtype(indices.dtype, np.integer)
                or np.any(indices < 0) or np.any(indices >= len(vertices))):
            raise ValueError("Invalid indexed mesh vertices or triangle indices")
        return vertices, indices.astype(int)
    if op == "ellipsoid":
        center = np.array(command["center"], dtype=float)
        radii = np.array(command["radii"], dtype=float)
        sides, rings = command.get("sides", 8), command.get("rings", 4)
        vertices.append(center + [0, -radii[1], 0])
        for j in range(1, rings):
            latitude = -math.pi / 2 + math.pi * j / rings
            for i in range(sides):
                angle = 2 * math.pi * i / sides
                vertices.append(center + radii * [math.cos(latitude) * math.cos(angle),
                                                 math.sin(latitude),
                                                 math.cos(latitude) * math.sin(angle)])
        vertices.append(center + [0, radii[1], 0])
        for i in range(sides):
            faces.append([0, 1 + i, 1 + (i + 1) % sides])
        for j in range(rings - 2):
            for i in range(sides):
                a, b = 1 + j * sides + i, 1 + j * sides + (i + 1) % sides
                faces.extend([[a, a + sides, b], [b, a + sides, b + sides]])
        last = 1 + (rings - 2) * sides
        for i in range(sides):
            faces.append([len(vertices) - 1, last + (i + 1) % sides, last + i])
    elif op in ("loft", "sweep"):
        sides = command.get("sides", 8)
        if op == "loft":
            # A station is [y, x, z, radius_x, radius_z].
            stations = command["stations"]
            for y, x, z, rx, rz in stations:
                for i in range(sides):
                    angle = 2 * math.pi * i / sides
                    vertices.append([x + rx * math.cos(angle), y, z + rz * math.sin(angle)])
        else:
            path, radii = np.array(command["path"], float), command["radii"]
            previous_u = previous_v = None
            for j, center in enumerate(path):
                tangent = path[min(j + 1, len(path) - 1)] - path[max(0, j - 1)]
                tangent /= np.linalg.norm(tangent)
                if previous_u is None:
                    ref = np.array([0., 1., 0.]) if abs(tangent[1]) < .9 else np.array([1., 0., 0.])
                    u = np.cross(tangent, ref)
                else:
                    # Transport the preceding section instead of switching world axes mid-limb.
                    # A world-axis switch can rotate adjacent rings by 180 degrees and fold the skin.
                    u = previous_u-tangent*np.dot(previous_u, tangent)
                    if np.linalg.norm(u) < 1e-8:
                        u = np.cross(previous_v, tangent)
                u /= np.linalg.norm(u)
                v = np.cross(tangent, u)
                previous_u, previous_v = u, v
                for i in range(sides):
                    angle = 2 * math.pi * i / sides
                    vertices.append(center + radii[j] * (math.cos(angle) * u + math.sin(angle) * v))
            stations = path
        for j in range(len(stations) - 1):
            for i in range(sides):
                a, b = j * sides + i, j * sides + (i + 1) % sides
                faces.extend([[a, a + sides, b], [b, a + sides, b + sides]])
        for j, reverse in ((0, op == "sweep"), (len(stations) - 1, op == "loft")):
            start = j * sides
            for i in range(1, sides - 1):
                face = [start, start + i, start + i + 1]
                faces.append(face[::-1] if reverse else face)
    else:
        if op == "box":
            x, y, z = command["center"]
            rx, ry, rz = np.array(command["size"]) / 2
            points = [[x-rx, y-ry, z+rz], [x+rx, y-ry, z+rz],
                      [x+rx, y+ry, z+rz], [x-rx, y+ry, z+rz]]
            offset = [0, 0, -2 * rz]
        else:
            points, offset = command["points"], command["offset"]
        # The polygon must be convex and counterclockwise when viewed from outside.
        vertices = list(points) + (np.array(points) + offset).tolist()
        count = len(points)
        for i in range(1, count - 1):
            faces.extend([[0, i, i+1], [count, count+i+1, count+i]])
        for i in range(count):
            j = (i + 1) % count
            faces.extend([[i, count+i, j], [j, count+i, count+j]])
    return np.asarray(vertices, dtype=float), np.asarray(faces, dtype=int)


def validate(recipe: dict) -> None:
    if recipe.get("schema_version") != VERSION or not recipe.get("commands"):
        raise ValueError("Expected a nonempty version 1 recipe")
    previous_stage = 0
    ids = set()
    for command in recipe["commands"]:
        if command["id"] in ids:
            raise ValueError("Duplicate command ID")
        ids.add(command["id"])
        if not previous_stage <= command["stage"] <= 5:
            raise ValueError("Construction stages must be ordered")
        previous_stage = command["stage"]
        if command["material"] not in recipe["palette"] or not command["purpose"]:
            raise ValueError("Missing material or construction explanation")
        for key in ("radii", "size"):
            if key in command and any(v <= 0 for v in command[key]):
                raise ValueError("Dimensions must be positive")
        if command["op"] in {"loft", "sweep"} and len(command.get("stations", command.get("path", []))) < 2:
            raise ValueError("A loft or sweep needs two stations")
        if command["op"] == "sweep":
            path = np.array(command["path"], float)
            if len(path) != len(command["radii"]) or np.any(np.linalg.norm(np.diff(path, axis=0), axis=1) < 1e-8):
                raise ValueError("Invalid sweep path")
        if command["op"] == "loft" and any(s[3] <= 0 or s[4] <= 0 for s in command["stations"]):
            raise ValueError("Invalid loft station")
        vertices, faces = mesh(command)
        if 'face_materials' in command:
            materials = command['face_materials']
            if (len(materials) != len(faces)
                    or any(name not in recipe['palette'] for name in materials)):
                raise ValueError('Expected one palette material per triangle')
        if not np.isfinite(vertices).all():
            raise ValueError("Nonfinite coordinates")
        if 'vertex_normals' in command:
            shading = np.asarray(command['vertex_normals'], dtype=float)
            if (command['op'] != 'indexed_mesh' or shading.shape != vertices.shape
                    or not np.isfinite(shading).all()
                    or not np.allclose(np.linalg.norm(shading, axis=1), 1, atol=1e-4)):
                raise ValueError('Expected one finite unit normal per indexed vertex')
        if 'fur_uv' in command:
            uv=np.asarray(command['fur_uv'],dtype=float)
            if uv.shape!=(len(vertices),2) or not np.isfinite(uv).all() or command.get('fur_texture',{}).get('schema_version')!=1 or command.get('fur_texture',{}).get('kind') not in {'bear_pelt','boar_bristle','tiger_stripes','wolf_pelt','animal_bear_pelt'}:
                raise ValueError('Expected finite per-vertex UVs and versioned fur material')
        if 'vertex_color_factors' in command:
            factors=np.asarray(command['vertex_color_factors'],dtype=float)
            if factors.shape!=(len(vertices),) or not np.isfinite(factors).all() or np.any(factors<0) or np.any(factors>2):
                raise ValueError('Expected one finite color multiplier in [0,2] per vertex')
        triangles = vertices[faces]
        area = np.linalg.norm(np.cross(triangles[:, 1]-triangles[:, 0],
                                       triangles[:, 2]-triangles[:, 0]), axis=1)
        if np.any(area < 1e-10):
            raise ValueError(f"Degenerate faces in {command['id']}")
        if command["op"] == "indexed_mesh":
            edges = {}
            for face in faces:
                for a, b in zip(face, np.roll(face, -1), strict=True):
                    edges.setdefault(tuple(sorted((a, b))), []).append((a, b))
            if any(len(pair) != 2 or pair[0] != pair[1][::-1] for pair in edges.values()):
                raise ValueError("Indexed mesh must be closed with consistent winding")
            volume = np.sum(np.einsum("ij,ij->i", triangles[:, 0],
                            np.cross(triangles[:, 1], triangles[:, 2]))) / 6
            if volume <= 1e-10:
                raise ValueError("Indexed mesh must enclose positive volume")


def compile_recipe(recipe: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[int]]:
    validate(recipe)
    positions, normals, colors, ends = [], [], [], []
    for command in recipe["commands"]:
        vertices, faces = mesh(command)
        tri = vertices[faces]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        n /= np.linalg.norm(n, axis=1)[:, None]
        rgb = np.array(list(bytes.fromhex(recipe["palette"][command["material"]].lstrip("#")))) / 255
        positions.extend(tri.reshape(-1, 3))
        if 'vertex_normals' in command:
            normals.extend(np.asarray(command['vertex_normals'])[faces].reshape(-1, 3))
        else:
            normals.extend(np.repeat(n, 3, axis=0))
        if 'face_materials' in command:
            triangle_colors = np.asarray([list(bytes.fromhex(recipe['palette'][name].lstrip('#')))
                                          for name in command['face_materials']]) / 255
            colors.extend(np.repeat(triangle_colors, 3, axis=0))
        else:
            colors.extend(np.tile(rgb, (len(tri) * 3, 1)))
        if 'vertex_color_factors' in command:
            factors=np.asarray(command['vertex_color_factors'])[faces].reshape(-1)
            colors[-len(tri)*3:]=np.clip(np.asarray(colors[-len(tri)*3:])*factors[:,None],0,1).tolist()
        ends.append(len(positions))
    return (np.array(positions, dtype="<f4"), np.array(normals, dtype="<f4"),
            np.array(colors, dtype="<f4"), ends)


def export_glb(path: Path, arrays: tuple, recipe: dict) -> None:
    positions, normals, colors, ends = arrays
    buffers = [a.tobytes() for a in (positions, normals, colors)]
    offsets = [0, len(buffers[0]), len(buffers[0]) + len(buffers[1])]
    accessors = [{"bufferView": i, "componentType": 5126, "count": len(positions),
                  "type": "VEC3"} for i in range(3)]
    accessors[0].update(min=positions.min(axis=0).tolist(), max=positions.max(axis=0).tolist())
    doc = {"asset": {"version": "2.0", "generator": "MoM authored recipe v1"},
           "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
           "meshes": [{"name": recipe["id"], "primitives": [{"attributes": {
               "POSITION": 0, "NORMAL": 1, "COLOR_0": 2}, "material": 0}],
               "extras": {"command_ends": ends, "command_ids": [c["id"] for c in recipe["commands"]], "recipe_schema": VERSION}}],
           "materials": [{"doubleSided": True, "pbrMetallicRoughness": {
               "metallicFactor": 0, "roughnessFactor": 1}}],
           "accessors": accessors,
           "bufferViews": [{"buffer": 0, "byteOffset": offset, "byteLength": len(data),
                            "target": 34962} for offset, data in zip(offsets, buffers, strict=True)],
           "buffers": [{"byteLength": sum(map(len, buffers))}]}
    from monsterforge.constructor_fur_texture import recipe_uvs, texture
    uv,kind=recipe_uvs(recipe)
    if kind:
        uvbytes=uv.tobytes();png=texture(kind)[1];png+=b'\0'*(-len(png)%4)
        uv_offset=sum(map(len,buffers));buffers.extend([uvbytes,png])
        doc['bufferViews'].extend([{'buffer':0,'byteOffset':uv_offset,'byteLength':len(uvbytes),'target':34962},{'buffer':0,'byteOffset':uv_offset+len(uvbytes),'byteLength':len(png)}])
        doc['accessors'].append({'bufferView':3,'componentType':5126,'count':len(positions),'type':'VEC2'})
        doc['meshes'][0]['primitives'][0]['attributes']['TEXCOORD_0']=3
        doc['images']=[{'bufferView':4,'mimeType':'image/png'}]
        doc['samplers']=[{'magFilter':9729,'minFilter':9729,'wrapS':10497,'wrapT':10497}]
        doc['textures']=[{'source':0,'sampler':0}]
        doc['materials'][0]['pbrMetallicRoughness']['baseColorTexture']={'index':0}
        doc['buffers'][0]['byteLength']=sum(map(len,buffers))
    # Team regions retain semantic identity after the authoring palette is baked.
    team_materials = set(recipe.get('team_materials', ('cloth', 'banner', 'team')))
    mask = np.zeros(len(positions), dtype='<f4')
    begin = 0
    for command, end in zip(recipe['commands'], ends, strict=True):
        if command.get('team_color', command['material'] in team_materials):
            mask[begin:end] = 1
        begin = end
    if mask.any():
        offset = sum(map(len, buffers))
        packed = mask.tobytes()
        buffers.append(packed)
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': offset, 'byteLength': len(packed), 'target': 34962})
        doc['meshes'][0]['primitives'][0]['attributes']['_TEAM_MASK'] = len(doc['accessors'])
        doc['accessors'].append({'bufferView': len(doc['bufferViews']) - 1, 'componentType': 5126, 'count': len(mask), 'type': 'SCALAR'})
        doc['buffers'][0]['byteLength'] = sum(map(len, buffers))
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    binary = b''.join(buffers)
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 28+len(encoded)+len(binary))
                     + struct.pack("<I4s", len(encoded), b"JSON") + encoded
                     + struct.pack("<I4s", len(binary), b"BIN\0") + binary)


def camera(positions: np.ndarray, yaw: float, pitch: float) -> np.ndarray:
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    rotation = np.array([[cy, 0, -sy], [sy*sp, cp, cy*sp], [sy*cp, -sp, cy*cp]])
    return positions @ rotation.T


def render_png(path: Path, arrays: tuple, *, yaw: float = .65, pitch: float = .18,
               size: int = 448, count: int | None = None, background: int = 30, recipe: dict | None = None) -> dict:
    """Orthographic CPU rasterizer with depth testing and diffuse vertex lighting."""
    positions, normals, colors, _ = arrays
    uv=tex=None
    if recipe is not None:
        from monsterforge.constructor_fur_texture import recipe_uvs, texture
        uv,kind=recipe_uvs(recipe)
        if kind:tex=texture(kind)[0]
    transformed = camera(positions, yaw, pitch)
    minimum, maximum = transformed.min(axis=0), transformed.max(axis=0)
    center = (minimum + maximum) / 2
    scale = size * .82 / max(maximum[:2] - minimum[:2])
    points = transformed - center
    points[:, :2] *= scale
    points[:, 0] += size / 2
    points[:, 1] = size / 2 - points[:, 1]
    rgb = np.full((size, size, 3), background, dtype=np.uint8)
    depth = np.full((size, size), -np.inf)
    lighting = np.array([-.4, .7, .6])
    lighting /= np.linalg.norm(lighting)
    n = camera(normals, yaw, pitch)
    shades = np.clip(.55 + .45 * np.abs(n @ lighting), 0, 1)
    flat_colors = np.clip(colors * shades[:, None] * 255, 0, 255).astype(np.uint8)
    for i in range(0, count if count is not None else len(points), 3):
        triangle = points[i:i+3]
        x0, y0 = np.maximum(np.floor(triangle[:, :2].min(axis=0)).astype(int), 0)
        x1, y1 = np.minimum(np.ceil(triangle[:, :2].max(axis=0)).astype(int), size - 1)
        if x0 > x1 or y0 > y1:
            continue
        a, b, c = triangle
        denominator = (b[1]-c[1])*(a[0]-c[0]) + (c[0]-b[0])*(a[1]-c[1])
        if abs(denominator) < 1e-8:
            continue
        yy, xx = np.mgrid[y0:y1+1, x0:x1+1]
        xx, yy = xx + .5, yy + .5
        u = ((b[1]-c[1])*(xx-c[0]) + (c[0]-b[0])*(yy-c[1])) / denominator
        v = ((c[1]-a[1])*(xx-c[0]) + (a[0]-c[0])*(yy-c[1])) / denominator
        w = 1-u-v
        z = u*a[2] + v*b[2] + w*c[2]
        region = depth[y0:y1+1, x0:x1+1]
        visible = (u >= -1e-6) & (v >= -1e-6) & (w >= -1e-6) & (z > region)
        region[visible] = z[visible]
        if np.array_equal(flat_colors[i], flat_colors[i+1]) and np.array_equal(flat_colors[i], flat_colors[i+2]):
            rgb[y0:y1+1, x0:x1+1][visible] = flat_colors[i]
        else:
            shaded = (u[..., None]*flat_colors[i]+v[..., None]*flat_colors[i+1]
                      +w[..., None]*flat_colors[i+2])
            rgb[y0:y1+1, x0:x1+1][visible] = np.clip(shaded[visible], 0, 255).astype(np.uint8)
        if tex is not None:
            tuv=u[...,None]*uv[i]+v[...,None]*uv[i+1]+w[...,None]*uv[i+2]
            sample=np.floor((tuv%1)*tex.shape[0]).astype(int)%tex.shape[0]
            factor=tex[sample[...,1],sample[...,0]].astype(float)/255
            region_rgb=rgb[y0:y1+1,x0:x1+1]
            region_rgb[visible]=np.clip(region_rgb[visible]*factor[visible],0,255).astype(np.uint8)
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind+payload))
    raw = b"".join(b"\0" + row.tobytes() for row in rgb)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
    return {"projection": "orthographic", "yaw_radians": yaw, "pitch_radians": pitch,
            "size": [size, size], "center_camera": center.tolist(), "pixels_per_metre": scale}
