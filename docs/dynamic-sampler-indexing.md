# Dynamic sampler indexing implementation

SHD-01 remains open. The earlier v2 candidate wheels retain their literal-only sampler
indexing contract. The source work described here is a successor experiment,
not support attributed to those existing wheel identities.

The first path selects one leaf of a one-dimensional sampler array for a
direct explicit `textureLod` or `texelFetch` call. It retains the existing
texture/sampler resource pair per leaf. Generated overloaded int/uint helpers
take the index, coordinate and LOD as parameters and switch over static leaves.
This avoids descriptor-array indexing and evaluates each argument once. Runtime
indices outside the declared extent return zero; constant invalid indices retain
the existing compile diagnostics. Float indices must fail type checking rather
than being silently converted.

Explicit sampling permits divergent indices without introducing implicit
derivatives. Implicit sampling, sampler arguments passed through user helpers,
multidimensional dynamic selection, projected/shadow sampling, extra overloads
and arbitrary preprocessor forms retain their existing guards. These boundaries
must not be inferred away from an explicit-LOD success. No new performance claim
accompanies switch expansion.

The C++ normalization contract compiles/reflects float 1D/2D/3D/cube and signed/
unsigned 2D selections, uniform/divergent/uint index expressions, fetch variants,
runtime default branches and a float-index negative control. Generated lines
must map to zero while user diagnostics retain their original lines. The static
resource graph, reflection and actual device binding limits remain authoritative.

The rendered regression in
`tests/shaders/test_dynamic_explicit_sampler_arrays.py` distinguishes float,
signed and unsigned words with independent pixel landmarks. It exercises both
explicit operations, uniform/divergent indices, negative/high runtime indices,
one index-function invocation per fragment, texture rebinding and forced device
loss. Windows experiment `dynamic-sampler-rendered-401` passes all 12 new cases
and 32 existing literal/diagnostic cases, without skips, using native module
`5d1a1462dabf876b4b5af1deaf01cbf5e842dfcdbee330594bbfbbe8f1f6251b`.
Its base wheel plus four explicit native replacements form an unqualified local
test installation; this does not qualify the original wheel. All 537 resulting
members and 56 loaded VisPy origins are checked; ten shutdown gauges are zero.

Native experiment `dynamic-sampler-native-399` built successfully. Its original
typed-sampling contract expected dynamic fetch to be refused. The successor
assertion checks both reflected live leaves for explicit fetch and retains
the implicit-sampling refusal. The complete successor run
`dynamic-sampler-native-402` passes all 44 native contracts with unchanged SDK
and toolchain origins and matching source-before/source-after identities.
Its production identity is
`9dff8569f9e4c75e00527e383bdd546c25ea75201affe544e1e970a83bfe671d`.
This is local native proof, not artifact/profile admission.
The failed original contract and the initial float-format fixture failure are
retained with their exact sources and logs. The float fixture now explicitly
requests `r32f`, matching its exact-value expectations.

The corrected native module
`8b93326abbc14d28fe6743bc3571d5dbb83edb5e75c8c91535294ab5da0398e2`
passes 47 Windows native-overlay cases in `dynamic-sampler-rendered-403`:
12 dynamic explicit selection/rebinding/loss cases, three rendered declaration/
macro/nested-call controls and the 32 existing literal/diagnostic regressions.
All ten tracked shutdown gauges are zero. Generated names avoid identifiers in
user declarations and directives; the portable shader identity includes the
`explicit-static-switch-zero-oob-v1` marker. No native build or output result is
transferred to the old v2 wheels.

Further Windows observations reuse that same native module, with no native
build: `dynamic-sampler-breadth-406` passes 67 cases; the two newly added binding
boundary cases pass in `dynamic-sampler-limits-407`; six additional single-level
LOD/filtering cases pass in `dynamic-sampler-lod-408`. Their union is 75 distinct
cases across those three executions, with separate exact test-source hashes.
All three processes retire ten shutdown gauges to zero and their scratch
targets are removed. The [WIP packet](../compat/api-acceptance/dynamic-explicit-samplers-wip.json)
preserves the earlier 47-case observation and adds these successor observations.

Twenty cases cover float 1D/3D/cube sampling in vertex and fragment stages with
int/uint indices and runtime negative/high bounds. The two limit cases use the
actual granted sampler/texture minimum: one extra live leaf refuses, then a
valid at-limit shader compiles and renders. Six gradient cases distinguish
nearest from linear interpolation at explicit LOD -2/0/2 on single-level
textures, with one invocation of each index, coordinate and LOD argument.
Linear byte expectations allow one unit of quantization; nearest expectations
are exact. These cases do not prove multilevel mip chains or arbitrary filters.

Linux CI run `42381467559` builds native source `f7d21c31`; these subsequent
changes add tests/documentation only. Do not restart its native build for them.
Linux outputs, multidimensional dynamic selection, broader preprocessor and
filter/LOD forms, implicit derivative decisions, cumulative independent review
and successor artifact/profile admission remain open.

## Windows successor wheel observation

`windows-dynamic-package-410` assembles a normal wheel from those same verified
native outputs using the existing locked backend; it invokes no native build.
Wheel SHA-256 is
`ba8a54c5b7ede9387d62ff72b1269602d61c0bdc61c77928ee52a7e37107bf24`,
with source commit `af6a91ee` and native production identity `9dff8569`.
Explicit source-version staging and exact source/native/license/RECORD joins pass.

One offline copied installation passes all 75 sampler cases in one process and
63 upload/shutdown, Tk state/capture and maintained-example cases in their
separate processes. All 537 installed members match in each child. Sampler
checks verify 56 loaded module origins; examples verify 172 Python origins.
The eight-branch Tk and four-branch capture validators pass; all five active
capture negative controls reject. Tracked shutdown gauges are zero.

The installation and assembly scratch are removed (42,541,359 bytes), with all
67 retained entries rehashed. The dedicated successor storage profile keeps
the existing 512 MiB allocation, 20 GiB aggregate cap and 10 GiB reserve. This
provides local functional evidence on an actual wheel, with no native overlay;
independent review, strict profile admission and release remain pending. The
earlier wheels and native-overlay observations retain their original scope.

## Linux successor wheel observation

Linux CI `42381467559` completed successfully for native source `f7d21c31`.
Imported original source/native/archive joins pass, all 44 native contracts
pass, and both remote cleanup receipts pass. Raw wheel `7b43577f` exactly
matches the current shipping sources and notices. Native production identity
is `7e4a732d`; `_dawn` SHA-256 is
`6c4e3beaaaf922160d9392fb12213b60911585eeca09b18ec07d4ac67fa5e286`.

The pinned existing auditwheel toolset reports manylinux_2_39_x86_64. Retagging
changes WHEEL/RECORD only, preserving 560 other members byte-for-byte. Final
wheel SHA-256 is
`4bc3cd778990a35a3ff3e72f68fc8905e74804cb78b1d7091adbdc1b1fbfcdc8`.
A normal installation passes 258 cases without skips: 75 sampler, 120 uniform
array and 63 upload/state/example cases. Tk/capture validators pass and all five
active capture controls reject. All 537 installed members match per child;
shader checks verify 150 loaded origins and examples verify 171 Python origins.
All tracked shutdown gauges are zero. Scope is CPython 3.12.13, Tk 9 and the
pinned Mesa 26.1.8 WSL software driver; no physical GPU claim follows.

The original raw wheel also passed the 195 shader cases separately before
retagging. Both observations retain their identities; no installed result is
transferred between wheel hashes. All local transport, retag/tool and installed
scratch is removed and retained files rehashed. A retention helper initially
used a Windows native-key spelling; its correction and the zero-deletion
missing-manifest refusal are preserved. Tests and verifiers were unchanged.

These results close the selected cross-platform artifact/functional gap for
the explicit one-dimensional path. Multidimensional dynamic selection,
broader preprocessing/filter/mip-chain forms, implicit derivative decisions,
independent review, strict profile admission and release remain open.
