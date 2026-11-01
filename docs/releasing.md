# Preparing the public constructor

The Apache-2.0 source includes the existing constructor, its parts, race
settings, presets and required original inputs. It runs independently of games.
[LICENSE_SCOPE.md](../LICENSE_SCOPE.md) defines the exact boundary alongside
[LICENSE](../LICENSE) and [NOTICE](../NOTICE).

## Source inventory

`config/constructor_resources_v1.json` pins every built-in recipe, metadata file
and required Front reference by path, size and SHA-256. Source bytes and their
history are immutable: add a new revision instead of rewriting a published part.
Keep the resource inventory in sync when deliberately adding a new source.

Derived GLBs, skin weights and selector cards rebuild in `/tmp/monster-forge`.
They stay outside Git. The three SDK bind-contract JSON files are included from
their single source under `media/rigs/`.

Unrelated game assets, imported applications, local assemblies, credentials,
review products and private Git history are excluded. Their local copies and
provenance are retained. The release selector does not admit an entire media
folder merely because one constructor resource lives there.

## Check and export

```sh
make check
.venv/bin/python -m tools.check_release --scope repository
.venv/bin/python -m tools.prepare_release --output /tmp/monster-forge-review
```

Use a new or empty destination. Every included file receives a size and hash in
`release-manifest.json`; `release-report.json` records admission checks.
The exporter preserves source files and does not publish or rewrite Git history.

`--scope code` selects the source distribution, including the explicitly
inventoried constructor resources. `--scope repository` additionally catches
accidentally tracked files outside that scope. Older policy versions do not
automatically acquire permission to include the new resources.

## Verify the exported source

```sh
python3.12 -m venv /tmp/monster-forge-review-venv
/tmp/monster-forge-review-venv/bin/python -m pip install -e '/tmp/monster-forge-review[app,dev]'
npm --prefix /tmp/monster-forge-review ci --ignore-scripts
make -C /tmp/monster-forge-review check PYTHON=/tmp/monster-forge-review-venv/bin/python
make -C /tmp/monster-forge-review run PYTHON=/tmp/monster-forge-review-venv/bin/python
```

Verify the existing race catalog, part selection, live preview, save and GLB/ZIP
export. This copy must work without a neighboring game checkout or access to
local historical asset folders. Numerical tests check geometry, bind matrices,
weights, floor alignment and source hashes; screenshots document the UI.

Before replacing a remote branch's history, retain a verified bundle of the
old refs and use an explicit force-with-lease tied to the reviewed remote SHA.
A local one-commit branch does not imply that a remote push succeeded.
