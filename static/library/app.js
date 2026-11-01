import { ConstructorViewer } from '../characters/constructor-viewer.js';

export function createLibraryApp({
  document = globalThis.document,
  fetch = globalThis.fetch,
  Viewer = ConstructorViewer,
  clipboard = globalThis.navigator?.clipboard,
  IntersectionObserver = globalThis.IntersectionObserver,
} = {}) {
  const $ = (id) => document.getElementById(id);
  const page = document.querySelector('.library-page'),
    kind = page.dataset.kind;
  const names = {
    gloves: 'Перчатки',
    pants: 'Штаны',
    bracelets: 'Браслеты',
    chain: 'Цепь',
    wings: 'Крылья',
    head: 'Голова',
    shoulders: 'Наплечники',
    torso: 'Торс',
    arms: 'Руки',
    legs: 'Ноги',
    boots: 'Обувь',
    belt: 'Пояс',
    talisman: 'Талисман',
    ring: 'Кольцо',
    amulet: 'Амулет',
    sword: 'Меч',
    axe: 'Топор',
    bow: 'Лук',
    staff: 'Посох',
    spear: 'Копьё',
    shield: 'Щит',
    dagger: 'Кинжал',
    hammer: 'Молот',
  };
  const decorationTitles = new Map();
  let assets = [],
    filtered = [],
    selected = null,
    group = '',
    shown = 80,
    viewer = null,
    epoch = 0,
    controller = null;

  function title(asset) {
    if (asset.title === asset.id && kind === 'decoration')
      return decorationTitles.get(asset.id) || asset.id;
    return names[asset.source_id] || asset.title;
  }
  function primary(asset) {
    return asset.files[kind === 'decoration' ? 'model' : 'image'];
  }
  function url(ref) {
    return '/media/' + ref.path.split('/').map(encodeURIComponent).join('/');
  }
  function error(e) {
    $('library-error').hidden = false;
    $('library-error').textContent = e.message || String(e);
  }
  async function request(path, signal) {
    const response = await fetch(path, { signal });
    if (!response.ok) {
      let message = 'Не удалось загрузить ассет';
      try {
        message = (await response.json()).error || message;
      } catch {}
      throw Error(message);
    }
    return response.json();
  }

  function renderFilters() {
    const box = $('group-filters');
    box.replaceChildren();
    for (const value of ['', ...new Set(assets.map((asset) => asset.group))]) {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = value || 'Все';
      button.setAttribute('aria-pressed', String(group === value));
      button.onclick = () => {
        group = value;
        shown = 80;
        renderFilters();
        render();
      };
      box.append(button);
    }
  }
  function render() {
    const query = $('asset-search').value.trim().toLocaleLowerCase();
    filtered = assets.filter(
      (asset) =>
        (!group || asset.group === group) &&
        (!query ||
          [title(asset), asset.id, asset.group, ...asset.tags]
            .join(' ')
            .toLocaleLowerCase()
            .includes(query)),
    );
    $('asset-count').textContent = filtered.length + ' / ' + assets.length;
    $('empty-results').hidden = filtered.length > 0;
    $('asset-grid').replaceChildren();
    appendCards(filtered.slice(0, shown));
    watchScroll();
  }
  function appendCards(batch) {
    const fragment = document.createDocumentFragment();
    for (const asset of batch) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'asset-card';
      button.dataset.assetId = asset.id;
      button.setAttribute('aria-label', title(asset));
      button.setAttribute('aria-pressed', String(selected?.id === asset.id));
      const thumbnail = asset.files.preview || (kind === 'decoration' ? null : primary(asset));
      let visual;
      if (thumbnail) {
        visual = document.createElement('img');
        visual.src = url(thumbnail);
        visual.alt = '';
        visual.loading = 'lazy';
        visual.decoding = 'async';
      } else {
        visual = document.createElement('span');
        visual.className = 'asset-card-placeholder';
        visual.setAttribute('aria-hidden', 'true');
        visual.innerHTML =
          '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="m24 4 17 10v20L24 44 7 34V14L24 4Zm0 20 17-10M24 24 7 14m17 10v20"/></svg>';
      }
      const text = document.createElement('span');
      text.className = 'asset-card-text';
      const label = document.createElement('strong');
      label.textContent = title(asset);
      const hint = document.createElement('small');
      hint.textContent =
        kind === 'icon'
          ? asset.tags.includes('ui')
            ? 'Интерфейс'
            : asset.tags.includes('equipment')
              ? 'Предмет'
              : 'Игровая иконка'
          : kind === 'terrain'
            ? 'Бесшовный материал'
            : '3D · GLB';
      text.append(label, hint);
      button.append(visual, text);
      button.onclick = () => select(asset);
      fragment.append(button);
    }
    $('asset-grid').append(fragment);
  }
  const sentinel = $('scroll-sentinel');
  const scrollObserver = new IntersectionObserver(
    (entries) => {
      if (!entries.some((entry) => entry.isIntersecting) || shown >= filtered.length) return;
      const from = shown;
      shown += 80;
      appendCards(filtered.slice(from, shown));
      watchScroll();
    },
    { rootMargin: '400px 0px' },
  );
  function watchScroll() {
    scrollObserver.unobserve(sentinel);
    sentinel.hidden = shown >= filtered.length;
    if (!sentinel.hidden) scrollObserver.observe(sentinel);
  }

  async function select(asset) {
    selected = asset;
    const version = ++epoch;
    if (controller) controller.abort();
    controller = new AbortController();
    viewer?.cancelPendingLoads();
    $('library-error').hidden = true;
    $('asset-title').textContent = title(asset);
    $('asset-group').textContent = asset.group;
    const ref = primary(asset),
      download = $('download-asset');
    download.href = url(ref) + '?download=1';
    download.classList.remove('disabled');
    download.setAttribute('aria-disabled', 'false');
    $('asset-identity').textContent = asset.id;
    $('asset-code').textContent = 'assets.path(' + JSON.stringify(asset.id) + ')';
    for (const button of document.querySelectorAll('.asset-card'))
      button.setAttribute('aria-pressed', String(button.dataset.assetId === asset.id));
    $('asset-stage').setAttribute('aria-busy', 'true');
    $('asset-metrics').textContent = 'Загружаем…';
    try {
      if (kind === 'icon' || kind === 'terrain') {
        const image = $('selected-image');
        image.hidden = true;
        image.alt = title(asset);
        image.src = url(ref);
        await image.decode();
        if (version !== epoch) return;
        image.hidden = false;
        $('asset-metrics').textContent =
          image.naturalWidth +
          ' × ' +
          image.naturalHeight +
          ' · ' +
          ref.media_type.split('/')[1].toUpperCase();
      } else {
        if (!viewer?.gl) {
          $('asset-metrics').textContent = '3D-превью недоступно';
          return;
        }
        if (!(await viewer.setParts({})) || version !== epoch) return;
        const data = await request(
          '/api/assets/v1/geometry?id=' + encodeURIComponent(asset.id),
          controller.signal,
        );
        if (version !== epoch) return;
        if (!(await viewer.setParts(data.parts)) || version !== epoch) return;
        $('asset-metrics').textContent = data.triangles.toLocaleString('ru-RU') + ' треугольников';
      }
    } catch (e) {
      if (e.name !== 'AbortError' && version === epoch) {
        $('asset-metrics').textContent = 'Не удалось загрузить превью';
        error(e);
      }
    } finally {
      if (version === epoch) $('asset-stage').setAttribute('aria-busy', 'false');
    }
  }

  async function copy(text, button, label) {
    try {
      await clipboard.writeText(text);
      button.textContent = 'Скопировано';
      setTimeout(() => (button.textContent = label), 1400);
    } catch {
      button.textContent = 'Выдели текст и скопируй';
    }
  }
  $('asset-search').addEventListener('input', () => {
    shown = 80;
    render();
  });
  $('copy-id').onclick = () => selected && copy(selected.id, $('copy-id'), 'Копировать ID');
  $('toggle-background').onclick = () => {
    const light = $('asset-stage').classList.toggle('light');
    $('toggle-background').textContent = light ? 'Тёмный фон' : 'Светлый фон';
    $('toggle-background').setAttribute('aria-pressed', String(light));
    if (viewer?.gl) {
      viewer.gl.clearColor(...(light ? [1, 1, 1, 1] : [30 / 255, 30 / 255, 30 / 255, 1]));
      viewer.render();
    }
  };
  if (kind === 'decoration') {
    try {
      viewer = new Viewer($('asset-canvas'), $('viewer-error'));
      $('reset-model').onclick = () => viewer.reset();
      $('fullscreen-model').onclick = async () => {
        try {
          if (document.fullscreenElement) await document.exitFullscreen();
          else await $('asset-stage').requestFullscreen();
        } catch (e) {
          error(e);
        }
      };
    } catch (e) {
      error(e);
    }
  }

  async function start() {
    try {
      const data = await request('/api/assets/v1/catalog?kind=' + kind);
      assets = data.assets;
      assets
        .filter((asset) => asset.kind === 'decoration')
        .forEach((asset, index) =>
          decorationTitles.set(asset.id, 'Декорация ' + String(index + 1).padStart(2, '0')),
        );
      renderFilters();
      render();
      if (assets.length) await select(assets[0]);
      if (kind === 'icon') {
        const style = await request('/api/assets/v1/icon-style');
        $('style-prompt').textContent = style.prompt;
        $('copy-prompt').onclick = () => copy(style.prompt, $('copy-prompt'), 'Копировать промпт');
      }
    } catch (e) {
      $('asset-count').textContent = 'Библиотека недоступна';
      error(e);
    }
  }
  return { start, select, render };
}
