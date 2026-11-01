# Product boundaries and next work

Monster Forge is a standalone modular character constructor. Preserve its
existing races, parts and appearance settings while making the same workflow
easier to install and extend. New production extensions target `humanoid_v1`;
games and animation runtimes are optional consumers of the resulting assets.

| Workflow | Current boundary |
| --- | --- |
| Asset SDK and bind contracts | Portable SDK, pinned file reads, consumer cache, packaged BHM contracts. |
| Browser library | Real catalog, geometry/image display, search, download and background controls. Own mathematical demo works independently. |
| Character authoring | Existing race/part catalog, source verification, established settings and composition policies through one registry/service API. |
| Body Parts / Assembly | Faces, hair, physique, clothing, limbs, accessories and palettes with shared preview, immutable saves and one-model exports. |
| Image generation | Approved Front master/template and saved text style are the production contract. An end-to-end OpenAI generation workflow is not implemented. |
| Equipment | Asset data/tools exist. The complete manual composite Tripo import, component assignment and socket-editing browser workflow remains to be completed. |
| Playground | The browser does not currently provide the complete shared-solver animation and input workflow. |
| Public release | Apache-2.0 constructor source with built-in recipes, races, presets and required references. Exact resource inventory; unrelated game assets, imported applications and private history excluded. |

## Complete the humanoid workflow

Keep the rich constructor usable independently of a game checkout. Validate
startup against the actual source catalog, previews, saved settings and exports.
Check availability of the complete source pack separately from the smaller
mathematical asset-library example.

Keep one approved positioning master and explicit immutable source revisions.
Provide a documented reference bundle that can be redistributed and exercises
the public registry API. Preserve model snapshot, prompts, combined mask,
references, source hashes and raw generation response. Do not grow edit chains
from arbitrary previous results or add unsaved style exceptions.

## Complete equipment authoring

Preserve manual Tripo use, disconnected-component assignments and per-set scale.
Add the browser workflow on the existing data contracts. Retain grip/projectile
sockets and make live socket corrections new immutable revisions. Equipment
style inherits the selected character image; do not add a second independent
style system or normalize each weapon separately.

## Complete Playground

Use the real bind pose and an explicit Python animation integration for idle,
run, directed dash, attack and cast. The browser should interpolate computed poses and implement the
documented input mapping. Validate numerical agreement with the game runtime,
floor contact and supported weapon profiles. Keep gameplay balance and rewards
in the consuming game. This runtime integration is separate from static
character composition. Do not create an Animations tab or a JavaScript solver.

## Keep maintenance focused

New extensions use the supported interfaces in [CONTRIBUTING.md](../CONTRIBUTING.md).
Historical sculptors, standalone generators and imported source stay compatibility
material. Preserve their evidence; do not silently turn them into supported
production features or delete them as cleanup. The historical standalone
generator and imported source are excluded from the tools-only distribution.
Any future asset redistribution review is separate from this release scope;
it is not a prerequisite for shipping the tools.
