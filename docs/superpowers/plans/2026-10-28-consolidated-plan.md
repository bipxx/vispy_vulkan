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
| Performance (W8) | Report done. Resident scenes keep the refresh rate; uploads are slower than OpenGL's, and partial texture updates much slower (B18). Readback presentation costs over 200 ms per 4K frame (B19). The hot swap moves to native presentation at R2, after the napari parity suites pass under it (D18). | `docs/performance-report.md` |

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
| D8 | **The four render-plane-scheduled cases stay failing and documented, with no new tolerance** (user, 2026-10-29). W5's wide-line fixes were tried first; this revises the user's earlier approval of a looser rule, which rested on a wrong diagnosis. | On the minimum-coverage test wheel (run `w5-fringe-native-234`), 11, 11, 8 and 14 pixels per case still exceed the bound, by up to 104: GL's driver-defined smoothing of short 3D stroke segments (W5 findings). Earlier, 52-61 pixels per case exceeded the 32-level bound. A one-pixel boundary-move rule was fixed and tested before the re-run. It explained 33-46 of them and left 15-25, so all four cases still failed (run `w10-render-plane-rule-221`). Inspection then showed the pixels are not on the render plane's boundary, as first described. They are on napari-threedee's manipulator strokes, vispy `Line(width=3, method='gl')`. They were first described as aliased, but napari-threedee sets `antialias = 2` on them after construction, so they are smooth lines, drawn in 3D against spherical markers that write per-fragment depth. |
| D9 | **Mesh `axes_colorbar` closes with a documented difference.** Only for that scene, the smooth-line rule's 1% frame cap does not apply. Interiors stay exact, every other pixel stays within 32 levels, alpha matches exactly, and the fixture's landmarks match exactly. Implemented in `tools/mesh_layout_smooth_line.py`, with CPU negative controls. | With the 0.14 px line-end fix, the scene's worst pixel fell from 147 to 12 levels. 418 pixels still differed (1.17%, cap 1%). 332 of them are the 166-px axis line's two antialiased edge rows, 11-12 levels off: GL's driver-defined side coverage, which a simple renderer model does not reproduce. |
| D10 | **napari `tracks` and `shapes_selected` (W4, M11) close with a documented difference like D9** (user, 2026-10-29). For those two cases the 1% frame cap does not apply. Interiors stay exact, every pixel stays within 32 levels, alpha matches exactly, and the fixture's landmarks match exactly. Implemented in `tools/napari_vector_layers_comparison.py`, with CPU negative controls. | On the minimum-coverage test wheel, both fail only the frame cap: 2.7% and 3.7% of pixels differ, by at most 14 and 13 levels, with interiors and alpha exact. `shapes_selected` already passes this rule on `444402`; `tracks` needs the minimum coverage that lands with R2. |
| D11 | **W4 napari `colorbar` and `histogram` close with the documented difference of D9 and D10** (user, 2026-10-29). No 1% frame cap; interiors exact, every pixel within 32 levels, alpha exact. Implemented in `tools/napari_layer_families_comparison.py`, with CPU negative controls. | On the test wheel with R2's fixes, 1.5% and 3.2% of pixels differ, on the antialiased box, tick and axis lines, by at most 19 and 12 levels. |
| D12 | **W4 napari `surface_shaded` closes with an edge-pixel rule** (user, 2026-10-29). Interiors (uniform reference 3x3 neighbourhoods) stay exact, and at most 0.1% of the frame may differ, only on edge pixels, by any amount. Implemented in the same module, with CPU negative controls. | 7 of 49,152 pixels differ where the folded surface's front and back faces meet: OpenGL shows a single dark back-face pixel, and Dawn's matches its neighbours. Vertex-precision differences decide which face covers a near-tie pixel. |
| D13 | **H01's glFinish counts are recorded as evidence, not compared** (user, 2026-10-29). The screenshot after a layer removal stays exact, and "no hidden finish" means the harness never requests one. Implemented in `tools/napari_layer_controls_comparison.py`. | napari requests the same finishes in both renderers. OpenGL's `QOpenGLWidget.grabFramebuffer` synchronizes inside Qt, invisible to the command log; the Dawn readback logs the same synchronization as a `glFinish` (2 against 1). |
| D14 | **W5 napari `volume_iso` closes with a small shading rule** (user, 2026-10-29). Pixels whose reference 3x3 neighbourhood is uniform stay exact; at most 0.1% of the frame may differ, each by at most 4 levels. Same module, with CPU negative controls. | 1 of 19,200 pixels differs by 3 levels inside the shaded iso surface: float differences in the hit point or shading normal. The other volume controls match exactly. |
| D15 | **M08's smooth wide-line cases and the defined-depth case use the smooth-line rule without the frame cap, with exact alpha** (user, 2026-10-29). Aliased cases stay exact. This narrows D5's "everything else stays exact" for these two fixtures. Implemented in `tools/wide_lines_comparison.py`, with CPU negative controls. | On the test wheel with R2's fixes, five cases fail only the 1% cap, which is under 8 pixels in a 32x24 frame: 8-68 edge pixels differ, by at most 19 levels, with interiors and alpha exact. |
| D16 | **The wide-line reference tests pin both shared-fixture hashes** (user, 2026-10-29): the packets were captured with `tools/fixture_wide_lines.py` `f689a08a`, and the current fixture is `2568d76f`. | A reviewed publication on 2026-10-11 replaced the shared fixture, adding only the depth clear for `depth_occlusion_smooth`, and asked later source contexts to acknowledge it. The tests never did, so every reference check failed on the hash. |
| D17 | **Markers M02 and M06 close with a documented difference** (user, 2026-10-29, under D4), fixed in the new fixtures before their final capture. M02: uniform pixels exact; at most 0.1% of the frame may differ, only on edge pixels, by any amount. M06: at most 0.5% of pixels may differ by more than 2 levels; every other pixel within 2. | Measured with exact captures first: aliased markers flip 41 edge pixels at exact inside/outside ties on arrow, diamond and tailed_arrow, as in the original native63 failure. The `points` method differs by 1-2 levels on fractional sizes (OpenGL appears to quantize sprite size; truncating to 1/32 explains about 70%), and dense overlap cascades that into 0.24% of pixels. |

| D18 | **The hot swap presents through a native swapchain on Windows, from R2, once the napari parity suites pass under it** (user, 2026-10-29, under D3). GL activity that the audit attributes to a driver's presentation path, outside the renderer, counts as host activity, in the hot-swap profile only. Readback stays the strict no-OpenGL path and is made cheaper (B19). | W8 (`docs/performance-report.md`): at 3840x2160, readback paints are 226 ms apart for a resident image, native paints 2.3 ms. Readback costs about 53 ms per frame even at 1920x1080, and the design forbids interaction that depends on a CPU readback (:631). Stock napari passes both hot-swap gates under each presentation, with no driver GL activity observed. **Parity under native presentation** (run `d18-native-parity-249`, R2 test wheel): no test changes outcome between readback and native. The five in-process napari suites pass 44 of 44 under both. In the plugin suites, the failures are the 17 documented ones (D6, D8) under both. The plugin-wheel suite and four CPU tests could not run outside the main tree; they run in the release tree. |

No decisions are open.

The user has already decided, and confirmed on 2026-10-29, that the Windows
napari-threedee row stays required, so the release waits for R1. On 2026-10-29
the user also chose to finish the full plan (W4-W8 and the backlog) before R2.
W11 publication and W12 upstream posting each need explicit approval.

## Work items

### Release-critical

| ID | Work | Exit | Needs |
| --- | --- | --- | --- |
| R1 (W9) | Windows napari-threedee strict row | A cause and a regression test, then full lifecycle, nine-zero shutdown and all three gates on the release artifact (spec :340-345; status :86-87). A passing replay never closes it (diagnosis :49-50). | Identify the closer. Instrument hot-swap and diagnostic launches and wait for a recurrence. **Instrumentation** (2026-10-29): `tools/pool_watch.py` watches the default thread pool's worker-factory handle and, when it is lost, records the time, the handle's new type and every Python thread's stack. It only queries object types; CPU tests cover the record. Launches enable it with `VISPY_POOL_WATCH=<events.jsonl>`. |
| R2 | Release assembly: a fresh build of the then-current source (D1) | Every mandatory row requalified on it, final-head CI, promotion review | R1. The fresh source must include run `w4-napari-layer-families-236`'s patch set: run `w1-w5-native-batch-227`'s (W1, W5 smooth line ends, W15), run `w5-fringe-native-234`'s minimum smooth coverage, and the Qt backend's Dawn canvas release fix. Those are pinned runtime files, so the Tk candidate's runtime inputs are renewed with it. The patch set is kept, applied to `main`, on the branch `r2/pending-runtime-patches` (O5). D18 adds the switch of the Windows hot swap to native presentation, with strict no-OpenGL qualification selecting readback explicitly. It applies only after the napari parity suites pass under native presentation on the R2 test wheel. |

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
| W3 | Hot-swap audit gates | Controls reached; the stock baseline passes | **Tooling done** (see Progress). The baseline's dynamic record is clean, but on `444402` its `renderer_gl` gate is UNVERIFIED because of one static GL reference in `gloo/glir.py`; it closes on the fresh build with W15. On the batch test wheel, which carries W15, stock napari reaches `PASS_HOT_SWAP_GATES`. W7 adds the Linux observer (run `w7-linux-observer-251`). W8 must decide how a driver's GL activity inside a native swapchain path counts before selecting native presentation. |
| W4 | napari families not yet covered: cyclic labels r8/r16, Shapes/Vectors/Tracks (M10, M11), Surface at napari level (a new fixture), overlays (E06, T04), histogram, sized export (Q03, Q06) | Each matches its OpenGL reference, or has a documented difference fixed before capture | Record results in `compat/vispy-compatibility.json`. **Fixtures done** (see Progress): every listed family has an OpenGL reference, and all pass on test wheels carrying R2's fixes (D10-D12). The matrix records them at R2. |
| W5 | Known defects: M02 and M06 markers, M08 wide lines (16 references; the depth failure is retained), M09 joins, caps and new line fixtures, B03 opacity mutation, H01 screenshot and layer removal with no hidden finish, V04 volume controls | Fixed and admitted. M02 and M06 close with a user-approved documented difference, fixed before re-capture (D4). | V07 and the plane widget belong to W10. V09 timing belongs to W8. M08 covers three residuals. Two are fixed in local test builds and ship with R2: the ends of smooth GL lines (W13 `scatter_axes`, W14 `axes_colorbar`), and the smooth-line fringe behind W4's `tracks` crossing (a minimum coverage, run 234). The third is napari-threedee's smooth 3D manipulator strokes, which keep W10's four render-plane-scheduled cases failing and documented (D8). See W5 findings in Progress. **B03, H01 and V04 have fixtures and pass** (run 237, D13, D14). **M08 passes on the R2 test wheel** under D15 and D16 (run 239). **M09 passes exactly** on `444402` (run 241). **M02 and M06 pass under D17** on `444402` and the R2 test wheel (run 242). **Done**: every W5 item has a fixture and passes, or is a documented failure (D8). |
| W6 | Hot-swap rows for PySide6 and CPython 3.11-3.14 | One row per cell passes W2 and W3 | Wheels for 3.10-3.14 exist only at an earlier epoch, so they must be rebuilt at the current source. Admissions use the 23-job CI and a promotion review. **Started** (see Progress): the PySide6 cp312 cell passes the probe's napari and threedee lifecycles. Its gates match PyQt6's, and both pass on the batch test wheel. The in-process scientific and plugin parity harnesses are PyQt6-only. **Local test wheels done** (2026-10-29, run `w6-abi-hot-swap-248`; the user chose local test builds now). CPython 3.11, 3.13 and 3.14 wheels were built from the R2 branch: the cp312 R2 test wheel with each ABI's two extension modules. All three pass the W3 gates and the probe's napari lifecycle; 3.11 and 3.13 also pass the threedee lifecycle. On 3.14 the threedee lifecycle is blocked upstream: napari-threedee 0.0.29 requires `zarr<3`, and zarr 2 needs a numcodecs older than 0.16, which has no 3.14 wheels. With zarr 3 forced, which fails `pip check`, it passes. Admission waits for R2's fresh build (D1). |
| W7 | WSL lavapipe hot-swap rows | WSL rows pass | Measure the smooth-line bound on lavapipe; 32 was measured on NVIDIA only. **Observer done** (2026-10-29; see Progress): a Linux hot-swap observer derived from the strict LD_AUDIT and ptrace pair. Its WSL native controls pass 20 of 20. Remaining: the Linux napari environments, the probe and gates on a test wheel that carries W15, and the lavapipe smooth-line measurement against Mesa llvmpipe OpenGL. The admitted `bd89a994` has the same `glir.py` PyOpenGL import as `444402`. |
| W8 (PERF-1) | Performance report: interaction frame time, large image and volume loads (including V09 timing), presentation path | A measured report against upstream OpenGL, with no speedup claim; the presentation choice is taken from the data (D3) | Native swapchain presentation is allowed only in hot swap. Inputs: the five-pair timings. PR #2 was closed, but its Qt single-present code is live (`src/vispy/app/backends/_qt.py:790-931`). Explain the unattributed Qt expose paints that invalidated the Native65 five-pair timing run (next-batch plan :443, :485, :3502). The pinned harness (`tools/benchmark_frames.py`) needs two environment settings: upstream PyQt6 canvases need `VISPY_PYQT5_SHARE_CONTEXT=true`, and only `VISPY_QT_PRESENTATION=native` reports the candidate completions it measures. It also passes `texture_format="rgba8"`, which VisPy expands to the invalid `rgbagba8`, so every RGBA workload fails on both sides. `tools/benchmark_frames_w8.py` runs the harness's code with those two lines fixed and the harness's hash recorded (O6). **Report done** (2026-10-29, run `w8-paced-benchmark-245`): [`docs/performance-report.md`](../../performance-report.md). Resident scenes keep the refresh rate, one refresh later than OpenGL. Full uploads run at about half OpenGL's rate. Partial texture updates run at 3.7 frames per second against 60 (B18). Readback presentation costs about 53 ms per frame at 1920x1080 and over 200 ms at 3840x2160 (B19). The unattributed paints come from desktop activity. Presentation: D18 (native for the hot swap from R2, after the napari parity suites pass under it). |
| W10 | Oracle fixtures: the threedee drag race; the render-plane fixtures, including V07 and the plane widget; the plugin plan's opaque-volume residual. In W2, 11 cases were blocked by unadmitted references in the threedee, initialized and render-plane suites. | Parity tests pass against new admitted oracle captures | New fixture modules and reference packets beside the retained ones, with an admission naming the oracle defect (D6). These suites draw manipulator lines, so they use the smooth-line criterion (D5). **Partly done** (see Progress): the repaired fixtures exist and D5 is applied. The four render-plane-scheduled cases stay failing and documented (D8). |
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
| B16 | Refresh stale records: coverage rows that still cite smooth-line refusals (E06, T04, H02, V07, M08); close H06 (now 5/5); refresh `docs/opengl-removal-status.md` (stale since 10-24). **Done** (2026-10-29): those rows, H06 and the other rows W4 and W5 changed (M02, M06, M09, M11, V04, B03, Q03, H01) carry dated statuses, and the status document has a dated update. | digests of 2026-10-28 |
| B17 | The local legacy 12,134-file compiler-cache set has no cleanup receipt. Do not repeat that cleanup blindly, and do not count its savings. | removal plan :120-122 |
| B18 | Partial texture updates copy the whole texture. `apply_texture_data` rebuilds the CPU shadow on every partial update. While a queued frame uses the texture, the update also copies the shadow once more and copies the texture into a new GPU texture. napari's labels painting makes such updates. W8 measured 3.7 frames per second against OpenGL's 60 for eight 64x64 patches per frame on 4096x4096 RGBA layers. The files are pinned runtime inputs, so the fix lands with R2 or later. | `docs/performance-report.md` (Partial texture updates) |
| B19 | Readback presentation's framebuffer read: about 23 ns per pixel natively (`read_canvas` allocates a staging buffer per read and converts each texel through a generic routine), then three Python copies (`_read_dawn_framebuffer`). That is about 53 ms per frame at 1920x1080. Pinned runtime files, as B18. | `docs/performance-report.md` (Readback presentation) |

### Organization (user, 2026-10-29)

| ID | Work | State |
| --- | --- | --- |
| O1 | Make drift between this working tree and published main visible | **Done.** `tools/publication_drift.py` compares every file of the publication clone's `origin/main` with the working tree, byte for byte, and lists changed (marking line-ending-only changes), missing and local-only files. A difference is explained only by the publication's own files (`--expect`) or by `KNOWN`, which records why a file stays local; anything else exits 1. Each publication runs it first. Its first run restored `main`'s bytes for two files whose local copies had lost their mixed line endings, and the missing `.gitattributes`. It also flagged two earlier-session notes: the 2026-10-23 scope note in the smooth-line mechanism plan and the 2026-10-22 Native63 notes in the coverage registry. The user chose to publish them after review (2026-10-29). Run `notes-publication-247` checked every claim against the linked local evidence (wheel, case names, pixel and pin counts; all hold). It marked stale wording as historical, and gave the 13 rows those notes rewrote their date, keeping `main`'s earlier text. |
| O2 | Mark the expected failures as expected | **Done, without xfail**, because the evidence rules forbid skip and xfail. `tests/hosts/conftest.py` and `tests/parity/conftest.py` label the 41 listed failures (D8's four cases and the superseded oracle fixtures kept by D6) in pytest's report and its JUnit XML. They count the failures the index does not explain and name any listed test that passes. No outcome changes. |
| O3 | One registry of the documented differences | **Done.** `tools/documented_outcomes.py` indexes D5 and D9-D17: the modules that apply each decision, and the cases and limits they hold. It also holds the expected failures. A CPU contract checks it against those modules and against each suite's case list. |
| O4 | One curated contract entry instead of re-exports through an unrelated module | **Done.** `tests/contract/curated_contracts.py` lists the curated contract modules. Until R2 the wheel suite imports it; at R2, CI's list names it directly. Its check requires every contract module to run in a workflow, be curated, or be declared. It found 11 published CPU contract modules that run in no workflow (`NOT_IN_CI`); each joins the curated list after a run in CI's environment. `test_wheel_index` stays local until W11 (`UNPUBLISHED`), so the check allows a checkout without it. The first version listed it in `NOT_IN_CI`, which failed every CPU job of PR #38, because the published tree lacks it. The local CI-list run had passed on the local tree, which has it. |
| O5 | Keep the pending runtime patches outside `build/` | **Done.** Branch `r2/pending-runtime-patches` (`bfe66d3`, on `main` `f2f9129`) carries run 236's patch set, with only the replaced lines changed. It has no PR, and no workflow runs on it. R2 builds from it. |
| O6 | Line endings, and the benchmark harness's setup and format | **Done.** `main`'s `.gitattributes` (`* -text`) keeps checkouts byte-preserving, because dependency checksums and pinned file hashes need exact bytes, so mixed line endings are intentional and nothing is normalized; O1 flags line-ending-only drift instead. The pinned W8 harness is fixed in a successor (W8). |

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
  - Crops show the differing pixels are on the manipulator's 3-px strokes, not on
    the render plane's boundary, which is identical in both frames. The earlier
    description of plane-raycasting boundary flips was wrong. The strokes are
    smooth lines: napari-threedee sets `antialias = 2` on them.
- **Decided (D8).** The rule is not used. W5's line fixes reduced the residual
  but did not remove it, so the four cases stay failing and documented (user,
  2026-10-29).

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

**W5 findings so far** (M08 line work).

- **Smooth GL line ends** (W13 Glue `scatter_axes`, W14 `axes_colorbar`).
  - GL extends each smooth line end by about 0.13-0.15 px, where Dawn ended
    exactly at the endpoint: a half-covered end pixel is 164 against 127, and a
    three-quarter one 230 against 191.
  - GL's faint pixel past an axis end also writes depth that hides the tick drawn
    after it.
  - A 0.14 px end extension is fixed in the batch below and ships with R2.
- **Probe on `444402`** (run `w5-wide-line-probe-225`).
  - Isolated 3-px aliased lines (horizontal, vertical, diagonal) match GL
    exactly.
  - 3-px smooth lines differed only on edges, by up to 37-47 levels.
  - M08's reference manifest records an older `tools/fixture_wide_lines.py`
    hash.
- **Manipulator strokes** (D8; run `d8-stroke-mechanism-228`). The strokes are
  smooth lines: napari-threedee sets `antialias = 2` on its `Line(width=3,
  method='gl')` visuals. `plane_handles` was rendered live under GL and Dawn (test
  wheel `7ad85601`) with four manipulator variants:

  | Variant | Pixels over the bound | Differing in total |
  | --- | --- | --- |
  | baseline | 15 (max 143) | 207 |
  | markers not spherical | 23 | 282 |
  | markers hidden | 38 | 394 |
  | lines not smoothed | 3 | 3 |

  So the spherical markers' per-fragment depth is not the cause. The residual is
  the smooth-line coverage of the short 3D stroke segments, which is where GL's
  driver-defined smoothing differs.
- **Fringe coverage** (W4 `tracks`; runs `w5-depth-semantics-233` and
  `w5-fringe-native-234`).
  - Not depth. The OpenGL capture draws with depth testing off, and napari draws
    its first visible layer with blend `(src_alpha, zero)`, so any fragment
    replaces the colour beneath it. Equal-depth crossings with depth testing on
    keep the first primitive in both renderers.
  - GL smoothing on the reference hardware gives no fragment to a pixel the line
    overlaps by at most 1/32 px, and otherwise steps coverage by about 1/16. Dawn
    emitted a fragment for any positive coverage, even from float error at an
    exact pixel boundary. Under that blend it wrote black over the earlier track.
  - Coverage at or below 1/32 is now no fragment, validated below; it lands with
    R2.
- **M08 references** (run `w5-m08-wide-lines-239`, test wheel `66e7e9ad...`).
  - Every wide-line and defined-depth reference check failed on the shared
    fixture's hash: both packets were captured with `f689a08a`, and a reviewed
    publication on 2026-10-11 replaced the fixture with `2568d76f`, adding only
    the depth clear. D16 pins both hashes.
  - Under D15, the wide-line suite passes 17 of 18; the 18th is the retained
    original `depth_occlusion_smooth` capture, an OpenGL-side failure kept by
    design (D6). Its defined-depth successor passes 3 of 3.
  - On `444402` the smooth cases exceed the edge bound (37-47 levels) until R2's
    line-end fix.
- **M09 Agg lines** (run `w5-m09-agg-lines-241`). The scene suite's two Agg
  cases match exactly on the R2 test wheel, so the new
  `tools/fixture_agg_lines.py` is exact, fixed before capture. Its cases are
  every vispy 0.17 cap code, miter, round and bevel joins at a right angle and
  an acute bend, degenerate joins, and `px_scale` 2 and 3. Dry runs corrected
  the scene twice. Upstream draws nothing for a polyline with a full reversal
  or a repeated vertex, and the landmarks record that. Neither the canvas dpi
  nor a larger render size scales line width, so the scale cases use
  `px_scale`. All five match exactly on `444402` and on the R2 test wheel
  (`tests/reference/agg-lines-opengl`,
  `tests/parity/test_agg_lines_parity.py`).
- **M02 and M06 markers** (run `w5-markers-measure-242`).
  - The marker-extension suites pass as admitted. The serialized packet matches
    exactly, 19 of 19. The original and corrected suites fail only on their
    unadmitted OpenGL captures, which the serialized packet supersedes.
  - The old native63 harnesses were not re-run. New repository fixtures took
    their place, first captured exactly to measure:
    `tools/fixture_markers_all_symbols.py`, with all 15 symbols, sizes 8 and
    24, edges 0 and 2, both methods, antialiasing 0 and 1, and scene scaling;
    and `tools/fixture_markers_million.py`, with one million fixed-seed markers
    in both methods.
  - Experiments on the `points` method: draw order and integer or eighth-pixel
    sizes match exactly. Computing `gl_PointCoord` from the fragment position
    changes nothing. Truncating the sprite size to 1/32 px explains about 70%,
    so OpenGL quantizes fractional sprite sizes by an exact rule still unknown
    (backlog).
  - Under D17 both packets pass on `444402` and on the R2 test wheel.

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

**W5 minimum smooth coverage** on 2026-10-28, run `w5-fringe-native-234`, with a
local test wheel `3d28fed6...`: run 227's patch set (by hash) plus the minimum
coverage in `line_consumer.cpp`, built the same way. 44 of 44 CTest cases pass.

- The fringe probe matches OpenGL's edge rows up to 1/64 px. Exactly at 1/32,
  float error still lets one 8-level pixel through.
- napari vector layers: as in W4 above, `tracks` and `shapes_selected` now fail
  only the 1% cap.
- Unchanged elsewhere: the wide-line cases are identical to the batch wheel's.
  The napari-threedee overlay passes 5 of 5 with fewer differing pixels, all 13
  mesh scenes pass (D9), all five Glue workflows pass, and stock napari reaches
  `PASS_HOT_SWAP_GATES`.
- The D8 strokes still fail all four cases, though three improve. For
  `plane_clipped`, `plane_handles`, `plane_rotation` and `plane_translation`,
  pixels over the bound go from 15, 15, 9 and 14 to 11, 11, 8 and 14. The worst
  go from 143, 143, 161 and 82 to 104, 104, 81 and 92.

**W6 started** on 2026-10-28, run `w6-pyside6-hot-swap-230`: the PySide6 cp312 cell
with stock hosts and `444402`.

- **Environment.** The napari input with PyQt6 replaced by PySide6 6.12.0 (the
  project's own pin), compiled with the PyQt6 lock's flags and cutoff date. Only
  `vispy` is replaced. The probe verified that the installed napari, QtPy and
  napari-threedee are byte-identical to their stock wheels.
- **W2 lifecycles.** The probe's napari scenario passes (image, overlay and pan,
  labels edits, 3D volume and export, device loss, close), and so does its
  threedee scenario (registration, Qt drag, device recovery, retirement, close),
  on PySide6 6.12.0 and Qt 6.12.0.
- **W3 gates.** No GL context or draw. The dynamic record has 24 host GL events, 0
  renderer and 0 unattributed. This needed one tooling fix: under PySide6, qtpy's
  `QtDataVisualization` import loads `Qt6OpenGL.dll` with no native caller, so the
  nearest preceding Qt binding import now explains Qt's own GL libraries.
  `renderer_gl` waits on W15, as for PyQt6. On the batch test wheel both gates pass.
  `control_gl_context` now uses qtpy, so it runs under either binding. The PyQt6
  scenarios were re-run with the final tool, and every verdict is unchanged.
- **Not covered.** The in-process scientific suites and the plugin parity suites
  are PyQt6-only harnesses. CPython 3.11, 3.13 and 3.14 need wheels at the current
  source.

**W7 Linux observer** on 2026-10-29, runs `w7-linux-observer-251` and
`w7-review-252`: W7 steps 1-2, done by an implementation agent and reviewed
before publication.

- **Derivation.** `tools/hot_swap/derive_linux_observer.py` builds the auditor,
  debugger and controller from the strict `tools/no_opengl/` Linux pair by exact
  replacements. No pinned file changed, and a test pins the derived files to the
  derivation.
- **What it records.**
  - The auditor stamps wall time on every record, records the object that
    requested each load (`la_objsearch`), and records the referencing object of
    each GL binding.
  - The debugger names the caller from the return address. Context and draw
    calls stop the process tree.
  - Other GL calls are recorded and stepped over past the export's leading
    `endbr64`, with the trap left armed. An export without `endbr64` fails
    closed.
- **Policy.**
  - The context and draw families became prefix and name tables, which the C
    copy is generated from. 379 export names of Windows' `opengl32.dll`
    classify as under the old regexes, so Windows verdicts cannot change.
  - Added for Linux: `libpython3`, `lib`-prefixed Qt GL libraries, POSIX
    origins, versioned `.so` files and ELF undefined symbols.
- **Results.**
  - In WSL, both collectors build with `-Werror`, and the native controls pass
    20 of 20: host calls stepped over once, context, draw and alias calls
    stopped, an export without `endbr64` failing closed, a 32-thread count, and
    fork, exec and static programs.
  - All 3,912 GL exports of WSL's glvnd libraries start with `endbr64`.
  - The local CI check passes 2,522 tests with the new CPU module curated. The
    Linux-only native module is declared in `NOT_IN_CI`.
- **Cleanup.** The guest scratch held pytest's `current` symlinks, which the
  hygiene tool refuses. An audited unlink removed only those 27 links, each
  pointing inside the same scratch, before both cleanups.

**D18 parity under native presentation** on 2026-10-29, run
`d18-native-parity-249`: the eleven napari parity suites on the R2 test wheel
`66e7e9ad`, under readback (the control) and under native presentation.

- **Isolation.** The suites write fixed folders under `build/evidence`, and some of
  those hold earlier runs' evidence in this tree. So they ran in a `git archive`
  copy of `main` without `third_party/`.
  - The plugin suites also read two untracked inputs: the qualified
    napari-threedee wheel and the pinned host environments. Copying environments
    into a run is forbidden, so the copy reached them through read-only directory
    junctions.
  - The junctions were removed before any cleanup. The build-hygiene preflight
    refuses reparse points in managed scratch, and it refused a concurrent
    registration while they existed.
- **Presentation check.** A canvas in that environment reports `native` under
  `VISPY_QT_PRESENTATION=native`, and `readback` otherwise.
- **Results.** Every test has the same outcome under both presentations.
  - The five in-process suites pass 44 of 44: layer controls, layer families,
    vector layers, scientific and volume.
  - The plugin suites fail only their 17 documented cases (D6, D8). The overlay
    suite's five plugin workflows pass.
  - Four CPU tests fail, and the plugin-wheel suite's five cases stop in setup.
    The copy lacks untracked inputs they need from the main tree: a helper
    executable, a host requirements file, and the upstream side's inputs. The
    CPU tests create no graphics by design. The plugin-wheel suite runs in the
    release tree.
- **Limit.** The suites compare offscreen captures, so they show that napari's
  workflows run correctly under native presentation, not that the presented
  pixels match.

**W6 local test wheels** on 2026-10-29, run `w6-abi-hot-swap-248`: CPython 3.11,
3.13 and 3.14 with PyQt6 (user: "Local test builds now").

- **Source.** The branch `r2/pending-runtime-patches` (`bfe66d3`), exported with
  `git archive`. Its 73 native build inputs match run 234's, which built the
  cp312 R2 test wheel's native module. Its Python files match that wheel's
  members; `dawn_parser.py` differs only in line endings.
- **Builds.** The three ABIs built at the same time from the sealed SDK with
  each version's build environment, in about 6.7 minutes each. Each passes its
  44 native CTests.
- **Wheels.** Each is the cp312 R2 test wheel `66e7e9ad` with only its two
  extension modules replaced and its tag updated: `8fc8b114` (cp311), `9819371e`
  (cp313) and `682d1ef1` (cp314). They are local test artifacts, not admitted.
- **Environments.** Each is the PyQt6 napari input compiled for that Python with
  the same flags and cutoff, plus W2's numba and napari-threedee locks.
  - 3.11 pins NumPy 2.4.6, because 2.5.3 has no 3.11 wheels.
  - On 3.14, numcodecs resolves to 0.17.0, which breaks `import zarr` for zarr
    2.18.6 without any renderer involved.
- **Results.** On all three, stock napari reaches `PASS_HOT_SWAP_GATES`, and the
  three controls give their designed verdicts. The probe's napari lifecycle
  passes on all three, and its threedee lifecycle on 3.11 and 3.13. On 3.14
  napari-threedee 0.0.29 cannot be installed in a working state from wheels: it
  requires `zarr<3`. With zarr 3 forced, a diagnostic environment that fails
  `pip check`, both lifecycles pass.
- **R1.** The pool watcher was armed in all eight probe launches through a
  `sitecustomize` that the gate audits leave inactive. It recorded no loss.
- **Testing time.** `tools/ci_local.py` runs the CPU contract workflow's 2,511
  tests in 116 s, against about 330 s one command after another. Its floor is
  `test_compatibility_inventory.py`.

**W4 started** on 2026-10-28, run `w4-napari-vector-layers-232`: coverage M11
(vectors, tracks, a shapes selection).

- **Fixture.** `tools/fixture_napari_vector_layers.py`, with an independent
  OpenGL capture (`tools/oracle_napari_vector_layers_capture.py`, upstream vispy
  0.17.0, napari 0.9.2, RTX 4090) in `tests/reference/napari-vector-layers-opengl`.
  The parity test is `tests/hosts/test_napari_vector_layers_parity.py`.
- **Criteria, fixed before capture.**
  - `vectors` is a triangle mesh and must match exactly.
  - `tracks` (antialiased lines) and `shapes_selected` (meshes, an antialiased
    selection outline and handles) use the smooth-line criterion.
  - A dry run in the OpenGL environment caught two scene errors before any
    capture: a two-point ellipse means centre and radii, and the 0.7 default
    opacity. Both were fixed.
- **Results on `444402`.**
  - `vectors` matches exactly.
  - `tracks` fails where tracks cross: 30 pixels exceed the bound, by up to 225.
    The cause is a smooth-line fringe, not depth (W5 findings).
  - `shapes_selected` fails only the 1% cap. 547 antialiased edge pixels (4.5%)
    differ, none over the bound (max 13), as with D9.
- **On the batch test wheel** the verdicts are the same. Its line-end fix changes
  30 `tracks` pixels, so 18 exceed the bound there, still by up to 225.
- **On the minimum-coverage test wheel** (run `w5-fringe-native-234`), `tracks`
  and `shapes_selected` both fail only the 1% cap: 328 and 457 pixels differ, by
  at most 14 and 13. `vectors` stays exact.
- **D10 applied** (user, 2026-10-29): `tracks` and `shapes_selected` close with a
  documented difference like D9 (`tools/napari_vector_layers_comparison.py`).
  Checked on the retained frames: both pass on the minimum-coverage test wheel.
  On `444402` and the batch wheel, `shapes_selected` passes and `tracks` still
  fails on its 225-level crossing pixels until R2's minimum coverage.

**W4 layer families** on 2026-10-29, run `w4-napari-layer-families-236`: cyclic
labels r8/r16, Surface, the scale bar, axes and colorbar overlays (E06, T04), the
histogram canvas and a sized export (Q03, Q06).

- **Fixture.** `tools/fixture_napari_layer_families.py`, eight cases, with an
  independent OpenGL capture (`tools/oracle_napari_layer_families_capture.py`,
  upstream vispy 0.17.0, napari 0.9.2, RTX 4090) in
  `tests/reference/napari-layer-families-opengl`. The parity test is
  `tests/hosts/test_napari_layer_families_parity.py`.
- **Criteria, fixed before capture.** Labels (uint8 through napari's `r8`
  texture, uint16 through `r16`), the shaded Surface, its wireframe and the sized
  export are exact. The overlays and the histogram draw napari's antialiased
  lines, so they use the smooth-line criterion. Dry runs in the OpenGL
  environment caught four scene errors before capture: r16 ids that repeated
  three colours (napari's cyclic colormap has period 49), a clipped axes
  overlay, a fixed canvas size that blocked the export resize, and an ignored
  scale-bar unit.
- **A Qt backend bug.** On `444402` the parity process aborted after `colorbar`.
  The Qt backend released each Dawn canvas from a lambda connected to the
  widget's `destroyed` signal. Closing a viewer runs napari's `gc.collect()`,
  which cleared a lambda in a garbage cycle; CPython drops a cleared function's
  defaults and name. The signal then called it, which raised `TypeError` in a Qt
  slot, which PyQt6's default excepthook turns into `qFatal`. The canvas also
  leaked. Each release slot now stays reachable from a module registry until it
  runs. `_qt.py` is pinned, so the fix lands with R2. On a Python test wheel
  (`66e7e9ad...`, the minimum-coverage wheel plus this fix), the reproducer is
  clean, the Qt CPU tests pass (29, including a new one), and the parity runs to
  completion.
- **Results on that test wheel**, under D11 and D12: all eight cases pass.
  Labels r8 and r16, the wireframe and the sized export match exactly, and
  `scale_bar_axes` passes the smooth-line criterion.
- **On `444402`**, `scale_bar_axes` and `colorbar` exceed the edge bound (41 and
  43 levels) until R2's line-end fix, and the process aborts before the
  histogram and the export.

**W5 layer controls** on 2026-10-29, run `w5-napari-layer-controls-237`: B03,
H01 and V04.

- **Fixture.** `tools/fixture_napari_layer_controls.py`: seven napari cases, each
  drawn once, changed through napari's public API, and captured. They are an
  opacity change, a first-layer transition, a reordered additive multichannel
  stack (B03), a layer removal followed by napari's public screenshot (H01), and
  volume controls changed after a first frame: the iso threshold, the
  attenuated-MIP attenuation, and the translucent opacity with a smaller ray
  step (V04). All are exact, fixed before capture. The OpenGL capture
  (`tools/oracle_napari_layer_controls_capture.py`) is in
  `tests/reference/napari-layer-controls-opengl`, and the parity test is
  `tests/hosts/test_napari_layer_controls_parity.py`.
- **The finish count.** The first capture counted `glFinish` across Qt paints.
  The Dawn Qt backend's Windows readback presentation finishes once per paint
  by design (W8 measures its cost), so the count moved to paint-suppressed
  change and capture paths. It then differed only for the screenshot (D13).
- **Results** on `444402` and on the test wheel with R2's fixes, under D13 and
  D14: all seven pass. Six match exactly; `volume_iso` differs on one pixel by
  3 levels.

**W8 report** on 2026-10-29, run `w8-paced-benchmark-245`:
[performance report](../../performance-report.md).

- **Runs.** Eight of the 66 workloads, five alternating pairs each, on the stock
  napari lock with the R2 test wheel `66e7e9ad`. They ran under readback and
  native presentation, with vsync. Windows turned the display off during the
  points workloads, so those re-ran with it held on; the RGBA workload ran on
  `tools/benchmark_frames_w8.py`. Both were approved by the user.
- **Results under native presentation.**
  - Resident images, volumes and points keep the refresh rate, one refresh
    later than OpenGL.
  - Full image and volume uploads run at about half OpenGL's rate, bound by
    Python's GLIR packing and the native conversion of the data.
  - Partial texture updates run at 3.7 frames per second against 60 (B18).
  - Cold start is no slower.
- **Readback presentation** cannot be timed by the harness. Separate scripts put
  its framebuffer read at about 23 ns per pixel, plus three Python copies (B19).
- **Unattributed paints.** Five runs show work outside the harness's frames:
  the display waking, Qt repaints, and mouse input over the canvas (upstream
  VisPy renders offscreen to pick on every press, wheel or gesture). Clean
  timing needs an idle desktop.
- **Lost completions.** One candidate run (native presentation) and two
  upstream runs never received a frame's presented completion. All three had
  windows spanning the desktop's three monitors.
- **Presentation.** Stock napari passes both hot-swap gates under readback and
  under native presentation, with the same host GL events and no driver GL
  activity observed. The user chose native presentation for the hot swap from
  R2, after the napari parity suites pass under it (D18).

## Order

1. R1's instrumentation runs alongside everything below.
2. W4's fixtures and all of W5 are done; D8 and D10-D17 are decided. The
   smooth line ends, the minimum smooth coverage and the Qt canvas release are
   fixed in local test builds and ship with R2.
3. W6 is done on local test wheels. W7's observer is done; its environments,
   rows and lavapipe measurement follow.
4. W8: the report is done. D18's napari parity under native presentation is done
   (run 249), except the plugin-wheel suite, which runs in the release tree.
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
  - Each publication first runs `tools/publication_drift.py` against the
    publication clone (O1).
  - A local run of CI's commands covers the local tree, which has local-only
    files. A test that lists a directory must also hold on the published tree
    (PR #38).
  - `tools/ci_local.py` runs the CPU contract workflow's test commands at the
    same time and splits large pytest commands into gate-checked shards
    (user, 2026-10-29: reduce testing time). Use it before publishing code.
    Documentation-only publications skip it.
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
| `docs/opengl-removal-status.md` | Refreshed on 2026-10-29 (B16). |
