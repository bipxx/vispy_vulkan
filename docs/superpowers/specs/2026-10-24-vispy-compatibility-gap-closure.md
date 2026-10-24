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
GL-shaped state entry points. Local evidence comprises nine Tk integration cases
and three immediate-state cases on Windows Vulkan and WSL software Vulkan, plus
13 package/source contracts. These do not cover every entry point, Tk event-loop
mode, dependency closure or upstream visual. No new local native wheel was built.

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
completion. Immediate `glFlush` remains unsupported until a real submit-without-
completion-wait path exists. Logging/parsing a GLIR `glFlush`, substituting
`glFinish`, or presenting a window does not implement that contract. The new
path must retain submitted resource owners through completion and work for
offscreen/FBO targets, multiple canvases, repeated/empty flushes, loss and close.
Verify submission/progress and ordering with native counters/control work;
wall-clock latency alone cannot establish absence of a GPU wait.

This requirement covers both immediate `gloo.gl.glFlush()` and the existing
public `gloo.flush()`/context flush wrapper. The latter currently queues the
same logging-only native operation; changing its documentation to unsupported
does not fix the advertised functionality. Test submission before any readback,
present or `glFinish` can mask the problem, and verify `finish_calls` does not
increase. Both routes must use the same native submission/lifetime contract.

STATE-5: Queries report actual dimensions, formats and granted limits in the
correct units and active target scope. Do not infer aggregate sampler budgets
from a single-stage limit or invent precision. Preserve synchronous exceptions;
`glGetError() == GL_NO_ERROR` is not evidence that arbitrary GL semantics work.
Raw object creation, raw shader/program APIs and raw drawing need a separate
inventory/design before expanding their surface.

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
state smoke's two member hashes are supplemental and cannot replace that audit.

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
