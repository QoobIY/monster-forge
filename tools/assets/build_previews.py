"""Publish missing scenery thumbnails using MoM's native importer and renderer."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from monster_forge_sdk import AssetIntegrityError, AssetNotFound, AssetStore
from monsterforge.paths import cache_directory

ROOT = Path(__file__).resolve().parents[2]


def missing_previews(store: AssetStore) -> list:
    missing = []
    for asset in store.list('decoration'):
        try:
            store.path(asset.id, 'preview')
        except (AssetNotFound, AssetIntegrityError, FileNotFoundError):
            missing.append(asset)
    return missing


def publish_previews(root: Path, previews: dict[str, Path], release_id: str) -> int:
    store = AssetStore(root)
    if store.release_id != release_id:
        raise ValueError('Catalog changed during rendering; run preview preparation again')
    paths = [root/'media'/name for name in ('imported_catalog.json', 'catalog.json')]
    snapshots = {p: p.read_bytes() for p in paths}
    documents = {p: json.loads(payload) for p, payload in snapshots.items()}
    updates = {}
    for identity, image in previews.items():
        asset = store.get(identity)
        payload = image.read_bytes()
        with Image.open(io.BytesIO(payload)) as png:
            if png.format != 'PNG':
                raise ValueError('Renderer must produce PNG previews')
            png.verify()
        checksum = hashlib.sha256(payload).hexdigest()
        target = root/'media/decorations/previews'/(identity+'.'+checksum[:20]+'.png')
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != payload:
            raise ValueError('Immutable preview conflict: '+identity)
        if not target.exists():
            target.write_bytes(payload)
        updates[identity] = ({'path': target.relative_to(root/'media').as_posix(),
                              'sha256': checksum, 'size_bytes': len(payload),
                              'media_type': 'image/png'}, asset.files['model'].sha256)
    if any(p.read_bytes() != original for p, original in snapshots.items()):
        raise ValueError('Catalog changed during preview publication; retry')
    for path, document in documents.items():
        for row in document['assets']:
            if row['id'] in updates:
                preview, source_hash = updates[row['id']]
                row['files']['preview'] = preview
                row['preview_model_sha256'] = source_hash
        payload = (json.dumps(document, ensure_ascii=False, indent=2)+'\n').encode()
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name+'.', delete=False) as output:
                temporary = Path(output.name)
                output.write(payload)
            os.replace(temporary, path)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
    return len(updates)


def build_previews(root: Path = ROOT, *, renderer: Path | None = None,
                   media: Path | None = None) -> int:
    store = AssetStore(root)
    assets = missing_previews(store)
    if not assets:
        print('All scenery previews are ready')
        return 0
    consumer = root.parent/'machine-of-monsters'
    renderer = renderer or consumer/'build/native/mom-scenery-review'
    media = media or consumer/'media'
    if not renderer.is_file():
        raise FileNotFoundError('Build mom-scenery-review or pass --renderer')
    work = cache_directory('library-previews', root=root) / store.release_id[:16]
    work.mkdir(parents=True, exist_ok=True)
    rows, keys = [], {}
    for asset in assets:
        key = 'preview_'+hashlib.sha256(asset.id.encode()).hexdigest()[:24]
        path = 'assets/forge/'+asset.files['model'].sha256[:24]+'.glb'
        rows.append({'key': key, 'before_path': path, 'after_path': path})
        keys[asset.id] = work/(key+'-after.png')
    manifest = work/'models.json'
    manifest.write_text(json.dumps(rows, indent=2)+'\n')
    subprocess.run([str(renderer.resolve()), str(media.resolve()), str(root.resolve()),
                    str(manifest), str(work)], check=True)
    count = publish_previews(root, keys, store.release_id)
    print('Published', count, 'scenery previews')
    return count


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--renderer', type=Path)
    parser.add_argument('--media', type=Path)
    args = parser.parse_args()
    build_previews(args.root, renderer=args.renderer, media=args.media)
