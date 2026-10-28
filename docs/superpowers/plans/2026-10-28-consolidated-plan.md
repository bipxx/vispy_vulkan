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
| D5 | **The smooth-line criterion also applies to Glue `scatter_axes`, the mesh axes/colorbar scene and the napari-threedee fixture suites.** Everything else stays exact. | These suites draw smooth lines and compared exactly. |
| D6 | **Broken oracle fixtures get new fixture modules and reference packets beside the retained ones, with an admission that records the oracle defect.** Original references are never replaced. | The fixture sources are pinned by `fixture_source_sha256` in their manifests. |
| D7 | **Monitor moves and fractional DPI stay out of scope and are documented as untested.** The other Qt lifecycle items run now. | Only these two need a physical-desktop session (completion :239). |
| D8 | **The four render-plane-scheduled cases close through W5's wide-line fix, with no new tolerance.** This revises the user's earlier approval of a looser rule, which rested on a wrong diagnosis. | 52-61 pixels per case exceeded the 32-level bound. A one-pixel boundary-move rule was fixed and tested before the re-run. It explained 33-46 of them and left 15-25, so all four cases still failed (run `w10-render-plane-rule-221`). Inspection then showed the pixels are not on the render plane's boundary, as first described. They are on napari-threedee's manipulator strokes, which are vispy `Line(width=3, method='gl')` wide aliased lines. Some candidate stroke pixels look partly covered where GL draws them solid. |

| D9 | **Mesh `axes_colorbar` closes with a documented difference.** Only for that scene, the smooth-line rule's 1% frame cap does not apply. Interiors stay exact, every other pixel stays within 32 levels, alpha matches exactly, and the fixture's landmarks match exactly. Implemented in `tools/mesh_layout_smooth_line.py`, with CPU negative controls. | With the 0.14 px line-end fix, the scene's worst pixel fell from 147 to 12 levels. 418 pixels still differed (1.17%, cap 1%). 332 of them are the 166-px axis line's two antialiased edge rows, 11-12 levels off: GL's driver-defined side coverage, which a simple renderer model does not reproduce. |

No decisions are open.

The user has already decided that the Windows napari-threedee row stays
required. W11 publication and W12 upstream posting each need explicit approval.

## Work items

### Release-critical

| ID | Work | Exit | Needs |
| --- | --- | --- | --- |
| R1 (W9) | Windows napari-threedee strict row | A cause and a regression test, then full lifecycle, nine-zero shutdown and all three gates on the release artifact (spec :340-345; status :86-87). A passing replay never closes it (diagnosis :49-50). | Identify the closer. Instrument hot-swap and diagnostic launches and wait for a recurrence. |
| R2 | Release assembly: a fresh build of the then-current source (D1) | Every mandatory row requalified on it, final-head CI, promotion review | R1. The fresh source must include run `w1-w5-native-batch-227`'s patch set (W1, W5 smooth line ends, W15). Those are pinned runtime files, so the Tk candidate's runtime inputs are renewed with it. |

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
| W1 | `GL_EXTENSIONS` reports `texture_float` only when float32 is filterable | CPU tests for both device answers; a napari float image renders with the fallback forced | No native change is needed: the answer is in `src/vispy/gloo/dawn_parser.py`, and `_dawn.device_info()` already reports `float32_filterable`. That file is pinned by the Tk candidate's runtime inputs, so the change lands with R2, like W15. Batched with W5 and W15 in run `w1-w5-native-batch-227`. Overlaps typed-sampling item B5. napari's fallback (`texture_format=None`) is the path fixture I07 covers. **Validated on the batch test wheel**: both CPU device answers, and the forced-fallback napari render within one level of the float path. |
| W2a | W2 residuals: run the 6 `np.row_stack` cases with NumPy 2.4.6, the pairing those suites require, and make the `initialized` suite honour `VISPY_PLUGIN_CANDIDATE_PYTHON` (1 case) | These 7 cases run on the hot-swap stack | **Done** (see Progress). Hot-swap plan, W2 table |
| W3 | Hot-swap audit gates | Controls reached; the stock baseline passes | **Tooling done** (see Progress). The baseline's dynamic record is clean, but on `444402` its `renderer_gl` gate is UNVERIFIED because of one static GL reference in `gloo/glir.py`; it closes on the fresh build with W15. On the batch test wheel, which carries W15, stock napari reaches `PASS_HOT_SWAP_GATES`. Windows only; W7 needs a Linux observer. W8 must decide how a driver's GL activity inside a native swapchain path counts before selecting native presentation. |
| W4 | napari families not yet covered: cyclic labels r8/r16, Shapes/Vectors/Tracks (M10, M11), Surface at napari level (a new fixture), overlays (E06, T04), histogram, sized export (Q03, Q06) | Each matches its OpenGL reference, or has a documented difference fixed before capture | Record results in `compat/vispy-compatibility.json`. |
| W5 | Known defects: M02 and M06 markers, M08 wide lines (16 references; the depth failure is retained), M09 joins, caps and new line fixtures, B03 opacity mutation, H01 screenshot and layer removal with no hidden finish, V04 volume controls | Fixed and admitted. M02 and M06 close with a user-approved documented difference, fixed before re-capture (D4). | V07 and the plane widget belong to W10. V09 timing belongs to W8. M08 covers two residuals. The first is napari-threedee's 3-px manipulator strokes, which block W10's four render-plane-scheduled cases (D8). The second is the ends of smooth GL lines, which block W13's Glue `scatter_axes` (corners and tick ends) and W14's `axes_colorbar` (axis line ends). The data fit GL extending each smooth line end by about 0.13-0.15 px where Dawn ends exactly at the endpoint: a half-covered end pixel is 164 against 127, and a three-quarter one 230 against 191. GL's faint pixel past an axis end also writes depth that hides the tick drawn after it. **Fixed in the batch** (see Progress): a 0.14 px end extension, validated on GPU, ships with R2. A probe on `444402` (run `w5-wide-line-probe-225`) bounds the strokes:
- isolated 3-px aliased lines (horizontal, vertical, diagonal) match GL exactly, so the strokes need a reproduction of the manipulator's segmented arcs, perspective and depth against its markers. The first test is the spherical markers' per-fragment depth (`gl_FragDepth = gl_FragCoord.z + depth_change`, with `depth_change` in GL NDC units) against a stroke that passes a sphere's edge;
- 3-px smooth lines differ only on edges, by up to 37-47 levels;
- M08's reference manifest records an older `tools/fixture_wide_lines.py` hash. |
| W6 | Hot-swap rows for PySide6 and CPython 3.11-3.14 | One row per cell passes W2 and W3 | Wheels for 3.10-3.14 exist only at an earlier epoch, so they must be rebuilt at the current source. Admissions use the 23-job CI and a promotion review. |
| W7 | WSL lavapipe hot-swap rows | WSL rows pass | Measure the smooth-line bound on lavapipe; 32 was measured on NVIDIA only. |
| W8 (PERF-1) | Performance report: interaction frame time, large image and volume loads (including V09 timing), presentation path | A measured report against upstream OpenGL, with no speedup claim; the presentation choice is taken from the data (D3) | Native swapchain presentation is allowed only in hot swap. Inputs: the five-pair timings. PR #2 was closed, but its Qt single-present code is live (`src/vispy/app/backends/_qt.py:790-931`). Explain the unattributed Qt expose paints that invalidated the Native65 five-pair timing run (next-batch plan :443, :485, :3502). |
| W10 | Oracle fixtures: the threedee drag race; the render-plane fixtures, including V07 and the plane widget; the plugin plan's opaque-volume residual. In W2, 11 cases were blocked by unadmitted references in the threedee, initialized and render-plane suites. | Parity tests pass against new admitted oracle captures | New fixture modules and reference packets beside the retained ones, with an admission naming the oracle defect (D6). These suites draw manipulator lines, so they use the smooth-line criterion (D5). **Partly done** (see Progress): the repaired fixtures exist and D5 is applied. The four render-plane-scheduled cases wait on W5's wide-line fix (D8). |
| W11 | Publication: GitHub Release plus a PEP 503 index with hashes, a manylinux build, and the 100 MiB wheel budget | A clean venv installs from the channel and the W2 smoke test passes | Only at the release, after R2 and approval; no preview (D2). Record a new artifact, and never replace the draft release's assets (gaps plan :581-582). Prepared locally (`tools/wheel_index.py`). |
| W12 | Upstream napari lazy `GLError` and qtpy lazy QtOpenGL | Upstream releases contain them | Approval. Drafts are in `docs/upstream-drafts/`. They remove the napari and qtpy patches, but stock Qt still fails the strict gates, so strict rows keep the Qt build without OpenGL. |
| W13 | Glue in hot swap: the five workflows (scatter, scatter edit, scatter axes, volume, volume edit) | All five pass with stock hosts | W3. `scatter_axes` uses the smooth-line criterion (D5; coverage H02). The design requires Glue (:26, :122), and no workstream covered it. **Partly done** (see Progress): 4 of 5 pass on `444402`. On the batch test wheel, which carries the smooth line end fix, all five pass, `scatter_axes` included, and the Glue scenario passes both hot-swap gates; this closes at R2. |
| W14 | Apply the smooth-line criterion to the mesh axes/colorbar scene and re-run it | It passes under the criterion | D5. Its fixture sources are pinned, so the criterion is added in new modules. **Partly done** (see Progress): 12 of 13 scenes pass on `444402`. On the batch test wheel all 13 pass, with `axes_colorbar` under its documented difference (D9); this closes at R2. |
| W15 | Remove upstream's PyOpenGL import from the shipped `gloo/glir.py`: `_check_pyopengl_3D()`, used only by the legacy GL `GlirParser`'s 3D textures | The W3 static scan finds no runtime GL reference, and the W3 stock baseline passes on the fresh build | R2. `glir.py` is pinned by the Tk candidate's runtime inputs, the DIVE PySide2 host environment and the Metal CI reuse record, so the edit lands with the fresh build. `GlirParser` stays public; its 3D-texture path now fails clearly instead. Validated on the batch test wheel: the static scan is clean, and stock napari passes both gates. |

W0 (drag race), W2 (baseline) and W2a are done. W3's tooling is done; its
baseline closes with W15.

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
| B8 | Qt lifecycle: reparenting and WinIdChange, zero-size no-submit, close in flight. Monitor moves and fractional DPI are out of scope and documented as untested (D7). Coverage rows Q02, Q04, Q05. | continuation plan :176; completion plan :239; design :378-387 |
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

## Progress

**W2a done** on 2026-10-28, run `w2a-plugin-residuals-216`.

- **Environment.** The lock is the NumPy 2.4.6 host lock with only `vispy`
  replaced by `444402...`. numba 0.68.0 and llvmlite 0.50.0 came from W2's numba
  lock, and napari-threedee 0.0.29 from its plugin lock. All 537 wheel members
  were verified installed (`wheel-verification.json`).
- **Interpreter fix.** The threedee and initialized suites now launch their
  candidate child in `VISPY_PLUGIN_CANDIDATE_PYTHON`, like the overlay and
  render-plane suites. A CPU contract guard covers all five suites. In this run
  only initialized `retirement` reached the child; the other threedee and
  initialized cases still stop at their reference admission (W10).
- **Initialized `retirement`** now passes exactly in the candidate interpreter.
- **The 6 former `np.row_stack` cases** (render-plane `plane_handles` and
  `plane_clipped`, and all four scheduled cases) now render. They differ only on
  reference edges: 0 interior pixels, and 0.44-0.53% of the frame. But 52-61
  edge pixels per case exceed the 32-level smooth-line bound, by up to 112-132
  levels (median 43-46; 1-2 pixels per case reach 112 or more). So they fail
  the criterion D5 sets for these suites, and any other bound would need a user
  decision. W10 investigates the cause.

**W3 tooling done** on 2026-10-28, run `w3-hot-swap-gates-217`; see
[hot-swap gates](../../hot-swap-gates.md).

- **New modules.** `tools/audit_hot_swap.py` and `tools/hot_swap/` add two gates,
  `renderer_gl` and `no_gl_context_or_draw`. They attribute host GL activity and
  scan the installed renderer package statically.
- **Observer.** It is derived from the pinned strict observer, which is unchanged.
- **Results.** On W2's stock lock with `444402`, all four scenarios match their
  expected verdicts:
  - the host-import control records 16 host GL events and no context or draw.
    Its `renderer_gl` is UNVERIFIED because it never imports vispy;
  - the renderer-import control fails `renderer_gl`;
  - the GL-context control fails `no_gl_context_or_draw`;
  - the stock napari baseline creates no GL context and draws nothing. Its
    dynamic record has 24 host GL events, 0 renderer and 0 unattributed.
- **Not yet passing.** The static scan finds one runtime GL reference in the
  renderer: `gloo/glir.py:1591 import OpenGL.GL`, in upstream's legacy GL
  parser. So the baseline's `renderer_gl` is UNVERIFIED, and W3's exit is not
  met on `444402`. `glir.py` is pinned, so the fix is W15, on the fresh build.
- **Tests.** Thirteen CPU contract tests cover the policy, the controller's tool
  errors and the observer's derivation. CI's curated list is pinned, so they run
  through `tests/contract/test_napari_plugin_wheel_suite.py`.

**W10 partly done** on 2026-10-28, run `w10-oracle-fixtures-219`.

- **The oracle repairs already exist** as new fixture modules beside the retained
  ones, as D6 requires:
  - `tools/fixture_napari_threedee_overlay.py` supersedes the threedee and
    initialized fixtures. It initialises both camera modes before
    napari-threedee adds its empty rotator markers, which upstream VisPy 0.17.0
    cannot bound. It also draws the volume `translucent_no_depth`, because an
    opaque volume hid the handles.
  - `tools/fixture_napari_render_plane_scheduled.py` supersedes the render-plane
    fixture. It delivers napari's 5 ms throttled mouse moves, which is W0's drag
    race on the oracle side.
  - The successors' references are fully admitted. The superseded suites keep
    their unresolved admissions as named oracle-side failures.
- **D5 applied.** All five napari-threedee fixture suites now compare frames
  with the smooth-line criterion, and a CPU guard covers this.
- **Results** on the NumPy 2.4.6 hot-swap stack:
  - overlay passes 5 of 5;
  - initialized `retirement` passes;
  - the four render-plane-scheduled cases fail the criterion: 52-61 pixels per
    case exceed 32 levels, by up to 112-132.
- **What the failure is** (run `w10-render-plane-rule-221`). The pixels lie in
  one 30x30 patch around the manipulator.
  - A one-pixel boundary-move rule, fixed before the re-run, explained 33-46 of
    them per case and left 15-25.
  - Crops show the differing pixels are on the manipulator's 3-px strokes, wide
    aliased GL lines, not on the render plane's boundary, which is identical in
    both frames. The earlier description of plane-raycasting boundary flips was
    wrong.
- **Decided (D8).** The rule is not used. The four cases stay failing until W5
  fixes wide lines.

**W14 partly done** on 2026-10-28, run `w14-mesh-axes-222`, wheel `444402`.

- **New module.** `tools/mesh_layout_smooth_line.py` compares `axes_colorbar`
  with the smooth-line criterion and leaves every other scene to the pinned
  fixture. The unpinned installed-wheel probe uses it, and the parity test
  allows edge alpha only for that scene. A CPU test covers both.
- **Results.** 12 of 13 scenes pass. `axes_colorbar` now renders, where it once
  refused smooth lines, and has no interior differences. It fails the criterion
  on two counts:
  - 4 pixels exceed the bound by up to 147 levels, at the x-axis line's two
    ends. GL's smooth line extends just past each end. That faint pixel's depth
    hides the tick drawn after it, where Dawn shows the tick. This is a smooth
    line end difference, W5's M08.
  - 414 pixels differ, 1.16% of this 224x160 frame, against the 1% cap. Almost
    all are antialiased edges, within the bound, along the 168-px axis line and
    its ticks.
- **Next.** Re-run after W5's smooth line end fix. If only the 1% cap still
  fails, changing it needs a user decision.

**W13 partly done** on 2026-10-28, run `w13-glue-hot-swap-224`, wheel
`444402`, stock Glue hosts; see [Glue wheel regressions](../../glue-wheel-regressions.md).

- **Criterion.** `tools/glue_wheel_suite.py` compares `scatter_axes` with the
  smooth-line criterion (D5). The other four workflows stay exact, and the
  pinned parity test is unchanged.
- **Results.** All five fresh OpenGL references pass.
  - `scatter`, `scatter_edit`, `volume` and `volume_edit` match exactly. The
    volume failure recorded in coverage H02 no longer occurs.
  - `scatter_axes` renders, with no interior or alpha difference. 0.7% of the
    frame differs, but 12 corner and tick-end pixels exceed the bound, by up to
    40 levels. They are smooth line ends, 35-40 levels darker than GL's, W5's
    M08.
- **Hot-swap gates** (`tools/hot_swap/scenarios/stock_glue.py`, all five
  workflows). No GL context or draw. The dynamic record has 11 host GL events, 0
  renderer and 0 unattributed. As with napari, `renderer_gl` is UNVERIFIED only
  on the static `glir.py` reference (W15).

**W1, W5 smooth line ends and W15, batched** on 2026-10-28, run
`w1-w5-native-batch-227`, with a local test wheel `7ad85601...`.

- **Source.** Patches against the pinned sources, which land with R2's
  candidate renewal:
  - `dawn_parser.py` (W1, with CPU tests);
  - `glir.py` (W15);
  - `line_consumer.cpp` (W5: each smooth line end extends 0.14 px past its
    endpoint).
- **Build.** A patched source snapshot was built the way `444402`'s native
  module was (run `windows-native-proof-94`): the sealed SDK
  `windows-x64-release-3`, the same toolchain and the same targets. 44 of 44
  CTest cases pass. The test wheel is `444402` with only the five changed members
  replaced. The rebuilt layer DLL's bytes differ although none of its sources
  changed, so these builds are compared by behaviour, not by hash.
- **Results on the test wheel.**
  - W1: withholding Float32Filterable drops `texture_float`. napari then uses
    `texture_format=None` and renders within one level of the float path.
  - W5: the wide-line fixture's smooth cases fall from 37-47 levels to 1-19,
    where the offline model predicted 0.8-18.8. Strips and loops become exact,
    and aliased cases stay exact. All five Glue workflows pass. All 13 mesh
    scenes pass, `axes_colorbar` under D9. napari-threedee overlay (5 of 5) and
    initialized `retirement` still pass. The four render-plane-scheduled cases
    still fail on the manipulator strokes (D8).
  - W15 and W3: the static scan is clean. Stock napari and stock Glue reach
    `PASS_HOT_SWAP_GATES`, and the controls keep their verdicts.

## Order

1. R1's instrumentation runs alongside everything below.
2. W5's manipulator strokes (D8; first test: spherical marker depth), then the
   rest of W5, and W4. The smooth line ends are fixed in the batch and ship with
   R2.
3. W6 and W7.
4. W8.
5. W15 and R2 (fresh release build), then W11 at the release and W12 on approval.
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
  - The smooth-line criterion applies to the two napari-threedee overlay suites
    and, by D5, to Glue `scatter_axes`, the mesh axes/colorbar scene and the
    napari-threedee fixture suites. Everything else stays exact.
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
| `plans/2026-10-21-{glue-cache,image,mesh-layout,volume}-*-plan.md` | Completed. Glue and mesh-layout are bounded (see D5, W13 and W14). |
| `plans/2026-10-21-napari-plugin-wheel-plan.md` | Completed. Its exact criterion is superseded by the smooth-line decision; its opaque-volume residual is W10. |
| `plans/2026-10-21-smooth-line-mechanism-plan.md` | Superseded by `docs/smooth-lines.md`. |
| `plans/scientific-fixture-coverage.md` | Active registry of coverage IDs, owned by the W, B and HW items here; stale rows refreshed under B16. |
| `plans/2026-10-23-opengl-runtime-removal-plan.md` | Mostly complete; its remaining scope is R1/R2. |
| `plans/2026-10-24-vispy-compatibility-gaps.md` | Log to 2026-10-28; superseded as a plan by this document. |
| `plans/2026-10-28-napari-hot-swap.md` | Origin of W0-W12 and their progress record; work continues here. |
| `docs/opengl-removal-status.md` | Stale since 2026-10-24 (B16). |
