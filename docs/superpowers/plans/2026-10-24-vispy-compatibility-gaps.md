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

## Current execution queue after source checkpoints

The [executable-handoff Astra max review](../reviews/2026-10-24-astra-executable-handoff-review.md)
and [specification section 15](../specs/2026-10-24-vispy-compatibility-gap-closure.md#15-executable-handoff-from-proposals-to-scoped-qualification)
refine the current queue. H0 is retained and cleaned; H1's additive execution
ledger and H3's worker-bound functional results have source implementations.
Their checkpoints below supersede the earlier pending instructions. Independent
cumulative implementation/scope review (H2), the exact-artifact qualification
index (H4), installed evidence and final promotion (H5) remain open. Section 16
of the specification defines the next bounded H4 implementation contract.
Source implementation supplies no approval or installed qualification.

This section governs remaining execution. The packet tables and numbered repair
lists below retain their design/history; a later source checkpoint supersedes
an earlier instruction to implement the same packet. Source completion does not
mean independently reviewed or installed-qualified completion.

| Order | Current state and next concrete output | Exit before advancing the claim |
| --- | --- | --- |
| 1 — I2 / coordinator + proof | The development manifest now contains 15 proposals, 30 Windows/WSL pairs and three executable workflows. Review its exact scope and reconcile methods/examples/events/wrappers into proposed conservation mappings, retaining residual required criteria. | Preparation validation passes without claiming qualification; independent scope review covers every proposed origin/successor criterion. Untouched and residual seed obligations remain blocking full closure; selected scoped work need not wait for all 142 mappings. |
| 2 — implementation review / coordinator | Freeze and review the cumulative Q1/B4/L1, conservation/candidate tooling, shared-progress/shutdown and resource-workflow source/fixture changes, including their auditor bindings. Map unresolved findings to affected pairs. | Independent source/fixture review passes for the selected candidate. This Astra plan review does not satisfy that gate. Do not rebuild those packets merely to repeat their pass counts. |
| 3 — bounded correctness / Python + native | Keep the original Tk8.6 profile blocked; verify the selected Tk9 profile independently and diagnose MSAA scissor separately. Retain the required Windows threedee diagnostic packet. Select each remaining legal-state, input/DPI or lifecycle gap from concrete candidate dependencies. | Each required failure has causal evidence and a distinguishing regression, or remains a visible blocker. Hardware absence cannot excuse independent software failures. |
| 4 — G2 / proof | Freeze the reviewed source, reuse matching artifacts or build each changed native leaf once, then audit exact installed workflows and all absence gates/controls. | Exact-member/closure audits, functional/shutdown receipts, current-head required CI and independent final promotion-evidence review pass for the same artifacts and profiles. Original mandatory host gates remain required. |
| 5 — G4/G5/G6 and full G0 / assigned owner | Extend one named shader/backend/host subset at a time; reconcile the remaining methods, examples, events and visual families. | Reviewed finite full inventory and every applicable required pair qualified before full compatibility/complete-removal claims. No completion percentage from the seed count. |
| 6 — G7 / proof | Measure fixed performance workloads after their correctness gates. Native Linux GPU and Metal retain separate hardware requirements. | WSL software is labelled separately; Metal stays experimental without a Mac. Optical/scanout instrumentation remains deferred. |

### Concrete next packets after this review

This table refines the queue above and supersedes stale pending wording in its
historical checkpoints. Roles preserve existing ownership; the table does not
authorize spawning implementation agents.

| Packet / role | Owned output and prerequisites | Required exit and stop condition |
| --- | --- | --- |
| H0 — workflow owner | Source complete, retained and cleaned: `observed-submission-30` using the existing source script/test files and retained native leaves. Both selected profiles now pass 18 source cases and direct entry points; all120bindings are script-ready. See the source checkpoint below and require the retained terminal cleanup receipt before handoff. | Verify both route/delay pairs on each selected development profile, strict counters/errors/recovery/host ownership and nine shutdown zeros. Retain the first failed controls. Update actual fixture/script hashes and the eight source-only bindings only after their branch checks pass, then retain/apply/verify terminal cleanup. No wheel/SDK build. |
| H1 — inventory/coordinator | Source materialization implemented; independent scope review remains pending. Freeze preparation/coverage and the cumulative source-review record. Design the mapping declaration and separate derived execution ledger against that frozen baseline; do not edit the baseline in place to add proposal IDs. | Reviewed selected operation/value/criterion map, exact proposal-to-row links and transitive same-profile dependencies. Negative controls reject changed/lost parents, duplicate/omitted mappings, optionalized dependencies and invented origins. All 142 original obligations persist; global closure stays incomplete. |
| H2 — independent implementation reviewer | Review cumulative runtime, fixtures, observers and inventory/preparation/coverage tools from the last independently reviewed base, including H0 and retained failures. Review H1 scope separately using the existing source/scope review kinds. | Exact input hashes, findings/dispositions and affected pairs. Relevant later edits renew affected reviews. This Astra plan review supplies neither approval. If a reviewer is unavailable, retain the review blocker and continue independent source-only work. |
| H3 — observer/proof owner | Source transport and controls implemented; independent review and installed evidence remain pending. Retain the closed branch-result transport in the existing script/worker/controller/normalizer chain. Use the exact four submission variants, two progress orders and resource failure/recovery contract in section 15. | Same-child result/hash/exit/wait bindings and semantic negative controls pass, including duplicate/missing/wrong branches, source/unrelated result substitution, missing output and wrong recovery/cleanup. Existing three absence gates and independent controls remain intact; changed observer code needs renewed source review. |
| H4 — artifact/proof owner | Define the closed qualification index and read-only validator, immutable subject and detached review/CI envelope. Freeze a requested admission set and establish profile/blocker/producer applicability before packaging. H1/H2/H3 reviews and affected correctness are prerequisites for real qualification. | Synthetic complete join plus stale/missing/wrong-input controls pass. Reuse matching admitted native artifacts or build changed leaves once. Actual scoped admission requires exact wheel/member/closure, branch/functional/absence/control/shutdown receipts and required CI for the declared head. Experimental Linux producer provenance stops Linux admission; Windows can proceed independently. |
| H5 — independent promotion reviewer/coordinator | Review the immutable real subject and every requested pair/dependency, required head CI and actual retention/cleanup. | Report explicit requested/proved/blocked/missing sets. Strict admission fails if any requested criterion fails; do not filter failed profiles afterward. Keep draft/merge and mandatory complete-removal gates in force. Scoped admission never asserts total candidate or full VisPy closure. |

H1/H3/H4 schema and source-only design work may proceed while reviews are pending;
real qualification cannot advance past affected prerequisites. Do not make
hardware availability or all-parent reconciliation a prerequisite for unrelated
bounded source work. Keep the independent Linux scissor and Windows threedee
diagnostics, remaining legal state/shaders/backends/hosts and full G0 reconciliation
as required work, rather than replacing them with this selected handoff.

The [Astra review and disposition](../reviews/2026-10-24-astra-candidate-conservation-review.md)
and [specification section 13](../specs/2026-10-24-vispy-compatibility-gap-closure.md#13-current-candidate-and-obligation-conservation-contracts)
define this queue's candidate, conservation and diagnostic deliverables. This queue changes no mandatory release
requirement and authorizes no additional agents or dependency builds.

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
the current execution queue near the top rather than restarting source-fixed work:

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

## Retained packet acceptance contracts (current state above)

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

Historical dependency note: Q1 could proceed alongside I1/B4 assessment.
Q1/B4 now have source checkpoints; remaining mapping, review and bounded
Linux/host investigations proceed from the current execution queue. Its selected requirements and fixture mappings must be
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


## Current preparation handoff and Astra review

The [latest Astra max review](../reviews/2026-10-24-astra-preparation-handoff-review.md)
and [specification section 14](../specs/2026-10-24-vispy-compatibility-gap-closure.md#14-current-delivery-contracts-after-candidate-preparation)
govern the next handoff. P1 reviews the existing candidate's selected criterion
map and residuals; P2 reviews the frozen cumulative implementation and fixtures;
P3 makes each required failure/recovery branch executable under observation;
P4 joins exact artifacts to the existing qualification evidence; P5 independently
reviews promotion. Independent source work may proceed while a review is pending.

The preparation v1 format remains development-only. A separate versioned
qualification index must join its frozen identity to canonical/v3 obligations,
exact installed members and existing workflow-bound receipts. Do not mutate the
preparation into an admission format or let the new index replace an auditor.
The ordinary state/resource observer scripts do not prove every failure branch
currently listed as a source fixture. Resolve that criterion-to-scenario mapping
before attempting installed qualification, with negative controls for wrong or
unexecuted branches, conjunctive required-variant coverage and harness-verified
expected errors that preserve actual process outcomes.

The selected mapping can proceed before all 142 origins have concrete successors;
untouched parents and uncovered residuals still prevent full closure. Retain the
original mandatory threedee row, separate Windows/WSL identities and experimental
native Linux GPU/Metal status. Run final native GUI profiles serially on this
shared machine, preserve deadlines/pixel thresholds, and report terminal cleanup
only after its exact receipt exists. No agents, builds or release-scope changes
are authorized by this execution table itself.


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

## Observed submission branches source checkpoint (P3, STATE-2/4)

The four actual raw/gloo immediate/delayed capacity/retry branches now pass in the
composite on both selected development profiles. Eighteen affected native cases
and the actual direct entry point pass per profile, each with nine zero shutdown
gauges. Missing/wrong errors and missing retries are rejected; first failed raw
negative controls and the corrected post-setup injection ordering remain retained.

The four selected failure/recovery criteria and eight bindings now reference the
real composite fixture. All120bindings are script-ready, not installed observed
or qualified. The production CPU contract checks strict readiness while retaining
142 original obligations, zero discharge and pending review. No runtime source,
native artifact, environment or SDK changes. Existing historical observations
remain attached to their original inputs; current focused source profiles carry
18cases rather than relabelling the previous69/68results.

Retain and verify `build/runs/observed-submission-30/` terminal cleanup before H1
handoff. Next freeze the reviewed baseline and design the separately derived
execution ledger/mapping, while H2 source/scope approval and H3 worker-bound
results remain required before real P4 qualification. The original scissor,
threedee, legal-state/shader/backend/host and full inventory gaps remain open.

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

## Observed-child functional-result source checkpoint (H3, EV-2..4)

The [functional-result contract](../../functional-results.md) now captures an
explicit JSON export from the actual isolated worker's returning namespace.
The worker binds its PID/workflow/mode and payload hash; the controller binds
the complete envelope and original worker-report hash. The existing normalizer
checks discovery and replay functional edges alongside every original absence,
member/environment/control/shutdown requirement. No stdout/result-file fallback,
new absence gate or success override is introduced. Later audit/cleanup failure
still fails even when the earlier functional payload was good.

The Tk contract enforces the exact ordinary/resource, two progress orders and
four submission route/delay branches, including actual retirement, counter/color,
error/traceback, explicit retry and cleanup/restoration records. Execution mappings
now bind each selected criterion to its exact contract/branch IDs; substituting
another existing branch is rejected after resealing. The same existing scope
approval covers these fields through its execution-map digest. Complete collector
Python/C sources and the native-image snapshot helper are frozen in preparation.

CPU controls and real isolated source-wrapper runs exercise transport and actual
Tk results using unchanged native artifacts. Source mode, wrapper identity and
arguments remain explicit; these are not installed candidate workflow or native
absence/control receipts. Independent cumulative source/scope review, exact
artifact index and installed qualification, final CI/promotion and all original
host/platform/full parity requirements remain open. No wheel, SDK, dependency
source history or environment is rebuilt. Source/evidence/actual exits/waits and
terminal cleanup disposition are retained in `build/runs/worker-results-33/`.

## H4 implementation sequence after the latest Astra max review

The [qualification-index review](../reviews/2026-10-24-astra-qualification-index-review.md)
and [specification section 16](../specs/2026-10-24-vispy-compatibility-gap-closure.md#16-qualification-index-implementation-contract-h4-ev-15-art-12-ret-1)
refine H4 without supplying H2 implementation/scope approval. H0/H1/H3 source
work is complete; installed qualification and H5 promotion remain pending.

| Step | Concrete output | Source-packet exit |
| --- | --- | --- |
| H4a - schema and selection | Closed subject, admission-selection, promotion-basis and envelope contracts; deterministic requested-set expansion to entire v2 rows/all four criteria and recursive same-profile dependency rows. | Reject partial-row success and missing dependency recovery. Cycles require complete proof. Preserve all original parents/history. |
| H4b - read-only artifact/provenance join | Exact archive/source/native members, admitted producer/toolchain/configuration, original inventory/functional/three-gate/control/shutdown receipts and actual execution ledger bytes. | One complete synthetic join; resealed wrong-member/producer/child/profile/source-mode/late-failure controls. Real reviews/artifacts stay missing until available. |
| H4c - CI, review and retention | Versioned authoritative required-job policy; exact head/run/attempt jobs; promotion basis binding subject plus CI/head/impact decision; exact terminal plan/apply/retained-hash joins. | Reject reduced check policy, old-head CI, valid review transplanted to another passing head, unapplied cleanup and missing retained input. No installation or cleanup mutation in validator. |
| H4d - focused integration | Wire existing validators and CPU checks; refresh preparation hashes for changed tools/schema/spec; retain incomplete real index and remaining prerequisites. | Structural mode explicitly incomplete; strict admission nonzero. No wheel/SDK rebuild for this source packet. Actual independent source/scope review still required. |
| Later installed qualification/H5 | Resolve applicable blockers and producer admission, freeze reviewed inputs, collect exact installed evidence, obtain current-head CI and independent promotion-basis review. | Every effective selected row/dependency passes conjunctively. Windows-first scope leaves required WSL/full-inventory/host obligations open. |

Use one existing environment and bounded storage. Register managed scratch only
if an actual experiment needs it, preserve failures and original licenses, and
finish its retention/cleanup receipt before the next run. This plan/spec review
allocates no scratch and initiates no native build or installed-artifact check.
