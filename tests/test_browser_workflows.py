"""Browser workflow state must survive navigation and out-of-order responses."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.browser_modules import NODE_MODULE_PRELUDE, constructor_source


@unittest.skipUnless(shutil.which('node'), 'Node is required for browser workflow checks')
class BrowserWorkflowTests(unittest.TestCase):
    def run_node(self, source, script):
        result = subprocess.run(
            ['node', '--input-type=module', '-e', NODE_MODULE_PRELUDE + source + '\n' + script],
            capture_output=True, text=True, timeout=20, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_frontend_templates_compile_and_module_files_are_served_as_javascript(self):
        from monsterforge import create_app
        from monsterforge.demo import create_demo

        temporary = tempfile.TemporaryDirectory(prefix='forge-template-test-')
        self.addCleanup(temporary.cleanup)
        app = create_app({'TESTING': True, 'MODE': 'library', 'ASSET_ROOT': create_demo(Path(temporary.name))})
        for filename in app.jinja_env.list_templates():
            app.jinja_env.get_template(filename)
        with app.test_client() as client:
            for route in ('/characters/', '/icons/', '/terrain/', '/decorations/', '/sdk/'):
                response = client.get(route)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_data(as_text=True).count('aria-current="page"'), 1)
            for source in Path('static').rglob('*.js'):
                with client.get('/' + source.as_posix()) as response:
                    self.assertEqual(response.status_code, 200, source)
                    self.assertIn('javascript', response.mimetype, source)

    def test_decoration_without_thumbnail_stays_accessible_and_loads_geometry(self):
        source = f"import {{createLibraryApp}} from '{Path('static/library/app.js').resolve().as_uri()}';\ncreateLibraryApp({{document,fetch,Viewer:ConstructorViewer,IntersectionObserver}}).start();"
        setup = r"""
const assert=require('node:assert/strict');
class Element {
 constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.attributes={};this.value='';this.classList={remove(){}};}
 append(...nodes){for(const node of nodes)this.children.push(...(node.fragment?node.children:[node]));}
 replaceChildren(...nodes){this.children=[];this.append(...nodes);}
 setAttribute(name,value){this.attributes[name]=value;}
 addEventListener(){}
}
const elements=new Map(),page=new Element();page.dataset.kind='decoration';
const document={
 getElementById:id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);},
 createElement:tag=>new Element(tag),createDocumentFragment:()=>Object.assign(new Element(),{fragment:true}),
 querySelector:()=>page,querySelectorAll:()=>document.getElementById('asset-grid').children
};
class IntersectionObserver{observe(){}unobserve(){}}
const displayed=[],requests=[];
class ConstructorViewer {
 constructor(){this.gl={};}
 cancelPendingLoads(){}
 async setParts(parts){displayed.push(parts);return true;}
}
const asset=(id,preview)=>({id,title:id==='plain'?'Без карточки':'С карточкой',kind:'decoration',group:'Test',tags:[],files:{model:{path:id+'.glb'},...(preview?{preview:{path:'preview.png'}}:{})}});
const fetch=async path=>{
 requests.push(path);
 return {ok:true,json:async()=>path.includes('/catalog')?{assets:[asset('plain',false),asset('pictured',true)]}:{parts:{whole:{id:new URL('http://localhost'+path).searchParams.get('id')}},triangles:12}};
};
"""
        self.run_node(setup + source, r"""
(async()=>{
 await new Promise(resolve=>setImmediate(resolve));
 const cards=document.getElementById('asset-grid').children;
 assert.equal(cards.length,2);assert.equal(cards[0].tagName,'BUTTON');
 assert.equal(cards[0].attributes['aria-label'],'Без карточки');
 assert.equal(cards[0].children[0].className,'asset-card-placeholder');
 assert.equal(cards[0].children[0].attributes['aria-hidden'],'true');
 assert.equal(cards[0].children[0].src,undefined,'A model must not become an img source');
 assert.equal(cards[1].children[0].tagName,'IMG');assert.equal(cards[1].children[0].src,'/media/preview.png');
 assert.equal(displayed.at(-1).whole.id,'plain');
 await cards[1].onclick();await cards[0].onclick();
 assert.equal(displayed.at(-1).whole.id,'plain');
 assert.equal(cards[0].attributes['aria-pressed'],'true');assert.equal(cards[1].attributes['aria-pressed'],'false');
 assert.equal(document.getElementById('download-asset').href,'/media/plain.glb?download=1');
 assert(requests.includes('/api/assets/v1/geometry?id=plain'));
 assert.equal(document.getElementById('asset-stage').attributes['aria-busy'],'false');
})().catch(error=>{console.error(error);process.exitCode=1;});
""")

    def test_workspace_tabs_preserve_current_settings_and_support_keyboard(self):
        source = f"import {{createPicker}} from '{Path('static/characters/constructor-picker.js').resolve().as_uri()}';"
        self.run_node(source, r"""
const assert=require('node:assert/strict');
class Element {
 constructor(){this.attributes={};this.hidden=false;}
 setAttribute(name,value){this.attributes[name]=value;}
 focus(){document.activeElement=this;}
}
const elements=new Map();
const document={getElementById:id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);}};
const settings={race:'human',reference_parts:{arms:3},colors:{cloth:'#123456'}},before=JSON.stringify(settings);
const {initWorkspaceTabs}=createPicker({settings,catalog:{races:[]}},{document});
initWorkspaceTabs();document.getElementById('assembly-tab').onclick();
assert.equal(document.getElementById('body-parts-panel').hidden,true);
assert.equal(document.getElementById('assembly-panel').hidden,false);
assert.equal(document.getElementById('randomize').hidden,true);
assert.equal(document.getElementById('assembly-tab').tabIndex,0);
let prevented=false;
document.getElementById('assembly-tab').onkeydown({key:'ArrowLeft',preventDefault(){prevented=true;}});
assert(prevented);assert.equal(document.activeElement,document.getElementById('body-parts-tab'));
assert.equal(document.getElementById('assembly-panel').hidden,true);
assert.equal(document.getElementById('randomize').hidden,false);
assert.equal(JSON.stringify(settings),before);
""")

    def test_cancelled_texture_load_cannot_replace_current_preview(self):
        source = f"import {{ConstructorViewer}} from '{Path('static/characters/constructor-viewer.js').resolve().as_uri()}';"
        self.run_node(source, r"""
const assert=require('node:assert/strict');
(async()=>{
 let release,deleted=0,closed=0;
 global.createImageBitmap=()=>new Promise(resolve=>release=resolve);
 const gl=new Proxy({createTexture:()=>({}),deleteTexture:()=>deleted++},{get:(target,key)=>target[key]||(()=>{})});
 const viewer=Object.create(ConstructorViewer.prototype);
 Object.assign(viewer,{gl,parts:{current:{id:'current'}},loadVersion:0,combine:()=>{throw Error('Cancelled preview was committed');}});
 const pending=viewer.setParts({old:{geometry:{positions:[0,0,0],normals:[0,1,0],colors:[1,1,1],uvs:[0,0],texture:'AA=='}}});
 viewer.cancelPendingLoads();release({close:()=>closed++});
 assert.equal(await pending,false);assert.equal(viewer.parts.current.id,'current');
 assert.equal(deleted,1);assert.equal(closed,1);
})().catch(error=>{console.error(error);process.exitCode=1;});
""")

    def test_saved_list_and_save_result_follow_the_latest_selection(self):
        source = constructor_source()
        setup = r"""
const assert=require('node:assert/strict');
class Element {
 constructor(){this.children=[];this.textContent='';this.attributes={};}
 append(...nodes){this.children.push(...nodes);}
 replaceChildren(...nodes){this.children=nodes;}
 setAttribute(name,value){this.attributes[name]=value;}
}
const elements=new Map();
const document={getElementById:id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);},createElement:()=>new Element()};
"""
        self.run_node(setup + source, r"""
(async()=>{
 catalog={all_races:[{id:'human',label:'Человек'}],races:[{id:'human'}]};
 let older,newer;
 request=async()=>({json:()=>new Promise(resolve=>{if(!older)older=resolve;else newer=resolve;})});
 const first=loadSaved(),second=loadSaved();await new Promise(resolve=>setImmediate(resolve));
 const item=label=>({id:label,label,settings:{race:'human'},preview:'/preview'});
 newer({revisions:[item('Latest')]});await second;
 older({revisions:[item('Old')]});await first;
 const flatten=node=>[node,...node.children.flatMap(flatten)];
 assert(flatten($('saved-list')).some(node=>node.textContent==='Latest'));
 assert(!flatten($('saved-list')).some(node=>node.textContent==='Old'));
 assert.equal($('saved-list').attributes['aria-busy'],'false');assert.equal($('refresh-saved').disabled,false);
 let release,savedSnapshot,refreshes=0;
 loadSaved=async()=>refreshes++;
 request=async(path,payload)=>{savedSnapshot=payload;return {json:()=>new Promise(resolve=>release=resolve)};};
 settings={race:'human',colors:{cloth:'#123456'}};ready=true;serial=1;
 const saving=saveAssembly();await new Promise(resolve=>setImmediate(resolve));
 settings.colors.cloth='#abcdef';serial++;
 release({id:'immutable-revision'});await saving;
 assert.equal(savedSnapshot.colors.cloth,'#123456');assert.equal(settings.colors.cloth,'#abcdef');
 assert.equal($('save-result').children.length,0,'Saving an earlier snapshot must not label the current draft as saved');
 assert.equal(refreshes,1);assert.equal(actionBusy,false);assert.equal($('save').disabled,false);
})().catch(error=>{console.error(error);process.exitCode=1;});
""")
