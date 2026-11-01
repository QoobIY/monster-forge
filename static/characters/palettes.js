import { COLOR_LABELS } from './state.js';
import { API_BASE } from './api.js';

/** Material controls share one saved settings palette. */
export function createPalettes(
  state,
  { document = globalThis.document, onChange = () => {} } = {},
) {
  const $ = (id) => document.getElementById(id);
  const API = API_BASE;
  const colorLabels = COLOR_LABELS;
  const commit = () => onChange();
  function createColors() {
    for (const [key, label] of Object.entries(colorLabels)) {
      const wrap = document.createElement('label');
      wrap.className = 'color-field';
      const enable = document.createElement('input');
      enable.type = 'checkbox';
      enable.id = 'use-' + key;
      enable.setAttribute('aria-label', 'Свой цвет: ' + label);
      const text = document.createElement('span');
      text.textContent = label;
      text.id = 'label-' + key;
      const input = document.createElement('input');
      input.type = 'color';
      input.id = 'color-' + key;
      input.setAttribute('aria-label', label);
      const change = () => {
        state.settings.colors[key] = enable.checked ? input.value : null;
        commit();
      };
      enable.onchange = change;
      input.oninput = change;
      wrap.append(enable, text, input);
      $(
        key.startsWith('back_')
          ? 'back-colors'
          : key === 'hair' || key === 'eyes' || key === 'skin'
            ? 'appearance-colors'
            : 'outfit-colors',
      ).append(wrap);
    }
  }
  function paletteImage(id) {
    return API + '/palette-cards/' + encodeURIComponent(id) + '.png?revision=static-palettes-v1';
  }
  function activePalette() {
    if (
      state.settings.reference_parts.colorways &&
      !['cloth', 'accent', 'metal', 'leather', 'secondary'].some((k) => state.settings.colors[k])
    )
      return 'material-' + state.settings.reference_parts.colorways;
    const p = state.catalog.palette_options.find(
      (p) =>
        p.id !== 'original' &&
        Object.entries(p.colors).every(([k, v]) => state.settings.colors[k] === v),
    );
    return (
      p?.id ||
      (!state.settings.reference_parts.colorways &&
      !['cloth', 'accent', 'metal', 'leather', 'secondary'].some((k) => state.settings.colors[k])
        ? 'original'
        : 'current')
    );
  }
  function refreshPaletteSelection() {
    if (!state.catalog.palette_options) return;
    const id = activePalette(),
      option = state.catalog.palette_options.find((p) => p.id === id);
    $('palette-current-label').textContent = option?.label || 'Своя расцветка';
    for (const b of $('palette-cards').children)
      b.setAttribute('aria-selected', String(b.dataset.paletteChoice === id));
    const img = $('palette-current-preview'),
      src = paletteImage(id);
    if (img.getAttribute('src') !== src) img.src = src;
    img.alt = option ? 'Пример расцветки: ' + option.label : 'Своя расцветка материалов';
  }
  function createPalettes() {
    for (const p of state.catalog.palette_options) {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'menu-palette-option';
      b.dataset.paletteChoice = p.id;
      b.setAttribute('role', 'option');
      b.setAttribute('aria-selected', 'false');
      const img = document.createElement('img');
      img.alt = 'Пример расцветки: ' + p.label;
      img.src = paletteImage(p.id);
      img.loading = 'lazy';
      const text = document.createElement('span');
      text.textContent = p.label;
      const swatches = document.createElement('span');
      swatches.className = 'palette-mini-swatches';
      for (const color of Object.values(p.colors)) {
        const chip = document.createElement('i');
        chip.style.backgroundColor = color;
        swatches.append(chip);
      }
      b.append(img, text, swatches);
      b.onclick = () => {
        for (const k of ['cloth', 'accent', 'metal', 'leather', 'secondary'])
          state.settings.colors[k] = null;
        state.settings.reference_parts.colorways = 0;
        Object.assign(state.settings.colors, p.colors);
        if (p.id.startsWith('material-')) state.settings.colors.secondary = p.colors.accent;
        $('palette-picker').open = false;
        commit();
      };
      $('palette-cards').append(b);
    }
    $('palette-cards').onkeydown = (e) => {
      const items = [...$('palette-cards').children],
        i = items.indexOf(document.activeElement);
      if (e.key === 'Escape') {
        $('palette-picker').open = false;
        $('palette-picker').querySelector('summary').focus();
        return;
      }
      const index =
        e.key === 'ArrowDown' || e.key === 'ArrowRight'
          ? Math.min(items.length - 1, i + 1)
          : e.key === 'ArrowUp' || e.key === 'ArrowLeft'
            ? Math.max(0, i - 1)
            : e.key === 'Home'
              ? 0
              : e.key === 'End'
                ? items.length - 1
                : null;
      if (index !== null) {
        e.preventDefault();
        items[index].focus();
      }
    };
    document.addEventListener('click', (e) => {
      if (!$('palette-picker').contains(e.target)) $('palette-picker').open = false;
    });
  }
  function createBackPalettes() {
    for (const p of state.catalog.colorways) {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'palette-card';
      b.dataset.backPalette = p.id;
      b.setAttribute('aria-label', 'Спина: ' + p.label);
      const stripe = document.createElement('span');
      stripe.className = 'palette-stripe';
      for (const color of [p.colors.cloth, p.colors.accent, p.colors.metal]) {
        const i = document.createElement('i');
        i.style.backgroundColor = color;
        stripe.append(i);
      }
      const label = document.createElement('span');
      label.textContent = p.label;
      b.append(stripe, label);
      b.onclick = () => {
        Object.assign(state.settings.colors, {
          back_primary: p.colors.cloth,
          back_secondary: p.colors.accent,
          back_frame: p.colors.metal,
        });
        commit();
      };
      $('back-palette-cards').append(b);
    }
  }
  return {
    createColors,
    createPalettes,
    createBackPalettes,
    refreshPaletteSelection,
    activePalette,
  };
}
