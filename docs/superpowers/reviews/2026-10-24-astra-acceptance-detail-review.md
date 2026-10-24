# Astra max review: detailed acceptance gates

Date: 2026-10-24. Reviewer: `gpt-6-astra`, reasoning effort `max`, explicitly
requested by the user. Reviewed current canonical plan/spec, previous review,
compatibility document and narrowly relevant runtime/tests. Publication source
checkpoint: `dc070cbea` (the canonical documentation draft was also reviewed).
Read-only review: no builds, installations, tests, scratch or runtime edits.

Disposition: **accept the six requirement refinements; implementation remains
open**. The coordinator incorporated them into specification section 10 and
the execution plan. This review does not qualify an artifact or close the first
review's unresolved findings.

| ID / priority | Evidence and finding | Adopted detail |
| --- | --- | --- |
| A1 / P1 | `cpp/runtime.cpp:5404` can defer at ticket capacity; `5308` tracks completion waits separately from finish calls. A fast loop cannot prove saturation. Submission is irreversible before later bookkeeping at `5812` and callback tracking at `1536`. | Empty flush may be a no-op; nonempty work needs actual submission observed before synchronization, unchanged completion/finish/presentation counters, controlled incomplete-ticket saturation and failure injection after submission. Retain owners and prevent duplicate retry submission. |
| A2 / P1 | `cpp/runtime.cpp:6539` calls `finish_target(canvas, true)`; presentation at `5793` updates `application_presents`. | Finish/flush must not request GUI drawing, swapping/presentation or change selected target/state. Assert presentation separately from completion and test explicit later presentation. Source-review concern; not newly executed failure. |
| A3 / P1 | `_dawn_tk.py:159` infers exclusive root ownership from `winfo_children()` at `170`; user callbacks/bindings may exist without child widgets. | Explicit adoption/exclusive-ownership policy and a no-child root fixture with unrelated timer, idle work and binding surviving VisPy teardown; independently retire VisPy jobs/images/native resources. |
| A4 / P2 | `_dawn_tk.py:425`, `498`, `441` use client size for framebuffer size and widget-local pointer coordinates. | State the default Tk 1:1 pixel policy, authoritative positive Configure, provisional geometry, zero-size retention and capture origin. Verify embedding, odd resize, hide/restore and local scaling. |
| A5 / P2 | Existing reference and host inventories have heterogeneous scopes; fields alone do not establish integrity. | Versioned canonical-ledger schema and validator; stable feature/profile keys, reference integrity, complete required mappings and same-artifact promotion predicate. |
| A6 / P1 | `tests/native/test_scissor_boundaries.py:11` requests four samples without asserting the granted count. A fallback could evade the failing path. | Record requested/granted samples and actual driver identity; four-sample gate fails on fallback. Bound fresh-process toolkit controls, retain all exits and use one pinned closure for plain Tk and VisPy. |

Runtime source paths above refer to the reviewed checkpoint; line numbers can
move. `_dawn_tk.py` is relative to `src/vispy/app/backends/`.

The coordinator refined A4 after checking `src/vispy/app/canvas.py:351`: the
reviewer's unconditional public-size equality applies to default `px_scale=1`.
The existing nondefault public `px_scale` option divides backend size; the spec
preserves that contract and adds a separate fixture rather than overriding it.

The Linux scissor failure, independent plain-Tk abort, real nonblocking flush,
new finish-side-effect finding, remaining inventory/shader/backend/host work and
same-artifact qualification remain open. Metal remains experimental without Mac
hardware. This pass creates documentation only and changes no runtime behavior.

## Implementation follow-up: A3 ownership

A later source packet implements explicit-parent adoption and preserves host
jobs, bindings, commands, namespaces, variable traces and images on final release
with no child widgets. A retained old VisPy image is tracked weakly and does not
accidentally adopt an exclusive root. Query-failure retry, shared final release
and adopted-root re-entry have regression cases. Windows Tk/state/capture passes
100 source cases; WSL Tk/state passes 86, plus 12 packaging/source contracts.
These results are not installed qualification. Existing Linux capture/runtime
blockers and the other review findings remain open; no independent re-review of
this implementation is implied by this coordinator update.

## Implementation follow-up: A1/A2 and sample-count proof

Matching Windows and experimental Linux native leaves now implement both public
flush routes with real submission, explicit bounded backpressure and no added
completion wait. Finish and readback no longer request presentation. Tickets are
owned before submission; frame counts commit before optional callback/map work,
and post-submit failure/retry never replays consumed commands. Thirty-one source
submission cases exercise controlled completion delivery, both sides of Submit,
callback/map errors, marked-frame retirement, resource mutation/deletion, loss,
close, FBO/canvas state and later explicit presentation.

The broader candidate suites pass 168 Windows and 146 WSL software cases; 67
CPU/source cases and the C++ lifecycle contract also pass. These are source
functional results, not exact-wheel or strict absence qualification. The source
parser refuses the historical logging-only operation on an older native module.

A6's scissor fixture now verifies allocated storage and requested/granted sample
counts. Windows passes all eight boundary cases. Linux still fails one of eight
with four samples actually granted, preserving the failure and actual loaded
driver hashes. The plain-Tk runtime blocker remains open. G2, the other state/Tk
requirements and independent review of the implementation are still required.
