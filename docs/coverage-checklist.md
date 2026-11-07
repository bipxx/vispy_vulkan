# VisPy Vulkan coverage checklist

Last reviewed: **2026-11-07**. This is the live coverage worklist for implementation,
verification and release follow-up. The [consolidated plan](superpowers/plans/2026-10-28-consolidated-plan.md)
remains the implementation plan; the linked manifests and admissions remain the
authority for each result.

The target is practical compatibility with documented differences and useful
improvements. Full upstream parity is optional, not a condition for completing
the selected release. An unreviewed API is not automatically an unimplemented API.

## How to read and maintain the checklist

- `[x]` means the stated exit condition is met **at the stated evidence level**.
- `[ ]` means work, verification, an explicit disposition or a release step remains.
- **Release-qualified:** admitted on the named installed release artifact/profile.
- **Source-tested:** code/regression evidence only; not qualification of a new wheel.
- **Historical:** valid evidence for an earlier artifact or environment.
- **Partial / audit:** some behavior has evidence, but the broader claim is unsettled.
- **Open:** a known defect or an unmet exit condition.
- **Deferred / unsupported:** an intentional boundary, not a failing release gate.

Do not combine these levels into a universal coverage percentage. In particular,
142 inventory parents, 128 admitted Tk criteria, eight mandatory rows, and 23 CI
jobs are different denominators. None measures line or branch coverage.

For every implementation, test, review or qualification change:

1. Identify the affected checklist IDs before starting.
2. Update those entries in the same change, including partial progress or a failure.
3. Link the source/test and durable result; state the source commit, wheel hash,
   platform, binding and important values/formats when claiming installed coverage.
4. Check an item only when its exit condition is proved. Keep source-tested fixes
   separate from the last published wheel until new artifacts are qualified.
5. Preserve old artifacts, failures, tolerances and admissions under their original
   identities. Add a successor instead of relabeling historical evidence.
6. Update the review date and the short change log below. Keep raw logs and captures
   in their existing evidence records, rather than copying them into this file.

Checked baseline items must be revalidated for an affected successor artifact;
they are not permanent passes for future code. Do not rebuild or repeat tests just
to update documentation. Follow [build hygiene](build-hygiene.md) for actual runs.

## Published baseline

These checks refer to **`v0.17.0-vulkan.1`**, not the later shutdown source fix.
Exact wheel hashes and scope: [release notes](release-0.17.0-vulkan.1.md).
Windows graphics evidence is bounded to its recorded GPU/driver cells; it is not
qualification of every Vulkan device. Linux evidence below uses software Vulkan.

| Artifact | Qualified scope | SHA256 |
| --- | --- | --- |
| Windows cp312 x86_64 | Selected Windows Vulkan profiles | `5c7142f38b0867fc744a7fe6025b8397f1bada46641b6d05da0d54dadbfab29e` |
| Linux cp312 x86_64 | Selected WSL lavapipe X11 profiles; `manylinux_2_39_x86_64` | `66f35ab0dae878af1744f2061be1042bd2c5abfd24d3192c7456865f2c6fd3f7` |

- [x] **REL-01 — Source and artifact identity.** Fresh release producers, native
  contracts, package members, dependencies and original licenses joined to the
  selected artifacts. Evidence: [record-renewal ledger](../build/runs/r2-records-315/ledger.md).
- [x] **REL-02 — Required CI.** All 23 selected jobs pass with the required source
  and attempt identities. Evidence: [CI ledger](../build/runs/r2-ci-319/ledger.md).
- [x] **REL-03 — Independent promotion.** Both finite Tk candidates admitted:
  120 state/resource criteria and eight capture criteria. Evidence:
  [promotion ledger](../build/runs/r2-promotion-320/ledger.md).
- [x] **REL-04 — Distribution.** Windows/Linux wheels, GitHub Release, hash-linked
  package index and clean channel-install smoke completed. Evidence:
  [release notes](release-0.17.0-vulkan.1.md), [publication ledger](../build/runs/w11-publication-321/ledger.md).

### Mandatory installed profiles

Each checked row requires all three strict gates, the defined functional lifecycle
and zero live-resource gauges on its exact installed artifact. This does not mean
that every Qt feature or upstream VisPy API was exercised. Authority:
[strict matrix](../compat/no-opengl-matrix.json).

- [x] **PRO-01 — Windows Vulkan headless**, CPython 3.12.
- [x] **PRO-02 — Windows Vulkan QWidget / PyQt5**, selected no-OpenGL profile.
- [x] **PRO-03 — Windows Vulkan QWidget / PyQt6**, selected no-OpenGL profile.
- [x] **PRO-04 — Windows Vulkan QWidget / PySide6**, selected no-OpenGL profile.
- [x] **PRO-05 — WSL lavapipe X11 headless**, CPython 3.12, software explicitly allowed.
- [x] **PRO-06 — WSL lavapipe X11 QWidget / PyQt5**, selected no-OpenGL profile.
- [x] **PRO-07 — WSL lavapipe X11 QWidget / PyQt6**, selected no-OpenGL profile.
- [x] **PRO-08 — WSL lavapipe X11 QWidget / PySide6**, selected no-OpenGL profile.

### Finite Tk application and rendering scope

The checked behaviors below are the bounded scope of the admitted candidate,
including its ordinary, mutation, failure and recovery criteria. They do not
discharge the broader inventory parents. Evidence and exact values:
[practical scope](practical-compatibility-release.md),
[state/resource coverage map](../compat/candidates/tk-state-resource-1/coverage.json).

- [x] **TK-01 — `tk.backend.raster`:** standalone and supplied-parent raster targets.
- [x] **TK-02 — `tk.application.manual`:** manual event progress and host-preserving quit.
- [x] **TK-03 — `tk.canvas.basic`:** embedded/standalone extent, RGB presentation and close order.
- [x] **TK-04 — `tk.context.current`:** two-canvas current-target and GLIR ordering.
- [x] **TK-05 — `tk.context.shared`:** shared program, texture and buffer survive first-consumer close.
- [x] **TK-06 — `tk.canvas.recovery`:** same live widget/resources recover after injected device loss.
- [x] **TK-07 — `tk.timer.once`:** one-shot callback, pixel update and generation stop.
- [x] **TK-08 — `tk.gl.flush`:** submission without an implicit completion/presentation claim.
- [x] **TK-09 — `tk.wrappers.submission`:** ordered clear/flush/finish and independent counters.
- [x] **TK-10 — `tk.wrappers.raster`:** selected viewport/blend/depth/scissor triangle behavior.
- [x] **TK-11 — `tk.readback.rgba`:** independently expected full-target RGBA8 bytes.
- [x] **TK-12 — `tk.object.delete`:** explicit deletion and queued resource retirement.
- [x] **TK-13 — `tk.buffer.triangle`:** selected float32 vertex-buffer triangle layout.
- [x] **TK-14 — `tk.texture.rgba8`:** selected texel mutation, sharing and loss recovery.
- [x] **TK-15 — `tk.program.texture`:** selected vertex attribute and sampler2D program.

### Finite Tk capture scope

Authority: [capture coverage map](../compat/candidates/tk-capture-1/coverage.json).

- [x] **CAP-01 — Ordinary crop:** byte and normalized float32 RGBA crop with independently
  expected orientation, alpha and pixels on the defined target.
- [x] **CAP-02 — Resize/mutation:** defined resized target and crop crossing quadrant boundaries.
- [x] **CAP-03 — Rejected arguments:** malformed viewport preserves the original error and
  pending work without extra submission, finish, wait or presentation.
- [x] **CAP-04 — Recovery:** valid retry consumes the retained clear without an intervening repaint.

## Immediate post-release work

- [x] **FIX-01 — Source-tested shutdown cleanup:** clear the host-block pool after
  engine/device teardown. The regression fails before the fix and passes on Windows
  and WSL; it covers warm caches, engine-owned imports, external owners and repeated
  shutdown. It executes the production wrapper with real CPU pools and simulated
  engine teardown. Evidence: [verification](../build/runs/shutdown-fix-322/verification.json),
  [regression](../tests/contract/test_upload_cache_shutdown.py).
- [x] **FIX-02 — CI registration:** the new regression is included in the curated
  suite, and its registration check passes. Evidence:
  [recorded pytest result](../build/runs/shutdown-fix-322/pytest-final.log).
- [x] **FIX-03 — Current progress summary:** the consolidated plan identifies the
  published wheels, current mandatory rows and the unreleased source fix separately.
- [ ] **FIX-04 — Review and integrate the source fix:** complete the applicable
  source checks and normal review/merge path; retain exact source identity.
  **In progress, 2026-11-06:** publication drift has zero unexplained paths against
  fetched main `27600878`. The existing candidate validator fails on the changed
  `cpp/runtime.cpp` native-input pin, as expected; matching artifact/record work
  from FIX-05 is a prerequisite to a green integration. The passing CPU regression
  does not override that refusal. Evidence: [drift report](../build/runs/source-fix-integration-323/drift-before.json).
  Source candidate: `b5fbe591`. Independent source review found no blocking defect:
  [review report](../build/runs/source-fix-integration-323/peer-review.md). This
  review does not approve an installed artifact or waive the native-input failure.
  Isolated CI setup `source-fix-integration-323` stopped before tests because the
  offline cache lacked locked Cython 3.1.5. Its checkout and scratch were removed;
  [cleanup receipt](../build/runs/source-fix-integration-323/post-cleanup.json)
  verifies 27 retained files. Retry `source-fix-ci-324` used the same source commit,
  the same 4 GiB limit and exact hash-checked locked package downloads. Dependency
  verification, all 44 CPU contracts and the curated shutdown regression passed.
  Parallel pytest temporary-directory collisions and two Windows fixture path-length
  failures were resolved by rerunning affected commands with isolated/short owned
  temporary paths. **16/23 source commands pass; seven still fail on old runtime
  pins.** These are source-CI command counts, not API coverage. Evidence:
  [acceptance report](../build/runs/source-fix-ci-324/acceptance-report.json).
  Matching native artifacts/records remain the next prerequisite; no merge or
  published-wheel coverage is claimed.
  Cleanup is complete: both temporary checkouts and managed scratch are absent;
  [run 324 receipt](../build/runs/source-fix-ci-324/post-cleanup.json) verifies
  127 retained files. uv's empty cache marker caused a preserved generic-planner
  refusal; audited `uv cache clean` removed only this run's cache before the
  normal registry-aware plan/apply succeeded.
- [x] **FIX-04-OBS — Fresh candidate source observations:** both successor wheels
  passed the 56 installed state/capture assertions and the real eight-branch Tk
  workflow. Both source/native capture observations passed all four asserted modes;
  each of the five active mutation controls was independently rejected. All nine
  live-resource shutdown gauges were zero. Evidence:
  [observations](../build/runs/shutdown-observations-332/verification.json),
  [cleanup](../build/runs/shutdown-observations-332/post-cleanup.json) (72 retained
  files rehashed, 86 MB scratch removed). This supports source/profile preparation;
  it grants no independent approval or installed observer/profile admission.
  Canonical v1 candidate records were not modified during collection.
- [x] **FIX-05 — Patch artifact verification:** build successor artifacts containing
  the fix, verify native/package/license joins, and exercise actual renderer teardown
  with live uploads and imports on Windows and WSL. CPU wrapper evidence alone does
  not prove a new installed renderer artifact.
  **Complete at local artifact-verification scope, 2026-11-06:** Windows and WSL
  substeps below passed against exact unreleased successor wheels. This does not
  complete record renewal, source integration or release qualification.
- [x] **FIX-05-WIN — Local Windows successor verification:** product source
  `b5fbe5917bcd5f6fb21cfda425980a12a8af34f1`, native `_dawn` SHA256
  `3b7e54641a127c72f476229a3459494154e83f519f41323f28c2f4fe0bd22feb`;
  unreleased cp312 x86_64 wheel SHA256
  `43af80d30a207e4f5e31273829fb2191d504f18cba2946a8229de7507b4b5c6c`.
  Reused the retained SDK/prepared environment; all 44 native contracts and the
  source/native/package/original-license joins passed. All 537 installed package
  members were verified under `-I -S`. Four distinct installed cases passed:
  texture upload, instanced/vertex buffer uploads, and actual shutdown ownership.
  Scope: `dawn_headless`, NVIDIA RTX 4090 / driver 610.88, 512×512 RGBA8 shutdown
  payload. One held submission and 2 MiB pinned imports retired; all ten checked
  ownership gauges were zero. Repeated shutdown and exact readback of a separately
  owned snapshot after shutdown passed. Warm CPU-cache byte release remains proved
  by FIX-01's direct CPU regression, not a new installed-memory gauge.
  Evidence: [native proof](../build/runs/shutdown-native-325/native-validation.json),
  [installed acceptance](../build/runs/shutdown-package-326/acceptance-report.json),
  [native regression](../tests/native/test_shutdown_uploads.py). The initial
  regression's context-manager cleanup failure and corrected rerun are retained;
  no native rebuild was needed for that test correction. Both runs' scratch is
  removed: [native cleanup](../build/runs/shutdown-native-325/post-cleanup.json),
  [installed cleanup](../build/runs/shutdown-package-326/post-cleanup.json).
  This is local artifact verification, not mandatory-row or release admission;
  the published v1 wheel is unchanged.
- [x] **FIX-05-LINUX — Local Linux successor verification:** fresh
  [CI run 42335940224](https://github.com/bipxx/vispy_vulkan/actions/runs/42335940224)
  passed at source `a00461b60d0751a4290e0000f1df8b8967a9af3d`. Its native production
  bytes match reviewed `b5fbe591` (the retry changes only collector/test/docs inputs).
  Native `_dawn` SHA256
  `2280cd8161fe058f39e4f7ed2f1c55c3ae59404323a849ce97d3612099fcf0cf`;
  unreleased cp312 x86_64 Linux-tagged wheel SHA256
  `b71ed6a3bfd5c43f4147a599787143a3fa5b98dbd6f552ffe9db26b81c37eb6d`.
  All 44 native contracts, CI installed smoke checks and producer cleanup passed.
  The original source/native/package/original-license joins validate. The WSL
  `-I -S` consumer verified all 537 package members and passed the same four
  installed cases as Windows: texture upload, instanced/vertex buffer uploads and
  actual shutdown ownership. Scope: `dawn_headless`, CPython 3.12.13, llvmpipe /
  Mesa 26.1.8 / LLVM 18.1.3, 512×512 RGBA8 shutdown payload. Host imports were
  supported; one held submission and 2 MiB pinned imports retired. All ten checked
  ownership gauges were zero, repeated shutdown passed and the external snapshot
  produced an exact pixel readback after shutdown.
  Evidence: [original native join](../build/runs/shutdown-linux-retry-329/native-capture-validation.json),
  [archive join](../build/runs/shutdown-linux-retry-329/linux-archive-join.json),
  [installed acceptance](../build/runs/shutdown-wsl-330/acceptance-report.json).
  Existing WSL driver/dependencies were reused; no local native build or new
  environment was needed. [Transport cleanup](../build/runs/shutdown-linux-retry-329/post-cleanup.json)
  rehashed 242 retained files; [consumer cleanup](../build/runs/shutdown-wsl-330/post-cleanup.json)
  rehashed 14. This is software Vulkan local verification, not native Linux GPU,
  mandatory-row or release admission. The wheel is not release-retagged; the
  published Linux v1 wheel remains unchanged.
  **Initial attempt, 2026-11-06:** WSL and `/mnt/c` were writable with sufficient
  capacity; the inherited guest registry, existing Python/dependencies and pinned
  external lavapipe library are available, and guest scratch is empty. Pushed
  only the reviewed source branch at `b5fbe591` and dispatched
  [fresh Linux CI run 42334823925](https://github.com/bipxx/vispy_vulkan/actions/runs/42334823925).
  This producer is needed for later admission; no duplicate local native build is
  planned. The first dispatch request timed out before acceptance; its preserved
  direct retry succeeded. Evidence: [producer decision](../build/runs/shutdown-linux-327/fresh-producer-decision.json),
  [filesystem check](../build/runs/shutdown-linux-327/wsl-filesystem.log).
  The first CI run failed before the renderer build: the driver and all four
  controls passed, but the parent live-size sampler raced with child cleanup and
  terminated the driver phase on `FileNotFoundError`. Original failure/partial
  inner-cleanup records are preserved; [local transport cleanup](../build/runs/shutdown-linux-327/post-cleanup.json)
  rehashed 93 retained files. The sampler now catches only a vanished-file
  `FileNotFoundError`, retaining budget checks, other I/O failures and the unchanged
  strict cleanup verifier. A deterministic failing baseline, 3/3 regression checks
  and 39/39 WSL lifecycle cases are retained in
  [run 328](../build/runs/ci-space-race-328/verification.json). Its guest scratch is
  [cleaned](../build/runs/ci-space-race-328/post-cleanup.json); the Windows successor's
  production inputs remain unchanged, so it needs no native rebuild.
  Exact current/previous collector hashes remain recognized by the semantic
  verifier; the actual published v1 producer still validates unchanged.
  [Verifier controls](../build/runs/collector-protocol-331/verification.json):
  83 pass; one real-candidate case still stops at an old evidence pin (actual exit
  1, not waived). [Guest source-test cleanup](../build/runs/collector-protocol-331/post-cleanup.json)
  is complete. The Windows-mounted verifier attempts' capture/timeout failures and
  unknown original child wait are preserved and are not passing gates.
- [ ] **FIX-06 — Patch qualification and publication:** renew affected records and
  mandatory rows on those artifacts, satisfy required CI/promotion, and publish only
  through the authorized release process. Existing v1 wheels do not contain FIX-01.
- [x] **FIX-06-VERSION — Successor release metadata:** choose/freeze the successor
  package version before final record renewal and qualification. The archive
    verifier originally hard-coded the v1 distribution directory, METADATA version
    and wheel filename. Support a source-bound expected version while preserving
  v1 validation; test rejection of mismatched/duplicate metadata and retained
  original notices. Audit the other packaging/CI callers before changing defaults.
  Do not overwrite the published v1 assets or reinterpret the development wheels
  as a separately versioned release. Native reuse must continue satisfying the
  unchanged producer-input rules; no verifier relaxation to avoid a build.
  **Partial, 2026-11-07:** the archive core now accepts an explicit normalized
  expected version, and the record validator derives that expectation from the
  source project's metadata. Distribution directory, METADATA, RECORD and
  original-license namespaces follow the same expectation. Legacy defaults remain
  v1, with no archive-driven version inference. A six-failure baseline now passes;
  all 53 focused cases pass, and the four actual published/development v1 archives
  still validate. [Evidence](../build/runs/package-version-333/verification.json).
    The pure-source repackager now binds RECORD, metadata lookup and license
    namespaces to the explicit expected/source version; it still preserves frozen
    metadata, notices, native bytes and membership. Three successor cases failed
    before the fix; all 47 repackager cases and 126 related cases now pass. The
    main CI wheel identity check and Linux producer auditor use source metadata
    instead of a v1 literal. Linux auditor identity includes the added helper.
    Embedded workflow Python blocks parse successfully; CI/native execution has
    not been repeated. [Caller evidence](../build/runs/package-callers-334/verification.json).
    **Metadata selected, 2026-11-07:** the successor is `0.17.0+vulkan.2`
    (planned tag `v0.17.0-vulkan.2`). Project, source module and lockfile agree;
    dependency content is unchanged. The required oracle and installed identity
    checks now use that source expectation; future preparation scripts derive the
    expected filename without modifying existing prepared-environment records.
    All 128 related source cases pass. Thirty remaining literal-bearing files have
    explicit legacy, synthetic-fixture or historical-protocol dispositions; they
    provide no v2 qualification. [Version audit](../build/runs/successor-version-335/verification.json).
    Exact older Linux producer captures still validate, and unknown collector/
    auditor implementations are rejected even after consistent source/retention
    rebinding. The full protocol suite records 85 passes and one stale-candidate
    refusal, not an overall pass. [Protocol evidence](../build/runs/version-protocol-336/verification.json),
    [historical joins](../build/runs/version-protocol-336/historical-producers.json),
    [guest cleanup](../build/runs/version-protocol-336/post-cleanup.json).
    **Complete at metadata/source-freeze scope:** exact source
    `4ed660bfcac535ed46ff3d092c1a9dae1213ed82` is pushed to the working branch;
    final drift has zero unexplained paths. An initial two-profile omission and its
    correction are preserved. The publication owner's checkout/index are unchanged.
    [Source freeze](../build/runs/successor-freeze-337/verification.json),
    [cleanup](../build/runs/successor-freeze-337/post-cleanup.json).
    Final matching producers/records, reviews and qualification remain FIX-04/FIX-06.
    No v2 artifact, installed identity, CI admission or release publication is claimed.
    **Final producer attempt, 2026-11-07:** Linux CI `42355088675` stopped in
    software-driver preparation before the renderer build. Its original failure
    artifact `13566538820` remains on GitHub; local transport was refused because
    C: fell below the 10 GiB reserve. Inner driver exit/cleanup evidence has not
    yet been retrieved. [Failure status](../build/runs/successor-linux-338/verification.json).
    The Windows SDK-linked run was cancelled when free space no longer covered
    its remaining declared allocation; the compiler and producer both have actual
    nonzero exits and waits. No CTests/new outputs are claimed. Its 56,846,683
    scratch bytes were removed and 79 retained files rehashed.
    [Capacity stop](../build/runs/successor-native-339/verification.json),
    [cleanup](../build/runs/successor-native-339/post-cleanup.json).
    New allocations on C: remain stopped. D: has spare capacity, but using it
    first requires an exact source/origin/proof-path audit; pinned inputs and
    rejected cleanup targets must remain untouched.
    **Windows storage/producer recovery, 2026-11-07:** completed the source and
    write-path audit and a fresh SDK-linked leaf under the hash-bound
    `windows-native-secondary-v1` profile. Source, prepared Python/compiler,
    original SDK and dependency origins stayed on C:; scratch and retained
    outputs used D:. All 44 native contracts passed without skips. All 133
    compiler/harness inputs matched source `982ceb83` before and after; cache,
    project, command and shipping-output joins passed, as did SDK/tool identity
    checks. No SDK/environment rebuild or install was needed.
    The 768 MiB allocation and shared 20 GiB/10 GiB limits are unchanged.
    Strict cleanup removed 277,648,912 bytes and rehashed 145 retained entries.
    [Native proof and cleanup](../build/runs/windows-secondary-native-374/external-evidence.json).
    The verifier's 21 new storage controls pass on Windows and WSL. Each current
    module run has 74 passes and the same two stale-v1-record failures; the old
    verifier/schema/tests reproduce those failures with 53 passes. The retained
    original Windows native proof still validates identically. This is not an
    overall source-suite pass or independent review.
    [Baseline comparison](../build/runs/native-storage-baseline-373/external-evidence.json).
    The Windows native producer/storage-path blocker is closed at local proof
    scope. Windows v2 packaging/installed checks were still pending here; their
    later closure is recorded below. Formal cross-store provenance admission,
    successor records and strict gates remain open.
    **Recovery, 2026-11-07:** selected fresh managed storage on D: under the same
    20 GiB/10 GiB policy, inheriting every protected/blocked path. Recovered all
    40 original Linux failure-artifact members. Ninja removed a temporary `.o.d`
    file during the inner Mesa guard's strict snapshot; that guard terminated and
    awaited its compiler. Both original remote cleanup records passed. The live
    sampler is now separate from terminal cleanup and preserves owner, registry,
    global/profile limits and other I/O errors. All 17 driver-tool tests pass on
    Windows and WSL, including the unchanged terminal-snapshot refusal control.
    D: transport and test scratch are absent after strict cleanup. Ten known pytest
    aliases were unlinked without following their targets; the initial refusal is
    retained. [Evidence references](../build/runs/driver-guard-341/external-evidence.json).
    Fresh Linux CI and the Windows producer/storage-path audit remain pending.
    **Reviewed retry:** independent source review found no blocking guard defect.
    Its production-wiring test request is closed by actual `build()` entry and
    old-guard mutation controls; the complete module now passes 19 cases on each
    platform. Tool-only source `fa72c6da` is pushed with zero unexplained drift;
    native production inputs remain unchanged from `4ed660bf`. Original test-fixture
    failure and cleanup refusals remain retained. Both storage roots have empty
    managed scratch. [Review/freeze references](../build/runs/driver-freeze-343/external-evidence.json).
    Fresh Linux retry [CI 42357137754](https://github.com/bipxx/vispy_vulkan/actions/runs/42357137754)
    was dispatched at that checkpoint; its verified outcome is recorded below.
    The later D: Windows producer recovery is recorded above; C: allocations remain stopped.
    **Linux v2 producer verified, 2026-11-07:** CI `42357137754` completed
    successfully at `fa72c6da`. All 44 native contracts and the unchanged original
    native/source/archive/license joins pass. The raw cp312 Linux wheel is
    `1afcf55a926022024d6202e5c32d7102dfa9f478f101bccb6fcee388e60a475e`;
    `_dawn` is `928e043978ac943d1aa44470656b7a43ab574523d60512898f7aa19c1aa4b5ec`.
    Both original remote cleanups passed. All 166 artifact members are retained;
    transport scratch was removed and 184 retained files rehashed.
    [Producer/archive evidence](../build/runs/linux-artifact-350/external-evidence.json).
    Two newer module-description edits are the only current pure-member changes.
    Repackage them around these verified native bytes, then run installed checks;
    this result grants no candidate, profile, hardware or release admission.
    **Current pure assembly:** the two corrected descriptions are now packaged
    around those same verified native bytes. Current cp312 Linux wheel:
    `4c826163cce271b36cd3ab3a981c8dec506f4cca7fa0396c5c381dfd462d59dd`.
    Exact archive/source/license joins pass; metadata, membership and native bytes
    are unchanged. Source is frozen/pushed at `99aafd1c`, with zero unexplained
    drift. [Source freeze](../build/runs/gloo-freeze-352/external-evidence.json),
    [assembly/cleanup](../build/runs/linux-pure-353/external-evidence.json).
    **Current installed WSL checks:** this exact wheel passes four upload/shutdown
    cases, including a held submission, 2 MiB of pinned imports, ten zero gauges
    after repeated shutdown and independent external-snapshot readback. A separate
    installed run passes 56 state/resource cases without skips and the unchanged
    eight-branch Tk recovery validator with Tcl/Tk 9.0; its nine measured shutdown
    gauges are zero. Both runs verify all 537 installed package members and use
    the pinned software Vulkan driver. No native rebuild or new environment was
    needed. [Upload/shutdown evidence](../build/runs/linux-installed-354/external-evidence.json),
    [state/Tk evidence](../build/runs/linux-observations-355/external-evidence.json).
    The same installed wheel also passes all four capture branches; five active
    output/queue corruptions are rejected, with nine zero gauges after every
    child. [Capture/control evidence](../build/runs/linux-capture-356/external-evidence.json).
    These local checks do not renew candidate admission, mandatory profiles or
    release qualification. Windows v2 production, admission and publication
    remain open; final-tagged Linux verification is recorded below.
    All three runs completed strict cleanup: 89,570,275 scratch bytes removed;
    17, 18 and 34 retained entries respectively rehashed after deletion. The
    capture retention path-format error is preserved with its corrected reader;
    no test verdict or validator was changed.

- [x] **FIX-06-SUCCESSOR-PREPARATION — Separate current v2 candidates:**
  [state/resource](../compat/candidates/tk-state-resource-2/candidate.json) and
  [capture](../compat/candidates/tk-capture-2/candidate.json) now validate against
  product source `db0697f7`, current runtime/tool identities and the exact Windows
  `5cb463cd` / Linux `b4c72484` wheels. Shared runtime and four fresh profile
  observations use exact source/native/archive/license joins; original producer
  and observation commits remain recorded. No producer is relabeled or rebuilt.
  Both candidates pass preparation on Windows and WSL and reject required review.
  Coverage/execution maps preserve 32 selected feature/profile pairs, 64 criteria
  and all 128 criterion/profile bindings. Complete dependency selections preserve
  every requested criterion and all 142 original required pairs/eight mandatory
  host rows. New execution rows have no transferred identity, receipt, review or
  admission flags. Four exact archive records pass per host; four native packets
  per host stop at the pending-review gate. Both qualification subjects remain
  unadmitted with zero proved and 128 missing obligations.
  [Exact review packet](../compat/candidates/tk-v2/review-packet.json),
  [preparation/validation evidence](../build/runs/successor-candidates-384/external-evidence.json).
  All 60 canonical v1 files are byte-identical. The original controller temp-dir
  failure and correction are retained; its failed attempt launched no test child.
  Scratch is removed and 65 retained entries rehashed. No build, install or new
  environment. Independent reviews, native admission, strict attempts, CI and
  promotion remain open. The optional peer wrapper/guide are absent; the later
  direct CLI attempt and its service limit are recorded below.

- [x] **FIX-06-EVIDENCE-STORE — Cross-store source/proof support:** optional
  hash-bound `secondary-v1` authority selects the retained D: store for produced
  native proofs, Linux original CI payloads and wheel/output bytes. Candidate,
  review, schema/policy, source, preparation and SDK origins retain source-root
  resolution. Native reuse reviews bind the store choice; the imported helper
  is a required candidate tool identity. Legacy records omit the selector and
  retain their previous behavior. Existing retained-file and scratch rules are
  unchanged; source/SDK origins and original producer locations do not move.
  All 25 new store/candidate-pin controls pass on Windows and WSL, including full
  synthetic archive and Linux-record joins with explicit candidate seams. The
  full Windows four-module run has 237 passes and three stale-v1-record failures;
  it is not an overall pass. The full WSL run hit its unchanged 150-second limit;
  only the targeted 25-case WSL completion is claimed. Initial scratch-root and
  synthetic RECORD-version fixture failures remain retained and cleaned.
  Real retained native proofs `325`/`374`, Linux CI capture `350`, and both current
  Windows/Linux wheel archive joins replay unchanged, without a build or install.
  [Conformance/replays](../build/runs/evidence-contracts-382/external-evidence.json),
  [full WSL timeout](../build/runs/evidence-contracts-381/external-evidence.json).
  This closes the source-level resolver blocker. Actual successor candidate,
  independent review, provenance/admission records, strict rows and CI remain open.

- [x] **FIX-06-WINDOWS-PACKAGE — Current Windows v2 packaging:** wheel
  `5cb463cd5e5c889af8b5c8d605bd6f60fe33d1bbeed521443d4f0966788017f9`
  is `vispy-0.17.0+vulkan.2-cp312-cp312-win_amd64.whl` (6,808,391 bytes).
  The existing backend assembled exact source `e99db28b` around the four verified
  native outputs from `windows-secondary-native-374`; no native rebuild, SDK or
  environment installation. The exact archive/source/native/license/RECORD join
  passes with the frozen source's explicit v2 expectation. The first caller's
  omitted version argument failed against the verifier's historical v1 default;
  that failed attempt is retained and cleaned. The successful audit reuses the
  same wheel bytes and leaves verifier defaults unchanged.
  [Original failure](../build/runs/windows-current-package-376/external-evidence.json),
  [exact archive audit](../build/runs/windows-current-installed-377/external-evidence.json).
- [x] **FIX-06-WINDOWS-INSTALLED — Exact current Windows v2 observations:** the
  same `5cb463cd` wheel passes 63 cases without skips: four upload/shutdown,
  56 state/capture and three maintained image-overlay/mesh/volume example cases.
  The unchanged eight-branch Tk and four-branch capture validators pass; all five
  active capture corruptions reject. Each child verifies 537 installed members;
  the examples verify 172 loaded VisPy Python origins under that one target.
  Measured shutdown gauges return to zero, including pinned host imports and
  repeated shutdown/external-snapshot readback. Scope is CPython 3.12.8, Tk/Tcl
  8.6 and RTX 4090 Windows Vulkan. The one offline no-deps copy-mode target uses
  existing dependencies. Strict cleanup removes 42,527,510 bytes across the
  failed assembly and installed run, rehashing 24/58 retained entries. A retention
  helper filename correction is preserved; no test or validator was changed.
  [Installed evidence and cleanup](../build/runs/windows-current-installed-377/external-evidence.json).
  These are local observations: formal cross-store provenance admission,
  successor reviews/records, mandatory rows, CI and release promotion remain open.

- [x] **FIX-06-LINUX-PACKAGE — Current Linux v2 platform packaging:** fresh
  auditwheel 6.8.2 analysis of wheel `4c826163` confirms
  `cp312-cp312-manylinux_2_39_x86_64`. The retagged wheel is
  `438ec1ce5b4b9f3e6565e2cb4ea83a4de55c9dc844b7af5f2d511d2d1fb613cd`.
  Only `WHEEL` and `RECORD` change; all other 560 distribution members, including
  every native binary, package source and license, are byte-identical. The exact
  current source/native/archive/license and RECORD joins pass. The four locked
  packaging tools' sources/licenses are retained once by hash. No native build,
  environment or physical-GPU qualification is involved.
  [Packaging evidence](../build/runs/linux-retag-357/external-evidence.json).
  Installed observations on `4c826163` remain bound to that raw wheel; exact
  installed verification of `438ec1ce` is recorded separately below. Final
  admission remains open. Packaging scratch cleanup reclaimed 23,224,370 bytes;
  all 27 retained entries rehashed after removal.
- [x] **FIX-06-LINUX-INSTALLED — Exact final-tagged Linux v2 observations:** wheel
  `438ec1ce5b4b9f3e6565e2cb4ea83a4de55c9dc844b7af5f2d511d2d1fb613cd`
  passes all 60 test cases (four upload/shutdown, 56 state/capture; no skips),
  the eight-branch Tk recovery validator and four-branch capture validator.
  All five active capture corruptions are independently rejected. Every child
  verifies all 537 installed package members; the held-upload/repeated-shutdown
  checks again prove 2 MiB pinned imports retire, ten gauges become zero and the
  external snapshot stays readable. State/capture children retire all nine of
  their measured gauges. This uses one offline no-deps installation, CPython
  3.12.13, Tcl/Tk 9.0 and pinned WSL llvmpipe/Mesa 26.1.8 with LLVM 18.1.3.
  [Exact installed evidence](../build/runs/linux-final-installed-358/external-evidence.json).
  Strict cleanup removed 29,856,782 scratch bytes; all 44 retained entries rehash
  successfully and the single installed target is absent.
  These observations do not discharge strict observer/absence gates, 120/8 finite
  criterion admission, the eight mandatory profiles or final release qualification.

## API breadth and inventory review

The [canonical inventory](../compat/vispy-compatibility.json) contains 142 seed
parents and still has `reviewed=false`. Its seed is not an exhaustive method/API
inventory. These are review tasks, not a demand to implement every upstream API.
Related sources: [inventory guide](compatibility-inventory.md), backlog B1/B2 in
the [consolidated plan](superpowers/plans/2026-10-28-consolidated-plan.md).

- [x] **API-01 — Application namespace:** review all 25 `app` parents, including
  backend selection, application, canvas, context, event and timer contracts.
  **Complete at parent/source-route review scope, 2026-11-07:**
  [the application review](application-coverage-review.md) accounts for 14 selector
  IDs and 11 exported entries against exact source `fa72c6da`, verifying the
  upstream pins and 15 fork source files. Nine explicit refusals remain distinct
  from the implemented, unqualified notebook route. All 22 boundary/event/curation
  checks pass on Windows and WSL with verified source origins. Independent review
  found no blocking accuracy or accounting issue. [Evidence/review references](../build/runs/app-audit-345/external-evidence.json).
  Inventory bytes, `reviewed=false`, all 142 original obligations and selections
  remain unchanged. API-05/06 retain method/value, alias, delivered-event, timer
  and exact-artifact acceptance work; no full parent or v2 admission transfers.
- [x] **API-02 — Rendering namespace:** review all 19 `gloo` parents, including
  public wrappers, resources, buffers, textures, programs and readback.
  **Complete at parent/source-route review scope, 2026-11-07:**
  [the gloo review](gloo-coverage-review.md) accounts for all 19 entries and retains
  dynamic wrapper/method/value work under API-05/06. Independent review's texture
  view and readback-ordering wording findings are corrected; the initial snapshot
  is preserved. The two public module descriptions now reflect Dawn compatibility
  limits, with identical executable ASTs, original BSD headers retained and explicit
  deviation entries. Both existing source-parity checks pass; native production
  inputs are unchanged. [Audit/correction/review references](../build/runs/gloo-audit-348/external-evidence.json).
  Inventory and selections remain unchanged. No full parent or v2 installed
  acceptance transfers. The corrected pure members are packaged and locally
  checked on Linux (FIX-06); broader API-05/06 acceptance remains open.
- [x] **API-03 — Scene namespace:** review all 22 `scene` parents, including
  aliases, cameras, viewboxes, transforms, clipping and shared lifetimes.
  **Complete at parent/source-route review scope, 2026-11-07:**
  [the scene review](scene-coverage-review.md) accounts for all 22 seed parents,
  37 generated visual aliases and the root camera/widget/transform wildcard
  exports against source `dcf730bf`. All 44 inspected source files match that
  commit and all three upstream source pins verify. Fifteen existing CPU cases
  pass without skips on each of Windows and WSL, with additional namespace,
  factory and ViewBox/Grid boundary probes; the GPU module is not imported, and
  no application, canvas or timer is created. The initial WSL pytest file-capture error is retained; retry
  uses the established sys-capture mode with unchanged test targets and probes.
  [Accounting/failure](../build/runs/scene-audit-360/external-evidence.json),
  [CPU retry](../build/runs/scene-cpu-361/external-evidence.json).
  Inventory, selections and shipping source remain unchanged. API-05/06 retain
  method/value/event, shader/clipping/picking and exact installed acceptance.
- [x] **API-04 — Visual namespace:** review all 76 `visuals` parents, including
  ordinary rendering, mutations, filters and application-specific visuals.
  **Complete at parent/source-route review scope, 2026-11-07:**
  [the visual review](visual-coverage-review.md) accounts for 39 visual classes,
  14 filters, nine shader helpers and 14 transform helpers across 56 definition
  files. All 143 recorded source files match `786079e8` and four upstream pins
  verify. Existing shader-composition, transform, graph-layout and Isocurve tests
  pass 51 cases without skips on each of Windows and WSL. Additional probes cover
  every parent origin, independent picking-ID bytes/dtype refusal, abstract base,
  negative clipping bounds and Alpha mutation; no GPU module, application, canvas
  or timer is used. The initial `Rect`-iteration harness error is retained; the
  retry uses its actual `pos`/`size` API with unchanged coordinate expectations.
  [Initial failure](../build/runs/visual-audit-363/external-evidence.json),
  [accounting/CPU evidence](../build/runs/visual-cpu-364/external-evidence.json).
  This does not qualify ordinary rendering, all mutations, filters, scientific
  consumers or shader compilation. Original inventory/selection bytes and all
  API-05/06, SHD, state, texture and scientific obligations remain unchanged.
- [ ] **API-05 — Method and route reconciliation:** map public methods, wildcard
  aliases, representative examples, events and raw interoperability not represented
  by the seed. A planning route is not an installed qualification.
  The scene review adds explicit factory/alias distinctions, direct-child
  untransformed ViewBox bounds and Grid removal's retained parent/cell references.
  [Method/alias discovery and example bindings](api-method-reconciliation.md) now
  retain 265 visible class/function aliases and 984 unreviewed source operation
  groups, with matching Windows/WSL catalog bytes. Inherited properties/methods,
  selected operators, source locations, three local examples and event declarations
  are recorded; generated signatures, values and general instance dataflow remain
  explicit limitations. The 142 original parents/selections are unchanged.
  All 58 selected CPU cases pass per platform, without a GPU module or GUI object.
  The initial WSL timeout/constructor-guard discovery defect is preserved; caching
  and original constructor references fix discovery within the same time limit.
  [Discovery/CPU evidence](../build/runs/api-reconciliation-367/external-evidence.json).
- [x] **API-05-EVENT-VALUES — Finite installed event-model semantics:**
  [method/value record](../compat/api-acceptance/event-values-v1.json) maps finite
  scopes for 38 catalog operation groups / 62 aliases, plus Event/Emitter/Group/Key
  helpers. Current Windows `5cb463cd` and Linux `b4c72484` each pass 57 CPU cases
  without skips: 30 new cases and 27 shipped emitter/key cases. Each child checks
  537 installed members and all loaded VisPy origins (180/179). No renderer or GUI
  backend loads; the installed CPU SDF helper is hash-checked. New cases prohibit
  GUI construction and cover payload/alias values, integer drag trails, flags and
  source-stack recovery, dynamic group names/blocking, scene coordinate-cache
  reset and scale refusal/recovery. Resize's required iterable size, borrowed
  mouse-button list and scene-copy/raw-native boundaries are explicit.
  [Windows](../build/runs/event-installed-windows-387/external-evidence.json),
  [WSL](../build/runs/event-installed-wsl-388/external-evidence.json).
  Strict cleanup reclaims 45,644,393 bytes and rehashes 15/20 retained entries.
  The 984-group discovery catalog and all 26 prepared v2 candidate records are
  unchanged. This finite CPU supplement supplies no parent, physical-delivery,
  rendering, strict-profile or release admission; API-05/06 and LIF-06 remain open.
- [x] **API-05-DOC — Correct reviewed public descriptions:** visuals now describe
  the supported gloo/GLIR/Dawn path, widgets describe their actual scene-layout
  exports, and ViewBox documents the existing BaseCamera default / explicit
  `panzoom` choice. Executable ASTs, original BSD headers and line endings are
  preserved; all three pure members are declared deviations. Source parity and
  identity contracts pass on each platform. Source is frozen at `c141eade` and
  packaged in the new Linux wheel below; no old wheel identity is relabeled.
  **Current Linux package and installed observations, 2026-11-07:** wheel
  `b4c724842cbb8bfadb2097a025acd30cbdce006bad2b27b3b62b149cda398b69`
  carries the five description changes since producer `fa72c6da`, including the
  three new corrections. Exact source/native/archive/license/RECORD joins and
  fresh manylinux_2_39 analysis pass. Existing locked packaging tools were reused;
  no dependency install, new environment or native build was needed.
  [Package evidence](../build/runs/linux-current-package-369/external-evidence.json).
  One offline installed target verifies all 537 package members in each test/capture child.
  All 63 tests pass without skips: four upload/shutdown, 56 state/capture and the
  three maintained image-overlay/mesh/volume example tests. The eight-branch Tk
  and four-branch capture validators pass; five active capture controls reject.
  The example process verifies 171 loaded VisPy Python-module origins under that target
  and retires all ten measured gauges, as do upload/shutdown checks; state/capture
  checks retire their nine gauges. Scope is CPython 3.12.13 / Tk 9.0 / pinned WSL
  Mesa software Vulkan. [Installed evidence](../build/runs/linux-current-installed-370/external-evidence.json).
  Strict cleanup removed 63,208,025 bytes across packaging and installation;
  all 30/51 retained entries respectively rehashed. Only the final new wheel is
  retained; its intermediate raw assembly and temporary tool target are removed.
  These are local functional observations; original v1 and earlier v2 records stay
  immutable. Windows production/installed checks later closed under FIX-06.
  Semantic/API acceptance, strict observer/profile gates, current CI, independent
  promotion and publication remain open.
- [ ] **API-06 — Selected API acceptance:** for each claimed finite subset, record
  supported values/formats, ordinary/mutation/failure/recovery behavior, clear
  refusals, documented differences and exact profile evidence. Keep original parent
  obligations intact; review does not itself qualify a parent or create an admission.
  **Partial current-artifact progress:** the three maintained examples have
  exact Linux observations in API-05-DOC and Windows observations under FIX-06.
  The finite CPU event supplement above adds value/dispatch evidence. This proves the named
  landmark, update/rejection and delivered drag/quarter-yaw cases. It does not
  establish every acceptance mode for every example, all methods, full DPI/input,
  large volumes or other profiles. Their source-discovery catalog remains unchanged.

## Shader and rendering edge coverage

These entries are **partial / audit** under B3–B6, not blanket claims that the
features are absent. Existing source tests and selected rendered cases must be
preserved. Required acceptance detail: SH-1–SH-5 in the
[gap-closure specification](superpowers/specs/2026-10-24-vispy-compatibility-gap-closure.md).

- [ ] **SHD-01 — Dynamic sampler arrays / SH-1:** supported sampler families, lengths,
  constant/runtime indices, uniform/divergent indexing, limits, rebinding and LOD.
  **Successor WIP:** direct explicit LOD/fetch selection over one-dimensional
  arrays now has source lowering and analytic regressions. Current v2 wheels
  remain literal-only. All 44 successor Windows native contracts pass. A Windows
  native-overlay experiment passes 12 dynamic cases, three rendered declaration/
  macro/nested-call controls and 32 existing regressions, with ten zero shutdown
  gauges. Twenty additional dimension/stage/int-uint cases, two granted-binding
  boundary/recovery cases and six single-level LOD/filter/argument-evaluation
  cases also pass against the same native bytes. Their three retained runs cover
  75 distinct cases (67 + 2 + 6), each with zero shutdown gauges and cleaned scratch.
  Linux verification, multidimensional selection and broader filter/preprocessor controls,
  implicit-derivative decisions and successor admission remain pending.
  [Implementation and remaining work](dynamic-sampler-indexing.md).
  **Actual Windows successor wheel:** `ba8a54c5` has exact source/native/license/
  RECORD joins and passes all 75 sampler plus 63 upload/state/example cases from
  one offline installation, with no native overlay. The Tk/capture validators
  and five active negative controls pass their expected outcomes. All tracked
  shutdown gauges are zero; 42,541,359 scratch bytes are removed and 67 retained
  entries rehashed. [Exact wheel evidence](../compat/api-acceptance/dynamic-explicit-samplers-wip.json).
  This is local functional acceptance, not independent/profile/release admission.

- [x] **SHD-01-LITERAL — Finite installed literal sampler-array scope:**
  32 cases pass without skips on each current Windows/WSL v2 wheel. Six sampler
  families and one/two/three-dimensional literal shapes render independent
  values after rebinding; selected queued revision/deletion and device-loss
  recovery cases pass. Eight new direct/helper diagnostics distinguish dynamic
  uniform/divergent indices, negative indices and out-of-range literals, then
  compile a valid shader after each refusal. All 537 installed members and
  loaded origins match; ten shutdown gauges are zero. Scratch targets removed.
  [Exact scope and evidence](../compat/api-acceptance/sampler-arrays-v1.json).
  Dynamic indexing, broader filtering/LOD, resource-limit and all-family loss
  coverage remain open under SHD-01; this does not admit a strict profile.
- [ ] **SHD-02 — Multidimensional arrays / SH-2:** supported storage/interface classes,
  indexing, partial updates, invalid shapes, reflection and cache identity.
- [ ] **SHD-03 — Matrix/array attributes / SH-3:** locations, column order, stride,
  offsets, divisors, constants, instancing, mutations and input-limit errors.
- [ ] **SHD-04 — Geometry consumers / SH-4:** bound supported compute/instanced
  expansion or document an application rewrite; preserve topology, interpolation,
  clipping, depth and mutation/loss behavior for that subset.
- [ ] **SHD-05 — Generated-line side effects / SH-5:** bound external storage,
  builtins, image/atomic/barrier and early/late-depth semantics. Preserve unsupported
  cases as explicit refusals until independently proved.
- [ ] **SHD-06 — Mesa clipping preparation:** integrate the reviewed clip-axis repair
  into the relevant prepared/installed CI profile before generalizing its evidence.
- [ ] **STA-01 — Legal raster state / B4:** reconcile dither, disabled multisampling,
  fractional polygon offset, mixed constant blending and stencil combinations.
- [x] **STA-02 — Reversed depth, finite installed proof:** all 30 existing
  analytic color/depth cases pass without skips on each current v2 wheel:
  Windows RTX Vulkan and pinned WSL software Vulkan. Ordering/clamping/equal
  ranges, masks, clipping, queued orientation, explicit/aliased fragment depth,
  indexed instancing and both forced device-loss paths are covered. Each process
  verifies 537 installed members and 56/55 loaded origins; ten shutdown gauges are
  zero. Both scratch targets are removed. [Exact evidence and boundaries](../compat/api-acceptance/reversed-depth-v1.json).
  Independent implementation review and strict observer/profile admission remain
  open; no arbitrary shader/format or performance claim follows.
- [ ] **TEX-01 — Typed sampling / B5:** review Uint/Sint, unfilterable float,
  comparison samplers, half precision and NaN behavior across claimed layouts.
- [ ] **LIN-01 — Line partitioning / B6:** prove chunk boundaries, topology,
  endpoint carry, resource limits and retained ordering on claimed routes.
- [ ] **LIN-02 — MSAA line coverage / B6 — Deferred:** the unshipped partial patch
  is not production support. Expand only if this deferred feature is selected.

## Scientific workflow reconciliation

The [scientific fixture table](superpowers/plans/scientific-fixture-coverage.md)
retains per-case evidence and historical epochs. A bounded pass there is not
automatically a pass on the latest wheel. The entries below track the remaining
broad claims and stale dispositions without duplicating that table.

- [ ] **SCI-01 — Indexed/instanced point inputs / U05:** source IDs, divisors,
  constants and ordered revisions; bind the claimed combinations to rendered proof.
- [ ] **SCI-02 — Mesh filters / E03:** enumerate filters and supported compositions,
  then verify mutations and meaningful outputs for the selected combinations.
- [ ] **SCI-03 — Scene/camera state / E04:** reconcile 3D cameras, planes,
  depth/stencil and polygon-offset interactions for selected scenes.
- [ ] **SCI-04 — Large volume scope / V09:** keep scientific-quality, performance,
  artifact and platform claims separate. The bounded historical large-volume
  packet does not establish all modes, devices or release performance.
- [ ] **SCI-05 — Remaining fixture dispositions / B15:** reconcile U05, E03, E04,
  Q11–Q13 and H03 with newer release/host evidence before calling each closed.
- [ ] **SCI-06 — Stencil wrapper / Q08, B10:** resolve the upstream admission gap
  independently from the native stencil capture cases that already pass.

## Resource lifecycle, capture and input

Exit conditions require the relevant finite lifecycle and failure/recovery
observations on each claimed profile, not just a successful screenshot.

- [ ] **LIF-01 — Native fault coverage / B7:** audit existing fault-injection,
  surface-acquisition-failure and physical-memory-accounting evidence; retain any
  unresolved cases rather than assuming the whole category is covered.
- [ ] **LIF-02 — Reparenting / Q02, B8:** actual layout reparenting, WinIdChange,
  native surface ownership and shared-resource lifetime.
- [ ] **LIF-03 — Zero/minimized windows / Q03, B8:** reconcile no-submit behavior
  and restoration; screenshot/overlay evidence alone does not close the full row.
- [ ] **LIF-04 — Close and loss / Q05, B8:** close with work in flight, actual
  surface loss, multicanvas recovery and owned-resource retirement.
- [ ] **LIF-05 — MSAA capture / Q11:** broader depth/stencil and format/feature
  matrix; single-sample and asymmetric color-resolve proofs remain separate.
- [ ] **LIF-06 — Input forwarding / Q13:** selected keyboard, wheel, touch, focus,
  mouse, timer and coordinate semantics beyond the currently proved workflows.
- [x] **LIF-06-TK — Finite installed Tk input acceptance:** 39 cases pass without
  skips on each exact v2 wheel: Windows Tk 8.6/RTX Vulkan and WSL Tk 9/software
  Vulkan. This comprises 22 explicit adapter vectors and 17 toolkit-generated
  cases, including three rendered camera landmark tests. Two new cases verify
  focus isolation/host Entry preservation and delivered key-release failure
  recovery. All 537 installed members and 175/174 loaded module origins match;
  ten shutdown gauges are zero on each platform. Scratch installations removed.
  [Exact scope and evidence](../compat/api-acceptance/tk-input-v1.json).
  Physical HID, touch/stylus, Qt gestures, other layouts and DPI remain outside
  this finite scope; parent LIF-06 and strict profile admission stay open.
- [ ] **LIF-07 — Tk extensions / B9:** camera, DPI and physical-input behavior
  beyond the admitted finite raster/manual-pump scope. The old Tk 8.6 WSL profile
  must not substitute for the admitted Tk 9 profile.
- [ ] **LIF-08 — Monitor changes and fractional DPI / Q04 — Out of release scope:**
  D7 documents these as untested. New cross-monitor/DPI claims require their own
  selected acceptance and installed evidence.
- [ ] **BUG-01 — Rare Windows startup stall / B22 — Open:** identify the closer,
  add a cause-specific regression and retain exact-profile recurrence evidence.
  It is documented rather than release-blocking under D33; a recurrence makes it
  release-blocking again. Use the external watcher; no generic retry/workaround.
- [ ] **BUG-02 — Historical PyQt5 OLE hang / B12 — Audit:** determine whether it
  shares B22's cause or needs a separate disposition.

## Host integrations

Host rows are optional under D32. Hot-swap uses stock hosts with only VisPy
replaced; strict profiles may use the recorded host patches. They are different
claims and must not borrow each other's gates.

- [x] **HOST-01 — Napari 0.10 migration:** successor fixtures, version-specific
  reference packets and the selected host rows moved to 0.10; retained 0.9.2 inputs
  remain historical. Authority: D30/D31 in the consolidated plan.
- [x] **HOST-02 — Release hot-swap follow-up:** selected napari/Glue/scientific
  workflows were rerun in R2 on the release artifacts. Scope and outcomes:
  [hot-swap ledger](../build/runs/r2-hot-swap-314/ledger.md).
- [ ] **HOST-03 — Optional strict host artifact renewal:** if claiming optional
  strict napari, Glue or napari-threedee rows for the current/next release wheel,
  requalify and bind that exact artifact. The six optional qualified host rows in
  the matrix retain Windows `62df5e4c...` / Linux `374a74ea...` identities; they
  are not the eight mandatory current-release rows.
- [ ] **HOST-04 — DIVE / B11 — Not admitted:** resolve its supported binding/API
  and upstream-baseline blockers before claiming actual application rendering and
  teardown. PySide2 is excluded from this fork's supported bindings.
- [ ] **HOST-05 — Visbrain and other applications / H07, B11:** imports and source
  inventories do not establish rendered workflows; select real acceptance cases.
- [ ] **HOST-06 — Glue upstream disposition / H03:** reconcile the older upstream
  volume-mutation gap with the newer five-workflow results; preserve each epoch.
- [x] **HOST-07 — Upstream posting disposition:** napari/qtpy PRs are not planned
  under D29. Prepared local changes and strict patches keep their recorded status;
  opening upstream PRs is not a coverage requirement.

## Platform and packaging boundaries

- [x] **PLAT-01 — Current wheels:** CPython 3.12, x86_64 Windows and Linux. Linux
  requires the documented manylinux/glibc/libstdc++/X11 environment and has WSL
  software Vulkan qualification only.
- [ ] **PLAT-02 — Other CPython release wheels:** earlier cp310–cp314 evidence
  does not qualify this release's other ABIs; build and qualify only if selected.
- [ ] **PLAT-03 — Native Linux GPUs — Unqualified:** select real hardware and
  complete installed graphics/lifecycle/gates on it before making this claim.
- [ ] **PLAT-04 — macOS Metal — Experimental:** build/CPU CI does not establish
  real Metal graphics, interaction or shutdown qualification; physical Mac needed.
- [ ] **PLAT-05 — Native Wayland — Unsupported:** current Linux scope is X11/xcb.
  No Wayland support claim without a selected implementation/qualification task.
- [ ] **PLAT-06 — ARM, free-threaded Python and ABI3 — Outside release scope:**
  current wheels/admissions do not establish these configurations.
- [x] **PLAT-07 — Tk presentation boundary documented:** manual pumping and CPU
  RGB PhotoImage presentation; no native Vulkan window/vsync/transparent-compositor
  promise for this mode. RGBA capture is a separate admitted contract.
- [ ] **PLAT-08 — Additional Vulkan GPUs and drivers — Unqualified:** other device
  vendors, models and driver versions need their own selected installed cells;
  current hardware evidence does not transfer automatically.

## Performance, tooling and evidence hygiene

Lab-grade input-to-visible scanout parity and exact OpenGL rasterizer parity stay
outside the agreed target. Documented visual differences keep their approved
criteria; software timestamps do not establish physical display scanout latency.

- [x] **PERF-01 — Measured performance report:** the report, selected presentation
  choice and documented differences satisfy the agreed performance requirement;
  the old universal 1.20x target is retired. See [performance report](performance-report.md).
- [ ] **PERF-02 — Remaining optional upload work / P5:** conversions such as RGB
  to RGBA into imported blocks are not covered by the direct-upload optimization.
- [ ] **PERF-03 — Remaining optional buffer work / P6:** batched draw routes still
  upload in the pass; do not generalize the streamed-buffer improvement to them.
- [ ] **PERF-04 — Cold builds and peak memory / B14:** obtain bounded measurements
  and reconcile the historical 16 review-finding regressions if making these claims.
- [ ] **TOOL-01 — Metal reuse / B23:** support the fresh lifecycle artifact layout
  and valid dispatch source ancestry. Fresh Metal dispatch satisfied the release
  jobs; the reuse-path failure is still a tooling gap.
- [ ] **TOOL-02 — Compiler-output caching / B13 — Optional:** select only a cache
  design that preserves input/toolchain identities and the shared disk budget.
- [ ] **TOOL-03 — Legacy cleanup receipt / B17:** audit/reconcile the missing
  historical compiler-cache cleanup receipt. Do not repeat the cleanup or claim
  reclaimed bytes without proof.
- [x] **TOOL-04 — Latest fix hygiene:** source-fix, artifact, transport and guest
  test/consumer scratch are removed. Latest receipts:
  [transport 329](../build/runs/shutdown-linux-retry-329/post-cleanup.json),
  [WSL consumer 330](../build/runs/shutdown-wsl-330/post-cleanup.json),
  [source tests 331](../build/runs/collector-protocol-331/post-cleanup.json).
  Meaningful failed attempts, original sources/notices, actual exits/waits and
  current proof/artifact identities remain retained; unknown waits are not passes.

## Next work order

Close one item at a time: record its source/artifact scope, run its acceptance
checks, retain the result and clean its scratch before moving on. A prerequisite
may be worked within the active item, but the checkbox stays open until every
exit condition is satisfied. Optional or deferred items are selected by need.

1. Settle FIX-06-VERSION before the final source/record freeze. The existing
   development artifacts and FIX-04-OBS observations stay valid at their exact
   hashes, but cannot silently acquire a different package identity.
2. FIX-04: use the now-verified FIX-05 Windows/Linux artifacts to renew their
   source/runtime/candidate/native/coverage/selection records and bound reviews.
   Rerun applicable source checks, then complete the normal merge. Preserve the
   original producer identities; no native rebuild is needed for record/doc-only
   changes. Do not mark FIX-04 complete while its evidence pins are failing.
3. FIX-06: renew the selected mandatory qualification rows, required CI/promotion
   and release metadata, then publish through the authorized process. Local
   artifact verification does not transfer the v1 admissions to these wheels.
4. BUG-01: keep recurrence evidence/cause work focused; follow D33 if it recurs.
5. API-01–API-06 and SCI-05: reconcile breadth and stale dispositions before
   expanding support claims or proposing broad implementation work.
6. Select optional rendering, lifecycle, host, platform or tooling work by need.
   Deferred scope does not become a release requirement merely by appearing here.

## Change log

| Date | Change | Evidence |
| --- | --- | --- |
| 2026-11-07 | Assembled the dynamic sampler Windows successor wheel from retained native outputs; 138 installed cases pass (75 sampler + 63 lifecycle/state/examples), with capture controls and zero gauges. No native build or new environment. | Wheel `ba8a54c5`; `windows-dynamic-package-410`, strict cleanup complete. |
| 2026-11-07 | Added 20 dimension/stage/index, two actual binding-limit refusal/recovery and six single-level LOD/filter/evaluation cases. All pass using the existing Windows native module; 75 distinct cases across three retained runs. | `dynamic-explicit-samplers-wip.json`; Linux CI continues on unchanged native source. |
| 2026-11-07 | Dynamic explicit sampler selection passes all 44 Windows native contracts and 47 native-overlay cases, including declaration/macro/nested-call controls. Added collision-safe names and a portable shader identity marker; ten shutdown gauges zero. | `dynamic-sampler-indexing.md`; SHD-01 stays open for Linux, breadth/limits, independent review and successor admission. |
| 2026-11-07 | Recorded finite installed event, Tk input, reversed-depth and literal sampler-array acceptance on both exact current v2 wheels. All scratch targets cleaned; broader parent claims remain separate. | `compat/api-acceptance/` packets and their exact source/wheel/evidence joins. |
| 2026-11-07 | Added source-bound successor version support to the archive core without changing v1 defaults or source package version. 53 cases and four real archive compatibility checks pass; remaining caller audit is explicit. | `package-version-333/verification.json`; FIX-06-VERSION remains open. |
| 2026-11-07 | Fixed successor RECORD handling in pure-source repackaging; source-bound main CI/Linux producer version checks. 47 repackager and 126 related cases pass. No new build, environment or scratch; remaining callers/version freeze are pending. | `package-callers-334/verification.json`; FIX-06-VERSION remains open. |
| 2026-11-07 | Selected v2 metadata consistently, audited remaining version literals and updated required oracle/installation checks. 128 source cases pass. Linux protocol controls: 85 pass, one stale record refusal; both historical real producers validate. Guest scratch cleaned. | `successor-version-335`, `version-protocol-336`; Git freeze/final qualification pending. |
| 2026-11-07 | Closed FIX-06-VERSION at source-freeze scope. Pushed `4ed660bf`, zero unexplained drift, preserved initial omitted-profile refusal and owner checkout/index. Private index cleaned. Fresh Linux producer dispatched at this exact commit as CI `42355088675`. | `successor-freeze-337`; final artifacts/qualification remain open. |
| 2026-11-07 | Preserved Linux driver-preparation failure and artifact identity; local transport refused below reserve. Cancelled the Windows compiler when remaining capacity no longer fit, awaited original exits, removed 56.8 MB scratch and rehashed 79 retained files. No new producer pass or release claim. | `successor-linux-338`, `successor-native-339`; alternative storage needs an origin/proof audit. |
| 2026-11-07 | Selected D: storage with inherited protection/block lists; recovered the Linux failure and both remote cleanup receipts. Fixed the inner Mesa live-sampling race; 17 tests pass on each platform, while strict terminal snapshots remain unchanged. Original failures and pytest alias cleanup retained; owned D: scratch cleaned. | `driver-guard-341/external-evidence.json`; fresh producer qualification remains open. |
| 2026-11-07 | Independent review's wiring gap closed; 19 cases pass per platform with an old-guard mutation control. Pushed the tool-only fix as `fa72c6da`, retained failures, cleaned all owned scratch and dispatched Linux retry `42357137754`. | `driver-freeze-343/external-evidence.json`; actual producer/release qualification remains open. |
| 2026-11-07 | Closed API-01 at 25-parent/source-route review scope after independent review. 22 CPU boundary/event/curation checks pass on Windows and WSL; no native application constructed. Inventory/selection unchanged, API-05/06 acceptance still open. Test scratch cleaned and 16 retained files rehashed. | `application-coverage-review.md`, `app-audit-345/external-evidence.json`; source review only. |
| 2026-11-07 | Closed API-02 at 19-parent/source-route scope after independent review and two wording corrections. Corrected public module descriptions; executable ASTs/native inputs unchanged, BSD headers/deviations verified, two source-parity checks pass. | `gloo-coverage-review.md`, `gloo-audit-348/external-evidence.json`; pure packaging and method/value acceptance remain open. |
| 2026-11-07 | Retained and verified the successful v2 Linux producer: 44 contracts, exact native/archive/source/license joins, both original cleanups. Raw wheel `1afcf55a`, `_dawn` `928e0439`; local transport cleaned, 184 files rehashed. | `linux-artifact-350/external-evidence.json`; current pure-member assembly, installed checks and admission remain open. |
| 2026-11-07 | Pushed reviewed gloo/module-description source `99aafd1c`, then assembled current Linux wheel `4c826163` by replacing only two pure description members in the verified v2 archive. Native bytes/metadata/notices unchanged; exact archive join passes. Both scratch roots empty after cleanup. | `gloo-freeze-352`, `linux-pure-353`; installed/admission/publication work remains open. |
| 2026-11-07 | Verified exact installed Linux v2 wheel `4c826163`: 537 members, four upload/shutdown cases, 56 state/resource cases without skips, eight Tk recovery branches and four capture branches. All five active capture controls reject; measured shutdown gauges are zero. Reused existing interpreter/dependencies/driver with no native build or new environment. | `linux-installed-354`, `linux-observations-355`, `linux-capture-356`; local software Vulkan observations, no admission transfer. |
| 2026-11-07 | Closed FIX-06-LINUX-PACKAGE: fresh locked auditwheel analysis confirms manylinux_2_39; wheel `438ec1ce` changes only WHEEL/RECORD, with 560 other members unchanged and exact current archive/source/native/license joins passing. Original helper-import failure and transient PID-check refusal are preserved; the unchanged strict planner subsequently passes. | `linux-retag-357`; exact installed checks and admission remain separate. |
| 2026-11-07 | Closed FIX-06-LINUX-INSTALLED: exact final-tagged wheel `438ec1ce` passes 60 no-skip test cases, eight Tk branches, four capture branches and all five active rejection controls on a single offline installed target. Every child verifies 537 members; measured gauges retire to zero. | `linux-final-installed-358`; local software Vulkan verification only, strict rows/admission/publication remain open. |
| 2026-11-07 | Closed API-03 at 22-parent/source-route scope: verified 44 source files/three upstream pins, recorded 37 generated visual aliases, and passed 15 existing CPU tests per platform plus namespace/factory/ViewBox/Grid probes. Preserved the WSL pytest file-capture failure; unchanged cases pass with sys capture. | `scene-coverage-review.md`, `scene-audit-360`, `scene-cpu-361`; no shipping change or method/artifact admission. |
| 2026-11-07 | Closed API-04 at 76-parent/source-route scope: 39 visuals, 14 filters, nine shader helpers, 14 transform helpers; 143 exact source files and four upstream pins verified. All 51 selected CPU cases pass per platform, plus parent/type/packing/clipping/Alpha probes. Original Rect-iteration harness failure retained. | `visual-coverage-review.md`, `visual-audit-363`, `visual-cpu-364`; actual shader/rendered/method acceptance remains open. |
| 2026-11-07 | Closed API-05-DOC with three docstring-only corrections and explicit deviations; executable ASTs/headers/line endings unchanged. Discovered 265 aliases / 984 unreviewed operation groups, event declarations and three source example/test bindings. Windows/WSL catalogs match and 58 CPU cases pass per platform. Initial timeout/guard-discovery failure retained. | `api-method-reconciliation.md`, `api-reconciliation-366/367`; API-05 semantic reconciliation, packaging and acceptance remain open. |
| 2026-11-07 | Packaged current source `c141eade` as Linux wheel `b4c72484` around the unchanged verified native leaf; exact archive/source/native/license joins and manylinux_2_39 analysis pass. Reused the locked tool archive without installation. All 63 installed cases, eight Tk branches, four capture branches and five active rejection controls pass, including the three maintained examples. | `linux-current-package-369`, `linux-current-installed-370`; local software Vulkan observations, no strict/admission/publication transfer. |
| 2026-11-07 | Closed FIX-04-OBS: fresh 56-assertion/eight-branch and capture/control observations on both successor wheels. Retained evidence and cleaned scratch. Identified v1-only package metadata coupling; settle successor version before final record freeze. | `shutdown-observations-332/verification.json`, `post-cleanup.json`; FIX-04/FIX-06 remain open. |
| 2026-11-06 | Initial live checklist; release baseline separated from source fixes, historical host qualifications and optional gaps. | Release notes, strict matrix, consolidated backlog and shutdown-fix-322 records linked above. |
| 2026-11-06 | Started FIX-04; recorded the native-input pin refusal and its FIX-05 prerequisite. | `source-fix-integration-323`; no release or qualification transferred. |
| 2026-11-06 | Source review passed; retained and cleaned failed offline CI setup. Started a bounded locked-package retry on the same candidate. | `source-fix-integration-323`, `source-fix-ci-324`; FIX-04 remains open. |
| 2026-11-06 | All 44 CPU contracts and the shutdown regression passed. Source CI remains 16/23 commands passing after isolated fixture retries; seven commands reject old runtime pins. | `source-fix-ci-324/acceptance-report.json`; FIX-04 remains open pending matching artifacts/records and merge. |
| 2026-11-06 | Removed both isolated checkouts and all run 323/324 scratch; preserved failures and rehashed retained evidence. | `source-fix-integration-323/post-cleanup.json`, `source-fix-ci-324/post-cleanup.json`; original publication checkout unchanged. |
| 2026-11-06 | Closed FIX-05-WIN: fresh SDK-linked Windows leaf, 44 native contracts, exact package/license join, 537 installed member identities and four distinct installed cases. Added explicit Linux substep; parent FIX-05 and FIX-04 remain open. | `shutdown-native-325`, `shutdown-package-326`; unreleased wheel `43af80d3`, both runs cleaned with 137/34 retained files rehashed. |
| 2026-11-06 | Started FIX-05-LINUX: healthy WSL/backing volume, unchanged driver/dependency reuse, source-only branch push and explicit fresh CI producer. | `shutdown-linux-327`, CI `42334823925`; no artifact or qualification pass yet. |
| 2026-11-06 | Preserved the failed first Linux CI producer; fixed its live scratch-sampling cleanup race with a deterministic baseline and 39 passing WSL lifecycle cases. Both local transport and guest test scratch cleaned. | `shutdown-linux-327/failure-analysis.json`, `ci-space-race-328/verification.json`; Linux renderer verification remains open. |
| 2026-11-06 | Closed FIX-05-LINUX and parent FIX-05 at local verification scope: fresh CI producer, 44 native contracts, exact source/native/package/license joins and four passing installed WSL cases. Preserved old collector/producer validity and stale-record failures. All owned scratch cleaned. | CI `42335940224`, `shutdown-linux-retry-329`, `shutdown-wsl-330`, `collector-protocol-331`; unreleased Linux wheel `b71ed6a3`. FIX-04/FIX-06 remain open. |
