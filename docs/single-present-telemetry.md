# Current single-present telemetry contract

This is an additive regression contract for the existing Qt paint and public
readback behavior. The separately named tests are
`tests/benchmarks/test_single_present_native.py`, with CPU negative controls in
`tests/contract/test_single_present_contract.py` and assertions in
`tools/single_present_contract.py`.

Status: authoring. The CPU controls pass on Windows and WSL. A new hardware
capture and review are required before these tests supply development evidence;
release admission still requires the original artifact and profile gates.
Run `r2-qt-native-277` remains **27 passed, 7 failed**. Its captures are not
retroactively admitted under this contract. The frozen two-present tests,
fixtures, reference packets and failed outcomes remain unchanged.

## Why the sequences differ from the historical fixtures

Commit `60b30d7ca08dbf15ec6de1232cca26b468ddc236` made Qt defer autoswap while
its paint token is active. The final present includes the Qt alpha tail.
The consolidated plan's W8 entry acknowledges that single-present code; D18
selects native presentation for Windows hot swap at R2 assembly. Strict
no-OpenGL qualification continues to select readback explicitly.

Commit `e6709ee60a3e0123f24f247cad9eef03e4cb585b` made public finish and readback
presentation-free. A capture must not be changed back to an implicit present
to satisfy the older submission sequence. Both decisions predate run277.

## Successful whole Qt paint

The scenario draws one resident full-screen quad (two triangles in one scene draw), keeps the existing
autoswap callback, applies the masked Qt alpha clear, and presents once at
paint close. Native presentation must be explicitly selected. Twelve issued
frame IDs include four warmup and eight measured frames.

| Observable | Normal | Explicit intermediate submission |
| --- | --- | --- |
| Owned submissions | 2 | 3 |
| Successful surface presents | 1 | 1 |
| Last present submission index | 1 | 2 |
| Render pass kinds | clear, scene, clear, surface_conversion | same |
| Pass submission indices | 0, 0, 0, 1 | 0, 0, 1, 2 |
| Public scene draws | 1 | 1 |
| Native draws | 3 | 3 |
| Transient uniform bytes | 32 | 32 |

The intermediate operation submits real work; it does not add a surface
present. Copying or inventing a second present receipt is rejected.

Every issued frame needs one FIFO receipt, a unique positive paint token,
closed and retired ownership, and counters frozen at submission. No terminal
receipt or GPU map may appear while the real paint remains open. Owned counts
must equal the actual global deltas from the frame's recorded baseline.

All existing resident geometry, texture, conversion, shader, pipeline and
completion-wait counters stay unchanged. Transient uniform upload time remains
visible rather than being subtracted from the report. Bounds on pending
tickets, queued frames and timestamp frames remain enforced. A deferred-path
claim requires its actual counter witness.

With queries enabled, each real pass must have the declared owner, submission
index, ordered timestamps, duration, quantization, sum and span. Required
unavailable timestamp hardware is a failed gate, not a skip or a synthetic map.
With queries disabled, no query allocation or GPU timing map is allowed.

The final exact pixel capture follows all resident/no-wait assertions. Its raw
BGRA bytes are retained and converted explicitly to RGBA without a row flip.
The expected binary RGB and alpha64 image is unchanged.

## Failures before the final surface present

The invalid-width action raises inside the scene callback, before autoswap.
Device loss and detach run in the observer after the deferred autoswap callback.
That callback alone proves no surface presentation.
Every terminal receipt must retain its error and closed/retired owner, report
zero successful presents, and use the unsubmitted last-present sentinel.
Failed receipts and timing maps must be rejected by the success collectors.

| Action | Completion status | GPU timing status |
| --- | --- | --- |
| Invalid width | failed | submission_error |
| Device loss | device_lost | device_lost |
| Surface detach | failed | submission_error |

Invalid width and loss before submission have no successful owned work.
Win32 detach has a separate synchronous native-owner retirement obligation.
Direct snapshots around `clear_surface` must show its one empty queue submit,
one deliberate completion wait and zero application-present increment. The
failed paint then owns two submissions. The full global deltas are therefore
three submits, one logical application-present operation and one wait, with no
extra `finish` call. The failed receipt's frozen counters must match the final
snapshot. These cleanup costs remain visible; baselines are never rebased.

The logical application-present increment is not evidence of a successful
`Surface.Present`. Actual surface success is represented by `presented`,
`present_count` and `last_present_submission_index`.

## Explicit headless capture

The fixed red clear and public RGBA readback use this sequence:

1. Presentation-free finish submits rendering at index0 (`clear`).
2. Readback submits the actual texture-to-buffer copy at index1. A copy is not
   fabricated as a render pass.
3. An explicit headless present request submits `present_capture` at index2.

The timing map contains `clear@0` and `present_capture@2`, with three owned
submissions. Before/after snapshots must prove readback added no application
present. Only the explicit later request increments that logical counter.
No surface is attached: the receipt remains `presented=false`,
`present_count=0`, with an unsubmitted last-present sentinel despite a
successful headless completion. Exact red RGBA, raw receipt/maps, copy and
explicit-present boundaries are retained before admission checks.
