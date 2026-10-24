# Astra review: VisPy compatibility gap-closure plan

Date: 2026-10-24. Reviewer: `gpt-6-astra`, reasoning effort `max`, as requested.
Reviewed source checkpoint: `98501f349229c809f9bf287e53eed73a1158cea4`.
The reviewer inspected the plan, compatibility/status documents, original design
and relevant source/tests read-only. It performed no builds, installations,
deletions or test runs. Findings below are code/plan review findings; existing
test evidence remains separately scoped.

Disposition: **changes required before Tk promotion**. Requirements and execution
order have been expanded; runtime defects are not fixed by this documentation
pass. Auto-merge on PR #14 was disabled while those findings remain unresolved.
The previously merged PR #13 and its retained qualification are unchanged.

## Findings and adopted disposition

| ID / priority | Finding and source evidence at reviewed checkpoint | Required response / disposition |
| --- | --- | --- |
| R1 / P1 | Tk camera dragging lacks pressed-button state. `_dawn_tk.py:207–224` omits `buttons`; `app/canvas.py:637–643` defaults it to empty; `scene/cameras/panzoom.py:222,230` and perspective/fly cameras consume it. Existing input test only checks transitions, wheel and one key. | **Accepted, implementation open.** TK-6 and G1a require maintained multi-button state, release outside/focus loss, modifiers and real PanZoom/3D camera drags with changed camera/render results. |
| R2 / P1 | Manual pumping surfaces stored draw errors at `_dawn_tk.py:60–75`, but Application.run calls plain mainloop at 77–78. Native progress/readiness at 178–180 is outside the draw handler. All current integration tests use manual pumping. | **Accepted, implementation open.** TK-2..4 and G1b cover all three loop modes, native progress, first-error preservation, owned/borrowed loop delivery and readiness/resize/input/timer/presentation errors. Preserve the existing EventEmitter callback-error policy. |
| R3 / P1 | Root and timer ownership are incomplete. `_dawn_tk.py:51–58` assumes private _default_root exists after NoDefaultRoot; distinct applications can share a root but track ownership separately. Backend-only stop at 81–82 does not update public Timer.running. Widget/image/bind construction at 107–122 precedes unwind handling. | **Accepted, implementation open.** TK-1,4 and G1a require parent/interpreter-derived ownership, shared Application objects, explicit-parent NoDefaultRoot, early allocation failure injection, root destruction/re-entry and consistent public timer state. |
| R4 / P1 | Both flush APIs need a real implementation. Raw glFlush is refused, but `gloo/wrappers.py:562–573` advertises gloo.flush and queues the logging-only native route at `cpp/runtime.cpp:6542–6543`. | **Accepted, implementation open.** STATE-4 and G1d require shared nonblocking submission, observed before readback/present/finish can mask it, unchanged finish_calls, retained resources and FBO/multi-canvas/loss/close coverage. Relabeling the existing wrapper is insufficient. |
| R5 / P1 | Artifact promotion is underspecified. `tools/immediate_state_wheel_smoke.py:38–44` checks two member hashes and one 96-pixel scene; it is not Tk qualification or complete installed-distribution verification. | **Accepted, qualification open.** EV-1..5, ART-1..2 and G2 require the existing complete member/profile audit, mapped installed Tk workflows, final artifact identity and all three existing absence gates. |
| R6 / P2 | Orientation checks share the candidate's readback path; a common flip can pass. Recovery permits either color. Tk/physical dimensions are aliased; META and broader input/scale behavior are untested. | **Accepted, coverage open.** TK-5..8 and G1c require independent known corners after resize/loss, alpha/cropped/float capture, odd sizes, full-client display, image/job ownership and explicit 125/150/200% coordinate policy. Synthetic scaling is not mixed-monitor proof. |
| R7 / P2 | Allowlisting 29 operation names is not full state compatibility. Reversed depth ranges and enabled GL_DITHER remain legal upstream cases refused by `cpp/runtime_state.hpp:267–286`; the three tests cover only selected clear/scissor/mask behavior. | **Accepted, inventory/coverage open.** STATE-1..3,5 enumerate legal-but-unimplemented inputs separately from invalid values, state/cache/queue behavior and coverage for blend/depth/stencil/cull/line/sample families. |
| R8 / P2 | Shader packets need explicit interface/layout/uniformity design. Existing guards include literal sampler indices, multidimensional arrays and matrix/array attributes in normalize.cpp, geometry stages in runtime.cpp, and line evaluator effects at normalize.cpp:921–930 / line_consumer.cpp:585–599. | **Accepted, implementation open.** SH-1..5 and G4a..d define feasibility, reflection, resource limits, derivative/layout/location rules, geometry subset, line coverage/depth/side-effect counts, negative controls and actual GPU proof. Keep refusals until implemented. |
| R9 / P2 | A finite upstream inventory and a strict completion definition are missing. Explained unsupported or hardware-blocked required rows could otherwise be mistaken for completed work. | **Accepted, inventory open.** INV-1..3 and G0 require pinned public APIs/visuals/hooks/backends/examples, requirements/evidence/owner rows, and every required row's functional plus same-artifact gates. No percentage inferred from host or fixture counts. |
| R10 / P2 | Threedee diagnosis needs resource and time bounds as well as an attempt count. Successful retries do not close the mandatory OLE row. | **Accepted, diagnosis open.** HOST-1..2 and G3 specify watchdog/log/capture bounds, owned child termination/wait, timeout stacks/repro/control, terminal unresolved outcome and no feature suppression. Hardware absence remains explicit without stopping independent software work. |

Source paths in the table are relative to `src/vispy` unless prefixed by `cpp`,
`tools` or `tests`. Exact line references describe the reviewed source, not an
assurance that future edits retain those line numbers.

## Sequencing and remaining implementation

Begin with the inventory and known Tk input/ownership/mainloop defects, using
existing native artifacts. Run bounded threedee diagnosis independently. Complete
native flush submission and state-family acceptance before the combined G2
artifact promotion, so a required native change does not immediately invalidate
a newly qualified packet. This consolidates packaging work rather than dropping
the reviewer's requirement for both source and installed checks.

Then implement one inventoried shader/backend/host packet at a time, retaining
its exact acceptance evidence. Native Linux GPU and Metal remain hardware-bound;
representative performance follows correctness. The old design's pre-implementation
status is marked historical, with current requirements linked prominently.

The full implementation remains incomplete. Current test totals, a merged PR,
or an explicit unsupported error cannot resolve these findings. Original
mandatory gates, AGPL/BSD/third-party source/notices, the 20 GiB aggregate scratch
budget and 10 GiB reserve remain in force. This review required no new native
build, environment or copied source history.

## Updated documents

- [Detailed specification](../specs/2026-10-24-vispy-compatibility-gap-closure.md)
- [Execution plan and dependencies](../plans/2026-10-24-vispy-compatibility-gaps.md)
- [User-facing compatibility boundaries](../../vispy-compatibility.md)
