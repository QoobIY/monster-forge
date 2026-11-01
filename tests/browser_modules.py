"""Explicit collaborators for the existing Node editor workflow scenarios."""

from pathlib import Path

NODE_MODULE_PRELUDE = "import {createRequire} from 'node:module'; const require=createRequire(import.meta.url);\n"


def constructor_source():
    base = (Path(__file__).resolve().parents[1] / 'static/characters').as_uri()
    imports = '\n'.join(
        f"import {{{symbol}}} from '{base}/{filename}.js';"
        for symbol, filename in (
            ('createState', 'state'), ('createApi', 'api'), ('createSelection', 'selection'),
            ('createPalettes', 'palettes'), ('createOptions', 'options'),
            ('createPreview', 'preview'), ('createRevisions', 'revisions'),
        )
    )
    return imports + r"""
let catalog,settings,viewer,ready=false,actionBusy=false,linkedLimbs=true,viewingPublished=false,serial=0,savedSerial=0,timer,controller;
const state={
 get catalog(){return catalog;},set catalog(value){catalog=value;},
 get settings(){return settings;},set settings(value){settings=value;},
 get viewer(){return viewer;},set viewer(value){viewer=value;},
 get ready(){return ready;},set ready(value){ready=value;},
 get actionBusy(){return actionBusy;},set actionBusy(value){actionBusy=value;},
 get linkedLimbs(){return linkedLimbs;},set linkedLimbs(value){linkedLimbs=value;},
 get viewingPublished(){return viewingPublished;},set viewingPublished(value){viewingPublished=value;},
 get serial(){return serial;},set serial(value){serial=value;},
 get savedSerial(){return savedSerial;},set savedSerial(value){savedSerial=value;},
 get timer(){return timer;},set timer(value){timer=value;},
 get controller(){return controller;},set controller(value){controller=value;}
};
const $=id=>document.getElementById(id),API='/creature-workshop/constructor';
const api=createApi({fetch:(...args)=>fetch(...args)});
let request=(...args)=>api.request(...args);
const notifyError=e=>{$('error').hidden=false;$('error').textContent=e.message||String(e);};
const actions=()=>{for(const id of ['save','export','screenshot'])$(id).disabled=!ready||actionBusy||(viewingPublished&&id!=='screenshot');};
let refreshPartPicker=()=>{},renderOptions,refreshSelection,renderAttributeOptions,card,renderSlots,loadSaved;
let commit=()=>{refreshSelection();schedule();};
const selection=createSelection(state,{onChange:()=>commit(),onOptionsChanged:()=>renderOptions()});
const palettes=createPalettes(state,{document,onChange:()=>commit()});
const picker={refreshPartPicker:()=>refreshPartPicker(),openPart:(...args)=>openPart(...args),showWorkspace:(...args)=>showWorkspace(...args)};
const options=createOptions(state,{document,selection,picker,palettes,createCard:(...args)=>card(...args),onRefresh:()=>refreshSelection(),renderAttributes:()=>renderAttributeOptions()});
renderOptions=(...args)=>options.renderOptions(...args);refreshSelection=(...args)=>options.refreshSelection(...args);renderAttributeOptions=(...args)=>options.renderAttributeOptions(...args);card=(...args)=>options.card(...args);
const numberPartCards=(...args)=>options.numberPartCards(...args),isCardSelected=(...args)=>options.isCardSelected(...args),chooseField=(...args)=>selection.chooseField(...args);
const preview=createPreview(state,{document,api:{request:(...args)=>request(...args)},notifyError,updateActions:actions});
let schedule=(...args)=>preview.schedule(...args),updatePreview=(...args)=>preview.updatePreview(...args);
renderSlots=(...args)=>preview.renderSlots(...args);
const revisions=createRevisions(state,{document,api:{request:(...args)=>request(...args)},selection:{commit:()=>commit()},preview:{renderSlots:(...args)=>renderSlots(...args)},options:{renderOptions:(...args)=>renderOptions(...args)},picker,notifyError,updateActions:actions,reloadSaved:()=>loadSaved()});
loadSaved=(...args)=>revisions.loadSaved(...args);
const showPublished=(...args)=>revisions.showPublished(...args),editSaved=(...args)=>revisions.editSaved(...args),saveAssembly=(...args)=>revisions.saveAssembly(...args);
"""
