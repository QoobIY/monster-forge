import { createState } from './state.js';
import { createApi } from './api.js';
import { ConstructorViewer } from './constructor-viewer.js';
import { createSelection } from './selection.js';
import { createPalettes } from './palettes.js';
import { createOptions } from './options.js';
import { createPreview } from './preview.js';
import { createRevisions } from './revisions.js';
import { createPicker } from './constructor-picker.js';
import { download } from './api.js';
/** Compose one editor instance. Modules receive state and collaborators explicitly. */
export function createConstructorApp({
  document = globalThis.document,
  fetch = globalThis.fetch,
  Viewer = ConstructorViewer,
} = {}) {
  const state = createState(),
    $ = (id) => document.getElementById(id),
    api = createApi({ fetch });
  function notifyError(e) {
    $('error').hidden = false;
    $('error').textContent = e.message || String(e);
  }
  function actions() {
    for (const id of ['save', 'export', 'screenshot'])
      $(id).disabled =
        !state.ready || state.actionBusy || (state.viewingPublished && id !== 'screenshot');
  }
  const picker = createPicker(state, { document });
  let options, preview;
  const selection = createSelection(state, {
    onChange: () => {
      options.refreshSelection();
      preview.schedule();
    },
    onOptionsChanged: () => options.renderOptions(),
  });
  const palettes = createPalettes(state, { document, onChange: () => selection.commit() });
  options = createOptions(state, { document, selection, picker, palettes });
  preview = createPreview(state, { document, api, notifyError, updateActions: actions });
  const revisions = createRevisions(state, {
    document,
    api,
    selection,
    preview,
    options,
    picker,
    notifyError,
    updateActions: actions,
  });
  function bindControls() {
    const commit = () => selection.commit(),
      referenceMode = () => selection.referenceMode();
    $('randomize').onclick = () => selection.randomize();
    $('link-limbs').onchange = () => {
      state.linkedLimbs = $('link-limbs').checked;
      if (state.linkedLimbs) {
        state.settings.arms = state.settings.legs = state.settings.outfit;
        if (referenceMode()) {
          state.settings.reference_parts.arms = 0;
          state.settings.reference_parts.legs = 0;
        }
      }
      commit();
    };
    $('eye-size').oninput = () => {
      state.settings.eye_size = Number($('eye-size').value) / 100;
      commit();
    };
    $('reset-appearance').onclick = () => {
      for (const k of ['hair', 'eyes', 'skin']) state.settings.colors[k] = null;
      commit();
    };
    $('reset-outfit').onclick = () => {
      state.settings.reference_parts.colorways = 0;
      for (const k of ['cloth', 'accent', 'metal', 'leather', 'secondary'])
        state.settings.colors[k] = null;
      commit();
    };
    $('background').onclick = () => {
      const light = $('background').getAttribute('aria-pressed') !== 'true';
      $('background').setAttribute('aria-pressed', String(light));
      state.viewer.gl?.clearColor(...(light ? [1, 1, 1, 1] : [30 / 255, 30 / 255, 30 / 255, 1]));
      state.viewer.render();
    };
    $('back-view').onclick = () => {
      state.viewer.yaw = Math.PI;
      state.viewer.pitch = 0;
      state.viewer.render();
    };
    $('reset-back').onclick = () => {
      for (const k of ['back_primary', 'back_secondary', 'back_frame'])
        state.settings.colors[k] = null;
      commit();
    };
    $('front-view').onclick = () => state.viewer.reset(true);
    $('reset-view').onclick = () => state.viewer.reset();
    $('show-bones').onclick = () => {
      state.viewer.showBones = !state.viewer.showBones;
      $('show-bones').setAttribute('aria-pressed', String(state.viewer.showBones));
      state.viewer.render();
    };
    $('fullscreen').onclick = async () => {
      try {
        if (document.fullscreenElement) await document.exitFullscreen();
        else await document.querySelector('.viewer-shell').requestFullscreen();
      } catch (e) {
        notifyError(e);
      }
    };
    $('screenshot').onclick = () => {
      state.viewer.render();
      state.viewer.canvas.toBlob((blob) => {
        if (blob) download('character.png', blob, { document });
      });
    };
    $('save').onclick = revisions.saveAssembly;
    $('export').onclick = revisions.exportAssembly;
    $('refresh-saved').onclick = revisions.loadSaved;
  }
  async function start() {
    picker.initWorkspaceTabs();
    try {
      state.catalog = await (await api.request('/catalog')).json();
      state.catalog.all_races = state.catalog.races;
      state.settings = structuredClone(state.catalog.active_defaults || state.catalog.defaults);
      state.viewer = new Viewer($('viewer'), $('viewer-error'));
      state.viewer.setBones(state.catalog.bind_bones);
      palettes.createColors();
      palettes.createPalettes();
      palettes.createBackPalettes();
      picker.initPartPicker();
      options.renderOptions();
      bindControls();
      preview.schedule();
      revisions.loadSaved();
    } catch (e) {
      notifyError(e);
      $('busy').textContent = 'Редактор недоступен';
      $('saved-status').textContent =
        'Редактор недоступен. Проверь установку authoring-зависимостей.';
      $('saved-list').setAttribute('aria-busy', 'false');
      $('refresh-saved').disabled = true;
    }
  }
  return { state, api, selection, palettes, options, preview, revisions, picker, start };
}
