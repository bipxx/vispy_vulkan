Source-archive build checkpoint, 2026-10-23: CMake now restores recognized Git
export-subst expansion of vendored VisPy archival metadata to the exact original
CRLF/no-final-newline blob before ordinary dependency verification. The standalone
checker stays read-only by default; checkouts, unrecognized edits and explicit
immutable-origin authorities are not rewritten. Dependency pins and license bytes
are unchanged. Nine focused regressions pass, including a genuine Git archive,
other-source mismatch and explicit-origin controls.

A complete real source archive at 727c5356640ff10c6325bee44c27049c2c75aa73 first
reproduced the sole VisPy checksum failure. Fresh native Linux Release CMake
configuration then restored the metadata automatically and verified all ten
original dependency trees; subsequent read-only verification passed. Archive,
lock and AGPL/original-BSD inputs remained unchanged. No renderer rebuild or GPU
claim is made for this build-script change. Owned build environment/cache and
both pytest temporary directories were removed; inputs, logs and failures remain.
The hosted Metal wheel jobs are still queued.

Metal producer preparation checkpoint, 2026-10-23: a separate hosted macOS
arm64/Intel CPython 3.12 workflow now builds the actual Metal renderer wheel.
The configured checks cover macOS 13 tags, Mach-O architecture, stripped native
origins, package bytes, system-library dependencies, AGPL/original-BSD licenses,
the compressed-wheel budget and isolated compiled-extension/CPU-SDF consumers.
Local Python/YAML and six shell-body syntax checks pass. Actual native macOS
execution remains pending; configuration is not a successful build or graphics
qualification. The existing CPU matrix/job bodies are unchanged. Its push trigger
now selects main, retaining PR/manual runs while avoiding duplicate work-branch
push and PR matrices. Cybersecurity remains excluded.

Current allocation checkpoint, 2026-10-23: empty RGBA8 color renderbuffers now
allocate storage through Dawn rather than preparing/uploading a CPU zero image.
Fresh Windows CPython 3.12 RTX4090 Vulkan and Linux CPython 3.12 WSL llvmpipe wheels
pass archive, native-origin and AGPL/original-BSD license checks. Initial/cleared/
resized renderbuffers and queued-clear-before-resize ownership pass for named
color and desktop RGBA8 formats. Both million-marker 2D input paths pass updates
and unchanged-frame reuse; all fourteen checked compiler/pipeline/conversion/
upload counters have zero warm deltas. Nine live gauges return to zero. Four
saved marker frames per backend match that backend's preceding wheel exactly.
Clear, analytic smooth-line and compiled-SDF-text consumers also pass.

Removed 24 Windows and 960 Linux disposable objects and owned caches/environments,
retaining wheels, binaries, source inputs, raw frames, logs and failures. The
Native67 Windows marker cache remains after an automatic-review deletion denial;
no denied cleanup was retried. This is focused allocation/functional validation,
not a renewed full host matrix, Metal admission or performance qualification.
The preceding smooth-line CPU CI has twelve artifact-audited cells, each passing
1018 pytest cases and 42 native contracts with no skips. Cybersecurity is excluded.

Current practical-completion checkpoint, 2026-10-23: the refreshed smooth-line
implementation passes installed Windows wheel consumers on CPython 3.10-3.14.
The CPython 3.12 wheel passes 53 functional host/scientific cases, including
previously blocked axes/colorbar, Glue axes and napari-threedee overlays.
Forty-two complete reference frames match exactly. Exact rasterizer parity and
lab-grade latency measurements are outside the user's practical completion scope;
historical strict results and failed attempts remain unchanged.

A fresh Linux CPython 3.12 wheel builds with GCC 13/Ninja after disabling Dawn's
unused C++ module interface. An isolated WSL software-Vulkan consumer passes clear,
blended smooth-line, pipeline-reuse and compiled-text checks. Package/native-origin
and AGPL/original-BSD license checks pass; all nine live gauges return to zero.
Owned environments, caches and 960 build objects were removed; artifacts remain.
Native Linux GPU, macOS Metal and manylinux portability remain unverified.

The public host lock's eight missing source/import inventories and requirement
files are restored byte-for-byte from their existing pins. The consistency test
reproduces three missing-input failures before the fix and passes all four host
rows afterward. CPU CI now runs that metadata test. This does not promote the
historical import inventories to renderer qualification. Cybersecurity work stays
out of scope. Earlier checkpoints below retain their recorded revision scopes.

# VisPy Vulkan implementation completion plan

Current source checkpoint, 2026-10-23: portable analytic smooth lines now use the
existing generated ABI2 consumer in both runtime paths. Width stays a uniform,
including fractional/subpixel widths. Coverage modulates original fragment alpha.
The user relaxed exact rasterizer parity and lab-grade display measurements as
practical completion gates; historical strict results remain unchanged.

An isolated current-source build verified ten immutable dependency origins and
the 213-file SDK. The generated-consumer C++ contract passed 38343 checks. Fresh
RTX4090 Vulkan rendering passed five whole-RGBA line checks against the declared
analytic policy (maximum error1), plus clipping, perspective, depth occlusion and
alpha blending checks. Width changes reused consumer/pipeline; nine checked live
resource gauges were zero after shutdown. The previously blocked axes/colorbar
fixture rendered and its saved image was visually inspected.

This is bounded source-build validation, not refreshed wheel/host admission or
exact OpenGL parity. Exact-reference smoothing and MSAA remain unsupported.
See docs/smooth-lines.md. Installed Native58 and all historical evidence remain
unchanged. AGPL and original BSD notices remain attached. Cybersecurity work
remains out of scope.


Current checkpoint, 2026-10-23: Native66 Qt presentation fix is ready for review
on `work/qt-single-present`. Backend swaps inside a native paint scope now defer
presentation until the alpha-clear tail is complete. Nested busy paints preserve
the outer paint token; the earlier native API keeps its existing swap sequence.

Validation on the fresh Windows CPython 3.12 wheel:

- 22 Qt CPU regression cases passed, including a nested-paint regression that
  reproduced the token-clearing error before the fix.
- All 44 native targets built and all 47 CTests passed, followed by the terminal
  source, compiler-policy and artifact audit.
- All 75 Qt stress cases passed: 25 loss/recovery cycles and exact red readbacks
  per PyQt5, PyQt6 and PySide6 binding.
- All 17 scientific-volume controls matched exactly across 156,672 pixels.
- All 24 large-volume controls passed across 96 complete frames and 251,658,240
  pixels, with maximum channel error 1 within the unchanged limit of 2 and no
  excluded pixels.

The isolated wheel passed package, native-origin and license audits. Its SHA256
is `ea48141c8bc1988d038eabd984f704e4a25d20fe1f38b432d0a91fb9a107cddd`.
The implementation remains AGPL-3.0-only; original BSD licenses, copyright and
third-party notices remain attached unchanged in source and the wheel.

The first volume workload completed five alternating OpenGL/Vulkan pairs, each
with 100 warm-up and 1,000 measured frames. All 10 workers and 15 paired full-frame
comparisons verified, with no unattributed draw, parser or paint work. Each
candidate measured 1,000 application/Dawn presents and 2,000 Vulkan submissions.
Release performance remains **unproven**: input-to-visible scanout and complete
driver/allocator peak accounting are still missing. These results do not qualify
a speedup or all 24 timing workloads.

The full implementation remains WIP. Marker and million-point parity, smooth-line
parity, remaining host/platform/hardware coverage, scanout and allocator evidence
remain open. WSL currently exposes only software Vulkan; macOS Metal hardware is
unqualified. Current source is epoch 66, snapshot 52; installed Native58 stays
unchanged. Removed 131 disposable object files (about 181 MiB) after terminal
validation, retaining binaries, sources, logs and raw evidence.

Historical checkpoints follow; each describes the state at its recorded revision.

Continuation checkpoint139, 2026-10-22: ACTUAL final63 image13, large24 and
large-image4 all passed their once-only serial runners, independent saved
audits and final admissions. Together with prior core44/scientific17, this is
102 scoped real GPU cases on the SAME fresh PEP517 wheel
c4b864e1e9123692ff70d25604815c96110a64f2979563e50f9d81ae436aebca,
native4f270c9ab9611948f1ece66a90c45f6195280a66527c64be75558b7f0e42038f.
Native47/source618/harness4141/full guards remain the actual compiled source
identity. No installed58 activation or production source change occurred.
All these are scoped correctness/quality results, not full release qualification.

Image13: source review39492/Claude71024 completed0 READY, followed by actual
execute_image1.py on exec66422 terminal0. Admit62316/run86924/saved38852/
final39648 all completed0. Every original13 entire128x96 RGBA frame matches
exactly,159744 pixels, zero error/exclusions. Independent audit retains host,
module origins, package identity, nonce/creation/actual terminal and cleanup
checks. `small` joins use ACTUAL scientific17 saved2 and current approved1;
the historical59 hard-coded wheel pin was replaced with current artifact
identity. Final `image-controls-final-admission1.json` and
`image-execution-control1/result.json` are under
`build/native63-science-prep-root-1`. Owned environment tzjfw8e3 and cache/cwd
were removed after terminal proof. README now reports this current artifact.

Large24: source1 retained a byte-exact59 executor that correctly still refused
any other wheel through its CANDIDATE_SHA global. This was caught BEFORE any
GPU execution; no failed GPU run/retry occurred. Source2 changes ONLY that
global fingerprint in new large_worker2.py, proving whole-byte inverse and
identical AST for EVERY function body. New execution-manifest2 changes only
explicit wheel/executor/scope metadata; all333 original inputs, data_manifest
and original manifest1 remain unchanged. Wrapper changes epoch status only.
CPU controls pass exact24 case-loop/saved96-frame-counter-loop equivalence,
current executor/manifest/wheel binding and real early -O refusals.
Actual review11392/Claude58344 completed0 READY. Actual execute_large2.py on
exec79109 completed0: admit41536/run91184/saved68692/final59872. The original24
workloads pass96 full frames,251658240 pixels,48 change-discrimination checks,
zero exclusions, maximum channel error1 within UNCHANGED original requirement2.
Independent saved audit recomputes all raw counter deltas, resident/full-update
hot-work zeros, upload bytes, camera/data/depth and intercepted Vulkan allocation
conservation. It does not establish opaque driver peaks or performance.
Final `large-controls-final-admission2.json`, saved SHA
285329db9ab2b4c3b3ec6afefef1987512a8cad192e785828932ae5e6dac126a.
Environment5j4wqmx8/cache/cwd removed after actual worker terminal.

Large-image4: source2 changes only the old59 executor wheel-fingerprint global;
all original function bodies and69 fixed inputs/data/reference criteria remain
byte/AST preserved. All CPU source equivalence/current fingerprint/early -O
refusal controls pass. Actual review4005/Claude63400 completed0 READY. The
review's nonblocking pre-install wheel-SHA observation is already covered by
the chained gate.verify -> base.verify -> artifact_gate2.verify, which checks
actual wheel bytes before install; no post-review source modification needed.
Actual execute_large_image2.py on exec8217 completed0: admit87728/run76088/
saved90708/final76400. All4 original4096square image cases pass16 whole exact
RGBA frames,268435456 pixels, zero error/exclusions,12 resident checks. Separate
saved reader recomputes original analytic/FBO/noDATA/residency/raw counters.
Final `large-image-controls-final-admission2.json` SHA
8bdc5d9657592392709e01e9fc20c6866f2874ba7ab1d2268eb42cc5c48b5391;
saved audit SHA f970c37b8c3da0bfad5a0863d79231fcb7535b06c8993721a40dc49219372b36.
Driver also holds the successful saved-audit SHA between saved/final stages.
Owned environment yvgcyzu8/cache/cwd removed after actual terminal.

Every new group gate binds the unchanged full550 vispy namespace and all523
pure/4 native/23 license payloads, original AGPL/BSD/notice bytes in both copies,
actual47/core44/scientific17 and prior terminal/cleanup results on this exact
wheel. Each group is serial, source/receipt held before/after stages, uses actual
child waits/one-hop Windows creation stamps and nonces, preserves unknown
workers and blocks new GPU work via the global hold, and never retries.
All observed build/review/GPU handles this checkpoint are TERMINAL. No owned
test environment/cache remains; no extra object cleanup or denied cleanup retry
was attempted. Raw success/failure images/logs/source/proofs are retained.

Read-only publication inventory `build/native63-publication-prep-root-1/copyplan3.json`
actually verifies every618 canonical source hash against approved63/actual47.
It uses canonical promoted source directly, with ZERO private overrides,
preserves existing publication .gitignore/exclusions and excludes native/build
junk. It finds188 changed/4236 unchanged/0 missing selected source files against
clean isolated public checkout main at be393c3f8eac3554461af514607e3d3a7983c689.
All ten vendor trees are outside the payload inventory. No copy, Git mutation,
commit or push occurred. README and this checkpoint changed AFTER that plan;
refresh/revalidate their row hashes before any copy. Authorized public WIP push
still needs concrete diff review/appropriate checks and honest qualification
limits; canonical workspace still must NOT be git-initialized.

Read-only performance evidence recheck ACTUALLY passes:
`build/native63-performance-prep-root-1/prior-failure-inspection1.json`. Required
Reader gates every historical payload, retains the original failed/partial
collection and never replays an old worker. All1000 stored frame samples each
have exactly one assigned update/draw/paint; raw before/after counters confirm
two ADDITIONAL unowned draw/paint paths, eight unowned GLIR parse/pack calls,
native1002 scene draws and2004 presents. This is actual extra work, not missing
good rows to exclude or reassign. Event cause is NOT established by aggregates.
Frozen tools/benchmark_frames.py remains exact
55f76b5cf1bc95b23547b572af61e41a6bd524911fd44bc2305318002e60ab26.
Current63 performance remains UNMEASURED. Next performance step is a current63
admission using real large quality proofs, then a bounded Qt event/paint-origin
diagnostic without altering frozen benchmark or suppressing/reassigning work,
before any justified lifecycle/renderer fix and original five matched pairs
at unchanged threshold1.10. Do not blindly optimize retained64MiB shadows first.

NEXT: prepare/review the actual63 performance admission and event-origin
diagnostic; refresh/review publication diff and perform the authorized WIP push
when source checks are ready. Portable SmoothReference/all16 fixed frames and
host overlays, broader ordinary/full30/other host workflows, other ABIs,
native Linux GPU/Metal, scanout and complete allocator/opaque driver peak
requirements remain in original13 scope. Private native smooth route remains
falsified/not promoted. Full goal stays active, cybersecurity excluded,
AGPL3-only implementation plus original BSD/copyright/notices retained.

Continuation checkpoint138, 2026-10-22: ACTUAL scientific17 on the fresh63
wheel is now admitted. `build/native63-science-prep-root-1/execute_small2.py`
completed all four serial stages0 on exec85883: admit90744, run12660,
independent saved audit87556 and final admission33948. Its
`small-execution-control2/result.json` is
PASS_NATIVE63_ACTUAL_SCIENTIFIC17_AND_INDEPENDENT_SAVED_ADMISSION.
`small-controls-final-admission2.json` is
ROOT_ADMITTED_NATIVE63_SEVENTEEN_SCIENTIFIC_VOLUME_CONTROLS,
SHA b4fbe8a852e14f1a75a362f25557640ca37a794398843e2649aa3e939879c150.
Wheel remains c4b864e1e9123692ff70d25604815c96110a64f2979563e50f9d81ae436aebca;
native4f270c9ab9611948f1ece66a90c45f6195280a66527c64be75558b7f0e42038f.

All original17 scalar/categorical volume cases passed their unchanged semantic
and reference criteria PLUS exact entire96x96 RGBA comparisons:156672 pixels,
zero excluded pixels, zero differing bytes and maximum error0. Independent
saved audit SHA7e783788a79b2bfd9b2a7f36990c66dbc63eca69ab9cb392dde47084c5442324
rechecks every raw frame, producer closure, process/nonce/creation joins,
installed package/native origins, Vulkan RTX4090/driver610.88, CPython3.12.8,
NumPy2.4.6 and categorical napari0.9.2/Numba0.68.0/PyQt6, eight shutdown zeros,
input preservation and cleanup. All17 actual workers are terminal. The owned
environment `vispy-image-wheel-b8ncdlos` and owned runtime/cache/cwd were removed
only after terminal proof; teardown is PASS_OWNED_ENVIRONMENT_TEARDOWN.
Installed58 native4 remain unchanged. Core44 plus scientific17 now make61
bounded real fresh-wheel GPU cases; no broad release qualification follows.

First actual source review33984/Claude74148 completed0 with FIX: the new
gate independently checked523 pure/native4/root licenses but did not enumerate
and verify all23 attached license files or exact550-member vispy namespace.
That review and source1 are preserved; no scientific GPU launched under them.
Source2 adds exact550 set equality =523 admitted pure +4 native +23 admitted
license members, derives every license digest from the held approved63 source
manifest, checks all23 bytes and refuses duplicate archive names. Root AGPL,
original unchanged BSD and LICENSING.md still match BOTH archive copies.
Reader2 additionally joins runtime SHA to admission and requires actualGPU.
Both versions' CPU controls pass exact wrapper inverse/17-case controller AST
(except additive verify calls)/17-case saved-reader AST and actual early -O
refusal before output/device creation. Original worker/fixtures/assertions are
unchanged. Source2's first review packet preparation refused a nonexistent
historical59-small_controls_saved_audit2.py path before Claude/GPU launch;
physical pre-fix review/artifact bytes and refusal receipt remain. The packet
path alone was corrected to the actual preserved historical1 source. Actual
review53312/Claude90404 then completed0, READY_FOR_SMALL17_GPU_EXECUTION.
Execution used ONLY reviewed source2 with held hashes, current approved1
manifest, actual native47/fresh wheel/core44 joins and unchanged criteria.

Read-only follow-up input preparation also completed0 on exec57967. It uses
the required Reader before each historical payload, checks original admission
hashes and preserves all inputs: image13 has107 members, large24 has333,
large-image4 has69. `followup-input-preparation1.json` records ZERO current
source deltas in all three groups. No GPU execution/admission is implied.
`prepare_image_sources1.py` prepares current63 image13 controller, wrapper and
saved reader only. Wrapper changes epoch protocol tag only; controller/reader
retain original13 entire128x96 frames/host/lifecycle criteria, replace the old
hard-coded59 wheel identity with actual artifact binding, and point at actual
scientific17 saved audit2/current approved1. `image-cpu-controls1.json` passes
exact controller/reader case-loop AST equivalence (only additive verification),
wrapper inverse and early -O refusal, with no GPU. Image execution remains
NOT READY: image_artifact_gate1.py, sealed actual artifact/source admission,
final admission and independent source review still need implementation.
Historical59 controllers/workers are adaptation references, never63 results.

README now reports the actual scoped63 native47/core44/scientific17 results
and explicitly retains large-workload/performance/platform/smooth-line gaps.
No publication copy/commit/push or installed native activation occurred.
All observed process handles this checkpoint are TERMINAL; no live build,
review or GPU worker remains. Owned environment/cache cleanup completed,
and denied historical cleanup attempts were not retried. Earlier once-only
136-object cleanup is not repeated. No cybersecurity work; original BSD
notices stay attached alongside AGPL.

NEXT: finish/review/bind/execute the image13 pipeline on this SAME fresh wheel,
then retarget and qualify the prepared unchanged large24 and large-image4
controls. Preserve original five matched performance-pair gate and unresolved
unattributed Qt paints, all16 smooth frames/host overlays, ordinary/full30,
other ABIs/platforms/native Linux GPU/Metal, scanout and full allocator/driver
peaks. Original13/full goal remains active; none is replaced by this batch.

Continuation checkpoint137, 2026-10-22: Native63 freeze/full runtime build,
all47 CTests and unchanged final guards are TERMINAL0. Independent terminal
audit passes exact618 source/4141 harness. Source tree
4c37994cae698331be61d18dc5dbf5c825c394e21d43da529a9850832b25cdd5,
harness tree6805462d0d538c4d038663093a0e3cde077246aabf08cff5f2c505d7444f20a5,
frozen inputs cbe9fc270f0003b4d178f9b38ff7367796fba16633ff60ab2b4faa4e5eb93d5b.
The creation-bound owner wait and all eight subsequent qualification-chain1
stages completed0, observed through actual exec session35184 termination.
`build/native63-prep-root-1/qualification-chain1/result.json` records the full
held-source chain; do not restart it or its already successful stages.

Fresh PEP517 wheel is ACTUAL, not the private patched baseline:
`build/native63-wheel-windows-cp312-root-1/wheels/vispy-0.17.0+vulkan.1-cp312-cp312-win_amd64.whl`,
SHA c4b864e1e9123692ff70d25604815c96110a64f2979563e50f9d81ae436aebca.
Actual fresh native4 origin/523 pure-package byte/license checks pass. Its
native _dawn SHA is4f270c9ab9611948f1ece66a90c45f6195280a66527c64be75558b7f0e42038f.
AGPL3-only LICENSE, original unchanged BSD LICENSE-BSD and LICENSING.md are
attached BOTH within vispy/_licenses and wheel dist-info/licenses; original
VisPy BSD copies all retain SHA a28bb857d763513c810ca843558c12cf97f64b990b855c1ce7f5e291e52fc25c.
No installed58 native activation occurred. Native63 binding17 failure-only CPU
checks and fresh-wheel-identical binding17 checks both actually pass, with no
device/renderer created by those CPU controls.

On that SAME fresh wheel, actual source-held finite8/23 entire captures,
queued lifetime8/5, recovery7/16 and numeric12/13304 logical values all pass
their original worker assertions and separate saved/root audits. Finite owned
transport remains9 transfers/11428 logical bytes. All35 core cases passed;
this is not full release/scientific/performance/platform qualification.
Recovery source3 peer FIX (missing prelaunch current-wheel/upstream identity
join) remains preserved. Corrected source4 admission/controller/readers and
final3 passed CPU controls, actual independent READY review, then the actual
seven-case GPU run. Finite/lifetime/numeric actual source reviews are READY.
All owned core environments/cache/cwd were removed after known worker terminal;
no unknown GPU worker hold was present at the next launch.

Native smooth capability investigation is PRIVATE and NOT promoted. RTX4090
reports native smooth/wide capability; Intel UHD770 smoothLines is false. The
auxiliary full vulkaninfo discovery was explicitly stopped once after its
needed feature blocks: exact creation-bound child14980, terminal exit130;
partial log retained, not a successful full utility run. Actual read-only
planning review recommends a standalone fixed two-case falsifier before any
Dawn/layer edits, and rejects ambient global/TLS policy because Dawn pipeline
specialization is lazy and descriptors can deduplicate. Standalone direct
Vulkan probe compiled successfully, then ran ONCE after the whole core chain
was terminal. Actual child59316 completed2, with same-handle terminal proof.
Horizontal fixed original GL frame matches all3072 bytes; diagonal differs
at exactly x4/y19 green: native164 versus reference173. Independent audit
`build/native-smooth-line-direct-probe-root-1/audit1.json` confirms failure,
source/input/reference hashes and unchanged zero-tolerance whole-frame rule.
The reference driver was595.79 versus current610.88; this does not authorize
changing references. Stop this native route; no retries, threshold edits,
production layer/runtime change or portable/all16 success claim follows.

`build/native63-special-prep-root-1` adapts the previously successful fixed
extra1D4/6 captures, generated-line4/8 and canonical Qt1/1 to the ACTUAL fresh
wheel. Original workers/wrappers/oracles and image/counter assertions are byte
preserved. New shared gate joins47/native origins/core35, actual wheel bytes,
all523 admitted pure files, native4 and AGPL/BSD/notice copies before install
and launch; controller/reader/execution scripts are held. First CPU-only gate
refused a mistaken count of523 for all wheel vispy files (actually550 =523
pure +4native +23license). Original gate/artifact are archived, and refined
gate instead verifies all523 admitted package bytes plus native/license checks
separately, before any special GPU run. Refined gate passes. Independent
read-only review49488/Claude87408 completed0, verdict READY_FOR_SPECIAL_GPU_EXECUTION,
with no concrete blockers. The two nonblocking observations (failure traceback
can be masked by a finally verification after an unknown-worker hold; Qt's
saved reader relies on the wrapper/device and gate/native joins) remain visible
in the retained response. All unknown-worker safety/retention rules hold.
Source-held execute1.py then ACTUALLY completed0 on session46089: extra4/6,
generated-line4/8 and Qt1/1, every original case/assertion plus separate saved
audit passed. Aggregate `execution-control1/result.json` is
ROOT_ADMITTED_NATIVE63_ACTUAL_FRESH_WHEEL_NINE_SPECIAL_CASES_FIFTEEN_CAPTURES,
same wheel c4b864e1e9123692ff70d25604815c96110a64f2979563e50f9d81ae436aebca.
All owned environments/cache/cwd were removed after observed actual worker
terminal. No private patched native, forced chunk controls or old results were
substituted. Core35 plus special9 =44 bounded real GPU cases on fresh63.
Subsequent `post-admission-audit1.json` independently rechecks all six actual
terminal operations and Qt's vendor/device/driver plus exact wheel-zip native
bytes, closing that nonblocking independent-reader observation without reruns
or edits to reviewed worker/controller/source bytes.

Next scientific input preparation ACTUALLY executed0:
`build/native63-science-prep-root-1/small-input-preparation1.json`. It copies
the unchanged85-member fixed17 scientific-volume closure using the required
Reader before every historical payload access, verifies all hashes, and finds
ZERO current-source deltas against the original packet. Historical59 controller
and wrapper copies are retained only as adaptation references. No scientific
GPU run/controller/admission/saved audit or new source review exists yet; do
not execute the historical59 controller as63. This prepares the next real
fresh-wheel scientific qualification without changing references/assertions.

Once-only bounded cleanup after actual build/wheel/probe terminal audits
removed136 owned .obj files,197309039 bytes, from exact native63 SDK build,
fresh wheel native-build and private direct-probe build roots. Receipt:
`build/native63-prep-root-1/completed-objects-cleanup1.json`. All binaries,
libraries, raw success/failure frames, source, frozen evidence and logs retained.
Do not rerun this cleanup or historical policy-denied cleanup attempts.

NEXT: author/review the actual63 scientific17 controller and independent saved
audit against the prepared fixed inputs and fresh wheel, then execute once.
Broader scientific/image/volume/hosts, all other ABIs, five matched performance
pairs, full allocator/driver peaks, scanout, native Linux GPU and Metal remain
required by the original13 items. WSL63 compile-only remains useful but not
Linux hardware qualification. Portable SmoothReference remains refused and all
16 fixed frames/host requirements stay open. Public main is still unchanged;
refresh the copy plan and honest qualification docs before any authorized push.
All processes from this checkpoint are terminal; no live build/GPU/review handle
remains. Full goal remains active; no cybersecurity work; AGPL plus original BSD retained.

Continuation checkpoint136, 2026-10-22: Native62 pipeline session76107 is
TERMINAL0. Actual full runtime build and all47 CTests passed, followed by all
unchanged final dependency/source/origin/compiler/protection guards. Independent
`build/native62-prep-root-1/native-terminal-audit1.json` passes47/47, frozen618
source/4141 harness, binaries and original AGPL/BSD/installed58 continuity. The
pending `build/native63-line-coloronly-prep-root-1/promote1.py` then executed0:
exact uninstrumented three CPP files and existing generated consumer test are
now CANONICAL. Promotion SHA is
a168c69aa838cc6148c1ccfd3470b3235d60f5354973dec9d926b9822b792efe.
The test-only two-row controls were not promoted. No installed native activation
or new wheel/public push occurred.

Actual WSL GCC13.3 validation of the exact63 candidate passes30 normalization
controls and compiles BOTH complete runtime.cpp and shader/line_consumer.cpp
translation units. `build/native63-wsl-portability-root-1/audit1.json` rechecks
all54 CPP members, actual Linux boot/start-tick worker identity, nonce, stage
exits/log hashes and removal of its owned /tmp directory. Observer1 had an
unexecuted stale61 prefix assertion; fresh observer2 corrected only that prefix
before actual observation. This is source compile-only, not Linux Dawn link,
wheel, display or hardware qualification. Actual `vulkaninfo --summary` exits0
and enumerates only Mesa25.2.8 llvmpipe LLVM20.1.2 PHYSICAL_DEVICE_TYPE_CPU here;
/dev/dxg and /dev/dri presence do not establish Vulkan hardware. No macOS device
was supplied. Hardware/platform requirements remain open, without blocking
other implementation/testing work or substituting software for hardware gates.

`build/native63-prep-root-1/prepare_draft1.py` sealed a CPU-owner packet using
the exact compiled/reviewed uninstrumented source/test and actual Windows/WSL
proofs, plus separately scoped whole and controlled-chunk GPU audits. Only
runtime.cpp transfers from the62 texture owner, and shader/line_consumer.cpp,
its header and existing generated contract transfer from the prior51 owner;
neither old owner is emptied, and all old archives stay immutable. After actual
promotion, finalize_manifest1 verified every618 source byte and actual62
terminal proof and finalized the source/harness bindings. Approved63 manifest:
62530fe2953a41a0361eb2d2910d40072b8b1c5d84f541e749dbfaba2b74a9f7,
retaining618 source/4141 harness/44 targets/47 exact CTests, snapshot49.

The actual once-only63 `freeze_build1.py` pipeline is LIVE on exec session58115.
Freeze launcher63000 owns actual82708, created15:37:59 local. Current dependency
launcher87328 owns actual61692, created from that same live process tree.
`live-observation1.json` records authoritative current process observations,
not just a marker. No63 freeze/build47 completion is claimed. Keep canonical
source/harness unchanged, observe the same handle, and never restart on quiet
output. Complete unchanged preflights remain enabled and actual successful
freeze automatically advances to the full build. Prepared63 wheel recipe,
builder and terminal/native-origin audit scripts use the actually successful61
recipe with explicit63/snapshot49 inputs and exact47-test gates. The recipe is
NOT_LAUNCHABLE until the real63 terminal audit binds source/frozen digests.
The superseded62 wheel recipe was never launched; final63 artifacts still need
all required CPU/GPU/scientific/host/performance/platform checks.

Read-only publication preparation revalidated clean isolated checkout
`C:/Users/HEQ/Projects/vispy_vulkan-publication`, public main at
be393c3f8eac3554461af514607e3d3a7983c689. Its latest CPU-contract workflow
39746758393 completed successfully on that commit; this does not qualify the
new63 source or hardware. `build/native63-publication-prep-root-1/copyplan1.json`
inventoried source changes without copying/staging/pushing. Refined copyplan2
preserves the publication's intentional .gitignore rules and filters101 local
generated/preparation paths, leaving187 source/doc/test/admission changes.
All ten third-party vendor trees were outside this read/copy inventory. The
publication-only docs/mesh-layout-wheel-regressions.md was restored byte-exact
to canonical docs because README references it; it is not an authorized deletion.
No publication files or Git state changed. Before copying, refresh/revalidate
the plan against current canonical hashes, promoted63 identity and actual tests;
plan doc hashes will need refresh after these checkpoint additions. Do not copy
the shorter canonical .gitignore over the publication's intentional exclusions.

Bounded once-only62 cleanup after actual successful terminal audit removed107
owned project .obj files,163,241,290 bytes. All binaries/libraries/frozen source/
harness/logs/evidence remain. WSL owned temporary outputs were removed and
observed absent. Policy-denied historical caches remain untouched; no retry.
Only main session58115 remains live from this continuation. Source/CPU/WSL and
publication preparation changed authoritative state; full goal remains active,
all original13 requirements retained, cybersecurity excluded.

NEXT: observe session58115 through actual freeze/build47 and independent63
terminal audit, bind/build the fresh PEP51763 wheel and audit native origins.
Then execute artifact-specific binding/finite/lifetime/recovery/numeric/extra1D/
generated-line/Qt and broader scientific/image/volume controls. Complete the
unchanged five-pair performance gates, hosts/platforms/ABIs, scanout and complete
allocator/driver peak requirements; push reviewed source WIP when ready with
honest qualification limits and both licenses. No final qualification is inferred
from private experimental wheels, test-only chunk controls or predecessor CI.

Continuation checkpoint135, 2026-10-22: Actual Native62 freeze completed0 and
automatically advanced to the full guarded build, still LIVE on exec session76107.
Frozen-input SHA is
89d8b59a1b5d03022b9d2765f6f5a44f43f913c17a9d51a7db622e61d1bcd5c9,
source tree439ff3deb8debe9c0d68e9422376dbe93b4d8aad5cd69e4cd27e63bd9be15076,
harness tree6640eb24c6285a7cd5f2dcf18dfb45adf892acbd655ef9f3adc6fa469af7480e.
`build/native62-prep-root-1/frozen-admission1.json` joins the actual successful
freeze receipt. Old freeze launcher43448/worker47172 and dependency15624 are
terminal; do not restart them. Current build launcher74004 owns actual42804,
created15:14:07 local; CMake87744 created15:19:45 owns current guard launcher76432.
`live-observation2.json` records the actual current process tree. The same
session76107 remains running. Build/47 CTests/native terminal audit/wheel are
not completed. Keep canonical source/harness unchanged until actual termination.

A new early GPU check at `build/native62-line1d-private-gpu-root-1` preserved a
real generated-line failure on the experimental62 runtime: a valid color-only
FBO rejects the generated fragment's unconditional FragDepth output because no
depth-stencil state exists. This is not a shader1D normalization failure; no
case was skipped and no depth attachment was added to hide it. Worker1 failed
before capturing a successful frame; origins/shutdown/actual terminal/owned
environment teardown were verified. Existing original GL horizontal_aliased
whole-frame evidence remains unchanged. The new declared analytic extension
samples(.5) from65 texels, with sole green texel32 and64 magenta texels, giving
that exact opaque-green frame. This is explicitly not a new upstream GL1D
capture or all-line/scientific/performance qualification.

Private `build/native63-line-coloronly-prep-root-1` changes only three CPP
files plus the existing generated consumer contract. Actual target depth
presence selects a depth_output policy in both whole and chunk preparation.
Color-only generated/user depth calculations retain invocation-local private
values; attached-depth shader output stays intact. Complete policy/cache
identity and retained/target checks distinguish them. Full private runtime
link and generated compiler contract pass0/38,320 total checks, including
actual SPIR-V FragDepth/DepthReplacing presence/absence, user depth assignment/
expression, key separation and composer line maps. Independent read-only
review1 finds no blocking source defect and gives conditional
READY_FOR_PRIVATE_GPU_AND_PROMOTION, requiring descriptor/leaf/loss and actual
whole/chunk hardware checks. Review sources and canonical62 remain unchanged.

The first63 GPU attempt passed its whole image and then stopped on an incorrect
native_draw_calls expectation. Actual finish_canvas/readback includes one
presentation flip, so worker2 requires exactly user draw1 + presentation1 =
native2, with unchanged compute1/endpoint2 and exact image criteria. Failed
attempt1 remains intact. Actual worker2 passed four vertex-compute/fragment-
consumer x color-only/depth-attached cases, each before/after loss without DATA
resubmission: eight whole exact images. `gpu-saved-audit2.json` independently
rehashes/recomputes every frame/counter/transport/origin/lifecycle join. These
are the uninstrumented private candidate's whole-route results.

`build/native63-line-coloronly-chunk-probe-root-1` is a separate TEST-ONLY source
and runtime. Two explicit routing controls force the existing chunk branch and
cap max_new endpoints at2; their exact inverse restores the entire production
candidate runtime.cpp and every other candidate member is byte-identical.
Actual device grants are unchanged. Four endpoints describe two identical
opaque segments, preserving the same entire GL frame while requiring two real
compute dispatches/four endpoint rows/two native scene draws plus presentation.
All four stage/target cases and recovery passed; its independent
`gpu-saved-audit1.json` verifies eight exact images/16 dispatches/32 endpoint rows,
source inverse, actual unchanged grants, lifetime/origins/shutdown and teardown.
This exercises the actual unchanged chunk functions on hardware, but does not
qualify the production artifact or real device-capacity boundary. Test controls
MUST NEVER be promoted.

The reviewer target-presence concern is resolved by source and hardware:
capture stores the depth attachment; encoding uploads/resolves its view before
pipeline creation; that view selects the combined Depth24PlusStencil8 state;
fill_pipeline_state derives descriptor presence from depth.format. Chunk leaves
copy DrawSnap before leaf edits. Both target types and loss pass whole and
controlled chunk execution. Two actual CPU probes at
`build/native63-line-redeclaration-cpu-root-1` show explicit gl_FragDepth output
redeclarations already fail unchanged original normalization, before consumer
generation; the source is identical before/proposal. This pre-existing broader
GLSL limitation remains visible and is not claimed supported by the patch.
`root-review-resolution1.json` joins the conditional source findings to all
actual evidence. `promote1.py` is prepared but NOT RUN: it requires successful
terminal62 build AND independent47 audit before copying the uninstrumented
three CPP files/test. No63 source is canonical, no63 formal build/wheel exists.

All private build/review/GPU/CPU sessions from this continuation are terminal;
only main session76107 remains live. All new private environment/cache/cwd roots
were removed after verified worker termination. Bounded once-only cleanup
removed53 private63/controlled-chunk/redeclaration object files,68,542,503 bytes,
preserving binaries, source, CMake metadata, captures, logs, reviews and failures.
Policy-denied paths remain untouched. Installed58 and AGPL/originalBSD notices
are unchanged. No activation/public push or cybersecurity work occurred.

NEXT: observe the same main session76107 through build47 and terminal audit.
Then promote only the reviewed uninstrumented63 source, prepare exact fresh63
ownership/freeze/build47 and a fresh PEP517 wheel. The prepared62 wheel recipe
may be superseded before launch to qualify the final63 artifact directly; no
final CPU/GPU/scientific/host/performance/platform requirement is dropped.
Run actual final-artifact finite/lifetime/recovery/numeric/generated-line/Qt and
broader scientific/image/volume admissions, unchanged five-pair performance,
remaining hosts/platforms/ABIs, scanout/allocator/driver peak evidence. All
original13 requirements remain in scope and full goal is active.

Continuation checkpoint134, 2026-10-22: Native61 completed the actual guarded
freeze, full runtime build and all47 CTests. Independent terminal and fresh
PEP517 wheel/native-origin audits pass at `build/native61-prep-root-1`.
The real wheel SHA is
1a46df0d715146edec281281d7ecbe5928bccc421e34de4bb2f99e274150b497.
Actual finite8/23 whole captures, queued lifetime8/5 whole captures and numeric12/
13,304 exact original-GL values passed with independent saved/root admissions.
Both formal and wheel binaries separately pass17 binding failure-only CPU
checks. Actual WSL GCC13.3 passes30 normalization controls and compiles the full
runtime translation unit; this is compile-only portability, not Linux native
link/wheel or hardware qualification. Recovery61 preserved a real failure:
six cases passed, but actual CREATE rejected Texture1D despite shader/layout
support. Its failed result remains unchanged and is not admitted.

The resulting private Native62 proposal at
`build/native62-texture1d-prep-root-1` implements real CREATE/SIZE/DATA rank,
history, partial upload origins/extents and maxTextureDimension1D grant exposure.
Review1 found a compatibility regression from stricter existing2D/3D/RenderBuffer
SIZE validation and requested actual queued1D hardware coverage. Revision2
preserves those legacy SIZE semantics, adds distinct nonzero y/z CPU origins,
and keeps stricter validation specific to the new1D path. Full private runtime
link and the texture suite pass, including unchanged14,603 full-upload cases.
The separately compiled revision2 runtime passed seven recovery cases/16 exact
whole captures and four extra cases/six exact whole captures: unbound1D white
placeholder recovery, queued partial/full revisions, and actual interpreter
SIZE compatibility/equal1D SIZE/invalid1D rejection with retained pixels.
Independent saved audits recompute every pixel. The placeholder is a native
convention, not a GL-oracle equivalence claim. Review2 is READY_TO_PROMOTE with
both actual execution gates required; root verified both and promoted the exact
four CPP files plus the permanent texture contract. Promotion receipt:
`build/native62-texture1d-prep-root-1/promotion-result2.json`, SHA
c6c73717fa97fbc5e36f51acf825666cef9557bbb1a4e0b20750efdfa9801095.
These private wheels replace only _dawn in the baseline wheel with recomputed
RECORD; they are explicitly experimental, not formal Native62 artifacts.

The canonical first QWidget lifecycle test now leaves recovery to the actual
paint instead of calling auto-recovering device_info() before paint. It requires
generation advance/loss_count+1, surface reconfiguration/presentation and every
channel of the4x4 recovered red image. Its exact unchanged AST test body ran
successfully in a fresh isolated private-wheel Qt consumer; independent saved
audit verifies the whole image and terminal/origin/shutdown/teardown joins.
Only this test body changed; other Qt tests are unchanged and not newly qualified.

Native62 source/CPU ownership metadata is prepared and root-approved at
`build/native62-prep-root-1`, manifest SHA
df5b7068d7d9b187ac1c038873fb2f05e1f2ddd2268d2dc61e65a09022ddc4c7.
It retains618 source/4141 harness/44 targets/47 CTests, transfers only the five
promoted native/test owners and updates the verified Qt harness input. Old
packets remain immutable. One preparatory pipeline script stopped at an
incorrect count assertion before any writes or child launch; the corrected
script2 preserves exact618/47 counts and advances only epoch62/snapshot48.
The actual once-only `freeze_build2.py` pipeline is LIVE, exec session76107.
Freeze launcher43448 owns actual Python47172, created2026-10-22 14:56:05 local;
both were authoritatively observed live. No terminal freeze/build success is
claimed. Observe this same handle/process tree, never restart on quiet output.
Complete unchanged source/dependency/physical-origin/SDK/compiler/protection
guards apply. Actual successful freeze automatically starts the full build47.
Do not edit canonical source/harness inputs while this pipeline is live.
`live-observation1.json` records the actual live freeze worker/process tree.
Fresh62 terminal/native-origin audit scripts and the PEP517 recipe/builder are
prepared from successful61 sources, retaining47 CTests and618/4141 inputs.
The recipe is explicitly NOT_LAUNCHABLE with unresolved frozen/source digests;
`finalize_wheel_plan2.py` requires the actual successful62 terminal audit before
binding them. No fresh62 wheel build or artifact qualification has started.

Cleanup this continuation removed24 completed Native61 wheel objects
(26,684,972 bytes) and44 completed private proposal objects (52,495,279 bytes),
with bounded once-only receipts; all sources/binaries/logs/raw captures/reviews
and failed evidence remain. All private GPU environments/cache/cwd roots were
removed after verified terminal workers; no unknown-worker hold exists. The
earlier formal Native61 object cleanup removed163,079,428 bytes. Previously
policy-denied cleanup paths remain untouched. Installed58 and original AGPL/BSD
licenses/copyright/notices remain byte-identical; packaging includes both.

NEXT: observe session76107 to actual terminal freeze/build47 and independent
audit, build a fresh Native62 PEP517 wheel/native-origin audit, then qualify that
actual artifact with strict finite/lifetime/recovery/numeric/extra1D/Qt checks.
Broader scientific/image/volume admissions, generated-line GPU checks, unchanged
five-pair performance gates, remaining platforms/hosts/ABIs, scanout and complete
allocator/driver peak evidence remain in scope. No new activation or public push;
no release/performance/full-goal completion claim, no cybersecurity work.

Continuation checkpoint133, 2026-10-22: Native61 source/CPU ownership metadata is
prepared and root-approved at `build/native61-prep-root-1`, exact manifestSHA
f9d665d3baa21a6b077fa56d4cfb1301844660c650358fa1f84d7ade5c9d7da1.
Source618/harness4141/targets44/CTests47 are retained. Only the promoted3 CPP
files and existing normalization test transfer to the new reviewed CPU packet;
the old packets and records remain immutable. Snapshot47/evidence61/build61
are fresh namespaces; installed58 and AGPL/originalBSD bytes still match.

The once-only `freeze_build1.py` pipeline is LIVE, exec session57735. Do not
restart because it is quiet. Freeze launcher35848 owns actual Python92016;
its current final dependency-verification launcher65700 owns actual worker18224,
created2026-10-22T13:14:34.726308-04:00. The last authoritative observation finds
18224 live with4,572,496,413 read bytes and100.328125CPU seconds; the parent
freeze has already written the source snapshot and captured evidence. No
frozen-admission or completed native build receipt exists yet. Observe the same
session/process tree; no terminal or native build success is inferred from
directory existence. The unchanged freeze/build tools keep every dependency,
origin, SDK, source, compiler, protection and47-contract guard. Freeze performs
its own complete read-only preflight before writes; no redundant separate
preflight was added. Full build automatically follows actual successful freeze.

Wheel builder2, recipe and independent terminal/native-origin audits are
prepared from the successful Native60 recipe with explicit61/snapshot47 paths.
The recipe contains unresolved frozen/source digests and cannot launch before
actual native47 audit resolves them. No Native61 wheel has been built or GPU
test launched. Finite worker179lines/wrapper70lines, lifetime worker/wrapper/
16fixture members, and corrected recovery worker4/wrapper3/7input members are
byte-identical reused sources, with fresh61 controllers and artifact gates.
Current lifetime/refusal/AST/projection and recovery256-originalGL/trace/refusal
CPU controls pass. Actual finite, lifetime and recovery source reviews completed0,
scratchremoved, with their READY_FOR_*_GPU_EXECUTION source-only verdicts.
Every actual new artifact/profile/native47/finite8/lifetime8 prerequisite remains
required before its dependent GPU launch. Source review did not qualify any
new artifact or relabel old results. Root separately reviewed the finite admit
and final-admit scripts explicitly excluded from that peer's supplied sources;
they preserve the successful old logic and require BOTH saved quality and owned
counter audits, so a supplementary PASS alone cannot admit anything.

New actual generated-line CPU evidence at
`build/native61-sampler1d-line-prep-root-1/result1.json` passes vertex-sampler1D
and fragment-sampler1D cases using real build_portable_shader,
build_line_evaluator and build_generated_line_consumer. Pinned Tint reader and
WGSL writer accept the generated compute/vertex/fragment modules, with actual
1D sampled types and live stage masks independently checked. All current CPP
members match the approved61 manifest before/after execution. This closes the
manual-compute-only CPU coverage gap; actual GPU dispatch/line pixels remain
pending. The seven owned private object files (9,266,751bytes) were removed once
after actual successful build/test termination; source/logs/executable/receipts
remain. Old policy-denied WSL caches were not touched.

NEXT: resume session57735, complete actual freeze/build47 and independent
terminal audit, finalize wheel plan then fresh build/native-origin audit.
Run current reviewed finite8, lifetime8 and unchanged seven-case recovery
sequentially on the actual new wheel, with saved/root admissions; actual1D must
execute. Unbound typed placeholder and generated-line GPU checks remain next,
along with numeric/scientific/image/volume, Qt recovery, performance and all
original requirements. The stale Qt test is in the frozen harness: do not edit
it while this pipeline is live. No activation/public push, no cybersecurity work;
full goal remains active. This turn adds actual generated-line CPU evidence and
source capture, and is currently a verified wait on the live dependency worker.

Continuation checkpoint132, 2026-10-22: Native60 recovery execution exposed and
preserved two different findings. Actual run1 completed1 with four cases passed;
the mixed-patch expected values used double division instead of the original GL
float32 transfer. Corrected expectations directly index the unchanged original
OpenGL256-value corpus (expectedSHA d5f525a13a07c1d604032ed460ac58ad9e012b8bec74236bd5f4f46142995b87),
verified against upstream arrays. No tolerance or candidate-derived oracle was
added. Actual run2 then completed1 with six cases passed and14 complete texture
captures: original device/program recovery, RGBA8 replacement2D, f64 full2D,
mixed partial2D and all3 float3D slices. It fails the final1D case at shader LINK:
sampler1D was not assigned a binding. Both failed runs, reviews and original
inputs remain intact; actual workers are terminal, shutdown counters zero and
owned environment/cache/cwd teardown passes. Neither run is a seven-case pass.

The real1D gap is now fixed in canonical source, pending Native61 artifact work.
Promotion `build/native61-sampler1d-prep-root-1/promotion-result1.json`, SHA
ac40e898fe0d0258bb79b648ec3d7ea16a87929408f6161875dbe7d3dac4502d,
changes normalize.cpp, glslang_spv.cpp, runtime.cpp and the existing permanent
normalization contract. It covers sampler1D declaration/helper/sample lowering,
Dim1D reflection, retained allocation dimension checks, ordinary/evaluator/
consumer e1D layouts, and dimension-specific1D/2D/3D white placeholders with
loss/shutdown reset and CPU-shadow accounting. Exact original source bytes are
retained before promotion. Native58 installed binaries and all AGPL/originalBSD
license/notices hashes remain unchanged; no activation or public push.

Actual CPU baseline fails the new missing-binding regression; candidate passes
50 checks. Actual pinned Tint ReadIR AND WGSL writer pass6 fragment cases,
2 vertex modes and explicitLOD compute. Initial peer review raised this missing
translator proof and the placeholder audit. Its successor found two remaining
evidence gaps, not source defects: exact candidate2 permanent test execution and
the runtime_texture.hpp integer-only2D policy guard. Root resolved both with
recorded actual evidence, retaining both original FIX verdicts unchanged.
The exact promoted test passes both ordinary and Tint-enabled builds over all
six original corpus pairs, and the complete exact candidate2 runtime.cpp TU
compiles. Final CPU resultSHA
9a064363366d6cc3fc57a387024fb8b05113e907f6cb0bca00779b93b4c59952;
root review resolutionSHA
343be309b1deae2a2a9d0cf24773fff63dbf225e3eecc871e1ae5dd4eab348e1.
The first compile-only harness failure mixed two physical header copies; its
failed log/result remain, and the corrected40-header private closure changes no
implementation bytes. The runtime_texture integer policy is reached only through
OpTypeInt-derived integer_sample_uses, not floating1D/r32f sampling. TextureData
defaults dimensions2/depth1 confirm unchanged2D placeholder defaults.

Cleaned31 owned private object files,48,955,238 bytes, after actual terminal
build/test results. Retained source/evidence/executables and the exact successful
runtime compile-only proof object. The first cleanup receipt's null aggregate
was corrected by a saved-record audit without retrying deletion. The two older
policy-denied WSL cache paths remain untouched. All current children terminal.

NEXT: fresh Native61 freeze/full runtime link and all47 contracts, new wheel and
actual seven-case recovery including1D; add unbound1D placeholder and generated
line sampler coverage. Current working source is newer than Native60 artifacts.
Numeric12 inputs28members/13304values and exact old worker are prepared under
native60-prep with passing CPU controls only; retarget explicitly to the next
artifact before any GPU launch. Do not relabel Native59/60 scientific evidence.
The stale Qt loss expectation still needs a repaint-driven recovery check.
Scientific/image/volume/numeric regressions, actual new performance, expose
ownership/five matched pairs, platform/host/ABI matrix, scanout, complete driver/
allocator peaks and original release requirements remain open. Goal active;
cybersecurity excluded; AGPL plus original BSD attachments preserved.

Continuation checkpoint131, 2026-10-22: The actual Native60 queued-lifetime
consumer completed0, with eight cases and five whole exact captures. Independent
saved audit and `build/native60-prep-root-1/lifetime-final-admission1.json` admit
that bounded result against the current wheel and fixed NumPy246 runtime.
The unchanged warm36 control reports zero completion waits, peak3 tickets and
36 retired; the96-generation control reports peak2 tickets,16384 live texture
bytes and48 live buffer bytes. Actual worker termination, package/native
origins, seven shutdown-zero counters and owned environment/cache/cwd teardown
pass. This does not prove device-loss recovery or performance.

Recovery packet1 was rejected before GPU execution: its DATA tracer attempted
list(integer) for buffer offsets. All rejected packet1 files remain retained.
Corrected worker3/controller2/wrapper2/audit2 preserve all seven recovery cases,
including actual1D sampling, and strict no-DATA/no-new-transfer checks after
device loss. CPU controls2 execute the exact trace function with actual NumPy
buffer and texture arrays and verify delegation, offsets, shapes and byte hashes;
the original seven AST definitions and optimized-worker refusal also pass.
Independent source review2 is running; no recovery GPU worker has launched.
The audit now independently binds expected transfer counts, pre-loss texture
DATA shapes and recovered hardware. Native60 scientific/image/volume/numeric,
Qt recovery, actual performance, the remaining platform/host/ABI matrix,
scanout, complete driver/allocator peaks and original release gates stay open.
AGPL-3.0-only and original unchanged VisPy BSD license/notices are retained in
source and package configuration. No activation or public push this checkpoint.
The two previously policy-denied WSL CPU cache paths remain untouched.

Continuation checkpoint130, 2026-10-22: Native60 full runtime compiled/linked and
all47 native CTests passed. The once-only freeze/build pipeline completed0;
session21644 is terminal, not a live handle to poll. Final dependency/SDK/compiler
policy and installed Native58 preservation checks pass. Independent terminal
audit `build/native60-prep-root-1/native-terminal-audit1.json`, SHA
8572586d2e637f6b50fe6869b4e6ea1d25d84657f0b0e068cdd046833caca01f,
verifies actual47 executed/no skipped, source618/harness4141, archived binaries,
unchanged policies, guard/source identities and license bytes.

Fresh isolated PEP517 wheel build completed0 (session25692 terminal) at
`build/native60-wheel-windows-cp312-root-1/wheels/vispy-0.17.0+vulkan.1-cp312-cp312-win_amd64.whl`,
SHA3147f56a4d714322e26e347d01b4ccbd95163f5a99d98da9ea1c9cf3af5fdba1.
523 package-source bytes and strict package/native inventory match; AGPL and
originalBSD/LICENSE/LICENSING copies and notices pass. Native4 equal their own
fresh CMake outputs, no strip exception/project-output reuse. New wheel native:
_dawn3c1e501169c06b95e0ead606165f8d295bd3590948888ec910289cd53172b2fc;
_sdf_cpu da927be322ec5ae1d6a746f7bb460d8549f8b5f0bd50d25d27e7c95e022a5a29;
layer421d4f9e40383affaa20743528b18db6aa92e9ec985e05c4272ee4a93f3014ae;
JSON7323cea73a46efcba615ca452d2b0235e3741109628c4bf2979c105e6ae69d56.
`wheel-native-audit1.json` SHA8c25888bf1feea0778ee439fe216cd54631e83022e6a0239e276f9340e117802.
Actual binding failure-only integration checks pass17 on the admitted native
binary and separately on the wheel-identical binary: invalid stats consume all
decoded capsules, malformed metadata/operation/duplicates discard whole batches,
bytes precedence preserves ignored capsules, empty payload and exporter errors
behave correctly. No device/canvas/draw/read/probe/info entry point is called.

Actual new finite GPU run `build/native60-gpu-run-root-1` completed0/session82594
terminal: eight unchanged cases/23 whole captures exact on real Vulkan RTX4090
NVIDIA610.88 with isolated Python3128/NumPy246. New source/lifecycle peer review
returned READY_FOR_FINITE_GPU_EXECUTION, completed0/toolsoff/scratchremoved;
conditional artifact/native47/profile gates were then actually satisfied.
Original worker179lines and wrapper70lines remain byte-identical, with actual
Native60 wheel/native SHA inputs; no old result was relabeled. Existing saved
probe windows/totals prove9 full transfers/11428logical bytes, including initial
2D, f64, replacements, warm dummy3D and source3D. No extra probe calls that could
poll/retire tickets. Original saved pixel/upload/copy/counter audits and separate
owned-counter audit both pass. Final root admission
`build/native60-prep-root-1/gpu-final-admission1.json`, SHA
38c08aa2a321700f6b69967a7392a7d28f9fcce7320109d79d12014107489cbb,
also rechecks actual profile/runtime hashes and saved driver610.88. Nine-profile
SHAf2e578773ed6233b177c38f4717210de3df587b7383086e59cf227df21dd5c65 and exact
runtimeSHA3e7fb65bc3424c1f898bdb9ecfab81ca327e103dabd56bdf30f3cb5ec2242d7a
match source admission/request/result. All native origins, actual creation-bound
terminal joins, environment/cache/cwd teardown and seven shutdown zero counters
pass. No active process or unresolved worker hold remains at this checkpoint.

After terminal audits, cleanup removed107 native +24 wheel generated objects /
189684480bytes total, retaining binaries/libraries/CMake caches/source/rawproofs.
Fresh wheel UV cache and finite-GPU own environment/cache/cwd removed. The two
policy-rejected WSL CPU site-packages/uv-cache directories remain retained and
must not be retried; no new cleanup rejection this turn. Original BSD and AGPL
remain unchanged; installed Native58 four still match; no public push/activation.

Next concrete sources are prepared at `lifetime-source-preparation1.json`: exact
unchanged queued-lifetime worker/wrapper/helper and16 fixture/reference members,
plus Native60 controller/audit path/count/admission bindings. Current CPU controls
pass five AST-exact lifecycle functions, byte serialization and actual optimized
worker refusal before renderer import (all8missing GPU cases preserved). This is
source/CPU evidence only; lifetime source review, admission and fresh GPU run
remain next. Queued-lifetime is not device-loss recovery. Numeric/scientific/image/
volume/recovery, Native60 actual performance, unchanged predeclared5pair/gap rules,
remaining platforms/hosts/ABIs, scanout/complete allocator/driver peaks and every
original release requirement not otherwise proved remain open. Native60 has no
measured performance result; do not attach old Native59 ratio or scientific
admissions to it. Full goal stays active; this turn made native/wheel/GPU progress,
not a narrower completion claim. Cybersecurity remains excluded.

Continuation checkpoint129, 2026-10-22: Native60 freeze completed0, with
`build/native60-prep-root-1/frozen-admission1.json` binding frozen-input SHA
9201c4f1508eb2409f04c757e6ee4e61d9ff84902f30b4f62c753d6a95ad0a1b,
source tree d0f7efbb80c1f24f8971cd4d5c1f1ea4b23acb93a02d6777e9fa1f4e9ef54e58,
and harness tree 4b07974813c482fad24f3f992c848f340bd61560a2f29cfbe408e6031486323c.
The same once-only pipeline advanced to build1, launch pid74828, exec
session21644. That live handle remains authoritative; do not relaunch on timeout.
Full runtime compile, actual47 native CTests and terminal binary audit remain
pending. Installed Native58 remains protected; no native activation/public push.

Independent work used the user's authorized Ubuntu WSL environment. Actual GCC13.3
/ Python3.12.3 with SHA-pinned NumPy2.4.6 compiled the unchanged permanent contracts
and passed all three CTests: 454 texture cases, 70 decoder checks and 148 packing
checks, including all eight actual allocation-failure positions and complete
batch discard on Linux. `build/native60-linux-cpu-root-1/audit1.json` verifies raw
JUnit/logs, exact source/dependency closure, ELF binaries and actual nonce/start
stamp/terminal records. Base Linux had no numpy/pip/nanobind; no global packages
were installed. Windows UV installed the official SHA-pinned manylinux NumPy wheel
into an exclusive target, and a pip-free temporary Linux venv referenced it.
Nanobind sources and SDK headers were directly SHA-bound to the accepted closure.
This is CPU-only header/binding evidence, not full Linux runtime/wheel or hardware
Vulkan admission. The full Python/version/ABI/platform matrix remains pending.

Prepared `native_terminal_audit1.py`, wheel recipe and finalizer while waiting.
Selected wheel builder is `wheel_build2.py`, finalizer `finalize_wheel_plan2.py`.
Draft1 had a stale Native59 status path caught by source inspection before any
launch; draft/source correction records are preserved. Finalization refuses to
run without actual Native60 terminal47 audit and joins completed frozen/source
digests. Fresh wheel project compilation, strict package/native inventory and
AGPL/originalBSD checks remain required; old Native59 is recipe provenance only.
The existing finite GPU worker uses the actual parser and records all integer
probe deltas, so its saved new owned counters can prove the path without adding
extra probe calls that could poll/retire work and change lifetime behavior.

Cleanup issue preserved accurately: Linux temp cleanup attempted once and got
ENOENT; read-only observation confirms the exact directory absent, with no second
delete. Automatic approval review rejected a separate PowerShell command deleting
the exclusive Windows-hosted WSL `site-packages` and `uv-cache` directories before
execution, reporting only "blocked by policy". They remain retained; the command
did not run and neither target may be retried through another method. Record:
`build/native60-linux-cpu-root-1/runtime-cleanup-rejection1.json`. No requested
permission or tool escalation. All source/logs/raw proofs/binaries preserved.

This turn made progress (actual completed freeze plus actual Linux contracts)
and verified the existing Windows build pipeline still live. The full goal is
active. Fresh native47/binary/wheel/GPU/scientific/lifetime/recovery, unchanged
performance qualification, remaining Windows attribution/platforms/hosts/ABIs,
scanout/allocator and original release requirements remain open. No new speedup,
GPU or release claim. Original BSD stays byte-identical alongside AGPL; no
cybersecurity work.

Continuation checkpoint128, 2026-10-22: reviewed owned-upload integration4 is
promoted to canonical runtime/binding/parser source, with four new headers and
permanent regression contracts. Before/candidate copies, exact source hashes and
license preservation are retained in
`build/native60-source-integration-root-1/promotion-result1.json`. Main CMake adds
one texture executable, one test-only nanobind module and three CTests. Actual
permanent tests compile and pass all three CTests: 454 texture cases, 70 decoder
checks and 148 packing checks. The real main-CMake fragment was exercised with
CPU header exposure; complete SDK linkage awaits the epoch. The test module has
no install rule. Permanent packing adds scalar/nested equivalence; the private
frozen telemetry-wrapper proof stays separate and preserved.

Actual parser + installed Native58 import/default packing/source snapshot check
passes, with both owned entry points absent and the real fallback condition
selecting legacy execution. No renderer was executed in that check; actual
installed-wheel and GPU fallback validation remain pending. Existing typed API
and native-epoch guard regressions pass 126 tests, zero failures. Exact owned
pytest temporary tree and 14 generated objects / 3,366,459 bytes were removed
after actual terminal waits; logs, binaries and evidence retained. No cleanup
denial or retry. AGPL plus byte-identical original BSD and third-party notices
remain attached and package license configuration stays unchanged.

Fresh Native60 candidate has 618 source members, 4,141 harness members, 44 targets
and 47 CTests. Seven native files plus two C++ tests belong to a new CPU packet;
three prior owned entries (runtime.cpp/runtime.hpp/module.cpp) transfer without
altering archived packet payloads. Retained input names and aliases were gated
before payload verification, including the physical dependency source closure;
this is a name scan, not rerunning old identity suites. Actual unchanged guard
read-only preflight completed successfully. Independent metadata review completed
0, tools disabled, scratch removed, verdict READY_FOR_NATIVE60_FREEZE_AND_BUILD.
SDK, preparation, dependency origins, native entrypoint tools and protected
Native58 four remain unchanged. One inaccurate test comment claiming no Dawn
linking is recorded as non-blocking; actual SDK linkage/import is a CTest gate.

`build/native60-prep-root-1/approval1.json` root-approves exact manifest SHA
2b51dc5664f549bc847e9ec017983e75a8adac8fb53c3f6206f25cf350def0df. The separate
approval supersedes historical candidate-preparation status without rewriting
reviewed bytes. `approve_freeze_build1.py` launched once; freeze1 launch pid83516,
exec session21644 is live at this checkpoint. Poll that existing handle; do not
restart on an observation timeout. It freezes source46/evidence60 and then calls
the unchanged initial build, which performs its own complete read-only build
preflight. No redundant separate build-preflight launch is scheduled.

Full runtime.cpp compile and 47 epoch CTests are not yet complete. Fresh binary
audit/wheel, matching NumPy246 external/scientific/lifetime/recovery/GPU checks,
unchanged predeclared performance qualification, Windows event attribution,
remaining platforms/hosts/ABIs, scanout/allocator evidence and every other original
release requirement remain open. No speedup/native/GPU/release claim from launch.
Installed Native58 unchanged; no public push this turn. Previous turn was actual
implementation/verification progress; this turn promotes that implementation,
adds permanent tests and starts the concrete native pipeline. Full goal remains
active and cybersecurity work stays excluded.

Continuation checkpoint127, 2026-10-22: actual private owned-upload integration
is root-accepted for Native60 preparation at
`build/native60-owned-upload-prototype-root-1/integration4/root-admission1.json`.
The proposed binding compiles; its exact nanobind decoder/capture implementation
passes 70 CPU checks, including a 64 MiB allocation transfer and eight injected
C++ bad_alloc positions discarding all 24 snapshots. Candidate Python packing
passes 148 checks across 44 layouts, ten unsupported dtypes, three exporter
fallbacks, reentrant mutation and the unchanged frozen telemetry wrapper. Final
texture helper passes 454 checked-iterator cases (220 transfers, 221 copy
fallbacks, 13 exact errors), existing texture assertions, unchanged 14,603
FullUpload preparation-equivalence cases and twelve original GL byte cases.
Final actual integration checks use Python 3.12.8 / NumPy 2.5.3, not the release
NumPy 2.4.6 profile. Earlier 2.4.6 primitive evidence is not relabeled.

The consuming runtime route retains the const API and all legacy 1D history,
partial/mixed conversion and depth/stencil behavior. Entire replacement with a
different previous dtype can still transfer, exactly matching canonical full
DATA assignment. Default bytes packing remains unchanged; the parser falls back
when installed Native58 lacks either private entry point. New capture/fallback
and transfer counters disclose scope. Root found a missed allocation-failure
case despite the first READY review: snapshots not yet collected remained usable.
Revision4 retains the original command root before allocation and discards it
without allocations; actual injected failures prove the fix. Owned commands
explicitly require acyclic list/tuple trees; legacy custom sequences remain
accepted. Final peer review is READY_FOR_PRIVATE_NATIVE_EPOCH, completed0, tools
disabled and scratch removed; root separately verified source hashes and gates.

Failures retained: initial test harness used C++17 rather than required C++20;
one telemetry fixture omitted `_add`, corrected using the actual frozen method.
Neither failure was repaired by changing implementation behavior. Two exact
cleanup receipts removed 58 generated objects / 19,322,056 bytes from terminal
private builds, retaining all source, binaries, libraries, logs and failed
evidence. No new cleanup denial or live process remains. Production runtime,
binding, parser and installed Native58 are unchanged. Original BSD license copies
remain byte-identical and included alongside AGPL; cybersecurity excluded.

Next: promote reviewed source plus permanent regression contracts/CMake wiring;
freeze and compile a fresh complete native epoch, then wheel and matching CPU,
external-consumer, NumPy246, scientific, lifetime, recovery and GPU validations.
Full runtime.cpp has not compiled for this integration. No GPU/performance/release
admission follows from these CPU checks. Native59's 2.18385 engineering median
ratio remains current; unchanged predeclared five-pair qualification, event
attribution, remaining hosts/ABIs/platforms, scanout/allocator evidence and all
original release requirements remain pending. Goal stays active; this turn made
implementation and verification progress and does not narrow the objective.

Continuation checkpoint126, 2026-10-22: Private CPU prototypes for the next copy-removal step are built and reviewed at build/native60-owned-upload-prototype-root-1; no canonicalnative/Pythonparser or installedmodule changed thisturn. inputs1.json c81eda0aab102defda8069d772d74c60514655f8acfa9f895ef8ad2055d3f2b0 copies46 approvedheaders with SDKmanifest1891ddd7/Reader exclusionguards and captures currentCpp/binding/parser/licenses/native58 preservation baseline. InitialCMake launchfailed beforechildcreation because cmakewasnotonPATH;emptylog/refusal preserved. SubsequentprivateCMake uses absolute .venv CMake4.4.4/MSVC14.44,CPU-only/noDawnlink/deviceinit/noactivation. Native59runtime21c94150/header e1988fe7/binding e6895246/parser37503cd2 and wheel4b88388c remain baseline.

First owned helper copied exact canonical validation and moved only whole ByteBlob vector into TextureData. Actual444cases/218addresspreservedfullmoves/216partialfallbacks/10identicalerrors/64MiB passed;existingtextureassertions+14603FullUploadoracle+12originalGLcontrols/13304values pass through explicit testcopy-to-ownedbridge. ActualCPython3.12.8 buffercapture helper uses GIL-held PyObject_GetBuffer/PyBUF_CONTIG_RO withRAIIrelease and one nativeownedcopy;59arraycases includeC/F/transposed/negative-stride/read-only/empty/endian/specialfloatbits/64MiB,postcallmutation/deletion,exportrelease,noncontiguous/nonbufferrejection. Initial delayed-memoryview route isNOTselected forintegration because it changes snapshot timing. Selectednativecapsule captures DURINGpacking;52dtype/layoutcases+64MiB and reentrantlaterEnum.__int__ mutatingearlierarray prove packing-timeimmutability and address-preservingconsume;consumedcapsulereuse rejected. Allcontrols also pass in freshhash-pinned NumPy246/Python3128 CPUenv (initialdesktopCPU NumPy253 explicit);both freshCPUenv/cacheowners removed after actualcreation-bound workers terminal.

Independent review1 FIX and review2 FIX preserved. Corrections nowselected: owned_texture_data2.hpp SHA89dd7b413355f78289b62defb6cb0ea293ff96df3fe10385cf14a552656ded6a requires explicitallow_transfer and returnsactualtransferbool. Legacyordinary1Dfulluploads mustretainDATAbytes forupdates whenruntimefullpredicate disagrees withhelperentire;fourruntime-shapedcases/two1Dhistorycases provefallback. Checkedcontract3 guards dimensions/rank/offsetrank BEFOREindexing;MSVC Debug/MTd/_ITERATOR_DEBUG_LEVEL2 staticassert provescheckediterators. Final454cases=220moves+221copyfallbacks+13errors,including malformedshape[W],emptyshape,dimensions0 andthreelegacy1Dwidth==channels2/3/4 mismatchcases preserving shadow/history. Existingassertions/14603oracle/12GLcontrols rerun through helper2 gatedbridge that conservativelycopiesall1D uploads;allpass. No old1D behavior silentlyfixed.

Secondcorrection freeze_owned_compatible2.py SHAead65732f24545638a2ff94bb0350f16205283489786d3e76b009ca274690bfd:only decoder-mappednumericwidths/bool optinto ownedcapture;M8/m8/structured/V/U/S/O/complex/i8/u8 retainexactlegacybytesdict;BufferError/TypeError/ValueError exporterfailures alsofallback. Tenactualdtypecases/threeinjectedexportfailures/twelvefastdtypes/reentrantmutation allpassonNumPy253andfresh246. Existingdefaultpack_commands byteprotocol untouched. RawCAPIinspectioncopies are disclosed andnotcounted asbindingcapture;actualnanobinddecoder/runtimeowned-commandroute stillNOTimplemented.

Review3 READY_FOR_OWNED_UPLOAD_INTEGRATION completed0/session31299/toolsdisabled/ownedpeerscratchremoved. CPUaudit2 PASS_SAVED_CORRECTED_OWNED_UPLOAD_CPU_PROTOTYPES rechecksallnewlogs/childwaits/targetenvironmentabsence,copiedvalidationprefix,currentcanonical/license/native58hashes and allfallbackresults;noGPU/releaseclaim. integration-packet1.json ROOT_ACCEPTED_CPU_PRIMITIVES_FOR_PRIVATE_INTEGRATION binds sevenselectedsources,review3/audit2andexplicitintegrationconditions. DirectsourceSHAs beforefutureintegrationbuild required (privatecheckedbuildinputmanifestreusedbaselinev1 butreview3 binds actualselectedcode). Earlierunsafeharness2,late-decodedmemoryview and rawCAPIinspectionmodule1 are unselected. Cleanupobjects1/2 removedexactnine terminal-build .obj files,5698091bytes,whileallnativeprototypepyd/exe hashes,source/data/logs/CMakeevidence unchanged;no olddenial retried. AllCPU/peerchildren terminal,no workspacehold/no livehandle. AGPL/originalBSD/noticespreserved;cybersecurityexcluded.

NEXT: integrate only in a new explicitownedconsumablecommand path;const execute_commands anddefaultlegacybytes mustneversteal/change. Capture synchronouslyatpacking underGIL,moveownedcapsulepayloadtodecoderthentextureshadowonlywhenallowed,retainpartial/mixed/depth/1Dfallback/history. Nativeerrors translatedby nanobind;capsulesone-shot,failedownedbatchdiscarded;fallbacks/capture/logicaldecodebyte countersandtimer scopesexplicit. Opt-in remains insideexistingtimedpack_commands wrapper,never in logging/pickling/debug consumers. Then freezefullcandidate/newnativeepoch/wheel andverifyconst/owned/default/duplicate/failedbatch/mutation/lifetime/CPU/GPU/scientificgates beforeanynewtiming. Currentactualengineeringratio2.18 remainsunimproved/unqualified;fivepairperformance/Exposecause/driverpeaks/scanout/remaininghostABIplatformworkloads/alloriginalrequirements open. Userresetgoalto“conintue”;continuefullimplementation scope,not aCPU-onlysubstitute. Previousgoalturnprogress(engineeringgapmeasured);currentturnimplementsandvalidatesprivateprimitives/fixesreviews/cleansownedassets. Goalactive;newworkunpublished.

Continuation checkpoint125, 2026-10-22: Controlled actual Windows redraw now reproduces the old spontaneousQWindowExpose→CanvasBackendDesktopPaint chain. Final controlled_worker3.py/controlled_run3.py completed0/session31551 on fresh Native59wheel4b88388c/Python3128/NumPy246. Three predeclared controls each perform1sceneDRAW/2presents/2submits: normal request getsreceipt0;unreservedRedrawWindow gets1unattributedpaint+draw/no measuredreceipt;reservedRedrawWindow getsreceipt1. Bothreceipts successful/closed/retired/submissioncountercaptured;stable120x160wholeRGBA before/after,8shutdownzeros. Controlled-audit1.json AUDITED_THREE_CONTROLLED_WINDOWS_PAINT_DIAGNOSTICS SHA c7188ca682b7e6c9deafbf4c9120dcd501847bc53c0851352bd01e5a65c88036 independently verifies rawcounters/eventorder/stamps/nativepackage/cleanup. TraceSHAee00828ed41791720d0a3268ea8a7aa1e3d4d05522ab6afc8785bb74e0c9ef15,parentSHA9484da931d27368e45091b478300827aa2bfd14a751e602f0176698092adb28a. Appnativeeventfilter doesNOTobserve the synchronously sentWM_PAINT despite actualsuccessfulRedrawWindow andQtExpose/Paint before APIreturn. Thus oldabsenceofnativefilterMSG is not proof of no nativeinvalidation. No events consumed/suppressed/reassigned.

Failed controlled attempts1/2 preserved:1Windowsdecoration minimum widened96request to120pixels(actual64x120frame);newfixture160x120 retains exactextent/quality checks.2actualunreservedchainworked but diagnosticwronglyrequiredWM_PAINTappfiltercallback;3records missingnativevisibility honestly and requires actualAPI/Qtchain. Canonicalrenderer/frozenbenchmark/requiredworkloadsize/quality/thresholds unchanged. All3attempt children terminal andowned env/cache/cwdremoved. Forensic1.json AUDITED_EXISTING_EXPOSE_FORENSICS rechecks old3325rowtrace/adjacent779/780samples with Reader guards: no recordedResize/Move/PlatformSurface cause,devicegeneration1→1,allocatorfailures0→0;missingWinId/DPI/configurecalls/sender observationsexplicit. Frozen upstream/candidate both havecommon unattributedwork gapchecks. Classification remains consistentwithwindowinvalidation,sender/surface-changecausalityunproven. Independent Claude peer-plan completed0/session33194/toolsdisabled/scratchremoved;advice only. Root adopts boundedforensics/engineering timing,not broad systemsettings changes,hooks/notifications or releaseclaim.

New public-source tool tools/volume_benchmark_adapter3.py adds only explicitSHA-pinned scientificv6 loading and separate sourceprovenance around unchangedadapter2/frozen sampler. Initialengineeringattempt1 failed before renderer startup because argparse abbreviated --admission to --admission-set-sha256;oldsource078cf921 preserved as volume_benchmark_adapter3.before-cli-fix1.py. Fixedallow_abbrev=False and emits actualinterpreterprocessstamp sidecar beforeimports/argparse. Six portable contracttests tests/contract/test_volume_benchmark_adapter3.py pass;actual earlyCLIerrorcontrol2 verifies bootstrap creation-bound terminalproof(error87absent) without renderer/GPU. Currentadapter3SHA7849bc543c585b7958732264b92deeef20d69012dc55df8efdbf712c8e421ae3. Initialmissingstamp correctlypreservedenv/hold;rootexplicitresolution records no creationstamp wasavailable,authoritativecompleteOSprocessinventory foundnoexclusive launcher/parent/nonce/script/interpreter process,argparseerror/preworkernorendereroutput,and sourceprojection preserved. engineering-bootstrap-resolution1.json archivesholdandmarker andcleans exactownedtemps;it doesNOTfabricate acreationstamp. Futurecontroller2 consumesrealbootstrapreceipt on earlyfailure. No oldcleanupdenial retried.

Exactlyone corrected engineeringpair engineering_pair2.py completed0/session72200,build/native59-engineering-full-update-pair-root-2/result.json ONE_ENGINEERING_PAIR_RETAINED_NOT_QUALIFIED SHA49e9ae5a98a53b3beb8f66c81b9fdfd42eda1d8875be6334dacec29e76cbb48e. Predeclared upstream then candidate,100warm/1000measured/queue3;noeventobserver loaded,no role replaced. Both0/measured andallsource/runtime/wheel/actualpackage joins pass. Upstreammedian74.4125ms,p95142.731345ms;candidate median162.50565ms,p95955.83861ms,max3700.5283ms;ratio2.1838488. It remains above1.10 and NOT releasequalification or proof of historical speedup(oldreferencebaseline differs). Saved audit engineering-pair2-audit.json SHA06fed9deffccc84c8be6f431951552f245e4cf9159ec5b014bff5cba1953cc54 reuses original pairs2.verify_run/raw1100receipts/GPUtimings/1000CPUframes/recomputedlatency/counter/conservation/attribution/workgates,and original paired3quality/2changedpixelchecks. Bothbootstrapstamps match normalstart/finish;allworkers terminal,freshenv/cache/cwdremoved,nohold,installedNative58native4unchanged.

Engineering-breakdown1.json binds rawsource/counters/samples: candidate Pythonpackmedian25.46395ms,decodecountermean45.87104ms,textureconversionmean29.76164ms,uploadCPUmean60.41534ms,1000exact67108864bytefulluploads. Timers overlap/differentstatistics andmustnotbesummed. Sourceproves prior unoptimizedcopies: array.tobytes→bindingByteBlobcopy→apply_texture_data entirecopy. Native59FullUpload borrows the later shadow only. NEXT: privateCPUprototype explicitownedfullblobtransfer + synchronousonecopybuffercapture;retainconstAPI/partialmixedemptyconversion behavior andprovebytes/descriptors/errors/source-mutationisolation before a newnativeepoch. No further stochastic benchmark retry planned;fivepairqualification/Exposecause/driverpeaks/scanout/remainingworkloadhostABIplatform/alloriginalrequirements open. Optimizationplan updatedwithactualdata. AGPL/originalBSD/notices preserved,cybersecurityexcluded. Previousgoalturnprogress(nativeQtobserver);currentturnrealreproduction/interfacefix/engineeringmeasurement/audit. Goalactive,publiccheckoutstillunmodified/unpublishednewwork,no liveprocess remains.

Continuation checkpoint124, 2026-10-22: Added and actually exercised a diagnostic-only Windows/Qt event observer to investigate the prior spontaneousExpose/unownedpaint. New build/native59-expose-diagnostic-prep-root-1/windows_paint_trace2.py observes selected native MSG(windowpaint/position/size/activation/display/DPI/composition) plus QWidget/QWindow events,always returnsFalse,never schedules/replaces/suppresses paints,records bounded raw ordering and callback errors/droppedrows. Actual PyQt6/Windows smoke windows_trace_smoke2.py passes39events,noerrors,nodrops,nopostremovalcallbacks,no renderer/GPU import. Initial failures retained in smoke1-observed:unshown QWidget had no effectiveWinId(fixed usingwinId fallback),and this PyQt QExposeEvent lacks region()(trace2 records unavailablebinding explicitly rather than omittingevent). Official Qt native-event contract recorded in helper source. No canonical renderer/benchmark source modified.

Actual one-shot Native59 diagnostic run1.py completed0/session41740:build/native59-windows-paint-diagnostic-run-root-1/result.json DIAGNOSTIC_CAPTURED_NOT_PERFORMANCE_QUALIFIED,2224trace rows,exactwheel4b88388c/freshPython3128/NumPy246/profile9,100warm+1000measuredfullupdates/queue3/volume256viewport1024MIP. Private paint_worker2.py accepts only root-admittedscientificv6output4,verifies exactrecord/schema/evidence and retains original adapter2/frozenbenchmark/telemetry/geometry/quality/threshold rules. It adds native/Qt observations and explicit diagnosticinstrumentationgap;timings never qualifyperformance. Worker finished0/reportedmeasured,and all1000paints wereowned. Intermittent spontaneousExpose DID NOT recur;there were0unownedpaints and0nativeMSGmessages during sampledwindow. This is not a fix or proof of the prior event'sexternalcause,and must not justify cherry-picking or rerunning untilpass. Priorfailedcollection/exposeaudit remains preserved.

New audit1.py completed0:audit1.json AUDITED_NATIVE59_WINDOWS_PAINT_DIAGNOSTIC,parentSHA3251b4786e882582f9b27899a0210ffdaaf8273a6906c7af337a2b8c8db71dfc,traceSHA0511dce8381aeedd2c3309b71a495d659b8c5572df85295ed26e085437087d35,requestSHA0db9adb76c392d1ba27a0d2fac55ce918bdcbb87981c223c69d436099c71c5dc. Audit verifiestraceordering/bothcounterboundaries,1000owned/0unowned,no callbackerrors/drops/eventconsumption,actualworkerstartfinishnonce/terminal/report/log hashes,freshinstalledpackage equalsNative59small17,source/wheel/profilepreservation,environment/cache/cwdteardown andunchangedinstalledNative58native4. All children terminal,allownedtemporaryenvironments/cache/cwdremoved,no workspacehold/no newcleanupdenials. AGPL/originalBSD/noticesunchanged;cybersecurityexcluded.

Next: use a predeclared controlled expose/paint diagnostic to distinguish genuine platform redraw behavior from benchmark reservation timing;seek a concrete ownership/environment fix without suppressing/reclassifying/dropping realwork or weakeningfrozengates. Single nonreproduction is insufficient to close gap. Then freshpredeclared5fullupdatepairs onNative59,actualmeasuredartifact/data/host/hardwarejoins andunchanged1.10mediancriterion. Full driverallocatorpeaks/scanout/remainingworkloadhostABIplatformmatrix/alloriginalrequirements remainopen. Previousgoalturnwasprogress(scientificv6admissions);thisturn adds actualWindowsobservationcapability and one complete diagnostic/audit,not aperformancequalification. Fullgoalactive;optimization/admissions remainunpublished pendingbroaderqualification.

Continuation checkpoint123, 2026-10-22: Fresh Native59 scientific admissions now root-admitted for scientific scope only. Final producer scientific_v6_producer4.py completed0/session53088 and generated build/native59-scientific-v6-root-4:24 perworkload records,quality-plan.json,qualification.json SHA97350906b4aec61d9cc3607e22dacf5264a6813a4dd698b5e08e47b3a4365c21. All24 frozen benchmark validate_admission calls passed with original data-only schema stubs (explicitly not actual timing-run identity). All5 saved cohorts small17/large24/image13/color24/large-image4 raw audits reexecuted without final receipt writes and reconstructed results equal original saved results. Original small semantic comparisons and exact images rerun; original large comparison/gate ASTs preserve actual workload parameters,camera,data SHA,wholeRGBAmax2/noexclusions,FBO ownership,raw counters,residency,allocation conservation,repeat equality and2 changed-pixel checks perworkload. All24 measured maximumchannelerror1 under unchanged2. Exact candidate wheel4b88388c/installedpackage equals small17; original upstreamwheelc486/reference bytes unchanged. No GPU used by admission generation.

Review1 FIX and review2 FIX are preserved along with private outputs1/2/3,all explicitly NOT root admitted. Final review3 READY_FOR_SCIENTIFIC_V6_ADMISSION completed0/session38450,toolsdisabled/owned scratchremoved. Producer4 closes actual loaded-module/source joins: audit sys.path/sys.modules restored,unique canonical benchmark55f76b loaded explicitly and equal packet copy,sibling hashes checked,original small/large module paths/digests checked,common module stems across all5packet trees require identical hashes,module origins rescanned before rename,original suite bytes readonce and member/render-source SHA joined,gates.sources equals actualcandidate source map. Projection records unchanged gate ASTs,direct/transitive calls,explicit namespace overrides and free-global allowlist. Eachlarge worker dependencies/device/nonsoftware4090driver61088 checked;all5 launch argv interpreter3128/flags/case/output/nonce/wheel/input joined to saved stamps and reviewed wrapper/executor source hashes and expectedREADY runtime reviews. External script copies were deliberately deleted by original controller teardown; current producer joins saved prelaunchhash/startfinish/argv records rather than pretending to reopen them.

Final scientific_v6_saved_audit3.py completed0/session6058:scientific-v6-saved-audit3.json PASS_SAVED_NATIVE59_V6_24_SCIENTIFIC_ADMISSIONS,24records/1473unique evidence files byteverified,10negativecontrols pass(status,workload/data,checks,evidence checksum,actualwheel/package/data/Python/NumPy). Syntheticcontrolbaseline passes;owned tempremoved,no renderer imported/noGPU. Root decision scientific-v6-root-admission2.json ROOT_ADMITTED_NATIVE59_V6_PRIVATE_SCIENTIFIC_ONLY completed0;verifies actual final output/no pending,review3codehashes/READY/terminal/scratchcleanup,audit3/quality hashes,all24record hashes/epoch and actual large executor source in every closure. Full small17 and largeoriginal/case raw evidence is pervolume-bound; supplementary image/color/largeimage reaudits enter pervolume records through audit/run/setup/teardown/log summaries,not all supplementary rawframes. Allsource/input/benchmark/legacyNative58pins preserved;licenses AGPL plus originalBSD/notices unchanged. No new cleanupdenials;all peer/synthetic scratch removed,no live processes/no workspacehold. Public checkout remains cleanbe393c3f8;canonicalnative optimization and private admissions not yet published.

Next concrete engineering gap: unsolicited spontaneousQWindowExpose causing unowned CanvasBackendDesktop paint during full-update timing; solve ownership without suppressing/reclassifying/dropping work or changing frozen telemetry/quality/threshold rules. Then collect fresh predeclared5full-update pairs on Native59 and evaluate unchanged1.10median limit. Newscientific admissions alone do not establish actual measured-run artifact/data/host/hardware equivalence; timing adapter must bind those explicitly. Complete opaque driver/allocator peaks,scanout,remaining workloads/hosts/ABIs/platforms/all original requirements remain open. Previous goal turn was progress(actual large-image4);this turn completed new artifact scientific producer/admissions,review fixes and independent evidence/rejection audit. Full goal active;cybersecurity excluded.

Continuation checkpoint122, 2026-10-22: Actual Native59 large-image4 completed0/session69802. build/native59-large-image-controls-run-root-1/result.json PASS_NATIVE59_LARGE_IMAGE4_CONTROLS: four original scalar/RGBA nearest/linear4096square cases,16 complete frames and268435456pixels exact,maxerror0,0exclusions. Baseline/repeat/pan/return all pass original analytic patterns,source-target texture separation,owned framebuffer draws and full originalRGBA equality;12 resident stages pass noDATA and original zero-work counters. Canonical large_image_wheel_suite.py retains Native58 selector105698c7. New large_image_worker1.py e436c487e8b37d0b985934f2efadb113e7f26d7e5f60cfed1206008a8b587e76 explicitly selects Native59wheel4b88388c, preserves AST-exact original sources/assert_successful_parent/load_reference/assert_stage/worker bodies and separates original13-source provenance from actual new executor/config fingerprint.

Original67-member data packet4d8b2fd1 unchanged; execution-manifest1.json d58c82d2a33aedd3af42017d2fae1b6c658fc055948d45b8f38e1fd17de9cd3b has69 members,adding only data manifest and projection. CPU preparation passes all source/reference bytes and actual -O refusals before renderer import for executor/controller. Independent read-only review READY_FOR_LARGE_IMAGE4_GPU_EXECUTION completed0/session7642,toolsdisabled/owned scratchremoved before root admission/actual run. New controller binds exact review,code,executor,input/runtime9/wheel and small17 installedpackage fingerprint; final cleanup/preservation failure exits1. No old target guard or prior admission relabeled.

large-image-controls-saved-audit1.json PASS_SAVED_NATIVE59_LARGE_IMAGE4_CONTROLS independently recomputes all16 full exact images,analytic quality patterns,camera rectangles,framebuffer ownership,raw counter deltas and12 residency/noDATA checks; all report/artifact/source/input/reference/start/finish/nonce/process-terminal/native-image/package/shutdown/cleanup joins pass. Audit confirms no renderer imported. Actual saved audit completed0/session24656. Every fresh worker uses Python3128/NumPy246/nonsoftwareRTX4090Vulkan610.88,all8shutdownzeros; installedpackage equals small17 exactwheel4b88388c. Fresh environment/cache/cwd removed,no unresolved-worker hold; installedNative58 native4 unchanged. Original licenses/notices retained,cybersecurity excluded.

Next: new artifact-aware scientific aggregate/admissions binding fresh small17/large24/image13/color24/large-image4 evidence and original workload/data semantics,without changing old Native58 producer/checksums. Then fix unsolicitedExpose ownership and collect predeclared5full-update pairs against unchanged1.10 criterion. Complete opaque driver/allocator peaks,scanout,remaining workload/host/ABI/platform matrix and every original requirement remain open. Full goal active;optimization unpublished pending broader qualification. Previous goal turn was progress(actualcolor24);this turn completed actuallarge-image4 and independent raw-evidence audit. No live process remains at this checkpoint.

Continuation checkpoint121, 2026-10-22: Actual Native59 color24 run completed0/session28844. build/native59-color-controls-run-root-1/result.json PASS_NATIVE59_COLOR24_CONTROLS: all24 original RGB(A) volume cases,24 final wholeRGBA frames plus4 original before frames,258048 total pixels exact,maxerror0,0exclusions. Seven original rendering methods each RGB/RGBA,planes,linear sampling,public updates and RGB/RGBA transitions all pass. Four two-input cases require original exact before image and changed final pixels. Both cross-case opacity controls pass (implicit RGB alpha equals explicitly opaque RGBA; lower RGBA opacity changes pixels). Generic original color_volume_wheel_suite.py,fixtures,landmarks,parameter and native-work checks remain unchanged; exact Native59wheel4b88388c selected by CLI, no legacy pin bypass.

color-controls-inputs1 manifest01c2041ee0282b92276d8b9a8c5d10f1134468d917544a52f91a3d89d1beb8cf retains160 unchanged members and original colorGL manifestc8af8d76e1ecdaac1e21303a47ba75a7cce83cb269085a230e89cf0f127c4337. color-controls-cpu1.json passes source/input integrity and actual optimized-interpreter refusal before renderer import. Independent read-only review1 READY_FOR_COLOR24_GPU_EXECUTION completed0/session30566,toolsdisabled/owned scratchremoved before execution; root confirmed controller NumPy availability and actual driver record before admitting run. color-controls-admission1.json binds exact reviewed wrapper/controller/lifecycle/input/profile9(3e7fb65b)/wheel. Controller parent CPU-only NumPy is2.5.3; every actual GPU worker uses fresh Python3128/NumPy246/PyQt6 pinned runtime. Parent array comparisons do not claim a second scientific rendering environment.

color-controls-saved-audit1.json PASS_SAVED_NATIVE59_COLOR24_CONTROLS independently verifies all28 full images,original parameters,7method exposure,4update discriminators,both opacity controls,all artifact/source/reference hashes,actual worker process stamp/nonce/start/finish/terminal joins,loaded native records and8shutdownzeros. Installed package fingerprints equal the already passed Native59 small17 artifact. Every final preservation flag true; fresh environment/cache/cwd removed,no workspace hold,installedNative58 native4 unchanged. New color controller returns nonzero for cleanup/preservation failure in addition to recorded failure status. These are scientific quality/provenance checks,not performance,full opaque driver memory,scanout,platform or release admission. AGPL/original BSD/notices remain preserved; cybersecurity excluded.

Next large-image4 inputs are prepared only: large-image-controls-inputs1 manifest4d8b2fd17d58de5964dd731eede7e141ed5fcef11dab29a82b63e8c3ee8c7441 binds67 byte-exact members (13sources,53 original reference artifacts,1runtime9). Four original scalar/RGBA nearest/linear cases verified before copy. Canonical large_image_wheel_suite.py still pins Native58wheel105698c7; need a separately named Native59 executor with unchanged worker/gate function bodies and explicit new artifact selector/projection,then review/actual run/saved audit. Remaining new scientific aggregate/admissions,Expose ownership/full-update5pairs,complete driver/allocator memory,scanout,remaining workloads/hosts/ABIs/platforms and every original requirement stay open. Full goal remains active; optimization unpublished pending broader qualification. Previous goal turn was progress (actual image13 evidence); this turn completed actual color24 evidence and next input preparation. No live process remains at this checkpoint.

Continuation checkpoint120, 2026-10-22: Actual Native59 image13 controls completed0/session32910. build/native59-image-controls-run-root-1/result.json PASS_NATIVE59_IMAGE13_CONTROLS: all13 original image/label cases,159744 wholeRGBA pixels exact,maxerror0,0excluded pixels. Includes scalar CPU/GPU NaNs,RGB/RGBA,integer host textures,channel blending,label tile/remap,multiscale edits and slice changes. Original image manifest9675b84e and all107 packet source/reference/profile members remain unchanged. New image_controls_run1.py/controller and wrapper were independently reviewed READY_FOR_IMAGE13_GPU_EXECUTION before launch; review actual terminal0/session61155, toolsdisabled and owned peer scratch removed. image-controls-admission1.json binds exact reviewed code, input manifestdd74e501, fullhost profilee5791fbf and Native59wheel4b88388c. Original generic image_wheel_probe.py and comparison/semantic criteria unchanged; no old checksum guards or admissions relabeled.

image-controls-saved-audit1.json PASS_SAVED_NATIVE59_IMAGE13_CONTROLS independently rechecks all13 complete saved images,original reference and artifact hashes,source maps,host versions,actual process stamps/nonces/terminal proofs,loaded native byte identities,8 shutdown zeros and cleanup. Every installed package fingerprint equals the previously passed fresh Native59 small17 package. All workers terminal; fresh environment/cache/cwd removed, all code/input/wheel preservation flags true, no workspace hold. InstalledNative58 native4 remains byte-exact. Audit imports no renderer; this is image quality/provenance evidence, not timing/platform/release admission. AGPL plus original BSD/copyright/third-party notices preserved.

Next color24 packet prepared only: color-controls-inputs1/manifest.json01c2041ee0282b92276d8b9a8c5d10f1134468d917544a52f91a3d89d1beb8cf binds160 unchanged original source/reference/runtime members. Original color-volume OpenGL manifestc8af8d76e1ecdaac1e21303a47ba75a7cce83cb269085a230e89cf0f127c4337 has24 original workers/reports/artifacts verified before copy, all exact original source identities. Includes7 methods each RGB/RGBA,opacity controls,planes,updates,linear sampling and RGB/RGBA transitions; runtime9 unchanged3e7fb65b. Generic color_volume_wheel_suite.py already accepts explicit candidate wheel; need new outer wrapper/controller/review and actual Native59 run, then remaining large-image/scientific regressions and aggregate admissions. Expose ownership/full-update5pairs,complete driver/allocator memory,scanout,remaining workloads/hosts/ABIs/platforms and every original requirement remain open. Full goal active; optimization not yet published; cybersecurity excluded. Previous license-only goal turn was no progress toward implementation; this turn completed new actual GPU evidence and next input preparation. No live process remains at this checkpoint.

Continuation checkpoint119, 2026-10-22: Actual Native59 large24 volume controls completed0/session41642. All24 original registered workloads (256/512cubes,1024/2048viewports,MIP/translucent/iso,resident/full),96 wholeRGBA frames and251658240pixels pass unchangedmax2/noexclusions; observed overallmaxerror1. New parent build/native59-large-controls-run-root-1/result.json PASS_NATIVE59_LARGE24_CONTROLS with no missing cases, all actual worker terminals and input/code/wheel/small-audit preservation true. Fresh9-package3128/246/Qt6 environment/cache/cwd removed and no workspace worker hold. Every installed package fingerprint equals the already qualified fresh small17 artifact4b88388c. Original worker/gate function bodies remain AST-identical; new executor520858fa and explicit selector4b88388c are separately bound from17 unchanged render-source files, not relabeled old Native58 admission. Canonical legacy target pins and reference/benchmark/quality formulas unchanged. Independent large review1 READY_FOR_LARGE24_GPU_EXECUTION completed0/scratchremoved before actual launch.

New execution descriptor large-controls-inputs1/execution-manifest1.json8668a9989fbf42e0d27e286d8487019beffe0277bc717f17e55ccb63f97eb61a retains original330-member baseline73a01bef and adds only exact runtime9/projection/baseline records (333members). Large controller and wrapper preserve parameter/camera/data/color-map/precision/source-shape/FBO ownership/change-discrimination/residency/upload/allocation-conservation/origin/shutdown gates. Private module config selects exact Native59 artifact while old canonical CANDIDATE_SHA stays unchanged. Actual96 captures all survive unchanged; all24 GUI owners report no visible windows after close.

large-controls-saved-audit1.json independently recomputes all96 complete frame differences,48 changed-pixel discriminators, actual raw counter deltas, resident/update zero-work gates and intercepted allocation/free conservation, plus case/process/start/finish/report/artifact/package/source/reference/cleanup joins. Result PASS_SAVED_NATIVE59_LARGE24_CONTROLS,251658240pixels,max1,0exclusions,48changechecks. InstalledNative58 native4 unchanged; audit imports no renderer. These remain quality captures with deliberate readback waits, not throughput, complete opaque driver-memory, scanout or release qualification.

Next13 image/label controls are prepared, not run: image-controls-inputs1 manifestdd74e5019a4773d7df7ca8db154bc57135cc74409d9b155acdc5f289c69e026e binds107 unchanged source/reference/provenance/profile members. Original image manifest9675b84eda8cd0c910d31fa668c6b77cda35ea94f26e8bc2e45a8d0ccd7bf70d and authoring/checksum/source/lock/before-candidate claims verified before copying; includes all13 cases/raw frames/parameters/GLIR/shaders and original stdout/stderr. Existing image_wheel_probe.py already accepts artifact CLI, so new driver can reuse it unchanged, as with small17. Need wrapper/controller/review and actual Native59 image13 run, then RGB(A) volume/other matching regressions and new scientific aggregate/admissions. Remaining expose ownership/full-update5pairs, full memory/scanout, other workloads/hosts/ABIs/platforms/all original requirements stay open. Goal active, optimization unpublished pending broader qualification, no cybersecurity work, AGPL/original BSD/notices preserved. All current children terminal; no live handle at this checkpoint.

Continuation checkpoint118, 2026-10-22: Fresh Native59 small17 scientific volume controls now pass on exactwheel4b88388c, all156672 pixels equal original captures with maxerror0/no exclusions, including6 napari092/numba068/PyQt6 categorical cases and11 scalar cases. Actual small_controls_run2.py completed0/session12563;17 fresh worker processes, parent result build/native59-small-controls-run-root-1/result.json PASS_NATIVE59_SMALL17_CONTROLS. Every actual worker stamp/nonce/terminal, installed package fingerprint, native-image origin,8 shutdown zeros and preserved reference/source/code/wheel checks passed. Shared fresh fullhost environment/cache/cwd removed; no unresolved-worker hold. small-controls-saved-audit1.json independently rechecks all17 actual start/finish/process/report/artifact/hash joins, original85-member input closure,17 whole exact images, all installed native fingerprints, host/profile and terminal/cleanup evidence; audit itself imports no renderer. InstalledNative58 native4 unchanged.

New artifact driver reuses unmodified existing volume_wheel_probe.py (already accepts wheel CLI), all original fixture/comparison/provenance/landmark checks, plus whole-image exact requirement. No frozen Native58 target pin or prior admission was modified. Source/reference/profile packet small-controls-inputs1 manifestf2cfe419d1f9359bdb616e1b9bec9407bf65f35108325ce76eb7286fcc737d72 has85 byte-exact members and fullhost profilee5791fbf4c108029597d6604bbd24df60e845fd750f3127140ba3c1d31fecac1. Initial exact readiness parser omitted digits17 and refused before creating environment/output/worker; refusal preserved. Controller2/admit2 only version bindings and [A-Z0-9_]+ exact-header grammar changed; actual negative/substr parser controls and independent diff review2 READY_FOR_SMALL17_GPU_EXECUTION passed before launch. SourceRoot imports, SystemExit0 handling, per-case admission after validation and hold/cleanup protocol independently reviewed. Case order is explicitly declared by new packet; all17 original cases/semantics retained. No timing/platform/release claim, and no claim of complete isolation from inherited napari/Qt user settings.

Large24 preparation is also concrete: large-controls-inputs1 manifest73a01bef7d80ce0decaae9d193687524cc2827999622681126e79bf312f63236 binds330 unchanged members (17 rendering/verification sources plus original313 reference artifacts). OriginalGL manifestaf7919c6f59dca7addee614a674942697b33d53df3446df0cea422ef980bf2ac, all24 actual original worker/terminal/source/artifact bindings verified before copying. No large candidate run yet. New large_worker1.py520858fa62bccda4d305589928fdc74568b1c1f69e51a43cc9f72031b008f30f preserves exact original ASTs for sources/assert_successful_parent/load_reference/assert_stage/worker (5functions), including all parameter, whole-frame quality, residency/hot-work, counter, original-reference and lifecycle checks. New module explicitly selects Native59 artifact4b88388c and copied source-root layout; old canonical large suite CANDIDATE_SHA remains unchanged. large-worker-projection1.json separates unchanged render-source map17 from new executor hash/artifact selector; not a relabeled Native58 admission. Large wrapper/controller, review and actual24-case run remain next.

Remaining: execute/review fresh large24 and other image/scientific regressions, generate new matching scientific aggregate/admissions, then expose ownership/full-update5pair performance, scanout/complete driver allocator peaks, remaining workloads/hosts/ABIs/platforms and every original requirement. Canonical optimization still unpublished pending broader matching regressions. Full goal active; cybersecurity excluded; AGPL/original BSD/notices preserved. All current children terminal; no live task handle remains at this checkpoint.

Continuation checkpoint117, 2026-10-22: Fresh Native59 numeric GPU qualification packet completed successfully; original full goal remains active. numeric-inputs/manifest.json c44c6b6912944a0b920f6b69cd0338b193685efcb33755c2e1a462cc49c529ca copies28 exact previously sealed CPU-packet members:26 fresh originalGL controls plus original process/root audit records. OriginalGL manifest remains fca64768c1e433e41494c197d0acd23c47841c7f039329d8a2b25b80e3ca5054, original wheelc486, Python3128/NumPy246/NVIDIA4090driver610.88. Twelve cases cover all8bit values and finite deterministic16/32bit controls;13304 logical values total. Rows are1xcount, no padding points or comparison exclusions, all original raw red bytes compared exactly (R32F via uint32 bits plus raw bytes), other channels exact, public DATA dtype/shape/SHA matched, one padded upload and separate padded readback/logical GPU byte count checked, user/native draw counters0.

numeric-controls1.json passes actual optimized-interpreter refusal before renderer import, exact input lengths/hashes and exhaustive8bit domains; owned CPU scratch removed. Independent numeric review completed0/scratchremoved with READY_FOR_NUMERIC_GPU_EXECUTION, exact numeric_worker1.py a3bc9953cf73f6744be34160a452d54abc8ecb3b3248a2e1bfe7f6975e9b6ded and numeric_run1.py5f01373d6a08e139728380788faebe42d881472d0e8126b5abab1a0267bc2001. numeric-admission1.json pins reviewed code/input/profile/runtime. Actual numeric_run1.py completed0/session72595, launcher89680, nonced6841e58e81446b28ba9b1a813bfb394, exactwheel4b88388c in fresh isolated3128/246 environment, real nonsoftwareRTX4090/Vulkan610.88. build/native59-numeric-run-root-1/result.json status PASS_TWELVE_NUMERIC_TRANSFER_CASES, all12cases/13304values zero mismatches, actual worker stamps/terminal and loaded-image origins/shutdown zeros verified. Every code/input/profile/wheel preservation flag true, fresh environment/cache/cwd removed, no workspace hold.

numeric-saved-audit1.json independently verifies saved12 complete RGBA captures plus12 raw red files against unchanged original bytes, all13304points, all dtype/shape/transport and raw counter deltas, all channels/no draws, actual start/finish/cleanup joins and installedNative58 native4 unchanged. This audit imports no renderer. Existing larger historical numeric corpus and its old Native28 guard remain untouched; new packet does not claim to replace it, nor exhaustive16/32bit, shader-sampling, allformats, scientific-image, performance or release qualification. No native source/wheel/reference/benchmarks/thresholds modified. AGPL and original BSD/notices retained; cybersecurity excluded.

NEXT: implement explicit new-artifact/versioned scientific driver and run fresh scientific/image/small17-volume/large24-volume checks for exact Native59wheel4b88388c, preserving old Native58 pins/admissions and original controls. Then expose ownership/full-update5pairs and remaining scanout/complete driver allocator/platform/workload/all original requirements. Current canonical optimization remains unpublished pending broader matching regressions.

Continuation checkpoint116, 2026-10-22: Lifetime review3 completed terminal0/scratchremoved with READY_FOR_LIFETIME_GPU_EXECUTION for exact worker2/controller3/wrapper1/projection/input/profile. lifetime-admission3.json binds those reviewed source hashes, manifest1578370d and runtime3e7fb65b; no older FIX verdict relabeled. Actual lifetime_run3.py completed0/session17145, launcher88164, nonce8767a4e4ac8944628f929fa0c2db4038, against exact Native59wheel4b88388c on fresh CPython3128/NumPy246/nonsoftwareRTX4090/Vulkan610.88. build/native59-lifetime-run-root-1/result.json status PASS_EIGHT_TEXTURE_LIFETIME_CASES, all source/profile/input/wheel preservation booleans true, actual worker terminal and shutdown zeros verified; fresh environment/cache/cwd removed and no workspace worker hold.

All3 original revision cases pass exact stored GL and analytic pixels with trace ordering preserved. Both new aligned64 and padded65 queued revision/delete cases retain >=2 draws through texture/program deletion, with no completion_waits, finish_calls or dawn_queue_submits changes before the one final read; final image exact red-left/blue-right,2 full uploads and exact2048/4096 total submitted bytes respectively. Original selected warm36 test reports0 hot completion waits, peak tickets1, retired36. Original96generation test passes exact final95-red image, peak tickets1,16384 live texture bytes and48 live buffer bytes at completion;12 close-with-submitted-work test passes. These are renderer-owned lifetime controls, not full opaque driver peaks or images for every generation. Actual saved lifetime audit independently verifies8case statuses,5 whole exact captures, raw queue/wait/submit conservation, original reference hashes, process/nonce/start/finish/cleanup joins, source holds and unchanged installedNative58 native4. No scientific/performance/release admission inferred.

User cleanup instruction applied again after actual terminal proof: wheel_objects_cleanup1.py removes only22 .obj files under this new wheel owner's four known MSVC project Release directories,26454252 bytes. All targets name/alias gated and absolute paths checked inside exact new native-build. Raw fresh native4, wheel archive and CMakeCache hashes remain unchanged. No old/rejected cleanup paths touched; no errors/retry. All raw/frozen/reference/failed review/CPU refusal evidence remains preserved. Native59 contract build and archived outputs are untouched.

NEXT: fresh numeric/scientific/image/volume regressions with an explicit new-artifact driver/source epoch rather than changing existing Native58 pins or old admissions. Then expose ownership correction and qualified five-pair full-update performance; scanout, complete driver/allocator peaks, remaining workload/platform/host/ABI and every original requirement stay open. Canonical native optimization is still unpublished pending broader matching regressions. Full goal active; cybersecurity excluded; AGPL and original BSD/notices preserved.

Continuation checkpoint115, 2026-10-22: Previous goal turn was progress (fresh Native59wheel4b8838 and actual8finiteGPU/23capture pass with cleanup). Current turn prepares a separate eight-case pending-revision/submission-lifetime packet; no lifetime GPU launch yet. lifetime-inputs/manifest.json SHA1578370da3260362527041ce5647efdeeaa1542e60db85849768a6f09bcfa7e5 binds16 exact copied members: original fixture_gloo and fixture_revisions match historical OpenGL manifest source hashes;3 original reference cases each retain RGBA/capture/GLIR/shader hashes; selected submission-lifetime module keeps5 original function bodies with AST equality, omitting only pytest metadata/unrelated device-generation tests. Original references/fixtures/source remain unchanged. Original NumPy253 versus candidate246 is explicit; this finite analytic/reference comparison is not a new matched scientific-environment admission.

Latest lifetime_worker2.py c408c5f14dc2dad5dad097b47db5dc5bf6fe4c23aba34670709af5494c12e9fe covers3 original queued texture revisions, new aligned64/padded65 queued red/blue revisions with program/texture deletion before final read, and exact original warm36/no-hot-waits,96generation/bounded live allocations and12close/submitted callback tests. ObservedRunner records last-clear counters without changing render steps; require >=2 newly pending draws and no completion_waits/finish_calls/dawn_queue_submits change before final read, then pending draws0. Delete cases require unchanged wait/submit counters and2 exact padded full uploads after consumption. Module/Runner identities and per-case observation cardinality checked. lifetime-controls2.json passes actual -O refusal before native import, bytes/array JSON reporting and all5 original function ASTs unchanged, owned CPU scratch removed.

Lifetime reviews1/2 are terminal0 with scratch removed, preserved FIX verdicts. Review1 B1/B2/B3 fixed in worker2/controller2. Review2 confirms those fixes but requires runtime profile and transitive helper binding. Latest lifetime_run3.py39c8a2eca6792aaae150d1969e27b2d8f744759ce7ee61bb90da2ac92f9a3f14 pins profile and derived nine-package runtime, all reviewed input members and final preservation; normalizes Windows review-map separators with alias rejection. image_lifecycle_selected.py da322bfac2e43860c11563652680d7fbf20ae6740f457ff0588f89033e801be9 preserves the exact5 used image_wheel_runner function ASTs/contextmanager decorator, with no unused fixture_image_extensions import and no stub. lifecycle projection receipt records original source/hash. Source tests/conftest.py only echoes captured stdout; no autouse fixture/device lifecycle omitted. CPU controls3 prove actual raw Windows metadata normalization and runtime file digest3e7fb65bc3424c1f898bdb9ecfab81ca327e103dabd56bdf30f3cb5ec2242d7a from profilef2e578773ed6233b177c38f4717210de3df587b7383086e59cf227df21dd5c65. Initial in-memory LF-versus-physical CRLF digest refusal is preserved; corrected text-mode file/control passed without launching a native/GPU process.

Follow-up lifetime_review3.py is currently running as exec session33209, Claude33044, output lifetime-review-response3.json / lifetime-review-operation3.json. Do not edit held code/input files during that review. No lifetime-admission3.json exists yet; after actual terminal response, resolve findings, create exact code/profile/runtime/input admission and execute lifetime_run3.py only when readiness/bindings pass. Old review/controller versions remain preserved. Native58 installed4 and frozen Native59/source/wheel unchanged. Next broader numeric/scientific/image/volume artifact-aware regressions still needed, then expose ownership/full-update performance, complete memory/scanout/platform/all original requirements. Goal active, AGPL/original BSD/notices preserved, cybersecurity excluded.

Continuation checkpoint114, 2026-10-22: Fresh Native59 CP312 PEP517 wheel completed0/session40171, package523 source members and exact allowed package/native/license inventory verified. Wheel SHA4b88388c79cb1566b9cc6d41d83a82e8454799882c1bcef664a504f94dd2bf8f at build/native59-wheel-windows-cp312-root-1/wheels/vispy-0.17.0+vulkan.1-cp312-cp312-win_amd64.whl. Source614 and installedNative58 native4 unchanged; owned build UV cache removed once after actual child wait. wheel-native-audit1.json passes all4 native bytes equal their own fresh leaf outputs without strip transformation. Wheel native SHA: _dawn d8aea7c6e24d7443cd78989985091ba147ebbba5774112c835763f611895ddf3; _sdf_cpu e3fd6a52e620e6d6e507d78949e5243dc83f1767acdf827d9b25f29e96595fb1; layer16caefd9436b9702d5fdfc11cbad922b457d2479a7affebf9efc672303ca83d2; layerJSON7323cea73a46efcba615ca452d2b0235e3741109628c4bf2979c105e6ae69d56. AGPL and original BSD/notices match both package and dist-info license attachments.

Actual finite GPU controller gpu_run2.py completed0/session46898, launcher79196, nonce00bce27ab5fb48829c1fc6d19345df8a, fresh CPython3128/NumPy246 wheel environment, nonsoftware RTX4090/Vulkan driver610.88. build/native59-gpu-run-root-1/result.json status PASS_EIGHT_FINITE_GPU_CASES. All eight cases pass with23 exact whole captures: aligned64/padded65, f64-to-r32f conversion with actual f64 DATA transport, empty-zero allocation, assembled initial patches, later partial, repeated full updates and every 3D slice. Upload/readback/logical memory accounting and two equal 3D resident draw copy baselines pass. Start/finish actual worker stamps, package/native image origins, shutdown zeros, source/wheel holds and actual terminal verified. Both fresh environment and cache/cwd removed; no unresolved-worker hold. This is finite correctness, not complete pending-revision lifetime, scientific, performance or release admission.

gpu-saved-audit1.json independently rechecks actual saved parent/worker/start/finish/teardown hashes,23 NPY whole capture payload digests against runtime expected digests, raw counter delta recomputation, required8 cases, terminal and cleanup proof and unchanged installed native4; audit itself imports no renderer/GPU. Worker report SHA b94c72fa5ea058084290b542589d3823a19a246e0f6247061ce5698cacfd5968. HistoricalNative58 archives/reference/benchmarks and failed drafts stay unchanged. Published CI39746758393 latest observation13 completed/0failures, remaining queued/running; no fullmatrix claim.

NEXT: complete forced pending-revision lifetime tests and fresh numeric/scientific/image/volume admissions on exact4b8838 Native59 wheel. Existing large_volume_wheel_suite.py / volume_scientific_admission.py hard-pin Native58; do not edit historical artifact pins or relabel old admissions. Add explicit new artifact-aware/versioned driver and provenance bindings, preserving original records, fixture formulas, whole-image limits, hardware and quality gates. Then qualified full-update performance after expose ownership correction; scanout, complete driver/allocator peaks, remaining workloads/platforms and every original requirement remain open. Canonical native port is still unpublished pending broader matching regression work. Full goal active; cybersecurity excluded; original license attachments preserved.

Continuation checkpoint113, 2026-10-22: Native59 is fully terminal-successful, not just CTest-successful. Continuation session65801 ended0; build1.json status BUILD_AND_CTEST_PASSED actual child31700 waited0, log17a61a87dc779d424c9c13492e8f0d1e0ac4ce9817af5192fdd9b54a2742eff5. Native59/status.json plus exact44 JUnit, all614 declared source members, installed Native58 native4, final ten-origin dependency log and archived new native4 are bound by new native-terminal-audit1.json (status PASS_NATIVE59_TERMINAL_BUILD_AUDIT, total/passed44). Build receipt SHA1fe82dc02554c8b4fd673c0ead3252074f8b5b6c5c1cd7551695394f8f309b70; source tree remains823292f29ad5967096aa10124e2e192b13f24cde768f3f0a45eb64cd8b1c2186. No in-place activation or GPU qualification.

Independent parent review completed0/scratchremoved with FIX_BEFORE_LAUNCH. Preserved reviewed wheel_build1.py / gpu_run1.py and response. New wheel_build2.py and gpu_run2.py apply W1..7/C1..7: actual terminal audit/exact44 binding, explicit optimize guards, unwaited UV child hold/preservation, robust result publication after cleanup/preservation errors, postwheel source recheck, clean UV/LINK/config and effective overrides, exact source/native/declared-license inventory; exact peer verdict token, immutable external parent-admission code hashes (avoids embedded self-hash fixed point), required native/wheel origin audits, pinned uv/base Python/version, root binding, complete hold paths/argv/startstamp, terminal lookup from start before finish and failure-report preservation. admit_parents1.py records root finite diff resolutions and actual two -O refusal subprocess controls, no GPU import/launch; parent-admission1.json fixes exact six code/helper hashes. No invented independent parent READY. Origin/strip audit necessarily follows fresh wheel construction and gates GPU execution.

Fresh PEP517 Native59 CP312 wheel build is now actually running under exec session40171, UV child36256 created10:45:22 UTC. Owner directory build/native59-wheel-windows-cp312-root-1, source exactw45, fresh native-build, immutable vendor SDK reused only. Build log shows real isolated Python3128 and MSVC configure. Preserve current outputs; never relaunch this initial owner on observation timeout. wheel_build2.py will record terminal result, source/native4 preservation, package/native/license checks and single owned UV cache cleanup after actual child wait. wheel_native_audit1.py is prepared, unexecuted: compares all four wheel native members to this fresh leaf's own outputs and source/SDK cache identity. Exact-byte match passes without strip transformation; any difference is retained and requires explicit strip/origin investigation, not relabeling. gpu_run2.py remains unexecuted until wheel result and origin audit pass. Full original goal/scientific/performance/platform/scanout/memory/lifetimes remain open; AGPL/original BSD/notices and no-cybersecurity constraint unchanged.

Continuation checkpoint112, 2026-10-22: Native59 CMake configuration and actual compilation passed; all exact44 CTests pass in7.95seconds. New ctest-audit1.json independently checks actual JUnit44 unique names equal the approved inventory, zero failures/errors/skips/disabled, and texture_contract's actual emitted14603 full-upload equivalence cases. Native build process remains active in final immutable source/harness/SDK/dependency post-checks (verifier child49980 started10:38:36 UTC); no terminal build1.json/status.json/archive admission yet. Continuation session65801 still owns the single initial attempt. Do not launch wheel_build1.py until its terminal prerequisites exist and pass.

GPU follow-up peer completed terminal0, owned scratch removed, verdict READY_FOR_FINITE_GPU_EXECUTION for exact gpu_worker2.py a621c23714667e97185adbf1f157d25f3795f2e2e8e7b18d63b1085995aecfb4 only. Parent hardware/isolation enforcement remains required. Root gpu-review-resolution2.json records actual upload_buffer source counter check (partial rows.size charged to copy_bytes) and R32Float readback defaults, finite scope and remaining gaps. New gpu_wrapper1.py and gpu_run1.py are syntax-checked, unexecuted lifecycle code: fresh external hash-locked runtime/wheel environment, copied held worker/helper, nonce/start/finish real process stamps, native module/package provenance, nonsoftware NVIDIA4318/9860 driver610.88, shutdown zeros, terminal proof before cleanup. Unknown actual worker termination preserves environment/cache/cwd and writes existing workspace-wide hold. Byte/scalar worker diagnostics supported; ndarray diagnostic serialization remains unsupported and cannot produce an accepted parent result. 2D storage rereads versus 3D sampled draws and residual copy-byte scope stay explicit; full pending-revision lifetime coverage still open.

Independent orchestration review parent_review1.py is currently running, exec session73035, Claude48004 started during postbuild checks. It covers wheel_build1.py, wheel-plan2.json, new wrapper/controller, reviewed worker and existing lifecycle helpers. Authoritative parent-review-response1.json / parent-review-operation1.json only after terminal completion. No parent READY or fresh wheel/GPU execution claim yet. Current new sources/tests are still unpublished; original full goal, scientific/performance/platform/scanout/memory gates, AGPL/original BSD/notices and cybersecurity exclusion remain intact.

Continuation checkpoint111, 2026-10-22: Native59 initial build has completed its repeated mandatory preflight and reached real CMake configuration at build/native-pass59-sdk. Actual CMake child66864 started10:29:35 UTC and dependency verifier39748 started10:29:41; source/native protection checks remain enabled. Configuration log is build/evidence/native-pass-59/configure.log. Continuation exec session65801 still owns the one initial build; no actual compile or 44CTest completion yet. Previous turn was progress (preflight passed, corrected eight-case GPU draft and CPU failure controls); current turn prepares the actual fresh-wheel builder while configuration runs. Never restart on observation timeout.

New build/native59-prep-root-1/wheel_build1.py is prepared and syntax checked, NOT launched. It requires actual terminal successful build1.json and native59/status.json, exact new frozen/manifest/source614 identities and unchanged Native58 native4, then checks pinned uv/base Python executables and exclusively creates build/native59-wheel-windows-cp312-root-1. It runs the fresh PEP517 command from wheel-plan2 with parallel3 and explicit clean build-environment settings. It verifies wheel source-package bytes, four native members, AGPL metadata, unchanged BSD/AGPL license attachments in both package and dist-info, and third-party text notices. Native runtime/source-origin/strip audit is still explicitly required; wheel construction alone is not qualification. Fresh owner UV cache is removed once only after actual child wait, failures recorded without cleanup retry; native build outputs and logs stay preserved.

Read-only GPU follow-up review is currently running as exec session44596, actual Claude41592 started10:31:34 UTC. gpu_review2.py binds unchanged corrected gpu_worker2.py plus prior review/root resolution/CPU controls; output gpu-review-response2.json and gpu-review-operation2.json will be authoritative only after terminal completion. No follow-up READY or runtime pass is claimed. A failed shell quoting attempt before preparing review2 made no file/source changes; corrected file-based preparation launched the single intended review. Full goal, pending lifetime/scientific/performance/platform gates, AGPL/original notices and cybersecurity exclusion remain unchanged.

Continuation checkpoint110, 2026-10-22: Native59 read-only build preflight passed, exact source tree823292f29ad5967096aa10124e2e192b13f24cde768f3f0a45eb64cd8b1c2186 and frozen-inputs6ccb8db4892b5adca819f20caf49107cd3ee3d7bb9e0e2d8a216ec5efe870eef. Preflight log53d775ad11ed0aef47a9108c779957d8993dc966e81778367cdf1d09c8a46ed4. Continuation session65801 started initial build launcher31700 at 10:25:21 UTC; build command repeats mandatory physical preflight before configuration/compilation. No build/CTest pass yet. Inspect current process creation identity and receipts; old PIDs may be reused. Never duplicate the initial attempt.

All eight GPU cases now drafted, including exact full three-slice 3D sampling. Independent code-only review gpu-review-response1.json returned FIX_BEFORE_GPU_EXECUTION, preserved with terminal0 operation and removed peer scratch. Reviewed gpu_worker1.py remains unchanged at6dd194ea034d3709ebdb40775ab1530b35ea336b07c3a227e8784bdd9b3d4a57. Corrected gpu_worker2.py a621c23714667e97185adbf1f157d25f3795f2e2e8e7b18d63b1085995aecfb4 addresses byte/scalar JSON serialization, atomic result publication, explicit Python optimize refusal, actual canvas warm-up, separate readback pitch, exact 3D copy delta against two equal resident draw/uniform controls, allocation branch recording, Dawn parser identity/restoration and missing-case derivation. gpu-controls1.json verifies bytes/scalar serialization and an actual optimized-interpreter child refusal before renderer import with atomic failure result/eight missing cases/GPU false; child waited and all owned control scratch removed. These are CPU controls, not GPU passes. Root resolution is explicit; no independent follow-up READY verdict or runtime/scientific/lifetime qualification claimed. Two-dimensional cases are storage rereads, not sampled redraws; complete pending-revision lifetimes remain open.

wheel-plan2.json prepares a fresh isolated CP312 PEP517 leaf build from exact w45 source, with immutable admitted SDK reused but no project/native outputs reused, INPLACE OFF, contracts OFF and dependency/origin/CRT checks retained. Plan1's absent source_tree_sha256 value is preserved and corrected in plan2 from the actual bound frozen inputs; no launch yet. Wheel native/package/license checks and terminal successful Native59/44CTest prerequisites remain mandatory. Goal active, full scope unchanged, no cybersecurity work, original BSD/notices retained beside AGPL.

Continuation checkpoint109, 2026-10-22: Native59/w45 source freeze completed successfully with actual child exit0/wait and receipt build/native59-prep-root-1/freeze1.json. Frozen-inputs SHA is 6ccb8db4892b5adca819f20caf49107cd3ee3d7bb9e0e2d8a216ec5efe870eef; freeze log SHA 1afcd6a25ae68dd4f4d7335cd47ad2e0ffb740ce40d263ec71c7d633baef4bb7. Snapshot/harness/evidence exist and build directory was absent at completion. Native4 protected baseline is unchanged. Continuation session65801 observed freeze parent termination and started read-only build preflight (launcher91220, creation 2026-10-22 10:21:05 UTC); actual compilation and CTest still pending. Do not start another initial attempt. All source/admission exclusions and original full goal remain intact.

gpu_worker1.py under the same owned preparation directory is a new unexecuted seven-case 2D GPU draft, syntax checked only. It requires explicit isolated installation/native SHA/nonce, actual Vulkan identity, captures exact whole image bytes and transport dtype, checks padded upload/readback counters and logical live texture bytes, tests resident redraw and later partial/repeated-full updates. Partial-copy expectation follows observed texture allocation versus exclusive reuse; it does not assume a completed read necessarily retains a prior Ticket. Runtime review/execution, forced pending-revision lifetime coverage and the separate 3D case remain required. It must not be promoted to GPU/scientific/release evidence from syntax checks. Goal active; cybersecurity excluded; AGPL and original BSD/notices preserved.

Continuation checkpoint108, 2026-10-22: Native59/w45 preparation now has an exact 614-member source inventory, 4133-member native harness, 18 CPU ownership packets covering 88 files, and unchanged 42 native targets / 44 CTest names. The new upload packet owns both edited renderer files and the three texture-test files; prior ownership transfers retain their original proofs and archives. Sixty focused Python controls pass with no failures or skips. Metadata-only independent review returned READY_FOR_READ_ONLY_PREFLIGHT after correction of the protected baseline from the Native58 build manifest's historical Native57 baseline to the actual Native58 activation. AGPL-3.0-only and all original BSD/notices remain attached unchanged in both canonical and public checkouts; no cybersecurity work.

The unchanged mandatory source preflight passed against candidate5, including current native binaries, source/harness/packet bindings, SDK and admitted dependency origins; new output directories remained absent. Root source-freeze approval6 binds ownership-manifest.approved6.json SHA b83c9f3aacf961424b00e9ce9ab01bd8019453fe11cfdfa6e9011e716ca61ead. Its scope is explicit: root CPU ownership/source freeze after finite metadata review and actual physical guard, not an independent physical reviewer or GPU/release admission. Source freeze1 is currently running, with snapshot and harness captured and the actual w45 dependency verifier active. Do not restart on observation timeout, reuse partial outputs, modify installed native binaries, or claim freeze success before freeze1.json records actual terminal success.

Prepared build_preflight1.py and build1.py retain all mandatory checks and use the exact new manifest/frozen-input SHA. Active continue1.py, exec session65801, holds a verified OS process handle to freeze parent76968 (creation 2026-10-22 10:07:16 UTC), waits for it to terminate, requires successful freeze1.json, then runs read-only build preflight and one initial build/CTest in sequence. It stops on any failure without retry. Its authoritative log/receipt and all runner files are under build/native59-prep-root-1. Inspect the live session/process and terminal receipts before taking another action; do not launch a duplicate build. Installed Native58 binary baseline remains protected.

gpu-acceptance-plan1.json records eight pending cases: aligned64/padded65 RGBA8, actual f64-to-r32f conversion, empty-zero allocation, padded3D, assembled initial patches, later ordered partial update, and repeated full updates. It specifies exact submitted/logical byte counts, full readback, completion/lifetimes, native transport verification, and separate readback/upload accounting. This is an execution plan, not passing GPU evidence. Fresh matching wheel, runtime/scientific/volume admissions and paired full-update timing remain required after Native59 build. Published CI39746758393 at be393c3 has all ten Linux/Windows CPU jobs passing; macOS CPU jobs remain running/queued at observation, not a whole-matrix or hardware pass. Expose ownership, scanout, complete driver/allocator peaks, remaining workload/platform gates and every original requirement remain open. Goal active.

Continuation checkpoint107, 2026-10-22: Previous goal turn was progress (CI drive fixture fixed/pushedbe393c3 and private14603case CPUprototype). Current turn ports fullupload optimization into canonical C++ and adds executable equivalence tests, fresh independent originalGL numeric controls, actualruntime translationunit checks and code-only peerreview. Full13goal remainsactive; cybersecurity excluded. Currentcode is WIP NOTpushed and no native59build/freeze/wheel/GPUqualification has run. Installednative4/archive/frozenrecords unchanged; allnewownedexternalcompile/provider/peer scratch removed after terminalwaits.

Fresh originalGL controls captured at build/full-upload-gl-corpus-run-root-1/worker from exactc486originalwheel, Python3128/NumPy246/PyQt6/NVIDIA4090driver61088, installedpayload verification and actualnonce/startfinish/processstamp/wait. Sixinteger types u8/i8/u16/i16/u32/i32 xR32F/R8, exhaustive8bit and deterministic16/32bit edge/rounding values. Raw24bytefiles+cases.txt hashes bound bymanifest fca64768c1e433e41494c197d0acd23c47841c7f039329d8a2b25b80e3ca5054. Exactexisting12case corpusreader and proposedfullupload/paddedrowreader bothpass12/0mismatchedbytes; no tolerance or originalreference replacement. This is a fresh additional corpus, not a claim that unlocatedhistorical corpus provenance passed. Actualupstreamworker/ownedcwd/env/cache terminal/removed. Captures are numeric correctness controls, not timing/image/platform/releasequalification.

Canonical edits cpp/runtime_texture.hpp e1988fe76563d4a4356a5c8c64791fbfd2fbe9f23e1a1caded60f337b242a66d and cpp/runtime.cpp initially61b6f6 now21c9415096e9623467880fb8ef132be4f06749196afeb3051df6d867c46d4555. Sharedvalidateddescriptor/directpredicate replacesduplicatedpreparation; FullUpload move-only view stores validatedextent, rejects temporarysource, checksborrowaddress/size. Existingdirect nonemptyengine-owned pixels borrow synchronously throughWriteTexture. Alignedrows skipmaterialization/copy; allconversion/empty/padded fallback retained. Fullpathlogicalrev.gpu_bytes usespayloadsize; submittedcopy/texture counters use paddedcallbackbytecount. Conversiontimer endsbefore uploadtimer, bothidempotent/lifetime ordering retained. Fullpartialblock/depth/orderedpaths preserved. Frozenlegacyoracle only in tests, absentfromproductheader. New tests/textures/texture_preparation_legacy_reference.hpp and texture_full_upload_contract.hpp calledfromexisting texture_contract.cpp, so existing CMake target/CTestnames unchanged.

build/full-upload-native-port-root-1/cpu1.json passesactualcanonicalheader/tests onMSVC/GCC:14603matrixcases each and actualfreshGL12controls throughbothprepare_texture andFullUpload submittedrowreader onbothcompilers. Wholecurrentruntime.cpp MSVCsyntaxpasses; firstGCCsyntaxfails preexisting missingtypename on decltype(obj.input_current)::Entry sizeof. One-wordstandardC++fix retained inportability-fix1.json, failedsyntax1/log preserved, syntax2 nowMSVC/GCCpasses. Syntax is not object/link/nativebuild/GPU evidence. AllactualCPUcheck subprocesses waited, externalheaders/binaries removed. audit1.json independently verifies code/source/log/GLmanifest/actualworker lifecycle; originalpartialblock and logical/submittedbyte coupling sourcechecked. OldCPU/syntax receipts stay bound to their actualversions.

Independent read-only code review completed0, heldsources andscratchverified, verdict READY_FOR_NEW_NATIVE_BUILD (codeonly, NOTNative59formaladmission). Rootresolution bindsrequirednextGPUcases: aligned64/padded65borrowed, convertedfallback, emptyzero,3D, assembledinitialpatches/laterpartial; assertuploadcount/logicalgpu_bytes/submittedcopy+texturebytes/readback/lifetimes. No speedup inferred from earlierprivate CPU microbench; latest canonicaltiming notmeasured. Callbacks recordprivateerror/lost/logstate only; all source reads underengine mutex throughinspected entrypoints. Moved-fromview validalias anduntesteddefensiveguards explicitlynotclaimedotherwise. ScopefreshGL12numeric controls narrowerthanallscientific/host gates.

Finite Native59/w45 preparation source-delta2.json checks614previouslydeclaredcurrentmembers through exclusion-awareReader, no dependency/SDK/oldownershippayload replay. Fourdeltas vsNative58: currentprior cmake/dependency_origins.py923772 andpyprojectb7ef21, plusnewruntime/sourceheader. Runtime priorCPUowner native57-composed-normal-ten-leaf-reviewed-cpu andheader priorowner native49-integer-sampling-transitions requireexplicittransfer. New2testheaders andchangedtexturetest needharnessbindings; currentCIrollbackfixture change alsofutureharnessidentity. Draft1 mislabelled packetmemberpaths ashashes; draft2 correctsmetadata labels usingalreadyreadparent hashes, preservesdraft1, no payloadre-read. Fullcurrentnamespace/ownership/admission stillpending. No fabricatedmanifestseals or oldproof promotion.

NEXT: formalnewNative59/w45 ownership/sourceadmission (includingpriorbuildmetadata deltas), freeze/build withSDK/origin/protected exclusions, fresh CPUCTest/native/wheel andruntimeGPU counter/readback cases; then scientific/fullvolume regressions andfullupdateperformance. Exposeownership, scanout, complete driverallocator peaks, remaining23volume/full66/platform andall13release requirements remainopen. AGPL/originalBSD/notices unchanged. Latestpublicbranch remainswork/volume-admission-ci-paths @be393c3; currentnewnativeport waitsforbuild/qualification beforepublication.

Continuation checkpoint106, 2026-10-22: Previous goal turn was progress (observer-free benchmark shipped @1f2ac566, resident5pairs and fullpartial/expose diagnostics audited). This turn fixes actual Windows CI cross-drive lifecycle-fixture failure and implements/tests a private native full-upload optimization prototype. Full13 objective unchanged/active; no cybersecurity work. No canonical renderer C++/Python runtime, native4, frozen artifacts, archives or scientific references modified.

Actual CI39745217828 Windows jobs fail test_later_case_failure_cannot_publish_partial_admission_set: checkout D:/pytest scratch C: makes os.path.relpath fail before intended latercase injection. Downloaded completedjob119711861521 log retained at build/volume-observer-ci-fix-root-1/windows312.log SHA d2b3bd6e11448b992c9b85dea0792ebe78df14541de5c4ed77230033ce953ae7. Scoped test-only os formatter proxy isolates publication lifecycle from evidence path serialization; global os.path and production producer remain unchanged. New assertions require first/second verifier calls, first staged admission exists and second absent. Public858+focused62+WSL62 pass0 skips/errors; ownedtemps removed. Onefile fix pushed/remoteverified clean @be393c3f8eac3554461af514607e3d3a7983c689 branch work/volume-admission-ci-paths, child of observer-free branch. Five original Windows failures preserved. New CI39746758393 all5Windows scientific steps PASS at observation33a1edd8; native/full20matrix still running/queued, no wholematrix/hardware claim. AGPL/originalBSD/license5 holds unchanged.

Private prototype under build/volume-full-upload-prototype-root-1 copies23 exact headers/licenses/testsource into owned external temporary directories. Existing SDK/native binaries not loaded. Reference header remains exact canonical cpp/runtime_texture.hpp; proposed copied header refactors shared descriptor/direct-storage predicate and compares exact legacy function kept as TEST-ONLY oracle. FullUpload is move-only, rejects rvalue TextureData at compile time, binds validated width/height/depth, borrows engine-owned vector only for nonempty existing direct formats, verifies source address/size, falls back to established conversions/zero-fill, and packs unaligned rows unchanged. No independent TextureData argument can mismatch row layout. Synchronous consumer callback limits row pointer lifetime. Canonical port MUST omit legacy_prepare_texture test oracle, preserve native byte accounting/timer/callback/ownership/revision semantics and leave partial/ordered/depth paths intact.

First wrapper attempt result1 FAILED before compilation due cmd/VsDevCmd quoting; fixed ownedbatch wrapper result2 passes11957 CPU cases bothMSVC19.44/GCC, existingtexture_contract, allchildren waited andtemp removed. Five alternating200iterations perrole CPU-preparation pairs include common64MiB shadowcopy and exclude DawnWriteTexture/GPU/Qt/driver: median legacy42.5545745ms/prototype5.626508ms. These timings belong ONLY to initial private version, not latest refactor or endtoendframeperformance. audit1.json retains exact scope/source/log hashes.

Independent read-only peer review completed0, scratchremoved, verdict FIX_BEFORE_PORT preserved. Findings: layout/source mismatch precondition, missing8ui/16i, deletedoverload tests, duplicateddescriptorlogic. New private full_upload2.hpp/contract2.cpp/proposed-runtime_texture3.hpp address them: concept/lvalue/move assertions, livecontent-edit visibility and resize rejection, expanded integer matrix, shared descriptor validation. Intermediate result3 compile fails missing texture_detail namespace in copied helper; retained, sources andtemp held/cleaned. Corrected result4 PASSED14603 cases on bothcompilers:922borrowed8856fallback4825rejections2094aligned7684padded. Exact bytes/descriptors/runtimeerror text, movedview consumption/sourceimmutability checked. Existing texture_contract now compiles against proposed refactored copy (not just unchanged header). audit4.json 4-way binds originaloracle/proposed/private23sources/compilerlogs, all6children terminal, allnewownedtempdirs gone. New prototype timing NOT measured and no GPU/native admission or speedup claim. Source3/4 snapshots, failures and review lineage retained; root review-resolution1 does not invent peerREADY.

Root source audit confirms current Vulkan QueueBase::WriteTextureImpl synchronously copies data inside DynamicUploader::WithUploadReservation before returning; copied API context stays under engine mutex in inspected execute/present/read paths. This is preparation for integration, not a complete everycaller/callback proof. Existing sealed12-case conversion corpus remains pending; do not substitute or claim it passed. No native59 source freeze/build/wheel or canonical upload port yet. NEXT: locate/run sealedcorpus; finish full native caller/callback and byte/timer/accounting audit, port tested shared helper under fresh native source epoch, build fresh artifacts and rerun scientific/image/fullupdate gates. Expose-paint ownership, scanout, complete driverallocator peaks, remaining workloads/platforms and every original13 requirement remain open. Existing saved Native58/current-source proofs remain historical as appropriate; changed test-harness source must be bound in future identity.

Continuation checkpoint105, 2026-10-22: Previous goal turn was progress (observer-free worker/controller implementation,434 CPU checks and actual first pair; subsequent candidate rejected for2 unowned paints). This turn ships the versioned observer-free tools and tests at public branch work/volume-observer-free @1f2ac5668f9f9a6128da7cce55d4d428bf97589b. All12 Git blobs and remote head verified; checkout clean. Source20/21 epochs, frozen benchmark, native4, archives, reference records, quality limits and performance thresholds stay unchanged. AGPL and all original BSD/notices byte holds preserved. Full13 objective remains active; cybersecurity excluded.

New handoff observes cold/warm geometry, restores pristine parser before exact frozen telemetry construction, checks zero raw calls/unchanged queued command identities in that unsampled gap, wraps warm observation outside frozen telemetry, then restores the exact frozen parse closure at the first counter snapshot after warm retirement. No begin override or geometry callback runs during measurement. Second snapshot verifies identity and invocation count. Mutable ledger cleared, immutable bytes/subclass attributes remain; no claim of pure-frozen interpreter state or absolute zero cache/GC effects. Pinned source/warm payload corroboration plus exact per-paint GL counters constrain original cube work; candidate generic hot-work/byte counters and warm residency unchanged. Full source shape identity checked. New saved/controller gates bind sample leaf, both worker-start/finish24-source maps, explicit verify directory, existing lifecycle/rawsample/statistics/quality/hardware/scientific checks. Retained gap strings never removed.

Independent reviews retain FIX_BEFORE_EXECUTION verdicts. Root resolutions add real frozen release-gate baseline-and-each-gap controls and complete source/command/count/report-hash receipts; no later peer READY claim. cpu6 passes434, public expanded workflow suite858, WSL434 and920-file standalone public-only copy434, all0 skips/failures/errors. All owned CPU/peer/standalone temps removed after terminal waits. Public CI39745217828 is queued at observation, not a matrix/hardware pass.

Actual second collection build/volume-observer-free-pairs-run-root-2/manifest.json efad59e67c369850276218e0d769fc9877bf9d771a1da8f69f5d5fe3740a5152 is FAILED/PARTIAL. It completes5 resident pairs (10workers),15 wholeRGBA checks max1 under2 and10 changedpixel checks. Then2 fullupdate pairs and third upstream verify; third candidate rejected for1 unowned measured paint. All16 actualworkers pass newgeometryhandoff with0 measuredobservercalls, allactualworkers terminal, allownedcwds/twoenvs/cachegone. saved-review4.json a58df87d38e58d6b4c074ea1e4517b9e431ba8bfa0a4066bf53e99ae0cb80671 independently recomputes saved gates/rawsamples/statistics/quality/hardware/digests, preserves failedfullcandidate and verifiescleanup. Overall failed collection is not relabeled complete. Old failed first collection remains unchanged. Resident gate still unproven from scanout/complete driverallocator gaps. Other23volumes/full66/platforms/all13requirements unproven.

Separate private diagnostic traces are explicitly unqualified by additional Qt event observation overhead. Resident trace does not reproduce; fullupdate trace reproduces spontaneous QWindow Expose immediately followed by unowned native QWidget Paint between frames779/780, with no delayed repaint timer scheduled. External platform trigger remains unknown. build/volume-paint-diagnostic-prep-root-1/audit2.json 565c370e03a65bd690e1a72f2182691f2635f6d11028656ec4ab40934a399053 binds3325 eventrows/1000owned+1unowned measured nativepaints and verifies actualterminal/allcleanup. No paint suppression, attribution relabeling or another wholecollection retry.

Fullupdate performance is a separate real engineering gap:2 verified pairs yield median-of-run-medians approx31ms original/116ms candidate, outside unchanged1.10update comparison; these remain unqualified/incomplete observations. Host decode/packing/preparation/submission costs substantial, timer scopes overlap. Read-only advisory Claude plan build/volume-full-upload-plan-root-1 completed0, source pins held andscratchremoved. Published docs/volume-full-update-optimization-plan.md recommends private CPU byte/descriptor/exception/lifetime equivalence prototype first: extract descriptor validation and short-lived engine-owned direct-source view, avoid redundant materialization/rowcopy only for existing direct-format and aligned fulluploads; preserve all conversion/empty/padded/partial fallback paths. No canonical native/upload implementation changed. Later stages need fresh native source epoch, build/wheel/scientific admission, no reused oldquality claims. NEXT: implement/test private CPU prototype, resolve unsolicited expose ownership without skipping rendering or weakening gates, then fresh qualified fullupdate5pairs; scanout/driverallocator/remainingworkload/platform requirements stay open.

Publication receipt build/volume-observer-controls-root-1/publication1.json records exact12files,858/434/434checks, actual16workers and cleanlicenseholds. This checkpoint is private canonical-plan state, not a public performance or release qualification.

Continuation checkpoint104, 2026-10-22: Implemented and pushed the actual
alternating paired-volume controller. Previous goal turn was progress (worker/
geometry adapter and finite diagnostics shipped). Current turn completes first
5pair integration for ONE registered256/1024MIPresident case. Full13requirement
objective, other23volumes/full66/platformmatrix and release remainunproven.

New tools/volume_benchmark_pairs.py owns two fresh hashed-wheel environments,
fixed9dependencyprofile and shared ownedUVcache; fresh externalcwd/process for
each index/role in fixed5alternatingpairs. Minimum100warm1000measured andqueue
depth1..3 unchanged. Explicit workloads orall-workloads selection required.
Request binds sources/controller+selected+basePython executable digests and
controller version, inputplan/science/hardware/wheel hashes; rechecks inputs.
Worker nonce/start+finish actualprocessstamp/launcheredge/reportSHA/runSHA,
raw issued/completed/measured/GPU receipts, perframeCPU totals, rawcounter
snapshots/deltas, latency, originalpacing/nativewholeQtpaintownership/finalGPU
pass maps andallocationwindow revalidated.15wholeRGBA checks and10existing
changedpixel tests fixed; no edge masks/exclusions/tolerance changes.

Lifecycle uses1secondwait slices/monotonicdeadline. Ownedlauncher terminated/
waited ontimeout orinterrupt; actualredirectchild separatelycreation-bound.
Unknownterminal preservescwd/env/cache and writes workspaceglobal
build/volume-benchmark-pairs-unresolved-worker.json; newoutput cannotbypass.
ExplicitoperatorOSproof/resolution required beforeclear. Actual normalrunbelow
created nohold. Launch/process/validation/log digests bound inmanifest.
Interruptidentity retained; no source/native/renderer changes to frozenworker.

Peer FIX_BEFORE_EXECUTION findings F1/2/3 andS1..5 fixed under rootresolution1.
Final346focusedCPU+44WSLchecks bindactualfinalcontroller/testhashes; no later
peerREADY claimed. Actual5managedPython3.10.19/31114/3128/3138/3140 statistics
check exposed ONLYdescriptive stdev1ULP difference on3.10. Controller allows
oneULP ONLYstdev and records recomputedstats; median/p95/count/allotherfields
remainexact. Tests use recomputedbaseline andbothdirections, reject2ULPstdev
andANYmedian/p95drift. No performance threshold relaxed.

Actual build/volume-benchmark-pairs-run-root-1/manifest.json SHA256
ca38a7ce5701acc85eb83fe6aab3f49705091ad09e8946e00db45ebb6341ff5d
collection_status complete/status unqualified. Tenactualworkers,1000warm and
10000measured frames total, all5pairsverified inalternatingorder; all15fullRGBA
comparisons maxerror1 underfixed2, all10changedpixel checks pass. Hardware and
scientificadmission pass. Savedinspector check_saved1.py independentlyreplays
allrawjoins/gates/statistics/countertotals/quality, lifecyclefiledigests, all10
actualworkers waited/terminal, allownedcwds/twoenvs/sharedcachegone.
saved-review1.json SHA25655d452fe4d201b7db652922eeeb6c03a6af6aa0b5fde490a5027fd421ff95259.
Releasegate correctlyunproven from unchanged3gaps: scanout, complete driver/
allocator accounting and unbounded observationeffect. No speedup/releaseclaim.

Portable23filepriorone-run/role diagnostic export (NOTnew5pairproof) under
tests/reference/volume-benchmark-diagnostics, manifestSHA256
d16dfa08fe376215cc421a1e6c22f609ce12d1a3306753652664d60b38cc74c5.
All770CPU pass inpubliccheckout; new44passWSL and906filedeclared-public-only
standalone copy withnobuild/provider/GPU. TempCPU/review/standalone directories
removed onceafterallchildrenwaited. Rawnew5pair/frozen/request/failure/source
proofs preserved. No rejectedcleanup retry or protectedpayload read/cyberwork.

Public branch work/volume-benchmark-pairs pushed/remoteverified at
43d740282cded045fc266c510c7203be72de6789;30Gitblobs verified,cleancheckout.
Receipt build/volume-benchmark-pairs-root-1/publication1.json SHA256
11e17fa2275836de8def9d59f6708b4b057866f7f95db51d1ef65c2f8bebb191.
All5AGPL/originalBSD/notices holds unchanged. No inplaceNative4/archive/source
or existingfrozenbenchmark/fixture changes. CI newexplicitCPUtest whitelist.

NEXT: resolve/bound observationeffect onactualpairedtiming (CPUhookcost isNOT
interactivebiasbound), input-to-visible scanout and complete driver/allocator
peak accounting; preservefixedreleasegates meanwhile. Expand pairedcollection
acrossremaining23volumes andfull66matrix when measurementadmission permits.
OtherABIs/bindings/GPUs/drivers/nativeLinux/Metal/smoothlines andall13original
release requirements remainopen. Nevercompletegoal basedonthisfinitepacket.

Continuation checkpoint103, 2026-10-22: Added and published a versioned volume
timing worker plus saved-run/release gates without modifying frozen benchmark
sources, renderer, native4, archive payloads, scene/update/quality/thresholds.
Previous goal turn was progress (24volume scientific admission packet pushed);
current turn completes the worker/geometry-admission implementation and actual
finite original+Native58 diagnostics, not full performance qualification.

New tools/volume_benchmark_adapter.py and volume_benchmark_geometry.py verify
actual wheel/archive-installed payloads, complete package fingerprint, Python/
NumPy/device/workload/adapter source identity and completed scientific set.
Pass-through parser observation binds actual typed VBO/IBO IDs and original
cold descriptors/offset/payload hashes. Measured original must repeat exactly
96Bvertex+56Bindex cube commands perframe with raw2uploads/152bytes; allraw
counters/time retained. Onlythese two zero requirements get an explicitproof
allowance, allotherGLwork and candidate19resident+2nowait zeros unchanged.

Independent peer FIX_BEFORE_EXECUTION found asymmetric in-window SHA work.
Root fixes defer SHA/JSON untilaftermeasurement, checks nbytes BEFOREcopy,
captures immutabletinybytes, audits per-role CPUcost but doesnotclaim calibration.
Source1 micro medians4.2us/1.2us, Source2repeat6.2us/1.3us; overhead effect on
interactive latency stays explicitgap and adapterrelease gate cannotpass. Pure
originalAST cube+VertexBuffer prep reproduces pinned livepayloads for256/512.
Teardown checks source drift evenonparserrestore errors; complete traceback
and nonzero worker receipt preserved. No new peerREADY claimed; rootresolutions
review-resolution1/2/3.json bindactualfixes andsource/evidence/testreceipts.

Actual firstoriginal100warm1000measure completed2000uploads/152000bytes but
ledger incorrectlycounted onepre-warm expose as measuredunowned work. Keep
build/volume-benchmark-worker-root-1/result.json blocked, SHA256
413bd512df904ec873390f7845e68a18af21820bba02d7cb03573038f2bddcfc.
Independent saved-failure1.json audits all1100exactcubestreams, zero measured
Pythonunattributed calls, actualterminal/removedenv+cache; no reclassification.
Source2 marks measured window at exactfrozen Pythoncounter before/after snapshots
afterwarmretirement/aftermeasuredretirement. Rawwarm/unowned records retained;
onlymeasured delta mustzero and4000exactbuffercommands required. Negative
window test stillrejects anymeasured unowned command. No timinggate weakened.

Fresh original result build/volume-benchmark-worker-root-2/result.json SHA256
b4ea77b477d3c4d568d4bef16149fdbe08275ec945c1e0a0f0766e9ee62c91ac
MEASURED_SINGLE_ORIGINAL_DIAGNOSTIC. All1000measured cubeproofs pass, original
raw2000uploads/152000bytes/4000commands retained, zero measuredunowned andother
forbiddenGL work. Threecaptures exactlymatch pinnedoriginalwholeRGBA frames.
Saved-original2.json recomputes gate/1000sample statistics/quality/receipts.

Fresh candidate result build/volume-benchmark-candidate-root-1/result.json SHA256
d61cc3f26eaf1ee52234e00cfa0a8fcd6469ea7b2a2df0b69610c1fdac0ebc50
MEASURED_SINGLE_CANDIDATE_DIAGNOSTIC. Samepublicadapter asSource2original;100warm
and1000measured, all19resident+2nowait fieldszero, wholeQtpaintownership verified
for1100frames, eventallocationwindow validated; all3capturepairs maxRGBAerror1
underfixed2/noedges. Saved-candidate1.json independentlyrecomputes actualgate,
sample stats, quality andprocess/source/artifact joins. All3actualworkers waited/
terminal, ownedexternalenvs+uvcaches removed. Source1/2/3 seals/snapshots preserved.
No 5pair/24volume/66matrix speedup/release claim. Rawmedians notqualifiedspeedup.

Final all726CPU passmain ANDpubliccheckout; new70CPUpassWSL and880file external
declared-public-only standalone copy withoutbuild/provider/GPU. Allownedpytest/
review/standalone scratch removed afterterminalchildren. Newtests added to
explicitCPUworkflow whitelist. Public branch work/volume-benchmark-adapter pushed
andremoteverified at06f2125464404a2dfed3012c59cbd8940ec11151,6changedGitblobs
verified, cleancheckout. Receipt build/volume-benchmark-adapter-root-1/publication1.json SHA256
4418d757c02c73aa79a5242ae3eb73460b2148c38fe233c07b44b9e8f4976c2c.
AGPL+originalBSD+all5license/notices holds unchanged. No cybersecurity work,
protectedpayload reads, rejectedcleanup retry or inplacenative/source edits.

NEXT: fullfresh-output pairedcontroller using load_admission + finalnonce/
actualprocessstamp/runSHA joins, retained complete samples/captures/hardware,
5alternatingpairs for24volumes thenfull66matrix. Resolve/bound interactive
observer-overhead bias, input-to-visible scanout and complete driver/allocator
peak accounting before anyreleasepass; frozen worker gapsremain and explicit
adapterrelease block stays. OtherABI/binding/provider/GPU/driver/nativeLinux/
Metal/smoothline/MSAA cells and all13originalrelease requirements stayopen.

Continuation checkpoint102, 2026-10-22: All24 large-volume scientific
admissions now bind the actual NumPy2.4.6 small controls to the same exact
Native58 installed artifact/device cell. Previous licensing-only turn made no
implementation progress; this turn revalidated the unfinished producer/output
and completed the scientific admission packet rather than assuming success.

Actual17 unchanged small controls pass exact156672 RGBApixels against pinned
originals, complete installed550file fingerprint matches all24 large cases.
Public raw controls manifest e9f2ef17e59a222372a4588dd5faa639f73beab0a8ad41e6713625864bbd406f;
largecandidate manifest e3f285bcbf97d4a40cb75e031bda9c23abf5fc5d35cf2ad6047c0c8ada9cd576.
New tools/volume_scientific_admission.py recomputes raw small controls and all4
large stages, fullRGBA<=2/noexclusions, repeats/changechecks and source/artifact
identity; includes originalsmall refs/oracle producer sources/runtime/licenses
directly, plus exact historicaldriver as inspection-only driver.py. Small
native execution/package fingerprints are worker-attested; no independent
small native draw/queue-submit counter deltas invented. Raw GLIR DRAW/shaders
required. Completearchive notpartofportablepacket.

Peer FIX_BEFORE_PUBLICATION findings resolved explicitly in
build/volume-admission-prep-root-1/review-resolution1.json; no laterpeerREADY
claimed. OptimizedPython refused, completed output renamed from sibling.pending
onlyafterall24 pass; failpending preserved andreuse refused. Requiredcheckset
maps exactly to verifiedcontrols. Candidatecase/kind/sources and child/launcher
parentPID checked. V1/V2/V3 savedadmissions preserved as historical; V4 stopped
at mistaken launcher=childPID equality beforeanyrecord, empty pending retained.
Current compat/scientific-admissions/volume-native58-cp312-numpy246-v5 generated
successfully; olderoutputs notpublished. No native/src/frozen producer changes.

Final62 tests pass from declaredfile-only standalone copy with nobuild tree;
publiccheckout full656CPU pass (cpu-publication3.xml). WSL62 pass before final
test-only fault-injection isolation fix; notclaimed as finaltesthash Linuxrun.
Priorpublication2 655pass/1fail preserved: deeplynestedWindows temp path hit
frozen schema validator pathlength before intended injectedfailure. Finaltest
isolates transaction fromschema; actual all24v5 producer and complete saved
evidence checks remainreal. Allownedtemps removed afteractualchildrenwaited.

Public branch work/volume-scientific-admissions pushed and remoteverified at
c5910af0bc220593a3007887477176091a053a2d; 878Gitblobs verified,468changedfiles,
cleancheckout. Receipt build/volume-admission-prep-root-1/publication1.json SHA256
e0ecb7e0cf80e1db960224e5681a6d6578c355bec01722ffa8f2dc9ef0e64bfb.
All5AGPL/originalBSD/notices holds unchanged. No protected reads/rejectedcleanup
retry, cybersecurity work, GPUreplay or timingrun in this admission step.

NEXT: implement versioned timing adapter with wholeactualartifact fingerprint
and measurement_identity enforcement plus frozen workload/science/hardware
gates; narrowly attest genuine unchanged original96B VBO+56B IBO repeated
cubegeometry in resident measuredwork without hiding its time/counters or
allowing arbitrary uploads. CandidateResidentZero remainsfixed. Then actual
100warm/1000measure x5alternatingpairs, resident>=1.20/no-worsep95/update<=10%,
presentation/no-wait/full66matrix. V09 staysINCOMPLETE; smoothlines, otherABI/
bindings/nativeLinux/Metal and all13originalrelease requirements remainopen.

Continuation checkpoint101, 2026-10-22: Added full256/512-cubed volume
quality/residency qualification for ALL24 registered benchmark workloads:
1024/2048-square actual physical viewports, MIP/translucent/iso, separate resident
rotation/full-data updates. Uses the actual shared benchmark scene factory,
initial/repeat/probe7/probe73, persistent owned RGBA8/depth FBO, complete-source
hash/byte/shape binding, actual controls/camera/TF samples and mandatory target
clear/draw command ordering. Existing wholeRGBA error<=2/noedges/exclusions and
predeclared >=50percent original changedpixel overlap remain fixed. No timing
speedup/no-wait/long-run memory or completeV09/release claim.

Actual Source3 build/large-volume-wheel-run-root-3/result.json
SHA25604cee47a20e21003faafee6c34c54e70f6cc59b4e43de18c316b8cc0440fb8a8
passes24 fresh originals before24 installed Native58 hardware candidates,4stages
each. Independent saved inspection build/large-volume-prep-root-1/saved-review1.json
SHA256fa67acaff2a72a4ac1f580f8e8a6eb78e4a53e6069437352cef02e7ed1cd79c2
recomputes251658240 pairedfullpixels/1006632960 RGBAbytes, maximumchannelerror1,
zeroexclusions,48 visiblechangechecks, exactunchangedrepeats, staticids/descriptors,
actual controls/opacity maps/sourcehashes, attested originalcubegeometry,
20candidate residentzeros/17fullupdate warmzeros, completeavailable tracking,
same-device/non-growing livegauges and allocation/free conservation,8shutdown
zeros per24candidates,48actualcaseworkers+2parents terminal, both externalenvs/
owneduvcache removed. No providerimport/GPU replay by inspector. Source3 seal
d9e79124ec600c5e95ae4797b4a073214d48c48d102e626b80a955d4e9274973 and21
source snapshots remain. Code/renderer/nativepyd activation unchanged except
shared benchmark setup (no src/native edits); olddata/camera/step/interpolation/
threshold/gamma/clim/update AST preserved aside explicit setup corrections below.

Source1 ALL24 originals fail beforecandidate:8overstrictlegacygeometry gates,
4blanktranslucent controls and12Qt viewportclamps. Official0.17.0 _prepare_draw
neverclears _need_vertex_update; fork alreadyfixesit. Preserve original96-byte
VBO/56-byteIBO repeatedSIZE/DATA onlywith actualtypedinitialids and byteidentical
initialdescriptors/offsets/hashes. Candidate stayszeroresidentwork. Defaultopaque
grays atzeroair makestranslucentblack. BEFOREanycandidate, shared factory declares
Workload.colormap: density-alpha publiclinear(t,t,t,t) ONLYtranslucent, other
currentfamilies/MIP/iso keepgrays. Newfield deliberatelychangesworkloadhashes;
prior admissions cannotbesilentlyreused. Shared prepare_benchmark_canvas warms,
publiclyresizes ifneeded andrequires exactphysicaltarget BEFOREdataallocation.
Real freshofficialwheel surfaceprobe build/large-volume-surface-root-1/result.json
observes2048x1901->2048x2048 bypublicresize, waited/closed/ownedenv/cache removed.
Source2 all24originals+12candidatespass;12othersfalsefailwhenlivegaugesdecrease
byconserved4MiB release. Source3 corrects no-growth signedgauge predicate with
nonnegativealloc/freeevents/exactcount+byteconservation/samedevice, rendering
andpixelcriteria byte-identicaltoSource2. No attribution of freedobjectorigin
claimed. FailedSource1/2raw/status/snapshots andsaved-failure1/2.json remainintact;
allactual48source2workers/24source1workers waited andscratchremoved.

313 unchanged originals export tests/reference/large-volume-opengl, manifest
af7919c6f59dca7addee614a674942697b33d53df3446df0cea422ef980bf2ac; everyfile equals
actualSource3original andactualcandidateparent/24workercommandreceipts bindthis
digest. New24mandatoryGPU pytestnodes requireworkerANDcompleteparent, no skip;
collected24 withoutprovider/GPU; wrappernotseparatelyreplayed (actualdriverproof).
All594combined CPUcontrols passmain ANDpublicationcheckout. Finalpublictestbytes
69353fdc84433cbdda7acb54363ccca61e05383f67821c4736db251c25ef8528 arebound by
cpuPublication1.json594PASS andcpuLinux3.json273PASS. ASTpin test madeportable
acrossPythonASTschemas; fiveactualmanagedparsers31019/31114/3128/3138/3140
reproduceoriginal/normalizedhash46292b578c6083d6d3b0b8b4f9b0c8039fc1f66641e9a1e8574afef1f2071d88
withoutproviderimport. Currentfactorynormalization permits ONLYhook, explicit
viewportpreparation andcolormapdeclaration; data/camera/update AST stayspinned.
338file externalNObuildmaterialization loads24refs/17sources/actualparentgate/
pytestentry withoutprovider/GPU andremovesscratch. Finalportability2 usesfinaldocs.

Finalpeerreview2 supports code/tests/evidence, butrequests exactfinalCPUtestreceipt
whichwasstillrunningwhenrequestsent; actualpublic594 receipt finishesandbindsall
finaltestbytes. Rootresolution4 joinsit, portable338filehashmap andlaterLinux273;
resolveswording: livegaugesconserved withnoobjectattribution, freshoutputrequired.
No additionalpeerREADYclaimed; rootCLEAR_FOR_PUBLICATION is explicit. CPUCI adds
41newcontrols+27immutable-referencecontrols+232existingbenchmarkmetrics to294=594,
unchanged20matrixrows. V09 nowINCOMPLETE (quality/residencycomponentpassed inone
Native58cp312/Windows/Python3128/NumPy246/PyQt6/RTX4090/61088cell), notcomplete.
Bounded supplement build/reports/scientific-fixture-coverage-native58-large-volume.json;
historical185/39aggregate andotherrowstatesunchanged. All5AGPL/originalBSDholds
unchanged; no native/src/protected/heldout access, rejectedcleanupretry orcyberwork.

Public work/large-volume-regressions pushed at
980279cf671517ab36f9b64f9e5cf47d7ddd71fb, parent5c102406bcc178d0966699559896eb93eb58705e.
338Gitblobs verified,323changedfiles, cleanHEAD/origin/liveremote agree. Receipt
build/large-volume-prep-root-1/publication1.json
SHA256f9ed7df3479eeb89a37a940a5a912a41b141eb7a57b1e43d2f6738872195b776
bindsruntime/failedlineage/setup/CPU/reviews/rootresolutions/portability/cleanup/
5licenses/remote/provenance. New594CI39721750439 has8running/12queued atobservation;
prior294CI39713010083 has12success/8queued, no failures. Do notrestart/canceljobs
becauseanobservationexpires. No currentlive localprocess/session fromthispacket.

Next necessary work: bind existing independent categorical/depth/clipping/numeric
smallcontrols toall24 benchmark-specificscientificadmissions; correct measurement
admission for the attested genuine originalcubegeometrywork (do NOTpatch/remove
upstreamcost orblindlyignore arbitrarybufferuploads), then actual100warmup/1000
measuredframes in5alternatingpairs/full66workload performance. Wholebenchmark
source isbound by immutablelarge-volume references: futuremeasurement edits need
an explicit versioned adapter orfreshsource/reference epoch, never loosenpins.
Performance target>=1.20residentmedian/no worsep95/update<=10percentregression
andalloriginal13requirements remain. Exactportable smooth/MSAA, physicalQt/
binding/ABI/nativeLinux/Metal, broaderhost/science, faults/ownership/caps/budgets,
presentation/artifact/release gates stillopen. Full goal remainsactive.

Continuation checkpoint100, 2026-10-21: Closed the full4096 image quality and
camera-residency gap for one explicit Windows hardware cell. New independent
fixture uses full4096 float32 scalar/uint8 RGBA fields, nearest/linear, each with
baseline/repeat/integer public camera pan(-13,17)/return. One persistent RGBA8
FBO/image survives all stages. Every original finishes before any candidate.
Preregistered analytic scalarRGB<=1/RGBA0/alpha0 and exact fullRGBA original
comparison stay unchanged; no pixels excluded and deliberate readback waits
never count as no-wait/performance evidence.

Actual Source4 pair build/large-image-wheel-run-root-4/result.json
SHA2563ab78ee3cade212f63f3ca7c4695ac5f796dcadeb24431728989f343efda6ed2
passes all4 original and4 candidate cases/all4 stages. Independent saved inspector
build/large-image-prep-root-1/saved-review1.json
SHA256b1e9c1753f20c44bc32cb2bc1bfdf0102469e15131d07a8464f01b5488278276
recomputes268435456 exact paired whole-frame pixels/1073741824 RGBA bytes,
analytic controls, repeat/return equalbaseline/pan differs, stable texture/FBO ids,
actual owned-target draws after CURRENT,20 resident-zero counters on all12 later
candidate stages, positive draws/queue work,8 shutdown zeros per candidate,
8 actual caseworker/2 parent waits and removed environments/cache. No provider
import/GPU replay by saved checker. Source4 seal32d54700c1fd4cd7abca02223d408f0bf53f2b46238049c7e6f4323b67843dd6
and17 source snapshots retained; later docs do not alter preregistration.

Prior failed Source1/2/3 roots and saved-failure1/2/3.json remain intact. Each
blocks candidates and verifies all actual workers terminal and owned scratch
removed. Fixes address NumPy Rect JSON scalars, explicit public TransformSystem
mapping (small logical canvas vs actual4k target), and GLIR CURRENT restoring
defaultFBO before repeat. The same FBO is now reactivated eachdraw; a new
command-order gate rejects draw on wrong/unbound target. Two pre-execution peer
reviews and root resolutions are explicit: first inaccurate SHADERS claim is
rejected by official program.py DATA source; second real defaultborder issue is
resolved by zero explicit border/margin/padding and complete layout assertions.
Final peer review3 accepts code/tests/evidence and requests documentation-only
scope/provenance/typography corrections; root resolution6 verifies those edits,
all53 exported original files equal actualrun and candidateparent/all4 worker
command receipts bind the same original manifest. No false peer READY claimed.

53 unchanged original files export to tests/reference/large-image-opengl,
manifestace47caea32759727170debd5a08db2c3255b29296873090290f12a12670c4d2.
New4 mandatory GPU pytest nodes require worker AND complete parent, no skip;
collect4 without graphics, not separately replayed. All294 combined CPU controls
pass from main AND public checkout,52 focused controls pass on WSL Linux.
73-file external no-build materialization loads all4refs/13 runtime sources/
actual parent gate/pytest entry without provider/GPU import and removes scratch.
CPU CI adds52 controls (242->294) on unchanged20-row matrix. I09 catalogue and
bounded supplement build/reports/scientific-fixture-coverage-native58-large-image.json
record only Native58cp312 vs officialVisPy0.17/PyQt6 OpenGL, WindowsCPython3.12.8,
NumPy2.4.6, NVIDIA RTX4090/610.88. Other ABI/binding/provider/GPU/driver,
fractional interpolation/zoom, performance/no-wait/long-run memory, native Linux,
Metal and all remaining release requirements are explicitly unqualified.
Historical185/39 aggregate and other catalogue rows stay unchanged.

Public work/large-image-regressions pushed at
5c102406bcc178d0966699559896eb93eb58705e, parent311f2268d426ae836279f11876a979e19be2b3cf.
73 Gitblobs verified,62 changedfiles, clean HEAD/origin/live remote match. Receipt
build/large-image-prep-root-1/publication1.json
SHA256921138a3e927c93bd7b6d386f840ab4077d5a11a9cc657ab8687582b852aaf89
binds runtime/CPU/portability/failedlineage/review/resolutions/cleanup/remote/5
unchanged AGPL+originalBSD licensing holds. No native/src edits or payload
activation; no protected/heldout access, rejected cleanup retries or cyber work.
New294-control CI39713010083 has5 running/15queued at observation; previous242
CI39708464187 has12success/8queued, no failures. Do not restart live/queued jobs.

Next useful unfinished work is V09 full256/512 volume quality/control and
residency/performance qualification, followed by other genuine outstanding
scientific/host/platform/performance gates. Preserve all original13 requirements,
including exact portable smooth lines/MSAA, physical Qt/binding/ABI/nativeLinux/
Metal, full66 workload performance/presentation, fault/ownership/error/resource
contracts and release gates. Full objective remains active, not complete.

Continuation checkpoint99, 2026-10-21: Extended RGB/RGBA scientific qualification
to the existing audited Linux Native58 artifact, without rebuilding the already
successful five-ABI basic Linux wheel consumers. Separate Linux adapter preserves
the Windows source/reference bytes and exact24-case fixture/quality gates. New
nine-package Linux closure keeps the Windows versions (NumPy2.4.6/PyQt6), with
platform-appropriate hashes. Six actual Mesa/LLVM inputs are pinned. Source1
review rejects mapped-driver/environment gaps before graphics; Source2 requires
actual pinned driver images, software identities, full relevant environment and
owned Xvfb lifecycle.74 controls pass on both Windows and Linux.

The first actual Source2 launch fails before any scene because WSLg's shared
/tmp/.X11-unix is read-only. Failed result e9eec8b0bbf8d14296eb9595cfdbeac21c247b93c9ed38fce68e09fdaea8c4ce
and saved-startup-failure1.json preserve empty stages, terminal Xvfb/driver and
removed scratch. No shared mount or previous evidence is modified. Source3 uses
the same pinned Xvfb with previously successful abstract-local transport flags,
DPI96 and a SO_PEERCRED check matching the owned server PID/UID before scenes.
Read-only review admits this transport-only fix; actual source snapshots remain.

Actual Source3 result build/color-volume-linux-run-root-2/result.json
SHA2562393755bac66ae1fb3e7ac48cc95739ec325d4a1692c7866dcbbc1cb6ab8b12c
passes all24 fresh Linux OpenGL originals before all24 Vulkan CPU llvmpipe
candidates. Independent saved inspection
build/color-volume-linux-prep-root-1/saved-review1.json
SHA256361ecd9e6456f466829c03e9dbacf0dabf80417bb31d788a7621368c959932da
recomputes221184 exact final and36864 before-frame pixels, all RGBA/parameters,
opacity/analytic plane controls,48 actual case workers/two parent suites,
archive/native origins, mapped pinned drivers, explicit submit layer ALL24,
positive native work/eight zeros and removed environments/cache. The owned
abstract endpoint matches Xvfb, alive through capture then stopped and waited.
This is software-only on WSL/glibc2.39/CPython3.12.8/Mesa25.2.8/LLVM20, not
native Linux hardware, Metal or all-volume/platform/release qualification.

149 unchanged originals export to tests/reference/color-volume-linux-opengl,
manifest971d48cee245e2551e27261052d09a04d83988864ebbb6393c292f5175dfe925.
New24-case Linux pytest entry point enforces the worker AND complete parent
status, no errors/missing results, opacity and the exact software profile. Its
parent gate is AST-held to the already CPU-tested Windows gate and passes the
real saved Linux parent without replay. All242 combined publication CPU controls
pass (217+25),24 graphics nodes collect, and76 focused controls also pass on Linux.
165-file external no-build materialization loads every reference/11 runtime
sources and parent gate without VisPy/GPU/driver-file access; owned scratch is
removed. A first publication harness accidentally omits source bodies and fails
metadata writing; its summary-only review is NOT admitted. Corrected request
includes/checks18 exact source/proof files; review5 is READY_FOR_PUBLICATION.

V08 catalogue now records the Windows hardware and WSL software cells separately;
new supplement build/reports/scientific-fixture-coverage-native58-color-volume-linux-software.json
keeps all wider requirements and the historical185/39 aggregate unchanged. CPU
CI adds the25 controls to the same20 rows; the explicit software graphics entry
point is not claimed as automatic hardware coverage. No native/src, protected,
heldout or original license bytes change; AGPL and original BSD remain attached.

Public work/linux-color-volume-regressions is pushed at
311f2268d426ae836279f11876a979e19be2b3cf, matches origin and is clean.165 Git
blobs verified;157 changed files. Receipt
build/color-volume-linux-prep-root-1/publication1.json
SHA256f35c1d87751d91b4a7740e40c848ff77e1781a04c38468e0ea1f63f6a06b4c6f
binds all source/failed-lineage/runtime/CPU/review/portability/cleanup/native-license
continuity and actual remote state. New242-control run39708464187 is queued.
Prior217-control run39703288703 has12 successes,8 queued,0 running/failures at
this observation. All original unverified requirements remain open, including
smooth lines/MSAA, physical Qt/bindings/native Linux/Metal, broader host/science,
4096 image quality/residency,256/512volume quality/performance and release gates.
Next meaningful work can close the named4096-image gap or another actual missing
scientific/lifecycle requirement; do not rebuild the unchanged Linux58 baseline
or repeat refused smooth formula families solely because prior handles ended.
Native source changes still require fresh matching build/qualification.

Continuation checkpoint98, 2026-10-21: Implemented and published the missing
RGB/RGBA public volume regression packet.24 fixed cases cover all seven exposed
methods in both color forms, RGBA opacity, plane/linear sampling, color updates
and both channel-count transitions. The original wheel's actual RGB luminance,
color bypass and camera transforms derive the controls before capture. Source1
is refused before GPU; Source2's first24 originals all fail missing optional
PyOpenGL. That failure and all closure/origin/cleanup evidence are retained, with
no candidate. Source3 selects the already-pinned PyOpenGL3.1.10 block, keeping
all scientific inputs/criteria unchanged, and passes read-only source review.

Actual Source3 pair passes all24 fresh originals before all24 installed Native58
candidates on Windows CPython3.12.8/NumPy2.4.6/NVIDIA RTX4090. Saved inspection
build/color-volume-wheel-prep-root-1/saved-review1.json
SHA2562825acf6135a718ee960074af3d3dca71612d75680d2d3d80fe31f376fc436bc
rechecks exact221184 final pixels plus36864 before-frame pixels, all RGBA,
analytic plane/opacity controls, wheel payloads (only installer RECORD excluded),
actual48 workers/two parent suites, origins, positive work, eight shutdown zeros
and removed environments/cache. Result e2941b9d7e9f896b6e8600a3d082f9ff111b348924c50410fd036098b8bdd346.
No renderer/native source, native4, heldout/protected payload or old reference is
changed. It uses the archived exact Native58 wheel, not a new native build.

149 original files export unchanged with manifest
c8af8d76e1ecdaac1e21303a47ba75a7cce83cb269085a230e89cf0f127c4337.
The new24-case pytest entry point keeps every case required. Publication review4
catches its ignored parent return/status; the fix enforces complete parent,
opacity, no-error and no-missing-results gates in every node. Six CPU controls
prove those failures cannot hide behind passing workers. The entry point also
requires its admitted Windows CPython3.12.8 cell. All217 publication CPU controls
pass (166 prior+51 new),24 GPU nodes collect, and the new parent gate passes
against the real saved candidate manifest without a GPU replay. Explicit no-build
external materialization verifies all24 references and10 runtime sources/nine
locked packages; fresh scratch is removed. Final review5 is READY_FOR_PUBLICATION.

Scientific catalogue row V08 is now bounded pass, with a machine supplement at
build/reports/scientific-fixture-coverage-native58-color-volume.json. It does not
recompute the historical185/39 aggregate or qualify full volume/platform/release
scope. The CPU workflow adds the51 controls in the same20 rows. The GPU entry
point is explicit, not claimed as automatically covered by all-platform CI.
AGPL implementation and original BSD/license attachments remain byte-exact.

Public work/color-volume-regressions is pushed at
cdefd2166cf3279b15ba11a77af53ed622faa2ab, matches origin and is clean;165 committed
blobs checked,157 changed files. Publication receipt
build/color-volume-wheel-prep-root-1/publication1.json
SHA2565aad4e5656546681e419a4d1e88f4bd35164a7420f1abbebea0b753968d7b319
binds source/GPU/failed-lineage/CPU/review/portability/catalogue/license/native
continuity and actual remote state. New217-control run39703288703 is queued.
Earlier166-control run39698950323 has11 successes,2 running,7 queued and no
failures at this observation. Required smooth-line/plugin failures, remaining
scientific controls/host/physical Qt/ABI/platform/performance and all original
unverified release requirements remain open. Do not repeat the refused smooth
arithmetic path or relabel this finite color-volume pass as full completion.

Continuation checkpoint97, 2026-10-21: Closed the concrete GPU arithmetic
measurement blind spot without weakening smooth-line parity. A new runtime-
uniform shader diagnostic and23 CPU controls check exact byte transport,
training-only directions and malformed/unstable sequences. Source4 executes
2068 exhaustive identity controls plus288 arithmetic/reverse observations on the
installed archived Native58 wheel, NVIDIA RTX4090 Vulkan. All2356 readbacks
and reverse repeats pass. Actual native work and550 wheel members/origins are
verified; worker is terminal, eight shutdown counters zero, new environment and
cache removed. Source1 failed preflight before GPU; all review/fix lineage stays.

The measured normal for(-9,-36), bits(3f785b42,be785b42), lies inside the
already refused nine-pair neighborhood. This rejects the specific explanation
that actual shader inverse-sqrt product bits escaped earlier CPU support. No
new interval sweep/model/renderer/native/line-reference/holdout operation follows.
Saved independent inspection
build/smooth-shader-arithmetic-prep-root-1/saved-review1.json
SHA25606fb1da1e7c4352cc3df39d7f033d2465c839ab5050e4873773255eb3f80894c
rechecks all2356 bytes and source/process/device/cleanup/comparison joins. Frozen
Source4 inputs remain available under that prep's source4 snapshot. Detailed
method, review naming resolution and limitations are in the mechanism plan.

The latest public host wiring remains be0c9803a9f0d1fc30238bf1ebf076335b06b213;
CPU run39698950323 is still observed queued. Four plugin smooth-line failures
remain mandatory. Exact portable smooth lines and every other unverified original
release requirement remain open. AGPL implementation and original BSD/license
notices remain attached unchanged. Next work must use a distinct derived
mechanism or another original release gap, not repeat rejected formula families.

Continuation checkpoint96, 2026-10-21: Published the napari-threedee upstream-only
Windows CPython3.12.8/PyQt6 host admission and required CI preparation. The static
hash-locked closure installs in a fresh external environment using portable
repository-relative plugin/asciitree wheels. Actual provenance verifies the
original VisPy members and genuine plugin files; no graphics run is inferred
from this environment check. The separate admission manifest binds existing
unchanged original frames, parameters, GLIR, shaders and before-frames. The
qualification gate admits only that upstream fixture/environment cell.

Ten focused preparation/admission controls and all166 combined publication CPU
controls pass with zero failures/errors/skips. Reviewed publication changes only
eight files; AGPL and original BSD notices retain their exact bytes. Existing
native4 remain unchanged. Fresh CPU/install/review scratch is removed. The five
required candidate GPU cases are retained: retirement passed in the saved paired
run, while handles/selection/translation/miss still fail on generated smooth
lines. Candidate, complete host and release qualification remain false.

Public work/napari-plugin-host-admission is pushed at
be0c9803a9f0d1fc30238bf1ebf076335b06b213, matches origin and is clean. Receipt
build/napari-plugin-host-admission-prep-root-1/publication1.json
SHA256eae6657af4f2bd9b27e0151dea54106a06b4ff0dc5e6ba901a8c5cb2e204aa9f
binds the exact eight committed blobs, reviewed source, installation, admission,
preparation and166-control results. CPU run39698950323 is observed queued;
this is not a platform GPU result. All original13 release requirements remain
in scope. Return next to the unresolved portable smooth-line mechanism, with
no approximate or NVIDIA-only substitute and no protected/heldout access.

Continuation checkpoint95, 2026-10-21: Published the self-contained installed-wheel
napari-threedee overlay/event/retirement suite without weakening its four required
smooth-line failures. The exact plugin/asciitree wheels, source archive, original
build proof/script and unchanged upstream license texts are a124284-byte input
bundle under tests/reference/napari-plugin-wheel-inputs. Manifest
da2dfaa21a2882f7bb04f98975f6e5c19ee40cdcad573232f3a03ea9c0452a36
binds all seven artifacts and their original observed source/inspection. Ten
original provenance inputs and the paired host closure are included unchanged
under compat/host-environments. There is no runtime source dependency on build/.

The original provenance checker temporarily selects the same genuine plugin
wheel from the portable bundle and restores its prior binding on both success
and failure. Explicit asciitree0.3.3 verification adds a condition; no package
version, host/plugin code, fixture, reference or scientific threshold changes.
Three new bundle/restoration controls extend the focused suite to22/22. Source5
freezes69 inputs with those passing controls and all five GPU nodes collected.
Restricted source review80f825e3b46b997199a46f60b9fabc36b935f238db632c73eb98bc910d917f02
admits the repeat from the portable snapshot. Actual parent6 result
build/napari-plugin-wheel-run-root-6/result.json,
SHA2565c9ea080eafa92fd9442b8704b5f12e809bc9e563a2653400c877721788c2432,
has the same complete original/candidate outcomes as Source4: all five original
frames and before-frames/parameters exact; retirement exact49152 candidate pixels;
handles/selection/translation/miss remain genuine generated smooth-line refusals.
Pytest is1pass/4fail/0errors/0skips, never xfail or dropped coverage.

Independent saved inspection712bef63a385b25cc2710d0b21c9432f13d09f456eda0d1803831183cfee78e1
rechecks full source/artifact/native/package/interpreter/state/frame/worker/cleanup
joins and confirms all12 actual workers used the portable plugin wheel while
both original private artifact locations were absent. All workers are terminal,
both new environments removed, every candidate has zero windows/eight shutdown
zeros, and retirement has positive actual native work. No platform/host-cell or
release qualification follows the one-of-five result.

Publication materializes all64 exact staged Git blobs into a fresh external tree
with NO build/ directory or original default wheel, validates all34 runtime sources
and generates the exact pinned runtime closure. This closes the non-stub portability
gap; owned scratch is removed. All156 combined publication CPU controls pass,
including22 new plugin controls, with no failures/errors/skips. The unchanged20-row
CPU matrix gains that contract file; required GPU nodes remain under tests/hosts.
Final independent review72270cef483061a3d35a9af2ad13adf6cdf034fb3875429e767717babff4aed0
is READY_FOR_PUBLICATION. Original VisPy BSD, AGPL and dependency license texts,
the original oracle and native4 retain their exact bytes. No src/ or cpp/ changes,
rejected cleanup retry or protected/heldout access occurs.

Public work/napari-plugin-wheel is pushed at
7c801172ed3e2bd04bf6d1babcb9b3e555888eb9, matches origin and is clean. Its26
changes include only curated test/provenance inputs, helper/tests/docs and the CPU
selection; no environment or build-cache directory is added. Receipt
build/napari-plugin-wheel-prep-root-1/publication1.json,
SHA2563472b904a12ab15732d66d7aa8b316cf55be7a0a785f64e643935eb4348a4ad7,
binds publication/reviews/CPU/portability/GPU/cleanup/native/license joins and actual
remote state. New156-control run39697011056 is queued. Older volume39675704330
and Glue39681785535 have18 successes each; Glue-admission39689331415 has13 and
phylib134-control run39690827417 has12, all queued without reported failures.
Phylib's separate Ubuntu import job39690827515 remains terminal SUCCESS. No hardware
workflow is dispatched. Formal upstream plugin-cell wiring, general smooth lines,
wider host/plugin lifecycle/platform/performance and the full original thirteen-step
release scope remain incomplete. Do not substitute the passing retirement case
for the other four workflows or relax any original gate; cybersecurity excluded.

Continuation checkpoint94, 2026-10-21: Remote Ubuntu phylib import job39690827515
is terminal SUCCESS. Its actual Ubuntu24.04 runner job119536295959 and uploaded
artifact12388434470 are inspected: all12 original modules pass with no VisPy/Qt
imports, exact source/package identity and CPU-only flags. The selected real
import/admission receipts and untouched artifact zip are retained under
build/phylib-linux-admission-prep-root-1/remote-ubuntu-root-1. Result
906f2d6269fb54339d6d806c627c777e60324c1a30444efb1990270304d646ab
proves remote Ubuntu CPU imports, distinct from WSL and any graphics admission.

Implemented canonical WIP tools/napari_plugin_wheel_suite.py,19 contract controls
and five mandatory installed-wheel GPU nodes for the existing unchanged plugin
overlay/event/retirement fixture. It uses genuine plugin wheelde115619..., the
previous paired NumPy2.4.6 closure, original wheelc4862155... and archived Native58
candidate105698c7..., with fresh external environments. Every fresh original must
reproduce retained original b4a118f6320af8f8d12010948ff00964fe5966f967003ab40cb887af37ddc77e
frames/parameters/before-frames before any candidate. Positive candidate work,
installed/native origins, real Qt/callback states, actual nonce/PID/creation/terminal
joins and failed-case zero cleanup remain mandatory. No new native renderer build
or refreshed whole-source native identity is claimed.

Independent source review catches -I ignoring PYTHONHASHSEED and the shared
sanitizer dropping the original context-sharing flag before graphics. Corrected
workers use sanitized -s -B environments and record/verify effective hash flag0,
seed0, disabled user-site/bytecode and context sharing true before VisPy imports.
The two actual interpreter controls prove the honored/ignored seed distinction.
Source2's two failed alias tests and Source1's refused review are retained; neither
runs graphics. Corrected Source3 passes18 controls. Parent3 stops before launching
providers on an absolute Reader path; independently reviewed parent4 converts it
to canonical in-root relative form with the same byte pin. Its first setup fails
on source-only asciitree0.3.3; both actual setup children finish and that owner is
removed, without graphics or candidate work.

Pinned asciitree sdist4aa4b9b649f85e3fcb343363d97564aa1fb62e249677f2e18a96765145cc0f6e
is built using existing hashed setuptools80.9.0/wheel0.45.1 and fixed source epoch.
Every package and original license file matches source bytes. Result wheel
d3c865c2cea5e56b52c090526c3ea87287356eaa7f8f4d78d4a872ca1c4cef10
provides the same0.3.3 dependency to both original and candidate, keeping all
versions and binary-only/hash-required installation. Build proof
0bc6baf52513bd45988d93b0bf6a5cb62ae49e4107aebfc98b43b92c894e440e
retains all three actual child waits and removed build owner/cache.

Source4 freezes65 exact inputs and passes19 controls plus five-node collection.
Review024269a44bc9cc72f1ac15cd8a18c38644a464d5135d7684697a0e0a3e8ec5ca
admits actual parent5. Run build/napari-plugin-wheel-run-root-5/result.json,
SHA256b211cdc995647ecc8f563465f628b042d6fb697431448e475ee1bba228eb1866,
closes with all five original frames exact (245760 final pixels plus147456
before-event pixels and all parameters). Candidate retirement matches49152 pixels
and all Qt/callback state with positive native work. Handles/selection/translation/
miss each refuse the known generated smooth-line consumer at DRAW42. Pytest is
one pass/four failures/zero errors/zero skips. No failing case is removed or xfailed.

Complete independent saved inspectionc2badba32da687f0acc19e49f6b4e53cc4a01a774b8a0eee8f4681f5645fd5e9
verifies full artifact namespaces, all source/plugin/native/image/state/interpreter
joins and all12 actual worker closures. Both new environments are removed; every
candidate has zero visible windows and eight zero shutdown counters. Continuity
760b8272fb53f04ab66e672426e459a4e843d3d4b676fdfe922b716da92198ce
holds native4, attached AGPL/original BSD texts and original oracle exact; all new
CPU/review/build/runtime scratch is removed. Useful frozen/raw/negative evidence
remains; rejected cleanup targets and protected/heldout payloads are untouched.

The new plugin suite remains canonical WIP, not public host admission or a release
pass. Next package the exact wheel/dependency/provenance inputs portably and publish
the mandatory suite with this failed scope. Public checkout stays clean at26605edee
on work/phylib-linux-import. Older CPU runs remain queued without failures:
volume39675704330 has17 successes, Glue39681785535 has16, Glue-admission39689331415
has12 and current134-control run39690827417 has9. All original release scope and
smooth-line/wider plugin/platform/performance work remain incomplete; cybersecurity
excluded.

Continuation checkpoint93, 2026-10-21: Closed the Linux phylib CPU import-only
admission gap with a real WSL Linux x86_64/CPython3.12.8 run. This is the phylib
library, separate from the phy GUI, and grants no X11/Vulkan/Metal/rendering or
release admission. A Linux binary dependency lock uses the existing Windows
version constraints and2026-10-09 cutoff. The source/package pins remain exact.

New tools/phylib_import_cell.py checks the entire pinned upstream source and
package trees before copying unchanged source into an isolated dependency venv,
then verifies all12 original imports, package version/bytes, isolated origins,
zero errors and no loaded VisPy/Qt modules. It creates no distribution metadata.
Ten source controls pass before independent restricted source review
ef9b0efcde23ccbfb87f920d42ce46d2d00b6637ea1df9957174b0a4b6011fe3
admits the import study. The frozen16-file driver creates a fresh external Linux
owner/cache, installs20 hash-locked binary dependency packages and runs the exact
isolated imports. All three actual children exit0 and are waited on; the owned
environment/cache is removed once. Actual result
build/phylib-linux-admission-prep-root-1/linux-1/result.json,
SHA2564f89369058913352adb88a576c2c91d61686632fa8712b103eba637f2a55fcb0.

Independent Linux saved inspection4f9d8d6585225182477bef9ba3ef7000c1393cde4ef6f5d15674544e7066f318
verifies every source/log/tool seal, the pinned source archive/tree, actual owner
absence and all12 loaded module hashes joined to original source. Import inventory
2ffdc4197ee272f549a9bcf1d4690e096d7fa7f7a3544ecf7bf751d29a951fe4
is attached unchanged alongside the Linux lock7c58e59c2847b790faf8420436960c54fba0123a5fa1889e52020ac7581de406.
Formal compat/qualifications/phylib/linux-x11/3.12.8/none/admission.json,
SHA25661f454bed71d7355f98ee8ec38e05d02b64e4a41f5338e5f40c8355e0fd4c422,
passes the strengthened existing gate. The linux-x11 path follows existing matrix
naming only; its scope explicitly excludes display/graphics qualification.

Only phylib.linux_environment is added to the host lock; all previous parsed host
data remains unchanged. The existing phylib job is factored into reusable
.github/workflows/phylib-import.yml, automatically triggered by relevant inputs.
The manual host matrix calls that same CPU job; its renderer matrix is byte-exact.
It now fetches and verifies pinned source and probes imports rather than requesting
distribution metadata never installed by the dependency-only lock. Eleven focused
controls and the full publication134-control suite pass with no failures/errors/
skips. All20 CPU matrix rows retain their scope and gain the11 controls. Independent
publication review03eb0da41ab33816c0d86c73cbc900b6f3f4f24840be689f2dbfac7ac577d2a8
is READY_FOR_PUBLICATION. YAMLs and canonical/public admission commands pass.

Ignored metadata discovery is resolved by adding only the exact required files:
the three new Linux artifacts plus four unchanged original phylib constraint/source/
Windows-inventory files. Supporting-pin audit77c9d3f249fcd2d94999a61095630e24f0f23da54eb316c1a36e40b53eac03a2
matches all original lock hashes and CPU-only flags. This makes the recorded lock
generation inputs and retained Windows/source metadata available from Git as well
as the local workspace. Local incomplete draft commits are amended before any
push. Final16 committed blobs all match the copy manifest; no ignored tree is added
wholesale and no new Windows qualification is claimed.

Public work/phylib-linux-import is pushed at
26605edee523e12b25fd8b79926552a2daf50567, matches origin and has a clean checkout.
Receipt build/phylib-linux-admission-prep-root-1/publication1.json,
SHA2564ac9d01ba03ae9d3de09f6918a6f9fc72a2ae048b7730583bafe414cbda10aad,
records exact source/proof/review/admission/remote joins, native4 and both license
holds, all new CPU/review/Linux scratch removed, and no hardware dispatch.
Dedicated Ubuntu import run39690827515 and full CPU run39690827417 are queued.
Older volume39675704330 has17 successes, Glue39681785535 has12 and Glue-admission
39689331415 has1, all queued without reported failures. Do not infer remote Ubuntu
success from WSL success. Smooth lines, wider host lifecycle/scientific/platform/
performance and all original release requirements remain in scope and incomplete;
cybersecurity excluded. No protected/heldout or rejected cleanup target is touched.

Continuation checkpoint92, 2026-10-21: Primary Vulkan/NVIDIA sources do not
specify a bit-exact smooth-line setup that explains the retained observations;
the mechanism plan records links and the limited inference. No further arbitrary
formula sweep or renderer approximation follows. Work instead closes the separate
upstream Glue fixture/environment admission gap for the observed Windows
CPython3.12.8/PyQt6/NVIDIA RTX4090 cell.

The exporter re-verifies the pinned Source3 snapshot and entire saved upstream
packet with its original saved verifier, checks the real3.12.8 interpreter, and
copies20 original RGBA/GLIR/shader/parameter artifacts unchanged to
tests/reference/glue-cache-update-opengl. New manifest
f94a245c2f4607b2ad6b2c9962363ee4793174e95173472a8b0eb9e99e0c2405
binds all five successful original scenes and exact128x128 full-frame criteria.
The old glue-opengl manifest1df82c2886606f864afcff7ec055451dd0d46fe0377e2ca1bc1423cab604080b
and its failed volume_edit remain unchanged. Initial exporter1 stops at a
historical metadata-field mismatch before creating output; corrected exporter2
completes without rewriting any previous reference.

Formal admission compat/qualifications/glue_vispy_viewers/windows/3.12.8/pyqt6/admission.json,
SHA25600b4bc20dfd621bfb83238fa63a253e5c460ff60ded4fcd861a0d5b3ace5bc2b,
passes the existing qualification_gate admission command. New
tools/prepare_glue_host_cell.py and the native host workflow supply only the
hash-locked original wheel, fresh pair evidence path and exact current Python.
The candidate remains the job's actual built wheel. Existing parity tests still
capture and verify all five fresh originals before every candidate workflow;
scatter_axes remains a mandatory genuine candidate failure. Every other missing
host admission remains a failure. No new graphics run or hardware qualification
is claimed; the formal admission covers upstream fixtures/environment only.

All21 focused CPU controls pass, including9 new preparation/reference-join cases.
Independent restricted review41ceecdb725b6bbeb6909288cacfbde91feaf6732a9af05817eed8ab26f5d5c1
is READY_FOR_PUBLICATION. Both workflow YAMLs parse; local admission/preparation
using the actual locked wheel pass. The complete publication suite passes123
controls with no errors/failures/skips and new scratch removed. CPU workflow now
includes all123 controls in every unchanged20-row matrix. Canonical CPU YAML
also receives the previously published scientific-test block; no public scope is
removed. All AGPL/original BSD copies and native4 retain their exact hashes.

Public branch work/glue-host-admission is pushed at
047c601e4682e1b84b1abfa45cb6103672bbd26b and matches origin with a clean checkout.
Publication receipt build/glue-host-admission-prep-root-1/publication1.json,
SHA25616497caaf4bfcf913f72d023b205d75419ad2c3fb3784674519a47bda43124a0,
records27 byte-matched files, review/CPU/export/admission/preparation evidence,
license/native holds and actual remote state. New CPU run39689331415 is queued;
volume39675704330 has15 successes and Glue39681785535 has11, both queued with
no failures. Prior mesh/image run39673954150 is terminal20/20 success. No hardware
workflow is dispatched. No protected/heldout data, new geometry, native mutation
or rejected cleanup retry occurs. Full original thirteen-step release scope,
smooth lines, wider host lifecycle/platform/performance work remain incomplete;
cybersecurity stays excluded.

Continuation checkpoint91, 2026-10-21: Implemented a CPU research helper for
coverage attributes interpolated through rounded rectangle triangles. Gradients
derive from vertex-difference determinants with declared32/64 setup and explicit
binary32 transport; both diagonals use exact dyadic integer orientation, including
subnormal corner offsets. The19 new affine/winding/attribute/diagonal/domain/
full-vs-selected/axial controls and69 prior exact arithmetic controls pass88/88.
No new Probe geometry is introduced beyond the three already excluded synthetic
controls. Shipping renderer and native binaries remain unchanged.

Restricted independent source review842f27af00aaeea033bdf10fc646955eff89b62b630ea1d0144835ea44af0986
admits the bounded study. It freezes22 files including the actual Source10
descriptor definition and seals all39744 RGBA predictions before comparison.
build/smooth-triangle-attribute-witnesses-root-1/result.json,
SHA256a6609ae64d151657fccf2665621f552f866521d10569656e9b18a04251cec1b2,
refuses all576 declared variants: zero necessary-gate survivors, best9/26
translated pairs. Independent saved inspection85ff3dd50e797343a7de0854b29e80371cf71434558a53b188ae600a28296778
reproduces every value and all pair/same-frame/original-symmetry outcomes from
the frozen source. No model is selected and no full-array/heldout/native study
follows the necessary refusal. A new family now requires a specific primary-source
derivation for sample-coordinate or interpolation precision and a distinct
necessary prediction; do not repeat the refused normalized/rounded families.

Continuity754071655baff8846f42a6f6ac524aa3d41fb878f7c1c752ff530068334ad076
holds native4 and attached AGPL/BSD texts exact, CPU/review scratch removed and
no retry of rejected cleanup targets. Raw source/prediction/failure evidence stays.
The volume CPU run39675704330 has14 successful jobs and Glue39681785535 has11;
both remain queued with no reported failures. The prior mesh/image run remains
terminal20/20 success. These checks do not qualify graphics hardware. No research
is promoted as renderer support. All original13 release requirements remain open;
cybersecurity excluded.

Continuation checkpoint90, 2026-10-21: The finite-evaluation constant-existence
diagnostic is complete.69 CPU controls pass with no errors/failures/skips and
owned scratch removed. Restricted source review attempt1 requests stronger
sample/coefficient/shared-module binding; attempts1/2 are never executed.
Corrected attempt3 review9cde31c1b8f4de7f87c2bea8d77c509fe197fe2490beee9c2c4babdab65004b7
admits a frozen15-file bounded study. The driver reproduces all54 predecessor
rational interval records and witnesses, checks exact slope transport and
shared helper bytes, then evaluates3696 original central observations across
648 group intersections/216 side summaries/six orders/two constant placements.

Result build/smooth-float-interval-existence-root-1/result.json,
SHA256c09809d5b03864255285d0d0eec545c967b07b0d0bc5e1feb2e51d95b0b42bcc,
has no coupled feasible coefficient pair in any of12 order/placement summaries.
All nine pairs admit opposite-side constants; none admits negative-side constants
across all three frames. Even free binary32 constants per side/frame cannot
rescue the declared nearby shared-gradient family. No constant/model is selected.
Saved inspection799465f24e863332ce41b230a9655ee57058ed4e4b8d5fec5e610e8456feddaa
recomputes all648 intersections and independently checks2592 exact rational
boundary comparisons. This excludes only the declared neighborhood/orders;
next work must derive a concrete geometry-based raster/interpolation setup,
with preregistered controls, rather than repeat this family or fit coefficients.

CI observation0def971b8f6e3cc20e9395389b0936d0f5b69f34e05249577eb8d7dd304e0d64
records mesh/image run39673954150 completed successfully20/20 atffed21d;
volume39675704330 remains queued with12 successes and Glue39681785535 queued
with11, neither reporting failures. These CPU matrices do not qualify graphics
hardware. Public checkout remains clean at a11b172; no unqualified research is
pushed as renderer support. Continuity9b9e09bedaf06c8d28328a264e9f00b61b7763bed89ec7298e301dbdc5163a62
verifies native4, AGPL and all original BSD copies unchanged and all new CPU/
review scratch removed. No protected/heldout access, new geometry/capture,
shipping renderer edit or retry of rejected cleanup targets. All original13
release requirements remain open; cybersecurity excluded.

Continuation checkpoint89, 2026-10-21: Implemented a bounded exact binary32 FMA
helper using exact64 products, TwoSum residual recovery and binary32 midpoint
correction. Rational controls exercise cancellations and a2^-60 addend that a
plain binary64 intermediate loses. All25 CPU arithmetic/domain/pixel-layout
controls pass; the newly owned test scratch is removed. This helper and the
preregistered global slope/intercept-before-normalization family remain research
only; no shipping line consumer or compiled native artifact changes.

Independent restricted read-only review8b71e6b26c710e232b3a71bd551b5fc94a0a96026070641028e074645dbf80b8
admits a bounded necessary-witness study. The driver freezes15 source/control/
license/selection files, seals all5760 variants'69 predicted values before
comparison, and reads admitted metadata only through the protected-path Reader.
Actual study closes0 with REFUSED_SLOPE_INTERCEPT_FAMILY, no survivor, best0/26
translated pairs. Result build/smooth-slope-plane-witnesses-root-1/result.json,
SHA2561b2b78182d40b57714dc0e4d1bb23f3fd25ee1b691d58527ac568c6848a9843c.
Saved inspection build/smooth-slope-plane-prep-root-1/saved-review1.json verifies
every frozen/current source and prediction seal before journal updates and all
149760 predicted pair equalities. Every selected major-axis slope is an exact
dyadic quarter, so raw intercept/residual arithmetic remains exact within this
bounded domain and delayed normalization cannot reproduce native translation
differences. Further variations of this factorization are excluded, not selected
as a best nonzero-error renderer. No raw reference/holdout, provider, device or
renderer call follows this refusal; all original full-array/holdout/state/budget/
hardware qualification remains required.

The next representability diagnostic should test finite32 evaluation before
another formula sweep, preserving the old9 nearby normalized coefficient pairs
and all3696 central observations without choosing fitted constants for prediction.
The latest future-holdout registry is
build/smooth-training-geometry-exclusion-root-3/registry.json,
SHA256a3ebbc9a3f696d05e0d91c30b2a4f64fa5dfa6924c9b48b902cbca01b8bf9420.
It is a strict superset of6142 native-training undirected geometries, adding3
synthetic controls/reversals for6145 total. Native directed12028 remains scoped
separately; no new holdout or native capture is generated.

Only the two closed owned study JSON files are transparently NTFS-compressed.
GetCompressedFileSizeW reports a94459139-byte reduction; all116266243 logical
bytes and both SHA256 values remain exact. No file is deleted/moved and no
rejected cleanup target is retried. CPU/review temporary directories are removed;
useful source/prediction/refusal evidence remains. Both attached licenses stay
unchanged. Unqualified mechanism research is not pushed as renderer support.
All original13 release requirements remain open, with cybersecurity excluded.

Final observation confirms the four installed native byte holds, both root
licenses and compressed study/prediction hashes unchanged. Remote CPU runs have
19/20 successful mesh/image jobs (Intel Mac CPython3.12.8 still building),12/20
successful volume jobs and11/20 successful Glue jobs, with no recorded failures.
All three matrices remain incomplete. The published review branches remain
unchanged by the unqualified mechanism study.

Continuation checkpoint88, 2026-10-21: Verified the separate Glue volume-edit
problem as the pinned host's fixed-resolution-buffer cache remaining stale after
Data.update_components. The prepared public invalidate_cache(data)-before-update
protocol is copied into tools/fixture_glue_extensions.py, with exact whole-file
reversal to the unchanged legacy fixture except those two lines and SPDX header.
All original data, camera, quality, landmarks and exact RGBA criteria remain.
The original failed reference/admission, legacy fixture and failure pixels remain
unchanged; no failed image is promoted or fitted.

Source1 preserves10 CPU controls and an independent refusal before any run:
require all517 source pins plus explicit extras, and prove upstream wheel hash
membership in the original lock. Source2 closes these with the exact original
CP312 wheelc4862155e735009b1af6aeda45ea94a72e1a375d6086c89273455d66238bb18e,
all517 files, four generated/native extras and original BSD. Frozen12 controls
and all5-case collection pass; restricted independent review admits the run.
The actual Source2 run closes1: real fresh CPU controls reproduce stale data and
prove invalidation-before-update without QApplication or Dawn; all5 fresh original
GL cases pass, including volume_edit. Four candidate cases match exactly, while
scatter_axes fails the existing generated smooth-line policy. Both owned envs
are removed; all10 actual graphics workers terminate and native origins/cleanup
pass. Saved partial inspection5e5ca60fd626ae208292736a9a62260f2d6d00856369c44222ba21190b6550c1
preserves the required failure. The module-fixture assertion wrongly expands one
failed candidate into five setup errors; this is a reporting defect, not a pass.

Source3 moves all5 required nodes to tests/hosts and reports each independently,
retaining every comparison and failure. Its source authoring:
build/glue-wheel-source-root-3/authoring.json,
SHA256d13a6223d4c36672432789b07ccd57e33430012cc5121216c57c795012ccd32a.
Frozen12 controls and exact5 collection pass, CPU result
2cf33d3e13989f41da129c6871ba8c236c635545fed547416b15f65f45d7b2e6.
Fresh independent review operationedbe8e54ffb13f4b5e2c5e58c378ec985189ac08d93db1491c2a134f69164da9
admits rerun and the explicit migration gate: all5 original references plus all5
terminal candidate outcomes must verify, and any real candidate failure stays
a required named failure rather than an xfail/skip or complete-pass claim.

Actual Source3 suite build/glue-wheel-run-root-3/result.json,
SHA25640f404d78c5b3af17d5768448472ccb57a070436f8db806b638de714a23be264,
closes1 in153.24s with4passed/1failed/0error/0skip. All5 fresh original GL scenes
pass and repeat81920 pixels byte-exactly from Source2. The archived audited
candidate105698c7c6cef1e643b788a7b3a800e9630ebd7d9d6422fb4d11323389286f81
matches65536 full pixels in scatter, scatter_edit, volume and volume_edit.
Scatter_axes remains an actual generated smooth/MSAA policy refusal. All5
candidate outcomes, including failure, prove exact package/native origins,
hardware NVIDIA RTX4090 Vulkan, zero visible windows and eight shutdown-zero
counters. All10 graphics workers and two real CPU cache-control children close;
both newly owned environments are removed. Saved verification:
build/glue-wheel-prep-root-1/saved-review3.json,
SHA2565638fb93615444e0529a5812ac680375b1e7efbae994b7a3e9d3776a2f835cef,
status VERIFIED_GLUE_REQUIRED_CASES_FAILED. It is not a complete Glue pass.

Migration proof build/glue-wheel-prep-root-1/migration3.json binds that saved
review and the exact independently reviewed before/after test files. The old
historical metadata function is unchanged; active GPU coverage moves entirely
to the five corrected tests/hosts/test_glue_wheel_parity.py nodes. The JUnit failed
node is independently joined to scatter_axes. Every current frozen22 source,
native4 and immutable auxiliary still holds after migration; actual uv paths
match the pinned tool. A names-only Reader boundary check admits all19 legacy
Glue reference members before the retained metadata audit reads them. Newly
owned CPU/review/runtime scratch is removed once. Useful source/raw/failure
evidence stays retained and rejected old cleanup targets are not retried.

The public checkout passes114 combined CPU controls, including the retained
legacy failure audit. Result build/glue-wheel-prep-root-1/publication-cpu-root-3/result.json,
SHA25649d1e154ee82f6a54860c760ec5f0849a3396e43ab19e6b0a4951a1294545954.
Original BSD and implementation AGPL attachments are unchanged. Formal Glue host
cell admission, general smooth-line implementation, broader hosts/plugins,
physical Qt/other ABI/platform/fresh build/performance and every original release
requirement remain open. Cybersecurity work remains excluded.

Glue publication closes at a11b17214b6cdfaf2156e5e91dd7c5cee1f7bc31 on
bipxx/vispy_vulkan branch work/glue-cache-regressions, with matching remote ref
and a clean public checkout. The final copy proof records an EOF-blank-line-only
normalization of the migrated historical test; its complete module AST is
unchanged and the reviewed before/after bytes remain retained. Staged raw source
hashes and all original BSD/AGPL attachments are verified. Actual new20-row CPU
run39681785535 is queued. Separate earlier runs continue without cancellation:
mesh/image39673954150 has17 successful jobs and no recorded failures; volume
39675704330 has11 successful jobs and no recorded failures. None is yet a
completed whole-matrix qualification at this observation. Main remains unmerged.

Continuation checkpoint87, 2026-10-21: Implemented installed-wheel scalar and
categorical volume regressions for all11+6 original cases. Original fixtures,
capture programs, manifest/reference bytes and comparisons remain unchanged.
New loader pins both original manifests and70 artifact bindings, fixture/capture,
host-lock, input, parameter and license joins. Scalar comparisons retain both
checked original analytic regions (interior maximum2, edge differing fraction
at most.001); categorical RGBA is exact. Native-widget checks, sparse IDs,
input revisions, all quality settings and geometry/camera parameters remain.

Source1 build/volume-wheel-source-root-1/authoring.json,
SHA2569717eee8ef63e47b0b9a5c70d5dbd33717492bbae8a56a14373f54b003e36ef7,
freezes26 source/control/license files and70 reference bindings. Its frozen30
CPU controls pass and collect all17 required cases without skip/deselection.
CPU result9efd28aa3c1df5ce22f9856eaf4c12f88d911f1f3ea485e8971e72a32321e328.
Independent restricted read-only peer review finds no bounded-run blocker,
operation48d3007967788127118c1b18db338fa563a2bc97d963742a232d214b4c45f3fe.
Nonblocking scope/reporting notes remain retained in the review; no physical Qt,
other ABI/platform or fresh renderer qualification follows from this harness.

Actual suite build/volume-wheel-run-root-1/result.json closes exit0 with17pass,
SHA256c5afebdeec88c7b799dbd1fe236fe229aeb68f765fe8c8843148defaf5b54765.
It uses archived audited CP312 Windows wheel105698c7c6cef1e643b788a7b3a800e9630ebd7d9d6422fb4d11323389286f81,
on NVIDIA RTX4090 Vulkan610.88/CPython3.12.8. All156672 pixels match byte-for-byte,
including exact alpha, without changing scalar tolerances. All scalar methods,
ray/plane/interpolation/clipping/foreground-mesh depth cases and six napari
categorical rendering/edit cases pass with original parameters. Every actual
worker terminates; native origins, eight zero-resource shutdown counters and
owned environment teardown pass. Saved verification independently rejoins the
full evidence namespace/hashes, original images/parameters/regions, package/native
origins, process identity/terminal state and removed environment. Result:
build/volume-wheel-saved-review-root-1/result.json,
SHA25669efb1aa9b1953c4eb7a32dcab6aec1a934484b77e3ab71c94d61ac3a5fbc099,
status PASS_ALL17_REQUIRED_WHEEL_VOLUMES. Supplementary setup audit confirms the
actual uv executable matches its pinned tool and both hashed runtime/host and
candidate requirements are installed together. Native4, sources, references and
archive remain held. Newly owned CPU/review/runtime scratch is removed once;
useful frozen and raw evidence remains. Rejected old cleanup targets are not
retried. Both original BSD and implementation AGPL attachments remain unchanged.

The publication checkout passes all101 combined mesh/image/volume CPU controls,
result build/volume-wheel-prep-root-1/publication-cpu-root-1/result.json,
SHA25690c5bf1babc9828beea327c5d9ed8a4d46dc91ca4adcda51b6a8d94e0c3bf3aa,
and its newly owned scratch is removed. Volume publication uses a separate
work/volume-wheel-regressions review branch based on ffed21d48, preserving the
active earlier mesh/image CI run39673954150. That run has15 scientific-control
steps passed and no recorded failures at the latest observation, but no whole
remote matrix pass is claimed. The older69ffefdcb run39671771858 is now actually
cancelled, with one completed successful job and no recorded failure. Glue's
separate volume discrepancy, smooth lines and every wider original release
requirement remain open. Cybersecurity work remains excluded.

Volume publication closes at cb74aba5ee8e42ab3059c0b5f83df3c6063bafb3 on
bipxx/vispy_vulkan branch work/volume-wheel-regressions. Remote ref and clean
publication checkout are confirmed. Seven staged new source/test/doc files hold
their tested hashes; original fixtures, references and exact AGPL/BSD attachments
are unchanged. Actual volume CPU run39675704330 is queued for this commit.
The separate ffed21d48 mesh/image run39673954150 remains live with15 running and5
queued jobs and no recorded failures, and is not cancelled by this branch push.
Neither remote matrix is complete; main remains unmerged. Next substantive work
includes the separate full Glue workflow/volume qualification and unresolved
smooth-line mechanism, retaining all original scope and evidence boundaries.

Continuation checkpoint86, 2026-10-21: Published the mesh/layout installed-wheel
regressions at bipxx/vispy_vulkan branch work/mesh-layout-wheel-regressions,
commit69ffefdcb4c2a18ed527092de714777f49e4edee. Both implementation AGPL and
original BSD texts and attachments are unchanged. Actual publication CPU45 pass;
twenty-row remote CPU run39671771858 remains pending at the last observation,
with fourteen mesh-control steps passed and no reported failures. No complete
remote matrix or graphics/platform admission is inferred.

Implemented installed-wheel image/label regressions for all13 original cases,
without modifying tools/fixture_image_extensions.py, original authoring,
reference frames or exact comparison criteria. The strict new loader pins
manifest9675b84eda8cd0c910d31fa668c6b77cda35ea94f26e8bc2e45a8d0ccd7bf70d
and93 original artifact bindings, source/authoring/lock/license joins. Full-frame
RGBA and presence-symmetric original label/paint/revision/level/slice observations
remain required. Ten actual napari/PyQt6 workflows and three direct ImageVisual
workflows run as separate isolated external installed-wheel processes, with
wheel-byte verification, actual PID/creation-bound termination, loaded-native
origin checks and zero-resource shutdown.

Source1 preserves an actual frozen CPU synthetic-test path failure. Source2
passes26 CPU controls and exact13-case/no-skip collection; independent review
admits it, but actual run2 stops during dependency setup, before any scene
worker or graphics. Hash-locked napari's vispy dependency cannot be satisfied
when the candidate wheel is installed in a later operation. Full failed packet
and independently checked setup failure remain retained; owned environment is
removed. Source3 changes only the runner install vector and its synthetic test,
installing locked runtime/hosts and the exact hashed candidate wheel together.
No dependency hash or comparison is relaxed. Source3 authoring:
build/image-wheel-source-root-3/authoring.json,
SHA256f27cfe64a023cd31fa2ffa277cc3129c8c5282222bf1c799705f5e241c84b2c3.
Its frozen26 CPU controls and exact13-case collection pass, CPU result
6c634d97115f1222525b49f759d61e31b8e733ddec68d15d61d70cc1a6a8262e.
Fresh independent read-only review admits bounded execution, operation
9671fd4a6e2f4495f11fe09acf740f16319108ab45a9b97de03785db8aacbe3e.

Actual Source3 execution closes exit0 with13pass, zero skips/errors. It uses the
archived audited CP312 Windows wheel105698c7c6cef1e643b788a7b3a800e9630ebd7d9d6422fb4d11323389286f81,
not a fresh renderer build. All159744 pixels are byte-exact; semantic observations,
native origins, all shutdown counters and actual worker termination pass.
NVIDIA RTX4090 Vulkan610.88, CPython3.12.8, napari0.9.2, numba0.68.0,
PyQt6-reported6.11.0. Suite result:
build/image-wheel-run-root-3/result.json,
SHA2565596f87ef0529de0da378205ef3ed82ea7caf65b3f9785ee0e784b158ac396f3.
Independent saved verification rechecks every frame/semantic result, exact
evidence namespace/hashes, package/native origins, terminal workers and removed
owned environment. Result build/image-wheel-saved-review-root-3/result.json,
SHA256753f983f62435341cae11e1f0d320eeaa1e1fa2bf6300dca4fea7b7daa519943,
status PASS_ALL13_REQUIRED_WHEEL_SCENES. Supplementary actual setup audit checks
the uv executable equals its pinned tool and both hashed requirement files were
used in one install. Sources, references, wheel and native4 remain held. Newly
owned CPU/review/runtime temporary environments are removed once; useful frozen,
failure and result evidence remains, and rejected old cleanup targets are not
retried. This closes the bounded image-wheel regression deliverable only.
Smooth lines and all original13 release requirements remain open; cybersecurity
work remains excluded. Both attached licenses and third-party notices remain.

Image publication closes on the same public review branch at
ffed21d48bee153ccd56f6250d746e69d00caf33, independently confirmed at the remote
ref with a clean publication checkout. Seven new source/test/doc files preserve
their tested bytes; original fixtures, reference packets and both attached
licenses are unchanged. The public checkout's combined71 CPU controls pass,
with fresh owned scratch removed; publication result
build/image-wheel-prep-root-1/publication-cpu-root-3/result.json,
SHA256cd990a5038c809e8081e7984d666711754eaed741c4fd7078f06f23494a09075.
The unchanged20-row CPU workflow now includes both scientific suites before
compilation. Actual new run39673954150 is pending and will supersede the earlier
incomplete branch run; no remote matrix pass is claimed. Main is not merged.

Continuation checkpoint85, 2026-10-21: Implemented portable installed-wheel
mesh/layout/text regressions as an independent scientific-validation deliverable
while smooth-line mechanism work remains open. All13 original NVIDIA GL scenes,
commands, shaders, parameters, CPU atlases and reports are exported byte-for-byte
to tests/reference/mesh-layout-opengl (80 files,33302907 payload bytes), retaining
both AGPL and original BSD. Manifest SHA256:
d4bdd74c7de56c9f2f615f6d0f9d591bf0de3670e762f7fc28b48e356719c153.
The original fixture and its per-case comparison contracts stay unchanged. The
new tests/parity/test_mesh_layout_wheel_parity.py requires every case, including
axes_colorbar, with no skip/xfail. The existing hardware qualification command
already discovers it through tests/parity and the gpu marker.

Source1 freezes20 source/control/license members, passes40 CPU controls and is
preserved unexecuted after independent review identifies a real Windows venv
launcher/Python PID mismatch plus native loaded-image provenance requirements.
The real CPU launcher observation confirms distinct42108/42648 PIDs. Corrected
Source2 binds per-case launch IDs, actual PID/parent/creation stamps and observed
worker termination; it strips inherited non-harness Vulkan/Dawn/VisPy controls
and records loaded native images before shutdown, rejecting repository images
before hashing excluded payloads and requiring loaded VisPy libraries to match
the supplied wheel. Unknown worker status blocks further launches and cleanup.
Source2 freezes22 members and80 canonical reference bindings without duplicate
reference-array copies. Authoring:
build/mesh-layout-wheel-source-root-2/authoring.json,
SHA256a1b66090992132d038b741dff3f0f1721080dc80005f906f24aa981ceb4950e1.
Its full frozen45-case CPU bridge and explicit13-case/0-deselection/0-skip
collection pass; CPU result SHA256:
7cf89ca03f9d6390d02ecee2fe4d0de1db40d24e4fcd9f8e3a1680fae48ac843.
Python3.10 syntax parsing accepts all14 frozen Python files; other ABIs/platforms
are not thereby qualified. Fresh read-only Claude review closes the findings,
review-operation SHA256f31a171be889fef4b68e0bd26c372ab2a9f985225ba0adafeeaed2b74923e5cf.

Actual bounded Source2 execution uses the archived audited CP312 Windows wheel
105698c7c6cef1e643b788a7b3a800e9630ebd7d9d6422fb4d11323389286f81,
not a fresh renderer build. All13 required workers run on hardware RTX4090
Vulkan/610.88. Pytest terminates1 with12pass/1fail in41.01s. The sole failure is
the required axes_colorbar generated smooth-line policy refusal. Its native
origins, installed package byte verification and resource cleanup still pass.
No antialiasing is disabled and no criterion is relaxed. Suite result:
build/mesh-layout-wheel-run-root-2/result.json,
SHA2562b63f7eb62efc55c8d1bb979c3380c1fdd9a7e47d5a6ab3ba0d862018010b1fd.

Independent saved-result verification checks exact evidence namespace/hashes,
launch IDs, all13 terminal actual workers, archive package hashes, loaded native
origins, full images, atlases/glyph/font/view metadata and cleanup. All12 compared
frames are byte-exact:430080 pixels,0 differing bytes,0 maximum channel error.
Every actual worker is observed already absent after its launcher terminates;
all resource counters are zero and the newly owned external wheel environment
is removed. Native4, source, reference, tool and archive holds remain exact.
Saved review: build/mesh-layout-wheel-saved-review-root-2/result.json,
SHA256eecee6bc7cd8886cbba777f69b9bc7aae75689805f629afcacfcda8f895e68ea,
status VERIFIED_REQUIRED_CASES_FAILED. This verifies the twelve-case scope and
the real required failure; it is not a complete13-scene pass, current-source
identity refresh, cross-ABI/platform/host/physical-Qt or release qualification.

Automatic approval review rejects removal of six disposable pytest scratch
folders with blocked by policy. They remain; deletion is not retried through
another method. Exact targets are recorded in
build/mesh-layout-portable-prep-root-1/cleanup-rejections.json (the four
pytest-temp-1..4 folders under that prep root and pytest-temp under CPU roots1/2).
Useful frozen sources, reference/candidate arrays, review and failure evidence
remain retained. The external graphics consumer environment is separately
verified removed. All13 original release requirements stay open; cybersecurity
remains excluded and both licenses are unchanged.

Continuation checkpoint84, 2026-10-21: Implemented exact coefficient quantization
for signed numerator/sqrt(integer), using isqrt and squared integer comparisons,
plus exact membership on binary fractional grids. All22 arithmetic controls pass,
including signed rounding, irrational roots, nearest-even ties and strict bounds.
The diagnostic covers precisions8..32 and4 rounding rules:100 cases. The earlier
preregistered count84 was a typo (the explicit range contains25 precisions);
the first frozen plan retains it, while actual source/result and current plan
use the complete100. Of those100,49 admit rational constants across all6 central
side/frame groups; minimum constant precision is diagnostic only, with unbounded
integer range. No format or interval member is selected. Result:
build/smooth-fixed-grid-format-diagnostic-root-1/result.json,
SHA2561f2ebfa580ef003704e7e2bfa36480223444d2a110a1e46e123f8de94910fa94.

Implemented400 explicit fixed-grid predictors with two geometric constant
formulas, common normal/constant precision,4 signed rounding rules and2 nibble
boundary rules. All10 final predictor controls pass; the earlier9-case control
is retained before the stronger type/overflow guards. Every400 variant fails
the sealed combined necessary gate, best2/26 translated pairs. Result:
build/smooth-fixed-plane-witnesses-root-1/result.json,
SHA2565855349fe95f52e5fac00759c6145e84fdf77ee3e5c94b453b1781a684773594.

The next structural family rounds expanded rectangle corners before deriving
the four coverage planes. Its576 declared geometry/normalization/setup/constant/
evaluation/tie paths preserve the existing cap staging, alpha encoder and axial
delegate. All21 geometry/domain controls pass, including exact axis corners,
direction-reversal vertex order and immutable geometry. Every576 variant fails
the same combined necessary witnesses, best11/26 translated pairs. Result:
build/smooth-quad-plane-witnesses-root-1/result.json,
SHA256e8c6b8608fc2d0cd05b30f5311b379759c76244596c3d6dbf9b7ffec13bee6d4.
No full arrays or native operation follows either refusal. These tests do not
exhaust every fixed format or geometry construction, and no model is qualified
for renderer integration. All prior exact constraints, source/prediction seals,
original references and protected holdout boundaries remain. Useful failed
study evidence is retained; no disposable build scratch is created. Both
licenses stay attached unchanged. All13 original release requirements remain
open, with cybersecurity excluded.

Continuation checkpoint83, 2026-10-21: Primary Vulkan documentation confirms
smooth-line coverage details are implementation-dependent and does not establish
an internal NVIDIA precision format; no such format is inferred. The next exact
diagnostic enumerates all9 nearby binary32 slope pairs independently on each
side, sharing each candidate across423/424/426. Of9 problematic-side candidates,
3 admit rational constants across all frames, but none admits binary32 coverage
or distance constants. All9 opposite-side candidates pass both binary32 checks.
Every candidate uses all central observations;54 exact interval/representability
cases cover3696 source samples. This class exclusion applies to exact evaluation
and plain nibble floor within the declared neighborhood. Result:
build/smooth-nearby-binary32-planes-root-1/result.json,
SHA256851f7910f28f85231e4c35ce96ced116a9fb777e031b18acdcc33f1610fe55e6.

Implemented block-relative planes anchored at first pixel centers for block
sizes1/2/4/8/16/32/64, retaining144 ordered arithmetic paths. Its20 CPU controls
pass. All1008 variants fail the sealed combined necessary witnesses, best12/26
translated pairs. Result: build/smooth-block-plane-witnesses-root-1/result.json,
SHA256b7df434989d81e31b2400fe5a347868239b4234a1420079722ec71a0b821562d.
The two-stage alternative constructs one global constant, evaluates at block
anchors and then evaluates local pixels. Its145 CPU controls pass, including
all144 block1-parent equivalences. All1008 variants fail the combined gate,
best11/26 pairs. Result:
build/smooth-incremental-plane-witnesses-root-1/result.json,
SHA256dbc82ae329f5996b0c5a6fe9b8df24c26ce213b38cb27f72f70bd4001d4a70cd.

Post-study seal verification holds all three frozen sources and both prediction
streams. Every144 incremental block1 stream matches its parent for every retained
pair/same-frame/original pixel. All432 block-relative size1/2/4 streams preserve
integer-shift correspondence exactly, corroborating that local-only block
coordinates cannot explain the actual inequalities; global setup remains a
distinct possibility. These are declared hypotheses, not claimed hardware tile
dimensions. No full arrays, native process or renderer change follows the
refusals. Next mechanism work must change coefficient/setup/precision structure
while retaining every exact constraint and full-frame requirement. Useful
frozen evidence remains retained; both licenses are attached unchanged. All13
original release requirements remain open; cybersecurity remains excluded.

Continuation checkpoint82, 2026-10-21: Added exact binary32 interval membership
by bisecting the finite ordered encoding space with Fraction comparisons,
including signed zeros, subnormals and strict rational endpoints. All27 current
certificate/interval/representability controls pass. Of24 fixed-normal cases,
13 admit any binary32 coverage constant and12 admit a distance constant. Among
the6 problematic rotate-first cases, only frame426/sqrt-recip has a binary32
coverage constant; none admits a distance constant. This excludes those fixed
normals with exact evaluation and plain nibble floor, not all finite-precision
evaluators. Result: build/smooth-constant-representability-root-1/result.json,
SHA256bf3555b8bd04a85f308239088a52ee441e7f9cb3bd4a6f6684b77a3e62896aac.

The exact unrounded homogeneous reciprocal product, retaining all product bits
and width addition, still admits only the12 opposite-side cases and none on
the problematic side. Removing final constant rounding alone is insufficient
for that exact class. Result:
build/smooth-unrounded-constant-diagnostic-root-1/result.json,
SHA2563ce03bf96b78e0d814082e94a461e8e712e98d6b84a313ce3af309767a019df3.

Added the previously absent coordinate nesting orders: three binary32 split
evaluation associations, both two-FMA nestings, binary64 evaluation, and both
fused constant nestings plus split setup. Nine arithmetic CPU controls pass,
including an exact cancellation case separating the x/y orders. The resulting
144 declared predictor variants all fail the sealed26 translated-pair/15 same-
frame-pixel/2 original-pixel necessary gate, best11/26 translated pairs. Result:
build/smooth-ordered-plane-witnesses-root-1/result.json,
SHA2567e21d9bad199b7435f6085abc7487302dcac663eae54b0247bd92669f6080a52.
No full-array sweep follows. This does not exhaust every hardware evaluation
or coefficient format; the next investigation must test a structurally different
setup/evaluation class while retaining all exact constraints. No native process,
renderer change, image correction or new holdout is introduced. Useful source,
sealed predictions and refusals remain retained, with both licenses attached.
All13 original release requirements remain open; cybersecurity stays excluded.

Continuation checkpoint81, 2026-10-21: Extended the exact affine certificate
helper to derive constant intervals for fixed rational normal slopes, retaining
strict upper bounds, saturation and bound-imposing observations without choosing
a constant. All18 certificate/interval controls pass. Across24 side/frame/path
cases,18 have feasible intervals. The6 problematic-side tangent-first cases are
infeasible under exact evaluation. The6 rotate-first cases are feasible but none
admits the existing ideal or split/fused constant constructions; the12 opposite-
side cases admit all5. Saved diagnostic:
build/smooth-fixed-normal-intercepts-root-1/result.json,
SHA2561b5c9a80e249be277ebbb1d3cf2818b8424cb337babf245ecdee727616e4c610.
This exact-evaluation conclusion does not exclude other finite-precision/tie
rules. No interval midpoint or fitted constant enters prediction.

The preregistered first/midpoint/second geometric-anchor check finds no common
rule that covers all cases. Midpoint retains12 admitted cases; exact second-
endpoint construction adds only2, and all binary32 variants still admit12.
Saved result: build/smooth-anchor-intercepts-root-1/result.json,
SHA256f6ea6f3f558010298a611618e2a00f5638af2478c83f3843403d5cd3f7e7fdd1.

Implemented tools/smooth_line_homogeneous_planes.py to form raw C from the
unnormalized direction and endpoint before applying reciprocal length. Its48
declared variants keep signed-normal rounding, nearest/upward constant rounding,
two reciprocal paths, three evaluations, two tie rules and two width/cap staging
paths explicit. All53 CPU controls pass. All48 variants fail the sealed combined
26 translated-pair/15 same-frame-pixel/2 symmetry-pixel gate, best8/26 translated
pairs. Refusal: build/smooth-homogeneous-plane-witnesses-root-1/result.json,
SHA2565ab97a3cf334d2f1bb828813845d6dcbcdc03f1f8ee5f985da5aa75626e88eff.
No full-array sweep, native operation, renderer change, image correction or new
holdout follows. Intercept construction/evaluation remains unresolved; future
work must retain all exact bounds and necessary witnesses. Sources, predictions
and refusal proofs are retained as evidence. Both licenses remain unchanged;
all13 requirements remain open and cybersecurity stays excluded.

Continuation checkpoint80, 2026-10-21: Implemented exact rational verification
of saturated affine nibble certificates. Nine CPU controls pass, including a
strict rational boundary distinction lost by binary64, saturation, inclusivity
and input refusal. A numerical LP only proposes certificates; every retained
certificate is checked using Fraction against all selected observations. Every
one of6 independent side/frame groups in423/424/426 admits an exact certificate,
covering3696 strict-central-half pixels. Saved diagnostic:
build/smooth-tilted-affine-diagnostic-root-1/result.json,
SHA256f704b4ebf03fead31b53c0b666ddf4f7dca865c9aa30c958ee039068ea98d9d7.

A stronger coupled test also passes: one shared normal slope pair with opposite
side signs, each slope bounded by neighboring binary32 values around the ideal,
plus6 independent intercepts, explains all3696 alpha nibbles exactly. Result:
build/smooth-tilted-affine-diagnostic-root-2/result.json,
SHA256e342cd8423853af97d6db08fed7d8b19dfa7309c02eec68b94b371d0b2d0bbeb.
These are fitted diagnostic existence certificates only. They do not establish
a shared intercept algorithm, mask or full-frame mechanism, and no coefficient
is imported into prediction or renderer code. Solver failure would be treated
as inconclusive; no numerical infeasibility claim is made.

This exposes another operation order: independently normalize the four already
rotated/opposing signed normals, instead of rounding a tangent and negating or
rotating rounded coefficients. New tools/smooth_line_rotated_planes.py combines
that distinction with48 declared setup/evaluation/tie/staging paths. Its51 CPU
controls pass. Sealed predictions include all26 translated pairs, all15 new
same-frame pixels and the earlier2 reciprocal-symmetry pixels. All48 variants
fail the combined necessary gate; best10/26 translated pairs. Refusal:
build/smooth-rotated-plane-witnesses-root-1/result.json,
SHA256070c08b32452307cb832cd210df4466fb3bcfd19be1f66800d780177ae2d42f8.
No full-image sweep or native operation follows this refusal. The uncertainty
is now shared setup/intercept construction/evaluation, with near-ideal tilted
slopes compatible diagnostically. Existing shipping smooth refusal remains;
no tolerance, image, holdout or per-pixel correction is changed. New frozen
proofs and sources are useful retained evidence, not disposable build assets.
Both licenses remain attached; all13 original requirements stay open and
cybersecurity remains excluded.

Continuation checkpoint79, 2026-10-21: A new read-only exact-distance diagnostic
checks all576 admitted window frames in each segment's strict central half.
Three frames (423,424,426) each contain one signed-distance group with both
clear and covered pixels, despite identical exact cross numerator-5015808.
All are vector5 reverse, width832, phase000/255. Frame423 contains clear pixels
(8,19),(9,23) and RGBA255/255/255/16 pixels(10,27),(11,31),(12,35). These all lie
on one exact perpendicular-distance locus inside the central half; changing a
per-frame scalar distance coefficient/intercept cannot explain their conflict.
Tilted coefficient pairs, along-line dependence and position-dependent rounding
remain possible. This is a class exclusion, not a unique mechanism selection.
Frozen diagnostic sources/licenses and the full conflicting coordinate groups
are retained at build/smooth-window-equal-distance-root-1/result.json,
SHA2562be0a3bcc6338e5829d8496f60ab845a483493157b7f5b87f45f1d7d4ec85fa1.
Input raw bytes hold before/after; no new GPU operation, held-out access or
renderer change occurs. Future mechanisms must satisfy both these same-frame
witnesses and the26 translated pairs before complete-array studies. All13
release requirements remain open, cybersecurity excluded, both licenses held.

Continuation checkpoint78, 2026-10-21: Implemented separate distance-plane
staging in tools/smooth_line_distance_planes.py, preserving the24 declared
normalization/setup/evaluation/tie combinations. Unlike the previous family,
zero-offset perpendicular/longitudinal planes are evaluated before subtracting
absolute distance from half-width or adding the cap footprint. Sources and all
24x52 RGBA predictions are frozen/sealed before comparing the26 translated
necessary witnesses. Every variant fails; best10/26 exact pairs. Result:
build/smooth-distance-plane-witnesses-root-1/result.json,
SHA2568196bd4d0462d4a781fa839fa5951ea99b9876f2058a688dd0f0009aff97f80a.
No full arrays, native process, correction table or new holdout are generated.
The existing29 normalization controls belong to the prior frozen family, not
new distance-plane tests; the saved witness study is this family's bounded
verification and refusal evidence. Next mechanism work remains other setup or
evaluation structure, with every prior necessary witness and full-frame gate
retained. All13 release requirements remain open; cybersecurity is excluded.

Continuation checkpoint77, 2026-10-21: Implemented the preregistered24-variant
normalized absolute-plane family in tools/smooth_line_normalized_planes.py.
It combines signed staged reciprocal-product rounding with the existing two
plane-constant paths, three evaluation paths and two nibble tie paths, preserving
the cap/attenuation/alpha rules and axial delegation. Its29 CPU controls pass.
Before observation comparison, the bounded witness study freezes16 source,
test, selection, license and control members and seals all24x52 RGBA predictions.
All24 variants fail the necessary26 translated-pair gate; best matches8 pairs.
No full-array generation, new native capture, held-out read or renderer change
is justified by this family. Refusal remains saved:
build/smooth-normalized-plane-witnesses-root-1/result.json,
SHA256f02c6687136b26568b5e7740b4e7053fc0ce55b43bcd40823de296d5d90c4d14.
This excludes these standard absolute-plane arithmetic combinations only; it
does not exclude all absolute-coordinate or incremental rasterizer setup.
Next mechanism work must discriminate a different setup/evaluation structure,
retaining the26 necessary witnesses and all full-frame gates. Useful frozen
source/prediction/refusal evidence is retained; no disposable build assets or
new native process are created. All13 original release requirements remain
open, cybersecurity excluded, AGPL and unchanged upstream BSD attached.

Continuation checkpoint76, 2026-10-21: Source9's independent review requires
corrections before capture; Source9 is preserved and never launched. Source10
keeps all576 main geometries and repeats every row in reverse order. Exact final
review-token admission rejects the actual Source9 FIX response, and all64 original
baseline footprints fit [8,56) on both axes before the declared shifts. Corrected
provider controls pass290 cases. Fresh Source10 review closes all four conditions;
its response is build/smooth-native-mechanism-prep-root-1/window-review-response10.json,
SHA25698bfa82c346f9d76e7abffb9f8e47e9207ff1f079ad2940ed53223a760193c6e.
Source10 authoring SHA256 is
7d8f95e309ebf27966995981d283f7b83fa5e50740f5a699bc52d0632dfb93d6.
Its prediction seal explicitly reuses the immutable Source9 prediction files,
after all streams regenerate unchanged. AGPL and original unchanged BSD remain
attached. Current native byte holds and protected-input boundaries are preserved.

Actual capture and saved review pass576 main frames,576 exact reverse repeats
and64 exact original baselines. Saved admission:
build/smooth-window-saved-review-root-11/result.json,
SHA256025a21dccc8a1f8ea3009446967093ebc7e4e01d6aa1153b7ac51f034a33727a.
All512 declared window correspondences are checked:21 differing rows,26 pixels.
All six direct stages terminate successfully, the actual worker is observed
absent and its external environment is cleaned. Repeatability is limited to
these two sweeps; unmatched-clear follows from the existing border requirement.

The directed-normalization family is also refused: only binary32 evaluation
variants pass the earlier two-pixel necessary condition, and those still miss
829/834 original pixels and790/732 setup pixels, respectively. No model enters
the renderer. Its12 CPU controls pass. Result:
build/smooth-directed-normalization-study-root-1/result.json,
SHA256f3e664c7a8d6d13517914fa537c2a5d462f01bb99ed520cf53f799c8d03313cb.

The new signed-local-coordinate helper passes6 controls. Frozen read-only
localization checks all512 counts and every one of26 witnesses against that
complete local key (signed delta, width, pixel relative to first endpoint): all
keys agree across their prescribed translations. Four differences are in the
central half;22 are elsewhere on the closed segment, including4 exactly at an
endpoint projection. None projects beyond an endpoint. Vector3 forward supplies
15 alpha-only differences; vector5 reverse supplies7 coverage-mask differences
(4 central); vector6 supplies4 endpoint alpha differences. Thus a purely local,
translation-invariant predictor cannot explain the data, including interior
coverage. Absolute-coordinate setup/evaluation or another nonlocal dependency
is required; this does not identify a unique hardware formula. Existing models
that evaluate an absolute centerline already have such a dependency and are not
refuted solely by this invariance test; their complete-array failures stand.
Proof: build/smooth-window-localization-root-1/result.json,
SHA2566e1ee6aefe3b809f8cd6112f41bdbb29553926e4784ca9d2d7dfd2424fa34cdc.
Raw image hash is held before and after. No GPU operation, held-out read, pixel
correction or fitted epsilon occurs. Next discriminate absolute line-equation
setup/evaluation using these necessary witnesses before any full-family study;
cap-only or local-only changes cannot close the observed gap. All13 original
release requirements remain open, with cybersecurity excluded.

Continuation checkpoint75, 2026-10-21: The next discriminating control changes
actual window position while preserving length, direction, width and subpixel
phase. New tools/smooth_line_window_training.py defines576 ordered rows: the64
viewport-study baselines under offsets{-4,0,4} squared, Y then X. Offset0 is row4
of each9-row group; all64 such baselines repeat after the sweep. Viewport/FBO/
readback stay64x64. Separate exact role/index admission precedes all operations;
old roles refuse the new IDs, and shared provider bodies remain unchanged.
The correspondence helper compares declared source/target pixels without changing
either raw frame and exposes unmatched nonclear pixels separately. These must be
zero before treating an invariance comparison as valid. It is a scientific
native/native diagnostic, not candidate-image alignment or renderer qualification.
Protocol tests include one read, raw-before-post-state refusal, direct role
rechecks, exact window/clip geometry, mutation and unmatched-pixel detection.
Relevant suite passes209 cases; complete new provider suite passes281 cases.
Owned sink-control temp is removed. Current/frozen isolated CLI imports pass.

Source9 freezes34 source/evidence/license members at
build/smooth-training-source-root-9/authoring.json
1f71e9a4acbfe955f075fb925a76575592adcdefbc146d94a1c43b657dc3b331.
All three already-refused normal-cap models'576 full-window predictions are
saved/sealed before observation, with64 original baseline aliases, at
build/smooth-window-prior-predictions-root-1/seal.json
b6d4678606e86a63a1aa6b853f5afdb039205ce12a5202fd284bb4703bf5643f.
Rehash/reload verification proves all1728 model correspondence checks exact,
including zero unmatched pixels; this does not admit any model. Launcher
24874a004a4d1caf0a504d67efe7603cc7a849b1130bff0f2bb012cfc7c341a2
is prepared for576 accepted rows and64 repeats. No Source9 review, admission or
GPU capture has run.

Before observation, freeze the expanded training-only geometry registry at
build/smooth-training-geometry-exclusion-root-2/registry.json
71be08191ffa5df72a526c29c5142c152ef68eeee7d5e2990c748c07fc975e3f.
It contains6142 reversal-invariant/12028 directed geometries over12512 declared
training rows, including the viewport controls flattened to window geometry.
The previous5886-key registry is explicitly retained as a subset and linked by
hash. No old protected or future held-out input is opened. Next prepare/review
the Source9 saved reader and source admission, then report every512 nonbaseline
native/native pixel correspondence and enforce exact64 original baselines and64
repeats. All13 original release requirements remain open; shipping coverage stays
gated; AGPL/original BSD intact; cybersecurity excluded. Frozen raw/prediction/
failure evidence is useful and retained; previously rejected cleanup targets
remain untouched.

Continuation checkpoint74, 2026-10-21: Source8 viewport CPU bridge verifies all256
exact window roundtrips,64 original baseline upload aliases,250 passing current/
snapshot controls and four direct role-before-operation checks. All32 reversal-
invariant window geometries are already in the frozen5886-key training exclusion
registry; no new window geometry or held-out input is introduced. Control:
build/smooth-viewport-overlap-control-root-1/result.json
e7ed67e6c5aa04a54a7f6a143f6161eab555aa278869856c59fe21d06a4b420a.

The Source8 saved reader is prepared with actual-viewport checks, verified one-
viewport command prefix, exact remaining chronological batch, setup/direct/cleanup
validation and startup/declared/prior-baseline joins. It requires all64 baseline
and repeat frames exact before analyzing all192 other whole-frame comparisons.
Restricted peer review444381/session76281 closes e2bc71/exit0, child59928, with
READY_FOR_SCOPED_VIEWPORT_OBSERVATION at response
c88f3c796945587b5eeb2bbd8094903b4dbea3133a71975fc3d2cba94f5ee3ff. Root closes
the two mandatory draft prerequisites by pinning that digest and resolving the
stale supplementary-review comment. Source and reader code are unchanged from
review. Reader9 is pinned atbf0742b0e749fcc5ccff2d65afe92a5c10c2125d4c76eabbc5475da98c4f6019
before launch. Viewport-edge effects remain an interpretive caveat rather than
an asserted cause. Prediction/policy files are checked before and after capture.

Actual coordinatorc501b3 exits0, launcher76116; direct stage children
81676/71700/34284/71212/84812/75788 all exit0 and are waited. Actual worker75792
is confirmed absent (OpenProcess error87) before owned external-environment
cleanup. Parent19cbb455e7b4cdaf40d15fc056d416d9f0b898fcc880e34c0584566ec88bae0a
and envelope56d9e41a0820faffcd69264e89958c0e54a186cb37b46ed94a592f822f4636cd
retain exact snapshot/native4 and prediction/policy preservation, real terminal
process observation and complete teardown. Worker
54cb3ea513c4bdd0985bb585ef012718ebd32048e4279eb0e0c8e8084fa9ccc6
records256 accepted rows plus64 repeats. Saved readerd8d132/exit0 validates all
state/hash/identity/commands and exact64 repeats/64 original baselines at
build/smooth-viewport-saved-review-root-9/result.json
73ed028041f09120f11f65fb45aab64c43e394cec130530875a76c4ead47a6cd.

All192 changed-viewport comparisons are byte-identical, including all64 cases
in each of the three origin/scale variants. No viewport-origin/scale effect is
observed in this scope; this does not prove universal viewport independence or
identify the missing rounding operation. Prior models0/2 still differ in168
pixels/20 rows, model1 in192/28, and all stay refused. Next isolate signed primitive
setup and actual window-coordinate evaluation, rather than choosing a free
viewport origin or another scalar reciprocal. Integer window-translation
contrasts are a possible next control; any must be predeclared and separated
from the new holdout roles. Shipping coverage remains gated and all13 original
requirements remain open. AGPL and original BSD intact; cybersecurity excluded.
Both owned peer-review and upstream environments are cleaned, useful frozen/raw
and failure evidence retained, prior cleanup-rejected targets untouched.

Continuation checkpoint73, 2026-10-21: Implemented a finite signed-normal
coefficient conversion family using nearest, negative-infinity, positive-infinity
and zero rounding with the twelve declared direct-plane paths. All56 CPU controls
pass. Frozen two-pixel necessary-condition gate refuses36/48 variants; predictions
for all3968 original oblique plus544 setup rows are sealed for each12 survivors
before either full array is opened. Every survivor fails, original4097..6544
pixels and setup1657..2972. Result build/smooth-signed-plane-study-root-1/result.json
20eb3f62ab16d0e7811ab0a91761269ebcfc7f5c2911ce77368def76eac128ee retains the
gate, sources and prediction seals. No nonzero winner advances.

New tools/smooth_line_viewport_training.py implements a separate typed256-row
control:64 original oblique geometries, each under four viewport origin/scale
settings, with inverse-transform clip uploads preserving identical window-space
geometry. Target/readback remains64x64; endpoint viewport margins are at least3
pixels for widths1/3.25. The64 default-viewport rows match original clip bytes;
64 end-of-sweep baseline repeats are predeclared. Exact role/index gates reject
original/corner/setup/holdout/forged/reordered descriptors before device or file
access. Actual viewport is checked before reusing other shared state invariants
on a copy; raw records remain unchanged. Require a single exact glViewport prefix
and unchanged complete row batch. The dedicated capture preserves one final read
and raw-before-acceptance ordering. Shared provider/old admission guards are held;
worker adds only the new study dispatch/import/module pins. Initial relevant
suite passes178 cases; complete future-provider suite passes250 with no skips.
Current and frozen isolated CLI import smoke pass. Owned sink-control temp is
removed by its scope; no actual provider/device is created.

Source8 freezes32 source/evidence/license members at
build/smooth-training-source-root-8/authoring.json
ed146ff07eb016f22bbea22397a1382e73d6639e8ae7421f258154c8516a7b5d.
All three previously refused normal-cap hypotheses'256 window-coordinate null
predictions are saved/sealed before observation at
build/smooth-viewport-prior-predictions-root-1/seal.json
166428d67b3d1701a3468055b0506153fe22283599f0ddf591d33bab95fb325f.
Verification rehashes all arrays, checks64 unique original baseline mappings and
proves each model predicts identical frames across every four-viewport group.
Launcher prepared at2d0d49bcd1adcaa7e79011b6923d001f6106b5a8a7456383096d07be31f98a31
requires256 accepted frames and64 repeats. No source admission, review or capture
has run for this packet. Next: source/reader review, admission, then the viewport
contrast observation with exact baseline/repeat gates and all192 changed-viewport
comparisons reported without selecting a failed model. Shipping smooth coverage
stays gated; all13 original requirements remain open. AGPL/original BSD intact;
cybersecurity excluded. Frozen failure/prediction evidence is retained, and prior
cleanup-rejected targets remain untouched.

Continuation checkpoint72, 2026-10-21: Implemented
tools/smooth_line_reciprocal_setup.py with twelve predeclared shared-reciprocal
paths: binary64 normalization, binary32 sqrt/reciprocal or single-round rsqrt;
binary64/binary32 local edge/dot evaluation; unchanged or oriented-nextafter ties.
The nibble/alpha/cap stages and axial delegation stay held. Thirty-one CPU
controls pass. All3968 original oblique and544 setup predictions for every path
are sealed before either oracle array is opened. Frozen result
build/smooth-reciprocal-study-root-1/result.json
613931a7519c870db127db544db92bcaedc6522cf12534aa5f12fedb12746730 REFUSES all12:
original errors2770..8782 pixels, setup errors1154..3642. All streams regenerate
unchanged during full comparison; no nonzero winner is selected. The existing
7168 axial/corner exact result is inherited through unchanged source/delegation,
not claimed as a new complete GPU qualification.

New exact local-product controls pass six cases. Saved counterexample
build/smooth-reciprocal-symmetry-proof-root-1/result.json
f4e6ce1fbc112be98e5f6597d07e3b51ad54104c42825b2e7091425cb174bb1b
verifies original vector2/width1/phase0 at forward pixel(29,24) and reverse
pixel(30,26). Both have identical canonical delta, width, signed cross and BOTH
endpoint dots: (9216,6912,256,-1474560,63406080,69304320) in integer units.
Their admitted reference RGBA is (255,255,255,115) versus(255,255,255,140).
All twelve frozen predictors return equal RGBA for the pair, so every path fails
at least one. The local differences/products here are exactly binary32
representable before normalization. This refutes outputs determined solely by
those local products plus a direction-independent reciprocal length, including
merely substituting a different scalar approximation. It does not refute signed
direction-dependent or absolute-coordinate plane setup/interpolation, or joint
origin/length effects. No data-derived lookup is installed; the pair is a
counterexample, not a correction. Next investigate those remaining setup
dependencies instead of more scalar reciprocal variants. No GPU capture,
reference/holdout mutation, renderer enablement or release claim occurs.
All13 original requirements remain open; AGPL and original BSD retained;
cybersecurity excluded. No disposable environment/build tree was created;
frozen prediction/refusal evidence remains useful and is retained.

Continuation checkpoint71, 2026-10-21: The twelve explicit binary32 direct-plane
setup variants all fail the unchanged3968-frame comparison (4103..6481 differing
pixels). Their sources and prediction seals remain held at
build/smooth-plane-setup-study-root-1/result.json
e9ecc4aa7e1787108f9178980fd1f611c4ffa7b63a849a7aeca457ebca44b2c4;
29 CPU controls pass. Exact nibble-affine constraints admit all64 wide-line side
groups; either binary32 or binary64 fixed gradients admit an intercept interval
in all64, with ideal-width intercept admitted in59. No fitted intercept is chosen.
Report build/smooth-line-setup-constraints-root-3/result.json
c6e653961721ba87578a13c60c94ce9df6448a42fc8d01d52c399ea836c0d74c;
expanded22 exact arithmetic controls pass.

New disjoint setup-along selection implements544 fine along-line rows over four
vectors, both directions, widths1/3.25, translate/start-only modes and17 steps.
All preserve the directed infinite line; start-only changes length. Provider suite
passes227 cases. Source7 freezes30 source/evidence/license members, author
f4f26d7b0a0309f886f953f02d97f028a486b3842e70314a660341727516a1e0.
All three already-refused normal-cap hypotheses'544 predictions are sealed before
capture, seal90752e5cc779a00ce89875a4d1ff0a0cf2dd05f29cd4a3b27798aed0968bd5fe.
The CPU overlap check first wrongly expects only32 baseline overlaps; the failed
check is retained. Corrected check finds36 overlaps (32 baseline plus4 diagonal
phase016 rows),20 unique original geometries, with exact clip bytes and four
direct role rechecks; control79b76ed7deb08a5a3fc73533e10ef6885f39a61dd311e0969395fbe7976d5518.

Restricted peer source review is ready conditionally. Conditions review accepts
future holdout scope and seal binding but requires setup chronology and baseline
cross-checks. Root implements both before capture: exact setup/direct/cleanup
command validation, startup/diagnostic/expected-oracle/prior-baseline joins and
explicit generated-mask/minimum-pixel caveats. Fourteen mutation controls and an
actual prior admitted metadata check pass. Final reader8 hash
2abce27951c9a0440a3de3b63e135903f4975d35183ebb43bf9328b231385aec is pinned
before launch; both reviews/refusals remain retained. A separately frozen training
geometry registry excludes5886 reversal-invariant geometries from future new
holdout generation; seven controls pass. Registryde613ec705abd00db4a21091318ac72ce087a1ed639d90eb271025f4c8ac5c76
contains all hashes,11516 directed geometries over11680 training rows. Old protected
study stays rejected/unread; no numerical disjointness from it is claimed. Future
holdout generation and qualification still require the registry gate.

Actual coordinator c67aca/session54575 closes666dc9/exit0, launcher4396; all six
stage children71892/64256/65356/66960/35216/55760 are waited. Native worker46372 is
confirmed absent before external-environment cleanup. Parent
6b371ea033850bae6669f84ea593b48cbcafc57ab495fac21ad5d28bc6d26faf and envelope
78c6402e42588f0139a82eb4ecee57f84cd4b4eb8dc20ceb59b07ff2b8dada81 preserve
exact snapshot/native4, prediction/policy hashes and teardown. Saved readerc93fa7
passes all544 rows,64 exact repeats and36 exact original overlaps, complete setup/
per-row/cleanup GLIR and baseline joins at build/smooth-setup-saved-review-root-8/result.json
99f8526c78d79a057a0814315387bd6a12fbfd58fe95324b1563c649eb290f4f.
All256 rigid-translation comparisons are exact. Of256 start-only comparisons,
64 differ in269 central pixels, exclusively the two Pythagorean vectors. This
points toward length normalization or end-dependent setup, rather than first
origin alone; it does not identify the complete arithmetic. Prior variants0/2
still miss1132 pixels/166 rows, variant1 misses1438/217 and all stay refused.
Next investigate unnormalized edge/dot evaluation with shared reciprocal length.
All13 original release requirements remain open; renderer remains gated; AGPL/
original BSD intact; cybersecurity excluded. All new owned temporary environments
are cleaned; useful raw/frozen/failure evidence remains, rejected cleanup targets
untouched.

Continuation checkpoint70, 2026-10-21: New exact setup diagnostics pass15 CPU
controls. Saved training analysis checks all1304 same-directed-infinite-line
translation pairs with zero central-half differences. All64 wide-line side
groups refuse an unsnapped nearest-integer affine coverage ramp, with rational
bound witnesses retained at build/smooth-line-setup-constraints-root-1/result.json
64caa17b88b9dd5d3fbd189e9a70984f390f60949261fb9e85fc3fbe2a654771.
This does not rule out a quantized ramp. All oblique interior codes lie in the
same16-value expansion2*n+(n>>3), n0..15, with no middle code16.

New CPU hypothesis tools/smooth_line_nibble_coverage.py uses perpendicular
coverage(width+1)/2-abs(distance), floor16 quantization, nibble expansion and the
retained integer alpha/staged cap encoding. Three precision variants are frozen
and prediction-sealed before whole3968-frame comparison. First family retains
major-axis caps and is REFUSED:20871/21392/20871 differing pixels and
1760/1770/1760 interior differences. Evidence build/smooth-nibble-study-root-1/result.json
7aeb8b959bed554081652d4f8c9c13cd9123549e41befb1f8afedbf6618dd68c.
Twelve CPU controls pass. Saved regeneration of variant0 reproduces its sealed
stream, identifies1755 exact normal-bin ties among1760 interior differences, and
localizes the other five to one geometry; diagnosis603b36e5771421e4b64d8a990b01663a8742c2ab620226f85374422155388159.

Second family changes only cap coverage to normal endpoint-plane distances,
keeping the .625 footprint/extension and staged major factor. Expanded18 CPU
controls pass. All three complete legacy prediction streams regenerate unchanged
before all new streams are sealed. Result build/smooth-nibble-study-root-2/result.json
90c9407a4c55779c588d3efea1bca9e6c62d95264d99d689c7f609e624c82d9f
still REFUSES all variants:2770/3580/2770 differing pixels. Variant0 has351
differing frames; four complete vector groups (1984 frames) now match exactly.
Interior differences remain1760. Saved regeneration/localization at
build/smooth-nibble-saved-diagnosis-root-2/result.json
50ef2eaa35c13ca8c858433240872cd36fbc3e73d88ff485cbf842b9d2829a81
preserves its stream and attributes2751/2770 differences to exact minor or cap
quantization boundaries; the other19 occur in two phase geometries. These are
diagnoses, not pixel corrections or model admission. Next investigate actual
normal-plane setup precision and directed ties, preserving all failed sources
and streams. No GPU capture, reference/holdout change, renderer enablement or
release qualification occurs. All13 original requirements remain open; AGPL and
original BSD intact; cybersecurity excluded. Only useful proof artifacts were
created; no disposable build/environment tree was needed.

Continuation checkpoint69, 2026-10-21: All eight frozen oblique hypotheses are
refused on the whole3968-row training set, including substantial interior errors;
no nonzero winner is selected. Result build/smooth-oblique-study-root-1/result.json
48696ff86428bdc53a89a23ff11dbef588b700969cf0e6526b99dab47ec3133b retains the
prediction seals and failures. The exact7168 axial/corner result is unchanged.
Standalone tools/smooth_native_vulkan_capture.cpp builds with both shaders
SPIR-V-validated. Earlier compiler-launch failures precede graphics creation;
owned external build/probe temporary trees are removed. Source2 freezes49
executable/shader/input/source/license files, including AGPL, unchanged BSD and
component notices. Restricted peer review is ready for this diagnostic only.
Actual child60964 exits0 and is waited; parent-result d5718e64d40cc54f0422f55488d11dc5f7e4e01fd8c941783f779aed5ae707e2
records process/module/device/driver checks, source preservation, raw hash/length
and resource closure. No shipping renderer path changes.

Saved native/GL comparison b13077031757b19bb3828930d332d1d870308055d6885a64ee174844b1c9989c
passes all11136 full RGBA frames:3072 original axial,3968 original oblique and4096
corner, zero differing pixels. Both contain834535 fractional-alpha pixels, with
no empty or fully aliased frames. New tools/smooth_line_frame_comparison.py checks
canonical role/order/exact geometry before frame access and tracks generated
masks independently of alpha. Its17 mutation/stream controls pass, including
clear/aliased false-pass, truncated/extra streams and generated zero-alpha masks.
An initial test-only tuple mutation failed (15pass/1fail) and was corrected.
The first separate audit snapshot omits transitive fixture_gloo and fails before
frame access; root-3 snapshot/refusal remain retained. Corrected root-4 includes
that unchanged dependency and rechecks all11136 saved frames with zero mask or
alpha differences: build/smooth-native-vulkan-saved-audit-root-4/result.json
3a4f9b1ea4a8c78f5a5c27a0b6d84dbb99887ba60f69775c121d85e22a621078.
No GPU capture, holdout access, reference edit or tolerance is used by this audit.
The result identifies native NVIDIA rasterization as a matching diagnostic target;
it does not implement or qualify the portable generated fallback. Intel has no
native smooth feature here. No runtime Vulkan validation layer, general fragment/
state, Metal or release/performance qualification follows. Next: investigate
oblique rasterizer setup/interpolation and quantization. All13 original release
requirements remain open; both licenses intact; cybersecurity excluded;
previously cleanup-rejected targets untouched.

Continuation checkpoint68, 2026-10-21: The endpoint gap is investigated with a disjoint corner-training selection rather than image corrections. New tools/smooth_line_corner_training.py predeclares4096 H/V-forward/reverse width1/1.5 inputs over32 longitudinal and16 perpendicular phases, plus64 repeats. Original7040 role gates still reject corner IDs; the corner path rejects original, holdout, forged and reordered descriptors before device/file access. Shared already-admitted bodies are factored without changing original entry guards. Worker explicitly selects one study kind and its canonical contract/count/sink/backend/capture function. Combined CPUdd7cec passes164 controls; after a test-name-only change, exact current corner controls208090 pass19. Source6 freeze4f9b45 retains24 source/evidence/license members at build/smooth-training-source-root-6/authoring.json9bbb0f19c22fae36148072f1e8c010822ba3743b6b1ef3198d75376b2dd2020a. It also freezes4096 predictions from the already-refused first CPU hypothesis before oracle capture, sealcbc66ca5d85877a8469ef9cdb2bbc48b39204a810f00600ee3950e26818c0424. Restricted no-tools review27f045/session87655 closes e87e6e/exit0, child24904; response2cd7f398555c4e155bdcd159379f163afbe5a028fa03abc17a68358ebdad3b54 is READY_FOR_SCOPED_CORNER_OBSERVATION conditional on pre-launch bindings. CPUe8f20e pins exact19-case XML/snapshot bytes, all128 overlap mappings with exact clip bytes, and four direct role-before-helper negatives at build/smooth-corner-overlap-control-root-1/result.json703271c97eb6690b9eac1020fc33c034e6e2645c48528d2bb98c2702273f7ef8. Root admission binds those proofs and the prediction hash before launch.

Actual corner coordinator235223/session32127 closes20d366/exit0, launcher70160; all six direct stage children64508/9576/65512/72672/29992/26176 are waited. Envelope build/smooth-native-mechanism-prep-root-1/training-envelope6.json7de8fc5f72054644fa380191845846e19ea2a07863fc1c117b5756263399e3a7 and parent build/smooth-training-launch-root-6/result.json2166fd95a74b66db981a864a7139838bf54e7b5b7d048938f24b12dd062e18ae retain exact snapshot/source/native4 preservation, real worker exit, Qt/parser/stream cleanup and automatic external-environment removal. Initial saved reader36fa52/exit1 preserves zero rows checked in result807fdf6acc4728c75151b03bc42332b18f04b928defe66c82e7f038041ee10da: it wrongly required NPY2.0 for np.save's sealed prediction file. Correction150939 pins old/new readers and the refusal, changes only that prediction's expected header toNPY1.0, and retains every oracle/repeat NPY2.0, hash/dtype/shape/length/state/command/role assertion. No capture or image is changed. Corrected reader1d5ff2/exit0 validates all4096 frames,64 exact repeats and128 exact original overlaps at build/smooth-corner-saved-review-root-7/result.json76199e3ad564abeb763dd113c257f9ccd9c6d5f8b0c16f08652c8a35e8c59d87. The frozen first prototype misses5984 endpoint pixels in3208 frames, max255, but zero central interior pixels.

Continuous-factor feasibility analysis241277/exit1 stops before its solver because the first alpha expansion produces131 at code16 while the observed alphabet has132. Its explicit refusal at build/smooth-corner-separability-analysis-root-1/result.json is an encoder-assumption failure, not a proof of nonseparability. New predict_axial_staged keeps the same directed minor-plane geometry and1/8-pixel extension, but uses minorCode=nearest(31*minorCoverage), majorFactor=0 for zero overlap else min(32,ceil(32*overlap)+1), combinedCode=floor(minorCode*majorFactor/32), and alpha=floor((263*combinedCode+16)/32), with generated mask combinedCode>0. It has no observed-level lookup or per-pixel branch. Eight CPU arithmetic/domain controlsc38cb4 pass. Frozen study065184/exit0 proves the refactor preserves all7168 old predictions, seals all new predictions before whole-corpus matching, and exactly matches all3072 original axial plus4096 corner frames. Report build/smooth-directed-axial-study-root-2/result.jsonc9321170297e2a10232d76249da721f4a30166c5f15017649d449da12291b82a and saved regeneration2e340a/exit0, build/smooth-directed-axial-saved-review-root-2/result.json9d9feabf81ff9419f0acde1a02249e650bea3c3edb2f9a9ac39bd8edd4c92bb6, show zero differing RGBA pixels over7168 rows. This closes the tested axial white-fragment training mismatch only. All3968 original oblique rows remain unrepresented; new holdouts, general fragments/state, normal-scale bounds, GPU/width reuse and all platform/release gates remain. No full model is selected and the shipping renderer still refuses smooth coverage. Original13 objective unchanged; AGPL/original BSD intact; cybersecurity excluded; rejected cleanup targets untouched.

Continuation checkpoint67, 2026-10-21: Explicit RGBA32F observation support retains raw float32 bytes, requires actual32-bit GL_FLOAT attachments/channels, and preserves the default RGBA8 rules. CPUa62866 passes137 controls. Source4 freeze704b8f retains20 source/evidence/license members at build/smooth-training-source-root-4/authoring.json450c38de89ee3eb41d84d9550587aba95aa7d6257115598f196d41819a665134. Restricted no-tools format review280f0c/session81373 closes18b0e2/exit0, child72196; responsee5b8273fd17f9543fac326ded71633b1b7d34b0bef1021ce01b2edb4ef872799 is READY_FOR_SCOPED_FLOAT_OBSERVATION. Root retains its unobserved clamp/pixel-transfer and driver-profile limits in admission and final saved result, and counts negative-zero bits rather than dropping them. Actual Source4 coordinatorf27c16/session88987 closesffb70f/exit0, launcher72000; six direct children63612/33768/45816/69060/72112/65868 are waited. Envelopeacec2cac8b282db40b379ec0f1a13206922c1b8a5803797c052c5ee0dfcb4363 and parent992b72cbe2b849c51af5615b95e52f285fcdfff9acdd778393dfc50dc80e08ef retain source/native4/namespace/lifecycle preservation and cleaned external environment. Worker7297baaaaf33df6160eade41f7fb1a04765ccb373ca605431073545d45a1bcbb contains7040 accepted rows plus64 repeats. Saved review4b56ef/exit0, build/smooth-float-saved-review-root-4/result.json1faf1f92bbbaceaf9cb0e98de6a82abfdaa4fad3afab012284b2605f479361ff, validates all state/hash/complete-command/float-bit gates, but generated alpha is only1.0 and masks differ in every row (326366 pixels). Both fixed float64*255 nearest conversions differ in553968 pixels across all7040 rows, max255. This experiment cannot expose pre-RGBA8 coverage; it is not used to fit a conversion or claim a universal float-target rule. ARB_color_buffer_float's primary specification describes coverage multiplying floating alpha, so the observed divergence needs its own explanation.

Normalized RGBA16 control adds only a distinct16-bit UNSIGNED_NORMALIZED attachment with standard GL_FLOAT readback. CPU3deff8 passes139 controls. Source5 freeze44a716 retains20 members at build/smooth-training-source-root-5/authoring.jsondbcaf380b743965b37854770fc75cfd72aa90fc8a5530ba33793b45ef0bd57c5. Bounded delta peer reviewc8e2ba/session58404 closes104cf6/exit0, child69140; response675e25fe35ac2cefba1ea8885bca5ecc975af2f3e9cbe4ccb699cc71c0289de4 is READY_FOR_SCOPED_NORMALIZED16_OBSERVATION. Root records quantization/tie-rule/target-path limitations, reports grid error without a fitted threshold, and retains the Source4 failure. Actual coordinator2941db/session83621 closes ee0c23/exit0, launcher63668; direct children28804/69920/68768/75344/76712/74832 are waited. Envelopef8432d677c51df5063064984938db3a54e777dc1ddba13ead8073082f93c0997 and parentffcb393b47d26656c12781b3126632c80f804fa0727f800726b8bff94cb13737 retain identical source/native4/namespaces, actor exit, Qt/parser/stream closure and automatic environment removal. Saved reader3c6e2b/exit0, build/smooth-normalized16-saved-review-root-5/result.jsone413f4d7e022e1577e5ddbc72f8025fabef812181de19d49688414ebd631220f, checks7040 frames/64 bit-identical repeats, with zero mask differences against Source3. Both predeclared nearest conversions nevertheless fail5980 rows/261718 pixels, maximum error1. Observed maximum16-bit-grid reconstruction error is1.4722347259521484e-05, not a claimed raw internal precision. No alpha table is made shader code.

Exploratory training-derived bit relation bccc20/exit0 preserves those failures and separately proves nearest(float64(normalized16)*65535)>>8 equals all7040 Source3 RGBA8 whole frames, zero differing pixels. All537127 partial-alpha fragments have zero low bytes in their reconstructed16-bit code. Report build/smooth-training-fixed-transfer-analysis-root-6/result.json438ec8e82dd79544eca12ad667a7355193fed8e614b2a890898b71f86bd622ed is explicitly post-observation, not a predeclared conversion pass or a selected physical mechanism.

New tools/smooth_line_directed_axial.py implements one CPU-only integer hypothesis using directed4-bit antialias-ramp intercept snapping,1/8-pixel endpoint extension, separable overlap product, nearest31 quantization and fixed integer alpha expansion, with no observed-level lookup. Six arithmetic/domain CPU controlse4473e pass; all oblique/degenerate/thin cases refuse in this exploratory component. Source and all3072 predictions are frozen/sealed before complete comparisonceaa26/exit1. Report build/smooth-directed-axial-study-root-1/result.json388728280a28c359763a3ea785bc2a98b9f1c3338ded367eaf3ba62f681ba69e honestly REFUSES:2304 frames exact,768 frames each with one incorrect endpoint pixel, maximum channel error9. Saved localization847f47/exit0 independently checks source/prediction/reference pins and every difference: all768 lie at the partial terminal major coordinate52, with zero other differing pixels. Its report build/smooth-directed-axial-saved-review-root-1/result.jsone7207f0dec3c681568126800296dc6b37f0b36a03e4f5cdd5c83b2c0d05e73aa preserves the whole-hypothesis refusal. All3072 axial interiors match; all3968 oblique training frames remain outside this draft. Frozen failed source, raw predictions/seal and report stay retained; no per-pixel adjustment, tolerance or final-model promotion occurs. Next work is the joint endpoint/minor-edge kernel and oblique arithmetic, with prospective training controls where needed; original7040 references and reserved holdouts are unchanged. Shipping renderer still refuses smooth coverage. All13 original release requirements remain open; AGPL/original BSD intact; cybersecurity excluded; no live actors or owned consumer environments remain, and cleanup-rejected targets are untouched.

Continuation checkpoint66, 2026-10-21: Source3 adds observed/disabled line stipple and alpha test, exact read-buffer/pixel-pack/PBO state, venv NumPy/PyQt6/sip module paths, removal of the temporary sibling import path and parser instance hook, and64 separate end-of-sweep repeats. The7040 descriptors and rejected800-member family stay unchanged. Provider CPU6d2ec2 passes111 cases; complete-command CPU18e8b4 passes10 more, including non-FUNC injection, wrong upload offset/order, shader and attribute mutations. Source3 freeze4b3b89 retains18 members at build/smooth-training-source-root-3/authoring.json136faa8b652914ee42bb82c5635b5923d80c9dfc53589c27e683ed721fff59fa. Restricted no-tools peer review0da72f/session16624 closes7b4262/exit0, child75328; responsebc70f6b5d7287b075f8aea1a58fdcf4306e99b38ca49cfa6134a4964cfc16a34 is READY_FOR_SCOPED_TRAINING_OBSERVATION. Root corrects its shader-recording finding using actual pinned Source2 GLIR85e9a3: this upstream sends DATA+string and both sources are recorded. No setup draw is added. Worker command validation remains FUNC/DRAW/final-upload scope; saved review now checks every chronological command, exact first-draw lifecycle, shader sources, stride, upload offset and order. Installed-upstream scope remains11 pinned files, versions/module paths and wheel-hash-at-install.

Root catches a coordinator-only export-pin issue before capture: the old full export hash includes absolute temporary paths in its comment header. Corrected external launcher uses --no-header and pins the unchanged dependency-body hash fb9298ab292843c93b568963e1e12ea82ae05030d6c9322e4ea1be2e1e68d330; actual CPU exportef02e6/exit0, child15200, proves that identity and cleans its temporary directory. Frozen Source3 sources and the originally reviewed launcher remain unchanged. Corrected launcher pins uv, disables ambient uv configuration, verifies exact snapshot namespace immediately before/after the worker, and observes real worker termination before cleanup. Root admission44d52a pins the corrected launcher, reader and full-command validator. Actual capture82e3af/session92834 closes80cb1e/exit0, coordinator child10200; all six direct stage children37172/64996/68684/66824/70400/62732 are waited. Real worker75680 is admitted through the proven redirector edge and confirmed absent (OpenProcess error87) before environment removal. Envelope build/smooth-native-mechanism-prep-root-1/training-envelope3.json736da86acefebff5538373e29aac8eb60645fe6dfc6bd9a0dd8bf2dea8e3b64e and parent build/smooth-training-launch-root-3/result.json515667c6b563adbec4b4b773bd61e046807ad86ce4e67a6345d7d25913c00b78 retain exact18-file/13-directory namespaces, source/Root native4 continuity, stream/parser/Qt cleanup and automatic external-environment removal. Worker result1e1e9a652ef50cc9d1b9e67a2c7050024b24681db4ce3d8ddf42e21d58dbb73a contains7040 accepted sweep frames plus64 separate repeats. Saved reviewbad228/exit0 at build/smooth-training-stability-review-root-3/result.jsond216968a4afabf10efe5d32d7e01d5143eb8d664db3aa55c3a2acae972af515d checks every frame/hash/state and complete GLIR batch: all7040 fresh-context frames equal Source2 and all64 repeats equal the fresh sweep, zero differing pixels. This establishes scoped observed stability only; unobserved driver-profile and general-determinism limitations remain.

Training-only analysis9bc0b6/exit1 refuses Root's preliminary nearest(255*k/31) encoding assumption: ranks20/25/29 are164/205/238, not165/206/239. Failed source and explicit refusal remain at build/smooth-training-descriptive-analysis-root-3/result.json; no image/capture changes. Corrected descriptive analysis8e389b/exit0 uses observed alpha ranks only, never physical coverage codes or a shader lookup. Report build/smooth-training-descriptive-analysis-root-4/result.json4c7aad4240b937815aa6408ad9d7a8d2d92f5c2f537dd7cbf4ad7ce41a083d37 finds435/3520 reversal pairs differ (10586 pixels), and94/1536 axial transpose pairs differ (7296 pixels). Training-only localization1e25b5/exit0, build/smooth-training-direction-analysis-root-5/result.jsonc429a9a2ebca6be6fd569f158692b7671f75dda527788d3bf6a7b4b73a1d7988, finds6090 reversal-differing pixels in central projected t interval(0.2,0.8); differences extend beyond endpoint caps. These are stable direction/axis-dependent observations, not a causal model. Next work must derive directed subpixel setup and conversion arithmetic, preserve the rejected family, and seal a specified new model before unseen holdouts. No empirical per-pixel correction or observed-alpha shader lookup may substitute for derivation. Shipping smooth refusal and all13 original requirements remain open; AGPL/original BSD unchanged; cybersecurity excluded; rejected cleanup targets untouched.

Checkpoint65 capture closure: Source2 peer review b0dcce/exit0, child69380, returns READY_FOR_SCOPED_TRAINING_OBSERVATION with conditions; response95415e3d7d7e1cc57f2342bbb3cc91e78e5753e5d620a426b51ed8fd88ccf749 and request28d5ee602e13d9cc5929f49916042818f4acd276f006bdaf1bface8d54d87fc2 remain retained. Root admission adds an exact18-file/directory namespace envelope before and after the unchanged reviewed launcher, retains unobserved driver-profile/spec-default compatibility-state/single-shot limitations, and requires saved-row revalidation. No source in the frozen packet is edited. Admission coordinator9e5dd7/session6211, launcher74916, closes f6158e/exit0. Envelope build/smooth-native-mechanism-prep-root-1/training-envelope2.json b897455a87779100a409102a514d8601906a0aa7b23945a4e39de1881c99d24c proves identical namespace/hash checks. Actual six direct stage children48356/59544/65528/64812/60372/52248 are waited; real worker70544 is admitted through the OS-proven one-edge Python redirector. Parent build/smooth-training-launch-root-2/result.json92f9e1b15a3c75bce47955b8b6bbed0f66d028b88613fe76247d0165c0973bf6 retains complete7040 raw/accepted rows, parser/Qt/stream cleanup, exact frozen source and Root native4 preservation, and automatic removal of its owned external environment. Worker result6a63f560e4de33b0048d1b90c26e2d8a6f3642e3ee640dfedbe46dd08d22b556 remains observation-only, not qualification.

Saved reader1c6827/exit1 retains zero checked rows at build/smooth-training-saved-review-root-2/result.json9938b218e7c4b59b433e9c83e83d5e9999c22c66fbd1a05a3d8d8ac182b0f431. The reader incorrectly expected program CREATE/ATTRIBUTE in FBO setup; actual upstream associates the Program/VBO queues on first DRAW. New reader74a73d derives those IDs from the pinned first-row command batch, retaining every shape/byte-length/per-row hash/state/command/identity/cleanup assertion and the failed reader/report. No capture is rerun or data changed. Corrected c5d0fe/exit0 validates all7040 saved rows at build/smooth-training-saved-review-root-3/result.json f7c7820695264c7c0fb8ee503b0f29ac265c443ff82ee0f010360bfef4d41af4. It finds1066122 generated fragments, zero generated-alpha-zero fragments in this selection, and31 observed alpha values:8,16,25,33,41,49,58,66,74,82,90,99,107,115,123,132,140,148,156,164,173,181,189,197,205,214,222,230,238,247,255. None satisfies the fixed4/8/16/32/64 population floor/nearest conversion lattice, a necessary condition shared by all800 predeclared hypotheses. The entire family is therefore REFUTED for this captured oracle before model selection, independent of geometry tuning. This is not mechanism identification or proof of determinism. No holdout is opened, no family parameter is changed, and shipping SmoothReference refusal remains. Next work must address the retained observation limitations and justify a distinct mechanism investigation from training evidence; it must preserve this failed family and all original release requirements.

Continuation checkpoint65, 2026-10-21: The original BSD license remains unchanged alongside AGPL-3.0-only; all three upstream BSD copies hash a28bb857d763513c810ca843558c12cf97f64b990b855c1ce7f5e291e52fc25c. Published main337693e3 CI39600106935 is now terminal SUCCESS: all20 jobs passed, zero failed. This does not qualify the remaining graphics/platform/performance requirements.

The first implemented training-provider packet build/smooth-training-source-root-1/authoring.json f86a3f248fb8a78edb3c7a560a3ca5958aa66709b7ae81ec9b546aa675775949 remains unchanged. Its independent restricted/no-tools Claude review terminates6efa21/exit0 with FIX_BEFORE_CAPTURE, response ec4d327c7222f8368caf4a3a63dfa3b895f68fe77723912d1cb18664a719c948. Root implements isolated direct-script startup, explicit optimization refusal, actual owned FBO/texture attachment checks, compatibility-profile checks, retained failure observations, exact per-probe FUNC operations, and a real training bulk-array reader with scientific-role admission before filesystem access. Four additional exact upstream source pins are available and enforced. Driver application-profile overrides remain explicitly unobserved; no global settings are changed. Existing process-identity helper remains unchanged; its self comparison is schema checking, while actual actor/image and redirector lineage are checked against the frozen interpreter by the parent.

CPU run21db31 exits0 with96 cases, no failures/skips, XML build/smooth-native-mechanism-prep-root-1/provider-controls-4.xml 6074775745150e4e9bb0e458e32c84f2feda0ffe9495e92d5e1685752fa4f9f0. Temporary reader/sink control directories are automatically removed. New source2 freeze a7568d retains18 members at build/smooth-training-source-root-2/authoring.json 8196fe412765a29123737ce0354f2767a9ee7f575cdaebc39d898138de45196f; it grants no capture authorization. An initial preparation8b7fef failed its exact loader-hash guard before creating that packet because an overly broad count replacement also changed a digest; the corrected derivation changes only count fields. Launcher2 invokes the pinned script directly and requires unoptimized -I/-S/-B startup. Independent Source2 review5feeea/session34611, child69380, is active at this checkpoint; it also covers the launcher. A saved-data reader is prepared but unexecuted. No new training frame, holdout, selected coverage model or renderer modification exists at this checkpoint. All13 original requirements remain open; no cybersecurity work; rejected cleanup targets untouched.

Continuation checkpoint64, 2026-10-21: Root traces the remaining axes/colorbar refusal to explicit SmoothReference rejection in cpp/shader/line_consumer.cpp and the runtime's smooth-reference-open policy. No renderer source is changed or antialiasing disabled. Primary Vulkan documentation identifies native RECTANGULAR_SMOOTH coverage-to-alpha as implementation dependent, so it is a mechanism hypothesis rather than parity proof. Actual vulkaninfo inventorye0f465 reveals a previously unavailable-to-this-ledger Intel UHD770 alongside RTX4090. Capability query10941f/exit0 waits both actual children44752/29824 and saves pinned profiles: RTX4090/610.88 supports wide/rectangular/Bresenham/smooth lines, range1..64/granularity.0625/precision8; Intel UHD770/101.7088 supports wide/Bresenham but NOT rectangular/smooth lines, range0..7.99219/granularity.0078125/precision8. Report build/smooth-native-mechanism-prep-root-1/result.json862c52948b8e8728b782608b58396c84d00957bd3f78c195ac3a1b02bc170eef records capabilities only, no rasterization. Native smooth mode alone cannot cover both current GPUs.

Process-local Intel driver selection1f1dfb uses the loader's documented manifest filter and observes only Intel UHD770, without changing system graphics settings. Derived consumer9d479ac4 preserves the exact prior installed-wheel/SDF-clear-Text/notices/uninstall/absence/hashed-upstream-restore contract and adds strict igvk64.json, integrated type, vendor8086/device4680 assertions. Actual consumers340d4f/fb574c/414f8e/32c45c/06f016 all exit0 across Windows CPython3.10.16/3.11.11/3.12.8/3.13.8/3.14.0. The original five audited AGPL/BSD wheel bytes and native module hashes are held. Every owned external consumer environment is automatically cleaned and installed Root native4 remains unchanged. Matrix readerc8f188/exit0 joins all five reports and archives at build/native58-integrated-wheel-consumer-matrix-root-1/result.json2b764ad51efdd288b4d7eb8eb588aad7d8e63e02856fbb2097f017b80d4ba809. This is real Intel hardware installed-wheel consumer scope, not the full integrated scientific/Qt/host/performance matrix. Integrated hardware is now available locally; its earlier availability gap must not be repeated as current fact.

The claude-peer-plan skill is applied for advisory architecture input. Its referenced helper/docs are absent after bounded search, so the installed CLI is used with no tools, MCP or repository access. First bare-mode453f41 exits1 because bare mode intentionally ignores OAuth; it consumes no API tokens and remains retained. Read-only auth observation1dc3f0 proves an existing login. Corrected restricted/settings-disabled invocation461de1/session97942 closes9469f1/exit0, actual child69444, one peer turn and no tool calls. Response build/smooth-native-mechanism-prep-root-1/peer-plan-response2.json de4b8e9c6be61d4ceab1850ef5e3dfe23748616675b2ade3c3128c629466bbff recommends a portable fixed-point coverage mechanism through the existing consumer, with optional native Vulkan diagnostic only. Root retains decisions and explicitly corrects blending-on advice, histogram over-identification, assumed Intel GL availability, direct WGSL bypass, and premature zero-alpha demote/discard assumptions. Both peer temporary directories are cleaned. This is advisory planning, not independent source admission.

New docs/superpowers/plans/2026-10-21-smooth-line-mechanism-plan.md and tools/smooth_line_mechanism.py predeclare a causally distinct finite-sample investigation,7040 deterministic exact-rational training descriptors, fixed GL state, separate generated-fragment/alpha observations and800 coupled later hypotheses. All training RGBA bytes must match before any model is selectable; holdouts cannot break ties or retune failures. New tests/lines/test_smooth_line_mechanism.py passes21controls f0aace and, after state/family completion,34940e with XML retained. Controls prove exact float32 endpoint round trips, unique full training selection, before-any-filesystem-access rejection of nontraining roles, separate generated zero-alpha fragments, a continuous null sharing a discrete histogram, rejection of dense levels for small populations, and invalid observation protocol refusal. No old17 payload/58-family file/8 reserved stem is opened, statted or hashed.

Draft freeze5179d7/exit0 retains14 source/evidence/license members and7040 inputs at build/smooth-mechanism-authoring-root-1/authoring.json f704d831baad75a38fb8113413631df9d9be21fea7f76b0476d3096de0e952d8. Its status is SOURCE_DRAFT_CPU_CONTROLS_ONLY: capture provider not implemented, no independent source admission, no training capture authorization, no raster capture/model selection or shader qualification. Keep this draft immutable while implementing a complete training-only GL provider, observed-state receipts and negative controls under a fresh source packet. The renderer's honest refusal remains. Full viewport arithmetic/overflow, fragment/helper/depth/stencil/custom shader behavior, clipping/topology/instances, MSAA, Metal, all original scientific/host/physical Qt/performance requirements and formal current-source/identity refresh remain open. Current public head337693e3d is clean; CPU workflow39600106935 has15 successful/five live jobs and zero failures at16645d. New mechanism/Intel evidence remains local WIP, not a new push. Original13 objective unchanged; cybersecurity excluded; all cleanup-rejected targets untouched.

Continuation checkpoint63, 2026-10-21: CPU workflow39589646020 at3949f0e188921a153f23d9018b03cd30708f1e53 completes successfully with all20 jobs at451261. The validated source-distribution fix117d6ad10 and bounded Linux/source-archive documentation337693e3dafe0cff8001b775ae9d35ff5a49aa07 are pushed5ebf6d to public main. Remote/head equality and clean publication checkout are verified4887f0; new source-head CPU workflow39600106935 has20 pending/zero failures at96bdd8. Its results are not yet qualified. Both AGPL and exact original BSD remain unchanged. New mesh/layout work below is local WIP and is not in that push.

Thirteen public mesh/filter/layout/text recipes and CPU authoring controls are added at tools/fixture_mesh_layout_extensions.py, tools/oracle_mesh_layout_extensions_capture.py and tests/contract/test_mesh_layout_authoring.py. Initial CPU fixturee545eb exposes float32 sine endpoint noise; explicit polynomial height data preserves the exact boundary requirement and passes16controls29689f before any rendering. First authoring35f7b6eb/43ae18 captures thirteen upstream actors but all fail an observation-only nonexistent gloo.get_parameter query. Parentbc3df6/session13688 closes8d436a/exit1, result8f2254e053d5ab4edb85c51d8c45902af6cb6104a96922e93ad53b70c17d1483; no candidate starts and the external environment is cleaned. Corrected GL parameter observation and a regression pass17controlsace5f5. Source2 preserves all scientific contracts exactly; actual3cf5d7/session81289 closesa973c5/exit1 with12 upstream passes and one raised-mesh clipping refusal, result7eeb7c0db73500cc5a3f23120dd5d6d3100cbbfb1f2814bb7ea008b49f07061d. No candidate starts. Source3 introduces an explicit orthographic depth/flip and strengthens interior checks to reject background masquerading as lighting variation. All18CPUcontrols passe4bc01; actual4eaa20/session61944 closes75e1d4/exit1 with10 upstream passes and3 ambient-only lighting refusals, result7b1ececb7ba0fa648c34c2a821f7799c432f5585f0d0ed8b801428c632486b02. No candidate starts. Every failed source, report and original recipe remains retained, and each owned temporary environment is automatically cleaned.

Source4 only orients the fixed light toward the visible camera-facing normals; geometry, projection, criteria and tolerances are held. All18CPUcontrols pass198112, authoring build/mesh-layout-authoring-root-4/authoring.json c6d88db15f4dccd9e7770467b3fba924cc6e2360780319e590a19a3eab47592a. Actor817d72/session54108 closesdbbcaf/exit1 afterb75621: all13 upstream cases pass, then12 installed candidate cases pass and the required axes_colorbar case fails at generated smooth-line consumer policy. Full parent result build/mesh-layout-capture-root-4/result.json c51a3cf5e28deb11b762f28723a7b1d080ba42d4b35c8a9600ac24ba3a3923f4 remains FAILED_PRESERVED; no full13-case pass is claimed. The actual candidate is the previously audited Windows CP312 wheel105698c7, native module08fccf15, Python3.12.8/NumPy2.5.3, RTX4090 Vulkan hardware. Each worker uses a fresh process and one final color read; no fixture changes after candidate execution. All33 setup/capture children are waited, all eight shutdown fields are zero in every candidate including the refused axes case, and both owned external environments are cleaned. No new local actor remains live.

Saved readerb8c186/exit0 recomputes all twelve complete224x160 RGBA pairs,430080 pixels, with zero differing bytes/no exclusions, plus exact CPU SDF atlases, glyph metadata, font bytes and alpha. Report build/mesh-layout-saved-review-root-4/result.json24e58de10783b54da44fa01d137ad042340e1bae57adb67e59e8fec31ed1e95b has CLEAR_TWELVE_CASE_SCOPE_WITH_REQUIRED_AXES_REFUSAL, not a complete13-case admission or independent-person review. Cases cover flat/smooth mesh,7x5 SurfacePlot, Texture+two clipping planes, Wireframe composition, pre-draw filter detach, perspective, scene polygon offset, clipped adjacent Grid ViewBoxes and three multiline/anchor/rotation text scenes at numeric DPI96/120/144. Actual text hashes/counts4887f0 prove three distinct DPI frames (953/1046/1287 nonbackground pixels). This is offscreen scientific export on the one Windows ABI/driver, not physical Qt/monitor, other-ABI/platform, all-filter/host or performance admission.

Scientific coverage rowsE02/E03/E04/E05/E06/T02/T03/T04 now include that bounded evidence and the actual smooth-line refusal. Supplement build/reports/scientific-fixture-coverage-native58-mesh-layout.json109fff252abefbd3e29017f4a6535f53ca5f7d968f7983fa582d364ff0ecf280 leaves the old inventory intact. Next: retain the frozen reference packet, integrate portable installed-wheel regressions, refresh formal current-source/identity metadata for published helper/packaging and new harness inputs, and implement genuine smooth-line coverage without disabling antialiasing or changing the reference. cpp/shader/line_consumer.cpp still intentionally refuses non-aliased/single-sample policies. Broad scientific/layout/Qt/hosts, hardware/Metal/native Linux and all66 performance/release requirements remain open. Original13 objective unchanged; cybersecurity excluded; rejected cleanup targets untouched.

Continuation checkpoint62, 2026-10-21: Actual extracted-source native build863e12/session64210 closesf8d400/exit0 after same-handle913e25/a12833/56eaba polls, uv child408. Raw /home/heq/vispy-vulkan-gap-closure/sdist-wheel-native58-cp312-run-root-1/result.json c9d61bd71107c48634fd95109c956b110469ed6f53ddaa6b56d16326dc753ffc records fresh full1080-step Clang18/Ninja/Release/PIC Vulkan build from the audited archive, default ten-tree immutable dependency verification, no outside authority or output reuse, unchanged source614/archive/Windows native4. New source tree cd15a4cf0bfa9c0aa93aff33d501d2e3c2d175bca933353056e3f9b5ba794a66 differs from the five-ABI cohort only by the packaging-settings pyproject hash b7ef21fc; package523 and CPP are unchanged. Actual wheel8493040 bytes SHA6d9b4e23ffbfd8cc227984d13b0c57a94a89df3314e7d90432baff602c1641e7.

Saved archive auditc091c9/exit0 retains ELF64/compiled CPP/install-strip lineage, complete package550/RECORD, licenses23 plus distribution22, AGPL and exact BSD, and joins the source archive audit/default dependency verification. Report build/native58-sdist-wheel-archive-review-root-1/result.json4561e0f8e5162d5b2dc99e94d91bd145cab63007e1b5ac01f96a457dfa75fae8. Actual isolated consumer001eb8/exit0 executes eight waited stages4507/4510/4515/4545/4603/4606/4607/4636, verifying compiled SDF/clear/Text/notices under CPU llvmpipe Vulkan, uninstall/absence, hash-verified upstream restoration and import. Its owned external temporary environment is automatically removed. Report build/native58-sdist-wheel-consumer-root-1/result.json262ecc0df150d543404866c4d1408942be4ede0c279b33cc0c09c7e5606168c0. Both licenses and failed predecessors remain retained. No new local compiler/GPU/consumer remains live.

README now describes the bounded five-ABI Linux software scope and actual source-distribution build/consumer scope. Packaging fix117d6ad10 remains a clean local commit, pending publication; remote3949f0e18 CPU run39589646020 has18 successful jobs and two healthy Intel Mac compilations at1c3c46, with no failed jobs. Keep that specific live run rather than restarting it for documentation. Next publication should include the tested packaging fix and current progress documents after the existing source-head CI settles. Formal current-source/identity refresh and all remaining broad science/layout/Qt/host/platform/hardware/performance requirements remain open. Original13 objective unchanged; cybersecurity excluded; cleanup-rejected targets untouched.

Continuation checkpoint61, 2026-10-21: The four remaining Linux CPython ABI builds finish successfully from corrected source614, without project/vendor output reuse: cp310 e0ad82/session48454 closes0d8b21, cp311 0bbc8a/session91284 closesa3c385, cp313 fceac8/session43819 closese6c1e0, and cp314 5719e5/session31310 closesc347e7. The four archive audits verify package550, licenses23 plus distribution22, ELF/compiled-source/install-strip lineage, full RECORD, AGPL and exact original BSD; original request/result records are retained in build/native58-sdist-prep-root-1/original-operations-current-turn.json. All four isolated software Vulkan consumers5b81bf/a58c06/43fb73/15e7b4 pass eight actual waited stages, compiled SDF/clear/Text/notices, uninstall/absence and hash-verified upstream restoration. Their owned temporary environments are automatically cleaned. The existing CP312 scope plus these four join in build/native58-linux-wheel-prep-root-1/matrix-result.json dabfdb48da380490395484452ef72f1b5febdea65cd839eae168dfd4e1355101 via e72e3d/exit0. This is Linux x86_64 software Vulkan and raw linux_x86_64 wheel scope; native hardware, manylinux/cross-distribution portability and broader hosts/science are not admitted.

Actual published-head source distribution4945de/session10838 closes63af53/exit0, but auditf1cdef/session36370 closes62deef/exit1:7773 tracked files are absent. Diagnosis6cb000/session94291 closes330e5f/exit0 and shows required glslang/SPIR-V/Vulkan/Abseil dependency trees omitted by upstream nested Git ignores. A meaningful miniature PEP517 archive regression10712d first fails against the original settings. Narrow vendored includes, generated-file exclusions and that regression pass8f2cba/ef2616 (four cases including existing Python310 hashing controls), with uv lock unchanged. The three-file change is committed locally99a91c at117d6ad1082aa0354653c001cb025fb48234b766, not yet pushed; runtime/package523 and all licenses remain unchanged. The CPU workflow adds only the new test argument to its unchanged matrix/command.

Fresh fixed archive576de8/session18838 closesd89eba/exit0:53260488 bytes, SHA03f5b0e0bdb637b2b936865937bf27cc05417c598964de4805fcfa492ab69c78. Initial fixed auditor79daa6/session63182 closesc043f4/exit1 because its broad suffix check rejects eight exact pinned upstream Vulkan-loader binary fixtures. Original reader/failure are retained; corrected reader5e0a4876 admits only those eight Git-verified fixtures while preserving all Git-blob/completeness/dependency assertions. Actual94c62a/session65764 closes073d0d/exit0: all97508 tracked files plus PKG-INFO, all ten immutable dependency trees, AGPL and exact BSD are verified. Report build/native58-sdist-prep-root-1/audit-fixed-result.json3fd4e6ad2b706e2c43b8f482bed018116f354876b9d6cfecff81fc1d8f293d49. No local generated/untracked payload enters the archive.

The actual build from this extracted archive863e12/session64210 is live, same-handle poll913e25, uv child408. It uses fresh source/build outputs, no outside dependency authority or SDK, default immutable dependency verification ON, Clang18/Ninja/Release/PIC, normal Vulkan/SPIR-V/Tint, INPLACE OFF and12 workers. Source614 includes the exact helper92377234 and packaging-only pyproject b7ef21fc deltas; unchanged package523/CPP/native4 are preserved inputs. It has passed the default ten-tree verification and is compiling343/1080 atf4e4ed; no terminal/archive/consumer claim follows. Prepared extracted-wheel archive/consumer checkers retain the earlier ELF/RECORD/licenses and unchanged probe/rollback checks, with explicit source-archive joins. Source-head CPU run39589646020 remains live with18 successes/two Intel Mac compilations and zero failures ate6fca0/f4e4ed. Remote main remains3949f0e18; push waits for concrete source-build validation. All13 original requirements, formal source refresh, broader science/Qt/hosts, native Linux/Metal/integrated hardware and66 performance rows remain open. Cybersecurity excluded; rejected cleanup targets are untouched.

Continuation checkpoint60, 2026-10-21: Fresh native Linux CP312 PEP517 wheel87224d/session81865 closes608278/exit0 after three same-handle polls, with actual uv child386. The source614 snapshot /home/heq/vispy-vulkan-gap-closure/source-wheel-native58-1 matches corrected Windows cohort tree4a4b05c1d79d08b3d33f477e65666a788b38c05e957b267b4e21c08259e5807f, including helper92377234 and unchanged CPP/package523. No project or vendor build outputs are reused; full Clang18/Ninja/Release/PIC/Vulkan/SPIR-V/Tint and immutable-origin checks remain enabled, SDK empty, INPLACE OFF, contracts/qualification variants absent. Raw result /home/heq/vispy-vulkan-gap-closure/linux-wheel-native58-cp312-run-1/result.json4dd33cf7ecbcbe970afca5b5343cea65c69c151b8808a7b49927ab39b84b0f16 closes with source and installed Windows native4 preserved. Wheel vispy-0.17.0+vulkan.1-cp312-cp312-linux_x86_64.whl is8497038 bytes, SHA4c98f9c1456fdd4d43815aea624734b9b4c734083d381455bed7ee0140214070. The raw linux_x86_64 tag does not establish manylinux/cross-distribution portability.

Saved archive audit567650/exit0 verifies actual FileAPI roots/Linux CPP compilation, ELF64 x86_64, payload lineage including deterministic Release install stripping on disposable copies, exact package550, licenses23 plus distribution licenses22, full RECORD, AGPL and byte-identical original BSD. Result build/native58-linux-wheel-archive-review-root-1/result.json77d55964ab237d64a534e8aeb816c9c81391a975b01df6170e053f8c96abfa37, seal7f3121f9733d6153d19841b2182e3a939fd5376cdab5370c637ddd1573ad935d. Original compiled ELFs are unchanged and strip temporary copies cleaned. Actual clean consumer d55776/exit0 executes eight waited stages: create/export/hash-verified install/unchanged SDF-clear-Text probe/uninstall/absence/hashed upstream restore/restored import. It passes on Linux Python3.12.8/NumPy2.5.3, actual Vulkan CPU llvmpipe LLVM20.1.2/software=True, and installed ELF hashes match the audited wheel. Its owned external environment is automatically removed. Result build/native58-linux-wheel-consumer-root-1/result.json419bdf402bca9988d5661f6a90222af84a1bdcf0628361abfc076c2b6d86296d, seal832fa21f9b74e511d2c5f85654f2b0767853bd67a50a0b507683493348ffc6e1.

This adds only the corrected-source Linux CP312 local wheel/software-consumer scope. Other Linux ABIs, Metal artifacts/native hardware, formal current-source refresh after the helper/new-test edit, broader scientific/layout/host scopes and original66 performance/release requirements remain open. Rejected Windows temporary-folder deletion is not retried. No new product source change or publication occurs here; source-head CI39589646020 has20 active/zero failures atf7d9bb. Original13 scope stays unchanged; cybersecurity excluded.

Continuation checkpoint59, 2026-10-21: The Python3.10 origin-hashing fix, three regression cases, unchanged20-row CI plus the added regression file, and bounded Windows five-ABI qualification are published94f704/0a633b at public main3949f0e188921a153f23d9018b03cd30708f1e53. Rootf37ea1 confirms remote/head equality and a clean publication checkout. Exact AGPL and original BSD hashes remain unchanged. New CPU workflow39589646020 is pending at that source head; prior documentation-only39581080352 is still in_progress at this observation and is not treated as success. The last complete20-job success remains39570591551 at3b531defc. Publication originals are retained in build/native58-cp310-hash-compat-prep-root-1/publication-original-operations.json. This checkpoint is local only. All new wheel builds/consumers are terminal, five corrected wheels remain retained, and every external consumer temporary environment was automatically cleaned. The separately rejected hashing-test pytest-temp deletion remains untouched. Next: reconcile formal current-source/identity metadata for the one build-helper change/new test, Linux and Metal artifact scopes, and remaining broader scientific/host/platform/performance requirements. Original13 scope stays open; cybersecurity excluded.

Continuation checkpoint58, 2026-10-21: Fresh isolated Windows CP312 wheel5ef7ba/session68264 closesa63824/exit0 from the immutable Native58 source614 and admitted SDK1891ddd7, without reusing project native outputs or changing installed native4. Initial archive checker469497/exit1 incorrectly expects Linux separators in the Windows layer manifest; its source d97fa01a and failure remain preserved. Fresh checker f6951356 uses the exact CMake Windows sibling path and passes27d24c. Initial CP312 consumer00a784/exit0 verifies compiled SDF, actual hardware Vulkan clear/Text, notices, uninstall/absence and hashed upstream restoration; its owned external environment is automatically removed.

The remaining ABI trial identifies a genuine Python3.10 build defect: cp310945cfc/session83903 closes102411/exit1 because pinned origin hashing calls hashlib.file_digest, unavailable before3.11. Its complete failure and untouched source are retained. Canonical cmake/dependency_origins.py now streams SHA256 in1MiB chunks (before19707b16, after923772347aa1e658a2d64180bdbfbbfe42075ae8af0d32fbc9a2e709b56e0541); every other origin-validator AST node remains identical. Three regression cases pass3630a3, including empty/binary multichunk hashing without file_digest and rejection of changed pinned inputs. Actual Python3.10.16 stdlib-only controls b392d8 pass the same behavior and clean their temporary files. CI adds only tests/contract/test_dependency_origin_hashing.py; YAML inverse e71b36 preserves all20 rows, runners, timeouts and previous assertions. A draft ABI-builder inverse-count assertion4338d7 is preserved; narrower exact replacement60826f passes without changing build criteria. No origin verification or checksum predicate is disabled.

All five final candidate wheels are freshly rebuilt from one source614 snapshot with only this build-helper delta: build/native58-cp310-source-2, source tree4a4b05c1d79d08b3d33f477e65666a788b38c05e957b267b4e21c08259e5807f. Runtime CPP and pure Python523 are byte-held. CP310 retry42299c/session8372 closesaba0ca/exit0; four other fresh builds also close0. Archive reader1771f538 binds actual CMake Release outputs and ABI tags, exact package550 (pure523/native4/licenses23), distribution licenses22, all RECORD hashes, AGPL expression and byte-identical original BSD. Five clean external consumers pass on NVIDIA RTX4090/Vulkan/software=False, with actual Python3.10.16/3.11.11/3.12.8/3.13.8/3.14.0 and NumPy2.2.6/2.4.6/2.5.3/2.5.3/2.5.3. Each verifies SDF, clear/Text, notices, native module hashes, uninstall/absence and upstream0.17.0 restoration, then automatically cleans its environment. Current source tests and installed Windows native4 remain unchanged. Consolidated90c194 result build/native58-cp310-hash-compat-prep-root-1/matrix-result.json6933cb6454cc61d38ab0a09e6f90880ac6fbca37ad43fd685d365c5c962066c8 joins all five real build/archive/consumer reports and wheel hashes. Earlier candidate artifacts remain historical, not the final cohort.

This closes the bounded Windows standard-ABI wheel build/license/external-consumer scope. The canonical helper edit and new regression mean the old formal Native58 current-source identity is historical; a fresh formal source/identity refresh remains pending. No new runtime CPP/Python behavior is claimed by the helper fix. Linux/Metal artifact qualification, broader binding/host/scientific/layout coverage, physical hardware/scanout/residency and original66-row performance/release gates remain open. Automatic approval review rejects deletion of the new build/native58-cp310-hash-compat-prep-root-1/pytest-temp folder with blocked by policy; it remains untouched and no alternate deletion is attempted. The preceding public documentation-head CPU run39581080352 at5c60d1d55 has19 passing jobs and one live Intel Mac CP312 compilation at49de3d; publishing the functional fix will supersede that run, not promote it to success. All13 original requirements retain their full scope; cybersecurity excluded.

Continuation checkpoint57, 2026-10-21: Authorized documentation publication commits3a60d7 as5c60d1d5575c7b022be2d298481482f00b0b30f7 and pushes c707a0/exit0 to public main. Root886561 verifies remote/head equality and a clean publication checkout. Only README and the plan through checkpoint56 change; diff check passesab0b52 and exact AGPL/original BSD/licensing hashes remain unchanged. The README records the completed bounded Linux58 CPU/software checks and the successful20-job CPU run39570591551 at tested implementation commit3b531defca320047a23e90aa4965431067b0e0da. New documentation-head CPU run39581080352 is queued, not passed, and the old successful run remains terminal. Publication originals are retained under build/native58-linux-gpu-prep-root-2/publication-original-operations.json. This checkpoint remains local. All owned capture/Xvfb processes are terminal; failed Source1, successful Source2, saved proofs and runtime/build inputs are retained for subsequent artifact/scientific checks. Next implementation-plan work includes current final artifacts and license audit plus broader scientific/layout/host coverage; missing native hardware/Metal and original66-row performance/release requirements are unchanged. No full-goal completion or cybersecurity work is claimed.

Continuation checkpoint56, 2026-10-21: Linux58 runtime staging3e5808/session61392 closes974dfe/exit0 PID295. Prepared report build/native58-linux-runtime-prep-root-1/result.json1c7d60954069bea2f3d4465d8eb9d40a074d0479192e68480249c4e83c7e61e5 verifies pure523 plus fresh Linux native4 and license3, exact stage530, unchanged runtime dependency12756, the retained accepted Linux OriginalGL6 reference, and current Windows native4 protection. AGPL and byte-identical original BSD notices remain attached. Source1 capture derivationf11797 and freezea3ab08 hold the accepted scientific fixture/contract bytes and full scientific tail AST, with exactly one epoch metadata-label rename. Initial private Xvfb launch170cdb/session76342 closes59bdf6/exit1 before a capture worker starts: its filesystem Unix socket listener cannot bind under WSL's shared /tmp/.X11-unix directory. Failed reportb98ed7a2 and complete Source1 remain preserved; its owned Xvfb392 exits-15 and runtime inputs remain unchanged. No filesystem permissions or shared WSL display setup are changed.

Fresh Source2 derives1bad47 with only two reversible launcher edits: abstract local X11 transport with TCP still disabled, and a fresh launcher output directory. Five other source members, scientific execution, comparisons and cleanup are byte-held. Source seal0f5bbc6e9e345fd5a9598ac2625700e0d01bdb6efe3eb709429b5d203a7631ef binds the failure and prior Source. Actual e405cd/session43822 closes819c62/exit0: launcher281 owns Xvfb375 and direct capture child378, and both children are waited. Launcher result69bf2588e0aaacf3d2f6a0cf1a6bd4a1486ee376652c91e9e472251b39df813c joins capture build/evidence/native58-linux-cull-candidate-root-1/result.json164a7dd52950928093d2d6d92afa0d3692c0704dfbba4a5db45ef68a30f8d2cf, seal29ad61875c17bd4733acd0b84d17cd92adf2608b2c419305eb2b7d354bc0860a. All six cases pass with actual Vulkan/CPU/software=True, llvmpipe Mesa25.2.8. Current source, stage, runtime dependencies, installed Windows native4 and cleanup remain intact. Source2 literal operations are retained in build/native58-linux-gpu-prep-root-2/capture-original-operations.json.

Saved-only Root reader85e9245b4ccf36d6bd880ee655638da15004d0f629a5f56fa73cd2e492fd4799 executes c53832/session81202 once and closes73d79e/exit0. It reuses the unchanged scientific saved-validator AST1586ee74 and draw conservation helper4c61b37f, binds283 saved inputs, and admits build/native58-linux-cull-saved-review-root-1/result.jsonddb0c10b70ff2c711625c585740e676b20ef068b2e514fc7b75e3e16bf1afe03/seal63098a7a7bd2fef17022bf4f0033c969b754db6b94d6eb73a16d9bddb5968bf5. All9 whole frames/27 attachments independently match analytic and retained OpenGL bytes;17 semantic/physical-user DRAWs conserve the declared intervals, six measured X11 warmups have retired ownership, and case/shutdown counters clear. No provider or GPU is imported by the reader. This is an explicit Root-only software audit, with no independent-person Source/outcome admission or separate X11 endpoint identity proof claimed. Native Linux hardware, Metal, physical scanout and performance remain unqualified.

Public CPU run39570591551 at3b531defca320047a23e90aa4965431067b0e0da is now terminal success:20 jobs passed, zero failures, zero active (8c19f3, head and URL95ee60). The README records this pinned run and the new bounded Linux result. Native58 CPU44 and software cull6 are now completed local scopes; final ABI artifacts/license audit, broader scientific/layout/host coverage, native hardware/Metal and original66-row performance/release requirements remain open. Full original13 scope is unchanged; cybersecurity excluded.

Continuation checkpoint55, 2026-10-21: Linux58 fresh build4d81a1/session74162 closes9a131d/exit0 after six same-handle polls. All42 project targets build (148 project steps after1053 dependency steps), actual discovery child3818 finds44 tests and CTest child3819 passes all44 without skips. Raw result /home/heq/vispy-vulkan-gap-closure/linux-build-native58-run-1/result.json681a25d50dfd589368eac943dac0aef14f96f3130f453b7c70fafb3de50b0f63 preserves exact source4699/dependency120670 after checks, tool/native4 preservation and separate Linux ELF3/manifest1. No installation or graphics provider execution occurs. Full literal start/poll chain is retained in build/native58-linux-readiness-root-1/build-original-operations.json916f93fae202661a81dfe455d644c320761b147db6932f8c9ecf88ab602bea39. Separate unchanged saved reader b7ebc5b5 executes once67498a/exit0 and clears its explicit Root-only scope in build/native58-linux-build-saved-review-root-1/result.json1f097d119800464497c17033cc4b1172f1287257ee75bc617269ade3f18272c0, seal995752b4cc10f638db738b3306492c75de2cedd406cfbf598f19ebb4a2f0db6f. It binds4820 saved inputs, all42 actual target/compiled-source groups and44JUnit passes, generated Clang18.1.3 compiler identities, Ninja/Release/C++20/PIC/platform definitions, ELF64 x86_64 artifacts and exact source namespace. The point_contract and input_batch_cache_contract changed CPP sources are explicitly compiled. Held validator functions remain unchanged; this does not claim an independent-person Source/outcome admission or replay of the full relocated dependency pass by the saved reader. Source and the original BSD/AGPL notices remain intact; the completed build is retained for the next capture and artifact checks. CI39570591551 is live with15 successful jobs, five active and zero failures at7da735. Next: prepare the new Linux runtime stage and exact software-Vulkan capture, then saved graphics/artifact/license checks. Native Linux hardware, Metal, broader scientific/layout/host/ABI coverage, final artifacts and all original performance/release requirements remain open. All13 original requirements retain their full scope; cybersecurity excluded.

Continuation checkpoint54, 2026-10-21: Fresh Linux58 preflight f3fdce/session18866 closes a0c7c3/exit0 after same-handle a1d3e7. Actual result /home/heq/vispy-vulkan-gap-closure/linux-build-native58-preflight-1/result.json8f079c573b4c4a90660154f1018d32a520ca4a9b24394435b0ecf64f7e5c15a4 verifies the full exact4699 source namespace, relocated120670-file dependency namespace, original3172114549-byte transport archive, six exact physical tool binaries and separately protected current Windows native4. Root source inspection c3d732 checks syntax and the fixed five-stage full recipe without claiming an independent-person Source review. Fresh build driver c94b4d5f9b4f63dd62470ad0cc3107bf28579f7ba9c1c26cee20d8472e3be574 starts4d81a1/session74162, actual configure child393; configure exits0 and dependency child1121 starts69595f. Full1053-step dependency build closes0 at735e4f, project child3467 starts. The build remains active at that observation; actual42-target completion,44CTest and saved admission are not yet claimed. Separate saved reader b7ebc5b5207ff04a5d48f6d7a45792ee42c52c9c367628ba75b5659b6dea4210 is prepared with the ten unchanged accepted codemodel/ELF/compiler/JUnit validator function ASTs; it never executes the old audit, main or current guard. Its source inspection9a357d is metadata only. Planned outcome retains explicit Root-only review scope and does not invent an independent-person admission. CPU CI39570591551 has14 successful jobs, six active and no failures at974695. No runtime provider/GPU import, installation, hardware or performance qualification follows from this checkpoint. All13 original requirements remain open; licenses retained and cybersecurity excluded.

Continuation checkpoint53, 2026-10-21: Native58 Linux source preparation completes d6bd71/exit0, PID360, at /home/heq/vispy-vulkan-gap-closure/source-work-native58-1. Snapshot result build/native58-linux-readiness-root-1/snapshot-result.json (c28222d79f0e3a20b8d8b3b8578af3b545c5cca0352a69090d586ddcc08d0c3c) verifies the exact4699-member union: source614, formal harness4131 plus tools4, package523 unchanged from57. Ten changed/added logical leaves match the admitted57-to58 maps, including the three license files. The old Linux57 namespace4696 is unchanged before/after; both declared dependency links are retained without auditing their payloads. Original LICENSE-BSD is byte-identical to the retained upstream notice; AGPL is attached. No native binaries are copied and no compiler, provider or GPU is invoked. An initial preparation is deliberately interrupted because repeated Windows-mount metadata checks are slow; its source and available literal operation records remain retained. The revised script separates logical Linux exclusion checks from physical Windows replacement reads, preserving the byte checks. Only its redundant interrupted source copy is removed fab144/exit0 after the successful replacement snapshot. Build command preparation0889ae derives the unchanged five-stage direct-source recipe, all42 project targets and exact44 CTests (build-recipe.json08095fb5), without invoking them. Fresh producer/saved-reader admission, physical dependency/toolchain verification, actual build/CTest, artifact/license audit and software Vulkan capture remain next. This is a source-snapshot checkpoint, not Linux build or graphics qualification. Original thirteen requirements remain open; cybersecurity excluded. This checkpoint is local while the existing public CI run proceeds.

Continuation checkpoint52, 2026-10-21: Authorized publication completes ef71d2/exit0 at public main3b531defca320047a23e90aa4965431067b0e0da. Root7870fd independently confirms remote equality and clean publication checkout;95a728 observes new full CPU matrix39570591551 queued at that exact commit. The published README records the newly closed bounded uniform14/reuse2 qualification, the plan includes checkpoint51, and Intel Mac CPU jobs receive90 minutes with all20 rows/checks preserved. AGPL LICENSE, exact original LICENSE-BSD and LICENSING.md hashes remain identical across canonical/publication copies (76fe08). Publication requests/returns are retained in build/native58-ci-observation-root-2/publication-original-operations.json. The cancelled prior run remains cancelled; fresh CI is not yet passed. This checkpoint is local only while the new healthy run proceeds. Next work retains the original thirteen-requirement scope: broader current rendering/scientific and platform/host/artifact/performance qualification remain open; no new cybersecurity work.

Continuation checkpoint51, 2026-10-21: The completed Source9 saved reference reader267400/session36172 closes8693d9/exit0 PID69716 exactly once, admitting reference a8ec16b2/eb2a3b5f. Root92add8 verifies the full saved boundary6b3f49bb/1d1223db and reference-reader carrierd182b898/b3c1b194, retaining1457 reader input bindings plus one external witness without replay. Root's own02870f compact compatibility-field selector refusal and physical before are retained; the corrected check uses the actual original_table_state_restored field and disclosed upstream-only compatibility scope. No Source or acceptance condition changes.

Candidate inputs868d2deb bind that exact new reference and unchanged current runtime roles. Fresh candidate path receipt10d185b9/908aa2eb covers61429 names/30 roots; Root9417c9 verifies full carrier1208f9f4/755a6ceb. Sole actual candidate9f5527/session40453 closes3ef54d/exit0 after same-handle39d9d5, driver61024/direct child67312. All14 tests/14 test frames plus2 reuse frames pass. GPU shutdown completes with all14 declared logical cleanup counters zero, immutable inputs and native58four preserved, one full parent/zero child identity admissions. Actual P0 device metadata identifies hardware Vulkan, NVIDIA RTX4090, software=False. Root closer9b5328 binds the whole capture4d4b0025/056b7f4e and all three actual calls into outerdcb0cdda/5e446606. Candidate raw stream90101658 and literal closer are retained; no actor replay.

Joint saved path receipt944776d3/0a409249 covers61445 names/33 roots. Exactly one unchanged joint reader49476a/session14549 closesb4eeab/exit0 PID64672, admitting60990bb6/0c833088. Rootf0e192 verifies both full boundary2dc3c067/506e27f8 and joint-reader carrier31ca225a/8367a607, all three original reader calls,1543 admitted bindings plus one external witness, all14 original assertions and sixteen complete candidate/reference arrays (4096 RGBA bytes) byte-exact, same-generation uniform-only reuse/counter windows, complete cleanup and reference15 teardown/restoration records. Immutable checkpoint build/native58-uniform16-qualification-checkpoint-root-9/progress.json2c7bd381/seal2fed7280 closes only Native58 CP312 Windows normal uniform14/reuse2. It does not qualify all R04, other ABIs/hosts/platforms, physical presentation or performance.

Public CPU run39558254054 is terminal cancelled with19 successful rows and zero test-failure conclusions; Intel Mac CPython3.14 job119083065884 hits the60-minute job budget during still-progressing Dawn compilation at93%, before CPU tests. Its complete formatted log is retained under build/native58-ci-observation-root-2; it is not promoted to success. The CI matrix now gives Intel Mac90 minutes, other targets60, with all20 rows, runners, build/test steps, triggers and assertions unchanged (real YAML parse/structural comparison6659d6). README removes the obsolete unqualified-uniform statement and distinguishes older bounded qualification. README/workflow are outside the qualified Source614/identity checked map; runtime evidence remains unchanged. Fresh CI on the timeout adjustment is pending. All13 original release requirements remain open; AGPL and exact original BSD notices remain attached, cybersecurity work is excluded.

Continuation checkpoint50, 2026-10-21: Fresh upstream path receipt dc59167e/bb9f3dd8 passes the exact frozen path gate. Its sealed plan covers61361 declared paths,60 complete pin-role maps and22 inventory roots; the author final count61362 adds exactly its own receipt directory. Root's initial761040 selector incorrectly expected the final count in the sealed report; physical before and failed return are retained, and corrected2accd4 passes without changing the receipt or Source. Root16645d verifies the complete nine-operation path carrier36635e1a/16215715 and all60 finite metadata bindings, preserving three own prepublication schema refusals and zero target/native/archive/scientific/external payload calls.

Sole actual Source9 upstream capture3b1eee/session62733 closes d1de26/exit0 after same-handle poll638716. Driver71676 directly launches child64684. Both report PASS_UNIFORM14_AND_DISTINCT_REUSE2:14 actual tests/14 test frames plus2 distinct reuse frames, lifecycle entered/15closed/15disposed/0embedded/restored, GPU released, immutable inputs preserved, installed native4 unchanged, one full parent identity admission and zero child admissions (Root metadata observationbc8ed4). Capture0f867f6d6adf08b19828d4e1a0d6622a5a46098b5b1d41729a2ab8f7b6e35a2a/seal1e9bf52f4f08be034c0fe72bc2295a51221638876ad941b253c32cb22d65c0a2 is retained under build/evidence/native58-uniform16-upstream-root-9. No candidate run has occurred.

Actual Root closer434a1b/exit0 verifies the whole new capture packet and all three literal original process observations, creating outer6b2782a3/dd3152dc. Complete raw tool stream6de2f6fe and actual closer request/return are retained under build/native58-uniform16-upstream-process-root-9-raw. New saved reference inputs e55184a1 bind the exact Source9 producer/source peer, actual upstream inputs, capture and closed Root process. Independent saved-input boundary and unchanged Source9 saved-reader review are next, with no guard/current-identity/provider/GPU replay. The new frames are not yet an admitted reference; a matching candidate/joint comparison and all remaining release requirements are still pending. All13 original requirements remain open; AGPL/BSD notices remain attached and cybersecurity work is excluded.

Continuation checkpoint49, 2026-10-21: Independent Source9 review a35289/exit0 PID70644 is CLEAR with2037 checks. It verifies all64 frozen members/899 known pins,938 producer/926 reader/965 unique needed bindings, eight exact command vectors and the corrected consumed Vulkan environment reset/record. Fifty-one final files and185 complete definitions are held; thirteen changed files and seven raw inverses are explicit. Science, lifecycle, formal58 and saved_metadata bytes remain held. Root5b90e6 verifies all974 finite carrier pins and all five original Native/five original Root operations in carrier760dbd85/653f335a. The reviewer's own4a3818 historical-control selector refusal and exact correction remain preserved; it is not a Source finding. Source8 remains refused.

Actual direct Base own-Source gates ce3919/exit0 PID65008 and b051b6/exit0 PID27568 pass, without current-identity or provider replay. Producer Root Source admission82e2934b/ea9171d9 and readerdcc84ebd/c3ea9743 are retained under the exact source-review-root-9 folders. Root closer c74f81/exit0 binds their literal argv, two full original terminal returns and actual self-reported PIDs into producer outer1d885c40/d1313891 and readerfb048613/65e712c3, with no invented OS-parent edge. Original calls/closer are retained under build/native58-uniform16-source-gates-root-9. Independent upstream path-only review is active for the exact frozen pair, these completed gates, actual runtime inputs92c41c9e and fresh upstream-root-9 outputs. Its completed receipt/carrier must be verified before the sole actual upstream GPU capture. No Source9 runtime/provider/GPU has run. Public CI39558254054 remains live with15 successful/five active rows and zero failures at609a5a. All13 original requirements remain open; AGPL/BSD notices remain attached and cybersecurity work is excluded.

Continuation checkpoint48, 2026-10-21: Source8 independent review completes 1863 checks but refuses two material findings: fourteen stale command-template script/helper/output joins, and inherited consumed VK_ADD_LAYER_PATH absent from the recorded child environment. Actual3d9903/exit1 PID64672 publishes refusal ea82e8cc/4035a7d8. Root7042dd verifies all961 finite pins and the complete nine-operation carrier a84d72a6/f955e803, preserving both findings and the limited transcribed provenance of the four original Root freezer calls. No other build-projection, Source3-format, saved-facade, lifecycle or scientific finding was reported. Source8 remains unchanged and unadmitted.

Fresh Source9 drafts correct command vectors by generating them from actual own scripts/hashes, use new output paths, and clear inherited VISPY_/PYTEST_/DAWN_/VK_ and PYOPENGL_PLATFORM before explicit route configuration. Child command records disclose removed configuration key names plus explicit layer/driver/dump values. The actual consumed shader-dump switch was already cleared by the old VISPY_ rule; arbitrary BACKEND_SHADER_DUMP is not claimed to be a consumed switch. Root59bec2 passes48 correction controls, including both routes with injected settings, eight actual command vectors and invalid script/hash/output/late-role cases. Scientific fixtures, thresholds, teardown code and formal58/saved_metadata functions are byte-held.

Source9 freeze5c473c/exit0 PID46944 creates producer source-seal e5b99b50aec5aa8206043f5be6c45f148803fffa49b0e26dade7c2e28bda1bb4;602c96/exit0 PID36756 creates reader adeb6c4840e4d2dc3b77f2d85154967b959d570692062c05a053bb0f924cb67c. They contain38/26 members,899 known inputs and twelve control records, including the preserved Source8 refusal and exact old Source bytes. Original prepare/control and contract/freeze operations are retained under build/native58-uniform16-prep-root-9. Independent Source9 review is active. Actual new upstream-inputs-root-9/inputs.json92c41c9e copies unchanged current runtime roles only; all reference roles remain null, and no capture or previous pass is inherited. No Source9 provider/GPU run has occurred. Latest public CPU run39558254054 has15 successful rows and five Intel Mac rows still in progress at observation1ae5b3; no failure is reported and the healthy run is left running. All13 original requirements remain open; AGPL/BSD notices remain attached and cybersecurity work is excluded.

Continuation checkpoint47, 2026-10-21: Completed Native58 saved identity admission f18a5748/4989ff37 passes its single unchanged consumer fc8fc7/session1129 through 7ea4fa/exit0, PID66036. Root fd442b verifies the full six-operation carrier bd890dd4/42ab5a1b, all five original Root stage/identity operations, the exact 5411-input admitted map and 5403 identity-map subset without payload replay. The reviewer's disclosed missing literal arguments for one pre-boundary dead-code tidy remain disclosed; actual process requests and returns are retained. This admits identity metadata, not graphics hardware.

Fresh Native58 Source8 producer/reader now explicitly consume the raw Native58 completed-build receipt through its reviewed projection, with 19 negative controls and one actual build-gate check. Root 5315de passes 79 fresh routing, exact teardown-receipt and whole-frame controls without providers or identity-consumer replay. Root 5148c1 checks all 753 historical known inputs at their original Native57 paths; old captures remain historical. Five stale current contract/review metadata routes are corrected, with scientific fixtures and lifecycle code held unchanged. Fresh runtime upstream inputs 92c41c9e contain actual new identity/build/activation roles and no inherited reference.

Initial source freezer attempts 0caf79 and bc2ca7 refuse a transitive canonical regression-test row outside the transport's permitted metadata namespaces. Correction cf8b76 removes only that redundant direct row; its enclosing independently reviewed Source3 seal remains pinned, and freezer code is unchanged. Final producer freeze e5f08d/exit0 creates source-seal ddf76162afc4ecadf6231f23410ad5ead54428c427dd4f97154693cfb3e0fc03 (38 members); reader freeze 236dc8/exit0 creates 12bb187255def78b7c5ae4f5f8a99a84dec7e47d812be1c7c1723a35347970f7 (26 members). Both bind 821 known inputs and eleven control records. Independent Source cross-review is pending; source peer admissions and path gates must precede actual upstream14 plus reuse2, saved reference, candidate and joint qualification. No Source8 provider/GPU run has occurred. Original AGPL/BSD notices remain attached. All13 original requirements remain open; cybersecurity work is excluded.

Continuation checkpoint46, 2026-10-21: Identity Source3 is independently clear with232 checks (d6fd5f1d/b5260fae), including all relative-root, linked-root, five-flag and omitted-input regressions. Rootc7542c verifies the complete two-call carrier7b50ade9/921c32d0 and all56 needed Source/input pins. Source1 andSource2 remain explicitly refused; none of their failure records was relabelled as success.

Actual source-bound stage53f1cb/session19374 closese3e3ba/exit0 and creates the complete523-file pure package stage under build/evidence/native58-current-python-stage-root-1. All523 copies come from the admitted57 parent stage; zero current replacements or native copies. Stage resultad26627d/seal19383620 passes. Actual identity author5705d6/session95975 closesecb6d0/exit0 and produces identity1731d9400795ca548f0072b3ed474897a0721fda92f9a113cb7314504e750a22, result4833dfdd/seal1b7e180b under build/evidence/native58-current-python-identity-root-1. It records614current source/523package/4131formal+4overlay, installed58/w44 and5403 immutable inputs, with no inherited device qualification. Literal original stage/author argv and all two/three returns are retained under build/native58-current-identity-controls-root-3. Independent completed admit_identity consumer review is active; it must preserve the separate legacy saved-admission schema expected by existing consumers. No graphics/provider/native module import occurred during metadata production.

All20 CPU CI rows succeeded on c466640c1. Public main73c31deb783a029d79093286819ca7812edce6cc publishes progress through checkpoint45; remote SHA and clean checkout were verified3d9669. Both AGPL and exact original BSD notices are retained. Next: complete saved identity admission, explicitly retarget Source8 metadata readers to Native58/raw completed-build receipts and exact new identity, then execute formal scientific/runtime qualification and remaining final-artifact release work. All13 original requirements remain open; cybersecurity work is excluded.

CPU CI39550335428 completed successfully on published source c466640c1: all20 platform/CPython rows passed, zero failures (Root7ad7f7/exit0). This verifies the expanded CPU contract/test matrix, including the self-contained56-test epoch-guard suite. It does not qualify native graphics hardware or final release wheels.

Continuation checkpoint45, 2026-10-21: Identity Source1 review f6b43793/06999dba is REFUSED with two material input-identity/Source-scope findings and126 successful checks: inventory could traverse a linked root before validating it, and the Source-specific build_invoked=False predicate was absent. Root7280d4 verifies the complete11-call carrier94987e3a/fd9d9295, retaining the expected ca2601/exit1 verdict and both counterexamples. Root's initial f54d2f selector refusal is preserved separately; it expected an abbreviated verdict string rather than the recorded full finding verdict. Source1 remains frozen and unadmitted.

Fresh Source2 fixes both findings, adds whole-workspace exclusion and passes91 routing plus14 correction controls. Its actual full context b1bf8e/session77985 closescaf650/exit0 with the unchanged614/4131+4/523parent+0current/4839-input/2765-alias topology. Independent Source2 review e0f1b22a/e02df856 verifies151 successful checks but REFUSES one remaining case: a relative root such as '.' could become the workspace root after the first exclusion check. Rootf1dace verifies its complete four-call carrier960f2994/14c57e4a and preserves expected08c22c/exit1. Source2 and all earlier evidence remain unchanged.

Fresh Source3 repeats the whole-root exclusion immediately after lexical absolute conversion, before any root/ancestor metadata or traversal. Exactly one line changes in each of the two guard copies; all other15 Source members are held. Routing91 b14343 and correction18 f93184 pass, including '.', empty, './' and 'build/..' rejected while directory-metadata methods are replaced with throwing stubs. Actual Source3 full context d0c86e/session85525 closes7ab228/exit0 PID65612 with the same complete maps and unchanged installed58. Freeze df3556 binds17 Source members and38 finite inputs, including both refused lineages: source-seal8dc6148a779c8a9056700c5c5eee84c3edad6aa419b60480ab9b7707dec5be87 and guarde130e829bbbb9b67d495a840b42b0db8f052a96ea89cd83982269cbe6e246379. Independent Source3 review is active. No stage, identity or graphics run has occurred. Scientific predicates and thresholds remain held. All13 original release requirements remain open; cybersecurity work is excluded; both licenses remain attached.

Continuation checkpoint44, 2026-10-21: Independent installed58 audit e0b1e4c0/8854eb50 is clear after exactly one unchanged Source3 scanner invocation7e65eb/exit0. It verifies all four installed copies and exact backups/staging/candidates, 644 approved inputs, the complete 622-file approval archive, 614 current sources and 523 package files. Root536ba8 verifies its full four-call carrier0e5874c2/1552834b and binds all653 independent scanner input pins without repeating the archived payload pass. This closes installed-copy verification only; matching runtime identity and device qualification remain pending.

The Native58 identity/stage implementation is prepared under build/native58-current-identity-root-1. It explicitly consumes the raw completed-build receipt through the reviewed projection and the new installed audit, reads admitted57 identity metadata without rerunning its now-stale current-native guard, preserves parent56 history, adds explicit parent57 roles and actual57 backups, and keeps frozen c113 and current CI7e286 guard inputs separate. All 523 pure package copies must come from the admitted parent stage; there is no current parser replacement. Actual read-only context011d3f/session68649 closes0cad79/exit0 with614source/4131formal+4overlay/523parent+0current,4839 immutable inputs and2765 exact historical aliases. Binding controls72bcd9/exit0 reject91 invalid cases and verify unchanged historical scientific-validator AST. Final source-only schema enforcement is covered by those controls; no production stage or identity has run.

Source freeze f04676/exit0 binds17 Source members and28 finite metadata inputs: source-seal c911b6f2355e70b8197987a87398709985ff3b3b5356b0629789e909bd480a01 and common_guard92dab89d56a8ef3cf6aa05955599696955374c40b94d0c1cff2c857aa5cdd981. Independent Source review is active. Actual identity input spec7608c90b is prepared under build/native58-current-identity-inputs-root-1; its handoff explicitly remains a projection rather than relabelling the original independent build report. Latest CPU CI79d03f has17 successful jobs, three Intel Mac jobs running and zero failures. Next: complete identity Source review, produce the real523-file stage and identity, independently admit the resulting consumer, then retarget and execute formal Source8 qualification. All13 original release requirements remain open; both licenses and third-party notices are retained; cybersecurity work is excluded.

Continuation checkpoint43, 2026-10-21: The complete Native58 activation adapter/loader review is clear with 193 independent controls (e635703b/67872708). Root ecd3cc verifies the full eight-call review carrier, including both preserved reviewer harness/selector refusals. Actual metadata author85ad6c writes input spec a5552c1c; source-bound preparefe626b publishes approval31e00ac6; read-only preflight864440 passes. Actual activation2d11ec/exit0 PID72316 commits activation61aa5915 and installs all four reviewed Native58 files. The unchanged Source3 transaction retains exact predecessor backups, staging and immutable approval-input blobs. Original prepare/preflight/activation returns are retained under build/native58-process-prep-root-1. Root closer1e7eb7 writes the original-command-compatible activation outer c16371a5/seal87e67192. No provider/device is imported or created.

Root's actual unchanged installed scanner6805bb/exit0 verifies Native58, all four committed copies and the complete immutable activation archive with 649 named immutable inputs. This Root scan is explicitly not independent. Independent installed audit is active against exact five-key input spec0dc198eb under build/native58-installed-audit-inputs-root-1. Matching current identity and formal Source8 graphics tests remain pending. The new pure identity package projection passes actual parent-map checks and 13 refusals (c22c5d/exit0): all 523 package files must copy from the admitted parent stage, with zero current parser replacements. No new identity stage has been created. Latest CPU CI observation275a37 shows 15 successful jobs and five Intel Mac jobs running, zero failures. Checkpoint42's installed57/review-pending state is historical; installed native4 are now58. All 13 original release requirements remain open, both licenses remain attached, and cybersecurity work remains excluded.

Continuation checkpoint42, 2026-10-21: Native58 completed its isolated build and all 44 CTests. Independent completed-build review Native3 is clear for the complete frozen CPU build only; Root verified the final report, both preserved reader refusals and the original 18-operation execution record (cd459c/exit0). Native58 activation, matching Python identity and graphics qualification are still pending; Native57 remains installed.

Public main c466640c1 fixes the epoch guard test's dependency on an untracked local pass25 manifest. The test now creates its own historical fixture and still invokes the real freeze command, requires rejection and verifies no mutation. All 56 guard tests passed locally. Canonical test/workflow files are synchronized while the reviewed Native58 frozen test remains unchanged at c1135c16. The current regression input at 7e2860b4 is explicitly separate. The latest observation of CPU CI39550335428 (8f38b1/exit0) shows 11 successful jobs, seven running and two queued, with no failures. This CPU matrix does not qualify graphics hardware.

The explicit build projection passed independent component review with 79 controls; Root verified its complete original execution record (134ba4/exit0). The implemented metadata loader passes the actual reviewed inputs and rejects 83 invalid cases (102477/exit0). The new Native58 activation adapter retains the five exact Source3 transaction functions, binds the exact predecessor57, all 614 current source files, four archived candidates and the separate historical/current guard inputs. Its actual read-only context and 38 context/source-gate refusal controls pass (dc5922/exit0); installed native4 are unchanged and no production approval or activation outputs were created. The two-file adapter source is frozen under build/native58-activation-source-root-1, actor884b148c/sealc13f53ed. Complete adapter/loader independent review is pending on packet0f74c5c0 under build/native58-activation-root-1. Source approval and real read-only activation preflight must precede copying. Existing transaction controls qualify the unchanged ancestor; they do not independently qualify the new adapter.

The implementation remains AGPL-3.0-only, with the original VisPy BSD license attached unchanged and included alongside the AGPL license in package/SDK configuration. No new temporary build tree was created for these metadata controls. All 13 original release requirements remain open; cybersecurity work remains excluded. Next: finish adapter review, prepare and activate Native58 with original execution records, audit installed copies, build the matching current identity, then resume formal Source8 scientific/runtime qualification and final-artifact release work.

Current progress, 2026-10-20: the eleven reviewed normal source changes are published. Formal Native57/w43 passes all 42 targets and 44 CTests, with installed native files and matching Python identity independently audited. Matching final-artifact normal thin-line13-case/78-frame and isolated qualification-artifact forced64 thin-line13-case/78-frame results have a joint independently clear156-frame review. Original126 (769 arrays/299 exact comparisons), integer128 and Text24 saved reviews are independently clear. The fresh current57-source WSL build also passes all 42 targets and 44 CTests with independent saved admission. The matching Linux runtime is staged (523 Python files and four native artifacts), and its six-case software-Vulkan capture and independent saved review pass, covering nine complete RGBA/depth/stencil frames and 17 user draws. Earlier GPU results retain their original build scopes.

Current continuation: all seven raw cancellation cases pass. The final submitted_open_paint_abort closes118527/session33605 to9fcc1f/exit0, driver41124/child63256. Root verifies its whole37-file packet and closes the original process carrier deccbf4f. The later Uniform3 upstream capture has now closed failed (session39299 to5ec5a3/exit1); no GPU actor remains live. Fresh seven-case saved inputs66a855bf bind every actual driver/worker/Root process, exact argv, runtime and independent four-fault admission. The fresh independent joint saved path review closes at67888 paths/86 roots/309 namedJSON files with zero protected visits; Root verifies its whole carrier and321 metadata pins. The ONE Point-owned saved reader closes e7368c/session5399 to fdaf09/exit0 (metadata launcher21332, actual reader44064). Its independent f7c68ef1 result admits all seven saved cancellation outcomes, checking57,705 inputs; the full original carrier a7fe575a closes with25 polls. Root independently verifies the seven process/input joins,76 selected metadata hashes and all path names without replaying all payload hashes. The corrected Root verification and its earlier typed-wait predicate refusal are separately preserved. These raw passes do not close all R03 or physical-timeout requirements. Wheel attempt1 assembled the CP312 wheel but failed backend cleanup on the legitimate scikit_build_core._vendor namespace package. That failed745-file packet remains preserved. A narrow exact-namespace correction passes47 focused controls and independent Source3 CODE review (1323 checks). Producer Source3 c507a815 and saved reader6de94f18 are frozen; independent frozen confirmation, both Root gates and a fresh737-pin path receipt pass. The actual retry closes0e7aa5/session45150 to f8e4e1/exit0, PID13636, producing the CP312 Windows wheel. Root verifies all744 sealed artifacts, including unchanged568 project and172 backend files, and closes the complete original process carrier. Fresh saved inputs de81ded6 and the independent1499-pin path receipt pass. ONE actual independent saved reader closes e8485e/exit0, PID55268, admitting the6746864-byte CP312 Windows wheel with569 ZIP members and matching RECORD rows,547 package members,19 distribution notices and exact admitted native4 bytes. The full original six-operation carrier closes5821cfd2; Root verifies the whole report/carrier and all1511 pins without replaying the reader. Clean-consumer tests and other ABI builds remain pending. Volume30 reference and Partition256 CPU saved admissions are closed at their stated scopes. All original thirteen requirements remain; cybersecurity work is excluded.

Uniform3 now passes independent Native CODE review (1490checks/418pins) and a separate Root raw-byte/target-helper review (3059checks/112pins). Its producer54692c19 and readerd25af68f are frozen (31/22files;349known metadata each); independent frozen confirmation and both Root metadata-only Source gates pass381/372 needed pins. The gates import no frozen Source modules. Fresh upstream input declarations preserve the exact normal runtime while inheriting no failed frames. The fresh independent upstream path review closes50cb480b with69,169 names/26 roots/224 named JSON files and zero protected visits; its full original carrier108fef3f and all234 metadata pins are verified. The first launch refuses at argparse because the required GPU opt-in flag was omitted; its full original carrier is preserved and no worker ran. The corrected template-derived invocation runs once as Root session39299 and closes5ec5a3/exit1, driver1360/worker62136. Root verifies its complete eight-file failed packet and unchanged installed native4, and seals the full original process carrier ffe33ecc. The failure occurs before any frames: the unchanged GLIR serializer rejects PyOpenGL IntConstant from the new owned target format; the intercepted list is not delegated and cleanup encounters the missing framebuffer. A fresh [one-line constructor-boundary proposal](../../../build/native57-uniform16-format-prep-root-1/review-packet.json) converts only format=GL.GL_RGBA8 to format=int(GL.GL_RGBA8). Nine inert selected controls reproduce the original refusal using actual pinned constant-class ASTs and prove the complete new SIZE command with the unchanged serializer. Source3 remains frozen/unchanged. Independent boundary CODE review closes f79b3ed5 with81 checks, including the complete actual public RenderBuffer.resize AST; the full10-operation/19-pin carrier cc8d230c is verified by Root. Fresh [Source4 transport draft](../../../build/native57-uniform16-prep-root-4/review-packet.json) fa32e377 is now composed:31 producer/22 reader files,40 whole-held files,11 complete raw-byte inverses and two regenerated freeze contracts,422 named metadata/code declarations each,66 selected composition controls. It remaps all eight CLI scripts to fresh Sources/receipt namespaces and refreshes both saved-reader helper pins. The original target authority stays normative with an explicit reviewed format-boundary amendment. All runtime/reference roles remain null. Its complete original Root carrier closes02b3a4a; the initial preflight metadata-field mismatch is preserved separately and ran before any Source creation. Full independent transport CODE review closes22edc6d9 with6,187 checks/541 pins and full carrier9135399a (546 pins); Root verifies the complete packet. Source4 is now frozen at producer88fc42f1/reader99fee16e (31/22 files;422 known each), with independent frozen companion8a8b1bc8 and full carrier0cf37cf0 verified across all562 pins. Both Root metadata-only gates pass454/445 needed pins. Fresh upstream input bytes7ab9 remain unchanged with all3 reference roles null; a fresh independent path receipt b87fa94b and full carrierb31c8cd8 pass69,306 names/28 roots/260 namedJSON reads and zero protected visits, verified by Root across all269 carrier pins. That single actual reference capture43f88c/session93836 is now terminal exit1 (driver31764/worker47396). The format boundary succeeds, but the strict metadata checker rejects actual Qt physical_size=[8.0,8.0] while logical_size=[8,8] and actual GL storage are exact8x8. All10 failure artifacts and the full original process carrierbd9592a2 are verified and retained. Neither raw frame is admitted; uniform14 tests were not reached. A narrow checker proposal939509e4 passes42 pure controls and preserves a full byte inverse: physical dimensions allow builtin int8/float8.0, logical/storage remain strict builtin integers, with no dimension/pixel/tolerance changes. Frozen Source4 remains untouched; Independent Native reviewd6ebd77a clears157 checks/15 pins and complete original carrierc2abe78c, all20 carrier pins Root-verified. The fresh Uniform5 transport draft8976a52c now passes66 composition controls over53 Source files:39 whole-held members,12 complete raw inverses and two regenerated contracts,491 known pins, all actual roles null. The explicit type-domain amendment/current checker SHA preserves original checker history and the prior format amendment. The full actual Root composer ea116d06 is retained. Independent Point complete transport review completes1927 checks and finds one prefreeze packaging blocker: the new42-control receipt lacks the held freezer schema fields. Root preserves original reports/contracts, binds a schema adapter to the actual original42/PID11548/e43943/exit0 carrier, and changes only the two unfrozen contracts. The corrected packet63a69ef3 receives1632 independent delta checks,51 whole-held Source confirmations and9 inert actual-freezer-assertion cases. Root verifies all557 current proof pins plus full carrier lineage. Source5 now freezes producer591ea53f/reader c501fdfa,31/22 files and492 known each, with both actual full freeze carriers retained. Native frozen-companion confirmation is queued after lifecycle path review; no Source5 gate/path receipt/capture or accepted frame exists. Actual16-frame reference admission and candidate comparison remain pending.

Clean-consumer preparation now locks the nine exact runtime dependency versions and downloads their WindowsCP312-compatible binary wheels plus upstreamVisPy0.17.0 from the official release metadata. All10 archives pass declared size/SHA checks; Root verifies the complete21-file sealed download packet (103303446 archive bytes), with no partial files left. The [preparation](../../../build/native57-final-wheel-clean-consumer-prep-root-1/preparation.json) and [download result](../../../build/native57-final-wheel-clean-consumer-download-root-1/result.json) bind the qualified fork wheel and full lifecycle requirements. The closed installation-only producer/saved draft passes73 selected controls and220 final static checks with a complete67-operation/113-pin preparation carrier25e41795. Independent Root CODE review adds65 selected checks over29 Source files/115 finite code and metadata pins, including all10 distribution declarations, exact native4, the one pinned Qt empty self-row spelling pair, child site flags and owned temporary roots. Root freezes actor5b0d72bc (15 files/24 known/40 needed) and saved67f6dfc7 (14/24/39); independent Native frozen confirmation closesde599678/744395bd with135 full carrier pins verified. Root metadata gates and fresh actor path receipte502d7ef pass. The actual installation-only actorf7181c/session82663 closes356729/exit0 and result4d090fde PASS_INSTALLATION_BYTES_ONLY. Its three real children and parent are closed; all10 distributions,547 fork package files,native4,19 notices,4 console launchers and8075 external files pass its byte checks. Root verifies all22 sealed internal artifacts and full original carrierb07dd941. The owned external environment is retained for subsequent verification/lifecycle; clean_consumer_qualified remains false. Windows canonicalized only executable argv0 spelling; both requested and actual orig_argv vectors are explicitly retained without an independent OSargv claim. Saved input22489df7 binds the actual result/inventory/full Root carrier. Fresh saved path receipt920fe74b and full carrier75c13765 pass95 exact merged pins,33924 declared names and zero external-root/protected payload access; Root verifies all72 carrier pins. That single independent saved reader527ad6 closes exit0/PID60904 with result3a3d0565 CLEAR_WITH_SCOPE; its complete original carrierbee5217f is Root-verified across78 pins. It admits all10 distributions/547 fork package/native4/19 notices/4 console launchers/8075 external files, with no rendering/lifecycle qualification. The environment remains retained. Root prepares the seven actual installation-context rows5fa6c110 as metadata only, with no new runtime Source bindings or external-root access. The installation stage keeps clean_consumer_qualified false; fresh path review and actual installation/saved admission precede installed rendering/SDF/assets/capture checks, uninstall and upstream restoration. A separate [fixed geometric SDF fixture](../../../build/native57-clean-consumer-sdf-fixture-root-1/fixture.json) and checker pass13 pure controls for25 complete samples, in-place identity/storage and negative shape/dtype/sign/border/return cases. No compiled SDF module was invoked.

Partition256 GPU Source3 independent CODE review found two draft metadata blockers: a stale reader producer-code hash and six CLI scripts pointing to old GPU Source2 directories. Both are repaired with complete before snapshots and raw-byte inverses. Current [packet4](../../../build/native57-partition256-gpu-prep-root-3/review-packet-4.json) a0bf3795 passes82 inert selected checks;27 producer/12 reader files retain all scientific predicates and the actual admitted CPU build Source3066/reader39d3. Independent final CODE review closes ac55dab6 with1,229 checks/506 finite code+metadata pins and a full29-operation carrier. Both Sources are now frozen at producerdd615e8b (27/381) and reader2eff0f47 (12/423); independent frozen confirmationcc736d20 covers409/436 needed pins and471 unique Source rows. Both Root metadata-only Source gates close without importing frozen modules. Root verifies the complete CODE/frozen carriers and612 unique metadata/code hashes. Fresh [actual capture inputs](../../../build/native57-partition256-graphics-inputs-root-3/preparation.json) bind the complete admitted CPU build and distinct official/partition native4. Fresh independent capture path exclusion closes01ba02a0/aecff945 with312,247 names/49 inventory roots and a complete16-operation carrierc3fc4a20. Root verifies all264 carrier pins. The single actual launch89f191 exits before admission/guard/output/child creation because isolated Python cannot resolve its local path_boundary import; the full original startup refusal4ee1d263 is preserved. A fresh [GPU4 startup transport draft](../../../build/native57-partition256-gpu-prep-root-4/review-packet.json)67a0375a corrects only the three entrypoints owned Source-path bootstraps, remaps GPU/gate/receipt/output namespaces and refreshes dependent CLI/core/code maps. It preserves23 whole files,14 complete raw-byte inverses and two regenerated contracts across39 Source files, with51 controls including actual isolated baseline refusal and selected original bootstrap AST plus stdlib module-spec resolution without target execution. Independent Point CODE review clears2144 checks, complete39 Source files and144 held scientific definitions; Root verifies its515+9 finite pins. Producer199ef0df and readerd973593f are frozen27/12 files with475/501 known inputs. Native frozen companion9c93d481 passes503/514/516 needed maps, and its whole542-pin carrier is Root-verified. Both Root metadata gates pass. Fresh capture path receipte09a6496 and whole original author carrier263ae16b are Root-verified across283 pins, with312190 names/50 roots and zero protected visits. That single Root-only captureeb67df/session2486 is now terminal31fd44/exit1 before output staging or child/provider/GPU creation. The bootstrap fix succeeds, but the generic packet checker recursively inventories the p572 build root even though its actual seal covers21 top-level files; this encounters declared dependency junctions and refuses. The full original failure21e1d582 is retained, with actual OS-observed60584 explicitly distinct from an unreported driver selfPID. A narrow top-level packet proposal2f1bc7db passes11 synthetic controls and independent Point70 checks/19 cases/two complete module inverses; Root verifies its25 source/carrier pins. Default recursive packets remain unchanged; only the exact p572 raw-build call selects its admitted top-level format, preserving separate full source/tree/two-junction/archive checks. Point is preparing a fresh GPU5 transport draft; no retry has launched. CPU Source3066/reader39d3 and all scientific bodies remain held; no p572 rebuild occurred.

Earlier detailed checkpoint, 2026-10-20 21:54 UTC (superseded by the continuation above):

- Five of seven cancellation raw captures pass: pending_abort_control, pending_destroy, pending_loss, retained_map_future_shutdown and submitted_destroy_control. The fifth closes8ffd05/session38271 to801767/exit0, driver34528/child22092; Root verifies all37 sealed files and closes its [full original process carrier](../../../build/native57-cancellation-submitted_destroy_control-outer-root-2/outer-observation.json). Expected cancelled diagnostics return zero raw/logical bytes, exactly one successful native retirement, once-only charge release and clean shutdown, without claiming GPU-busy/unfinished-callback qualification. The sixth, submitted_loss, is the sole Root GPU actor (actualb0b14c/session92272), with actual child21064 observed and no terminal result claimed yet. submitted_open_paint_abort and the single joint independent seven-case saved review remain pending. The earlier independent joint four-fault admission retains its bounded scope.
- The isolated p572 Partition256 build passes all42 targets and44 CPU tests. Its first saved reader closes refused on independently reconstructed input-snapshot equality; the [original failed review](../../../build/evidence/native57-partition256-build-review-native-2/result.json) and [full original reader carrier](../../../build/native57-partition256-build-saved-observation-native-2/observation.json) remain preserved. A reader-only correction explicitly binds the actual build-input row into the reconstruction without relaxing equality. Independent review caught undeclared mixed-line-ending normalization in the first draft; the corrected [packet2](../../../build/native57-partition256-build-saved-prep-root-3/review-packet-2.json) preserves all80 original CRLF pairs and proves whole-byte inverses, with50 focused controls and252 independently checked pins. Source3 is frozen (39d3c544), its Root source gate passes233 needed pins, and its fresh independent saved path receipt passes311,994 names/67 roots with no protected visits. Actual CPU saved reader3 now closes CLEAR_WITH_SCOPE/exit0 (a137b4/session53716 to d39f72), with55,735 checked pins and [new independent admission](../../../build/evidence/native57-partition256-build-review-native-3/result.json). Its [full original process carrier](../../../build/native57-partition256-build-saved-observation-native-3/observation.json) closes with six reader calls and actualPID46564. Root verifies the whole result/carrier, all16 reader Source files and44 archives (65 distinct hashes) and exclusion-checks all55,745 carrier path names; it does not replay all55,745 file hashes. No build or reader was replayed. GPU qualification remains pending. A fresh [GPU producer/saved metadata Source3 packet2](../../../build/native57-partition256-gpu-prep-root-3/review-packet-2.json) now binds admitted build-reader39d3:27 producer/12 reader files,23 whole-held files,14 whole-byte inverses,381/423 known declarations and73 selected metadata controls. A second metadata-only correction finishes concatenated receipt-family names to fresh3; its original draft and byte copies remain preserved. Fixture/science/accounting predicates are unchanged and all actual GPU roles remain NULL. Independent CODE review, Source freezing/gates, fresh actual path receipts and the256 witness are still required; no GPU2 actor ran.
- The corrected RGB/RGBA upstream volume capture passes all30 cases with complete Root128-file preservation and full process closure. Saved reader2 refuses before scientific decode because its expected pre-import map omits two already verified current-identity-admission files; actual handoff and raw maps agree exactly at51,344 pins. The [JSON-only diagnosis](../../../build/native57-volume-rgb-snapshot-diagnostic-root-1/result.json) identifies those two files without any payload hash/stat or guard/reader replay. A reader-only union correction preserves exact equality, all13 other functions and all scientific files, and passes37 focused controls plus independent joint CODE review. Source3 d7b5ac00 is frozen, its Root source gate passes274 needed pins and its fresh independent path receipt passes69,987 paths/36 roots. The one independent saved reader3 closes CLEAR_WITH_SCOPE/exit0 (f45a02/session10433 to11f61e), actualPID34568, admitting all30 reference frames/1,105,920 complete RGBA bytes. Its [full original carrier](../../../build/native57-volume-rgb-reference-saved-observation-native-3/observation.json) closes with eight reader calls and916 pins; Root verifies the whole packet and all916 pins. Fresh [candidate input declarations](../../../build/native57-volume-rgb-candidate-inputs-root-2/preparation.json) now bind this actual reference admission. A new candidate path receipt and candidate rendering/comparison remain pending; producerSource2 and all30 reference frames remain unchanged.
- Uniform Source2 upstream closes failed at the distinct reuse red-frame assertion, before any of the14 pytest cases. Both partial8x8 frames contain63 transparent pixels plus one correct red/green pixel. Root verifies the complete10-file failed packet and seals the [full original process carrier](../../../build/native57-uniform16-upstream-failed-outer-root-2/outer-observation.json); neither frame is an accepted reference or cleanup pass. A [source-only target proposal](../../../build/native57-uniform16-target-prep-point-1/review-packet.json) provisions one owned upstream8x8 RGBA8 framebuffer while holding the candidate P0–P3 window and all draw science. It passes54 inert controls and an independent [Root source review](../../../build/native57-uniform16-target-review-root-1/report/result.json). Hidden Qt fallback storage remains a source-supported inference, not a measured driver fact. The original14 tests use their unchanged Canvas context-manager behavior. The fresh [Source3 transport packet](../../../build/native57-uniform16-prep-point-3/review-packet.json) is complete and held:31 producer/22 reader files,349 known declarations each,54 selected controls and full raw-byte inverses. Its [eleven-call carrier](../../../build/native57-uniform16-prep-point-3/preparation-observation/observation.json) closes; Root checks all408 pins and53 Source files. New worker/saved checks cover actual FBO storage and cleanup; all14 test bodies, original scientific checker and candidate probes remain unchanged. Independent CODE review, freezing and a new actual16-frame reference remain pending. The separately reviewed reader-only identity-union draft remains unfrozen and is not an admission of the failed science run.
- The fresh all-five Glue transport/saved draft is coherent and unfrozen:25 producer/20 reader files,371 known metadata rows per Source, exact83-distribution/25,057-file runtime declaration,67 observer/science plus36 source/path/snapshot controls. Its [packet](../../../build/native57-glue-five-prep-point-1/review-packet.json) and [complete36-call carrier](../../../build/native57-glue-five-prep-point-1/preparation-observation/observation.json) are closed; Root verifies all424 carrier pins and45 Source members. It includes the two identity-admission receipt pins in exact expected reconstruction. No independent CODE review, Source freeze, real host actor, inherited old-four result or final-wheel host qualification is claimed.
- The final-wheel core validates exact523 source/4 native/20 package notices plus19 distribution notices and standard metadata/RECORD. Core2 fixes exact Metadata-Version2.4 (586 controls/26 independent delta checks). The full producer/saved draft passes229 focused controls; independent review finds a missing retained stdout summary join. The narrow Source2 correction holds19 files/two complete byte inverses, passes34 integrated controls and806 independent checks, and is frozen at producer30b24694/readerb06aeae7. Native frozen confirmation, Root gates (13/10 needed) and fresh complete737-pin path receipt all close before actual execution. The [first actual public no-CMake packaging run](../../../build/native57-final-wheel-production-outer-root-1/outer-observation.json) creates the CP312 wheel but closes FAILED/exit1 because cleanup rejects legitimate fileless scikit_build_core._vendor. Root verifies all745 failed packet files, unchanged568 staged project/172 backend files and preserves every original diagnostic/result; no release pass is claimed. A fresh [Source3 namespace correction draft](../../../build/native57-final-wheel-release-prep-root-3/review-packet.json) allows only the declared vendor namespace with actual standard NamespaceLoader metadata and one exact owned directory, while retaining complete file/tree checks. It holds14 files, four byte inverses and three declared metadata regenerations;47 selected namespace/lifecycle/restoration controls pass, and the corrected saved-reader implementation is wholly held. The original inert control constructor failure is preserved and only that test fixture was corrected. Independent Source3 CODE review is underway; fresh Source freezing/gates/path receipts must precede a second actual attempt in unused outputRoot2. Clean consumers and genuine native builds for four other ABIs remain required. Previously blocked inert-tree/bytecode deletions are not retried.

The published normal Native57 source, original126, integer128, Text24, thin156, Broad64, bounded stencil/public-query and WSL software-Vulkan admissions retain their original scopes. The [original thirteen-requirement ledger](../../../build/all-gaps-audit-point-1/ledger.md) still has broader shader/texture, Qt/host, final wheel/ABI, general smooth-line, 66-workload performance and external native hardware requirements open. WSL software results do not qualify native Linux hardware; macOS hardware is unavailable. Cybersecurity is excluded. Protected predictions and reserved holdouts remain untouched. GPU producers remain serialized. Prior checkpoint text is retained in the [checkpoint backup](../../../build/native57-continuation-checkpoint-root-3/plan-before.md). No evidence or rejected bytecode deletion is retried as cleanup.

[Closed Native57 compiler-cache cleanup](../../../build/native57-closed-cache-compression-root-1/result.json) recovers112,285,815 bytes from553 files while preserving their bytes, file identities and creation/modified clocks, plus current611, archive44, installed57 four and before56 four. Rejected bytecode-cache deletion remains unperformed. Earlier dated checkpoints and the detailed work record follow.

Active closure work, 2026-10-19: the [original thirteen-requirement ledger](../../../build/all-gaps-audit-point-1/ledger.md) distinguishes implementation defects, missing current qualification and external environment requirements. The [reviewed culling correction](../../../build/cull-both-review-native-1/result.json) now has an [independently admitted isolated Windows build](../../../build/evidence/native55-cull-build-review-line-2/result.json): all42 targets,44 CTests and44 archived binaries pass. The [joint scientific admission](../../../build/evidence/cull-both-candidate-review-native-2/result.json) accepts six cases/nine complete color/depth/stencil frames, exact fresh OriginalGL and analytic comparisons, all17 semantic/physical user draws, source-derived internal clear/presentation accounting and logical cleanup. The real Native54 baseline refusal and both failed checker predecessors remain preserved. Root [published the exact two C++ files and state contract test](../../../build/cull-both-publication-root-1/result.json), retaining before3 backups and separately observing all seven canonical/native files before and after. Installed Native54 remains unchanged. The [independent publication audit](../../../build/cull-both-publication-review-point-2/result.json) is clear, and the [formal Native55 ownership admission](../../../build/evidence/native55-cull-ownership-review-line-2/result.json) accepts source611, package523 and official harness4131 plus four separate tools. The [actual Native55/w41 standard freeze](../../../build/native55-standard-freeze-outer-root-1/outer-observation.json) and [formal standard build](../../../build/native55-standard-build-outer-root-1/outer-observation.json) passed, including all42 targets and44 CTests. The [independent saved-build audit](../../../build/evidence/native-pass-55-build-review-line-1/result.json) is clear, including all44 archived binaries and strict source, harness, SDK, dependency-origin and toolchain checks. Installation is held for the Linux lifecycle correction; final-artifact qualification remains pending; the isolated proposal does not claim that formal identity. Final broad/thin/fault/cancellation and other required qualification must bind the final artifact.

Linux work uses the user-authorized Ubuntu WSL environment, exact CPython3.12.8 and locked build packages, with4,696 explicit source/harness inputs and the unchanged closed dependency authority relocated to Linux. After the missing X11 development header was installed, the [actual recovery build](../../../build/linux-build-recovery-outer-root-1/outer-observation.json) passed full configure, five dependency targets,42 project targets and44 CTests. Its original missing-header failure remains preserved; the [independent saved-build audit](../../../build/evidence/linux-relocated-build-outcome-review-native-2/result.json) is clear after correcting CMake compiler-alias metadata handling. Linux graphics preparation uses the same unchanged six-case scientific fixture, a separate19-package runtime and pinned llvmpipe ICD. The [fresh Linux OriginalGL reference admission](../../../build/evidence/linux-cull-reference-review-native-3/result.json) accepts all nine complete color/depth/stencil frames. The first Vulkan attempt initialized and presented through X11 but stopped before scientific capture because an ordinary warmup paint cannot emit a measured-frame completion. A [reviewed Source4 helper](../../../build/linux-cull-science-review-native-4/result.json) reserves a measured frame after cold paints settle, retaining strict completion and cancellation checks. Its [actual Source4 run](../../../build/linux-cull-candidate-failure-outer-root-4/outer-observation.json) passed warmup and wrote five passing case packets, then aborted with a native glibc mutex assertion during setup of the sixth Canvas. The full process failed before the top-level result was sealed; these partial frames are diagnostic evidence. The [closed fresh debugger run](../../../build/linux-cull-gdb-outer-root-5/outer-observation.json) stopped in xcb_unregister_for_special_event through Mesa and Dawn FencedDeleter during later event processing. This confirms deferred Vulkan WSI cleanup can outlive the Xlib Display that the current runtime immediately closes. The [three-file lifetime correction](../../../build/xlib-wsi-lifetime-implementation-native-1/result.json) and its [completed Root Source gate](../../../build/xlib-wsi-lifetime-source-review-root-1/result.json) are now ready. Independent review covers owned and borrowed Xlib retirement, deletion-serial draining, error/loss/timeout retention and eager Dawn device teardown. Its48 saved source controls pass. The [fresh full Linux build Source](../../../build/linux-wsi-build-point-1/source-seal.json) and [independent preparation review](../../../build/linux-wsi-build-review-native-1/result.json) are clear; Root is running new source3/build3/run4. Actual C++ contract results and the matching complete runtime capture remain pending. Canonical files and installed Native54 remain unchanged by this isolated proposal. Failed attempts are retained and no scientific Linux Vulkan pass is claimed yet. WSL software correctness cannot close native Linux hardware or performance rows. The user has no macOS machine; Metal qualification remains an external prerequisite. [Closed-archive compression](../../../build/all-gaps-closed-archive-cleanup-root-1/result.json) reclaimed2,485,113,685 physical bytes with contents and protected source/native files unchanged. A second [closed-cache compression](../../../build/native55-closed-cache-compression-root-1/result.json) retains all886 Native55 build-cache files and reclaims194,280,126 storage bytes measured consistently with GetCompressedFileSizeW, while source611 and installed Native54 remain exact. Access/change metadata is recorded rather than reset. Keep scientific thresholds and unsupported-operation refusals intact, exclude cybersecurity, and clean closed temporary outputs as work completes.

Current integer/Text checkpoint, 2026-10-19: the [joint Native54/current Python611 qualification checkpoint](../../../build/native54-python611-integer-text-qualification-checkpoint-root-1/progress.json) is complete at its stated scope. Independent audits verify128 new integer-sampling frames and24 new Text frames matching their accepted OriginalGL references, with scientific, resident-work, process and logical cleanup checks passing. The integer scope includes seven requested ForceLoss API recoveries. A one-expression checker path-spelling correction preserves its failed predecessor and all scientific criteria; both GPU captures run once. [Independently audited closed-asset compression](../../../build/evidence/sprint29-cleanup-outcome-review-native-1/result.json) preserves871 files across14 named roots and reclaims5,865,827 physical bytes. Installed Native54, current source611/package523/harness4135 and formal build source610/harness4131 retain their distinct scopes. Ordinary thin-line cap64, fault/cancellation matrices and the broader original requirements remain open; cybersecurity work is excluded.

Current broader GPU checkpoint, 2026-10-19: the [Native54/current Python611 broader qualification checkpoint](../../../build/native54-python611-broad-qualification-checkpoint-root-1/progress.json) is complete at its stated scope. The [independent joint audit](../../../build/evidence/native54-python611-broad-gpu-outcome-review-line-1/result.json) verifies all 64 full frames across ten normal and ten isolated forced cases, exact OriginalGL comparisons, 13 endpoint captures/849 logical rows and three requested ForceLoss API recoveries per route, resident counters, process closure and cleanup. The isolated derivative passes all 42 targets and 44 CTests with 44 archived binaries; installed Native54 remains unchanged. The [independent storage audit](../../../build/evidence/native54-python611-broad-cleanup-outcome-review-point-1/result.json) verifies all 1,540 retained files and 145,502,870 reclaimed physical bytes. Current source611/package523/harness4135 remains separate from formal Native54 source610/harness4131. Prior 68 CPU, 24 focused rendering frames and 126 original regressions retain their separate completed scopes. Remaining matching Native54 matrices and the broader scientific, host, platform, performance and release criteria remain open; cybersecurity work is excluded.

Current Python checkpoint, 2026-10-18: the [empty-instance drawing/bounds correction and seven-case rendering batch are qualified at their stated scope](../../../build/instanced-empty-draw-render-regression-checkpoint-root-1/progress.json). All 68 copied-canonical CPU cases pass. Seven Isocurve/InstancedMesh cases produce 24 complete frames matching fresh independent OriginalGL references byte for byte. The new 523-member stage and current Python identity are independently admitted. The [fresh original126 audit](../../../build/evidence/native54-python611-original126-outcome-review-line-1/result.json) verifies all 17 ordinary and 109 affected tests, 769 decoded numeric arrays and 299 exact saved comparisons, with resident/recovery/cleanup and complete process closures passing. Publication, canonical CPU and external physical-write audits are clear. Declared current source611/package523, formal Native54 source610, formal harness4131 plus four tools and the installed Native54 binaries retain their separate scopes. [Audited closed-Source compression](../../../build/sprint27-cleanup-outcome-review-point-1/packet/result.json) reclaims 298,973 more physical bytes with all 106 files preserved. The broader original thirteen requirements remain open; cybersecurity work is excluded.

Current Native54 integration, 2026-10-18: the measured-allocation window is published, the isolated snapshot40 build passes all42 targets and44 CTests, and its [independent full-build admission](../../../build/evidence/native-pass-54-build-review-line-1/result.json) is clear. Root's [actual installation](../../../build/native54-activation-outer-root-2/outer-observation.json) closes exit0 with exact Native53-before backups, and the [independent installed audit](../../../build/evidence/native-pass-54-installed-audit-line-1/result.json) is clear. The [idle allocation API audit](../../../build/evidence/native54-idle-api-outcome-review-line-1/result.json) and [fresh original126 regression audit](../../../build/evidence/native54-original126-outcome-review-line-1/result.json) are now independently clear: all17 ordinary and109 affected tests pass, with769 decoded numeric arrays and299 exact saved comparisons. These results bind source610/package522/formal harness4131 plus four tools and the installed Native54 binaries. These formal build and regression results predate the subsequent Python changes described above. Earlier Native53 GPU results retain their historical contexts. The original thirteen requirements remain open; cybersecurity work is excluded.

Current implementation, 2026-10-18: the reviewed [filtered Volume resize fix is published](../../../build/volume-filtered-resize-publication-root-1/result.json), all [97 copied-canonical CPU cases pass](../../../build/evidence/volume-filtered-resize-canonical-cpu-root-1/result.json), and its [independent publication/CPU audit](../../../build/volume-filtered-resize-publication-review-point-1/result.json) is clear. The [actual d00c Python identity and stage4 admission](../../../build/native53-python-source-revision-identity-outcome-review-line-2/result.json) bind the new source. The [scoped filtered Volume checkpoint](../../../build/volume-filtered-resize-qualification-checkpoint-root-1/progress.json) now also admits four cubic/Lanczos MIP resize cases across both scaling paths: all eight final/resident frames match fresh references exactly, with 24 landmarks, one lookup/geometry rebuild and resident reuse. Immediately before publication, the [seven-case public napari workflow was independently admitted](../../../build/napari-label-public-outcome-review-native-2/result.json): all 28 complete candidate screenshots match fresh upstream references exactly, with 168 landmarks, signed-category edits, multiscale restoration and ownership/cleanup checks passing at b4dd. Broader scientific, host, platform, performance and release requirements remain open. Cybersecurity work remains excluded.

Benchmark implementation, 2026-10-18: [all six telemetry leaves are published](../../../build/benchmark-telemetry-publication-root-1/result.json), and [398 canonical CPU contracts pass](../../../build/benchmark-telemetry-canonical-cpu-record-root-1/result.json) with four actual canonical module origins. The [independently admitted eight-frame Windows diagnostic](../../../build/benchmark-owned-pacing-checkpoint-root-1/progress.json) records owned interval0, GPU timestamps, scene/presentation fence completion, clean measured resident work and shutdown. The [independent publication/CPU audit](../../../build/benchmark-telemetry-publication-review-point-1/result.json) passes68,224 checks and12,483 physical pins. The [new harness-only identity](../../../build/native53-benchmark-harness-identity-outcome-review-line-1/result.json) is independently admitted, and the [published telemetry batch checkpoint](../../../build/benchmark-telemetry-publication-checkpoint-root-1/progress.json) is complete at its stated scope. All609 renderer source leaves, the521-member package stage and Native53 four remain unchanged. The diagnostic does not qualify throughput, scanout, input-to-visible latency, the full matrix or release.

Previous bounded Python rendering checkpoint, 2026-10-18: the published scalar/color transition fix is [qualified at its bounded scope](../../../build/image-channel-qualification-checkpoint-root-1/progress.json). All twenty-six focused Image CPU cases pass, and eight complete public-view frames for nearest/subdivide scalar-to-RGBA and RGBA-to-scalar replacement match two fresh direct references exactly (294,912 RGBA bytes, forty landmarks). The b4dd Python identity, actual publication, capture Source and joint outcome are independently admitted; the other 607 source leaves and Native53 four remain unchanged within that publication's scope. Existing-first/original/late/resident paths rebuild once then reuse. The preceding [forty-frame grayscale/LUT checkpoint](../../../build/image-current-qualification-checkpoint-root-1/progress.json) retains its 3e5b source context.
Previous Python checkpoint, 2026-10-18: the [volume redraw/geometry fix](../../../build/volume-redraw-checkpoint-root-1/progress.json) and [Image resize/lookup/view-initialization fix](../../../build/image-resize-checkpoint-root-1/progress.json) are published and independently audited. All eighteen focused canonical CPU tests pass. The [fresh Python-layer checkpoint](../../../build/python-layer-checkpoint-root-1/progress.json) binds the independently audited 521-member stage and current 609-source identity over formal Native53/snapshot39. The [current Image/Volume rendering checkpoint](../../../build/visual-mutation-checkpoint-root-1/progress.json) binds ten independently admitted fresh upstream frames and twenty exact candidate final/resident frames, with preparation/event/cleanup checks passing at that ten-case scope. The [direct Qt Volume checkpoint](../../../build/volume-qt-redraw-checkpoint-root-1/progress.json) additionally admits automatic notifications, coalesced redraw requests, completed native paints and two exact later exports for same/changed-shape updates. The [napari Image checkpoint](../../../build/image-resize-napari-redraw-checkpoint-root-1/progress.json) additionally admits one same-node cubic layer resize with automatic ready drawing and two exact later exports, with async slicing and autoswap disabled. Earlier GPU receipts retain their frozen source contexts. Public Image.view pixels, broader scientific cases, other host behavior and the remaining original requirements stay open.

Installed native checkpoint, 2026-10-18: Native53/snapshot39 includes the point attribute-limit diagnostic correction and the existing fan, point, generated-line and thin-line implementation. The [independent full-build admission](../../../build/evidence/native-pass-53-build-review-map-1/result.json) verifies all 42 targets, all 44 passing CTests, 44 archived binaries, 609 source leaves, 4,130 harness inputs and 85 native owners. Native53 is [installed and independently audited](../../../build/evidence/native-pass-53-installed-audit-map-1/result.json), with exact Native52 backups retained. Matching qualification is now independently admitted: [all 126 original regressions](../../../build/evidence/native53-original126-outcome-review-map-1/result.json), [128 new Dawn53 integer frames against 128 accepted OriginalGL frames](../../../build/evidence/typed-integer-sampling-native53-gpu-outcome-review-map-1/result.json) (256 joint frames), and [all 24 TextVisual frames](../../../build/evidence/text-native53-gpu-outcome-review-map-1/result.json). The [Native53 normal/cap64 thin-line admission](../../../build/evidence/native53-thin-line-gpu-outcome-review-map-1/result.json) also qualifies all 156 newly captured complete frames, ordinary endpoint-compute counters, direct process closure and logical cleanup at its 13-case horizontal width-one scope. The [sealed thin checkpoint](../../../build/native53-thin-qualification-checkpoint-root-1/progress.json) binds the new isolated build and actual artifacts. The [broader64 admission](../../../build/evidence/native53-broad-gpu-outcome-review-map-1/result.json) qualifies all64 new frames, typed endpoint/guard capture, six requested ForceLoss recoveries and cleanup on normal and combined forced routes. Its [sealed checkpoint](../../../build/native53-broad-qualification-checkpoint-root-1/progress.json) binds the matching artifacts and previous qualifications. The [sealed matching126/integer/Text checkpoint](../../../build/native53-matching-qualification-checkpoint-root-1/progress.json) binds those three admissions and the current installed binaries; the thin and broader checkpoints extend it. [Build-asset compression](../../../build/closed-native53-storage-root-1/result.json) reclaimed 143,115,195 bytes across 4,498 files; the final 1,411-file result pass saved zero additional bytes. All file names and bytes remain unchanged. Native52 and earlier results retain their historical artifact scopes. The [matching four-fault admission](../../../build/evidence/native53-chunk-fault-outcome-review-map-1/result.json) and [sealed fault checkpoint](../../../build/native53-fault-qualification-checkpoint-root-2/progress.json) now qualify the fresh baseline, late padding fault, real map error and deferred retry. The [seven cancellation schedules](../../../build/evidence/native53-capture-cancellation-outcome-review-map-1/result.json) are also independently admitted and bound by the [sealed cancellation checkpoint](../../../build/native53-cancellation-qualification-checkpoint-root-1/progress.json). General smooth rendering and the original scientific, host, platform, performance and release conditions remain open. Cybersecurity work remains excluded.

Previous installed checkpoint, 2026-10-18: Native52/snapshot38 includes the published ordinary native thin-line batching fix. [Independent full-build admission](../../../build/evidence/native-pass-52-build-review-map-1/result.json) verifies all42 targets, all44 passing CTests,44 archived binaries,609 source leaves,4,130 harness inputs and85 native owners. Native52 is [installed and independently audited](../../../build/evidence/native-pass-52-installed-audit-map-1/result.json), with actual Native51 backups retained. Its matching [normal three-case GPU smoke](../../../build/evidence/native52-normal-smoke-outcome-review-map-2/result.json) is independently admitted at that limited scope. The thin-line13case fixture now has independently admitted [OriginalGL references](../../../build/evidence/native52-thin-line-original-outcome-review-map-3/result.json). The matching normal and isolated cap64 thin-line13 matrices are [independently admitted](../../../build/evidence/native52-thin-line-gpu-outcome-review-map-1/result.json): all156 complete frames match the same actual OriginalGL references. Broader fan/point/generated-line [OriginalGL32 references](../../../build/evidence/native52-broad-original-outcome-review-map-1/result.json) and the matching [Native52 normal/combined forced GPU matrices](../../../build/evidence/native52-broad-gpu-outcome-review-map-2/result.json) are independently admitted: all 64 complete frames, typed endpoints/guards, resident updates, six requested ForceLoss API recoveries and clean retirement pass. The isolated [late-part guard, map and deferred-retry matrix](../../../build/evidence/native52-chunk-fault-outcome-review-map-2/result.json) is independently admitted: four exact complete frames, real map/validation callbacks, baseline-identical retry and once-only native retirement pass. The [seven existing-API cancellation/loss/shutdown schedules](../../../build/evidence/native52-capture-cancellation-outcome-review-map-1/result.json) are independently admitted, including an actual failed native retirement on submitted loss and retained-map shutdown raw evidence. The matching original126 attempt has125 passing tests and one point attribute-limit diagnostic wording failure; the compatible two-file wording fix has passed focused CPU checks and independent CPU review and is now published to canonical source, with the independent saved publication audit passed and Native53 build still pending. General smooth coverage and the original scientific/host/platform/performance/release conditions remain open. Cybersecurity work remains excluded.

Previous coherent build checkpoint, 2026-10-17: the implementation-first sprints add ordered TRIANGLE_FAN batching, bounded point-sprite batches with partitioned user streams, and bounded generated-line endpoint/output chunks with once-only endpoint evaluation and copied seam/loop-head results. Chunked endpoint diagnostics now retain one logical record with real per-chunk raw evidence captured before carry copies. The coherent fan/point/line/capture candidate now has an [independently admitted Native51/w37 full build](../../../build/evidence/native-pass-51-build-review-map-1/result.json): all 41 targets build and all 43 CTests pass from 609 source leaves, 4,129 harness inputs, 1,936 dataset rows and 84 disjoint native owners. Native51 is installed and [independently audited](../../../build/evidence/native-pass-51-installed-audit-map-1/result.json); matching new-route GPU qualification remains pending. Native50 backups retain their exact prior bytes. The [latest affected CPU suite](../../../build/implementation-sprint-4/cpu-1/outcome.json) retains all 13 selected line/capture contracts and runtime/binding compilation, with 62 source-matched Python decoder controls. Earlier point, batching and accounting results retain their original source scopes. The [24-frame endpoint precision probe](../../../build/smooth-endpoint-tie-probe-work-6/review-outcome-1/result.json) is independently admitted as calibration only: both old nominal frames reproduce exactly, while rotating the negative-slope case changes one alpha byte from 173 to 164. General smooth coverage needs a new frozen mechanism/prediction contract and unseen qualification data. The broader original scientific/host/platform/performance/release requirements remain open. Cybersecurity work remains excluded.

Previous installed checkpoint, 2026-10-17: Native50 was installed and independently audited after a complete37-target/39-CTest build. Its matching original126 regression tests,256 integer-sampling frames and24 TextVisual frames are independently qualified at their stated scopes. Native49's earlier matching126/256 qualification remains historical. Ordered TRIANGLES batching and finite nearest/base-level signed/unsigned2D sampling are canonical. Ordinary TRIANGLE_STRIP batching is now applied to source and independently publication-audited after normal and forced37-target/39-CTest builds,94 exact GPU frames and the original126 regression tests. TextFont kernel texture reuse is also applied and independently publication-audited after24 exact complete frames. Native50 ownership, snapshot36 freeze, full build, activation and installed audit are independently admitted. Matching installed126/256/24 qualification is admitted. Historical results retain their original artifact/driver scopes. General topology, smooth coverage, remaining scientific/host/platform rows, fixed-quality performance and release conditions remain open. Cybersecurity issues are excluded. The detailed entries below retain their historical scope; checkpoints at the end provide the complete evidence trail.

Updated 2026-10-11 from actual results and independent reviews. [complete build12 admission](../../../build/evidence/line-helper-compile12-review-validation-1/result.json) verifies all six Release outputs and the complete source/build/protected/tool maps. [inventory14 admission](../../../build/evidence/line-helper-compiler14-inventory-review-validation-1/result.json), [focused14 admission](../../../build/evidence/line-helper-compiler14-focused-review-validation-1/result.json), [full15 admission](../../../build/evidence/line-helper-compiler14-full-review-validation-1/result.json) and [consolidated CPU suite admission](../../../build/evidence/line-helper-compiler14-suite-review-validation-1/result.json) pass at complete Tint CPU compiler scope. 56,900 compiled occurrences, 56,896 unique IDs, 56,890 enabled occurrences and 7,168 focused instances; 276 authored rows include 148 new definitions. Ten normal disabled cases and the four original duplicate pairs remain exactly two each. The [retained full14 reporting failure](../../../build/evidence/line-helper-compiler14-full-reporting-failure-outer-observation-1/outer-observation.json) stays failed and unchanged; full15 passes with lossless transport of 298 raw bytes in 23 value_param attributes. The original XML bytes, reversal ledger and [XML transport controls admission](../../../build/evidence/line-helper-compiler14-xml15-parser-controls-review-validation-1/result.json) (18 methods/51 subchecks) are admitted. Current interface/ingestion and SDK/native work remains open; every original completion condition still applies.

The [original thirteen requirements](2026-10-09-vispy-vulkan-completion-plan.md#original-thirteen-step-scope) and [design specification](../specs/2026-10-08-vispy-vulkan-design.md) define completion. The [continuation plan](2026-10-10-vispy-vulkan-continuation-plan.md) retains the six milestone descriptions; the [evidence journal](implementation-evidence.md) retains historical results. This document supplies the current execution order.

Latest work, 2026-10-17: the one-leaf TextFont kernel texture-reuse change is applied and independently publication-audited after all24 complete frames match accepted Original OpenGL, exact atlas/geometry/transform checks pass and12 resident intervals show17 zero-work counters. The first application preflight's receipt-field error and superseded source admission remain recorded; corrected work2 passes independent source/schema admission and its actual preflight/application/audit. Native50 ownership is independently admitted for604 sources,4119 harness inputs,1936 dataset paths and75 native owners, with37 targets/39 CTests. The actual snapshot36 freeze and37-target/39-CTest build completed successfully, and independent full-build and installed-file audits pass. Source-only review admits the matching original17/109 regression preparation and integer-sampling transport/saved reader; final regression identity, preflights and actual matching126/256 GPU outcomes are independently admitted. The matching24-frame text saved review also passes after the independently admitted process-evidence metadata correction; its failed predecessor is retained. Closed build/capture caches are compressed with byte-exact inventories; all evidence and failures remain available. See the final checkpoints below.

## Delivery sequence

| Phase | Deliverable | Required gate before proceeding |
| --- | --- | --- |
| 1. Compiler, complete CPU gate | Preserve admitted build12 and inventory14/focused14/full15 with consolidated whole-suite admission. | Exact enabled selection, disabled origins, four duplicate pairs, all fifteen depth/semantic controls and the sixteen original proof origins remain admitted. Source changes require fresh affected qualification. |
| 2. Interfaces and ingestion | Admit logical link/header proposals and required helper/demote/derivative CPU chains; admit complete origin inputs, new lock/physical origins and final public interfaces. | Observed logical interface/bindings independently admitted; all required CPU ingestion rows pass from the same epoch. Final physical SDK interface follows admitted source origins. |
| 3. SDK and native integration | Stage a relocatable SDK, integrate the reviewed runtime candidate, build/install/audit the matching native artifact. | Clean external consumers, integrated tests and native identity admission. |
| 4. Rendering and ownership | Qualify aliased lines, resolve and implement smooth coverage, and finish partitioning, state and lifetime behavior. | Full reference frames and genuine native ownership/retirement evidence on Vulkan and Metal. |
| 5. Scientific, hosts and platforms | Finish required visuals, installed workflows, instrumentation, lifecycle rows and final artifacts. | Every required correctness, host, platform and package row passes on final source. |
| 6. Performance and release | Run the fixed 66-workload comparison matrix. | All original quality, performance and release conditions pass. |

Prepare smooth measurements, independent native fixtures and platform environments alongside the compiler work. Serialize GPU jobs and source publication. Reuse unchanged admitted controls; repeat checks when code, bindings or acceptance evidence changes.

## Verified starting point

| Area | Actual result | Remaining work |
| --- | --- | --- |
| Installed baseline | Native34 is installed, audited and qualified by its ten matching regression packets. | Preserve it while preparing the new candidate; qualify every affected changed artifact. |
| Published compiler repair | [publication10 admission](../../../build/evidence/line-helper-focused13-publication10-review-shaders-2/result.json) preserves the exact512/513 boundary correction, shared binary/call continuation and all59 owners. | Preserve all inherited assertions, all fifteen depth/semantic controls and every failed predecessor packet without replay or relabeling. |
| Fresh generation | [generation15 admission](../../../build/evidence/line-helper-focused13-generation15-review-shaders-2/result.json) and [recipe15/phase19 admission](../../../build/evidence/line-helper-focused13-recipe15-outcome-review-validation-2/result.json) pass for source16/owner15, unchanged generated delta,52 configure arguments and six shipping roles. | Retain their actual closed source/data receipts and immutable metadata-reader failures; no producer replay. |
| Staleness | [stale13 admission](../../../build/evidence/line-helper-stale13-review-validation-1/result.json) and [configure12 admission](../../../build/evidence/line-helper-configure12-review-validation-2/result.json) pass for the same epoch and exact Release policy. | Retain the actual configure/storage/compile sequence; measure available storage before later substantial outputs. |
| Dependency build | [complete build12 admission](../../../build/evidence/line-helper-compile12-review-validation-1/result.json) independently checks118225 source files,6034 build files,21660 protected inputs, five tools, current59 owners/native4 and all six Release outputs. [supervisor14 emitted-source admission](../../../build/evidence/line-helper-supervisor14-emission-review-validation-1/result.json) binds the actual executable and supervisor source. | Complete build scope is distinct from compiler suites, complete interfaces, SDK and native qualification. |
| Compiler inventory | [inventory14 admission](../../../build/evidence/line-helper-compiler14-inventory-review-validation-1/result.json) passes. 56,900 compiled occurrences, 56,896 unique IDs, 56,890 enabled occurrences and 7,168 focused instances; 276 authored rows include 148 new definitions. Ten normal disabled cases and the four original duplicate pairs remain exactly two each. | Preserve exact occurrence expansion, disabled origins and schema2 selected-set authority. Its four derived protection additions are the exact complete predecessor inventory13 review packet, not Dawn source files. |
| Focused compiler tests | [focused14 admission](../../../build/evidence/line-helper-compiler14-focused-review-validation-1/result.json) passes all7168 required instances, including all fifteen depth/semantic controls, with zero failure/error/skip. | Preserve the strict original union and all failed focused12/13 evidence; successful bodies do not substitute for interface, ingestion or native results. |
| Full compiler suite | [full15 admission](../../../build/evidence/line-helper-compiler14-full-review-validation-1/result.json) passes56890 enabled instances with ten disclosed normal disabled cases. [consolidated CPU suite admission](../../../build/evidence/line-helper-compiler14-suite-review-validation-1/result.json) admits the complete CPU suite and all sixteen original proof origins. | Preserve the [retained full14 reporting failure](../../../build/evidence/line-helper-compiler14-full-reporting-failure-outer-observation-1/outer-observation.json), original raw XML and exact byte-reversal ledger. No compiler pass qualifies a native device or raster result. |
| Runtime candidate | [Final source review](../../../build/evidence/line-runtime-consumer-policy-integration-source-review-validation-1/result.json) is clear. [CPU outcome](../../../build/evidence/line-runtime-policy-cpu-outcome-review-shaders-1/result.json) verifies 538 checks for policy cache, device records, shared FIFO and accounting. | Compile the full candidate with the matching tested SDK; qualify actual Tickets, pipelines and pixels. |
| Dependency interfaces and SDK | [Graph11 admission](../../../build/evidence/line-helper-build12-graphs-outcome-review-root-1/result.json) retains all three actual graph projections. [corrected PP8/COFF9 metadata admission](../../../build/evidence/line-helper-build12-metadata-outcome-review-root-2/result.json) admits PP8 tint/bundle, the corrected dawn_native_objects native producer and COFF9. The original native wrapper receipt retains its valid metadata scope; [retained Interface9 wrapper refusal](../../../build/evidence/line-helper-build12-interface9-failure-outer-observation-root-1/outer-observation.json) remains immutable. Logical proposal, required ingestion/origin inputs and final-interface gates remain pending; both Interface9 refusals remain preserved. [SDK10 source admission](../../../build/evidence/line-helper-sdk10-source-review-shaders-1/result.json) passes source-only review. [SDK10 changed-function controls admission](../../../build/evidence/line-helper-sdk10-inventory-controls-review-packaging-1/result.json) passes 15 synthetic methods/49 case subchecks with zero failures, errors or skips; 79 events and all 2,599 fixture files are retained. Six exact SDK10 source copies and their [source-handoff/path identity admission](../../../build/evidence/line-helper-sdk10-source-handoff-review-shaders-1/result.json) pass source-only scope; actual runtime import and production remain unrun. Origins, new lock, final descriptor, staging, relocation and native qualification remain pending. | Admitted logical proposals and required ingestion/origin inputs precede the new lock/physical origins and final interface, then SDK production, clean relocated consumers and matching native qualification. |
| Smooth rendering | Probe controls, admitted provider freeze and three original OpenGL captures pass: full baseline exact, endpoint alpha164 before RGB blending. The [depth repair/reference publication](../../../build/evidence/line-opengl-smooth-depth-source-publication-review-packaging-1/result.json) passes after one admitted original capture with all six landmarks unchanged. | Resolve the general smooth filter; use the new depth reference with its explicit source provenance. Candidate raster and SmoothReference remain unqualified. |
| Smooth measurements and model | [Orientation32 source admission](../../../build/evidence/line-opengl-smooth-orientation-source-review-validation-1/result.json), [context admission](../../../build/evidence/line-opengl-smooth-orientation-context-review-shaders-1/result.json) and [complete32-frame admission](../../../build/evidence/line-opengl-smooth-orientation-result-review-shaders-1/result.json) pass with an exact full baseline. Prior six-model analysis still fails the old oblique geometry. The [finite mathematical contract](../../../build/evidence/line-opengl-smooth-orientation-model-contract-review-validation-1/result.json) is independently source/data-admitted. | Retain [admitted39 controls](../../../build/evidence/line-opengl-smooth-orientation-model-controls-review-packaging-2/result.json) and the [fixed negative study](../../../build/evidence/line-opengl-smooth-orientation-model-study-2/result.json). Retain its [independent negative-study admission](../../../build/evidence/line-opengl-smooth-orientation-model-study-outcome-review-validation-2/result.json) and investigate the training mechanism. The frozen candidate cannot be retuned from holdouts; future hypotheses require a new contract and unseen holdouts. SmoothReference and native raster remain unqualified. |

## Next implementation batch

| Owner | Concrete action | Acceptance before the next step |
| --- | --- | --- |
| Root and shaders | Retain accepted compiler14/full15 CPU suite and actual matching Graph11/PP8/COFF9 receipts. Source-admit the demonstrated CMake-input path correction and independently admit fresh logical interface proposals. | Complete proposal/physical-input admission; final interface follows origin inputs and the new lock. Preserve both actual Interface9 failures. |
| Root and validation | Retain the passing three phase admissions and consolidated CPU suite. Admit required native-policy/helper/demote/derivative and reader4 ingestion/probe chains on the same build. | Complete required CPU chains and strict positives/negatives; no inventory or synthetic-only receipt substitutes for ingestion. |
| Packaging and validation, in parallel | Retain SDK10 source, meaningful15/49 guard controls and the admitted six exact source-copy paths. Prepare matching logical proposals, ingestion and origin-input bindings. | Same-epoch proposal/ingestion and complete physical origin-input admissions -> new lock/physical origins -> final interface -> descriptor, staging and clean relocated consumers. |
| Shaders and validation, in parallel | Retain admitted proposal, sources, context, all32 original captures, mathematical contract and39 controls; retain the admitted fixed negative study and investigate the unresolved mechanism. | Preserve the existing39 passing controls and exclusive calibration. No frozen-family retuning from observed holdouts; any future model needs independently admitted full-frame baseline/holdout agreement at original tolerances. |
| Packaging, then root | Complete required ingestion, tested SDK, runtime integration, native build/tests and activation/audit. | Clean relocated consumers and matching native artifact qualify before device tests. |

## 1. Retain the published compiler assertion correction

**Owners:** shaders own the source/fixture repair; validation reviews semantics and outcomes; packaging preserves and publishes the next source epoch. Root integrates and follows actual producer processes.

Preserve the failed focused9 packet, executable, raw logs, XML and actual process closure. Its failed outcome must remain distinct from a successful compiler admission. Build7/inventory9 remain immutable history after sources change.

The focused10 correction changes only the expected substring to `expected '}' for struct declaration`. The diagnostic is derived from unchanged parser routing and the inherited invalid-token control. Publication7 and its independent complete source-publication admission pass; generation12 and its independent result admission pass. The original failed XML and assertion repair remain retained. Parser rejection, `has_error()`, all 423 declarations and production grammar remain unchanged.

The independently reviewed repair has two parts, now published:

1. **Internal helper builtin text path.** The exact `__helper_invocation` spelling now has a dedicated reserved token and is consumed only inside `@builtin`. Public builtin enum parsing, ordinary-identifier rejection and the resolver's extension allow-list, explicit enable, scalar-bool and fragment-input constraints remain restrictive. Nine new lexer/parser controls cover the exception and forbidden positions. Compute-input and fragment-output negatives now check actual semantic stage/direction diagnostics rather than matching text in lexical-error excerpts.
2. **SPIR-V fixtures and semantic assertions.** The loop checks discard → body query → store → continue, a second query → `break_if`, and true-exit/false-backedge behavior. The missing-extension fixture checks extension absence and mandatory SPIRV-Tools capability/extension refusal. Flat is added only to the invalid integer helper-input fixture so it reaches the bool-scalar rejection. Strict validation and the invalid uint negative remain intact.

All 414 inherited test declarations are preserved, with nine new controls. Previous source bytes, the failed focused9 outcome and the reviewed patch are retained. Check the actual publication outputs and current source before starting the next generator; follow any failure into a bounded repair while preserving its diagnostic and semantic assertion.

**Exit:** the corrected negative and all4,210 focused tests retain their historical build9 pass. Current build12 and compiler14/focused14/full15/consolidated CPU gates now pass. Full11, focused12/13 and full14 reporting failures remain immutable history; interface/ingestion and all native/rendering exit gates remain open.

## 2. Qualify the fresh dependency and complete shader ingestion

**Owners:** packaging owns generation/build/interface helpers; shaders own compiler behavior; validation owns independent admissions and ingestion checks. Root follows original child handles to closure.

Execute the following sequence using actual inputs and receipts at every boundary:

1. Retain [publication10 admission](../../../build/evidence/line-helper-focused13-publication10-review-shaders-2/result.json), [generation15 admission](../../../build/evidence/line-helper-focused13-generation15-review-shaders-2/result.json), [recipe15/phase19 admission](../../../build/evidence/line-helper-focused13-recipe15-outcome-review-validation-2/result.json), [stale13 admission](../../../build/evidence/line-helper-stale13-review-validation-1/result.json), [configure12 admission](../../../build/evidence/line-helper-configure12-review-validation-2/result.json), [complete build12 admission](../../../build/evidence/line-helper-compile12-review-validation-1/result.json) and [supervisor14 emitted-source admission](../../../build/evidence/line-helper-supervisor14-emission-review-validation-1/result.json). Their original processes are closed; no replay is required.
2. Retain [inventory14 admission](../../../build/evidence/line-helper-compiler14-inventory-review-validation-1/result.json), [focused14 admission](../../../build/evidence/line-helper-compiler14-focused-review-validation-1/result.json), [full15 admission](../../../build/evidence/line-helper-compiler14-full-review-validation-1/result.json) and [consolidated CPU suite admission](../../../build/evidence/line-helper-compiler14-suite-review-validation-1/result.json). All required CPU bodies and original occurrence/XML/source/disabled/duplicate gates pass. Inventory14 derives only the exact four predecessor independent-review origins, preserving every initial hash.
3. Retain [Graph11 admission](../../../build/evidence/line-helper-build12-graphs-outcome-review-root-1/result.json) and [corrected PP8/COFF9 metadata admission](../../../build/evidence/line-helper-build12-metadata-outcome-review-root-2/result.json); source-admit the demonstrated CMake-input path correction, then independently admit fresh logical interface proposals. Preserve the original wrapper observation and both failed Interface9 attempts.
4. Run/admit the required native-policy and reader4 CPU ingestion/probe chains below against the same accepted build and proposal bindings. Admit complete physical origin inputs before the new lock/physical origins, final interface and SDK10 production. No failed, source-only or isolated observation scope unlocks SDK/native qualification.

Check available disk space before SDK staging and native compilation. [Lossless historical-build7 compression](../../../build/evidence/line-helper-build7-compression-1/after.json) closes0 and verifies all 6,034 logical names and bytes unchanged. Later [historical-build8 compression](../../../build/evidence/line-helper-build8-compression-outcome-review-validation-1/result.json) also closes0 and admits all6,034 logical names and bytes unchanged. Its actual post-check records5,426,917,376 free bytes. Measure space again before substantial new output. Utility stdout was truncated and is labeled accordingly; complete logical integrity is established by the independent stored-map comparison.

Preserve both focused failures, their actual closures/XML and unrun full9/full10. Reuse unchanged qualified transport algorithms and controls at their original scope. Never overwrite an executed attempt or run a success reader on a failed manifest.

Require exact occurrence expansion, the four inherited duplicate pairs, disabled-case disclosure, command bounds and strict XML. Missing, foreign, failed, errored or unexpectedly skipped required cases refuse admission. Passing focused tests are required before the full suite; neither an inventory nor a failure-reader receipt unlocks SDK production.

[Graph11 admission](../../../build/evidence/line-helper-build12-graphs-outcome-review-root-1/result.json) retains all three actual graph projections. [corrected PP8/COFF9 metadata admission](../../../build/evidence/line-helper-build12-metadata-outcome-review-root-2/result.json) admits PP8 tint/bundle, the corrected dawn_native_objects native producer and COFF9. The original native wrapper receipt retains its valid metadata scope; [retained Interface9 wrapper refusal](../../../build/evidence/line-helper-build12-interface9-failure-outer-observation-root-1/outer-observation.json) remains immutable. Logical proposal, required ingestion/origin inputs and final-interface gates remain pending; both Interface9 refusals remain preserved. Preserve exact archive order/repetitions, native object aggregation into webgpu_dawn, evaluated imports, public headers/defines, CRT, licenses and system libraries, typed -ignore:4221 and the aggregate compiler-controls role. Logical proposals do not close the final interface gate; physical origin inputs, the new lock and independent final-interface admission remain required.

Then run the required native-policy controls and reader4 chains against these admitted interfaces: 24 controls/16 outputs; all twelve native-demote SPIR-V chains, twelve explicitly emulated MSL chains and twelve negatives. Each positive must complete validation, ReadIR, core IR, ProgramFromIR, emitted WGSL, actual text parsing, inspection/lowering, validated IR and backend writing. Preserve implicit sampling and query/demote order, production-default restrictions and strict derivative/MSL negatives.

**Exit:** passing full compiler suite, complete interfaces and required ingestion controls against one admitted build. The emulated MSL CPU chains do not close genuine Metal helper/demote behavior, including normal MSL2.3+ and queries after discard. Shipping Vulkan/Metal module, complete pipeline configurations and raster qualification follow the native build.

## 3. Stage a tested SDK and coherent dependency identity

**Owners:** packaging owns origins, lock/descriptor/staging and clean consumers; validation admits complete contents and identities.

Bind actual build12/compiler14/full15 and proposal/ingestion receipts while admitting the complete physical origin inputs, source delta, public headers/licenses, unrelated baseline and native4 inventory. Produce the revised lock and physical origins, then independently admit the final public interface before descriptor10 and staging. The six admitted source placements are separate from runtime import and production qualification. Preserve all five shipping archives, six public targets, exact options and platform dependencies.

Run relocation and external clean configure/link consumers after SDK production admission. Require exact target properties and source/dependency/interface identity through cmake/dependencies.lock.json, cmake/NativeSDK.cmake, descriptor10 and the eventual native build. Reuse unchanged admitted sealing/origin/link controls; [SDK10 changed-function controls admission](../../../build/evidence/line-helper-sdk10-inventory-controls-review-packaging-1/result.json) supplies the new meaningful inventory/source guard checks. The inventory14 effective map preserves every initial digest and validates each of its four exact predecessor-review origins; focused/full protection remains strict. No general evidence-prefix allowance or historical SDK equality receipt qualifies the current epoch.

**Exit:** a tested, independently admitted and relocatable SDK tied to the repaired dependency epoch. Historical SDK/header syntax checks do not qualify the new runtime.

## 4. Integrate the canonical consumer and runtime line path

**Owners:** root owns `cpp/runtime.cpp`, `cpp/runtime_state.hpp` and runtime resource helpers; shaders own `cpp/shader/` compiler/evaluator/consumer code. Packaging owns CMake/SDK integration; validation owns independent fixtures. Keep file ownership explicit during parallel edits.

Integrate the reviewed candidate from `build/line-runtime-consumer-policy-integration-work-1/candidate` and its corrected source handoff. Preserve acknowledged replacement origins before publishing live source. Compile all native targets against the tested SDK and run matching integrated/inherited CTests.

Retain exact original/evaluator/policy/generation identity, immutable per-policy records held by DRAW/LineWork/Tickets, the shared 128-entry FIFO, deduplicated descriptor charging, checked budgets and loss behavior. Retain independent line readiness, full original uniform prefix plus the 64-byte ABI2 block, and compute-before-render on the same leased Ticket. Capture requires both diagnostics and capture. Genuine LINK failures and contextual capability refusals remain observable.

Freeze the matching source/SDK/context, complete the native build and guarded activation, and independently audit the installed candidate. Then run the three genuine native admission/retirement cases and all affected regression packets against that exact artifact. Preserve native34 and its qualified references for comparison and recovery.

**Exit:** complete native compilation, matching installation/audit and genuine native ownership/rendering evidence. The 538 standalone CPU checks remain supplementary to these results.

## 5. Finish required line behavior and ownership

**Owners:** shaders implement coverage/compiler policies; root implements runtime ownership/partitioning; validation fixes independent references and native fixtures before candidate observation.

Qualify aliased rendering first, then the remaining line policies against all original 16 plus six private/clipped references. Retain the fifteen successful original captures and old failed smooth-depth record unchanged. The newly admitted depth frame is published through its [per-case reference descriptor](../../../build/evidence/line-opengl-smooth-depth-source-publication-1/reference.json); bind its explicit source provenance in future contexts. Require once-only original vertex/fragment execution, six-plane homogeneous clipping, perspective/noperspective/flat-LAST interpolation, original segment/index/instance identity, helper/demote behavior, depth/stencil/scissor/blend and correct preceding copy/FBO order. Use actual fixture bindings, sample types, color/depth formats and sample count; qualify normal rendering and capture with diagnostics disabled.

Retain the passed original-OpenGL probe2, its15 guard controls and admitted provider freeze. The unchanged full-RGBA baseline reproduced exactly before two supplemental captures. Across the full frame, baseline green equals unblended alpha; endpoint alpha is 164, framebuffer sRGB is disabled and dithering is enabled. This localizes that fixture's discrepancy to stored coverage before RGB blending; it does not establish a general analytic filter or exclude dithering. Resolve the model with bounded original-only measurements before implementing SmoothReference. The twelve fixed CPU models remain exploratory. Keep reference value 164 and original tolerances.

The fixed24 job has closed successfully and its complete context and capture are independently admitted: unchanged baseline first, eleven predetermined alpha-zero blend-off/on geometry pairs and one separate dither-disabled diagnostic. Every frame, state, GLIR, vertex binding, provenance and actual closure is retained. Work2 and all nine archive controls remain admitted; preserve the Windows fixture failure and unexecuted source1 without replay. The bounded study evaluates six declared hypotheses against all 24 frames. Its compact empirical model matches the horizontal training frames but fails 35 pixels in each oblique holdout frame, including missing support pixels. It does not qualify a general filter.

The orientation32 proposal, producer/reader sources, composed context and [all32 original captures](../../../build/evidence/line-opengl-smooth-orientation-result-review-shaders-1/result.json) now have independent passing admissions. Retain these completed packets and prior failures without replay. The [finite mathematical model contract](../../../build/evidence/line-opengl-smooth-orientation-model-contract-review-validation-1/result.json) is independently source/data-admitted:162 fixed coupled polygon-convolution candidates, twelve blend-off training geometries and three new holdout pairs excluded from selection. Work1 source review found premature holdout hashing/state opens; its sealed source is preserved unrun. Corrected work2 defers every nonselected capture artifact until exclusive calibration and all32 predictions are sealed. Its [independent39-control admission](../../../build/evidence/line-opengl-smooth-orientation-model-controls-review-packaging-2/result.json) includes911 passing subcontrols and17 retained synthetic fixture trees. The [fixed study](../../../build/evidence/line-opengl-smooth-orientation-model-study-2/result.json) completes with selected index9 (box,radius0.5,extension0.125,bias0,floor32_fixed5): training alpha-error sum2,549/max17/287 differing pixels. Its32-frame prediction differs at860 pixels; all six holdout frames fail, with258 differing pixels. The model remains unqualified. The [independent negative-study admission](../../../build/evidence/line-opengl-smooth-orientation-model-study-outcome-review-validation-2/result.json) independently verifies all162 training reductions, the frozen winner and all32 selected plus192 old-model comparisons. Investigate training mechanisms and require a new predeclared contract with unseen holdouts for future model selection. The old oblique failure remains an observed regression. Preserve original references, tolerances and endpoint164; no per-frame/pixel corrections. A new mismatch refuses model qualification and cannot retune the frozen family from holdout data.

The [depth fixture/reference publication](../../../build/evidence/line-opengl-smooth-depth-source-publication-1/result.json) applies six explicit initialization lines before the two unchanged draws. Its single original capture and independent complete admission pass all six landmarks, two draws and one final read. Canonical fixture hash2568 replaces f689 with prior bytes archived; the old failed capture and all 15 successful references remain exact. All jobs bound to the prior source closed before publication. Future contexts must acknowledge the new fixture and per-case reference provenance; historical contexts and references retain their original identities.

Implement `SmoothReference` only from the resolved model. It must provide a genuine second consumer policy alongside `AliasedMajorAxis` for the same original/evaluator identity and device. Qualify pending, queued and submitted A→B→A snapshots/Tickets, retained old selections, first-use B costs and zero-work warm A reuse. Exercise the shared 128-entry FIFO and joint byte budget, eviction with deleted/retained owners, and loss/new-generation recovery with full reference frames. Width/viewport/topology changes alone do not constitute that second policy.

Complete ordered line partitions across actual storage/stride/binding/workgroup limits, carrying strip/loop boundary rows without reevaluating the user program. Finish MSAA, early depth/stencil tests, fragment side effects, joins/caps, picking and the existing Agg path; enable each policy only with its matching evidence. Retain contextual refusals while those implementations remain unfinished.

Close the remaining milestone-2 native fault, capacity and ordering cases alongside line work: pipeline/encoding/queue/map/timeout failures, simultaneous owners, mixed mutations and pending snapshots, texture/FBO order, nonpolling ownership inspection, the caller-owned one-MiB diagnostic arena, actual physical allocation scope and once-only retirement after true completion. Preserve original graphs and qualified public FIFO behavior.

**Exit:** full required line/ownership behavior on matching Vulkan and Metal artifacts, including independent raster, retirement, capacity and warm-cost evidence.

## 6. Close remaining renderer and release milestones

The compiler repair unblocks the implementation; it does not complete the renderer. Preserve the detailed [milestones 4–6](2026-10-10-vispy-vulkan-continuation-plan.md#milestone-4-finish-scientific-rendering-and-hosts) and all original requirements:

- Finish ordinary layout/storage partitioning, typed transfers/sampling, images/labels, markers/picking, shapes/meshes/composed filters, vectors/tracks, Grid/axes, fixed-font SDF text at 96/120/144 DPI and every required scalar/categorical volume path. Preserve quality, reference arrays, geometry identity and warm reuse.
- Qualify installed napari, Glue, DIVE and declared visbrain/plugin workflows, including actual interaction, export, recovery and teardown. Prepare pinned upstream/candidate environments and Linux/macOS producers/runners in parallel. Require real reflected corpus pipelines on both Vulkan and Metal.
- Finish asynchronous frame/presentation attribution, actual compiler/link/upload/draw/wait counters, uncertainty and physical-memory/Metal allocation observations. Qualify Windows Qt bindings, Linux X11/xcb including XWayland and macOS13+ arm64/x86-64 lifecycle rows on the designated software/integrated/discrete adapters.
- Build final CPython3.10–3.14 Windows wheels and declared Linux/macOS artifacts from qualified frozen source. Verify the 100-MiB compressed-wheel budget, licenses/assets/origins, external clean rendering/host consumers, uninstall/restoration and all sixteen original review-finding regressions. Missing required host or hardware rows remain open rather than passing skips.
- Run all 66 fixed-quality performance workloads on final artifacts: 4096² images with one/eight layers, one million points and 256³/512³ volumes. Use at least 100 warmups, 1,000 measured frames and five alternating upstream/candidate pairs. Require median speedup ≥1.20, no p95 regression, update regression ≤10%, and zero unchanged warm compiler/pipeline/upload/conversion work and deliberate waits for each required row.

**Release exit:** every original correctness, scientific, host, platform, lifecycle, artifact and performance condition passes on the final matching source and artifacts.

## Parallel work and immediate handoff

| Branch | Work that can progress now | Dependency before execution/qualification |
| --- | --- | --- |
| Compiler and packaging | [complete build12 admission](../../../build/evidence/line-helper-compile12-review-validation-1/result.json) verifies all six Release outputs and the complete source/build/protected/tool maps. [inventory14 admission](../../../build/evidence/line-helper-compiler14-inventory-review-validation-1/result.json), [focused14 admission](../../../build/evidence/line-helper-compiler14-focused-review-validation-1/result.json), [full15 admission](../../../build/evidence/line-helper-compiler14-full-review-validation-1/result.json) and [consolidated CPU suite admission](../../../build/evidence/line-helper-compiler14-suite-review-validation-1/result.json) pass at complete Tint CPU compiler scope. 56,900 compiled occurrences, 56,896 unique IDs, 56,890 enabled occurrences and 7,168 focused instances; 276 authored rows include 148 new definitions. Ten normal disabled cases and the four original duplicate pairs remain exactly two each. [Graph11 admission](../../../build/evidence/line-helper-build12-graphs-outcome-review-root-1/result.json) retains all three actual graph projections. [corrected PP8/COFF9 metadata admission](../../../build/evidence/line-helper-build12-metadata-outcome-review-root-2/result.json) admits PP8 tint/bundle, the corrected dawn_native_objects native producer and COFF9. The original native wrapper receipt retains its valid metadata scope; [retained Interface9 wrapper refusal](../../../build/evidence/line-helper-build12-interface9-failure-outer-observation-root-1/outer-observation.json) remains immutable. Logical proposal, required ingestion/origin inputs and final-interface gates remain pending; both Interface9 refusals remain preserved. [SDK10 source admission](../../../build/evidence/line-helper-sdk10-source-review-shaders-1/result.json) passes source-only review. [SDK10 changed-function controls admission](../../../build/evidence/line-helper-sdk10-inventory-controls-review-packaging-1/result.json) passes 15 synthetic methods/49 case subchecks with zero failures, errors or skips; 79 events and all 2,599 fixture files are retained. Six exact SDK10 source copies and their [source-handoff/path identity admission](../../../build/evidence/line-helper-sdk10-source-handoff-review-shaders-1/result.json) pass source-only scope; actual runtime import and production remain unrun. Origins, new lock, final descriptor, staging, relocation and native qualification remain pending. | Admit logical proposals, required ingestion and complete origin inputs, then new lock/physical origins and final interface before SDK production/clean relocation and matching native integration. Source preparation and synthetic controls retain their own scopes. |
| Runtime | Prepare integration and fixed native ownership/reference fixtures from the reviewed candidate. | Tested SDK and matching native build/audit before device qualification. |
| Smooth reference | Retain the independently admitted failed finite-model study and investigate the training mechanism under a new predeclared hypothesis. | Seal training selection before new holdout access; require complete full-frame model validation and explicit depth-reference provenance before filter/second-policy qualification. |
| Platforms and hosts | Prepare pinned environments, Linux/macOS producers and required runner/host inventories. | Matching artifacts and actual devices before declaring graphics/platform success. |

Admit the demonstrated CMake-input path correction and fresh logical interface proposals, then run/admit the required native-policy and reader4 CPU ingestion/probe chains on build12. Admit the complete physical origin inputs, source delta, public headers/licenses, unrelated baseline and native4 inventory; produce the new lock and physical origins, then independently admit the final public interface. Descriptor10, staging, clean relocation/configure/link/probe and their independent admissions follow those gates. NativeSDK/CMake/runtime47 integration and the state-contract repair then require a matching native build/tests/install/audit and genuine ownership/raster evidence. Scientific, host, platform, package and every original performance/release gate remain open. Retain the negative162-candidate smooth study and its admitted32 captures/39 controls without replay or retuning; new model/capture/provider work is outside this immediate batch. Any future smooth hypothesis needs a new admitted contract and unseen holdouts. Reuse unchanged qualified evidence and repeat only checks justified by changed behavior or an unresolved result.


## Continuation checkpoint, 2026-10-12

This checkpoint supersedes the pending status in the earlier immediate handoff while preserving that historical record. Cybersecurity work is excluded by the user.

The CPU ingestion and policy checks now have [independent complete admissions](../../../build/evidence/line-consumer-build12-ingestion-outcome-review-packaging-1/result.json). The original 12 input rows, 24 positive cases, 12 negative cases and 24 WGSL reparses are preserved. The policy scope passes 24 checks and 16 outputs. Physical dependency capture and the new lock have [independent Origin2 admission](../../../build/evidence/line-helper-sdk10-origin-outcome-review-validation-2/result.json), covering all 119,083 physical files without relabeling the upstream lock. The [final physical public interface admission](../../../build/evidence/line-helper-sdk10-interface-outcome-review-packaging-2/result.json) passes all 209 public archive/header/license rows and six targets. Earlier failed review packets remain unchanged.

[Descriptor authoring](../../../build/line-helper-dependency-work-1/sdk-descriptor-attempt-1/result.json) passed its single original process. It describes 210 copy rows, three generated metadata files, and 214 total SDK files including the future manifest. Root checked the complete packet, all 241,391 named inputs and the separate four installed native files. This is metadata authoring; staging and runtime initialization still need their own actual results. Its reviewer is receiving the same narrow public-versus-private archive classification correction already proven by the final-interface review.

The [corrected runtime/CMake dependency-lock bridge](../../../build/evidence/line-native-origin-runtime47-integration-source-review-root-2/result.json) passed source review, including independent Packaging review. All four native SDK/origin calls and the CMake/CLI/cache paths now select the admitted captured lock. The 47 runtime rows, five bridge rows with one CMake overlap, and State14 repair derive 52 source destinations. Source application and a matching native build remain pending.

Continue in this order:

1. Admit the corrected descriptor reviewer and run its actual review once.
2. Stage the exact SDK under the measured storage budget; measure free space again before copying it for relocation.
3. Configure and link the clean public consumer against the relocated SDK. Admit both complete SDK byte maps and the two actual child process results.
4. Run the clean CPU initialization executable once, then independently admit its actual result.
5. Review the complete source application proposal, retained before bytes and source/harness preservation maps; apply the 52 admitted destinations.
6. Complete the new dependency-lock correctness controls and fresh ownership/ACK records. Freeze the matching source, then build the 24 declared targets and execute the exact 26-test CTest inventory. Install and audit only the matching admitted artifacts.
7. Continue the required native ownership and raster checks on those artifacts. CPU or SDK results alone do not close the renderer, scientific, host, platform, packaging or performance requirements.

The new smooth model, capture and provider study stays outside this immediate batch. Reuse unchanged qualified evidence; rerun only changed behavior or an unresolved check.


The actual descriptor reviewer subsequently refused attempt1 because three original CPU admission maps include the four installed native-file guards. Those guards must remain separate from immutable staging inputs. The failed review is retained at [descriptor review attempt1](../../../build/evidence/line-helper-sdk10-descriptor-outcome-review-shaders-1/result.json). Before step1 can close, prepare SDK11's narrow admission classification correction, capture native before/after separately, and carry its exact source identities through fresh execution/reviewer bindings. Keep the original CPU proofs and descriptor attempt1 unchanged. Run the changed descriptor producer under a fresh attempt after source review; resume steps2 onward only after its independent admission.


Continuation evidence, 2026-10-12: the [new lock-selection controls](../../../build/evidence/line-native-origin-runtime47-lock-controls-outcome-review-packaging-1/result.json) pass all 21 methods and 83 fixed cases, including captured-lock selection, dependency CLI forwarding and cache values. All 1,080 fixture files, logs, XML, original Root process and unchanged inputs are independently admitted. The [six SDK native-classification controls](../../../build/evidence/line-helper-sdk11-native-classification-controls-review-packaging-1/result.json) also pass all six actual extracted-admission calls with zero failures, errors or skips. They admit the changed synthetic boundaries only; original compiler/CPU controls were not replayed.

[SDK11 source review](../../../build/evidence/line-helper-sdk11-native-separation-source-review-root-1/result.json) admits the narrow correction: all four installed native files still receive exact digest checks, remain separate from immutable SDK inputs, and have before/after guards. The old descriptor producer and failed review stay unchanged. The fresh descriptor11 attempt2 was launched once through the original Root process and is checking the retained dependency inputs at this checkpoint. The descriptor reviewer3, execution2 stage/relocation reviewer3, clean wrapper2 and clean outcome reviewer2 have fresh source admissions using actual source identities. SDK staging, public configure/link, the one CPU initialization run, the 52-destination source application and matching native freeze/build/install/audit still require their own actual passing outcomes, in the order above.

Descriptor handoff checkpoint, 2026-10-12: descriptor11 attempt2 now passes, with all 241,388 immutable input bytes checked and native4 protected separately. The corrected [descriptor reviewer4](../../../build/evidence/line-helper-sdk10-descriptor-outcome-review-shaders-3/result.json) independently admits all 210 copy rows and 213 planned files; its original process closed with exit0. Root checked all 241,563 reviewer inputs, the whole held reviewer source and original process transcript. The earlier local-path name collision and its failed review remain preserved.

Before SDK staging, finish the fresh metadata input author correction: the actual review records its helper and seal in its input map and separately verifies the complete source folder. Require those two recorded source rows together with the complete held source and Root source admission. Preserve the unrun earlier author. Then create the exact twelve-key staging inputs once, check fresh raw disk budget, and continue the existing stage, relocation/link, CPU initialization and source/native gates in order. No compiler/CPU producer replay is needed.

SDK staging preflight checkpoint, 2026-10-12: the exact twelve-key [staging inputs](../../../build/line-helper-sdk11-staging-inputs-attempt-1/result.json) pass their metadata guards. The first actual EXEC2 stager stopped before creating either output folder because its private-Tint prefix check rejected the admitted public `include/tint/tint.h`. Preserve its [original failure](../../../build/evidence/line-helper-sdk11-stage-preflight-failure-root-1/result.json); no SDK byte copy, configure, compile or native action occurred.

[SDK12 source review](../../../build/evidence/line-helper-sdk12-public-header-source-review-root-1/result.json) admits a single preflight correction: allow that exact public header while retaining every other Tint-prefix exclusion and all five ABI/object suffix exclusions. The descriptor, origin, CPU and interface proofs and staging-input bytes are unchanged. Fresh EXEC3 holds the corrected contract with the stager, relocator and C++ probe byte-exact to EXEC2. The changed [shipping boundary controls](../../../build/evidence/sdk12-shipping-boundary-controls-attempt-1/result.json) pass all five methods and 29 fixed manual cases, with zero failures, errors or skips and all fixtures retained. Complete their independent outcome admission, then remeasure the actual EXEC3 raw budget and run the changed stage once. StageReloc4 and Wrapper3 have actual source admissions for the fresh execution path; follow relocation, CPU initialization, source application and matching native gates in the original order.


SDK12 actual-stage checkpoint, 2026-10-12: the shipping boundary controls now have [independent admission](../../../build/evidence/sdk12-shipping-boundary-controls-outcome-review-packaging-1/result.json). The single EXEC3 stage copied all 213 planned files, then failed its literal inventory comparison because Windows preserved the shared directory as `include/SPIRV`, while 36 admitted SPIRV-Headers paths use `include/spirv`. All file digests match. The [bounded failure review](../../../build/evidence/line-helper-sdk12-stage-failure-review-packaging-1/result.json) verifies the retained partial SDK, failed packet and original Root transcript. No manifest, relocation, compiler or native success is claimed; the complete 241,568 before/after input guard is preserved without another unchanged census.

Continue with SDK13's reviewed deterministic directory-ancestor projection. Keep descriptor11 and original interface/source/CPU admissions unchanged. Preserve filenames, content hashes and complete logical-to-physical provenance; reject file collisions, file/directory conflicts and undeclared aliases. All consumers must derive the same physical map, and the unchanged format2 verifier must continue requiring literal actual inventory equality with manifest files. Meaningful Windows copy-order and refusal controls, fresh source admissions, a fresh raw storage budget and one fresh staging attempt precede relocation/link and CPU initialization. Preserve the failed SDK12 prefix unchanged. Cybersecurity work remains excluded.


SDK13 namespace checkpoint, 2026-10-12: [Root source review](../../../build/evidence/line-helper-sdk13-namespace-source-review-root-1/result.json) and [independent Packaging source review](../../../build/evidence/line-helper-sdk13-namespace-source-review-packaging-1/result.json) admit the complete directory projection and logical-to-physical provenance ledger. EXEC4 preserves the existing format2 verifier, relocator and C++ probe. The [actual namespace controls](../../../build/evidence/sdk13-namespace-controls-attempt-1/result.json) pass seven methods and 36 fixed cases, including two retained 213-file synthetic Windows trees copied in opposite orders. [Independent actual-outcome review](../../../build/evidence/sdk13-namespace-controls-outcome-review-shaders-1/result.json) admits all 50 events, seven XML rows, 37 fixed fixtures, 428 runtime files and unchanged source/native/Python guards. These controls establish their synthetic namespace scope; actual SDK qualification remains a separate gate.

StageReloc5, Wrapper4, CleanOutcome4 and CleanInputs3 now have complete Root source admissions for the same physical namespace, preserved original schemas and current execution4 bindings. The fresh SDK13 raw budget requires 1,699,756,509 bytes, with 142,274,637,824 free when measured. Root launched execution4 staging once through original tool699be0/session86855; its original preflight remains active at this checkpoint. Continue by preserving the terminal transcript, checking the actual whole SDK and manifest, remeasuring relocation space, then following public import/link, one CPU initialization, source projection and matching native build/install/audit.

The user requested temporary build cleanup. A bounded audit identified five disposable caches containing 101 files and 1,805,667 raw bytes outside all retained guard maps. Automatic approval review rejected both recursive cleanup and a safer individual-file removal as "blocked by policy" before execution. No files were deleted and no workaround was used. The [cleanup audit](../../../build/line-workspace-temp-cleanup-record-2/result.json) preserves that result. Active SDK, source, evidence, vendor and native outputs remain held for the following checks. Cybersecurity work remains excluded.


### 2026-10-12 SDK13 actual staging passed; relocation in progress

The original Root staging invocation (tool699be0, session86855, terminalab78bc) closed with typed exit0. Its sealed result reports selfPID38472, passed_SDK_staging, SDK_staged/format2_verified true, no child/compile/native import/device/GPU use, 214 physical SDK files, exactly36 directory-ancestor rewrites and 177 unchanged planned paths. The241568 protected before/after entries and separate native4 maps match. Root independently checked all214 current SDK files, the descriptor-derived namespace/provenance ledger and literal manifest namespace (tool8b9663, exit0); the complete current guard rehash remains a separate independent outcome-review requirement.

Actual stage packet: build/line-helper-sdk10-execution-work-4/stage-attempt-1/result.json (50d210afaa0a97ac1862e18e50cdfc97cdcc1cbebf963cf035c4220a1f538b2a), seal243f49cc5cff9127a97d928fa8455c41986944a95cd1b43d7996b07d66bb8624. Manifest1891ddd710e4d9f3a158759beb7ed7f3a494ff7698970ee8ff67319e7b8d2151. The original observations and argv were saved before post-querying in build/evidence/line-helper-sdk13-stage-outer-root-1 (outer8c42b8eee90bd3234c32897bb127fadd7600d891733eb4f273ba58ade2fabd1b; seal9c2c0202124e811cd673e4189f5cf867d208ac4b57bb8431c85bc1db241d716d). PID is confirmed from the actual sealed result; stage stdout does not contain a PID.

Fresh relocation budget passed (cbbe1b, exit0): raw4114914730 bytes versus fresh142434344960 bytes, including the actual891764352-byte SDK, cluster padding, explicit consumer-build and metadata allowances, and retained-failure headroom. One unchanged relocator invocation launched (814de7, session18544) with currentEXEC4 source, actual stage pins and absent import-attempt-1/relocated-sdk-1 destinations. It is still running; no relocation, CPU, source-application or new-native-build success is claimed. Continue with its original terminal/outer, StageReloc5 independent child admissions, exact11-key CPU input authoring, one CPU child, canonical source proposal/application and new native ownership/build checks.

Cleanup remains blocked by automatic command review; neither rejected deletion attempt executed. Retain the corrected build/line-workspace-temp-cleanup-record-2 audit and all guarded outputs.


### 2026-10-12 relocation compile failure preserved; minimal SDK14 source fix

The original relocation invocation (tool814de7, session18544, terminalb6e87b) closed with typed exit1, selfPID58848. Configure child46588 closed0; build child34152 closed1. The sealed65-file import-attempt-1 packet records failed_relocated_SDK_import_link and no executable. Result076ad4d8b5614c0a1ce07d7705b64553d974f6c812d36c3e705e61fc23a58394; seal6c0ad165cbf6a68c79dc116adcbd248761460cab17d5239d7379c2f0b4d1df7f. The original argv/tool objects were saved first in build/evidence/line-helper-sdk13-relocation-failure-outer-root-1 (outerfeba61645d5dae7071b321dcc43a56afea5a41586c95208a17485b0abc9347c4; seal37306945e7e72927ab2061025e19a97d4c3dd008f8a7e6b7b022d438abf62133). Root bounded failure reviewb363d3 checked both214-file current SDKs match, all241573 stored before/after inputs match, both original child closures are retained and current native4 is unchanged. It does not claim a new full current241573 rehash.

The compile log and actual public headers isolate two misspelled namespaces: probe uses spirv_tools::SpirvTools/Optimizer, while both SDK headers declare spvtools. Includes and SDK header bytes are correct. No link or CPU initialization succeeded. Retain the passed stage4 SDK and failed relocation; fix exactly those two tokens in fresh EXEC5. A narrow new relocator guard must bind the source SDK and stage packet to the actual pinned stage-helper4 parent, while fresh relocation outputs remain exclusive EXEC5 siblings. Contract remains byte-identicalef03. Shader owns SDK14/StageReloc6/Wrapper5 SOURCE descendants; Validation owns CleanOutcome5/CleanInputs4 with explicit mixed stage4/relocation5 roles. No old helper, proof or SDK is rewritten.

A further downstream gap is now being implemented in fresh isolated native activation SOURCE: old installation/cache audit/build-handoff helpers hardbind epoch34/oldSDK/obsolete manifest fields. Packaging owns minimal generic mandatory-actual-input descendants, unchanged transaction primitives where possible, strict26-CTest/24-target/full-binary-map build review and small synthetic changed-binding controls. Actual ownership/freeze/build/admission/activation/audit remain unrun. Source qualification, fresh budgets and actual complete results are still required.


### 2026-10-12 corrected probe verified; fresh relocation5 running

The exact two-token spvtools correction (probe6c886e2ab95c469e075f7a9e52247d38a36dd9e48dfc7d2ea952d20a0d2f403a) passed one real MSVC syntax-only invocation ddde8f, typed exit0, with /Zs and the pinned MSVC/Windows SDK headers and Release/DLL/legacy-mutex policy. No output files were requested. The retained three-file build/evidence/line-helper-sdk14-public-probe-syntax-root-1 packet (result3c75438bcc84434a75a3ba328ce35dc3f94dc499b7e19c1cc19dc361829295a7; seal55ee6f3daa2a91b1d26ea880a2d3bd792ef29489587f5b468b0a26d6c1392513) confirms all214 SDK files preserved and current native4 exact; linking/initialization remain separate gates.

Root Source review340f3b cleared SDK14 whole20/19parents/current216 and five unchanged raw/AST relocation functions. One actual synthetic source-role control24c9a6 (selfPID65900, typed0) passed one method/nine fixed cases (one positive/eight refusals), with all216 inputs and native4 preserved. Result29a15196f5375e3b72a2674c0d6b6975b1b89bde585dd48d81314c2f9b935215; sealb1aa7fe9a1c82ebd0b6fd21e8e18aeb412f7035b74d958db9f38e1b2817c167d. Root saved its original inline source/argv/tool return separately in the control outer packet.

Fresh budget7d1e76 passed required4114914730 raw bytes against fresh165007511552. Exactly one fresh relocation5 launched eed697/session19039, retaining the actual passed stage4 result/seal/manifest and stager4 pin, with new relocator2067c9b1ce65fa11ea0048c4b0638391380c8340a96e5eaf167f07a7fb18c9ee, probe6c886, byte-exact contractef03 and absent EXEC5 import-attempt-1/relocated-sdk-1. It remains live; no final success is claimed.

All caller SOURCE gates now clear: StageReloc6 Root5 (35752431…/ed3dec63…), Wrapper5 Root5 (a048927f…/c8494fec…), CleanOutcome5 Root5 (a7b117e8…/b26f8d57…), CleanInputs4 Root4 (b4cfb32c…/8452e29d…). Schemas8/11/7/11, original process follow/finally code, physical namespace ledger and explicit stage4/relocation5 roots remain intact.

Independent native activation source review found concrete project-versus-tool ACK, cache-owner/state, current-policy, original-session/typed-exit and precommit input-continuity gaps. Fresh Source2 contains the fixes and108 fixed synthetic cases, but its own raw-correspondence postcheck failed on inherited newline normalization. Preserve Source1/Source2 and that failure. Fresh Source3 is authorized only to restore exact donor spans/coupled hashes, with semantic fixes/fixtures unchanged. All native activation controls and production mains remain unrun, pending Source review and actual new ownership/freeze/build receipts.


### 2026-10-12 corrected relocation passed; native installation controls passed

The single corrected relocation invocation eed697/session19039 closed with typed exit 0 at terminal60d77f, self PID64316. Configure child21716 and build child15792 both closed with exit 0. The [relocation result](../../../build/line-helper-sdk10-execution-work-5/import-attempt-1/result.json) preserves 74 files, all 214 relocated SDK files and the linked consumer executable (bbc8af0252441ad0ba1242bb244144da1cd71cc44acbff26b0533f07ff2889de). Its result ca323712e2a8416ead7155435ccd825b7a16477c6089c38078393c67d122fd51 and seal0874e4a73f69389c2beea1c3c1d0626236779d26519f8c38e2d15ce69e96a404 bind the saved original [process transcript](../../../build/evidence/line-helper-sdk14-relocation-outer-root-1/outer-observation.json). The independent StageReloc6 original review316aa7/session74583 has now closed with typed exit 0; its whole receipts and outer observation are being joined before exact11-key clean inputs and one CPU child.

Native activation Source3 restores seven exact donor byte spans while retaining the five reviewed semantic fixes and all 108 fixed fixtures. Root's [complete source review](../../../build/evidence/line-runtime47-native-activation-source-review-root-1/result.json) admits whole138, 12 parent packets and 536 current named inputs; an independent bounded source review cleared the five compatibility findings. The one Root [binding-controls run](../../../build/evidence/native-runtime47-activation-binding-controls-attempt-1/result.json), original toola242ce/self PID54800, passed seven methods and108 subchecks with zero failures, errors or skips. All retained fixture, immutable-source, Python and separate native4 guards match. Its independent retained-outcome audit is still in progress. Production activation, native freeze/build and installed audit remain separate pending actions.

Preserve all failed attempts and original evidence. The temporary-cache cleanup remains blocked by automatic review; no files were deleted. Cybersecurity work remains excluded.


### 2026-10-12 source application admitted; native35 source21 freeze running

The one public SDK CPU initialization run (054557/session57898 to b97aef, driver66856, child60924) passed. Its [independent outcome review](../../../build/evidence/line-helper-sdk10-clean-probe-outcome-review-validation-1/result.json) closed with exit 0 and admitted both 214-file SDKs and 612 current inputs. Source14/SDK/native installation binding controls remain separate from hardware qualification.

The [reviewed projection proposal](../../../build/evidence/line-runtime47-source-projection-proposal-review-packaging-1/result.json) covers 52 destinations. One source application b8d7c8 passed: 30 files changed and 22 already matched. The [application peer](../../../build/evidence/line-runtime47-source-projection-application-review-packaging-1/result.json) admits all current destinations, seven ACKs, 596 project files, 2,288 harness files and 3,431 current named inputs. Canonical native_epoch now has the admitted 9f0502a32bec4eda1abb86a8f663d30161c9c2b3d24ae30403b14322a1029b4a hash.

The original ownership metadata author stopped before output because it expected an obsolete error field. That failure is retained. Source3 changes one conjunct to the actual material_findings list, with 23 other functions and 15 qualified primitives unchanged. The new [ownership author result](../../../build/line-runtime47-native-ownership-attempt-2/result.json) passed original8c30e1/session11973 to9ad848, authorPID5968. It binds epoch35/snapshot21, 25 fresh owned rows, four whole active archives and matching source/harness/SDK/origin authority. Ownership manifest b5d2c573f0b5ad9d1d3d6f8ca0f359ab739a7cee344154ec30793ef003208995 is admitted for the next native execution.

Fresh [resource budget](../../../build/evidence/native-pass-35-resource-budget-root-1/result.json) passed: 247,796,956 raw copy bytes across 3,529 files, complete archives, cluster padding and explicit build/failure/metadata allowances require 22,275,004,179 bytes versus 234,627,731,456 free; 88,845,508,608 physical memory bytes were available. One freeze fe3226/session5215 is running. Native build, 26 CTest outcomes, matching installation and installed audit remain pending.

Step7's existing genuine-three shader/retirement fixture is required after the matching install. All three cases create a real hardware device; the first checks full-frame RGBA rendering and retirement/loss/recovery. Fresh metadata adapters are being prepared for NativeSource3 receipts while preserving the three test/runner/plugin algorithms and reference bytes. No GPU fixture has run on native35. Temporary cleanup remains blocked by automatic review, and cybersecurity work remains excluded.


### 2026-10-12 native35 configure failure retained; exact dataset mappings restored

Source21 freeze passed with frozen-inputs SHA30121900a94aa6aebd7a9e194c935dbfd85bef13ec2ca5953b5d6e0c7f0dec99. The one Native35 build invocation 98a6c8/session98820 closed at 8fcc14 with typed exit 1 during configure: CMake reported the missing frozen point-corpus. No build targets or CTests ran. Its [original failure outer](../../../build/evidence/native-pass-35-build-failure-outer-root-1/outer-observation.json) retains the actual original tool returns and argv (outer4e12742c391cc711b228265f4a20710a22699345f1b9538a6093b3eb96d985c8; seal364d6c07d20793ba9e04b623bc4f81893e73d240399f49d09376ab5cfd3f8ba1). Frozen Source21, failed Native35/cache and the four previously activated native bytes remain unchanged.

OwnershipAuthor Source4 restores exactly 28 existing historical path/SHA mappings: point-corpus16, marker-corpus8, text-corpus2 and volume-corpus2, totaling178,748 raw bytes. The canonical datasets directory was absent, so the prior ownership reconstruction dropped these external mappings. CMake and cache paths remain correct. Only ownership_views changes; 23 other functions and 15 qualified primitives remain exact. The [Root Source4 gate](../../../build/evidence/line-runtime47-native-ownership-author-source-review-root-3/result.json), b8edcf/self PID28628/typed0, admits whole21, 20 parents and212 current named checks (resulte3b0846073704ae6b35bccc11bea7826fe30d99b81d2a50c5cc474f530dc7074; seal7ff3bb4e2fda52870433eeb36d8ed4a39d21b902b368ae3ff50cecee7ea05189). The new [synthetic mapping controls](../../../build/evidence/line-runtime47-dataset-mapping-controls-attempt-1/result.json) subsequently passed one Root invocation d79996, typed0/self PID38604: nine cases, one positive and eight refusals, zero errors or skips. Their scope is dataset-binding correctness.

Fresh observed ownership inputs select Native36/Source22. A new ownership invocation has been dispatched; its terminal receipt is still pending at this checkpoint. Native36 freeze, complete build, 26 CTests, installation and installed audit remain open. No failed Native35 record is relabeled or replayed.

RetirementSource4/Fixture3 have clear Root and [independent source admission](../../../build/evidence/line-consumer-admission-validation-source-review-shaders-4/result.json) (result3324e2e481fc761537ea77b04b85ac34bfa3e085b48df36dc456e001c7f0c84b; seal3eaba054f5d660ecf05e76d73f58990736dab1c81b45c53f0bea091530281e38). The one [metadata authority-controls run](../../../build/evidence/line-consumer-admission-authority-controls-cpu-4-attempt-1/result.json), original0caaff, passed one valid case and13 refusals; its independent outcome admission remains pending. The genuine three hardware fixture cases remain unrun and require the matching admitted native installation.

Temporary cleanup remains blocked by automatic approval review. Both rejected deletion requests stopped before process creation; zero files and zero bytes were deleted. All retained source, failure, fixture and build assets remain preserved. Cybersecurity work remains excluded.


### 2026-10-12 complete historical dataset topology restored; native37 freeze running

The 28-row Source4 correction supplied CMake's corpus inputs but omitted 1,908 historical dataset names required by the unchanged complete-build admission. Native36/Source22 freeze passed (frozen SHA 23e98e8eb698b8ac6f15ea85b56fac51bf84785d9da7c41dac70bbbf72882f32; [original outer](../../../build/evidence/native-pass-36-freeze-outer-root-1/outer-observation.json) 26af2f0f7131ae8ccabe287ff2e8407ac65cb25edfa3fe348894337bcb09d627, seal aea01ebc6bb2ef355bf0dde1b9490b2960fcc24f986e7caa703e609e67c75dd4) and remains preserved without compilation.

[OwnershipAuthor Source5](../../../build/line-runtime47-native-ownership-author-source-work-5/source-ready.json) supersedes that correction with all 1,936 historical logical dataset names and original hashes. Three provenance rows resolve to exact old-SHA copies already retained in Native34's frozen harness; the original mappings and explicit same-byte aliases remain recorded. No bytes were regenerated. Source author a43493/self PID54276 and post 1a38b0 passed. Root Source gate ad85b7/self PID25580 admits whole22, 26 parents and the unchanged 23 functions/15 qualified primitives (result 3602a7cb08647891d2b12254e03e14b22a74df2f7d16e7f1e6090518b7d127e4; seal 59e2a00799f7000dc0e4bf94ed0f28bda5c548f9ab83dd1a3b410e984703d3ef). The one new [synthetic mapping-controls run](../../../build/evidence/line-runtime47-dataset-mapping-controls-attempt-2/result.json), 22bed8/self PID50940, passed ten cases: one valid and nine refusals, zero errors or skips.

Actual Native37/Source23 ownership closed with typed exit 0, original 779faf/session60918 to 197211, self PID54308. Its whole419 packet has manifest SHA 9b2355cdb8bf739e8f7093f09b1dcde14869567a85fb018f4da5c9cd0dd589f0, 596 source rows and 4,097 harness rows including all 1,936 datasets. Root 511dab and independent Shader f5af97 admit the exact old dataset hashes and complete parent source/harness-name subsets. Fresh resource budget 9b211e passed: required 22,771,256,461 bytes, free 403,301,638,144 bytes and physical memory 89,697,923,072 bytes. This is an observed resource point, without a cleanup or reclaimed-space claim. One Native37 freeze, 118ea3/session56724, is still live at this checkpoint. Complete build, 26 CTests, installation and installed audit remain pending.

The retirement authority-controls [independent outcome](../../../build/evidence/line-consumer-admission-authority-controls-outcome-review-validation-1/result.json), f81315/self PID61548, is clear (result f87ab50885bcfa388d1fa6103dc20582ce320236d7ae9fbe70d506e672587c6d; seal 8a861315951d52980d309fe32db97a74a707676fb9e927ba1c79271a4aa994cb); Root bea048 admits whole2 and all 493 current inputs. This qualifies the synthetic metadata cases. The genuine three hardware cases remain unrun.

The current integration batch is approaching its final validation gates. Broader smooth/scientific behavior, hosts and platforms, performance, and other project requirements remain open. Cleanup remains blocked by automatic approval review with zero deletions; all failures and immutable assets remain retained. Cybersecurity work remains excluded.


### 2026-10-12 native37 build and installation admitted; real GPU pipeline failure retained

Native37/Source23 freeze passed with frozen-inputs SHA a17e4fb864f10ccd4617381148d8406a0cd337c5f6a0851a41a63d4d0266ed00. One actual build, 9941a8/session29526 to d60370, closed with typed exit 0: all 24 targets built and the exact 26 CTests passed. The [saved status](../../../build/evidence/native-pass-37/status.json) is 69df26b5fd9b6438e5b1235f75eb3d2948598153c606bb14c58fb6f5d87ac502. The [independent build review](../../../build/evidence/native-pass-37-build-review-shaders-1/result.json) is clear (result 7f23261c2d09113e8317080dae873c16bcf18c68630dac77749691c667d2fbae; seal d754b727870ca3531e94596e613f1baeaec08563e50aeab143aa37a4a516e551), admitting whole4, 4,808 current inputs, 596 source/4,097 harness rows, 45 owners and 26 binary artifacts. Original build argv and closure remain in the [FIRST outer](../../../build/evidence/native-pass-37-build-outer-root-1/outer-observation.json).

The actual approval and one activation, 372d24/session11533 to 14d0870, installed all four exact native outputs, self PID62496. The [activation record](../../../build/evidence/native-pass-37/activation.json) is e08dcadfceae2f1ae55ade9f4aea288e6c11b016fc839c70155d982083ca8a0c. Validation's [installed audit](../../../build/evidence/native-pass-37-installed-audit-validation-1/result.json), ca33ba/self PID16884, is clear with 4,818 current inputs (result c2bd296bc0d9ac8c658818fcf68de14cb5d9a24c5c7f6c057bea2a1bba5668aa; seal 505348205e97bb17449263d6a48ab809fc18b5484a68a1ed6d0abab453346b11).

All three genuine RTX4090/Vulkan retirement attempts remain retained failures in their first case; both LINK-refusal cases passed in each attempt. The first exposed missing dtype/shape fields in Fixture3's blob. The second exposed the pending-count mismatch after Source5 ignored the CLEAR snapshot. Qualified Source6/Fixture5 with RawGraph4 corrects the wire fields and pending count while preserving the single draw, single dispatch, two submitted rows and full quality. Root and independent source gates admit Source31/Fixture6 and 325 current inputs; the actual third frozen context and its independent review also preserve all declared inputs and archives. These source/transport corrections do not qualify rendering.

The [third actual GPU attempt](../../../build/evidence/native-pass-37-retirement-native-attempt-3/result.json), 27d949/session34220 to 9a12b9, closed with typed exit 1, self PID14568 and child20492. LINK and the corrected pending checks succeeded; actual presentation failed with an invalid DawnRenderPipeline after NVIDIA NVVM compilation failed (code 3), identifying failed SPIR-V shader 0x2cf323fcd2401a75. This is the current pipeline integration blocker under read-only Shader triage. Its whole44 result is 7740898511a1e4806dc7bbdcf92a955dec5bb088d5e11c12c657df2264f7a3b2; seal 742ff6cebf40651d6125ed74fe2be505d8d01648a678c69b47b40a3c16e49aa4. The [FIRST original outer](../../../build/evidence/native-pass-37-retirement-native-outer-root-3/outer-observation.json) retains the actual tool returns and argv (f936d11f67b2ea8ce4a37b81feb23b126e80c8d506cdc32abf852c92b54a8eb7; seal 4caa007c913c18714413195d15ad16c3b8dd6db650bafc782fe43a0c26cb9365). Installed Native4 identities remained unchanged through all three GPU jobs.

Step7 remains open: the complete three-case rendering, warm reuse, loss/recovery and retirement behavior is not qualified. Broader scientific/smooth behavior, hosts, platforms, package and all 66 performance gates remain open. The current integration batch has reached real GPU validation, with the concrete shader failure still to resolve. Preserve every failed receipt. Both automatic cleanup rejections and zero deleted files remain recorded; no reclaimed-space claim is made. Cybersecurity work remains excluded.

Packet-count clarification: the Source6/Fixture5 source gate covers 31 source files and six fixture files, with 325 current named inputs.


### 2026-10-13 native38 admitted; pipeline creation remains blocked

runtime.cpp now captures Internal/OOM/Validation creation errors for graphics, compute and consumer-module paths, with explicit scopes/labels and opt-in input/backend-disassembly dumps. Shader literals and test assertions are unchanged.

Native38/Source24 built all 24 targets; the exact 26 CTests passed in 3.83s. The [independent build review](../../../build/evidence/native-pass-38-build-review-shaders-1/result.json) and [installed audit](../../../build/evidence/native-pass-38-installed-audit-validation-1/result.json) passed, binding the matching four installed outputs. Failed metadata freeze1 (missing current audit seal) remains retained; corrected freeze2 passed.

The [genuine RTX4090/Vulkan attempt](../../../build/evidence/native-pass-38-retirement-native-attempt-1/result.json) still records one failed case and two passed cases. Named generated line raster93361... fails at creation with Internal/VK_ERROR_UNKNOWN; presentation was not reached. Input and backend diagnostics are sealed in the [dump manifest](../../../build/evidence/native-pass-38-shader-diagnostics-1/manifest.json). Preserve this failure and its original observations.

Next safe action is full-stage pipeline-creation isolation diagnostics, followed by the unchanged 31-variable/raster/warm/loss/retirement acceptance. Step7 and full renderer acceptance remain open; this is no full Step2 or release qualification. All broader 13 requirements remain unchanged. Cybersecurity work remains excluded. The last cleanup retry was blocked; zero deletions remain recorded.


### 2026-10-13 creation controls isolate both generated stages

Root work1 controls fe2ecf/self PID41004 on RTX4090/595.79: baseline passed; full VS/simple FS, simple VS/full FS and full pair failed. Both full stages independently fail. Reviewed work2 was CPU-built. Reconvergence-OFF controls 2a5253/self PID15796 exited0, with the actual toggle absent, and repeated that pattern ([receipt](../../../build/evidence/native-pass-38-pipeline-reconvergence-off-attempt-1/result.json)). Maximal reconvergence does not resolve the failure. No submissions, full-fixture acceptance or production toggle change occurred.

Next investigation targets the shared generated-stage/backend path. Step7 and all broader 13 requirements remain open. The user's renewed cleanup request reached Root's literal native PowerShell delete, which was blocked before process creation ("blocked by policy"); zero files were deleted and the existing 1.72MiB cache remains retained. Cybersecurity work remains excluded.


### 2026-10-13 direct Vulkan and word-array controls retain failure

Root direct Vulkan ed4dcc/self PID43176 used exact original SPVs and a new minimal device on RTX4090/595.79: all four validations/modules passed; simple graphics passed, each full stage and the full pair failed with VK-13 ([receipt](../../../build/evidence/native-pass-38-direct-vulkan-attempt-1/result.json)). Original returns are retained. The different device chain prevents a sole-Tint-cause claim.

Root word-array 41144b/self PID52492 repeated that pattern ([receipt](../../../build/evidence/native-pass-38-word-array-pipeline-attempt-1/result.json)); all four SPVs validated. Full31 values, layout, guards and math remain, original regeneration is byte-exact, and no submit occurred. Word representation did not fix creation.

A source-only numeric-inline three-pass diagnostic is active. No production/fixture patch, pixels, warm reuse, loss or retirement is qualified. Step7 and all broader 13 requirements remain open. Cybersecurity work remains excluded.


### 2026-10-13 numeric inlining did not fix creation

Original SPVs changed only through MergeReturn, InlineExhaustive and EliminateDeadFunctions. Validation, capabilities, interfaces, globals, full32-member layout and512-byte stride remain; CPU/source pins are independently clear with zero helper calls. Root 5b2b15/self PID56452 exited0 on RTX4090/595.79: baseline passed, both full stages failed and full pair failed; no submit ([receipt](../../../build/evidence/native-pass-38-numeric-inline-pipeline-attempt-1/result.json)). Inlining did not fix creation; production is unchanged.

Next is CPU/source-only equivalence for three finite-classification helpers over all IEEE bits, with no other changes; GPU is unrun. Ordinary17 needs final-epoch cancellation2 first; the old34 adapter cannot run38 unchanged or bypass that gate. All31 fixture assertions, Step7 and broader13 requirements remain open. Cybersecurity work is excluded.


### 2026-10-13 finite equality did not fix creation

FiniteEq3 has exact32-bit helper equivalence, byte-exact CPU baseline, four validated SPVs and guarded inputs; independent afc204 is clear. Root007849/self57952 on RTX4090/595.79 retained PASS/FAIL/FAIL/FAIL, no submit ([receipt](../../../build/evidence/native-pass-38-finite-equality-pipeline-attempt-1/result.json)). No canonical contract/cache identity changed; old-ops admission is retained.

Next read-only helper micro-creation proposal keeps the common prefix and changes only main. It localizes diagnosis; original31 payload/pixel assertions, Step7 and all13 requirements remain open.

### 2026-10-13 helper creation probes localize parameter validation

The fixed CPU matrix regenerated both originals exactly and validated20 stages. Independent source review and the matching driver build passed. Root GPU7f9494/PID19756 on RTX4090/595.79 passed WGSL/UBO baselines, finite1/2/4, plane, clip and window; parameters, segment and unchanged originalVS failed Internal/VK_ERROR_UNKNOWN. All witnesses passed; no commands submitted. The [sealed result](../../../build/evidence/native-pass-38-helper-micro-pipeline-attempt-1/result.json) localizes a dependency tree, not renderer acceptance. Next source-only probes separate row-zero loading, array length, unsigned division and modulo, retaining both failure anchors. Original31-variable pixels, warm/loss/retirement, Step7 and all13 requirements remain open. Work excludes cybersecurity.


### 2026-10-13 parameter operation creation controls

Root fc619e/PID26660 (RTX4090/595.79) passed WGSL/UBO witnesses and row0-clip-load, rows-length, unsigned-div and unsigned-mod. Parameters/original-full still failed Internal/VK_ERROR_UNKNOWN. All interpretation witnesses passed; no queue use. [Result](../../../build/evidence/native-pass-38-parameter-ops-micro-pipeline-attempt-1/result.json) SHA aa721a5fe44bd37b796e775f7668ebb6cb8c534c1f70f64a30bf302f58e079e5; seal 802cf4ad8f65a68b9b43f3f9f9237a547bb0ec8c0bb8a1684773181d96aeddaa (writer e6f7e5/PID3480).

Next source-reviewed controls isolate ordered early-return parameter guards. No production change/renderer acceptance; original31 pixels, warm/loss/retirement, Step7/all13 remain open. Cybersecurity excluded.


### 2026-10-13 ordered parameter guards did not fix creation

Root e915c4/PID42336 on RTX4090/595.79 retained PASS/FAIL/FAIL/FAIL, no submit. Independent reviews cleared the full mains, 31-field layout/512-byte stride and guard semantics. [Result](../../../build/evidence/native-pass-38-ordered-guard-pipeline-attempt-1/result.json) SHA 592f8723e76caa9651f730f649599bb7739586669d7b59da1349ead94fca00a5; seal e3ed29ef14fad9fb8e08e2eb727a2034572c252a0df5613fb48953d85886285b (writer 620731/PID42440).

No production adoption or rendering acceptance. Next bounded source-only controls localize original parameter predicate groups under review. Original rendering criteria, Step7/all13 remain open. Cybersecurity excluded.


### 2026-10-13 parameter groups isolate G2 prerequisites

Root GPU/PID10948 on RTX4090/595.79 passed WGSL/UBO baselines, header-topology and finite-raster; overflow-ranges, parameters and originalVS failed. All witnesses passed; no submit. [Result](../../../build/evidence/native-pass-38-parameter-groups-micro-pipeline-attempt-1/result.json) SHA 2d4aae53813d64b1135d1db8bdbf2feca78393b9b31154bffc1df7b35227a05b; seal b901119ec4d783869523dab6d030a43923982c996557c6304eae701cf8e13726 (writer PID47712).

This localizes G2 plus shared prerequisites only. Next source-only controls separate reciprocal overflow from total slice, under review. No production change/rendering acceptance; Step7/all13 remain open. Cybersecurity excluded.


### 2026-10-13 reciprocal overflow subtree remains the failing split

Root GPU/PID53564 on RTX4090/595.79 passed WGSL/UBO baselines and total-slice; reciprocal-overflow and all three anchors failed Internal/VK_ERROR_UNKNOWN. All witnesses passed; no submit. [Result](../../../build/evidence/native-pass-38-overflow-split-micro-pipeline-attempt-1/result.json) SHA 7bb9196640a62b3ec20b70259676f2544bfbf03cb4fd524c53c9e84a3ae4abc2; seal 32dfd22b07917e8a76f5d5b7aaf62c9abf68a103374ef11d652c441127f6158f (writer 6dbe70).

Next source-only full-pair candidate removes only the MAX/E guard under the bounded-product proof. Candidate GPU test is unrun; no production adoption or acceptance. Original31 pixels, warm/loss/retirement, Step7/all13 remain open. Cybersecurity excluded.


### 2026-10-13: bounded product creation control

Root GPU 54820d (PID 8028), RTX4090/595.79: all four creation pairs PASS, no submit. [Retained result](../../../../build/evidence/native-pass-38-bounded-product-pipeline-attempt-1/result.json) and seal retain the actual run. Removing only the unreachable MAX/E guard preserves the topology bound floor(Y/X)*E <= Y <= UINT32_MAX. Canonical shader/policy-v2 and arithmetic/CFG/cache contract updates are source changes awaiting Native39 build and full renderer acceptance. No production rendering acceptance is claimed; Step7, all 13 requirements and original pixel/warm/loss/retirement criteria remain open. Cybersecurity work remains excluded.


### 2026-10-13: contract compile correction and fresh Native40

Native39 full build failed on the new test's out-of-scope Mode enum; failed build/frozen records remain immutable. The sole correction adds local using vispy::lines::Mode. [Standalone CPU preflight](../../../../build/native40-contract-compile-work-1/result.json) configured, built and passed 26,846 checks with source/native4 guards unchanged. Root e15134 published fresh Native40 ownership; freeze cb9b30/session20371 is active at this checkpoint. Full native build, installation and unchanged renderer acceptance remain pending. Installed native4 is still Native38. Step7 and all 13 requirements remain open; cybersecurity work stays excluded.


### 2026-10-13: Native40 full CPU build passed

Root freeze cb9b30 -> f43ac1 passed. Full build 49aefa/session42661 -> 024117 exited 0: all 24 targets built and all 26 CTests passed in 3.83s. [Original build outer](../../../../build/evidence/native40-build-outer-root-1/outer-observation.json) retains the actual closure. Independent build handoff and Source3 activation metadata are under review; no installation is claimed and native4 remains Native38. Failed Native39 records remain retained and unqualified. Full renderer/pixel/warm/loss/retirement acceptance, Step7 and all 13 requirements remain open. Cybersecurity work remains excluded.

Outer link correction: [actual packet](../../../../build/native40-build-outer-root-1/outer-observation.json).


### 2026-10-13: Native40 installed; renderer gate pending

Root activation 86d98d -> d5f6a4 exited 0 (PID 52496), installing the reviewed Native40 artifacts. Independent Source3 build review2 is CLEAR with the exact actual handoff; installed-audit review is still in progress. The unchanged Source6/Fixture5 retirement route will receive a fresh Native40 authority only after that audit result and seal are available. No fresh renderer fixture has run at this checkpoint. Full pixel/warm/loss/retirement acceptance, Step7 and all 13 requirements remain open; successful installation alone does not qualify them. Failed Native39 and prior GPU attempts remain retained. Cybersecurity work remains excluded.


### 2026-10-13: full Native40 fixture reached presentation

[Retained full fixture](../../../../build/evidence/native-pass-40-retirement-native-attempt-1/result.json): 1 failed, 2 passed; original child closed and GPU released. Pipeline creation, draw/dispatch/row counters, retirement and readback were reached, but the first frame was opaque black instead of the unchanged 72 green reference pixels. Full renderer acceptance remains unqualified. Read-only parameter reconstruction matches the expected 80B render UBO, 16B compute UBO and 1024B endpoint buffer; static coverage/math checks found no rejection. Actual endpoint bytes remain unknown; a separate capture diagnostic is under review. Step7 and all 13 requirements remain open; cybersecurity work stays excluded.


### 2026-10-13: endpoint capture isolates the remaining blank frame

Root capture c3b344 (PID 39432) confirmed both 512B endpoint rows: all 31 original fields match, and padded-row/canary checks pass. The presented frame remains blank, so correct compute transport does not qualify rendering. A separate consumer-stage render/readback probe is proposed to distinguish expansion and fragment behavior using the unchanged data and state. Full fixture pixel/warm/loss/retirement acceptance remains pending; Step7 and all 13 requirements stay open. No production or fixture criteria are relaxed. Cybersecurity work remains excluded.


### 2026-10-13: consumer Y-conversion diagnostic passed

Root GPU dfedbc (PID 48812), same RTX4090: all four expected image controls PASS; the full generated pair matches all 72 unchanged reference pixels exactly. Full-VS bounds are now [2,15,30,19]. Root sealed result de9d8474dc405e63d293f01688da70180e4865cb0347a464e17705f4f2f04e16. Removing the duplicate Y conversion and introducing coordinate policy/cache-v3 passed the standalone CPU contract's 26,868 checks. This qualifies the bounded diagnostic only. Full Native41 build and the original renderer warm/loss/retirement fixture remain pending; Step7 and all 13 requirements stay open. No fixture criteria changed. Cybersecurity work remains excluded.

2026-10-13 checkpoint: Native41 built all 24 targets; all 26 CTests passed in 3.57s. Build admission, installed activation and independent installed audit are clear. The original full GPU fixture remains failed (1 fail/2 pass): 72 green pixels were the exact vertical reverse of the unchanged reference. Retained failed-outcome review: 669800e24682b5a73ee6b76cca300d0b873cb6d41a85f98a51555ca36b2b6652. The presentation UV flip plus consumer-specific viewport/scissor mirrors exposed a coordinate mismatch. Canonical policy v4 now matches ordinary GL-window rendering: vertex -Y, direct fragment coordinates, and ordinary viewport/scissor Y; presentation/readback stay unchanged. Contract CPU checks and complete Native42 qualification remain pending; no renderer acceptance is claimed. Cancellation SOURCE2 CPU14 passed 191 subtests and was independently admitted (f976e9024d6c9c1e903e5aadf48a583fc0b815bbb7397256407b82f46413d6cf).

2026-10-13 checkpoint: Native42 full build passed all 24 targets and 26 CTests in 3.80s; build admission, installed activation and independent installed audit are clear. The original three-case GPU fixture remains 1 fail/2 pass: default, warm and after-ordinary-refusal images match the exact reference; forced loss then leaves device_info.ok false. Failed outcome retained: eb461fceae24980b48ba49c63782124348dfa6dbb2cdeaed9178a36975d33b62 / seal647cdf08b386e5030dba9a718be75813faf43e0819ea294811f18f59a49ee5d3. Native43 removes only ensure_device's lost early return so its existing initializer can recover. The updated legacy GPU loss test and complete Native43 qualification still require execution. Cancellation42 CPU14/191 was independently admitted; its GPU gate remains held. Renderer acceptance is not claimed.

2026-10-13 checkpoint: Native43 built all 24 targets and passed all 26 CTests in 3.81s; build review, installation and independent installed audit are clear. The only runtime change removes ensure_device's lost early return; two native Python harness tests now match explicit device-info recovery. Root's original three-case GPU fixture passed all three in 12.46s (cf13c3 -> 75deba), including exact default/warm/recovered pixels, loss-generation recovery and retirement checks. Complete independent Source7 outcome admission is still pending, so renderer acceptance is not yet claimed. Cancellation43 source and CPU14/191 controls are clear; cancellation GPU execution remains held. The broader 13 requirements and smooth-line scope remain open.

Follow-up: Native43 Source7 outcome admitted, result927fb550941e6718eb8fe6743067ccb76a2bca2cfc221e83a0dbc3125893dcf3, sealc1cd3fc982ca52bd3734d9e9100a5b2f36045f6d343bc34cbc40ee919760c433; broader13/smooth remain open.

2026-10-13 checkpoint: Native43 cancellation GPU passed both cases (79 deselected) in 5.55s and independent outcome review is CLEAR (c5a8dfb1e52b77527cb30cf13c4bd82f8352577e0811497240792a134462b0a4). Ordinary-input GPU regression retained 14 pass/3 fail: all 219 image pairs match, but the three line topologies require native Bresenham routing and observed a zero counter. Native44 restores native routing for eligible unsmoothed width-one interfaces and keeps generated routing for other admitted lines. Its focused CPU contract passes 224 checks, including actual compiled fragment builtin artifacts. Independent source review and complete Native44 build/GPU qualification remain pending. Affected109 and broader13/smooth scope remain open. Historical failed attempts remain retained; cybersecurity work remains excluded.

Native44 full build checkpoint: original Root a1e9c3/session21545 ->45a23a exited0; all24 targets compiled and all26 CTests passed in4.17s. Source ownership b5e17e52/frozen e0a49588 bind the four authorized files and unchanged Native43 parent artifacts. Independent Source3 build review, installation/audit and fresh GPU regression gates remain pending. Cancellation44 CPU14/191 passed and independent outcome is CLEAR (6ede3d2bf1bb38901446f820eee553dcb460992397667e7b5564a2eb8d91dd20); this qualifies binding controls only. Ordinary17/affected109/device2/six-case line parity and broader13/smooth remain open.

Native44 handoff follow-up: passing24/26 native build remains intact. Source5 admits only the exact independently reviewed CMake70be transition while retaining seven historical acknowledgements; pure4 positive/41 refusal checks and source admission are clear. Build-review2 then refused the original final tool output because Root captured1208 tokens with a1000-token limit, leaving a truncated JSON summary. Original typed exit0/capture/proof files remain unchanged. A separate derived summary from recorded preflight/status matches both visible2000-character ends exactly; its middle is explicitly not recovered stdout. A narrowly fixed Source6 metadata join is pending review; no install/GPU44 qualification is claimed. Ordinary44 SOURCE4 is clear after the epoch and full-line fingerprint corrections;17/109/device2 selections are preserved.

Native44 installed checkpoint: Source6 explicit capture handling passed3 positive/29 refusal controls and independent source review; complete buildreview3 CLEAR a34c7605/ce807fb3 admits24targets26Ct. Fresh guard qualification retains original7methods108checks and separate7positive70refusal metadata checks, independently admitted. Root checked activation5effcc/session78600 ->7eb29f exited0/PID16628, receipt47a324d9; allfour installed hashes match. Independent Source6 installed audit077ced ->8e4b5e exited0/PID44016 CLEAR56a33495/77055d3c. Fresh Source7 renderer/cancellation/ordinary17/affected109/device2 GPU qualification remains pending. Broader13/smooth remain open; no GPU44 acceptance claimed.

Native44 renderer checkpoint: Root original unchanged Fixture6/Source7 GPU run e447b9/session49919 ->e96d1d exited0, driver33308/child28328, allthree XMLcases PASS17.851s and GPUreleased. Exact current native module8978ac97 was used. Complete unchanged Source7 independent outcome b7606c ->bdc35f exited0/PID57592 is CLEAR cb17d4de/15e9fd95 for originalpixels/warm/loss/capture/retirement/contextualLINKDRAW only. Fresh matching-epoch Cancellation2/ordinary17/affected109/device2 remain pending. Wider six-case/smooth/full13 requirements remain open.

Native44 Cancellation2 checkpoint: current44 authority6ecf370b and frozen inputs9bbbffab were independently admitted by new binding-only reader67f82a16/653d90b4. Root original GPU attempt135365/session41771 ->e1e5fc exited0, child56496 closed0 and GPUreleased; both cases PASS9.08s,79 CPU cases deselected. Terminal0f501b78 retained. Complete independent outcome admission is pending; ordinary17/affected109/device2 and broader13/smooth remain open.

Native44 ordinary-input checkpoint: Cancellation2 complete independent outcome10117915/bd7be58 is CLEAR on retained realtwoGPUcases. Exact11-key current batch spec494f616b joins same authority6ecf and currentSource4. Root ordinary17 preflight passed; originalGPUrunefd583/session65099 ->16d4a5 exited0, all17tests PASS2.45s/fourCPUdeselections. This resolves allthree old Bresenham-routing assertions with unchanged image/reference criteria. Terminal40899ca0 retained; independent ordinary outcome still pending. Affected109preflight passed0f7e65 ->6df760 but its recipe retained an old43output label; no affectedGPUrun occurred, a fresh metadata-only destination correction is pending. Device2source review/run and broader13/smooth/six-case scopes remain open.

Native44 final-regression checkpoint: correctedSource5 eleven-keyspec2b0862df preflight109 passed; actualGPU886ce5/session83318 ->358c02 exited1,108passed/1failed43.78s. Solefailure is benchmark test_cold_shader_stage_time_is_not_replayed_by_cache_or_device_recovery legacy assertnotdevice_info.ok at455; explicit recovery is the reviewed43 behavior. Failed result54f048bb/outer3655eec3 retained. Candidate d410a35e frombaselinef64aa383 changes only that test function to verify recovery/loss+1/generation/repeatedreuse, preservesall compiler/cache timing/recreation assertions. Candidate whole6 retained/canonicalbaseline restored until review. Independentordinary17outcome305be910/b42256c clear219pairs/nativeBresenham1/2/2/no endpointdispatch. Device2actual77f2c2 ->f95cf4 exited0/PID13988/child4128;2PASS0.50s hardware4090/gen1->2/loss1, independentoutcomepending. Freshharnesscandidateadmission and109rerun remainpending; native44 unchanged. Broader13/smooth/sixcase scopes open.

Benchmark harness transition checkpoint: Device2 complete independent outcome3d108500/a38965d3 CLEAR; ordinary17 completeindependent305be910/b42256c clear. Benchmarkcandidate sourcebc7cde73/4de9916e CLEAR on exact14functionIDs/alloriginalassertions exceptobsolete sticky-loss expectation. Root835b95 applied exactd410a35e candidate, applicationfec84905/18c14a3a; oldNative44frozenf64aa and firstfailed109retainedunchanged. SOURCE6harnesstransition hold20/sealfecb76d9 binds exactcandidate/source/application and protects oldfrozen/livechangedharnessseparately, keeps109IDs/predicates/native44roles unchanged, newoutput44-gpu-2. Independentsourcegate andactual109rerun remainpending. No broadercompletionclaim.

Native44 affected109 rerun checkpoint: SOURCE7 exactone-leaf authority projection admits preservedf64 archive/live d410 withoriginalauthority6ecf/nativebuildroles unchanged; actualmetadata2positive/30refusals/source7gate7ccd949a/bf9a3966 clear. Fresh11specba7f821a preflight56b2b5 ->690966 exited0/109cases. RootfinalGPU453f14/session81775 ->e6b169 exited0, all109PASS40.17s/42existingdependencywarnings, admissionerrors[]. Result5f2d883c/outer9fd93d0a retained; independentcompleteoutcomereview pending. Earlier108/1failure andmetadatafailures remainimmutable. Originalrenderer3/Cancellation2/ordinary17/Device2 independentadmissions remainclear. Native44code fix isverified byoriginalsuite; wider13/smooth/sixcase/platform/performance/release scopes remainopen.

### 2026-10-13: Native44 implementation batch validated

The final affected regression run passed all 109 tests in 40.17s. Independent retained-outcome review is CLEAR_WITH_SCOPE: result `b79cfa7762684115fb4429d4987ef183bc7182a41b437dd156e3b2f8fdce2767`, seal `9660aec2d0095707d49da7eba38f588b9a0d168bc60bcefdbec39d2939b9c4dc`. It verified the original test IDs, selectors and order, 14,295 protected inputs, the archive, installed native binaries, hardware and package origins, actual child closure, 331 complete numeric arrays and 80 exact expected image pairs. The reviewer did not rerun the GPU producer. All 42 dependency warnings remain recorded.

This closes the current Native44 batch: 24 native targets built; all 26 CTests passed; original renderer 3, cancellation 2, ordinary-input 17, explicit device recovery 2 and affected regression 109 cases passed with independent outcome reviews. Eligible unsmoothed width-one lines use native topology again; generated routing handles other admitted line cases. The benchmark recovery assertion now checks explicit recovery while preserving its original compiler, cache and timing assertions. Failed attempts and frozen baseline inputs remain retained.

The wider completion plan remains open, including smooth lines, expanded parity cases, cache stress, other platforms, performance and release validation. Cybersecurity issues remain excluded. Temporary cleanup must preserve evidence and respect the earlier deletion rejection; this checkpoint does not claim any new deletions.

Next bounded graphics gate: qualify the six existing aliased wide-line cases against their frozen references before changing more renderer code. Use `horizontal_aliased`, `vertical_aliased` and `diagonal_aliased` in `tests/parity/test_wide_line_parity.py`, plus `private_state_aliased`, `clipped_noperspective_aliased` and `clipped_perspective_aliased` in `tests/parity/test_wide_line_semantics.py`. These results remain pending. Patch only a demonstrated failure, then run checks appropriate to that change. Smooth/MSAA policies remain separate open work.

Cache scope clarification: Native44's CTests cover synthetic shared-policy FIFO and generation behavior, but the runtime currently implements only the aliased coverage policy. Genuine second-policy A-to-B-to-A and FIFO128 hardware acceptance depends on an implemented SmoothReference policy. Existing endpoint lifetime cases for DATA/uniform A-to-B-to-A, warm zero costs and device loss can qualify endpoint output/ownership separately; they cannot substitute for a second raster policy.

### 2026-10-14: six aliased line cases expose two raster defects

The contained current-Native44 runner passed source review and actual preflight. Root run `ea70b0` closed with exit 1, driver PID 51856, launched child 59272; the original six tests produced 3 passed / 3 failed in 2.92s. Failed result `dcdc0f969aceb612f13fe0413b8e38da769791dcbb12962abd1c2773d4615d81` and seal `7ae156d0a5dae97d1b277cb6075c383ce56c048f0beda79f96be762014c84e33` are retained in `build/evidence/line-aliased-six-native44-attempt-1`. Horizontal, vertical and private-state cases match their complete references exactly. The diagonal differs at four boundary pixels; both clipped cases omit only the final column's three pixels. Every surviving clipped pixel matches the original perspective/noperspective reference exactly. All six draw/dispatch/row deltas and retirement checks passed, and six explicit shutdown receipts have zero queues and line-pool slots. This is a failed parity gate, not six-case acceptance. No reference or tolerance changed; renderer diagnosis and repair remain in progress.

Coverage repair checkpoint: the three changed files preserve endpoint projection residuals through explicit affine diamond-plane FMA operations, distinguish synthetic clipped endpoints from original LAST, and revise the pre-generation coverage/cache identity. Before-files are saved under `build/line-aliased-coverage-repair-work-1/before`. Root focused CPU run `f7dee8` / session 21431 closed at `313b53` with exit 0, driver PID 13692: configure, five-source build and actual contract executable all exited 0. The generated compiler contract passed 28,356 checks, including independent diagonal/terminal counterfactuals and actual nested-FMA SPIR-V controls. Result SHA256 `2fee692ea7346ce15a0d56ba0cfe4578f84cfb7764585b691b150caae3eec74b`; named inputs remained unchanged. This qualifies the focused CPU contract only. Native45 full build, activation/audit and matching six-case hardware rerun remain pending; Native44 remains installed.

Native45 freeze checkpoint: independent source/CPU review `e420dd94` and ownership review are clear. Root published manifest `08568b67408857456c14dde8c54fd315bcfd85356a0baf5aee5deb592c442439` from the executed helper `eb97cba5`; a later unexecuted helper edit was preserved separately and the exact executed bytes restored. The published output is unchanged. Root canonical freeze `1fc9ce` / session 43241 closed at `19c390` with exit 0. Frozen inputs `d12caf020d6cd2c720508adf80656f168d9090e071f4bd895c47dab20e211f41` bind source tree `bb2ba3cc5d01de2db1f25b62b96c2dd43b06777288e991cd0d2f0125a9f7855f` and harness tree `a69a8090a4ba207f85b825bcaf12f6768edd7f7d9e7e3db7b7982a5ae68ea081`. The full canonical build started as `6f4a21` / session 93447 and remains active at this checkpoint. Native44 is still installed; no Native45 hardware acceptance is claimed.

Native45 full-build checkpoint: the original `6f4a21` / session 93447 closed at `55c64e` with typed exit 0 and a complete untruncated summary. All 24 native targets built and all 26 CTests passed in 4.62s; final source, harness, SDK, dependency and protected-binary checks passed. Root's retained original outer SHA256 is `1c26910a1a997cf55bac28e4240dafd47bd09e8ce379c975220f5876ce697b61`, seal `dff996a00cac4e7d0a4c99a54d513c50338fd53b81e2a0b10ebd5f7ffb7ac1e4`. The fresh activation adapter's independent source admission is clear (`e696c9fb` / `84be7f03`); its imported transaction and normal complete-build checks remain unchanged. Independent build admission, activation/audit and the original six-case hardware rerun remain pending. Native44 stays installed.

Native45 installed checkpoint: actual independent build review `675b65` / session 48259 closed at `23046e` with exit 0, admitting 24 targets, 26 CTests and all source/harness/archive/native identities. Review `7bcc526e` / `ba468284`, handoff `2fe151f1`, retain the actual normal build summary. Root preparation `c97928` / 41588 closed at `52855c` with exit 0; approval `6af516d6`. Root activation `a110d6` / 41356 closed at `615f3d` with exit 0, driver PID 56860; activation `910f34273abb590c974e20b1cc5ece5fb0bd8d3fea90c2566e3bb87e30698fb6`. The four installed hashes match the reviewed Native45 artifacts. Root activation outer `b2148e04` / `286a959b` preserves the original transaction. Independent installed audit and the six-case hardware rerun remain pending. No Native45 GPU result is claimed.

Native45 six-case hardware checkpoint: actual installed audit `5416ee` exited 0 and is clear (`8eac4115` / `346857f8`) on all four committed copies, backups, staging and approved inputs. The new seven-file six-case runner binds current45/31 directly and marks Native44 warm/loss/cancellation admissions historical only; source review `7eabd2c4` / `8acd34e6` is clear. Root preflight `96d756` exited 0, then GPU run `8d76d7` exited 0, driver PID 59756, launched child 45520 and actual Python PID 48984 through one validated Windows redirector edge. All six unchanged canonical tests passed in 3.49s. Result `84d790531849965676fe1a72d17aaf9c2c547e2bd1a1d06d94f7981c8ed1681f` / seal `7e33e510311460798a12431ab1f66ce8a31d121aeb5deb621ec286afa21a02fb` preserve full exact images and actual retirement/shutdown receipts. The original failed Native44 result remains unchanged. Independent retained-outcome review and affected regression qualification are pending; per-case warm/loss, smooth and full release scope remain open.

Six-case outcome admitted: actual independent review `19bb7b` exited 0, result `6c4fb30b715ad9711152fb872e2f3757b6f9c791f2b87b5f3eb10456d9011c5b` / seal `e29f5e898314b12b7cb63f034adae017c312fc4fed1e032795868274b609e71a`. It verified current Native45 inputs and binaries, actual hardware/module/Python/child closure, all six complete 768-pixel RGBA arrays, per-case draw/dispatch/row deltas, six retirements and six explicit shutdown receipts. The diagonal matches all 60 covered pixels; each clipped case matches all 96 covered pixels, including the restored final column. This closes the six-case aliased raster gate only. Matching ordinary-input and affected-regression runs are being prepared; smooth, per-case warm/loss and wider release gates remain open.

Native45 affected regression checkpoint: the contained seven-file regression runner uses unchanged canonical selectors, test bodies and references, full frozen harness identity, isolated output paths and current45 hardware/Python/cleanup gates. Source admission `4c263c54` / `65ada5ed` is clear. Root ordinary17 preflight `cf7f27` passed; GPU `33cad7` / session 10426 closed at `4b6e6b` with exit 0, 17 passed / 4 original CPU deselections in 3.86s. Result `cd4bdc33` / `7340707a` retains launched child 51748 and actual Python 53752. Root affected109 preflight `742a11` passed; GPU `dec24a` / session 38703 closed at `71ba49` with exit 0, all 109 passed in 37.02s with 42 retained dependency warnings. Result `a1020b16` / `352ed58f` retains launched child 25468 and actual Python 55860. Both actual children closed with native cleanup receipts and unchanged named inputs/binaries. Root tool observations are preserved in the repair work directory. Independent retained-outcome review remains pending; wider smooth/platform/performance/release requirements remain open.

### 2026-10-14: Native45 coverage repair batch validated

The combined independent retained-outcome review `0a97c1` exited 0, result `10d3440c95ddaa3d43d36f6723de4975d6361a783dfa802081a527911d62c1e7` / seal `227093c872abe9f8eaa8bfc9f50ad5eaf2f87279ba1e83e596d4e8c87d8b35ff`. It checked 4,565 bindings, both complete jobs, 3,678 unchanged inputs per job, current native binaries, exact XML selections, real hardware/module/Python edges and API cleanup. All 219 ordinary saved image pairs and 80 affected saved pairs match exactly; ordinary resident zero-cost phases, six recovery generation advances and native-line counters satisfy their original predicates. Scientific and timing assertions retain their original source and actual passing XML; the reviewer did not reexecute them or claim universal byte equality for masked/toleranced cases. All 42 dependency warnings remain recorded.

This closes the current repair batch: three canonical files changed, before-files preserved, focused generated contract 28,356 checks passed, full build 24 targets / 26 CTests passed, installed audit clear, six aliased GPU cases and 17 ordinary / 109 affected cases passed with independent outcome reviews. The six-case references and all existing tolerances/assertions stayed unchanged. New work and build assets remain in named directories; no new deletion is claimed. Smooth coverage, expanded parity, genuine second-policy hardware cache tests, additional hosts/platforms, performance and release validation remain open. Cybersecurity issues remain excluded.

### 2026-10-16: ordinary field partitioning passes focused CPU checks

`cpp/runtime_point.hpp` now finds an exact minimal field partition under stride and joint buffer-slot grants, preserving original field locations and separate vertex/instance step modes. `cpp/runtime.cpp` uses that layout for ordinary artifact creation and retains all physical streams of one category under a composite conversion owner. Single-stream keys and payloads remain compatible. A failed category conversion leaves its previous complete owner available; pending snapshots retain their physical children. Before-files and all new work are contained in `build/input-field-partition-work-1`.

Root's original runtime-object/contract build session 7374 closed at `4cbc8a` with exit 0. The final test-only literal negative-zero correction was rebuilt at `50a704`, exit 0, and the contract executable ran at `dab878`, exit 0. [Focused CPU outcome](../../../build/input-field-partition-work-1/cpu-outcome.json) binds three current source hashes and four logs. The tests include 1,680 independent reduced-limit partition cases, a first-fit counterexample, exact indexed/affine/divisor data, NaN/integer/negative-zero words, category reuse, failed publication, simulated loss and child ownership. Existing compiler warnings remain recorded. Source review and a fresh Native46 full build/activation/device qualification are in progress; Native45 stays installed.

The actual RTX4090 grants do not force thirty admitted attributes across the stride boundary, so reduced-limit CPU coverage does not establish hardware acceptance of a split layout. Allocation-size ordered batching and the point-sprite packed path remain separate open requirements. The new smooth side/cap calibration study in `build/smooth-side-cap-hypothesis-work-1` matches all 6,385 interior calibration pixels but still differs at twelve complete-frame pixels. It is an unqualified hypothesis; production SmoothReference, frozen holdouts, references and tolerances remain unchanged. Full original release scope remains open; cybersecurity work is excluded.

Follow-up evidence remains separate: [smooth calibration study 2](../../../build/smooth-side-cap-hypothesis-work-2/calibration-result.json) derives a global side/cap composition but retains six full-frame endpoint mismatches in its primary float32 model; a nominal-coordinate control retains one mismatch. Neither result qualifies production smoothing. Nine future predictions were sealed before any new capture access. The [pinned upstream public-API probe](../../../build/typed-sampling-public-probe-work-1/result.json), actual `ad44c7` exit 0, confirms that `r32i`/`r32ui` construction and `isampler2D`/`usampler2D` assignment are refused in VisPy 0.17.0. A typed GLIR sampling fixture is being prepared; no shader-sampling parity or new public-API support is claimed.

Native46 freeze passed: Root's original `8515f4` / session 75250 closed at `7d4d1e`, exit 0. Ownership `f3bfb497eb3472b242dad5c47af2beac366c885303a48b2bb81c341a5c188b1f` and [frozen inputs](../../../build/evidence/native-pass-46/frozen-inputs.json) `4b0ff639154f63cd63f7e4c6f9ba8f8f4422151d515236ce6c664fd479be4d7a` bind source tree `7e611ba4ddd7ff4a165d570a505bb4203668c9937602285e482b25b39a70ad65` and harness tree `0d4d08b7ab1fdeb012e32ad1919a26b152a5a44738dc8e25f0e959dce52a2e54`. All 596 sources, 4,097 harness inputs, 45 ownership leaves, protected Native45 files and dependency-origin checks passed. The full build began as `a3b995` / session 21348 and is running; its 24 targets / 26 CTests, installation and device gates are not yet qualified. [Activation-adapter source review](../../../build/evidence/native46-activation-adapter-source-review-1/result.json) and [regression source review](../../../build/evidence/native46-regression-source-five-review-remaining-1/result.json) are clear at their source-only scopes. Native45 remains installed.

External driver change observed: the first typed-GLIR attempt stopped at its strict 595.79 identity gate, actual `d45aab` / session 24580 closed at `44875b` with exit 1, child exit 1 and successful canvas cleanup. [Failed attempt](../../../build/evidence/typed-sampling-glir-oracle-attempt-2/result.json) `777d5495f988bb6aae25a080d39af40132029c702156a17df6a9c5dfafbfc7f5` is retained with unchanged inputs and no admitted reference cases. A separate unchanged-Runner [OpenGL identity diagnostic](../../../build/typed-sampling-glir-identity-probe-1/result.json), actual `66b1a4` exit 0, reports NVIDIA RTX4090 / 4.6.0 NVIDIA 610.88. A separate hash-pinned historical-Native45 [Vulkan identity diagnostic](../../../build/native45-driver-identity-probe-61088-1/result.json), corrected source `probe2.py`, actual `6471c9` exit 0, reports discrete Vulkan / NVIDIA 610.88 and successful shutdown. Its first import-only failure is retained. These are identity observations, not raster qualification. Historical Native45 and smooth-calibration GPU results remain scoped to 595.79; fresh native/device acceptance must record 610.88. The existing regression predicates have no obsolete driver equality and remain unchanged. A new strict-610.88 typed-reference source derivative is being reviewed; original inputs, expected bytes and tolerances remain fixed.

Native46 complete-build checkpoint: original `a3b995` / session 21348 closed at `cc4f40` with typed exit 0 and the complete untruncated summary. All 24 targets built and all 26 CTests passed in 3.91s. Final source, harness, SDK, dependency and protected-native checks passed. [Root outer observation](../../../build/native46-build-outer-root-1/outer-observation.json) `2a9c9af450b58b3ca791e74a322c22e58418631f769f0b5d9cc955728aaed09a` / seal `65b94067cb39c82118a61d50396468f382680f8e465d5f132662b04a871dff0c` retains that actual process. Actual build-input author `4ce378` exited 0, spec `58895783c6838f2bb6a23ae4d0e554cceef9c3b33e206a0562c795625711b5d1`; independent full-build review is running before installation. Native45 remains installed.

Typed upstream texture-load checkpoint: [source3 independent review](../../../build/evidence/typed-sampling-glir-oracle-source-review-typed-3/result.json) binds the exact 610.88 identity correction and unchanged domains, shaders and expected bytes. Root reused the passing unchanged transport/provider preflight2; the actual source3 run repeated its complete source/provider/native checks before launching. Original `75b84d` / session 44565 closed at `304ebb`, exit 0, with child exit 0 and unchanged inputs. [Actual two-case outcome](../../../build/evidence/typed-sampling-glir-oracle-attempt-3/result.json) `2061abb8d23dc47aca84a840494d971936a5a5565f71ec5d391f323615952864` / seal `5423fbadd9f9835f4b848121759677f77200d50fc2f7561e4896834e44723b82` passes both complete 32x24 RGBA comparisons, preserving uint32/sint32 words above 2**24. Independent saved-outcome review is running. This is original GLIR `texelFetch` evidence; it does not qualify filtering, wrapping, a live sampler binding, public integer-Program support or candidate rendering.

Next integer-sampler implementation remains isolated in `build/typed-sampling-implementation-work-1` and `build/typed-sampling-runtime-work-1`. Actual `87892f` exited 0 with three passing shader CTests (new typed sampler, complete inherited normalization and artifact contracts). The first combined runtime-object build failed because the trial setup mixed canonical and candidate header trees; its full log is retained and a coherent source overlay is being prepared. No typed candidate source was applied to the canonical tree or installed. The separate forced-stride GPU-test candidate is also unbuilt and unqualified. Full-frame smooth arithmetic study3 still retains one calibration mismatch; no smoothing policy was enabled.

Native46 installed/device checkpoint: [actual independent build review](../../../build/evidence/native-pass-46-build-review-typed-1/result.json) `e58c1a525bcdd1fcc830f0d32365b92f9ee9f570825c638b767098d2d3e1af10` is clear. Root preparation `5c8dbe` / session 18704 closed at `9ade0f`, exit 0; activation `c95a7f` / session 57621 closed at `c5b000`, exit 0, PID 40436. [Activation](../../../build/evidence/native-pass-46/activation.json) `0ebbafd9928912f2c175f0c3a4fe6e4b654ed5ee9c9ff55fcba11a336001568b` commits the four exact reviewed copies with Native45 backups retained. [Independent installed audit](../../../build/evidence/native-pass-46-installed-audit-typed-1/result.json) `7f91f0dcfb32824eef61e1f7fdbaaf58725d4f39e01c05c7db9b284b9c7eefb1` is clear, actual `1593af` exit 0, 4,299 bindings.

After full runner-source admissions and actual preflights, Root ordinary17 `9f4f0e` / session 15258 closed at `8e1f9b`, exit 0: 17 passed / four original CPU deselections in 3.92s. [Ordinary result](../../../build/evidence/native-pass-46-affected-regressions-1/ordinary17/result.json) `7cf1e179c250326e2e38610de6ab6aa3175c3e73d84d5570507cd9317e686b05` retains real Python PID 11528, zero test failures/errors/skips and actual zero-owner shutdown. Root affected109 `e49dc5` / session 98768 closed at `bd78b2`, exit 0: 109 passed in 43.83s with all 42 dependency warnings retained. [Affected result](../../../build/evidence/native-pass-46-affected-regressions-1/affected109/result.json) `d7a6b1df2ceaac9dbb01cacfe925f86ed3e994cd4eb40ac95b3896e2c4b73981` retains actual Python PID 19408 and successful cleanup. Root aliased6 preflight `17b89f` passed; actual `f85e1e` exited 0, six passed in 2.74s. [Six-case result](../../../build/evidence/line-aliased-six-native46-attempt-1/result.json) `9fdebc7649b1113d70238ee02ffc7d1e7ef41827a7cc8af519ae58756de68cc5` preserves complete fixed-reference comparisons, row/retirement/cleanup receipts and current native identities. These are separate actual jobs on 610.88; historical 595.79 results are unchanged. Independent saved-outcome reviews remain pending.

The [typed upstream saved-outcome review](../../../build/evidence/typed-sampling-glir-oracle-outcome-review-1/result.json) is independently clear (`e60a926bf309b61b65523b0d2cbefa4895ae404aaac89ba330515558f36477db`), including both full integer-byte frames, actual GLIR, R32I/UI formats, current 610.88 state, unchanged providers and cleanup. It remains original GLIR texture-load evidence only. The [isolated typed candidate CPU outcome](../../../build/typed-sampling-runtime-work-1/cpu-outcome.json) now passes the coherent 40-file compile overlay: actual `859b06` / session 67171 closed at `6e5da3`, exit 0, all four targets compiled; `2f688d` exits 0 with all three CTests passing in 0.65s. The earlier trial configurations/build failure and compiler warnings remain retained. Canonical typed integration, endpoint sampler scalar compatibility, matching native build and candidate pixel parity remain open at this historical checkpoint.

### 2026-10-16: Native46 qualified; typed sampler integration prepares Native47

The [independent ordinary17/affected109 outcome review](../../../build/evidence/native46-regression-outcome-review-smooth-1/result.json) is clear, `0b7ad84f27ecab2af4650e92f371b64080fd40b548d9cf78f245e5c900c56f22`. It checks all 126 original XML outcomes, 769 decoded arrays, 299 exact saved pairs, original resident/recovery predicates, complete before/after input maps, native identity, process edges and cleanup on 610.88. The [independent aliased-six review](../../../build/evidence/line-aliased-six-native46-outcome-review-remaining-1/result.json) is also clear, `098bdc077ac7b7d9ffd6a89b10026c74959681edd821e6d7f1f0b1e919ea5fa5`: all six complete reference frames, retained GLIR, draw/dispatch/row counters, retirements and zero-owner shutdowns agree. These close the Native46 batch at those scopes. They do not qualify subsequent canonical changes or smoothing.

The exact reviewed compiler candidate was applied to five canonical shader files plus the new `typed_sampling_contract.cpp`; [application receipt](../../../build/typed-sampling-canonical-application-work-1/application.json) is `0038ac4713b065c3014b4b93c5d0327b91ff1be83b96da9411420313151c2382`. Root then integrated the byte-exact compiled runtime, endpoint sampler scalar compatibility, four corresponding line-contract controls and CMake registration. [Root application/focused CPU receipt](../../../build/typed-sampling-runtime-application-work-1/application.json) is `8bf13e8663060ab2aff9adff75f69bae135839b12f4deb994d877c9117817ed3`. Actual configure `27e692`, build `7379e0` / session 23257 closed at `27f42c`, and CTest `c33e02` all exited 0; the canonical line evaluator contract passed. The first receipt-author metadata path failure is retained separately and does not change the successful CPU observations.

The ten canonical transitions add Uint/Sint sampler2D normalization/reflection and actual bind-layout types, derive storage signedness from retained allocations, admit the original numeric RED_INTEGER/R32I/UI GLIR formats and reject scalar/dimension mismatches. Existing float paths and public Python APIs retain their previous scope. A complete independent source review and Native47 ownership/adapter preparation are in progress. Matching full build (25 targets / 27 CTests), activation/audit and candidate integer texelFetch GPU parity remain pending. Installed Native46 remains unchanged.

The isolated 96-byte planning-budget test's first source review blocked its mixed header paths and package-source lookup; work1 stays preserved. Fresh `build/input-partition-forced-budget-work-2` addresses those setup issues and unknown device-attempt reporting while retaining exact candidate/fixture/criteria bytes. Independent work2 source review is in progress at this historical checkpoint; no test extension or GPU result is yet qualified there. New outputs stay in named folders. No deletion is claimed; the earlier deletion rejection remains respected.

Native47 CPU/build checkpoint: Root ownership author `d88509` exited 0, publishing `b0d61f7e3cedda07bef39ca99c7176001f511ecc87a61352bc00d50a8b87b2b9`. Original freeze `b1570a` / session 86105 closed at `ff11bd`, exit 0, [frozen inputs](../../../build/evidence/native-pass-47/frozen-inputs.json) `160136a37d0f4d5e2480e4fd09ab4f5d68328e51eb5727803f95e5f9bb1deb5c`. Original build `cd79e7` / session 8003 closed at `f38444`, exit 0: all 25 targets and all 27 CTests passed in 3.31s, with final source/harness/SDK/origin/protected-native checks passing. [Independent complete-build admission](../../../build/evidence/native-pass-47-build-review-remaining-2/result.json) `6669c14f7312a86e420339fddcc88fa16f3403f68d2eb4497f17a0d80a3e06d6` checks 4,323 inputs. The first review's `external_argv` metadata-key failure is retained; fresh outer2 preserves every original observation and corrects that key only. No producer or test replay occurred. Root installation preparation `16d4bf` / session 73580 closed at `e22530`, exit 0, approval `1fdf3cd2a3904d3dcddd9d41456f1908e08bad91307810ec8011ee319755f018`; no native copies have been committed yet.

The isolated partition extension built and passed [independent build admission](../../../build/evidence/input-partition-forced-budget-build-review-remaining-1/result.json). Its 525-file package preserves the exact frozen Python source and separate native origin. The first actual attempt stopped before device creation on editable-import interception. Driver3 fixes import isolation; its first exact frame then exposed an incorrect test count that included presentation. Driver4 corrects scene/presentation/native counts to 1/1/2 and warm temporary allocations to one uniform plus one readback, with exactly 32 uniform bytes. Actual `553cfa` exited 1 after cold, resident and recovered frames all matched the first case exactly, with two physical streams (96/28 bytes), stable CPU children, warm zero geometry conversion/upload and a real generation advance/reupload. The remaining assertion conflates retained user compilation with internal presentation compilation. Frozen primary source and original acceptance conditions establish exactly 2 parse / 1 link / 2 SPIR-V calls for the recreated presentation pair, with zero new portable misses/normalizations/conversions and subsequent warm compilation zero. Fresh tests are being prepared to require those exact attributed counts. This remains a partial failed gate, not full six-case acceptance or a claim of zero global compiler work during recovery.

Contained storage maintenance `94a08b` exited 0: [before/after result](../../../build/focused-cpu-storage-maintenance-work-1/result.json) verifies all 190 files in two closed focused CPU build directories remain byte-identical after NTFS compression. Complete logs are retained; no files were deleted and no rejected deletion was retried.

### 2026-10-16: Native47 installed and matching regression groups admitted

Root activation `51e5f1` / session 50847 closed at `54c1fb`, exit 0. [Activation](../../../build/evidence/native-pass-47/activation.json) commits the four reviewed Native47 files, retaining Native46 backups. The installed `_dawn` SHA256 is `72ec70d4f15a9a615e7033306c9af98ca290ca7f1598c053c7d2c04b029f16c8`. The [independent installed audit](../../../build/evidence/native-pass-47-installed-audit-remaining-1/result.json) is clear on all committed copies and immutable activation inputs. No native build or installation was replayed to correct the earlier metadata-key failure.

The unchanged ordinary17 and affected109 selections passed on this installed artifact. Their [independent combined outcome review](../../../build/evidence/native47-regression-outcome-review-remaining-1/result.json) verifies all 126 XML outcomes, 769 saved arrays, 299 exact expected pairs, the original resident/recovery predicates, process and hardware identities, before/after inputs and zero-owner cleanup. All 42 affected-suite dependency warnings remain recorded. The six aliased cases also passed their unchanged complete references and [independent outcome review](../../../build/evidence/line-aliased-six-native47-outcome-review-smooth-1/result.json), including draw/dispatch/row counts, retirement and shutdown. Those six cases do not establish additional per-case warm/loss or smooth-policy coverage.

The isolated 96-byte planning-budget extension passed its complete six-case gate: Root `be83b9` / session 94558 closed at `af59c3`, exit 0. [Actual result](../../../build/input-partition-forced-budget-work-2/gpu-attempt-4/result.json) and [independent outcome review](../../../build/evidence/input-partition-forced-budget-outcome-review-smooth-1/result.json) establish all 18 full frames, two- and three-stream layouts, stable warm owners, three real device losses and exact retained-input reuploads. Resident shader/conversion/geometry-upload work is zero; recovery retains user artifacts while the internal presentation pair incurs exactly parse2/link1/SPIR-V2, followed by zero compiler work on recovered warm captures. This uses a separate extension with an explicit reduced planning budget; it does not claim a natural hardware limit, production allocation batching or zero global compiler work during recovery. Every earlier failed setup/assertion attempt remains retained.

Integer-sampler GPU driver work3 stopped before device creation on dynamic module registration; work4 corrected registration and reached the actual Native47 Vulkan device, then stopped before the first draw on unsupported `GL_FRAMEBUFFER_SRGB` disable. Both failures and cleanup receipts remain retained. Work5 omits only that context command, using pinned source evidence for fixed linear RGBA8Unorm scene/readback and BGRA8Unorm presentation targets, one sample and a nearest-sampled Y flip without gamma conversion. This is source-derived state equivalence, not a runtime format query or framebuffer-sRGB API qualification. Original 21 fixture commands, all integer words, complete expected frames, exact comparison and recovery requirements remain unchanged. Independent source review and the fresh GPU attempt are next.

Allocation-size ordered batching is being developed as a separate portable CPU planner before runtime/shader integration. It must preserve original vertex/instance identity, divisor origins and instance-major primitive order, enforce all allocation/control limits before publication, and retain one complete immutable owner for a logical draw. Native47 sources remain fixed during its current hardware qualification. Cybersecurity work remains excluded.

Native47 integer2D gate completed: independent work5 source review is clear. Root preflight `219fac` and actual GPU run `8f4de4` both exited 0. [Actual typed result](../../../build/typed-sampling-native47-gpu-work-5/gpu-attempt-run-1/result.json) retains the production module, driver PID 40024, actual Python PID 40828 and explicit GPU release. The [independent saved-outcome review](../../../build/evidence/typed-sampling-native47-gpu-outcome-review-remaining-1/result.json), `27d1f2d796c5db3aaa879d0d78f483bbbd7723c8bb7381d8ca2f11b0d103da9e`, verifies all eight complete 32x24 RGBA frames against both immutable original captures and independently expanded integer input bytes. Both 128-byte signed/unsigned uploads and all 21 cold fixture commands match exactly. Four resident phases have zero work across all 17 required counters; two genuine loss recoveries preserve portable artifacts and reupload inputs with the exact attributed presentation-helper compilation, then return to zero warm work. Retirement, shutdown, all retained failures and all before/after source/native inputs are admitted. This closes the selected integer2D texelFetch gate only; live sampling/filtering, other dimensions, public Program assignment and wider plan13 scope remain open.

Portable batching planner applied: [independent source/saved-CPU review](../../../build/evidence/allocation-batching-planner-review-remaining-1/result.json) is clear. Root application `577abe` publishes `cpp/runtime_batch_plan.hpp`, the new `tests/input_layout/batch_planner_contract.cpp` and a separate `input_batch_contract` CMake target. The [application receipt](../../../build/allocation-batching-application-work-1/application.json) confirms production runtime/shader sources and all four installed native files remain unchanged. Focused canonical-source CMake configure `668429`, Release build `34a782` and CTest `056e57` all exit 0: 27,526 checks pass. [CPU observations](../../../build/allocation-batching-application-work-1/cpu-outcome.json) retain the initial shell PATH lookup failure before any configure, followed by the explicit local CMake invocation. The standalone focused project does not substitute for a fresh full-root SDK/native build.

The planner bounds all physical streams, remapped indices, the distinct eight-byte identity header, logical control charge and encoded draw count. Independent selected-row/primitive traces retain sparse/high IDs, incomplete tails, divisor origins and instance-major order; four-stream tests compare every packed word at exact byte boundaries. Its shared-owner publication seam is a portable prototype only. Actual DrawSnap/cache transactions, shader ABI, submission/Tickets, non-LIST carry and production removal of allocation-size refusals remain pending. Public integer Texture2D/Program support is being prepared and tested in an isolated Python candidate; it has not been applied or hardware-qualified at this checkpoint.

### 2026-10-16: public integer2D bindings applied and qualified

Explicit `Texture2D(..., internalformat='r32i'/'r32ui')` now retains native int32/uint32 words, requires one red channel and nearest interpolation, and emits the numeric integer-format GLIR already supported by Native47. `Program` accepts a matching explicit `isampler2D`/`usampler2D` texture, updates an existing typed texture, and replays pending assignments. Invalid signedness, dimensions, filters and typed updates fail before their relevant object/queue mutations. Default floating-point behavior remains unchanged. The [source/CPU admission](../../../build/evidence/typed-sampling-public-api-source-cpu-review-remaining-1/result.json) verifies 70 new focused plus 73 legacy CPU tests, with one actual-canvas test explicitly deselected. The first isolated test-selection/setup failure and its attempted native import remain retained; the passing isolated run attempted no native graphics import.

The unchanged ordinary17 and affected109 groups passed against the complete candidate package and the audited installed Native47 leaves. The [independent regression outcome review](../../../build/evidence/typed-sampling-public-regression-outcome-review-remaining-1/result.json) admits all 126 XML outcomes, 769 decoded arrays, 299 exact saved pairs, original warm/recovery/lifecycle predicates, process origins and cleanup. Its 4,299 producer bindings remain equal before/after. The isolated launch transport uses the complete staged package and only two explicitly audited native leaves; it does not assert that the whole current source tree equals historical Native47. Dependency warnings remain recorded.

Root public GPU run `5771e1` exited 0. The [actual result](../../../build/typed-sampling-public-gpu-work-4/gpu-attempt-1/result.json) and [independent saved-outcome review](../../../build/evidence/typed-sampling-public-gpu-outcome-review-remaining-1/result.json) establish all ten complete 32x24 RGBA frames: two public OpenGL reference captures followed by eight Vulkan cold/resident/loss-recovered/recovered-resident captures. All bytes match the independent integer-word oracle and immutable original captures; Vulkan also matches the fresh public OpenGL frames. Public constructors, properties, shaders, exact 128-byte signed/unsigned DATA, numeric SIZE and TEXTURE association are observed. Four resident phases have zero work across all 17 required counters. Two real losses advance generation and reupload retained inputs while preserving portable artifacts, with the exact presentation-helper parse2/link1/SPIR-V2 attribution. Retirement and explicit shutdown reach zero logical owners. Both backends use 610.88; Native47 production CPP37/native4 stay unchanged.

The first public GPU setup attempt stopped before drawing because the fork's Qt backend always selects Dawn. It remains failed and retained with honest unknown partial-context cleanup. The corrected OpenGL producer uses the complete original 518-file upstream package plus exactly the same two reviewed gloo overlays; Vulkan uses the complete 521-file fork package. Original source/data identities, generated version, distribution RECORD and both overlay origins are pinned. No backend graft, shader change, mask or tolerance adjustment was used. Live integer `texture()` sampling remains unrun and unqualified: the pinned Tint core has only float/depth sampling overloads, and its SPIR-V ImageSample lowering has no integer fallback. Integer texelFetch support does not close that requirement.

Root application `ae0da6` exited 0 and published the exact reviewed Python files, new focused test and two compatibility-ledger entries. [Application receipt](../../../build/typed-sampling-public-application-work-1/application.json) verifies all 521 canonical package leaves now match the tested candidate, with backups and all four installed native files preserved. Canonical CPU check `a408bf` passes all 143 identical normalized test IDs with one observed canvas deselection and no graphics-native import attempts; [result](../../../build/typed-sampling-public-application-work-1/cpu-attempt-2/result.json). Its first harness attempt overblocked the audited CPU-only font extension and is retained; the corrected harness permits only that unchanged SDF artifact while retaining the Dawn import block. Normal editable-import smoke `68464f` also passes public typed assignment and pending replay without a draw or device. No new native build or activation is claimed for these Python changes or the unused portable planner.

Additional contained maintenance `bd631c` compresses the two closed allocation-planner CPU build directories; [before/after result](../../../build/allocation-batching-storage-maintenance-work-1/result.json) verifies all 68 files remain byte-identical. No files were deleted. Runtime batching, smooth coverage, live integer sampling, remaining formats/platforms, performance and release remain open; cybersecurity work remains excluded.

## 2026-10-17: ordered allocation batching, staged renderer integration

The installed artifact remains Native47. Public integer2D changes retain the preceding qualification. The full original thirteen requirements remain active, with cybersecurity work excluded. The current batching candidate is a separate, uninstalled source tree; none of the following CPU results qualifies native raster output or completes general topology batching.

- The [split-ABI2 owner bridge](../../../build/allocation-batching-owner-work-1/REPORT.md) keeps each geometry identity/index/vertex graph once and each instance-block origin/stream graph once. It preflights exact packed payloads and explicit representation/object/native-call budgets, then publishes one complete owner. It avoids geometry-by-instance table duplication and ownership cycles. Its saved MSVC `/W4 /WX` run passes 20,231 checks; [independent source/outcome review](../../../build/evidence/allocation-batching-owner-review-root-1/result.json) is clear at portable CPU scope.
- [Batch shader policies](../../../build/allocation-batching-shader-work-1/README.md) append distinct affine/indexed policies without changing the old policy ordinals or layouts. A reflected std14016 instance-origin block plus native firstInstance restores original uint32 instance IDs; geometry storage restores original uint32 vertex IDs without consuming a user attribute. Four actual compiler contracts pass, including 1,124 new SPIR-V checks and all thirty active user attributes. [Independent review](../../../build/evidence/allocation-batching-shader-review-map-1/result.json) binds the source, compiler inputs and saved outputs; Dawn/device/raster behavior remains unqualified.
- The [topology extension](../../../build/allocation-batching-topology-work-1/REPORT.md) passes 171,317 checks across 4,379 independently derived plans plus the unchanged 27,526-check triangle-list baseline. It retains strip winding/LAST, fan center, loop closure, restart runs, incomplete selections and line-neighbor metadata. [Independent review](../../../build/evidence/allocation-batching-topology-review-map-1/result.json) is clear. Restart remains explicitly off by default, matching current GLIR policy. Low-storage strip/fan/loop affine/carry alternatives, native joins, point expansion and renderer integration remain open.
- A [combined portable run](../../../build/allocation-batching-combined-cpu-work-1/outcome.json) rebuilds the actual planner/owner/topology/transaction contracts together against staged source5 dependencies: 27,526 + 20,231 + 171,317 + 164 checks, all passing with `/W4 /WX`. This directly checks coexistence; it is not a whole-native or GPU gate.
- The [transaction fault controls](../../../build/allocation-batching-runtime-cache-review-1/result.json) exposed MSVC list-move allocation and a nodiscard diagnostic. The candidate adds an allocation-free list/scalar swap and an explicit discarded bounds-check result; 164 controls pass for real cache publication, failures, reuse, eviction, previous-owner lifetimes and one logical DRAW versus fourteen physical calls. Failed compiler attempts remain preserved.
- [Runtime source5 review](../../../build/evidence/allocation-batching-runtime-source-review-remaining-1/result.json) found and verified repair of a raw uint8 direct-binding path. The [976-check routing packet](../../../build/allocation-batching-routing-review-map-1/evidence/process-receipt.json) proves the actual width/whole-upload helpers and independent cap96/cap95 chunk boundaries. A count-based repeated-index routing limitation is explicitly recorded and is being repaired with an exact, cached whole-compact capacity probe.
- The first actual native build of source5 failed its deliberate nothrow-move assertion: pinned Dawn handle wrappers move pointers but lack a noexcept declaration. The [retained failure](../../../build/allocation-batching-runtime-work-1/build-outcome-3.json) remains failed. Source6 compiles the complete runtime translation unit after preparing directly in an unpublished queue slot. Source7 adds explicit rollback/destruction constraints, excludes provisional slots from semantic pending telemetry, and commits clear state only after successful admission. Its full native configuration/build and independent queue fault review are the next gates; no activation occurred.
- Nine independent full-frame GPU fixtures/oracles have been authored before candidate outcomes, including original IDs/divisors/LAST, order-sensitive blend/depth/stencil, instance blocks and the raw uint8 routing regression. Their source/driver and future isolated96-byte planning artifact must be independently admitted before GPU execution. Actual device grants must remain unchanged. Direct OpenGL integer-attribute calls are required because upstream VisPy GLIR does not support that integer attribute API; no upstream-GLIR support claim is made.

Closed CPU build directories were compressed with all 138 files byte-exact before/after and no deletions: [storage receipt](../../../build/allocation-batching-cpu-storage-work-2/result.json). The installed four native files and canonical shipping sources remain unchanged during this staging work.


### 2026-10-17: final batching candidate enters native validation

The final staged production candidate is source12, with 2,190 held project/test leaves. Its [independent source review](../../../build/evidence/allocation-batching-runtime-source-review-remaining-3/result.json) is clear. Batch and compact-fit cache keys now include the actual DRAW instance count; the original geometric selection key remains unchanged. The prior source8 review remains blocked on its demonstrated missing-instance defect. The [expanded transaction/domain contract](../../../build/allocation-batching-runtime-cache-review-3/result.json) passes 502 checks, including same-object 1/13/1 reuse, queue-slot failures and preservation of prior strong owners. The [exact whole-compact probe](../../../build/evidence/allocation-batching-capacity-review-root-1/result.json) passes 103,463 checks across 24,993 probes, allowing legal repeated-ID compaction before selecting batching.

The prior source7 native build compiled all 26 requested targets but passed only 27 of 28 CTests: the line evaluator test still expected seven cache categories. That failure is retained in its [actual build outcome](../../../build/allocation-batching-runtime-work-1/build-outcome-4.json). Source12 preserves the old category ordinals and shared budget predicates while checking the two appended categories. Six focused batching contracts are now registered in the standard build. Configure6 passed on the frozen SDK/toolchain; its production build of 32 targets and full 34-CTest run are in progress at this checkpoint. The [recipe review](../../../build/evidence/allocation-batching-build-recipe-review-typed-1/result.json) is clear. No passing full-build or raster result is inferred before actual process closure.

An [independently reviewed isolated derivative](../../../build/evidence/allocation-batching-planning96-source-review-root-2/result.json) changes only the internal input-planning limit to min(actual grant, 96 bytes). All other production/test inputs invert exactly to source12; reported device grants, native limits and public APIs stay unchanged. Its source preflight passed and its separate CPU configuration is running. It is supplementary forced-batching evidence, not a native release epoch or a real device-limit claim.

The first GPU packet has a retained source-admission inventory defect and must not run; its earlier clear review was incorrect. [Corrected packet2 review](../../../build/evidence/allocation-batching-gpu-source-review-map-2/result.json) verifies that only top-level execution-output directories are excluded and all 175 held source leaves remain checked. All nine frozen full-frame fixtures and scientific predicates remain unchanged. The [separate instance-domain packet review](../../../build/evidence/allocation-batching-instance-domain-source-review-map-1/result.json) admits a same-Program 1/13/1/13 sequence with expected physical draw counts 1/3/1/3. Both GPU packets await actual independently reviewed native/layer artifacts; neither has executed graphics at this checkpoint.

Additional [storage maintenance](../../../build/allocation-batching-native-storage-work-1/result.json) compresses 933 files in four closed native-build directories, verifying every byte before and after. No files were deleted. Active builds, failed attempts and scientific evidence are retained. Native47 remains installed; canonical renderer sources are unchanged. General topology integration, live integer texture() sampling, smooth coverage, remaining scientific/host/platform rows, fixed-quality performance and release requirements remain open. Cybersecurity remains excluded.

### 2026-10-17: production batching candidate passes native and affected regression gates

Root production build6 closed with exit0: all 32 requested targets compiled and all 34 CTests passed in 6.62 seconds. The isolated planning96 build also closed with exit0 for its two native targets. The [independent artifact review2](../../../build/evidence/allocation-batching-native-artifact-review-remaining-2/result.json) rechecks source12's complete 2,190 leaves, the exact single-expression derivative inverse, SDK/toolchain/configuration, actual process closures and all output hashes. Both tested runtime bundles now colocate the extension, DLL and unchanged generated JSON in one exact three-file directory. Production uses the actual granted planning limit; the isolated derivative alone uses 96 bytes. No activation occurred.

The original ordinary17 and affected109 groups pass on the uninstalled production artifact. The [independent retained-outcome review](../../../build/evidence/allocation-batching-production-regression-outcome-review-typed-1/result.json) verifies all 126 original test IDs/XML outcomes, four ordinary CPU deselections, all 769 numeric arrays and 299 exact saved expected pairs, original warm/loss/pending/LAST/native-line predicates, actual process/module origins and zero shutdown gauges. The 42 dependency warnings remain recorded. All 4,344 named before/after inputs match. The earlier failed17 remains failed: a separate layer directory loaded a second DLL instance, so the sibling extension and actual Vulkan interceptor did not share compatibility/telemetry state. The corrected three-file bundle fixes packaging without changing renderer bytes, expected images or scientific assertions.

Forced-budget batching is still unqualified. Source-admission inventory and import-order failures remain preserved. The next direct-OpenGL reference attempt exposed PyOpenGL's default scalar allocation for a four-word integer attribute query; its saved logical close was followed by actual child exit0xC0000374 and is not admitted as normal termination. The following packet supplies a verified uint32[4] output, then stops on array-to-scalar conversion in a different getter, with actual normal child exit1. Both failed before any captured reference frame or Dawn child. A fresh source-only correction supplies explicit scalar getter outputs and preserves every original fixture/oracle/criterion. Actual forced-budget full frames, physical draw counts, warm/loss ownership and same-object instance-domain qualification remain next; ordinary126 cannot replace them.

Separate integer sampling progress: the standalone SPIR-V lowerer2 uses actual immutable per-binding nearest/base-only/wrap policy, preserves float sampling and existing integer fetch instructions, and leaves runtime integration untouched. Root identified avoidable cancellation at mirrored internal texel boundaries; a new contract frozen before observations reproduces 240 mismatches in 23,760 coordinate pairs, including float(1/7) at width7. The principled parity/select correction has zero mismatches on that same contract, and all five candidate CPU tests pass. [Independent source/saved-CPU review](../../../build/evidence/typed-integer-sampling-lowerer-source-review-remaining-2/result.json) is clear within scope. All 96 float32-versus-exact-math distinctions remain visible in both runs. This does not qualify exact-real or OpenGL sampler precision, Tint/Dawn execution, sampler-state snapshots, variant ownership/cache integration or live public texture() behavior.

Further [closed-build storage maintenance](../../../build/allocation-batching-native-storage-work-2/result.json) compresses 1,028 files in three terminal CPU build trees. Every byte matches before and after; no files were deleted. Native47 and all canonical renderer sources remain unchanged. General topology runtime integration, smooth coverage, remaining scientific/host/platform rows, fixed-quality performance and final release scope remain open. Cybersecurity remains excluded.

### Ordered TRIANGLES source applied; matching Native48 build pending, 2026-10-17

The final forced-budget run passes nine OpenGL and 37 Vulkan frames across array/indexed identity, sparse uint32 IDs, divisors, instance traversal, blend order, depth/stencil/LAST, direct-fit routing, warm reuse, device loss, pending deletion and retirement. A separate same-object instance-count sequence passes four OpenGL plus four Vulkan frames for 1→13→1→13 instances. Independent saved-outcome reviews are clear for [the 46-frame group](../../../build/evidence/allocation-batching-gpu-outcome-review-map-work-4/base5-outcome-1/result.json) and [the eight-frame instance sequence](../../../build/evidence/allocation-batching-gpu-outcome-review-map-work-4/instance-outcome-1/result.json). The internal 96-byte planning budget leaves actual device grants unchanged; this qualifies selected TRIANGLES routing rather than general topology batching.

The exact20 reviewed source transitions are now applied. The [independent publication audit](../../../build/evidence/allocation-batching-runtime-application-outcome-review-map-1/result.json) verifies current bytes, ten before backups, the complete2190-leaf reviewed projection and unchanged Python/native baselines. The staged production build remains qualified by32 targets /34 CTests and [the independent original17/affected109 review](../../../build/evidence/allocation-batching-production-regression-outcome-review-typed-1/result.json). Native47 is still installed; those candidate results do not substitute for a fresh formal Native48 build, activation audit and matching device checks.

Native48 ownership is published and [independently reviewed](../../../build/evidence/native48-ownership-review-map-1/result.json):601 source files,4111 harness inputs,1936 inherited datasets,67 native owners,32 targets and34 CTests. Two earlier read-only metadata preflights stopped on inventory-scope assumptions (unchanged pyproject.toml and held physical dataset origins); both failed attempts remain recorded. Author3 and the unchanged formal build tool's read-only freeze preflight pass. The [actual freeze](../../../build/native48-build-process-root-1/freeze-outer.json) completed with frozen-inputs SHA cc37f1db33aab848a19abf8ab0aea38aa95badbda169d0235c1caf54709598e5. The [formal32/34 build](../../../build/native48-build-outer-root-1/outer-observation.json) and [independent complete-build review](../../../build/evidence/native-pass-48-build-review-remaining-1/result.json) pass, including toolchain, SDK/origins, complete artifacts, current/frozen inputs and installed Native47 protection. The installation record is prepared without copying any native files. The existing formal tools support each inherited dataset's individual physical path and remain unchanged.

Live integer sampling compiler/runtime integration is in a separate staging tree. The reviewed standalone lowerer2 remains CPU-only evidence; runtime snapshots, bounded variant ownership, post-transformation resource liveness and actual GPU/public behavior require fresh qualification. General topology, smooth coverage, remaining scientific/host/platform rows, performance and release remain open. Cybersecurity remains excluded.

The first coherent integer-sampling integration candidate passes7/7 focused CPU contracts. [Independent compiler/source and saved-CPU review](../../../build/evidence/typed-integer-sampling-compiler-integration-review-root-1/result.json) and [independent runtime-only cross-review](../../../build/typed-integer-sampling-runtime-review-typed-1/result.json) are clear within scope. These cover immutable sampler snapshots, self-contained bounded variants, actual post-DCE resource masks and exact shader IO preservation. The [fresh second revision](../../../build/evidence/typed-integer-sampling-build-registration-source-review-map-1/result.json) registers all four new contracts in normal CMake builds while retaining the reviewed compiler/runtime/test bodies. Its exact2196-leaf source passes the [complete36-target/38-CTest build and independent artifact review](../../../build/evidence/typed-integer-sampling-native-artifact-review-map-1/review/result.json), with all38 unique tests passed and complete source/toolchain/process/artifact joins. This is CPU/native compilation evidence; no renderer or device is qualified by that review. Installed Native47 and canonical inputs stayed unchanged.

The live-integer GPU test's scientific inputs are frozen before any capture. [Independent science review](../../../build/evidence/typed-integer-sampling-runtime-gpu-science-review-map-1/result.json) reproduces all128 complete frame oracles per backend from binary32 coordinates and integer-ratio arithmetic. Driver/transport admission and actual OpenGL/Dawn captures, warm/loss behavior and public live sampling remain pending. This is no GPU or arbitrary OpenGL precision qualification.

The first GPU transport remains blocked by two source-proven fixture errors found before launch: the float control must request red format explicitly, and public same-size Program array updates still emit SIZE before DATA. A fresh second transport corrects both while preserving every scientific input, image and native reuse criterion; source controls pass203 checks, and the actual artifact/protected-Native47 input preflight passes. Independent source admission is pending. Native48 installation is held through this first current47 GPU comparison; the future48 donor route is unqualified until the historical native47 observations receive explicit matching held/before-backup origins.

Further [closed-build compression](../../../build/closed-native-storage-root-3/result.json) preserves all1,148 files and their complete before/after inventory in Native47's closed build and three closed integer-sampling CPU builds. No files are deleted; the first failed CPU attempt stays failed. Canonical source and installed native binaries remain unchanged by this maintenance.

The two newly closed Native48 and integer-sampling build trees are also [compressed with identical bytes and full inventories](../../../build/closed-native-storage-root-4/result.json):1,482 files retained, none deleted.

The corrected live-integer GPU transport has now passed [independent source admission](../../../build/evidence/typed-integer-sampling-runtime-gpu-source-review-typed-2/result.json), actual execution and [independent saved-outcome review](../../../build/evidence/typed-integer-sampling-gpu-outcome-review-map-1/result.json). Root's original `e6fc7c` / session88452 closed at `423471`, exit0. All128 OpenGL and128 Dawn complete32×24 RGBA frames match their frozen oracles exactly, with matching cross-backend frames. The review also checks actual public updates, pending sampler/DATA ordering, warm reuse, seven real device-loss recoveries, process origins, normal terminal exits and explicit shutdown cleanup. This qualifies finite nearest/base-level signed/unsigned2D sampling within the frozen domain; unsupported filtering, mipmaps and generated line stages remain outside it. Canonical integer-sampling source is still unapplied. The unchanged original17/affected109 groups on this uninstalled source2 artifact are the next gate; Native47 remains installed until those current47-only jobs close. Formal Native48 installation and its matching regression checks follow.

The uninstalled integer-sampling source2 artifact also passes the original17/affected109 groups. [Independent saved-outcome review](../../../build/evidence/typed-integer-sampling-production-regressions-outcome-review-map-1/result.json) verifies all126 original tests,769 decoded arrays,299 exact saved expected pairs, the unchanged scientific recipes, resident/recovery behavior, actual process closure and explicit cleanup. The first saved reader's metadata-field mismatch remains recorded; reader2 changes only that field predicate and preserves the scientific decoder. No test replay was needed.

Root's Native48 activation `ae3b08` / session90592 closed at `1c6c4c`, exit0, committing the exact four reviewed files; [actual outer observation](../../../build/native48-activation-outer-root-1/outer-observation.json) retains the real standalone Python argv. The first independent installed audit stopped on its inherited venv-only launcher predicate, before emitting a review. A separate read-only derivative admits only the exact observed launcher path/hash while retaining the original activation, transaction and receipt checks; the original failed audit and actual installation record remain unchanged. Installed audit admission and matching Native48 original17/109 checks remain pending at this checkpoint. The integer12 source application helper has [independent source admission](../../../build/evidence/typed-integer-sampling-runtime-application-source-review-typed-1/result.json); both126 gates and the actual installed48 audit are mandatory before applying source.

Native48 is now qualified at its build/install/original126 scope. The [audit-origin derivative source review](../../../build/evidence/native48-installed-audit-python-origin-source-review-map-1/result.json) and [actual installed audit](../../../build/evidence/native-pass-48-installed-audit-remaining-2/result.json) pass without replaying activation. After complete actual Source7 admission, Root's ordinary17 and affected109 both pass. [Independent saved review](../../../build/evidence/native48-regression-outcome-review-map-1/result.json) confirms all126 tests,769 arrays,299 exact pairs, original resident/recovery/pending/LAST/line predicates, normal process exits, cleanup and protected inputs. The earlier audit failure remains unchanged.

The exact integer12 source change is applied to the canonical tree. Root preflight `a539a4` / session76531 closed at `835177`, exit0, with17203 protected inputs. Application `959e27` / session88424 closed at `0350bd`, exit0. The [independent publication audit](../../../build/evidence/typed-integer-sampling-runtime-application-outcome-review-typed-1/result.json) verifies all12 current files, six before backups,37 events,2196 canonical/staged source leaves, Python521/public API protection, both126 gates, the256-frame qualification and unchanged installed Native48. Each file replacement is atomic; the12-file sequence is not atomic as a whole. Native49 ownership is published for603 sources/4117 harness inputs/73 native owners/36 targets/38 CTests and awaits full independent admission before the matching freeze/build. General topology, smooth coverage, remaining scientific/host/platform rows, fixed-quality performance and release remain open; cybersecurity remains excluded.

The [complete Native49 ownership review](../../../build/evidence/native49-ownership-review-map-1/result.json) is clear. The unchanged formal freeze tool's read-only preflight also passes with installed Native48 protected. Actual snapshot35 freeze is in progress; no Native49 build or installation is inferred before process closure.

Next topology slice, after integer sampling is qualified: ordinary triangle strips lowered to ordered triangle lists with restart disabled. Reuse the existing topology planner, ABI2 owners and instance-major schedule. Route oversized byte indices before eager widening, key batch reuse by original topology, select indexed identity from the lowered payload even for original array draws, and publish the triangle-list mode only with the complete prepared snapshot. Preserve strip parity, degenerates and original LAST; retain conservative capacity accounting until the ABI1 planner/ABI2 owner accounting difference is explicitly resolved. Existing topology/cache/owner contracts and original strip parity tests remain unchanged regressions; a separately frozen forced-strip seam fixture is still required. Fan, sprite-point and generated-line paths require their own later integration.

### Native49 built and installed; matching hardware checks pending, 2026-10-17

The actual snapshot35 freeze and formal Native49 build closed successfully. All36 targets and38 CTests pass; final source, harness, SDK, toolchain-origin and protected-native checks pass. The [independent complete-build review](../../../build/evidence/native-pass-49-build-review-remaining-1/result.json) admits the complete603-source/4117-harness/73-owner build and all archived artifacts. The first input author failed before publication because its inventory omitted two nested seals. Fresh author3 corrects only that inventory predicate, has independent source admission and produces the actual build inputs; the original failure is retained without replaying the build.

Root activation `e248f4` / session57598 closed at `9ccbd8`, exit0. The [activation record](../../../build/evidence/native-pass-49/activation.json) commits the four reviewed Native49 files through the approved project interpreter, retaining Native48 backups. The [independent installed audit](../../../build/evidence/native-pass-49-installed-audit-remaining-1/result.json) confirms all four committed copies and complete immutable activation inputs. Matching installed49 original17/109 regression qualification and the128 OpenGL/128 Vulkan integer-sampling frame comparison remain pending at this checkpoint. Earlier uninstalled source2 results retain their historical scope.

The closed Native49 build cache is [compressed with complete before/after inventories](../../../build/closed-native-storage-root-5/result.json): all784 files remain byte-identical, with no deletion. A separate isolated ordinary-strip candidate is being prepared; canonical sources and Native49 artifacts remain fixed during qualification. General topology, smooth coverage, remaining scientific/host/platform rows, fixed-quality performance and release remain open. Cybersecurity remains excluded.

Native49's matching hardware gates now pass. Root ordinary17 `3ad096` / session30448 closed at `e6dff7`, and affected109 `6c3c1e` / session15262 closed at `78216f`, all exit0. The [independent original126 review](../../../build/evidence/native49-regression-outcome-review-map-1/result.json) decodes all769 arrays and confirms299 exact saved pairs, unchanged scientific/resident/recovery/LAST/line/lifecycle predicates, original selections, normal process exits,6526 unchanged protected inputs and explicit cleanup. Current installed49 files are checked separately.

Root matching sampling run `2c9041` / session38367 closed at `739721`, exit0. The [independent installed49 GPU outcome review](../../../build/evidence/typed-integer-sampling-native49-gpu-outcome-review-map-1/result.json) verifies all128 OpenGL and128 Vulkan complete32×24 RGBA frames against128 unchanged pre-observation goldens and each other. It admits actual public same-object updates and queued sampler/DATA snapshots,70 resident phases with17 zero-work counters, seven genuine device-loss recoveries with retained portable artifacts and the exact presentation-helper compilation attribution, normal process closure and explicit logical cleanup. All formal49 source/build/activation/audit/native4 identities join. This closes finite nearest/base-level signed/unsigned2D sampling in the frozen domain on installed Native49. Other dimensions, filtering/mipmaps, generated-line sampling, general topology, remaining scientific/host/platform rows, performance and release retain their open scope.

### Isolated strip implementation and text reuse work, 2026-10-17

The ordinary triangle-strip proposal changes four logical leaves: runtime routing, a small topology/identity adapter, its contract and normal CMake registration. Direct and legal whole-compact paths remain first; oversized strips lower to ordered indexed triangle lists, preserve original parity/LAST/degenerates and instance order, and keep original topology in cache keys. Review caught and corrected shader/string preparation occurring after cache publication. The final proposal restores preparation before cache access and checks the actual lowered policy before private owner publication and warm LRU mutation. [Independent source and saved focused-CPU review](../../../build/evidence/ordered-strip-runtime-review-root-1/result.json) passes seven contracts,3258 new strip checks and complete runtime translation-unit compilation. The two failed control/compile attempts remain preserved. This is a67-leaf partial overlay, not a complete native or GPU qualification.

The coherent2198-leaf full project has [independent source/runner admission](../../../build/evidence/ordered-strip-full-build-source-review-map-1/result.json),37 targets and39 expected CTests. Root preflight passes and actual configuration is in progress at this checkpoint. A separate planning96 derivative is being prepared; granted device limits remain unchanged. [Independent frozen strip science review](../../../build/evidence/ordered-strip-gpu-science-review-root-1/result.json) reproduces all47 complete expected frames with the unbatched oracle,4608 exact sample-center checks and seven distinguishable wrong-result oracles. Actual original OpenGL/forced Vulkan frames, warm/loss behavior, matching regressions and canonical application remain pending. All342 files in the two closed focused build caches are [compressed without byte changes or deletion](../../../build/closed-native-storage-root-6/result.json).

The [text geometry science](../../../build/evidence/text-geometry-science-review-root-1/result.json) freezes12 public cases across96/120/144DPI, rotation, multiline text and anchors, with24 future complete frames per backend, exact CPU atlas/local geometry and strict resident counters. New text images remain unobserved. Source review found that unchanged TextVisual kernel ndarray assignment causes a fresh texture DATA update each draw. A [separate one-leaf Python candidate and saved public-GLIR CPU review](../../../build/evidence/text-kernel-reuse-review-root-1/result.json) preserve the exact65536-byte first upload/defaults and real data changes while reusing one font-owned texture. Its coherent521-leaf package remains staged. The extra64KiB snapshot and byte comparison have no performance qualification. Capture transport, original references, actual candidate pixels/reuse, affected tests and canonical application remain open. Installed Native49 and canonical renderer/Python sources stay fixed. Cybersecurity remains excluded.

Both complete strip builds now pass all37 targets and39 CTests. The [normal saved-build review](../../../build/evidence/ordered-strip-full-build-outcome-review-map-1/review/result.json) and [forced96 saved-build review](../../../build/evidence/ordered-strip-forced96-full-build-outcome-review-map-1/review/result.json) independently verify actual process closure, all project/link outputs, exact passing XML, complete2198-leaf source, SDK/toolchain/dataset identities and uninstalled artifact copies. The forced derivative changes only the planning-limit expression; actual device grants remain unchanged. The first saved reader failed its launcher-image predicate before admission; reader2 adds only the two exact previously proven launcher path/hash pairs and reviews the same unchanged build outcomes without rerunning them. Original OpenGL/forced Vulkan strip captures, matching regressions, source application and a formal installed epoch remain pending.

The text capture transport has [independent source admission](../../../build/evidence/text-geometry-gpu-source-review-typed-1/result.json), and Root's source/artifact-only preflight closes successfully without a graphics launch. A separate frozen saved-quality reader is required before the original24-frame capture. It must admit nonempty live typed transform witnesses and the complete actual OpenGL results before a separate candidate invocation can run. No new text GPU outcome or source application is claimed at this checkpoint.

The two closed full strip build caches are [compressed with complete before/after inventories](../../../build/closed-native-storage-root-7/result.json). All1602 files remain byte-identical; no files are deleted. Raw outputs, all failed attempts, source and installed Native49 artifacts remain available.

The first frozen strip transport remains unrun and has a [superseding execution hold](../../../build/evidence/ordered-strip-gpu-source1-superseding-hold-root-1/result.json). Review of a prior actual capture showed that this driver reports two integer built-ins in active-attribute reflection, which its exact-five-user predicate would reject. Source2 validates and removes only those two known built-in rows, keeps all five exact user inputs and has an exact whole-worker inverse for that narrow correction. Its [independent source review](../../../build/evidence/ordered-strip-gpu-source-review-root-2/result.json) and source/artifact preflight pass. The independent saved reader was frozen before capture, with1330 pure controls and an additional [Root source-boundary review](../../../build/evidence/ordered-strip-saved-reader-source-review-root-1/result.json).

Root strip run `0df0fa` / session5175 closes at `231c9f`, exit0, after reporting all47 original OpenGL and47 forced96 Vulkan frames exact against the unchanged science and each other. The producer also reports20 resident phases with17 zero-work counters, eight actual recoveries,54 logical scene draws,6664 physical scene calls and47 presentation passes. [Literal outer process observations](../../../build/ordered-strip-gpu-process-root-1/outer.json) retain actual direct driver/worker identities and normal exits. Independent decoding of these saved outcomes is pending; no canonical strip application or installed epoch is inferred yet.

The initial actual text reference attempt is failed and retained: `5f6975` / session95838 closes at `7865c0`, exit1, with zero complete frame pairs. It stops at the observation predicate because upstream STTransform stores the pixel scale as float32, while that predicate expects double-precision algebra. The [failed outer observation](../../../build/text-original-process-root-1/outer.json) preserves the actual process results and unknown aggregate logical release for the incomplete corpus. A fresh source-derived binary32 expectation is being reviewed; complete pixel, geometry, atlas, DPI and resident criteria remain unchanged. Original references, candidate text rendering and source application stay open.

The strip [independent saved-GPU review](../../../build/evidence/ordered-strip-gpu-outcome-review-remaining-1/result.json) now closes successfully: reader `6ac8c4` / session79152 terminates at `4d163a`, exit0. It decodes all94 complete frames against the frozen47 goldens and actual OpenGL pairs, checks actual typed attributes/state and every raw-GLIR phase, confirms all20 resident intervals, eight genuine recoveries with exact helper attribution and all draw/presentation counts, and joins12295 immutable inputs with current Native49 checked separately. Both actual workers exit0 and explicit logical cleanup passes. Native internal chunk traces remain predicted;83-byte refusal obligations and physical residency remain unqualified. The normal candidate's original17/affected109 regression transport is being prepared before any canonical application or formal installed epoch.

The normal candidate has an [actual nine-field artifact specification](../../../build/ordered-strip-normal-actual-inputs-root-1/artifact-spec.json) joined to the closed37/39 build and exact uninstalled three-file bundle. Its [original126 transport source review](../../../build/evidence/ordered-strip-normal126-source-review-root-3/result.json) is clear, preserving the exact scientific plugin/recipes and complete staged521 Python leaves while checking current Native49/SDF separately. Both Root source-only preflights pass (`7be486` ordinary17 and `cc84bf` affected109), with16238 immutable inputs. Actual regression runs await the frozen saved reader.

Text source2 has [independent source admission](../../../build/evidence/text-geometry-gpu-source-review-typed-2/result.json), a frozen44-control saved reader and Root source admission. Actual reference retry `f3381c` / session45179 terminates at `adbaf7`, exit1. Four complete frames are saved before the third case stops in upstream OpenGL active-uniform reflection with GL_INVALID_OPERATION. These four frames do not qualify the twelve-case corpus. The [failed outer record](../../../build/text-original-process-root-2/outer.json) remains unchanged. Source inspection finds deferred cyclic Qt canvas destruction and upstream tests' explicit GC boundaries; the exact destructor-to-error chain is not proven. A fresh worker-only lifecycle boundary is being prepared outside the unchanged cold/resident intervals. Candidate text rendering remains unrun.

The two closed failed text capture trees are [compressed with full before/after inventories](../../../build/closed-native-storage-root-8/result.json): all39 files remain byte-identical, including every failed receipt and partial array; none are deleted or promoted to references.

The normal strip artifact now also passes the complete original126 regression gate. Ordinary17 `fd7e9c` / session1675 closes at `c224da`, and affected109 `457801` / session83165 closes at `e92a7d`, all exit0. The [independent saved review](../../../build/evidence/ordered-strip-normal126-outcome-review-map-1/result.json) closes at `845c8d`, exit0, decoding all769 arrays and299 exact saved pairs while preserving original masks, tolerances, resident/recovery/pending/LAST/line assertions, actual process identities and explicit cleanup. [Literal outer records](../../../build/ordered-strip-normal126-process-root-1/outer.json) retain both complete sessions and separate successful preflights. Installed Native49 remains protected; the normal artifact remains uninstalled.

The [exact-four-file publication helper source review](../../../build/evidence/ordered-strip-runtime-application-source-review-map-1/result.json) is clear, including43 saved synthetic controls, two existing-file backups, two new files, all four payloads prepared before replacement and the mandatory actual normal126 admission. The four-file sequence is not atomic as a whole and has no whole-batch rollback. Application has not run. Current text qualification binds the existing CMake/runtime bytes, so strip publication is deferred until its closed Original/candidate saved reviews are complete.

Text source3 adds only durable before/after GC boundaries outside each unchanged complete fixture interval, following upstream's own context-lifetime test practice. Its [independent source admission](../../../build/evidence/text-geometry-gpu-source-review-typed-3/result.json),65-control saved reader and [Root reader source review](../../../build/evidence/text-original-reader-source-review-root-4/result.json) pass. Root source/artifact preflight also passes. Actual Original3 is in progress at this checkpoint; neither a successful reference corpus nor any candidate text GPU output is inferred yet.

Original3 now closes normally: Root `854a44` / session20846 terminates at `efcc47`, exit0, with all24 frames across12 cases. The [independent saved-quality review](../../../build/evidence/text-geometry-original-quality-review-typed-1/result.json) admits complete repeat frames, historical atlases and geometry, actual nonempty typed transform witnesses, DPI/anchor/rotation coverage, all GC boundaries, normal process closure and logical canvas cleanup. [Root process observations](../../../build/text-original-process-root-3/outer.json) preserve the actual driver40788/worker29592 identities and literal session results. Earlier failed attempts remain historical failures. The separate candidate saved reader has [Root source admission](../../../build/evidence/text-candidate-reader-source-review-root-2/result.json); a Root review-script count-shape error is retained separately and changes no producer or scientific predicates. Candidate execution is in progress; its pixels, resident reuse and canonical text application remain unqualified until actual closure and independent saved review.

The separate candidate run `5975b3` / session84608 closes at `90e786`, exit0. Its [independent saved review](../../../build/evidence/text-geometry-candidate-outcome-review-map-1/result.json) closes at `0c8d69`, exit0, admitting all24 complete RGBA frames exactly against the accepted Original3 corpus, all12 historical atlas/geometry/glyph/texture-coordinate payloads and nonempty actual typed transform/DPI/anchor/rotation witnesses. Every resident interval has one public scene draw and17 zero-work counters; all external GC boundary pairs, normal OS exits, explicit retirement/shutdown and zero logical queues pass. [Root outer observations](../../../build/text-candidate-process-root-1/outer.json) retain actual driver44148, exact argv and every literal tool return. The one-leaf candidate remains staged pending its publication checks. Both text saved reviews are closed, so the qualified strip exact-four application is now in progress after a successful17401-input preflight. Installed Native49 remains protected and no new installed epoch is inferred.

The exact-four strip source application now closes successfully: `43f398` / session85409 terminates at `5d707e`, exit0. Its [application record](../../../build/ordered-strip-runtime-application-work-1/application-attempt-1/application.json) records four prepared/replaced files, two exact backups, all2198 resulting native-project leaves, unchanged Python521 and unchanged installed Native49. [Root outer observations](../../../build/ordered-strip-application-process-root-1/outer.json) bind helper41448, actual process observations, literal argv, complete preflight/apply sessions and all actual receipt pairs. Independent publication audit is pending. This source change does not activate a new native artifact. The two closed successful text capture trees are [compressed with complete inventories](../../../build/closed-native-storage-root-9/result.json); all259 files remain byte-identical and none are deleted.

The [independent actual strip publication audit](../../../build/evidence/ordered-strip-application-outcome-review-map-1/result.json) now passes: `8c73e2` / session57137 closes at `8b12a0`, exit0. It checks all17 application output members,13 ordered events with all four payloads prepared first, two actual before backups and two newly created files, all2198 current canonical native-project leaves, Python521/public API protection and unchanged installed Native49. Only the two exact historical CMake/runtime aliases project through their actual backups and known current-after hashes. Normal37/39, strip94, original126 and actual Root process closure remain joined to their original scopes. The one-leaf text publication helper is being finalized; its contained absolute module-origin path correction preserves the prior failed sealer and unchanged criteria. Native50 source-only ownership preparation verifies604 source leaves,4119 harness inputs,1936 dataset files,75 owners (43 shipping/32 contracts),37 targets and39 CTests. Actual Native50 ownership, freeze, compilation, activation and matching installed tests remain future work.

The text helper's first actual preflight is failed and retained: `b7fdce` / session27471 closes at `ac2636`, exit1, before its output directory or any source replacement. [Literal failed process observations](../../../build/text-kernel-application-process-root-1/failed-preflight-1.json) preserve the error: the helper expects `provider_imported`, while the accepted saved candidate review records `reviewer_provider_imported`. Canonical text remains5907 and installed Native49 is unchanged. A fresh work2 changes that exact receipt-field check and local payload metadata, retaining the original frozen helper, source admission and failure; rendering criteria and accepted24-frame results are unchanged. The Native50 source1 ownership proposal is held because it pins that superseded helper. Actual text application and its audit remain pending new source admission and successful preflight.

Corrected text work2 has [independent source/schema admission](../../../build/evidence/text-kernel-runtime-application-source-review-typed-4/result.json), including168 real qualification field chains,24 actual frame/12 case schemas,56 saved controls and the exact metadata-only inverse. Root preflight `6da628` / session93327 closes at `a08a43`, exit0. Application `a2d073` / session92046 closes at `552532`, exit0, applying exactly `text.py`5907→ab7. [Root outer observations](../../../build/text-kernel-application-process-root-1/outer.json) preserve the actual helper38956, literal tool closure, successful preflight and retained failed predecessor. After [Root auditor-source admission](../../../build/evidence/text-publication-auditor-source-review-root-1/result.json), [independent actual publication audit](../../../build/evidence/text-kernel-publication-outcome-review-typed-1/result.json) `710830` / session23785 closes at `477d22`, exit0. It verifies the exact current file, actual backup, four journal events, all521 Python and2198 native-project leaves, unchanged Native49, all24 complete frame pairs and exactly three historical source projections. No native activation is claimed.

Native50 ownership source1 remains held for superseded text helper origins; source2 is blocked for its text-audit field spelling. [Source3 independent admission](../../../build/evidence/native50-ownership-author-source-review-map-3/result.json) checks the corrected `protected_normal2198_after_exact` field against the real auditor schema and preserves all prior failures. Root preflight `3848d0` and actual author `9e2090` close synchronously, exit0. The [actual ownership manifest](../../../build/native50-ownership-1/ownership-manifest.json) records snapshot36/epoch50,604 sources,4119 harness inputs,1936 dataset paths,75 owners (43 shipping/32 contracts),72 retained plus three changed/new owners,37 targets and39 CTests. [Root process observations](../../../build/native50-ownership-process-root-1/outer.json) bind both applications and independent audits. Actual ownership admission is pending; the unchanged formal freeze tool is running read-only preflight. Installed Native49 remains protected and no Native50 compilation is inferred.

Native50 actual ownership [independent admission](../../../build/evidence/native50-ownership-review-map-1/result.json) passes. Snapshot36 [frozen inputs](../../../build/evidence/native-pass-50/frozen-inputs.json) close at aa05c7, exit0. The full build session42154 starts9f73e9 and closesa40493, exit0, with37 targets and39 passing CTests; [literal Root observations](../../../build/native50-build-outer-root-1/outer-observation.json) retain every original tool return. The [complete independent build review](../../../build/evidence/native-pass-50-build-review-remaining-1/result.json) passes at604 sources/4119 harness inputs/75 owners and213 SDK files. Activation session19346 startsa46c1a and closes645a8f, exit0; [literal activation observations](../../../build/native50-activation-outer-root-1/outer-observation.json) bind driver16112 and all four committed files. The [independent installed audit](../../../build/evidence/native-pass-50-installed-audit-remaining-1/result.json) closesc0d5ba, exit0, checks4751 immutable inputs and separately verifies the installed four. Native50 is installed; its matching126/256/24 outcomes remain pending. Cybersecurity work remains excluded.

Native50 matching integer capture d055c5/session29724 closes55f0c2, exit0, with Original and Dawn children44004/27384 both closed0. [Root observations](../../../build/native50-integer-sampling-process-root-1/gpu-outer.json) bind exact actual argv and every literal tool return. The [independent saved integer review](../../../build/evidence/typed-integer-sampling-native50-gpu-outcome-review-map-1/result.json) closes460bb4, exit0, and verifies all256 full3072-byte frames,128 actual GL witnesses,70 resident-zero17 intervals, seven actual loss recoveries,136 scene/128 presentation/264 native draws, exact graph revisions/pending snapshots and explicit cleanup. Historical Source2 feature identity is distinguished from the complete current604/4119 formal50 source/harness and current521 Python. Installed native4 remains separately byte-exact.

Matching original126 preparation has [final actual identity admission](../../../build/evidence/native50-regression-actual-source-review-map-2/result.json); all14 scientific modules, recipes/selectors/XML IDs and547 final source members are retained. Both read-only preflights pass. Ordinary17 runs53ebb1/session88963 throughd398b7, exit0; affected109 runs4dc4ca/session74540 throughe375a1, exit0. [Root observations](../../../build/native50-regression-process-root-1/outer.json) preserve their real preflights, complete tool sessions, driver and Popen IDs, result/seal pairs and unchanged installed50 files. After [Root reader-source admission](../../../build/evidence/native50-regression-saved-reader-source-review-root-1/result.json), the [independent saved126 review](../../../build/evidence/native50-regression-outcome-review-map-1/result.json) runs24f958/session18244 throughdea8bb, exit0: all126 tests,769 numeric arrays,299 saved expected pairs, resident/recovery/pending/LAST/line/process/cleanup predicates pass on Native50.

Matching text50 passes read-only preflight and actual capture50f1c6/session81844 through9ddd28, exit0, using direct driver31680/worker26812 and the same accepted Original24. The initial Root reader-source receipt normalized496 absolute keys; a [fresh exact-key receipt](../../../build/evidence/text-native50-saved-reader-source-review-root-2/result.json) preserves every raw spelling and leaves the source/scientific checks unchanged. The first actual saved review remains [blocked and retained](../../../build/evidence/text-geometry-native50-candidate-outcome-review-map-1/result.json): Root outer1 omitted a required complete driver OS observation. The genuinely captured partial CIM row records only process/parent IDs; a [fresh outer2 with that exact partial evidence](../../../build/text-native50-candidate-process-root-2/outer.json) explicitly distinguishes tool launch argv from OS-observed image/command-line fields. No driver OS command line is invented and no GPU capture is replayed. A narrow independently source-reviewed saved-reader derivative is being prepared; all24 image/atlas/geometry/uniform/GC/resident/process/cleanup predicates remain fixed. Closed cache801files/238885273 logical bytes has a prepared compression script; actual compression remains pending final matching text admission.

Native50 batch checkpoint: the [final text Work2 reader-source admission](../../../build/evidence/text-native50-partial-CIM-reader-source-review-root-2/result.json) verifies all29 held files/31141 inputs, the complete raw inverse, unchanged scientific helpers/Main frame loop/companions,184 pure controls and the actual closed process metadata with targeted refusals. Root's first extracted-helper check failed for a missing stdlib os namespace entry; the script, literal failure and fresh helper-only correction remain preserved. The [independent actual text saved review2](../../../build/evidence/text-geometry-native50-candidate-outcome-review-map-2/result.json) runs91f0c9/session93496 throughc81361, exit0, on the original closed capture. All24 full candidate frames exactly match admitted Original24; all12 atlases, geometry/UV/glyph results, real typed uniforms, DPI/anchor/rotation, GC boundaries, same graph, resident17 zero counters, retirement/shutdown and normal OS child closure pass. Its process facts distinguish actual tool launch argv and the genuine partial CIM record from unmeasured direct driver OS command line/image; the worker OS parent image is observed. No graphics replay or changed scientific criterion is used. Failed saved review1 and original outer1 remain immutable.

[Closed-cache compression](../../../build/closed-native-storage-root-10/result.json) runs77677a/session75859 through872184, exit0. The exact801 files and238885273 logical bytes have identical before/after inventory hash b31417d3; no file is deleted or moved, and installed50 native4 remains exact. compact.exe reports101312700 stored bytes, saving137572573 bytes (about131MiB). [Actual tool observations](../../../build/closed-native-storage-process-root-10/outer.json) are outside the immutable18-member execution packet. Final read-only check3c3048 confirms the five published canonical leaves, installed Native50 four and complete cleanup execution seal remain exact.

This completes integration and matching qualification of the current ordered-strip batching and TextFont kernel-reuse batch on Native50. The original thirteen requirements remain open for the broader topology, smooth-coverage, remaining scientific/host/platform, fixed-quality performance and release conditions. Cybersecurity work remains excluded.

Implementation-first sprint1 checkpoint: the canonical fan route preserves an oversized fan's original selection before u8 widening or global expansion, bypasses unsupported direct/whole-compact paths and uses the existing bounded ABI2 owner. Existing legal whole-fan expansion remains in place. The extended ordered strip/fan CPU contract checks independent primitive order, original LAST and degenerate IDs, arrays/u8/u16/u32, high/all-ones IDs, divisor2/3 and instance seams, cache domains, zero draws and conservative budget refusal. The existing 64MiB planner control limit still applies.

The new point planner produces constant-size implicit ranges over the original point/instance domain. Its owner builds separate bounded user/identity leaves, admits aggregate payload/control/record/key and actual-capacity charges, and retains no borrowed Plan, index or source span. Runtime integration preserves the legal whole-draw path, keys the new route by original selection, source/index revisions and grants, commits through the transactional Batch cache and encodes each range with local firstInstance0. Stored identities preserve the original global instance for shader IDs and divisor fetches. Real Tickets retain the complete owner graph, and existing semantic/native draw counters and device-loss traversal include the new route. Point field partitioning beyond the existing packed layout remains open.

The [final CPU snapshot](../../../build/implementation-sprint-1/cpu-2/outcome.json) passes eight contracts with no failures/skips, verifies all213 pinned SDK leaves and compiles runtime.cpp without linking/loading a native module or creating a device. The point contract also passes the worker's standalone MSVC C++20 /W4 /WX build. Owner tests read actual leaves after producer inputs are destroyed and cover optional leaves, exact/one-under budgets, huge implicit-plan refusal, sparse high IDs, late leaf/attach failure cleanup and predecessor preservation. The initial seven-batching-plus-point-preparation CPU snapshot remains retained as an intermediate result. These CPU results do not qualify GPU pixels, runtime cache reuse or native retirement.

Next, build one native candidate containing both routes, then run matching ordinary regressions and lowered-grant fan/point GPU cases. The affected cases must cover complete frame/order agreement, gl_VertexID/gl_InstanceID and point coordinates, divisor2/3 seams, repeated resident draws, mutation/eviction, queued snapshot survival, loss/recovery, retirement, and physical-versus-semantic draw counts. Keep heavy cross-platform and fixed-quality performance qualification grouped behind that coherent candidate. Generated-line batching needs bounded endpoint/output maps, consumer rebasing and pool scheduling; general smooth coverage still needs the frozen endpoint tie measurements. Neither is closed by this sprint.

Closed sprint CPU outputs are compressed with byte-exact inventories: [CPU1 cleanup](../../../build/implementation-sprint-1/storage-cpu-1/result.json) preserves201 files and saves33876633 bytes; [CPU2 cleanup](../../../build/implementation-sprint-1/storage-cpu-2/result.json) preserves201 files and saves34602363 bytes. The [point worker cleanup](../../../build/implementation-sprint-1/point-cpu/owner-cleanup.json) also preserves all scratch bytes. No installed Native50 file, prior source snapshot, result or failure evidence is deleted or moved.

Implementation-first sprint2 checkpoint: generated-line List/Strip/Loop draws that exceed an individual buffer, compute-dispatch or physical-draw count limit can use bounded endpoint/output chunks. The existing legal whole-draw route remains available. The constant-size planner stops chunks at original instance boundaries and preserves occurrence identity, original vertex/instance IDs, divisor reads, original LAST and flattened primitive IDs. Fresh endpoint occurrences are evaluated exactly once; command-encoder copies carry the previous endpoint and loop head into trailing output rows before rendering. A closing-only loop chunk owns two copied rows and issues no compute invocation.

Each chunk holds a separate existing pool lease and immutable compute/render uniforms. The route retains128-slot,64MiB aggregate output/UBO and1MiB native-control admission, plus64MiB packed-input and8MiB host-descriptor limits. It does not reuse an in-flight slot by overwriting queue-written uniforms. The complete original snapshot owns the leaves until submission; flattening preserves clear operations on the first leaf and one semantic DRAW while counting every physical draw. Real Tickets retain original inputs, chunk work, leases and bound resources through retirement. Probe and failure traversal include pending leaves. Oversized diagnostic endpoint capture is explicitly refused until an aggregate capture protocol is implemented.

Packed chunk inputs publish as one transactional cache graph. Review found and repaired historical/oversized cache-hit promotion before snapshot validation: the preparation callback now stages all leaves before copied-cache commit. Review also found missing slot/membership/affinity overhead in initial pool preflight; preparation now runs the exact empty-pool admission algorithm with non-native payloads before publishing. Source/index revisions, topology, original selection and grants separate cache domains. CPU packing accepts bounded row accessors without changing the evaluator ABI. The generated consumer retains its64-byte parameter block and adds paired local mapping in both shader stages, with a changed policy/cache identity. Coverage arithmetic and Smooth/MSAA refusals remain unchanged.

The [combined focused CPU outcome](../../../build/implementation-sprint-2/cpu-1/outcome.json) passes19 contracts with no failures/skips and compiles runtime.cpp without linking/loading a native renderer or creating a device. All213 SDK leaves and final canonical source hashes are checked. The new planner contract covers5,400 exhaustive small schedule cases plus actual raw packing, repeated/high/all-ones IDs, index-prefix semantics, nonzero first,13 instances/divisor2/3, odd list tails, copied-only closures and budget/overflow refusals. The [consumer compiler contract](../../../build/implementation-sprint-2/consumer-cpu/outcome.json) passes38,299 checks, including execution of compiled SPIR-V segment mapping and ordinary mapping regression controls. Its interpreter stubs parameter validation, so malformed-UBO rejection has structural coverage rather than dynamic execution. Two failed test-authoring attempts remain retained; production code was unchanged across those corrections.

The next qualification step is one coherent native ownership/freeze/build candidate containing fan, point and generated-line changes. Matching lowered-grant GPU cases must exercise pixels and order, real seam/head copies, primitive/vertex/instance IDs, divisors, resident reuse, mutation/eviction, queued snapshot survival, device loss/recovery, semantic/native draw counters and actual retirement. General smooth coverage and original scientific/host/platform/performance/release conditions remain open. [Closed combined CPU cleanup](../../../build/implementation-sprint-2/storage-cpu-1/result.json) preserves408 files byte-for-byte and saves63633272 bytes; the consumer worker also saves9687218 bytes and the planner worker522444 bytes. No native installation or GPU qualification is claimed.

Final sprint2 accounting refinement charges retained capacities of copied snapshot vertex/binding/slot/stream/sampler-policy vectors and strings in the host-control admission, alongside uniforms and work metadata. Only runtime.cpp changes after the19-contract run; [runtime recheck2](../../../build/implementation-sprint-2/cpu-2/outcome.json) verifies that exact single-file difference, recompiles the final translation unit against all213 verified SDK leaves, and inherits the19 passing tests with byte-identical test/header/compiler inputs. Its closed output cleanup is recorded [separately](../../../build/implementation-sprint-2/storage-cpu-2/result.json). This remains CPU qualification only.

Implementation-first sprint3 checkpoint: point-sprite fields can now partition across the complete granted vertex-buffer budget. Both canonical artifact preparation and captured DRAW preparation use the same exact partitioner with every physical stream advancing per flattened instance. Shader locations remain unchanged; point corners and original identities consume no extra vertex attribute or stream. Existing legal single-stream whole-draw packing remains available. Nonzero multi-stream selections use the owning batch route even when only one physical draw is needed, while zero rows create no derived payload/cache owner.

Point batch row capacity is bounded by the largest individual user stream, identity storage and native draw count. Aggregate payload costs still include every stream. Each immutable draw descriptor owns an ordered vector of user-stream records; metadata admission charges its actual vector capacity, every leaf and slot-specific key, payload capacities and aggregate retained/control costs before publication. The plan keeps a fixed scalar partition description, and the runtime cache includes the exact validated slot/stride/field/offset map alongside source/index revision and divisor dependencies. Runtime binding offsets/strides and native encoding select each physical stream by slot. No point shader or identity ABI changes are required.

The [final focused result](../../../build/implementation-sprint-3/cpu-1/outcome.json) passes10 contracts with no failures/skips and compiles runtime.cpp against all213 verified SDK leaves, without native loading or GPU creation. Coverage includes the seven retained ordinary batching contracts, existing point shader/input contract, generalized point owner contract and new partition contract. Independent oracles verify the noncontiguous12/12/8/8 packing into two20-byte streams, mixed widths, byte-exact single-stream compatibility, all index widths and high/repeated/all-ones IDs,13 instances with divisor2/3 seams, actual owned leaves after producer destruction, exact and refused budgets, map replacement, source bounds and late failure cleanup. Worker standalone MSVC C++20 /W4 /WX passes both point contracts. The earlier wrong test namespace and zero-width test-fixture crash are corrected; their failed records remain retained.

The [closed combined CPU cleanup](../../../build/implementation-sprint-3/storage-cpu-1/result.json) preserves253 files byte-for-byte and saves51401801 bytes. The [point worker cleanup](../../../build/implementation-sprint-3/point-cpu/storage/result.json) preserves88 files and saves2053459 bytes. Installed Native50 remains unchanged; no file is deleted or moved. Next implementation gaps include aggregate endpoint capture for chunked lines and the required smooth-line precision measurements. Consolidate the fan/point/line source into one native candidate before the deferred GPU pixel, cache, recovery, retirement, platform and performance checks.

Implementation-first sprint4 checkpoint: chunked generated-line diagnostics now publish one capture ID and logical record per original draw. The bounded capture plan owns scalar metadata for each physical part; logical data concatenates only fresh evaluated rows in original occurrence order, and raw data concatenates the actual mapped allocations. Optional `chunks` metadata and `capture_phase="evaluated_before_carry"` appear only on chunked records, preserving the legacy capture format. Readback commands run after evaluation and before seam/head copies, so every byte after the fresh prefix, including future carry slots, must retain its canary. A closing-only loop part owns its two render rows without a compute dispatch or readback.

Admission checks rounded workgroup padding, every physical binding, aggregate raw/logical storage and retained metadata capacities before publishing the capture/cache graph. Each physical part retains its own map state; collection starts after Ticket retirement, and timeouts preserve the same owner, readbacks and budget charge for retry. Ticket/probe traversal deduplicates the shared logical capture. Loss and shutdown include all physical readbacks. Review caught partial logical data surviving a later-part failure; terminal chunk failures now clear logical data while preserving actual raw evidence. Independent source reviews found no remaining helper/schema, publication or lifecycle blocker; this is source review rather than GPU qualification.

The [focused CPU result](../../../build/implementation-sprint-4/cpu-1/outcome.json) passes all 13 selected contracts without failures or skips and compiles both runtime.cpp and the Python binding against the exact source snapshot and all 213 verified SDK leaves. The new contract covers independent List/Strip/Loop occurrence order, repeated/high IDs, copied-only closures, pre-carry guards, retained failure bytes, malformed metadata, budgets and ownership. The [Python decoder controls](../../../build/implementation-sprint-4/schema-cpu/result.json) pass 40 new chunk cases plus 22 existing reflected-decoder cases, with 25 GPU/other cases deselected. Their four source hashes are checked against the final snapshot before those results are inherited. No native renderer is loaded or device created.

The [closed combined CPU cleanup](../../../build/implementation-sprint-4/storage-cpu-1/result.json) preserves 323 files byte-for-byte and saves 60,200,555 bytes. The [capture helper cleanup](../../../build/implementation-sprint-4/capture-cpu/storage/result.json) preserves 65 files and saves 513,571 bytes. Installed Native50 remains exact, and no evidence or failure is deleted or moved. Aggregate capture implementation is now CPU-checked; the next native qualification must exercise real mapping, guard failure, carry ordering, timeout/retry, loss/recovery and retirement together with the fan/point/line routes. General smooth coverage still needs the frozen endpoint precision measurements, and the original scientific/host/platform/performance/release requirements remain open.


Implementation-first sprint5 checkpoint: the combined fan, point, generated-line batching and chunked endpoint-capture source now has [independently reviewed Native51 ownership metadata](../../../build/native51-ownership-review-map-1/result.json). The actual metadata author closes exit0 and its complete manifest equals the independent parent/policy projection. There are 609 source leaves, 4,129 harness inputs, 1,936 unchanged dataset rows and 84 disjoint native owners (48 shipping/36 contracts). Eighteen final-matching leaves derive from the exact sprint3 seven-leaf and sprint4 eleven-leaf CPU archives; nine prior owners transfer and 66 remain. Complete historical packet inventories and proof scopes are retained. The candidate declares 41 targets/43 CTests. All 67 authored files and 64 source-context members are checked; no Native51 freeze, compilation, installation or GPU qualification is claimed. Native50 remains installed and exact. [Next commands](../../../build/implementation-sprint-5/native-next-commands.json) retain the fresh formal destinations and actual-frozen-input hash prerequisite.

The frozen work3 endpoint protocol now has a complete original-only capture runner. The first source review rejected state guards running before observation persistence and incomplete required-state checks; rejected work4 is retained. Work5 fixes those issues but its first actual capture stops on a PyOpenGL glGetShaderiv availability error in the fourth fresh context. Its [independent failed-outcome review](../../../build/smooth-endpoint-tie-probe-work-5/review-outcome-1/result.json) verifies three complete frames, exact negative-family baseline reproduction, all four closes and unchanged identities, while explicitly disclosing the fourth attempt's missing partial GLIR. It remains failed and is not counted as a completed calibration corpus.

[Work6 source](../../../build/smooth-endpoint-tie-probe-work-6/source-ready.json) keeps one original hidden Qt canvas/context alive, resizes the real target and private readback dimensions together, saves local GLIR/shaders on every frame exit and closes the shared canvas in job-finally. All 31 focused runner controls pass, including the previous 23 state controls plus eight resize/lifetime/failure-evidence controls. The 65 protocol controls are inherited only with exact validator/test/receipt identity. Separate independent source and fresh provider/context admissions pass. No shader, explicit vertex bits, protocol case, old expected frame or tolerance changes.

The second actual original-only run closes exit0 (Root session13817, initial51c1a4, terminald1e4dd). Its [independent saved outcome](../../../build/smooth-endpoint-tie-probe-work-6/review-outcome-1/result.json) admits all 24 complete frames, both exact old-family gates, every raw upload/local GLIR/shader/state record, 24 user draws/finishes/readback deltas, four actual canvas dimension transitions and one successful job-finally close. Actual NVIDIA610.88 and GL_SUBPIXEL_BITS=8 are observed; complete provider/base-Python and installed Native50 before/after identities remain exact. Actual Popen-handle and worker-self PIDs retain their separate scopes; no unobserved OS launcher edge is invented.

[Descriptive frame differences](../../../build/smooth-endpoint-tie-probe-work-6/review-outcome-1/diagnostic-differences.json) show all 12 exact endpoint-row reversal pairs and all 16 adjacent-float32 clip-Y-versus-nominal comparisons are byte-exact. Whole-window quarter-turn rotation is exact for the vertical family. The negative-slope family differs at one alpha byte, rotated saved-array pixel (17,4): the rotated nominal frame has alpha173 and the actual rotated geometry has alpha164, with RGB unchanged, in either endpoint order. These are calibration facts, not a unique hardware mechanism or a qualified filter. The nine frozen future predictions and eight reserved holdouts remain unopened, and production Smooth/MSAA guards remain unchanged. A revised mechanism still needs a new frozen formula/prediction contract and genuinely unseen qualification data.

Closed [preparation/failure cleanup](../../../build/closed-native51-and-smooth-storage-root-1/result.json) preserves 118 files and saves 2,555,759 bytes; [final calibration cleanup](../../../build/closed-native51-and-smooth-storage-root-2/result.json) preserves 186 files and saves 79,108 bytes. Every name and byte is checked before/after; no evidence or failure is deleted or moved. No compiler/build assets were generated by this sprint. The coherent native freeze/build and matching batch-route GPU checks, general smooth coverage, remaining scientific/host/platform rows and fixed-quality performance/release requirements remain open. Cybersecurity work remains excluded.

Implementation-first sprint6 checkpoint: the coherent fan, partitioned-point, generated-line batching and chunked endpoint-capture candidate is now frozen as Native51/snapshot37 and fully built. The actual read-only freeze preflight and actual freeze close exit0. [Independent frozen-source admission](../../../build/native51-frozen-review-map-1/result.json) verifies all 609 source leaves, 4,129 harness inputs, 1,936 datasets, 84 owners and complete inherited packet inventories. The frozen source tree is `efa62a95d91f486bc63b621f7512fd9fe992cafb31f3f8c1782dff195bc3b028`; the harness tree is `638e1bdc9eeba5d24f796277da700982aa5e23f60717a12a6ee752c491de3702`. These results close the freeze/build items left pending at the historical sprint5 checkpoint.

The original nine-argument build command completes exit0 (Root session21413, initial1358d7, terminal0f58a0). All 41 targets build and all 43 CTests pass, including the new fan, point-partition, generated-line chunk and chunk-capture contracts. The unchanged build driver runs its own complete preflight before writing build outputs. The literal coordinator transcript retains that exact command and every initial/poll/terminal observation without claiming an unobserved OS parent edge. [Independent saved-build admission](../../../build/evidence/native-pass-51-build-review-map-1/result.json) is clear at complete frozen native build/CTest scope: it verifies 43 binary artifacts, all current/frozen sources and harness inputs, 84 disjoint owners, complete source-context archives, all 213 SDK leaves and their origins, the toolchain, project policy, build cache, test XML and terminal proof hashes. The actual reviewer closes exit0 after checking 4,847 inputs; no producer build is replayed.

Native51 remains uninstalled and GPU-unqualified. Installed Native50's four files remain byte-exact. Matching qualification must exercise fan order and original identities, point stream partitioning, generated-line seam/head copies, aggregate capture mapping and pre-carry guards, timeout/retry, loss/recovery and real retirement. Activation and installed audit precede that matching device work. The [bounded fixture preparation map](../../../build/implementation-sprint-6/batched-fixture-preparation.json) is a proposal only; it is not an executed GPU result or an admitted golden corpus. Production Smooth/MSAA guards remain unchanged. The admitted 24-frame original-only calibration remains separate from Native51 and does not qualify a general smooth filter; a new frozen mechanism/prediction contract and unseen qualification data are still required. Original scientific/host/platform, fixed-quality performance and release requirements remain open.

The [closed full-build cleanup](../../../build/closed-native51-full-build-storage-root-2/result.json) transparently compresses 7,443 files in the closed build cache, frozen source and formal evidence packet, saving 143,715,965 bytes (about 137 MiB). Every regular-file name and byte is checked before/after. Both frozen dependency junctions are preserved unchanged without traversal; the conservative first cleanup attempt stopped on those links before any compression and remains recorded. No evidence, failure or build output is deleted or moved. The [sprint6 machine-readable checkpoint](../../../build/implementation-sprint-6/progress.json) records the actual proofs, scopes, cleanup and remaining gates. Cybersecurity work remains excluded.

Implementation-first sprint7 checkpoint: Native51 activation is complete. The [independent activation-adapter source review](../../../build/evidence/native51-activation-adapter-source-review-point-1/result.json) verifies the exact retained Source3 transaction, approval, actor and installed-audit functions, all Native51 ownership/build bindings and 52 bounded metadata controls. Root's actual metadata author, complete approval preparation and read-only activation preflight pass. Actual activation session35702 starts209366 and closesf66f6d, exit0, driver42656; [literal coordinator observations](../../../build/native51-activation-outer-root-1/outer-observation.json) retain every original tool return and exact command. All four files commit with actual Native50 backups and complete immutable input archives. The [independent installed audit](../../../build/evidence/native-pass-51-installed-audit-map-1/result.json) closes exit0 and checks4,888 inputs, exact committed/staged/archived copies and complete activation input/terminal closure. This establishes installed identity; matching new-route GPU qualification remains open.

Review found a separate implementation gap in ordinary width-1 unsmoothed LINES/LINE_STRIP/LINE_LOOP: those native routes bypassed oversized input batching and large loops attempted complete index expansion. A staged four-file fix adds generic ordinary-input bridging to the existing ABI2 owner, defers oversized loop/u8 conversion, emits ordered native line-list pairs and preserves successful direct/whole-compact paths. All triangle-only helper bodies remain unchanged, while generated/smooth, generic owner/cache and Ticket retirement implementations remain unchanged. [Independent source/CPU review](../../../build/native-thin-line-batching-review-point-1/result.json) is clear. It caught a missed triangle-only final snapshot validation; all three policy sites now use the generic bridge. The first two CPU attempts retain their failed test-authoring assumptions (no-op ABI preparation and a purported one-draw refusal that actually fit). The corrected [CPU3 result](../../../build/native-thin-line-batching-work-1/cpu-3/outcome.json) freshly compiles the final runtime, executes the corrected new contract and explicitly inherits seven exact-source passing contracts from CPU2. The new executable reports490,815 total checks, including10,697 retained triangle/fan checks. New CMake wiring is source-reviewed only; no full canonical build, source publication or thin-line GPU qualification is claimed at this checkpoint.

The small Native51 normal smoke is being prepared while its canonical sources remain exact. The ten-case fan/point/chunk-capture science corpus has independent original-draw expectations; its forced derivatives and hardware outcomes remain unexecuted. The reviewed thin-line fix will join a new Native52 source epoch before the larger affected GPU matrix. Closed activation records preserve3,359 files and save38,201 additional bytes; [closed thin-line CPU cleanup](../../../build/native-thin-line-batching-work-1/storage-cpu-1-3/result.json) preserves695 files and saves103,915,356 bytes (about99 MiB). Every retained file is byte-exact; no evidence or failure is deleted or moved. General smooth coverage, remaining scientific/host/platform work and original performance/release conditions remain open. Cybersecurity work remains excluded.

Implementation-first sprint8 source checkpoint: source publication commits exactly CMakeLists.txt, runtime.cpp, runtime_batch_strip.hpp and the new ordinary_line_runtime_contract.cpp after the independent CPU/source review. The three prior files are retained as actual publication backups; the [publication audit](../../../build/native-thin-line-publication-review-point-1/result.json) verifies the complete four-file transition and unchanged installed Native51. All historical CPU/native/GPU receipts retain their original source/artifact scopes. The Native52 metadata author closes exit0 (Root session98366, initialf16e41, terminalf51ac4); the [independent ownership review](../../../build/native52-ownership-review-point-1/result.json) verifies the complete manifest projection, 13 packet inventories, 14 source-context files, current sources/harness and the unchanged Native51 four. There are 82 retained owners, two prior-owner transfers and three changed/new owners. This admits ownership metadata only. The [source checkpoint](../../../build/implementation-sprint-8/source-progress.json) makes no Native52 compilation or GPU qualification claim.

The Native51 normal smoke completes with three passing cases (fan winding, point ordered revisions and the 65-endpoint diagnostic). Its independent saved review checks complete frames and all typed endpoint/raw canary bytes, direct worker identity, closure and released GPU ownership. The refused work1 transport remains preserved and unexecuted. [Closed smoke/publication/preparation cleanup](../../../build/closed-native51-smoke-publication-storage-root-1/result.json) preserves 779 files and saves 1,482,107 additional bytes. No evidence, failure or build output is deleted or moved. Matching Native52 build/activation and the larger affected GPU matrix remain pending.

Implementation-first sprint8 installed checkpoint: Native52/snapshot38 freeze,42-target/44-CTest build, activation and matching installed audit are complete and independently admitted. The actual build closes exit0 (Root session64367, initial0ca651, terminalbc9a1d) from the original nine-argument command. The saved full-build review checks4,933 inputs, the complete SDK213/origin/toolchain/cache closure and44 archived binaries. Activation session17145 starts81ccb0 and closes15ebe5, exit0, driver43332. The installed audit checks4,970 inputs and the exact four committed files and archived inputs. These close the freeze/build/activation items pending at the preceding source checkpoint.

The actual Native52 normal smoke closes exit0 (Root session92594, initialdb49eb, terminal1c87d2; driver47732, direct worker12556). Its fan winding, point ordered revisions and65-endpoint cases pass; the independently saved review retains complete original frames, typed endpoint fields, padded canaries, one dispatch/draw, query-disabled counters, real process closure and zero queues/pool after shutdown. The first saved reader fails before admission on a Python parser/local-variable name collision; its failed source/output remain preserved. The corrected saved reader consumes the same completed GPU run. Normal3 does not qualify the forced new routes or the full regression/failure/performance matrix.

Independent fixture review refuses work1 for unsupported buffer-backed stride-zero assumptions. Corrected work2 uses supported positive strides and explicit true constants; its90 CPU controls and independent reconstruction admit all13 source/primitive-row/78-frame proposals and capacity inequalities (12 forced obstacles, one whole-fit control) as PROPOSED_CPU_ORACLE_ONLY. Actual OriginalGL and Native52 observations remain pending. The three closed cleanup receipts preserve12,704 file observations and reclaim150,356,525 bytes (about143 MiB), with no evidence or failure deleted or moved. The [machine-readable checkpoint](../../../build/implementation-sprint-8/progress.json) records all actual scopes and remaining original completion conditions.

Implementation-first sprint9 reference checkpoint: the actual original-only thin-line capture closes exit0 in Root tool32a180, a single terminal return with no allocated session, driver35124 and direct worker43036. Independent saved review admits all13 cases,78 complete RGBA8 frames (239,616 bytes),926 direct GL_LINES transform-feedback endpoint rows (36 bytes each;33,336 bytes),463 primitives and every reflected type/offset/stride, count,144-byte per-case guard, original binding/draw mode/LAST/restart state, process/ABI/image/closure, provider/source pin and cleanup. Current Native52 source/four files remain exact. These references are frozen before candidate observation. No matching Native52 thin matrix result is claimed.

Sourcework1 remains refused for a Windows path-separator error in RECORD self-row metadata. Corrected work2 keeps worker/driver/guard bytes unchanged and truthfully records the self-listed unhashed RECORD row; its24 new metadata controls and221 exact inherited controls pass. An intermediate source-reader additive-field projection failure is retained. The first saved-outcome reader adds an unnecessary empty-stderr condition; its failure is preserved. Corrected map2 records the exact Qt DPI diagnostic and retains all scientific checks against the same completed capture. The [reference progress](../../../build/implementation-sprint-9/original-reference-progress.json) keeps remaining original completion conditions explicit.

Implementation-first sprint9 thin-line checkpoint: the isolated cap64 build completes all42 targets and44 CTests (7.62 seconds), with exact609 source leaves,4,130 harness inputs,44 archived binaries, both approved dependency-origin links and all10 logical origin identities independently admitted. The initial missing-link configuration is retained; a separate exact609-leaf build view supplies the links and redirects configuration and the final dependency script without editing the sealed derivative or installing it. The actual normal13 capture (Root51707, worker18388) and isolated forced13 capture (Root41832, worker45888) close exit0 with78 complete3072-byte frameplanes each. Independent joint review verifies all156 planes (479,232 bytes) against the same actual OriginalGL references. Normal raw156 minus78 presentation draws yields78 scene draws; forced raw564 minus78 presentation draws yields486 scene draws. All12 forced cases encode2–39 scene draws per plane; the small whole-fit control encodes1. The926 typed36-byte endpoint rows and transform-feedback guards remain OriginalGL reference evidence only. Clean queue/resource retirement, direct process closure, overlays, current source and installed Native52 four-file continuity are admitted.

The first normal launch stops before creating a worker because the runtime receipt omits the four artifact hashes it already validated; a separately source-reviewed metadata addendum rechecks every prior input and all four artifacts, preserving the original receipt and fields. Reader prefix and auxiliary review-seal failures remain retained; corrected receipts pass exact saved-command and completed-packet checks. No GPU outcome is replayed. Closed reference/build/GPU caches and overlays reclaim166,036,435 bytes across5,413 files through byte-preserving compression; no file is deleted or moved. The [actual checkpoint](../../../build/implementation-sprint-9/progress.json) retains every admission and remaining requirement. Broader fan/point/generated-line reference transport is under source/CPU preparation; general smooth coverage and original scientific/host/platform/performance/release completion remain open. Cybersecurity work remains excluded.

Implementation-first sprint9 broader reference checkpoint: the original-only capture closes Root51092, initial68eb45 (child_started and PASS) followed by empty terminal7c2bb6 exit0, driver30200 and directworker26012. Independent saved review admits10 cases,13 distinct version states,32 complete frames (98,304 bytes),748 assembled primitives,1,561 mixed-width typed rows,39,028 defined prefix bytes,40,196 prefix-plus-guard bytes and48 original draw calls (35 raster plus13 typed passes). Fan rows780x28, point rows195x4 and line rows586x28 close the exact typed total. The three native-loss phase labels are original version1 reference repeats; neither actual OpenGL loss nor Native candidate qualification is claimed. Source/profile review, independent reconstruction, all-observation process closure, original bindings/state, reflected formats, raw-before-validation guards, provider/source pins, current Native52 and clean resource/canvas closure are admitted without replay.

The matching combined forced-route derivative is staged with seven reversible runtime seams and a609-leaf source map. A missing four-artifact metadata propagation was caught before build; frozen work1 is preserved while corrected sourcework2 is prepared. Source-view, build and evidence outputs are external. The [broader reference checkpoint](../../../build/implementation-sprint-9/broad-reference-progress.json) records actual admissions and the next gates. This cleanup step reclaims5,281,047 bytes; sprint9 now reclaims171,317,482 bytes across6,283 file observations, preserving every name and byte. Normal/forced broader Native qualification, failure/retry/loss/retirement, general smooth and the original scientific/host/platform/performance/release conditions remain open. Cybersecurity work is excluded.


Implementation-first sprint 10 combined-route checkpoint: the isolated fan96/point96-layout20/generated-line2064 build passes all 42 targets and 44 CTests (7.01 seconds). Independent saved review admits the complete 609-leaf variant, 4,130 harness inputs, SDK/origins/toolchain and 44 archived binaries. The derivative stays outside the installed Native52 files. The [joint normal and forced GPU review](../../../build/evidence/native52-broad-gpu-outcome-review-map-2/result.json) independently admits both completed runs: normal Root 48635 (3be3c9 to b49a28, driver 45556, worker 35480) and forced Root 2965 (5cbd0b to 918a4b, driver 30988, worker 24500), all exit0. All64 complete frames (196,608 bytes) match the same actual OriginalGL references. Each route has 13 captures and 849 logical 32-byte endpoint rows; the first 28 defined bytes per row match original-derived fields. Every physical guard/part passes, with 53,456 normal and 181,632 forced raw bytes. Observed presentation subtraction gives 35 normal and 499 forced scene draws, with 32 presentation draws per route. Each run observes three requested ForceLoss API recoveries, generation/loss-count and device-grant joins, resident input/build zeros, pending-update snapshot survival, once-only native retirement, released capture charges and empty final queues/pools. These are requested API recovery observations; fresh native padding, shader invocation counts and uncontrolled hardware faults are not qualified.

The first broader normal attempt is retained as failed: its assertion omitted the queued Clear snapshot from pending_draws. Source inspection and all 10 saved cold counter snapshots establish one Clear plus the original DRAW count while semantic/native encoding counters remain unchanged before submission. Fresh adapter 2 passes 382 source controls and 113 saved-snapshot regressions before independent source admission and the successful reruns. No renderer or isolated binary rebuild was needed for this adapter correction. The [machine-readable checkpoint](../../../build/implementation-sprint-10/progress.json) records all actual rows, failure history and remaining requirements. Closed build caches, overlays, captures and transport records reclaim 173,441,234 bytes across 5,529 files this sprint through byte-preserving compression. Sprints 9 and 10 together reclaim 344,758,716 bytes across 11,812 file observations; no file is deleted or moved. Late-part guard/map/retry and cancellation/retirement failure qualification, general smooth coverage, matching full scientific regressions and the original host/platform/performance/release conditions remain open. The next isolated diagnostic-fault source is under independent review; its first recipe's stale build/XML paths were caught before execution and preserved while fresh source 2 corrects them. Cybersecurity work remains excluded.


Implementation-first sprint 11 diagnostic checkpoint: the isolated default-off chunk-fault derivative passes all 42 build targets and 44 CTests (6.79 seconds). Independent saved-build review admits all 609 source leaves with four substitutions, SDK213/origins/toolchain, all 48 generated projects and 44 archived binaries. The derivative remains outside the installed Native52 files.

The [independent joint saved review](../../../build/evidence/native52-chunk-fault-outcome-review-map-2/result.json) admits all four completed outcomes. The four serialized Root GPU jobs close exit0: baseline tool750f80 (driver47412, worker47908), guard-copy toolb4f1e3 (driver21708, worker46472), destroyed-map tool1421c0 (driver35816, worker25136) and deferred-once tool940c3d (driver15584, worker35568). Each saves one complete3072-byte frame equal to the same admitted actual OriginalGL strip65 v0 reference. The baseline returns65 logical32-byte rows and4128 raw bytes. The late guard copy changes exactly four raw bytes at offset2096 and yields padding_error with no logical data. Destroying the second readback before real MapAsync yields map_error with no logical data and the actual2064-byte first-part raw prefix; the real map callback status is3 and the completed error-scope callback reports Validation2. These are controlled diagnostic faults, not spontaneous hardware faults.

The first deferred collection returns an empty list while retaining the same capture, charge and Future, with observed raw/logical prefix sizes2064/2048. Retry returns the actual2080/4128-byte arrays exactly equal to the successful baseline; repeated collection is empty. Every job keeps the same generation/loss count, two evaluator dispatches, two scene draws, one presentation draw and one render submission. Every native Ticket retires successfully exactly once, including the two diagnostic failures. Collection releases capture charges and shutdown leaves queues and resource pools empty.

Saved-reader corrections preserve their failed predecessors: literal MSVC path-key binding, CMake's two legitimate Release compiler definition nodes, and the historical installed-audit three-field schema. No completed GPU job or build is replayed for those reader corrections. The first fault source recipe's stale build/XML paths also remain retained. Capture cancellation/loss/shutdown schedules, general smooth coverage, matching full scientific regression and original host/platform/performance/release requirements remain open. Cybersecurity work remains excluded.

The [machine-readable checkpoint](../../../build/implementation-sprint-11/progress.json) records all actual source/build/runtime/job admissions and preserved refusals. Closed build and GPU assets reclaim170,308,815 bytes across3,886 files through byte-preserving compression; sprints9–11 together reclaim515,067,531 bytes across15,698 file observations. No evidence or failure is deleted or moved.


Implementation-first sprint 12 lifecycle checkpoint: [independent saved review](../../../build/evidence/native52-capture-cancellation-outcome-review-map-1/result.json) admits all seven serialized existing-API schedules on the isolated Native52 diagnostic derivative. Pending destroy returns cancelled, pending abort returns failed, and pending loss returns device_lost without a native Ticket or retirement. Submitted open-paint abort returns failed and submitted destroy returns cancelled while each native Ticket retires successfully once. Submitted loss actually reaches the loss-before-retirement path and retires exactly one failed native Ticket. The retained-map-Future shutdown returns cancelled with no logical data and the exact2,064-byte baseline first-part raw prefix. It does not recreate a device or render a resumed frame.

All seven terminal collections release the observed capture charge once, repeated collection is empty, and final shutdown leaves queues and resource pools empty. The reader independently checks passive pending/submitted/terminal boundaries, actual map state and raw bytes, charge/Ticket joins, loss classification, direct worker identity, full Root closure, input maps and installed Native52 continuity. The selector's missing-argument failure and a wrong-output-prefix invocation are retained separately; the corrected external selector preserves the admitted reader and runs the complete actual shared prefix before main. No GPU result is replayed.

The [machine-readable checkpoint](../../../build/implementation-sprint-12/progress.json) records the final Source/actual-input/control/observation/result roles. Closed lifecycle outputs reclaim43,249,485 bytes across4,008 files, preserving every name and byte. Sprints9–12 together reclaim558,317,016 bytes across19,706 file observations. No evidence is deleted or moved.

The matching Native52 original-regression attempt completes all126 tests: ordinary17 passes; affected109 reports108 passing tests and one diagnostic wording failure. The unchanged public test expects active inputs in the point attribute-limit error, while the new partition helper says active fields. The refusal condition, exception type and DRAW/object context are correct. The failed packet remains failed; no complete126 admission is claimed. A two-file compatibility fix and strengthened focused CPU diagnostic check are being staged for a fresh Native53 source/build epoch. Integer256/text24, general smooth and the original scientific/host/platform/performance/release requirements remain open. Cybersecurity work remains excluded.


## Sprint13: published point-limit diagnostic compatibility

The [two-file publication](../../../build/native-point-diagnostic-publication-root-1/result.json) and [independent saved audit](../../../build/native-point-diagnostic-publication-review-point-1/result.json) pass. The point partition helper now reports `active user inputs exceed granted attribute limit`, restoring the original pytest diagnostic contract. The existing C++ over-grant test now requires the exact `std::runtime_error` text; the rejection threshold, original Python tests and all other source/harness bytes remain unchanged. The [focused CPU outcome](../../../build/native-point-diagnostic-compat-cpu-root-1/result.json) and [independent admission](../../../build/native-point-diagnostic-compat-cpu-review-native-1/result.json) pass one source-matched CTest under MSVC with warnings as errors. Installed Native52 remains unchanged. Its original126 result stays125 passed/1 failed until a fresh matching Native53 run succeeds.

Native53/w39 ownership, full freeze/build, activation, installed audit and matching regressions remain next. The [checkpoint](../../../build/implementation-sprint-13/publication-progress.json) retains all exact publication/CPU/failed-regression identities. Closed CPU/regression assets were compressed with every filename and byte preserved, reclaiming1,292,955 bytes across982 files. General smooth, scientific/host/platform/performance/release conditions remain open; cybersecurity work stays excluded.

### 2026-10-18: Native53 matching regression, integer and Text qualification admitted

The installed Native53/w39 build now has independently admitted matching original126, integer and Text results. The 17-test and 109-test groups both pass, including 769 independently decoded arrays, 299 exact saved pairs, actual process identity and explicit cleanup. Integer qualification combines 128 retained accepted OriginalGL frames with 128 newly executed Dawn53 frames; all 256 full RGBA frames, 70 zero-work resident phases, seven losses and logical cleanup are admitted. Text qualification admits all 24 complete frames across 12 cases, with exact atlas/geometry/glyph witnesses, typed uniform/DPI checks, GC boundaries, 17-counter resident reuse and explicit cleanup. All producer and saved-reader sessions are closed. The [sealed checkpoint](../../../build/native53-matching-qualification-checkpoint-root-1/progress.json) was produced after checking all five complete build/installation/device admission packets and rehashing the current installed native4; its seal preserves the exact matching scopes. The failed Native52 point-diagnostic run and superseded reader/source failures remain unchanged.

Housekeeping compressed 4,498 closed Native53 build files and reclaimed 143,115,195 bytes. A final pass over the 1,411 new result files confirmed their already-compressed state with zero additional savings. Both passes preserve every name, size and byte, with no deletions or moves; installed Native53 hashes are unchanged. The continuation total is 366,158,126 bytes reclaimed, with 710,916,842 bytes across sprints9–13.

The next proposed packet is a fresh Native53 cap64 thin-line derivative based on `build/native52-thin-line-forced-source-work-1`, preserving cap behavior while rebinding the two diagnostic context changes to Native53/w39 and requiring new isolated build/artifacts and 156-frame qualification. It has not started. Broader64, four chunk-fault and seven cancellation successors also need matching Native53 variant/baseline evidence. Shared integer53 identity supplies formal metadata, not those variant or baseline admissions. General smooth, scientific/host/platform, fixed-quality performance and release requirements remain open; cybersecurity remains excluded.

### Sprint14: Native53 cap64 thin-line preparation started

The previously proposed cap64 successor is now in progress. Its immutable source packet, view-based build tools and strict saved-build reader, and thin156 transport/result reader are being adapted in separate work folders. The parent remains the sealed Native53/w39 matching126/integer/Text checkpoint. Cap64 behavior, the 13 accepted OriginalGL cases and 78 reference frames, image tolerances, and the 42-target/44-CTest build scope stay fixed. The shared integer53 identity supplies current formal metadata; the new variant still requires its own source, source-view, build, four-artifact and runtime admissions. No new C++ compile, native build or GPU job has run. The [source-work checkpoint](../../../build/implementation-sprint-14/source-progress.json) records ownership and the current filesystem state.

A [closed Native52 cap64 cache/archive pass](../../../build/closed-native52-thin-cap64-storage-root-1/result.json) verified 930 files totaling 334,504,312 logical bytes. They were already compressed, so no additional bytes were reclaimed. Every name, size and byte and the current installed Native53 hashes remain unchanged; nothing was deleted or moved. All broader final-artifact, smooth/scientific, host/platform, performance and release gaps remain open. Cybersecurity remains excluded.

The [current successor](../../../build/implementation-sprint-14/forced-started-progress.json) supersedes the source-only snapshot above. Cap64 Source and build-tool Source have passed independent review; Root has closed the current build-input admission and sole source-view materialization. Actual isolated build session 53233 closes exit0 after all 42 targets and 44 CTests pass (6.90 seconds), and the [strict independent saved-build review](../../../build/evidence/native53-thin-line-forced-build-review-map-1/result.json) admits all source, harness, toolchain, project and binary evidence. All four variant artifacts remain external, and installed Native53 is unchanged. Runtime metadata, thin156 execution Source and its saved-reader Source are admitted. The normal GPU route closes exit0 with 13 cases and 78 complete frames passed, explicit cleanup and current installed hashes unchanged. The forced cap64 route is running; joint saved outcome admission remains pending.

The [closed Native53 cap64 cache/archive pass](../../../build/closed-native53-thin-cap64-storage-root-1/result.json) preserves 930 files totaling 334,521,038 logical bytes and reclaims 143,169,120 bytes. Every name, size and byte remains exact; nothing is deleted or moved.

The [joint independent saved review](../../../build/evidence/native53-thin-line-gpu-outcome-review-map-1/result.json) now admits both actual Native53 routes: all 156 complete frames (479,232 bytes) match the same 78 accepted OriginalGL reference frames. Normal and forced runs close exit0 with 78 and 486 observed scene draws respectively, presentation subtracted, zero ordinary endpoint-compute counters, actual queue retirement and complete logical cleanup. The 926 typed36-byte rows and TF guards belong to the OriginalGL reference only; no native endpoint or canary capture is claimed. All actual Source, metadata, build, capture and saved-reader sessions are closed. The [sealed thin checkpoint](../../../build/native53-thin-qualification-checkpoint-root-1/progress.json) checks the parent checkpoint, complete new build/runtime/independent GPU admission packets and current installed native4 without replay.

The [closed capture/overlay pass](../../../build/closed-native53-thin-gpu-storage-root-1/result.json) preserves another 2,902 files and reclaims 12,290,548 bytes. Sprint14 reclaims 155,459,668 bytes across 3,832 disjoint closed files; sprints9–14 total 866,376,510 bytes reclaimed. No file is deleted or moved. The first default-OFF fault Source stays unexecuted after its peer found missing/conflicting physical artifact-path checks; that refusal is preserved for a fresh corrected successor. Matching broader, fault and cancellation outcomes, general smooth, scientific/host/platform, performance and release requirements remain open. Cybersecurity remains excluded.

### Sprint15: matching Native53 broader64 preparation

The [sealed broader checkpoint](../../../build/native53-broad-qualification-checkpoint-root-1/progress.json) now binds the independently admitted combined fan96/point96-layout20/generated-line2064 Source, build tools, full isolated42-target/44-CTest build (6.84 seconds), runtime metadata and new normal/forced captures. The [independent saved GPU review](../../../build/evidence/native53-broad-gpu-outcome-review-map-1/result.json) admits all64 complete frames (196,608 bytes), exact reference equality,13 native endpoint captures and849 logical32-byte rows per route. The first28 defined bytes per row match actual OriginalGL-derived fields; all physical guards and chunk descriptors pass. Normal/forced scene draws are35/499 after subtracting32 presentations per route. Each route observes three requested ForceLoss API recoveries, stable device grants, zero-work resident phases, pending snapshot survival and once-only native retirement, with clean charges/queues/pools. These are requested API recoveries; padding, shader invocation counts and uncontrolled hardware faults are not claimed. The1561 mixed typed rows belong to the OriginalGL reference. Every producer and saved-review session is closed; installed53 remains unchanged.

Closed build/cache/archive and GPU/overlay passes preserve3,826 files and reclaim155,436,628 bytes this sprint. Every name, size and byte remains exact; nothing is deleted or moved. Sprints9–15 total1,021,813,138 bytes reclaimed. Remaining fault/cancellation, general smooth/scientific, host/platform, performance and release requirements remain open.

### Sprint16: matching Native53 diagnostic fault qualification admitted

The [sealed fault checkpoint](../../../build/native53-fault-qualification-checkpoint-root-2/progress.json) binds Source2, its independently admitted tools, the new isolated42-target/44-CTest build (6.99 seconds), actual four artifacts, all runtime metadata and the [independent four-job saved review](../../../build/evidence/native53-chunk-fault-outcome-review-map-1/result.json). All four exact complete frames pass. The fresh baseline and deferred retry each return65 logical32-byte rows and4128 raw bytes. The late guard changes exactly one physical word and returns padding_error without logical data. Destroying the late buffer produces the actual non-success MapAsync callback and Validation scope, with2064 raw prefix bytes and no logical data. The first injected deferral returns no arrays; retry matches the exact fresh baseline. Collection/retry adds no drawing, dispatch or submission. All four successful encoding Tickets retire once, all direct workers close, cleanup passes and installed53 stays unchanged. These are controlled diagnostic cases; hardware faults, fresh padding ABI and new scientific coverage are not claimed.

The isolated diagnostic flag defaults OFF; only its recipe enables it, producing exactly two Release macro entries on _dawn (ClCompile and ResourceCompile). The initial Source1 artifact-path refusal remains preserved and unexecuted. The first final checkpoint's baseline-started metadata typo is preserved; the current successor correctly records both started and closed.

Closed cache/archive and capture/overlay compression preserves3217 disjoint files and reclaims168029239 bytes. Every filename, size and byte remains exact; no deletion or move occurs. Sprints9–16 total1189842377 bytes reclaimed. All actual fault producers and saved readers are closed; cybersecurity remains excluded.

### Sprint17: matching Native53 cancellation qualification admitted

The [sealed cancellation checkpoint](../../../build/native53-cancellation-qualification-checkpoint-root-1/progress.json) binds the fresh Native53 fault baseline and matrix, current four artifacts, corrected ActorSource2 and its independently admitted saved reader. All seven metadata producers and all seven GPU schedules close exit 0. The [joint independent saved review](../../../build/evidence/native53-capture-cancellation-outcome-review-map-1/result.json) checks 40,122 inputs with no findings, after 66 selected closure checks and 57 shared-prefix checks.

Pending destroy, abort and loss return cancelled, failed and device_lost without native Tickets. Submitted abort and destroy and retained-map shutdown each retire their native Ticket successfully once; submitted loss actually records one failed retirement because loss is processed first. Capture charges remain until exactly one terminal consumption, repeat collections are empty and collection adds no rendering, compute, submission, retirement or fresh wait. Shutdown returns only the 2,064-byte first-part baseline raw evidence. No logical data, resumed frame, device recreation, unfinished callback or hardware-fault claim is made. All direct processes close, cleanup passes and installed Native53 stays unchanged. Source1's checker-schema refusal remains preserved; Source2 changes only the strict driver-local current53 projection.

Closed cancellation capture/overlay compression preserves 3,938 disjoint files and reclaims 43,210,454 bytes. Combined fault/cancellation cleanup reclaims 211,239,693 bytes; sprints9–17 total 1,233,052,831 bytes. Every filename, size and byte remains exact; no deletion or move occurs. All matching Native53 thin, broader, fault and cancellation jobs and their saved readers are closed.

The [uploaded-bit CPU replay](../../../build/smooth-uploaded-bit-replay-work-1/findings.md) implements exact uploaded float32 endpoints and observed viewport dimensions for all 24 admitted calibration cases, including rotations. Its 384 contract controls pass. All 32 existing global recipes and 768 complete predictions are frozen and sealed before image reads. The [independent review](../../../build/smooth-uploaded-bit-replay-review-native-1/result.json) passes 3,720 controls and reconciles all 2,359,296 RGBA bytes and the complete signed difference tensor. The best recipes still miss 16 pixels, only alpha 164 versus 173. This remains calibration-only; production smooth support is unqualified. The nine frozen predictions and eight reserved holdouts remain unopened. A justified global coverage mechanism and unseen qualification are still required.

### Sprint18: public volume mutation fix published

The [sealed volume checkpoint](../../../build/volume-redraw-checkpoint-root-1/progress.json) binds the exact two-file publication, original backups, reviewed candidate, canonical CPU verification and [independent saved publication audit](../../../build/volume-redraw-publication-review-native-1/result.json). VolumeVisual.set_data now requests redraw after all successful data/state updates. The clim reupload branch returns after that notification, avoiding a duplicate event. A successful geometry build clears its dirty flag; failed creation preserves the flag for retry.

Real-class CPU tests reproduce five regressions in the original code (four pass, five expected failures). The candidate passes all nine tests. After publication, [canonical pytest verification](../../../build/evidence/volume-redraw-cpu-published-root-1/result.json) again passes all nine, with 52 other tests deselected. Coverage includes ready-state events, both clim paths, gamma, same-shape geometry reuse, changed-shape rebuild once, failed geometry retry and invalid/failed data uploads. Tests exercise actual VolumeVisual objects, events, _prepare_draw and queued buffer operations without rendering a canvas. The independent audit verifies the exact current source and tests, before copies, JUnit/literal results and physical installed Native53 four.

Production changes are three added statements. New test imports were moved into the existing import block while preserving all definition bodies and CRLF. The failed initial LF staging observation remains preserved; it wrote no canonical files. Current production volume.py is d66661770fcee25473d3aea976e78e884d622e74a747e2eb9ed70f2a45007186 and test_volume.py is 88adf0cd226e28bcdc651a89f8528a77a1bd325d651b347a3184a6f299a2043b.

This Python publication follows the Native53/w39 qualification checkpoint. Native binaries stay byte-identical, and prior GPU results retain their original frozen source contexts. Future whole-source execution needs a fresh source identity; updated volume GPU/scientific and actual host interaction/recovery/teardown qualification is pending. RGB/RGBA volume acceptance already exists and requires qualification rather than another renderer patch.

Closed-asset cleanup this continuation reclaimed 522,135,989 bytes across the thin, broader, fault and cancellation batches. All artifact names, sizes and bytes remain exact, with no deletions or moves. The small volume work folders contain no pyc, temporary or editor-backup files; original backups and failed observations remain available.

General smooth still needs a justified global coverage mechanism and genuinely unseen qualification; the best admitted calibration replay retains 16 alpha-pixel mismatches. Remaining original scientific/host/platform behavior, all 66 fixed-quality performance scenarios and CPython3.10–3.14 release artifacts are open. Cybersecurity remains excluded.

### Sprint19: Image resize and view initialization fix published

The [sealed Image checkpoint](../../../build/image-resize-checkpoint-root-1/progress.json) binds the reviewed two-file publication, original backups, canonical CPU verification and [independent saved publication audit](../../../build/image-resize-publication-review-native-1/result.json). A size-changing ImageVisual.set_data now marks interpolation state dirty. Successful geometry preparation refreshes the shared image_size uniform, including nearest/linear paths and existing second views. Transform preparation tolerates the provisional method state during public view construction; the normal method update completes initialization.

Real-class CPU tests reproduce seven failures in the original implementation, with two passes. The revised candidate and [published canonical tests](../../../build/evidence/image-resize-cpu-published-root-1/result.json) each pass all nine tests; canonical pytest deselects 220 other tests. Coverage includes filtered lookup sizes, nearest/linear uniforms, real prepare calls, an existing second view, repeated pending resizes, same-size reuse, failed geometry retry, interpolation aliases and invalid replacement state. The first candidate's two failures remain preserved: one test incorrectly expected earlier dimensional validation, while the other exposed the public view-initialization bug now fixed. No upstream API restriction was added for that test assumption.

Production changes add two statements and replace one method-state read. Current image.py is 8a208f4b3f66f4bc772affab253c3dff676846b1ffe592ba5a3215acff094ebe and test_image.py is 5a4e40e0502fc4a3fbe76ac11dc7772b734bce26966b2321c552f71012975f1c. Native53 binaries remain byte-identical. This checkpoint proves CPU setup, state and queued operations; Image/Volume pixels, actual host behavior and GPU work still need matching qualification.

The [fresh Python-layer checkpoint](../../../build/python-layer-checkpoint-root-1/progress.json) now binds actual staging and metadata, both closed exit 0, and their [independent saved-output audit](../../../build/native53-python-source-identity-outcome-review-native-1/result.json). The stage retains all 521 package members, including 147 resources: 517 exact parent members and four independently audited replacements. The current identity preserves the other 605 source identities, all 4,130 harness identities, 85 native owners and the separate native four. No C++ rebuild was needed or claimed. The shared identity consumer passes the independent saved audit; earlier GPU passes do not transfer to the new Python bytes.

The [independently reviewed ten-case fixture](../../../build/visual-mutation-fixture-review-line-1/result.json) freezes Image nearest/linear/cubic/custom across subdivide/impostor and Volume same/changed shape mutations. Its data, operations, camera and exact full-frame criteria are fixed before any capture. Ten fresh upstream final-state reference frames and twenty candidate final/resident frames remain unexecuted. Public Image.view pixel parity stays open because unchanged upstream construction fails; CPU view tests are admitted separately. An event-timing clarification and a partial UTF-8 staging failure remain preserved in earlier unexecuted fixture packets. The rendering worker is being prepared separately.

The new work folders contain no pyc, temporary or editor-backup files; original backups and failed observations remain available. Cybersecurity remains excluded.

### Sprint20: current Image/Volume rendering preparation

The ten-case fixture and corrected capture Source2 pass independent review. The process launcher also passes independent review and 26 synthetic controls covering normal exit, nonzero exit, timeout, bounded reap, exact raw output, environment changes and fresh-journal refusal. Actual reference inputs bind the unchanged upstream package and real CPython3.12.8 interpreter; candidate inputs bind the new Python stage and installed Native53 four.

The [first actual reference attempt](../../../build/visual-mutation-reference-process-root-1/process.json) closes exit 1 and is fully reaped, with no timeout. It stops before provider/native imports or GPU work: the worker passes absolute fixture tracking paths into the shared identity guard, which requires workspace-relative keys. The [raw startup failure](../../../build/evidence/visual-mutation-reference-root-1/result.json) remains preserved. Independently reviewed worker Source3 isolates identity admission and merges physical identities with conflict checks. Its actual stdlib integration regression uses the same saved identity and all eight absolute fixture pins; normalized collisions refuse atomically. Fixture data, camera, operations and pixel criteria remain unchanged.

The [second reference attempt](../../../build/visual-mutation-reference-process-root-2/process.json) reaches the unchanged OpenGL provider and captures five fresh frames. The nearest and linear cases pass for both methods; cubic/subdivide fails a frozen analytic landmark check. The [raw five-frame result](../../../build/evidence/visual-mutation-reference-root-2/result.json) stays failed and unadmitted. The direct process closes exit 1, is reaped without timeout, and reports clean canvas cleanup and unchanged installed Native53. Only upstream SDF is imported as a native module; the candidate renderer is not loaded. No candidate job has run. A bounded source/math review of the landmark assumption is underway without opening frame bytes or fitting tolerances. Canonical Image/Volume and installed native hashes remain unchanged.

That source review establishes that the upstream packed RGBA8 filter does not preserve fractional DC values exactly; custom filtering also omits out-of-bounds taps without renormalization. [Fresh fixture4](../../../build/visual-mutation-fixture-review-line-2/result.json) uses new asymmetric binary Image data and landmarks derived from one complete-support rule, with exact full-frame comparison and the existing tolerance retained. Source coefficient input analysis proves endpoint clamp stability. Volume data, kernel, settings and criteria stay exact. No failed output pixels were opened to choose these changes.

The [third reference attempt](../../../build/visual-mutation-reference-process-root-3/process.json) captures six passing nearest/linear/cubic frames, then custom/subdivide encounters GL1282 at framebuffer creation before its texture or shader commands execute. The complete packet remains failed and unadmitted. The [custom-only diagnostic](../../../build/evidence/visual-mutation-custom-context-probe-root-1/result.json) subsequently completes that same public custom route in a fresh context. Its [independent metadata/closure review](../../../build/visual-mutation-custom-context-probe-outcome-review-native-2/result.json) verifies 25 stable WGL/context observations, zero recorded errors and a cleanly reaped process. This is permanently diagnostic-only, with reference eligibility and qualification false; it does not establish the earlier error's cause.

Source inspection identifies a missing finish-before-close boundary in the runner: SceneCanvas.render flushes before readback but queues FBO pop/deletion afterward, while upstream Canvas.__exit__ explicitly finishes its current context before closing. A fresh worker successor is adding that public cleanup boundary while retaining trace recording and failing on cleanup errors. All shader, data and rendering code remain unchanged. The next full reference run and the candidate comparison are pending.

Worker Source5 passes [independent review](../../../build/visual-mutation-capture-review-native-5-2/result.json), including 14 cleanup failure-path controls. The [fourth reference attempt](../../../build/visual-mutation-reference-process-root-4/process.json) closes exit 1 without timeout and is fully reaped. Seven Image cases pass, including custom/subdivide; custom/impostor captures its frame and fails the frozen background landmark. All eight canvases finish with their contexts current and close successfully; cleanup errors are empty and installed Native53 remains unchanged. This run does not establish the cause of the previous GL error. Volume cases and the candidate remain unexecuted.

Independent source review identifies a separate coverage assumption: upstream custom filtering omits whole-coordinate discard, so its full-viewport impostor shades exterior fragments instead of preserving the colored canvas background. The fixture's proof covered only the four interior landmarks. A fresh successor is binding the custom/impostor exterior landmark to source-derived opaque black, while preserving the colored background input, all inner criteria, exact full-frame equality, and every other case. Failed frame pixels have not been inspected to choose this correction.

[Fixture5's independent review](../../../build/visual-mutation-fixture-review-line-3/result.json) passes 34 checks and twelve stdlib tests. One complete-exterior-support rule moves the exterior point to row0/column2 for all eight Image cases. Its source y coordinate is -23/20, so every custom-filter tap is out of bounds; custom/impostor therefore returns opaque black through the unchanged Grays map. The former row2 point retains one valid tap and cannot justify that prediction. All other methods preserve the original colored background at the new point. Only custom/impostor has an explicit expected-color override; the four interior criteria and all uploaded bytes, Volume settings, tolerances and exact frame equality remain unchanged. Worker integration and fresh execution are pending.

The [closed reference storage check](../../../build/visual-mutation-closed-assets-cleanup-root-1/result.json) verifies all 516 files in the four closed packets retain their exact bytes and names. They are already compressed, so additional savings are zero. No file is deleted or moved. Bounded scans of the new work folders find no bytecode, temporary or editor-backup files.

Worker6's [independent source review](../../../build/visual-mutation-capture-review-native-6/result.json) passes 15 source checks and eleven independent tests. Its only rendering-path change selects the predeclared case criteria; cleanup and complete-frame equality are exact Source5. The [fifth reference attempt](../../../build/visual-mutation-reference-process-root-5/process.json) closes exit 0 without timeout. All [ten fresh final-state cases](../../../build/evidence/visual-mutation-reference-root-5/result.json) pass: eight Image cases and both same/changed-shape Volume cases. All ten current-context finishes and canvas closures complete, cleanup errors are empty, and installed Native53 remains unchanged. Independent saved reference admission and the first candidate comparison are pending.

The [independent reference admission](../../../build/visual-mutation-reference-review-native-1/result.json) now verifies all 303 packet members, ten complete RGBA frames and 48 frozen landmarks, plus unchanged source/package/module identities and actual process closure. The [first candidate process](../../../build/visual-mutation-candidate-process-root-1/process.json) subsequently closes exit 0 without timeout. All [ten candidate cases](../../../build/evidence/visual-mutation-candidate-root-1/result.json) pass: twenty final/resident complete frames match those fresh references exactly; ten warm frames are diagnostic only. The observed twelve committed-data update events, expected geometry/lookup/upload preparation counts and zero resident Python preparation counts pass. All canvases finish and close, native shutdown reports released work, and installed Native53 remains unchanged. Independent joint saved-output admission is pending. These observations do not qualify automatic redraw, public Image.view pixels, actual host behavior, zero native GPU work or performance.

The [independent joint outcome admission](../../../build/visual-mutation-outcome-review-native-3/result.json) now passes 891 checks: all twenty complete final/resident frames match exactly (737,280 RGBA bytes, zero differences), all 96 candidate landmarks and twelve ready events pass, and preparation/state/raw resident GLIR, 262 loaded module origins, 521 staged package members, installed Native53 four, literal process closure and native shutdown are verified. Ten warm frames remain diagnostic only. Two reviewer-only refusals remain preserved: a structured NumPy void-record dtype was missing from the reviewer's byte-size parser, and it incorrectly required unused impostor subdivision buffers to flush as GPU uploads. The corrected review distinguishes Python calls from the buffers actually drawn; producer and canonical source remain unchanged.

The [scoped final checkpoint](../../../build/visual-mutation-checkpoint-root-1/progress.json), produced by a closed exit-0 process, binds the actual Source6/fixture5, both independent outcome admissions, both actual process records, current Python identity, eighteen passing CPU tests and unchanged canonical/native hashes. This closes the ten-case captured Image resize and Volume mutation preparation/event/parity gap. It does not transfer historical GPU scopes, promote previous failures or complete the original thirteen-step plan.

The next bounded host case is a public napari cubic Image layer resize from2x3 to6x8 on the same cached visual node, observing scheduled Qt/native drawing before any forced draw or screenshot. Existing host fixtures force draws, and their historical installed wheels are not the current source identity. Fresh current-stage/native bindings and a fresh unchanged-upstream host reference are required. Volume notification needs a separate direct Qt public set_data-only case because napari and Glue add their own update calls. Source preparation for the napari case is underway; no new host execution or qualification is claimed.

### Sprint21: automatic redraw preparation

Two narrow runners are under source preparation: one napari cubic Image layer resize on the same visual node, and direct Qt Volume same/changed-shape mutations. The latter preserves the admitted reference5 data, camera and 96-square offscreen export; it observes two committed-data events and one coalesced backend update request before public event processing. A reserved native measured owner must return a successful, closed and retired qt_paint receipt before any later explicit export. Draw callbacks alone precede final presentation and do not satisfy that boundary. No swapchain pixel or performance claim is made.

The [actual Qt runtime specification](../../../build/volume-qt-runtime-inputs-root-1/environment.json) pins the existing oracle NumPy/PyQt6 dependencies, including QtOpenGL, real CPython and current staged Qt backend without importing a provider. Volume Source1 passes its CPU controls and [37 independent contract/timing checks](../../../build/volume-qt-contract-review-root-1/result.json), but the [worker review refuses it](../../../build/volume-qt-worker-review-native-1/result.json): failure after a successful backend import can leave provider_imported falsely reported as false. That frozen packet remains unexecuted. A narrow fresh successor will recompute actual provider presence in finally; the timing/science criteria stay unchanged. Fresh reviews are required before the first Qt job.

Napari startup baselines and one-case camera/landmark criteria are staged separately. A fresh unchanged-upstream host reference is required because its camera and host scene differ from the direct Image fixtures. The worker will observe scheduled drawing before explicit export and preserve actual Qt callback errors, same-node identity and prepared final dimensions. No new host or automatic-redraw capture has run yet. Bounded scans continue to find no bytecode, temporary or editor-backup junk in the new work folders.

Fresh Volume Source2 fixes only the reporting boundary and passes ten new fake-module regressions. Its [independent worker/identity review](../../../build/volume-qt-worker-review-native-2/result.json) and [fresh timing delta review](../../../build/volume-qt-contract-review-root-2/result.json) are clear; the finished Source gate consumes both actual sealed peers successfully. The [first actual Qt process](../../../build/visual-mutation-volume-qt-process-root-1/process.json) closes exit 0 without timeout and is fully reaped. Both [same/changed-shape Volume cases](../../../build/evidence/volume-qt-redraw-root-1/result.json) pass: two ready events and one coalesced backend request per case precede event processing; successful native qt_paint tokens4/7 close and retire before separate exports. Each native receipt records two submissions and two presents. Both complete exports match admitted reference5 exactly, all callbacks and cleanup pass, and Native53 remains unchanged. Submission-time counter snapshots are separate from the later zero-pending-work probe. Independent saved-outcome admission is pending; swapchain pixels, performance and general host behavior are not qualified by these results.

Napari Source1 is now frozen with eight passing stdlib tests. Independent fixture/timing and worker/origin reviews are running. The [mode environment inputs](../../../build/image-resize-napari-runtime-inputs-root-1/reference-environment.json) are prepared without imports; the first fresh host reference and candidate jobs remain unexecuted.

The [final independent Volume saved admission](../../../build/volume-qt-redraw-outcome-review-point-3/result.json) now binds both real paint owners, four ready events, two coalesced requests, prepared final state, two complete exact exports and all eight landmarks, current package/source/native/module identities, actual process closure and cleanup. Its metadata successor corrects a review-only physical stderr byte count while retaining all original scientific checks and failed review history. The [scoped Volume Qt checkpoint](../../../build/volume-qt-redraw-checkpoint-root-1/progress.json) closes exit 0 and binds that admission, both Source2 peers, the actual raw/process packets and the earlier captured-parity checkpoint. No swapchain pixel, performance or general host admission is inferred.

Napari Source1 subsequently passes both independent source reviews. The [first actual upstream host-reference process](../../../build/visual-mutation-napari-reference-process-root-1/process.json) closes exit 1 without timeout and is fully reaped. Its [saved startup result](../../../build/evidence/image-resize-napari-reference-root-1/result.json) fails on a missing sys.modules['qtpy'] entry: the bootstrap checks origins before lazy host startup has imported that required dependency. The actual Qt provider and upstream SDF are recorded as loaded; GPU attempt/use and candidate renderer are false, no frame is produced, cleanup passes and Native53 remains unchanged. A narrow fresh successor will explicitly import pinned required dependencies before checking their origins, preserving every fixture, camera, tolerance and automatic-draw condition. The failed packet stays unadmitted; no candidate host run has occurred.

Napari Source2 explicitly imports all nine pinned dependencies before validating all nine origins. Its [worker/identity delta review](../../../build/image-resize-napari-redraw-source-review-native-2/result.json) and [fixture/timing delta review](../../../build/image-resize-napari-contract-review-line-2/result.json) pass, together with all thirteen retained/new stdlib tests. The [second upstream host-reference process](../../../build/visual-mutation-napari-reference-process-root-2/process.json) closes exit 0 without timeout and is fully reaped. Its [fresh host reference result](../../../build/evidence/image-resize-napari-reference-root-2/result.json) passes, with clean callbacks and cleanup, unchanged Native53 protection and no candidate renderer import. The declared host settings disable async slicing and autoswap buffers; the result has that limited scope. Independent saved reference admission and the first actual candidate resize are pending.
The [fresh napari reference admission](../../../build/image-resize-napari-reference-review-native-1/result.json) verifies the complete upstream host frame, all five fixed landmarks, the locked dependency and package origins, actual settings, process closure and cleanup. The finished candidate reference gate accepts that sealed receipt. The [first candidate host process](../../../build/visual-mutation-napari-candidate-process-root-1/process.json) then closes exit 0 without timeout and is fully reaped. Its [saved resize observations](../../../build/evidence/image-resize-napari-candidate-root-1/result.json) pass: the same cached Image node and program survive the public 2x3-to-6x8 layer.data replacement; one scheduled Qt paint returns a ready target draw with updated size and lookup state before any explicit export. No scene render, host reset, interpolation callback or interpolation setter repairs that interval. Both later complete final/resident frames match the fresh host reference exactly, callbacks and cleanup pass, and Native53 remains unchanged. Independent joint saved-output admission is pending. This is an integrated napari case with async slicing and autoswap buffers disabled; it does not establish original-failure causality, default asynchronous host behavior, swapchain pixel equality or performance.

The [closed host storage cleanup](../../../build/visual-mutation-closed-host-cleanup-point-1/result.json) retains all 373 files across 35 fixed closed folders with exact names, sizes and SHA256 values. NTFS compression saves another 2,567,292 physical bytes; no file is deleted or moved. The bounded temporary/bytecode/editor-backup scan is empty. Active review folders and changing sprint scripts are excluded.
The [independent napari joint outcome admission](../../../build/image-resize-napari-outcome-review-native-1/result.json) passes 1,979 checks. Both complete exports match the accepted host reference exactly (73,728 RGBA bytes, zero differences); all ten landmarks, the scheduled paint and ready draw before export, same cached node/program, current 521-member stage, 1,619 module origins, Native53 protection, callbacks, restored profiling and process/shutdown cleanup pass. One warm frame remains diagnostic only. The [scoped napari checkpoint](../../../build/image-resize-napari-redraw-checkpoint-root-1/progress.json), produced by a closed exit-0 process, binds the actual source peers, fresh reference admission, joint outcome admission, process records and earlier rendering/Volume Qt checkpoints. The one-case integrated-host gap is closed at its declared settings; broader host behavior and the original thirteen requirements remain open.

### Sprint22: public Image.view rendering

Existing canonical CPU coverage already checks public existing and late views across four interpolation modes and both Image methods. It prepares the original before the second view, so it does not qualify actual public view drawing first after resize. A bounded runner is under preparation using the unchanged fixture5 and admitted direct Image references. It will warm the original and an existing public view, replace the original data, draw that existing view first, then export the original, a newly created view and the resident existing view. Eight cases provide thirty-two final/resident complete-frame comparisons. The reused reference frames define direct image semantics; they are not presented as a successful upstream public-view workflow. No canonical/native change or new public-view GPU result is claimed yet.

Source inspection and a bounded CPU-only probe identify a separate LUT-backed colormap defect. With both Image methods, preparing one public view binds texture2D_LUT only to that view's program while clearing a shared color-transform flag. Existing and later views remain unbound; preparing them afterward does not repair the sampler. Replacing the colormap through another view can also leave the original holding the old LUT. The probe uses real ImageVisual, public view construction and real preparation, with no canvas, draw, flush, renderer or Qt import. An isolated two-line sharing fix and regressions are under preparation; canonical source and the current grays rendering fixture remain unchanged. Grays uses an analytic map and does not exercise this LUT branch.

The [public-view Source review](../../../build/image-public-view-capture-source-review-line-1/result.json) passes 36 independent checks and five retained stdlib tests; the finished source gate consumes the sealed receipt. The [first actual public-view process](../../../build/visual-mutation-image-public-view-process-root-1/process.json) closes exit 0 without timeout and is fully reaped. All [eight current grayscale cases](../../../build/evidence/image-public-view-root-1/result.json) pass: thirty-two complete existing-first/original/late/resident frames match the admitted direct semantic references exactly (1,179,648 RGBA bytes); sixteen warm frames remain diagnostic only. Each first existing-view draw prepares the shared geometry, lookup and texture once; the three later paths have zero further preparation calls. All canvases finish and close, native shutdown releases work, cleanup is empty and Native53 remains unchanged. Independent saved-outcome admission is pending. These observations do not cover the separate LUT colormap branch or claim an upstream public-view workflow, automatic redraw or performance.
The [independent public-view saved admission](../../../build/image-public-view-outcome-review-native-2/result.json) passes 7,198 checks: thirty-two complete grayscale frames match exactly, all 160 landmarks and shared preparation/state/actual public draw identities pass, all 521 package members and 236 loaded module origins match, and process closure, Native53 protection, current-context cleanup and shutdown are verified. One reviewer-only absolute-versus-relative path assumption remains preserved; corrected physical-path comparison changes no producer or frame. The [scoped public-view checkpoint](../../../build/image-public-view-checkpoint-root-1/progress.json), produced by a closed exit-0 process, binds that admission, the actual source peer/process and accepted direct reference evidence. Its scope remains the pre-LUT 15cb identity.

The [LUT sharing patch and CPU review](../../../build/image-lut-view-review-line-1/result.json) independently verifies the two-line production fix and eight new cases across both Image methods: existing/late views, view-first preparation and colormap replacement. The actual current baseline passes nine retained tests and fails the eight new cases; the isolated candidate passes all seventeen. The [actual publication](../../../build/image-lut-view-publication-root-1/result.json) then closes exit 0, preserves exact before backups and changes only Image/test_image; the other 607 current-source leaves and Native53 four are unchanged. The [published-source CPU receipt](../../../build/evidence/image-lut-view-canonical-cpu-root-1/result.json) binds seventeen passing real test bodies, actual argv/literal/JUnit, canonical inputs and the exact loaded copy in a fresh 521-member stage with two replacements. Source1 remains immutable: its proposed nested published output was replaced by a reviewed external-output runner, and the actual child disables pytest's cache. Independent publication/CPU admission and the next Python-layer identity remain pending. Current LUT pixels and post-publication GPU behavior are not yet admitted.
The [independent actual LUT publication/CPU audit](../../../build/image-lut-view-publication-review-line-1/result.json) passes fifty bounded checks. Exact two-file backups/replacements, all 607 other current-source leaves, Native53 four, immutable Source1, the fresh 521-member CPU copy, seventeen exact JUnit cases, 150 loaded origins and all three actual process closures are admitted. The current-source LUT CPU gap is closed; the next package identity and LUT pixels remain open.

The [closed LUT/public-view storage cleanup](../../../build/image-lut-public-view-closed-compression-native-1/result.json) preserves 2,155 files across eight fixed closed roots with exact names, sizes and hashes. Compression saves another 2,772,066 bytes, bringing these two host/public-view cleanup passes to 5,339,358 bytes. No file is deleted or moved; no bytecode, temporary or editor-backup file is found. Nine known standard pytest-cache files from the earlier isolated CPU runs are separately enumerated and preserved. The new published CPU output has no pytest cache; future runs disable it.

The first revision-identity helper is [refused before any stage or author run](../../../build/native53-python-source-revision-source-review-line-1/result.json). Its eight stdlib tests pass and its actual saved ancestor projection succeeds, but the full saved context reaches historical baseline/candidate CPU receipts with top-level-only seals and applies the new recursive packet rule to them. Those old receipts have separately mapped 521-file CPU packages and nine declared cache files; the current canonical raw CPU packet is already recursive and passes. A fresh narrow helper successor will recognize only those historical receipt roles while keeping current recursive packet checks strict. Canonical publication and its independent audit remain admitted; no failed helper is promoted and no new GPU result is claimed.


The corrected [revision Source3](../../../build/native53-python-source-identity-work-3/source-seal.json) passes its actual read-only context, nine stdlib controls and independent Source admission. Its narrow historical CPU handler preserves the old top-level packet roles while current packets remain recursive. The actual [stage2](../../../build/evidence/native53-python-source-stage-root-2/result.json), [3e5b revision identity](../../../build/evidence/native53-python-source-identity-root-2/identity.json) and [independent saved identity admission](../../../build/native53-python-source-revision-identity-outcome-review-native-1/result.json) close cleanly: 521 staged members, 519 retained plus the two LUT replacements, current 609 sources and unchanged Native53 four. All thirty-two grayscale public-view frames are [rerun and independently admitted at this identity](../../../build/image-public-view-current-outcome-review-native-1/result.json); no earlier GPU result is substituted.

The [LUT capture Source peer](../../../build/image-lut-view-capture-source-review-line-1/result.json), [two fresh direct reference admissions](../../../build/image-lut-view-reference-review-line-1/result.json) and [final joint LUT outcome audit](../../../build/image-lut-view-outcome-review-line-1/result.json) pass. Both cubic methods warm red LUTs, then use public data/blue-colormap replacement and existing-view-first, original, late and resident drawing. All eight complete candidate frames equal their same-case fresh direct references exactly (294,912 RGBA bytes, forty landmarks). Actual blue LUT upload bytes, shared sampler objects/GLIR IDs across all views, one preparation then reuse, resident command behavior, loaded origins and clean process/native shutdown are admitted. Four warm frames remain diagnostic. The [combined checkpoint](../../../build/image-current-qualification-checkpoint-root-1/progress.json) binds these eight plus the current thirty-two grayscale frames: forty complete frames, 1,474,560 exact candidate RGBA bytes, 200 landmarks and twenty diagnostic warm frames. This is bounded public Image rendering; automatic redraw, broader hosts, performance and the original thirteen requirements remain open.

The [current closed-asset compression](../../../build/image-current-closed-compression-line-1/result.json) preserves all names, byte sizes and SHA256 values for 1,421 files across thirty explicit closed folders, saving another 2,998,712 physical bytes. These three host/public-view passes now save 8,338,070 bytes. No files are deleted or moved; the nine previously declared cache files remain preserved outside this pass.

A separate scalar/color transition defect is confirmed with actual CPU regressions: changing Image data between scalar and RGB/RGBA can retain the old shader chain when the texture internal format remains None. The [independent Source/CPU review](../../../build/image-channel-transform-review-native-2/result.json) verifies the five-statement invalidation fix, retained tests, validation order and the external published CPU runner. Baseline has twenty-two passes/four expected failures; candidate has twenty-six passes. The [actual publication](../../../build/image-channel-transform-publication-root-1/result.json) preserves before backups and changes only Image/test_image; all other 607 leaves and Native53 four remain unchanged. The [canonical CPU receipt](../../../build/evidence/image-channel-transform-canonical-cpu-root-1/result.json) records twenty-six passes, copied canonical origins, full recursive output seal and disabled pytest cache. One Root invocation error passed a JSON row where the runner required a pathname and refused before package/imports/tests; its sealed failure is retained, and the fresh successful invocation changes only that argument and output destination. Independent actual publication audit, the next Python identity and source-derived nearest/subdivide scalar-to/from-RGBA rendering are next. Cybersecurity work remains excluded.

The [independent channel publication/CPU admission](../../../build/image-channel-transform-publication-review-native-1/result.json) passes 6,363 bounded checks. Exact reviewed/canonical/before bytes, other 607 source leaves, Native53 four, all twenty-six actual JUnit cases, 519+2 copied package members, 150 loaded Python origins, no new cache and all actual process closures are admitted. The initial pathname invocation refusal remains preserved and is excluded from successful execution. The scalar/color source and CPU implementation gap is closed; current-identity rendered qualification remains next.

The first actual Source4 context is refused before freeze/stage/author: its inherited strict publication gate requires both prior baseline and candidate CPU results retained by the postpublication audit. Audit1 retains the candidate/current canonical results but omits the prior baseline result from checked_inputs. The implementation and actual twenty-six-pass run remain admitted at their scopes. A fresh metadata audit successor will bind both recursive prior CPU packets; the strict identity requirement and all sealed earlier records remain unchanged.

The [fresh postpublication audit successor](../../../build/image-channel-transform-publication-review-native-2/result.json) closes exit 0, retains all audit1 facts and physically validates/merges both complete recursive prior CPU packets (2,252 pins). A fresh external actual input spec changes only that audit role. Source4 actual context is being rerun against the completed records; the prior refusal remains preserved.

The [closed channel CPU storage pass](../../../build/image-channel-closed-compression-point-1/result.json) preserves 1,635 files across fourteen fixed closed roots and saves another 408,118 physical bytes. Total saved by these four bounded host/public-view/channel passes is 8,746,188 bytes. Names, sizes, hashes and Native53 four remain exact, no files are deleted/moved, and the incidental bytecode/temp/editor-backup scan is empty. The new [identity Source4](../../../build/native53-python-source-identity-work-4/source-seal.json) passes its actual final context against the completed audit2 records (9,285 pins) and nine controls, then freezes for independent Line review. No stage/author action is implied by Source preparation.

The [Source4 independent peer](../../../build/native53-python-source-revision-source-review-line-3/result.json) passes 87 independent checks, nine retained controls and the completed Source consumer. Root creates the actual [stage3](../../../build/evidence/native53-python-source-stage-root-3/result.json) and [b4dd identity3](../../../build/evidence/native53-python-source-identity-root-3/identity.json) in closed exit-0 processes. Their [independent saved admission](../../../build/native53-python-source-revision-identity-outcome-review-line-1/result.json) passes 22,885 checks and exact completed guard4.admit_identity: 609/607+2 sources, 521/519+2 staged files, 147 resources, 4,130 harness files, 85 owners, formal 42 targets/44 tests/44 archived binary identities and unchanged Native53 four. Environment3 retains the dependencies and changes only the candidate backend path to the actual stage3. Earlier GPU qualifications retain earlier source contexts; the new transition capture Source is next.

The [channel capture Source peer](../../../build/image-channel-render-source-review-point-1/result.json) passes 94 independent checks, twelve retained controls and the completed Source consumer. Its [fresh direct references](../../../build/evidence/image-channel-render-reference-root-1/result.json) run and close exit 0; their [saved admission](../../../build/image-channel-reference-review-line-1/result.json) passes eighty checks, both complete frames (73,728 bytes) and ten landmarks, source-derived scalar active LUT versus direct RGBA inactive-sampler semantics, actual uploads, upstream package/origins and clean shutdown. The finished reference gate consumes the receipt. An extra reviewer-only empty-stderr rule is corrected to retain the actual Qt DPI warning, matching the frozen capture rules; captures and criteria remain unchanged. The [actual candidate](../../../build/evidence/image-channel-render-candidate-root-1/result.json) then passes both directions and closes exit 0 without timeout, with native release and empty cleanup errors. Eight final existing-first/original/late/resident frames match the references; all six first preparation counts are one, all three later phase counts zero. Joint independent saved admission is pending; four warm frames remain diagnostic.

The [final joint channel saved admission](../../../build/image-channel-outcome-review-line-1/result.json) passes 233 checks and 10,228 pins. All eight complete frames and forty zero-tolerance blue endpoint landmarks match the fresh same-case references. The actual public set_data-only category changes rebuild the scalar/direct chain 4-to-3 and 3-to-4 once, then reuse it for original/late/resident paths; the active scalar sampler and inactive direct-RGBA sampler/storage states are admitted truthfully. Native work, retirement, current identity/origins, process closure and cleanup pass. The [final scoped checkpoint](../../../build/image-channel-qualification-checkpoint-root-1/progress.json), produced by Root's closed exit-0 process, explicitly joins each review to the exact raw/process/reference/identity/source-review rows, the canonical CPU sources/native artifacts to the identity, and all eight full frame bytes again. Its scope is two nearest/subdivide transition directions; other interpolation/method/host matrices and automatic redraw/performance remain open.

The [closed identity metadata cleanup](../../../build/image-channel-identity-closed-compression-native-1/result.json) saves another 1,431,254 bytes across eleven explicit folders/575 files. The [final closed capture cleanup](../../../build/image-channel-capture-closed-compression-point-1/result.json) preserves ten folders/281 files and saves another 52,310 bytes. These six bounded host/public-view/channel passes save 10,229,752 physical bytes in total, with exact names, sizes, hashes and Native53 four retained. No deletes/moves or new bytecode/temp/editor-backup junk occur; nine earlier declared historical cache files remain preserved outside these passes. The scalar/color implementation and bounded rendered qualification gap is closed. The original thirteen requirements remain active.

### Sprint23: filtered Volume resizing, public host capture and performance evidence

A source defect is confirmed in VolumeVisual: spatial data replacement updates geometry and u_shape while retaining the old software-filter lookup shape. The [one-statement patch and independent CPU admission](../../../build/volume-filtered-resize-review-point-1/result.json) cover every exposed interpolation name (sixteen software names including the bicubic alias, plus nearest/linear controls), both CPU/GPU scaling classes, same-size reuse, existing/late views, pending resizes, one-axis changes, validation/upload refusal and retry. The actual baseline has 53 passes/44 expected failures; candidate has 97 passes. All 32 software-filtered resize observation rows move from stale XYZ(4,3,2) to correct XYZ(7,6,5); each run has 150 staged Python origins and no canvas/draw/flush/provider/VisPy native execution. After the b4dd host packet closes, Root [publishes exactly the reviewed Volume/testVolume files](../../../build/volume-filtered-resize-publication-root-1/result.json), preserving the other 607 source leaves and Native53 four, then the [actual copied-canonical run passes all 97 cases](../../../build/evidence/volume-filtered-resize-canonical-cpu-root-1/result.json). The [independent postpublication admission](../../../build/volume-filtered-resize-publication-review-point-1/result.json) verifies both original recursive CPU packets, all new canonical cases, 36 lookup observations, 150 staged Python origins, actual argv/closure and exact immediate-before backups. That CPU-only admission makes no GPU qualification claim; the later four-case rendered checkpoint below supplies its separate bounded scope.

Identity Source5 passes eight stdlib controls and its actual 11,463-input metadata context. Its [independent preparation peer](../../../build/native53-python-source-revision-source-review-native-5-2/result.json) verifies all 63 required pins and the exact completed Source consumer. Root produces the actual [stage4](../../../build/evidence/native53-python-source-stage-root-4/result.json) and [d00c identity4](../../../build/evidence/native53-python-source-identity-root-4/identity.json) in closed exit0 processes. Their [independent saved admission](../../../build/native53-python-source-revision-identity-outcome-review-line-2/result.json) passes 22,897 checks and exact guard5.admit_identity: 609/607+2 sources, 521/519+2 package members, 374 Python files/147 resources, 4,130 harness inputs, 85 owners, formal42 targets/44 tests/44 archived binary identities and unchanged Native53 four. Only immediate old Volume/testVolume bindings resolve to the actual publication's before-backups; all earlier Image/LUT/channel lineage stays exact. A reviewer-only hardware-lookup None assertion is corrected without changing Source. The [four-case filtered capture Source1 admission](../../../build/volume-filtered-resize-render-source-review-line-1/result.json) passes74 independent checks, twelve retained controls and all108 required inputs. The [first actual fresh reference attempt](../../../build/evidence/volume-filtered-resize-render-reference-root-1/result.json) closes exit1 without timeout after its first cubic/CPU frame: a prepared-state assertion incorrectly expects unchanged upstream to clear its geometry-dirty flag. Independent pinned-source and executable stdlib review confirms upstream retains that flag after successful geometry preparation while the already-published candidate correctly clears it; both clear lookup-dirty. No failed frame pixels are opened to alter criteria. The [independent Source2 admission](../../../build/volume-filtered-resize-render-source-review-line-2/result.json) passes40 checks, fifteen controls and all140 required pins, with whole capture/worker inverse proof for the mode-specific flag check and truthful runtime-failure status. All data, camera, kernels, full-frame RGB2/alpha0, landmarks, identity and cleanup remain unchanged. The [second actual fresh reference run](../../../build/evidence/volume-filtered-resize-render-reference-root-2/result.json) closes exit0 and all four full filtered MIP frames pass. The [independent fresh-reference admission](../../../build/volume-filtered-resize-render-reference-review-line-3/result.json) passes101 checks, 13,124 pins, all147,456 reference bytes/eight landmarks and the completed205-pin reference consumer. Two reviewer-only packed-byte decoder/timeout assumptions are corrected against unchanged source and actual900s request; their failed receipts remain preserved. The [actual candidate2](../../../build/evidence/volume-filtered-resize-render-candidate-root-2/result.json) then closes exit0: all eight complete final/resident frames have RGB0/alpha0 differences, geometry/lookup rebuild once, resident preparation is zero and native cleanup passes. The [independent joint saved admission](../../../build/volume-filtered-resize-outcome-review-point-1/result.json) passes125,995 checks and13,386 pins: all294,912 candidate RGBA bytes and24 reference/candidate landmarks match exactly, lookup XYZ16-to-32, one rebuild/resident reuse, actual geometry/data GLIR bytes, positive native work/retirement, literal process closures, origins/current609/521/4130/native4 and cleanup pass. The [Root scoped checkpoint](../../../build/volume-filtered-resize-qualification-checkpoint-root-1/progress.json), produced by a closed exit0 metadata process, joins publication/CPU97/currentidentity/Source/reference/outcome admissions to the exact raw/process rows and independently rechecks all eight complete frame bytes and current Volume/native hashes. Four warm frames remain diagnostic; other interpolation/method/automatic/host/platform/performance scopes stay open.

The public napari workflow covers six blend modes with signed/sparse high-ID Labels over RGBA Image, public paint and tile/refresh, layer removal/finish and retained owned captures; a seventh public multiscale case changes locked_data_level0-to-1-to-0 without content mutation. Its [independent Source admission](../../../build/napari-label-public-source-review-native-1/result.json) consumes the exact completed Source gate. All 28 fresh reference exports pass and receive [independent reference admission](../../../build/napari-label-public-reference-review-point-1/result.json). The actual candidate also closes exit0, and the [joint saved admission](../../../build/napari-label-public-outcome-review-native-2/result.json) independently verifies all 1,376,256 RGBA bytes and 168 landmarks: actual RGB and alpha differences are zero, within the predeclared RGB1/alpha0 bounds. Public on_draw/grabFramebuffer routes, 95 actual default Numba mapping calls, signed category/remap state, unchanged multiscale levels, edit-region invariance, original returned-array ownership after close, layer-removal finish, native retirement and process cleanup pass. A reviewer-only requirement for full-array mapping on one-pixel paint is corrected to preserve legitimate incremental mapping; actual captures and criteria stay unchanged. Both modes use the complete oracle-napari dependency donor with NumPy2.5.3/Numba0.68.0/llvmlite/napari0.9.2/PyQt6 6.11.0 and job-owned Numba caches. This qualification retains b4dd/stage3 and is limited to these seven prescribed2D workflows; broader original17, wheel/platform, automatic-only and performance claims remain open.

Performance inspection identifies an implementation gap beyond unrun workloads: the resident gate ignores some already available conversion/compiler counters and final release admission does not independently recheck them. The isolated candidate adds strict shared validation, actual upstream resource/compiler/wait attribution, bounded same-scene-context timestamp queries and separate scene/presentation sync completion. Source review finds and corrects ownership of a presentation fence before a potentially raising flush; Source1 and its evidence remain preserved. [Source2's independent admission](../../../build/benchmark-telemetry-source-review-root-1/result.json) validates 191 CPU cases, six loader controls, the retained190 suite and all34 clean baseline regression failures, with the original66 workloads and100/1000/five-run minima unchanged. The first small probe closes exit1 before provider/GPU imports: its strict census correctly refuses 508 unrecorded donor extras. The [independent donor diagnostic](../../../build/benchmark-telemetry-donor-diagnostic-point-1/result.json) proves all8010 named original inputs unchanged and identifies the complete8518-file physical inventory:506 bytecode files and two virtualenv bootstrap files are additional. [Source3's independent admission](../../../build/benchmark-telemetry-source-review-root-2/result.json) retains the 191 production CPU cases, checks the exact8518 census with zero exclusions, and refuses active donor bytecode/bootstrap paths. Its real probe reaches OpenGL but refuses an unrecorded96-pixel geometry mismatch before timing. [Source4's independent admission](../../../build/benchmark-telemetry-source-review-root-3/result.json) keeps production bytes exact, sets a public fixed128-square native client, records geometry before assertion and passes11 loader controls. The [third actual diagnostic](../../../build/evidence/benchmark-upstream-probe-root-3/result.json) confirms exact128 geometry/DPR1 and clean initialization/shutdown, but refuses nonzero Qt scene-context swap-interval metadata before any timed frame. [Source5's independent admission](../../../build/benchmark-telemetry-source-review-root-4/result.json) verifies a shared early Qt default-format request before either application/context, 204 passing provider-free CPU cases and twelve loader controls. Its [actual fourth probe](../../../build/evidence/benchmark-upstream-probe-root-4/result.json) requests interval0 and reads back default0 but still refuses the Qt scene-context format before warm/timed frames; this does not establish an unpaced context or a driver cause. No driver override or pacing bypass is used. Canonical benchmark tools remain unchanged. Full throughput GL protocol, full fixed-quality matrix, opaque allocation peaks, input-to-visible latency and release qualification remain open.

A separate calibration-only smooth study tests the missing add-before-scale binary32 viewport hypothesis from the mathematical Khronos glViewport transform. The [independent Source review](../../../build/smooth-viewport-parenthesization-source-review-root-1/result.json) verifies the single global operation-order change, the unchanged side/cap/byte formula and uploaded endpoints, all 199 synthetic controls, and the exact sixteen normalization/endpoint recipes. The [actual closed replay](../../../build/smooth-viewport-parenthesization-work-1/replay-1/result.json) freezes all 384 complete predictions before accessing the same 24 already-admitted calibration images. Its [independent saved-output admission](../../../build/smooth-viewport-parenthesization-outcome-review-line-1/result.json) reconciles all 1,179,648 prediction bytes and 2,359,296 signed-difference bytes, every summary and all sixteen totals. The best recipe differs at forty pixels, worse than the parent study's sixteen; it does not qualify a smooth model or production change. The primary equation does not mandate a machine evaluation order. Nine frozen future predictions and eight reserved holdouts remain unopened/unhashed; production smooth refusals remain unchanged.

The [closed Volume CPU storage pass](../../../build/volume97-closed-compression-root-1/result.json) preserves all 1,084 files across four explicit closed folders and saves 170,866 physical bytes. Names, logical sizes, SHA-256 hashes and installed Native53 four remain exact; deleted/moved counts are zero. New active host and benchmark folders remain outside this pass.

The [closed smooth study storage pass](../../../build/smooth-viewport-closed-compression-root-1/result.json) preserves all 27 files across the three explicit closed Source/replay/review folders and saves another 1,532,240 physical bytes. This sprint's two bounded passes save 1,703,106 bytes, with names, sizes, hashes and Native53 four exact and zero deletes/moves. No future predictions or reserved holdouts are compression targets.

The [closed benchmark Source/CPU/probe storage pass](../../../build/benchmark-telemetry-closed-compression-root-1/result.json) preserves 79 files in seven explicit closed folders and saves another 422,977 physical bytes. The three bounded sprint passes save 2,126,083 bytes in total. Active Volume identity preparation, donor diagnostics and host saved review folders are outside this pass; no file is deleted or moved.

The [closed public-host storage pass](../../../build/napari-label-public-closed-compression-point-1/receipt/result.json) preserves 1,041 files in all nineteen explicit closed host folders and saves another 3,325,556 physical bytes. This sprint's four bounded passes save 5,451,639 bytes. No names, sizes, hashes or Native53 four change; no deletes/moves or incidental bytecode/temp/editor-backup/pytest caches occur in those target folders.

[Source6's independent admission](../../../build/benchmark-telemetry-source-review-root-5/result.json) keeps all four production candidates byte exact to Source5 and retains its 204-test evidence. Fourteen stdlib controls admit an explicit normal-paced diagnostic while preserving the default throughput interval0 refusal; both modes permanently refuse throughput/release qualification. The [fifth actual probe](../../../build/evidence/benchmark-upstream-probe-root-5/result.json) confirms normal request and Qt context-format interval1, initializes bounded queries and issues its first warm paint, then fails at the implicit PyOpenGL64-bit timestamp-result allocation (GL_UNSIGNED_INT64_AMD mapping). No frame completion or timed samples are admitted. Process closure, cleanup and all8518 donor/original8010/native4 identities pass. A narrow explicit-output-buffer reader fix is under preparation; the unpaced context and real timestamp/two-fence protocol remain open.

The [closed Volume publication/identity storage pass](../../../build/volume97-identity4-closed-compression-line-1/result.json) preserves 1,134 files across twenty present roots and saves another 2,044,442 physical bytes. One exact missing predecessor review folder is skipped without replacement. This sprint's five bounded passes save 7,496,081 bytes in total, with exact names, sizes, hashes and Native53 four retained and zero deletes/moves.

The [closed telemetry storage pass](../../../build/benchmark-telemetry-closed-compression-point-1/receipt/result.json) preserves all 106 files in twenty-one explicit Source3/4/5, probe and review roots, saving another 426,199 physical bytes. This sprint's six passes save 7,922,280 bytes; exact names, sizes, hashes and Native53 four remain unchanged, with zero deletes/moves. Active Source6/probe5 and dependency donors remain outside the pass.

[Source7's independent admission](../../../build/benchmark-telemetry-source-review-root-6/result.json) verifies the sole production change: an explicit caller-owned ctypes uint64 output for timestamp results, preserving both-available-before-read, exact current-context ownership, wait/refusal/cleanup behavior, all66 workloads and full benchmark/work/probe bytes. All208 provider-free CPU cases and14 stdlib controls pass, including exact values above2^53 and2^63; a prior fake's unrepresentable negative unsigned timestamp is corrected to a representable reversed pair, with failed history preserved. The [sixth real diagnostic](../../../build/evidence/benchmark-upstream-probe-root-6/result.json) closes exit0 and passes two warm/six sampled actual paints, eight timestamp records, both separately signaled scene/presentation fences, zero measured forbidden uploads/compiler/waits/readbacks and clean shutdown. The [independent saved admission](../../../build/benchmark-telemetry-protocol-outcome-review-native-1/result.json) passes50,304 checks and8,770 physical pins, including all8518 donor files, original8010/extras508, actual process/Sourcepeer/current native4, 480-to-481 module origins and all eight exact unsigned64 query records. CPU completion latency retains the independently reviewed producer semantics; its original start timestamp is not saved for independent recomputation. It uses an explicit normal request and remains permanently diagnostic-only.

The [read-only Qt pacing analysis](../../../build/benchmark-qt-pacing-source-note-native-1/note.md) establishes an evidence distinction: the collector reads the widget scene-context format, while Qt propagates requested swap interval separately to the top-level presentation surface. The context-format value is not platform swap-interval proof. No platform readback exists in the old packets; neither actual paced nor actual unpaced swaps are established by their value1. A future owned-callback platform query is proposed without setters or context repair; throughput, compositor/scanout, full matrix and release claims remain open. Canonical benchmark files remain unchanged.

The [late closed telemetry storage pass](../../../build/benchmark-telemetry-late-closed-compression-point-1/receipt/result.json) preserves all73 files in fourteen explicit Source6/7, probe5/6, runtime and review roots, saving339,560 additional physical bytes. This sprint's seven bounded passes save8,261,840 bytes, with exact names, sizes, hashes and Native53 four and zero deletes/moves. Active Volume2 and saved reviewers remain outside this pass.

Frozen Source8 implements direct Windows presentation-window API interval observation inside the already-current owned frameSwapped callback. Expected top-level Qt surface/window, current HGLRC/HDC, WindowFromDC ownership, thread/token and strict typed before/after snapshots are mandatory; no setter or context repair is allowed. Each producer phase, controller-loaded raw sample file and release gate requires every requested owned interval0 receipt; missing, unowned, positive, adaptive-negative, duplicate/gapped/reordered or unsupported evidence cannot become unpaced qualification. The [independent Line code/API review](../../../build/benchmark-telemetry-pacing-source-review-line-1/result.json) passes122 checks and all six source maps. Because original CPU2/3 full outer tool carriers were not retained, Root [reruns the frozen394-case suite externally](../../../build/evidence/benchmark-telemetry-source8-cpu-root-1/result.json), preserving complete actual initial/terminal returns and14 passing loader controls without changing Source8. The [final Root Source admission](../../../build/benchmark-telemetry-source-review-root-7/result.json) joins both reviews, all23 source/305 named external inputs, the fresh394JUnit/argv/environment/literal evidence, retained timestamp/work modules and unchanged fence/flush/completion tail, then consumes exact admit_source. No canonical benchmark file is published.

The [final closed Volume capture storage pass](../../../build/volume-filtered-resize-render-closed-compression-point-1/receipt/result.json) preserves all645 files across all28 exact closed Source, reference, candidate, runtime and review folders and saves3,115,047 more physical bytes. This sprint's eight bounded passes save11,376,887 bytes total, with exact names, sizes, hashes and Native53 four retained and zero deletes/moves. No new incidental bytecode/temp/editor-backup/pytest caches occur in these targets; older declared historical caches remain outside the passes. Source8 and the new checkpoint are excluded.

The [seventh actual throughput-request diagnostic](../../../build/evidence/benchmark-upstream-probe-root-7/result.json) reads WGL interval0 from the owned target window but closes exit1 before any completed sample: strict before/after Qt Python wrapper IDs differ, while native HGLRC/HDC/HWND/thread and Qt surface values remain exact. Cleanup and donor8518/original8010/native4 identities pass. This remains unqualified evidence. Source inspection and SIP lifetime documentation support a missing strong-reference boundary between the two snapshots. Source9 retains Qt wrappers for one whole observation and clears its references in finally. The old helper fails all four new forced-GC weak-cache regressions; the new helper passes all398 CPU cases and14 loader controls. The [independent Line source review](../../../build/benchmark-telemetry-pacing-source-review-line-2/result.json) and [Root Source admission](../../../build/benchmark-telemetry-source-review-root-8/result.json) bind all six candidates and the complete original CPU execution carrier. Whole-helper inverse controls preserve every ownership/type/interval/fence predicate, and Root consumes exact admit_source before runtime.

The [eighth fresh Windows throughput-request diagnostic](../../../build/evidence/benchmark-upstream-probe-root-8/result.json) closes exit0 in6.87 seconds: all eight actual callbacks, two warm and six sampled, have owned interval0 receipts with exact typed before/after Qt/native ownership; eight GPU timestamp records and separately signaled scene/presentation fences complete. Measured work is six draws, twelve clears, six presents and634 zero-timeout polls; all forbidden uploads/compiler/blocking waits/readbacks remain zero. Queries/fences drain, observer/cleanup errors are empty, and donor8518/original8010/native4 remain unchanged. The [independent saved-outcome admission](../../../build/benchmark-telemetry-owned-pacing-outcome-review-line-1/result.json) passes49,989 checks and8,922 physical pins. The [Root diagnostic checkpoint](../../../build/benchmark-owned-pacing-checkpoint-root-1/progress.json) seals the complete actual process, Source, CPU and protocol joins. The packet remains diagnostic-only: no throughput, compositor/scanout, full-matrix, input-to-visible or release claim follows. The [six exact benchmark leaves are now published](../../../build/benchmark-telemetry-publication-root-1/result.json), with both old canonical files retained as exact backups. All [398 canonical CPU cases pass](../../../build/benchmark-telemetry-canonical-cpu-record-root-1/result.json), with actual four-module canonical origins, unchanged Native53 four and full original initial/poll returns retained. The [independent publication/CPU audit](../../../build/benchmark-telemetry-publication-review-point-1/result.json) admits exact current six, both preserved baselines, all398 exact JUnit names, actual four-module origins, actual initial/same-handle terminal returns and unchanged609/stage521/native4 across68,224 checks and12,483 physical pins. The [fresh metadata-only harness identity](../../../build/native53-benchmark-harness-identity-outcome-review-line-1/result.json) is now independently admitted. The [final publication checkpoint](../../../build/benchmark-telemetry-publication-checkpoint-root-1/progress.json) closes this bounded implementation batch. The explicit harness overlay accounts for the tracked-file distinction: only the old metrics test is among the4130 tracked harness members, so tracking all six leaves yields4135 members, with five newly tracked members and one modified tracked member. This differs from the filesystem delta of four new files and two modified files. Historical canonical pins require exact backup aliases; the609 source leaves and521-member package stage stay unchanged.

The [ninth closed telemetry storage pass](../../../build/benchmark-telemetry-source8-9-compression-point-1/receipt/result.json) preserves160 files across23 exact closed Source8/9, CPU, runtime, probe7/8 and source-review roots, saving709,995 additional physical bytes. This sprint's nine bounded passes save12,086,882 bytes; names, logical sizes, hashes, both frozen Sources and Native53 four remain exact, with zero deletes/moves. Active saved-outcome, publication, canonical CPU and new identity folders stay outside the pass.

The [tenth closed publication/harness storage pass](../../../build/benchmark-harness-publication-closed-compression-point-1/receipt/result.json) preserves143 files across28 present exact roots, skips the explicitly missing controls-native-1 root, and saves6,344,909 additional physical bytes. This sprint's ten bounded passes save18,431,791 bytes. All names, logical sizes, SHA-256 hashes, canonical six, old two backups, both frozen Sources and Native53 four remain exact; no file is deleted or moved. Active Root/Line review and metadata-output roots stay excluded.

The [frozen harness-identity Source](../../../build/native53-benchmark-harness-identity-work-1/source-seal.json) adds a separate metadata layer over d00c: one tracked metrics test changes and five members become newly tracked, giving4135 current harness members while formal Native53 retains4130. Exact historical old-frame-script and old-metrics hashes bind only to their two actual publication backups. Windows-relative separator spelling is normalized without rewriting the historical documents; the first context refusal is preserved. All14 stdlib tests/143 controls and the final saved-context20992-pin check pass. [Independent Point Source admission](../../../build/native53-benchmark-harness-identity-source-review-point-2/result.json) passes751 checks; its first reviewer-only external-presence mistake remains retained. [Root Source admission](../../../build/native53-benchmark-harness-identity-source-review-root-1/result.json) rechecks21087 physical inputs and consumes exact source_gate.

The [actual harness identity author](../../../build/evidence/native53-benchmark-harness-identity-root-1/result.json) closes exit0 from the exact isolated command, binding identity d38acf, all609 unchanged renderer sources, the original521-member stage4, current4135 harness members and the same Native53 four. The [independent saved admission](../../../build/native53-benchmark-harness-identity-outcome-review-line-1/result.json) consumes exact admit_identity once and passes134126 checks/21099 physical pins, including all parent source/native/formal85-owner/42-target/44-CTest/44-archive bindings, six canonical leaves, both old backups, all398 canonical JUnit cases, actual module origins and original Root author tool returns. No package restage or native rebuild is claimed, and no old GPU qualification is inherited. The [Root final checkpoint](../../../build/benchmark-telemetry-publication-checkpoint-root-1/progress.json) joins these completed independent admissions and rechecks the current six/backups/native4. The benchmark telemetry implementation batch is closed; the full66-workload fixed-quality performance matrix, opaque allocation peaks, normal input-to-visible latency, remaining scientific/host/platform/package gates and the original thirteen requirements remain open. Cybersecurity work stays excluded.

The [eleventh final closed telemetry storage pass](../../../build/benchmark-harness-final-closed-compression-point-1/receipt/result.json) preserves all25 files in the nine exact final Root/Line Source-review, identity, execution and checkpoint folders, saving3,173,365 more physical bytes. This sprint's eleven bounded passes save21,605,156 bytes total. Every name, logical size and SHA-256 remains exact; current canonical six, both baseline backups, frozen Source/guard and Native53 four are unchanged, with zero deletes/moves or incidental caches in these targets. No live capture, provider, build or metadata process remains in this batch.

### Sprint24: Mesh bounds and texture topology updates

The [reviewed five-file Mesh patch](../../../build/mesh-update-invalidation-publication-root-1/result.json) is published. Geometry changes refresh shared bounds before update events, public view bounds and draw forwarding return their results, and TextureFilter refreshes expanded UVs when topology changes while reusing unchanged UV data. The focused baseline has eleven passes and twenty-six failures; the candidate and [canonical CPU run](../../../build/mesh-update-invalidation-canonical-cpu-record-root-1/result.json) each pass all thirty-seven cases. The [independent publication/CPU audit](../../../build/mesh-update-invalidation-publication-review-line-1/result.json) admits the exact five current leaves, four old backups, real loaded origins and unchanged Native53 four. A post-write publication-report error is preserved with its original execution record; a separately reviewed recorder verified the applied bytes and wrote the missing report without replaying publication.

The first Mesh metadata identity remains unadmitted: independent descriptor checks found stale historical physical bindings before invoking its identity consumer. [Corrected Source2](../../../build/native53-mesh-python-source-identity-work-2/source-seal.json) derives the immediate-parent map from the actual parent and projects only the four exact Mesh ancestors onto their preserved backups. Its sixteen tests and 185 controls pass. The [corrected identity admission](../../../build/native53-mesh-python-source-identity-outcome-review-line-2/result.json) passes 5,411 checks, verifies both 609-member logical/physical ancestor maps and completes the new guard's identity consumer exactly once. The [Root CPU/identity checkpoint](../../../build/mesh-update-invalidation-checkpoint-root-1/progress.json) joins all thirty-seven canonical CPU passes with 610 current sources, 522 package members and 4135 harness members. No native binary changes or inherited GPU result are claimed.

The [four-case Mesh rendering Source](../../../build/mesh-update-render-work-1/source-seal.json) passes [independent source review](../../../build/mesh-update-render-source-review-line-1/result.json): inferred 2D bounds after set_data, inferred 3D bounds after public MeshData notification, same-size UV topology replacement, and topology growth. The [first actual upstream reference](../../../build/evidence/mesh-update-render-reference-root-1/result.json) closes exit1 after the first case returns background-only pixels; its raw frame, actual same-session closure and clean cleanup are retained and [independently refused](../../../build/mesh-update-render-reference-review-line-1/result.json). The [saved-state diagnosis](../../../build/mesh-update-render-clipper-diagnosis-native-1/result.json) establishes a harness lifecycle defect: the ViewBox constructor resizes before creating its scene clipper, leaving unit clip bounds that discard correctly transformed Mesh fragments. [Fresh Source2](../../../build/mesh-update-render-work-2/source-seal.json) sets public size immediately after construction, before the camera or Mesh. Its [independent Source admission](../../../build/mesh-update-render-source-review-line-2/result.json) verifies the exact final scene, fixture, cameras, twenty landmarks, complete-frame tolerances and upload criteria are unchanged. The [second actual upstream run](../../../build/evidence/mesh-update-render-reference-root-2/result.json) and [saved reference admission](../../../build/mesh-update-render-reference-review-line-2/result.json) pass all four fresh cases with clean callbacks, cleanup and shutdown.

The [actual candidate capture](../../../build/evidence/mesh-update-render-candidate-root-1/result.json) and [independent final outcome audit](../../../build/mesh-update-render-outcome-review-line-1/result.json) pass all eight final/resident frames: 294,912 complete RGBA bytes equal the fresh references exactly, all forty candidate landmark checks pass, and no pixel is excluded. Each final draw prepares Mesh/position once, each topology case updates its expanded UV once, main textures receive no final upload, and resident Mesh/position/UV/main-texture counts are all zero. Actual public-view-first bounds, inferred cameras, same-object mutation, parsed upload bytes, module origins and clean native shutdown are admitted. Four warm frames remain diagnostic. The [Root final Mesh checkpoint](../../../build/mesh-update-render-checkpoint-root-1/progress.json) joins the thirty-seven canonical CPU cases, corrected identity and all source/reference/outcome/process admissions. This bounded Mesh preparation/bounds/topology rendering gap is closed; automatic redraw, general hosts and the original thirteen requirements remain open.

Seven byte-preserving cleanup passes now save 27,632,782 additional physical bytes with names, sizes, SHA-256 hashes and Native53 four unchanged. The [closed stage/identity pass](../../../build/native53-mesh-stage-identity-closed-compression-native-1/result.json) preserves all584 files across fifteen exact roots; the [closed rendering pass](../../../build/mesh-render-closed-compression-native-1/result.json) preserves431 files across all33 named roots and saves14,312,253 more bytes. The [closed allocation CPU pass](../../../build/measured-allocation-window-closed-cpu-compression-line-1/result.json) preserves275 files across twenty named roots and saves374,504 more bytes. No file is deleted or moved.

The separate unpublished measured-allocation-window proposal passes twenty-two provider-free protocol tests after three review fixes: missing optional exports remain compatible, Python retains the received token before fallible copying, and cancellation bypasses fallible polling. The first portable C++ run is [refused for a wrapper proof gap](../../../build/measured-allocation-window-cpp-review-native-1/result.json): its batch guard missed negative Windows exit codes and saved no per-stage codes; no unit crash is claimed. The [fresh actual C++ rerun](../../../build/evidence/measured-allocation-window-cpp-root-2/result.json) retains the same header/test/toolchain and records exact setup, compilation and execution codes of zero, with nonzero guards covering negative codes. Its [independent saved audit](../../../build/measured-allocation-window-cpp-review-native-2/result.json) admits the actual header/helper CPU assertions; the first review's malformed self-declaring seal is separately retained with a correctly sealed byte-exact snapshot of its unchanged refusal members.

All [398 existing benchmark CPU contracts](../../../build/evidence/measured-allocation-window-existing-cpu-line-1/result.json) pass against the staged candidate and unchanged helper bytes, with exact prior case names, a NoProviders barrier and unchanged current sources/native artifacts. All fifteen fake runner controls pass. The [actual fake-dispatched layer contract](../../../build/evidence/measured-allocation-window-hook-cpu-root-1/result.json) configures, compiles and runs its exact named CTest with three integer-zero process exits and both success markers. Its wrapper receipt remains failed solely because CTest now prints a different successful summary phrase. The [independent saved execution audit](../../../build/measured-allocation-window-hook-review-native-1/admission.json) verifies the exact JUnit case, generated two-TU build, compiler/header/source/flags, actual markers and protected inputs. The [Root CPU checkpoint](../../../build/measured-allocation-window-cpu-checkpoint-root-1/progress.json) records that actual pass without rebuilding, rerunning or rewriting the failed reporter. The layer test covers event-level short-lived allocation peaks, lifetime/window separation, token and ABI refusal, failures, two-device ownership and retirement; full runtime/binding/hardware and broader fault-injection qualification remain open. No canonical allocation-window file is published. The original thirteen requirements remain open, and cybersecurity work remains excluded.

### Sprint25: measured-allocation native integration

Native54 ownership/freeze and saved-reader/activation successors are being prepared in isolated build folders. The publication contains the six reviewed production leaves and an include-only canonical-route successor of the tested Vulkan-layer contract. The isolated include path is not copied into the canonical harness. The existing target/test set stays42/44/44; the policy retains48 C++ and37 CPU-contract owners and explicitly records the separately tested existing harness role. The admitted current harness partitions into4131 cpp/tests/datasets members and four benchmark tools; the four tools remain a separate overlay under the formal reader's existing path restriction. Source610/package522 and the validated213-file dependency SDK are retained, with no vendor rebuild or old GPU-pass inheritance. Fresh freeze/build, installation and device protocol validation have not run.

The [frozen seven-file publication Source](../../../build/measured-allocation-publication-work-root-1/source-seal.json) binds all4,264 named physical inputs. Its [independent Source review](../../../build/measured-allocation-publication-source-review-line-1/result.json) passes4,200 checks. Root's [actual publication](../../../build/measured-allocation-publication-root-1/result.json) closes exit0 and preserves all seven immediate-before files. The [independent saved publication audit](../../../build/measured-allocation-publication-review-line-1/result.json) passes8,348 checks: exact current7 and backups7, source610 with605 unchanged, harness4135 with4128 unchanged, every physical binding and unchanged installed Native53 four. Root's [ownership Source admission](../../../build/native54-allocation-epoch-source-review-root-1/result.json) and [build-reader Source admission](../../../build/native54-allocation-build-review-source-review-root-1/result.json) pass their completed consumers before publication. The initial publication preparation stopped before creating an output or changing canonical files because logical dataset aliases were treated as physical paths; its successor consumes the admitted physical binding map. A separate cross-review identifies an activation CLI mismatch between the new JSON2 arguments and the retained installed-audit argument validator. The first activation preparation remains unadmitted, and a fresh successor will fix and test that integration before installation.

The [activation successor](../../../build/native54-allocation-activation-adapter-work-2/seal.json) restores the literal approval path/hash and Source-seal hash expected by the retained installed audit. All39 focused metadata controls pass, including the reproduced predecessor refusal and the corrected actual argument tail. Its [Root Source review](../../../build/native54-allocation-activation-adapter-source-review-root-2/result.json) binds all77 required physical inputs and passes the completed Source consumer. The [closed preparation cleanup](../../../build/native54-preparation-closed-compression-root-1/result.json) preserves158 files across twenty explicit closed folders and reclaims6,853,090 physical bytes, with all current seven files and installed Native53 four unchanged. No file is deleted or moved.

Root's [actual ownership metadata author](../../../build/native54-ownership-root-1/result.json) closes exit0 on snapshot40/epoch54. It uses the single reviewed projector, validates the new five-source CPU archive with the formal packet checker, retains all37 original contract owners and records the existing hook harness separately. Its exact source-policy,85-owner manifest, four-tool overlay and qualification context await independent saved ownership admission before the formal freezer/build runs. The [full original Root terminal](../../../build/native54-allocation-owner-author-terminal-root-1/observation.json) preserves the literal arguments and all same-session tool returns. This is metadata preparation, without a native compilation or installation claim.

The [independent saved ownership admission](../../../build/native54-allocation-ownership-review-line-1/result.json) passes4,192 checks, and Root's [completed ownership consumer](../../../build/native54-allocation-ownership-consumer-observation-root-1/observation.json) passes all5,563 physical pins. The [actual epoch54/snapshot40 freeze](../../../build/native54-freeze-outer-root-1/outer-observation.json) closes exit0, sealing frozen-inputs35aa1d6a and unchanged installed Native53 four. The [actual isolated native build](../../../build/native54-full-build-outer-root-1/outer-observation.json) closes exit0: all42 targets and44 CTests pass, with44 archived artifact identities. Its [independent saved admission](../../../build/evidence/native-pass-54-build-review-line-1/result.json) verifies5,636 inputs and the two separate external MSVC witnesses; source610/package522/formal4131 plus four tools remain exact. A narrowly scoped [qualification-context successor](../../../build/native54-qualification-context-root-2/result.json) retains all5,493 immutable workspace pins while recording the two actual external MSVC witnesses separately, as the saved reader already requires. The original owner/policy/context remain exact; the first context wrapper's self-including seal is preserved and unadmitted, and its corrected packaging is verified in a fresh folder. The [idle API smoke Source review](../../../build/native54-allocation-smoke-source-review-line-1/result.json) passes38 metadata checks and is ready only after actual installation admission. Installation and device protocol validation remain pending; no earlier GPU pass is inherited by Native54.

The [saved build-storage audit](../../../build/native54-cleanup-saved-review-line-1/result.json) verifies both closed compression processes and preserves the first failed receipt. That verification stopped solely because the concurrently completed installation approval added one file; no existing name, size, hash or directory changed. With evidence writers stopped, the repeat completes as an already-compressed no-op. Physical storage falls733,751,912 to587,023,608 bytes, a146,728,304-byte net reduction including the approval's creation cost. Together with the earlier preparation pass, this sprint saves153,581,394 net physical bytes. No files are deleted or moved.

The [read-only installation preflight](../../../build/native54-activation-preflight-outer-root-1/outer-observation.json) and actual activation close exit0. The first Root transcript omitted the installer's observed PID; its refused metadata-author run and original carrier remain preserved. The fresh carrier adds only the actual PID48672 from the unchanged original tool return. The independent installed audit then validates5,666 inputs and all four committed copies, including exact staging and Native53-before backups. The actual idle API run passes three ownership windows, nine refusal cases, cancellation, unsigned counter accounting and clean shutdown. Its scope includes device initialization and the API protocol; rendering and performance qualification require their own fresh results.

The [independent saved idle API audit](../../../build/evidence/native54-idle-api-outcome-review-line-1/result.json) now verifies9,157 physical inputs and the complete protocol result. Root's [current original126 identity](../../../build/evidence/native54-original126-identity-root-1/identity.json) and its [independent saved identity admission](../../../build/evidence/native54-original126-identity-review-line-1/result.json) bind the parent package522, source610, unchanged formal4131 plus tools4 and installed Native54 four. The identity adapter explicitly derives the current build handoff from the completed build admission; no native rebuild occurs. Root then runs the unchanged [ordinary17](../../../build/evidence/native-pass-54-affected-regressions-1/ordinary17/result.json) and [affected109](../../../build/evidence/native-pass-54-affected-regressions-1/affected109/result.json) recipes sequentially. All126 pass. The [independent saved regression audit](../../../build/evidence/native54-original126-outcome-review-line-1/result.json) decodes769 full numeric arrays, verifies299 exact saved comparisons and admits recovery, resident behavior, cleanup and terminal process closure. A refused transcript omitted actual driver/Popen IDs; its [fresh metadata successor](../../../build/native54-original126-outer-root-2/observation.json) supplies only the IDs already present in the original results, including the actual Windows launcher-to-Python edge. The recipes, acceptance criteria, captures and original process returns remain unchanged.

The [post-install closed-assets cleanup](../../../build/native54-post-install-closed-compression-root-1/result.json) preserves715 files in36 explicit closed folders and reclaims1,839,293 physical bytes. Its [independent saved audit](../../../build/native54-post-install-cleanup-saved-review-line-1/result.json) passes137 checks. Including the two earlier cleanup passes, Sprint25 reclaims155,420,687 net physical bytes. The current source, installed binaries, file names and evidence bytes are retained. The [scoped Native54 integration checkpoint](../../../build/native54-integration-scoped-checkpoint-root-1/progress.json) binds these completed build, installation, API and original126 admissions at source610/package522; later Python revisions need their own validation.

### Sprint26: Isocurve and instanced-mesh Python fixes

The [instanced-mesh source and CPU review](../../../build/instanced-mesh-bounds-review-line-1/result.json) admits a focused correction for two-dimensional template bounds and empty instance arrays. All26 candidate CPU cases pass;21 reproduce the defect on the unchanged baseline. The [Isocurve source and CPU review](../../../build/isocurve-empty-levels-review-line-1/result.json) admits empty-level handling and preservation of original contour-level color indices. All25 candidate CPU cases pass;20 reproduce the defect on the unchanged baseline. These results use isolated candidate copies with provider/device imports blocked. The [first read-only publication preflight](../../../build/python-contour-instance-preflight-refusal-outer-root-1/outer-observation.json) refuses an evidence-path normalization mismatch before any canonical write. Its [reviewed metadata successor](../../../build/python-contour-instance-publication-source-review-root-2/result.json) recognizes only the three exact external witnesses already admitted by the parent identity; the reviewed renderer changes are unchanged. Root's [actual preflight](../../../build/python-contour-instance-preflight-outer-root-2/outer-observation.json) then passes13,065 named inputs, and [publication](../../../build/python-contour-instance-publication-root-1/result.json) preserves all three old files before writing the four approved leaves.

All [26 copied-canonical instanced-mesh cases](../../../build/evidence/python-contour-instance-canonical-instanced-root-1/result.json) and [25 copied-canonical Isocurve cases](../../../build/evidence/python-contour-instance-canonical-isocurve-root-1/result.json) pass. The [independent saved publication/CPU audit](../../../build/python-contour-instance-publication-review-line-1/result.json) verifies14,171 workspace pins, three external witnesses, the complete original tool transcripts and exact test IDs, ASTs, JUnit results and staged module origins. Current source611 retains607 unchanged parent leaves; package523 retains519 unchanged members plus four current copies. Formal4131 plus tools4 stays4135 with all bindings unchanged. The original GL tests and actual optional scikit-image contour algorithm remain unexecuted; these51 cases qualify the focused CPU behavior. The [independent identity adapter cross-review](../../../build/native54-contour-instance-identity-cross-review-point-1/result.json) catches and resolves a separate original-JUnit wire mismatch before any stage or identity production. Source1 is preserved unadmitted; Source2 passes82 controls and Root's completed Source gate.

Root's [actual new stage](../../../build/evidence/native54-contour-instance-python-stage-root-1/result.json) copies519 immutable parent members and the four published files, retaining376 Python modules and147 resources. The [actual new identity](../../../build/evidence/native54-contour-instance-python-identity-root-1/identity.json) and [independent saved identity audit](../../../build/evidence/native54-contour-instance-identity-review-line-1/result.json) complete the new guard's actual identity consumer, checking14,766 workspace inputs and three external witnesses. Formal Native54/snapshot40 source610 and harness4131 retain their historical build scope; the current Python revision has611 sources,523 package members and4135 harness members. Exact immediate-before aliases cover only the three replaced files. Root's complete stage/identity tool returns and self-reported metadata PIDs are sealed without an OS parent-edge claim. No old prepublication identity guard is replayed, and no earlier GPU or host pass is inherited by the new Python revision.

The [first cleanup attempt](../../../build/python-contour-instance-cleanup-refusal-outer-root-1/outer-observation.json) stops before output creation, target inventory or compression because its path classifier omits four declared top-level project files. The [reviewed successor](../../../build/python-contour-instance-closed-cleanup-source-review-root-2/result.json) adds only those literal names and passes the actual611-member publication gate. Root's [actual compression](../../../build/python-contour-instance-closed-compression-root-1/result.json) and [independent saved audit](../../../build/evidence/python-contour-instance-cleanup-review-line-1/result.json) preserve all2,201 files and280 directories across16 explicit closed folders. Both compact batches close exit0;29 files become compressed, reclaiming1,453,015 physical bytes. Every name, size, SHA, file ID and write clock remains exact. The cumulative Sprint25/26 net storage reduction is156,873,702 bytes, with no deletion or move. The [sealed batch checkpoint](../../../build/python-contour-instance-cpu-checkpoint-root-1/progress.json) binds the actual publication, canonical51 CPU results, stage, identity, independent admissions and cleanup. Next work is bounded rendering qualification for this Python revision and the remaining original scientific, host, platform, performance and release conditions.

### Sprint27: contour and instanced-mesh rendering qualification

The [fresh current-identity preflight](../../../build/contour-instance-render-identity-preflight-outer-root-1/outer-observation.json) passes14,746 named inputs before any renderer import, retaining current611/package523/harness4135 and installed Native54 four. Seven bounded rendering cases are being prepared with independent literal Line and explicitly transformed noninstanced Mesh references on the unchanged OriginalGL package. The Native54 subjects use the published Isocurve and InstancedMesh implementations. Full frames, landmarks, analytic camera bounds and cleanup criteria will be frozen before capture. Excluded minimum/maximum contour levels are labeled as strict-filter cases; the extractor-returning-empty and optional scikit-image branches retain their existing CPU-only scope.

Source review exposes an additional implementation gap before capture: accepted empty instance positions/transforms yield a zero instance count, which the existing GLIR draw code treats as an ordinary draw. The [isolated two-file proposal](../../../build/instanced-empty-draw-work-point-1/result.json) adds a visual-level draw guard, propagates the inherited missing-template skip, and preserves warmed template bounds when only instance attributes change. All68 focused candidate CPU cases pass; the unchanged baseline passes38 and fails30. The [independent saved Source/CPU admission](../../../build/instanced-empty-draw-review-line-1/result.json) verifies4,370 physical inputs, full original process returns, exact test names and complete production/test inverses. The original26 bounds cases and three unexecuted GL tests remain intact. Rendering validation over the explicit two-file overlay is next. Qualification must include actual empty background frames and later repopulation. Publication, canonical CPU replay and a new Python-only stage/identity follow a passing GPU result. The unchanged original17/affected109 recipes will then run against that new revision. Canonical source remains at the admitted48ac identity until publication. No native rebuild or cybersecurity work is part of this batch.

The [bounded closed-CPU storage check](../../../build/instanced-empty-cpu-closed-compression-root-1/result.json) verifies3,198 files and378 directories across the six completed baseline/candidate output folders. All eligible files are already compressed, so the pass changes no file and reclaims zero additional bytes. Names, sizes, hashes, file IDs and write clocks remain exact, as do current611 and installed Native54 four. No files are deleted or moved.

The first capture Source is superseded before runtime because sorted JSON changes dictionary iteration order; Source2 adds an explicit phase-order list while preserving the rendering data and criteria. Root consumes the [actual Source2 gate](../../../build/contour-instance-render-source-review-root-2/result.json) and separately admits the saved-only reader. The [first real OriginalGL reference run](../../../build/evidence/contour-instance-render-reference-root-1/result.json) completes four cases and captures the fifth, then refuses its camera-scale check: the noninstanced Mesh bounds retain float32 scalars, while the analytic calculation used double precision. All recorded landmarks match exactly and all cleanup/current-source/native checks pass. The [complete original process carrier](../../../build/contour-instance-render-reference-observation-root-1/observation.json) retains this failed run. [Independently reviewed Source3](../../../build/contour-instance-render-source-review-line-3/result.json) expresses only the reference's float32 arithmetic explicitly, retaining the candidate's Python-float bounds calculation, the same camera tolerance and all whole-frame pixel criteria. Root consumes its exact gate before the fresh rerun.

All [seven fresh OriginalGL references](../../../build/evidence/contour-instance-render-reference-root-2/result.json) pass, and the [independent saved-reference admission](../../../build/evidence/contour-instance-render-reference-review-line-1/result.json) verifies 56 analytic landmarks, camera state, module origins and complete original process closure. The [actual Native54 proposed run](../../../build/evidence/contour-instance-render-candidate-root-2/result.json) passes all seven cases: 24 qualified frames match their independent references byte for byte across 884,736 RGBA bytes. The [independent joint rendering audit](../../../build/evidence/contour-instance-render-candidate-review-line-1/result.json) admits those results, including empty/no-template frames, repopulation, bounds, resident reuse and cleanup. Root then [publishes the exact reviewed two-file correction](../../../build/instanced-empty-draw-publication-root-1/result.json), and all [68 copied-canonical CPU cases pass](../../../build/evidence/instanced-empty-draw-cpu-published-root-1/result.json). The [saved publication/CPU audit](../../../build/evidence/instanced-empty-draw-publication-review-line-1/result.json) and [external physical-write audit](../../../build/instanced-empty-draw-publication-observer-review-line-1/result.json) are independently clear. The new 523-member stage and [current Python identity are independently admitted](../../../build/evidence/native54-instanced-empty-draw-python-identity-review-line-1/result.json); the [fresh original17/affected109 execution and independent saved audit pass](../../../build/evidence/native54-python611-original126-outcome-review-line-1/result.json). The [independent cleanup audit](../../../build/sprint27-cleanup-outcome-review-point-1/packet/result.json) verifies all 106 retained files and 298,973 reclaimed physical bytes. No failed or earlier GPU result is promoted, and installed Native54 four are unchanged.

The [final scoped checkpoint](../../../build/instanced-empty-draw-render-regression-checkpoint-root-1/progress.json) binds the actual publication, 68 canonical CPU passes, 24 exact rendering frames, current stage/identity, all 126 original regression passes, their independent admissions and full execution journals, and the audited cleanup. Root retains the [metadata-recorder failure and recovery](../../../build/native54-python611-original126-metadata-recorder-recovery-root-1/result.json): a path-type error fails before the outer record is written; fresh helpers add only Path coercion and then capture the successful closures. Both scientific jobs run once, and the frozen transport, reader, masks, thresholds and scientific recipes remain unchanged. The broader original thirteen requirements remain open.

### Sprint28: current Native54 broader GPU qualification

Preparation is in progress for the existing ten-scene broader matrix on current Native54 and Python611/package523. The normal and isolated combined-forced routes retain the existing 32 phases each, accepted OriginalGL references, whole-frame criteria, endpoint fields, resident work, three requested ForceLoss recoveries per route and cleanup requirements. The forced derivative must preserve the Native54 allocation-window implementation and differ only at the seven existing private planning seams (fan96, point96/layout20, generated-line2064). Native54 remains installed unchanged. Source/build transport, capture transport and the saved-only reader are prepared independently before Root executes source admissions, the isolated build and sequential GPU jobs. No current broad result is claimed yet. Earlier Native53 results remain historical; the completed68/126/24 checkpoint is retained without replay. Closed build/output assets will be compacted after their consumers finish. The original thirteen requirements remain open and cybersecurity work remains excluded.

Root has completed the [forced Source gate](../../../build/native54-python611-broad-forced-source-review-root-1/result.json), [build-tool Source gate](../../../build/native54-python611-broad-tools-source-review-root-1/result.json), [capture Source gate](../../../build/native54-python611-broad-capture-source-review-root-1/result.json) and [saved-reader Source gate](../../../build/native54-python611-broad-reader-source-review-root-1/result.json). The [actual isolated build](../../../build/evidence/native54-python611-broad-forced-build-root-1/result.json) closes exit0 with all42 targets, all44 CTests and the complete44-member binary archive; the [full original Root execution journal](../../../build/native54-python611-broad-build-outer-root-1/outer-observation.json) retains every phase and terminal return. The derivative is built externally with in-place installation disabled. Its independent saved build audit and the two actual GPU routes are pending; source controls and native CTests do not qualify those future outcomes.

The independent capture/reader compatibility review supersedes the first saved-reader Source before any saved-outcome execution: it finds a stale helper path and historical canonical hashes that require their exact retained physical copies. A fresh reader successor will bind those history mappings explicitly, retain the same scientific functions and thresholds, and receive its own Root Source admission. The first Source and its actual static receipt remain preserved; neither is a completed GPU outcome admission.

The [independent saved build audit](../../../build/evidence/native54-python611-broad-forced-build-review-line-1/result.json) is clear, and the [actual runtime-input admission](../../../build/evidence/native54-python611-broad-forced-runtime-inputs-root-1/result.json) binds its four archived artifacts, current identity and accepted OriginalGL references. The [corrected saved-reader Source2](../../../build/native54-python611-broad-reader-source-review-root-2/result.json) passes its actual Root gate and [independent static cross-review](../../../build/native54-python611-broad-reader2-cross-review-point-1/packet/result.json): all17 old-reference canonical conflicts map to exact admitted retained copies, current source/harness/native hashes remain direct, and all20 scientific functions plus the full37-span metadata inverse are unchanged. The [actual normal route](../../../build/evidence/native54-python611-broad-normal-root-1/driver-result.json) passes all10 cases and32 full frames,13 endpoint captures/849 logical rows and three requested ForceLoss API recoveries. Its child closes exit0 with cleanup and installed Native54 continuity checked; the [complete Root process journal](../../../build/native54-python611-broad-normal-outer-root-1/outer-observation.json) preserves the original launch, polls and terminal return. The isolated forced route and joint independent outcome admission are still pending.

The [actual isolated forced route](../../../build/evidence/native54-python611-broad-forced-root-1/driver-result.json) also passes all10 cases and32 full frames, with499 scene draws,13 endpoint captures/849 logical rows,181,632 guarded capture bytes and three requested ForceLoss API recoveries. Its [full Root execution journal](../../../build/native54-python611-broad-forced-outer-root-1/outer-observation.json) closes the real child exit0. The [joint saved-only outcome audit](../../../build/evidence/native54-python611-broad-gpu-outcome-review-line-1/result.json) is independently clear over35,232 physical inputs: all64 frames/196,608 RGBA bytes match the accepted OriginalGL references and each other; endpoint defined fields, physical guards/chunks, resident counters, passive ownership, recovery, real direct child identities, module origins and cleanup pass. Its [complete original audit journal](../../../build/native54-python611-broad-gpu-review-observation-line-1/observation.json) retains the single actual saved-reader execution without replaying either GPU route. The three requested ForceLoss API recoveries per route do not qualify uncontrolled hardware faults or timeouts.

After those readers close, Root's [actual closed-build compression](../../../build/native54-python611-broad-closed-compression-root-1/result.json) preserves1,540 files and238 directories across nine exact copied-source/build/evidence targets. All26 exact-file compact batches close exit0;601 files are selected and physical storage falls312,879,896 to167,377,026 bytes, reclaiming145,502,870 bytes. Every name, size, SHA, file ID, creation/modification clock and non-compression attribute is unchanged; current611 and installed Native54 four are directly rechecked. Vendor trees and dependency junctions are excluded. The [independent saved cleanup audit](../../../build/evidence/native54-python611-broad-cleanup-outcome-review-point-1/result.json) verifies the complete records, original logs and Root process closure without replaying compression or walking the target trees. The cumulative recorded Sprint25–28 saving is302,675,545 physical bytes. No files are deleted or moved.

The [final broader qualification checkpoint](../../../build/native54-python611-broad-qualification-checkpoint-root-1/progress.json) and [actual Root checkpoint-author journal](../../../build/native54-python611-broad-checkpoint-outer-root-1/outer-observation.json) bind the exact current identity, Source2 reader, source/build/runtime admissions, both32-frame routes, joint outcome and independently audited cleanup. Its reviewed author successor requires the completed Point cleanup admission and exact storage/receipt joins before sealing; the current identity seal is also pinned. The completed prior68/24/126 batch remains distinct, and no historical Native53 GPU pass is inherited. Remaining matching Native54 thin/integer/Text/fault/cancellation matrices and the broader original scientific, host, platform, performance and release requirements remain open. Cybersecurity work remains excluded.

### Sprint29: current Native54 integer sampling and Text qualification

Preparation is in progress for fresh128-frame integer-sampling and24-frame Text runs on current Native54/source611/package523. The existing accepted OriginalGL references and scientific acceptance rules remain fixed; historical Native53 Dawn frames confer no current pass. Capture adapters use one current identity admission per driver and a complete immutable handoff to their direct children, with no repeated child identity consumer. Saved readers are prepared independently and use completed identity metadata without producer replay. GPU jobs remain serialized and installed Native54 remains unchanged. The ordinary thin-line cap64 matrix needs a distinct three-method derivative and compiled artifact; the completed fan/point/generated-line broad derivative cannot be relabelled cap64. That build, the fault/cancellation matrices and broader original requirements remain pending. Closed outputs will be compacted after their readers finish. Cybersecurity work remains excluded.

Root completes the [integer capture Source gate](../../../build/typed-integer-native54-python611-source-review-root-1/result.json), [integer saved-reader Source gate](../../../build/typed-integer-native54-python611-reader-source-review-root-1/result.json) and [Text capture Source gate](../../../build/text-native54-python611-capture-source-review-root-1/result.json). The [actual current integer run](../../../build/evidence/typed-integer-native54-python611-root-1/result.json) closes exit0: one fresh Native54/Python611 child captures128 complete frames matching the retained accepted OriginalGL128 references, with resident work, seven requested ForceLoss API recoveries and logical cleanup passing. Its [complete original Root execution journal](../../../build/typed-integer-native54-python611-outer-root-1/outer-observation.json) retains the actual driver45032/direct child38636 process evidence and all launch/poll/terminal returns. Independent saved integer admission and the sequential Text24 run are pending; the producer pass alone does not complete this batch.

The [independent saved integer admission](../../../build/evidence/typed-integer-sampling-native54-python611-gpu-outcome-review-native-1/result.json) is clear across53,078 workspace pins and three external witnesses. It revalidates all128 accepted OriginalGL state/frame receipts and all128 new current Dawn frames,70 resident intervals with17 zero-work counters,136 scene draws,128 presentation passes, seven requested ForceLoss API recoveries, module origins, process closure and cleanup. Its [complete original audit journal](../../../build/typed-integer-native54-python611-reader-observation-native-1/observation.json) retains the single actual saved-reader execution. The [Text saved-reader Source gate](../../../build/text-native54-python611-reader-source-review-root-1/result.json) passes after62 focused metadata controls and two pre-freeze capture-wire corrections; all scientific helpers, four companions and the entire24-frame loop remain unchanged. The [actual Text capture](../../../build/evidence/text-native54-python611-gpu-attempt-root-1/result.json) passes all12 cases/24 complete frames against the accepted OriginalGL references and closes its direct child21936/driver26932 exit0. Its [full original Root journal](../../../build/text-native54-python611-outer-root-1/outer-observation.json) retains the actual launch, polls and terminal return. Independent saved Text admission, closed-asset cleanup and the final joint checkpoint are pending.

The [first saved Text audit](../../../build/evidence/text-native54-python611-outcome-review-point-1/result.json) refuses before its24-frame scientific block on a command metadata mismatch. Its [complete failed execution journal](../../../build/text-native54-python611-saved-outcome-observation-point-1/observation.json) remains preserved. Exact comparison finds only childargv index0 differs: the capture uses the backslash spelling in its frozen criteria, while the checker expects the forward-slash spelling in the identity row; both identify the same71b Python executable, and allother31 tokens and cwd are exact. [Root-admitted reader Source2](../../../build/text-native54-python611-reader-source-review-root-2/result.json) changes only that expected expression to the actual Source-owned criteria path. Every other26 parent member, all scientific helpers and the full24-frame comparison loop remain byte exact. Five focused controls pass without replaying the62 prior controls or the GPU capture; the fresh saved Source2 outcome remains pending.

The [independent saved Text Source2 outcome](../../../build/evidence/text-native54-python611-outcome-review-point-2/result.json) is now clear across41,404 workspace pins and three external witnesses. All12 cases/24 complete current frames, historical atlases, local geometry, texcoords, glyph metrics, actual DPI/anchor/transform uniforms and public graph/kernel reuse pass unchanged criteria; each resident interval retains17 zero-work counters. Its [complete original audit journal](../../../build/text-native54-python611-saved-outcome-observation-point-2/observation.json) closes the actual single saved-reader execution exit0 without replaying either capture. The failed Source1 result stays unpromoted, and the installed Native54 four remain exact.

Root's [closed-asset compression](../../../build/sprint29-closed-compression-root-1/result.json) preserves871 files and51 directories across14 explicitly named completed capture/reader/evidence roots, including the failed checker attempt. One exact-file compact batch compresses nine eligible files and reduces physical storage84,948,790 to79,082,963 bytes, reclaiming5,865,827 bytes. Names, logical sizes, SHA hashes, file IDs and creation/write clocks remain exact, with zero deletes or moves and current611/native4 directly rechecked. The [full Root operation journal](../../../build/sprint29-closed-compression-outer-root-1/outer-observation.json) retains the actual metadata process and terminal return. The [independent saved cleanup audit](../../../build/evidence/sprint29-cleanup-outcome-review-native-1/result.json) verifies all stored inventories, exact compact arguments/raw logs, storage arithmetic, current pins, actual consumer joins and Root process closure without replaying compression or walking the target trees. Recorded cumulative Sprint25–29 reclamation is308,541,372 physical bytes.

The [final joint checkpoint](../../../build/native54-python611-integer-text-qualification-checkpoint-root-1/progress.json) and [actual Root checkpoint journal](../../../build/sprint29-qualification-checkpoint-outer-root-1/outer-observation.json) bind both complete capture packets, exact retained arguments, original Root execution journals, independent saved admissions and their complete actual audit journals, current identity and independently audited cleanup. It qualifies152 new current frames against152 retained accepted reference frames at the two stated scopes. No canonical renderer source or installed native artifact changes in this batch. The distinct cap64 ordinary thin-line derivative and156-frame matrix, late-chunk fault/retry matrix, cancellation/loss/shutdown schedules and broader scientific/host/platform/performance/release conditions remain pending. The original thirteen requirements are not complete, and cybersecurity work remains excluded.

### Gap closure: culling and Linux Xlib lifetime

The [cull-both publication](../../../build/cull-both-publication-root-1/result.json) and [independent publication audit](../../../build/cull-both-publication-review-point-2/result.json) complete the three-file culling correction. The Windows isolated six-case comparison passes against its accepted OriginalGL reference, with exact whole-frame criteria and source-derived draw accounting. The [formal Native55 saved build audit](../../../build/evidence/native-pass-55-build-review-line-1/result.json) admits all42 targets,44 CTests and44 archived artifacts at source611/formal4131 plus tools4/package523. Native55 is built and admitted but is not installed; the four installed Windows Native54 files remain unchanged.

Linux is available through WSL using Mesa llvmpipe software Vulkan. The original relocated build and accepted Linux OriginalGL reference are independently admitted. The first usable Vulkan capture completes five cases and then aborts; the [GDB diagnosis](../../../build/linux-cull-warmup-diagnosis-native-3/result.json) identifies deferred Vulkan WSI cleanup accessing a retired Xlib Display. Failed attempts and partial outputs remain preserved. The [isolated lifetime proposal](../../../build/xlib-wsi-lifetime-implementation-native-1/result.json) retains Xlib owners through deferred surface deletion and explicit device destruction. Its [independent source review](../../../build/xlib-wsi-lifetime-source-review-point-1/result.json) and [Root source admission](../../../build/xlib-wsi-lifetime-source-review-root-1/result.json) are clear. The proposal remains isolated through the build and scientific checks below; its subsequent canonical publication is recorded separately.

The [fresh Linux build closure](../../../build/linux-wsi-build-outer-root-1/outer-observation.json) records all42 targets and44 passing CPU contract tests on the isolated lifetime proposal. The [first saved build audit](../../../build/evidence/linux-wsi-build-outcome-review-native-1/result.json) refuses on the CMAKE_CXX_COMPILER cache spelling. Fresh CMake stores the exact observed absolute compiler alias; the recovered parent cache used the recipe basename. The [Source2 reader](../../../build/linux-wsi-build-saved-native-2/source-seal.json) changes only that compiler-cache predicate and its fresh output path, preserving the literal configure command, generated compiler facts, Clang18.1.3, physical compiler hash, alias resolution and every other cache check. Its14 focused controls, independent code review and Root source gate pass. The [actual Source2 saved build audit](../../../build/evidence/linux-wsi-build-outcome-review-native-2/result.json) is clear. The first refusal stays preserved; the native build is not replayed.

The [fresh plain Source6 Vulkan capture](../../../build/evidence/linux-cull-candidate-root-6/result.json) passes all six cases and exits0 with actual Linux PID385; the repeated Xlib window lifecycle no longer crashes. Its [complete Root launch and terminal journal](../../../build/linux-cull-candidate-outer-root-6/outer-observation.json) retains the original warnings and process returns. The [capture Source6](../../../build/linux-cull-science-point-6/source-seal.json), [independent capture-source review](../../../build/linux-cull-science-review-native-6/result.json) and [Root source gate](../../../build/linux-cull-source-review-root-6/result.json) remain unchanged. The [independent saved joint audit](../../../build/evidence/linux-cull-candidate-review-native-6/result.json) is clear: all nine complete color/depth/stencil frames,27 arrays and17 semantic/physical user draws pass unchanged exact whole-frame criteria against accepted Linux OriginalGL3, with no excluded pixels.

The [reviewed publication Source](../../../build/xlib-wsi-publication-native-1/source-seal.json), [independent source review](../../../build/xlib-wsi-publication-review-point-1/result.json) and [Root completed source gate](../../../build/xlib-wsi-publication-source-review-root-1/result.json) admit the exact publisher and external observer. Root's [actual three-file publication](../../../build/xlib-wsi-publication-root-1/result.json) now closes exit0, preserving all three verified immediate-before files before any write. Its [external physical observations](../../../build/xlib-wsi-publication-physical-root-1/result.json) and [complete Root process journal](../../../build/xlib-wsi-publication-outer-root-1/outer-observation.json) confirm the actual direct-Base Python child, all seven before/after leaves and unchanged installed Windows Native54 four. Source611 changes two leaves and harness4135 changes three; package523 remains unchanged. The [independent saved publication admission](../../../build/xlib-wsi-publication-outcome-review-point-2/result.json) is clear across19,850 physical pins. Its WSL-local reader preserves all18 audit functions and passes45 focused path controls; the Windows-only reader remains unused. Formal Native56, installation and matching current regression matrices remain pending. Software WSL results do not qualify physical Linux GPU performance or macOS Metal; the user has no macOS machine. Prepublication Source6 or publication guards are not replayed after mutation; only the exact three old path/hash pairs map to their actual backups.

The [frozen Native56 ownership preparation](../../../build/native56-wsi-formal-prep-line-1/source-seal.json), [independent source review](../../../build/native56-wsi-formal-source-review-native-1/result.json) and [Root completed Source gate](../../../build/native56-wsi-formal-source-consumer-root-1/result.json) are clear. Root's [actual ownership author](../../../build/native56-wsi-ownership-root-1/result.json) creates the formal56/w42 manifest with86 owners:48 C++ and38 contracts. The new contract path is owned, the prior two C++ owners transfer exactly, and every other owner remains intact. Source parent55 and actual activation parent54 remain distinct. Source611/formal4131 plus tools4/package523, standard42 targets and44 CTests remain exact. The [complete Root author journal](../../../build/native56-wsi-ownership-outer-root-1/outer-observation.json) closes exit0. The [independent saved ownership admission](../../../build/evidence/native56-wsi-ownership-review-line-1/result.json) completes the actual owner consumer across4,797 pins. Root's [standard56/w42 snapshot freeze](../../../build/native56-freeze-outer-root-1/outer-observation.json) passes the full dependency-origin and integrity checks. The [actual standard Windows build](../../../build/native56-standard-build-outer-root-1/outer-observation.json) closes exit0 with all42 targets, all44 CTests and44 archived artifacts; its [independent strict saved admission](../../../build/evidence/native-pass-56-build-review-line-1/result.json) is clear. The [saved build-review Source gate](../../../build/native56-formal-build-audit-source-review-root-1/result.json) and [activation Source gate](../../../build/native56-activation-source-review-root-1/result.json) pass. The installation inputs and exact transaction record are prepared, and the actual four-file activation is running. The [new current identity Source gate](../../../build/native56-current-identity-source-review-root-1/result.json), [original126 transport Source gate](../../../build/native56-original126-transport-source-review-root-1/result.json) and [saved-reader Source gate](../../../build/native56-original126-reader-source-review-root-1/result.json) pass. Actual installed admission, stage/identity production and fresh rendering regressions remain pending.

Root's [actual Native56 activation](../../../build/evidence/native-pass-56/activation.json) now closes exit0. All four Native54 files are preserved in the committed transaction's immediate-before backups. The [independent installed audit](../../../build/evidence/native-pass-56-installed-review-line-1/result.json) is clear, including all four committed copies, archived binaries, staging, backups and immutable activation inputs. Its [complete original process journal](../../../build/native56-preferred-installed-review-observation-perf-1/observation.json) records the single actual saved-audit execution without replaying installation. The current Python stage and identity are being produced from this admitted Native56 installation; fresh rendering regressions remain pending.

The [new Python stage](../../../build/evidence/native56-current-python-stage-root-1/result.json) and [current identity](../../../build/evidence/native56-current-python-identity-root-1/identity.json) now pass. They bind current611 source, pure523 package, formal4131 plus four tools, installed Native56 and snapshot42 without borrowing prior GPU outcomes. The [full stage](../../../build/native56-current-python-stage-outer-root-1/outer-observation.json) and [identity](../../../build/native56-current-python-identity-outer-root-1/outer-observation.json) Root journals preserve the actual direct-Base metadata processes and terminal returns. The [independent saved identity audit](../../../build/evidence/native56-current-identity-review-native-1/result.json) is clear across29,999 workspace pins and three external witnesses, including both complete actual Root actor closures. Its [full execution journal](../../../build/native56-current-identity-saved-observation-native-1/observation.json) retains the single completed identity consumer. Root's ordinary17 regression job is running; affected109 follows only after terminal exit and cleanup. The [combined integer/Text code review](../../../build/native56-integer-text-source-review-native-1/result.json) and all four Root Source consumers pass; their actual current rendering jobs remain pending.

Root's [fresh ordinary17](../../../build/evidence/native56-original126-root-1/ordinary17/result.json) now passes all17 original tests with four expected deselections, actual hardware Vulkan and explicit cleanup. The [complete original Root journal](../../../build/native56-original17-outer-root-1/outer-observation.json) closes exit0. Affected109 is running sequentially. The inherited child performs four full identity admissions before testing; the [reviewed cache prototype](../../../build/original126-admission-cache-prototype-native-1/proposal-refined.json) reduces that to one per child while preserving independent copies, active Source namespace checks, final package checks and the parent's complete archive checks. Its48 synthetic controls pass; it remains an unexecuted future-epoch proposal with unset runtime roles.

Two further repairs are isolated from the installed build. The [distinct-face stencil proposal](../../../build/stencil-face-implementation-point-1/proposal.json), [independent source review](../../../build/stencil-face-source-review-native-1/result.json) and [Root completed Source gate](../../../build/stencil-face-source-review-root-1/result.json) are clear. It preserves instance/triangle order with complementary face draws, actual physical accounting and a separate final-SPIR-V replay proof. Its three CXX contracts, runtime encoding, full-frame oracle and host scope remain unqualified. The [capability-query proposal](../../../build/native56-r02-query-candidate-perf-1/result.json) corrects vertex-texture and uniform-byte enums and stops substituting sampler counts or bytes for independent array-layer/combined domains. Its actual isolated CPU candidate passes12/12; the baseline has3passes,6failures and3errors. The [independent code/saved-CPU review](../../../build/native56-r02-query-source-review-point-1/result.json) is clear. Neither repair is canonically published, and no current GPU result is inherited by them.

Closed archive compression reclaims2,485,113,685 physical bytes, and [closed Native55 cache compression](../../../build/native55-closed-cache-compression-root-1/result.json) reclaims194,280,126 more. Every retained file keeps its bytes and identity; no files are deleted or moved. A separate bytecode-cache deletion attempt was rejected before execution by automatic approval review with the reason "blocked by policy" and is not retried. The original thirteen requirements remain open, and cybersecurity work remains excluded.

The [fresh affected109](../../../build/evidence/native56-original126-root-1/affected109/result.json) now passes all109 original tests; together with ordinary17, all126 pass on the admitted installed Native56. Its [complete actual Root journal](../../../build/native56-affected109-outer-root-1/outer-observation.json) closes exit0 after explicit device cleanup. The [combined closed-job carrier](../../../build/native56-original126-outer-root-1/observation.json) preserves both complete original tool streams and actual child process edges; the independent saved126 review is running without another rendering job. The [first stencil CPU recipe attempt](../../../build/stencil-face-cpu-run-root-1/result.json) stops before any compiler or junction process because its copy predicate rejects20 declared license files. The failed partial staging and [full Root journal](../../../build/stencil-face-cpu-run-attempt1-outer-root-1/outer-observation.json) remain preserved; fresh recipes will admit only those declared license paths while retaining dependency-tree and escape refusals. Current integer128 capture is running sequentially; Text24 and closed Native56 cache compression remain pending.

The [independent saved126 review](../../../build/evidence/native56-original126-outcome-review-line-1/result.json) is now clear across31,557 pins:17+109 original tests,769 decoded arrays and299 exact comparison pairs. Its [complete original audit journal](../../../build/native56-original126-saved-observation-perf-1/observation.json) closes the single actual saved-reader job without a rendering replay. The [current integer128 capture](../../../build/evidence/typed-integer-native56-python611-root-1/result.json) and [Root launch/terminal journal](../../../build/native56-integer-capture-outer-root-1/outer-observation.json) close exit0 with explicit cleanup. Its [independent saved audit](../../../build/evidence/typed-integer-sampling-native56-python611-gpu-outcome-review-native-1/result.json) verifies all128 new frames against128 accepted reference frames across53,997 pins; the [complete actual audit journal](../../../build/native56-integer-saved-observation-native-1/observation.json) is closed. Current Text24 capture is running, and its saved review and Native56 cache compression remain pending.

The [corrected isolated stencil CPU build](../../../build/stencil-face-cpu-run-root-2/result.json) passes all three focused contracts after the narrow declared-license copy correction. The [full actual Root journal](../../../build/stencil-face-cpu-run-outer-root-2/outer-observation.json) closes exit0; Source1's failed partial staging remains preserved. Runtime.cpp and the full renderer are not compiled by this three-target run. The [stencil graphics fixture Source gate](../../../build/stencil-face-graphics-source-review-root-1/result.json) is complete for19 cases,22 frames and66 full attachment arrays, including four pre-pixel observability corrections. Its actual capture adapter, complete renderer build, independent OriginalGL reference, public baseline refusal and isolated normal/partition rendering remain unexecuted. The [missing mesh/layout and Visbrain fixture Source2 gate](../../../build/r01-missing-fixtures-source-review-root-2/result.json) is complete; Source2 fixes resource roots for staged and canonical capture locations while preserving all geometry, cameras and frame criteria. All five canonical fixture paths remain unpublished and their actual runtime/reference/host prerequisites remain open. A separate boolean-uniform lexical-scope candidate is isolated and uncompiled; no current source or installed native changes are claimed for these proposals.

Current Text qualification is complete: the [actual24-frame capture](../../../build/evidence/text-native56-python611-root-1/result.json), [Root process closure](../../../build/native56-text-capture-outer-root-1/outer-observation.json), [independent saved review](../../../build/evidence/text-native56-python611-outcome-review-point-1/result.json) and [complete audit journal](../../../build/native56-text-outcome-review-observation-point-1/observation.json) all close successfully. Installed Native56 therefore has completed independent reviews for original126, integer128 and Text24. The [closed Native56 cache compression](../../../build/native56-closed-cache-compression-root-1/result.json) reclaims106,434,560 physical bytes from607 closed intermediate files using ordinary NTFS compression; bytes, file identities and installed native leaves are preserved. The rejected bytecode deletion remains unperformed.

The [full isolated normal stencil renderer build](../../../build/stencil-face-renderer-run-root-2/result.json) now builds all42 targets and passes all44 CTests. Its [Root process journal](../../../build/stencil-face-renderer-run-outer-root-2/outer-observation.json), [independent saved build review](../../../build/evidence/stencil-face-renderer-outcome-review-native-2/result.json) and [complete audit journal](../../../build/stencil-face-renderer-saved-observation-native-2/observation.json) are closed. Runtime.cpp and the final shader replay proof were compiled; the43 PE artifacts and one layer manifest are admitted for this isolated build. Stencil pixels, the explicit baseline refusal and forced partition variant remain pending. The focused boolean-scope CPU baseline/candidate run is active in a separate isolated tree. The [mesh/layout upstream runtime preparation](../../../build/r01-mesh-layout-upstream-runtime-root-1/result.json) has completed with all517 upstream source files preserved in an exact521-member package; actual12-frame rendering remains pending. These isolated proposals are still unpublished and the broader thirteen-requirement release gap remains open.

The [boolean-scope CPU job](../../../build/r04-bool-cpu-run-root-1/result.json) and [complete Root process journal](../../../build/r04-bool-cpu-run-outer-root-1/outer-observation.json) now close successfully:22 original GLSL program pairs parse/link, the old production code reproduces the concrete bool-parameter syntax failure, and the isolated candidate passes the full shader_contract CTest. Its independent saved review is pending; conditional/macro legacy behavior and the wider R04 scope remain open. The [first mesh/layout upstream capture](../../../build/evidence/r01-mesh-layout-upstream-root-1/result.json) closes as FAILED_PRESERVED after six frames, with OpenGL invalid-operation1282 during annotation Text uniform lookup. Its [Root failure journal](../../../build/r01-mesh-layout-upstream-capture-attempt1-outer-root-1/outer-observation.json) is complete and all runtime pins remain intact; no twelve-frame admission is claimed. Context/resource lifetime across the separate fixture canvases is being investigated. The [stencil capture transport Source gate](../../../build/stencil-face-capture-source-review-root-1/result.json) is complete and the independent OriginalGL stencil capture is running; normal/forced candidate rendering remains pending.


The [independent boolean-scope saved audit](../../../build/evidence/r04-bool-scope-cpu-outcome-review-native-1/result.json) now passes at its narrow CPU scope: 22 original GLSL pairs, the preserved baseline bool-parameter failure and the candidate shader_contract result. Its [complete actual audit journal](../../../build/r04-bool-scope-saved-observation-native-1/observation.json) is closed. Macro/conditional legacy behavior and the wider R04 requirement remain open.

The [fresh stencil OriginalGL capture](../../../build/evidence/stencil-face-reference-root-1/result.json) and [independent saved reference2 admission](../../../build/evidence/stencil-face-reference-review-native-2/result.json) pass 19 cases, 22 frames and 66 complete attachment arrays. The [full saved-audit journal](../../../build/stencil-face-reference-saved-observation-native-2/observation.json) retains the single corrected-reader execution. The [first saved-reader origin-spelling refusal](../../../build/evidence/stencil-face-reference-review-native-1/result.json) and [Root environment prelaunch failure](../../../build/stencil-face-reference-prelaunch-attempt1-outer-root-1/outer-observation.json) remain preserved. These are accepted upstream references, not isolated-candidate stencil runtime qualification or all R05b closure.

The [Source3 mesh/layout readiness retry](../../../build/evidence/r01-mesh-layout-upstream-root-2/result.json) still fails after 6 of 12 frames, now at `glGetAttribLocation(program7,a_position)` with OpenGL invalid-operation 1282. Its [complete Root failure journal](../../../build/r01-mesh-layout-upstream-capture-attempt2-outer-root-1/outer-observation.json) is preserved; the readiness guard did not resolve the failure. A [fresh single-annotation diagnostic](../../../build/r01-annotation-diagnostic-point-1/diagnose.py) is queued to distinguish an intrinsic case failure from prior-canvas lifetime effects. No twelve-frame reference admission or confirmed root cause is claimed.

The [first partition renderer attempt](../../../build/stencil-face-renderer-partition256-run-root-1/result.json) fails on a 262-character MAX_PATH copy before CMake or any compiler stage; its [complete Root journal](../../../build/stencil-face-partition-renderer-attempt1-outer-root-1/outer-observation.json) is retained. The [reviewed short-path recipe](../../../build/stencil-face-partition-renderer-recipe-point-2/run_renderer.py) adds declared-path preflight and uses build/sfp2. That full 42-target/44-CTest build is running; no successful partition build, rendering result or thirteen-requirement closure is claimed. Cybersecurity work remains excluded.

The [short-path partition build](../../../build/sfp2/result.json) now passes all42 targets and44 CTests. Its [complete Root journal](../../../build/stencil-face-partition-renderer-outer-root-2/outer-observation.json), [independent saved admission](../../../build/evidence/stencil-face-partition256-renderer-outcome-review-native-2/result.json) and [complete audit journal](../../../build/stencil-face-partition-renderer-saved-observation-native-2/observation.json) are closed. The actual partition256 definition is enabled only for _dawn; actual DeviceInfo/grants remain unchanged. The [installed56 baseline](../../../build/evidence/stencil-face-baseline-root-1/result.json) reproduces the expected distinct-front/back stencil refusal, with its [Root process](../../../build/stencil-face-baseline-capture-outer-root-1/outer-observation.json) closed and pending state zero. The [normal isolated candidate capture](../../../build/evidence/stencil-face-candidate-root-1/result.json) passes19 cases,22 frames and66 exact whole attachment comparisons; its [complete Root journal](../../../build/stencil-face-candidate-capture-outer-root-1/outer-observation.json) is closed. Independent normal saved review and the forced-partition pixel comparison are running; no broad R05b or release closure is claimed.

The [fresh annotation-only diagnostic](../../../build/evidence/r01-annotations-diagnostic-root-1/result.json) succeeds for both unchanged phases, with its [full Root journal](../../../build/r01-annotation-diagnostic-outer-root-1/outer-observation.json) closed. It narrows the failure to a multi-case interaction without proving its cause. The [reviewed Source4 successor](../../../build/r01-missing-fixtures-source-native-4/source-seal.json) precisely restores the prior parser instance attribute, or deletes the injected observer when the method originally came from its class, before guaranteed canvas closure. Scene/readiness/scientific criteria stay exact;53 provider-free cleanup controls and the [finished Root Source gate](../../../build/r01-missing-fixtures-source-review-root-4/result.json) pass. The [new metadata handoff](../../../build/r01-mesh-layout-upstream-runtime-root-3/result.json) and [Root closure](../../../build/r01-mesh-layout-upstream-prepare-outer-root-3/outer-observation.json) preserve and reuse the original521 package and8518 donor without copying. The full12-frame Source4 rerun remains queued.

The [real public-query execution Source gate](../../../build/r02-public-query-source-review-root-1/result.json) is complete for two fresh baseline/candidate workers and five concrete query differences; runtime execution remains queued. The [merged stencil/thin qualification draft](../../../build/native56-stencil-thin-qualification-merge-native-1/proposal.json) resolves the runtime.cpp overlay collision. Independent whole-byte inverses reproduce both the normal stencil base and prior combined qualification runtime, with all eight planner seams and12 fault additions retained. This unfrozen derivative remains qualification-only with INPLACE=OFF; disabling fault APIs does not remove its forced planner limits. No canonical source or installed native files change in these isolated checks. The thirteen requirements remain open, and cybersecurity work remains excluded.

The [normal stencil saved review](../../../build/evidence/stencil-face-candidate-review-native-2/result.json) and [forced-partition saved review](../../../build/evidence/stencil-face-partition256-review-native-2/result.json) are now clear. Each admits19 cases,22 frames and66 complete attachment arrays; the forced route records99 elements across four instances and11 geometry chunks under its private256 cap, without rewriting actual device grants. The separate [OriginalGL PrimitiveId review](../../../build/evidence/stencil-face-reference-negative-review-native-2/result.json) confirms the draw completes, while the [candidate negative review](../../../build/evidence/stencil-face-candidate-negative-review-native-2/result.json) confirms the exact contextual refusal. These bounded results do not close all R05b state, shader-side-effect or performance requirements.

The [actual public-query baseline/candidate run](../../../build/evidence/r02-public-query-root-1/result.json) and [independent saved review](../../../build/evidence/r02-public-query-outcome-review-independent-1/result.json) pass. Five intended query changes and20 unchanged queries/four closed-device controls are checked through the real public API on matching actual hardware; the candidate changes one Python leaf and leaves installed native files unchanged. Broader allocation limits and R02 budgets remain open.

The [direct Source4 mesh/layout retry](../../../build/evidence/r01-mesh-layout-upstream-root-3/result.json) still fails after6 of12 frames at the annotation attribute lookup; the observer cleanup correction does not resolve it. A [passive first-four diagnostic](../../../build/evidence/r01-first-four-diagnostic-root-1/result.json) renders all eight frames. Both controlled GC diagnostics, [A without explicit collection](../../../build/evidence/r01-gc-boundary-diagnostic-A-root-1/result.json) and [B with collection between cases](../../../build/evidence/r01-gc-boundary-diagnostic-B-root-1/result.json), also render all eight frames and restore the original GC state. There is no A/B differential or established GC fix. A smaller diagnostic using the original six-case producer body is being prepared to remove the passive-logging confound; twelve-frame reference and host admission remain pending.

The [closed stencil-build compression](../../../build/stencil-renderer-closed-cache-compression-root-1/result.json) reclaims211,574,784 physical bytes from1,106 closed intermediate files, preserving bytes, file identities, clocks, current611 and all installed/isolated native leaves. No files are deleted or moved. The [two-variant composition](../../../build/native56-gap-composition-native-1/proposal.json) has independently reviewed maps for11 normal changed paths and14 qualification changed paths. Its qualification build recipe is being prepared with in-place installation disabled; no composite build or publication is claimed yet. The broader thirteen requirements remain open, including physical-platform checks unavailable on this machine. Cybersecurity work remains excluded.

The unchanged Source4 six-case producer body now renders all12 frames inside each small diagnostic wrapper: [default automatic GC](../../../build/r01-original-main-gc-default-diagnostic-wrapper-root-1/result.json) and [disabled automatic GC](../../../build/r01-original-main-gc-disabled-diagnostic-wrapper-root-1/result.json). Both preserve their separate original raw packets, runtime inputs and actual process closure, and restore GC and the original argv object. The wrapper runs remain diagnostic-only and show no GC differential. A single pyqt6-only preconstruction collection boundary is proposed for the fixture, matching upstream test cleanup; its sufficiency and the underlying failure cause remain unproven. The [combined qualification build recipe](../../../build/gap-qualification-renderer-recipe-perf-1/recipe.json) passes independent whole-helper and composition review. Root is compiling its14-path variant in build/gq1, with INPLACE=OFF, fault APIs enabled, all42 targets/all44 CTests requested, and no partition256 substitution or installed-file changes. Independent saved build review and fresh fault/cancellation/thin-line runtime checks remain pending.

The [actual combined qualification build](../../../build/gq1/result.json) and [complete Root journal](../../../build/gap-qualification-renderer-build-outer-root-1/outer-observation.json) now close exit0. All42 targets and44 CTests pass, and43 actual PE files plus the generated layer manifest are copied byte exactly into a44-member archive. The [independent saved build review](../../../build/evidence/gap-qualification-renderer-build-review-native-1/result.json) and [complete actual audit journal](../../../build/gap-qualification-renderer-saved-observation-native-1/observation.json) are clear over10,553 workspace inputs and one external witness. FileAPI confirms compilation of the changed runtime, bindings, SPIR-V and normalization units; the fault macro belongs only to _dawn, with INPLACE=OFF and no partition256 flag. Current611 and installed Native56 four remain exact. This is an isolated qualification artifact, not the normal installed renderer or a GPU fault-matrix pass.

The [Source5 fixture gate](../../../build/r01-missing-fixtures-source-review-root-5/result.json) completes77 inputs after36 provider-free controls and whole-byte Source4 inverses. Its only fixture behavior change collects unreachable closed Qt canvas cycles before each new pyqt6 canvas; geometry, readiness, observer cleanup and science stay fixed. The [fourth metadata handoff](../../../build/r01-mesh-layout-upstream-runtime-root-4/result.json) reuses the same521-member upstream package and8518-member donor without copying. The [fresh direct upstream capture](../../../build/evidence/r01-mesh-layout-upstream-root-4/result.json) now completes all six cases/twelve frames, with its [full Root closure](../../../build/r01-mesh-layout-upstream-capture-outer-root-4/outer-observation.json), no rendering or closure error, and runtime inputs preserved. Independent saved-reference admission and current-candidate parity remain pending. The earlier failures and successful diagnostic-only wrappers remain separate; no general Qt root cause or host/platform closure is inferred.

The [four-job fault transport Source gate](../../../build/native56-gap-chunk-fault-source-review-root-1/result.json) and [independent code/controls companion](../../../build/native56-gap-chunk-fault-source-review-point-1/result.json) are clear over81 Source inputs. Review fixes a guaranteed pre-render self-hash refusal: the handoff file is checked separately, while every other child witness must belong to the parent's immutable snapshot. The first actual unarmed baseline job is running on the admitted gq1 artifacts and exact qualification523 package; no fault GPU outcome is claimed yet. The three fault kinds follow its completed baseline.

The [first independent twelve-frame saved audit](../../../build/evidence/r01-mesh-layout-upstream-review-native-1/result.json) refuses an overstrict reader schema check, with its [full actual journal](../../../build/r01-mesh-layout-saved-observation-native-1/observation.json) preserved. The axes traces contain valid public zero-count DRAW commands; locked upstream Program permits them and GlirProgram intentionally skips their native draws. A narrow saved-reader successor retains these commands, requires at least one positive-count draw per phase, and keeps all full-frame, metadata, readiness and process checks. It does not recapture or alter the twelve reference frames. Candidate runtime metadata is independently reviewed but awaits a successful actual reference admission.

The [corrected saved-reference audit](../../../build/evidence/r01-mesh-layout-upstream-review-native-2/result.json) now admits the same twelve upstream frames, with its [complete audit journal](../../../build/r01-mesh-layout-saved-observation-native-2/observation.json) closed. The [current56 candidate metadata](../../../build/r01-mesh-layout-candidate-runtime-root-1/result.json) and [Root preparation journal](../../../build/r01-mesh-layout-candidate-prepare-outer-root-1/outer-observation.json) bind that admission without replaying the identity guard. The [actual candidate capture](../../../build/evidence/r01-mesh-layout-candidate-root-1/result.json) fails after four frames at the axes/colorbar scene: the native line consumer refuses the requested smooth-line policy. Its [full Root journal](../../../build/r01-mesh-layout-candidate-capture-outer-root-1/outer-observation.json) preserves the actual failure and completed shutdown. The installed native files and runtime remain unchanged. Twelve-frame candidate parity remains open; fixture semantics and exact-frame criteria are retained.

The [unarmed strip65 baseline](../../../build/evidence/native56-gap-chunk-fault-baseline-root-1/driver-result.json) and [guard-copy fault case](../../../build/evidence/native56-gap-chunk-fault-guard_copy-root-1/driver-result.json) both pass on the admitted combined qualification artifacts. Their actual Root journals are [baseline](../../../build/native56-gap-chunk-fault-baseline-outer-root-1/outer-observation.json) and [guard-copy](../../../build/native56-gap-chunk-fault-guard_copy-outer-root-1/outer-observation.json). Both retain the complete OriginalGL-equal frame; baseline returns all65 rows, while guard-copy reports the expected padding error and returns no logical rows. Each retires its ticket exactly once and completes shutdown with empty logical queues and pools. Destroyed-map is running; deferred collection and the independent four-job saved audit remain pending. These checks do not prove physical resource destruction, spontaneous hardware faults, normal-renderer qualification, or all R03 requirements. Cybersecurity work remains excluded.

The [destroyed-map](../../../build/evidence/native56-gap-chunk-fault-destroyed_map-root-1/driver-result.json) and [deferred-collection](../../../build/evidence/native56-gap-chunk-fault-defer_once-root-1/driver-result.json) jobs now also pass, with closed Root journals for [map failure](../../../build/native56-gap-chunk-fault-destroyed_map-outer-root-1/outer-observation.json) and [deferred retry](../../../build/native56-gap-chunk-fault-defer_once-outer-root-1/outer-observation.json). The former records a real failed MapAsync callback and completed validation error; the latter retains the ticket/Future across an empty first collection and returns all65 rows on retry without new encoding or submission. All four frames equal the complete OriginalGL frame and all four jobs complete cleanup. The [first independent saved audit](../../../build/evidence/native56-gap-chunk-fault-outcome-review-native-1/result.json) refuses before scientific checks because its metadata reader tries to JSON-decode a Python helper. The [reviewed Source2 gate](../../../build/native56-gap-chunk-fault-reader-source-review-root-2/result.json) changes only that code binding and fresh output names; its saved audit is running on the same four closed jobs. No graphics capture is replayed. The [seven-schedule cancellation Source gate](../../../build/native56-gap-cancellation-source-review-root-1/result.json) passes167 inputs; actual cancellation remains gated on the independent four-job admission.

The [normal composed renderer build](../../../build/gn1/result.json), [complete Root journal](../../../build/gap-normal-renderer-build-outer-root-1/outer-observation.json), [independent saved build admission](../../../build/evidence/gap-normal-renderer-build-review-native-1/result.json) and [complete saved-audit journal](../../../build/gap-normal-renderer-saved-observation-native-1/observation.json) now close successfully. All42 targets and44 CTests pass with44 archived artifacts. This separate normal source variant includes seven source substitutions and ten harness substitutions across eleven paths; the cache and actual compile definitions contain no qualification switches. INPLACE remains OFF, current611 and the installed Native56 files remain unchanged, and no formal future epoch or GPU qualification is inferred. The [four-frame diagnostic](../../../build/r01-mesh-layout-four-frame-diagnostic-perf-1/result.json) finds every byte equal for the candidate's grid and linked-view frames; the failed twelve-frame candidate and smooth-axis blocker remain open.

The [corrected independent four-fault audit](../../../build/evidence/native56-gap-chunk-fault-outcome-review-native-2/result.json) is now clear, with its [complete actual audit journal](../../../build/native56-gap-chunk-fault-saved-observation-native-2/observation.json) sealed. It admits all four unchanged complete frames, defined fields, canaries, callback/Future boundaries, exact-once retirement and logical cleanup on the same closed jobs. The seven cancellation inputs now bind that admission and the same baseline; the first pending-destroy run is underway. The cancellation saved reader retains all23 scientific functions and has passed35 selected controls plus four Source-support controls, with final source gates pending.

The [frozen ideal-area model comparison](../../../build/smooth-area-training-comparison-point-1/result.json) completes all24 training frames and73,728 RGBA bytes. All24 frames differ:744 pixels/bytes differ only in alpha, with maximum absolute error45; RGB matches exactly. Predictions and the single global formula were sealed before training image access. This disproves parity for that stated hypothesis on this calibration set; it does not identify the driver's filter or qualify production smooth lines. No formula is retuned, no pixels excluded, and the nine frozen future predictions and eight reserved holdouts remain untouched. The twelve-frame current candidate gap remains open.

The [first cancellation schedule](../../../build/evidence/native56-gap-capture-cancellation-pending_destroy-root-1/driver-result.json) passes pending destruction with zero logical/raw bytes, no native ticket retirement, one-time charge release, repeated empty collection and complete cleanup. Its [full Root journal](../../../build/native56-gap-capture-cancellation-pending_destroy-outer-root-1/outer-observation.json) is closed. The other six schedules and joint independent saved audit remain pending. The [saved-reader Source gate](../../../build/native56-gap-cancellation-reader-source-review-root-1/result.json) passes225 required inputs without executing outcomes.

The [closed combined-build cache compression](../../../build/gap-renderer-closed-cache-compression-root-1/result.json) preserves1,106 temporary compiler files within84 explicitly declared Release intermediate directories and reclaims225,976,320 physical bytes across47 successful compact batches. File bytes, identities and creation/write clocks, current611, installed Native56 four and both isolated archive sets remain exact. No files are deleted or moved. The [full Root operation journal](../../../build/gap-renderer-closed-cache-compression-outer-root-1/outer-observation.json) is retained.

The [Visbrain CP311 environment metadata](../../../build/r01-visbrain-upstream-runtime-root-1/result.json) admits11,235 unchanged environment members,137 installed host-source leaves and148 source-archive authority rows, without a rendering claim. The [first actual upstream capture](../../../build/evidence/r01-visbrain-upstream-root-1/result.json) stops before drawing because its module-origin checker passes a JSON2 file reference to a path constructor. The [full failure journal](../../../build/r01-visbrain-upstream-capture-outer-root-1/outer-observation.json) is closed. A fresh transport successor will correct that single representation mismatch and retain the frozen fixture and two-frame/export criteria; Source1 and its failed output remain unchanged.

The [second cancellation control](../../../build/evidence/native56-gap-capture-cancellation-pending_abort_control-root-1/driver-result.json) also passes, with [complete Root closure](../../../build/native56-gap-capture-cancellation-pending_abort_control-outer-root-1/outer-observation.json). Pending abort reports its required failed terminal, no logical/raw bytes or native ticket retirement, one-time charge release and full cleanup. The submitted open-paint abort schedule is running; joint seven-schedule admission remains pending.

The [corrected Visbrain Source2 gate](../../../build/r01-visbrain-upstream-transport-source-review-root-2/result.json) and [fresh environment metadata](../../../build/r01-visbrain-upstream-runtime-root-2/result.json) pass. Both metadata manifests have identical11,235-member namespaces/hashes. The [actual Source2 capture](../../../build/evidence/r01-visbrain-upstream-root-2/result.json) reaches the unchanged public screenshot call, then fails restoring its canvas size: pinned Visbrain passes upstream physical-size floats to PyQt5 resize(), which accepts integer dimensions. Its [full Root journal](../../../build/r01-visbrain-upstream-capture-outer-root-2/outer-observation.json) closes exit1 and complete environment continuity is confirmed. This is an upstream workflow failure, not a host parity pass. No host source, dimensions, fixture criteria or pixel comparisons are patched to admit it. A bounded public show/event-processing readiness proposal is under review; no further actual capture is authorized yet.

The [submitted open-paint abort](../../../build/evidence/native56-gap-capture-cancellation-submitted_open_paint_abort-root-1/driver-result.json), [submitted destruction control](../../../build/evidence/native56-gap-capture-cancellation-submitted_destroy_control-root-1/driver-result.json) and [pending explicit loss](../../../build/evidence/native56-gap-capture-cancellation-pending_loss-root-1/driver-result.json) now pass, bringing the total to five of seven schedules. The submitted controls preserve successful native retirement independently of their failed/cancelled diagnostic terminal; pending loss creates no native ticket retirement. All return zero logical/raw bytes and complete cleanup. Their complete Root process journals are retained. Submitted loss and retained-Future shutdown remain pending, followed by the independent joint audit.

The [sealed12-frame alpha/DITHER diagnostic](../../../build/evidence/smooth-alpha-dither-diagnostic-root-1/result.json) and [complete Root journal](../../../build/smooth-alpha-dither-diagnostic-outer-root-1/outer-observation.json) close exit0 on the exact recorded training renderer. Every complete on/off pair is byte-identical. Solid quad alpha0,1/4,1/2,3/4,1 yields0,64,127,191,255; the known vertical line retains six partial pixels at alpha164 in both arms. These observations rule out DITHER as the explanation within this test; they neither identify a global driver coverage/UNORM rule nor qualify a replacement smooth-line model. No formula, frozen predictions or reserved data is changed. An independent saved diagnostic audit is being prepared.

The [thin-line producer Source gate](../../../build/native56-gap-thin-source-review-root-1/result.json) passes131 required inputs, and the [independent saved-reader Source gate](../../../build/native56-gap-thin-reader-source-review-root-1/result.json) passes229. Its two actual route inputs bind the separate completed unflagged gn1 and forced gq1 builds, compiled pure packages and archive sets. All nine saved scientific functions and four constants remain exact, with30 metadata and four Source controls passing. The two78-frame captures and joint156-frame saved outcome audit have not yet run.

All seven cancellation schedules now pass. The [submitted-loss result](../../../build/evidence/native56-gap-capture-cancellation-submitted_loss-root-1/driver-result.json) records one failed native retirement and no returned logical/raw bytes. The [retained-mapping shutdown result](../../../build/evidence/native56-gap-capture-cancellation-retained_map_future_shutdown-root-1/driver-result.json) also closes successfully with complete cleanup. Both complete Root journals are retained; the independent seven-schedule saved audit is running. These bounded controls do not establish physical device destruction or spontaneous hardware loss.

The [independent Alpha12 saved audit](../../../build/evidence/smooth-alpha-dither-saved-review-native-1/result.json) is clear, including full frame/state/upload joins, distinct launcher and worker identities, provider preservation and current611/native4 preservation. The new ten-frame factorization diagnostic has passed two full code reviews and39 synthetic controls. Its Source is frozen; no ten-frame graphics capture has run yet. Compatibility of its exact coverage intervals is an observation, not a capture acceptance criterion or production model qualification.

The reviewed public canvas-readiness sequence resolves the pinned Visbrain screenshot failure. The [third upstream capture](../../../build/evidence/r01-visbrain-upstream-root-3/result.json) completes both full256x256 RGBA frames and the public PNG export, with exact screenshot/frame equality, actual canvas closure and all11,235 environment members preserved. Its [complete Root journal](../../../build/r01-visbrain-upstream-capture-outer-root-3/outer-observation.json) closes exit0. Independent saved admission is being prepared; candidate ABI and host/platform qualification remain separate work. The normal thin-line route is now running, with its forced route queued.

The [independent seven-schedule cancellation audit](../../../build/evidence/native56-gap-cancellation-outcome-review-native-1/result.json) is now clear, with its [full original process stream](../../../build/native56-gap-cancellation-saved-observation-native-1/observation.json) closed. All seven return no logical bytes or extra native work. The retained-Future shutdown preserves only the already-mapped2064-byte part; it does not establish resumed rendering, device recreation or spontaneous hardware failure behavior.

Both [normal](../../../build/evidence/native56-gap-thin-normal-root-1/driver-result.json) and [forced](../../../build/evidence/native56-gap-thin-forced-root-1/driver-result.json) thin-line routes pass13 cases and78 full frames each, with actual child closure, complete cleanup and current611/native56 preservation. Both Root process journals close exit0. Their joint156-frame independent saved audit is next. The [Visbrain independent upstream admission](../../../build/evidence/r01-visbrain-upstream-review-native-1/result.json) is clear for exactly two frames and one export; candidate ABI, candidate parity and broader host/platform qualification remain open.

The [ten-frame alpha factorization capture](../../../build/evidence/smooth-alpha-factorization-diagnostic-root-1/result.json) and [complete Root journal](../../../build/smooth-alpha-factorization-diagnostic-outer-root-1/outer-observation.json) close exit0. Both groups preserve RGB across shader alphas. All768 pixels admit a common per-pixel coverage interval under each separately declared exact-real and one-binary32-RNE multiplication hypothesis, and every interval contains a binary32 value. The six partial line pixels produce alpha0,41,82,123,164 across the five alphas; quad values remain0,64,127,191,255. The tested arithmetic allows these observations with constant coverage; the earlier ideal-area discrepancy remains unexplained. It does not identify a coverage kernel or qualify a smooth-line implementation. Independent saved integrity review is authorized after its code review; shared exact math provenance is explicit. The nine frozen future predictions and eight reserved holdouts remain untouched.

The [factorization saved integrity audit](../../../build/evidence/smooth-alpha-factorization-saved-review-point-1/result.json) now clears all ten full frames, state/upload/GLIR/process joins and provider/current preservation. The exact interval math is explicitly copied reviewed code, not an independently derived algorithm; neither model nor driver qualification follows.

The [first joint thin saved audit](../../../build/evidence/native56-gap-thin-outcome-review-native-1/result.json) refuses before current/build/reference or scientific comparison: its reader requests the obsolete contract field `runtime_success_defaults`, absent from the frozen producer contract. The two passed78-frame captures remain unchanged. A fresh saved-reader successor will check the actual mandatory runtime contract and preserve all scientific predicates; Source1 and its refusal are retained. No graphics rerun is needed for this reader correction.

The [corrected thin-reader Source2 gate](../../../build/native56-gap-thin-reader-source-review-root-2/result.json) passes252 required pins and30 actual-contract/schema controls. Its [saved audit](../../../build/evidence/native56-gap-thin-outcome-review-native-2/result.json) reaches current56 continuity, then refuses before route comparison because the old OriginalGL receipt names a pre-change `cpp/runtime_point_partition.hpp` without a matching historical backup alias in the current identity. Its [full process record](../../../build/native56-gap-thin-saved-observation-native-2/observation.json) is closed. The next narrow reader correction must bind the exact old path/hash to retained before bytes and check all remaining reference pins; it must preserve every scientific check and both failed readers. The captures remain unchanged.

The normal eleven-file publication package has passed full Root and independent code review plus31 metadata controls. Its [frozen Source](../../../build/gap-normal-publication-perf-1/source-seal.json) and [independent frozen review](../../../build/gap-normal-publication-source-review-point-1/result.json) preserve exact backups, external observations and source7/harness10/package1 map changes. No canonical publication, native installation or formal57 build has run. Its thin-reader prerequisite will be updated in a fresh metadata successor after the historical reference correction is admitted; canonical611 and installed Native56 remain unchanged meanwhile.

The [thin-reader Source3 gate](../../../build/native56-gap-thin-reader-source-review-root-3/result.json) passes289 required pins after31 resolver/inverse and22 actual-publication-schema controls. The exact old point-partition path/hash maps only to its already admitted before-file backup; all10,392 old reference pins remain required. The independent Source3 saved audit is running against the unchanged156 captured frames. No graphics replay occurs.

The [normal publication Source2 gate](../../../build/gap-normal-publication-source-review-root-2/result.json) now binds the corrected thin-reader Source3, with39 controls and unchanged complete publisher/observer bodies. Its actual eleven-file application remains held until that saved audit and its process record close successfully. The [pure formal57/w43 ownership projector](../../../build/gap-normal-formal57-root-1/project_manifest.py) is also prepared and independently code-reviewed;17 controls check ten existing-owner transfers, unchanged86-owner totals and actual activation56 protection. No formal57 ownership artifact, compilation, installation or matching final-artifact qualification is claimed yet.

The [joint thin Source3 saved audit](../../../build/evidence/native56-gap-thin-outcome-review-native-3/result.json) is clear for all156 full frames/479,232 RGBA bytes and926 OriginalGL endpoint rows, with exact normal/forced draw accounting, actual child closure, cleanup and installed56 continuity. Its [six-return original process record](../../../build/native56-gap-thin-saved-observation-native-3/observation.json) is closed. Both earlier reader refusals remain retained; no GPU test was repeated.

Root has now [applied the eleven reviewed normal source files](../../../build/gap-normal-publication-root-1/result.json). All eleven immediate-before backups were verified before writes. The [external physical observer](../../../build/gap-normal-publication-physical-root-1/result.json) and [complete Root process record](../../../build/gap-normal-publication-outer-root-1/outer-observation.json) close exit0, with exact source7/harness10/package1 changes and unchanged installed Native56 four. This integrates the validated stencil-state/batching corrections, public capability-query correction and GLSL boolean-scope correction into canonical source. Independent saved publication admission and formal57/w43 ownership/build/activation follow; no old current56 source guard is replayed after mutation.

The [independent saved publication audit](../../../build/gap-normal-publication-outcome-review-point-1/result.json) now clears all eleven canonical files and immediate-before backups, source611, formal harness4131+tools4, package523, actual observer/Root process joins and unchanged installed Native56 four. It also verifies the completed gn1 and joint thin Source3 prerequisites through exact historical path/hash projections; no graphics or publication was replayed. Its [reviewed reader Source gate](../../../build/gap-normal-publication-saved-source-review-root-1/result.json) passed93 required pins.

Formal57/w43 ownership preparation preserves42 targets,44 contract tests and86 owners while transferring the six changed native leaves and four changed contracts. Root reviewed the complete author, saved consumer, freezer and support, verified both whole-file inverses and the unchanged pure projector, and checked the actual completed publication receipt against the future ownership metadata wire. Independent Source review, actual ownership creation and the unchanged standard freeze/build sequence remain next; no formal57 compilation or installation is claimed yet.

The [formal57 ownership manifest](../../../build/gap-normal-ownership57-root-1/ownership-manifest.json) is now created and its [independent saved audit](../../../build/evidence/gap-normal-ownership57-review-native-1/result.json) clears49,874 physical input pins, the actual Root author process and all86 owners. Source and activation parents are both56, with actual activated56 binaries protected. A pre-write string/Path failure in the preparation freezer was corrected and retained with its failed attempt; the active author, consumer and both Source helpers were checked for the same launch seam. The unchanged [standard freeze preflight](../../../build/native57-standard-freeze-preflight-outer-root-1/outer-observation.json) passes. Actual snapshot capture is running; no compilation or installed replacement has occurred yet.

The [standard build-audit Source gate](../../../build/native57-formal-build-audit-source-review-root-1/result.json) passes84 required pins, and the [activation Source gate](../../../build/native57-activation-source-review-root-1/result.json) passes56. They retain the admitted strict build inspector and exact-copy/backup/rollback/installed-scanner behavior. The build metadata assembler's parent input names the completed56 specification; its future output remains57. New current57 identity/stage and matching normal Thin13 transport are being prepared with actual build and activation rows still required late. The stage must contain522 unchanged parent package copies plus the reviewed parser replacement, total523; no final57 graphics pass is inherited.


The [formal57 standard build](../../../build/evidence/native-pass-57/status.json) now closes exit0 after all42 targets and44 CTests, with44 archived artifacts and unchanged installed56 binaries. Its [complete original Root process](../../../build/native57-standard-build-outer-root-1/outer-observation.json) is closed, and the [actual57 build specification](../../../build/native57-composed-standard-build-inputs-root-1/input-spec.json) binds the frozen w43 source, owner57, four complete proof files and that exact process stream. Independent saved build admission is running; activation has not occurred.

The [current57 identity/stage Source gate](../../../build/native57-current-identity-source-review-root-1/result.json), [final57 normal Thin13 producer Source gate](../../../build/native57-thin-normal-source-review-root-1/result.json) and [normal saved-reader Source gate](../../../build/native57-thin-normal-reader-source-review-root-1/result.json) now pass. The reader preserves all nine scientific functions, four constants and full frame/reference criteria;45 metadata and four support controls pass. These are preparation gates. Actual installation, Python stage/identity admission and the matching78-frame normal run remain required; prior isolated GPU results are not inherited. Cybersecurity work stays excluded.


The [independent formal57 build audit](../../../build/evidence/native-pass-57-build-review-native-1/result.json) is clear for57/w43, all42 targets,44 CTests,44 archived artifacts and49,926 physical pins; its [complete original audit stream](../../../build/native57-standard-build-saved-observation-native-1/observation.json) is closed. Root authored the exact fifteen-key installation inputs and [durable approval](../../../build/evidence/native-pass-57/activation-approval.json). The [first preflight](../../../build/native57-activation-preflight-outer-root-1/outer-observation.json) refused the prepared command's absolute approval path before any copy. The held installer requires a canonical workspace-relative role; correcting only that operator argument yields a [successful second read-only preflight](../../../build/native57-activation-preflight-outer-root-2/outer-observation.json) with the same approved artifacts and unchanged frozen code. Actual four-file activation is now running; installed admission and graphics qualification remain pending.

The [saved current57 identity-reader Source gate](../../../build/native57-current-identity-saved-source-review-root-1/result.json) is complete after full Root and independent code review,169 independent static checks and18 selected closure controls. It binds typed positive actor/Root process identities, complete original tool streams, exact stage/identity arguments and one completed new57 identity consumer. Its actual stage/identity inputs remain late. The [completed-build handoff](../../../build/native57-current-identity-inputs-root-1/build-handoff.json) is derived only from the successful formal57 build admission; it grants no graphics or platform result.


The [actual Native57 activation](../../../build/evidence/native-pass-57/activation.json) and [complete Root transaction](../../../build/native57-activation-outer-root-1/outer-observation.json) now close exit0. All four installed artifacts match the formal57 archive, and the actual Native56 before-files are retained. The [independent installed57 audit](../../../build/evidence/native-pass-57-installed-review-native-1/result.json) is clear over49,954 inputs, all four exact committed copies, backups and the complete immutable activation archive. Its [full original audit stream](../../../build/native57-installed-audit-saved-observation-native-1/observation.json) is closed. Device qualification remains pending.

The [current57 Python stage](../../../build/evidence/native57-current-python-stage-root-1/result.json) passes with523 pure package members and no staged native binaries. Its [full Root process](../../../build/native57-current-python-stage-outer-root-1/outer-observation.json) binds the actual actor PID and original command/returns. Matching identity creation is running; independent identity admission and the final-artifact78-frame normal thin-line capture follow.

The [closed Native57 compiler-cache compression](../../../build/native57-closed-cache-compression-root-1/result.json) recovers112,285,815 bytes measured by GetCompressedFileSizeW across553 object/debug/tracker files in24 explicit compact batches. All selected bytes, file identities, creation/modified clocks, current611,44 archived artifacts, installed57 four and actual before56 four remain exact. No files are deleted or moved, no WOF/EXE compression is used, and rejected bytecode deletion is not retried. The [complete Root cleanup process](../../../build/native57-closed-cache-compression-outer-root-1/outer-observation.json) is closed. Cybersecurity remains excluded.

The [current57 Python identity](../../../build/evidence/native57-current-python-identity-root-1/identity.json) is now created successfully from the admitted57/w43 build, installed four and matching523-member stage. Its [complete Root process](../../../build/native57-current-python-identity-outer-root-1/outer-observation.json) closes exit0 and binds the actual identity actor PID40152. The independent saved consumer is running once against the actual stage, identity, seals and original Root streams. Its result remains required before the final57 normal78-frame capture; no earlier GPU result is promoted.

The [independent current57 identity review](../../../build/evidence/native57-current-identity-review-native-1/result.json) is now clear with no findings over50,588 workspace inputs and three external witnesses. It admits the actual stage and identity process closures, exact57/w43/611/523/formal4131+tools4 and one completed current57 consumer. Its [full original process stream](../../../build/native57-current-identity-saved-observation-native-1/observation.json) is closed. Root has retained the actual runtime inputs and literal command before starting the final57 normal13-case/78-frame driver once.

The [actual final57 normal thin-line capture](../../../build/evidence/native57-thin-normal-root-1/driver-result.json) closes exit0 with all13 cases and78 complete frames, actual child46608 closed, all cleanup receipts true and installed57 four unchanged. The [complete original Root stream](../../../build/native57-thin-normal-outer-root-1/outer-observation.json) binds actual driver53976, the one full parent identity admission and zero child admissions. The independent frozen saved reader is now running once on the actual outputs and accepted OriginalGL reference. Forced routes, failure/cancellation, smooth lines and broader qualifications remain outside this capture.

The new [original126 transport Source gate](../../../build/native57-original126-transport-source-review-root-1/result.json) and [saved-reader Source gate](../../../build/native57-original126-reader-source-review-root-1/result.json) are clear over150 and155 unique inputs. The [independent source review](../../../build/native57-original126-source-review-native-1/result.json) verifies four whole-file metadata inverses, four exact scientific transport copies, all23 unchanged scientific reader functions,769 arrays/299 comparisons and32 selected metadata controls. Its [complete review stream](../../../build/native57-original126-review-observation-native-1/observation.json) retains the prefreeze backup-field correction and an independent writer's count refusal; corrected closure preserves both. The original first draft and four before-files remain retained. The frozen helper's additive reader count157 deduplicates to155 actual required paths; both Root and independent Source consumers use the exact union. Root has started ordinary17 once from the admitted actual57 identity; affected109 follows its successful terminal and cleanup. No original126 result is claimed yet.

The [independent final57 normal thin-line saved audit](../../../build/evidence/native57-thin-normal-outcome-review-native-1/result.json) is clear with no findings across52,080 workspace inputs and three external witnesses. All78 full frames/239,616 bytes equal accepted OriginalGL; its926 typed reference endpoint rows and transform-feedback guards are exact. The typed endpoint evidence belongs to the reference, with no new native endpoint or canary claim. Actual process closure, zero ordinary endpoint-compute query counters, installed57 continuity and cleanup pass. The [complete actual saved-review journal](../../../build/native57-thin-normal-saved-observation-native-1/observation.json) closes the single saved-reader invocation without replay. This closes the final-artifact normal13-case scope; forced/fault/cancellation, broader R03, smooth lines, platforms and release performance remain separate.


The [integer producer Source gate](../../../build/native57-integer-capture-source-review-root-1/result.json), [integer reader gate](../../../build/native57-integer-reader-source-review-root-1/result.json), [Text producer gate](../../../build/native57-text-capture-source-review-root-1/result.json) and [Text reader gate](../../../build/native57-text-reader-source-review-root-1/result.json) now pass. The [independent combined review](../../../build/native57-integer-text-source-review-native-1/result.json) verifies17 whole-file inverses,227 held files,139 held function bodies and the exact four frozen Sources. The [retained capture commands](../../../build/native57-integer-text-runtime-prep-point-1/result.json) bind the actual current57 identity, installed four and accepted reference roles. No new128-frame integer or24-frame Text rendering result is claimed by these preparation checks.

The [stencil producer Source gate](../../../build/native57-stencil-source-review-root-1/result.json) and [saved-reader gate](../../../build/native57-stencil-reader-source-review-root-1/result.json) pass132 and117 required inputs. The [independent corrected-code review](../../../build/native57-stencil-review-point-1/proof-result.json) passes800 checks; it caught and resolved identity-context field placement and a missing hashlib import before Source freeze. All19 positive cases,22 frames,66 attachments and the original negative scientific criteria remain held. The [combined frozen Source companion](../../../build/native57-stencil-source-review-point-1/result.json) is clear, and [actual-runtime capture arguments](../../../build/native57-stencil-runtime-inputs-root-1/result.json) are retained. Rendering and saved-outcome review remain pending.

The [actual final57 ordinary17 regression](../../../build/evidence/native57-original126-root-1/ordinary17/result.json) now closes exit0:17 executed, zero failures, errors or skips, logical GPU cleanup true, complete50647-input before/after equality and unchanged installed57 four. Its [complete original Root stream](../../../build/native57-original17-outer-root-1/outer-observation.json) binds driver1816 and the actual Windows redirector edge to worker21556. Root started affected109 once after that closure; the combined126 scientific saved audit still requires its successful result. The held raw transport scope retains its historical Native54 label; current-artifact authority comes from the actual57 identity and exact runtime joins.


The [public-query producer Source gate](../../../build/native57-public-query-source-review-root-1/result.json) and [saved-reader gate](../../../build/native57-public-query-reader-source-review-root-1/result.json) now pass 90 and 105 required inputs. The [independent code proof](../../../build/native57-public-query-review-point-1/proof-result.json) passes 2,024 checks; the [combined frozen Source companion](../../../build/native57-public-query-source-review-point-1/result.json) binds the full 107-input union. Exact before-parser copies provide the baseline, while the candidate uses the actual current 523-member stage; both workers must use the same final57 native four. The unchanged scientific contract contains 20 total live probes, five expected differences, 15 unchanged pairs and four closed-canvas controls per worker. [Actual capture inputs and commands](../../../build/native57-public-query-runtime-inputs-root-1/result.json) are retained. No current57 public-query runtime pass is claimed yet.

The [WSL refresh map](../../../build/native57-linux-refresh-map-perf-1/note.md) establishes that the admitted Linux source3 maps equal formal56 before normal11. Root's [read-only WSL readiness process](../../../build/native57-linux-readiness11-outer-root-1/outer-observation.json) physically verifies all eleven affected before-files and confirms that three proposed fresh source/build/output paths are unused, using Linux CPython 3.12.8. This check does not cover the full source or dependency namespaces and invokes no compiler or GPU. Fresh current57-source Linux build/reader preparation is in progress; compilation, independent build admission and a matching software-Vulkan capture remain required. Native Linux hardware, performance and unavailable macOS requirements remain open.

The [current57-source Linux build Source gate](../../../build/native57-linux-build-source-review-root-1/result.json) and [saved-reader Source gate](../../../build/native57-linux-build-saved-source-review-root-1/result.json) now pass. The [independent code proof](../../../build/native57-linux-build-review-point-1/proof-result.json) passes 359 checks, preserving five complete file inverses and 40 held function bodies; its [frozen Source companion](../../../build/native57-linux-build-source-review-point-1/result.json) covers the full 55-input union. Root separately verifies that companion and binds the actual check into both complete gate journals. The [retained fresh-build command](../../../build/native57-linux-build-actual-arguments-root-1/launch.json) targets new source, build and output directories. Full dependency/source admission, all 42 targets and 44 CTests, independent build admission and matching software-Vulkan rendering remain pending; source gates grant no runtime result.

The [remaining qualification refresh map](../../../build/native57-broad-refresh-map-native-1/note.md) confirms that all 611 declared normal source digests equal the previously admitted normal candidate. The existing final57 normal78 result is reused as completed evidence. Forced78, fault4 and cancellation7 need a distinct qualification artifact with private compiled controls; their metadata adapters are being prepared with mandatory new qualification roles left unbound. Old qualification results remain lineage evidence. Partition256 requires a separate compiled variant, and neither variant is installed as the normal renderer. Cybersecurity remains excluded, and the nine frozen predictions and eight holdouts remain untouched.

The [actual affected109 group](../../../build/evidence/native57-original126-root-1/affected109/result.json) now closes exit0 with 109 executed, zero failures, errors or skips, 416 sealed output files, complete 50,647-input before/after equality and unchanged installed57 four. The [full Root process journal](../../../build/native57-affected109-outer-root-1/outer-observation.json) retains the single actual session through terminal closure, driver56720 and the redirector54568 to worker61280 edge. Logical shutdown leaves zero live renderer resources and 252 Vulkan allocations matched by 252 frees; these counters do not qualify physical memory or performance. The [combined original126 carrier](../../../build/native57-original126-outer-root-1/observation.json) is authored from both complete original tool streams. One independent saved126 audit is authorized from the exact emitted command. Root then starts the fresh integer128 driver once; Text, stencil, query and WSL jobs remain serialized behind it.

The [independent final57 original126 saved audit](../../../build/evidence/native57-original126-outcome-review-line-1/result.json) now clears all 126 original tests, 769 decoded numeric arrays and 299 exact comparisons with no findings. It also verifies resident/recovery/cleanup behavior, actual process closures and installed57 continuity across 52,165 checked inputs. Its [complete original review stream](../../../build/native57-original126-saved-observation-perf-1/observation.json) closes the one saved-reader invocation; no producer is replayed.

The [fresh final57 integer128 capture](../../../build/evidence/typed-integer-native57-python611-root-1/result.json) passes all 128 new candidate frames against the retained accepted OriginalGL128. Driver1280 and direct child52348 close exit0, all protected inputs and installed57 four remain unchanged, and logical GPU cleanup passes. The [complete Root capture stream](../../../build/native57-integer128-outer-root-1/outer-observation.json) is closed. [Actual saved-reader inputs](../../../build/native57-integer128-saved-inputs-root-1/inputs.json) and its exact command are retained for one authorized independent audit. The Text24 driver is now running once; its rendering result remains pending.

The [unfrozen Linux software-rendering adapter correction](../../../build/native57-linux-gpu-prep-point-1/review-packet.json) resolves two Root review findings before freeze: the saved checker now binds actual current identity metadata before comparing it, and its process checker resolves the worker from the admitted producer Source rather than the separate reader directory. Initial bytes and the first packet remain retained. Selected controls cover both corrections while preserving the complete six-case, nine-frame, 27-attachment and 17-draw scientific comparison. Independent code review and Source freeze/gates remain pending; no new WSL rendering result is claimed.

The [independent final57 integer128 saved audit](../../../build/evidence/typed-integer-sampling-native57-python611-gpu-outcome-review-native-1/result.json) now clears all 128 fresh candidate frames against accepted OriginalGL128, all 70 resident intervals with 17 zero-work counters, seven requested ForceLoss API recoveries, actual process closure and logical cleanup. All 74,516 checked inputs pass with no findings; the [complete original saved-review stream](../../../build/native57-integer128-saved-observation-native-1/observation.json) closes the one invocation. This finite corpus does not claim physical faults or driver residency.

The [fresh final57 Text24 capture](../../../build/evidence/text-native57-python611-root-1/result.json) passes all 24 complete frames against its accepted reference, with driver63040/direct child51352 closed exit0 and logical GPU cleanup true. The [complete Root process](../../../build/native57-text24-outer-root-1/outer-observation.json) is closed, and [actual saved inputs](../../../build/native57-text24-saved-inputs-root-1/inputs.json) bind one authorized independent reader. Root's first diagnostic incorrectly required identical before/after input maps; the corrected held criterion preserves every initial pin and admits exactly 112 new owned worker-output pins, with none changed or removed. The diagnostic refusal is retained and no capture was repeated. The independent Text reader is now running once.

The [forced-line producer preparation gate](../../../build/native57-thin-forced-source-review-root-1/result.json) and [joint saved-reader gate](../../../build/native57-thin-forced-reader-source-review-root-1/result.json) pass 94 and 105 required inputs. The [independent 717-check proof](../../../build/native57-thin-forced-review-point-1/proof-result.json) preserves five whole-file inverses, 33 complete function bodies and all nine scientific saved functions; the [frozen companion](../../../build/native57-thin-forced-source-review-point-1/result.json) covers the 112-input union. The already completed official57 normal78 is reused as evidence. A fresh forced78 result still requires a separately admitted qualification artifact and matching actual capture. The GQ1 reuse witness remains an unfrozen proposal; no old qualification result is promoted.

The [Linux rendering producer gate](../../../build/native57-linux-gpu-source-review-root-1/result.json) and [saved-reader gate](../../../build/native57-linux-gpu-saved-source-review-root-1/result.json) now pass 59 and 58 required inputs. The [independent 679-check proof](../../../build/native57-linux-gpu-review-native-1/proof-result.json) and [74-input frozen companion](../../../build/native57-linux-gpu-source-review-native-1/result.json) verify both corrections, seven whole-file inverses, 37 held functions and the complete scientific loops. Root's first metadata precheck expected only five verified fields while the companion declared additional review facts; its corrected explicit schema validates those facts and the full union. Both original attempts are bound in the complete gate journals; no frozen code or companion changed. After Text closed, Root started the fresh current57-source WSL full build once. Compilation, independent build admission and a matching new software-Vulkan capture remain required; native hardware, macOS and performance are outside these preparation gates.

The [independent final57 Text24 saved audit](../../../build/evidence/text-native57-python611-outcome-review-point-1/result.json) now clears all 24 full frames, all twelve atlas/geometry/texcoord/glyph cases, live typed DPI/anchor/rotation uniforms, resident graph/work checks and actual process/logical cleanup. All 62,586 bindings pass without findings. Its [complete saved-review stream](../../../build/native57-text24-saved-observation-point-1/observation.json) separates the actual tool launcher from the one exact saved-reader Popen vector and verifies reader39668 against the completed report; it makes no direct tool-launch or invented OS-edge claim.

The fresh current57-source WSL build now passes all five synchronous stages, all 42 project targets and all 44 distinct CPU contracts with zero failures, errors or skips. Its [complete Root process](../../../build/native57-linux-build-outer-root-1/outer-observation.json) binds actual Linux driver301 and the full original session; the four new Linux artifacts remain distinct from the protected installed Windows57 four. Complete source611, formal4131+tools4, package523 and combined4696 maps, source/dependency namespace conservation and unchanged transport/native files pass. A Root diagnostic initially compared the five CTest counts against the entire object, overlooking its declared testcase_names field; the corrected read validates all five counts and all 44 unique names without replaying the build. [Actual independent-build-audit inputs](../../../build/native57-linux-build-saved-inputs-root-1/inputs.json) and exact argv are retained, and that one saved audit is running. The normal stencil capture starts once after Linux compilation closes; Linux runtime qualification remains pending.

Current57 Linux software capture, 2026-10-20: [actual capture](../../../build/evidence/native57-linux-cull-candidate-root-1/result.json) passes six cases, nine complete RGBA/depth/stencil frames, and clean runtime/package preservation with no callback or cleanup errors. The [Root transcript](../../../build/native57-linux-cull-candidate-outer-root-1/outer-observation.json) retains the one actual WSL stream, process317 and exit0. All221 sealed packet files were checked. Independent Native saved review is authorized once and running; hardware/performance qualification remains separate. The first stencil environment-check failure and its [operator diagnosis](../../../build/native57-stencil-environment-diagnostic-root-1/result.json) are preserved; corrected launch uses the same frozen Source and literal capture argv.

Current57 Linux saved qualification, 2026-10-20: the [independent saved audit](../../../build/evidence/native57-linux-cull-candidate-review-native-1/result.json) is CLEAR_WITH_SCOPE, with15,498 checked inputs, no material findings, all six cases/nine full frames/27 attachments exact, all17 semantic and physical user draws, six X11 paint witnesses, and clean preservation. The reader made no provider, device, GPU or build calls. Its once-only caf860/session19488 to df6599/exit0 stream is retained; the frozen reader does not emit a self-PID, which remains explicitly unrecorded. This closes current57-source Linux software rendering at its stated scope, without hardware, physical-residency, performance or original-thirteen completion claims.

Current57 exact qualification-archive reuse, 2026-10-20: the unchanged86d6 core and bounded Source support pass independent125+204 code/metadata checks and eight saved support controls. Root froze27 members with24 known metadata inputs ([Source](../../../build/native57-qualification-reuse-prep-perf-1/source-seal.json)); the actual independent frozenSource companion and [Root Source gate](../../../build/native57-qualification-reuse-source-review-root-1/result.json) clear all52 needed inputs. Root authorized only exact GQ1 archive reuse under current57 continuity, keeping official57 native files and original GQ1 build/Root/admission identities separate. The independent [actual-input protected-path check](../../../build/native57-qualification-reuse-review-native-1/actual-witness-input-exclusion-result.json) checks62 names/12 roots with zero intersections against17 protected payloads/58 family files and fresh-eight IDs; seven explicit metadata documents were read, with no mapped target payloads visited. Root late command emission preserves its own92769c path receipt and exact4d22f3d argv. The one actual physical witness is running (6445c1/session93035); no compiler/provider/device/GPU is called. Actual saved equivalence and forced-route rendering remain pending. Frozen preparation files are unchanged.

Current57 stencil positive capture, 2026-10-20: the corrected [normal stencil capture](../../../build/evidence/native57-stencil-normal-root-1/result.json) passes19 cases with driver31300/direct child54204, child exit0/wait observed, one full parent current-identity admission and zero child full admissions, clean package/native preservation and no driver/preservation error. Root verified all1,260 sealed files. The [actual Root journal](../../../build/native57-stencil-normal-outer-root-1/outer-observation.json) retains4bd76f/session31735 to98d514/exit0. The operator-only environment correction leaves the frozen producer/reader Sources unchanged; failed first attempt remains preserved. The separate PrimitiveId negative started a0f4d3/session94883 after normal closure; no negative result yet. A once-only normal saved review is authorized to Native after its qualification-equivalence audit closes. Current57 GQ1 physical continuity passes50,628 pins without compilation; the exact saved equivalence audit is running from retained a8204929 argv and separate final saved-role exclusion34ac/b0e560 receipts. Forced rendering remains pending that independent result.

Current57 isolated qualification identity, 2026-10-20: the [independent saved source-equivalence audit](../../../build/evidence/native57-qualification-source-equivalence-review-native-1/result.json) is CLEAR_WITH_SCOPE (50,633 checked inputs; no findings), with its [full original process carrier](../../../build/native57-qualification-reuse-saved-observation-native-1/observation.json) closed. Root also evaluated the exact frozen fe6c pure qualification contract against the actual report, q7 roles and current identity context: source611/formal4131 and all declared predicates pass. This admits exact GQ1 archive reuse under current57 continuity, not an official57 binary relabel or inherited GPU pass. The forced78 exact runtime68f076 and retained command a1718e are ready; the separate new-input path exclusion passes (50,718 names/22 roots, zero protected intersections), and a free serialized GPU lane remains required before launch. Independent normal-stencil saved review is running, and the separate negative capture continues.

Current57 normal stencil saved admission, 2026-10-20: the [independent saved review](../../../build/evidence/native57-stencil-normal-review-native-1/result.json) is CLEAR_WITH_SCOPE, with53,873 checked inputs, no findings,19 cases/22 whole frames/66 complete attachment pairs and202,752 compared bytes, with zero excluded pixels. Actual saved reader51352 remains distinct from capture driver31300/child54204. Root independently checked the complete result packet. The scope leaves general R05b, PrimitiveId runtime, external vertex effects, physical residency and performance qualification false. The separate negative capture remains active. Forced78 current Source/actual runtime path exclusion f4103108 is clear over94 Source-needed pins,17 runtime keys, qualification7,50,718 names and22 roots; it makes no physical target or guard calls and does not itself execute the capture.

Current57 PrimitiveId negative capture, 2026-10-20: the [actual negative job](../../../build/evidence/native57-stencil-negative-root-1/result.json) passes the exact contextual PrimitiveId refusal with driver57232/direct child20236, child wait/exit0, canvas close and completed cleanup finish, preserved installed57 and one parent/zero child identity admissions. Root verified all544 sealed files and separately checked the expected error substring and role distinction. Its [complete Root transcript](../../../build/native57-stencil-negative-outer-root-1/outer-observation.json) retains a0f4d3/session94883 to d4f23c/exit0. This is refusal qualification, not PrimitiveId rendering support. The independent negative saved audit is authorized once; no outcome yet. The prepared public-query command started33c248/session83979 only after negative capture closure. Broad64 coherent unfrozen producer/reader preparation passes262+28+9+148 saved controls; Native code/support review is running, and Source/runtime/capture roles remain late.

Current57 contextual negative saved admission, 2026-10-20: the [independent negative review](../../../build/evidence/native57-stencil-negative-review-native-1/result.json) is CLEAR_WITH_SCOPE,53,155 checked inputs/no findings, actual reader25516, exact candidate-only contextual error, canvas close and cleanup. This closes the bounded positive/negative current57 stencil refresh; broad R05b remains open. Broad64 producer20/reader16 Sources are now frozen as d39e/efb5, with corrected overlay metadata and61 code/JSON known pins each. Independent review clears99 unique Source-needed pins, but Root first Source-gate fa2fdc correctly refused an incomplete companion seal (author.py was not listed). The [failed gate transcript](../../../build/native57-broad64-source-gate-failed-outer-root-1/outer-observation.json) and original packet stay unchanged; a fresh packaging-only Native companion is being prepared. No Broad GPU actor or Root gate output was created, and frozen code remains unchanged. Partition256 [map](../../../build/native57-partition256-map-point-1/map.json) requires a fresh current-source42/44/archive44 build: normalization code/test and parser differ from old sfp2; only exact07df runtime overlay/15ef enable code remains reusable.

Current57 public-query capture, 2026-10-20: the [actual comparison](../../../build/evidence/native57-public-query-root-1/result.json) passes five expected capability-query changes and unchanged controls, with one parent identity admission, driver57176 and two direct children59464/61536 closed exit0. The [Root process record](../../../build/native57-public-query-outer-root-1/outer-observation.json) retains33c248/session83979 to75cbb2/exit0. Root first used an overstrict recursive parent-seal assertion; the unchanged producer explicitly seals ten top-level files, two independent527-file runtime packages and two separately sealed child packets. Corrected Root7a7e30 verifies that whole declared hierarchy, with no capture replay. Point is authorized once for the saved review. The prepared forced78 capture startedc173e7/session64734 after public-query process closure; actual result remains pending.

Current57 fault/cancellation producer Sources, 2026-10-20: independent Point review accepts840+86 selected code/delta checks and the exact two cancellation metadata corrections (new saved-perf-1 path and Point matrix reviewer). Root froze fault19/132 Source86682a35 and cancellation22/137 Sourcec8b35cdc once, then their finished Source gates4c2099/015557 pass152/160 needed pins. No guard/runtime/device was invoked. Actual fault4 baseline/map/defer matrix and seven cancellation schedules remain pending their new saved readers, final no-visit receipts and serialized GPU runs. Fresh saved-reader preparation preserves whole science and passes168+38 pure controls; independent code review is pending.

Broad receipt-packet successor, 2026-10-20: Source1 remains frozen/unexecuted after Root identified a complete result/seal snapshot gap in its protected-path receipt role. Fresh Root-owned Source2 producer/saved folders add full adjacent metadata packet validation before generic binds, include both receipt files in checked/final snapshots, and move worker runtime receipt admission before the handoff bind. The original scientific predicates/counts remain held. Actual87 selected packet/hash/schema/order/core-inverse controls pass; a same-line AST-column harness refusal is retained. Native found two stale CLI helper hashes after path adaptation; only those literals were corrected, with two binding controls and direct34-member inverses composed to Source1. Corrected [unfrozen packet](../../../build/native57-broad64-receipt-prep-root-2/review-packet-2.json)649ecb08 is under independent review. No Source2 freeze, source gate or broad capture has run.

Current closure checkpoint, 2026-10-20 14:25 UTC: [public-query saved review](../../../build/evidence/native57-public-query-review-point-1/result.json) and [full original process carrier](../../../build/native57-public-query-saved-observation-point-1/observation.json) are independently clear, with 51,729 checked pins, five changed enums and unchanged controls. Root verifies the result-only seal and full carrier. This does not close all R02 allocation/error requirements.

The [forced thin-line capture](../../../build/evidence/native57-thin-forced-root-1/driver-result.json) passes all 13 cases and 78 complete frames; actual driver3568 waited child60176 to exit0, and Root verifies all926 sealed output files, cleanup and unchanged installed Native57. Its [full actual transcript](../../../build/native57-thin-forced-outer-root-1/outer-observation.json) is sealed. The [joint saved inputs](../../../build/native57-thin-forced-saved-inputs-root-1/inputs.json) join this new capture with the already admitted normal78 outcome; normal78 is not replayed. Independent saved review is pending.

Broad64 successor Source2 is frozen after the bounded receipt result+seal binding correction and two CLI helper-hash fixes. Both [producer Root Source gate](../../../build/native57-broad64-source-review-root-2/result.json) and [reader Root Source gate](../../../build/native57-broad64-reader-source-review-root-2/result.json) pass with101/97 needed pins. The [independent companion](../../../build/native57-broad64-source-review-native-3/result.json) covers118 distinct needed pins and links the1,275-check successor proof plus the held1,970-check scientific proof. Actual normal/forced runtime path-exclusion receipts remain pending; Source1 is retained and was never GPU executed.

Both fault/cancellation saved-reader Sources are now frozen after642 independent CODE checks. Their [fault reader Root gate](../../../build/native57-chunk-fault-reader-source-review-root-1/result.json) and [cancellation reader Root gate](../../../build/native57-cancellation-reader-source-review-root-1/result.json) pass with41/42 needed pins; full original freeze/gate transcripts are retained. The actual [unarmed baseline runtime inputs](../../../build/native57-chunk-fault-baseline-inputs-root-1/inputs.json) are prepared, with the exact independent GQ1 continuity admission and no baseline inherited. Its actual path-exclusion receipt and GPU run remain pending, followed by the other three fault jobs, the independently admitted fault matrix and seven cancellation schedules. Fresh Partition256 build preparation remains separate and incomplete. No broader original requirement, native Linux hardware, Metal or performance completion is claimed. Protected Smooth payloads remain untouched and cybersecurity is excluded.

Runtime checkpoint, 2026-10-20 14:27 UTC: both [Broad64 actual runtime path-exclusion receipts](../../../build/native57-broad64-no-visit-native-2/normal/result.json) and the matching [forced receipt](../../../build/native57-broad64-no-visit-native-2/forced/result.json) are clear, with protected payload stat/open/hash calls zero. Their [full original author carrier](../../../build/native57-broad64-no-visit-native-2/execution-observation/observation.json) is sealed and Root-verified. Root bound them into the exact18-role runtime files and started the normal Source2 capture once (session79274, first tool return efe3ef); no terminal result exists yet. Forced broad capture waits for this sole GPU lane. Independent final forced78 saved review and the fault-baseline receipt are assigned next to the existing Native reviewer; no normal78 replay is authorized.

Broad64 preflight correction checkpoint, 2026-10-20: the Source2 normal attempt closed exit1 before output creation/provider import/child launch. Its [full failed actual transcript](../../../build/native57-broad64-normal-failed-outer-root-2/outer-observation.json) is retained unchanged. Independent diagnosis identifies empty retained stdout at build_Root_process.observations[*].output, which the declaration walker incorrectly classified as a filesystem output. The [unfrozen Source3 review packet](../../../build/native57-broad64-stdout-prep-root-3/review-packet.json) adds a strict exact-tool-return stdout classifier; ordinary output paths, archive/package/overlay roots, receipt result+seal binding and protected17/58/fresh8 checks remain enforced. Its [384 selected controls](../../../build/native57-broad64-stdout-prep-root-3/controls-result.json) pass against both actual runtime metadata sets plus malformed record/protected-path negatives. Thirty-four whole-member inverses retain the previous science and receipt checks. Full original preparation/control transcripts are sealed. Source3 independent review is pending; neither Source3 freeze nor a GPU retry has occurred. The independent forced78 saved audit is running once under the existing Native reviewer; the fault-baseline exclusion is paused at a safe metadata checkpoint. Partition256 producer/saved entrypoints exist, with controls and coherent source preparation still pending.

Source3 final source checkpoint, 2026-10-20 14:43 UTC: independent [1,562-check proof](../../../build/native57-broad64-stdout-review-native-3/proof-result.json) and its [full original carrier](../../../build/native57-broad64-stdout-review-observation-native-3/observation.json) pass. Actual producer/reader freezes are c50ca669/c55c9b53. The [frozen companion](../../../build/native57-broad64-source-review-native-4/result.json) binds137 distinct needed pins and the held scientific lineage. Root [producer gate](../../../build/native57-broad64-source-review-root-3/result.json) and [reader gate](../../../build/native57-broad64-reader-source-review-root-3/result.json) close exit0 with120/116 needed pins; their full original journals are sealed. No Source3 GPU attempt has occurred. Fresh Source3 normal/forced runtime projections are retained and actual path-exclusion receipts are assigned before any retry. The unarmed fault-baseline receipt is independently queued; GPU work remains serialized. An existing worker is producing a broader exact acceptance-row catalogue, separating current57 original126 image/layout/volume coverage from missing tests. Its preliminary nonduplicative next local R04 subrow is14 rendered uniform-packing/coordinate tests outside the actual original126 recipes; upstream/actual57 qualification remains unperformed. This does not close full R04, Metal or any remaining original requirement.

Joint thin156 and runtime checkpoint, 2026-10-20 14:54 UTC: the [independent joint156 report](../../../build/evidence/native57-thin-forced-outcome-review-native-1/result.json) is CLEAR with53,647 checked pins, all156 complete frames/479,232 bytes exact,926 actual OriginalGL endpoint rows, cleanup and installed57 continuity. Normal was not replayed; the forced artifact is explicitly not relabelled official57. Root initially refused the saved-carrier namespace because the old seal covered only observation.json while auxiliary files were present. The old folder and refusal remain unchanged. A [packaging-only successor](../../../build/native57-thin-forced-saved-observation-native-2/observation.json) copies all seven original files byte-for-byte, retains the prior seal, and seals the whole eight-file namespace; Root verifies all physical before/after pairs and the [actual repack carrier](../../../build/native57-thin-forced-saved-repack-native-2/execution-observation/observation.json). No test/review replay occurred.

The actual [fault-baseline inputs](../../../build/native57-chunk-fault-baseline-inputs-root-1/inputs.json) and [literal argv](../../../build/native57-chunk-fault-baseline-inputs-root-1/argv.json) are bound to a fresh [Native path receipt](../../../build/native57-fault-cancel-no-visit-native-1/fault/baseline/result.json); Root validates the exact frozen receipt contract and the complete packet. One actual baseline run ec4236/session6631 is live, Root sole poller and sole GPU/compiler operator. Fresh Source3 broad runtime receipts and their full carrier pass; the exact18-role [normal](../../../build/native57-broad64-runtime-inputs-root-3/normal.json)/[forced](../../../build/native57-broad64-runtime-inputs-root-3/forced.json) inputs and literal argv are prepared, with no Source3 capture yet.

The [72-row scientific catalogue](../../../build/native57-acceptance-catalogue-perf-1/catalogue.md) separates current57 fixed image/layout/marker/volume coverage from missing rows; it does not close all R01/original requirements. The [uniform14 map](../../../build/native57-uniform14-map-perf-1/map.md) identifies the exact existing shader tests and whole8x8 expectations. Their hardcoded Dawn import/backend requires a reviewed backend-only upstream adapter; no upstream render pass is inferred. Point is preparing this distinct next fixture after the Partition correction. Partition independent review confirms a schema:true equality seam in its unfrozen receipt parser; the narrow typed-integer correction and actual selected controls are authorized, while whole source/SDK/target/macro/scientific predicates remain held. No Partition freeze/build occurred.


Baseline and build-source checkpoint, 2026-10-20 15:29 UTC: the [actual fault baseline](../../../build/evidence/native57-chunk-fault-baseline-root-1/driver-result.json) passes with driver22084, child18384 waited to exit0, clean logical cleanup, preserved inputs and installed57 continuity. Root verifies the complete46-file packet and worker seal, and seals the [full original process stream](../../../build/native57-chunk-fault-baseline-outer-root-1/outer-observation.json). The [actual baseline reference](../../../build/native57-chunk-fault-baseline-inputs-root-1/baseline-reference.json) pins this driver, worker, Root transcript and actual first-collection data/raw rows for three new fault inputs. This is one baseline result; the complete fault matrix and cancellation admission remain pending. Source3 broad normal is running once, with no terminal outcome claimed.

Partition256 [final independent proof](../../../build/native57-partition256-review-native-1/proof-result.json) passes789 checks, including seven composed inverses from physical retained before files and whole scientific-function conservation. Producer d744e6ed and reader eeacdeed Sources are frozen. Both [producer gate](../../../build/native57-partition256-build-source-review-root-1/result.json) and [reader gate](../../../build/native57-partition256-build-reader-source-review-root-1/result.json) pass129 needed inputs; the [producer original gate stream](../../../build/native57-partition256-producer-source-gate-outer-root-1/outer-observation.json) and [reader original gate stream](../../../build/native57-partition256-reader-source-gate-outer-root-1/outer-observation.json) are sealed. The fresh build remains a separate qualification variant, with no canonical publication or normal-artifact relabel. Path checks, actual compilation, independent saved-build admission and matching rendering remain pending.


Broad overlay correction checkpoint, 2026-10-20 15:40 UTC: the [Source3 actual normal result](../../../build/evidence/native57-broad64-normal-root-3/driver-result.json) closes exit1 with driver62548/child39636 and unchanged input/native files. The [actual worker failure](../../../build/evidence/native57-broad64-normal-root-3/worker/worker-result.json) shows zero native import/provider/GPU attempt: its inherited copy helper requires native54-python611-broad-overlay-, conflicting with the actual native57-broad64-overlay- namespace. Root verifies the complete nine-file failure packet and seals the [full original process](../../../build/native57-broad64-normal-failed-outer-root-3/outer-observation.json). Frozen Source3 stays unchanged. A [fresh Source4 packet](../../../build/native57-broad64-overlay-prep-root-4/review-packet.json) holds34 whole-member inverses and changes the one helper prefix plus successor paths and helper CLI bindings. Its [34 selected controls](../../../build/native57-broad64-overlay-prep-root-4/controls-result.json) reproduce the old refusal, copy both synthetic route packages completely, verify manifest/full bytes and reject bad namespaces, overlaps, corruption and existing output. Independent code review is pending; no Source4 freeze or capture has run.

All three remaining fault [path receipts](../../../build/native57-fault-cancel-no-visit-native-1/fault-kinds-observation/observation.json) now pass152 Source names,60,172 declared paths and32 inventory roots per kind, with zero protected payload visits. Root evaluates each exact frozen receipt contract and exact two-file namespace, emits literal19-token commands, and verifies the complete original author carrier. The guard_copy actual job starts f29541/session17122 after Broad normal terminal closure; destroyed_map and defer_once remain serialized behind it. The [Partition build path receipt](../../../build/native57-partition256-no-visit-native-1/result.json) and full author carrier also pass, and Root emits its [literal build command](../../../build/native57-partition256-build-inputs-root-1/argv.json); compilation waits for the free lane.


Broad Source4 admission checkpoint, 2026-10-20 15:50 UTC: the [independent CODE proof](../../../build/native57-broad64-overlay-review-native-4/proof-result.json) clears1,664 checks,34 complete physical Source3-to-Source4 inverses and224 complete held function bodies/ASTs. Its [whole original carrier](../../../build/native57-broad64-overlay-review-observation-native-4/observation.json) and all three Root preparation journals are sealed. Producer d6eb7a3b and reader09e97ff7 Sources freeze20/16 members with125 known inputs each. The [frozen companion](../../../build/native57-broad64-source-review-native-5/result.json) verifies all163 distinct needed inputs; its [complete original carrier](../../../build/native57-broad64-source-review-observation-native-5/observation.json) closes. Root checks both whole namespaces, typed results and all protected-path declarations, then [producer gate](../../../build/native57-broad64-source-review-root-4/result.json) and [reader gate](../../../build/native57-broad64-reader-source-review-root-4/result.json) pass146/142 needed pins. Full actual freeze/gate journals are retained. Both17-role actual runtime projections remain byte-identical to the admitted Source3 role projections; they still require fresh Source4 receipts and exact late18-role inputs. No Source4 capture has run.


Guard-copy closure and broad retry checkpoint, 2026-10-20 15:55 UTC: the [actual guard_copy result](../../../build/evidence/native57-chunk-fault-guard_copy-root-1/driver-result.json) passes with driver25184/child32060 closed exit0, complete cleanup, preserved input pins and installed57. Root verifies the whole46-file packet and complete worker seal; its [full original capture stream](../../../build/native57-chunk-fault-guard_copy-outer-root-1/outer-observation.json) is sealed. This advances two of four fresh fault jobs; the complete independently admitted matrix remains pending.

Source4 [normal path receipt](../../../build/native57-broad64-no-visit-native-4/normal/result.json) and [forced path receipt](../../../build/native57-broad64-no-visit-native-4/forced/result.json) check all163 Source union pins,60,090/60,137 declared paths and30/37 roots, with zero protected payload visits. The [whole original author carrier](../../../build/native57-broad64-no-visit-native-4/execution-observation/observation.json) is closed and Root-verified. Root exact frozen receipt/schema checks pass and emit [normal inputs](../../../build/native57-broad64-runtime-inputs-root-4/normal.json), [forced inputs](../../../build/native57-broad64-runtime-inputs-root-4/forced.json) and both literal vectors; the complete Root preparation stream is sealed. Actual normal4 starts634265/session74362 only after guard_copy terminal closure. No Source4 normal or forced rendering result is claimed yet.


Uniform fixture review checkpoint, 2026-10-20 16:05 UTC: the shared uniform14/reuse2 fixture remains unfrozen, with Source support and independent complete-code admission pending. Root selected science review identifies a real transport mismatch: canonical GlirQueue.command enqueues command tuples, while recursive tuple tagging changed the outer commands into dictionaries and the reuse checker indexes command sequences. The [retained correction derivation](../../../build/native57-uniform14-prep-point-1/command-tuple-correction-derivation.json) preserves the prior whole science file; the corrected serializer keeps outer commands as lists while retaining nested DRAW-range tuple tagging and ndarray payloads. Twelve selected actual-function controls pass, including same-object delegation and malformed-command refusal, without importing a provider, pytest or target runtime. This closes that preparation bug, not actual upstream or candidate rendering qualification.


Shared uniform preparation checkpoint, 2026-10-20 16:08 UTC: the [coherent unfrozen packet](../../../build/native57-uniform14-prep-point-1/review-packet.json) holds29 producer and20 reader members with53 finite known inputs each. Five pure selected suites pass215 checks, with the complete-code derivation, two exact GL-only adapter spans, unmodified14 candidate test bodies/decorators, separate first reuse2 group, actual-origin authorities, direct-process closure support, strict path boundaries and late-null actual templates retained. Its [complete original preparation carrier](../../../build/native57-uniform14-prep-point-1/preparation-observation/observation.json) closes50 groups/72 actual calls, preserving original nonzero reads and truncated output. Root verifies the whole exact two-file namespace. Native is assigned the complete independent CODE/support review; no Source freeze, current guard call, test collection, provider or GPU has run for this fixture. Separate matching Partition256 GPU Source preparation is assigned in fresh owned folders while its reviewed build remains queued; old sfp2 outcomes stay historical.


Broad normal4 and uniform CODE checkpoint, 2026-10-20 16:20 UTC: the [new broad normal result](../../../build/evidence/native57-broad64-normal-root-4/driver-result.json) passes all10 cases/32 whole frames,13 endpoint captures/849 logical32-byte rows,53,456 guarded raw bytes,35 scene/67 raw draws and3 requested ForceLoss recoveries. Driver56836 waits child58552 to exit0 with complete cleanup, preserved inputs and installed57 continuity. Root verifies the whole923-file packet and full worker seal; its [complete original process journal](../../../build/native57-broad64-normal-outer-root-4/outer-observation.json) is sealed. Forced4 starts c76eaf/session99076 only after normal4 terminal closure, with no outcome claimed yet. One joint independent saved review remains pending.

Uniform [independent CODE proof](../../../build/native57-uniform14-review-native-1/proof-result.json) clears2,492 checks across complete modules/decorators, retained physical before/final inverses, copied formal/process/saved bodies, all49 Source files/53 known inputs each,12 admitted METADATA/RECORD authorities and523 reconstructed wheel rows. Actual selected AST checks cover complete16-frame predicates, exact14 nodes/42 reports, outer GLIR command sequences and nested tuple/ndarray payloads, same-object delegation, reuse counters, literal process/CLI, current57 parent1/child0 and path checks before generic bindings. Source templates remain unfrozen/null at this checkpoint. Root prepares [actual upstream-only runtime inputs](../../../build/native57-uniform16-upstream-inputs-root-1/inputs.json) from real current57 normal roles, with all three upstream reference roles null; no guard, provider or producer is called. Code closure, Source freeze/gates and fresh actual path receipt precede any upstream run.


Continuation checkpoint19, 2026-10-20: clean installation bytes pass; full installed consumer/SDF/Text24/capture, uninstall and upstream restoration remain open. Point is implementing the complete five-child lifecycle in fresh owned Source-only folders with all actual admission roles null. The independent fixed SDF fixture review clears154 checks; Root verifies all17 source/carrier pins, with no compiled SDF runtime claim. Partition GPU4 is the sole live Root GPU session2486. Uniform physical-size metadata proposal passes42 controls; independent review and successor transport remain pending. All13 original release requirements remain in scope and incomplete. Cybersecurity work is excluded. No disposable assets were removed or required inputs discarded.


Continuation checkpoint20, 2026-10-21 00:00 UTC: the coherent [full consumer lifecycle draft](../../../build/native57-final-wheel-clean-runtime-prep-point-1/review-packet.json)89a0261a contains25 producer/21 reader Source members and49 known inputs each. Its133 pure controls and242 final static checks pass. The complete56-operation preparation carrierdb34081f preserves all7 metadata/checker refusals and108 physical pins, all Root-verified. Five child phases cover fork SDF25/Text24/clear, actual uninstall, separate package absence, exact downloaded upstream restoration, and fresh upstream SDF25/Text24/clear. The full60-array/24-frame-pair comparisons retain original Text24 geometry/border/transform criteria. Native independent complete CODE review is in progress; all actual Source/input/admission roles remain null, no lifecycle runtime/provider/installer has run. Uniform5 independent transport review is in progress. Partition4 remains sole live Root GPU actor eb67df/session2486, with no terminal/rendering outcome claimed. The explicit seven-folder junk check finds no pyc/tmp/partial files and deletes nothing. All original13 requirements remain incomplete; cybersecurity work remains excluded.


Continuation checkpoint21: the full consumer lifecycle independent CODE reviewc5ed5736 clears297 checks and all46 Source files/49-known maps. Its complete20-operation carrier2b5afcf8 and118 pins are Root-verified. Root freezes actor3708c9eb (25/49/75) and readerd2a9364a (21/49/71), preserving both literal freeze carriers. Native frozen companionsb32d615c/3cb55384 validate75/71/97 needed maps; the full5-operation/139-pin carrierdb95c5c5 is Root-verified. Out-of-Source stdlib Root gates f1ef5124/ff864146 pass75/71 needed pins, with no frozen Source module imports. Actual lifecycle inputs07a96871 bind all seven real installation/admission/inventory/python roles plus95 normative read pins and two external tools; full original input author0277bccf is retained. A fresh independent actor path review is underway; no lifecycle actor or device has run. Partition GPU4 is terminal, so no GPU actor is currently live. Uniform5 is frozen and pending Native frozen confirmation. Point owns the fresh Partition GPU5 draft applying only the reviewed build-packet shape and fresh transport metadata. All13 original requirements remain incomplete; cybersecurity excluded. The newly owned synthetic packet fixture was explicitly cleaned after controls; no rejected cleanup targets were retried.


Continuation checkpoint22: the first clean lifecycle attempt c487d7 exits1 before any OS child, provider, installer or graphics operation because the Root shell wrapper created present-empty Vulkan environment variables. The five-file failure packet and complete Root failure carrier e7fc6bd6 are preserved; all8075 installed files remain unchanged. Correct Env removal is independently checked in the actual Python process; strict Source environment admission is retained. Fresh routing-only lifecycle Source2 passes Root2683 checks/211 finite pins, nine raw inverses and35 whole held files, plus101 Point controls. Actor2297cd6b and reader29eb09cc freeze25/21 members,159 known each and185/181 needed maps. Native companion carrier5af45515 closes234 pins, all236 including carrier files Root-verified. Both new Root metadata gates cf0b84a3/a4da54cc close; actual inputs0cd9bcf3 bind95 normative pins and the same seven installation context roles. Fresh Source2 actor path review is underway, reusing the admitted525-member upstream metadata authority without reopening the archive. No Source2 lifecycle actor has launched.

Uniform5 frozen companion and both Root gates close; fresh upstream NoVisit36db41bc covers69,330 names/31 roots with zero protected visits. Root verifies its full306-pin carrier486d888b plus both carrier files. Capture remains queued behind lifecycle. Partition GPU5 complete independent CODE review clears10,262 checks, and Root verifies all635 carrier/source pins; producer9d7e8325 and reader13d874ed are frozen, with Native frozen companion queued after the lifecycle path review. No GPU actor is live. Full clean-consumer qualification and all13 original requirements remain incomplete. Cybersecurity is excluded. Required evidence, Sources and installations remain retained; no rejected cleanup targets were retried.


Continuation checkpoint23: Source2 lifecycle fresh NoVisit f2e66567 passes the exact266-pin bootstrap predicate; Root verifies all158 author-carrier pins plus carrier files. The one Root actual109995 exits1 with driver61764, real fork Popen24560/self55048 terminal1. The environment correction succeeds and installed rendering begins, but the observation helper performs two exclusive writes to the same between-canvas-gc.json within its first call. No uninstall or restoration ran. Root verifies all15 sealed files, the complete Root process carrier4913ae42, and all8075 unchanged external installed files. Only the exact verified empty owned settings directory is removed. Failed output and Source2 remain immutable. Point proposal961de237 changes only the two observation filename expressions to include the existing boundary and before/after stage;39 checks/five inert scenarios preserve exclusive writes, GC calls and failure propagation. Root verifies the16 finite proposal/carrier pins; independent Native semantic review and fresh Source3 transport are underway.

The uniform5 upstream actual starts323b8e/session57835 once after lifecycle2 terminal closure, using the prepared reviewed Source/gate/input/NoVisit rows and correct environment removal. It remains active with no terminal result claimed. Partition GPU5 frozen companion23f12aea and full carrier68649cfc are Root-verified over648 finite pins. Root producer/reader metadata gates afbd9cab/45428984 close610/621 needed inputs. Fresh runtime inputs821028f5 remain byte-identical to Source4; fresh Source5 path review is queued, with no partition capture launched. All13 original release requirements remain incomplete; cybersecurity is excluded.


Continuation checkpoint24: Uniform5 upstream actual323b8e/session57835 is terminal f2c228/exit1, driver17340/worker32176. The corrected physical-size metadata admits both same-generation reuse frames and owned RGBA8 cleanup;14 pytest nodes run,12 pass and2 fail (mat2 array shader setup returns handle0; boolean-vector upload raises upstream bvec3 KeyError). Twelve test frames plus two reuse frames remain failed, unadmitted evidence. Root verifies all22 sealed files, complete worker packet, actual process closure and unchanged52,115 original input pins; exactly16 worker-output bindings are added afterward. Root-owned checker selector corrections are preserved separately and do not change Source or actual results. Full failed process carrier9d9d3050 closes all literal polls. Point is diagnosing the two failures in Source-only scope, preserving assertions, shaders and pixels.

Lifecycle3 filename fix receives independent214 checks; Root verifies43 proof/carrier pins. Coherent Source3 transport db6690b7 passes326 staticchecks/101 controls,46 members/10 raw inverses/34 whole-held files/187 definitions/277 known inputs each. Its complete10-operation carrier8f8c277c and all112 pins are Root-verified; Native complete transport review is underway, with no Source3 freeze or actual actor yet. Partition GPU5 fresh capture path receipt78b7ddbf checks312,307 names/55 roots with zero protected visits; Root verifies its full329-pin carrier plus both files, derives the exact argv, and starts the sole Root actual c8ea59/session45267 after Uniform5 terminal closure. No partition rendering result is claimed. All13 original release requirements remain incomplete; cybersecurity excluded.


Continuation checkpoint25: Lifecycle3 complete independent transport review c3088540 clears3181 checks/332 pins, ten raw module inverses,34 whole-held files and191 decorated/nested definitions. Root verifies its338-pin original carrier0f7bc60b plus carrier files. Actor29c89b40 and reader1e97efb0 freeze25/21 members with277 known inputs each. Native per-Source companions d9800ce6/60cd3460 and their354-pin carrier412f9128 are Root-verified;303/299 needed maps,325 union. Root metadata gates1ac68529/24886f18 close with no frozen Source imports. Exact inputs50eaeb01 retain95 normative pins/two tools/seven installation roles. Fresh actor path review fb897ca2 checks384 merged pins,35,820 normalized names/75 roots,17/58/fresh8zero, with no archive reopen or external-root visit. Root verifies its219-pin author carrier883f3c31 plus carrier files and exact384-pin bootstrap predicate; actual argv/environment are prepared. The actor is queued behind the still-live sole Partition GPU5 session45267, and no Source3 lifecycle actor has launched.

Uniform upstream diagnosis confirms both bvec host table widths and int32 upload conversion are required. Final source-only proposal b3db3f2a adds a reversible explicit adapter with43 selected-call inert checks alongside429 source/control checks, preserving all14 scientific drawing functions/assertions and pristine admitted upstream package files. A separate explicit public canvas.set_current after entry is proposed; actual context-loss causation remains an inference. Root verifies both complete20+4 operation carriers over47 finite pins. Independent Native compatibility review is underway, with no Source6 transport or actual replay. Seven newly owned folders contain no disposable pyc/tmp/partial files. All13 original release requirements remain incomplete; cybersecurity excluded.


Continuation checkpoint26: Partition GPU5 capture c8ea59/session45267 closes7b156d/exit0 with driver38108/direct child50628. Root verifies all1260 sealed files including the726-file worker packet,19 cases/22 whole frames/66 complete attachment pairs/202,752 compared bytes,zero excluded pixels, logical shutdown counters zero and installed Normal57 unchanged. The real256-byte partition witness spans11 chunks/99 selected elements/four instances; physical device grants remain distinct. Full Root actual carrierb06e6bc3 retains the complete stream and literal driver vector. Independent saved admission remains pending; all_R05b_closed staysfalse.

Lifecycle3 actual c5614b/session44051 closescf2ce4/exit0 with driver48004 and all five redirector/self process pairs closed0. Root verifies365 sealed files,60 full array pairs/24 Text frame pairs/one clear pair. The complete fork inventory8075 is held through rendering, exact uninstall removes572 files, the absence phase holds7503, and exact upstream restoration adds528 files to8031; upstream rendering holds that final inventory. Full Root original process carrier4c7ee79f retains actual sys.orig_argv, distinct requested vector and all literal tool returns. Only the verified exact empty owned settings directory is removed; restored upstream environment and all evidence remain retained. The producer status remains pending saved review, not final qualification.

Root metadata-only saved input author968768 binds exact lifecycle751 normative pins (inputs20d7b7d0) and partition joint roles (inputse1bf12ee), with complete author carrierb9ccfcef. Native fresh saved path checks are underway before either saved reader. Uniform explicit reversible compatibility proposal receives737 independent checks; Root verifies all39 carrier pins plus both carrier files. Point owns a fresh Source6 transport applying only the reviewed upstream14-only adapter and public set_current helper, preserving pristine upstream package files, candidate, shaders/assertions/pixels and reuse2. No Source6 freeze, gate or actual run has occurred. No GPU actor is live. All13 original release requirements remain incomplete; cybersecurity excluded.


Continuation checkpoint27: Lifecycle3 independent saved reader c35578/exit0 PID65056 admits the complete CP312 Windows clean consumer lifecycle. Result3f52ef12 and sealca7b579e are CLEAR_WITH_SCOPE/no findings, clean_consumer_qualified true; full4-operation carrier038fa615 retains the single original reader command/no polls. Root verifies341 finite carrier pins plus carrier files and exact saved facts: compiled SDF25 both phases,60 complete array pairs/24 Text frame pairs/one clear pair, uninstall absence and exact upstream restoration. This closes that bounded CP312 Windows consumer, not the other four ABIs or broader host/hardware/performance requirements. Partition5 original authorized saved reader started49a0b6/session56269 after explicit confirmation it had not launched before the reviewer interruption; Native remains sole poller, no terminal result yet.

Uniform6 coherent unfrozen draft9b9a9d7b contains35 producer/24 reader members and689 known inputs each. Point504 proof checks,98 integration controls and7 metadata checks pass. The complete26-operation758-pin preparation carriere695524e preserves initial59-file checkpoint, two output suffix corrections, helper JSON2 pin correction/compatibility authority and actual named-read refusal. Root verifies760 finite pins including carrier files; Native complete independent review is underway. No Source6 freeze/guard/provider/GPU has run.

User explicitly requests public publication to bipxx/vispy_vulkan when ready. GitHub confirms the organization and admin membership, but no matching repository exists yet. Canonical workspace has no Git metadata. A source-only publication map is being prepared for an isolated checkout, preserving provided pinned vendor trees and omitting in-source CMake products, virtual environments and build evidence. No remote repository was created or pushed. All13 original release requirements remain in scope and incomplete; cybersecurity excluded.


Continuation checkpoint28: Partition5 independent saved reader49a0b6/session56269 closes5f0bc6/exit0 PID28180. Resultc62d7c1a/sealac2748b4 is CLEAR_WITH_SCOPE/no findings; full10-operation carrier7f9a0dba retains all six same-handle polls and original-neverstarted audit. Root verifies56 finite carrier pins plus both carrier files and all exact scientific facts:19 cases/22 whole frames/66 attachment pairs/202,752 bytes/zero excluded pixels,256-byte witness11chunks99elements4instances. BroaderR05b, PrimitiveId,external vertex effects,physical residency/performance remain false.

Uniform6 independent CODE74a408bb clears9002 checks/763pins,14 raw whole-file inverses,39 whole-held files and183 decorated/nested function/class holds. Root verifies767-pin original carrier8b99a33b plus both files. Producer4641e330 and readera6fd2329 freeze35/24members with689known each. Frozen companion5451b487 and781-pin carrier3085fba4 are Root-verified;725producer/714reader/750unique needed. Root metadata gates e6378e68/5b4fa6df close with no Source-module imports. Actual upstream inputs7ab9ddf7 remain byte-identical to the previous request, all three reference roles null. Fresh Source6 upstream path review is underway before the one new capture; no Source6 GPU actor has run.

The isolated source publication checkout is staged at C:/Users/HEQ/Projects/vispy_vulkan-publication. Copyf42568 verifies97,497 source files/456,592,704 bytes and all ten immutable vendor tree digests, retaining binary test fixtures and77 extra Dawn build/generator support files. Root license, explicit unfinished-qualification README, byte-preserving Git attributes and exact CPU compatibility metadata are added; four package-input tests pass. Git index session96447 remains live. No canonical source/vendor/evidence files were altered for publication; remote bipxx/vispy_vulkan has not been created/pushed. All13 original requirements remain in scope/incomplete; cybersecurity excluded.


Continuation checkpoint29: Uniform6 fresh upstream NoVisit acd829a0 and full409-pin original carrierad1aac33 close; Root verifies411 finite pins including carrier files. The receipt covers725/714/750 Source-needed maps,400 named JSON/69,643 normalized names/36 roots,protected17/58/fresh8zero. Exact Source6/gate/input/receipt argv be520ec2 is prepared and the sole Root actual starts7948e1/session14710 once, with no terminal result yet. No prior failed frames are promoted; pristine upstream521 package files and disclosed reversible upstream14-only compatibility scope remain distinct.

Publication Git indexing session96447 remains live. Four isolated package-input tests pass; all ten raw-copied vendor tree digests match. Vendor nested Git attributes can override the root text rule; local core.autocrlf=false/core.eol=lf are configured and a finite source-EOL review is underway before clean-checkout verification. No remote repository or push exists. The public README reports unfinished qualification explicitly. All13 original release requirements remain incomplete; cybersecurity excluded.

Continuation checkpoint30: The isolated publication commit32445b20d contains97,501 source-only files. Highest-priority local Git attributes and explicit rehashing repair6,960 staged EOL candidates; all repaired blob IDs equal raw working bytes. Fresh local clone uses no local-object sharing and installs the override before checkout. It passes all ten immutable vendor source digests and all four package-input tests (0.34s), with clean status. The three publication CI workflows add only the checked byte-preserving checkout step. A redundant serial source reread was stopped after the original full copy proof, exact index repair and fresh-clone verification succeeded; it is not claimed as a completed check. The publication README states unfinished qualification. Public bipxx/vispy_vulkan publication is authorized; remote creation/push is next.

Uniform6 original7948e1/session14710 closes e19ac6/exit1, driver35956/direct child70572. Result7b7ff672c22cba2a0b1e66cce54621eeef402d4014f713b3e7403db200540cbb and seal3a99629f1e384ef4c5287195ffd891e0e4416b5f417d41b6181db9d04c0165c2 preserve the failed pytest gate. Worker5874ce3f/c7957dac has inputs_preserved true but no successful complete-test or cleanup admission. No failed frames qualify or authorize a candidate capture. Complete independent failure review remains pending. All13 original release requirements remain incomplete; cybersecurity excluded.

Publication completion: public https://github.com/bipxx/vispy_vulkan, default branch main, initial commit750631b36e42f7f73392006e0f4115936a9ae6c9. Push730bb7/session29104 closesd4dd9a/exit0; remote main SHA independently matches. Fresh-checkout verificationaadd30/exit0 confirms all ten immutable vendor digests and four package-input tests. The serial redundant source recheck was interruptedb55dfb/exit1 and is not a passed check. Uniform6 complete original tool returns are retained at build/native57-uniform16-failed-process-root-6/original-tool-operations.json for pending failure admission. Automatic approval review rejected removal of C:/Users/HEQ/Projects/vispy_vulkan-publication-check, stating only blocked by policy; target remains and no retry was attempted. Canonical workspace remains without Git metadata; publication checkout is separate. All13 original release requirements remain incomplete.

Continuation checkpoint31: Uniform6 failed packet whole checka37fd8/exit0 verifies23 sealed files, direct35956/70572 closure, preserved input maps and unchanged native4,14 actual tests/13passed/1failed,13 test frames plus2reuseframes, and exact Boolean-adapter table restoration. The sole remaining test is mat2-array shader creation handle0; context loss remains a hypothesis, not a measured cause. Full Root process carrier7f2daf5e/b6ab20f5 retains original7948e1 and all same-handle polls through e19ac6. No reference/candidate admission follows.

A fresh source-only native-context diagnostic proposal is retained at build/native57-uniform16-context-diagnosis-root-1. It observes WGL current-context handles around exactly-once shader creation and GC events, with pytest node/time. It does not select a context, change GC policy, retry rendering, alter shader inputs or relax criteria. Generic observation controls29 and fake-provider/WGL integration controls65 pass (94 total), including normal/error restoration, zero handles, added hook preservation, invalid query rejection and both initially enabled/disabled GC states. No real provider/GPU diagnostic is run; real cause remains unproven. Fresh source integration/admission is next. Public main750631b remains the source release WIP. Cleanup-rejected scratch checkout remains untouched. All13 original requirements remain incomplete; cybersecurity excluded.

Continuation checkpoint32: Independent proposal1 review6d8fec7b/ed74d8b1 records228checks with two diagnostic blockers (cross-thread false context-loss attribution and observer errors masking original outcomes) plus the compatibility-wrapper nesting requirement. Rootfce1e6 verifies all24 carrier pins plus both original carrier files bce33ee3/2d48c5c2, with13 operations. Proposal2 preserves that correction but independent review identifies handle int conversion still outside the protected observation path. Proposal1/2 and all controls/refusals remain held. Fresh proposal3 moves conversion inside the protected observer, preserves original handle identity even when conversion raises, and passes148 injected controls via3899f7/exit0 PID67568. No real GL diagnostic is run.

Fresh diagnostic Source7 drafts are staged at build/native57-uniform16-gpu-root-7 and build/native57-uniform16-saved-root-7:63 files (38producer/25reader),768 known metadata pins each. The unchanged Boolean adapter wraps an inner context observer on the original scientific group; candidate/scientific fixtures remain byte-held. Diagnostic data stays outside the strict Boolean record. Successful upstream worker status is explicitly DIAGNOSTIC_UNIFORM14_AND_REUSE2_NOT_A_REFERENCE; unchanged parent and reader admission predicates reject it. Initial Source7 composition ff2a2a,199checks3d9110, declared proposal3 updatee44575 and final199checks3716bc are retained. Final full code proof01b4f8/exit0 PID70188 verifies838finitepins,191 whole raw/AST definition holds,3 routing-only definitions and one semantic predecessor change(worker.main). Packet build/native57-uniform16-prep-root-7/review-packet.json28cae604af7f41f766d4c7623be24d408844648e0ec2214f0e0ea5e0137957eb /proofb8131469cf5237c6b37ab4474d3d88ece889dbe1d67a269715f38eba945a0a4d is with the existing independent reviewer. No Source7 freeze/gate/runtime/GPU has run. Public main750631b CPU action39533235755 remainsqueued. All13 original release requirements remain incomplete; cybersecurity excluded. Cleanup-rejected scratch remains untouched.

Continuation checkpoint33: Proposal2 independent finding proofc0b03c05/7a940ff3 preserves235checks and the remaining conversion seam; Root1a5ef6 verifies its full10-original carrier a805f4df/40cc2468 with15 pins plus both carrier files. Proposal3 independent CLEAR7ae140/exit0 PID45500 verifies276checks/16pins,30 observation-error cases and arbitrary/unconvertible return identity, exact two-span inverse and held wiring. Rootf08901 verifies full8-original carrier5205da09/28f3ac9f,20pins plus both carrier files; no remaining material diagnostic finding. No diagnostic GPU/provider has run. Full Source7 integration review is now active on packet28cae604. The Root metadata-only Source7 gate c5d55b59 is prepared from exact prior6helper0dfe8662 with complete predecessor bytes retained, fixed38/25members/768known, fixed freshSource7 paths and mandatory actual freeze-row CLI. Gate not executed. Future freeze argv is prepared from current exact helper digests; actual process roles remain null. No Source7 freeze/gate/actual yet. Public CPU workflow39533235755 is stillqueued. All13 original release requirements remain incomplete; cybersecurity excluded.

Continuation checkpoint34: Source7 review finds B4: two concatenated output suffixes remain6 despite native7 receipt prefixes/CLI paths. Exacttwo-literal repairbbf67f/exit0 PID58036 updates only producer/saved path_boundary.py and dependent two freeze-contract core hashes, preserving four physical before copies and all prior draft packets. Fixed199checks and complete843pin proof7523ea/exit0 PID59404/35072 yield packetba90f8e8/proof6d6734e7. Full repair carriercc215c0e/b9ace8cf retains both originalexec calls and850currentpins; prior842pin draft carrier is historical for its four changed pins.

Independent final Source7 CODEf525da/exit0 PID63480 passes9,564checks/864pins,63files/768known,11whole inverses,46whole files and191definitions held; all four exact future output/receipt joins and both compatibility/diagnostic restoration layers pass. Root166fd7 verifies full28-original carrier9a312c9e/1202fdf2 plusall878pins. Root actual producer freeze d56a45/0PID17232 Source94b5ebdfd05265201b7ef505a23890f4b5d0f0dd1e51ff4306287b1f69a22116 (38/768), reader4abf54/0PID66080 Sourced9d3f6759fbfbbf3de09c03b53ef3291c08b94684788664a65f934c75042a9bf (25/768). Full Root freeze carriers e889788c/c6b58d09 and1279b44c/95abfbe8 retain exact single-terminal toolreturns. Independent frozen companion7ad350/0PID68932 bbcbad10/97842f33 clears807/794/833 needed and887pins/five facts; Rootbaaa45 verifies full6-original carrieraea6fb80496882a9bb54351b08b41a3bca0d9158177e6c20e80ef9efd5042b88/15169b2c with891pins plus both files.

Root metadata-only gates57675a/0PID47396 andc2e7a9/0PID27204 close with producer c1a92c3b/25f853fd andreaderfe37bbe4/901b4ea2; fullRootgates70a20d0f/91844dc7 and03068cd1/c9a30fdd. Rootcc7f2b/0PID23248 authors unchanged upstream requestbytes at native57-uniform16-upstream-inputs-root-7/inputs.json7ab9ddf7, all three reference rolesNULL. Fresh Source7 Native upstream NoVisit is underway; noSource7GPUactor yet. Diagnostic captures remain expressly ineligible as references even if all14tests pass.

GitHub run39533235755 job details are authoritativein_progress despite earliercached runlistqueued status. Completed jobs show missingexactsetup-python3.10.19/3.11.14 downloads on someplatforms,33unbuilt registered CTests aftersix-target-only builds, and WindowsDawn byte-check mismatch with85899files. Publication-only CI fix a30d401956506b245aa47da2bfd05ac0f8833372 is pushed: uv-managed exactPython binaries (availability verified for both patches/all4platforms), buildallCPUnative targets beforeCTest, sparse initial checkout then byteoverride/longpaths before vendor materialization. All20matrix rows held;3YAMLparse/diffchecks pass. Finite Windows sparse checkout control959346/0PID69844 preserves all16vendor byte fixtures from initialautocrlftrue; full Windows vendor and CI matrix qualification remain pending. Canonical three workflow files are not yet synchronized with the publication checkout, preserving current immutable canonical runtime scope during Source7 capture. No cybersecurity work. All13 original requirements remain incomplete.

Continuation checkpoint35: Fresh Source7 upstream NoVisit originale11806/session45205 closesc8e00b/0PID58028. Receipt164d54a0b4ec2f3566a1adc015f3c3971b47b033f3abd762a867bf92c5135501 /seald6250e75401f8373a8fe4128769e19930d3143767f52bda56f05adfcf90142f3 checks807/794/833Source maps,433JSON,69,758names/36roots and zero17/58/fresh8 protected visits. Rootf5b7ba verifies full11-operation carrierf71984f5/a6e5eedc and442pins plus both files. Rooted984e/0PID71892 prepares exact driverargv02f198288bee603aadf4cd2c754b21931caed1bcfd44785bb2bace71d26ac2f3 at build/native57-uniform16-upstream-inputs-root-7/actual-driver-argv.json. Root sole actual diagnostic starts0b6c36/session14601 once, remains live at first same-handle poll; no terminal result and no qualified reference. Full arguments/returns retained in functions store uniform7UpstreamActual1, no restart authorized from timeout alone.

CI fix maina30d401 is remoteverified. New run39536373368 has20rows; actual job status confirms exact managedPython install AND complete immutable vendor verification successful on Windows3.10.19 (119013852855),3.11.14 (119013852776),3.12.8 (119013852837) and Linux3.11.14 (119013852745). Allfour are now building every registered CPU target; completed whole-suite/ABI/hardware qualification is not claimed. Remaining rows run/queue. Canonical workflow synchronization is still intentionally pending until current Source7 immutable-scope capture closes. Cleanup-rejected old scratch untouched; finite new16file sparse-checkout control is retained as evidence. All13 original requirements remain incomplete; cybersecurity excluded.

Continuation checkpoint36: Source7 sole Root actor0b6c36/session14601 remains verifiedlive across same-handle polls, no terminal result or restart. WindowsOS observation sees driver35956/parent62152 (not yet selfreported); heavy admitted metadata byte checks progress (1,213,137 reads/36,424,900,414 bytes observed), so elapsed silence is not inferredfailure. Full live partial argv/execargs/toolreturns are saved at native57-uniform16-upstream-inputs-root-7/active-process-record-1.json and functionsstoreuniform7UpstreamActual1. No canonical input files are changed while capture is active.

Actual newCI a30d401 Linux3.11.14 job119013852745 builds allCPUtargets and passesall39CTests, then fails Pythoncollection because tools.fixture_gloo is not importable from the workflow script's directory. Fixed publicationGate adds only resolved repository root to sys.path; two real affected collector/failing-worker regression cases pass da71fb/0. Own first local test refusal43d722 was missing basetemp parent (not Source), retained. Full metadata suite then exposes12 existing visual/test deviations absent from compat/deviations.txt; eight production diffs are read in full and all45 original upstream test functions in four modified test modules are AST-held (82 added functions). The declaration now records those12 actual differences with reasons, preserving all parity assertions and immutable upstream pins. Metadata suite957e7a passes21cases; remaining CPU/SDF suite133991 passes71 with canonical-sourcepaths matching the installed editable package, total92localCPU/metadata cases. Own first remaining-suite refusal17e7c8 is the local editable/publication conftest-origin mismatch; corrected sourcepaths retain the same tests and strict gate. No pass is claimed for the refused runs.

macOS actualCI clang fails at tests/input_layout/runtime_batch_cache_contract.cpp:484: combinedauto declares size_t and uint64_t with different underlying types. The publication-only fix splits this one declaration, all other bytes/assertions held by change-proof.json. WSLGCC13.3 contract2af48d/session48408 closes09d084/0; WindowsClang19.1.5 contract1550ea/session84176 closes451731/0; both502checks pass CPUonly. Published commits:4a5cf9a26636588892d74f47f7e309e5c88c916f (portable declaration),75f0e7c7349c52e277eef5d126412a67f5b0bbb5 (pytest fixture import root),3df46b929d0e9661c8d9ffafc0349ad8651022bc (honest visual deviation declaration). NewmainCI39538657541 isqueued; a30d401 jobs retain their actual earlierSource scopes. Canonical synchronization remains pending for three workflowYAML files, qualification_gate.py, the one C++contract and compat/deviations.txt until Source7 capture closes. No production visual implementation is changed in this turn.

Automatic approval review rejects deletion of the new disposable input_batch_cache_contract-win.obj with only blocked by policy; file remains and no retry is attempted. Prior cleanup-rejected scratch/oldtargets remain untouched. All13 original requirements remain incomplete; cybersecurity excluded.

Continuation checkpoint37: Source7 original actor0b6c36/session14601 terminates879877/exit1, driver35956/direct child12292. Root whole-packet verification a75e9c/exit0 checks all21 sealed files; resultb8568541/seal59836ee3 retains14 tests,11passed/3failed,11test frames and2reuse frames. The failures are vec3 array, mat4 columns and scalar Boolean True. All145 context-observation events occur on native thread73468; three matched GC start/stop pairs change the current WGL context from nonzero to zero during precisely those three failing tests. The mat4 shader creation subsequently returns handle0. GC policy and dispatcher are restored; no retry, context repair or reference admission is claimed. Full original actual Root carrier33a8a760/sealda304d3c closes20d335/exit0. The prior live-process checkpoint is historical; Source7 must not be restarted or polled again.

Standalone Qt6.11/PyQt6.11 Windows diagnosis at build/qt-context-lifecycle-root-2/reproduce.py closesca5041/exit0: three closed GL-widget collections clear another widget's active WGL context, while three retained-GL, three collected-plain-widget and three explicit boundary-disposal controls preserve it. First diagnostic20132c/exit1 had the same measured native-context outcome but incorrectly expected the Python destroyed signal during wrapper GC; it is retained. Follow-up uses weak references to establish wrapper collection, with unchanged context predicates and enabled/default GC policy. A failed inline preparation command6376cc is retained; it ran no diagnostic.

Actual pristine upstream Canvas prototype at build/qt-context-lifecycle-proposal-root-1/check_upstream.py closesaa6cf9/exit0: baseline3/3 lose context after the previous closed canvas/widget is collected; temporary explicit top-level disposal3/3 holds the next context. Six adapter closes dispose six widgets, original close method is restored and upstream backend bytes are unchanged. Boundary controls3b8c97/exit0 preserve embedded-widget parent ownership, repeated Canvas.close idempotence, original exception identity and inherited-method restoration after exceptional exit. Initial harness setup refusals4c25c1 (backend not selected) ande0fe0a (QApplication absent) are retained with before scripts. These development controls establish a concrete lifecycle mechanism/remedy, not a qualified uniform reference, and do not mutate frozen Source7. Next rendering work is a fresh reviewed source integrating the teardown adapter before reuse2 and uniform14, with unchanged science/assertions/pixels and explicit ownership/restoration gates.

Public mainc3460497469c827cc2737e9786ea46ee1577cf38 changes the fork implementation/modifications to AGPL-3.0-only at the user's request. Original VisPy BSD text is attached byte-for-byte as LICENSE-BSD and retains its existing third_party/licenses copy; all19 third-party license hashes remain unchanged. Canonical and publication license/packaging/install/snapshot inputs are updated. Four package-input tests pass0537aa, actual scikit-build metadataada3bd reports License-Expression AGPL-3.0-only and contains exact AGPL and original BSD texts. Existing CRLF/trailing space in the preserved original BSD text remains intentional. Existing built wheels are historical artifacts and do not acquire the new metadata without rebuilding.

Actual macOS ARM CI119022689465 on15f709f reaches point_contract then rejects a mixed auto declaration combining size_t and uint64_t. New public maincafa26c46fc9fd090da4101f74c952d7e956b5a0 splits that declaration into three, preserving all assertions/other source bytes; WSL GCC syntax checke81d78 passes. Latest full20-row CPU run39540576219 is queued at the last authoritative observation; earlier runs39539164680 and39540378329 are terminalcancelled after supersession. No whole matrix or hardware qualification is claimed. After Source7 closes,9f1ecf explicitly synchronizes the six earlier CI-fix files from publication into canonical, preserving original bytes and all before/after hashes in build/agpl-license-update-root-1/canonical-ci-sync.json. Canonical strict workflow gate23695c passes21 package/source/reference-metadata cases, with no skips. Current license/build-input changes require fresh source provenance for future formal captures. Automatic approval review rejects deletion of the new build/agpl-license-update-root-1/pytest-temp scratch directory with blocked by policy; the directory remains and no retry is attempted. All13 original release requirements remain open; cybersecurity excluded.

Continuation checkpoint38: The reviewed lifecycle prototype is implemented as tools/upstream_qt_lifecycle.py, with an owning-thread check before the provider close, targeted top-level DeferredDelete delivery, embedded-parent preservation and whole-method restoration on exit. It is explicitly upstream VisPy0.17.0/PyQt6 only. Six CPU lifecycle/error contracts pass2e202a alongside two existing legacy capture-worker controls. Actual integrated pristine upstream Canvas control42dc88/exit0 reproduces context loss3/3 without the helper and preserves it3/3 with the public helper, with six disposals and exact original method/provider bytes held.

First development integration temporarily amended tools/oracle_capture.py; real upstream uniform_snapshot worker005566 passes. Broader strict suite ddf781 correctly refuses the changed current capture hash against saved reference provenance (26pass/1fail). The historical script is restored byte-for-byte; no saved reference metadata, images or assertions are changed. Its development body is retained at build/qt-context-lifecycle-integrated-root-1/oracle_capture-development-before-split.py. New explicit tools/oracle_capture_qt.py carries the updated protocol, self-identifying capture hash, lifecycle helper hash, finalized provenance/fixture teardown records and regeneration command. The legacy entry point remains the exact source for existing saved references. The new tool's process spawning uses its own entry point, and candidate paths do not enter the upstream adapter.

Strict suite865b0f passes27 existing metadata/new lifecycle cases; new entrypoint stale-result/nonzero-worker contractsd6cca9 add2 passing controls (8total in the lifecycle module). Actual new-entrypoint uniform_snapshot worker865b0f and parent/child flow23cb28 both pass unchanged whole fixture/landmark assertions, at build/evidence/qt-lifecycle-smoke-root-2 androot-3. These development captures are not the formal uniform14/reuse2 reference and confer no broader rendering qualification. CPU workflow adds all8 lifecycle/worker contracts to every existing matrix row. The latest cafa26c run39540576219 remains authoritatively live with no terminal job failures at observationde717a; no full-matrix pass is claimed. Next formal rendering step remains fresh Source8 integrating the helper before reuse2 and uniform14 under new current-source admission. All13 original requirements remain open; cybersecurity excluded.

Continuation checkpoint39: Fresh unfrozen Source8 preparation524b92 creates64producer/reader source members,753known pins,35 strict typed lifecycle receipt controls and13 whole-held scientific/Boolean/candidate files. Producer scopes the temporary Qt helper around BOTH reuse2 and uniform14; candidate uses nullcontext. Both worker and independent reader require exactly15closed/15disposed top-level widgets,0embedded and method restoration, without changing assertions or frames. No Source8 freeze/gate/provider/actor has run. Independent review identifies that the first draft assigned PASS before scope exit/receipt validation. Correction6944b4 moves the exact original success update after both, current worker09625dbdc702d91c52989949d9964c94d7086bf65926b257412dfde5e9ae8e52 and composition-2.json; physical before worker/contracts and first composition remain historical. The current Native57-named draft must be retargeted to freshly admitted native inputs before any actual launch.

Independent current-source audit proves Normal57 admission stale after current CMakeLists.txt, cmake/snapshot_wheel_sources.py, tests/markers/point_contract.cpp and tools/native_epoch.py differ from its pinned current inputs. New LICENSE/CI files alone are not represented in those old maps and are not asserted to invalidate them independently. No old guard is weakened, aliased to new bytes, or invoked as if current. The next prerequisite is a genuine Native58/w44 ownership/build/identity admission, retaining protected current57 native4. Inspection also finds that native_epoch.SOURCE_ROOTS omitted the three root license files now required by CMake install. Adding LICENSE/LICENSE-BSD/LICENSING.md makes new frozen native sources distributable with both licenses. Three new synthetic-freeze cases verify exact copied license bytes and rejection after mutation. Initial full suitea7dcfa/session64400 closes410c96/exit1 (20fail/36pass) because an existing dependency mock did not accept the require_mappings keyword. Updating that stub's signature preserves its intended mocked dependency scope; correctedd8bf77/session61632 closes10bd1c/exit0 with all56cases passing. Historical frozen guard copies stay unchanged.

Native58 portability CPU preparation firstf4478a refuses an incorrect50-total count because the old source map has48C++/header files plus2layer JSON inputs; no source freeze occurs, and the attempted configure records missing sources. Corrected author filters actual C++/header extensions, freezes48native inputs plus2current contracts; Windows/MSVC19.44 SDK build548df2/session50394 closes544f90/exit0. Exact subprocess runner2abecb/exit0 passes full point/ordinary grouping/identity/instancing/cache tests and502independent cache checks; all50 frozen/live source files hold before and after, no GPU/native Python module used. Proof and binaries remain retained at build/native58-portability-cpu-root-1.

Ownership author569677/exit0 produces build/native58-ownership-root-1/ownership-manifest-draft.json with614sources (7source deltas:3root licenses+4license/build inputs), same86owners/17packets/4131formal harness entries/42targets/44CTestnames. Two portability contract ownerships transfer explicitly to the new tested packet; the prior single-point packet and prior cache ownership are retained in transfer history without archive mutation. Current57activation/native4 match and are protected; new58/w44 destinations remain absent. No real58preflight/freezer/build or activation has run; independent complete exclusion/ownership review is pending. Latest ff74fa0 CPU run39541418003 has no terminal job failures at observationb0848e, and whole-matrix qualification remains pending. All13 original requirements remain open; cybersecurity excluded.

Continuation checkpoint40: Original Native58 ownership verifier f87d26/session82681 terminates8a29e9/exit1, PID55860, after123172 verified files/2691654122 hashed bytes. It refuses the inherited old hash for tests/contract/test_native_epoch_guards.py; exact namespace and CPU-proof phases are not reached. Its REFUSED report ffe2ecdad2211880cb70119adfd9a1214aa03da0987aa9c6eef040eb81e4c6ff and full26-original-operation carrier b762d8bd331cd449aa434f5994f36a9ef80c11fd6031132ec550519c69bb00d9 remain unchanged. Root d9eb78 verifies all109 finite carrier metadata files and retains the original refusal; it does not rehash or promote the partial pass.

Root correction7c661f checks4225 finite source/harness/tool pins and finds only that stale harness entry. New build/native58-ownership-root-2/ownership-manifest.json a2b8f7ec8a18a626bf51788ad96f07398db4c81ac36b87f30ca5edbec27fc488 changes its hash from3d3c0031d45b380fa1f82960d3b105ac5caad38384e1d8753a00ca2feadad110 to c1135c1683db9aa7e1235a3a8cc3ff2635d7b503d56c8b5c53e8cec91bf586f5, and serializes JSON with LF instead of CRLF. Implementation source, packet ownership and destinations are unchanged. Independent correction/resume proposal bfa73dba2460c7ab00e4c478869936730a9d5b6ff88da07b5802782ff6d3f803 preserves the failed lineage and admits only the exact123172 successful sorted-prefix pins for reuse;2153 remaining/changed/overlay pins and all namespace/proof joins still require verification. Root3214af independently derives that partition;95dd07 verifies the full19-file/four-operation proposal carrier, including the reviewer's corrected raw-inverse assumption refusal.

Fresh names-only boundary author d8e9a1/session5958 closes2b98b3/exit0 PID57576: Native3 result1006df8d0d80cc1c447760780df606f2d7173659bc0607f6086e8825b1cf0773 covers125338 prospective pins,71 roots and114 finite metadata inputs, with zero target/protected payload calls. Bounded payload verification and composed ownership admission remain pending. No Native58 generic preflight/freeze/build, activation or formal Source8 capture has run. CPU workflow39541418003 reaches18/20 successful jobs with no failures at c0ba0f; Intel Mac CPython3.11/3.12 jobs remain in progress. These CPU checks do not qualify Metal graphics. AGPL implementation licensing retains the exact original VisPy BSD license and third-party notices in source/package/SDK configuration. All13 original release requirements remain open; cybersecurity excluded.

Continuation checkpoint41: Bounded ownership verifier17e76c/session86553 closes8de688/exit0 PID64640 with260522 checks. Final Native3 result8f6dbfee94a1016b6106527f6e9cf8164ad396e21271fadb1e927a51a8122b65 clears all125338 prospective pins, exact614 source/17 packet/214 SDK/119083 dependency namespaces and CPU proof joins. It retains123172 verified prefix files from the REFUSED original, freshly hashes2153 remaining-plan rows plus2 canonical CPU-owner joins, and preserves native4. Root3f5766 verifies the full128-file/four-operation carrier664e2c5e69001e91f2fa81ebecdac3e64985b6733a5a72f3ac4d43e34ffb8f55 without replaying the old payload pass. This admits ownership only.

Root native preflight d01c7c/session74071 closes41facc/exit0; full7-operation carrier8809b2c847a5b32e164abb5b91df2395b005250eed44f9ea5bdfe3c749654ea1 is closed65dbed. Actual freeze3ce8d2/session73990 closesf967f9/exit0, frozen-inputs b565444aad0117ec96959b89d68d3a378aecc6bb13e9c3617e29c6745bc6aa25 at build/evidence/native-pass-58/frozen-inputs.json. Root251b71 closes all11 original operations in carrierd7c1e9d7351507dbeae3dcfc13e71cf0051b16f32d11ebb0ef69f3435d45cdf9 and verifies614source/4131harness/86owners, exact three snapshot license files and protected native4 continuity. Isolated build eb5bfb/session31590 is active; CMake configuration and _dawn linking have completed at observationd4ae40, but no completed build/CTest/admission/activation claim follows. Independent completed-build review preparation4da313eaa64536e72bf539b61649deff52ac89890cf5827cbc12813f415000ad prepares6821 fresh frozen-copy pins and waits for terminal output/44CTest/producer roles. Root02a197 verifies its complete22-file/three-call metadata carrier.

Root59803b prepares Native58 current-identity transition metadata only: all523 pure package files equal the admitted57 parent, seven source-map deltas include three added license files, and eight changed historical source/harness/tool bindings resolve to exact retained physical copies. Future staging must copy523 parent members and0 current replacements; the old522-plus-one parser rule does not apply. No new stage or identity is admitted. CI39541418003 has18 successful jobs, one Intel Mac3.11 job still running, and Intel Mac3.12 job119030146593 failed only when artifact finalization timed out after39/39 native CTests and100 Python tests passed. Exact logs/job records are retained by34edaa under build/native58-ci-observation-root-1; the upload failure remains a failure. Local commitcfce8ded0 adds the existing56 native-epoch/license regression cases to every unchanged20-row CPU matrix; YAML/diff checks pass, actual expanded CI is pending. Push is held while the current run remains active. All13 original release requirements remain open; cybersecurity excluded.


Continuation 2026-10-22, observer-free volume implementation: new versioned tools retain all frozen worker/controller/reference/native sources and thresholds. Cold/warm-only geometry observation restores the exact frozen parser wrapper for measurement, with source/warm corroboration and raw per-paint counter bounds. New controller preserves gap labels, joins both start/finish source maps and explicit sample leaves, and reuses existing process ownership/cleanup. Independent peer reviews remain FIX_BEFORE_EXECUTION historical verdicts; root resolves required real-release-gap test and receipt findings with cpu6:434 passed,0 failures/errors/skips, full26 source closure plus command/count/report hashes. Actual fresh collection build/volume-observer-free-pairs-run-root-1 is FAILED/PARTIAL: first upstream/candidate pair verified; next candidate rejected for2 unsolicited unattributed Qt paints. All3 actual workers pass geometry handoff with0 measured observer invocations; actual candidate warm geometry empty. Independent partial-review1.json revalidates firstpair images/hardware/rawsamples, rejection of thirdworker and allterminal/cleanup. Do not promote this to fivepairs, speedup, observer release-gap closure or fullmode/platform qualification. Pending: investigate unsolicited paints without suppressing renderer work or weakening ownership, collect5 valid pairs, actualfullmode, scanout/driverallocator and allother original13 requirements. New source/WIP not pushed. OriginalAGPL+BSD notices unchanged; cybersecurity excluded.
