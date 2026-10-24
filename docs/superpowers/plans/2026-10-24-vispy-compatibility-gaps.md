# VisPy compatibility gap-closure execution plan

Date: 2026-10-24. Status: source implementation exists; Astra review found
functional and acceptance gaps. The follow-up is not ready for qualification.

Requirements and acceptance are defined in the
[gap-closure specification](../specs/2026-10-24-vispy-compatibility-gap-closure.md).
The [original runtime-removal plan](2026-10-23-opengl-runtime-removal-plan.md)
retains its mandatory application gates. This plan does not restart completed
renderer work or redefine the 13/14 host matrix as overall feature completeness.

The [Astra max review and finding disposition](../reviews/2026-10-24-astra-compatibility-plan-review.md)
records ten accepted findings; specification changes do not mark the associated
implementation or qualification work complete.

## Baseline and review disposition

- Earlier implementation PR #13 merged. The installed matrix still has one
  mandatory unqualified row: Windows napari-threedee startup.
- Follow-up PR #14 contains Tk raster presentation and selected immediate state
  calls. Twelve local integration cases pass on Windows and WSL Linux, and 13
  package/source checks pass. Those counts do not qualify a new installed wheel
  or every exposed state call. Installed and hardware evidence stay separate.
- Astra found concrete Tk input/ownership/event-loop gaps and an existing
  gloo.flush submission gap. Auto-merge for PR #14 was disabled pending fixes;
  do not restore it merely because the current tests/CI pass.
- Original draft release assets describe the earlier candidate. Do not replace
  their scope or hashes with a newer source commit without a new artifact record.

## Execution ownership and order

Use the existing ownership boundaries: Python/hosts owns Tk and application
integration; native owns submission, shaders and resource lifetime; packaging/
proof owns wheel identity, profiles, observers, CI and evidence. The coordinator
owns integration, the inventory ledger, review disposition and shared storage.
These are responsibility assignments, not instructions to spawn more agents.

Inventory and bounded host diagnosis can proceed independently. Fix known Tk
and flush behavior before adding more backends or shader surface. A requirement
marked blocked-external does not prevent independent software work.

| Packet | Requirement IDs / owner | Dependencies | Exit evidence |
| --- | --- | --- | --- |
| G0 — inventory and baseline | INV-1..3, EV-1..5 / coordinator + proof | None; reuse existing inventories and pins | Reviewed public-workflow ledger with state, fixture, required capability, owner, exact failure/evidence and source/artifact identity; unknown rows stay unknown. Record CI/PR state at handoff. |
| G1a — Tk input and lifecycle | TK-1,4,6 / Python | G0 baseline; existing source/native binaries | Fix pressed-button tracking and real camera drags; explicit-parent NoDefaultRoot, multiple Application objects, partial construction failure, external destruction, quit/re-entry and public Timer.running tests. |
| G1b — Tk event loops/errors | TK-2..4 / Python | G1a ownership decisions | Manual pump, Application.run and external mainloop progress/error tests; first failure retained, native readiness/presentation exceptions delivered, healthy canvas usable, bounded animation and cancelled generations. |
| G1c — Tk coordinates/capture | TK-5,7,8 / Python + proof | G1a/b | Independently expected corner pixels and camera interaction; alpha/cropped/floating capture; odd sizes; 125/150/200% policy, minimize/restore, resize/loss/close and Tk image/job release. No claim based on candidate-vs-candidate comparisons. |
| G1d — state and nonblocking flush | STATE-1..5 / native + Python | G0 state inventory; ownership contract reviewed | Enumerated state-family coverage and invalid-value isolation; glFlush and gloo.flush share actual native submission, checked before finish/readback/present; no added completion wait and resource owners retained. |
| G2 — installed qualification | ART-1..2, EV-2..5 / proof | G1a..d pass; final source frozen for this packet | Exact Windows/Linux wheel identity, isolated consumer origin, actual Tk and state workflows, strict dependency/load/execution gates and original controls, shutdown plus Tcl ownership checks; CI on the new head. |
| G3 — threedee root cause | HOST-1..2 / Python + native observer owner | Existing pinned environment; independent of G1 | Initial three diagnostic starts + one targeted confirmation; actual stalled thread/wait-chain and control comparison. A fix needs causal evidence, regression and final-artifact full host gates. Otherwise preserve unresolved row with next evidence-driven experiment. |
| G4a — sampler indices | SH-1 / native | G0 relevant upstream fixtures; G2 stable artifact baseline | Feasibility/lowering decision, uniformity/derivative rules, resource/reflection/limit cases, compile/negative controls and actual GPU outputs; affected workload requalification. |
| G4b — arrays and attributes | SH-2..3 / native + Python | G0 feature-specific requirements; G4a compiler/interface lessons where applicable | Layout/indexing/location/divisor/stride and cache-key decisions; valid/invalid inputs, updates, boundaries and rendered outputs. Separate uniform arrays from buffer/attribute claims. |
| G4c — geometry consumers | SH-4 / native | G0 named consumers; explicit design review | Supported expansion/rewrite subset and observable semantics; dispatch/draw/lifetime tests. Unsupported arbitrary geometry stages remain visible. |
| G4d — generated-line effects | SH-5 / native | G0 actual evaluator requirements; explicit coverage/depth/order design | Storage/image/atomic/barrier and early-test side effects preserve execution counts and visibility; existing refusals remain until the selected subset has GPU proof. |
| G5 — backend admission | BACKEND-1..2 / Python + native + proof | G0 required workflow and G1/G2 reusable acceptance | One named backend, no-GL creation/presentation design, complete lifecycle/input/capture profile and exact installed gates. Do not enable all legacy names at once. |
| G6 — host breadth | HOST-2 / Python + proof | Capability inventory and matching backend/native features | Each new host/version has pinned dependencies and a complete real workflow; no import-only admission. |
| G7 — hardware/performance | HW-1, PERF-1 / proof + native | Appropriate hardware and affected packet correctness | Separate native Linux GPU/Metal records; absent hardware stays blocked-external. Fixed workload median/tail and CPU/upload/GPU/readback/presentation breakdown, without unsupported speedup/scanout claims. |

## G0 ledger and promotion details

Before new porting work, record each selected upstream feature with a stable ID,
source path/API and upstream pin, selected ordinary and mutation/failure fixture,
required capabilities, owner, platform/profile, source/wheel identity, state,
evidence links and next action. Use the finite reviewed inventory for any future
coverage summary. Do not derive an overall percentage from host rows or GPU case
counts. Prefer extending an existing machine-readable inventory over a second
incompatible source of truth.

The allowed states and scope rules are in EV-1..5. Missing tests are not
"supported"; implemented-but-untested code remains explicit. Native compiler
feasibility failures produce a small decision record, not repeated full builds.

## First implementation packet after review

Progress: pressed-button tracking is implemented with focus-loss cancellation
and outside-coordinate releases. Three new regression cases verify button-state
sequences and real PanZoom/Turntable drags with changed camera state and pixels.
All twelve Tk cases pass on Windows; WSL software Vulkan passes those twelve
plus three immediate-state cases. This is source evidence using reused native
binaries, not installed qualification. Remaining TK-6 modifier/double-click and
ownership/event-loop work stays open; R1 is partially addressed, not closed.

Ownership follow-up: interpreter-level application tracking now preserves live
canvases across another application's quit and retains unrelated Tk windows.
Canvas preparation selects an explicit parent's interpreter before default-app
creation, including NoDefaultRoot embedding. Early widget/image/binding failure
unwinds owned allocations while preserving the originating exception. Quit
updates public timer state; restarting binds a recreated root. External root
destruction and re-entry are covered. Twenty-six combined Tk/state cases pass
on Windows and WSL software Vulkan, plus thirteen package/source contracts.
R3 has source regression evidence for these cases, but full lifecycle/loop/error
and installed-artifact acceptance remain open; do not close TK-1/4 wholesale.

Loop follow-up: shared interpreter progress and callback delivery now distinguish
manual pumping, Application.run and external mainloops without replacing the
user's Tk handler. Source tests cover draw, readiness, native progress, resize,
input, timer, presentation and image failures in all three modes; corrected
failures recover on explicit redraw. Further cases cover idle polling, owned-loop
interruptions, first-error preservation, independent-canvas recovery, device loss
and timer restart generations. The combined Tk/state suite has 62 passing cases
on Windows and WSL software Vulkan, with 13 package/source checks. This is source
evidence for G1b, not full TK-1..4 or installed-profile qualification; teardown
failure paths and G1c coordinate/capture acceptance still need work.

Teardown follow-up: an escaping Canvas close callback now still runs backend
cleanup and forgets the current canvas. Timer.stop records stopped public state
even if backend cancellation raises. Tk quit attempts independent resources,
preserves the first error, logs secondary errors and prevents callback-driven
resurrection while quitting. Unretired native IDs and uncancelled jobs keep their
owners/handles for explicit quit retry; failed releases are not immediately
retried inside the same operation. Root destruction finishes other timer/canvas
cleanup before delivering a callback failure. Seventy-two combined source cases
pass on Windows and WSL software Vulkan, plus thirteen package/source contracts.
The final headless cleanup check uses the existing viewport API so it works with
the reused Windows native binary. This expands TK-1..4 evidence but does not close
all lifetime interleavings or installed qualification. G1c is the next packet.

1. Reproduce the missing pressed-button state using a real SceneCanvas camera.
   Add regression expectations before changing input dispatch; include release
   outside/focus loss and modifiers. Do not weaken camera code to hide bad events.
2. Define root/interpreter and run-loop ownership for explicit parents,
   NoDefaultRoot, shared Application objects, external destruction and re-entry.
   Repair teardown and public timer state around that ownership model.
3. Adopt one callback-error/native-progress contract for all three loop modes.
   Verify readiness/resize/input/timer/presentation failures as well as draw
   failures. Preserve first error and cleanup diagnostics separately.
4. Replace self-referential image checks with independent expected corners and
   the same expected orientation after resize and loss. Exercise documented
   physical/logical input and framebuffer dimensions and capture semantics.
5. Implement native submit-without-wait for both flush APIs, then test submission
   before any synchronizing operation. Cover FBO/offscreen, empty/repeated flush,
   interleaved canvases, pending-resource mutation/deletion, loss and shutdown.
6. Reuse the matched SDK/native dependency inputs for one required native rebuild
   if submission code changes. Package exact candidate wheels once, qualify the
   installed Tk/state profiles and run affected regressions plus required CI.
7. Resolve Astra findings in a review disposition record. Only then restore
   normal auto-merge. Merging still does not close the independent threedee row
   or establish full VisPy parity.

Useful existing entry points are `_dawn_tk.py`, `gloo/gl/dawn.py`,
`gloo/wrappers.py`, `cpp/runtime.cpp`, `cpp/runtime_state.hpp`,
`tests/native/test_tkinter_backend.py`, `test_dawn_immediate_state.py` and
`tools/immediate_state_wheel_smoke.py`. Paths are relative to the source roots
shown in the specification. Extend current suites rather than creating copied
harness/source histories. The installed state smoke covers one 96-pixel scene,
not Tk or the entire state allowlist.

## Validation, storage and handoff

Follow RET-1, LIC-1, root AGENTS.md and [build hygiene](../../build-hygiene.md): one 20 GiB
scratch budget and 10 GiB free reserve across workers, preflight before scratch,
backing-volume checks for WSL builds and verified terminal cleanup. Reuse
existing environments and artifacts for investigation. New documentation does
not justify native builds, source snapshots, wheel repacks or environment clones.
A necessary larger toolchain build needs an explicit versioned profile.

Each packet retains source identity/patch, original licenses, exact commands,
exit/wait results, independent expectations, passing and meaningful failing
receipts, scope limits and a cleanup result. Keep stable artifacts once and
reference their hashes; do not recursively archive older runs. Never mutate
identity-pinned origins or retry blocked cleanup paths. AGPL implementation and
original BSD/third-party notices remain attached. Skip cybersecurity work.

A handoff states which requirement IDs passed, which remain open, the exact
artifact/profile tested, external blockers, review disposition and next bounded
packet. CI must match the changed head; no previous green run qualifies new code.
Do not publish the draft release, hide failed mandatory rows or advertise full
parity while their existing gates remain unmet. Native Linux GPU and Metal can
only leave blocked-external with actual suitable hardware evidence. The user has
deferred photodiode/LDAT and extreme pixel/scanout parity work.
