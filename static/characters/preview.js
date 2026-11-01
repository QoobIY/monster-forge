import { SLOT_LABELS } from './state.js';

/** Latest-request-wins preview orchestration. The renderer receives Python geometry. */
export function createPreview(
  state,
  { document = globalThis.document, api, notifyError = () => {}, updateActions = () => {} } = {},
) {
  const $ = (id) => document.getElementById(id);
  const slotLabels = SLOT_LABELS;
  const request = (...args) => api.request(...args);
  const actions = () => updateActions();
  function schedule() {
    state.viewingPublished = false;
    state.ready = false;
    actions();
    $('error').hidden = true;
    $('save-result').replaceChildren();
    $('busy').textContent = 'Собираем…';
    state.serial++;
    clearTimeout(state.timer);
    if (state.controller) state.controller.abort();
    state.viewer.cancelPendingLoads();
    const version = state.serial;
    state.timer = setTimeout(() => updatePreview(version), 180);
  }
  async function updatePreview(version) {
    state.controller = new AbortController();
    try {
      const data = await (
        await request('/preview', structuredClone(state.settings), state.controller.signal)
      ).json();
      if (version !== state.serial) return;
      if (data.bind_bones) state.viewer.setBones(data.bind_bones);
      if (!(await state.viewer.setParts(data.parts)) || version !== state.serial) return;
      renderSlots(data.parts);
      $('mesh-info').textContent = data.triangles.toLocaleString('ru') + ' △';
      $('parts-count').textContent = Object.keys(data.parts).length + ' частей';
      $('warnings').replaceChildren(
        ...data.warnings.map((text) => {
          const p = document.createElement('p');
          p.textContent = text;
          return p;
        }),
      );
      $('busy').textContent = 'Готово';
      state.ready = true;
      actions();
    } catch (e) {
      if (e.name === 'AbortError' || version !== state.serial) return;
      notifyError(e);
      $('busy').textContent = 'Ошибка сборки';
      state.ready = false;
      actions();
    }
  }
  function renderSlots(parts) {
    const signature = Object.keys(parts).join('|');
    if (state.viewer.slotSignature === signature) return;
    state.viewer.slotSignature = signature;
    if (state.viewer.slot && !parts[state.viewer.slot]) {
      state.viewer.slot = '';
      state.viewer.combine();
    }
    $('slot-cards').replaceChildren();
    const names = {
      ...slotLabels,
      whole: 'Готовая модель',
      left_wing: 'Л. крыло',
      right_wing: 'П. крыло',
      left_claw: 'Л. клешня',
      right_claw: 'П. клешня',
      tail: 'Хвост',
      abdomen: 'Брюшко',
      front_left_leg: 'Перед. л. нога',
      front_right_leg: 'Перед. п. нога',
      hind_left_leg: 'Зад. л. нога',
      hind_right_leg: 'Зад. п. нога',
    };
    if (state.settings.race === 'ghost' && state.settings.form === 'ghost_spirit')
      Object.assign(names, { left_leg: 'Л. шлейф', right_leg: 'П. шлейф' });
    for (const id of ['', ...Object.keys(parts)]) {
      const b = document.createElement('button');
      const match = id.match(/^(left|right)_leg_(\d)$/);
      b.textContent =
        names[id] || (match ? (match[1] === 'left' ? 'Л.' : 'П.') + ' нога ' + match[2] : id);
      b.type = 'button';
      b.setAttribute('aria-pressed', String(id === state.viewer.slot));
      b.onclick = () => {
        state.viewer.slot = id;
        state.viewer.combine();
        for (const other of $('slot-cards').children)
          other.setAttribute('aria-pressed', String(other === b));
      };
      $('slot-cards').append(b);
    }
  }
  return { schedule, updatePreview, renderSlots };
}
