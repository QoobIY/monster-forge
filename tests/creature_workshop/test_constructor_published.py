"""Published MOM appearances remain visible and retain exact runtime geometry."""
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from monster_forge_sdk import AssetStore
from monster_forge_sdk.characters import read_character_model
from monsterforge import create_app
from monsterforge import workshop_constructor as editor
from monsterforge.constructor_published import list_published
from tests.browser_modules import NODE_MODULE_PRELUDE, constructor_source


class PublishedConstructorTests(unittest.TestCase):
    def test_published_appearances_are_listed_even_without_local_saves(self):
        client = create_app().test_client()
        with tempfile.TemporaryDirectory() as temporary, patch.object(editor, 'STORE', Path(temporary)):
            data = client.get('/creature-workshop/constructor/revisions').get_json()
        self.assertEqual(data['revisions'], [])
        published = {item['asset_id']: item for item in data['published']}
        for asset in ('character.maps.mom_rpg.classes.mage.body',
                      'character.maps.mom_rpg.classes.viking.body',
                      'character.maps.mom_rpg.classes.witcher.body',
                      'character.shared.mom_skins.knight.body'):
            self.assertIn(asset, published)
            self.assertNotIn('edit_error', published[asset])
            editor.validate_settings(published[asset]['settings'])
        self.assertEqual(len(published), len(data['published']))

    def test_every_published_view_uses_hash_pinned_parts_and_can_be_downloaded(self):
        client = create_app().test_client()
        store = AssetStore()
        # Viewing an existing publication must never rebuild it with current rules.
        with patch.object(editor, 'build', side_effect=AssertionError('Unexpected rebuild')):
            for item in [r for r in list_published() if r['asset_id'].startswith('character.maps.mom_rpg.') or r['asset_id']=='character.shared.mom_skins.knight.body']:
                with self.subTest(label=item['label']):
                    with client.get(item['model_url']) as response:
                        self.assertEqual(response.status_code, 200)
                        model = response.get_json()
                    metadata = read_character_model(store.read(item['asset_id']), metadata_only=True)
                    self.assertEqual(model['contract'], metadata['skeleton_id'])
                    self.assertEqual(set(model['parts']), {'whole'})
                    self.assertEqual(model['parts']['whole']['model_sha256'], item['model_sha256'])
                    self.assertTrue(model['parts']['whole']['geometry']['positions'])
                    with client.get(item['download']) as response:
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(hashlib.sha256(response.data).hexdigest(), item['model_sha256'])
                    with client.get(item['preview']) as response:
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.mimetype, 'image/png')

    def test_current_published_settings_match_the_pinned_recipe(self):
        store = AssetStore()
        for item in list_published():
            instruction = json.loads(store.read(item['asset_id'], 'assembly'))
            if 'edit_error' not in item:
                self.assertEqual(item['settings'], editor.validate_settings(instruction['constructor_settings']))

    def test_unknown_publications_and_actions_are_rejected(self):
        client = create_app().test_client()
        for suffix in ('model', 'preview', 'download'):
            self.assertEqual(client.get(f'/creature-workshop/constructor/published/{"0" * 64}/{suffix}').status_code, 404)
            self.assertEqual(client.get(f'/creature-workshop/constructor/published/invalid/{suffix}').status_code, 400)
        item = list_published()[0]
        self.assertEqual(client.get(f'/creature-workshop/constructor/published/{item["id"]}/delete').status_code, 404)

    @unittest.skipUnless(shutil.which('node'), 'Node is required for the saved list behavior check')
    def test_saved_selection_restores_full_settings_and_edits_the_selected_character(self):
        source = constructor_source()
        published = next(p for p in list_published() if p['settings']['race'] == 'quillboar')
        local = editor.default_settings()
        local.update(race='orc', gender='female', face='library-orc-01',
                     outfit='library-orc-01', arms='library-orc-01', legs='library-orc-01')
        local['reference_parts']['arms'] = 2
        script = """
const assert=require('node:assert/strict');
class Element{constructor(){this.children=[];this.textContent='';}append(...nodes){this.children.push(...nodes);}replaceChildren(...nodes){this.children=nodes;}setAttribute(){}}
const elements=new Map();
const document={getElementById:id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);},createElement:()=>new Element()};
const item=%s,local={id:'local-orc',settings:%s,preview:'/local-thumb'};
const initial=%s,exact={whole:{glb:'exact-original-model'}},editable={head:{glb:'edited-head'},torso:{glb:'edited-torso'}};
let pendingExact=null,previewSettings;
const fetch=async (path,options)=>({ok:true,json:async()=>{
 if(path.endsWith('/revisions'))return {revisions:[local],published:[item]};
 if(path.endsWith('/preview')){previewSettings=JSON.parse(options.body);return {contract:'humanoid_v1',parts:editable,triangles:15,bind_bones:[],warnings:[]};}
 if(pendingExact)return await pendingExact;
 return {contract:'humanoid_v1',parts:exact,triangles:12,bind_bones:[]};
}});
let openedPart='saved',workspace='assembly';function openPart(part){openedPart=part;}function showWorkspace(key){workspace=key;}
%s
(async()=>{
catalog={all_races:[{id:'human'},{id:'quillboar'},{id:'orc'}],settings_version:5};catalog.races=catalog.all_races;settings=structuredClone(initial);
let shown,rendered;viewer={slot:'torso',setBones:()=>{},cancelPendingLoads:()=>{},setParts:async parts=>{shown=parts;return true;}};renderSlots=()=>{};
renderOptions=()=>{rendered=structuredClone(settings);};refreshSelection=()=>{};
await loadSaved();
const flatten=n=>[n,...n.children.flatMap(flatten)];const nodes=flatten($('saved-list'));
assert(nodes.some(n=>n.textContent===item.label));
assert.equal(nodes.filter(n=>n.textContent==='Редактировать').length,2);
await nodes.find(n=>n.textContent==='Посмотреть опубликованную версию').onclick();
assert.deepEqual(shown,exact);assert.equal(viewingPublished,true);
assert.deepEqual(settings,item.settings);assert.deepEqual(rendered,item.settings);
assert.equal(openedPart,null);assert.equal(viewer.slot,'');
assert.equal($('save').disabled,true);assert.equal($('export').disabled,true);assert.equal($('screenshot').disabled,false);
// Changing a detail after the exact MOM view must rebuild that character,
// including its race, body, reference selections, colours and gender.
settings.decor.emblem='none';commit();clearTimeout(timer);await updatePreview(serial);
assert.deepEqual(previewSettings,{...item.settings,decor:{...item.settings.decor,emblem:'none'}});
assert.deepEqual(shown,editable);assert.equal(viewingPublished,false);assert.equal($('save').disabled,false);
// Local selections leave the saved list and preserve independent arm choices.
openedPart='saved';await nodes.filter(n=>n.textContent==='Редактировать')[1].onclick();
assert.deepEqual(settings,local.settings);assert.equal(linkedLimbs,false);assert.equal(openedPart,null);
assert.equal(workspace,'body-parts');
clearTimeout(timer);await updatePreview(serial);assert.deepEqual(previewSettings,local.settings);
// A slow previous publication must not replace a more recent selection.
let release;pendingExact=new Promise(resolve=>{release=resolve;});
const old=showPublished(item);await new Promise(resolve=>setImmediate(resolve));
await editSaved(local);clearTimeout(timer);await updatePreview(serial);
release({contract:'humanoid_v1',parts:exact,triangles:12,bind_bones:[]});await old;
assert.deepEqual(settings,local.settings);assert.deepEqual(shown,editable);
})().catch(e=>{console.error(e);process.exitCode=1;});
""" % (json.dumps(published, ensure_ascii=False), json.dumps(local), json.dumps(editor.default_settings()), source)  # noqa: UP031 — Keep JavaScript braces and $ helpers literal in this fixture.
        result = subprocess.run(['node', '--input-type=module', '-e', NODE_MODULE_PRELUDE + script], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
