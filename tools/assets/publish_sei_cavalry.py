import hashlib
import json
from pathlib import Path

from monster_forge_sdk import AssetStore

from machine_of_monsters.content.map_assets import validate_glb

root=Path(__file__).resolve().parents[2];store=AssetStore(root);donor=store.get('decoration.mom_rpg.sei.cavalry_guard.v5');ref=store.file(donor.id,'model');count=validate_glb(store.path(donor.id))
payload=(json.dumps({'schema_version':1,'skeleton_id':'humanoid_v1','slot':'whole','bind_profile':'canonical','model_sha256':ref.sha256,'bone_palette':['root'],'skin_indices':[[0,0,0,0]]*count,'skin_weights':[[1,0,0,0]]*count},separators=(',',':'))+'\n').encode();path=root/'media/decorations/mom_rpg/v5/sei/cavalry_guard/guard.weights.json'
if path.exists() and path.read_bytes()!=payload:raise ValueError('Immutable weights changed')
path.write_bytes(payload);p=root/'media/imported_catalog.json';data=json.loads(p.read_text());entry={'id':'character.mom_rpg.sei.cavalry_guard.v2','kind':'character','title':'Конный страж Сея · Стационарная оборона','revision':1,'group':'MOM RPG','tags':['mom_rpg','sei','cavalry','guard','stationary','humanoid_v1'],'files':{'model':{'path':ref.path,'sha256':ref.sha256,'size_bytes':ref.size_bytes,'media_type':ref.media_type},'weights':{'path':path.relative_to(root/'media').as_posix(),'sha256':hashlib.sha256(payload).hexdigest(),'size_bytes':len(payload),'media_type':'application/json'}}}
old=next((a for a in data['assets'] if a['id']==entry['id']),None)
if old and old!=entry:raise ValueError('Immutable character changed')
if not old:data['assets'].append(entry)
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
from tools.assets.build_catalog import build_catalog

build_catalog(root);print('Cavalry guard',count,'vertices, root-only stationary binding')
