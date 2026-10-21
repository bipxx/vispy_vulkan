# VisPy Dawn implementation completion plan

Refreshed 2026-10-10 from reviewed WIP and actual terminal evidence. Pass31/w17 is active and independently audited; device behavior remains a separate acceptance gate. Preserve pass 30's separate hardware packets and failed outer readers. The original thirteen-step scope below remains byte for byte unchanged.

Finish in two milestones: qualify the Windows Vulkan renderer and installed scientific/host workflows, then close the declared platform, binding, artifact and performance matrix. Preserve VisPy 0.17.0's public Python API, composer, scene graph, cameras, GLIR emitters and ordering. Keep distribution/import `vispy`, version `0.17.0+vulkan.1`, pinned dependencies and explicit deviations in `compat/deviations.txt`. The [design spec](../specs/2026-10-08-vispy-vulkan-design.md) defines release requirements; the [evidence journal](implementation-evidence.md) retains prior results and failures.

The endpoint route is compiled in active pass31/w17: 589 source files, 1,394 harness inputs, 28 disjoint owners, 16 linked targets and 18 passing CTests. CPU5 separately retains 856 evaluator, 380 core and 369 synthetic pool assertions. Transactional activation and independent audit pass with native30 backups retained. First endpoint freeze failed independent review before GPU launch because Windows changed generated plugin bytes. Fresh runner2 fixes only byte emission; 80 CPU guards and independent source/proof review pass. The preserved first hardware attempt has 1 pass, 17 failures and 74 deselections: sixteen unsupported write-only storage errors and one idle-record prerequisite failure. The shader source repair now passes CPU6. [Runner3 CPU117](../../../build/evidence/line-endpoint-native-runner-cpu-6/result.json) verifies direct PID or one exact OS-observed Windows launcher edge with executable hashes; a real stdlib child demonstrates that edge. Its [independent review](../../../build/evidence/line-endpoint-native-runner-review-shaders-3/result.json) preserves original 18/74/54 criteria. Fresh matching hardware acceptance remains open. Wide/smooth, SIZE/LINK12 and the full original release scope remain open.

The fresh [full32/w18 build](../../../build/evidence/native-pass-32-build-handoff-1/result.json) and [independent build review](../../../build/evidence/native-pass-32-root-build-review-1/result.json) pass: 589 sources, 1,485 harness inputs, 28 owners, all 16 linked targets, all 18 CTests and 18 archived outputs. The evaluator retains 7,422 instrumented assertions; core 380 and pool 369 remain separate assertion counts. Pass31 remains active. Production activation preflight, activation audit and fresh matching hardware qualification are next; this full build does not establish endpoint device behavior or wide/smooth rendering. The first freeze was rejected before copying because of an absolute manifest argument; the corrected relative argument passed in a fresh attempt, preserving the failed result. [Activation98 CPU guards](../../../build/evidence/native-pass-32-activation-guards-2/result.json) and [independent source review](../../../build/evidence/native-pass-32-activation-review-shaders-2/result.json) pass. Actual build-context preflight remains required.

## Reviewed status

| Area | Verified current result | Remaining work |
| --- | --- | --- |
| Active native build | [Pass31 activation](../../../build/evidence/native-pass-31/activation.json), [actual transaction](../../../build/evidence/native-pass-31-activation-process-1/result.json) and [independent audit](../../../build/evidence/native-pass-31-activation-audit-validation-1/result.json) pass. New current/staged/archived four files and old30 backups match; 898 approved Python/proof inputs remain held. Full31 has 589 sources/1,394 harness files/28 owners, 16 linked targets and 18 passing CTests. | Qualify actual endpoint behavior and separately rerun affected historical packets on this epoch. ABI source edits require a fresh matching build/activation. |
| Preserved parent epoch | Pass30/w16 retains 584 sources/1,051 harness inputs/21 owners, 14 targets/16 CTests and separate matching affected109, ordinary17, numeric12, paint8, oversized3, pending/reuse15 results. | Preserve originals and exact criteria; historical30 results do not qualify active31. |
| Oversized retention and pending draws | Six current categories and the unchanged 128-entry/64-MiB history coexist with an eight-entry/256-MiB per-Program oversized LRU working set, accounting for deduplicated child graphs. The 32-source CPU packet passes nine compiles/23 runs. Three original oversized cases pass on native30. Fifteen additional hardware cases cover selection/affine/divisor pending old→new DATA/constant-ATTRIBUTE snapshots, source/Program deletion before present, submitted deletion through real Ticket retirement, honest submitted loss and survivor recovery, unchanged A→B→A resident reuse, five-selection budget eviction and twelve ordered draws in three genuinely queued submissions. Exact raw pixels, actual execution and zero resident conversion/upload/allocation/compiler/wait costs pass separate offline admission and independent review. | SIZE/LINK and mixed mutations, arbitrary mutated layouts, general order-preserving storage partitioning and physical allocator/RSS remain open. Current/history/working gauges overlap and cannot be added; DELETE evidence is logical ownership. Failed capture and outer-reader runs remain immutable. |
| Affected regressions and ordinary inputs | Separate matching pass30 packets pass all 109 affected regressions and seventeen ordinary-input cases with exact historical IDs, zero errors/failures/skips and unchanged protected inputs. The broad packet includes image13/marker14/ordering2 plus affected point/Text/scientific/Qt/artifact/collector behavior. Ordinary17 preserves full thirty-input analytic capacity, original first/index/instance identities, constants/divisors, pending revisions, six topologies, flat-LAST, warm reuse and six losses; all 455 raw artifacts are retained. | Do not infer a new reference aggregate. Ordinary full-thirty upstream raster admission and general layout/storage partitioning remain unresolved. |
| Numeric texture transfer | Twelve matching pass30 hardware cases preserve original integer source dtypes and exact independent red R8/R32F bytes or float bits: full 8/16-bit domains and fixed/seeded 32-bit samples. Each uses one upload and typed copy, with zero DRAW commands. The wrapper rebinds only the canonical activation guard to pass30 before native import; original fixtures, arrays and criteria stay unchanged. | Shader sampling, other channels/formats/drivers, mixed revisions/FBO/loss/half storage, typed binding and universal signaling-NaN preservation remain unqualified. Glue's four-pixel/max-one volume difference remains open. |
| Whole Qt paint and completion ownership | All eight matching pass30 paint cases pass unchanged pixel and ownership gates. Established raw BGRA is retained and explicitly mapped once to owned RGBA. Forty-eight successful closed/retired owner joins and 36 enabled GPU maps remain required, including intermediate presentations and alpha tails; query-off checks still poll completion. Error/cancel/loss/detach cases reject unsuccessful frames honestly. The current FIFO case has twelve unique paints and ordered bounded receipts, with 0 observed deferred-counter increments; its queued path remains unqualified. Parent29's nine increments remain historical. The separate oversized queued case observes actual deferral. Neither count measures visible scanout. | Actual attached-surface acquisition fault, upstream context-owned instrumentation, visible/input timing and other binding/platform rows remain open. Queue completion is not visible presentation. |
| Endpoint evaluator WIP | CPU6 reviews and compiles the storage-access repair; eleven selected CTests pass. CPU5/full31 compile the pool, canary ordering, paired-render resources, Ticket lifecycle and accounting. Basic36 and lifetime38 CPU pass. [Runner2](../../../build/evidence/line-endpoint-native-runner-authoring-3/authoring.json) passes 80 CPU guards and independent review while preserving exact 18/74/54 hardware criteria. First freeze and failed review remain immutable. Fresh job status: failed. | The preserved first hardware attempt has 1 pass, 17 failures and 74 deselections: sixteen unsupported write-only storage errors and one idle-record prerequisite failure. The shader source repair now passes CPU6. [Runner3 CPU117](../../../build/evidence/line-endpoint-native-runner-cpu-6/result.json) verifies direct PID or one exact OS-observed Windows launcher edge with executable hashes; a real stdlib child demonstrates that edge. Its [independent review](../../../build/evidence/line-endpoint-native-runner-review-shaders-3/result.json) preserves original 18/74/54 criteria. Fresh matching hardware acceptance remains open. Native bounds/failure/category release/texture/FBO controls remain required. |
| Lines, scientific behavior and installed hosts | Portable ordered-segment, homogeneous clipping, perspective/noperspective and endpoint packing math passes 380 CPU checks in CPU4's matching line CTest. Six new private-state/clipped-interpolation upstream frames are frozen independently, alongside the original sixteen wide/smooth, five plugin-overlay and four scheduled-plane references. Older DIVE export/image and Glue scatter/edit successes remain historical. | The portable core is not integrated with runtime wide/smooth rendering. Implement isolated original-endpoint evaluation, expansion and the unresolved smooth coverage model, then qualify all original and new frames and affected installed hosts. Complete mesh/filter/vector/Grid/axes/colorbar/text/volume and ordinary DIVE/admissible visbrain workflows. |
| Platforms, artifacts and performance | SDK3 policy and historical wheel preflights are retained. Four fresh Windows PyQt5/PySide6 upstream/candidate environments pass CPU-only binding/import/origin checks; the candidate uses a historical w10 wheel. | Actual current-artifact graphics for these bindings, declared Windows/Linux/macOS and software rows, full integration including required stencil/wide cases, final installed artifacts, trustworthy upstream/visible/Metal telemetry and the original fixed-quality release matrix. |

Historical pass29 oversized wrapper2's hardware child exits zero with three exact tests and thirteen CPU cases deselected; its outer wrapper exits one solely on the parent `tools` import path. The fresh CPU-only offline admission completes the unchanged raw validator, verifies all 1,788 protected paths and 872 archive blobs and preserves that failed terminal. Historical pass29 wrapper3's explicit file-loader repair passes eighteen CPU guards; its separate pass29 hardware output remains unexecuted. Current pass30's original oversized3 job passes both its hardware child and outer admission. No GPU replay or criterion change is needed to admit the retained child evidence. Earlier source/harness lookup errors and all prior authoring/build/GPU failures remain archived.

Historical pass29/w15 and pass28/w14 retain their separately sealed numeric12, paint8, affected109 and ordinary17 qualifications. Pass29's separate matching packets remain immutable parent evidence; the current pass30 qualifications above are distinct jobs. Older pass23's 247 selected integration successes and the 185-admitted/39-unresolved inventory remain historical, including their unresolved required stencil/wide cases. Refresh inventories from evidence rather than adding separate packet counts.

## Ownership and dependencies

| Owner | Writable responsibility |
| --- | --- |
| Renderer | Ordinary/point runtime, native bindings, shader normalization and matching C++ contracts. |
| Coordinator | Texture runtime/contracts, benchmark collector, completion plan and integration decisions. |
| Validation | Independent reference/fixture admission, ordering/image/marker/scientific/paint checks and raw parity evidence. |
| Packaging | CMake, SDK/build guards, compatible artifacts, provenance and locked environments. |

Preserve peers' edits and acknowledged holds. Immutable CPU builds and independent authoring may run in parallel; binary activation and GPU jobs remain serialized. Every job uses fresh outputs with archived commands, environment, source/harness/reference/native identities, actual counters and terminal exits. Preserve original expected pixels and tolerances. A later renderer packet follows independent admission → matching CPU proof/review → ownership freeze/build/CTest → guarded activation → serialized hardware → affected requalification.

The reviewed storage-access repair uses read-write output storage and a new evaluator cache identity. [CPU6](../../../build/evidence/line-evaluator-cpu-6/result.json) compiles seven requested targets plus the layer dependency and passes all eleven selected CTests; eighteen were discovered. Its [independent build review](../../../build/evidence/line-evaluator-cpu-6-root-review-1/result.json) verifies the whole 91-file archive, 589 sources and 1,027 selected harness inputs. The 7,422 evaluator, 380 core and 369 pool instrumented assertions are separate from case counts. Native31 remains active; the isolated CPU6 module has not been imported or activated. Full32/w18 now passes all sixteen targets/eighteen CTests and independent review. Guarded activation and fresh hardware context are next.

## Execution packets

These packets preserve earlier checkpoint detail and all acceptance requirements. Use the reviewed status and next implementation batch for current progress: the historical 294-check core now has 380 assertions, and resource changes described below as source-only are compiled in CPU5 and full pass31. Their hardware and raster qualification remains open.

### 1. Preserve pass30 qualification and close remaining oversized lifetime cases

Preserve the completed pass30 build and separate matching affected109, ordinary17, numeric12, paint8, original oversized3 and fifteen-case pending/reuse qualifications. Keep the canonical context guards, exact historical IDs, all parent results and failed outer readers immutable. The pending packet's child passes15; the outer reader fails because it expects monolithic SHADERS records. Its separate CPU-only admission reconstructs actual CREATE/DATA/ATTACH/LINK events and checks every working DRAW's linked sources before applying the unchanged remaining raw validators.

The qualified pending/reuse packet covers old/new DATA and constant ATTRIBUTE snapshots, source/Program deletion before presentation, submitted Ticket deletion, actual submitted loss and survivor recovery across all three oversized families. Extend independent authoring to SIZE, LINK and mixed mutations without weakening those pixels or retirement criteria. Verify immutable old/new identities, flat-LAST and order, eventual ownership retirement, honest failed loss receipts, no deleted replay, retained survivor CPU conversions and exact one-time GPU reconstruction. Keep quality reads outside resident intervals and conversion/upload/allocation/compiler/wait negative checks in place.

Final SIZE/LINK authoring is sealed: two mutations × three original oversized families × survivor or source/Program DELETE before final present, for twelve GPU cases. The final run passes nineteen exact CPU tests with twelve GPU cases deselected, zero errors/failures/skips and no native import or GPU. Its [authoring record](../../../build/evidence/ordinary-oversized-mutations-authoring-1/authoring.json) and [terminal](../../../build/evidence/ordinary-oversized-mutations-authoring-1/terminal.json) are independently checked, including one synthetic guard positive and twenty-one guard negatives. Six current-source installed upstream emitter witnesses pass without a GL context or parser/raster execution; they prove command/payload emission only. Preserve the original expected arrays and validate each DRAW against the sources attached at its successful LINK, rather than a later global shader map. Scratch runs remain historical.

Use the sealed final authoring inputs and require a guarded matching future native epoch (at least 31) for these twelve cases, which remain candidate-unseen and unrun. Each pending case must retain CLEAR plus old/new DRAW before one final submission, prove two scene draws/one submit/one retired Ticket and match the independent full 48×24 image. SIZE survivors prove changed-input conversion/upload; LINK survivors prove the new shader output and may reuse unchanged geometry. Both then demonstrate zero resident conversion/upload/allocation/compiler/wait costs; deletion must release logical ownership after real retirement. Mixed DATA/SIZE/ATTRIBUTE/LINK, post-submit deletion, loss/recovery and backpressure are further independent packets.

**Exit:** remaining independently admitted oversized mutation/lifetime cases pass on a matching build, with the five regression packets preserved and rerun after affected source changes. Physical allocation/RSS uses separate evidence from logical ownership gauges.

### 2. Close remaining oversized reuse and layout limits

The implemented oversized working set has an eight-entry/256-MiB per-Program budget and LRU selection order. Two unchanged affine payload graphs of 67,109,040 bytes each fit together; A→B→A hardware checks require zero resident conversion/upload/allocation/compiler/wait costs. Five selection payloads exceed the budget and require bounded capacity eviction, while the current selected record stays reusable. The separate six current owners and unordered historical 128-entry/64-MiB cache remain visible. Exact keys and source generations, deduplicated child accounting and replacement staging are CPU-tested. This qualifies unchanged DRAW selection, not arbitrary mutated layouts or physical allocator usage.

Implement field partitioning for legal layouts that exceed granted per-buffer stride/storage limits, then ordered batches when a compact selection cannot fit one storage binding. Each Vertex/Instance category needs a composite current owner for all partitions; replacing its single slot repeatedly would defeat resident reuse. Preserve original uint32 vertex/instance IDs, nonzero first, divisors/constants, sparse indices, topology boundaries, flat-LAST, primitive restart and blending/depth order across partitions. Preserve instance-major primitive order; submitting all instances of vertex chunk A before chunk B can change blending. Plan from actual granted stride/buffer-count/allocation limits with checked arithmetic. Retain strip winding/joins, fan/loop closure and the original provoking value at every batch boundary. A field with no legal representation under those grants requires a contextual capability error before encoding work.

**Exit:** independent boundary/reference fixtures and matching native cases prove legal layout handling, resident reuse, revision/loss behavior and bounded CPU/GPU ownership. Reduced-limit CPU contracts supplement actual hardware; they do not replace the device's real grants.

### 3. Implement wide and smoothed lines, then qualify affected hosts

Follow [wide-line notes](wide-line-implementation-notes.md). The six private-global and clipped perspective/`noperspective` fixtures are now independently frozen upstream. Integrate the portable 294-check segment/clipping core; native runtime evaluation and rasterization remain open. Snapshot width/smoothing state with each immutable draw. Evaluate original endpoints once in isolated invocations using the original shader inputs, private state, uniforms, textures and integer identities; calling mutable vertex `main` twice in one invocation lacks that guarantee. Preserve homogeneous clipping, perspective/noperspective interpolation, flat-LAST, depth/discard/scissor/stencil/culling and overlapping segment order. Suppress introduced triangle culling/bias and duplicate quad-seam coverage. Derived compute/render resources require bounded ownership, actual dispatch counters and timestamp intervals, mapped diagnostics, resident counters and loss recovery.

The implementation persists typed varying/array/interpolation metadata in `shader/normalize` and the portable artifact. `shader/line_evaluator` generates isolated compute through the existing glslang parse/link, SPIR-V validation and reflection route. ABI1 carries a four-word header, exact uint32 vertex/instance identities and raw attribute components; reflected output rows contain original GL clip position and typed varyings. CPU4 compiles the diagnostic runtime module and passes the evaluator, core and existing shader/point/artifact/Text/volume contracts. Ten of seventeen discovered CTests execute, including 856 evaluator and 380 core checks; no module import, activation or GPU work occurs.

The compiler initializer-order blocker is repaired and covered by CPU2. The pinned compiler's original initializer aggregates retain declaration order and source locations at a checked generated-entry marker after valid-invocation input decoding and before one user-main call. Ordinary render/default-compute compilation remains intact; unexpected AST shapes fail contextually. Genuine SPIR-V/CFG regressions cover direct input/ID dependencies, helper and conditional initialization, private state, early returns and inactive padded invocations. A default-policy comparison reproduces the preceding hoisting defect; CPU1 remains immutable historical evidence.

The raw-input bound is also repaired: `runtime_line.hpp::pack_endpoint_inputs` and `line_evaluator_dispatch` require total header plus payload to fit UINT32_MAX uint words. The new boundary negative uses 2,147,483,646 list endpoints and a two-word identity-only row, requiring the specific ABI error before source reads/allocation. The fresh CPU2 source/cache/evidence set passes all ten selected contracts/corpora against the eleven held inputs; active native30 remains unchanged. This completes checkpoints A–C in CPU scope.

The compiled CPU3 baseline captures original line selection/index ownership before topology rewriting and original attribute/uniform/texture bindings before ordinary packing. It retains evaluator CPU artifacts within the existing shader-cache budget across device loss, exposes compute grants/counters and checks reflected resource mapping. CPU4 compiles D3's exact original-artifact retention, private diagnostic preparation and compute-before-render encoding. A seventh `LineEndpoint` input category shares existing cache budgets; native30's six categories remain its qualified baseline. CPU4 also compiles the reviewed cancellation/pre-Ticket failure, mutation invalidation, bounded diagnostic error/control accounting and shutdown/map-lifetime fixes. Actual device behavior is unrun. Later capture-off and pool telemetry changes are source-only; reusable endpoint and paired-render resources still require integration and a fresh proof. Width greater than one and smoothing remain unsupported pending runtime image/lifetime gates.

Use the portable core to clip against all six GL homogeneous planes, retain original flat-LAST and instance-major order, distinguish perspective from noperspective interpolation, and convert Y/depth once. Apply the same granted-limit partition and topology/order requirements as packet 2 to evaluator input/output storage.

Qualify the evaluator outputs before triangle expansion. Then preserve fragment depth/discard/front-facing/coordinates, suppress triangle culling and fill bias, prevent duplicate quad-seam coverage and retain overlap/blend order. Implement aliased major-axis rasterization and smooth coverage separately. The ideal box-filter experiment predicts endpoint coverage 128 where the pinned smooth reference observes 164. Establish a principled coverage model against all sixteen unchanged references; retain the explicit-depth-clear admission and original undefined-depth failure. Then qualify installed Glue axes, five genuine plugin overlays and four scheduled-plane interactions using real Qt input/timers and clean teardown.

**Exit:** exact admitted width/smoothing frames, clipping/interpolation/depth controls and affected host interaction states pass on the matching build without unexpected graphics or lifetime errors.

### 4. Complete typed sampling and scientific semantics

Carry actual Uint/Sint, unfilterable-float and comparison/depth sample types through prepared/retained textures, shader normalization, bind-group layouts and pipeline/cache keys. Freeze legal upstream references before candidate pipelines. Cover feature-negative errors, multisample depth/stencil, mixed-dtype partial updates, sized float/integer formats, revisions, pending draws, framebuffer behavior and loss. Preserve scientific range/NaNs and exact categorical IDs; the observed red-transfer arithmetic is not a universal texture contract.

Refresh [scientific coverage](scientific-fixture-coverage.md) and the requirement-to-fixture inventory. Add flat/smooth mesh, SurfacePlot, composed filters/clipping, shapes/vectors/tracks, Grid/axes/colorbars and rotated multiline text at 96/120/144 DPI. Complete scalar/categorical volume modes and threshold/gradient/step/opacity, ray/plane, RGB(A), clipping and mesh depth. Refresh affected image13/marker14/ordering/point/Text/volume checks after source changes.

**Exit:** every required behavior has an independently admissible reference and matching pipeline/image/depth/revision/lifetime/resident evidence. Imports or shader compilation alone do not qualify rendering.

### 5. Close installed scientific and host workflows

Resolve public stencil-wrapper, Glue volume-edit and ordinary DIVE admissions separately from candidate renderer defects. Preserve Glue's four-pixel/max-one volume criterion and ordinary teardown/scatter failures. Admit visbrain only through a successful pinned upstream workflow. Constructor/private-API failures stay visible; scoped direct semantics and export successes do not qualify unchanged public host flows.

Rebuild installed artifacts after affected native changes and run the original host workflows with recorded artifact versions, real input/timers, exact captures, exports and clean close. Keep upstream and candidate environments separate and restore upstream after uninstall checks.

**Exit:** required host rows link to frozen admissible references and matching installed results, with constructor, interaction, rendering and teardown scope stated explicitly.

### 6. Finish trustworthy completion and measurement instrumentation

Preserve whole outer Qt paint ownership, alpha tails, intermediate presentations, all owned Tickets and final-submission counter snapshots. Keep strict issued/closed/retired receipt and GPU-map joins, query-off polling and complete rejected-batch ledgers. Add an actual attached final-surface acquisition failure after an earlier successful present; real detachment and CPU fault injection do not replace this hardware gate.

Implement context-owned asynchronous upstream GPU queries and actual compiler/link/upload/resource/draw/wait counters. Define unpaced completed-frame throughput and normally paced completion/input latency profiles before tuning. Label callback/fence-poll clocks and uncertainty; establish calibrated presentation/input-to-visible observations. Keep logical bytes, API allocator observations, process RSS and physical/opaque coverage distinct. Add actual Metal commit/allocation evidence on its runner and measure instrumentation cost.

**Exit:** both processes have complete frame joins, honest failure/cancellation, scoped timing/counter/memory evidence and bounded queues for each comparison profile. Capability metadata cannot set verified scope.

### 7. Qualify Qt bindings and declared platforms

Prepare Windows/Linux x86-64 Vulkan, Linux X11/xcb through XWayland and macOS 13+ arm64/x86-64 Metal runners with designated integrated/discrete devices and recorded access. Use supported PyQt5/PyQt6/PySide6 environments; retain legacy PySide2 host scope separately. Pair correctness on a pinned software Vulkan ICD and separately pinned upstream software OpenGL, retaining all assertions; software rows do not qualify hardware.

Exercise surfaces, resize/reparent/show/hide, sharing/multiple canvases, actual DPI/monitor transitions, capture, timers/input, asynchronous errors, close and device/surface loss. Record installed artifacts, drivers/backends and granted limits. Reconcile older alpha-clear prohibitions with independently proven Qt capture semantics while retaining raw scientific alpha checks.

**Exit:** all declared rows have real graphics and clean lifecycle evidence. Missing runners/access remain open dependencies while available implementation proceeds.

### 8. Integrate finished source and qualify final artifacts

Join one hashed finished source/build for the full admitted CPU/native/shader/gloo/texture/state/marker/Qt/parity/host matrix. Start from `build/reports/integrated-native-pass-3-command.json`, explicitly accounting for formerly excluded required stencil/wide cases. Archive individual failures, diagnostics and terminal exits.

Build compatible Windows CPython 3.10–3.14 wheels and declared Linux/macOS artifacts. Run external installed clear/Text/SDF/capture/assets/notices, supported Qt/host workflows and uninstall/upstream restoration. Verify dependency/compiler policy, package/license/provenance inventories and clean loader discovery. Later affected source changes require rebuild and requalification.

**Exit:** final source/artifacts pass full applicable matrices without required skips, native crashes, unexpected validation errors or unbounded retirement.

### 9. Measure the fixed-quality release matrix

Use separate upstream/candidate processes on the same designated hardware/driver/host versions, including presentation conversion and Y orientation. Complete the 66-workload catalog: 4096² scalar/RGB(A) at 4K with one/eight layers, one million structured points in both methods, and 256³/512³ volumes. Freeze resident/full-update/region-update parameters and quality admissions.

Use at least 100 warmup frames, 1,000 measured frames and five alternating reference/candidate pairs. Every primary resident workload needs median speedup ≥1.20 and no worse p95; admitted update regression is at most 10%. Unchanged warm data requires zero texture/vertex reuploads, CPU conversions, compiler/pipeline misses and deliberate waits. Report throughput and paced/visible latency only at packet 6's verified boundaries; repair regressions and repeat affected correctness/artifacts.

**Exit:** publish release/capability/performance claims only after all required gates pass. Smaller, lower-quality or software speed results cannot replace the release contract.

## Next implementation batch

Finish endpoint behavior first, then wide/smooth rendering, then the full renderer and release matrix. Active31 compilation, transactional activation and independent audit are complete; repaired full32 passes all16/all18 and independent build review, with activation/device gates pending. [Checkpoint31](../../../build/evidence/completion-plan-refresh-pass-31/report.json) records actual evidence. Preserve original arrays, pixels, tolerances, failures and acceptance conditions.

| Sequence | Owner and files | Exit condition |
| --- | --- | --- |
| 1. Complete: source, CPU and activation | Runtime/shader/CMake owners; validation audit | CPU5/full31 pass; exact four files activate; old30 backups and 898 approved inputs match independent audit. |
| 2. In progress: build reviewed repairs and retry endpoint acceptance | Shader evaluator/contract; validation runner and held basic/lifetime tests; coordinator review | Demonstrated failures fixed; fresh matching reviewed context; exact 18 GPU IDs/74 deselections/54 successful phases and original typed output/canary/lifetime gates pass. |
| 3. Close endpoint gaps | Validation independent fixtures; renderer/coordinator for demonstrated defects | Capacity/churn/zero-row, category release, texture/FBO order, real rollback/fault and submitted-cancellation ownership have witnesses. |
| 4. Matching affected regressions | Validation serialized jobs; packaging provenance | Separate affected109, ordinary17, numeric12, paint8, oversized3, pending/reuse15 and eligible SIZE/LINK12 pass original criteria. |
| 5. Wide/smooth rendering | Renderer/coordinator; validation original 16 plus new 6 references and hosts | Original endpoint consumption, clip/interpolation/flat-LAST/seams/depth/blend and aliased/smooth coverage pass. |
| 6. Original renderer and release scope | All owners; execution packets1–9 and original thirteen steps | Scientific/host/platform behavior, installed artifacts and fixed-quality performance gates pass. |

### 1. Retain the completed source, CPU and activation

Whole-batch reservation precedes dequeueing. Pending draws receive exclusive output, compute-UBO and paired-render-UBO storage; exact native binding keys and uniform shadows are cached and submitted owners move to real Tickets. Canary initialization follows Ready reservation. Retain bounded PMR control, weak CPU revisions with native wrappers, presentation caching, generation teardown and descriptor deduplication. Limits are 128 slots, 64 MiB owned capacity including 64 KiB maximum shared canary reservation, and 1 MiB control; staging ceilings do not exceed resident ceilings. Overlapping logical gauges do not prove physical driver memory.

CPU5 seven requested targets plus layer/eleven selected of 18 discovered CTests pass; 856 evaluator/380 core/369 pool assertions remain separate. Pool assertions use synthetic payloads and explicit phase calls. Full31 all 16 targets/all 18 CTests and 18 pinned artifacts pass with SDK3/private Tint disabled. The 74 activation guards, actual transaction and independent audit exit 0, preserving native30 rollback leaves. The fail-closed late-preparation-error retry limitation remains disclosed.

### 2. Fix demonstrated endpoint defects and qualify basic11 plus lifetime7

Freeze1 exited0 but [independent review](../../../build/evidence/line-endpoint-native-pass31-frozen-review-1/result.json) failed before GPU launch: Windows text writing changed LF to 16 CRLF lines. Preserve original plugin/context/runner1 and all 898 approved inputs. Runner2 changes only exact UTF-8 byte emission. [CPU80](../../../build/evidence/line-endpoint-native-runner-cpu-5/result.json) includes all 77 original guards plus actual Windows freeze-body, old-bug counterfactual and exact-delta checks; [independent review](../../../build/evidence/line-endpoint-native-runner-review-shaders-2/result.json) passes.

Fresh line-endpoint-native-pass31-2 was frozen with actual31 activation/handoff/ownership hashes and CPU5 result/seal, root build review, activation guard/audit, new runner2 CPU/source/review proofs. Its [independent frozen review](../../../build/evidence/line-endpoint-native-pass31-frozen-review-2/result.json) verifies emitted bytes, command/environment/interpreter/native origins, all 2,916 archived originals, 1,247 blobs and exact IDs.

This context has already been attempted and must remain immutable. Preserve all failures, raw records, receipts and terminal closure. Retry only in a NEW reviewed output after source review, matching CPU/full native build and guarded activation for any ABI source edit.

The preserved first hardware attempt has 1 pass, 17 failures and 74 deselections: sixteen unsupported write-only storage errors and one idle-record prerequisite failure. The shader source repair now passes CPU6. [Runner3 CPU117](../../../build/evidence/line-endpoint-native-runner-cpu-6/result.json) verifies direct PID or one exact OS-observed Windows launcher edge with executable hashes; a real stdlib child demonstrates that edge. Its [independent review](../../../build/evidence/line-endpoint-native-runner-review-shaders-3/result.json) preserves original 18/74/54 criteria. Fresh matching hardware acceptance remains open.

The [retained hardware terminal](../../../build/evidence/line-endpoint-native-pass31-2/terminal.json), strict XML and raw failure records expose the current blocker. The repaired declaration is compiled and reviewed in full32; retain the original diagnosis from cpp/shader/line_evaluator.cpp: GLSL writeonly becomes SPIR-V storage access that the pinned Dawn/Tint path rejects. The supported read-write declaration preserves layout, row bounds, store-only behavior, canaries and original results; its meaningful compiled access-decoration contract passes in CPU6 and full32. Qualify actual Dawn pipeline and output behavior after guarded activation.

The idle failure involves a failed owner's uncollected terminal timing record. Collect terminal records before reconfiguring frame slots. [New independent failure controls](../../../build/evidence/line-endpoint-failure-dawn-authoring-2/result.json) pass 29 CPU cases and [source/evidence review](../../../build/evidence/line-endpoint-failure-dawn-review-shaders-2/result.json). Three device cases for cancel, paint abort and destroy remain unrun. They cover negative-first DRAW rejection before any Submit and terminal-record drainage; pipeline-failure rollback, encoding/queue/map faults, endpoint output and genuine queued/submitted cancellation remain separate open gates. Runner3's real Windows control observes launched PID24176, actual Python50888 and parent24176 with matching live image hashes; it has not run a hardware context.

Require original eight D1 cases, three basic controls and seven lifetime cases without changing arrays/tolerances: exact reflected types, matrix/array strides/raw bits, logical65/padded128 rows, inactive/trailing canaries and owned arrays. Capture-off still computes/draws/submits/retires with zero unchanged allocation/bind/conversion/input-upload/compiler/wait costs. Separately warmed UNIFORM-only edits require positive changed bytes; quality reads stay outside measured intervals. Query-on records actual compute/scene/capture pairs; query-off retires without query allocation. Pending matrix/DATA A→B→A, cancellation and loss/recovery retain independent criteria.

**Exit:** exact 18/74/54 and strict raw admission pass. Missing genuine queued/submitted/deferred witnesses stay unresolved. Process closure alone does not establish native cleanup. Diagnose actual failures and rebuild fresh matching epochs before retrying renderer fixes.

The reviewed storage-access repair uses read-write output storage and a new evaluator cache identity. [CPU6](../../../build/evidence/line-evaluator-cpu-6/result.json) compiles seven requested targets plus the layer dependency and passes all eleven selected CTests; eighteen were discovered. Its [independent build review](../../../build/evidence/line-evaluator-cpu-6-root-review-1/result.json) verifies the whole 91-file archive, 589 sources and 1,027 selected harness inputs. The 7,422 evaluator, 380 core and 369 pool instrumented assertions are separate from case counts. Native31 remains active; the isolated CPU6 module has not been imported or activated. Full32/w18 now passes all sixteen targets/eighteen CTests and independent review. Guarded activation and fresh hardware context are next.

### 3. Close native lifetime and failure controls

Add independent ATTRIBUTE/index/SIZE/LINK/DELETE release, count/byte/control/staging bounds, heterogeneous A→B→A, eviction/churn/zero rows, whole-batch deferral/rollback, ordered texture revisions and preceding FBO writes. Cover pre-Ticket, encoding/queue/map/timeout failures. Probes that poll completion cannot establish submitted-cancellation charges before processing; use a distinct ownership observation. Retain actual PMR/native handles, Submit/callback retirement, generation teardown and warm-zero witnesses. Authoring/CPU review may run in parallel; activation/hardware stay serialized.

### 4. Requalify affected behavior and oversized mutations

[Six31 provenance adapters](../../../build/evidence/native-pass-31-requalification-authoring-1/authoring.json) pass 151 CPU checks and [independent review](../../../build/evidence/native-pass-31-requalification-review-shaders-1/result.json); failed CPU1 remains retained. Actual context freeze and hardware remain separate gates. Preserve historical IDs, validator bodies, fixtures, arrays and criteria. Pending15 admits actual CREATE/DATA/ATTACH/LINK sources while retaining every remaining raw predicate and the failed parent outer reader. Create and review its fresh canonical31 recipe before freeze. Emit plugins as byte-exact UTF-8 on Windows.

Run affected109, ordinary17, numeric12, paint8, oversized3 and pending/reuse15 separately on matching artifacts. Then run eligible SIZE/LINK12: two ordered draws, one final submit, one retired Ticket, full independent 48×24 pixels and negative survivor costs. Mixed/post-submit mutations, loss/backpressure, arbitrary layouts, ordered storage partitions and physical allocation/RSS remain additional gates. Do not sum separate packets into a reference aggregate.

### 5. Integrate wide and smoothed lines

Consume admitted typed endpoint output without invoking the user vertex shader again. Snapshot finite positive width/smoothing per DRAW; retain original segments/indices/instances, loop closure and provoking LAST. Apply six-plane homogeneous clipping before expansion, reconstruct perspective/noperspective interpolation, and apply Y/depth conversion once. A typed consumer reads leased output and emits six procedural corners per ordered segment; extend binding/layout/control accounting against actual grants, retain Ticket owners, warm reuse and preceding FBO/copy order.

Wrap original fragment entry once, preserving discard/depth/scissor/stencil/front-facing/blend order. Suppress introduced culling/bias and duplicate quad-seam coverage; reject unsupported sample/builtin policy before encoding. Qualify original 16 plus new 6 references: H/V/diagonal and private/clipped interpolation first, then color/flat-LAST/scissor/overlap/depth. Resolve smooth 128-predicted versus 164-observed coverage from a principled model with unchanged pixels/tolerances. Enable width/smoothing only after qualification; then test installed Glue axes, five plugin overlays and four scheduled-plane interactions.

### 6. Close every original renderer and release requirement

Execution packets1–9 and original thirteen steps remain active: layout/storage partitions and mutation lifetime; Uint/Sint/unfilterable/comparison/depth/MSAA/half/NaN sampling; mesh/filter/vector/Grid/axes/colorbar/text/volume; Glue, ordinary DIVE and unchanged admissible visbrain. Qualify current-artifact Windows Qt bindings, Linux X11/Xwayland, declared macOS Vulkan/Metal, software/integrated/discrete, attached-surface faults, DPI/input/teardown, context-owned queries, visible timing and physical memory. Missing runners/unadmitted references remain explicit dependencies.

Run full integration including required stencil/wide, then final CPython3.10–3.14 Windows and declared Linux/macOS artifacts with external installed hosts and uninstall/upstream restoration. Measure original 66 fixed-quality workloads: 100 warmups, 1,000 measured frames, five alternating pairs, median speedup≥1.20, no p95 regression, update regression≤10%, warm zero uploads/conversions/compiler misses/waits.

**Exit:** every original acceptance condition passes. The complete implementation goal remains active.

## Original thirteen-step scope

The steps below preserve the initial requirements and baseline context. The current sequence above and the evidence journal determine what remains; implemented items need integrated verification rather than reimplementation. Each step retains its original acceptance condition.

1. **Establish reproducible environments and meaningful regressions.** Preserve a source snapshot before editing because the workspace has no Git history. Record build tools, native dependency revisions and checksums, Python, Qt, NumPy, host versions, adapter, and driver. Add locked host qualification environments before running `uv sync`: napari is installed in the current environment but is absent from the project lock, so a synchronized environment can otherwise remove it. Separate CPU contract tests from GPU and host tests; a missing required host dependency must fail its qualification job rather than skip it.

   Create an upstream OpenGL environment independent of the fork. Add a shared deterministic fixture runner and oracle capture tools under `tools/`, with manifests and arrays under `tests/reference/`. Capture raw RGBA, expanded shaders, filtered upstream GLIR, package origins, fixture parameters, and versions. Rework the six order proofs to keep operations pending before one final submission and readback. Add regressions for each reproduced review failure, with expected pixels or explicit errors. Fix comparison masks and tolerances before examining candidate results: use the design spec's interior and edge rules, and exact category, landmark, and depth decisions.

   **Acceptance:** the current implementation fails the new regression cases for the expected reasons; upstream passes the corresponding supported fixtures; every reference has sufficient provenance to regenerate it. Candidate-versus-candidate capture consistency remains a separate check.

2. **Make native errors and capabilities accurate.** In `cpp/runtime.cpp`, `cpp/runtime.hpp`, and `cpp/bindings/module.cpp`, capture Dawn creation and submission errors using the pinned API's error scopes or creation status. A non-null error object must never count as a valid shader, pipeline, texture, or buffer. Return compiler stage and mapped diagnostics to Python, and reject unsupported GLIR commands or state with the object and operation identified. Request the limits and features required by admitted fixtures, then report the limits actually granted by the device. Correct the Python query bridge so 2D, 3D, buffer, attribute, and sampler budgets are distinct.

   **Acceptance:** invalid shader or pipeline descriptors report failure with diagnostics; legal allocations at a reported limit succeed; requests above a granted limit fail before allocation. Hardware and software adapter runs remain distinguishable.

3. **Repair submission ownership and resource retirement.** Replace callback pointers into growable vectors and stack wait objects with stable owned completion state. Callbacks record status; engine event processing retires completed submissions and releases their staging data and GPU resources. Use a bounded frame ring, initially three slots, with event-loop rescheduling when slots are busy. Make its bound configurable for measurement without permitting unbounded growth. Bound diagnostic retention as well.

   Land safe lifetime handling and event processing before removing presentation waits. Ordinary frame presentation must submit without polling for GPU completion. Explicit `finish()`, capture, and shutdown wait for the appropriate submitted work with valid owned callback state and error propagation. Connect completion processing to Qt and headless event processing. Replace forced process-exit teardown with ordered cleanup once all callbacks and native objects have safe lifetimes.

   Add counters for deliberate completion waits, pending submissions, live allocation bytes, retired resources, upload bytes, and pipeline reuse. Count actual GPU uploads separately from CPU revisions.

   **Acceptance:** delayed completion, canvas closure, device loss, and cancellation cannot access freed memory. A long update loop keeps submissions bounded and releases superseded allocations after completion. Warm interactive frames add zero deliberate completion waits; explicit finish completes all prior work. Use resource counters as the retirement assertion and process memory as supplementary evidence.

4. **Separate shader artifacts from pipeline variants.** Extract the portable program artifact from device-specific shader modules and render pipelines. Retain composer source, normalized GLSL, SPIR-V, reflection, and source maps after Python deletes the attached shader objects. Key pipelines by device generation, vertex layout, primitive topology, binding sample types, attachment formats, blend and depth/stencil state, culling, write masks, and sample count. Keep viewport, scissor, resource bindings, and uniform values dynamic where supported.

   Add reflection and uniform packing helpers under `cpp/shader/`. Pack matrices and arrays using reflected offsets, strides, and orientation. Lower boolean storage together with boolean expressions. Apply coordinate conversion once after the user vertex entry point completes. Preserve sampling behavior; replace blanket LOD-zero rewriting with transformations justified by each admitted shader fixture. Keep the glslang parse, link, and SPIR-V route isolated in `glslang_spv.cpp`, with validation enabled.

   **Acceptance:** scalar and vector arrays, matrix arrays, `mat2`, `mat3`, `mat4`, and boolean expressions render expected values. Uniform edits reuse a pipeline; layout or state changes select a distinct variant. Cache-hit reporting distinguishes first creation from reuse. Corpus tests construct pipelines using each fixture's actual vertex, binding, color, depth, and sample configuration.

5. **Record ordered GLIR operations and complete render state.** Replace the detached clear flag and draw-only pending list with ordered clear and draw operations. Capture clear color/depth/stencil values and masks at the command's position. Snapshot viewport, scissor, blend, depth/stencil, color masks, culling, and admitted depth bias. Implement the framebuffer stack and reset its environment on `CURRENT` as upstream does. Capture attachment allocation generations so later deletion, resize, or reattachment cannot redirect an earlier operation.

   Encode pass boundaries for target changes, clears, attachment sampling, and resource hazards. A clear-only operation must target its captured framebuffer. Keep the Python queue filter's result and flush boundaries intact. Unsupported state must fail explicitly until its admitted implementation exists.

   **Acceptance:** draw-red then clear-blue ends blue; clear-blue then draw-red preserves the correct ordered result; a clear-only FBO leaves the canvas unchanged. Nested FBO deactivation restores the previous target. Viewport/scissor, separate blend factors, depth, masks, and state changes between draws agree with upstream. Resize and deletion before submit preserve earlier snapshots.

6. **Complete vertex, index, and texture semantics.** Build vertex layouts from formats, strides, offsets, and divisors. Support interleaved structured arrays and constant attributes throughout the draw. Encode index selection with `SetIndexBuffer` and `DrawIndexed`; widen unsigned-byte indices through an explicitly counted conversion. Preserve first/count, topology, strip index format, and instance count. Divisors above one and primitive modes requiring expansion need an admitted conversion path.

   Introduce an explicit scientific texture format table covering dimensions, channels, dtype, internal format, sample type, and filtering support. Preserve floating-point range, NaN behavior, and integer identity. Apply partial uploads at their offsets within the allocation descriptor. Use ordered copies or versioned allocations where an earlier pending draw must see older contents; reuse allocations when no ordering hazard requires a new version. Implement wrapping and interpolation rather than hard-coding nearest sampling. Handle 3D uploads and host-used LUT formats.

   **Acceptance:** indexed quads with 8-, 16-, and 32-bit indices, interleaved attributes, constants, and instanced layouts render correctly. A corner update preserves untouched texels and earlier draws. A float texture value of 15 with clim `(10,20)` yields midpoint intensity. Signed, unsigned, and sparse categorical values retain identity. Noncontiguous input copies are accounted for. Resident pan and rotation do not upload unchanged texture or vertex data.

7. **Recover resident resources and complete Qt presentation and capture.** Use actual device-loss notifications and device generations. Recreate shader modules, pipelines, buffers, textures, and surfaces from retained CPU artifacts before resuming an existing program. Device loss must invalidate old bind groups and pending device work without invalid callback access. Report unrecoverable failures to Python.

   Complete parented QWidget lifecycle behavior for handle changes, reparenting, zero size, minimize/restore, close with pending submissions, and surface loss. Preserve inherited input and gesture handling. Treat headless swap/present as a frame boundary, separate from explicit finish. Add depth/stencil attachments and MSAA resolve as required by canvas configuration. Capture the current owned target with correct crop, alpha, output type, and row origin; returned arrays and QImages must own their data independently.

   **Acceptance:** the same resident program and data render identically after recovery. Zero-size/minimized canvases do not submit. Shared canvases keep independent state and targets. Capture survives canvas destruction, excludes child overlays, and agrees with upstream for asymmetric scenes and MSAA. Real Qt pan/zoom renders frames and adds no deliberate completion waits. Test PyQt5, PyQt6, and PySide6 in separate environments; monitor moves and fractional desktop scaling require actual desktop qualification.

8. **Finish CPU helpers and qualify the Windows wheel.** Build the pinned `_sdf_cpu.pyx` with Cython and NumPy headers through CMake and include it in editable and wheel installations. Remove the copy-return shim or replace it with a correct in-place implementation if a supported fallback is retained. Include upstream assets, font licenses, VisPy's license, and linked native dependency notices. Add reproducible CMake presets and immutable dependency configuration, and keep generated build output separate from source.

   Run the repaired contract, native, shader, GLIR, Qt, and napari tests. Run supported upstream CPU tests with their original assertions. Build a wheel and install it in a clean environment outside the repository. Verify distribution and module origins, compiled SDF behavior, rendering, text, assets, native loader discovery, uninstall, and reinstall of upstream VisPy.

   **Acceptance:** all 16 review findings are covered by passing tests; deterministic fixtures agree with independent upstream references; resource retirement and warm-frame counters meet their assertions; the clean Windows consumer environment uses only the fork's installed files. This completes the Windows engineering milestone.

9. **Complete image and label behavior.** Extend the fixture matrix to scalar and RGB(A) images, admitted signed/unsigned/float dtypes, explicit and automatic clim, gamma, NaNs, continuous colormaps, LUTs, nearest/linear interpolation, edited tiles, multiscale levels, and all required multi-layer blend modes. Run unmodified napari image and label workflows with screenshots and transparent exports.

   **Acceptance:** every image fixture meets its fixed pixel tolerance; categories and edited regions match exactly; layer ordering and separate RGB/alpha blend factors reproduce the host's behavior.

10. **Complete markers, lines, shapes, meshes, and text.** Preserve upstream instanced marker hooks and lower admitted point sprites to quads without Python loops. Implement admitted line widths, joins, and caps, including the existing Agg path. Complete mesh shading, filters, clipping, layout, axes, colorbars, annotations, depth/stencil, camera behavior, and inventoried picking. Compare CPU SDF atlas texels and final text images using a licensed fixed font.

    **Acceptance:** scientific fixtures pass at the specified DPI values; camera motion keeps resident geometry; marker symbols, spherical depth, selection outlines, and picking match upstream. Host admission follows successful upstream runs of the same fixtures.

11. **Complete volume rendering.** Implement and validate all scalar and categorical modes listed in the design spec, ray and plane depiction, 3D interpolation, clipping, and depth against other geometry. Use the analytic sphere/ellipsoid fixtures and captured host shaders. Keep step size, sampling quality, thresholds, and accumulation behavior identical to the reference.

    **Acceptance:** each exposed and admitted mode has a valid actual render pipeline and a passing scientific image/depth fixture. Compilation alone does not establish volume correctness.

12. **Qualify operating systems, hosts, and wheels.** Add typed Linux X11 surface integration and macOS NSView/CAMetalLayer integration. Select Vulkan on Windows/Linux and Metal on macOS; keep the SPIR-V reader and validation enabled on every platform. Adapt submit instrumentation and native library discovery per platform.

    Create locked upstream and fork environments for napari, glue 1.4.0, DIVE, and selected plugins. Admit visbrain only after its hashed sdist fixture succeeds on upstream; retain phylib as an import inventory. Exercise PyQt5/PyQt6/PySide6 and the CPython 3.10-3.14 wheel matrix where each pinned host supports the interpreter. Add CPU/build CI, software Vulkan correctness CI, and hardware qualification jobs.

    **Acceptance:** actual Vulkan and Metal corpus pipelines, typed native surfaces, clean wheel consumers, host/plugin fixtures, and supported upstream tests pass on their designated environments. Missing hardware or an upstream-incompatible host is recorded as an unresolved admission, never converted to a passing skip. The current Windows machine supplies only its Windows Vulkan/PyQt6 qualification evidence.

13. **Measure performance and close v1 release gates.** Add shared upstream/candidate workloads under `benchmarks/` for 4096 images, one million points, and 256-cubed/512-cubed volumes, including resident interaction and data updates. Measure complete presented frames with format conversion and Y orientation included. Use separate processes on the same hardware/driver and preserve rendering quality. Collect timings without inserting completion waits into the sampled interactive path.

    Warm at least 100 frames, measure at least 1,000 frames, and run five alternating reference/candidate repetitions. Retain median, p95, variability, uploads, allocations, cache misses, queue depth, and application/Dawn/backend submit counts. The design spec requires reference median time divided by candidate median time of at least 1.20 on each primary resident workload, no worse p95, and no update regression above 10 percent.

    **Acceptance:** the full scientific and host matrix, platform lifecycle checks, packaging/rollback checks, and fixed-quality performance gates pass. Publish the supported capability matrix and reproducible evidence. Failure of a required scientific or performance gate keeps v1 incomplete.

Work can run in parallel after the internal interfaces are agreed. Assign file ownership as follows to avoid concurrent edits to the current monolithic runtime:

| Workstream | Owned files and responsibilities |
| --- | --- |
| Native integration | `cpp/runtime.*`, `cpp/bindings/module.cpp`, and extracted `cpp/device/` and `cpp/glir/` modules; error handling, submissions, resources, state, draw encoding, and recovery |
| Shader implementation | `cpp/shader/`; normalization, SPIR-V compilation, reflection, source maps, and uniform packing; coordinate interfaces with the native integrator |
| Reference and regression validation | `tools/`, `tests/reference/`, `tests/native/`, `tests/gloo/`, `tests/shaders/`, `tests/parity/`, and `tests/hosts/`; deterministic fixtures and independent oracle comparisons |
| Python and packaging integration | `src/vispy/gloo/dawn_parser.py`, targeted wrappers and Qt/headless backends, text helper integration, `CMakeLists.txt`, presets, `pyproject.toml`, lock files, and installation tests; coordinate shared build interfaces before changes |

All workers preserve other workers' changes. One native integrator owns `runtime.cpp` until extraction is complete. Resource lifetime and scheduler changes must integrate before asynchronous presentation; pipeline variants must integrate before completing draw/state support. Reference capture and regression authoring can proceed while those implementation changes are underway.

The review findings map to these steps:

| Review finding | Implementation step |
| --- | --- |
| Invalid pipeline success | 2 and 4 |
| Unsafe callback lifetime | 3 |
| Completed submission retention | 3 |
| GPU waits in interactive frames | 3 and 7 |
| Lost clear ordering and target | 5 |
| Ignored viewport/state | 5 |
| Ignored index selection/topology | 6 |
| Ignored vertex stride/offset/divisor | 4 and 6 |
| Partial texture replacement | 6 |
| Float texture clamping/quantization | 6 |
| Incorrect device limits | 2 |
| Broken resident program recovery | 4 and 7 |
| Incorrect matrix/array packing | 4 |
| Invalid boolean lowering | 4 |
| Missing independent screenshot oracle | 1 and 8 |
| Incorrect CPU SDF fallback | 8 |

After the environments and tests have been repaired, use an x64 Visual Studio developer shell for the Windows validation sequence:

```powershell
# Synchronize the revised lock and its explicit host qualification group first.
# The implementation must add that group before this command is made a gate.
uv sync --locked --python 3.12 --extra pyqt6 --group dev --group hosts
uv run --no-sync pytest tests/contract -q
uv run --no-sync pytest tests/native tests/shaders tests/gloo -q -m gpu
$env:QT_API = 'pyqt6'
uv run --no-sync pytest tests/qt -q -m gpu
uv build --wheel --out-dir dist
```

Independent oracle capture, delayed-completion tests, long resource-retirement stress, supported upstream CPU tests, clean wheel consumer tests, and host/performance qualification commands must be added as part of the relevant steps. Record each command and its evidence when the step closes; do not substitute the present smoke suite for those gates.
