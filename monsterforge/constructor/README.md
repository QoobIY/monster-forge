# Constructor core

The supported application API is `ConstructorService`. HTTP routes and authoring
commands call it; geometry code does not import Flask or saved revision storage.

| Module | Owns |
| --- | --- |
| `registry` | Source identities, contracts and admitted extension bundles |
| `settings` | Complete settings schema, validation and explicit migrations |
| `sources` | Pinned source reads, provenance and GLB/recipe equivalence |
| `catalog` | User-facing projection of the inventory |
| `geometry` | Slot recipe transformations |
| `builder` | Disposable part compilation and numerical invariants |
| `service` | Preview/export orchestration and `AssemblyRepository` integration |
| `_inventory` | Bundled data and historical authoring definitions |

`service.catalog()` preserves every existing active race, part and setting. The
same inventory drives editing, previews and saved selections. New source-bundle
extensions remain limited to `humanoid_v1`; `catalog(include_legacy=False)` is an
explicit view of that extension boundary, not the default editor.

The constructor uses BHM's own SDK skeletons and its existing GLB exporter's
static bind matrices. Preview, weights, saves and export do not need a game
runtime or implement an animation solver. `default_registry()` loads the shipped
immutable source pack on demand. Recipes, original reference hashes and cache
integrity checks remain unchanged; disposable GLBs are rebuilt under `/tmp`.

## Add an approved humanoid source

An extension supplies an immutable source bundle in `media/constructor/`, using
an existing supported race and the existing Front template and style contract.
Do not add a new skeleton contract or a custom prompt/style exception here.
The directory contains `parts.json`, `record.json`, source images and the pinned
models/recipes for all six required slots, with optional `back_attachment`.
Derived models may use the existing recipe cache. Keep approval evidence,
prompts, references and hashes in the source record; publish changed sources at
a new directory/id rather than overwriting old files.

```python
from pathlib import Path
from monsterforge.constructor import ConstructorService, SourceBundle

service = ConstructorService()
extended = service.with_source(
    SourceBundle(
        id="community-human-v1",
        label="Community human",
        race="human",
        gender="male",
        directory=Path("media/constructor/community/human/v1"),
        manifest_sha256="<approved SHA-256 of parts.json>",
    )
)
settings = extended.default_settings()
settings.update(
    face="community-human-v1",
    outfit="community-human-v1",
    arms="community-human-v1",
    legs="community-human-v1",
)
extended.build(settings, Path("/tmp/monster-forge/community-build"))
```

`with_source` returns a separate registry. It validates identity collisions,
contract, schema, required slots, containment and the approved manifest hash.
Registration snapshots recipe, provenance-record and reference-image hashes;
later reads reject changed evidence even when geometry is unchanged.
`sources.load_part` checks model hashes and exact recipe/model equivalence before
the builder uses a slot. Validation, catalog and build all use the same registry.
The original service and published asset bytes are unchanged by registration.

Pass the extended service to the app to use it in the browser:

```python
from monsterforge import create_app

app = create_app({"CONSTRUCTOR_SERVICE": extended})
```

An embedding application can also set `app.extensions["constructor_service"]`.
Catalog, preview, exports and saved revision downloads use that same service.
Existing card URLs automatically render registered source slots. Cards live only
under `/tmp/monster-forge`; a warm card cache never bypasses source hash checks.

`monsterforge.workshop_constructor` remains a compatibility adapter for existing
commands. New code should use the service or the individual core modules. Some
historical author modules still call that adapter: their self-file hashes are
immutable provenance and changing their imports requires a new source revision.
