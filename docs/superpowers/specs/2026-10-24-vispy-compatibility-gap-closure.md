# VisPy compatibility gap-closure specification

Date: 2026-10-24. Status: reviewed requirements for continued implementation;
requirements below are not claims that the implementation already satisfies them.
Target: the pinned VisPy 0.17.0 source/API, commit
`117b054598f4758b598f4b8f48feea48c11fe7b0`.

This is the current extension to the [original renderer design](2026-10-08-vispy-vulkan-design.md).
It governs the follow-up [execution plan](../plans/2026-10-24-vispy-compatibility-gaps.md).
The original ordered-renderer, source preservation and licensing contracts remain
in force. This document does not waive an existing mandatory application row.

## 1. Baseline and scope

The existing installed-artifact matrix has 13 of 14 selected mandatory rows
qualified. Windows napari-threedee startup is unresolved. That ratio describes
application configurations, not VisPy feature completeness. PR #13 merged the
earlier implementation; PR #14 introduces new source that needs its own checks.
Remote merge/CI state must be recorded at handoff rather than inferred from this
dated checkpoint.

The first follow-up packet implements Tk raster presentation and 29 selected
GL-shaped state entry points. Its initial local evidence comprised nine Tk integration cases
and three immediate-state cases on Windows Vulkan and WSL software Vulkan, plus
13 package/source contracts. These do not cover every entry point, Tk event-loop
mode, dependency closure or upstream visual. No new local native wheel was built.

Subsequent source checkpoints expanded the combined Windows suite to 86 passing
cases; the earlier 72-case Linux suite passed before the new capture workflows
exposed the two independent blockers described in section 10. The separate
headless scissor suite passes eight Windows cases and seven of eight Linux cases.
These are historical scoped observations, not a current-head CI result or a new
installed-wheel qualification. The execution plan retains the progression.

The goal is broader, measurable VisPy compatibility through the existing
gloo/GLIR boundary. Each supported public workflow must work end to end; importing
an API, recognizing a shader or returning a deliberate error is not completion.
Arbitrary OpenGL programs, native GL context interoperation and vendored VisPy
imports are separate contracts. EGL/OSMesa names must not silently be repurposed
to different semantics. Geometry-stage replacements require explicit design.

## 2. Evidence and promotion rules

| ID | Required contract | Acceptance evidence |
| --- | --- | --- |
| EV-1 | Separate source implementation, source functional tests, installed-wheel functional tests and qualified shipping status. | A feature has one explicit state and evidence/source/artifact identifiers. No promotion from an import, source test or old wheel receipt. |
| EV-2 | Bind installed results to exact artifacts and environments. | Source commit, dirty patch if any, wheel SHA-256, tested Python/native member hashes, interpreter tag, dependency/profile lock hashes, OS and adapter/ICD; real exits and child waits. |
| EV-3 | Require all three existing no-OpenGL gates for a new strict shipping profile. | Installed dependency closure, startup/transient load observation and execution/API observation, with the existing independent controls. Source import assertions or final loaded-module snapshots alone are insufficient. |
| EV-4 | Match the scope of the claim to the executed test. | Exact categorical pixels; independently authored numerical/edge tolerances where justified. Record changed pixels and exclusions. Do not weaken thresholds after observing a failure or claim full-frame parity from landmarks. |
| EV-5 | Preserve distinct platform scopes. | Windows GPU, WSL software Vulkan, native Linux GPU and Metal have separate records. Software results, CPU-only contracts and successful compilation cannot qualify hardware rendering. |

A proposed feature state is one of `not-inventoried`, `unsupported`,
`implemented-untested`, `source-tested`, `wheel-tested`, `qualified`, or
`blocked-external`. Every positive state names its tested profile. An issue may
add a blocker/reason without hiding the previous result or failure. A supported
subset must state its excluded inputs; the word "supported" without a scope is
not sufficient.

## 3. Upstream inventory contract

INV-1: Generate the inventory from the pinned source tree, then review public API
families, exported visual classes, backend registry, representative examples,
shader hooks, scene composition, events and admitted host workflows. Reuse the
existing feature/reference inventories before adding another list. Record the
source path/class or workflow, fixture mapping and exact unsupported operation.
Do not declare unexecuted examples successful because their Python files ship.

INV-2: Each inventory row must contain a stable feature ID, upstream source pin,
public entry point, required backend/native/shader capabilities, selected fixture
and expected result, state/profile, evidence references and next action/owner.
Record source-only, installed and hardware evidence separately. A denominator
or feature-completeness percentage is forbidden until the inventory is finite
and reviewed; the host matrix remains a different denominator.

INV-3: Cover images/labels/volumes; markers/points; lines/arrows/tracks; meshes and
filters; text; transforms/cameras; ViewBox/Grid/clipping; framebuffer capture;
partial updates; indexed/instanced inputs; custom Function/FunctionChain and
shader interfaces. For each family select an ordinary workflow and an important
mutation or failure/recovery case. Extend coverage based on actual failures and
use, rather than exhaustively reproducing every driver rasterization detail.

## 4. Tk backend contract

Implementation entry points: `src/vispy/app/backends/_dawn_tk.py`, backend
registration, runtime manifest and `tests/native/test_tkinter_backend.py`.
Rendering remains Vulkan offscreen plus Tk raster presentation. It creates no
GL context and imports neither pyopengltk nor PyOpenGL.

### Ownership, event loops and errors

TK-1: Define distinct ownership for the application-created hidden root,
application-created Toplevel, an externally owned root/parent, Tk image, native
canvas and each scheduled callback. Closing a canvas destroys its native target
and owned widget/window once. It must not destroy a supplied parent/root or stop
unrelated Tk work. External widget destruction must release the native target.
Failed construction must unwind all allocations made before the failure,
including failures before native registration, during initialization callbacks
and during first presentation. Release/recreation of the root must be tested.

Derive embedding ownership from the supplied parent's Tcl interpreter. Test
`tk.NoDefaultRoot()` with an explicit parent: the current direct private
`tk._default_root` access fails when that attribute has been removed. Multiple
VisPy Application objects may share one interpreter, so one application's quit
must not destroy another application's live canvas or externally owned work.
Do not equate "created this root" with permission to destroy all its consumers.

TK-2: Exercise manual `process_events()`, `Application.run()` and externally
owned `root.mainloop()`. Native progress, readiness retry and timers must work in
each mode, including idle periods and device recovery. Manual pumping must return
under a self-updating animation; one stalled callback is not made interruptible
by a loop-level time budget. Redraw requests coalesce, a request during drawing
is retained, and pending jobs are cancelled when their target closes.

TK-3: Use one documented policy for errors in drawing, native progress/readiness,
resize, input, timers, image creation and presentation. Preserve the first
failure and relevant traceback; never replace it with a later cleanup failure.
Manual pumping must surface pending failures. An application-owned run loop must
exit and surface a failure through its documented caller-visible route. For an
externally driven mainloop, deliver failures to the user's Tk error-reporting
route or a documented VisPy route without globally replacing the user's handler.
No silent failure, endless retry or repeated exception dialog is acceptable.
KeyboardInterrupt/SystemExit must not become ordinary swallowed drawing errors.
Honor the existing EventEmitter callback-error policy when deciding whether an
application callback propagates; adapting loop delivery must not silently
override a caller's configured policy.

TK-4: After a recoverable application callback fails, a different healthy canvas
must remain usable; after correction, an explicit redraw may recover the failed
canvas. Timer callbacks that stop or restart their timer must not leave a second
scheduled generation. Define quit semantics separately for the currently driven
run loop and root ownership. Test zero-interval timers and user-owned roots.

Stopping through application quit must also make public `Timer.running` false;
cancelling only its backend job leaves an inconsistent public object. Test
restart after quit/root recreation and ensure no timer retains a dead root.

### Coordinates, input and presentation

TK-5: State the relationship between requested canvas size, actual Tk client
pixels, physical framebuffer size, input coordinates and DPI. Respect window
manager minimum sizes and embedded geometry managers. Ignore zero-sized/minimized
targets without invalid native allocation, then recover on a positive configure.
Verify resize coalescing, hide/show, minimize/restore and repeated resize/close.
Exercise fractional/integer scale settings without changing global OS settings;
synthetic scaling tests must not be called mixed-monitor hardware qualification.

TK-6: Verify press/release/drag, simultaneous buttons, double-click behavior,
wheel direction/magnitude, modifiers, printable/navigation/function keys, focus
transfer and separate-window routing. Linux button-4/5 wheel handling and Windows
MouseWheel handling need distinct controls. Parent applications retain their
own bindings and layout. Unsupported capabilities, such as monitor-index
fullscreen or compositor transparency, must be implemented or explicitly refused.

At the Astra review checkpoint the adapter omitted the pressed `buttons` list
expected by VisPy camera handlers. Follow-up source changes repair that defect;
the execution plan records the evidence and remaining input acceptance. Track
pressed buttons through press/move/release, including
release outside the widget and focus loss. Require real SceneCanvas PanZoom and
3D camera drags that change camera state and rendered output; synthetic event
emission without a camera response cannot close this requirement. Include META
alongside SHIFT/CONTROL/ALT in the platform-specific modifier policy.

TK-7: Tk owns displayed RGB pixels independently of native readback storage.
Replacing an image releases the prior image, and closing releases all images.
Use asymmetric fixtures to verify top/bottom orientation, width/height, color
channels, odd row sizes and multiple canvases. RGBA capture retains renderer
alpha even though the displayed Tk image is opaque. An application's selected
viewport/scissor must not accidentally crop the presented full client frame.
Specify whether embedded capture includes surrounding widgets; it must not
silently include unrelated parent content.

Expected corner pixels must be authored independently of the candidate's own
`gloo.read_pixels` result; comparing two paths with the same flip does not prove
orientation. Preserve the same known-corner expectations after resize and device
loss. Test alpha below one and cropped/floating framebuffer capture separately
from opaque display, and exercise the coordinate policy at 125/150/200% scaling.

TK-8: GPU loss recreates rendering state while keeping the Tk widget usable.
Test loss before the first frame, while a frame is pending and after resize.
Close/readiness/loss races must not present into a destroyed widget. Observe
native shutdown and Tk image/job ownership separately; zero GPU counters alone
do not prove that Tk objects or Tcl callbacks were released.

Before qualification, add tests missing from the current nine-case suite. The
observed Windows Tcl/pytest descriptor-capture interaction is an environment
limitation; preserve its failure and use `-s` for current integration runs.
Do not present a successful retry or capture-mode change as a lifecycle fix.

## 5. Immediate state and query compatibility

STATE-1: Maintain an explicit operation/value contract alongside
`src/vispy/gloo/gl/dawn.py`. The current allowlist routes state through ordered
GLIR; it is not an OpenGL object namespace. Enumerate accepted enums, argument
counts/types, native limitations and behavior without a current/live canvas.
Unsupported calls and values fail contextually; no silent fallback or no-op.

Distinguish invalid input from legal upstream input that is not implemented.
For example, enabling GL_DITHER retains a native refusal despite its function
name being allowlisted. Reversed depth ranges now have the L1 source checkpoint
below and still await independent review and installed qualification. Give such legal
exclusions inventory rows and future acceptance criteria; do not label them
invalid arguments or treat the whole operation as fully compatible.

STATE-2: Earlier queued uploads/draws and framebuffer binding changes execute
before an immediate state command. State remains isolated to the selected canvas
and correct framebuffer scope. Query/cache values agree with successfully
executed native state. Invalid values do not partially mutate that state/cache;
the fate of earlier successfully executed queued work is documented separately
from rollback. Test nested FBOs, A/B/A canvas selection and state after errors.

STATE-3: The initial three pixel cases established selected clear/scissor/mask
and ordering behavior; later source checkpoints expand that evidence. Retain
coverage by state family for depth, blending, front/back
stencil, culling, line/sample state and limits, with real rendering where the
state affects output. Test integer enum inputs and negative/invalid values.
Reuse native state tests but verify the new Python entry route reaches them.

STATE-4: `glFinish` submits relevant preceding work and waits for the promised
completion. Both flush routes require a real submit-without-completion-wait
path; a candidate implementing it is described below. Logging/parsing a GLIR
`glFlush`, substituting `glFinish`, or presenting a window does not implement that contract. The new
path must retain submitted resource owners through completion and work for
offscreen/FBO targets, multiple canvases, repeated/empty flushes, loss and close.
Verify submission/progress and ordering with native counters/control work;
wall-clock latency alone cannot establish absence of a GPU wait.

This requirement covers both immediate `gloo.gl.glFlush()` and the existing
public `gloo.flush()`/context flush wrapper. At the first review both reached or
refused the logging-only operation. New matching native candidates implement
actual submission; changing documentation alone would not fix that behavior.
Test submission before any readback,
present or `glFinish` can mask the problem, and verify `finish_calls` does not
increase. Both routes must use the same native submission/lifetime contract.

The source implementation uses submission contract version 1 and a bounded
in-flight ring. It accepts empty no-ops, submits nonempty accepted work and
raises explicit capacity/resource backpressure if work remains unsubmitted.
Pending/queued owners survive that failure for progress and retry; a failed call
is never promoted as successful flush. GPU-completion delivery can be held by
diagnostic controls to prove saturation. Both finish APIs and native readback
complete without requesting presentation; explicit later presentation remains
required. This is candidate behavior, not an installed-profile admission or an
unlimited-queue guarantee. Remaining state-family and qualification gates apply.

STATE-5: Queries report actual dimensions, formats and granted limits in the
correct units and active target scope. Do not infer aggregate sampler budgets
from a single-stage limit or invent precision. Preserve synchronous exceptions;
`glGetError() == GL_NO_ERROR` is not evidence that arbitrary GL semantics work.
Raw object creation, raw shader/program APIs and raw drawing need a separate
inventory/design before expanding their surface.

The [operation/value and query records](../../immediate-state-compatibility.md)
now enumerate the 30 entry routes and their known legal exclusions. A source
follow-up adds 74 cases (77 immediate cases total), rejects polygon-offset
float overflow before committing state, requires integer query selectors and
refuses target queries on closed canvases. Matching native candidates pass
286 Windows/272 WSL affected source regressions, with 19 CPU/package contracts,
a passing Windows C++ state contract and nine zero shutdown gauges per profile.
These results do not implement every legal input, qualify the experimental
Linux SDK provenance, or replace installed-wheel/profile and observer acceptance.

## 6. Shader extension contracts

Keep compiler-backed GLSL/SPIR-V/Tint validation and existing refusal diagnostics.
For each packet retain an upstream source fixture, shader inputs, reflected
resources, selected lowering and exact compiler/backend versions. Reject an
unsupported interface before submitting a partially valid pipeline.

| ID | Packet and design obligations | Required tests |
| --- | --- | --- |
| SH-1 | Dynamic sampler-array indices: decide supported sampler families, array lengths and index uniformity. A binding/switch lowering must preserve sampling/derivative semantics; divergent implicit derivatives cannot be treated as uniform. Define out-of-range behavior from the pinned API rather than indexing host memory. | Constant and runtime indices; stage-uniform and divergent cases; integer/float sampler distinctions; array/resource limits, rebinding, filtering/LOD and source diagnostics. Native compile/validation plus actual GPU outputs on each claimed profile. |
| SH-2 | Multidimensional arrays: design type/reflection and layout handling for each supported storage/interface class; flattening must preserve element order, indexing, uploads and cache identity. | At least 2D indexing, partial uniform update, nested access, mixed dimensions, invalid shapes and translated reflection. Do not generalize a uniform-only implementation to buffers/attributes. |
| SH-3 | Matrix/array vertex attributes: define location expansion, column order, stride/offset, divisors, constants versus buffer inputs and granted input limits. | Interleaved and separate buffers; instancing; partial updates; limit/overflow refusals; rendered transforms and exact reflection. Account for expanded locations in native limits and pipeline keys. |
| SH-4 | Geometry-stage consumers: inventory the actual visual/filter and decide compute/instanced expansion or a documented application rewrite. Preserve topology, interpolation/provoking rules, clipping, depth and observable side effects for that subset. | Independent geometry/output fixtures, degenerate/clipped cases, dispatch-to-draw ownership and mutation/loss behavior. Unsupported arbitrary geometry programs remain explicit; no general geometry-shader translation claim. |
| SH-5 | Generated-line evaluators: inventory the guarded external storage/builtin, early_fragment_tests, image/atomic/barrier and external-write cases. Define coverage/depth/order and execution-count semantics before moving shader work into an expansion pass. | Independent output and side-effect counts for covered/clipped/degenerate inputs, early/late depth, atomic/storage visibility and dispatch-to-draw order. Preserve current refusals until that subset has actual native/GPU proof. |

Start with a feasibility spike that has a small retained decision record and
stop before a full rebuild if the pinned compiler/device cannot express the
contract. Never remove a refusal merely because a shader compiles. Requalify
affected workloads against the changed native artifact; prior receipts remain
historical.

## 7. Additional backends and hosts

BACKEND-1: Admit one backend at a time after inventory identifies a required
workflow. For GLFW/SDL2/pyglet/wx, select no-GL window creation and presentation
before enabling its registry entry. Native Vulkan WSI is outside the strict
Windows profile until its previously observed driver GL load/lookup is resolved;
copying Qt's raster presentation concept does not establish another toolkit's
native behavior. Pure Wayland, old Qt and browser/notebook paths need independent
scope decisions and evidence. Preserve original excluded source as reference.

BACKEND-2: Reuse the Tk/Qt lifecycle, ownership, resize/DPI, input, capture,
completion and failure requirements for each admitted backend. Specify which
embedding/capture/fullscreen capabilities are supported. Do not replace a missing
backend with headless output while reporting a displayed result.

HOST-1: Diagnose Windows threedee in the current pinned environment. Separate the
observer/debugger from the application and capture the actual stalled OLE/RPC
thread and wait chain. Compare a minimal upstream/stock Qt control and the Vulkan
profile with one variable changed. Retain timeouts and failed trials. A bounded
initial budget is three diagnostic starts plus one targeted confirmation; extend
only when new evidence supports a specific next experiment. Repeated successes
without a mechanism leave the row unresolved.

Before each trial record its watchdog deadline, stack-capture grace and log cap.
Reuse the pinned fixture deadline; if none exists, use a 120-second diagnostic
startup deadline, 20-second capture grace and 32 MiB text-log cap. These diagnostic
defaults do not change release qualification deadlines. On timeout, capture the
owned stalled process/thread evidence, terminate only the owned process tree and
wait for its actual exit. Preserve timeout stacks, command/source/environment
identity and a minimal reproducer before cleanup. If no stall is reproduced in
the bounded packet, write a terminal unresolved report and the next concrete
evidence request; do not enter an indefinite retry loop.

HOST-2: A fix needs a reproducer/causal explanation, an affected-workflow
regression, successful startup/render/update/input/capture/recovery/close against
the final artifact, and the existing absence gates. Do not disable drag/drop,
plugins, input hooks or observers merely to bypass the startup requirement.
Additional host versions receive separate pins and real workflow admission;
unrelated host/plugin dependency compatibility is not inferred from VisPy imports.

## 8. Artifact, CI and platform acceptance

ART-1: Preserve distribution/import identity, exact wheel contents, native
dependency closure and ABI/platform tags. New backend Python files appear in the
runtime manifest; excluded legacy loaders remain excluded. A clean isolated
consumer must resolve imports to its installed wheel, not a checkout or producer
directory. Verify native and relevant Python bytes against the supplied wheel.

Promotion must reuse the existing exact installed-distribution/member auditor,
including the declared runtime manifest and native/profile closure. The new
state smoke's selected member hashes are supplemental and cannot replace that audit.

ART-2: The immediate-state wheel smoke in Linux CI checks a bounded 96-pixel
result and nine native shutdown gauges. It does not cover the complete state
allowlist, Tk, the complete installed Python distribution or all absence gates.
Add the Tk installed/profile fixture with a real display and system toolkit pins
before qualifying it; never substitute a skipped display case for a green gate.
Required CI names/gates remain intact. A doc-only review needs link/schema checks,
not another local native wheel or environment.

HW-1: Windows GPU and WSL software results remain separate. Native Linux needs a
GPU/driver/display record; Metal requires a Mac and its toolchain/runtime. With
no suitable machine, record `blocked-external` and the exact missing resource,
not a fake pass. Hardware absence does not block independent software packets.

PERF-1: Measure a small fixed workload set after correctness: image/volume
updates, points/lines and interactive view changes. Report warmup, repeats,
adapter, CPU preparation, upload, GPU timing where supported, readback and
presentation separately; report median/tail and variability. Changes that add
per-call command flushing or full-frame CPU copies need an explicit cost note.
Use the existing benchmark protocol and upstream oracle where available. No
performance-parity or speedup claim follows from functional test counts. The
user has deferred extreme pixel/scanout parity; no photodiode/LDAT work is needed.

## 9. Storage, licenses and definition of done

RET-1: Follow root `AGENTS.md`, `docs/build-hygiene.md` and versioned
`compat/build-hygiene.json`. One coordinator shares the 20 GiB scratch budget and
10 GiB reserve across agents; WSL builds also check their Windows backing volume.
Reuse matched artifacts, SDKs and environments. Register unique scratch before
new allocation; preserve sources/licenses, small results and failure reproducers
outside scratch, wait for owned children and apply the unchanged cleanup plan.
No recursive capture of old build histories. Preserve pinned origins and never
retry rejected cleanup targets through another path or shell.

LIC-1: Implementation remains AGPL-3.0-only, with original BSD and third-party
licenses/notices attached. Preserve preferred source and exact patches/recipes
for shipped custom native/toolkit components. Documentation changes do not
justify repacking existing large release archives; use a small source addendum
when appropriate and keep its artifact scope explicit.

A packet is done when its requirement IDs, scoped acceptance evidence, source
changes, review outcome, outstanding restrictions and terminal cleanup receipt
are linked. It is not automatically a shipping qualification. Full gap closure
requires every required inventory row to meet its scoped functional and
same-artifact qualification gates. Unsupported, failed, pending, untested and
blocked required rows keep full closure incomplete even when their reasons are
well explained. The matching qualified artifacts must be retained.
Merging code or preparing a draft release must not
silently change that definition or erase the unresolved mandatory host row.

## 10. Executable acceptance records

This section refines the existing requirement IDs. It does not introduce a new
completion denominator or promote any current implementation.

### Inventory and evidence records (INV-1..3, EV-1..5)

The G0 deliverable must select and name its canonical machine-readable ledger.
The selected draft is `compat/vispy-compatibility.json`, with schema and validator
described in the [inventory guide](../../compatibility-inventory.md). Its generated
seed is unreviewed; selection and structural validation alone do not close G0.
Reconcile `compat/upstream_manifest.json`, `compat/no-opengl-matrix.json`,
`tests/reference/inventory.json` and host inventories before adding rows; they
describe different scopes and must not be merged by counting their entries.
Link them by stable identifiers rather than copying their evidence payloads.

Each feature/profile row must record:

- Stable feature ID and requirement IDs; pinned upstream source path and public
  entry point; whether the workflow is required or an explicitly excluded
  interoperation contract, with the exclusion rationale.
- Ordinary and mutation/failure test node IDs, expected observable behavior,
  required native/shader/backend capabilities and dependencies on other rows.
- Platform/profile ID, implementation state, latest attempt outcome, source
  commit/dirty-patch hash, artifact identity when tested, evidence references,
  open failure/blocker, owner and next bounded action.

A new failed attempt must remain visible alongside any historical pass. A row
cannot retain an unqualified current-success claim after a relevant failure or
source/artifact/profile change. Historical receipts remain valid only for their
recorded scope. Missing receipts, skipped selected cases, unexpected collection
counts or unawaited child processes fail the packet gate.

### Flush submission proof (STATE-2,4, G1d)

Before implementation, record the flush linearization point: which preceding
GLIR operations and active target are included, and when native ownership moves
from queued to submitted work. Define behavior when the in-flight ticket budget
is exhausted. A queue-full path must not silently leave the promised work
unsubmitted or fall back to a completion wait. If the supported bounded policy
cannot meet that contract, retain the explicit unsupported status until the
design is resolved. Document how an application observes submission failures.

The acceptance table must exercise both public routes independently and together:
empty/repeated flush, offscreen target, nested FBO selection, A/B/A canvases,
upload/draw followed by resource mutation/deletion, full in-flight budget,
device loss before/after submission and close with submitted work. Take native
counter snapshots before any readback, presentation or finish. Observe an actual
submission and unchanged completion-wait/finish counters at that point; use a
later explicit synchronization only to validate output and retirement. Retain
counter definitions and a negative control that detects the logging-only route.
An asynchronous submission need not have completed when flush returns.

Empty or repeated flushes with no new work may be genuine no-ops; they must not
be required to increment submission counters. Prove the saturated case using
controlled incomplete tickets and a recorded precondition, not a fast loop that
may finish between calls. Distinguish successful submission, permitted empty
no-op and documented failure in the expected result for every case.

Treat queue submission as an irreversible ownership boundary. If later
bookkeeping, readback mapping or completion-callback registration fails, keep
submitted owners alive until completion or a documented device-loss retirement
path. Inject failures on both sides of that boundary; verify no duplicate GPU
submission, early release, lost ticket or permanently leaked owner. A retry must
not replay work whose submission already succeeded.

### Tk root adoption and unrelated work (TK-1..4)

An empty `winfo_children()` result does not prove exclusive ownership of a Tcl
interpreter. A root can still own user `after`/`after_idle` jobs, variable traces,
bindings and commands. Before changing teardown, record the policy for a root
created by VisPy that is subsequently exposed to or adopted by the host. Define
the ownership transition and permitted explicit shutdown action; inference from
child widgets alone is insufficient. Preserve unrelated user work when a canvas
closes or an application releases its share of an adopted interpreter.

Acceptance includes an exposed application-created root with no child widgets
but an unrelated timer, idle callback and root binding. Close/quit the VisPy
consumer, then demonstrate the documented survival or explicit host-owned
shutdown behavior. Also exercise two applications sharing the interpreter,
external parent destruction and a failed release followed by explicit retry.
Assert widget, image, Tcl job and native ownership independently; zero native
resource counters do not establish interpreter cleanup.

Current source policy: an explicit `parent` declares host ownership of its Tcl
interpreter, including a root created earlier by VisPy; this declaration applies
to all applications sharing that root. Without an explicit parent, final release
preserves a root with remaining unrelated widgets, after jobs, instance bindings
or Tcl commands added since interpreter attachment, including child namespaces
and variable-trace callbacks. VisPy-owned image commands are tracked weakly and
excluded from that adoption decision, so a retained old image wrapper cannot
prevent exclusive-root destruction. Reading `Application.native` alone is not
an adoption declaration. Opaque Tcl state must use the explicit-parent contract.

The host explicitly destroys an adopted root after its work is done. VisPy quit
must not drain host idle callbacks to decide whether to destroy it. An ownership
query failure retains the application/interpreter association for explicit retry;
it must not falsely report release. Test re-entry on an adopted root and shared
applications' final release, as well as the individual host resource kinds.

### Coordinate and input policy record (TK-5..7)

Before G1c closes, retain a per-platform policy table naming units and conversion
for requested size, actual client size, public `Canvas.size`, `physical_size`,
resize-event fields, mouse positions, native allocation and capture rectangles.
State the rounding rule and behavior at zero size. If Tk client coordinates and
framebuffer pixels intentionally have a 1:1 mapping, document why the selected
profile guarantees it; changing `tk scaling` alone does not prove a physical
monitor transition. Record requested versus actual scale in each fixture.

Input acceptance must specify platform modifier masks including META, button
number mapping, press/release ordering, wheel units, printable text versus key
identity and double-click delivery. Fixtures compare the emitted sequence with
the pinned upstream public event contract and verify a real camera response.
For explicit-parent embedding, verify that user bindings still fire once and
that two canvases route input independently. Unsupported platform capabilities
remain explicit inventory gaps until implemented and tested.

### Linux blocker separation (TK-7,8, STATE-3, ART-1,2)

The current Linux failures require separate rows and reproducers:

| Blocker | Isolation evidence | Acceptance before affected profile promotion |
| --- | --- | --- |
| Tk Xlib/XCB abort | A plain Tk Label/window lifecycle without VisPy or Vulkan also aborts in the current managed-Python runtime. | Pin the selected Python, Tcl/Tk, display and runtime-library closure; run the plain toolkit control and actual VisPy embedding/lifecycle suite in that same profile. A replacement runtime is a new profile and needs its own receipts. |
| Multisample scissor boundary | Headless clear and ordinary draw reproduce the error without Tk; direct creation at the failing size also fails. Shader-discard control passes but does not establish a safe replacement. | Preserve exact independently authored boundary expectations. Run zero/nonzero origins, samples 0/4, both 257x129 and 301x177, direct creation and resize, plus ordinary draw as well as clear. Record actual driver/ICD identity and compare only one intended variable per diagnostic trial. |

`tests/native/test_scissor_boundaries.py` is the initial eight-case clear
regression, not the entire expanded acceptance table. Preserve the failing
driver receipts. A driver release note is a hypothesis, not causal proof or a
qualified repair. Driver/runtime changes require closure and absence gates for
the changed profile. Shader-based workarounds additionally require review of
depth/stencil, sample coverage, early tests and user-visible shader side effects
under SH-5; passing the boundary fixture alone cannot justify them.

### Packet handoff and promotion (ART-1,2, RET-1)

Every packet report names the source/artifact/profile tuple, selected requirement
IDs and tests, collected/pass/fail/skip counts, actual child exit/wait, unresolved
restrictions, retained evidence hashes and terminal cleanup receipt. The G2
report maps every selected workflow to the exact installed wheel and separately
lists dependency, startup/transient-load and execution/API observer outcomes
with their controls. Never combine those gates into an unexplained green label.
An environment repair or source-only pass permits the next scoped experiment;
it does not qualify another profile or replace final installed-artifact proof.

### Additional Astra review gates

The [second Astra max review](../reviews/2026-10-24-astra-acceptance-detail-review.md)
adds these concrete refinements to the preceding acceptance records:

- **INV-1/2, EV-1/2:** G0 supplies a versioned schema and validator for its selected
  ledger. Reject duplicate feature/profile keys, unknown requirement IDs,
  dangling capability/dependency/fixture references, missing required acceptance
  mappings and qualified rows backed only by source or stale artifact receipts.
  Required capabilities and workflow acceptance must match the same claimed
  profile/artifact; exclusions cannot silently drop previously required work.
- **STATE-4:** Public `gloo.finish()`/`gloo.gl.glFinish()` and both flush routes
  must not request a swap/window presentation, emit another GUI draw or change
  selected canvas, FBO, viewport or scissor. Assert `application_presents` and
  GUI-draw observations separately from submission/completion. For nonempty
  flush, assert unchanged `completion_waits` as well as `finish_calls` before
  any synchronizing observation. Explicit later presentation must show the
  correct completed frame. The raw finish route's former presentation request
  has source-functional regression evidence in the native submission checkpoint;
  exact installed-artifact qualification and independent review remain open.
- **TK-5/7, STATE-5:** For default `Canvas(px_scale=1)` Tk raster presentation,
  the last positive Configure client dimensions determine both public size and
  physical size; backend scale is 1 and pointer coordinates remain widget-local
  Tk pixels. Requested geometry is provisional until Tk acknowledges it. Local
  toolkit scaling must not independently multiply the native allocation. Zero
  Configure sizes retain the last valid allocation until a positive resize.
  Full-frame raster output has top-left row order; framebuffer crop rectangles
  use the documented lower-left origin. Preserve the separate existing public
  `px_scale` option: `Canvas.size` divides backend dimensions by that integer,
  so do not generalize default-size equality to every Canvas configuration.
  Add an explicit nondefault-px_scale fixture and camera/input mapping check.
- **STATE-3/5, TK-7/8, ART-2:** Boundary receipts name requested and granted sample
  counts, actual adapter/ICD and loaded driver-library identity. A four-sample
  acceptance case fails when four samples were not actually granted; silent
  single-sample fallback cannot close the scissor row. Before toolkit control
  execution, declare a finite fresh-process create/pump/destroy trial budget
  and deadlines, retaining every exit including abnormal termination. Plain Tk
  and VisPy controls must use the same pinned runtime/display closure. A passing
  replacement profile does not identify the old failure's cause.

## 11. Implementation-ready contract details

The records below refine existing requirement IDs. They are required planning
outputs for the affected packet, not statements that the current fixtures or
validator already enforce every rule. Keep them linked from the canonical
ledger; do not create a second feature denominator.

### Tk input acceptance vectors (TK-6)

Before editing input dispatch, record expected public events for each sequence
below, including `pos`, `button`, `buttons`, `modifiers`, `key`, `text` and native
event provenance where applicable. Derive expectations from the pinned public
event contract, not from the adapter's current output.

| Sequence | Required observation |
| --- | --- |
| Press left, press right, move, release left, move, release right | Correct VisPy button mapping, ordered transitions and current held-button sets; drag linkage remains valid until its initiating press is released. |
| Release outside the widget, then lose focus | No stuck drag. Document cancellation events; clear held state and click history so a later focus session cannot inherit a phantom double-click. |
| Two clicks, then a different button/position or a delayed click | Document the selected native or fallback double-click policy and threshold. An accepted double-click retains the triggering position/button/modifiers and does not suppress ordinary press/release delivery or emit duplicates. Test threshold boundaries deterministically. |
| Left/right variants of SHIFT, CONTROL, ALT and META | Name platform masks and key aliases, key-press/release transition semantics, and behavior when one of two held modifier keys is released. Focus loss clears tracked state. A platform/layout not observed remains unqualified. |
| Printable, shifted printable, Unicode, navigation, keypad and function keys | Separate logical key identity from text. List admitted aliases/function-key range and unknown-key behavior; do not turn control characters into printable text. |
| Windows fractional/negative wheel delta; Linux button 4/5 | Declare wheel units and direction. A wheel action cannot create a held mouse button; physical extra buttons on another platform cannot silently become wheel actions. |
| Two canvases and an embedded canvas with host bindings | Only the intended canvas receives the action; unrelated host bindings run once and survive canvas closure. Include an actual camera response, not only emitted-event assertions. |

Synthetic Tk events prove adapter translation, not keyboard layout, compositor
delivery or physical device behavior. Record those evidence types separately.
No system-wide input injection or global keyboard/DPI changes are required.

Current source input policy and acceptance checkpoint:

| Profile | Modifier/wheel policy | Evidence boundary |
| --- | --- | --- |
| Windows Tk | SHIFT=1, CONTROL=4, floating ALT=0x20000, META=0x10000 plus tracked Win/Meta/Super key aliases. Mod1=8 is not Alt. MouseWheel delta/120 preserves fractional and negative ticks; extra physical buttons remain buttons. | Live widget event generation and synthetic modifier/key vectors on Windows Vulkan; physical keyboard/device delivery remains unqualified. |
| Linux Tk/X11 default layout | SHIFT=1, CONTROL=4, ALT includes Mod1=8, META includes Mod4=64, plus floating Alt/Meta bits and tracked aliases. Buttons 4/5 are vertical wheel ticks with no held-button mutation. | WSL software Vulkan source tests; remapped modifier layouts, native Linux GPU and the separate capture runtime remain unqualified. |
| macOS Tk | Proposed Command Mod1/Option Mod2 translation plus floating bits; native wheel units retained. | Synthetic translation vectors only; no Mac or hardware admission. |

The [Tk 8.6 Windows modifier implementation](https://raw.githubusercontent.com/tcltk/tk/core-8-6-14/win/tkWinPointer.c)
distinguishes NumLock/Mod1 from Alt; its
[key table](https://raw.githubusercontent.com/tcltk/tk/core-8-6-14/win/tkWinKey.c)
names Win_L/Win_R. These references inform adapter policy, not a claim that every
test environment has that exact toolkit patch release.

The source uses the pinned base double-click detector (same button and exact
position, consecutive press interval <=0.3 seconds), forwarding the triggering
event's metadata and retaining every ordinary press/release. Focus loss clears
the detector and cancels held gestures. Modifiers are updated before key delivery;
a release removes that logical modifier unless its other alias remains held,
even when native state describes the pre-release transition. Pointer/wheel events
combine native masks with tracked keys, including Windows META.

Named navigation/keypad aliases and F1–F12 emit public key identities; printable
characters (including Unicode and keypad digits) retain text separately. Control
characters and nonprinting special keys have empty text. A keycode's release
retains its press identity/text across changed or missing release symbols; focus
loss and close clear this cache. Unknown nonprinting symbols remain key=None with
native provenance rather than acquiring invented printable text.

Thirty new cases cover these vectors, double-click boundary/position/button
controls, real widget events and host/canvas routing. Focus-loss cancellation
finishes every held-button release and clears gesture state before delivering
the first callback failure; a regression proves the next move is not dragging.
Final affected suites pass 130 Windows and 116 WSL software cases with nine zero
shutdown gauges. Existing real PanZoom/Turntable drags remain in those suites. This advances TK-6 source
acceptance, not exact installed qualification or unsupported physical profiles.

### Backend capabilities and configuration (TK-1,5,6, BACKEND-2)

Before admission, retain a capability table for standalone and embedded modes.
List each advertised capability, constructor option and mutable property;
requested versus granted color/depth/stencil/sample configuration; ownership and
permitted UI thread; and the fixture proving observable behavior or contextual
refusal. Include size/position, title, visibility, decoration, resizability,
fullscreen, parenting, capture and context/resource sharing. Host-controlled
embedding behavior must be explicit rather than silently ignoring requests.

A sharing claim requires two canvases using shared resources, an update visible
to each according to the documented ordering, closure of one consumer without
invalidating the other, and final resource retirement. Do not infer sharing from
an advertised boolean. An accepted configuration request must name the actual
granted attachments/limits; unsupported requests cannot silently become another
configuration. Cross-thread use must have a documented supported route or a
clear refusal; no arbitrary cross-thread toolkit support is inferred.

### Immediate operation records (STATE-1..5)

For each allowlisted command and admitted query, retain a contract row with:
signature and accepted numeric types; legal enum/value subsets; default and
queried values; canvas/FBO scope; ordering relative to queued GLIR; success and
failure effects on native state and Python caches; and ordinary, boundary,
legal-but-unimplemented and invalid-input fixtures. Query rows additionally name
return type/shape, units, actual-versus-requested semantics and limit provenance.
An allowlist-name count is not a completed contract table.

Map at least viewport/scissor/clear/masks, depth, blend, front/back stencil,
culling/winding, line width, polygon offset, sample coverage and synchronization
to their actual output fixtures. Distinguish attachment/sample-format restrictions
from general API behavior. After a rejected operation, verify the last committed
state and a subsequent valid draw; document any preceding queued work that was
already committed. Do not promise whole-stream rollback unless implemented.

### Shader decision records (SH-1..5)

Before a native implementation, retain one small decision record per selected
subset: named upstream consumer; accepted and refused shader forms; original
shader and independently expected output; compiler/reflection representation;
chosen lowering; resource/limit accounting; update and pipeline-cache identity;
failure stage/diagnostic; and profile-specific acceptance fixtures.

| Packet | Additional decision required before removing a guard |
| --- | --- |
| SH-1 | Distinguish constant, dynamically uniform and divergent indexing. Specify implicit-derivative versus explicit-LOD behavior and binding expansion cost at the actual stage/combined limits. |
| SH-2 | Record dimension order, element/byte offsets, storage class and reflection/upload agreement for every admitted shape. Include an update that distinguishes swapped dimensions. |
| SH-3 | Record each expanded location and matrix column, byte stride/offset and divisor. Include a non-symmetric transform and multiple instances to expose transposition and divisor errors. |
| SH-4 | Name the actual geometry-stage consumer and its input/output topology. Document amplification limits, clipping/interpolation/provoking behavior and ownership between expansion and draw. |
| SH-5 | State which logical invocations perform external effects, and how clipping, coverage, depth/stencil and ordering affect those counts. A matching color image alone cannot prove side-effect equivalence. |

Every packet includes two independently varied resources or programs to detect
cache aliasing, an update after first use, close/loss with work outstanding, and
a contextual negative control. Compilation alone does not admit the subset.
Feasibility failure retains the guard and the next bounded design question.

### Change impact and evidence reuse (EV-1..5, ART-1..2)

Before G0 review closes, represent required applicability at the feature/profile
pair, with a rationale for each nonapplicable pair. A feature-wide `required`
flag and a global profile list do not establish this mapping. The original v1
ledger/validator required an explicit migration or equivalent validated mapping:
required applicable pairs block full closure unless qualified; optional pairs
do not block full closure merely because an experimental receipt exists.
Missing hardware makes an applicable required pair `blocked-external`, not
nonapplicable. Preserve existing required scope during migration and test all
three cases, including absence of a required pair, before marking G0 reviewed.

Source checkpoint: ledger v2 now declares all feature/profile applicability and
same-profile dependencies explicitly. Its validator distinguishes required,
optional and nonapplicable pairs, rejects missing decisions and scope/dependency
inconsistencies, and retains required blockers. The explicit non-overwriting v1
migration preserves rows/receipts and required scope while resetting review.
Sixty-eight CPU cases pass, including the original optional-profile regression.
All 142 seed pairs remain required/unreviewed; this closes the mapping defect at
source level, not G0 reconciliation or artifact qualification. Human review of
scope rationale and affected-profile application of the B1 workflow-bound gate
adapter remain necessary.

Each implementation packet lists affected feature/profile rows before testing.
Changes to lowering, bindings, layout, submission or resource lifetime include
their dependent consumers; toolkit/driver/runtime changes include that profile's
closure and observer gates. A narrowed rerun requires an explicit dependency
rationale, not an assumption that previous unrelated green totals transfer.

Retained native binaries may be reused for Python-only source tests after
verifying their hashes and native contract version. A shipping wheel containing
changed Python bytes is still a new exact artifact: audit its complete installed
members and run its selected functional and independent absence gates. Historical
receipts remain attached to their original identity. Reusing native inputs does
not permit relabeling an old wheel receipt with a new wheel hash.

Bind each normalized absence-gate record to the observed scenario/script hash,
arguments, covered feature/workflow IDs, observer/control identity and raw report
hashes, in addition to the existing artifact/profile identity. The validator and
receipt adapters must reject evidence for an unrelated workflow even when its
wheel/profile match. Gate/status/control/identity checks alone do not establish it.

Source checkpoint B1: qualified rows now require a workflow mapping. Controller
and worker record the actual script hash/arguments and coverage IDs; the worker
rejects a script changed during execution. The normalization adapter validates
the original discovery, inventory, dependency receipt, fresh replay and control
reports, including hash edges, collector identity, process completion, installed
members and shutdown. The ledger validator recomputes those records rather than
accepting unrelated or manually labelled green gates. Existing full auditors and
independent controls remain mandatory. See the [receipt protocol](../../compatibility-inventory.md#workflow-bound-qualification).

Selected CPU/protocol suites pass 141 cases on Windows and 141 on Linux, with
one existing symlink-venv regression explicitly deselected in both selections;
it is not counted as covered by this packet. An earlier broad Windows selection
failed the strict gate on that platform skip and is retained as a failed attempt.
The real bounded Tk/state script passes separately on both retained native
candidates with nine zero shutdown gauges. These source/adapter results do not
qualify an installed wheel, re-run native controls or close the complete G2 matrix.

Use the existing `tools/audit_no_opengl.py --scenario script` path for installed
Tk/state workflows. Preserve its discovery run, environment inventory and fresh
receipt-bound replay protocol described in [the observer guide](../../../tools/no_opengl/README.md).
A headless observation cannot qualify Tk presentation or input executed in a
separate unobserved process. Keep the three gate outcomes and their controls
independent; no new substitute auditor is authorized by this refinement.

Independent review has two checkpoints: source/fixture review before packaging
checks the actual patch, requirement-to-fixture mapping and retained failures;
promotion-evidence review after qualification checks the exact final artifacts,
installed-member/auditor/observer receipts, controls and required current-head CI.
Both checkpoints must pass before promotion. A source review cannot approve
receipts not yet produced, and a later evidence review does not replace patch
review. The plan review itself is neither implementation-review checkpoint. Record finding IDs,
dispositions and remaining restrictions; unresolved required findings prevent
promotion of their affected rows.

Dependencies are evaluated per claimed feature/profile, not as an all-platform
barrier. Shader feasibility and source work can start from a hash-identified
known baseline when their actual prerequisites hold, even while an unrelated
Linux Tk profile fails. G2 qualification for a particular affected workflow
still requires that workflow's G1 criteria and exact installed artifact. Such
independence neither qualifies the failing profile nor closes full scope.

## 12. Next-packet designs and exit checks

These designs refine STATE-1..5, INV-1..3 and BACKEND-2. Q1 queries, selected B4
capabilities and L1 reversed depth now have source checkpoints below; their
contracts are retained for independent review and installed qualification. Other
selected rows remain future work. The next implementation must reference its
selected rows in the existing ledger and operation table; the tables here are
acceptance instructions, not a replacement inventory or promotion mechanism.

### Mutable-state queries (STATE-2,5)

The first query packet covers the state already represented by the renderer:
blend enable/color, RGB and alpha factors/equations; depth enable, function,
write mask, range and clear value; front/back stencil comparisons, references,
read/write masks and operations; culling/winding; color clear/write masks;
viewport/scissor; line width/smoothing; polygon offset; multisample,
alpha-to-coverage and sample-coverage controls. Attachment/sample configuration
and device-limit queries retain their distinct provenance and target scope.
An unsupported state such as enabled dither does not acquire a fabricated query
value merely because its enum exists. Record exact admitted selectors before
coding; no arbitrary glGetParameter compatibility claim follows.

| Decision / invariant | Required implementation and acceptance |
| --- | --- |
| Authority | Read the selected native canvas's committed logical RenderState before draw/pipeline lowering, including values belonging to disabled features. Effective pipeline descriptors and the last draw are not API state: MIN/MAX lowering can replace factors, depth-test disable can suppress effective depth writes, and converted draws can collapse front/back stencil. A Python cache or separate state mirror cannot be the sole query source. Return newly committed state even before a draw. Attachment/configuration queries alone consult actual target configuration. |
| Native compatibility | Name an explicit state-query contract and check it together with the native entry point before draining queued work. An older retained module must fail contextually without consuming the queue. Submission contract version alone does not advertise the new query API. |
| Selector validation | Validate selector type and membership in the admitted selector table before draining queued GLIR. Malformed or unsupported selectors leave pending state/draw commands untouched. Test this separately from a valid query that encounters a queued execution failure. |
| Ordering | Execute preceding GLIR through the existing ordered route before reading state. Record the last successful command when a queued command fails; no stale-value success or whole-stream rollback claim. Queries must not replay failed or already submitted work. |
| Observation effects | Native state projection adds no queue submission, completion wait, readback, presentation, GUI draw or target allocation. Separately account for effects explicitly requested by preceding queued commands; their execution is not an observational side effect. Inspect counter deltas before a later readback can mask an accidental submit/wait. |
| Return conversion | Specify scalar versus tuple shape, integer versus floating return, enum identities, flag representation and precision per selector against the pinned upstream implementation. Resolve signed/high-bit stencil mask conversion explicitly, including 0xffffffff and 0x80000000; do not infer it from C++ storage type. |
| Rectangles | Resolve the native target-sized sentinel versus explicit rectangle distinction before implementation. State belongs to a canvas; FBO binding changes attachments and effective target extent. Specify what default viewport/scissor queries return on creation, resize and nested FBO changes, and prove agreement with the actual raster path. Never expose an internal negative-size sentinel as a valid public rectangle. |
| Target validity | No current Dawn canvas, a closed canvas, missing native owner and an unknown selector produce contextual synchronous failures. A failed close retaining a native ID does not make the public target live again. Do not manufacture a temporary canvas to answer a state query. |
| Lifetime | Preserve state isolation across A/B/A canvas selection and nested FBO entry/exit. Specify retained/reset state across device loss from the actual recovery contract; demonstrate a known subsequent draw. Querying or closing one target cannot mutate another's state. |

Extend the existing immediate-state/native and CPU contract suites. Include
pristine defaults before a VisPy preset; every admitted field after mutation;
independent front/back stencil values; depth write mask while depth testing is
disabled; nondefault stored blend factors under MIN/MAX equations; clamping and
float conversion boundaries;
rejected-operation state preservation; invalid/unsupported-selector queue
preservation versus valid-selector committed-prefix failure; queued versus
immediate ordering; live,
closed and absent targets; and the old-native guard. Separate a pure native
projection test from actual Python/native integration and output tests. Record
exact fixture node IDs before execution and selected/pass/fail/skip counts after.

A query packet is source-complete only when every selected selector has a
return/type/scope record, both public state-setting paths agree with native
queries, and no added synchronization occurs. It does not close legal setter
gaps, other selectors or exact-wheel G2 qualification. Update the existing
[query records](../../immediate-state-compatibility.md#query-records) with actual
implementation results rather than duplicating a second support table here.

### Remaining legal state values (STATE-1,3)

Each row below is a separate bounded design/output packet. A successful query
packet cannot close these setter/rasterization gaps. Preserve contextual guards
until the selected behavior and dependent pipeline/cache paths are tested.

| Gap | Decision required | Distinguishing output / negative control |
| --- | --- | --- |
| Reversed depth range — L1 source-tested | Retain the depth conversion decision and source checkpoint below; independent source review and exact installed qualification remain. | Overlapping primitives with reversed near/far ordering; equal/clamped endpoints; masks/comparisons; fragment depth/coordinates; indexed instancing; queued orientation changes and loss. |
| Dither enable | Identify the pinned observable contract and admitted attachment formats; determine whether native raster behavior or an explicit lowering satisfies it. | A gradient/quantization fixture for the selected format and an enable/disable control. A fixed arbitrary noise pattern or unexamined no-op is not proof. |
| Multisample disabled with multisample storage | Distinguish rasterization/sample shading semantics from attachment count and resolve behavior, coverage and depth/stencil interaction. | Assert actual four-sample storage, toggle enable state without reallocating the target, and compare edge/coverage and depth/stencil outcomes. Single-sample fallback is not acceptance. |
| Fractional/out-of-int32 polygon offset units | Define representable bias and depth-format dependence; assess native integer bias limits without silently rounding or saturating accepted public values. | Positive/negative fractional units, factor interactions and boundary values that produce independently predicted visibility; rejected values preserve prior state. |
| Mixed constant-color/constant-alpha blend domains | Determine a lowering preserving independent RGB/alpha factors and equations with correct resource/pipeline identity. | Unequal constant channels and alpha, unequal source/destination colors, separate equations, and constant changes after first use; avoid equal-channel fixtures that conceal substitution. |
| Remaining stencil/enum/format combinations | Inventory exact untested values and attachment restrictions before expanding a claim. | Saturating versus wrapping stencil operations, distinct faces/masks and affected attachment-format cases; distinguish invalid values from legal unsupported ones. |

If feasibility fails, retain the smallest counterexample and decision, keep the
row unsupported or blocked with its next action, and proceed with independent
packets. Do not promise a driver workaround or remove a guard on compilation
success alone. GPU output, failure recovery, mutation/cache identity and affected
profile reruns remain required by sections 5, 6 and 11.

### Concrete inventory and backend outputs (INV-1..3, TK-1,5,6, BACKEND-2)

For the next G0 pass, select actual Tk/state public entry points from the pinned
source and map existing fixture node IDs, including mutation and failure cases.
Do not directly replace required unassigned rows through the existing v2 schema:
it has no obligation-transfer contract, and current preservation tests forbid
that replacement. Implement and review the conservation mechanism in section 13
before changing those invariants. Preserve all seed scope and original receipts. Record unresolved method, example, event,
visual and host families separately; do not set global reviewed=true merely
because the selected Tk/state slice has been mapped.

A backend capability record has one row per option/property and mode, with:
public API; standalone or supplied-parent mode; requested value; actual granted
value; observable behavior or contextual refusal; owning interpreter/UI thread;
constructor, mutation and teardown fixture; and unresolved restrictions.

| Selected capability group | Minimum distinguishing cases |
| --- | --- |
| Geometry/window properties | Requested and Tk-acknowledged size/position; embedded geometry-manager authority; title/show/hide; decoration/resizability; fullscreen boolean and monitor-index requests. Check mutation as well as constructor handling. |
| Framebuffer configuration | Color/alpha, depth, stencil and samples requested versus actual attachment formats/counts. Unsupported precision or modes need an explicit refusal or documented native minimum/unknown precision; a constructor dictionary alone proves nothing. |
| Resource/context sharing | Two consumers of one resource, update visible under documented ordering, close either consumer first, survivor output and final retirement. Distinguish VisPy resource sharing from native OpenGL context interoperation. |
| Ownership/threading | Supplied parent/interpreter, application-created windows and shared roots; UI-thread supported route or deterministic refusal. Check that the capability test does not disturb host jobs/bindings. |

For this documentation packet, validate local links, requirement references and
plan/spec consistency. No new native build, dependency installation, wheel,
source snapshot or scratch allocation is needed. Implementation packets still
follow RET-1 and the unchanged managed cleanup policy.


## Native state-query source checkpoint (Q1, STATE-2/5)

Native state-query contract version 1 now projects 46 mutable-state selectors
from committed canvas RenderState before pipeline lowering. The existing viewport
route uses the same native projection; SAMPLE_BUFFERS uses actual target sample
configuration. Flags/enums/masks are integers, floating selectors use the pinned
GLfloat conversion and high stencil-mask bits retain signed 32-bit patterns.
Python rejects malformed/unsupported selectors and mismatched native contracts
before consuming queued GLIR. A valid query executes the ordered prefix and
propagates native failure; committed work is not rolled back or replayed.

Default viewport/scissor extents follow the selected target until explicitly set;
explicit rectangles survive target switches and resize. A baseline GPU regression
exposed an enabled-default-scissor clear that discarded every pixel; rasterization
now resolves that internal sentinel to the same full-target extent as the query.
A first broader run caught a changed missing-canvas diagnostic; the candidate
preserves the existing diagnostic contract rather than weakening its regression.

Thirty-seven new query cases cover typed defaults, all selected families,
disabled-state/MIN/MAX/front-back distinctions, queue preservation versus committed
prefix failure, actual output, A/B/A ownership, resize, loss and sample storage.
Final affected suites pass 323 Windows and 309 WSL software cases; 36 focused
CPU/package cases, the expanded 121-case CPU CI selection and the Windows C++
state contract pass. Both profiles report nine zero shutdown gauges. The native
projection adds no allocation/submit/wait/readback/presentation; explicitly queued
commands retain their own effects. All 224 Windows SDK members rehash unchanged,
and the original inplace module remains unchanged. Linux still uses retained
libraries and recompiles all first-party units under experimental provenance.

This is source-functional Q1 evidence, not independent implementation review,
full G0 reconciliation, exact installed-wheel qualification or closure of legal
setter gaps. Current CI execution remains separate from the local CI selection.
The Linux scissor/toolkit and mandatory threedee blockers remain open. Retained
commands, failures, source/artifact identities and managed cleanup are in the
local `build/runs/state-query-15/` packet; no release profile was promoted.


## Tk capability source checkpoint (B4, TK-1/5/6, BACKEND-2)

The [mode-specific capability record](../../tkinter-capabilities.md) now maps
window options/properties, requested/granted attachments, resource sharing and
UI-thread ownership to concrete fixtures. Invalid framebuffer/window requests
fail before interpreter adoption or widget/native registration, leaving a
correctable Canvas request. Accepted minimum color/depth/stencil and sample
requests are checked against actual storage. Explicit stereo/native double
buffering and unrepresentable precision remain contextual unsupported requests;
the inherited default double-buffer hint is not reported as an actual back buffer.

Embedded hide/show now restores pack/grid/place layout and host bindings, preserves
pack order and respects a new host placement. Embedded window-manager requests
fail instead of silently changing a cached flag. Standalone fullscreen reports
native acknowledgement. Shared texture updates reach both consumers and survive
closing either first. UI-thread preconditions protect toolkit entry points and
public Canvas/Timer state before rejected worker calls can mutate it.

The initial Windows run reproduces 20 failures and four sharing passes. The final
45 new capability cases pass within 328 Windows and 314 WSL software affected
suites, with nine zero native shutdown gauges per profile; 47 CPU/source contracts
also pass. Reused native binaries are unchanged. Canvas/Timer deviations are
recorded and the existing source-preservation verifier passes. No new native
build, wheel, environment or installed/hardware qualification was produced.

This advances B4 source behavior and acceptance mapping. Full G0 reconciliation,
independent implementation review, exact installed gates and remaining legal
state/backend/host work remain open. The retained preexisting/intermittent Tcl
ThemeChanged diagnostic for a destroyed interpreter still needs attribution for
complete Tk shutdown qualification; source pass counts do not erase it. The
existing Linux scissor/toolkit and threedee blockers remain distinct. Packet
commands, source/native identities, failures and cleanup are retained locally in
`build/runs/tk-capabilities-16/` under the unchanged hygiene policy.


## Inventory source-observation checkpoint (I1, INV-1/2, EV-1/2)

The canonical v2 ledger now retains concrete optional Windows/WSL development
observations for eight Tk/state/resource features, with ordinary/mutation node
IDs, exact case counts, profile-local dependencies, runtime source identity and
original reports. Fourteen fixture functions collect 37 cases per platform; both
runs pass with nine zero shutdown gauges. Interpreter/toolkit/native/lock and
source identities are retained in the pinned observation JSON. No native build,
wheel, environment or dependency history was created.

All 142 original required seed pairs and rows remain unchanged and unreviewed;
the new observations add no shipping support or full-feature claim. Six new
controls cover real optional observations preserving required scope and failed,
wrong-profile, live-resource, missing-gauge and wrong-pin evidence. The final
127-case CPU CI selection passes. The bootstrap regression preserves original
scope while permitting additive curation; the production qualification gates
remain intact. The source-observation validator additionally checks its hash,
profile, exit/status and all shutdown gauges before accepting the new evidence.

This is partial I1 progress. Full methods/examples/events/hosts reconciliation,
required shipping profiles, independent review, exact installed/observer gates
and all previously retained runtime/platform restrictions remain open. See the
[inventory guide](../../compatibility-inventory.md#recorded-tkstate-source-observations).
`--require-complete` still fails with 142 incomplete required rows. Commands,
source reconstruction and terminal cleanup are retained in the local
`build/runs/inventory-map-17/` packet.


## Depth-range source checkpoint (L1, STATE-1/2/3/5)

The [depth-range decision and acceptance record](../../depth-range-compatibility.md)
implements ascending Dawn viewports with a captured reverse clip-Z shader variant
for reversed logical ranges. Equal endpoints and independent endpoint clamping
are retained. Actual compiled fragment-depth/early-test metadata selects the
window-depth route, preserving explicit depth outside a partial viewport range
and logical fragment coordinates through a captured std140 control. Generated
line reconstruction and existing early-test/side-effect guards remain separate.

The baseline reproduces 17 failures/four passes, including the existing forward
explicit-depth clamp defect. Thirty depth cases now cover ordinary/point/line,
clipping, comparisons/masks, queued A/B/A, indexed instancing, aliases and loss.
Final affected suites pass 421 Windows and 407 WSL software cases, 36 CPU/package
cases and the Windows state, shader/corpus and artifact/cache C++ contracts.
Both native profiles have nine zero shutdown gauges. The immutable Windows SDK
and retained Linux libraries are reused; Linux keeps experimental provenance.

This advances L1 source behavior, not arbitrary shader/attachment forms,
performance parity, independent review or G2 qualification. Remaining legal
state packets, full G0/required-profile review, exact installed/absence gates and
all prior platform/host restrictions stay open. Older optional source observations
keep their recorded product/native identities and are not relabelled with this
candidate. Commands, preferred source/artifact identities, baseline failures and
cleanup are retained in local `build/runs/reversed-depth-18/`.


## 13. Current candidate and obligation-conservation contracts

This section governs the next execution queue and refines INV-1..3, EV-1..5,
ART-1..2 and RET-1. The I2 source checkpoint below records the subsequently
implemented v3 tooling. Concrete profile transfers, candidate manifests and
release qualification remain future deliverables.
The source checkpoints above remain historical evidence with their original
source/native identities. Q1, selected B4 and L1 depth behavior need review and
installed qualification rather than another implementation from scratch.

### Candidate manifest and release boundaries

Before another qualification build, the coordinator and packaging/proof owner
retain a small versioned candidate manifest. Validate it before allocating
scratch. A development candidate, a qualified scoped workflow and full upstream
closure are distinct outcomes. A development candidate may remain a draft with
explicit blockers; calling it first usable does not bypass a mandatory gate.

| Manifest field | Required content and rejection rule |
| --- | --- |
| Identity | Candidate ID, source commit/dirty patch hash, upstream pin, native/Python input hashes, wheel/member identities when produced, profile/lock hashes and the manifest's own hash. Missing wheel identity means source evidence only. |
| Profiles | Each selected Windows Vulkan or WSL software Vulkan interpreter/ABI, toolkit, display path, adapter/driver and dependency pins. Each selected headless, standalone Tk, embedded Tk or Qt/host workflow has its own actual mode. A profile name alone establishes no runtime capability. Native Linux GPU stays unqualified; Metal stays experimental without a Mac. |
| Acceptance selection | Explicit feature/profile obligations, required workflow IDs, exact ordinary/mutation/failure/recovery fixture node IDs and independently authored expected results. Record public options, granted attachments, shared-resource behavior, input/DPI and teardown boundaries. No broad feature can be qualified by one smoke fixture. |
| Existing obligations | References to every original mandatory host row and applicable no-OpenGL gate; Windows napari-threedee stays required and unresolved until its existing acceptance passes. Separate broader full-compatibility obligations from the selected workflow without deleting them. |
| Restrictions and blockers | Legal unsupported state/shader forms, backend/mode limitations, Linux toolkit/scissor failures, Tcl shutdown diagnostic, hardware gaps and next evidence-driven action/owner. Experimental or blocked work cannot acquire a qualified state from a scope label. |
| Gate closure | Source/fixture review; full installed-member/closure audit; installed functional and shutdown results; dependency, transient-load and execution/API gates with their original controls; required current-head CI; final independent promotion review. Every receipt binds the same final artifact/profile and covered workflow. |
| Reconstruction and retention | Installation recipe, installed-origin verification command, per-workflow launch command and independently expected visible/captured result; previous known-good artifact; existing source/artifact/toolchain references, original licenses and patches, command, actual exit/child wait, managed run owner/budget and terminal cleanup receipt. Reference retained inputs by hash rather than copying their histories. |

An installable first usable candidate must identify its actual wheel and admitted
workflows, with their full functional and all three absence gates passing against
that artifact. Windows workflows may be selected first; this leaves WSL software
and native Linux GPU obligations distinct and open. Preparing this candidate
does not authorize publication of the existing draft release.

A scoped workflow qualifies only when every selected required criterion and its
same-artifact evidence passes. Publishing or merging the complete-removal
release still requires the original mandatory matrix; a new manifest cannot
waive it. Full VisPy compatibility additionally requires reviewed finite G0 and
all required applicable feature/profile pairs. Optical display instrumentation
and extreme driver pixel parity remain deferred as already agreed.

### I2: lossless transition from seed obligations to concrete profiles

The current v2 schema has no transfer/retirement object. Positive evidence cannot
attach to the unadmitted `unassigned` profile. Current generator/source-observation
tests deliberately preserve all 142 required seed pairs and literal seed records.
Thus adding optional source profiles cannot complete G0, while directly deleting
or relabelling seed pairs would defeat the preservation contract.

Implement a versioned, non-overwriting migration and conservation validator
before altering those invariants. The design record must specify the new schema
version or separately pinned obligation index, deterministic transfer semantics,
validator entry point and compatibility of existing receipt readers. Do not add
unrecognized transfer fields to v2 and claim they are already validated.

For each original obligation retain its stable origin feature/profile key,
original upstream source/record hash, review rationale, reviewer and disposition.
A transfer names concrete required successors, their public behavior boundaries,
profile-local dependencies and the union of covered acceptance criteria. A split
into methods/options must preserve every original behavior; a narrower successful
subset cannot stand for the original whole. Retain unresolved residual criteria
as blocking obligations. A merge retains every parent origin independently.
A genuine scope exclusion needs explicit reviewed justification consistent with
existing authorization; hardware absence or an unresolved failure is no reason
to erase required scope. Broader release-scope changes still need authorization.

A parent obligation is discharged only when the conservation validator proves
complete reviewed coverage and every required terminal successor is qualified
with appropriate evidence. Keep original records/receipts in immutable history;
never rewrite their product identity, turn source receipts into wheel receipts,
or count both a transferred parent and its successors as separate completed work.
Before this mechanism is implemented, all current required seed obligations stay
blocking, `reviewed=false`, and `--require-complete` continues to fail.

| Conservation control | Required result |
| --- | --- |
| Missing origin, duplicate origin disposition or altered origin hash | Reject; an unaccounted original obligation must remain visible. |
| Transfer cycle, dangling successor or uncovered split criterion | Reject; a chain must terminate in explicit applicable obligations with complete behavioral coverage. |
| Optional/nonapplicable successor substituted for required work | Reject unless a separately valid authorized scope disposition explains it; a change of flag is insufficient. |
| Missing/unreviewed destination profile, or hardware absence recast as nonapplicability | Reject; review concrete applicability and preserve externally blocked required obligations. |
| Broader parent represented by a narrow smoke, or required dependency removed | Reject; preserve residual work and same-profile dependency closure. |
| Stale source receipt, mismatched profile/artifact/workflow or forged qualification | Reject under unchanged evidence gates; transfer conveys scope only, never evidence status. |
| Optional failed experiment alongside complete required obligations | Preserve its failure and original status without making it a new mandatory requirement. |
| One ordinary/mutation-mapped concrete slice and untouched remaining seed | Structural validation succeeds; full closure still fails on remaining required work. |

Replace literal-preservation regression assumptions only with stronger verified
conservation assertions against the frozen seed. Preserve deterministic bootstrap,
original pins and negative controls. The migration exits with a validated mapping,
a before/after obligation report and an independent scope review; it does not
itself qualify a feature or manufacture a completeness percentage.

### Bounded execution, evidence reuse and stop conditions

The next packet begins with named requirements, affected files/workflows, oracle,
negative control, resource estimate and stop condition. Every legal-state or
shader guard removal is limited to its demonstrated subset. Keep independent
software work moving when hardware is unavailable; do not spend repeated build
runs gathering equivalent source pass counts.

Linux toolkit capture and MSAA scissor have different controls and causes. A
plain Tk control must use the same pinned Python/Tcl/Tk/display environment as
the affected workflow. Scissor proof must assert actual four-sample storage,
nonzero-origin odd-sized boundaries, original expected pixels and loaded driver
identity. A replacement-profile pass does not explain or qualify the old profile.
Windows threedee uses the existing three diagnostic starts plus one targeted
confirmation, with a declared watchdog, log cap and awaited owned children.
No reproduction leaves that row unresolved; success-only retries cannot close it.

A failed bounded trial retains its counterexample and next discriminating
experiment. Stop new allocation on budget/reserve failure, unknown ownership,
changed pinned inputs or an unbounded/hung child; preserve the actual exit/wait
and use existing process ownership rules. Independent review unavailability keeps
promotion pending while other source work proceeds. A documentation change alone
requires local links/anchors, requirement/queue consistency and applicable schema
checks, with no native rebuild, environment clone or release archive repack.


### Cumulative implementation review and Tcl shutdown attribution

The source-review input is a frozen cumulative patch and fixture mapping for Q1,
selected B4 and L1, including their shared query/state/shader/Tk boundaries.
Review both the original base and intervening changes; a latest-commit-only
review cannot establish that the earlier packets are covered. Bind comments and
disposition to reviewed source hashes. Check logical query authority and queue
preservation, Canvas/Timer public-state interactions with other backends,
constructor/thread/host ownership, reverse-depth cache identity,
compiled fragment-depth/early-test classification, hidden uniform layout and
resource limits, the forward explicit-depth correction, ordinary, point and generated-line
boundaries, and loss/close. Source test totals and this plan review are supporting context,
not implementation-review approval. A subsequent relevant code change invalidates
the affected approval/receipts until reviewed and rerun as appropriate.

Treat the intermittent Tcl `ThemeChanged` diagnostic after destroyed-interpreter
teardown as an unresolved lifecycle observation distinct from the Linux plain-Tk
abort. Before its next run declare three fresh-process diagnostic trials and at
most one causal confirmation, 60 seconds per process, a 2 MiB per-trial log cap
and 10 seconds to terminate/wait for an owned child on timeout. A need to revise
these bounds is a new documented experiment, not an automatic retry.

Record interpreter/root identities and ownership, construction/destruction order,
VisPy and unrelated host jobs/bindings/images before and after close, thread ID,
full diagnostic/traceback and exit status. Compare a minimal plain-Tk control and
same-profile standalone and supplied-parent VisPy workflows, changing one
variable per comparison. Retain all trials, including passes and abnormal exits. Confirm diagnostic collection with
a deliberately failing owned callback; absence of captured stderr alone cannot
prove correct teardown. Preserve unrelated host timers/bindings and use the nine
native gauges plus Tk job/image/interpreter assertions for shutdown acceptance.

Close the observation only with a causal fix and regression, or evidence that
identifies an external toolkit cause and justifies the exact affected profile's
scope. Do not silence callbacks/stderr, ignore unraisable exceptions, retry until
a pass, or infer clean shutdown from native gauges alone. If not reproduced,
retain unresolved status and next discriminating experiment; do not claim a
newly qualified Tk lifecycle profile.


## Obligation-conservation tooling source checkpoint (I2, INV-1..3, EV-1..5)

The [v3 tooling contract](../../compatibility-inventory.md#conserved-obligation-transfers-v3-tooling)
is implemented by the optional v3 schema and conservation validator. An explicit
non-overwriting v2-to-v3 migration pins a frozen valid baseline and preserves
existing records. Reviewed transfers cover every scope/ordinary/mutation,
requirement/capability/dependency criterion, retain original scope and historical
rows, require concrete required successors and reject cycles. Scope approvals
bind exact baseline/transfer hashes. They declare reviewed coverage; the tool
cannot infer the truth of a behavioral rationale or approve its own reviewer.

Twenty-two new CPU cases cover the mechanism and shortcuts. The exact affected
CI selection passes 149 Windows and 149 WSL cases without skips. Synthetic
terminal qualification still requires all existing gates; source-only successor
proof remains incomplete. v2 receipts/constraints remain unchanged. The first
WSL launcher failed before collection because pytest was absent from its default
search path; the corrected launcher reused the already retained package paths,
with no installation or environment creation. Both outcomes are retained.

Canonical v2 scope, original 142 required/unassigned pairs and historical optional
source observations remain unchanged. No real obligation has transferred or
qualified. Selected concrete profiles, behavioral scope review, candidate
manifest, cumulative implementation review and exact G2 artifacts/receipts are
still required. This source packet changes no hardware or mandatory host gate.
Evidence, source reconstruction and managed terminal cleanup are retained in
local `build/runs/inventory-conservation-19/`.


## Tk shutdown and shared-progress source checkpoint (G1b, TK-2..4, EV-1..5)

The [shutdown/progress record](../../tkinter-shutdown-compatibility.md) retains
bounded minimal controls, a 421-case phase trace and the failing fresh-process
Tcl stderr regression. The known ThemeChanged observation came from a test host
that destroyed its adopted root without first draining its idle work. The host
cleanup now drains idle work at its own explicit teardown; backend quit still
preserves host callbacks and does not pump a borrowed interpreter.

The broad isolated run exposed a separate native-progress duplicate report in an
external event loop. Two callback-order controls fail before the correction.
Draw and timer routes now share stopped-until-explicit-retry polling, delivering
the original error once and preserving cancellation ownership if cleanup fails.
Three new deterministic cases cover ordering, recovery, host jobs and secondary
cancellation failure; the fresh-process stderr case adds a fourth regression.

Final affected source suites pass 425 Windows/411 WSL cases, with all nine native
shutdown gauges zero and no ThemeChanged diagnostic. Thirty-eight CPU/package/
source-preservation contracts also pass. Existing native leaves, SDKs, locks and
environments are reused. Original test fixture line endings were restored after
the broad runs with retained tested copies and AST equality; runtime bytes are
unchanged. Source evidence and exact installed qualification remain distinct.

The known source diagnostic is attributed/covered, not a complete Tk shutdown
qualification. Independent cumulative review must now include the shared poll
failure/retry and host stderr controls. Required-profile mappings, candidate
manifest, exact G2/observer/CI evidence and original host/platform gates remain
open. The separate Linux toolkit/scissor failures and experimental native Linux/
Metal scope are unchanged. No historical optional observation is relabelled.
All actual failures and child waits, source reconstruction and managed cleanup
are retained locally in `build/runs/tk-shutdown-20/`, `tk-theme-trace-21/`,
`tk-shutdown-regression-22/` and `tk-progress-23/`.


## Concrete candidate preparation source checkpoint (I2, INV-1..3, EV-1..5)

The [candidate preparation record](../../candidate-preparation.md) and versioned
declaration now name 15 scoped proposals, 30 proposed Windows/WSL pairs and two
real observer scripts. The new resource workflow exercises public Program,
VertexBuffer, Texture2D and Timer operations, shared consumer close, native
device-loss recovery and host-preserving teardown. Exact categorical GPU/Tk
expectations wait for the actual configured target extent, not a stale image.
An injected timer-upload error preserves the original failure and returns all
scoped resource counters exactly to baseline; global worker shutdown still
requires all nine zero. Final affected source suites pass 429 Windows/415 WSL.

Preparation validation pins complete runtime/native/build/lock/license inputs,
fixture/script/verifier bytes, local dependency closure and every original
mandatory host row. It rejects changed or missing inputs, stale reviews and
source/installed or software/hardware relabelling. The source snapshot's 603
runtime/build/license blobs match declared commit c7e191ee8ee506d4ba6244eaa217efceb43d115c.
These checks neither run builds/installs nor replace any installed auditor/gate.

All proposals are unapplied and unreviewed. The original 142 required pairs and
historical observations remain unchanged; narrower subsets discharge no parent.
Source/scope review, missing method/wrapper reconciliation and conservation
mappings, exact candidate wheels and G2 evidence remain pending. Even reviewed
v1 preparation cannot claim installability, qualification or release completion.
Other legal-state/shader/backend/host requirements and experimental hardware
scopes remain in force. Sources, meaningful failures and actual test exits/waits
are retained in local `build/runs/candidate-workflow-24/`. Its terminal manifest
and cleanup receipt now verify 131 retained files and removal of 6,063 scratch
files (61,298,281 bytes); the separate source/qualification gates remain open.

Final preparation/protocol checks pass 177 cases on Windows and WSL. The
recovery watchdog retains its 1000 ms deadline; its owner now cancels it before
a successful quit, because Tcl may otherwise service another already-ready
timer. Two deterministic controls fail before that test-harness correction.
Final native validation runs profiles serially on the shared machine and keeps
the original concurrent failures. No runtime deadline or pixel criterion was
relaxed. All nine process-wide shutdown gauges remain zero.


## 14. Current delivery contracts after candidate preparation

This section governs the next work after the concrete candidate checkpoint.
Earlier packet designs retain their acceptance requirements; their historical
pending wording does not instruct rebuilding source-tested packets. The
[Astra review disposition](../reviews/2026-10-24-astra-preparation-handoff-review.md)
records the planning findings behind these refinements. These are requirements
for future implementation, not approval of the current implementation.

### Selected scope and residual obligations (INV-1..3)

Start from the frozen `tk-state-resource-1` preparation: 15 proposed subsets,
30 feature/profile pairs and three executable workflows: ordinary state,
ordinary resources and composite failure/recovery. Validate their current bytes
before scheduling work. Do not create a replacement manifest merely
because its proposals are not yet reviewed. The canonical inventory remains the
source of required obligations; proposal counts are never a completion denominator.

For each selected pair, write a criterion-level mapping containing the origin
feature/profile and criterion ID, proposed concrete successor, exact public
methods/options/values, required dependencies, expected behavior, acceptance
mode, fixture and observer scenario, exclusions and unresolved residuals. Include
unseeded wrapper methods in reconciliation rather than inventing an origin or
hiding them within a successful exported parent. Scope review checks behavioral
coverage against the pinned upstream source, not just schema validity.

There are two curation routes: add explicit required scoped rows while broad
parents remain unchanged and blocking, or use the implemented v3 conservation
mechanism for selected transfers with complete successor/residual coverage.
Neither route sets global inventory review to true. Preserve the frozen v2
baseline and original receipts. A partial split keeps uncovered
criteria explicitly required and prevents parent discharge. An untouched seed
remains blocking without needing a speculative successor. Selected scope review
and scoped artifact work may proceed before all 142 parents have concrete
successors; full inventory closure still requires complete reviewed conservation
and qualified terminal coverage of every applicable required criterion.

### Preparation-to-artifact handoff (EV-1..5, ART-1..2)

The v1 preparation deliberately cannot represent a wheel or shipping admission.
Do not add a wheel, flip its phase or reinterpret `VALID_PREPARATION` as a
qualified result. Freeze its hash and use a separate exact-artifact qualification
index that references the existing canonical/v3 obligations, workflow-bound
receipt protocol and mandatory host matrix. This index is a join over existing
proof, not another auditor or alternative completion denominator.

Before implementing that index, define its versioned schema and read-only
validation entry point. Its required joins are:

| Identity or join | Required content and rejection |
| --- | --- |
| Reviewed source | Preparation hash, cumulative base/patch or commit, exact source/fixture review scope and disposition. Relevant changes invalidate affected approvals. |
| Obligations | Proposed pair to canonical/v3 feature/profile/criterion IDs, dependency closure, residual required obligations and scope-review digest. Reject dangling, optionalized or incompletely covered required criteria. |
| Exact product | Wheel filename/SHA-256/tags, complete installed-member audit, native producer/member identities, lock/toolkit/driver closure and actual consumer interpreter/profile. Reject a source checkout or old wheel receipt substituted for changed Python bytes. |
| Workflows | Exact scenario script/arguments/injection identity and covered criterion IDs; receipt references for each required acceptance mode, with actual exit, child wait and shutdown. |
| Independent gates | Existing dependency, transient-load and execution/API reports, their independent controls and hash edges, plus required current-head CI and final promotion review. Reject mismatched product/profile/workflow or missing original reports. |
| Retention | Reconstructable preferred source/patches/recipes, original licenses, previous known-good artifact references, run owner/budget and verified terminal cleanup result. |

A structurally valid index with missing/failed gates is incomplete, not qualified.
Require controls for stale preparation, wrong wheel/member, wrong profile,
missing dependency, wrong branch receipt, missing control, live child, nonzero
shutdown, stale review and stale CI before using the index for admission. Reuse
the current evidence validators; do not weaken them to accept the new join.
No exact-artifact index or admission mechanism is implemented by this section.

### Acceptance branches must execute under observation (EV-3,4)

A workflow-level list containing ordinary, mutation, failure and recovery kinds
is insufficient to prove each feature's behavior. Before installed execution,
map each selected required feature/profile/mode criterion to its actual fixture,
expected result, observed script or scenario variant, literal arguments, fault
injection and gate receipts. Several criteria may share a run only when the
observed run actually exercises and identifies every claimed branch.

The ordinary state/resource scripts alone do not execute all failure/recovery
fixtures. The third composite script now includes controlled upload and native-
progress failures; its later source checkpoints record that implementation.
The submission-capacity extension has now passed its source profile checks and
exact declaration bindings; the later source checkpoint records their scope. Executable scripts
still provide source evidence until bounded installed-origin scenarios execute
under the original observation protocol.
Record the injection route and expected original exception/traceback, exactly-once
delivery, stopped polling/timer state, permitted explicit retry, survivor output
and host-owned work after cleanup, as applicable to the criterion. An unexpected
callback error or cleanup failure cannot be normalized into a successful run.

For an expected-error branch, the scenario harness catches and verifies the
intended exception and traceback, cleanup and explicit recovery postconditions,
then exits successfully only when all assertions and observer completion pass.
Record the actual error and injection in its evidence. An unexpected failure,
missing injection/branch, wrong exception, duplicate delivery, failed recovery or
missing observer completion remains a failed gate with its actual child exit.
Do not rewrite a failed exit, suppress diagnostics or introduce a permissive
observer success type to admit a failed process.

Current v2/v3 rows carry one workflow; preparation may list overlapping workflows
and additional fixtures. Required coverage is conjunctive. Either use one
hash-pinned composite observed scenario asserting every required branch, or
split scoped rows/workflows with an explicitly validated all-required aggregation
and complete conservation mapping. One successful workflow receipt cannot stand
for several required variants. Test ordinary-only proof, a missing variant and
one failed variant as rejected claims before using this aggregation.

### Profile blocker applicability before packaging (EV-5, ART-1,2)

For every selected pair, link the original failing fixture, artifact/profile,
execution path and shared dependencies; record whether the proposed workflow
intersects those dependencies and why. The Linux plain-Tk abort involves a
shared toolkit/lifecycle path. Excluding a capture fixture alone does not prove
that an embedded or standalone candidate is unaffected. Either show the affected
path is outside the claimed dependency closure with evidence, reproduce/fix it
in the exact candidate profile, or retain its blocking status. Apply the same
analysis separately to four-sample scissor; one cause cannot explain the other.

A replacement toolkit/driver/runtime establishes a new profile identity and
needs its own closure and affected-workflow gates; it does not qualify the
original failing profile. The retained Linux native leaf has experimental
producer provenance. Putting it in a wheel cannot upgrade that provenance.
Before any qualification claim, satisfy the original producer/source/toolchain
requirements for the claimed profile or explicitly keep it experimental and
unqualified. Windows scoped progress can continue independently. Native Linux
GPU and Metal hardware admission still require their separate real evidence.

### Bounded execution and invalidation

| Packet / responsible role | Inputs and concrete output | Exit and next dependency |
| --- | --- | --- |
| P1 / coordinator and inventory owner | Existing preparation, pinned upstream and canonical baseline; selected criterion map, residuals and reviewed transfer proposal. | Scope review accepted for selected pairs; unresolved parent scope remains visible. Full G0 reconciliation can continue independently. |
| P2 / independent source reviewer | Frozen cumulative runtime, Tk/state, conservation/candidate/auditor tools and fixtures, including retained meaningful failures. | Findings disposed by exact hashes; fixes get affected regressions and renewed review. This Astra plan review is not P2. |
| P3 / workflow owner | Reviewed criterion map and existing observer protocol; bounded installed failure/recovery scenario variants with independent expected outcomes. | Per-branch identity/exit/cleanup controls pass; no claim from a branch executed only outside observation. Source-only development may proceed while review is pending. |
| P4 / artifact and proof owner | Reviewed source and admitted P1/P3 scope; reuse matching native inputs and package changed Python bytes once. | Separate exact-artifact index plus full installed-member/closure, functional/branch, original absence/control/shutdown receipts for each selected profile. Missing evidence leaves that profile incomplete. |
| P5 / independent promotion reviewer | P4 receipts and required CI for the frozen head; unchanged original mandatory matrix. | Scoped admission only for fully proved criteria. Complete-removal release still requires all original mandatory rows; full VisPy compatibility additionally requires full G0 closure. |

P2 starts from the last independently reviewed baseline, not merely the latest
commit or the Q1/B4/L1 subset. Its frozen inputs include submission ownership and
post-submit failures; shared native progress, error delivery and retry; root/job
ownership and shutdown; resource/Timer flows; readiness and watchdog harness
corrections; workflow evidence binding and affected observers; and inventory,
conservation and preparation validators. Retain exact hashes, finding IDs and
dispositions. Any later relevant edit invalidates the affected approval.

Do not wait for unrelated hardware or full G0 reconciliation before independent
source packets; do not advance an affected qualification past its dependencies.
Select remaining legal-state, shader and backend work from explicit consumer
requirements in sections 5-7 and 12. Each packet names planned files, oracle,
negative control, affected dependency reruns and a retained feasibility decision
before guard removal. Existing Linux toolkit/scissor and Windows threedee
investigations retain their separate bounds and unresolved status.

Final GUI/native profiles run serially on this shared machine unless a documented
resource-isolation arrangement justifies concurrency. Preserve the one-second
recovery watchdog and exact pixel criteria; cancel an owned watchdog on success
before quitting its loop. Host-owned jobs remain outside that cancellation.
Record actual collection, cases/skips, exits/waits, native gauges and relevant
Tk jobs/images independently; a pass total does not establish all of them.

A spec/verifier/script/fixture edit refreshes the affected preparation hashes and
self digest and invalidates affected review bindings. It does not change the
runtime source commit when runtime bytes are unchanged. Documentation-only work
uses existing environments for reference/schema checks, with no native build,
new environment or source snapshot. Never claim a terminal cleanup receipt
before the manifest, exact plan/application and retained-hash verification exist.


## Composite failure/recovery source checkpoint (P3, EV-3,4)

The third candidate workflow, `tools/tkinter_failure_scenario.py`, now executes
ordinary state/resource behavior, a controlled Timer upload fault and explicit
resource/device recovery, plus both native-progress callback orders through an
actual borrowed Tk mainloop. The harness checks original errors/tracebacks,
exactly-once progress delivery, stopped public Timer/job, scoped gauge baseline,
blue survivor/recovery output and unrelated host job/binding preservation.
Expected errors pass only after all assertions; missing injections, wrong errors,
failed recovery or secondary cleanup errors are rejected by four native controls.
Two CPU tamper controls
reject sibling script changes before/during execution; a third pins the full
sibling set and nine gauge names to the original policy.

All eight affected native cases pass on Windows and WSL software; direct script
entry points also exit zero with nine zero shutdown gauges. No runtime package
or native binary changed. Historical ordinary-script observations retain their
original identities; the new composite pins exact sibling bytes and needs those source
inputs alongside it for eventual isolated observation. Preparation now names
three workflows with the same 15 proposals/30 pairs and all 142 original required
pairs preserved. This does not implement the qualification index, canonical
criterion/conservation mappings, independent reviews or installed absence gates.
The new packet retains its sources, original failures and actual exits/waits in
`build/runs/observed-failures-25/`; terminal cleanup must be verified separately.


## Alternate toolkit and input source checkpoint (B4, TK-6..8, P2/P3)

The [runtime profile record](../../tkinter-runtime-profiles.md) attributes the
old managed-Python Label abort before teardown and retains three failed controls
plus cleanup in `build/runs/linux-toolkit-cause-27/`. The identical control passes
12 lifecycles on the already-installed CPython3.12.13/Tcl-Tk9.0.3 runtime. This
is a distinct development profile; old toolkit/receipt identities remain blocked
or historical, and the independent MSAA scissor defect is not repaired.

Source fixes normalize typed Tcl command/namespace names and distinguish legacy
X11 Button4/5 wheel notifications from Tk9 extra buttons/MouseWheel. Focused
before-failing controls and both toolkit families retain exact input/state,
host ownership and pixel assertions. Plain-Tk controls also isolate a Windows
worker-GC finalization hazard; the thread fixture retires prior test garbage on
its UI owner and releases checked error cycles without changing production GC.
Mac CPU CLI proof now preserves the observed baseline native-GL failure while
checking successful argument/workflow plumbing; aggregate gates are unchanged.

Sources, actual failures/exits/waits, profile identities and affected results
are retained in local `build/runs/linux-toolkit-profile-28/`. This checkpoint
adds no installed-wheel, hardware, source/scope review or shipping qualification.
Experimental Linux native provenance and all remaining required obligations
stay visible. Terminal cleanup is proved only by that packet's applied receipt.

Final affected source acceptance passes 69 Windows/68 alternate-profile Linux
cases with nine zero gauges, including mixed Label/Vulkan host workflows and
controlled delayed completion progress. Original broad failures and the known
four-sample scissor failure remain retained. Direct script and legacy-toolkit
controls are recorded separately. The completion fixture now waits for observed
retirement before explicit retry; no runtime wait/presentation behavior changed.


## Criterion coverage proposal checkpoint (P1, INV-1..3, EV-1..5)

The [criterion coverage contract](../../criterion-coverage.md) and closed schema
join 60 selected criteria to 120 profile bindings. Each criterion pins public methods,
finite values, expected behavior, fixture bytes/counts and partial origin links.
All 142 original parents retain every criterion and identity; this additive proposal
applies/transfers/discharges nothing. Unseeded wrappers remain new requirements.
The validator accepts 112 script-ready bindings and exposes 8 source-only flush
capacity/retry bindings. Its strict readiness/review commands remain failing.
An ordinary or unrelated successful fixture cannot satisfy an unexecuted branch.
The existing scope review must bind both candidate scope and coverage hashes;
no extra review type or qualification bypass is introduced. Semantic coverage
and independent implementation review remain pending.

The same packet corrects missing glslang header propagation for 2 compiler-free
CPU contract targets, reproduced in current-head Linux/macOS CI. Both compile/run
on Windows and Linux with existing inputs. No renderer or SDK was rebuilt.
Current runtime Python/native bytes still match `53194f10`; only the contract build
recipe changes its source pin. Original functional/qualification identities are
retained with an explicit reuse basis. Source, failures, commands, retained small
native artifacts and cleanup are in local `build/runs/criterion-coverage-29/`.
All original installed, observer/control, host, hardware and full parity gates
remain unchanged. Source preparation is not release completion.

## 15. Executable handoff from proposals to scoped qualification

This section refines sections 13-14 following the
[current Astra max review](../reviews/2026-10-24-astra-executable-handoff-review.md).
It specifies future implementation. No derived execution ledger, branch admission
validator or exact-artifact qualification index is implemented by this text.
Source/scope approvals remain pending. All 142 original required obligations and
the original mandatory host matrix remain binding.

### Current unfinished packet and review freeze (EV-1,2, RET-1)

At this review checkpoint, `observed-submission-30` extends the composite script with raw/wrapper submission
capacity and retry branches. Its retained Windows result records 18 source cases,
zero failures/skips and exit zero. This is an unfinished packet: equivalent
selected Linux checks, direct entry-point checks, declaration/coverage updates,
and terminal retention/cleanup have not yet been completed. Preserve the first
three failed negative controls and their correction; they are harness evidence,
not a runtime fix. The current declared coverage remains 112 script-ready and
8 source-only bindings until the packet's exit checks and binding update pass.

Before P1/P2 review, freeze a small input record containing the last independently
reviewed base, cumulative commit/patch SHA-256, sorted changed-file hashes, runtime
input manifest, preparation scope digest, coverage digest, scripts/siblings,
fixtures, validators, schemas and original license references. Include retained
meaningful failures, actual commands/exits/waits and an explicit pending-work
list. A Git-less workspace needs its preferred-source reconstruction references
and exact dirty patch; a path or latest commit label alone is insufficient.
Do not recursively copy evidence, environments or build directories into it.

Review records identify their exact input digest, reviewer, finding IDs,
dispositions and affected feature/profile/criterion pairs. A changed script,
fixture, validator, scope or runtime member invalidates the affected approval.
Documentation-only changes refresh affected declaration hashes without changing
the product-source commit when runtime bytes remain identical. A plan review
cannot supply the pending implementation or scope approval.

### Materialize scoped rows without changing the frozen baseline (INV-1..3)

The development preparation pins a baseline ledger and rejects proposal IDs
already present there. The coverage proposal enumerates that baseline's exact
required parents. Adding the proposed scoped features directly to the pinned
baseline would invalidate those inputs. Use this explicit additive route:

1. Keep the preparation, its baseline ledger and coverage map immutable at the
   reviewed hashes. The baseline retains its original feature/profile objects,
   applicability, rows, receipts and required criteria. Its 142 parents are not
   replaced, optionalized or marked qualified by the selected scope review.
2. Produce a separate derived execution ledger with an explicit baseline path/
   hash and proposal-to-execution mapping. Use the existing v2/v3 inventory
   schema for the ledger and a closed mapping declaration for provenance; do
   not add unrecognized fields to an existing schema. The additive route needs
   no v3 transfers. Its read-only validator compares retained baseline objects
   and all original criteria before accepting any added feature/profile/row.
3. Add only the selected scoped features and concrete profiles. Map each proposal
   ID, preparation profile and selected criterion to exactly one execution
   feature/profile/criterion, listing its workflow and same-profile dependencies.
   Required selected pairs have reviewed applicability and explicit rows. Preserve
   upstream identities and the full selected operation/value/requirement scope.
   Reject omissions, duplicate destinations, invented origins, scope reduction,
   optional dependencies and profile relabelling. Map unseeded wrappers as new
   required features, with no fabricated parent-discharge credit.
   Populate the complete applicability matrix required by the existing schema.
   Newly introduced unselected combinations have explicit unreviewed scope and
   rationale; they cannot change an original required pair or imply proven
   nonapplicability. Review only the selected pairs for scoped admission.
4. Run the existing inventory validator on that derived ledger. Run the existing
   evidence normalizer with its `--ledger` argument pointing to that ledger, so
   its workflow and identity checks address the actual concrete execution row.
   Continue validating preparation/coverage against their frozen baseline; do
   not point them back at the derived ledger or rewrite historical receipts.
5. The qualification index joins the reviewed mapping and derived ledger. Check
   all selected rows and their transitive same-profile dependencies conjunctively.
   Keep global inventory review false while original required applicability is
   unreviewed; full-closure validation must still fail for unresolved parents.
   Scoped admission is a separate result with an explicit admitted set.

Negative controls must remove or alter a retained parent, point preparation at
the derived ledger, omit a mapped criterion/dependency, duplicate a destination,
optionalize a selected requirement, invent a wrapper origin and reuse a receipt
for another profile. Each must be rejected after recomputing declaration seals;
an obsolete self hash alone is not a sufficient regression control.

### Machine-readable results for every required branch (EV-3,4)

Free-text injection descriptions, fixture counts and declared feature coverage
cannot establish that a branch ran. Before installed admission, define a closed,
versioned branch-result record in the existing script/worker report path. Use
stable branch IDs, including every member of these finite sets:

| Branch family | Required members and observable proof |
| --- | --- |
| Submission capacity/retry | `raw` and `gloo`, each with immediate and deliberately delayed completion progress: exactly four distinct members. Record configured/saved slots, held completion, baseline/queued/rejected/retired/retried snapshots, verified capacity exception/traceback, one retry submission, and exact green readback while the Tk image stays blue. |
| Native progress failure/recovery | `poll` and `draw` callback orders: exactly two distinct members, each with actual borrowed-mainloop delivery, original exception/traceback, exactly-once delivery, stopped job, explicit retry and survivor output. |
| Resource upload failure/recovery | Actual controlled upload error and explicit resource/device recovery; original exception/traceback, public Timer stopped, scoped counters equal baseline and exact recovery/survivor output. |

Each member records branch ID, route/order/delay parameters, injection identity,
actual observed values, expected-value contract/version, verified status and
cleanup/restoration outcome. Map the selected criterion/profile to these branch
IDs through reviewed data. Shared branches may serve several criteria only when
their public operations and expected behavior match the reviewed mapping.

The worker result, scenario hash/arguments and installed product/profile must be
bound to the same original observed child and its exit/wait. Discovery, dependency
inventory and fresh replay retain their existing identity and control checks.
The current script probe discards `runpy.run_path()`'s return value and the scripts
print their result to stdout; existing workflow success is not a structured
branch-result binding. Before changing the observer, specify one explicit result
transport, its exact producer and capture point, closed schema and report hash
edges. Capture the scenario's result in that observed worker, then include its
hash-bound content/reference in the worker report and controller/normalizer join.
Test absent/truncated/malformed output and a successful script exit without its
required result. Do not parse an arbitrary last JSON-looking log fragment or
reuse an unrelated process log as the result channel.
The branch adapter consumes the hash-bound worker result through the existing
report protocol; it cannot accept an independently supplied JSON file or a
source-test result as evidence that the installed child executed that branch.
Do not replace any of the three existing absence gates or their controls.

The validator requires the exact branch-ID set and parameter tuples, unique
members, all successful verified assertions and required restored state. A
four-element list containing one duplicated route does not prove four branches.
Reject ordinary-only output, a missing/duplicate/unknown branch, wrong route or
delay, wrong exception, missing retry, changed counters/pixels, failed secondary
cleanup and a branch report copied from another child/product/profile. For
negative controls, reseal the outer metadata so the semantic check is exercised.
Expected injected errors may yield a successful script exit only after their
assertions and cleanup succeed; unexpected errors retain their actual failure.

### Qualification subject, detached review and current CI (EV-2, ART-1,2)

Implement one read-only qualification-index validator and versioned closed schema
as P4 work. Validate existing reports by calling their existing validators; do
not duplicate or relax their gate logic. Resolve references by path and SHA-256,
reject missing/unrecognized fields, duplicate keys/IDs and dangling references,
and report missing or failed requirements per selected profile/criterion.

Separate these identities to avoid a hash or commit fixed point:

| Identity | Required meaning |
| --- | --- |
| Product source | Exact runtime/native/build/license inputs and patch, plus each wheel and its complete installed-member audit. Changed scenario/docs do not relabel old product receipts. |
| Qualification implementation | Commit/patch and hashes of the actual scripts, fixtures, schemas, adapters and observers used to generate/validate evidence. |
| Reviewed scope | Frozen preparation scope/coverage hashes, baseline and derived-ledger/mapping hashes, selected required criteria and dependency closure. |
| Evidence subject | Immutable manifest of the preceding inputs, exact wheels/profiles and original report references, commands, exits/waits, shutdown and retention. Its digest excludes detached review/CI envelope fields. |
| Promotion envelope | Hash-bound reference to the immutable subject, independent final review of that subject and required CI receipts for an explicit qualification head. The reviewer is not asked to approve a record containing the review's own future hash. |

The required CI check set comes from the current project policy; record exact
repository/head, workflow/check/job identities and conclusions. Failed, cancelled,
skipped, missing or pending required checks are incomplete. CI for another head
cannot substitute through a job-name match; record workflow revision, run ID and
attempt as well as the actual checked head. CI for another head
cannot qualify the claimed head. A later commit requires CI for that new head
and an explicit change-impact/review decision. Retaining a detached evidence
envelope outside that head avoids a self-referential commit; it does not waive
current-head CI or final promotion review. The subject's product commit and
qualification head must each be explicit and cannot substitute for each other.

Structural validation can report an incomplete index, but its strict admission
mode must exit nonzero unless every selected criterion/dependency, exact product/
profile, installed-member/producer closure, original absence/control report,
shutdown, independent review and required CI join passes. Return the admitted
criterion/profile set explicitly. Do not return global release/full-compatibility
completion from this scoped result; unresolved original obligations remain visible.

Declare the requested admission set before running qualification, including its
transitive profile-local dependencies. A Windows-only request can succeed for
that set while the total preparation, WSL and full inventory remain incomplete.
A request selecting both profiles fails strict admission if either selected
profile fails; the validator cannot silently drop it. Report requested, proved,
blocked and missing sets separately and distinguish scoped admission from total
candidate completion. Reject cross-profile dependency substitutions. Changing
the requested set changes the subject and requires renewed scope/promotion
review; it is not a post-failure filter that can turn an old run green.

Before admission, exercise stale preparation/coverage/source reviews, altered
derived mappings, wrong wheel/member/profile, experimental producer provenance,
missing branch/control/dependency, source-mode receipts, unawaited/live child,
nonzero gauges, stale/failing CI and a final review of another subject. Retain
the precise rejection for each control and one complete synthetic join clearly
labelled test data. Synthetic approval is never a real review disposition.

### Profile decisions and bounded next actions (EV-5, RET-1)

Record blocker applicability before packaging, using the selected workflow's
actual dependency path and a distinguishing control. The original Tk8.6 profile
remains blocked; Tk9 is a separate development profile, not a fix receipt for
Tk8.6. Its source passes cannot cure experimental native producer provenance.
The four-sample odd-size/nonzero-origin scissor failure remains an independent
required graphics defect. Do not rename a failing profile out of the obligation
set. If a reviewed selected workflow cannot encounter an excluded capability,
retain that explicit limitation and the broader required defect separately.

Windows scoped qualification may proceed when its own prerequisites pass. WSL
software qualification needs admitted producer provenance and its own exact
profile evidence. Native Linux GPU remains unqualified and Metal experimental
without hardware. Keep the bounded three-diagnostic/one-causal-confirmation
Windows threedee packet required for the complete-removal release; favorable
retries alone cannot close it. Legal-state, shader/backend/host breadth and full
inventory reconciliation remain named independent work after this handoff.

Each subsequent packet declares owned files, exact input hashes, oracle, negative
control, affected reruns, deadline and expected additional disk allocation before
execution. Run final native GUI profiles serially. An observation timeout resumes
the same live process handle; it does not authorize a second producer. A failed
budget preflight stops allocation. After the child actually exits, retain small
source/evidence/license/reproducer references and verify the managed cleanup
receipt before the next experiment. This documentation pass allocates no scratch
and makes no cleanup claim for the still-open submission packet.

## Observed submission branches source checkpoint (P3, STATE-2/4, EV-3/4)

The composite now runs raw and gloo capacity/retry routes with immediate and
controlled delayed progress: all four branches are actual native operations.
Single-slot completion delivery is held; capacity rejection preserves queued
green work with unchanged submit/wait/presentation counters. Release and observed
retirement precede an explicit exactly-once retry. Exact green readback leaves
the Tk image blue, while cleanup preserves host work and restores the prior slot
configuration. No GUI pumping masks submission inside the measured region.

Eighteen affected native source cases pass on each selected development profile,
including six missing/wrong-error and absent-retry controls. The direct composite
entry point also passes on Windows and WSL, with nine zero shutdown gauges in
each producer. The first three failed raw-route negative controls are retained:
canvas setup reinstalls that proxy, so their faults now attach after setup. No
production submission wait, deadline or pixel assertion was relaxed.

All120criterion/profile bindings are now script-ready, including the eight former
source-only failure/recovery bindings. Candidate/default/strict-readiness checks
pass without admitting an artifact. Reviews remain null, wheels absent, original
142parents retained and originals_discharged zero. Section15 still requires a
structured result bound to the actual installed observed child; direct source
stdout is not that proof. Cumulative source/scope review, derived execution ledger,
exact-artifact index, original absence/control/host/CI/hardware gates and remaining
full parity work stay open. No runtime source commit or native leaf changed.

Sources, original failures, direct results, actual commands/exits/waits and
reconstruction references are retained in local
`build/runs/observed-submission-30/`. Its terminal manifest and applied cleanup
receipt determine the final retention/cleanup outcome; earlier in-progress review
wording does not override that actual evidence. No new environment, SDK or wheel
is needed for this source/script packet.

## Generated-line and Metal source checkpoint (ART-1/2, EV-1/2)

The [CI correction record](../../ci-contract-corrections.md) separates the missing
Metal CATransaction declaration from the stale generated-line empty-UBO assertion.
The original generated-line failure reproduces locally; exact runtime depth-range
metadata and a separate truly empty shader now pass 46,055 compiler checks on
Windows and Linux using existing inputs. Metal imports its declaring header;
actual Mac compilation and hardware qualification remain separate pending gates.

Preparation now inventories Objective-C++ native source as well as C++/headers.
Missing/changed platform-source controls are rejected with otherwise resealed
metadata; an intact set remains development-only. Current source/profile pins
include the previously omitted Apple source and preserve original Windows/WSL
observed identities with explicit non-Apple byte-equivalence. No old report is
relabelled, renderer/SDK rebuilt or independent review supplied. Source, failures,
commands, tiny retained contract artifacts and actual cleanup disposition are
recorded in `build/runs/ci-contracts-31/`. Existing full-closure and scoped handoff
gates remain unchanged.

## Additive execution-ledger source checkpoint (H1, INV-1..3, EV-1/2)

The [execution-ledger record](../../execution-ledger.md), closed mapping schema
and read-only validator implement the additive materialization route. The draft
contains 30 new required concrete pairs and 120 criterion bindings in a separate v2
ledger, preserving every original feature/profile/applicability/row/receipt.
All 142 original required parents remain unchanged and blocking. Unselected new
cross-product pairs stay explicitly optional/unreviewed, not nonapplicable.
No previous source report is transferred into a new positive row.

A semantic scope digest binds the complete baseline, new feature/profile scope,
applicability/dependencies, workflow and fixture mapping. Only selected proof and
review/admission state is excluded; the future artifact subject must pin complete
actual evidence bytes. The existing scope approval additionally binds the exact
execution-map digest. Applying actual bound source/scope reviews changes only
selected applicability flags without creating a hash cycle or global approval.
Missing approvals, omitted/narrowed parents or selected scope, changed history,
lost dependencies, wrong/duplicate destinations and multiple unaggregated
workflows are rejected even with recomputed seals. Synthetic approvals are tests,
not real review dispositions. Current real reviews remain null.

Existing inventory/evidence validators consume the derived ledger; their actual
member/profile/functional/absence/control requirements remain intact. This source
packet does not supply H2 implementation/scope review, H3 same-child branch proof,
H4 exact-artifact index/admission or P5 final review/current CI. No installed wheel,
SDK, native renderer, environment or upstream source history is rebuilt. Retained
source, actual commands/exits/waits and terminal cleanup disposition are in local
`build/runs/execution-ledger-32/`; only its applied receipt proves cleanup.
