# Consolidated plan

Date: 2026-10-28. This is the single active plan. It merges every still-open
item from the earlier plans, notes and specs into one list, with one owner ID
per item. The earlier documents stay as historical records and are not
rewritten. The one exception is the coverage registry, whose stale rows are
refreshed under B16. Several of the earlier documents are hash-pinned or kept
byte-exact by policy. Their status is in the [plan index](#plan-index).
Requirement IDs (HOST-1, PERF-1, SH-1, ...) remain defined by the pinned
[gap-closure spec](../specs/2026-10-24-vispy-compatibility-gap-closure.md).

## Goal and scope

The product is a same-name `vispy` 0.17.0 fork, version `0.17.0+vulkan.N`.
It has a Dawn renderer behind gloo/GLIR and creates no OpenGL context. The goal is that
unmodified scientific hosts, napari first, run on it with practical parity.

- **Parity is practical** (user decision, 2026-10-23). Documented and tested
  differences are allowed. Exact rasterizer parity and lab-grade latency are
  out of scope.
- **Platforms.** Windows Vulkan and WSL software Vulkan are qualified. Metal is
  experimental. Native Linux GPU is not qualified, because no hardware is
  available. Linux is X11/xcb only; native Wayland is refused.
- **Python and bindings.** Standard CPython 3.10-3.14; napari needs 3.11 or later.
  No ABI3, free-threaded or ARM builds. The bindings are PyQt5, PyQt6, PySide6 and
  Tk. PySide2 is refused.
- **Two profiles.**
  - **Strict no-OpenGL** uses patched napari/qtpy/Glue and Qt without its OpenGL
    modules. On Linux, Qt is built with OpenGL and EGL disabled; on Windows,
    selected stock modules are used and the GL modules excluded. It must pass
    three gates on one installed artifact.
  - **Hot swap** uses stock PyPI hosts with only `vispy` replaced. Its claim:
    - vispy and its native module never import, load or resolve GL;
    - no GL context is created or made current, and no GL draw runs, anywhere
      in the process;
    - GL loads by host packages are recorded with attribution, not claimed
      absent (hot-swap plan :33; design :615-621).

    A hot-swap pass never qualifies a strict row, and only the strict profile
    may be called "no-OpenGL".

## Where things stand

| Area | State | Source |
| --- | --- | --- |
| Practical milestone | Closed: 120 selected criteria, 23 CI jobs, promotion review (PR #14/#15) | `docs/practical-compatibility-release.md` |
| Current admitted wheels | `444402...` (Windows cp312), `bd89a994...` (Linux, `linux_x86_64`, not manylinux) | same, :105-106 |
| Earlier wheels | Windows cp310-cp314 and WSL cp312 at an earlier source epoch | `docs/tested-platforms.md` |
| Published wheels | None uploaded anywhere | `docs/tested-platforms.md` |
| Strict matrix | 13 of 14 mandatory rows qualified (6 Windows, 7 WSL), bound to `62df5e4c...` and `374a74ea...`. **Windows napari-threedee: PENDING.** DIVE and visbrain are non-mandatory and not admitted. | `compat/no-opengl-matrix.json` |
| Hot swap | Stock napari works with the current wheel on Windows cp312. Drag-race fix merged (PR #24). Smooth-line criterion merged (PR #25). | `2026-10-28-napari-hot-swap.md` |
| Startup stall | Mechanism found for the 2026-10-28 dev-environment recurrence: the default thread pool was lost early in startup. The qualification stall's pool state was never captured. The closer is unidentified (PR #26). | `docs/threedee-startup-diagnosis.md` |

## Decisions

### Decided (user, 2026-10-28)

| ID | Decision | Background |
| --- | --- | --- |
| D1 | **The first release ships a fresh build of the then-current source, and every mandatory row is requalified on it.** | The 13 qualified rows bind `62df5e4c`/`374a74ea` (536 members), which predate the Tk follow-up (status :12-18). The admitted wheels are `444402`/`bd89a994` (537 members). Rows are bound to their artifact (removal plan :321-322). |
| D2 | **No preview publication.** Nothing is published before the release gates pass. | The gaps plan forbids publishing the draft release, hiding failed mandatory rows, or claiming full parity while gates are unmet (:980-981). The removal plan makes publishing subject to the release gates (:128). |
| D3 | **The performance gate is a measured report (PERF-1), with no speedup claim. The presentation path is chosen from the measurements.** The design's 1.20x targets are retired. | The design required, on each primary resident workload, a median speedup of at least 1.20x, no worse p95, and at most 10% update regression (design :446). The 66-workload set comes from the completion and continuation plans (:126, :188). The design also forbade interaction that depends on a CPU readback (:631). |
| D4 | **Markers M02 and M06 close with a documented difference.** The criterion is fixed, tested and approved by the user before re-capture, as for smooth lines. | M02 (exact plus tie-pixel) and M06 (sealed maximum error of 2) had already failed, and tolerances are never widened after a failure without a user decision. |

### Open

Each of these is blocked on the user, and work that depends on one waits for it.

| ID | Question | Why it is open |
| --- | --- | --- |
| D5 | Should the smooth-line criterion extend to Glue `scatter_axes`, mesh axes/colorbar and the napari-threedee fixture suites? | Those suites compare exactly and draw smooth lines. W10 and W13 will probably fail without it. |
| D6 | May the broken oracle fixtures be re-captured (W10)? | Original references are never replaced, and the fixture sources are pinned by `fixture_source_sha256` in their manifests. The compatible route is a new fixture module and reference packet beside the retained one, with an admission that records the oracle defect. |
| D7 | Monitor moves and fractional DPI: schedule a physical-desktop session, or keep them out of scope? | Only these two need a desktop session (completion :239). The other lifecycle items in B8 can run now. |

The user has already decided that the Windows napari-threedee row stays required.
W11 publication and W12 upstream posting each need explicit approval.

## Work items

### Release-critical

| ID | Work | Exit | Needs |
| --- | --- | --- | --- |
| R1 (W9) | Windows napari-threedee strict row | A cause and a regression test, then full lifecycle, nine-zero shutdown and all three gates on the release artifact (spec :340-345; status :86-87). A passing replay never closes it (diagnosis :49-50). | Identify the closer. Instrument hot-swap and diagnostic launches and wait for a recurrence. |
| R2 | Release assembly: a fresh build of the then-current source (D1) | Every mandatory row requalified on it, final-head CI, promotion review | R1 |

Additional R1 evidence: the 2026-10-23 stall in a napari-hosted volume case
(`iso_categorical_fast`, run native65) had a consistent signature. Its main
thread waited in `RegisterDragDrop` while two native threads used CPU in
Windows worker-factory waits, with a wait chain to RpcSs. Its symbols were
approximate and its pool handle state was not captured (next-batch plan
:7196-7200). This suggests the stall family is not specific to napari-threedee.
Diagnostic runs in the exact qualification profile keep the spec budget
(:325-333). Qualification runs never carry handle tracing.

### Hot swap

| ID | Work | Exit | Needs or notes |
| --- | --- | --- | --- |
| W1 | `GL_EXTENSIONS` reports `texture_float` only when float32 is filterable | CPU tests for both device answers; a napari float image renders with the fallback forced | Native rebuild. Overlaps typed-sampling item B5. Reuse fixture I07. |
| W2a | W2 residuals: run the 6 `np.row_stack` cases with NumPy 2.4.6, the pairing those suites require, and make the `initialized` suite honour `VISPY_PLUGIN_CANDIDATE_PYTHON` (1 case) | These 7 cases run on the hot-swap stack | Hot-swap plan, W2 table |
| W3 | Hot-swap audit gates | Controls reached; the stock baseline passes | New modules only, because the audit tools are pinned. Attribution must decide how a driver's GL load inside a native swapchain path counts, if W8 picks one. |
| W4 | napari families not yet covered: cyclic labels r8/r16, Shapes/Vectors/Tracks (M10, M11), Surface at napari level (a new fixture), overlays (E06, T04), histogram, sized export (Q03, Q06) | Each matches its OpenGL reference, or has a documented difference fixed before capture | Record results in `compat/vispy-compatibility.json`. |
| W5 | Known defects: M02 and M06 markers, M08 wide lines (16 references; the depth failure is retained), M09 joins, caps and new line fixtures, B03 opacity mutation, H01 screenshot and layer removal with no hidden finish, V04 volume controls | Fixed and admitted. M02 and M06 close with a user-approved documented difference, fixed before re-capture (D4). | V07 and the plane widget belong to W10. V09 timing belongs to W8. |
| W6 | Hot-swap rows for PySide6 and CPython 3.11-3.14 | One row per cell passes W2 and W3 | Wheels for 3.10-3.14 exist only at an earlier epoch, so they must be rebuilt at the current source. Admissions use the 23-job CI and a promotion review. |
| W7 | WSL lavapipe hot-swap rows | WSL rows pass | Measure the smooth-line bound on lavapipe; 32 was measured on NVIDIA only. |
| W8 (PERF-1) | Performance report: interaction frame time, large image and volume loads (including V09 timing), presentation path | A measured report against upstream OpenGL, with no speedup claim; the presentation choice is taken from the data (D3) | Native swapchain presentation is allowed only in hot swap. Inputs: the five-pair timings. PR #2 was closed, but its Qt single-present code is live (`src/vispy/app/backends/_qt.py:790-931`). Explain the unattributed Qt expose paints that invalidated the Native65 five-pair timing run (next-batch plan :443, :485, :3502). |
| W10 | Oracle fixtures: the threedee drag race; the render-plane fixtures, including V07 and the plane widget; the plugin plan's opaque-volume residual. In W2, 11 cases were blocked by unadmitted references in the threedee, initialized and render-plane suites. | Parity tests pass against new admitted oracle captures | D6. These suites compare exactly and draw manipulator lines, so the exit will probably fail unless D5 extends the smooth-line criterion to them. |
| W11 | Publication: GitHub Release plus a PEP 503 index with hashes, a manylinux build, and the 100 MiB wheel budget | A clean venv installs from the channel and the W2 smoke test passes | Only at the release, after R2 and approval; no preview (D2). Record a new artifact, and never replace the draft release's assets (gaps plan :581-582). Prepared locally (`tools/wheel_index.py`). |
| W12 | Upstream napari lazy `GLError` and qtpy lazy QtOpenGL | Upstream releases contain them | Approval. Drafts are in `docs/upstream-drafts/`. They remove the napari and qtpy patches, but stock Qt still fails the strict gates, so strict rows keep the Qt build without OpenGL. |
| W13 | Glue in hot swap: the five workflows (scatter, scatter edit, scatter axes, volume, volume edit) | All five pass with stock hosts | W3, and D5 for `scatter_axes` (coverage H02). The design requires Glue (:26, :122), and no workstream covered it. |

W0 (drag race) and W2 (baseline) are done.

### Backlog (not release-blocking)

| ID | Work | Source |
| --- | --- | --- |
| B1 | 142 inventory parents (`reviewed=false`) | spec :1094-1100 |
| B2 | API breadth route map | gaps plan :305-309 |
| B3 | SH-1 to SH-5 shader items; take the Mesa clip-axis repair into preparation and installed CI | spec :293-299; gaps plan :397-444 |
| B4 | Legal state values: dither, multisampling disabled, fractional polygon offset, mixed constant blend, stencil combinations. Reversed depth is tested at source level only. | spec :857-864 |
| B5 | Typed sampling and layout partitioning (Uint, Sint, unfilterable, comparison, half, NaN) | completion plan :58-64, :84-90; continuation plan :156 |
| B6 | MSAA line coverage, deferred by the user; the partial MSAA patch stays outside production and is not shipped. Line partitioning, which is open. Agg joins and caps belong to W5 (M09). | `docs/tested-platforms.md` :63-65; next-batch plan :46-53; continuation plan :148-150 |
| B7 | Native faults: fault injection, surface-acquisition failure, physical-memory accounting. Disposition unknown. | continuation plan :127-129, :176; completion plan :102 |
| B8 | Qt lifecycle. Schedulable now: reparenting and WinIdChange, zero-size no-submit, close in flight. Needing a desktop session (D7): monitor moves and fractional DPI. Coverage rows Q02, Q04, Q05. | continuation plan :176; completion plan :239; design :378-387 |
| B9 | Tk: the old Tk 8.6 WSL profile is blocked; camera, DPI and physical input | gaps plan :148-157, :538 |
| B10 | Admit the unchanged upstream stencil wrapper (8 stock upstream failures; coverage Q08) | coverage list :130 |
| B11 | DIVE and visbrain (non-mandatory; coverage H04, H05, H07). DIVE passed only through PySide2, which the wheel now excludes, and its PyQt5 path fails upstream. visbrain has never run. | host-admission :165-167; native-sdk-reuse :231-243; `compat/runtime-package.json` :523; cp311 notes :84-88 |
| B12 | Historical PyQt5 OLE lifecycle hang. May share R1's cause. | `docs/opengl-removal-status.md` :125-128 |
| B13 | CI compiler-output caching | gaps plan :194-205 |
| B14 | Unverified: cold-build time and peak memory; the 16 review-finding regressions | design :677; completion plan :245 |
| B15 | Coverage rows that are not napari-specific: U05, E03, E04, Q11 (missing), Q12 (partly done), Q13; upstream gap H03 | coverage list |
| B16 | Refresh stale records: coverage rows that still cite smooth-line refusals (E06, T04, H02, V07, M08); close H06 (now 5/5); refresh `docs/opengl-removal-status.md` (stale since 10-24) | digests of 2026-10-28 |
| B17 | The local legacy 12,134-file compiler-cache set has no cleanup receipt. Do not repeat that cleanup blindly, and do not count its savings. | removal plan :120-122 |

### Blocked on external hardware

- **Native Linux GPU rows** (HW-1): needs a Linux GPU machine.
- **Metal graphics:** needs a Mac. Mac CPU and build checks already pass. PySide6
  needs macOS 14, and there are no Intel-Mac numba wheels (platform-qualification
  :90-96).

## Order

1. Decisions D5-D7, while R1's instrumentation runs alongside.
2. W2a and W3, then W10 (after D6), then W4 and W5 (after D5), then W13.
3. W6 and W7, then W1 (native rebuild).
4. W8.
5. R2 (fresh release build), then W11 at the release and W12 on approval.
6. Backlog as capacity allows.

## Standing rules

- **Identity.** Distribution `vispy`, version `0.17.0+vulkan.N`, through direct
  wheels or a dedicated index, hash-locked by consumers. No Provides-Dist, no
  sys.path overlays, and no PyPI release without upstream.
- **Evidence.**
  - Tolerances are fixed before capture and never widened after a failure,
    except by an explicit user decision.
  - A missing host or missing hardware is never a passing skip.
  - Failures are never relabeled.
  - Original references are never replaced.
  - No skip, xfail, masks or fitted tolerances.
  - The smooth-line criterion applies only to the two napari-threedee overlay
    suites, by user decision; extending it needs D5.
- **Qualification.**
  - Three gates per row, on the same installed artifact.
  - Full lifecycle, and nine-zero shutdown on the resource gauges.
  - Auditor-only results count as UNVERIFIED.
  - No fake OpenGL modules and no shipped monkeypatches.
  - Results never transfer across artifacts.
  - Rows are requalified after affected changes.
  - GUI profiles run serially.
  - Software Vulkan needs an explicit allowance and does not count as GPU
    coverage.
- **Threedee stall.**
  - No generic retry or COM workaround.
  - Never disable drag-drop, plugins, hooks or observers.
  - Keep the exact-profile diagnostic budget.
- **Pinned files.** Put new behaviour in new modules. Pinned are:
  - the spec and `compat/no-opengl-matrix.json`;
  - `tools/no_opengl/*` and `tools/audit_no_opengl.py`;
  - the fixture sources and reference manifests;
  - `tests/hosts/test_napari_plugin_wheel_parity.py`;
  - `.github/workflows/cpu-contract.yml`.

  R2 must edit the matrix. That renews the candidate, execution-ledger and
  `compat/vispy-compatibility.json` pins, along with their reviews
  (spec :1441-1443).
- **Process.**
  - A failing test or control comes first.
  - Windows and WSL evidence.
  - Independent review.
  - PRs merge only through the 11 required checks.
  - Admissions also need the 23-job CI and a promotion review.
- **Hygiene.**
  - Follow AGENTS.md: 20 GiB scratch and a 10 GiB reserve.
  - Use `UV_LINK_MODE=copy`.
  - Provision temporary interpreters with `--no-registry`.
  - Never repeat a benchmark run identically.
  - Never retry a rejected cleanup target. The authoritative list is
    `blocked_roots` in `build/.hygiene/registry.json`. It includes the Native70
    wheel caches, the Native67 marker cache,
    `build/native66-windows-graphics-telemetry-root-1/allocation_probe2.obj` and
    `build/mesh-layout-portable-prep-root-1/pytest-temp-{1,2}`.
- **Licensing and exclusions.**
  - The fork's implementation and modifications are AGPL-3.0-only.
  - The original VisPy BSD licence (`LICENSE-BSD`) and the third-party licences
    stay attached byte-exact.
  - Cybersecurity work is excluded.

## Plan index

| Document | Status |
| --- | --- |
| `specs/2026-10-08-vispy-vulkan-design.md` | Historical baseline. Its renderer, source and licensing contracts still hold. |
| `specs/2026-10-24-vispy-compatibility-gap-closure.md` | Normative requirement IDs; pinned; still governs. |
| `plans/2026-10-09-vispy-vulkan-completion-plan.md` | Superseded by the continuation plan. |
| `plans/2026-10-10-vispy-vulkan-continuation-plan.md` | Superseded by the next-batch plan and the gap-closure work. |
| `plans/2026-10-10-vispy-vulkan-next-batch-plan.md` | Historical log to 2026-10-23; do not edit. Its published copy keeps its earlier body byte-exact, and must never be overwritten by the 1.17 MB local agent-history file. Open items carried here. |
| `plans/implementation-evidence.md` | Historical, to 2026-10-11. |
| 2026-10-09 notes: cp313-314, msvc-runtime, napari-threedee packaging, native-sdk-reuse, qt-binding | Completed. |
| 2026-10-09 notes: cp310-dive-pyside2, wide-line, wheel-qualification, native-epoch | Superseded or historical. |
| 2026-10-09 notes: cp311 (DIVE blocker), host-admission (DIVE and visbrain), platform-qualification | Remaining items carried as B11, HW-1 and the Metal notes. |
| `plans/2026-10-21-{glue-cache,image,mesh-layout,volume}-*-plan.md` | Completed. Glue and mesh-layout are bounded (see D5 and W13). |
| `plans/2026-10-21-napari-plugin-wheel-plan.md` | Completed. Its exact criterion is superseded by the smooth-line decision; its opaque-volume residual is W10. |
| `plans/2026-10-21-smooth-line-mechanism-plan.md` | Superseded by `docs/smooth-lines.md`. |
| `plans/scientific-fixture-coverage.md` | Active registry of coverage IDs, owned by the W, B and HW items here; stale rows refreshed under B16. |
| `plans/2026-10-23-opengl-runtime-removal-plan.md` | Mostly complete; its remaining scope is R1/R2. |
| `plans/2026-10-24-vispy-compatibility-gaps.md` | Log to 2026-10-28; superseded as a plan by this document. |
| `plans/2026-10-28-napari-hot-swap.md` | Origin of W0-W12 and their progress record; work continues here. |
| `docs/opengl-removal-status.md` | Stale since 2026-10-24 (B16). |
