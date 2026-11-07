# Dynamic sampler indexing implementation

SHD-01 remains open. The published v2 wheels retain their literal-only sampler
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

Remaining work includes Linux outputs, broader macro/preprocessor forms, vertex-stage and dimension
breadth, actual resource-limit refusals, LOD/filtering outputs, cumulative
independent review and successor artifact/profile admission. Implicit derivative
semantics require their own design and output packet.
