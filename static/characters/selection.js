/** Selection rules only mutate settings; the caller schedules previews and rendering. */
import { getRace } from './state.js';
export function createSelection(
  state,
  { onChange = () => {}, onOptionsChanged = () => {}, random = Math.random } = {},
) {
  const race = () => getRace(state);
  const renderOptions = () => onOptionsChanged();
  const pick = (items) => items[Math.floor(random() * items.length)];
  function commit() {
    if (state.settings.race === 'randomium') {
      for (const key of Object.keys(state.settings.colors)) state.settings.colors[key] = null;
      state.settings.reference_parts.colorways = 0;
    }
    onChange();
  }
  function chooseField(field, id) {
    state.settings[field] = id;
    if (field === 'face' && id.match(/^expansion-(ape|owl)-/))
      state.settings.features.mouth = 'profile';
    const clear = {
      face: ['male_faces', 'female_faces', 'race_heads'],
      hair: ['hair'],
      outfit: ['male_clothes', 'female_clothes'],
      arms: ['arms'],
      legs: ['legs'],
      back: ['back'],
      form: ['body_forms'],
      eye_shape: ['eyes'],
    };
    for (const key of clear[field] || []) state.settings.reference_parts[key] = 0;
    if (field === 'outfit' && state.linkedLimbs) {
      state.settings.arms = state.settings.legs = id;
      state.settings.reference_parts.arms = state.settings.reference_parts.legs = 0;
    }
    if (field === 'arms' || field === 'legs') state.linkedLimbs = false;
    commit();
  }
  function chooseRace(id) {
    state.settings.race = id;
    const r = race();
    if (r.gender_mode === 'neutral') state.settings.gender = 'male';
    if (r.owned_body || r.contract !== 'humanoid_v1') state.settings.form = 'regular';
    state.settings.face =
      state.settings.gender === 'female' && r.female_face ? r.female_face : r.library_faces[0];
    state.settings.hair = 'original';
    state.settings.outfit =
      state.settings.arms =
      state.settings.legs =
        r.owned_body || r.animal_body
          ? r.body_variants[state.settings.gender][0].id
          : r.library_outfits[0];
    state.settings.back =
      r.owned_body && r.id === 'kobold' ? state.settings.face : r.default_back || null;
    state.settings.eye_size = 1;
    state.settings.eye_shape = 'original';
    state.settings.reference_parts = structuredClone(state.catalog.defaults.reference_parts);
    state.settings.features = Object.fromEntries(
      Object.keys(state.catalog.features).map((k) => [k, 'profile']),
    );
    if (r.animal_body || r.flying_body)
      for (const key of ['skin', 'hair', 'eyes']) state.settings.colors[key] = null;
    for (const key of Object.keys(state.settings.decor))
      if (key !== 'pattern' || r.owned_body || r.flying_body) state.settings.decor[key] = 'none';
    if (r.id === 'randomium') state.settings.decor.emblem = 'original';
    state.linkedLimbs = true;
    useReferenceBase();
    renderOptions();
    commit();
  }
  function referenceMode() {
    return race().contract === 'humanoid_v1' && !race().owned_body;
  }
  function useReferenceBase() {
    if (!referenceMode()) return;
    const o = race().attribute_options[state.settings.gender],
      head = o[state.settings.gender + '_faces']?.length
        ? state.settings.gender + '_faces'
        : 'race_heads';
    for (const key of ['male_faces', 'female_faces', 'race_heads'])
      if (key !== head) state.settings.reference_parts[key] = 0;
    if (race().anatomies?.[state.settings.gender]?.length) {
      for (const key of ['male_faces', 'female_faces', 'race_heads'])
        state.settings.reference_parts[key] = 0;
      state.settings.face = race().anatomies[state.settings.gender][0].id;
      state.settings.hair = 'bald';
    } else if (o[head]?.length && !o[head].includes(state.settings.reference_parts[head]))
      state.settings.reference_parts[head] = o[head][0];
    const clothes = state.settings.gender + '_clothes';
    state.settings.reference_parts[
      state.settings.gender === 'male' ? 'female_clothes' : 'male_clothes'
    ] = 0;
    if (state.settings.race === 'goblin') {
      state.settings.outfit = state.settings.arms = state.settings.legs = race().library_outfits[0];
      state.settings.reference_parts[clothes] = 0;
    } else if (state.settings.race === 'skeleton') {
      state.settings.reference_parts[clothes] = 0;
    } else if (o[clothes]?.length && !o[clothes].includes(state.settings.reference_parts[clothes]))
      state.settings.reference_parts[clothes] = o[clothes][0];
    state.settings.features = Object.fromEntries(
      Object.keys(state.catalog.features).map((k) => [k, 'profile']),
    );
    state.settings.form = 'regular';
    state.settings.eye_shape = 'original';
    state.settings.back = null;
    for (const key of Object.keys(state.settings.decor)) state.settings.decor[key] = 'none';
  }
  function chooseGender(id) {
    const r = race();
    state.settings.gender = id;
    if (r.human_upper) {
      for (const k of Object.keys(state.settings.reference_parts))
        state.settings.reference_parts[k] = 0;
      state.settings.hair = 'original';
    }
    state.settings.face = id === 'female' && r.female_face ? r.female_face : r.library_faces[0];
    if (r.owned_body || r.animal_body) {
      state.settings.face = r.body_variants[id][0].id;
      state.settings.outfit = state.settings.arms = state.settings.legs = state.settings.face;
      state.settings.back = r.id === 'kobold' ? state.settings.face : null;
    }
    useReferenceBase();
    renderOptions();
    commit();
  }
  function randomize() {
    if (referenceMode()) {
      state.settings.reference_parts = Object.fromEntries(
        Object.keys(state.catalog.defaults.reference_parts).map((id) => [id, 0]),
      );
      useReferenceBase();
      const options = race().attribute_options[state.settings.gender];
      for (const spec of state.catalog.attribute_library) {
        const allowed =
          spec.id === 'race_heads' && race().anatomies?.[state.settings.gender]?.length
            ? []
            : options[spec.id] || [];
        if (
          !allowed.length ||
          (spec.id === 'race_heads' && options[state.settings.gender + '_faces']?.length)
        )
          continue;
        state.settings.reference_parts[spec.id] = pick(allowed);
      }
      state.settings.hair = 'original';
      state.settings.eye_size = pick([0.9, 1, 1.1]);
      state.linkedLimbs = false;
      for (const key of Object.keys(state.settings.colors)) state.settings.colors[key] = null;
      renderOptions();
      commit();
      return;
    }
    state.settings.reference_parts = Object.fromEntries(
      Object.keys(state.catalog.defaults.reference_parts).map((id) => [id, 0]),
    );
    const r = race();
    if (r.flying_body) {
      const own = r.library_outfits;
      state.settings.face = pick(r.library_faces);
      state.settings.outfit = state.settings.arms = state.settings.legs = pick(own);
      state.settings.hair = 'original';
      state.settings.form = 'regular';
      state.settings.eye_shape = 'original';
      state.settings.eye_size = 1;
      state.settings.back = null;
      state.settings.colors = { ...state.catalog.defaults.colors };
      for (const key of Object.keys(state.settings.decor)) state.settings.decor[key] = 'none';
      state.linkedLimbs = true;
      renderOptions();
      commit();
      return;
    }
    if (r.animal_body || ['crab', 'beetle', 'scorpion'].includes(r.id)) {
      const own = r.library_outfits;
      state.settings.face = pick(r.library_faces);
      state.settings.outfit = pick(own);
      state.settings.arms = pick(own);
      state.settings.legs = pick(own);
      state.settings.form = 'regular';
      state.settings.hair = 'original';
      state.settings.eye_shape = 'original';
      state.settings.eye_size = 1;
      state.settings.back = null;
      for (const key of Object.keys(state.settings.decor)) state.settings.decor[key] = 'none';
      for (const key of Object.keys(state.settings.features))
        state.settings.features[key] = 'profile';
      state.settings.colors = { ...state.catalog.defaults.colors };
      state.linkedLimbs = false;
      renderOptions();
      commit();
      return;
    }
    if (r.human_upper) {
      state.settings.face = pick(r.library_faces);
      state.settings.outfit = pick(r.library_outfits);
      state.settings.arms = pick(r.library_outfits);
      state.settings.legs = pick(r.library_outfits);
      state.settings.form = 'regular';
      state.settings.hair = 'original';
      state.settings.eye_shape = 'original';
      state.settings.eye_size = 1;
      state.settings.back = null;
      for (const key of Object.keys(state.settings.decor)) state.settings.decor[key] = 'none';
      for (const key of Object.keys(state.settings.features))
        state.settings.features[key] = 'profile';
      for (const spec of state.catalog.attribute_library) {
        const allowed = r.attribute_options[state.settings.gender][spec.id] || [];
        if (allowed.length) state.settings.reference_parts[spec.id] = pick(allowed);
      }
      state.linkedLimbs = false;
      renderOptions();
      commit();
      return;
    }
    if (r.owned_body) {
      const own = r.body_variants[state.settings.gender];
      state.settings.face = pick(own).id;
      state.settings.outfit = state.settings.arms = state.settings.legs = pick(own).id;
      state.settings.hair = 'original';
      state.settings.form = 'regular';
      state.settings.eye_shape = 'original';
      state.settings.eye_size = 1;
      state.settings.back = r.id === 'kobold' ? state.settings.outfit : null;
      state.linkedLimbs = true;
      renderOptions();
      commit();
      return;
    }
    state.settings.face = pick(r.library_faces);
    state.settings.hair = pick(r.library_hair);
    state.settings.outfit = pick(r.library_outfits);
    state.settings.arms = state.settings.legs = state.settings.outfit;
    state.linkedLimbs = true;
    state.settings.form = pick(Object.keys(state.catalog.forms));
    state.settings.eye_shape = pick(Object.keys(state.catalog.eyes));
    state.settings.eye_size = pick([0.9, 1, 1.1]);
    Object.assign(state.settings.colors, pick(state.catalog.colorways).colors);
    state.settings.colors.hair = pick(['#594430', '#303539', '#bca578', '#954f38', '#c4c7b7']);
    state.settings.colors.eyes = pick(['#568b95', '#92a05d', '#885844', '#c4a161']);
    for (const key of Object.keys(state.catalog.decor))
      state.settings.decor[key] =
        r.contract === 'humanoid_v1' || key === 'pattern'
          ? pick(Object.keys(state.catalog.decor[key]).filter((id) => id !== 'original'))
          : 'none';
    for (const key of Object.keys(state.catalog.features))
      state.settings.features[key] =
        r.contract === 'humanoid_v1' ? pick(Object.keys(state.catalog.features[key])) : 'profile';
    state.settings.back = null;
    renderOptions();
    commit();
  }
  function chooseAttribute(category, number) {
    if (number === 0) {
      state.settings.reference_parts[category] = 0;
      if (['arms', 'legs'].includes(category)) state.settings[category] = state.settings.outfit;
      commit();
      return;
    }
    state.settings.reference_parts[category] = number;
    if (category === 'hair') state.settings.hair = 'original';
    if (category === 'body_forms') state.settings.form = 'regular';
    if (['arms', 'legs'].includes(category)) state.linkedLimbs = false;
    if (['male_clothes', 'female_clothes'].includes(category) && !race().human_upper) {
      state.settings.outfit = 'library-human-01';
      if (state.linkedLimbs) state.settings.arms = state.settings.legs = 'library-human-01';
    }
    if (['male_clothes', 'female_clothes'].includes(category) && state.linkedLimbs) {
      state.settings.reference_parts.arms = 0;
      state.settings.reference_parts.legs = 0;
    }
    if (['male_faces', 'female_faces', 'race_heads'].includes(category)) {
      for (const k of ['male_faces', 'female_faces', 'race_heads'])
        if (k !== category) state.settings.reference_parts[k] = 0;
      for (const k of ['skin', 'eyes']) state.settings.colors[k] = null;
    }
    if (category === 'hair' || category === 'beards' || category === 'mustaches')
      state.settings.colors.hair = null;
    if (category === 'colorways') {
      for (const k of ['cloth', 'accent', 'metal', 'leather', 'secondary'])
        state.settings.colors[k] = null;
    }
    commit();
  }
  function chooseFeature(category, id) {
    state.settings.features[category] = id;
    state.settings.reference_parts[
      { nose: 'noses', ears: 'ears', jaw: 'jaws', brows: 'brows', mouth: 'mouths' }[category]
    ] = 0;
    commit();
  }
  function chooseDecoration(category, id) {
    state.settings.decor[category] = id;
    const k = {
      beard: 'beards',
      mustache: 'mustaches',
      emblem: 'emblems',
      shoulders: 'shoulders',
      belt: 'belts',
      headwear: 'headwear',
      pattern: 'patterns',
    }[category];
    if (k) state.settings.reference_parts[k] = 0;
    if (category === 'belt') state.settings.reference_parts.accessories = 0;
    commit();
  }
  return {
    commit,
    chooseField,
    chooseAttribute,
    chooseFeature,
    chooseDecoration,
    chooseRace,
    chooseGender,
    referenceMode,
    useReferenceBase,
    randomize,
  };
}
