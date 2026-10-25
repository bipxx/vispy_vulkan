# Uniform array update ordering

Date: 2026-10-25. The renderer now applies overlapping uniform assignments in
command order. An indexed update followed by a whole-array upload uses the later
whole-array values. A subsequent indexed update overrides its element again.
Previously, the draw packer always reapplied the stored indexed value, even when
that value was older than the whole-array upload.

The retained old development module fails four independent pixel cases covering
float, int, bool and mat2 arrays. The regression now checks both an intervening
draw and assignments queued before the first draw. Expected output is authored
from the assigned values, not from the renderer's packed buffer.

`cpp/runtime_uniform_updates.hpp` replaces the parent and retires its older
indexed descendants in both typed value stores. Unrelated names and sibling
elements remain intact. Replacement storage is acquired before retiring prior
values. Ordered maps provide prefix lookup/removal without scanning every
uniform for each scalar assignment. The CPU contract covers parent replacement,
later elements, typed replacement, sibling/prefix distinctions and nested parent
retirement. That last bookkeeping control does not implement multidimensional
shader declarations, reflection or uploads; SH-2 remains open.

Verification uses committed product source
`794f03f3827b8c5a30e8e44cf20f34dda6ab636f`:

- Windows and WSL each pass all 82 rendering checks: eight ordering cases,
  sixteen existing uniform/packing cases and 58 scissor/Tk capture cases.
- Both selected source environments pass all eight required Tk state/resource/
  failure composite branches. Every final graphics child reports nine zero
  live-resource gauges.
- Windows uniform/state/shader/artifact CPU contracts and the Linux uniform
  contract pass. The shader contract includes normalization, reflection,
  SPIR-V validation and packing.
- All 337 affected native/epoch/index/inventory source checks pass. The original
  required obligations and selected criterion/dependency closure remain intact.

The existing installed-wheel immediate-state CI smoke now includes eight array
oracles and verifies the program/GLIR source members as well as its prior four
members. Its pixel helper passes against both fresh source modules. A targeted
control verifies six actual members of the older installed wheel and catches
the old array pixel error. The initial attempt to use the entire current smoke
on that legacy wheel stops earlier because it predates immediate `glViewport`
support; that separate result is retained and is not evidence of the array oracle.
The complete updated installed entry point still needs its fresh-head CI wheel.

Only first-party native leaves were rebuilt. Windows reused the verified
immutable SDK, and Linux reused its existing vendor archives under its explicit
experimental source-only status. No vendor build, environment installation or
source-history clone occurred. Original licenses and source/exit/wait evidence
are retained under `build/runs/uniform-write-order-52/` and
`build/runs/uniform-order-native-53/`.

Preparation now references fresh source observations for both native leaves and
the tested Mesa 26.1.8 Linux configuration. Previous profile files and failures
remain preserved. These observations are not independent approvals, installed
candidate receipts, native producer admission or full API completion. Both
candidate wheels and promotion proofs remain absent.

Cleanup removed 20,630 owned scratch files / 333,322,636 bytes from the native
packet. All 297 retained source/evidence/artifact/license records were rehashed
and scratch is absent. The earlier failing regression packet is also retained
and cleaned. Current/previous native leaves remain immutable; vendor origins
were neither moved nor rewritten.


## Multidimensional uniform implementation: source verification

Product source `0a0e8ec55e7e59b1f63a8142f9add6fed72a00e1` now preserves ordered
uniform dimensions through Python declaration/upload handling, native normalization,
std140 layout, SPIR-V reflection and generated line-consumer UBO declarations.
The packer reuses a flattened leaf count and innermost stride; dimension metadata
remains separate so `[2][3]` cannot match `[3][2]`. Layout arithmetic is checked
before allocating the member, and nested boolean conversion follows every array
index. Indexed names resolve to checked contiguous subviews; sparse ordered
traversal visits actual writes and applies parents before descendants across both
typed stores. Parent replacement retains the existing command-order semantics.

Whole arrays, indexed subarrays and individual leaves produce typed, contiguous
GLIR payloads. Arrays of vectors/matrices use a final packed-component axis;
multidimensional scalars accept their natural dimension shape or a final singleton
component axis. The original one-dimensional shape contract remains unchanged.
All six rectangular matrix types are now present in the public upload type table.
A rejected upload queues no command, and conflicting stage declarations fail.

Verification in `build/runs/multidimensional-native-55/`:

- Windows and WSL each pass 154 checks: 48 new multidimensional pixel cases,
  24 Python shape cases, and 82 existing uniform/scissor/resize regressions.
  Pixel cases cover float/int/bool/vec3/bvec3, square and every rectangular matrix,
  triangle and generated wide-line consumers, whole/subarray/leaf replacement,
  with and without intervening draws. Expected values use a separate 1D scalar
  reference. Both children finish with all nine shutdown gauges at zero.
- Windows and Linux compiler/layout contracts pass nested-array shape/stride
  reflection, checked subviews, overflow/invalid-index controls, three-dimensional
  arrays and nested boolean indices. Windows additionally runs Dawn's pinned Tint
  reader. Existing shader corpus, state, artifact and ordering contracts pass on
  Windows; Linux runs the shader corpus/compiler contract.
- The full eight-branch source Tk composite passes on both fresh native modules,
  with zero-resource shutdown. A separate final device-free check passes 31 tests
  and excludes two existing application/draw cases.

The first Windows rendering attempt retained two failures from the missing
`mat2x3` Python type entry; adding the type table fixed them without rebuilding
native code. A Linux extension-launch attempt failed before spawning a child
because a local string replacement altered an original receipt filename. The
failed launcher and correction are retained separately from renderer results.

Both native leaves and original licenses are retained by hash. Windows reused its
verified SDK; Linux reused six existing vendor archives under its experimental
producer status, plus the isolated Mesa 26.1.8 configuration. No vendor rebuild,
new environment or source-history clone occurred. The product commit is frozen;
preparation declarations now reference fresh source observations while preserving
the previous profiles. Exact installed CI and independent review remain pending.
Older profiles, observations and failures are preserved.

This source packet does not complete SH-2 or qualify an installed artifact.
Sampler arrays, storage/stage-interface arrays, broader shader/API scope,
independent cumulative reviews, producer admission and exact installed candidate
proof remain open. Two-dimensional arrays have pixel proof here; three-dimensional
arrays additionally have compiler/layout/subview proof, without a 3D pixel claim.


Managed cleanup removed 325 owned scratch files / 139,970,508 bytes. All 166
retained source/evidence/artifact/license records were rehashed after cleanup;
this run's scratch is absent and the shared `build/work` directory is empty.
The protected/blocked registry and identity-pinned dependency origins are unchanged.


The installed-wheel state smoke now includes all 48 nested-array/line pixel cases
and its previous eight array-order cases. The exact helper passes all 56 cases
against each retained native module with zero-resource shutdown. This is source
helper verification; the full installed entry point still requires a fresh CI
wheel. CPU CI also runs the 24 public array-shape contracts. All 475 affected
native/epoch/index/CI/artifact/inventory/preparation/shape source checks pass after
renewing exact declarations. Requested selection, dependency closure, execution
ledger and all 142 original required parents are unchanged; admission stays false.
Evidence is retained in `build/runs/multidimensional-qualification-56/`.


Publication preserves the original LF serialization of preparation JSON. After
correcting Windows newline translation, 308 affected qualification-index,
inventory and CI reference controls pass on the final bytes. This follows the
475-check source run and requires no native rebuild or repeated rendering.
The helper/declaration check run reclaimed 119,409,907 bytes and verified all
43 retained records; its scratch is absent.


## Composed arrays and shader-rebuild replay: source follow-up

Local product source `c188878efa752b3ba36897860a4070dcf4a98fd1` extends explicit typed `Variable` declarations
such as `uniform vec3 grid[2][3]`. Declaration dimensions are separate from the
compiler-assigned base name, remain intact through collisions/renaming, and are
exposed as the immutable `array_shape` tuple. Values use the same component-axis
contract as Program; rejected assignments preserve both the old value and cache
identity. `ModularProgram` uploads changes without unnecessary source rebuilds.

A rename/recompile regression exposed a second existing bug: Program cached
flattened array data, then replayed it as a new shaped upload after replacing
shaders. It also retained first-insertion order, which could revive an indexed
write superseded by a later whole-array write. Replay now restores the original
shape and uses last-write cache order. Public cached getter values remain packed.

Both Windows and WSL pass 129 focused checks: 36 Variable contracts, 27 Program
shape/replay contracts, ten existing shader-function contracts, 48 composed-array
pixel cases, and eight existing uniform-order cases extended through recompile.
Pixels cover one, two and three dimensions; scalar/int/bool/vector/boolean-vector
and matrix values; shared vertex/fragment uniforms; colliding names; live value
updates; rename-triggered recompilation; triangles and generated wide lines.
Both platforms also pass the complete 104-case smoke helper in one canvas, with
all nine shutdown gauges at zero. The installed entry point additionally verifies
its three actual loaded shader-composition modules against wheel members.

The first declaration/value failure and all 48 rename/recompile failures are
retained with their source and reproducer. The new pixel oracle is shared by
pytest and the installed smoke to prevent separate copies from drifting. Native
source/header hashes and binaries are unchanged: the retained modules from the
previous packet were reused without SDK work or new environments.

Evidence: `build/runs/variable-array-composition-58/`. This is local source proof;
preparation references now bind fresh source observations for this Python change;
final-head installed CI and independent approvals remain pending. Native producer status, independent review requirements, original
parents and other SH-2 storage/interface obligations are unchanged.


Managed cleanup reclaimed 17,241,753 bytes from this Python-only packet. All
105 retained source/evidence/artifact/license records were rehashed, scratch is
absent and shared managed work is empty. No native build or environment install
was needed. The published head's CI continues separately; this local product
commit awaits one coherent preparation/publication update rather than cancelling
that active run for each small source checkpoint.


## Qualification follow-up for the composed-array source

Fresh complete eight-branch source Tk composites pass on Windows and WSL after
the Python replay change, with all nine shutdown gauges at zero. Both changed
Python modules are hash-bound in these observations. New composed-array profile
files retain the previous multidimensional profiles and explicitly reuse the
same native leaves; native production inputs are byte-identical. Preparation
keeps the requested selection, dependency closure, execution ledger, both
profiles and all 142 original required parents intact. No producer admission or
independent approval is created by this renewal.

The earlier published head `a1a0f789bee6aff926ff79b12c9119459318a913` now has an
actual successful Linux CI installed-wheel receipt: eight uniform-order plus 48
multidimensional cases, six exact wheel-member checks and zero shutdown gauges.
The original PR merge-checkout identity and all five checked Python members were
verified against that source head. Its wheel is retained once by hash, together
with original small receipts; expanded native-origin copies were not extracted.
This belongs to the Linux CI profile and the earlier product, not the WSL Tk
profile or the newer 104-case composed-array helper. The latter still needs its
own full installed entry point on the new declared head. Metal's CI pass is build
proof only. Neither result changes the real subject's missing admission evidence.

Follow-up source and receipt evidence: `build/runs/variable-array-qualification-59/`.


All 514 affected native/epoch/index/inventory/CI/artifact/preparation and public
array contracts pass on the renewed source declarations. The real subject still
has 120 requested/closure/missing criteria, zero proved criteria and admission
false. The immutable original compatibility ledger hash is unchanged. These
checks validate the preparation and rejection gates; they do not approve source,
producer reuse, installed candidate workflows or release promotion.
