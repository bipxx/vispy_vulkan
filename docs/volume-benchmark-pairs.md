# Paired volume collection

`tools/volume_benchmark_pairs.py` owns two fresh installed-wheel environments
and launches a fresh process for each role in the fixed alternating schedule.
Each workload requires at least five pairs, 100 warm frames and 1,000 measured
frames. Select workloads explicitly with `--workloads`, or use `--all-workloads`
for all 24 registered volume workloads. The full 66-workload release is separate.

The newer [observer-free integration](volume-benchmark-observer-free.md) uses
versioned worker/controller entry points. This page describes the original
controller and its retained observation-overhead gap.

Supply the two qualified wheels, the completed scientific `quality-plan.json`,
a predeclared hardware JSON and a fresh output directory. The admitted Windows
cell's hardware designation is in
`compat/hardware/windows-rtx4090-61088-pyqt6.json`, based on the prior actual
original and Native58 diagnostics. Both renderer identities and common host
versions are checked against the new captures. The controller records its own
Python version and the selected/controller/base executable digests, source
hashes, wheel hashes, scientific inputs and exact request before collection.

For every worker the controller records the launch before waiting, joins a
unique nonce, actual process stamp, final worker receipt and run digest, then
checks all retained artifacts. It reconstructs complete frame retirement,
latency statistics, CPU and renderer counter deltas, original pacing receipts,
native whole-paint ownership and GPU map joins, and the measured allocation
window. Median, p95 and counts must match the raw samples exactly. Only the
descriptive standard deviation permits one ULP of variation across CPython's
statistics implementations; actual 3.10–3.14 checks exposed that difference.
Release thresholds are unchanged.

Each pair must pass all three whole-frame RGBA comparisons with the existing
error limit of 2 and both existing changed-pixel checks. The manifest binds
launch, process, validation and log files by digest. Worker `run.json` and all
raw samples/captures remain unchanged. The process is waited in short intervals
against a wall deadline so an interrupt can initiate cleanup promptly.

If actual termination cannot be verified, the controller preserves the owned
cwd, wheel environment and cache. It also writes the workspace-wide hold
`build/volume-benchmark-pairs-unresolved-worker.json`. A fresh output directory
does not bypass this hold. An operator must verify the recorded actual process
is terminal and record an explicit resolution before clearing it; the controller
never clears an unresolved hold automatically.

`collection_status: complete` means all requested pairs and their evidence
joins were collected. It is distinct from `status: passed`. The existing
observer-overhead, input-to-visible scanout and driver/allocator accounting gaps
remain release blockers. A complete but unqualified collection exits with code
2. See [the worker adapter](volume-benchmark-adapter.md).

`tests/reference/volume-benchmark-diagnostics` retains the exact prior one-run
diagnostics and their actual parent receipts for CPU regression checks. Its
manifest is `d16dfa08fe376215cc421a1e6c22f609ce12d1a3306753652664d60b38cc74c5`.
These fixtures are not evidence of a new five-pair execution.

The first actual controller integration completed five alternating pairs for
`volume-256-1024-mip-resident`: ten fresh worker processes, 1,000 warm frames
and 10,000 measured frames in total. All 15 full-frame comparisons passed with
maximum channel error 1; all ten changed-pixel checks, hardware equivalence and
scientific admission passed. Independent saved inspection recomputed every
worker gate, sample statistics, counter delta, capture comparison and lifecycle
digest. All actual workers were waited and terminal; both owned environments,
all worker cwd directories and the shared cache were removed.

The retained manifest is `build/volume-benchmark-pairs-run-root-1/manifest.json`,
SHA256 `ca38a7ce5701acc85eb83fe6aab3f49705091ad09e8946e00db45ebb6341ff5d`.
It correctly reports collection complete and release unqualified. Observer
overhead effects, scanout measurement and complete driver/allocator accounting
remain open. This finite result does not qualify the other 23 volumes, the full
66-workload matrix or other hardware/platform/binding/ABI cells.

The implementation is AGPL-3.0-only. The original VisPy BSD license, notices and
disclaimer remain attached unchanged.
