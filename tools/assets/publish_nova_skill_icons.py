"""Publish reviewed imagegen originals and UI exports as immutable BHM icons."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


def build(jobs_path: Path, results_path: Path, *, finish: bool = False) -> None:
    jobs = {job['key']: job for job in json.loads(jobs_path.read_text())}
    results = json.loads(results_path.read_text())
    media = ROOT/'media'
    catalog_path = media/'imported_catalog.json'
    catalog = json.loads(catalog_path.read_text())
    by_id = {entry['id']: entry for entry in catalog['assets']}
    reference = ROOT/'styles/icons/mom-style-reference.jpg'
    reference_hash = hashlib.sha256(reference.read_bytes()).hexdigest()
    manifest = []
    for result in results:
        job = jobs[result['key']]
        identity = 'icon.ability.nova_skills.v1.'+job['key']
        folder = media/'icons/nova_skills/v1'/job['key']
        folder.mkdir(parents=True, exist_ok=True)
        source = Path(result['path']).read_bytes()
        image = Image.open(io.BytesIO(source))
        if image.width != image.height or image.width < 256:
            raise ValueError('Skill icon must be a square high-resolution original')
        if image.mode == 'RGBA' and image.getchannel('A').getextrema() != (255,255):
            raise ValueError('Skill buttons require an opaque background')
        # Mechanical UI export only. Retain the unmodified generated original.
        preview = image.convert('RGB').resize((256,256), Image.Resampling.LANCZOS)
        buffer = io.BytesIO(); preview.save(buffer, format='PNG')
        recipe = {'schema_version':1,'tool':'imagegen','label':job['label'],
                  'subject':job['subject'],'prompt':result['prompt'],
                  'reference':'styles/icons/mom-style-reference.jpg',
                  'reference_sha256':reference_hash,
                  'source_sha256':hashlib.sha256(source).hexdigest(),
                  'ui_export':{'size':[256,256],'filter':'lanczos','background':'opaque'},
                  'nova_ability_ids':job['abilities']}
        payloads = [('image',folder/'icon.png',buffer.getvalue(),'image/png'),
                    ('source',folder/'source.png',source,'image/png'),
                    ('recipe',folder/'recipe.json',(json.dumps(recipe,ensure_ascii=False,indent=2)+'\n').encode(),'application/json')]
        files = {}
        for role,path,payload,mime in payloads:
            if path.exists() and path.read_bytes()!=payload:
                raise ValueError('Published icon is immutable: '+identity)
            if not path.exists():path.write_bytes(payload)
            files[role] = {'path':path.relative_to(media).as_posix(),
                           'sha256':hashlib.sha256(payload).hexdigest(),
                           'size_bytes':len(payload),'media_type':mime}
        entry = {'id':identity,'kind':'icon','title':job['label'],'revision':1,
                 'group':'Nova',
                 'tags':['nova','ability','imagegen','mom-icons-v1','faceted'],
                 'files':files}
        if identity in by_id and by_id[identity]!=entry:
            raise ValueError('Published catalog entry is immutable: '+identity)
        by_id[identity]=entry
        manifest.append({'key':job['key'],'label':job['label'],'asset':identity,
                         'ability_ids':job['abilities'],'recipe':files['recipe']['path']})
    if finish:
        if len(results)!=len(jobs) or len({r['key'] for r in results})!=len(jobs):
            raise ValueError('Incomplete icon collection')
        path=media/'icons/nova_skills/v1/manifest.json'
        payload=(json.dumps({'schema_version':1,'style':'mom-icons-v1','icons':sorted(manifest,key=lambda r:r['key'])},ensure_ascii=False,indent=2)+'\n').encode()
        if path.exists() and path.read_bytes()!=payload:raise ValueError('Immutable collection manifest')
        path.write_bytes(payload)
        ref={'path':path.relative_to(media).as_posix(),'sha256':hashlib.sha256(payload).hexdigest(),'size_bytes':len(payload),'media_type':'application/json'}
        entry={'id':'icon.collection.nova_skills.v1','kind':'icon','title':'Nova · Способности · Полный набор','revision':1,'group':'Nova','tags':['nova','ability','collection'],'files':{'manifest':ref,'image':by_id['icon.ability.nova_skills.v1.fire_bolt']['files']['image']}}
        previous=by_id.get(entry['id'])
        if previous and previous!=entry:raise ValueError('Immutable collection entry')
        by_id[entry['id']]=entry
    catalog['assets']=list(by_id.values())
    catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    from tools.assets.build_catalog import build_catalog
    build_catalog(ROOT)
    print('Published',len(results),'icons; collection complete:',finish)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('jobs',type=Path);parser.add_argument('results',type=Path)
    parser.add_argument('--finish',action='store_true')
    args=parser.parse_args();build(args.jobs,args.results,finish=args.finish)
