"""Rebuild UI thumbnails from the same choices used by the constructor."""
import tempfile
from pathlib import Path

import numpy as np


def selector(path):
    """Describe an existing generated card using stable constructor choices."""
    from . import workshop_constructor as e
    from .constructor_atlas import defaults, part_folder
    from .constructor_cache import reference
    from .constructor_decor import OPTIONS
    from .constructor_racial_anatomy import VARIANTS
    # A preview beside an immutable recipe belongs to that exact source,
    # including its category and revision. Never guess a costume from its number.
    for recipe in (path.with_suffix('.recipe.json'), path.parent / 'recipe.json'):
        if recipe.is_file():
            return {'kind': 'preview', 'size': 256, 'recipes': [reference(recipe)]}
    categories = {'face', 'hair', 'outfit', 'arms', 'legs', 'headwear', 'eyes',
                  'nose', 'ears', 'jaw', 'mouth', 'brows', 'beard', 'beards',
                  'mustache', 'mustaches', 'shoulders', 'belts', 'belt', 'patterns',
                  'pattern', 'emblems', 'emblem', 'gloves', 'boots', 'form', 'back', 'palette'}
    categories.update(defaults())
    explicit_category = next((p for p in reversed(path.parts[:-1]) if p in categories), None)
    category = explicit_category or 'outfit'
    if 'static_palettes' in path.parts:
        category = 'palette'
    category = {'beards': 'beard', 'mustaches': 'mustache', 'belts': 'belt',
                'patterns': 'pattern', 'emblems': 'emblem'}.get(category, category)
    if 'hair_review' in path.parts:
        category = 'hair'
    gender = 'female' if 'female' in path.parts or category.startswith('female_') else 'male'
    identifier = path.stem
    anatomy = VARIANTS.get(identifier) if category in {'face', 'hair'} else None
    if anatomy is not None:
        gender = anatomy['gender']
    if identifier == 'front' and path.parent.name.isdigit():
        identifier = path.parent.name
    designs = {d['id'] for d in [*e.LIBRARY_DESIGNS, *e.REFERENCE_DESIGNS]}
    donor = next((p for p in reversed(path.parts[:-1]) if p in designs), None)
    if donor and identifier in {'front', 'face', 'hair', 'outfit', 'arms', 'legs'}:
        if explicit_category is None and identifier in categories:
            category = identifier
        identifier = donor
    aliases = {'face': gender + '_faces', 'outfit': gender + '_clothes', 'beard': 'beards',
               'mustache': 'mustaches', 'belt': 'belts', 'emblem': 'emblems', 'pattern': 'patterns',
               'nose': 'noses', 'jaw': 'jaws', 'mouth': 'mouths'}
    if identifier.isdigit():
        if explicit_category is None:
            return None
        recipe = part_folder(aliases.get(category, category), int(identifier)) / 'recipe.json'
        if recipe.exists():
            return {'kind': 'preview', 'size': 256, 'recipes': [reference(recipe)]}
    known = (anatomy is not None or identifier in designs or identifier in OPTIONS.get(category, {})
             or category == 'hair' and identifier in e.HAIR
             or category in {'outfit', 'arms', 'legs'} and identifier in e.OUTFITS
             or category == 'form' and identifier in e.FORMS
             or category in e.FEATURES and '--' in identifier
             or category == 'back' and identifier in e.BACK_IDS)
    if category == 'palette':
        from .constructor_palette_previews import options
        known = identifier == 'current' or any(p['id'] == identifier for p in options())
    if not known:
        return None
    return {'kind': 'card', 'category': category, 'identifier': identifier, 'gender': gender}


def arrays(spec):
    from . import workshop_constructor as e
    from .constructor_atlas import load, part_folder
    from .constructor_decor import OPTIONS
    from .constructor_racial_anatomy import VARIANTS
    category, identifier = spec['category'], spec['identifier']
    gender = spec.get('gender', 'male')
    aliases = {'face': gender + '_faces', 'outfit': gender + '_clothes', 'eye': 'eyes',
               'nose': 'noses', 'jaw': 'jaws', 'mouth': 'mouths', 'beard': 'beards',
               'mustache': 'mustaches', 'belt': 'belts', 'emblem': 'emblems', 'pattern': 'patterns'}
    attribute = aliases.get(category, category)
    if identifier.isdigit() and not spec.get('assembled') and (part_folder(attribute, int(identifier)) / 'recipe.json').exists():
        from tools.creature_workshop.geometry import compile_recipe
        return compile_recipe(load(attribute, int(identifier)))
    settings = e.default_settings()
    settings['gender'] = gender
    design = next((d for d in [*e.LIBRARY_DESIGNS, *e.REFERENCE_DESIGNS] if d['id'] == identifier), None)
    anatomy = VARIANTS.get(identifier) if category in {'face', 'hair'} else None
    if spec.get('assembled') and identifier.isdigit():
        settings['reference_parts'][attribute] = int(identifier)
    elif anatomy is not None:
        # The authored anatomy is a head choice on its own existing body donor,
        # not a new full-body donor or a numbered human clothing reference.
        settings.update(race=anatomy['race'], gender=anatomy['gender'], face=identifier, hair='bald',
                        outfit=anatomy['source'], arms=anatomy['source'], legs=anatomy['source'])
    elif design:
        # A human upper body can use either gender with the same carrier donor.
        selected_gender = gender if design['race'] == 'centaur' else design['gender']
        settings.update(race=design['race'], gender=selected_gender, face=identifier,
                        outfit=identifier, arms=identifier, legs=identifier)
        if category == 'back':
            settings['back'] = identifier
    else:
        if category in OPTIONS and identifier in OPTIONS[category]:
            settings['decor'][category] = identifier
        elif category == 'hair' and identifier in e.HAIR:
            if identifier in e.PROCEDURAL_HAIR:
                race = e.PROCEDURAL_HAIR[identifier][0]
                donor = next(d for d in e.LIBRARY_DESIGNS if d['race'] == race)
                settings.update(race=race, gender=donor['gender'], face=donor['id'],
                                outfit=donor['id'], arms=donor['id'], legs=donor['id'])
            settings['hair'] = identifier
        elif category in {'outfit','arms','legs'} and identifier in e.OUTFITS:
            settings['outfit'] = settings['arms'] = settings['legs'] = identifier
        elif category == 'form' and identifier in e.FORMS:
            settings['form'] = identifier
        elif category in e.FEATURES and '--' in identifier:
            race = identifier.split('--', 1)[0]
            donor = next(d for d in e.LIBRARY_DESIGNS if d['race'] == race)
            settings.update(race=race, gender=donor['gender'], face=donor['id'],
                            outfit=donor['id'], arms=donor['id'], legs=donor['id'])
            settings['features'][category] = identifier.split('--', 1)[1]
        elif category == 'back' and identifier in e.BACK_IDS:
            settings['back'] = identifier
        elif category == 'palette':
            from .constructor_palette_previews import options
            option = next((p for p in options() if p['id'] == identifier), None)
            if option:
                settings['colors'].update(option['colors'])
        else:
            # Some cards are named for a full native donor by their directory.
            donor = spec.get('donor')
            design = next((d for d in e.LIBRARY_DESIGNS if d['id'] == donor), None)
            if not design:
                raise ValueError('Unknown generated thumbnail selector: ' + identifier)
            settings.update(race=design['race'], gender=design['gender'], face=donor,
                            outfit=donor, arms=donor, legs=donor)
    with tempfile.TemporaryDirectory(prefix='forge-card-') as temporary:
        root = Path(temporary)
        manifest = e.build(settings, root)
        slots = list(manifest['parts'])
        if category in {'face', 'hair', 'eye', 'eyes', 'nose', 'ears', 'jaw', 'mouth', 'headwear', 'beard', 'beards', 'mustache', 'mustaches', 'brows'}:
            slots = [slot for slot in slots if slot == 'head']
        elif category == 'arms':
            slots = [slot for slot in slots if slot.endswith(('_arm', '_claw', '_leg_1'))
                     or slot.startswith('front_') or settings['race'] == 'spider' and slot.startswith('left_leg')]
        elif category in {'legs', 'boots'}:
            slots = [slot for slot in slots if slot.endswith('_leg') or slot.startswith('hind_')
                     or '_leg_' in slot and not slot.endswith('_leg_1')
                     or settings['race'] == 'spider' and slot.startswith('right_leg')]
        elif category in {'belt', 'shoulders', 'emblem', 'pattern'}:
            slots = [slot for slot in slots if slot == 'torso']
        elif category == 'back':
            slots = [slot for slot in slots if slot in {'back_attachment', 'tail', 'left_wing', 'right_wing'}]
        if not slots:
            raise ValueError('Thumbnail has no selected body geometry')
        pieces = [e._glb_arrays((root / manifest['parts'][slot]['model']).read_bytes()) for slot in slots]
        return tuple(np.concatenate([piece[i] for piece in pieces]) for i in range(3)) + ([],)
