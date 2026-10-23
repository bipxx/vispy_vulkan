# Large-volume benchmark quality and residency protocol

This protocol uses all 24 registered volume benchmark workloads: 256³ and 512³
float32 scalar ellipsoids, 1024² and 2048² physical viewports, MIP/translucent/iso,
and separate resident rotation and full-data updates. It calls the actual shared
`benchmark_frames.build_scene` factory. The data generator, camera, linear
interpolation, relative step size 0.8, threshold 0.5, gamma 1, clim (0,1) and
update formulas retain their prior AST. Declared setup fixes add physical-surface
preparation, explicit colormap controls and an optional capture hook. The timing
benchmark uses the same fixes and does not use the capture hook.

The first original-only execution exposed invalid benchmark setup before any
candidate ran: zero-density air was opaque black with the default `grays`
colormap, so translucent output was entirely black; Qt initially constrained the
2048-square window to 2048×1901. A fresh official-wheel surface probe confirms
one explicit public resize restores the required 2048×2048 physical extent.
The factory now prepares the actual extent before allocating source data and
fails if exact resizing is unavailable. Translucent workloads explicitly declare
`colormap="density-alpha"`: a public linear Colormap maps density t to (t,t,t,t),
so zero density transmits the ray. MIP/iso retain `grays` with alpha 1. No dataset,
step, threshold, camera, update multiplier, sample count or comparison tolerance
is adjusted to candidate output. No candidate had run when these controls were
fixed. The new colormap field deliberately changes workload identities; prior
admissions cannot be silently reused under the new declarations.

Each installed-wheel case captures initial, unchanged repeat, and the benchmark's
probe frames 7 and 73. Resident cases change the camera azimuth; update cases
use the factory's preallocated full-data update buffer and original multiplier.
Both renderers use the factory's PyQt6 scene. One owned RGBA8/depth framebuffer
survives every capture and must be rebound after GLIR CURRENT for every draw.
The actual physical viewport and public canvas-to-FBO corner mapping must match.

All 24 fresh original cases must succeed before any candidate case starts.
Original VisPy 0.17.0 and the Native58 cp312 candidate archives, installed payloads,
runtime closure, sources, parameters and actual native origins are bound exactly.
The initial GLIR source upload must cover the complete float32 dataset and match
the scene factory's actual source hash. All methods, controls, camera states,
texture shapes and source identities are retained. Pixel arrays and stage
metadata are saved losslessly before any quality gate; failures remain intact.

Comparison uses the existing benchmark's default whole-frame quality rule:
absolute channel error at most two uint8 values, including alpha, with no edge
mask, crop or excluded pixels. Blank/constant output cannot pass. The unchanged
repeat must equal initial exactly. Each probe must change pixels from its own
initial frame, with changes overlapping at least 50% of the original changed
pixels. Original maximum change and changed/overlapping counts are recorded.
A probe with no visible original change is explicitly non-discriminating and
cannot qualify update behavior merely by remaining inside the two-byte rule. This is the existing rule, fixed before
execution; no tolerance will be fitted to candidate results.

Unchanged candidate repeats and resident-rotation stages require actual native
draws and Vulkan queue work, zero GLIR DATA/SIZE and all 20 established
resident-zero counters. Official VisPy 0.17.0 redundantly resubmits its unchanged
96-byte cube vertex and 56-byte index buffers on every draw; the fork already
clears that update flag. The original remains unmodified: later SIZE/DATA is
allowed only on those two actual initial typed buffer IDs with byte-identical
initial descriptors, offsets and payload hashes. It cannot update the resident
source texture, change geometry or create/delete objects. This original geometry
work remains part of the future timing baseline, not removed to force zero work.
The performance gate must account for that bounded attested original work rather
than falsely label an unchanged official render invalid. No timing pass is
claimed by this quality packet.
Full-update stages must upload exactly one complete source dataset, match the
original source-upload hash, and report matching requested bytes. Warm shader,
pipeline and geometry work is forbidden on updates too. Source/target/FBO
identities remain fixed; no later CREATE or DELETE is permitted. Resident SIZE
commands are forbidden. Full replacement legally emits SIZE with the identical
source shape/format, as the unchanged original Volume.set_data API requires.
Actual upload conversion time is allowed only for full updates. The packet does
not claim zero temporary native revision allocation during full replacement.
Complete, available Vulkan memory tracking must report no net live allocation
or byte growth across each post-initial stage. Live gauges may decrease when
warmup resources retire: declines require the same device generation, nonnegative
allocation/free event deltas and exact count/byte conservation. Event-counter
resets, missing observations and unexplained declines fail. Owned color+depth clear ordering
is checked before every draw. Actual rendering controls must equal the declared
workload, not merely agree between the two renderers. Readback waits are recorded and deliberately permitted. Actual
workers and parents must be waited; shutdown resources must be zero and newly
owned environments and uv cache removed. Useful raw, failed and frozen evidence stays.

This is quality and bounded residency qualification for one Windows CPython
3.12.8 / NumPy 2.4.6 / PyQt6 / NVIDIA RTX 4090 / driver 610.88 cell. It does not
qualify other ABIs, bindings, providers, GPUs/drivers, native Linux or Metal.
It does not replace the smaller independent categorical, depth, clipping and
numeric scientific controls, or mark their per-workload admission automatically.
V09 and the full release remain open until the required performance and wider
qualification gates pass. Timing requires at least 100 warmup and 1,000 measured
frames in five alternating original/candidate pairs, speedup >=1.20 on each
primary resident workload, no worse p95 and no update regression above 10%.

AGPL-3.0-only covers the implementation. Original VisPy BSD and dependency
licenses, copyright notices and attribution remain attached unchanged.

Source3 passes all 24 fresh originals before all 24 installed candidates, across
four stages each. Independent saved-byte inspection checks 251,658,240 paired
whole-frame pixels (1,006,632,960 RGBA bytes), with maximum channel error 1 under
the predeclared bound 2 and zero exclusions. All 48 update/rotation discrimination
checks pass. Unchanged repeats equal initial exactly. The inspector also checks
actual controls and opacity maps, full source-upload hashes/bytes, stable resource
identities/descriptors, attested original geometry, owned color+depth clears and
draws, 20 candidate resident-zero fields and 17 full-update warm-zero fields.

The 12 live-gauge declines satisfy allocation/free count and byte conservation;
no counter resets or growth are admitted. The inspector does not attribute the
freed allocations to particular objects. All snapshots have complete available
tracking and the same device generation. All 48 actual workers and two parent suites are terminal;
eight shutdown resource counters are zero in every candidate; both owned wheel
environments and the uv cache are removed. The saved inspector imports no VisPy
or provider and does not replay graphics. The actual result is
`build/large-volume-wheel-run-root-3/result.json`, SHA256 `04cee47a20e21003faafee6c34c54e70f6cc59b4e43de18c316b8cc0440fb8a8`.
Independent inspection is `build/large-volume-prep-root-1/saved-review1.json`,
SHA256 `fa67acaff2a72a4ac1f580f8e8a6eb78e4a53e6069437352cef02e7ed1cd79c2`; preregistered sources and exact snapshots are bound by
`build/large-volume-prep-root-1/source-seal3.json`, SHA256 `d9e79124ec600c5e95ae4797b4a073214d48c48d102e626b80a955d4e9274973`.

The 313-file original bundle in `tests/reference/large-volume-opengl` is unchanged
from that actual original run, including its manifest, SHA256
`af7919c6f59dca7addee614a674942697b33d53df3446df0cea422ef980bf2ac`.
The candidate parent and all 24 worker command receipts bind this exact digest.
`tests/contract/test_large_volume_wheel_parity.py` declares 24 mandatory installed
candidate cases, requiring successful workers AND the complete successful parent.
It is a reusable entry point, not a separately replayed wrapper: the actual GPU
evidence above comes from the waited driver. Missing artifacts fail rather than
skip. Each invocation requires a fresh evidence directory; set
`VISPY_LARGE_VOLUME_EVIDENCE` to a new path when rerunning and retain earlier
results. The CPU workflow checks the actual source generator, update behavior,
controls, quality/signal/residency/fault gates, immutable references and existing
benchmark metrics without invoking graphics.

The factory AST control now uses a version-independent canonical form, retaining
all semantic fields and rejecting generic parameters, while ignoring only empty
`type_params` metadata introduced in newer Python. Actual CPython 3.10.19,
3.11.14, 3.12.8, 3.13.8 and 3.14.0 parsers reproduce the same original and
normalized current factory hash without importing a provider.

Failed Source1 and Source2 executions remain intact. Source1 preserved all 24
original failures (eight overstrict legacy-geometry gates, four invalid blank
translucent setups and twelve initially constrained viewports), blocked every
candidate, waited workers and removed owned scratch. Source2 passed all originals
and 12 candidates; the other 12 stopped at the erroneous equality check on live
memory after a genuine 4 MiB release. Source3 fixes that signed-gauge predicate
with allocation/free conservation; rendering inputs and pixel rules are identical
to Source2. Every failed status and artifact remains unchanged. Source review and
explicit root resolutions are retained; no later peer READY verdict is claimed.

This closes the bounded large-data quality/residency component only. Per-workload
links to the independent categorical/depth/clipping/numeric controls are recorded
in [volume scientific admissions](volume-scientific-admissions.md). Performance,
other hardware/platform/binding/ABI cells and the full release remain unqualified.
