# Volume benchmark without measured geometry observation

`tools/volume_benchmark_adapter2.py` and
`tools/volume_benchmark_pairs2.py` introduce a new evidence epoch. Existing
workers, paired runs, reference files, renderer commands, and benchmark thresholds
are unchanged. Their original geometry-observer gap remains in those records.

The new worker observes geometry during scene creation and warm-up. Before the
frozen Python telemetry constructor runs, it restores the pristine parser. A
temporary profiler in that unsampled constructor interval verifies that the raw
parser did not run; the queued command objects must also remain unchanged. The
worker verifies the exact frozen parser-wrapper code and its captured pristine
parser, then installs the warm observer outside that wrapper.

After every warm frame retires, the first counter snapshot restores the exact
frozen wrapper, serializes the warm ledger, and clears its mutable command lists.
The measured interval inherits the frozen `begin` implementation and executes no
geometry observer. At the second counter snapshot, the parser identity and
observer invocation count must still match. Both roles use this handoff.

This removes the measured observer callback and payload copies. It does not claim
that interpreter state is identical to a process that never observed geometry:
the telemetry subclass, extra attributes, and immutable warm ledger remain
allocated, with possible cache or garbage-collector effects. No observer CPU cost
is subtracted from timings.

For the pinned original volume program, `volume_geometry_causality.py` checks the
admitted installed sources, the original cube computation and draw dispatch, and
shape-preserving update route. Its predicted vertex/index bytes must match the
existing original references. Actual cold IDs/types/bytes and every warm cube
upload corroborate those invariants. This source check alone never proves a
measured run.

`volume_benchmark_geometry2.py` additionally requires stable scene, source shape,
and buffer identities across measurement; exact raw per-paint and aggregate GL
draw/upload counters; and absence of errors, fallback storage, buffer creation or
deletion, or other forbidden work. Together these constrain each original draw
to its existing two uploads totaling 152 bytes. Candidate work retains the
generic native gate and warm geometry residency checks. Full updates require
one complete source texture upload per measured frame on both roles. These are
invariants of the closed, pinned benchmark program, not a theorem about arbitrary
host scenes or callbacks.

The new paired controller reuses the existing alternating schedule, actual-worker
termination checks, unresolved-worker hold, raw-sample/statistics verification,
whole-frame image comparisons, hardware and scientific admissions, and cleanup.
It changes the worker entry point and measured-work gate through scoped bindings.
It preserves all instrumentation-gap strings already present in a run. New runs
retain the frozen scanout and complete driver/allocator accounting gaps.

CPU contract tests use synthetic metadata and retained raw API receipts; they do
not qualify fresh GPU timings. Actual new workers and saved-run revalidation are
required before claiming this observer mechanism works in a measured collection.
Five pairs for one workload do not qualify other workloads, native Linux Vulkan,
macOS Metal, or the full release plan.

The implementation is AGPL-3.0-only. Original VisPy BSD license texts and
third-party notices remain attached unchanged; see `../LICENSING.md`.

## Current validation

The focused CPU suite passes 434 tests with zero skips. The private receipt
`build/volume-observer-controls-root-1/cpu6.json` binds the complete 26-file
controller source closure, test files, command, counts, and JUnit/log hashes.
Tests through the actual frozen release gate verify that each retained gap
independently prevents a pass, using explicitly synthetic passing metrics.

The first new collection at `build/volume-observer-free-pairs-run-root-1`
is **failed and partial**, not a completed five-pair benchmark. The first actual
upstream/candidate pair passes saved-work, full-sample, hardware, and image
checks. A subsequent candidate worker has two unsolicited Qt paints outside
issued-frame ownership; the unchanged controller rejects that worker and stops
the collection. No retry, gap removal, or reclassification of those records has
been performed.

All three actual workers pass the new geometry handoff checks, including exact
frozen parser identity and zero measured observer invocations. The actual
candidate warm ledger is empty as required. These observations support the
handoff mechanism in this resident case, but do not close its release gap:
five valid pairs and actual full-update validation are still pending.
`build/volume-observer-controls-root-1/partial-review1.json` independently
recomputes that distinction and verifies all three actual workers terminated
and all owned worker directories, both environments, and their cache were
removed. The origin of the unsolicited paints remains unproven.

A second predeclared collection, `build/volume-observer-free-pairs-run-root-2`,
completes all five resident pairs. All 15 image comparisons have maximum channel
error 1 under the existing limit of 2; all ten changed-pixel checks pass. The
subsequent full-update collection verifies two pairs and a third upstream
worker, then rejects a candidate with one unowned paint. The overall collection
remains failed/partial. All 16 actual workers pass the geometry handoff with zero
measured observer invocations. `saved-review4.json` in the preparation directory
recomputes the saved checks and verifies terminal processes and removed owned
directories, environments, and cache. This supports the observer mechanism for
the completed resident case; other workload cases remain unqualified.

The two valid full-update pairs also expose a substantial performance gap:
median of run medians is about 31 ms upstream and 116 ms candidate. These are
unqualified observations from an incomplete collection, not a release result.
See [the upload optimization plan](volume-full-update-optimization-plan.md).

Separate Qt tracing diagnostics retain their own explicit observation-overhead
gap. The resident diagnostic does not reproduce an unowned paint. The full-update
diagnostic reproduces a spontaneous `QWindow` expose followed immediately by an
unowned native-widget paint between issued frames 779 and 780; no delayed repaint
timer is scheduled. The external platform trigger remains unknown. Audit
`build/volume-paint-diagnostic-prep-root-1/audit2.json` binds that event trace and
verifies cleanup. No paint is suppressed or reclassified by this diagnostic.

The standalone 920-file public-source/fixture copy passes the same 434 focused
CPU checks without access to `build/`, renderer providers, or graphics hardware.
Saved-run validation in a new process must use `volume_benchmark_pairs2.verify_run`
to bind the run directory; the private in-memory directory key is not persisted.
