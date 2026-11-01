import assert from 'node:assert/strict';
import test from 'node:test';

import { createApi } from '../../static/characters/api.js';
import { createConstructorApp } from '../../static/characters/app.js';
import { createPicker } from '../../static/characters/constructor-picker.js';
import { ConstructorViewer } from '../../static/characters/constructor-viewer.js';
import { assemblyDescription } from '../../static/characters/options.js';
import { createPreview } from '../../static/characters/preview.js';
import { createRevisions } from '../../static/characters/revisions.js';
import { createSelection } from '../../static/characters/selection.js';
import { createState, migrateSettings } from '../../static/characters/state.js';

class Element {
  children = [];
  attributes = {};
  dataset = {};
  textContent = '';

  constructor(tag = 'div') {
    this.tagName = tag;
  }

  append(...nodes) {
    this.children.push(...nodes);
  }
  replaceChildren(...nodes) {
    this.children = nodes;
  }
  setAttribute(name, value) {
    this.attributes[name] = value;
  }
  closest() {
    return this;
  }
  addEventListener() {}
  querySelectorAll(selector) {
    const descendants = this.children.flatMap((child) => [child, ...child.querySelectorAll('*')]);
    return descendants.filter((child) => {
      if (selector === '*') return true;
      const className = selector.match(/\.([\w-]+)/)?.[1];
      if (className && child.className !== className) return false;
      if (selector.includes('[aria-pressed="true"]') && child.attributes['aria-pressed'] !== 'true')
        return false;
      const tag = selector.match(/^[a-z]+/)?.[0];
      return !tag || child.tagName === tag;
    });
  }
  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }
}

function createDocument() {
  const elements = new Map();
  return {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, Object.assign(new Element(), { id }));
      return elements.get(id);
    },
    createElement: (tag) => new Element(tag),
  };
}

function catalog() {
  return {
    settings_version: 5,
    defaults: {
      schema_version: 5,
      race: 'human',
      gender: 'male',
      face: 'head-a',
      outfit: 'outfit-a',
      arms: 'outfit-a',
      legs: 'outfit-a',
      colors: { cloth: '#123456' },
      features: { mouth: 'profile' },
      decor: { beard: 'none', belt: 'none' },
      reference_parts: {
        male_faces: 2,
        female_faces: 0,
        race_heads: 0,
        arms: 3,
        gloves: 4,
        legs: 5,
      },
    },
    races: [{ id: 'human', contract: 'humanoid_v1' }],
  };
}

test('editor instances never share mutable choices or request state', () => {
  const source = catalog(),
    first = createState(source),
    second = createState(source);
  createSelection(first).chooseField('arms', 'arm-b');
  assert.equal(first.settings.arms, 'arm-b');
  assert.equal(first.settings.reference_parts.arms, 0);
  assert.equal(first.settings.reference_parts.gloves, 4);
  assert.equal(first.linkedLimbs, false);
  assert.equal(second.settings.arms, 'outfit-a');
  assert.equal(source.defaults.arms, 'outfit-a');
  assert.notEqual(first.settings.colors, second.settings.colors);
  assert.equal(second.serial, 0);
});

test('the assembly note distinguishes static authoring drafts from rigged humanoids', () => {
  assert.match(
    assemblyDescription({ contract: 'humanoid_v1', animation_support: 'static_bind' }),
    /со скелетом/,
  );
  assert.match(
    assemblyDescription({ contract: 'centaur_authoring_v1', animation_support: 'authoring_only' }),
    /без скелета/,
  );
  assert.match(
    assemblyDescription({ contract: 'quadruped_v1', animation_support: 'static_bind' }),
    /со скелетом/,
  );
  assert.match(
    assemblyDescription({ contract: 'ghost_v1', animation_support: 'static_bind' }),
    /со скелетом/,
  );
  assert.match(assemblyDescription({ contract: 'humanoid_v1', rigging: 'none' }), /без скелета/);
});

test('the real picker refresh reads linked limb choices from its own state', () => {
  assert.equal(globalThis.settings, undefined);
  const state = createState(catalog()),
    document = createDocument();
  state.settings.reference_parts.arms = state.settings.reference_parts.legs = 0;
  for (const slot of ['arms', 'legs']) {
    const option = new Element('button');
    option.className = 'visual-card';
    option.dataset.value = 'outfit-a';
    option.setAttribute('aria-pressed', 'true');
    document.getElementById(slot + '-cards').append(option);
  }
  const picker = createPicker(state, { document });
  picker.initPartPicker();
  picker.refreshPartPicker();
  for (const slot of ['arms', 'legs']) {
    const button = document
      .getElementById('part-cells')
      .children.find((node) => node.dataset.part === slot);
    assert.equal(button.hidden, false);
    assert.equal(button.querySelector('.part-current').textContent, 'Из костюма');
  }
});

test('settings migrations preserve the source and reject unknown versions', () => {
  const source = { ...catalog().defaults, schema_version: 4 };
  delete source.reference_parts;
  const snapshot = structuredClone(source),
    result = migrateSettings(source, catalog());
  assert.deepEqual(source, snapshot);
  assert.equal(result.schema_version, 5);
  assert.equal(result.reference_parts.arms, 0);
  assert.equal(result.colors.cloth, '#123456');
  assert.throws(() => migrateSettings({ ...source, schema_version: 99 }, catalog()), /версию/);
});

test('API transport sends the saved snapshot and propagates server errors', async () => {
  let captured;
  const payload = catalog().defaults;
  const api = createApi({
    fetch: async (path, options) => {
      captured = { path, options };
      return { ok: false, status: 400, json: async () => ({ error: 'Invalid assembly revision' }) };
    },
  });
  await assert.rejects(api.request('/save', payload), /Invalid assembly revision/);
  assert.equal(captured.path, '/creature-workshop/constructor/save');
  assert.equal(captured.options.method, 'POST');
  assert.deepEqual(JSON.parse(captured.options.body), payload);
});

test('an archived publication remains viewable without replacing the editable draft', async () => {
  const state = createState(catalog()),
    document = createDocument(),
    errors = [];
  const draft = state.settings,
    exact = { whole: { glb: 'archived-runtime-geometry' } };
  let rendered,
    requests = 0;
  state.viewer = {
    setBones() {},
    async setParts(parts) {
      rendered = parts;
      return true;
    },
  };
  const revisions = createRevisions(state, {
    document,
    api: {
      request: async () => {
        requests++;
        return {
          json: async () => ({
            parts: exact,
            triangles: 17,
            contract: 'archived_contract',
            bind_bones: [],
          }),
        };
      },
    },
    selection: {
      commit() {
        throw Error('A read-only view cannot commit choices');
      },
    },
    options: {
      renderOptions() {
        throw Error('An archived contract cannot enter the editor');
      },
    },
    preview: { renderSlots() {} },
    picker: {
      openPart() {},
      showWorkspace() {
        throw Error('An archived view must remain in Assembly');
      },
    },
    notifyError: (error) => errors.push(error.message),
  });
  const item = {
    id: 'archived',
    label: 'Archived model',
    editable: false,
    edit_error: 'Unsupported historical contract',
    settings: { ...draft, race: 'legacy-creature' },
    model_url: '/creature-workshop/constructor/published/archived/model',
  };
  await revisions.showPublished(item);
  assert.deepEqual(rendered, exact);
  assert.equal(state.settings, draft);
  assert.equal(state.ready, true);
  assert.equal(state.viewingPublished, true);
  assert.equal(document.getElementById('character-name').textContent, item.label);
  assert.equal(document.getElementById('warnings').children[1].disabled, true);
  assert.deepEqual(errors, []);
  await revisions.editSaved(item);
  assert.deepEqual(errors, ['Unsupported historical contract']);
  assert.equal(requests, 1);
});

test('late preview responses cannot overwrite a newer model', async () => {
  const state = createState(catalog()),
    document = createDocument();
  let release, shown;
  state.viewer = {
    slot: '',
    setBones() {},
    combine() {},
    async setParts(parts) {
      shown = parts;
      return true;
    },
  };
  const preview = createPreview(state, {
    document,
    api: {
      request: async () => ({
        json: () =>
          new Promise((resolve) => {
            release = resolve;
          }),
      }),
    },
  });
  state.serial = 1;
  const old = preview.updatePreview(1);
  await new Promise((resolve) => setImmediate(resolve));
  state.serial = 2;
  const newer = { current: { glb: 'newer' } };
  state.viewer.setParts(newer);
  release({ parts: { previous: { glb: 'older' } }, warnings: [], triangles: 1 });
  await old;
  assert.deepEqual(shown, newer);
});

test('an unavailable constructor ends loading and reports the setup error', async () => {
  const document = createDocument();
  const app = createConstructorApp({
    document,
    fetch: async () => {
      throw Error('Install the authoring dependencies to enable the constructor');
    },
  });
  await app.start();
  assert.match(document.getElementById('error').textContent, /authoring dependencies/);
  assert.equal(document.getElementById('busy').textContent, 'Редактор недоступен');
  assert.equal(document.getElementById('saved-list').attributes['aria-busy'], 'false');
  assert.equal(document.getElementById('refresh-saved').disabled, true);
});

test('static source textures preserve orientation while existing geometry keeps its default', async () => {
  const previousBitmap = globalThis.createImageBitmap;
  const orientations = [];
  globalThis.createImageBitmap = async (_blob, options) => {
    orientations.push(options.imageOrientation);
    return { close() {} };
  };
  try {
    const gl = new Proxy(
      { createTexture: () => ({}), deleteTexture() {} },
      { get: (object, name) => object[name] || (() => {}) },
    );
    const viewer = Object.assign(Object.create(ConstructorViewer.prototype), {
      gl,
      parts: {},
      loadVersion: 0,
      combine() {},
    });
    const geometry = {
      positions: [0, 0, 0],
      normals: [0, 1, 0],
      colors: [1, 1, 1],
      uvs: [0, 0],
      texture: 'AA==',
    };
    await viewer.setParts({ head: { geometry: { ...geometry, texture_flip_y: false } } });
    await viewer.setParts({ head: { geometry } });
    assert.deepEqual(orientations, ['none', 'flipY']);
  } finally {
    if (previousBitmap === undefined) delete globalThis.createImageBitmap;
    else globalThis.createImageBitmap = previousBitmap;
  }
});
