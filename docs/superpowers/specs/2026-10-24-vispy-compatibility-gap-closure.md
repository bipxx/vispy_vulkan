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
For example, reversed depth ranges and enabling GL_DITHER currently have native
refusals despite their function names being allowlisted. Give such legal
exclusions inventory rows and future acceptance criteria; do not label them
invalid arguments or treat the whole operation as fully compatible.

STATE-2: Earlier queued uploads/draws and framebuffer binding changes execute
before an immediate state command. State remains isolated to the selected canvas
and correct framebuffer scope. Query/cache values agree with successfully
executed native state. Invalid values do not partially mutate that state/cache;
the fate of earlier successfully executed queued work is documented separately
from rollback. Test nested FBOs, A/B/A canvas selection and state after errors.

STATE-3: The current three pixel cases establish selected clear/scissor/mask and
ordering behavior. Add coverage by state family for depth, blending, front/back
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

Before promotion, an independent implementation review checks the actual patch,
requirement-to-fixture mapping, retained failures and final artifact receipts.
The plan review itself is not that implementation review. Record finding IDs,
dispositions and remaining restrictions; unresolved required findings prevent
promotion of their affected rows.

Dependencies are evaluated per claimed feature/profile, not as an all-platform
barrier. Shader feasibility and source work can start from a hash-identified
known baseline when their actual prerequisites hold, even while an unrelated
Linux Tk profile fails. G2 qualification for a particular affected workflow
still requires that workflow's G1 criteria and exact installed artifact. Such
independence neither qualifies the failing profile nor closes full scope.
