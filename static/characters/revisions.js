import { API_BASE } from './api.js';
import { migrateSettings as migrate } from './state.js';
import { download } from './api.js';
/** Immutable saves, exact published views and explicit edits of historical choices. */
export function createRevisions(
  state,
  {
    document = globalThis.document,
    api,
    selection,
    preview,
    options,
    picker,
    notifyError = () => {},
    updateActions = () => {},
    reloadSaved,
  } = {},
) {
  const $ = (id) => document.getElementById(id);
  const API = API_BASE;
  const request = (...args) => api.request(...args);
  const actions = () => updateActions();
  const migrateSettings = (s) => migrate(s, state.catalog);
  const renderOptions = () => options.renderOptions();
  const renderSlots = (parts) => preview.renderSlots(parts);
  const openPart = (key) => picker.openPart(key);
  const showWorkspace = (...args) => picker.showWorkspace(...args);
  const commit = () => selection.commit();
  async function openSavedCharacter(item, exact = false) {
    let version;
    try {
      const editable =
        !item.edit_error &&
        item.editable !== false &&
        item.settings &&
        state.catalog.races.some((r) => r.id === item.settings.race);
      if (!exact && !editable)
        throw Error(item.edit_error || 'Настройки этой сборки недоступны для редактирования');
      const next = editable ? migrateSettings(item.settings) : null;
      clearTimeout(state.timer);
      if (state.controller) state.controller.abort();
      version = ++state.serial;
      state.viewingPublished = exact;
      state.ready = false;
      actions();
      $('error').hidden = true;
      $('save-result').replaceChildren();
      if (next) {
        state.settings = next;
        state.linkedLimbs =
          state.settings.arms === state.settings.outfit &&
          state.settings.legs === state.settings.outfit &&
          !state.settings.reference_parts.arms &&
          !state.settings.reference_parts.legs;
        renderOptions();
      }
      state.viewer.slot = '';
      state.viewer.slotSignature = null;
      openPart(null);
      if (!(await state.viewer.setParts({})) || version !== state.serial) return;
      if (!exact) {
        showWorkspace('body-parts', true);
        commit();
        return;
      }
      $('busy').textContent = 'Загружаем опубликованную версию…';
      state.controller = new AbortController();
      const data = await (
        await request(item.model_url.slice(API.length), undefined, state.controller.signal)
      ).json();
      if (version !== state.serial) return;
      state.viewer.slot = '';
      state.viewer.contract = data.contract;
      state.viewer.setBones(data.bind_bones || []);
      if (!(await state.viewer.setParts(data.parts)) || version !== state.serial) return;
      renderSlots(data.parts);
      $('mesh-info').textContent = data.triangles.toLocaleString('ru') + ' △';
      $('parts-count').textContent = Object.keys(data.parts).length + ' частей';
      if (item.label) $('character-name').textContent = item.label;
      const note = document.createElement('p');
      note.textContent = editable
        ? 'Опубликованная версия. Изменение деталей создаст новую сборку.'
        : 'Архивная версия. Доступны просмотр и скачивание.';
      const edit = document.createElement('button');
      edit.type = 'button';
      edit.textContent = 'Редактировать';
      edit.disabled = !editable;
      if (!editable) edit.title = item.edit_error || 'Сборка использует архивный контракт';
      edit.onclick = () => editSaved(item);
      $('warnings').replaceChildren(note, edit);
      $('busy').textContent = 'Опубликованная версия';
      state.ready = true;
      actions();
    } catch (e) {
      if (e.name === 'AbortError' || (version !== undefined && version !== state.serial)) return;
      notifyError(e);
      $('busy').textContent = 'Не удалось загрузить персонажа';
      state.ready = false;
      actions();
    }
  }
  function showPublished(item) {
    return openSavedCharacter(item, true);
  }
  function editSaved(item) {
    return openSavedCharacter(item);
  }
  async function loadSaved() {
    const version = ++state.savedSerial;
    $('refresh-saved').disabled = true;
    $('saved-list').setAttribute('aria-busy', 'true');
    $('saved-status').textContent = 'Загружаем сборки…';
    $('saved-error').hidden = true;
    try {
      const data = await (await request('/revisions')).json(),
        nodes = [];
      if (version !== state.savedSerial) return;
      const groups = [
        ['Опубликованные персонажи', data.published || []],
        ['Сохранённые локально', data.revisions || []],
      ];
      for (const [title, items] of groups) {
        if (!items.length) continue;
        const heading = document.createElement('h3');
        heading.textContent = title;
        nodes.push(heading);
        for (const item of items) {
          const row = document.createElement('div');
          row.className = 'saved-item';
          if (item.error) {
            row.textContent = item.id.slice(0, 8) + ': ' + item.error;
            nodes.push(row);
            continue;
          }
          const published = item.source === 'mom',
            img = document.createElement('img');
          img.src = item.preview;
          img.alt = item.label || 'Сохранённый персонаж';
          img.loading = 'lazy';
          const info = document.createElement('div'),
            name = document.createElement('strong');
          const savedRace = item.settings?.race;
          name.textContent =
            item.label ||
            (state.catalog.all_races.find((r) => r.id === savedRace)?.label ||
              state.catalog.archived_race_labels?.[savedRace] ||
              savedRace ||
              'Сборка') +
              ' · ' +
              item.id.slice(0, 8);
          info.append(name);
          const edit = document.createElement('button');
          edit.type = 'button';
          edit.textContent = 'Редактировать';
          if (
            item.edit_error ||
            item.editable === false ||
            !item.settings ||
            !state.catalog.races.some((r) => r.id === item.settings.race)
          ) {
            edit.disabled = true;
            edit.textContent = item.edit_error ? 'Настройки несовместимы' : 'Архивная сборка';
            if (item.edit_error) edit.title = item.edit_error;
          }
          edit.onclick = () => editSaved(item);
          const download = document.createElement('a');
          download.href = item.download || API + '/revisions/' + item.id + '/download';
          download.textContent = published ? 'Скачать модель ↓' : 'Скачать сборку ↓';
          info.append(edit);
          if (published) {
            const view = document.createElement('button');
            view.type = 'button';
            view.textContent = 'Посмотреть опубликованную версию';
            view.onclick = () => showPublished(item);
            info.append(view);
          }
          info.append(download);
          row.append(img, info);
          nodes.push(row);
        }
      }
      if (!nodes.length) {
        const p = document.createElement('p');
        p.className = 'hint';
        p.textContent = 'Сохрани персонажа — он появится здесь.';
        nodes.push(p);
      }
      $('saved-list').replaceChildren(...nodes);
      const count = (data.published || []).length + (data.revisions || []).length;
      $('saved-status').textContent = count ? 'Сборок: ' + count : 'Пока нет сохранённых сборок.';
    } catch (e) {
      if (version === state.savedSerial) {
        $('saved-status').textContent = 'Список сборок недоступен.';
        $('saved-error').textContent = e.message || String(e);
        $('saved-error').hidden = false;
      }
    } finally {
      if (version === state.savedSerial) {
        $('refresh-saved').disabled = false;
        $('saved-list').setAttribute('aria-busy', 'false');
      }
    }
  }
  async function saveAssembly() {
    const snapshot = structuredClone(state.settings),
      version = state.serial;
    state.actionBusy = true;
    actions();
    $('error').hidden = true;
    try {
      const data = await (await request('/save', snapshot)).json();
      if (version === state.serial) {
        const a = document.createElement('a');
        a.href = API + '/revisions/' + data.id + '/download';
        a.textContent = 'Сборка сохранена · Скачать ZIP ↓';
        const open = document.createElement('button');
        open.type = 'button';
        open.className = 'text-button';
        open.textContent = 'Открыть в Assembly';
        open.onclick = () => showWorkspace('assembly');
        $('save-result').replaceChildren(a, open);
      }
      await (reloadSaved || loadSaved)();
    } catch (e) {
      notifyError(e);
    } finally {
      state.actionBusy = false;
      actions();
    }
  }
  async function exportAssembly() {
    const snapshot = structuredClone(state.settings);
    state.actionBusy = true;
    actions();
    $('error').hidden = true;
    try {
      download(snapshot.race + '-assembly.zip', await (await request('/export', snapshot)).blob(), {
        document,
      });
    } catch (e) {
      notifyError(e);
    } finally {
      state.actionBusy = false;
      actions();
    }
  }
  return { openSavedCharacter, showPublished, editSaved, loadSaved, saveAssembly, exportAssembly };
}
