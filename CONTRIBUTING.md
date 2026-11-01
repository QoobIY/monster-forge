# Contributing to Monster Forge

Start with `make setup`, `make run`, and `make check`. The constructor's existing
parts, race definitions and presets are included. Python 3.12+ and Node.js 22+
are required for application development; no game checkout is needed.
The standalone SDK supports Python 3.11+.

Project-owned software, documentation and configuration use Apache-2.0, together
with the built-in constructor resources identified in
[LICENSE_SCOPE.md](LICENSE_SCOPE.md). Unrelated game assets, imported source
and private Git history are excluded.
See [LICENSE](LICENSE), [NOTICE](NOTICE), and [release instructions](docs/releasing.md).

## Choose the right boundary

| Change | Supported entry point |
| --- | --- |
| Read an asset release in another application | `monster_forge_sdk.AssetStore` and `ContentCache` |
| Add reviewed humanoid source parts | `monsterforge.constructor.SourceBundle` and `ConstructorRegistry.with_source()` |
| Compose, validate, preview or save a character | `monsterforge.constructor.ConstructorService` |
| Store or download an immutable local assembly | `monsterforge.assembly_repository.AssemblyRepository` |
| Add a browser workflow | Native modules in `static/characters/`; compose them in `app.js` |
| Change the asset catalog HTTP adapter | `monsterforge/asset_library.py` |
| Read the static bind pose | `monsterforge/runtime.py`; SDK skeleton contracts and exporter matrices |
| Add an appearance preset | JSON preset and index under `config/constructor_presets/v1/` |

`workshop_constructor.py` preserves old imports and authoring-tool overrides.
New integrations should use the constructor package. The historical sculptors
and `tools/imported_mom` are compatibility material, not a second extension API.
Some old authoring scripts pin their own source bytes in immutable recipes;
mass-formatting them can invalidate reproducible output.

## Keep one product and one style

- Preserve the existing races and parts. New creature rigs and universal autorig are outside the vertical slice; new source bundles use `humanoid_v1`.
- Follow `config/style_profile.json`; save prompts, references and hashes with source revisions.
- Use one approved Front template for humanoid parts and a separate one for equipment.
- Keep raw images, composite GLBs, assignments and publication history immutable.
- Use schema versions and explicit migrations. Unsupported data must produce a visible error.
- Keep weights inside the slot's permitted bones. Align legs to one floor without independently stretching them.
- Keep geometry, weights and bind transforms in Python; the browser displays the backend result.
- Keep Tripo manual. New network services require a separate product decision.
- Use the shared CSS tokens and system typography; do not add page-specific style exceptions.

The full production contract is in [AGENTS.md](AGENTS.md). Project-owned source
and immutable asset evidence have different lifetimes; preserve both.

## Validate the change

Run `make check`. It checks the supported Python core, frontend formatting,
native module contracts, and portable tests. Run `npm run format` after editing
frontend files. Prettier is pinned; the application has no npm runtime dependency
or bundler.

For character changes, run `make test`. Start with the smallest affected part
or assembly. Check numerical
invariants such as bind/inverse-bind agreement, normalized weights, permitted
bones, floor alignment and identical saved settings. Images are not a substitute
for these checks; tests do not rate artistic quality.

Add portable tests for core API changes and integration tests for actual source
bundles. Include relevant tests in the Makefile's portable
suite so CI covers the public extension API.

## Keep the pull request reviewable

Explain the concrete problem, resulting behavior, compatibility impact and
validation. Include migrations for data changes. Generated previews, compiled
parts, node_modules, environment files and temporary exports stay out of Git.
Review products belong under `/tmp/monster-forge`.

Keep asset origin, applicable terms and evidence in `config/release_rights.json`.
Excluded asset scopes can remain pending without blocking a tools-only release.
Adding imported or historical material to a future asset release requires its
own recorded decision; do not change `pending` to `approved` without evidence.
Do not commit credentials or use live paid services in tests.
