/** Browser state stores choices and request lifecycle; geometry stays in Python. */
export const COLOR_LABELS = {
  hair: 'Волосы',
  eyes: 'Глаза',
  skin: 'Кожа / мех',
  cloth: 'Ткань',
  accent: 'Отделка',
  metal: 'Металл',
  leather: 'Кожа доспеха',
  secondary: 'Цвет узора',
  back_primary: 'Основа / перья',
  back_secondary: 'Отделка / панели',
  back_frame: 'Каркас / крепления',
};
export const SLOT_LABELS = {
  '': 'Все',
  head: 'Голова',
  torso: 'Торс',
  left_arm: 'Л. рука',
  right_arm: 'П. рука',
  left_leg: 'Л. нога',
  right_leg: 'П. нога',
  back_attachment: 'Спина',
};
export function createState(catalog = null) {
  return {
    catalog,
    settings: catalog ? structuredClone(catalog.active_defaults || catalog.defaults) : null,
    viewer: null,
    ready: false,
    actionBusy: false,
    linkedLimbs: true,
    viewingPublished: false,
    serial: 0,
    savedSerial: 0,
    timer: null,
    controller: null,
  };
}
export function getRace(state) {
  return (state.catalog.all_races || state.catalog.races).find((r) => r.id === state.settings.race);
}
export function migrateSettings(s, catalog) {
  const result = structuredClone(s);
  if (result.schema_version === 1) {
    result.schema_version = 2;
    result.decor = Object.fromEntries(
      ['emblem', 'shoulders', 'belt', 'headwear', 'pattern'].map((k) => [k, 'none']),
    );
    Object.assign(result.colors, { metal: null, leather: null, secondary: null });
  }
  if (result.schema_version === 2) {
    result.schema_version = 3;
    Object.assign(result.decor, { beard: 'original', mustache: 'original' });
    result.features = Object.fromEntries(Object.keys(catalog.features).map((k) => [k, 'original']));
  }
  if (result.schema_version === 3) {
    result.schema_version = 4;
    Object.assign(result.colors, { back_primary: null, back_secondary: null, back_frame: null });
  }
  if (result.schema_version === 4) {
    result.schema_version = 5;
    result.reference_parts = Object.fromEntries(
      Object.keys(catalog.defaults.reference_parts).map((id) => [id, 0]),
    );
  }
  if (result.schema_version !== catalog.settings_version)
    throw Error('Этот персонаж использует неподдерживаемую версию настроек');
  return result;
}
