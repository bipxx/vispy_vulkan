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

The [second Astra max review](../reviews/2026-10-24-astra-acceptance-detail-review.md)
adds six acceptance refinements, incorporated in specification section 10.
Flush no-op/saturation and post-submit ownership, finish presentation effects,
root adoption, concrete Tk coordinate policy, ledger validation and actual
granted-sample proof remain implementation/acceptance obligations.

The [workflow/specification Astra max review](../reviews/2026-10-24-astra-workflow-spec-review.md)
adds four refinements: workflow-bound observer evidence, required applicability
per feature/profile, profile-local dependencies and mode-specific backend
capability/configuration acceptance. Specification section 11 details these
requirements plus input vectors, state/query records and shader decisions.
The source checkpoints below implement B2 applicability and B1 workflow binding;
remaining inventory, implementation-review and installed gates stay open.

The [current-head Astra max review](../reviews/2026-10-24-astra-next-packet-review.md)
adds three accepted refinements: query logical state before draw lowering,
reject malformed/unsupported selectors before queue consumption, and separate
source/fixture review from final promotion-evidence review.
Specification section 12 and the detailed next-packet table define the next
bounded implementation and its exit checks. This documentation review does not
qualify source, artifacts or hardware.

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
| G2 — installed qualification | ART-1..2, EV-2..5 / proof | Applicable G1a..d criteria pass for the claimed workflow/profile; final source frozen for this packet | Exact Windows/Linux wheel identity, isolated consumer origin, actual Tk and state workflows, strict dependency/load/execution gates and original controls, shutdown plus Tcl ownership checks; CI on the new head. |
| G3 — threedee root cause | HOST-1..2 / Python + native observer owner | Existing pinned environment; independent of G1 | Initial three diagnostic starts + one targeted confirmation; actual stalled thread/wait-chain and control comparison. A fix needs causal evidence, regression and final-artifact full host gates. Otherwise preserve unresolved row with next evidence-driven experiment. |
| G4a — sampler indices | SH-1 / native | G0 relevant upstream fixtures; hash-identified known baseline for feasibility/source work; affected-profile G2 gates before qualification | Feasibility/lowering decision, uniformity/derivative rules, resource/reflection/limit cases, compile/negative controls and actual GPU outputs; affected workload requalification. |
| G4b — arrays and attributes | SH-2..3 / native + Python | G0 feature-specific requirements; G4a compiler/interface lessons where applicable | Layout/indexing/location/divisor/stride and cache-key decisions; valid/invalid inputs, updates, boundaries and rendered outputs. Separate uniform arrays from buffer/attribute claims. |
| G4c — geometry consumers | SH-4 / native | G0 named consumers; explicit design review | Supported expansion/rewrite subset and observable semantics; dispatch/draw/lifetime tests. Unsupported arbitrary geometry stages remain visible. |
| G4d — generated-line effects | SH-5 / native | G0 actual evaluator requirements; explicit coverage/depth/order design | Storage/image/atomic/barrier and early-test side effects preserve execution counts and visibility; existing refusals remain until the selected subset has GPU proof. |
| G5 — backend admission | BACKEND-1..2 / Python + native + proof | G0 required workflow and G1/G2 reusable acceptance | One named backend, no-GL creation/presentation design, complete lifecycle/input/capture profile and exact installed gates. Do not enable all legacy names at once. |
| G6 — host breadth | HOST-2 / Python + proof | Capability inventory and matching backend/native features | Each new host/version has pinned dependencies and a complete real workflow; no import-only admission. |
| G7 — hardware/performance | HW-1, PERF-1 / proof + native | Appropriate hardware and affected packet correctness | Separate native Linux GPU/Metal records; absent hardware stays blocked-external. Fixed workload median/tail and CPU/upload/GPU/readback/presentation breakdown, without unsupported speedup/scanout claims. |

## Native submission source checkpoint (G1d)

Native submission checkpoint (G1d): both flush APIs now enter one real
submit-without-completion-wait path. Capacity is checked before moving pending
work; a full ring raises contextual backpressure, preserving unsent work for
explicit progress/retry. Resource deferral cannot return a false successful
flush. Empty calls do not create submissions. Finish/readback no longer request
presentation; a subsequent explicit present copies the completed target.

Every submitted Ticket gets an Engine owner before Queue.Submit. Consumed draws
are cleared after irreversible submission, so later failures cannot replay them.
Frame ownership/counts commit at that boundary before optional completion/map
registration; a registration error retries delivery through progress without
resubmitting. Diagnostic controls hold completion delivery and inject one-shot
pre/post-submit, callback-registration and query-map failures. They establish
capacity/error branches without depending on a fast-loop timing accident.

The final candidate checks pass 168 Windows source cases, 146 WSL software cases,
67 CPU/source cases and the C++ frame-lifecycle contract. Thirty-one submission
cases cover both routes, empty/saturated calls, FBO/canvas state, finish without
presentation, mutation/deletion, loss/close and marked-query failures. The native
leaf builds reuse the verified Windows SDK and retained Linux libraries; Linux
recompiles all first-party units and remains an experimental build profile.
Neither producer origins nor the existing inplace native artifacts were changed.
Separate Linux scissor testing is still seven pass/one fail with granted sample
counts and loaded driver hashes; the toolkit/capture blocker is not repaired.

This advances STATE-2/4 and review A1/A2 source behavior. STATE-1/3/5 coverage,
remaining Tk acceptance, exact installed artifacts, strict absence gates and
independent implementation review still prevent G2 promotion. The installed
state smoke now requires both flush submissions before synchronization, finish
without presentation and four selected loaded-member hashes; its new behavior
has not yet been executed against a final wheel and does not replace the full
auditor or Tk/profile gates.

## Tk input source checkpoint (G1a, TK-6)

The remaining input packet now preserves native provenance and double-click
metadata, clears click/key/modifier state on focus loss, tracks both sides of a
modifier independently, adds META/Windows/Super and keypad aliases, distinguishes
printable text from control/navigation keys and retains press identity on release.
Wheel vectors preserve fractional/negative Windows ticks, Linux button 4/5
semantics and held mouse buttons. Host bindings and separate embedded-canvas
routing have live-widget regressions. The specification's section 11 records the
exact selected masks, key range, base double-click threshold and scope limits.
Focus cancellation completes all releases and clears gesture state before
surfacing a release callback failure, preserving the existing first-error policy.

Thirty new cases pass; final affected suites pass 130 Windows and 116 WSL
software cases, including existing real camera drags. Both profiles report nine
zero native shutdown gauges. Tests reuse the retained matching native leaves;
there was no native rebuild or installed-wheel promotion. Synthetic modifier and
Unicode vectors do not qualify physical devices, remapped layouts or macOS.
Linux capture/toolkit/scissor blockers, backend capability/configuration review,
remaining state-family coverage, G0 reconciliation and G2 gates stay open.

## Immediate-state source checkpoint (STATE-1..5)

The [operation/value contract](../../immediate-state-compatibility.md) now records
all 30 admitted entry routes, defaults, types, scopes, limits, fixture mappings
and legal exclusions. Seventy-four added cases bring the immediate-state suite
to 77: real raw depth/blend/stencil/cull/offset/line/sample output, invalid-value
recovery, granted queries and closed-target behavior. Four baseline overflow
regressions expose state poisoned by narrowing finite doubles to infinite floats;
the native parser now rejects that conversion before either offset field commits.
Five prior selector failures expose float/string/bool query coercion; the Python
route now requires integer selectors and live target owners.

Matching first-party native leaves pass the 77 cases on Windows/WSL. Broader
affected regressions pass 286 Windows and 272 WSL software cases; 19 CPU/package
contracts and the Windows C++ state contract also pass. Both native profiles have
nine zero shutdown gauges. Windows reuses its verified immutable SDK; Linux
recompiles all nine first-party units against unchanged retained libraries and
keeps its experimental provenance restriction. No inplace native origin changed.

This advances state-family acceptance, not every legal value or G2. Reversed
depth ranges, dither enable, multisample disable on multisample storage,
fractional polygon offset units, mixed blend-constant domains and remaining
enum/format combinations stay visible required work. The later Q1 checkpoint
adds the selected mutable-state queries; other selectors remain unimplemented.
Exact wheels, independent implementation review and all absence gates still
apply before promotion. Existing Linux scissor/toolkit blockers remain open.

## G0 ledger and promotion details

Workflow checkpoint (review B1): an additive v2 `workflow` row mapping now binds
qualified gates to the actual observed scenario, script bytes, arguments and
covered feature IDs. Controller/worker metadata, original dependency/discovery/
inventory/replay reports, independent controls and collector identity are
checked by `tools/compatibility_evidence.py` and recomputed by the ledger validator.
The original full auditors/controls are not replaced. Literal script argument
boundaries are preserved and mid-run script changes fail. A bounded real Tk/state
observer script exercises both flush routes and embedded/displayed behavior.

The selected CPU/protocol suites pass 141 cases each on Windows and Linux; one
existing symlink-venv case is explicitly outside this selection. The earlier
skipped Windows attempt failed its strict gate and remains retained. The new real
Tk/state flow passes separately on Windows and WSL software native candidates,
with nine zero shutdown gauges. No final wheel, actual new native-control packet
or G2 profile was qualified. Full inventory reconciliation, affected acceptance,
independent implementation review and exact installed-artifact work remain.
CPU CI now includes the real worker-metadata regressions in its inventory gate;
that exact 104-case selection passes locally. Current-head remote CI is separate.

Applicability checkpoint (review B2): ledger schema v2 and the validator now
use explicit required/optional/nonapplicable feature/profile decisions and
profile-local dependencies. An optional experiment no longer blocks completion;
missing required rows and hardware-blocked required work still do. Explicit v1
migration preserves evidence and all original required pairs, resets review and
refuses overwrite. Sixty-eight CPU cases pass, including the retained failing
optional-profile reproducer before the fix. All 142 seed pairs remain required,
unreviewed and incomplete. Full G0 inventory reconciliation remains pending;
the B1 source checkpoint above supplies gate-scenario binding. No installed or
hardware claim was promoted.

### Next bounded packets and review artifacts

The detailed planning records in specification section 11 apply before the
affected implementation. Preserve the historical checkpoints below, but use
this queue rather than restarting already completed source work:

| Order | Bounded deliverable | Review/acceptance stop condition |
| --- | --- | --- |
| 1 | Reconcile concrete G0 feature/profile rows for the current Tk/state work; map ordinary and mutation fixtures, known failures and candidate identities using the implemented v2 applicability mapping. | Schema validity alone is insufficient. V1 migration and missing-required, optional and blocked-hardware controls have source evidence above. Keep the full inventory unreviewed until method/example/event/host reconciliation is actually complete. |
| 2 | TK-6 input translation now has the source checkpoint above; map those fixtures into concrete G0 rows and the installed Tk scenario. | Preserve the section 11 policy and remaining physical/layout restrictions. G2 still needs exact-wheel functional/observer proof; source passes do not admit an installed profile. |
| 3 | Implement the bounded native mutable-state query packet in specification section 12, extending the existing operation/query records and fixtures. | Resolve native authority, old-module guard, return conversions, default rectangle/FBO scope and no-added-synchronization proof before promotion. Legal setter gaps remain separate packets. |
| 4 | Diagnose the two Linux G1c blockers separately with pinned, bounded controls. | A toolkit repair cannot close scissor correctness; a driver comparison cannot close toolkit lifecycle. Preserve exact failing receipts and granted-sample proof. |
| 5 | Freeze scoped G1 source and obtain independent source/fixture review; produce/reuse exact G2 artifacts, collect qualification receipts, then obtain independent promotion-evidence review. | The first review checks the patch and fixture mapping; the second checks final artifact/auditor/observer/CI receipts. Both must pass. Run complete installed/profile/functional/absence/control/shutdown gates. An old wheel receipt cannot acquire a new identity. |
| 6 | Select one G4/G5/G6 packet from the reviewed capability dependencies. | Retain the shader/backend design decision before expanding the surface; requalify dependent workflows against the changed artifact. |

G3's bounded threedee diagnosis and available G0 reconciliation may proceed
independently; this table does not authorize additional agents. Native Linux GPU
and Metal hardware records remain blocked-external while independent software
work continues. G2 is a scoped baseline for later packets, not final full-feature
closure: later implementation changes invalidate affected qualifications and
must receive their own exact-artifact evidence.

For each packet, record the affected ledger rows, planned files, fixture node IDs,
independent expectations, dependency-based rerun set, reused inputs and storage
estimate before execution. End with actual results, review dispositions and
cleanup evidence. Plan/spec edits alone need bounded document/reference checks;
they allocate no native build, environment or scratch history.

Implementation checkpoint: `compat/vispy-compatibility.json` is now the selected
draft ledger, with versioned JSON schema, source-only validator and bootstrap
generator. It contains 142 entries from hash-verified pinned public namespace
exports and backend registration; duplicate gloo exports retain both source
references. Forty-eight CPU regression cases pass, including stale receipt,
missing wait, collection/skip, dependency, installed-audit and observer-control
negative cases. CPU CI now checks this gate before native compilation.

This is partial G0 implementation: all seed rows are `not-inventoried` in an
unassigned profile, `reviewed` is false, and the full-completion command fails.
Examples, method-level contracts, scene wildcard aliases, events, host mappings,
concrete required profiles and application of the adapter to actual retained
auditor/observer outputs remain to be reconciled. No host receipt was promoted and no support percentage
follows from 142 seed entries. The [inventory guide](../../compatibility-inventory.md)
documents the schema, receipt protocol and remaining integration work.

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

Second-review ownership follow-up: explicit-parent embedding now adopts the
interpreter for the host, including a previously VisPy-created root. Final release
also preserves unrelated pending jobs, bindings, Tcl commands/namespaces and
variable-trace callbacks when no child window remains. Weak ownership of VisPy
images avoids mistaking a retained old image for host work. New source cases
cover each resource kind, host image, explicit opaque-state adoption, query
failure/explicit retry, shared final release and adopted-root re-entry. The final
Windows Tk/state/capture suite passes 100 cases; WSL Tk/state passes 86, with 12
packaging/source cases. Linux capture failures remain separate and open. This
advances TK-1..4/A3 source acceptance without promoting an installed profile.

G1c progress: fourteen new independent capture/coordinate cases pass on Windows;
the combined Windows suite has 86 passing cases plus thirteen package/source
contracts. Authored quadrants test odd sizes, alpha, cropped byte/float capture,
resize/loss, four samples, embedding, Tcl image retirement and local Tk scale
settings. These local scale controls are not mixed-monitor DPI qualification.
Monitor-index fullscreen requests are now explicitly refused rather than
silently converted to bool; monitor selection remains unsupported.

Linux G1c is incomplete. The existing final Linux renderer fails an exact
four-sample clear boundary after odd-size resize; the isolated case reproduces
it and retains actual/expected arrays. Do not change its categorical expectation
or transfer the Windows pass. A separate Xlib/XCB abort occurs while creating a
Tk Label; a plain Tk control without VisPy or Vulkan reproduces the same abort.
The current WSL managed-Python toolkit environment is therefore not qualified
for that workflow, and system Python has no Tk comparison available. Full logs,
the first-failure receipt and controls are retained with the G1c run. Resolve
the toolkit runtime/profile and add the MSAA clear fix to the next affected
native packet before G2; no old qualified row is silently promoted or erased.

Scissor isolation: a headless control reproduces the 477-pixel mismatch without
Tk. Reversing the size order fails immediately at 301x177 and passes at 257x129,
so "resize-only" is too narrow a diagnosis. An ordinary vertex-buffer draw using
hardware scissor reproduces it; an otherwise comparable shader-discard rectangle
has zero differences. This isolates a multisample scissor path, not a proven
project-source or driver root cause. The producer runtime.cpp hash matches the
current source. [Mesa's official 25.3.0 notes](https://docs.mesa3d.org/relnotes/25.3.0.html)
list an llvmpipe scissor-plane fix;
it is a candidate explanation, not verified by this investigation. Test a pinned
isolated driver before introducing a shader workaround that could change user
shader side effects. `tests/native/test_scissor_boundaries.py` retains the
toolkit-free exact acceptance contract. Existing failed-driver evidence remains.

The toolkit-free boundary suite now includes both zero and nonzero rectangle
origins: eight Windows cases pass; Linux passes seven and fails the four-sample
301x177 nonzero-origin case. The zero-origin rectangle alone passed and would
have missed this defect. Retain that contrast when evaluating a driver change.

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

## Detailed next-packet deliverables

Use specification [section 12](../specs/2026-10-24-vispy-compatibility-gap-closure.md#12-next-packet-designs-and-exit-checks)
for the next implementation boundary. The immediate-state source checkpoint
above remains the baseline; do not rerun its native build merely for this plan.

| Packet / responsibility | Concrete output | Exit / explicit remaining work |
| --- | --- | --- |
| Q1 / native + Python | Native committed-state query projection and versioned binding; guarded ordered Python route; per-selector type/scope/default records; CPU and native fixtures. Planned source areas: runtime state/query helper, runtime API/binding, dawn_parser, existing state and immediate-state suites. | Both queued and immediate setters agree with native query/output; old natives cannot consume work; default rectangle/FBO decisions are tested; observation adds no submit/wait/present. No setter-gap or installed-artifact promotion. |
| I1 / coordinator + proof | Concrete Tk/state feature/profile/fixture mappings in the canonical v2 ledger, with original required scope and receipts preserved. | Reviewed selected slice, validated dependencies and honest unresolved scope; the full generated inventory remains unreviewed until its remaining families are reconciled. |
| B4 / Python + proof | Standalone/embedded capability and configuration record, including resource sharing, requested/granted attachments and thread ownership. | Every selected advertised capability has observable behavior or contextual refusal, constructor/mutation/teardown fixtures and an affected-row mapping. |
| L1..Ln / native | One design and distinguishing output packet for each legal state-value gap in section 12. | Guard removed only for the proven subset; failure retains its counterexample. Do not couple independent software work to unrelated hardware blockers. |
| G2 / proof | Source freeze and independent source/fixture review; exact artifacts and complete installed/observer/CI receipts; independent promotion-evidence review of those final receipts. | Both review checkpoints must pass. Source passes and this plan review cannot substitute for implementation review, exact installed identity or any of the three absence gates. |

Q1 can proceed while I1/B4 assessment and bounded Linux/host investigations
continue independently. Its selected requirements and fixture mappings must be
recorded first. L1..Ln are not all prerequisites for a scoped Tk/state G2 packet;
every required criterion for the selected workflow/profile still must pass.
A narrower demonstrated subset must be represented explicitly and cannot
qualify a broader required row. Excluded required behavior remains an explicit
full-closure blocker. No new backend/shader admission may infer support from a query implementation.
The ownership labels assign responsibilities and do not request new agents.

The historical numbered repair checklist above records the original sequence.
The current queue and these deliverables govern remaining work; source-fixed
input and flush behavior must not be treated as missing implementation again.

## Validation, storage and handoff

| Decision/check before implementation or promotion | Required deliverable |
| --- | --- |
| G0 ledger integrity | Select canonical ledger, versioned schema and validator; reconcile existing inventories, validate references and same-artifact promotion. |
| G1a adopted-root ownership | Define adoption/exclusive destruction policy; retain no-child user timers, idle work and bindings through VisPy teardown. |
| G1c coordinate policy | Default Tk client/framebuffer 1:1 contract, positive Configure authority and zero-size behavior; test nondefault public px_scale separately. |
| G1d submission design | Define flush inclusion/linearization and saturation behavior; controlled incomplete tickets, no-op versus submit outcomes and post-submit failure ownership. |
| G1d finish regression | Verify both public finish routes complete work without presentation/GUI draw or target/state changes; retain independent counter proof. |
| Linux G1c repair | Separate runtime/driver profiles; actual granted samples and loaded-driver identity; finite fresh-process toolkit controls and exact boundary expectations. |
| G2 promotion | Final installed-wheel member/closure audit, mapped functional cases and all three observer gates with controls; bind gate scenarios to covered workflows and reject unrelated-workflow receipts. No stale source-only promotion. |
| Backend capability acceptance | Standalone/embedded capability/options and requested/granted configuration table; sharing/update/consumer-close fixtures and explicit UI-thread policy. |

The specification's [executable acceptance records](../specs/2026-10-24-vispy-compatibility-gap-closure.md#10-executable-acceptance-records)
define the minimum G0 ledger fields, flush submission/saturation proof, separate
Linux blocker records and packet receipts. Apply those criteria before promoting
an implementation; documentation detail alone closes no runtime finding.

The next bounded work must distinguish two independent Linux investigations:
repair or select a pinned toolkit runtime using a plain-Tk control, and compare
the headless multisample scissor reproducer under an isolated pinned driver.
Neither result transfers to the other. Preserve existing failures, reference
inputs by hash, and change one diagnostic variable at a time. The bounded native
flush design now has source-functional candidate evidence above; its capacity
error is an explicit failed call, never a successful deferred submission.
G2 remains dependent on the affected G1 paths
and an exact candidate artifact, rather than on a favorable source-only retry.

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
