"""Rebuild a tiny example release from mathematical shapes, without imported art.

Everything is derived in /tmp. These examples exercise the actual SDK, HTTP
catalog and renderer; they do not replace the shared character/animation code.
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
import tempfile
import zlib
from pathlib import Path

from .paths import STYLE_PATH, cache_directory
from .serialization import encoded


def _block() -> bytes:
    faces = [
        ((0, 0, 1), [(-.5, 0, .5), (.5, 0, .5), (.5, 1, .5), (-.5, 1, .5)]),
        ((0, 0, -1), [(.5, 0, -.5), (-.5, 0, -.5), (-.5, 1, -.5), (.5, 1, -.5)]),
        ((-1, 0, 0), [(-.5, 0, -.5), (-.5, 0, .5), (-.5, 1, .5), (-.5, 1, -.5)]),
        ((1, 0, 0), [(.5, 0, .5), (.5, 0, -.5), (.5, 1, -.5), (.5, 1, .5)]),
        ((0, 1, 0), [(-.5, 1, .5), (.5, 1, .5), (.5, 1, -.5), (-.5, 1, -.5)]),
        ((0, -1, 0), [(-.5, 0, -.5), (.5, 0, -.5), (.5, 0, .5), (-.5, 0, .5)]),
    ]
    positions = [component for _, vertices in faces for point in vertices for component in point]
    normals = [component for normal, _ in faces for _ in range(4) for component in normal]
    indices = [4 * number + offset for number in range(6) for offset in (0, 1, 2, 0, 2, 3)]
    position_bytes = struct.pack('<72f', *positions)
    normal_bytes = struct.pack('<72f', *normals)
    binary = position_bytes + normal_bytes + struct.pack('<36H', *indices)
    document = {
        'asset': {'version': '2.0', 'generator': 'Monster Forge mathematical example v1'},
        'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'mesh': 0}],
        'buffers': [{'byteLength': len(binary)}],
        'bufferViews': [
            {'buffer': 0, 'byteOffset': 0, 'byteLength': len(position_bytes)},
            {'buffer': 0, 'byteOffset': len(position_bytes), 'byteLength': len(normal_bytes)},
            {'buffer': 0, 'byteOffset': len(position_bytes) + len(normal_bytes), 'byteLength': 72},
        ],
        'accessors': [
            {'bufferView': 0, 'componentType': 5126, 'count': 24, 'type': 'VEC3',
             'min': [-.5, 0, -.5], 'max': [.5, 1, .5]},
            {'bufferView': 1, 'componentType': 5126, 'count': 24, 'type': 'VEC3'},
            {'bufferView': 2, 'componentType': 5123, 'count': 36, 'type': 'SCALAR'},
        ],
        'meshes': [{'primitives': [{'attributes': {'POSITION': 0, 'NORMAL': 1},
                                    'indices': 2, 'material': 0}]}],
        'materials': [{'pbrMetallicRoughness': {'baseColorFactor': [.46, .59, .52, 1],
                                               'roughnessFactor': 1, 'metallicFactor': 0}}],
    }
    header = encoded(document).rstrip(b'\n')
    header += b' ' * (-len(header) % 4)
    return (struct.pack('<4sII', b'glTF', 2, 28 + len(header) + len(binary))
            + struct.pack('<I4s', len(header), b'JSON') + header
            + struct.pack('<I4s', len(binary), b'BIN\0') + binary)


def _png(*, icon: bool) -> bytes:
    size = 32
    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            if icon:
                color = (212, 182, 126, 255) if abs(x - 15.5) + abs(y - 15.5) < 12 else (30, 30, 30, 255)
            else:
                color = (91, 111, 83, 255) if (x // 8 + y // 8) % 2 else (107, 123, 91, 255)
            raw.extend(color)

    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload))

    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def create_demo(root: Path | None = None) -> Path:
    """Materialize deterministic, hash-addressed example files outside Git."""
    root = cache_directory('demo') if root is None else Path(root).resolve()
    media = root / 'media'
    media.mkdir(parents=True, exist_ok=True)

    def write_file(folder, stem, extension, content):
        digest = hashlib.sha256(content).hexdigest()
        path = folder / f'{stem}.{digest[:24]}.{extension}'
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() != content:
            raise ValueError('Immutable demo example changed: ' + path.name)
        if not path.exists():
            path.write_bytes(content)
        return path

    entries = []
    for identity, kind, title, extension, blob in (
        ('decoration.example.block', 'decoration', 'Гранёный блок', 'glb', _block()),
        ('icon.example.diamond', 'icon', 'Ромб', 'png', _png(icon=True)),
        ('terrain.example.ground', 'terrain', 'Земля', 'png', _png(icon=False)),
    ):
        path = write_file(media / 'examples', identity, extension, blob)
        role = 'model' if kind == 'decoration' else 'image'
        entries.append({
            'id': identity, 'kind': kind, 'title': title, 'revision': 1,
            'group': 'Примеры', 'tags': ['example', 'generated'],
            'provenance': {'origin': 'monsterforge.demo', 'schema_version': 1},
            'files': {role: {'path': path.relative_to(media).as_posix(),
                             'sha256': hashlib.sha256(blob).hexdigest(), 'size_bytes': len(blob),
                             'media_type': 'model/gltf-binary' if kind == 'decoration' else 'image/png'}},
        })
    styles = root / 'styles/icons'
    style = json.loads(STYLE_PATH.read_text(encoding='utf-8'))
    prompt = '\n'.join(style.values())
    source = write_file(styles, 'style', 'txt', (prompt + '\n').encode())
    reference = write_file(styles, 'reference', 'png', _png(icon=True))
    (styles / 'profile.json').write_bytes(encoded({
        'schema_version': 1, 'prompt': prompt,
        'source': source.name, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'reference': reference.name, 'reference_sha256': hashlib.sha256(reference.read_bytes()).hexdigest(),
    }))
    for name in ('prompts.json', 'prompts-mom.json'):
        (styles / name).write_bytes(encoded({'schema_version': 1, 'style_profile': style, 'prompt': prompt}))
    catalog = encoded({'schema_version': 1, 'assets': entries, 'aliases': {}})
    with tempfile.NamedTemporaryFile(dir=media, prefix='.catalog-', delete=False) as output:
        pending = Path(output.name)
        try:
            output.write(catalog)
            output.flush()
            os.replace(pending, media / 'catalog.json')
        finally:
            pending.unlink(missing_ok=True)
    return root
