# VisPy Vulkan coverage checklist

Last reviewed: **2026-11-06**. This is the live coverage worklist for implementation,
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
- [ ] **FIX-05 — Patch artifact verification:** build successor artifacts containing
  the fix, verify native/package/license joins, and exercise actual renderer teardown
  with live uploads and imports on Windows and WSL. CPU wrapper evidence alone does
  not prove a new installed renderer artifact.
- [ ] **FIX-06 — Patch qualification and publication:** renew affected records and
  mandatory rows on those artifacts, satisfy required CI/promotion, and publish only
  through the authorized release process. Existing v1 wheels do not contain FIX-01.

## API breadth and inventory review

The [canonical inventory](../compat/vispy-compatibility.json) contains 142 seed
parents and still has `reviewed=false`. Its seed is not an exhaustive method/API
inventory. These are review tasks, not a demand to implement every upstream API.
Related sources: [inventory guide](compatibility-inventory.md), backlog B1/B2 in
the [consolidated plan](superpowers/plans/2026-10-28-consolidated-plan.md).

- [ ] **API-01 — Application namespace:** review all 25 `app` parents, including
  backend selection, application, canvas, context, event and timer contracts.
- [ ] **API-02 — Rendering namespace:** review all 19 `gloo` parents, including
  public wrappers, resources, buffers, textures, programs and readback.
- [ ] **API-03 — Scene namespace:** review all 22 `scene` parents, including
  aliases, cameras, viewboxes, transforms, clipping and shared lifetimes.
- [ ] **API-04 — Visual namespace:** review all 76 `visuals` parents, including
  ordinary rendering, mutations, filters and application-specific visuals.
- [ ] **API-05 — Method and route reconciliation:** map public methods, wildcard
  aliases, representative examples, events and raw interoperability not represented
  by the seed. A planning route is not an installed qualification.
- [ ] **API-06 — Selected API acceptance:** for each claimed finite subset, record
  supported values/formats, ordinary/mutation/failure/recovery behavior, clear
  refusals, documented differences and exact profile evidence. Keep original parent
  obligations intact; review does not itself qualify a parent or create an admission.

## Shader and rendering edge coverage

These entries are **partial / audit** under B3–B6, not blanket claims that the
features are absent. Existing source tests and selected rendered cases must be
preserved. Required acceptance detail: SH-1–SH-5 in the
[gap-closure specification](superpowers/specs/2026-10-24-vispy-compatibility-gap-closure.md).

- [ ] **SHD-01 — Dynamic sampler arrays / SH-1:** supported sampler families, lengths,
  constant/runtime indices, uniform/divergent indexing, limits, rebinding and LOD.
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
- [ ] **STA-02 — Reversed depth:** move the claimed cases beyond source-only coverage
  if installed support is to be claimed.
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
- [x] **TOOL-04 — Latest fix hygiene:** shutdown-fix scratch removed and 18 retained
  files rehashed. Evidence: [post-cleanup receipt](../build/runs/shutdown-fix-322/post-cleanup.json).

## Next work order

1. FIX-04–FIX-06: review the source candidate, produce the matching FIX-05 native
   artifact/record prerequisites, then complete the FIX-04 checks/merge and FIX-06
   qualification/publication. This is one active fix workstream; do not mark
   FIX-04 complete while its native-input validation is failing.
2. BUG-01: keep recurrence evidence/cause work focused; follow D33 if it recurs.
3. API-01–API-06 and SCI-05: reconcile breadth and stale dispositions before
   expanding support claims or proposing broad implementation work.
4. Select optional rendering, lifecycle, host, platform or tooling work by need.
   Deferred scope does not become a release requirement merely by appearing here.

## Change log

| Date | Change | Evidence |
| --- | --- | --- |
| 2026-11-06 | Initial live checklist; release baseline separated from source fixes, historical host qualifications and optional gaps. | Release notes, strict matrix, consolidated backlog and shutdown-fix-322 records linked above. |
| 2026-11-06 | Started FIX-04; recorded the native-input pin refusal and its FIX-05 prerequisite. | `source-fix-integration-323`; no release or qualification transferred. |
