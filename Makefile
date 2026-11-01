PYTHON ?= .venv/bin/python
PORT ?= 5050

CORE_SOURCES = monster_forge_sdk monsterforge/constructor app.py \
	monsterforge/__init__.py monsterforge/__main__.py monsterforge/web.py \
	monsterforge/runtime.py monsterforge/demo.py monsterforge/asset_library.py \
	monsterforge/creature_workshop.py monsterforge/character_assembly.py \
	monsterforge/asset_geometry.py monsterforge/assembly_repository.py \
	monsterforge/serialization.py monsterforge/paths.py monsterforge/constructor_cache.py \
	monsterforge/resources.py monsterforge/static_assembly.py \
	monsterforge/constructor_thumbnails.py monsterforge/constructor_published.py \
	tools/check_release.py tools/prepare_release.py

PORTABLE_TESTS = tests.test_sdk_characters tests.test_asset_cache \
	tests.test_assembly_repository tests.test_constructor_index \
	tests.test_application_modes tests.test_browser_workflows \
	tests.test_release_audit tests.test_prepare_release tests.test_distribution_license tests.test_constructor_core \
	tests.test_constructor_core_integration tests.test_standalone_constructor tests.test_static_assembly \
	tests.test_static_bind tests.creature_workshop.test_constructor_thumbnails \
	tests.creature_workshop.test_constructor_hair_fit

.PHONY: setup run demo test test-archive test-portable test-sdk test-wheel test-dist test-js test-frontend format-check lint check build release-audit release-audit-repository release-draft release-tools

setup:
	uv sync --locked --extra app --extra dev
	npm ci --ignore-scripts

APP_PYTHON = $(PYTHON)
ifeq ($(PYTHON),.venv/bin/python)
APP_PYTHON = uv run --locked --extra app python
endif

run:
	$(APP_PYTHON) -m monsterforge --port $(PORT)

demo:
	$(APP_PYTHON) -m monsterforge --demo --port $(PORT)

test: test-portable

# Optional compatibility checks against the preserved local game/asset archive.
test-archive:
	$(PYTHON) -m unittest discover -s tests -t .

test-portable:
	$(PYTHON) -m unittest $(PORTABLE_TESTS)

# These readers and their tests must work without Flask, NumPy or MoM.
test-sdk:
	$(PYTHON) -S -m unittest tests.test_sdk_characters tests.test_asset_cache

test-wheel:
	@test -n "$(WHEEL)" || (printf '%s\n' 'Set WHEEL to the built SDK wheel path.'; exit 2)
	MONSTER_FORGE_TEST_WHEEL="$(WHEEL)" $(PYTHON) -S -m unittest tests.test_sdk_characters

test-dist:
	@test -n "$(WHEEL)" -a -n "$(SDIST)" || (printf '%s\n' 'Set WHEEL and SDIST to the built SDK archive paths.'; exit 2)
	MONSTER_FORGE_TEST_WHEEL="$(WHEEL)" MONSTER_FORGE_TEST_SDIST="$(SDIST)" $(PYTHON) -S -m unittest tests.test_sdk_characters tests.test_distribution_license

test-js:
	@for source in static/*.js static/characters/*.js; do node --check "$$source" || exit $$?; done

test-frontend:
	npm run test:frontend

format-check:
	npm run check:format

# Frozen authoring scripts can pin their own bytes in immutable recipes.
# Supported extension code lives in CORE_SOURCES; do not mass-format provenance.
lint:
	$(PYTHON) -m ruff check $(CORE_SOURCES)

check: lint format-check test-js test-frontend test-portable

build:
	$(PYTHON) -m build

release-audit:
	$(PYTHON) -m tools.check_release --scope code

release-audit-repository:
	$(PYTHON) -m tools.check_release --scope repository

release-draft:
	$(PYTHON) -m tools.prepare_release --draft --output /tmp/monster-forge-source-draft

release-tools:
	$(PYTHON) -m tools.prepare_release --output /tmp/monster-forge-tools-source
