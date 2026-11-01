# Apache-2.0 distribution scope

The root [LICENSE](LICENSE) applies to Monster Forge's own source code,
documentation, tool configuration and built-in constructor resources.
Contributors retain copyright in their contributions; see [NOTICE](NOTICE).

## Included constructor resources

`config/constructor_resources_v1.json` is the exact inventory of included
constructor data, with SHA-256 hashes and sizes. It preserves the existing race
and part definitions, appearance presets, immutable geometry recipes, source
records and required project-generated Front references. These are inputs to
the shipped constructor, rather than an external game's asset collection.

Three project-owned bind contracts remain the single source for the SDK:

- `media/rigs/body_rigs.json`
- `media/rigs/humanoid/canonical.json`
- `media/rigs/humanoid/workshop_knees_v1.json`

The SDK wheel includes its code and these contracts. The full browser constructor
runs from the source checkout. Documentation screenshots are limited to
`docs/images/constructor.png` and `docs/images/sdk-guide.png`.

## Excluded material

This grant does not extend to unrelated game assets, third-party imports,
archived applications or material absent from the declared source inventory.
The release excludes `styles/`, `artifacts/`, `assets/`, `tools/imported_mom/`,
`tools/assetforge_generator/`, private state, credentials, caches and historical
Git objects. Local source evidence outside the public inventory remains intact.

Compiled GLBs, weights, thumbnails and review products rebuild in `/tmp` and
are not bundled as source. User-created saved assemblies remain local.
The tools do not automatically license users' imported assets or their output.
Third-party dependencies retain their own terms and are not vendored.

## Release preparation

`tools.check_release` and `tools.prepare_release` share one selector. Policy v3
admits the exact constructor resource inventory; neighboring media and future
configuration files remain excluded until explicitly added. Resource bytes must
match their declared hashes. Earlier policy versions retain their narrower
scope through explicit read-only migration.

The exported `release-manifest.json` lists every included file and its hash.
Release checks prepare a reviewable local snapshot; they do not grant rights,
publish packages, push Git refs or inspect private historical objects.
