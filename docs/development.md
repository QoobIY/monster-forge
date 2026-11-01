# Development

## Independent source checkout

Python 3.12+, uv, and Node.js 22+ are the application development prerequisites.
The SDK alone needs Python 3.11+ and no third-party runtime dependency.

```sh
make setup
make run
```

`make setup` installs the locked Python application/development dependencies
and the pinned frontend formatter. The character constructor keeps the existing
race/part catalog and versioned appearance settings. Its source pack supplies
the immutable recipes, attribute metadata and preset data used by those controls.
Source-pack availability is reported explicitly; a game checkout is not part
of the constructor's installation contract.

The application is served at `http://127.0.0.1:5050/`. Override the interpreter
or port with `make run PYTHON=python3.12 PORT=5051`. `python -m monsterforge
--help` lists the source application options. `app.py` remains a WSGI entrypoint
and a compatible command-line wrapper.

The Apache-2.0 source distribution includes the constructor's race definitions,
presets, immutable geometry recipes and required original Front references.
The exact source inventory is `config/constructor_resources_v1.json`. Compiled
parts and thumbnails rebuild in `/tmp/monster-forge`; they are not stored in Git.
Unrelated game assets and imported applications remain outside this release.
See [release instructions](releasing.md) and [LICENSE_SCOPE.md](../LICENSE_SCOPE.md).

The package wheel installs only the SDK. The `app` and `authoring` extras install
dependencies for tools run from the source checkout. `authoring` also includes
CairoSVG, which requires the system Cairo library. It does not install the game.

## Asset releases and app configuration

A release directory contains `media/catalog.json` and all files it references.
The SDK verifies their declared hashes and sizes. Mount a release explicitly:

```sh
.venv/bin/python -m monsterforge --asset-root /path/to/release --mode library
```

| Setting | Meaning |
| --- | --- |
| `MONSTER_FORGE_ASSET_ROOT` | SDK/application release root |
| `MONSTER_FORGE_MODE=auto` | Select the available constructor or asset-library workflow |
| `MONSTER_FORGE_MODE=library` | Run the asset browser without loading constructor sources |
| `MONSTER_FORGE_MODE=authoring` | Require the constructor source pack; report unavailable sources early |
| `MONSTER_FORGE_CACHE_ROOT` | Optional verified SDK consumer cache |
| `FLASK_HOST`, `FLASK_PORT`, `FLASK_DEBUG` | Local server settings |

`create_app(config)` also accepts `ASSET_ROOT`, `MODE`, and normal Flask settings.
App instances keep separate catalogs and geometry cache identities. The public
`/api/capabilities` response reports which workflows are available. Missing
constructor sources yield a clear setup page and JSON 503 responses.
The application does not load `.env` files; `.env.example` documents optional
shell values without credentials.

## Built-in constructor sources

Preserve the included races, native parts, numbered attributes, palettes and
presets. Character composition, static bind data, weights and
`assembly.json`/GLB export belong to the constructor. These operations use
Monster Forge's own skeleton contracts and existing exporter matrices.
No game process, sibling checkout or animation package is required.

The browser displays geometry calculated by Python. Future animation previews
must use an explicit backend interface without duplicating a solver in JavaScript.

## Checks

```sh
make check                 # supported core + frontend + portable tests
make test-sdk              # SDK tests with site-packages disabled
make test                  # constructor and SDK tests using the included source pack
make test-archive          # optional compatibility tests; requires the historical asset release
npm run test:frontend      # native ES-module contracts using Node's built-in runner
npm run check:format       # pinned Prettier, read-only
npm run format             # format frontend source/templates
make build                 # SDK sdist and wheel
make test-wheel WHEEL=/path/to/monster_forge_sdk.whl
```

CI runs the dependency-free SDK on Python 3.11/3.12 and the portable application
on Python 3.12 with Node.js 22. The standalone constructor checks exercise the shipped source pack without
loading a game module. Run the complete source-pack suite for changes to
character output.

The Makefile explicitly identifies the supported Python core. Frozen historical
authoring modules are excluded from formatting because their source hashes can
be part of preserved recipes. Extend the supported modules through the new API
instead of adding another special-case sculptor.

## Register reviewed source parts

Use `ConstructorRegistry.with_source(SourceBundle(...))` to derive a registry;
the original registry and source files stay unchanged. Pin the reviewed manifest
SHA-256, use a new donor ID for a new revision, and retain source evidence. Only
the supported humanoid contract is admitted. See the portable registry tests for
a minimal manifest and the integration tests for an actual build.

`ConstructorService.with_source()` extends the installed authoring source pack.
Pass that service as `create_app({'CONSTRUCTOR_SERVICE': service, ...})` to use
the same registry for browser catalogs, validation, preview, save and download.
Custom source cards derive from the approved slot geometry in the temporary
cache. A bare registry supports independent registration and source admission;
the extended browser constructor still uses its existing attribute/preset
source pack. Its complete UI is separate from the smaller mathematical
asset-library example.

## Data changes

Preset settings, source recipes, catalog records and assembly instructions have
different schema versions. A new preset does not rewrite an existing publication.
New geometry becomes a new part revision; assembly settings never own a hidden
placement correction. New export contains `assembly.json` schema 2 and one
`model.glb`. Humanoids retain their skeleton and skin weights. Existing authoring
templates without a rig save static geometry with explicit skinning metadata;
this does not introduce a new rig. Legacy downloads remain readable through
the repository.

Never delete source evidence to make a rebuild pass. Verify a minimal failing
combination before running a complete library build. Compiler output and review
products belong in `/tmp`; generated files must be reconstructible.
