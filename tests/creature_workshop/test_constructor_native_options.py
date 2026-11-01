"""Published constructor recipes must remain fully selectable in the editor."""
import json
import shutil
import subprocess
import unittest
from unittest.mock import patch

from flask import Response

from monsterforge import create_app
from monsterforge.constructor_cache import artifact_index
from monsterforge.constructor_published import list_published
from monsterforge.constructor_thumbnails import selector
from monsterforge.paths import ROOT
from monsterforge.workshop_constructor import catalog
from tests.browser_modules import NODE_MODULE_PRELUDE, constructor_source


@unittest.skipUnless(shutil.which('node'), 'Node is required for constructor UI checks')
class NativeOptionTests(unittest.TestCase):
    def test_all_selected_parts_of_witcher_mage_and_viking_are_visible_and_replaceable(self):
        data = catalog()
        human = next(r for r in data['races'] if r['id'] == 'human')
        ui = {k: data[k] for k in ('defaults', 'colors', 'decor', 'features', 'hair', 'forms', 'eyes')}
        ui.update(races=[human], all_races=[human], cards_version=data['cards_version'],
                  face_labels={k: v for k, v in data['face_labels'].items() if k.startswith('library-human-')},
                  outfits=[o for o in data['outfits'] if o['id'].startswith(('library-human-', 'costume-'))],
                  back=[b for b in data['back'] if b['contract'] == 'humanoid_v1'])
        identities = {'character.maps.mom_rpg.classes.' + name + '.body' for name in ('witcher', 'mage', 'viking')}
        published = [p for p in list_published() if p['asset_id'] in identities]
        self.assertEqual(len(published), 3)
        source = constructor_source()
        script = """
const assert=require('node:assert/strict');
class Element{constructor(){this.children=[];this.dataset={};}replaceChildren(...c){this.children=c;}append(...c){this.children.push(...c);}closest(){return this;}querySelector(){return new Element();}setAttribute(){}}
const elements=new Map();const document={getElementById:id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);},createElement:()=>new Element()};
%s
catalog=%s;const publications=%s;viewer={contract:'humanoid_v1',setBones(){}};
let cards=[],changed=0;const images=new Set();
card=(container,option,field,choose)=>{cards.push({container,field,choose,...option});if(option.image)images.add(option.image);};
renderAttributeOptions=()=>{};refreshSelection=()=>{};refreshPartPicker=()=>{};commit=()=>{changed++;};
for(const item of publications){
 settings=structuredClone(item.settings);linkedLimbs=true;cards=[];const before=JSON.stringify(settings);renderOptions();
 assert.equal(JSON.stringify(settings),before,'Opening native controls must not replace saved choices');
 const expected={face:settings.face,hair:settings.hair,form:settings.form,eye_shape:settings.eye_shape,outfit:settings.outfit,arms:settings.arms,legs:settings.legs,back:settings.back??''};
 for(const [key,value] of Object.entries(settings.decor))expected['decor.'+key]=value;
 for(const [key,value] of Object.entries(settings.features))expected['features.'+key]=value;
 for(const [field,value] of Object.entries(expected)){
  const selected=cards.filter(c=>c.field===field&&String(c.id)===String(value));
  assert.equal(selected.length,1,item.label+' missing/duplicate '+field+'='+value);
  const numberedHair=field==='hair'&&settings.reference_parts.hair;
  assert.equal(isCardSelected(field,value),!Boolean(numberedHair),item.label+' wrong highlight for '+field);
  if(numberedHair)assert(isCardSelected('reference_parts.hair',String(numberedHair)),item.label+' missing numbered hairstyle');
 }
 // Switching to a native costume clears its numeric override and uses that
 // actual library part rather than silently retaining the reference clothes.
 settings.reference_parts[settings.gender+'_clothes']=2;
 assert.equal(isCardSelected('outfit',settings.outfit),false);
 const replacement=cards.find(c=>c.field==='outfit'&&c.id!==settings.outfit);
 replacement.choose(replacement.id);
 assert.equal(settings.outfit,replacement.id);assert.equal(settings.reference_parts.male_clothes,0);assert.equal(settings.reference_parts.female_clothes,0);
 assert(isCardSelected('outfit',replacement.id));
 // Numeric facial and beard overrides must win the active-card highlight.
 settings.reference_parts[settings.gender+'_faces']=3;
 assert.equal(isCardSelected('face',settings.face),false);
 assert(isCardSelected('reference_parts.'+settings.gender+'_faces','3'));
 settings.reference_parts.beards=4;assert.equal(isCardSelected('decor.beard',settings.decor.beard),false);
 assert(isCardSelected('reference_parts.beards','4'));
 const beard=cards.find(c=>c.field==='decor.beard'&&c.id==='pointed');beard.choose('pointed');
 assert.equal(settings.reference_parts.beards,0);assert(isCardSelected('decor.beard','pointed'));
 assert.equal(isCardSelected('reference_parts.beards','0'),false);
}
assert(changed>=6);
process.stdout.write(JSON.stringify([...images]));
""" % (source, json.dumps(ui, ensure_ascii=False), json.dumps(published, ensure_ascii=False))  # noqa: UP031 — Preserve literal JavaScript braces and $ helpers.
        result = subprocess.run(['node', '--input-type=module', '-e', NODE_MODULE_PRELUDE + script], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        available = artifact_index()
        def image_source(root, name):
            path = (root / name).resolve()
            present = path.is_file() or path.relative_to(ROOT).as_posix() in available or selector(path) is not None
            return Response(status=200 if present else 404, mimetype='image/png')
        with create_app().test_client() as client, patch('monsterforge.creature_workshop._read_file', side_effect=image_source):
            missing = [url for url in json.loads(result.stdout) if client.get(url).status_code != 200]
        self.assertFalse(missing, str(sorted({url.split('/v28/')[-1].split('?')[0] for url in missing})))

    def test_unified_grid_preserves_choices_and_switches_between_both_sources(self):
        source = constructor_source()
        script = r"""
const assert=require('node:assert/strict');
class Element{
 constructor(){this.children=[];this.dataset={};this.attributes={};}
 append(...children){this.children.push(...children);}
 setAttribute(key,value){this.attributes[key]=value;}
 querySelector(selector){return this.children.find(c=>c.className===selector.slice(1))||null;}
}
const elements=new Map();
const document={getElementById:id=>{if(!elements.has(id)){const e=new Element();e.id=id;elements.set(id,e);}return elements.get(id);},createElement:()=>new Element()};
%s
catalog={races:[{id:'human',attribute_options:{male:{male_faces:[1],male_clothes:[2],arms:[3],eyes:[4],gloves:[5]}}}],attribute_library:['male_faces','male_clothes','arms','eyes','gloves'].map(id=>({id,label:id}))};
settings={race:'human',gender:'male',face:'library-human-01',outfit:'library-human-01',arms:'library-human-01',legs:'library-human-01',eye_shape:'original',reference_parts:{male_faces:0,male_clothes:0,arms:0,eyes:0,gloves:0},colors:{},features:{},decor:{}};
commit=()=>{};
card('face-cards',{id:settings.face,label:'Лицо 01',number:1},'face',id=>chooseField('face',id));
card('outfit-cards',{id:settings.outfit,label:'Рыцарь',number:1},'outfit',id=>chooseField('outfit',id));
card('eye-cards',{id:'original',label:'Как у лица'},'eye_shape',id=>chooseField('eye_shape',id));
const before=JSON.stringify(settings);renderAttributeOptions();numberPartCards();
assert.equal(JSON.stringify(settings),before,'Rendering must preserve the saved assembly');
assert(![...elements.keys()].some(id=>id.startsWith('attribute-')),'No separate source grids');
const faces=$('face-cards').children;
assert.deepEqual(faces.map(c=>c.dataset.field),['face','reference_parts.male_faces']);
assert.deepEqual(faces.map(c=>c.querySelector('.card-number').textContent),['01','02']);
assert.deepEqual(faces.map(c=>c.querySelector('.card-label').textContent),['Голова 01','Голова 02']);
assert.equal($('outfit-cards').children[1].querySelector('.card-label').textContent,'Костюм 02');
assert.equal($('eye-cards').children.length,2,'Only one default option for eyes');
faces[1].onclick();assert.equal(settings.reference_parts.male_faces,1);assert(isCardSelected('reference_parts.male_faces','1'));assert(!isCardSelected('face',settings.face));
faces[0].onclick();assert.equal(settings.reference_parts.male_faces,0);assert(isCardSelected('face',settings.face));
settings.arms='library-human-02';settings.reference_parts.arms=3;
const inherit=$('arms-cards').children.find(c=>c.dataset.field==='reference_parts.arms'&&c.dataset.value==='0');
inherit.onclick();assert.equal(settings.arms,settings.outfit);assert.equal(settings.reference_parts.arms,0);
const gloves=$('arms-cards').children.find(c=>c.dataset.field==='reference_parts.gloves'&&c.dataset.value==='5');
gloves.onclick();assert.equal(settings.reference_parts.gloves,5);
assert.equal(gloves.querySelector('.card-label').textContent,'Перчатки 02');
""" % source  # noqa: UP031 — Preserve literal JavaScript braces and $ helpers.
        result = subprocess.run(['node', '--input-type=module', '-e', NODE_MODULE_PRELUDE + script], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
