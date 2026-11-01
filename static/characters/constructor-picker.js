import { getRace } from './state.js';
// One compact inventory of editable parts and one inline options panel.
const partDefinitions = [
  ['face', 'Голова', 'face-cards'],
  ['hair', 'Волосы', 'hair-cards'],
  ['eye', 'Глаза', 'eye-cards'],
  ['brows', 'Брови', 'brows-cards'],
  ['nose', 'Нос и морда', 'nose-cards'],
  ['ears', 'Уши', 'ears-cards'],
  ['jaw', 'Челюсть', 'jaw-cards'],
  ['mouth', 'Рот и зубы', 'mouth-cards'],
  ['beard', 'Борода', 'beard-cards'],
  ['mustache', 'Усы', 'mustache-cards'],
  ['form', 'Силуэт', 'form-cards'],
  ['appearance', 'Цвета внешности', 'appearance-colors'],
  ['outfit', 'Костюм', 'outfit-cards'],
  ['arms', 'Руки', 'arms-cards'],
  ['legs', 'Ноги', 'legs-cards'],
  ['palette', 'Расцветка', 'palette-picker'],
  ['headwear', 'Головной убор', 'headwear-cards'],
  ['shoulders', 'Наплечники', 'shoulders-cards'],
  ['belt', 'Пояс и вещи', 'belt-cards'],
  ['emblem', 'Эмблема', 'emblem-cards'],
  ['pattern', 'Руны и узоры', 'pattern-cards'],
  ['back', 'Спина и крылья', 'back-cards'],
];

/** Picker state is local to one editor instance. */
export function createPicker(state, { document = globalThis.document } = {}) {
  const race = () => getRace(state);
  let activePart = null,
    partPickerReady = false;
  const partSections = new Map(),
    partButtons = new Map();
  function showWorkspace(key, focus = false) {
    for (const name of ['body-parts', 'assembly']) {
      const active = name === key,
        tab = document.getElementById(name + '-tab');
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
      document.getElementById(name + '-panel').hidden = !active;
      if (active && focus) tab.focus();
    }
    document.getElementById('randomize').hidden = key !== 'body-parts';
  }
  function initWorkspaceTabs() {
    const names = ['body-parts', 'assembly'];
    for (const [index, name] of names.entries()) {
      const tab = document.getElementById(name + '-tab');
      tab.onclick = () => showWorkspace(name);
      tab.onkeydown = (e) => {
        const next = ['ArrowRight', 'ArrowLeft'].includes(e.key)
          ? 1 - index
          : e.key === 'Home'
            ? 0
            : e.key === 'End'
              ? 1
              : null;
        if (next !== null) {
          e.preventDefault();
          showWorkspace(names[next], true);
        }
      };
    }
  }
  function partGlyph(key) {
    const strokes = {
      face: 'M28 24 Q50 10 72 24 L68 64 50 78 32 64Z M39 42h2 M59 42h2 M44 61h12',
      hair: 'M25 53 L28 27 44 15 68 22 76 50 61 30 48 41 41 30Z',
      eye: 'M18 45 Q50 18 82 45 Q50 72 18 45Z M58 45a8 8 0 1 1-16 0a8 8 0 1 1 16 0',
      brows: 'M20 41 Q32 25 44 35 M56 35 Q68 25 80 41',
      nose: 'M48 22 L39 55 Q50 64 63 54 L57 49',
      ears: 'M53 18 C24 13 26 63 43 75 Q60 70 48 52 Q33 45 45 33 Q58 29 59 42',
      jaw: 'M25 28 L31 62 50 77 69 62 75 28',
      mouth: 'M19 45 Q36 31 50 37 Q64 31 81 45 Q50 69 19 45Z M19 45h62',
      beard: 'M27 27 L34 66 50 80 66 66 73 27 M37 39h26',
      mustache: 'M50 44 Q25 26 18 52 Q39 64 50 44 Q75 26 82 52 Q61 64 50 44',
      outfit: 'M30 20 L16 36 29 49 34 72 66 72 71 49 84 36 70 20 59 24 Q50 40 41 24Z',
      arms: 'M39 21 L55 25 65 43 60 72 49 75 45 48 33 36Z',
      legs: 'M34 20 L64 20 60 45 64 74 53 74 48 46 42 74 31 74 35 45Z',
      headwear: 'M25 60 L26 35 Q50 10 74 35 L75 60 M32 60h36 M44 44h12',
      shoulders: 'M14 50 L22 30 42 26 49 47 M51 47 58 26 78 30 86 50',
      belt: 'M17 39h66v18H17Z M42 34h16v28H42Z',
      emblem: 'M50 18 L59 36 80 39 65 54 69 75 50 65 31 75 35 54 20 39 41 36Z',
      pattern: 'M32 18v57 M32 18 64 35 32 52 M64 18v57 M32 35 64 52',
      back: 'M48 39 L25 19 14 21 20 61 44 72 M52 39 75 19 86 21 80 61 56 72',
      form: 'M35 21 Q50 13 65 21 L69 43 59 57 60 76 M40 76 41 57 31 43Z',
    };
    if (key === 'palette' || key === 'appearance')
      return '<span class="part-swatches"><i></i><i></i><i></i></span>';
    return `<svg viewBox="0 0 100 90" aria-hidden="true"><path d="${strokes[key] || strokes.face}" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  }
  function initPartPicker() {
    for (const [key, label, anchor] of partDefinitions) {
      const section = document.getElementById(anchor).closest('.collection');
      section.id = section.id || 'part-panel-' + key;
      section.dataset.part = key;
      section.hidden = true;
      section.setAttribute('role', 'region');
      section.setAttribute('aria-label', label);
      document.getElementById('part-panels').append(section);
      partSections.set(key, section);
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'part-cell';
      button.dataset.part = key;
      button.setAttribute('aria-expanded', 'false');
      button.setAttribute('aria-controls', section.id);
      const visual = document.createElement('span');
      visual.className = 'part-cell-visual';
      visual.innerHTML = partGlyph(key);
      const text = document.createElement('span');
      text.className = 'part-cell-text';
      const title = document.createElement('strong');
      title.textContent = label;
      const selected = document.createElement('small');
      selected.className = 'part-current';
      selected.textContent = 'Выбрать';
      text.append(title, selected);
      button.append(visual, text);
      button.onclick = () => openPart(activePart === key ? null : key);
      document.getElementById('part-cells').append(button);
      partButtons.set(key, button);
    }
    document.getElementById('close-part-options').onclick = () => {
      const previous = activePart;
      openPart(null);
      partButtons.get(previous)?.focus();
    };
    document.getElementById('part-browser').addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && activePart) {
        e.preventDefault();
        document.getElementById('close-part-options').click();
      }
    });
    partPickerReady = true;
  }
  function openPart(key) {
    activePart = key;
    for (const [id, section] of partSections) {
      section.hidden = id !== key;
      partButtons.get(id).setAttribute('aria-expanded', String(id === key));
    }
    document.getElementById('part-options').hidden = !key;
    if (key) {
      document.getElementById('part-panels').scrollTop = 0;
      partSections
        .get(key)
        .querySelectorAll('img')
        .forEach((img) => (img.loading = 'eager'));
      requestAnimationFrame(() => {
        if (activePart === key)
          document.getElementById('part-options').scrollIntoView({
            block: 'nearest',
            behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
          });
      });
    }
  }
  function partAvailable(key, section) {
    const r = race();
    if (r.hidden_parts?.includes(key)) return false;
    if (['appearance', 'palette'].includes(key)) return true;
    if (key === 'legs' && r.id === 'ghost' && state.settings.form === 'ghost_spirit') return false;
    if (['form', 'hair'].includes(key) && r.id === 'ghost') return true;
    if (
      r.owned_body &&
      !(key === 'mouth' && r.feature_options?.mouth?.length) &&
      [
        'hair',
        'eye',
        'brows',
        'nose',
        'ears',
        'jaw',
        'mouth',
        'beard',
        'mustache',
        'form',
        'pattern',
      ].includes(key)
    )
      return false;
    if (key === 'mouth' && state.settings.face.match(/^expansion-(ape|owl)-/)) return false;
    if (r.mount_options?.[key]) return true;
    if (key === 'hair' && r.mane_options && Object.keys(r.mane_options).length) return true;
    if (key === 'form' && r.form_options && Object.keys(r.form_options).length) return true;
    if (r.gender_mode === 'neutral' && ['hair', 'beard', 'mustache'].includes(key)) return false;
    if (
      r.contract !== 'humanoid_v1' &&
      !(key === 'back' && (r.animal_body || r.flying_body || r.tail_options)) &&
      [
        'hair',
        'beard',
        'mustache',
        'eye',
        'form',
        'headwear',
        'shoulders',
        'belt',
        'emblem',
        'pattern',
        'back',
        'brows',
        'nose',
        'ears',
        'jaw',
        'mouth',
      ].includes(key)
    )
      return false;
    // Racial head designs currently own these features; do not offer edits that get overwritten.
    if (
      r.anatomies?.[state.settings.gender]?.length &&
      ['brows', 'nose', 'ears', 'jaw', 'mouth'].includes(key)
    )
      return false;
    return section.querySelectorAll('button.visual-card').length > 0;
  }
  function refreshPartPicker() {
    if (!partPickerReady) return;
    for (const [key, section] of partSections) {
      const button = partButtons.get(key),
        available = partAvailable(key, section);
      button.hidden = !available;
      if (key === 'headwear')
        button.querySelector('strong').textContent =
          race().id === 'beetle'
            ? 'Шлем жука'
            : race().mount_options?.headwear
              ? 'Сбруя'
              : 'Головной убор';
      if (key === 'hair')
        button.querySelector('strong').textContent =
          race().id === 'beast-horse' ? 'Грива' : 'Волосы';
      if (key === 'back')
        button.querySelector('strong').textContent = race().tail_options
          ? 'Хвост и жало'
          : race().flying_body
            ? 'Крылья'
            : race().animal_body
              ? 'Спина и хвост'
              : 'Спина и крылья';
      if (key === 'outfit')
        button.querySelector('strong').textContent =
          race().id === 'tree'
            ? 'Ствол'
            : race().animal_body || race().flying_body || ['crab', 'scorpion'].includes(race().id)
              ? 'Корпус'
              : race().id === 'ghost'
                ? 'Облачение'
                : race().owned_body
                  ? 'Расовое тело'
                  : 'Костюм';
      if (key === 'arms') button.querySelector('strong').textContent = race().arm_label || 'Руки';
      if (key === 'legs') button.querySelector('strong').textContent = race().leg_label || 'Ноги';
      if (key === 'shoulders')
        button.querySelector('strong').textContent =
          race().id === 'beetle'
            ? 'Грудная броня'
            : race().mount_options?.shoulders
              ? 'Защита животного'
              : race().owned_body
                ? 'Рукава и наплечники'
                : 'Наплечники';
      if (key === 'belt')
        button.querySelector('strong').textContent =
          race().id === 'beetle'
            ? 'Броня надкрыльев'
            : race().mount_options?.belt
              ? 'Седло и попона'
              : race().owned_body
                ? 'Штаны и пояс'
                : 'Пояс и вещи';
      const chosen =
        [...section.querySelectorAll('.visual-card[aria-pressed="true"]')]
          .reverse()
          .find((b) => b.dataset.value !== '0') ||
        section.querySelector('.visual-card[aria-pressed="true"]');
      const visual = button.querySelector('.part-cell-visual'),
        current = button.querySelector('.part-current');
      const img = chosen?.querySelector('img');
      if (img) {
        const previous = visual.querySelector('img');
        if (!previous || previous.getAttribute('src') !== img.getAttribute('src')) {
          const copy = img.cloneNode();
          copy.loading = 'eager';
          copy.alt = '';
          visual.replaceChildren(copy);
        }
      } else visual.innerHTML = partGlyph(key);
      let label = chosen?.querySelector('.card-label')?.textContent;
      if (
        ['arms', 'legs'].includes(key) &&
        !state.settings.reference_parts[key] &&
        state.settings[key] === state.settings.outfit
      )
        label = race().animal_body || race().flying_body ? 'Из корпуса' : 'Из костюма';
      current.textContent =
        key === 'palette'
          ? document.getElementById('palette-current-label').textContent
          : key === 'appearance'
            ? 'Кожа, волосы, глаза'
            : label || 'Выбрать';
      button.title = button.querySelector('strong').textContent + (label ? ' · ' + label : '');
    }
    const gender = document.getElementById('gender-cards').closest('.collection');
    gender.hidden = race().gender_mode === 'neutral';
    if (activePart && !partAvailable(activePart, partSections.get(activePart))) openPart(null);
  }

  return {
    showWorkspace,
    initWorkspaceTabs,
    initPartPicker,
    openPart,
    partAvailable,
    refreshPartPicker,
  };
}
