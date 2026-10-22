# Volume benchmark adapter

`tools/volume_benchmark_adapter.py` runs the unchanged complete-frame benchmark
worker with additional scientific artifact and geometry checks. It supports the
24 registered volume workloads in the existing Windows CPython 3.12.8,
NumPy 2.4.6, PyQt6, RTX 4090/610.88 scientific cell. It changes no renderer,
scene factory, update function, quality limit or frozen performance threshold.

The original VisPy 0.17.0 volume visual repeats its cube geometry upload on
every draw. That work belongs in the reference timing. The adapter observes the
actual parser stream before allocation, binds the visual's vertex and index
buffer IDs and checks them against the pinned original cold descriptors and
payload hashes. Every measured original frame must repeat exactly the 96-byte
vertex and 56-byte index uploads with their original offsets. Extra commands,
changed data, unowned measured buffer commands, missing frames or incomplete observation
prevent admission. The raw OpenGL counters must account for exactly two uploads
and 152 bytes per frame. The counters and elapsed time are retained unchanged.
Every other forbidden OpenGL operation remains forbidden. Candidate resident
work continues through the original native zero-work gate.

The live hook checks the size before copying at most 152 bytes of cube data per
frame. Hashing and JSON records are built after measurement. It passes each
batch unchanged to the original parser and stays inside the measured Python
parse/draw scope. Its cost is included. Frame ownership follows the existing Python paint telemetry,
including parser work after swap inside the same paint. Cold and warm operations
are recorded separately from the measured-frame range. The frozen Python
counter snapshots explicitly open and close the measured ledger window after
warm retirement and after measured retirement. Pre-warm expose commands remain
in the raw record and cannot become measured work or disappear from evidence.

Before timing, the worker checks the supplied wheel digest, every installed
wheel payload, the complete package fingerprint admitted by the scientific
controls and the Python/NumPy profile. After timing, the measured-work gate also
checks the actual workload, device/driver and adapter source identities. The
saved-run gate recomputes these checks rather than trusting a previous verdict.
`release_gate` retains the frozen five-pair, 100-warmup/1,000-measured-frame,
20% resident speedup, p95, update, scientific, hardware, presentation and
instrumentation requirements.

Run a worker only in a fresh installed-wheel environment and a fresh output
directory. A controller must supply a unique launch ID, wait the actual process,
verify `worker.json` and its process stamp and run digest, then join retained
samples, captures, scientific admission and designated hardware records. The
worker CLI accepts `--worker`, `--launch-id`, `--workload`, `--wheel`,
`--admission` and `--output`; it enforces the minimum warmup/frame counts.
An individual worker is not paired performance qualification. The
[paired controller](volume-benchmark-pairs.md) now owns the environment, process
and evidence joins. Matrix execution and release qualification remain pending.

The frozen worker still reports input-to-visible scanout and complete driver
allocator accounting as instrumentation gaps. They are preserved. This adapter
does not turn a measured diagnostic into a release pass while those gaps remain.
The effect of different observer costs on the paired timing is also unbounded;
it is an explicit gap and prevents the adapter release gate from passing.
A CPU no-op-parser microbenchmark of saved role batches measured median hook
costs of 4.2 microseconds for the original and 1.2 for the candidate. A fresh
CPU run after the window-boundary change measured 6.2 and 1.3 respectively. These are
not an interactive timing calibration or a bound on completion-latency bias.
Other hardware/platform/binding/ABI cells and the full release remain open.

The first actual original worker completed 100 warm and 1,000 measured frames,
with exactly 2,000 measured GL buffer uploads and 152,000 bytes, but was rejected
because the initial ledger also counted one pre-warm expose draw as unowned
measured work. Its blocked result remains unchanged at
`build/volume-benchmark-worker-root-1/result.json`, SHA256
`413bd512df904ec873390f7845e68a18af21820bba02d7cb03573038f2bddcfc`.
Independent saved inspection verifies all 1,100 cube streams, zero measured
unattributed Python calls, terminal actual worker and removed environment/cache.
That diagnosis motivated explicit measured-window boundaries and a fresh run;
the failed run has not been reclassified as passing.

The fresh original run with explicit boundaries passed all 1,000 measured cube
checks: 4,000 exact buffer commands, 2,000 actual uploads and 152,000 bytes,
with zero measured unowned commands and all other forbidden GL work zero.
Its three quality captures exactly match the pinned original frames. Result:
`build/volume-benchmark-worker-root-2/result.json`, SHA256
`b4ea77b477d3c4d568d4bef16149fdbe08275ec945c1e0a0f0766e9ee62c91ac`.

A fresh Native58 candidate then completed 100 warm and 1,000 measured frames
using the same adapter sources. It passed the unchanged native resident and
no-wait checks, verified whole-paint ownership for all 1,100 frames and the
event-level allocation window. Its three full-frame quality captures differ
from the fresh original by at most 1 under the fixed limit of 2. Result:
`build/volume-benchmark-candidate-root-1/result.json`, SHA256
`d61cc3f26eaf1ee52234e00cfa0a8fcd6469ea7b2a2df0b69610c1fdac0ebc50`.
Independent saved inspectors recompute the gates, sample statistics and capture
comparisons. Both actual workers are terminal; owned environments and caches
were removed. This is one diagnostic run per role, not five alternating pairs,
a speedup qualification, a full 24-volume result or a full 66-workload release.

The implementation is AGPL-3.0-only, with the original VisPy BSD license,
copyright notices and disclaimer attached unchanged. See `LICENSING.md`.
