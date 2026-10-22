# Full-update upload optimization plan

Native60 native/wheel/finite-GPU update, 2026-10-22: the full runtime compiled and
linked, all 47 native CTests passed, and post-build dependency/preservation checks
completed successfully. `build/native60-prep-root-1/native-terminal-audit1.json`
independently verifies the completed pipeline, source618/harness4141, exact CTest
inventory, binaries, compiler policy and unchanged installed Native58.

A fresh PEP517 build produced
`build/native60-wheel-windows-cp312-root-1/wheels/vispy-0.17.0+vulkan.1-cp312-cp312-win_amd64.whl`,
SHA `3147f56a4d714322e26e347d01b4ccbd95163f5a99d98da9ea1c9cf3af5fdba1`.
All 523 package-source members, strict native/package inventory and both AGPL and
original BSD license copies match. Its four native members equal its own fresh
CMake leaf outputs; no stripping exception or project-output reuse was needed.
The wheel's `_dawn` SHA is
`3c1e501169c06b95e0ead606165f8d295bd3590948888ec910289cd53172b2fc`.
Failure-only integration checks on the actual native binding pass 17 cases, and
the same checks pass separately on the wheel-identical fresh binary, including
whole-batch discard after stats failure. These checks do not create a device.

Actual `build/native60-gpu-run-root-1` completed0: all eight unchanged finite GPU
cases and 23 whole captures pass on Vulkan / RTX4090 / driver610.88, with isolated
Python3.12.8 / NumPy2.4.6 and exact wheel/module origins. Independent saved audits
recomputed pixel/counter checks and confirmed nine full ownership transfers /
11,428 logical bytes, including2D/f64/replacements/3D. No extra probe calls were
added: existing windows/totals provide the ownership evidence. Root admission is
`build/native60-prep-root-1/gpu-final-admission1.json`; runtime/profile hashes and
saved driver are rechecked there. All GPU worker/environment/cache/cwd ownership
checks and seven shutdown zero counters pass. This is finite functionality, not
scientific, queued-lifetime, recovery, performance or release qualification.

Generated objects were cleaned after terminal audits: 107 native plus24 wheel
objects, 189,684,480 bytes total. Binaries, libraries, source, raw logs and frozen
evidence remain. Wheel UV cache and finite-GPU owned environments were removed.
The two previously policy-rejected WSL dependency/cache directories remain
untouched; no retry through another method was made.

Next queued-lifetime source and 16 immutable fixture/reference members are staged
at `build/native60-prep-root-1/lifetime-source-preparation1.json`. Five lifecycle
helper functions match current ASTs; actual optimized-worker refusal occurs
before renderer import and preserves all eight missing-case records. These CPU
controls are not a lifetime GPU run. Source review/admission/execution are next,
followed by device recovery, matching scientific/image/volume/numeric controls and
the unchanged performance gates. Native60 performance has not been measured;
Native59's old engineering ratio is not a Native60 result. Installed Native58
remains unchanged, and new optimization source is not yet pushed.

Native60 freeze and Linux CPU update, 2026-10-22: source46/evidence60 freeze
completed and root checked its identities. Frozen-input SHA is
`9201c4f1508eb2409f04c757e6ee4e61d9ff84902f30b4f62c753d6a95ad0a1b`,
source tree is
`d0f7efbb80c1f24f8971cd4d5c1f1ea4b23acb93a02d6777e9fa1f4e9ef54e58`,
and harness tree is
`4b07974813c482fad24f3f992c848f340bd61560a2f29cfbe408e6031486323c`.
The existing pipeline then started build1, pid74828, exec session21644. Poll that
same live handle. Full runtime compile and all 47 native CTests are still pending
at this checkpoint; no new native artifact or wheel is admitted.

The unchanged permanent contracts also passed all three CTests in actual Ubuntu
WSL with GCC13.3 and Python3.12.3 / NumPy2.4.6: 70 decoder checks, 148 packing
checks and 454 texture cases. This includes the real injected allocation failures
on Linux. NumPy came from one official SHA-pinned manylinux wheel installed into
an exclusive target; no global Linux package install was performed. Actual
worker start/nonce/source hashes, terminal observation, raw logs/JUnit, source
closure and ELF binaries are retained under `build/native60-linux-cpu-root-1`.
`audit1.json` independently checks the saved results. This is a CPU header/binding
contract, not a Linux Dawn renderer build, wheel or GPU hardware qualification.

`native_terminal_audit1.py` and wheel recipe/finalizer are prepared under
`build/native60-prep-root-1` for the next completed stages. Selected draft builder
is `wheel_build2.py` with `finalize_wheel_plan2.py`: source inspection corrected
a stale Native59 status path before any launch, preserving unused draft1. The
wheel plan still requires actual Native60 terminal47 audit/frozen identities;
historical Native59 artifacts are recipe inputs only. Wheel builds must compile
fresh project outputs and retain both AGPL and original BSD notices.

Cleanup note: the Linux temporary-directory cleanup returned ENOENT; a subsequent
read-only check confirmed that exact path absent. No second delete was attempted.
Automatic approval review rejected removal of the Windows-hosted WSL
`site-packages` and `uv-cache` directories before the command executed, reporting
only "blocked by policy". Those two directories remain in place. The rejection
is recorded in `runtime-cleanup-rejection1.json`; do not retry either target via
another method. Sources, binaries, inputs and all raw evidence stay preserved.

Source integration update, 2026-10-22: the reviewed integration4 sources are now
in the canonical repository. Permanent tests and main CMake wiring add
`owned_texture_contract`, `owned_upload_decoder_contract` and
`owned_upload_packing_contract`. All three actual CTests pass (454 texture cases,
70 decoder checks and 148 packing checks). The decoder and packing tests load a
CPU-only nanobind inspection module built from the actual binding headers; it is
a test target with no install rule. A scalar/nested-container equivalence case
replaces the private test's frozen telemetry-wrapper case; the private wrapper
evidence remains preserved. Source promotion and before/candidate copies are at
`build/native60-source-integration-root-1/promotion-result1.json`.

The actual source parser also imports with the installed Native58 module and
preserves default bytes packing/source snapshot behavior. Both private entry
points are absent in Native58, so its real parser condition selects legacy
execution. This import/selection check did not execute the renderer and is not
the required installed-wheel consumer or GPU fallback admission. Existing public
typed API and native-epoch regressions pass 126 tests; temporary test files and
14 generated objects (3,366,459 bytes) were cleaned after actual terminal waits.

Native60 preparation has 618 source members, 4,141 harness members, 44 targets
and 47 CTests. The new packet owns seven native files and two test C++ files;
runtime.cpp, runtime.hpp and module.cpp transfer from prior owners without
rewriting their immutable archives. Original BSD/license/notices, SDK, dependency
origin authority, preparation and entrypoint guards remain unchanged. Actual
read-only preflight passed, and the independent metadata review returned
`READY_FOR_NATIVE60_FREEZE_AND_BUILD`. Root approval binds the exact manifest
`2b51dc5664f549bc847e9ec017983e75a8adac8fb53c3f6206f25cf350def0df`
in `build/native60-prep-root-1/approval1.json`.

The once-only freeze/build pipeline is launched, with `freeze1` running at this
checkpoint (exec session21644, launch pid83516). Poll that existing handle; an
observation timeout is not terminal and must not trigger another launch. Full
runtime compile, all 47 epoch CTests, binary audit, wheel and GPU/scientific/
lifetime/recovery validation remain pending. Native58 is still installed. The
metadata review records one harmless test-comment inaccuracy about Dawn linking;
real SDK linkage and Python imports are explicit epoch CTest gates. No native,
GPU, performance or release admission is claimed from launch or CPU evidence.

Private integration update, 2026-10-22: the actual proposed nanobind decoder,
capture layer, Python packing route and consuming runtime entry point are now
assembled under `build/native60-owned-upload-prototype-root-1/integration4`.
The binding compiles as an object, and its exact decoder/capture headers run in
a CPU test extension. All 70 decoder checks, 148 packing checks and 454 checked
texture cases pass. The final helper also passes existing texture assertions,
the unchanged 14,603 FullUpload preparation-equivalence cases and twelve original
OpenGL byte cases. These are CPU checks; full `runtime.cpp` has not compiled yet.

The const interpreter API remains replayable. An explicit owned entry point
consumes its command vector, and only validated complete non-depth 2D/3D uploads
transfer storage into the texture shadow. All 1D history behavior remains on the
copy route. The default packing API still emits legacy bytes; the parser uses
native capture only when both private native entry points exist. Capture/fallback
counters and logical-byte timing scope are explicit. Unsupported dtype and
exporter failures retain the old representation, including its endian behavior.

Root inspection found an exception-safety gap after the first integration review:
allocation failure during collection could leave uncollected snapshots reusable.
The final batch guard retains the command root before allocation and discards its
payload leaves without allocating. Eight injected C++ allocation failures each
invalidate all three snapshots and translate to Python MemoryError. The explicit
owned protocol requires acyclic list/tuple command trees; legacy custom-sequence
acceptance remains unchanged. Final independent review returned
`READY_FOR_PRIVATE_NATIVE_EPOCH`, and the root decision is
`integration4/root-admission1.json`. Earlier failed builds and fixture records
remain preserved. Cleanup removed 58 generated objects totaling 19,322,056 bytes;
binaries, inputs, sources and raw evidence remain intact.

Next promote the reviewed sources with permanent regression contracts and CMake
wiring, then freeze a fresh native epoch and build the complete runtime and wheel.
Repeat external-consumer, NumPy 2.4.6, scientific, lifetime, recovery and GPU gates
before performance qualification. This final integration was tested with NumPy
2.5.3; earlier primitive checks on 2.4.6 do not qualify it. Production source and
installed Native58 remain unchanged at this checkpoint. No speedup or release
claim follows from the CPU tests. AGPL and original BSD/notices remain attached.

Owned-upload CPU prototype update, 2026-10-22: private primitives now pass
454 checked-iterator cases, the existing texture assertions and 14,603 upload
equivalence cases, and all twelve unchanged OpenGL byte controls. Buffer and
packing-time snapshot controls pass on Python 3.12.8 with NumPy 2.5.3 and a
fresh pinned NumPy 2.4.6 environment. The selected design captures into a native
owned snapshot during packing, then transfers its allocation. A plain
memoryview passed to a later decoder is not selected because it would delay
the snapshot and change behavior when later command conversions mutate data.

Review found two integration hazards and the corrected controls cover both:
preserve the legacy 1D update-history classification, and keep unsupported
NumPy dtypes/export failures on the original bytes path. Transfer requires an
explicit permission and reports whether it consumed the payload. Validate shape
rank before any caller-side indexing, or conservatively keep 1D on the copy
route. The legacy default `pack_commands` bytes protocol remains unchanged.

The reviewed CPU packet is
`build/native60-owned-upload-prototype-root-1/integration-packet1.json`.
It is ready for private integration, not a native runtime or wheel admission.
Next implement an explicit consumable command-owner entry point and the actual
nanobind snapshot decoder. Keep the const API, fallback behavior, logical byte
counts and timed packing wrapper; translate errors and discard failed owned
batches. Freeze the candidate sources directly before building a new native
epoch, then repeat lifetime/scientific/GPU gates. No new performance improvement
has been measured, and the Native59 engineering result below remains current.

Native59 engineering update, 2026-10-22: the first optimization is scientifically
validated but remains insufficient for performance. One new predeclared pair
completed with 1,000 measured frames per role and passed saved receipt, quality,
change-discrimination, counter and attribution checks. Median completion latency
was 74.4125 ms upstream and 162.50565 ms candidate (2.18385 times upstream).
These are one-pair engineering observations, not the required five-pair result;
they must not be compared directly with the older pair medians as a speedup.
The new pair and audit are retained under
`build/native59-engineering-full-update-pair-root-2` and
`build/native59-expose-diagnostic-prep-root-1/engineering-pair2-audit.json`.

Recorded candidate Python packing has a median of 25.46395 ms per frame.
Native decode and texture-conversion counters average 45.87104 ms and
29.76164 ms per frame, respectively. These timers overlap and use different
summary statistics; do not add them. Source inspection confirms that Python
still creates `array.tobytes()`, the binding copies those bytes into `ByteBlob`,
and complete `apply_texture_data` copies them again into texture shadow storage.
The Native59 borrowed upload removes later preparation copies, not these earlier
ones. Next, prototype owned full-replacement transfer and synchronous one-copy
buffer capture together before committing to another native build epoch.

Controlled Windows redraws also reproduced the historical spontaneous Qt expose
and paint sequence. An unreserved redraw performs real work with no measured
receipt; reserving first yields one correct receipt. Keep the current rejection
of unattributed work. No renderer suppression or reassignment is justified by
this evidence. The historical external sender and surface-change causality are
still unknown. Any later qualifying collection must retain these limits and all
failed attempts, and must not include the diagnostic event observers.

The current native volume full-update path is too slow in the new observations.
Two valid 256³ float32 MIP pairs have a median of run medians of approximately
31 ms upstream and 116 ms candidate. The collection is incomplete and retains
instrumentation gaps, so these numbers do not qualify a release. They identify
an engineering problem against the unchanged update requirement: candidate
median must be at most 1.10 times the upstream median.

Native counters and source inspection identify repeated host byte copies and
texture preparation as concrete targets. Inclusive timer scopes overlap and
must not be added together. Removing copies alone is not assumed sufficient to
meet the target. The first independent planning packet is retained privately at
`build/volume-full-upload-plan-root-1`; it is advice, not an implementation or
admission result.

1. Build a private CPU prototype after live timing workers finish. Preserve the
   canonical native source, current native modules, frozen inputs, and wheels.
   Compare a copied legacy preparation path against the proposed path using
   identical inputs and exact descriptor/byte/exception comparisons.
2. First optimize only complete uploads whose existing direct-format predicate
   already proves byte identity. Separate descriptor validation from materialized
   preparation bytes, and use a short-lived view of the engine-owned source
   vector through the upload call. For aligned rows, avoid creating and copying
   a redundant padded vector. Preserve conversion, empty-source, partial-update,
   and unaligned-row fallbacks. Borrow no Python pointer beyond the binding call.
3. Test float32 NaN payloads, signed zero, subnormals and infinities; integer
   identities; normalized and half-float conversion; channel expansion; empty
   input; mixed source types; bounds and overflow; and aligned/unaligned 2D/3D
   extents. Check source immutability and ownership through moves. Run the
   existing texture contracts and conversion corpus against both paths.
4. Audit every consumer of preparation bytes before porting the change. Storage
   accounting, texture views, samplers, pending revisions and asynchronous GPU
   lifetimes must retain their existing behavior. Reject any byte, descriptor,
   exception, non-timing counter, or ownership mismatch.
5. Port a proven prototype through a new native source epoch, fresh build and
   wheel, and fresh scientific and image admissions. Existing artifacts and
   saved references remain unchanged. Compare actual full-update upload counts
   and bytes, all hot-work gates, GPU ownership, waits, and allocation accounting.
6. Collect a fresh predeclared five-pair full-update result after fixing the
   unsolicited expose-paint ownership problem. Keep all failed attempts.
   Preserve the quality limits, input sizes, update formulas, precision, volume
   sampling, and performance thresholds.

If the first change is insufficient, next evaluate transferring an already
owned full-replacement blob rather than copying it, and removing the redundant
Python `tobytes` intermediate while still capturing immutable bytes before the
binding returns. An asynchronous staging-buffer design requires a separate
lifetime and reuse plan; no synchronous wait is acceptable on the measured path.

Pending independently: scanout measurement, complete driver/allocator peak
accounting, the remaining workload/platform matrix, and every other original
release requirement. The implementation remains AGPL-3.0-only with the original
VisPy BSD license and third-party notices attached unchanged.
