import { getRace, COLOR_LABELS, migrateSettings } from './state.js';
import { API_BASE } from './api.js';

export function assemblyDescription({ animation_support, rigging }) {
  return rigging === 'none' || animation_support === 'authoring_only'
    ? 'статический черновик без скелета и анимаций'
    : 'части собираются в одну модель со скелетом';
}

/** Render the catalog and active choices. Selection rules belong to selection.js. */
export function createOptions(
  state,
  {
    document = globalThis.document,
    selection,
    picker,
    palettes,
    createCard,
    onRefresh,
    renderAttributes,
  } = {},
) {
  const $ = (id) => document.getElementById(id);
  const race = () => getRace(state);
  const API = API_BASE;
  const colorLabels = COLOR_LABELS;
  const commit = () => selection.commit();
  const chooseField = (...args) => selection.chooseField(...args);
  const chooseRace = (id) => selection.chooseRace(id);
  const referenceMode = () => selection.referenceMode();
  const refreshPartPicker = () => picker.refreshPartPicker();
  const refreshPaletteSelection = () => palettes.refreshPaletteSelection();
  const card = createCard || renderCard;
  const attributeTargets = {
    male_faces: 'face',
    female_faces: 'face',
    race_heads: 'face',
    hair: 'hair',
    brows: 'brows',
    eyes: 'eye',
    noses: 'nose',
    ears: 'ears',
    jaws: 'jaw',
    mouths: 'mouth',
    beards: 'beard',
    mustaches: 'mustache',
    body_forms: 'form',
    male_clothes: 'outfit',
    female_clothes: 'outfit',
    arms: 'arms',
    legs: 'legs',
    gloves: 'arms',
    boots: 'legs',
    shoulders: 'shoulders',
    belts: 'belt',
    headwear: 'headwear',
    emblems: 'emblem',
    back: 'back',
    accessories: 'belt',
    patterns: 'pattern',
    colorways: 'palette',
  };
  function svg(markup) {
    return `<svg viewBox="0 0 100 90" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">${markup}</svg>`;
  }
  function silhouette(width = 1) {
    const x = 19 * width;
    return svg(
      `<circle cx="50" cy="15" r="8" fill="#cdb386"/><path d="M${50 - x} 27 L${50 + x} 27 L${50 + x * 0.75} 53 L${50 + x * 0.6} 79 L54 79 L50 58 L46 79 L${50 - x * 0.6} 79 L${50 - x * 0.75} 53 Z" fill="#a7b6aa"/><path d="M${50 - x} 30 L${42 - x} 52 M${50 + x} 30 L${58 + x} 52" stroke="#a7b6aa" stroke-width="7" stroke-linecap="round"/>`,
    );
  }
  function eyeIcon(key) {
    const profile = {
      original: [1, 1],
      round: [1, 1.12],
      narrow: [1.06, 0.84],
      almond: [1.1, 0.94],
      wide: [1.14, 1.02],
      deep: [0.94, 0.9],
      small: [0.86, 0.86],
      large: [1.13, 1.13],
      slanted: [1.07, 0.9],
      soft: [0.96, 1.07],
    }[key] || [1, 1];
    return svg(
      `<g transform="translate(50 44) scale(${profile.join(' ')})"><path d="M-34 0 Q0 -29 34 0 Q0 26 -34 0" fill="#d4d2bc"/><ellipse rx="11" ry="13" fill="${state.settings.colors.eyes || state.catalog.colors.eyes}"/><ellipse rx="4" ry="7" fill="#253238"/><path d="M-34 0 Q0 -29 34 0" fill="none" stroke="#b59976" stroke-width="4"/></g>`,
    );
  }
  function renderCard(container, { id, label, image, icon, number, description }, field, choose) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'visual-card';
    button.dataset.field = field;
    button.dataset.value = id;
    button.setAttribute('aria-label', label);
    if (description) button.title = description;
    button.setAttribute('aria-pressed', 'false');
    if (image) {
      const img = document.createElement('img');
      img.src = image;
      img.alt = '';
      img.loading = 'lazy';
      img.decoding = 'async';
      button.append(img);
    } else {
      const visual = document.createElement('div');
      if (icon) visual.innerHTML = icon;
      else {
        visual.className = 'empty-icon';
        visual.textContent = '∅';
      }
      button.append(visual);
    }
    if (number) {
      const n = document.createElement('span');
      n.className = 'card-number';
      n.textContent = String(number).padStart(2, '0');
      button.append(n);
    }
    const text = document.createElement('span');
    text.className = 'card-label';
    text.textContent = label;
    button.append(text);
    button.onclick = () => choose(id);
    $(container).append(button);
    return button;
  }
  function image(category, id) {
    return category === 'back' ||
      id.startsWith('expansion-') ||
      id.startsWith('flyer-') ||
      id.startsWith('native-') ||
      id.startsWith('anatomy-') ||
      id.startsWith('costume-') ||
      id.startsWith('reference-') ||
      id.startsWith('library-') ||
      id.startsWith('hair-') ||
      Object.hasOwn(state.catalog.decor, category) ||
      Object.hasOwn(state.catalog.features, category)
      ? `${API}/cards/v${state.catalog.cards_version}/${category}/${id}.png?revision=${id.includes('randomium-') ? 'randomiums-10' : 'component-fit-v2'}&gender=${state.settings.gender}`
      : null;
  }
  function shortLabel(id) {
    const label = state.catalog.face_labels[id];
    if (!label) return id.replaceAll('-', ' ');
    const prefix = state.catalog.races.find((r) => label.startsWith(r.label + ' · '));
    return prefix ? label.slice(prefix.label.length + 3) : label;
  }
  function raceImage(r) {
    if (r.anatomies?.male?.length) return image('face', r.anatomies.male[0].id);
    const o = r.attribute_options.male;
    const category = o.male_faces?.length
      ? 'male_faces'
      : o.race_heads?.length
        ? 'race_heads'
        : null;
    return category
      ? `${API}/attribute-parts/${category}/${o[category][0]}.png?revision=component-fit-v2`
      : image('face', r.library_faces[0]);
  }
  function renderAttributeOptions() {
    const options = race().attribute_options[state.settings.gender];
    for (const spec of state.catalog.attribute_library) {
      if (spec.id === 'colorways') continue;
      const allowed =
        spec.id === 'race_heads' && race().anatomies?.[state.settings.gender]?.length
          ? []
          : options[spec.id] || [];
      if (
        state.settings.reference_parts[spec.id] &&
        !allowed.includes(state.settings.reference_parts[spec.id])
      )
        state.settings.reference_parts[spec.id] = 0;
      if (!allowed.length) continue;
      const grid = $(attributeTargets[spec.id] + '-cards');
      if (!grid) continue;
      const resetLabels = {
        arms: 'Из костюма',
        legs: 'Из костюма',
        gloves: 'Без дополнительных перчаток',
        boots: 'Без дополнительной обуви',
        accessories: 'Без аксессуаров',
      };
      if (resetLabels[spec.id])
        card(grid.id, { id: '0', label: resetLabels[spec.id] }, 'reference_parts.' + spec.id, () =>
          selection.chooseAttribute(spec.id, 0),
        );
      for (const n of allowed)
        card(
          grid.id,
          {
            id: String(n),
            label:
              spec.id === 'headwear' && state.catalog.attribute_headwear_labels
                ? state.catalog.attribute_headwear_labels[n - 1]
                : state.settings.race === 'goblin' && spec.id === 'gloves'
                  ? race().goblin_glove_labels[n - 1]
                  : state.settings.race === 'goblin' && spec.id === 'boots'
                    ? race().goblin_boot_labels[n - 1]
                    : spec.id === 'patterns'
                      ? state.catalog.motif_labels[n - 1]
                      : spec.id === 'hair' && state.catalog.attribute_hair_labels[n]
                        ? state.catalog.attribute_hair_labels[n]
                        : 'Вариант ' + String(n).padStart(2, '0'),
            number: n,
            description: state.catalog.attribute_descriptions?.[spec.id]?.[n],
            image:
              API +
              '/attribute-parts/' +
              spec.id +
              '/' +
              n +
              '.png?revision=component-fit-v2' +
              ([
                'hair',
                'beards',
                'mustaches',
                'body_forms',
                'shoulders',
                'belts',
                'headwear',
                'boots',
              ].includes(spec.id)
                ? '&gender=' +
                  (state.settings.race === 'ghost' && spec.id === 'hair'
                    ? n >= 26 || (n >= 16 && n <= 20)
                      ? 'female'
                      : 'male'
                    : state.settings.gender)
                : '') +
              (state.settings.race === 'goblin' && ['gloves', 'boots'].includes(spec.id)
                ? '&race=goblin'
                : ''),
          },
          'reference_parts.' + spec.id,
          () => selection.chooseAttribute(spec.id, n),
        );
    }
  }
  function numberPartCards() {
    const labels = {
      face: 'Голова',
      hair: 'Волосы',
      brows: 'Брови',
      eye: 'Глаза',
      nose: 'Нос',
      ears: 'Уши',
      jaw: 'Челюсть',
      mouth: 'Рот',
      beard: 'Борода',
      mustache: 'Усы',
      form: 'Телосложение',
      outfit: 'Костюм',
      arms: 'Руки',
      legs: 'Ноги',
      shoulders: 'Наплечники',
      belt: 'Пояс',
      headwear: 'Головной убор',
      emblem: 'Эмблема',
      back: 'Спина',
      pattern: 'Узор',
    };
    for (const [target, label] of Object.entries(labels)) {
      let number = 0;
      for (const button of $(target + '-cards').children) {
        if (
          !button.dataset.field ||
          ['', '0', 'none', 'bald', 'original', 'profile'].includes(String(button.dataset.value))
        )
          continue;
        const text = button.querySelector('.card-label');
        if (!text) continue;
        const displayNumber = String(++number).padStart(2, '0');
        let badge = button.querySelector('.card-number');
        if (!badge) {
          badge = document.createElement('span');
          badge.className = 'card-number';
          button.append(badge);
        }
        badge.textContent = displayNumber;
        if (/^(Вариант|Лицо) \d+$/.test(text.textContent)) {
          const kind =
            { gloves: 'Перчатки', boots: 'Обувь', accessories: 'Аксессуар' }[
              button.dataset.field.split('.')[1]
            ] || label;
          text.textContent = kind + ' ' + displayNumber;
          button.setAttribute('aria-label', text.textContent);
        }
      }
    }
  }
  function clearOptions() {
    for (const id of [
      'race',
      'gender',
      'face',
      'hair',
      'form',
      'eye',
      'outfit',
      'arms',
      'legs',
      'back',
      ...Object.keys(state.catalog.features),
      ...Object.keys(state.catalog.decor),
    ])
      $(id + '-cards').replaceChildren();
  }
  function renderSectionLabels(r) {
    $('back-cards').closest('.collection').querySelector('h2').textContent = r.tail_options
      ? 'Хвост и жало'
      : 'Спина и крылья';
    $('headwear-cards').closest('.collection').querySelector('h2').textContent =
      r.id === 'beetle'
        ? 'Шлем жука'
        : r.mount_options?.headwear
          ? 'Сбруя и защита головы'
          : 'Головной убор';
    $('outfit-cards').closest('.collection').querySelector('h2').textContent = r.human_upper
      ? 'Конский корпус и одежда верха'
      : r.id === 'tree'
        ? 'Ствол трента'
        : ['crab', 'scorpion'].includes(r.id)
          ? 'Панцирь и корпус'
          : r.animal_body
            ? 'Корпус животного'
            : r.owned_body
              ? 'Расовое тело и комплект'
              : 'Костюм';
    $('shoulders-cards').closest('.collection').querySelector('h2').textContent =
      r.id === 'beetle'
        ? 'Грудная броня'
        : r.mount_options?.shoulders
          ? 'Защита животного'
          : r.owned_body
            ? 'Рукава и наплечники'
            : 'Наплечники';
    $('belt-cards').closest('.collection').querySelector('h2').textContent =
      r.id === 'beetle'
        ? 'Броня надкрыльев'
        : r.mount_options?.belt
          ? 'Седло и попона'
          : r.owned_body
            ? 'Штаны, шкуры и пояс'
            : 'Пояс и вещи';
    if (state.viewer.contract !== r.contract) {
      state.viewer.setBones(r.contract === 'humanoid_v1' ? state.catalog.bind_bones : []);
      state.viewer.contract = r.contract;
    }
    $('race-count').textContent = state.catalog.races.length + ' народов и видов';
    $('hair-cards').closest('.collection').querySelector('h2').textContent =
      r.id === 'beast-horse' ? 'Грива' : 'Волосы';
    $('hair-count').textContent =
      (Object.keys(r.mane_options || {}).length ||
        r.attribute_options[state.settings.gender].hair?.length ||
        r.library_hair.length) + ' вариантов';
    $('arm-label').textContent = r.arm_label;
    $('leg-label').textContent = r.leg_label;
  }
  function renderIdentity(r) {
    for (const item of state.catalog.races)
      card(
        'race-cards',
        { id: item.id, label: item.label, image: raceImage(item) },
        'race',
        chooseRace,
      );
    for (const [id, label] of Object.entries(
      r.gender_mode === 'neutral' ? { male: 'Не выражен' } : { male: 'Мужчина', female: 'Женщина' },
    )) {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = label;
      b.dataset.field = 'gender';
      b.dataset.value = id;
      b.onclick = () => selection.chooseGender(id);
      $('gender-cards').append(b);
    }
    $('gender-note').textContent = r.gender_mode === 'neutral' ? 'Пол не выражен' : '';
  }
  function renderHeads(r) {
    const faces = [
      ...new Set([
        ...(r.owned_body || r.animal_body
          ? r.body_variants[state.settings.gender].map((d) => d.id)
          : [...r.library_faces, ...(r.reference_faces || [])]),
        ...(r.anatomies?.[state.settings.gender] || []).map((a) => a.id),
      ]),
    ];
    if (!faces.includes(state.settings.face)) faces.push(state.settings.face);
    for (const [i, id] of faces.entries())
      card(
        'face-cards',
        {
          id,
          label:
            (r.anatomies?.[state.settings.gender] || []).find((a) => a.id === id)?.label ||
            (r.owned_body ||
            ['centaur', 'beast-elephant', 'crab', 'scorpion', 'beetle'].includes(r.id)
              ? shortLabel(id)
              : 'Лицо ' + String(i + 1).padStart(2, '0')),
          image: image('face', id),
          number: i + 1,
        },
        'face',
        (id) => chooseField('face', id),
      );
    const hair = r.anatomy_only
      ? ['original']
      : r.human_upper
        ? ['original', 'bald']
        : Object.keys(r.mane_options || {}).length
          ? ['original', 'bald', ...Object.keys(r.mane_options)]
          : ['original', 'bald', ...r.library_hair, ...(r.reference_hair || [])];
    if (!hair.includes(state.settings.hair)) hair.push(state.settings.hair);
    for (const id of hair)
      card(
        'hair-cards',
        {
          id,
          label:
            id === 'original'
              ? r.animal_body
                ? 'Грива комплекта'
                : 'Как у лица'
              : state.catalog.hair[id],
          image:
            r.id === 'beast-horse' && id !== 'original' && id !== 'bald'
              ? API + '/horse-cards/mane/' + id + '.png?revision=constructor-hair-satyr-1'
              : image('hair', id === 'original' ? state.settings.face : id),
        },
        'hair',
        (id) => chooseField('hair', id),
      );
  }
  function renderPhysique(r) {
    const widths = [1, 0.94, 1.06, 0.9, 1.03, 1.1, 1.14, 0.86, 0.97, 1.18];
    Object.entries(Object.keys(r.form_options || {}).length ? r.form_options : state.catalog.forms)
      .filter(
        ([id]) =>
          (r.id === 'beast-horse' || !id.startsWith('horse_')) &&
          (!r.owned_body || r.id === 'ghost') &&
          (r.contract === 'humanoid_v1' || !['muscular', 'bodybuilder', 'strongman'].includes(id)),
      )
      .forEach(([id, label], i) =>
        card(
          'form-cards',
          {
            id,
            label,
            image:
              r.id === 'ghost'
                ? API + '/ghost-cards/form/' + id + '.png?revision=constructor-hair-satyr-1'
                : r.id === 'beast-horse'
                  ? API + '/horse-cards/form/' + id + '.png?revision=constructor-hair-satyr-1'
                  : null,
            icon: silhouette(widths[i]),
          },
          'form',
          (id) => chooseField('form', id),
        ),
      );
    for (const [id, label] of Object.entries(state.catalog.eyes).filter(
      ([id]) => !r.anatomy_only || id === 'original',
    ))
      card('eye-cards', { id, label, icon: eyeIcon(id) }, 'eye_shape', (id) =>
        chooseField('eye_shape', id),
      );
  }
  function renderCostumes(r) {
    for (const [target, field] of [
      ['outfit', 'outfit'],
      ['arms', 'arms'],
      ['legs', 'legs'],
    ]) {
      const ids = [
        ...new Set(
          r.owned_body || r.animal_body
            ? r.body_variants[state.settings.gender].map((d) => d.id)
            : [
                ...r.library_outfits,
                ...(r.reference_outfits || []),
                ...(referenceMode()
                  ? state.catalog.outfits
                      .filter((o) => o.id.startsWith('costume-'))
                      .map((o) => o.id)
                  : []),
              ],
        ),
      ];
      if (!ids.includes(state.settings[field])) ids.push(state.settings[field]);
      ids.forEach((id, i) =>
        card(
          target + '-cards',
          { id, label: shortLabel(id), image: image(target, id), number: i + 1 },
          field,
          (id) => chooseField(field, id),
        ),
      );
    }
  }
  function renderFeatures(r) {
    for (const [category, options] of Object.entries(state.catalog.features)) {
      if (!r.feature_options[category]?.length) {
        const note = document.createElement('p');
        note.className = 'hint';
        note.textContent =
          r.id === 'skeleton'
            ? 'У скелета нет внешних ушей.'
            : 'Выберите расовый вариант головы выше.';
        $(category + '-cards').append(note);
        continue;
      }
      for (const [id, label] of Object.entries(options).filter(
        ([id]) => !r.feature_options?.[category] || r.feature_options[category].includes(id),
      ))
        card(
          category + '-cards',
          {
            id,
            label: r.feature_labels?.[category]?.[id] || label,
            image: image(category, (r.human_upper ? 'human' : r.id) + '--' + id),
          },
          'features.' + category,
          (id) => selection.chooseFeature(category, id),
        );
    }
  }
  function renderDecorations(r) {
    for (const [category, options] of Object.entries({
      ...state.catalog.decor,
      ...(r.decor_options || {}),
      ...(r.mount_options || {}),
    })) {
      if (r.hidden_parts?.includes(category)) continue;
      if (
        r.anatomy_only ||
        (r.contract !== 'humanoid_v1' &&
          !r.human_upper &&
          category !== 'pattern' &&
          !r.mount_options?.[category])
      ) {
        const note = document.createElement('p');
        note.className = 'hint';
        note.textContent = 'Для этого типа используются собственные анатомические детали.';
        $(category + '-cards').append(note);
        continue;
      }
      for (const [id, label] of Object.entries(options).filter(
        ([id]) =>
          (id !== 'original' ||
            state.settings.decor[category] === 'original' ||
            Boolean(r.decor_options?.[category])) &&
          (r.owned_body || !id.startsWith('wild_')),
      ))
        card(
          category + '-cards',
          {
            id,
            label,
            image:
              id === 'none'
                ? null
                : id === 'original' && r.emblem_defaults?.[state.settings.outfit]
                  ? image('emblem', r.emblem_defaults[state.settings.outfit])
                  : r.mount_options?.[category]
                    ? API +
                      '/mount-cards/' +
                      r.id +
                      '/' +
                      category +
                      '/' +
                      id +
                      '.png?revision=constructor-hair-satyr-1'
                    : image(category, id),
          },
          'decor.' + category,
          (id) => selection.chooseDecoration(category, id),
        );
    }
  }
  function renderBack(r) {
    card(
      'back-cards',
      {
        id: '',
        label: r.tail_options
          ? 'Хвост выбранного корпуса'
          : r.animal_body
            ? 'Без дополнения; хвост из корпуса'
            : 'Без плаща и крыльев',
      },
      'back',
      () => chooseField('back', null),
    );
    const back = state.catalog.back.filter(
      (b) =>
        (b.contract === r.contract || (r.animal_body && b.contract === 'humanoid_v1')) &&
        (b.id.startsWith('back-') ||
          b.id.startsWith('wing-') ||
          r.library_outfits.includes(b.id) ||
          (r.reference_outfits || []).includes(b.id) ||
          b.id === state.settings.back),
    );
    for (const b of back)
      card('back-cards', { id: b.id, label: b.label, image: image('back', b.id) }, 'back', (id) =>
        chooseField('back', id),
      );
  }
  function renderOptions() {
    clearOptions();
    const r = race();
    renderSectionLabels(r);
    renderIdentity(r);
    renderHeads(r);
    renderPhysique(r);
    renderCostumes(r);
    renderFeatures(r);
    renderDecorations(r);
    renderBack(r);
    if (renderAttributes) renderAttributes();
    else renderAttributeOptions();
    numberPartCards();
    if (onRefresh) onRefresh();
    else refreshSelection();
    refreshPartPicker();
  }
  function isCardSelected(field, value) {
    const [name, key] = field.split('.'),
      refs = state.settings.reference_parts;
    const overrides = {
      face: ['male_faces', 'female_faces', 'race_heads'],
      hair: ['hair'],
      outfit: ['male_clothes', 'female_clothes'],
      arms: ['arms'],
      legs: ['legs'],
      form: ['body_forms'],
      eye_shape: ['eyes'],
      back: ['back'],
      'features.nose': ['noses'],
      'features.ears': ['ears'],
      'features.jaw': ['jaws'],
      'features.brows': ['brows'],
      'features.mouth': ['mouths'],
      'decor.beard': ['beards'],
      'decor.mustache': ['mustaches'],
      'decor.headwear': ['headwear'],
      'decor.shoulders': ['shoulders'],
      'decor.belt': ['belts', 'accessories'],
      'decor.emblem': ['emblems'],
      'decor.pattern': ['patterns'],
    };
    if ((overrides[field] || []).some((k) => refs[k])) return false;
    if (
      ['arms', 'legs'].includes(field) &&
      state.settings[field] === state.settings.outfit &&
      (refs.male_clothes || refs.female_clothes)
    )
      return false;
    if (name === 'reference_parts' && String(value) === '0') {
      const decor = {
        beards: 'beard',
        mustaches: 'mustache',
        headwear: 'headwear',
        shoulders: 'shoulders',
        belts: 'belt',
        emblems: 'emblem',
        patterns: 'pattern',
      };
      if (decor[key] && state.settings.decor[decor[key]] !== 'none') return false;
      if (key === 'hair' && state.settings.hair !== 'bald') return false;
      if (key === 'body_forms' && state.settings.form !== 'regular') return false;
      if (['arms', 'legs'].includes(key) && state.settings[key] !== state.settings.outfit)
        return false;
      const feature = { noses: 'nose', ears: 'ears', jaws: 'jaw', brows: 'brows', mouths: 'mouth' }[
        key
      ];
      if (feature && !['profile', 'original'].includes(state.settings.features[feature]))
        return false;
    }
    const selected = key ? state.settings[name][key] : state.settings[name];
    return String(selected ?? '') === String(value);
  }
  function refreshSelection() {
    refreshPaletteSelection();
    $('contract-note').textContent = assemblyDescription(race());
    for (const b of document.querySelectorAll('[data-field]'))
      b.setAttribute('aria-pressed', String(isCardSelected(b.dataset.field, b.dataset.value)));
    for (const b of document.querySelectorAll('[data-palette]')) {
      const p = state.catalog.colorways.find((p) => p.id === b.dataset.palette);
      b.setAttribute(
        'aria-pressed',
        String(Object.entries(p.colors).every(([k, v]) => state.settings.colors[k] === v)),
      );
    }
    for (const b of document.querySelectorAll('[data-back-palette]')) {
      const p = state.catalog.colorways.find((p) => p.id === b.dataset.backPalette);
      b.setAttribute(
        'aria-pressed',
        String(
          state.settings.colors.back_primary === p.colors.cloth &&
            state.settings.colors.back_secondary === p.colors.accent &&
            state.settings.colors.back_frame === p.colors.metal,
        ),
      );
    }
    $('link-limbs').checked = state.linkedLimbs;
    $('eye-size').disabled = Boolean(race().anatomy_only);
    $('eye-size').value = Math.round(state.settings.eye_size * 100);
    $('eye-size-label').textContent = $('eye-size').value + '%';
    for (const k of Object.keys(colorLabels)) {
      $('color-' + k).value = state.settings.colors[k] || state.catalog.colors[k];
      $('use-' + k).checked = Boolean(state.settings.colors[k]);
      $('color-' + k).disabled = !state.settings.colors[k];
    }
    for (const b of $('hair-cards').children)
      if (b.dataset.value === 'original') {
        const img = b.querySelector('img');
        if (img) img.src = image('hair', state.settings.face) || img.src;
      }
    if (race().id === 'randomium') {
      const img = $('emblem-cards').querySelector('[data-value="original"] img');
      if (img) img.src = image('emblem', race().emblem_defaults[state.settings.outfit]);
    }
    for (const b of $('eye-cards').children)
      if (b.dataset.field === 'eye_shape') b.firstElementChild.innerHTML = eyeIcon(b.dataset.value);
    $('label-skin').textContent =
      state.settings.race === 'skeleton'
        ? 'Кость'
        : state.settings.race === 'golem'
          ? 'Камень'
          : state.settings.race === 'kobold'
            ? 'Чешуя'
            : 'Кожа / мех';
    $('reference-link').replaceChildren();
    const reference = (state.catalog.reference_presets || []).find(
      (p) => p.id === state.settings.face,
    );
    if (reference) {
      const a = document.createElement('a');
      a.href = reference.reference_image;
      a.target = '_blank';
      a.rel = 'noopener';
      a.textContent = 'Открыть исходный референс · ' + reference.label;
      $('reference-link').append(a);
    }
    refreshPartPicker();
    $('character-name').textContent =
      race().label +
      ' · ' +
      (race().gender_mode === 'neutral'
        ? 'персонаж'
        : state.settings.gender === 'female'
          ? 'женщина'
          : 'мужчина');
  }
  function createReferenceCards() {
    for (const p of state.catalog.reference_presets || [])
      card(
        'reference-cards',
        { id: p.id, label: p.label, image: image('outfit', p.id) },
        'outfit',
        () => {
          state.settings = migrateSettings(p.settings, state.catalog);
          state.linkedLimbs = true;
          renderOptions();
          commit();
        },
      );
  }
  return {
    renderOptions,
    renderAttributeOptions,
    numberPartCards,
    isCardSelected,
    refreshSelection,
    createReferenceCards,
    card: renderCard,
    image,
  };
}
