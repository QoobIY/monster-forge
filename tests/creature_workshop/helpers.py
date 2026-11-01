from monsterforge import workshop_constructor as editor


def clean_settings(race, donor):
    settings = editor.default_settings()
    settings.update(race=race, face=donor, outfit=donor, arms=donor, legs=donor)
    return settings
